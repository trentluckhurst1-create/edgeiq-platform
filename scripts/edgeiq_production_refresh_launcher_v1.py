from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
DEFAULT_DATA_ROOT = PUBLIC / "data"
DEFAULT_PI_ROOT = PUBLIC / "performance-intelligence"
DEFAULT_RUNTIME_ROOT = Path(os.environ.get("EDGEIQ_RUNTIME_ROOT", "/var/data" if sys.platform != "win32" else str(ROOT)))
DEFAULT_DOCS_PI_ROOT = ROOT / "docs" / "performance-intelligence"
DEFAULT_MARKET_DATA_ROOT = ROOT / "data" / "market" / "ladbrokes"


def env_path(name: str, default: Path) -> Path:
    return Path(os.environ.get(name, str(default))).resolve()


DATA_ROOT = env_path("EDGEIQ_DATA_ROOT", DEFAULT_DATA_ROOT)
PI_ROOT = env_path("EDGEIQ_PERFORMANCE_INTELLIGENCE_ROOT", DEFAULT_PI_ROOT)
DOCS_PI_ROOT = env_path(
    "EDGEIQ_PERFORMANCE_DOCS_ROOT",
    DEFAULT_RUNTIME_ROOT / "docs" / "performance-intelligence",
)
MARKET_DATA_ROOT = env_path(
    "EDGEIQ_MARKET_DATA_ROOT",
    DEFAULT_RUNTIME_ROOT / "data" / "market" / "ladbrokes",
)
HEALTH_PATH = env_path(
    "EDGEIQ_HEALTH_PATH",
    DATA_ROOT / "edgeiq_production_health_v1.json",
)
SEED_DIR = env_path(
    "EDGEIQ_SEED_DIR",
    Path("/var/data/seed") if sys.platform != "win32" else Path("C:/EDGEIQ_DEPLOYMENT_SEED_V1"),
)
SEED_STATE_PATH = env_path(
    "EDGEIQ_SEED_STATE_PATH",
    DEFAULT_RUNTIME_ROOT / "state" / "edgeiq_seed_state_v1.json",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_link(relative_path: Path, target: Path) -> None:
    source = (ROOT / relative_path).resolve()
    target.mkdir(parents=True, exist_ok=True)
    source.parent.mkdir(parents=True, exist_ok=True)
    if source.exists():
        if source.is_symlink() or source.resolve() == target:
            return
        if target == source:
            return
        raise RuntimeError(
            f"Cannot mount {target} at {source}: source already exists and is not a symlink."
        )
    if os.name == "nt":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(source), str(target)],
            check=True,
            capture_output=True,
            text=True,
        )
    else:
        source.symlink_to(target, target_is_directory=True)


def run_command(command: list[str], stage: str) -> dict[str, object]:
    started = utc_now()
    result = subprocess.run(
        command,
        cwd=str(ROOT),
        env={
            **os.environ,
            "PYTHONPATH": str(ROOT)
            + os.pathsep
            + os.environ.get("PYTHONPATH", ""),
        },
        text=True,
    )
    return {
        "stage": stage,
        "command": command,
        "started_utc": started,
        "finished_utc": utc_now(),
        "returncode": result.returncode,
        "status": "PASS" if result.returncode == 0 else "FAIL",
    }


def bootstrap_data() -> dict[str, object]:
    default_enabled = "false" if DEFAULT_RUNTIME_ROOT.resolve() == ROOT.resolve() else "true"
    enabled = str(os.environ.get("EDGEIQ_BOOTSTRAP_ENABLED", default_enabled)).lower() == "true"
    if not enabled:
        return {
            "stage": "production_data_bootstrap",
            "status": "SKIPPED",
            "reason": "EDGEIQ_BOOTSTRAP_ENABLED=false",
        }
    command = [
        sys.executable,
        "scripts/bootstrap_edgeiq_production_data_v1.py",
        "--seed-dir",
        str(SEED_DIR),
        "--data-root",
        str(DEFAULT_RUNTIME_ROOT),
    ]
    if str(os.environ.get("EDGEIQ_BOOTSTRAP_REPLACE_EXISTING", "false")).lower() == "true":
        command.append("--replace-existing")
    return run_command(command, "production_data_bootstrap")


def read_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def count_csv_rows(path: Path) -> int:
    if not path.exists() or path.stat().st_size == 0:
        return 0
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def file_status(path: Path, min_rows: int = 1) -> dict[str, object]:
    exists = path.exists() and path.stat().st_size > 0
    rows = count_csv_rows(path) if path.suffix.lower() == ".csv" else (1 if exists else 0)
    return {
        "path": str(path),
        "exists": exists,
        "bytes": path.stat().st_size if path.exists() else 0,
        "rows_or_items": rows,
        "status": "PASS" if exists and rows >= min_rows else "FAIL",
    }


def current_runner_audit_status(path: Path) -> dict[str, object]:
    status = file_status(path)
    pipeline_failures = 0
    unexplained_missing = 0
    if path.exists() and path.stat().st_size > 0:
        with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as handle:
            for row in csv.DictReader(handle):
                if str(row.get("pipeline_failure", "")).upper() == "YES":
                    pipeline_failures += 1
                if str(row.get("missingness_legitimate_or_failure", "")).upper().startswith("FAIL"):
                    unexplained_missing += 1
    status.update(
        {
            "pipeline_failures": pipeline_failures,
            "unexplained_missing": unexplained_missing,
            "status": "PASS"
            if status["status"] == "PASS" and pipeline_failures == 0 and unexplained_missing == 0
            else "FAIL",
        }
    )
    return status


def build_health(command_results: list[dict[str, object]], trigger: str) -> dict[str, object]:
    daily = read_json(ROOT / "docs" / "operations-readiness" / "daily-refresh" / "edgeiq_daily_product_refresh_v1_audit.json")
    authority = read_json(ROOT / "outputs" / "current-feed-authority-v1" / "edgeiq_current_feed_authority_inventory_v1_summary.json")
    hardening = read_json(ROOT / "outputs" / "production-hardening-v1" / "edgeiq_global_production_data_completeness_v1_summary.json")
    encoding = read_json(ROOT / "outputs" / "production-hardening-v1" / "edgeiq_production_text_encoding_audit_v1_summary.json")
    authority_metrics = (
        authority.get("metrics")
        if isinstance(authority.get("metrics"), dict)
        else authority.get("final_gates")
        if isinstance(authority.get("final_gates"), dict)
        else authority
    )
    current_audit = current_runner_audit_status(DATA_ROOT / "edgeiq_current_runner_intelligence_audit_v1.csv")
    form_guide = file_status(DATA_ROOT / "edgeiq_form_guide_enriched_v2.json")
    performance = file_status(PI_ROOT / "edgeiq_performance_intelligence_product_feeds_v1.json")
    catalog = file_status(DATA_ROOT / "edgeiq_three_day_product_catalog_v1.json")
    window = read_json(DATA_ROOT / "edgeiq_three_day_window_v1.json")
    seed_state = read_json(SEED_STATE_PATH)

    gates = {
        "OPERATIONAL_TODAY": daily.get("operating_date") or window.get("today"),
        "LAST_SUCCESSFUL_REFRESH": daily.get("generated_utc"),
        "THREE_DAY_WINDOW": window,
        "CURRENT_FEED_FRESHNESS_AUTHORITY": authority_metrics.get("CURRENT_FEED_FRESHNESS_AUTHORITY")
        or authority_metrics.get("status")
        or "UNKNOWN",
        "CURRENT_RUNNER_CHAIN": current_audit["status"],
        "FORM_GUIDE": form_guide["status"],
        "PERFORMANCE": performance["status"],
        "CURRENT_CATALOG": catalog["status"],
        "STALE_SOURCE_SELECTION": authority_metrics.get(
            "STALE_SOURCE_SELECTION",
            authority.get("stale_source_selection", "UNKNOWN"),
        ),
        "TEXT_ENCODING": encoding.get("GLOBAL_ENCODING_HEALTH", "UNKNOWN"),
        "GLOBAL_DATA_COMPLETENESS": hardening.get("EDGEIQ_PRODUCTION_HARDENING_V1", "UNKNOWN"),
        "UNEXPLAINED_MISSING": hardening.get("UNEXPLAINED_MISSING", "UNKNOWN"),
        "SOURCE_TO_FEED_DROPS": hardening.get("SOURCE_TO_FEED_DROPS", "UNKNOWN"),
        "PRODUCTION_TEXT_BLOCKERS": encoding.get("PRODUCTION_TEXT_BLOCKERS", "UNKNOWN"),
        "PRODUCTION_DATA_SEEDED": seed_state.get("status", "UNKNOWN"),
    }
    failed_commands = [row for row in command_results if row.get("status") != "PASS"]
    failed_gates = []
    for key, value in gates.items():
        if isinstance(value, dict):
            if not value:
                failed_gates.append(key)
            continue
        if value in {"FAIL", "UNKNOWN", "", None}:
            failed_gates.append(key)
    health = {
        "schema_version": "EDGEIQ_PRODUCTION_HEALTH_V1",
        "generated_utc": utc_now(),
        "trigger": trigger,
        **gates,
        "command_results": command_results,
        "artifacts": {
            "current_runner_audit": current_audit,
            "form_guide": form_guide,
            "performance": performance,
            "catalog": catalog,
            "seed_state": seed_state,
        },
        "EDGEIQ_PRODUCTION_HEALTH": "PASS"
        if not failed_commands and not failed_gates
        else "FAIL",
        "failed_gates": failed_gates,
    }
    return health


def write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    shutil.move(str(temporary), str(path))


def last_command_allows_next(commands: list[dict[str, object]]) -> bool:
    if not commands:
        return True
    return str(commands[-1].get("status", "")).upper() in {"PASS", "SKIPPED"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trigger", default="manual")
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()

    if DATA_ROOT != DEFAULT_DATA_ROOT.resolve():
        ensure_link(Path("public/data"), DATA_ROOT)
    if PI_ROOT != DEFAULT_PI_ROOT.resolve():
        ensure_link(Path("public/performance-intelligence"), PI_ROOT)
    if DOCS_PI_ROOT != DEFAULT_DOCS_PI_ROOT.resolve():
        ensure_link(Path("docs/performance-intelligence"), DOCS_PI_ROOT)
    if MARKET_DATA_ROOT != DEFAULT_MARKET_DATA_ROOT.resolve():
        ensure_link(Path("data/market/ladbrokes"), MARKET_DATA_ROOT)

    commands: list[dict[str, object]] = []
    commands.append(bootstrap_data())
    bootstrap_status = str(commands[-1].get("status", "FAIL")).upper()
    bootstrap_ok = bootstrap_status in {"PASS", "SKIPPED"}
    if not args.audit_only and bootstrap_ok:
        commands.append(
            run_command(
                [sys.executable, "scripts/run_edgeiq_daily_product_refresh_v1.py"],
                "daily_product_refresh",
            )
        )
    if last_command_allows_next(commands):
        commands.append(
            run_command(
                [sys.executable, "scripts/build_edgeiq_current_feed_authority_inventory_v1.py"],
                "current_feed_authority",
            )
        )
    commands.append(
        run_command(
            [sys.executable, "scripts/audit_edgeiq_production_text_encoding_v1.py"],
            "production_text_encoding_audit",
        )
    )
    commands.append(
        run_command(
            [sys.executable, "scripts/audit_edgeiq_global_production_data_completeness_v1.py"],
            "global_production_data_completeness_audit",
        )
    )

    health = build_health(commands, args.trigger)
    write_json_atomic(HEALTH_PATH, health)
    print(json.dumps(health, indent=2, sort_keys=True))
    return 0 if health["EDGEIQ_PRODUCTION_HEALTH"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
