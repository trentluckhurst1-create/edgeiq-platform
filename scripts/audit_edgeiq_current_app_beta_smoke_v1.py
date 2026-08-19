from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SRC = ROOT / "src" / "edgeiq-os" / "race"
OUT_JSON = DATA / "edgeiq_current_app_beta_smoke_v1_audit.json"
OUT_TXT = DATA / "edgeiq_current_app_beta_smoke_v1_audit.txt"

REQUIRED_MARKERS = {
    "edgeiq_current_app_dependency_graph_v1_audit.json": "EDGEIQ_CURRENT_APP_DEPENDENCY_GRAPH_V1_AUDIT_PASS",
    "edgeiq_current_identity_matching_v1_audit.json": "EDGEIQ_CURRENT_IDENTITY_MATCHING_V1_AUDIT_PASS",
    "edgeiq_current_map_matching_repair_v1_audit.json": "EDGEIQ_CURRENT_MAP_MATCHING_REPAIR_V1_AUDIT_PASS",
    "edgeiq_current_insights_matching_repair_v1_audit.json": "EDGEIQ_CURRENT_INSIGHTS_MATCHING_REPAIR_V1_AUDIT_PASS",
    "edgeiq_historical_epi_matching_repair_v1_audit.json": "EDGEIQ_HISTORICAL_EPI_MATCHING_REPAIR_V1_AUDIT_PASS",
    "edgeiq_current_analytical_matching_repair_v1_audit.json": "EDGEIQ_CURRENT_ANALYTICAL_MATCHING_REPAIR_V1_AUDIT_PASS",
    "edgeiq_market_coverage_repair_v1_audit.json": "EDGEIQ_MARKET_COVERAGE_REPAIR_V1_AUDIT_PASS",
    "edgeiq_current_gear_availability_v1_audit.json": "EDGEIQ_CURRENT_GEAR_AVAILABILITY_V1_AUDIT_PASS",
    "edgeiq_current_eri_results_readiness_v1_audit.json": "EDGEIQ_CURRENT_ERI_RESULTS_READINESS_V1_AUDIT_PASS",
    "edgeiq_current_lock_reconciliation_v1_audit.json": "EDGEIQ_CURRENT_LOCK_RECONCILIATION_V1_AUDIT_PASS",
    "edgeiq_beta_readiness_report_v2_audit.json": "EDGEIQ_BETA_READINESS_REPORT_V2_AUDIT_PASS",
    "edgeiq_current_victorian_end_to_end_v2_audit.json": "EDGEIQ_CURRENT_VICTORIAN_END_TO_END_V2_AUDIT_PASS",
}

REQUIRED_FEEDS = [
    "edgeiq_three_day_product_catalog_v1.json",
    "edgeiq_market_terminal_feed_v1.csv",
    "edgeiq_map_terminal_feed_v1.csv",
    "edgeiq_insights_terminal_feed_v1.csv",
    "edgeiq_epi_workspace_terminal_feed_v1.csv",
    "edgeiq_gear_terminal_feed_v1.csv",
    "edgeiq_meeting_results_terminal_feed_v1.csv",
]

REQUIRED_BUILDERS = [
    "build_edgeiq_market_terminal_feed_v1.py",
    "build_edgeiq_map_terminal_feed_v1.py",
    "build_edgeiq_insights_terminal_feed_v1.py",
    "build_edgeiq_epi_workspace_terminal_feed_v1.py",
    "build_edgeiq_beta_readiness_report_v2.py",
]

FORBIDDEN_VISIBLE_TERMS = [
    "Back/Lay",
    "COMMAND",
    "Background Run",
    "Historical Reference",
    "Analyst Summary",
]


def marker_from_json(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return str(payload.get("marker") or payload.get("audit_marker") or payload.get("status") or "")


def parse_feed(path: Path) -> dict:
    if path.suffix.lower() == ".json":
        json.loads(path.read_text(encoding="utf-8"))
        return {"path": path.name, "type": "json", "rows": None, "status": "PASS"}
    rows = 0
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        for _ in reader:
            rows += 1
    return {"path": path.name, "type": "csv", "rows": rows, "status": "PASS"}


def active_source_files() -> list[Path]:
    files = []
    for pattern in ("*.tsx", "*.ts"):
        for path in SRC.rglob(pattern):
            name = path.name.upper()
            if "CHECKPOINT" in name or "STABLE" in name or ".BAK" in name:
                continue
            files.append(path)
    return files


def main() -> None:
    failures: list[str] = []
    marker_checks = []
    for file_name, expected_marker in REQUIRED_MARKERS.items():
        path = DATA / file_name
        if not path.exists():
            failures.append(f"MISSING_AUDIT:{file_name}")
            marker_checks.append({"file": file_name, "status": "MISSING", "expected": expected_marker, "actual": ""})
            continue
        actual = marker_from_json(path)
        ok = expected_marker in actual
        if not ok:
            failures.append(f"AUDIT_MARKER_MISMATCH:{file_name}")
        marker_checks.append({"file": file_name, "status": "PASS" if ok else "FAIL", "expected": expected_marker, "actual": actual})

    feed_checks = []
    for file_name in REQUIRED_FEEDS:
        path = DATA / file_name
        if not path.exists():
            failures.append(f"MISSING_FEED:{file_name}")
            feed_checks.append({"path": file_name, "status": "MISSING"})
            continue
        try:
            feed_checks.append(parse_feed(path))
        except Exception as exc:
            failures.append(f"FEED_PARSE_FAIL:{file_name}:{exc}")
            feed_checks.append({"path": file_name, "status": "FAIL", "error": str(exc)})

    builder_checks = []
    for file_name in REQUIRED_BUILDERS:
        path = ROOT / "scripts" / file_name
        ok = path.exists()
        if not ok:
            failures.append(f"MISSING_BUILDER:{file_name}")
        builder_checks.append({"file": file_name, "status": "PASS" if ok else "MISSING"})

    forbidden_hits = []
    for path in active_source_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for term in FORBIDDEN_VISIBLE_TERMS:
            if term in text:
                forbidden_hits.append({"file": str(path.relative_to(ROOT)), "term": term})
    if forbidden_hits:
        failures.append("FORBIDDEN_VISIBLE_TERMS_IN_ACTIVE_SOURCE")

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    marker = "EDGEIQ_CURRENT_APP_BETA_SMOKE_V1_AUDIT_PASS" if not failures else "EDGEIQ_CURRENT_APP_BETA_SMOKE_V1_AUDIT_FAIL"
    audit = {
        "marker": marker,
        "generated_at": generated_at,
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "marker_checks": marker_checks,
        "feed_checks": feed_checks,
        "builder_checks": builder_checks,
        "forbidden_hits": forbidden_hits,
        "confirmations": [
            "Meeting lock reconciliation present",
            "Race/current terminal feeds parse",
            "Selected-race and selected-runner identity audits pass",
            "No forbidden profile terms found in active race source files",
            "Build must be run after this audit for final compile proof",
        ],
    }
    OUT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    OUT_TXT.write_text(
        "\n".join(
            [
                marker,
                f"status={audit['status']}",
                f"failures={'; '.join(failures) if failures else 'none'}",
                f"feeds_checked={len(feed_checks)}",
                f"markers_checked={len(marker_checks)}",
            ]
        ),
        encoding="utf-8",
    )
    print(marker)
    if failures:
        raise SystemExit("; ".join(failures))


if __name__ == "__main__":
    main()
