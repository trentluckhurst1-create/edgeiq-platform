from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

from edgeiq_results_common_v1 import DATA, ROOT, coverage_pct, has_value, read_csv, row_has_speed, summarize_master, write_csv


ORCH_OUT = DATA / "edgeiq_post_race_capture_orchestrator_summary_v1.csv"
QUALITY_OUT = DATA / "edgeiq_post_race_data_quality_summary_v1.csv"

PIPELINE = [
    "audit_edgeiq_speed_source_coverage_v1.py",
    "build_edgeiq_speed_master_v1.py",
    "build_edgeiq_results_master_v1.py",
    "build_edgeiq_results_calendar_index_v1.py",
    "audit_edgeiq_results_sp_population_v1.py",
    "audit_edgeiq_sp_join_trace_v1.py",
    "build_edgeiq_standard_times_v1.py",
    "build_edgeiq_standardised_sectionals_v1.py",
    "build_edgeiq_form_sectional_terminal_feed_v1.py",
    "build_edgeiq_gear_terminal_feed_v1.py",
    "build_edgeiq_results_terminal_feed_v1.py",
    "build_edgeiq_speed_retry_engine_v1.py",
    "build_edgeiq_true_track_rating_engine_v1.py",
    "build_edgeiq_sectional_intelligence_v1.py",
    "build_edgeiq_historical_year_feed_v1.py",
    "build_edgeiq_historical_month_feed_v1.py",
    "build_edgeiq_historical_meeting_feed_v1.py",
    "build_edgeiq_historical_race_feed_v1.py",
    "build_edgeiq_historical_runner_feed_v1.py",
    "build_edgeiq_sectionals_retry_queue_v1.py",
    "audit_edgeiq_speed_master_quality_v1.py",
]


def run_script(name: str) -> dict[str, object]:
    script = ROOT / "scripts" / name
    started = datetime.now().replace(microsecond=0).isoformat()
    if not script.exists():
        return {
            "step": name,
            "script": str(script),
            "status": "SKIPPED_MISSING",
            "returncode": "",
            "started_at": started,
            "finished_at": datetime.now().replace(microsecond=0).isoformat(),
            "output_tail": "",
        }

    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    finished = datetime.now().replace(microsecond=0).isoformat()
    output = "\n".join((proc.stdout + "\n" + proc.stderr).splitlines()[-8:])
    return {
        "step": name,
        "script": str(script),
        "status": "OK" if proc.returncode == 0 else "FAILED",
        "returncode": proc.returncode,
        "started_at": started,
        "finished_at": finished,
        "output_tail": output[:2000],
    }


def write_quality_summary() -> None:
    master = DATA / "edgeiq_results_master_v1.csv"
    rows = list(read_csv(master)) if master.exists() else []
    summary = summarize_master(rows)
    resulted_races = {row.get("race_key", "") for row in rows if row.get("result_status") == "RESULTED" and row.get("race_key", "")}
    sectionals_races = {
        row.get("race_key", "")
        for row in rows
        if row.get("race_key", "") and (row.get("sectional_status") == "CAPTURED" or row_has_speed(row))
    }
    resulted_sectionals_races = sectionals_races.intersection(resulted_races)
    sp_races = {
        row.get("race_key", "")
        for row in rows
        if row.get("race_key", "") and (has_value(row.get("sp", "")) or has_value(row.get("starting_price", "")))
    }

    retry_summary_path = DATA / "edgeiq_sectionals_retry_queue_summary_v1.csv"
    retry_summary = next(iter(read_csv(retry_summary_path)), {}) if retry_summary_path.exists() else {}
    trace_summary_path = DATA / "edgeiq_sp_join_trace_summary_v1.csv"
    trace_rows = list(read_csv(trace_summary_path)) if trace_summary_path.exists() else []

    source_missing = sum(int(row.get("rows", "0") or 0) for row in trace_rows if row.get("failure_reason") == "SOURCE_SP_MISSING")
    output_missing = sum(int(row.get("rows", "0") or 0) for row in trace_rows if row.get("failure_reason") == "OUTPUT_JOIN_MISSING")
    quality = {
        **summary,
        "resulted_races": len(resulted_races),
        "sp_race_coverage_pct": coverage_pct(len(sp_races), len(resulted_races)),
        "sectional_race_coverage_pct": coverage_pct(len(resulted_sectionals_races), len(resulted_races)),
        "sectionals_retry_queue_races": retry_summary.get("retry_queue_races", ""),
        "upstream_source_sp_missing_trace_rows": source_missing,
        "downstream_output_join_missing_trace_rows": output_missing,
        "built_at": datetime.now().replace(microsecond=0).isoformat(),
    }
    write_csv(QUALITY_OUT, [quality], list(quality.keys()))


def main() -> None:
    rows = [run_script(name) for name in PIPELINE]
    write_csv(
        ORCH_OUT,
        rows,
        ["step", "script", "status", "returncode", "started_at", "finished_at", "output_tail"],
    )
    write_quality_summary()
    print(f"Wrote {ORCH_OUT} ({len(rows)} steps)")
    print(f"Wrote {QUALITY_OUT}")

    failed = [row for row in rows if row["status"] == "FAILED"]
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
