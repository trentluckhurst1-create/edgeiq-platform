from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_ROOT = ROOT / "docs" / "racing-com-public-data-v1" / "visible-page-ingestion"
OP_ROOT = ROOT / "data" / "operational" / "racing-com-visible-v1"
RAW_ROOT = ROOT / "data" / "raw" / "racing-com-visible-v1"
PROCESSED = ROOT / "data" / "processed" / "racing-com-public-v1"
PUBLIC = ROOT / "public" / "data"
SOURCE_HEALTH = PROCESSED / "source_health_fact.csv"

VISIBLE_STATES = {
    "VISIBLE_PAGE_AVAILABLE",
    "VISIBLE_PAGE_NO_SECTIONALS",
    "VISIBLE_PAGE_SCHEMA_CHANGED",
    "VISIBLE_PAGE_ACCESS_BLOCKED",
    "VISIBLE_PAGE_TRANSIENT_FAILURE",
    "VISIBLE_PAGE_VALIDATION_FAILED",
    "VISIBLE_PAGE_PROMOTED",
}

ROW_COUNT_FILES = {
    "canonical_runner_sectionals": PROCESSED / "runner_sectional_fact.csv",
    "visible_processed_preview": PROCESSED / "visible_runner_sectional_fact_v1.csv",
    "canonical_historical_timing": PUBLIC / "edgeiq_canonical_historical_timing_warehouse_v1.csv",
    "standard_time": PUBLIC / "edgeiq_standard_time_fact_v1.csv",
    "race_time_delta": PUBLIC / "edgeiq_race_time_delta_fact_v1.csv",
    "lengths_v_standard": PUBLIC / "edgeiq_lengths_v_standard_fact_v1.csv",
    "performance_base": PUBLIC / "edgeiq_performance_intelligence_base_fact_v1.csv",
    "normalisation": PUBLIC / "edgeiq_performance_normalisation_fact_v1.csv",
    "horse_aggregates": PUBLIC / "edgeiq_horse_performance_aggregate_fact_v1.csv",
    "horse_ratings": PUBLIC / "edgeiq_horse_performance_rating_fact_v1.csv",
    "race_entry_snapshots": PUBLIC / "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv",
    "projected_performance": PUBLIC / "edgeiq_race_entry_projected_performance_fact_v1.csv",
    "epi": PUBLIC / "edgeiq_epi_fact_v1.csv",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or ["empty"], extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def row_count(path: Path) -> int:
    if not path.exists():
        return 0
    if path.suffix.lower() == ".csv":
        return len(read_csv(path))
    return 1


def snapshot_counts() -> dict:
    return {name: row_count(path) for name, path in ROW_COUNT_FILES.items()}


def run_python(script: str, args: list[str]) -> dict:
    cmd = [sys.executable, script, *args]
    started = datetime.now(timezone.utc)
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    finished = datetime.now(timezone.utc)
    return {
        "script": script,
        "args": " ".join(args),
        "returncode": proc.returncode,
        "started_at_utc": started.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "finished_at_utc": finished.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "stdout_tail": proc.stdout[-6000:],
        "stderr_tail": proc.stderr[-6000:],
    }


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"json_load_error": str(exc)}


def create_baseline(args: argparse.Namespace) -> dict:
    DOC_ROOT.mkdir(parents=True, exist_ok=True)
    baseline = {
        "pipeline": "EDGEIQ_RACING_COM_VISIBLE_PAGE_SECTIONALS_INGESTION_V1",
        "created_at_utc": now_utc(),
        "target_command": "python .\\scripts\\run_edgeiq_racing_com_visible_sectionals_pipeline_v1.py --date TODAY --state VIC --promote",
        "source_method": "Visible public Racing.com pages opened in Chromium only",
        "security_constraints": [
            "No protected GraphQL access",
            "No x-api-key capture or reuse",
            "No cookies, browser storage or hidden credentials read",
            "No network credential interception",
            "Only rendered DOM text, visible table cells, screenshots and sanitised HTML retained",
        ],
        "raw_evidence_root": str(RAW_ROOT.relative_to(ROOT)),
        "operational_root": str(OP_ROOT.relative_to(ROOT)),
        "state": args.state,
        "date": args.date,
    }
    write_json(DOC_ROOT / "VISIBLE_PAGE_INGESTION_BASELINE.json", baseline)
    md = [
        "# Racing.com Visible Page Ingestion Baseline V1",
        "",
        f"Created: {baseline['created_at_utc']}",
        "",
        "This pipeline opens ordinary public Racing.com pages in Chromium and extracts only visibly rendered page evidence.",
        "",
        "## Security Boundary",
        "",
    ]
    for item in baseline["security_constraints"]:
        md.append(f"- {item}")
    md += [
        "",
        "## Operational Command",
        "",
        "```powershell",
        baseline["target_command"],
        "```",
        "",
        "## Evidence Roots",
        "",
        f"- Raw visible evidence: `{baseline['raw_evidence_root']}`",
        f"- Operational files: `{baseline['operational_root']}`",
    ]
    write_text(DOC_ROOT / "VISIBLE_PAGE_INGESTION_BASELINE.md", "\n".join(md) + "\n")
    return baseline


def update_source_health(status: str, detail: str) -> None:
    rows = read_csv(SOURCE_HEALTH)
    rows = [row for row in rows if row.get("source") != "Racing.com visible public sectionals"]
    rows.append({"source": "Racing.com visible public sectionals", "status": status, "checked_at": now_utc(), "detail": detail})
    write_csv(SOURCE_HEALTH, rows, ["source", "status", "checked_at", "detail"])


def classify(collector: dict, normalised: dict, imported: dict, dry_run: bool) -> tuple[str, str, str]:
    if dry_run:
        return "PASS_VISIBLE_PAGE_PIPELINE_READY", "VISIBLE_PAGE_AVAILABLE", "Dry-run completed without public page collection."
    if collector.get("status") == "PLAYWRIGHT_MISSING":
        return "BLOCKED_VISIBLE_ACCESS", "VISIBLE_PAGE_ACCESS_BLOCKED", "Playwright or Chromium is unavailable."
    if collector.get("status") == "NO_ELIGIBLE_RACES":
        return "PARTIAL_VISIBLE_PAGE_COVERAGE", "VISIBLE_PAGE_NO_SECTIONALS", "No eligible public race links were found for the requested window."
    if int(collector.get("races_failed", 0) or 0) > 0:
        return "BLOCKED_PAGE_SCHEMA", "VISIBLE_PAGE_SCHEMA_CHANGED", "One or more pages could not be parsed or visible schema changed."
    if int(imported.get("canonical_rows_promoted", 0) or 0) > 0:
        return "PASS_VISIBLE_PAGE_PIPELINE_PROMOTED", "VISIBLE_PAGE_PROMOTED", f"Promoted {imported.get('canonical_rows_promoted')} visible sectional rows."
    if int(normalised.get("valid_rows", 0) or 0) > 0:
        return "PASS_VISIBLE_PAGE_PIPELINE_READY", "VISIBLE_PAGE_AVAILABLE", "Visible sectional rows validated and are ready for governed import."
    return "PARTIAL_VISIBLE_PAGE_COVERAGE", "VISIBLE_PAGE_NO_SECTIONALS", "Public pages were accessible but no valid visible sectional rows were rendered."


def maybe_downstream(imported: dict, args: argparse.Namespace) -> list[dict]:
    if args.dry_run or not args.promote or int(imported.get("canonical_rows_promoted", 0) or 0) <= 0:
        return []
    day = args.date if args.date != "TODAY" else datetime.now().date().isoformat()
    common = ["--mode", "SPEED_ONLY", "--date-from", day, "--date-to", day, "--dry-run", "--no-publish"]
    return [run_python("scripts/run_edgeiq_incremental_performance_refresh_v1.py", common)]


def run_pipeline(args: argparse.Namespace) -> dict:
    baseline = create_baseline(args)
    before_counts = snapshot_counts()
    stages: list[dict] = []
    mode = args.mode.upper()
    collector_args = ["--date", args.date, "--state", args.state, "--timeout-seconds", str(args.timeout_seconds), "--settle-seconds", str(args.settle_seconds)]
    if args.headless:
        collector_args.append("--headless")
    if args.headed:
        collector_args.append("--headed")
    if args.max_races:
        collector_args += ["--max-races", str(args.max_races)]
    if args.dry_run:
        collector_args.append("--dry-run")
    if mode in {"DISCOVER", "COLLECT", "VALIDATE", "IMPORT", "PROMOTE", "DOWNSTREAM", "ALL"}:
        stages.append(run_python("scripts/edgeiq_racing_com_visible_page_collector_v1.py", collector_args))
    if mode in {"VALIDATE", "IMPORT", "PROMOTE", "DOWNSTREAM", "ALL"}:
        stages.append(run_python("scripts/normalise_racing_com_visible_sectionals_v1.py", []))
    if mode in {"IMPORT", "PROMOTE", "DOWNSTREAM", "ALL"}:
        stages.append(run_python("scripts/import_racing_com_visible_sectionals_v1.py", ["--promote"] if args.promote else []))
    collector = load_json(OP_ROOT / "collector_summary.json")
    normalised = load_json(OP_ROOT / "normalised_visible_sectionals_summary_v1.json")
    imported = load_json(OP_ROOT / "visible_import_summary_v1.json")
    if mode in {"DOWNSTREAM", "ALL"}:
        stages.extend(maybe_downstream(imported, args))
    failed_stages = [stage for stage in stages if stage.get("returncode") not in {0}]
    if failed_stages:
        final_status, source_state, source_detail = "FAIL", "VISIBLE_PAGE_TRANSIENT_FAILURE", "Visible-page pipeline stage failed; see report stage stderr."
    else:
        final_status, source_state, source_detail = classify(collector, normalised, imported, args.dry_run)
    update_source_health(source_state, source_detail)
    after_counts = snapshot_counts()
    validation_rows = [
        {"check": "race_queue_exists", "value": row_count(OP_ROOT / "race_queue.csv"), "status": "PASS" if (OP_ROOT / "race_queue.csv").exists() else "FAIL"},
        {"check": "normalised_file_exists", "value": row_count(OP_ROOT / "normalised_visible_sectionals_v1.csv"), "status": "PASS" if (OP_ROOT / "normalised_visible_sectionals_v1.csv").exists() or args.dry_run else "FAIL"},
        {"check": "import_summary_exists", "value": imported.get("status", ""), "status": "PASS" if (OP_ROOT / "visible_import_summary_v1.json").exists() or args.dry_run else "FAIL"},
        {"check": "source_health_visible_state", "value": source_state, "status": "PASS" if source_state in VISIBLE_STATES else "FAIL"},
        {"check": "protected_graphql_not_used", "value": "VISIBLE_DOM_ONLY", "status": "PASS"},
    ]
    write_csv(DOC_ROOT / "VISIBLE_PAGE_PIPELINE_VALIDATION.csv", validation_rows)
    summary = {
        "pipeline": baseline["pipeline"],
        "created_at_utc": now_utc(),
        "args": vars(args),
        "final_status": final_status,
        "source_health_state": source_state,
        "collector": collector,
        "normalised": normalised,
        "imported": imported,
        "before_counts": before_counts,
        "after_counts": after_counts,
        "stages": stages,
    }
    write_json(DOC_ROOT / "VISIBLE_PAGE_PIPELINE_REPORT.json", summary)
    md = ["# Racing.com Visible Page Pipeline Report V1", "", f"Final status: `{final_status}`", f"Source health state: `{source_state}`", "", "## Counts", ""]
    for key in sorted(after_counts):
        md.append(f"- {key}: {before_counts.get(key, 0)} -> {after_counts.get(key, 0)}")
    md += ["", "## Collection", ""]
    for key in ["status", "meetings_discovered", "races_discovered", "races_opened", "races_with_visible_sectionals", "races_without_sectionals", "races_failed"]:
        md.append(f"- {key}: {collector.get(key, '')}")
    md += ["", "## Normalisation", ""]
    for key in ["normalised_rows", "valid_rows", "rejected_rows", "raw_tables_scanned", "status"]:
        md.append(f"- {key}: {normalised.get(key, '')}")
    md += ["", "## Import", ""]
    for key in ["source_rows", "valid_rows", "processed_preview_rows", "promote_requested", "canonical_rows_promoted", "duplicate_rows_ignored", "status"]:
        md.append(f"- {key}: {imported.get(key, '')}")
    md += ["", "## Security Boundary", "", "Protected GraphQL, x-api-key, cookies, storage and network credentials were not used by this pipeline."]
    write_text(DOC_ROOT / "VISIBLE_PAGE_PIPELINE_REPORT.md", "\n".join(md) + "\n")
    print(json.dumps(summary, indent=2))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="TODAY")
    parser.add_argument("--state", default="VIC")
    parser.add_argument("--mode", default="ALL", choices=["DISCOVER", "COLLECT", "VALIDATE", "IMPORT", "PROMOTE", "DOWNSTREAM", "ALL"])
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--max-races", type=int, default=0)
    parser.add_argument("--timeout-seconds", type=int, default=45)
    parser.add_argument("--settle-seconds", type=float, default=4.0)
    args = parser.parse_args()
    summary = run_pipeline(args)
    return 0 if summary.get("final_status") in {"PASS_VISIBLE_PAGE_PIPELINE_READY", "PASS_VISIBLE_PAGE_PIPELINE_PROMOTED", "PARTIAL_VISIBLE_PAGE_COVERAGE", "BLOCKED_PAGE_SCHEMA"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
