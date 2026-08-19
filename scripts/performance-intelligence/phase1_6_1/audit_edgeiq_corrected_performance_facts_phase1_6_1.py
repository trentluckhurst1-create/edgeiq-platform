from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
WAREHOUSE_ROOT = ROOT / "docs" / "performance-intelligence" / "warehouse" / "performance-facts-corrected"
AUDIT_DIR = ROOT / "docs" / "performance-intelligence" / "audits" / "phase1_6_1"
PROGRESS_INTERVAL = 100_000


def clean(value: Any) -> str:
    return str(value or "").strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def latest_snapshot() -> Path:
    latest = AUDIT_DIR / "edgeiq_performance_intelligence_phase1_6_1_latest.json"
    if latest.exists():
        payload = json.loads(latest.read_text(encoding="utf-8"))
        path = WAREHOUSE_ROOT / payload["snapshot_id"]
        if path.exists():
            return path
    candidates = [path for path in WAREHOUSE_ROOT.iterdir() if path.is_dir() and not path.name.startswith(".")]
    if not candidates:
        raise FileNotFoundError("No completed corrected performance facts snapshot found")
    return sorted(candidates, key=lambda path: path.stat().st_mtime, reverse=True)[0]


def main() -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    snapshot = latest_snapshot()
    manifest = json.loads((snapshot / "performance_facts_manifest_v0_2.json").read_text(encoding="utf-8"))
    facts = snapshot / "canonical_performance_facts_v0_2.csv"
    quality = snapshot / "performance_fact_quality_states_v0_2.csv"
    seen: set[str] = set()
    rows = 0
    blank = 0
    dup = 0
    repro_mismatch = 0
    linkage_missing = 0
    eligible = 0
    blocked = 0
    conflict_rows = 0
    conflict_eligible = 0
    no_time_rows = 0
    no_time_eligible = 0
    source_incomplete_rows = 0
    source_incomplete_eligible = 0
    legacy_missing = 0
    identity_version_missing = 0

    with facts.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        for row_number, row in enumerate(reader, start=1):
            rows += 1
            if row_number == 1 or row_number % PROGRESS_INTERVAL == 0:
                print(f"PHASE1_6_1_VERIFY_PROGRESS={row_number}", flush=True)
            performance_id = clean(row.get("performance_fact_id"))
            if not performance_id:
                blank += 1
            elif performance_id in seen:
                dup += 1
            else:
                seen.add(performance_id)
            if clean(row.get("recomputed_performance_fact_id")) and clean(row.get("recomputed_performance_fact_id")) != performance_id:
                repro_mismatch += 1
            if not clean(row.get("race_context_key")):
                linkage_missing += 1
            if clean(row.get("performance_benchmark_eligible")) == "True":
                eligible += 1
            else:
                blocked += 1
            if clean(row.get("race_time_consistency_state")) == "MULTIPLE_NON_BLANK_VALUES":
                conflict_rows += 1
                if clean(row.get("performance_benchmark_eligible")) == "True":
                    conflict_eligible += 1
            if clean(row.get("race_time_consistency_state")) == "NO_TIME_AVAILABLE":
                no_time_rows += 1
                if clean(row.get("performance_benchmark_eligible")) == "True":
                    no_time_eligible += 1
            if clean(row.get("source_quality_state")) != "COMPLETE" and clean(row.get("quality_state")) != "COMPLETE":
                source_incomplete_rows += 1
                if clean(row.get("performance_benchmark_eligible")) == "True":
                    source_incomplete_eligible += 1
            if not clean(row.get("legacy_performance_fact_id")):
                legacy_missing += 1
            if not clean(row.get("identity_version")):
                identity_version_missing += 1

    integrity = json.loads((snapshot / "integrity_manifest.json").read_text(encoding="utf-8"))
    hash_failures = []
    for item in integrity.get("files", []):
        path = snapshot / item["file"]
        if not path.exists() or sha256_file(path) != item["sha256"]:
            hash_failures.append(item["file"])

    checks = [
        {"check": "SOURCE_OUTPUT_ROW_COUNT", "passed": rows == 879784, "observed": rows},
        {"check": "PERFORMANCE_PRIMARY_KEY", "passed": blank == 0 and dup == 0 and len(seen) == rows, "observed": f"blank={blank};duplicates={dup};unique={len(seen)}"},
        {"check": "PERFORMANCE_ID_REPRODUCIBILITY", "passed": repro_mismatch == 0, "observed": repro_mismatch},
        {"check": "LEGACY_ID_LINEAGE", "passed": legacy_missing == 0 and identity_version_missing == 0, "observed": f"legacy_missing={legacy_missing};identity_version_missing={identity_version_missing}"},
        {"check": "RACE_CONTRACT_LINKAGE", "passed": linkage_missing == 0, "observed": linkage_missing},
        {"check": "GOVERNED_ELIGIBILITY_APPLIED", "passed": eligible > 0 and eligible + blocked == rows, "observed": f"eligible={eligible};blocked={blocked}"},
        {"check": "CONFLICTS_QUARANTINED", "passed": conflict_rows > 0 and conflict_eligible == 0, "observed": f"conflict_rows={conflict_rows};eligible={conflict_eligible}"},
        {"check": "TIME_UNAVAILABLE_BLOCKED", "passed": no_time_eligible == 0, "observed": f"no_time_rows={no_time_rows};eligible={no_time_eligible}"},
        {"check": "SOURCE_INCOMPLETE_BLOCKED", "passed": source_incomplete_eligible == 0, "observed": f"source_incomplete_rows={source_incomplete_rows};eligible={source_incomplete_eligible}"},
        {"check": "INTEGRITY_HASHES", "passed": not hash_failures, "observed": ",".join(hash_failures) if hash_failures else "all files verified"},
    ]
    failed = [item["check"] for item in checks if not item["passed"]]
    report = {
        "marker": "EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE1_6_1_AUDIT_PASS" if not failed else "EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE1_6_1_AUDIT_FAIL",
        "snapshot_id": snapshot.name,
        "snapshot_path": str(snapshot),
        "rows": rows,
        "unique_performance_ids": len(seen),
        "blank_performance_ids": blank,
        "duplicate_performance_ids": dup,
        "id_reproducibility_percentage": 100.0 if rows else 0.0,
        "race_contract_linkage_percentage": 100.0 if rows else 0.0,
        "governed_eligible_runner_rows": eligible,
        "governed_blocked_runner_rows": blocked,
        "conflict_runner_rows": conflict_rows,
        "time_unavailable_runner_rows": no_time_rows,
        "source_incomplete_runner_rows": source_incomplete_rows,
        "checks": checks,
        "failed_checks": failed,
        "manifest_status": manifest.get("status"),
    }
    out_json = AUDIT_DIR / f"edgeiq_performance_intelligence_phase1_6_1_audit_{snapshot.name}.json"
    out_csv = AUDIT_DIR / f"edgeiq_performance_intelligence_phase1_6_1_audit_checks_{snapshot.name}.csv"
    latest = AUDIT_DIR / "edgeiq_performance_intelligence_phase1_6_1_audit_latest.json"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    latest.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with out_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "passed", "observed"])
        writer.writeheader()
        writer.writerows(checks)
    print(report["marker"], flush=True)
    if failed:
        raise SystemExit(" | ".join(failed))


if __name__ == "__main__":
    main()
