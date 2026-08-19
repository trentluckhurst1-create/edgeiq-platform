from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DATA = ROOT / "public" / "data"
DOCS_OUT = ROOT / "docs" / "victoria-live-recovery-v1"


STAGES: list[dict[str, Any]] = [
    {
        "order": 1,
        "stage": "Results Warehouse",
        "builder": "scripts/build_edgeiq_daily_official_results_ingestion_v1.py",
        "primary_output": "public/data/edgeiq_canonical_results_truth_v1.csv",
        "audit_outputs": ["public/data/edgeiq_canonical_results_truth_summary_v1.csv"],
        "inputs": ["Racing.com public/discovered results", "daily official results snapshots"],
    },
    {
        "order": 2,
        "stage": "Timed Races",
        "builder": "scripts/promote_edgeiq_timing_warehouse_canonical_v1.py",
        "primary_output": "public/data/edgeiq_canonical_historical_timing_warehouse_v1.csv",
        "audit_outputs": [
            "public/data/edgeiq_timing_canonical_promotion_v1.csv",
            "public/data/edgeiq_timing_canonical_promotion_v1_summary.json",
        ],
        "inputs": ["recovered governed timing warehouse", "canonical results truth"],
    },
    {
        "order": 3,
        "stage": "Standard Times",
        "builder": "scripts/build_edgeiq_standard_time_engine_v1.py",
        "primary_output": "public/data/edgeiq_standard_time_fact_v1.csv",
        "audit_outputs": ["public/data/edgeiq_standard_time_fact_v1_audit.json"],
        "inputs": ["canonical historical timing warehouse"],
    },
    {
        "order": 4,
        "stage": "Race Time Delta",
        "builder": "scripts/build_edgeiq_race_time_delta_versus_standard_v1.py",
        "primary_output": "public/data/edgeiq_race_time_delta_versus_standard_fact_v1.csv",
        "audit_outputs": ["public/data/edgeiq_race_time_delta_versus_standard_fact_v1_audit.json"],
        "inputs": ["canonical historical timing warehouse", "standard time fact"],
    },
    {
        "order": 5,
        "stage": "Lengths v Standard",
        "builder": "scripts/build_edgeiq_lengths_versus_standard_v1.py",
        "primary_output": "public/data/edgeiq_lengths_versus_standard_fact_v1.csv",
        "audit_outputs": ["public/data/edgeiq_lengths_versus_standard_fact_v1_audit.json"],
        "inputs": ["race time delta", "canonical result margins", "length conversion parameter"],
    },
    {
        "order": 6,
        "stage": "Performance Base",
        "builder": "scripts/build_edgeiq_performance_intelligence_base_fact_v1.py",
        "primary_output": "public/data/edgeiq_performance_intelligence_base_fact_v1.csv",
        "audit_outputs": ["public/data/edgeiq_performance_intelligence_base_fact_v1_audit.json"],
        "inputs": ["lengths v standard", "race context", "condition evidence"],
    },
    {
        "order": 7,
        "stage": "Normalisation",
        "builder": "scripts/build_edgeiq_performance_normalisation_fact_v1.py",
        "primary_output": "public/data/edgeiq_performance_normalisation_fact_v1.csv",
        "audit_outputs": ["public/data/edgeiq_performance_normalisation_fact_v1_audit.json"],
        "inputs": ["performance base", "normalisation parameters"],
    },
    {
        "order": 8,
        "stage": "Horse Aggregates",
        "builder": "scripts/build_edgeiq_horse_performance_aggregate_fact_v1.py",
        "primary_output": "public/data/edgeiq_horse_performance_aggregate_fact_v1.csv",
        "audit_outputs": ["public/data/edgeiq_horse_performance_aggregate_fact_v1_audit.json"],
        "inputs": ["performance observations", "normalisation outputs"],
    },
    {
        "order": 9,
        "stage": "Horse Ratings",
        "builder": "scripts/build_edgeiq_horse_performance_rating_fact_v1.py",
        "primary_output": "public/data/edgeiq_horse_performance_rating_fact_v1.csv",
        "audit_outputs": ["public/data/edgeiq_horse_performance_rating_fact_v1_audit.json"],
        "inputs": ["horse aggregates", "rating methodology parameters"],
    },
    {
        "order": 10,
        "stage": "Snapshots",
        "builder": "scripts/build_edgeiq_race_entry_horse_performance_snapshot_fact_v1.py",
        "primary_output": "public/data/edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv",
        "audit_outputs": ["public/data/edgeiq_race_entry_horse_performance_snapshot_fact_v1_audit.json"],
        "inputs": ["horse ratings", "race entry context"],
    },
    {
        "order": 11,
        "stage": "Projected Performance",
        "builder": "scripts/build_edgeiq_race_entry_projected_performance_fact_v1.py",
        "primary_output": "public/data/edgeiq_race_entry_projected_performance_fact_v1.csv",
        "audit_outputs": ["public/data/edgeiq_race_entry_projected_performance_fact_v1_audit.json"],
        "inputs": ["snapshots", "race entry context"],
    },
    {
        "order": 12,
        "stage": "EPI",
        "builder": "scripts/build_edgeiq_race_entry_epi_fact_v1.py",
        "primary_output": "public/data/edgeiq_race_entry_epi_fact_v1.csv",
        "audit_outputs": ["public/data/edgeiq_race_entry_epi_fact_v1_audit.json"],
        "inputs": ["projected performance", "EPI parameters", "entry context"],
    },
    {
        "order": 13,
        "stage": "Daily Operations",
        "builder": "scripts/run_edgeiq_daily_operations_engine_v1.py",
        "primary_output": "public/data/edgeiq_daily_operations_checkpoint_fact_v1.csv",
        "audit_outputs": ["public/data/edgeiq_daily_operations_engine_v1_audit.csv"],
        "inputs": ["core performance facts", "current race discovery", "optional sectionals/weather/market"],
    },
    {
        "order": 14,
        "stage": "React Feeds",
        "builder": "scripts/build_edgeiq_epi_workspace_terminal_feed_v1.py",
        "primary_output": "public/data/edgeiq_epi_workspace_terminal_feed_v1.csv",
        "audit_outputs": ["public/data/edgeiq_epi_workspace_terminal_feed_summary_v1.csv"],
        "inputs": ["EPI", "runtime feed contracts", "Victoria live terminal facts"],
    },
]


def path_exists(rel: str) -> bool:
    return (ROOT / rel).exists()


def csv_count(path: Path) -> tuple[int, list[str]]:
    if not path.exists():
        return 0, []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return 0, []
        return sum(1 for _ in reader), header


def json_summary(path: Path) -> str:
    if not path.exists() or path.suffix.lower() != ".json":
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - forensic script should report, not crash.
        return f"JSON_PARSE_ERROR:{exc}"
    if isinstance(data, dict):
        keys = [
            "status",
            "verdict",
            "acceptance_status",
            "rows",
            "row_count",
            "races",
            "eligible_rows",
            "output_rows",
            "builder_status",
        ]
        parts = [f"{k}={data[k]}" for k in keys if k in data]
        return "; ".join(parts)
    return ""


def main() -> None:
    DOCS_OUT.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    first_zero = ""
    first_missing = ""

    for stage in STAGES:
        output_path = ROOT / stage["primary_output"]
        builder_path = ROOT / stage["builder"]
        row_count, columns = csv_count(output_path) if output_path.suffix.lower() == ".csv" else (0, [])
        output_exists = output_path.exists()
        builder_exists = builder_path.exists()

        audit_existing = [p for p in stage["audit_outputs"] if path_exists(p)]
        audit_summaries = [json_summary(ROOT / p) for p in audit_existing]
        audit_summaries = [s for s in audit_summaries if s]

        if not output_exists and not first_missing:
            first_missing = stage["stage"]
        if output_exists and row_count == 0 and not first_zero:
            first_zero = stage["stage"]

        status = "PASS"
        reason = "primary output exists with non-zero rows"
        if not builder_exists:
            status = "BUILDER_MISSING"
            reason = "builder script not found at expected path"
        elif not output_exists:
            status = "OUTPUT_MISSING"
            reason = "primary output missing"
        elif row_count == 0:
            status = "ZERO_ROWS"
            reason = "primary output exists but has zero data rows"

        rows.append(
            {
                "order": stage["order"],
                "stage": stage["stage"],
                "builder": stage["builder"],
                "builder_exists": "YES" if builder_exists else "NO",
                "primary_output": stage["primary_output"],
                "output_exists": "YES" if output_exists else "NO",
                "row_count": row_count,
                "column_count": len(columns),
                "audit_outputs_found": "|".join(audit_existing),
                "audit_summary": " | ".join(audit_summaries),
                "inputs": "|".join(stage["inputs"]),
                "status": status,
                "reason": reason,
            }
        )

    zero_or_missing = [r for r in rows if r["status"] != "PASS"]
    first_blocker = zero_or_missing[0]["stage"] if zero_or_missing else "NONE"
    overall_status = "PIPELINE_FORENSICS_PASS" if not zero_or_missing else "PIPELINE_FORENSICS_BLOCKER_FOUND"

    csv_path = DOCS_OUT / "edgeiq_victoria_live_pipeline_forensics_v1.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "status": overall_status,
        "stages_audited": len(rows),
        "passing_stages": sum(1 for r in rows if r["status"] == "PASS"),
        "blocked_stages": len(zero_or_missing),
        "first_zero_stage": first_zero or "NONE",
        "first_missing_stage": first_missing or "NONE",
        "first_blocker": first_blocker,
    }
    (DOCS_OUT / "edgeiq_victoria_live_pipeline_forensics_v1_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    report_lines = [
        "# EDGEiQ Victoria Live Pipeline Forensics V1",
        "",
        f"Status: {overall_status}",
        f"Stages audited: {summary['stages_audited']}",
        f"Passing stages: {summary['passing_stages']}",
        f"Blocked stages: {summary['blocked_stages']}",
        f"First zero stage: {summary['first_zero_stage']}",
        f"First missing stage: {summary['first_missing_stage']}",
        f"First blocker: {summary['first_blocker']}",
        "",
        "## Stage Results",
        "",
    ]
    for r in rows:
        report_lines.extend(
            [
                f"### {r['order']}. {r['stage']}",
                f"- Status: {r['status']}",
                f"- Builder: {r['builder']} ({r['builder_exists']})",
                f"- Output: {r['primary_output']} ({r['output_exists']})",
                f"- Rows: {r['row_count']}",
                f"- Reason: {r['reason']}",
                "",
            ]
        )
    (DOCS_OUT / "edgeiq_victoria_live_pipeline_forensics_v1.md").write_text(
        "\n".join(report_lines), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
