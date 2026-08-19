from __future__ import annotations

import csv
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"

REPORT = PUBLIC / "edgeiq_ecology_daily_report.md"

def read_metric(file_name: str, key: str) -> str:
    path = PUBLIC / file_name
    if not path.exists():
        return "MISSING"

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("metric") == key:
                return row.get("value", "")

    return "N/A"

def run_stack() -> None:
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_edgeiq_ecology_master_memory_orchestrator_v2.py"),
        ],
        cwd=str(ROOT),
        check=True,
    )

def build_report() -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""# EDGEiQ Ecology Daily Report

Generated: {now}

## Stack Health

| Metric | Value |
|---|---|
| Master memory stack | {read_metric('edgeiq_ecology_master_memory_orchestrator_summary_v2.csv', 'overall_stack_health')} |
| Pipeline passed | {read_metric('edgeiq_ecology_master_memory_orchestrator_summary_v2.csv', 'pipeline_passed')} |
| Pipeline failed | {read_metric('edgeiq_ecology_master_memory_orchestrator_summary_v2.csv', 'pipeline_failed')} |

## Longitudinal Memory

| Metric | Value |
|---|---|
| Temporal health | {read_metric('edgeiq_ecology_temporal_drift_summary_v1.csv', 'overall_temporal_memory_health')} |
| Snapshot count | {read_metric('edgeiq_ecology_temporal_drift_summary_v1.csv', 'snapshot_count')} |
| Structures tracked | {read_metric('edgeiq_ecology_temporal_drift_summary_v1.csv', 'structures_tracked')} |
| Drift events | {read_metric('edgeiq_ecology_temporal_drift_summary_v1.csv', 'total_drift_events')} |
| Mutation events | {read_metric('edgeiq_ecology_temporal_drift_summary_v1.csv', 'total_mutation_events')} |
| Boundary violations | {read_metric('edgeiq_ecology_temporal_drift_summary_v1.csv', 'total_boundary_violations')} |

## Memory Quality

| Layer | Current State |
|---|---|
| Decay | {read_metric('edgeiq_ecology_memory_decay_summary_v1.csv', 'overall_decay_health')} |
| Pressure | {read_metric('edgeiq_ecology_memory_pressure_summary_v1.csv', 'overall_pressure_health')} |
| Confidence | {read_metric('edgeiq_ecology_memory_confidence_summary_v1.csv', 'overall_confidence_health')} |
| Maturity | {read_metric('edgeiq_ecology_memory_maturity_summary_v1.csv', 'overall_maturity_health')} |
| Resilience | {read_metric('edgeiq_ecology_memory_resilience_summary_v1.csv', 'overall_resilience_health')} |
| Stress | {read_metric('edgeiq_ecology_memory_stress_summary_v1.csv', 'overall_stress_health')} |
| Recovery | {read_metric('edgeiq_ecology_memory_recovery_summary_v1.csv', 'overall_recovery_health')} |

## Boundary Lock

| Metric | Value |
|---|---|
| Research boundary | {read_metric('edgeiq_ecology_memory_recovery_summary_v1.csv', 'research_boundary')} |
| Live modelling | {read_metric('edgeiq_ecology_memory_recovery_summary_v1.csv', 'live_modelling_yes')} |
| Live execution | {read_metric('edgeiq_ecology_memory_recovery_summary_v1.csv', 'live_execution_yes')} |

## Simple Interpretation

Good signs:
- Snapshot count is increasing.
- Pipeline remains healthy.
- Boundary violations remain 0.
- Decay remains low.
- Pressure does not keep rising.

Warning signs:
- Pipeline failures.
- Confidence stays low after many snapshots.
- Pressure rises.
- Stress failures worsen.
- Recovery remains low after many snapshots.
- Any live modelling or live execution flag becomes non-zero.

Current read:
This remains OFFLINE_RESEARCH_ONLY. The system is collecting longitudinal evidence, not producing betting outputs.
"""

def main() -> None:
    run_stack()
    report = build_report()
    REPORT.write_text(report, encoding="utf-8")
    print(report)
    print("")
    print(f"SAVED REPORT: {REPORT}")

if __name__ == "__main__":
    main()
