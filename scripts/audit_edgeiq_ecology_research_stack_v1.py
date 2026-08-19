from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from edgeiq_memory_safe_io import count_csv_rows_streaming, safe_read_csv, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OUT_AUDIT = DATA / "edgeiq_ecology_research_audit_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_ecology_research_audit_summary_v1.csv"
OUT_FAILURES = DATA / "edgeiq_ecology_research_audit_failures_v1.csv"

ENGINE_VERSION = "EDGEIQ_ECOLOGY_RESEARCH_AUDIT_V1"
BOUNDARY = "OFFLINE_RESEARCH_ONLY"

PATTERNS = [
    "edgeiq_qld_position_schema_*.csv",
    "edgeiq_qld_telemetry_ontology_*.csv",
    "edgeiq_qld_race_state_transition_*.csv",
    "edgeiq_transition_*.csv",
    "edgeiq_ecology_*.csv",
    "edgeiq_research_command_*.csv",
]

REQUIRED_FILES = [
    "edgeiq_qld_position_schema_patterns_v1.csv",
    "edgeiq_qld_telemetry_ontology_summary_v1.csv",
    "edgeiq_qld_race_state_transition_summary_v1.csv",
    "edgeiq_transition_persistence_summary_v1.csv",
    "edgeiq_transition_ecology_drift_summary_v1.csv",
    "edgeiq_ecology_memory_summary_v1.csv",
    "edgeiq_ecology_evolution_summary_v1.csv",
    "edgeiq_ecology_evidence_summary_v1.csv",
    "edgeiq_ecology_governance_summary_v1.csv",
    "edgeiq_ecology_research_ledger_summary_v1.csv",
    "edgeiq_ecology_orchestrator_summary_v1.csv",
    "edgeiq_research_command_summary_v1.csv",
    "edgeiq_ecology_governance_gate_v1.csv",
    "edgeiq_ecology_research_ledger_v1.csv",
    "edgeiq_research_command_feed_v1.csv",
]

AUDIT_FIELDS = [
    "check_name",
    "file_name",
    "status",
    "rows",
    "details",
    "timestamp_utc",
    "research_boundary",
    "live_modelling_yes",
    "live_execution_yes",
    "engine_version",
]

SUMMARY_FIELDS = ["metric", "value"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(value: object) -> str:
    return str(value or "").strip()


def upper(value: object) -> str:
    return clean(value).upper()


def metric_map(path: Path) -> dict[str, str]:
    return {clean(row.get("metric")): clean(row.get("value")) for row in safe_read_csv(path) if clean(row.get("metric"))}


def discover_files() -> list[Path]:
    files: dict[str, Path] = {}
    for pattern in PATTERNS:
        for path in DATA.glob(pattern):
            if path.is_file():
                files[path.name] = path
    return [files[name] for name in sorted(files)]


def csv_headers(path: Path) -> list[str]:
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            return [clean(item) for item in next(reader, [])]
    except Exception:
        return []


def add_check(rows: list[dict[str, str]], check_name: str, file_name: str, status: str, row_count: int, details: str, timestamp: str) -> None:
    rows.append(
        {
            "check_name": check_name,
            "file_name": file_name,
            "status": status,
            "rows": str(row_count),
            "details": details,
            "timestamp_utc": timestamp,
            "research_boundary": BOUNDARY,
            "live_modelling_yes": "0",
            "live_execution_yes": "0",
            "engine_version": ENGINE_VERSION,
        }
    )


def is_zero(value: object) -> bool:
    return upper(value) in {"", "0", "NO", "FALSE"}


def audit_required_files(rows: list[dict[str, str]], timestamp: str) -> None:
    for name in REQUIRED_FILES:
        path = DATA / name
        if not path.exists():
            add_check(rows, "required_file_exists", name, "FAIL", 0, "Required file is missing.", timestamp)
            continue
        row_count = count_csv_rows_streaming(path)
        status = "PASS" if path.stat().st_size > 0 else "FAIL"
        add_check(rows, "required_file_non_empty", name, status, row_count, f"bytes={path.stat().st_size}", timestamp)


def audit_file_flags(rows: list[dict[str, str]], files: list[Path], timestamp: str) -> None:
    for path in files:
        headers = csv_headers(path)
        row_count = count_csv_rows_streaming(path)
        if row_count == 0 and not any(token in path.name for token in ["failures", "alerts", "blocked"]):
            add_check(rows, "row_count", path.name, "WARN", row_count, "File has headers but no data rows.", timestamp)
        else:
            add_check(rows, "row_count", path.name, "PASS", row_count, "File is readable.", timestamp)

        if "offline_research_only" in headers:
            metrics = metric_map(path) if "metric" in headers and "value" in headers else {}
            value = clean(metrics.get("offline_research_only"))
            add_check(rows, "offline_research_only", path.name, "PASS" if value == "YES" else "FAIL", row_count, f"offline_research_only={value}", timestamp)

        if "research_boundary" in headers:
            bad_rows = [item for item in safe_read_csv(path) if clean(item.get("research_boundary")) and clean(item.get("research_boundary")) != BOUNDARY]
            add_check(rows, "research_boundary", path.name, "PASS" if not bad_rows else "FAIL", row_count, f"bad_boundary_rows={len(bad_rows)}", timestamp)

        if "live_modelling_yes" in headers:
            bad_rows = [item for item in safe_read_csv(path) if not is_zero(item.get("live_modelling_yes"))]
            add_check(rows, "live_modelling_lock", path.name, "PASS" if not bad_rows else "FAIL", row_count, f"non_zero_rows={len(bad_rows)}", timestamp)

        if "live_execution_yes" in headers:
            bad_rows = [item for item in safe_read_csv(path) if not is_zero(item.get("live_execution_yes"))]
            add_check(rows, "live_execution_lock", path.name, "PASS" if not bad_rows else "FAIL", row_count, f"non_zero_rows={len(bad_rows)}", timestamp)

        if "approved_for_modelling" in headers:
            bad_rows = [item for item in safe_read_csv(path) if upper(item.get("approved_for_modelling")) == "YES"]
            add_check(rows, "approved_for_modelling_lock", path.name, "PASS" if not bad_rows else "FAIL", row_count, f"approved_yes_rows={len(bad_rows)}", timestamp)

        if "approved_for_execution" in headers:
            bad_rows = [item for item in safe_read_csv(path) if upper(item.get("approved_for_execution")) == "YES"]
            add_check(rows, "approved_for_execution_lock", path.name, "PASS" if not bad_rows else "FAIL", row_count, f"approved_yes_rows={len(bad_rows)}", timestamp)


def audit_governance_ledger(rows: list[dict[str, str]], timestamp: str) -> None:
    governance = {upper(item.get("track")): item for item in safe_read_csv(DATA / "edgeiq_ecology_governance_gate_v1.csv") if clean(item.get("track"))}
    ledger = {upper(item.get("track")): item for item in safe_read_csv(DATA / "edgeiq_ecology_research_ledger_v1.csv") if clean(item.get("track"))}
    contradictions = 0
    for track, gate in governance.items():
        led = ledger.get(track, {})
        gate_status = upper(gate.get("governance_gate_status"))
        research_flag = upper(led.get("approved_for_research"))
        expected = "YES" if gate_status in {"APPROVED_CORE_RESEARCH", "APPROVED_ACTIVE_RESEARCH"} else "WATCHLIST" if gate_status == "WATCHLIST_ONLY" else "NO"
        if research_flag != expected:
            contradictions += 1
    add_check(rows, "governance_ledger_alignment", "edgeiq_ecology_research_ledger_v1.csv", "PASS" if contradictions == 0 else "FAIL", len(ledger), f"contradictions={contradictions}", timestamp)

    approved_count = sum(1 for item in ledger.values() if upper(item.get("approved_for_research")) == "YES")
    add_check(rows, "ledger_approved_research", "edgeiq_ecology_research_ledger_v1.csv", "PASS" if approved_count >= 1 else "FAIL", len(ledger), f"approved_research_rows={approved_count}", timestamp)

    watchlist_leaks = [
        item
        for item in ledger.values()
        if upper(item.get("approved_for_research")) == "WATCHLIST"
        and (upper(item.get("approved_for_modelling")) == "YES" or upper(item.get("approved_for_execution")) == "YES")
    ]
    add_check(rows, "watchlist_boundary_lock", "edgeiq_ecology_research_ledger_v1.csv", "PASS" if not watchlist_leaks else "FAIL", len(ledger), f"watchlist_leak_rows={len(watchlist_leaks)}", timestamp)


def audit_orchestrator_and_feed(rows: list[dict[str, str]], timestamp: str) -> None:
    orchestrator = metric_map(DATA / "edgeiq_ecology_orchestrator_summary_v1.csv")
    health = clean(orchestrator.get("health_status"))
    add_check(rows, "orchestrator_health", "edgeiq_ecology_orchestrator_summary_v1.csv", "PASS" if health == "HEALTHY_RESEARCH_STACK" else "FAIL", count_csv_rows_streaming(DATA / "edgeiq_ecology_orchestrator_summary_v1.csv"), f"health_status={health}", timestamp)

    feed_rows = count_csv_rows_streaming(DATA / "edgeiq_research_command_feed_v1.csv")
    add_check(rows, "command_feed_cards", "edgeiq_research_command_feed_v1.csv", "PASS" if feed_rows > 0 else "FAIL", feed_rows, f"cards={feed_rows}", timestamp)


def overall_status(rows: list[dict[str, str]]) -> str:
    fail_count = sum(1 for row in rows if row["status"] == "FAIL")
    warn_count = sum(1 for row in rows if row["status"] == "WARN")
    if fail_count:
        return "AUDIT_FAIL"
    if warn_count:
        return "AUDIT_WARN"
    return "AUDIT_PASS"


def build_audit() -> None:
    timestamp = utc_now()
    files = discover_files()
    rows: list[dict[str, str]] = []
    audit_required_files(rows, timestamp)
    audit_file_flags(rows, files, timestamp)
    audit_governance_ledger(rows, timestamp)
    audit_orchestrator_and_feed(rows, timestamp)

    failures = [row for row in rows if row["status"] in {"WARN", "FAIL"}]
    status = overall_status(rows)
    pass_count = sum(1 for row in rows if row["status"] == "PASS")
    warn_count = sum(1 for row in rows if row["status"] == "WARN")
    fail_count = sum(1 for row in rows if row["status"] == "FAIL")
    summary = [
        {"metric": "overall_status", "value": status},
        {"metric": "audit_rows", "value": str(len(rows))},
        {"metric": "pass_count", "value": str(pass_count)},
        {"metric": "warn_count", "value": str(warn_count)},
        {"metric": "fail_count", "value": str(fail_count)},
        {"metric": "files_audited", "value": str(len(files))},
        {"metric": "failures_rows", "value": str(len(failures))},
        {"metric": "offline_research_only", "value": "YES"},
        {"metric": "research_boundary", "value": BOUNDARY},
        {"metric": "live_modelling_yes", "value": "0"},
        {"metric": "live_execution_yes", "value": "0"},
        {"metric": "engine_version", "value": ENGINE_VERSION},
    ]

    write_csv_atomic(OUT_AUDIT, rows, AUDIT_FIELDS)
    write_csv_atomic(OUT_SUMMARY, summary, SUMMARY_FIELDS)
    write_csv_atomic(OUT_FAILURES, failures, AUDIT_FIELDS)

    print(f"Ecology audit status: {status}")
    print(f"PASS: {pass_count}")
    print(f"WARN: {warn_count}")
    print(f"FAIL: {fail_count}")
    print("Live modelling: 0")
    print("Live execution: 0")


if __name__ == "__main__":
    build_audit()
