from __future__ import annotations

import csv
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from edgeiq_memory_safe_io import count_csv_rows_streaming, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SCRIPTS = ROOT / "scripts"

OUT = DATA / "edgeiq_telemetry_refresh_orchestrator_v1.csv"
SUMMARY = DATA / "edgeiq_telemetry_refresh_summary_v1.csv"

ORCHESTRATOR_FIELDS = [
    "step_order",
    "script_name",
    "status",
    "runtime_seconds",
    "rows_generated",
    "errors_detected",
    "warnings_detected",
    "refresh_timestamp",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

PIPELINE = [
    {
        "script": "build_edgeiq_ra_historical_results_harvester_v1.py",
        "primary_output": "edgeiq_ra_historical_results_harvest_v1.csv",
        "summary_output": "edgeiq_ra_historical_results_harvest_summary_v1.csv",
        "timeout": 1800,
        "notes": "Official historical result refresh. Offline exact-race harvesting only.",
    },
    {
        "script": "build_edgeiq_canonical_results_truth_v1.py",
        "primary_output": "edgeiq_canonical_results_truth_v1.csv",
        "summary_output": "edgeiq_canonical_results_truth_summary_v1.csv",
        "timeout": 900,
        "notes": "Canonical settled result truth refresh.",
    },
    {
        "script": "build_edgeiq_temporal_physics_validation_v1.py",
        "primary_output": "edgeiq_temporal_physics_validation_v1.csv",
        "summary_output": "edgeiq_temporal_physics_validation_summary_v1.csv",
        "timeout": 900,
        "notes": "Temporal physics outcome validation refresh.",
    },
    {
        "script": "build_edgeiq_raw_sectional_payload_discovery_v1.py",
        "primary_output": "edgeiq_raw_sectional_payload_discovery_v1.csv",
        "summary_output": "edgeiq_raw_sectional_payload_discovery_summary_v1.csv",
        "timeout": 900,
        "notes": "Cached/local raw sectional payload discovery refresh.",
    },
    {
        "script": "build_edgeiq_raw_sectional_payload_schema_parser_v1.py",
        "primary_output": "edgeiq_raw_sectional_payload_schema_parser_v1.csv",
        "summary_output": "edgeiq_raw_sectional_payload_schema_summary_v1.csv",
        "timeout": 900,
        "notes": "Cached/local split ladder schema parsing refresh.",
    },
    {
        "script": "build_edgeiq_enhanced_temporal_phase_confidence_v2.py",
        "primary_output": "edgeiq_enhanced_temporal_phase_confidence_v2.csv",
        "summary_output": "edgeiq_enhanced_temporal_phase_summary_v2.csv",
        "timeout": 900,
        "notes": "Enhanced phase confidence refresh.",
    },
    {
        "script": "build_edgeiq_timing_lineage_validation_v1.py",
        "primary_output": "edgeiq_timing_lineage_validation_v1.csv",
        "summary_output": "edgeiq_timing_lineage_summary_v1.csv",
        "timeout": 900,
        "notes": "Timing provenance and lineage validation refresh.",
    },
    {
        "script": "build_edgeiq_telemetry_health_monitor_v1.py",
        "primary_output": "edgeiq_telemetry_health_monitor_v1.csv",
        "summary_output": "edgeiq_telemetry_health_summary_v1.csv",
        "timeout": 900,
        "notes": "Telemetry health and drift watch refresh.",
    },
    {
        "script": "build_edgeiq_longitudinal_telemetry_accumulation_v1.py",
        "primary_output": "edgeiq_longitudinal_telemetry_accumulation_v1.csv",
        "summary_output": "edgeiq_longitudinal_telemetry_summary_v1.csv",
        "timeout": 900,
        "notes": "Longitudinal telemetry accumulation refresh.",
    },
    {
        "script": "build_edgeiq_shadow_research_loop_v1.py",
        "primary_output": "edgeiq_shadow_research_loop_v1.csv",
        "summary_output": "edgeiq_shadow_research_loop_summary_v1.csv",
        "timeout": 900,
        "notes": "Offline shadow environment research state refresh.",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean(value: object) -> str:
    return str(value or "").strip()


def read_summary(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            rows = csv.DictReader(handle)
            return {clean(row.get("metric")): clean(row.get("value")) for row in rows if clean(row.get("metric"))}
    except Exception:
        return {}


def tail_text(value: str, limit: int = 900) -> str:
    text = clean(value).replace("\r", "\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    joined = " | ".join(lines[-8:])
    return joined[-limit:]


def warning_count(stdout: str, stderr: str, summary: dict[str, str]) -> int:
    text = f"{stdout}\n{stderr}".lower()
    count = 0
    for token in ("warn", "failed races", "failure_reason", "drift", "degraded", "unstable", "missing_input"):
        if token in text:
            count += text.count(token)
    for key, value in summary.items():
        key_l = key.lower()
        if (
            key_l.startswith("missing_input::")
            or key_l in {"failed_races", "steps_failed", "degraded_health_rows", "unstable_health_rows", "telemetry_decay_rows", "environment_drift_rows"}
            or "failure" in key_l
            or "warning" in key_l
            or "drift" in key_l
            or "degrad" in key_l
        ):
            try:
                if float(value or 0) > 0:
                    count += 1
            except ValueError:
                if value:
                    count += 1
    return count


def run_step(step_order: int, config: dict[str, object]) -> dict[str, object]:
    script_name = clean(config["script"])
    script_path = SCRIPTS / script_name
    output_path = DATA / clean(config["primary_output"])
    summary_path = DATA / clean(config["summary_output"])
    started = time.perf_counter()
    timestamp = utc_now()
    if not script_path.exists():
        return {
            "step_order": step_order,
            "script_name": script_name,
            "status": "FAILED_MISSING_SCRIPT",
            "runtime_seconds": "0.00",
            "rows_generated": 0,
            "errors_detected": 1,
            "warnings_detected": 0,
            "refresh_timestamp": timestamp,
            "notes": f"Missing script: {script_path}",
        }

    env = os.environ.copy()
    env["EDGEIQ_TELEMETRY_REFRESH_ORCHESTRATOR"] = "1"
    env.setdefault("EDGEIQ_ENABLE_RESEARCH_PIPELINE", "0")
    command = [sys.executable, str(script_path)]
    try:
        result = subprocess.run(
            command,
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=int(config.get("timeout", 900)),
        )
        runtime = time.perf_counter() - started
        rows_generated = count_csv_rows_streaming(output_path)
        summary = read_summary(summary_path)
        errors = 0 if result.returncode == 0 else 1
        warnings = warning_count(result.stdout or "", result.stderr or "", summary)
        status = "PASSED" if result.returncode == 0 else "FAILED"
        notes = clean(config.get("notes"))
        if result.returncode != 0:
            notes = f"{notes} Return code {result.returncode}. stderr tail: {tail_text(result.stderr)}"
        elif warnings:
            notes = f"{notes} Completed with {warnings} warning signals. stdout tail: {tail_text(result.stdout)}"
        else:
            notes = f"{notes} Completed cleanly. stdout tail: {tail_text(result.stdout)}"
        return {
            "step_order": step_order,
            "script_name": script_name,
            "status": status,
            "runtime_seconds": f"{runtime:.2f}",
            "rows_generated": rows_generated,
            "errors_detected": errors,
            "warnings_detected": warnings,
            "refresh_timestamp": timestamp,
            "notes": notes,
        }
    except subprocess.TimeoutExpired as exc:
        runtime = time.perf_counter() - started
        return {
            "step_order": step_order,
            "script_name": script_name,
            "status": "FAILED_TIMEOUT",
            "runtime_seconds": f"{runtime:.2f}",
            "rows_generated": count_csv_rows_streaming(output_path),
            "errors_detected": 1,
            "warnings_detected": 1,
            "refresh_timestamp": timestamp,
            "notes": f"Step exceeded timeout. stdout tail: {tail_text(exc.stdout or '')} stderr tail: {tail_text(exc.stderr or '')}",
        }
    except Exception as exc:
        runtime = time.perf_counter() - started
        return {
            "step_order": step_order,
            "script_name": script_name,
            "status": "FAILED_EXCEPTION",
            "runtime_seconds": f"{runtime:.2f}",
            "rows_generated": count_csv_rows_streaming(output_path),
            "errors_detected": 1,
            "warnings_detected": 1,
            "refresh_timestamp": timestamp,
            "notes": f"Unhandled orchestrator exception: {type(exc).__name__}: {exc}",
        }


def build_summary(step_rows: list[dict[str, object]], total_runtime: float) -> list[dict[str, object]]:
    row_count_by_script = {clean(row.get("script_name")): int(row.get("rows_generated") or 0) for row in step_rows}
    steps_failed = sum(1 for row in step_rows if clean(row.get("status")) not in {"PASSED"})
    return [
        {"metric": "steps_run", "value": len(step_rows)},
        {"metric": "steps_passed", "value": len(step_rows) - steps_failed},
        {"metric": "steps_failed", "value": steps_failed},
        {"metric": "total_runtime_seconds", "value": f"{total_runtime:.2f}"},
        {"metric": "telemetry_rows_refreshed", "value": row_count_by_script.get("build_edgeiq_telemetry_health_monitor_v1.py", 0)},
        {"metric": "shadow_rows_refreshed", "value": row_count_by_script.get("build_edgeiq_shadow_research_loop_v1.py", 0)},
        {"metric": "lineage_rows_refreshed", "value": row_count_by_script.get("build_edgeiq_timing_lineage_validation_v1.py", 0)},
        {"metric": "phase_confidence_rows_refreshed", "value": row_count_by_script.get("build_edgeiq_enhanced_temporal_phase_confidence_v2.py", 0)},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
        {"metric": "offline_research_only", "value": "YES"},
        {"metric": "not_wired_to_render_worker", "value": "YES"},
    ]


def main() -> None:
    started = time.perf_counter()
    step_rows = []
    print("=" * 88)
    print("EDGEIQ TELEMETRY REFRESH ORCHESTRATOR V1")
    print("=" * 88)
    print("Offline telemetry research refresh only. No live modelling or execution.")
    for index, config in enumerate(PIPELINE, start=1):
        print(f"[{index}/{len(PIPELINE)}] running {config['script']}")
        row = run_step(index, config)
        step_rows.append(row)
        print(f"    {row['status']} in {row['runtime_seconds']}s rows={row['rows_generated']} warnings={row['warnings_detected']}")

    total_runtime = time.perf_counter() - started
    summary_rows = build_summary(step_rows, total_runtime)
    write_csv_atomic(OUT, step_rows, ORCHESTRATOR_FIELDS)
    write_csv_atomic(SUMMARY, summary_rows, SUMMARY_FIELDS)
    print("-" * 88)
    for row in summary_rows:
        print(f"{row['metric']}: {row['value']}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")


if __name__ == "__main__":
    main()
