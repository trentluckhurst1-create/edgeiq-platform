from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DOCS = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
DATA = ROOT / "public" / "data"
PROD = DATA / "edgeiq_racingcom_performance_warehouse_v2.csv"
CAND = DATA / "edgeiq_racingcom_performance_warehouse_v2_RUNNER_CANDIDATE.csv"
STATE = DOCS / "edgeiq_racingcom_production_orchestration_state_v1.json"
AUDIT = DOCS / "edgeiq_racingcom_production_orchestration_audit_v1.csv"
SUMMARY = DOCS / "edgeiq_racingcom_production_orchestration_summary_v1.json"
MANIFEST = DOCS / "edgeiq_racingcom_production_orchestration_manifest_v1.json"
REPORT = DOCS / "edgeiq_racingcom_production_orchestration_report_v1.md"
BACKUP_DIR = DOCS / "production-orchestration-backups"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["stage", "status", "exit_code", "detail"])
        writer.writeheader()
        writer.writerows(rows)


def run(script: str, env: dict[str, str] | None = None, extra: list[str] | None = None) -> tuple[int, str]:
    cmd = [sys.executable, "-u", str(ROOT / "scripts" / script)]
    if extra:
        cmd.extend(extra)
    result = subprocess.run(cmd, cwd=str(ROOT), env=env, text=True, capture_output=True)
    return result.returncode, (result.stdout + result.stderr).strip()


def promote_if_needed(no_promote: bool) -> tuple[str, str]:
    prod_sha = sha(PROD)
    cand_sha = sha(CAND)
    if prod_sha == cand_sha:
        return "NO_OP_HASH_UNCHANGED", ""
    if no_promote:
        return "PROMOTION_SKIPPED_NO_PROMOTE", ""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = BACKUP_DIR / f"edgeiq_racingcom_performance_warehouse_v2_PRE_ORCHESTRATOR_PROMOTION_{ts}.csv"
    shutil.copy2(PROD, backup)
    tmp = PROD.with_suffix(".csv.tmp")
    shutil.copy2(CAND, tmp)
    tmp.replace(PROD)
    return "PROMOTED_ATOMIC", str(backup.relative_to(ROOT))


def row_counts() -> dict[str, int]:
    prod = read_csv(PROD)
    cand = read_csv(CAND)
    return {
        "production_rows": len(prod),
        "production_races": len({r.get("race_id") for r in prod}),
        "candidate_rows": len(cand),
        "candidate_races": len({r.get("race_id") for r in cand}),
        "candidate_graphql_rows": sum(1 for r in cand if r.get("sectional_source") == "RACING.COM_GRAPHQL_GETRACEFORM_V2"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Governed Racing.com V2 production ingestion orchestrator.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--network", action="store_true", help="Acquire uncached eligible GraphQL races. Requires EDGEIQ_RACINGCOM_WIDGET_API_KEY.")
    mode.add_argument("--offline", action="store_true", help="Reuse existing acquisition/cache outputs.")
    parser.add_argument("--resume", action="store_true", help="Retain and report continuation state.")
    parser.add_argument("--audit-only", action="store_true", help="Run gates without rebuilding discovery/acquisition stages.")
    parser.add_argument("--race-id", default="", help="Optional diagnostic race id. Current implementation records it in manifest and does not truncate discovery.")
    parser.add_argument("--force-refresh", action="store_true", help="Permits network acquisition to refresh request outputs when configured.")
    parser.add_argument("--no-promote", action="store_true", help="Build and audit candidate but do not promote.")
    args = parser.parse_args()

    network = bool(args.network)
    offline = bool(args.offline or not args.network)
    run_id = datetime.now(timezone.utc).strftime("racingcom_prod_orchestration_%Y%m%dT%H%M%SZ")
    api_key = os.environ.get("EDGEIQ_RACINGCOM_WIDGET_API_KEY", "").strip()
    stages: list[dict[str, str]] = []

    if network and not api_key:
        stages.append({"stage": "network_configuration", "status": "BLOCKED_MISSING_API_KEY", "exit_code": "2", "detail": "EDGEIQ_RACINGCOM_WIDGET_API_KEY is MISSING. Value not printed."})
        write_csv(AUDIT, stages)
        summary = {"decision": "RACINGCOM_PRODUCTION_ORCHESTRATION_BLOCKED_BY_CONFIG", "api_key_status": "MISSING", "production_changed": "NO", **row_counts()}
        SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        MANIFEST.write_text(json.dumps({"run_id": run_id, "mode": "NETWORK", "decision": summary["decision"], "api_key_status": "MISSING"}, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        REPORT.write_text("# Racing.com Production Orchestration\n\nDecision: `RACINGCOM_PRODUCTION_ORCHESTRATION_BLOCKED_BY_CONFIG`\n\nNetwork mode requires `EDGEIQ_RACINGCOM_WIDGET_API_KEY`. Value was not printed or written.\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 2

    scripts = [] if args.audit_only else [
        "build_edgeiq_racingcom_meeting_discovery_v2.py",
        "build_edgeiq_racingcom_race_discovery_v2.py",
        "build_edgeiq_racingcom_graphql_race_evidence_v1.py",
        "build_edgeiq_racingcom_graphql_source_admission_v1.py",
        "build_edgeiq_racingcom_graphql_request_contract_v1.py",
    ]
    if network and not args.audit_only:
        child_env = os.environ.copy()
        child_env["RACINGCOM_PUBLIC_WIDGET_API_KEY"] = api_key
        scripts.append("build_edgeiq_racingcom_graphql_acquisition_v1.py")
    elif offline:
        stages.append({"stage": "graphql_acquisition", "status": "OFFLINE_CACHE_REUSE", "exit_code": "0", "detail": "Existing acquisition ledger and raw cache reused."})
    scripts.extend([
        "validate_edgeiq_racingcom_graphql_response_v1.py",
        "build_edgeiq_racingcom_graphql_parser_v2.py",
        "build_edgeiq_racingcom_canonical_speed_contract_v1.py",
        "build_edgeiq_racingcom_runner_aggregate_adapter_v2.py",
        "audit_edgeiq_racingcom_runner_candidate_historical_regression_v1.py",
        "audit_edgeiq_racingcom_graphql_runner_aggregate_validation_v1.py",
        "audit_edgeiq_racingcom_runner_candidate_downstream_compatibility_v1.py",
        "audit_edgeiq_racingcom_runner_candidate_readiness_v1.py",
    ])

    ok = True
    for script in scripts:
        env = None
        if script == "build_edgeiq_racingcom_graphql_acquisition_v1.py":
            env = child_env
        code, out = run(script, env=env)
        status = "PASS" if code == 0 else "FAIL"
        stages.append({"stage": script, "status": status, "exit_code": str(code), "detail": out[-800:]})
        if code != 0:
            ok = False
            break

    promotion_status = "NOT_ATTEMPTED"
    backup = ""
    if ok:
        promotion_status, backup = promote_if_needed(args.no_promote or args.audit_only)
        stages.append({"stage": "atomic_promotion", "status": promotion_status, "exit_code": "0", "detail": backup})

    counts = row_counts()
    decision = "RACINGCOM_PRODUCTION_ORCHESTRATION_PASS" if ok and promotion_status in {"NO_OP_HASH_UNCHANGED", "PROMOTED_ATOMIC", "PROMOTION_SKIPPED_NO_PROMOTE"} else "RACINGCOM_PRODUCTION_ORCHESTRATION_FAIL"
    state = {"last_run_id": run_id, "last_decision": decision, "resume_supported": "YES", "race_id_filter_requested": args.race_id, "complete": "YES" if ok else "NO"}
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    write_csv(AUDIT, stages)
    summary = {"decision": decision, "mode": "NETWORK" if network else "OFFLINE", "promotion_status": promotion_status, "backup_path": backup, "api_key_status": "AVAILABLE" if api_key else "MISSING", "production_changed": "YES" if promotion_status == "PROMOTED_ATOMIC" else "NO", **counts, "production_sha256": sha(PROD), "candidate_sha256": sha(CAND)}
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    MANIFEST.write_text(json.dumps({"run_id": run_id, "args": vars(args), "summary": summary, "stages": stages}, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT.write_text(f"# Racing.com Production Orchestration\n\nDecision: `{decision}`\n\nMode: `{summary['mode']}`\n\nPromotion status: `{promotion_status}`\n\nProduction changed: `{summary['production_changed']}`\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if decision.endswith("_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
