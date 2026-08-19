from __future__ import annotations

import csv
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"

OUT_RUN_LOG = PUBLIC / "edgeiq_ecology_master_memory_orchestrator_v2.csv"
OUT_SUMMARY = PUBLIC / "edgeiq_ecology_master_memory_orchestrator_summary_v2.csv"
OUT_HEALTH = PUBLIC / "edgeiq_ecology_master_memory_orchestrator_health_v2.csv"

ENGINE_VERSION = "EDGEIQ_ECOLOGY_MASTER_MEMORY_ORCHESTRATOR_V2"

PIPELINE = [
    "build_edgeiq_ecology_snapshot_archive_v1.py",
    "build_edgeiq_ecology_temporal_drift_history_v1.py",
    "build_edgeiq_ecology_memory_decay_v1.py",
    "build_edgeiq_ecology_memory_pressure_v1.py",
    "build_edgeiq_ecology_memory_confidence_v1.py",
    "build_edgeiq_ecology_memory_maturity_v1.py",
    "build_edgeiq_ecology_memory_resilience_v1.py",
    "build_edgeiq_ecology_memory_stress_test_v1.py",
    "build_edgeiq_ecology_memory_recovery_v1.py",
]

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def write_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()

        for row in rows:
            writer.writerow(row)

def run_script(script_name):
    script_path = ROOT / "scripts" / script_name

    start = time.time()

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            check=True,
        )

        duration = round(time.time() - start, 2)

        return {
            "script_name": script_name,
            "status": "PASS",
            "duration_seconds": duration,
            "stdout_preview": result.stdout[-500:],
            "stderr_preview": result.stderr[-500:],
        }

    except subprocess.CalledProcessError as exc:
        duration = round(time.time() - start, 2)

        return {
            "script_name": script_name,
            "status": "FAIL",
            "duration_seconds": duration,
            "stdout_preview": exc.stdout[-500:],
            "stderr_preview": exc.stderr[-500:],
        }

def main():
    print("=" * 88)
    print("EDGEIQ ECOLOGY MASTER MEMORY ORCHESTRATOR V2")
    print("=" * 88)

    run_rows = []

    for script in PIPELINE:
        print(f"RUNNING: {script}")

        result = run_script(script)

        run_rows.append({
            "script_name": result["script_name"],
            "status": result["status"],
            "duration_seconds": result["duration_seconds"],
            "stdout_preview": result["stdout_preview"],
            "stderr_preview": result["stderr_preview"],
            "research_boundary": "OFFLINE_RESEARCH_ONLY",
            "live_modelling_yes": 0,
            "live_execution_yes": 0,
            "engine_version": ENGINE_VERSION,
            "timestamp_utc": now_iso(),
        })

        print(
            f"{result['script_name']} -> "
            f"{result['status']} "
            f"({result['duration_seconds']}s)"
        )

    total = len(run_rows)
    passed = sum(1 for r in run_rows if r["status"] == "PASS")
    failed = sum(1 for r in run_rows if r["status"] == "FAIL")

    if failed == 0:
        health = "HEALTHY_LONGITUDINAL_MEMORY_STACK"
    else:
        health = "STACK_FAILURE_PRESENT"

    summary_rows = [
        {"metric": "pipeline_steps", "value": total},
        {"metric": "pipeline_passed", "value": passed},
        {"metric": "pipeline_failed", "value": failed},
        {"metric": "overall_stack_health", "value": health},
        {"metric": "research_boundary", "value": "OFFLINE_RESEARCH_ONLY"},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
    ]

    health_rows = [{
        "overall_stack_health": health,
        "pipeline_steps": total,
        "pipeline_passed": passed,
        "pipeline_failed": failed,
        "research_boundary": "OFFLINE_RESEARCH_ONLY",
        "live_modelling_yes": 0,
        "live_execution_yes": 0,
        "engine_version": ENGINE_VERSION,
        "timestamp_utc": now_iso(),
    }]

    write_csv(
        OUT_RUN_LOG,
        run_rows,
        [
            "script_name",
            "status",
            "duration_seconds",
            "stdout_preview",
            "stderr_preview",
            "research_boundary",
            "live_modelling_yes",
            "live_execution_yes",
            "engine_version",
            "timestamp_utc",
        ],
    )

    write_csv(
        OUT_SUMMARY,
        summary_rows,
        ["metric", "value"],
    )

    write_csv(
        OUT_HEALTH,
        health_rows,
        [
            "overall_stack_health",
            "pipeline_steps",
            "pipeline_passed",
            "pipeline_failed",
            "research_boundary",
            "live_modelling_yes",
            "live_execution_yes",
            "engine_version",
            "timestamp_utc",
        ],
    )

    print("=" * 88)
    print("MASTER MEMORY STACK")
    print("=" * 88)

    for row in summary_rows:
        print(f"{row['metric']}: {row['value']}")

if __name__ == "__main__":
    main()
