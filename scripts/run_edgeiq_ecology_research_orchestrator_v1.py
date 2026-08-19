from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from edgeiq_memory_safe_io import count_csv_rows_streaming, safe_read_csv, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SCRIPTS = ROOT / "scripts"

OUT_RUN_LOG = DATA / "edgeiq_ecology_orchestrator_run_log_v1.csv"
OUT_HEALTH = DATA / "edgeiq_ecology_orchestrator_health_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_ecology_orchestrator_summary_v1.csv"

ENGINE_VERSION = "EDGEIQ_ECOLOGY_RESEARCH_ORCHESTRATOR_V1"
BOUNDARY = "OFFLINE_RESEARCH_ONLY"

PIPELINE = [
    {
        "order": 1,
        "script": "build_edgeiq_qld_explicit_position_candidate_parser_v1.py",
        "outputs": [
            "edgeiq_qld_explicit_position_candidate_parser_summary_v1.csv",
            "edgeiq_qld_position_schema_patterns_v1.csv",
        ],
    },
    {
        "order": 2,
        "script": "build_edgeiq_qld_telemetry_ontology_inspector_v1.py",
        "outputs": [
            "edgeiq_qld_telemetry_ontology_summary_v1.csv",
            "edgeiq_qld_telemetry_ontology_fragments_v1.csv",
        ],
    },
    {
        "order": 3,
        "script": "build_edgeiq_qld_race_state_transition_engine_v1.py",
        "outputs": [
            "edgeiq_qld_race_state_transition_summary_v1.csv",
            "edgeiq_qld_race_state_transition_profiles_v1.csv",
        ],
    },
    {
        "order": 4,
        "script": "build_edgeiq_transition_persistence_engine_v1.py",
        "outputs": [
            "edgeiq_transition_persistence_summary_v1.csv",
            "edgeiq_transition_persistence_memory_v1.csv",
        ],
    },
    {
        "order": 5,
        "script": "build_edgeiq_transition_ecology_drift_engine_v1.py",
        "outputs": [
            "edgeiq_transition_ecology_drift_summary_v1.csv",
            "edgeiq_transition_ecology_drift_v1.csv",
        ],
    },
    {
        "order": 6,
        "script": "build_edgeiq_ecology_memory_engine_v1.py",
        "outputs": [
            "edgeiq_ecology_memory_summary_v1.csv",
            "edgeiq_ecology_longitudinal_memory_v1.csv",
        ],
    },
    {
        "order": 7,
        "script": "build_edgeiq_ecology_temporal_evolution_v1.py",
        "outputs": [
            "edgeiq_ecology_evolution_summary_v1.csv",
            "edgeiq_ecology_temporal_evolution_v1.csv",
        ],
    },
    {
        "order": 8,
        "script": "build_edgeiq_ecology_evidence_accumulation_v1.py",
        "outputs": [
            "edgeiq_ecology_evidence_summary_v1.csv",
            "edgeiq_ecology_evidence_accumulation_v1.csv",
        ],
    },
    {
        "order": 9,
        "script": "build_edgeiq_ecology_governance_gate_v1.py",
        "outputs": [
            "edgeiq_ecology_governance_summary_v1.csv",
            "edgeiq_ecology_governance_gate_v1.csv",
        ],
    },
    {
        "order": 10,
        "script": "build_edgeiq_ecology_research_ledger_v1.py",
        "outputs": [
            "edgeiq_ecology_research_ledger_summary_v1.csv",
            "edgeiq_ecology_research_ledger_v1.csv",
        ],
    },
    {
        "order": 11,
        "script": "build_edgeiq_research_command_feed_v1.py",
        "outputs": [
            "edgeiq_research_command_summary_v1.csv",
            "edgeiq_research_command_feed_v1.csv",
        ],
    },
    {
        "order": 12,
        "script": "run_edgeiq_ecology_master_memory_orchestrator_v2.py",
        "outputs": [
            "edgeiq_ecology_master_memory_orchestrator_summary_v2.csv",
            "edgeiq_ecology_master_memory_orchestrator_health_v2.csv",
            "edgeiq_ecology_temporal_drift_summary_v1.csv",
            "edgeiq_ecology_memory_decay_summary_v1.csv",
            "edgeiq_ecology_memory_pressure_summary_v1.csv",
            "edgeiq_ecology_memory_confidence_summary_v1.csv",
            "edgeiq_ecology_memory_maturity_summary_v1.csv",
            "edgeiq_ecology_memory_resilience_summary_v1.csv",
            "edgeiq_ecology_memory_stress_summary_v1.csv",
            "edgeiq_ecology_memory_recovery_summary_v1.csv",
        ],
    },
]

REQUIRED_OUTPUTS = [
    "edgeiq_qld_explicit_position_candidate_parser_summary_v1.csv",
    "edgeiq_qld_telemetry_ontology_summary_v1.csv",
    "edgeiq_qld_race_state_transition_summary_v1.csv",
    "edgeiq_transition_persistence_summary_v1.csv",
    "edgeiq_transition_ecology_drift_summary_v1.csv",
    "edgeiq_ecology_memory_summary_v1.csv",
    "edgeiq_ecology_evolution_summary_v1.csv",
    "edgeiq_ecology_evidence_summary_v1.csv",
    "edgeiq_ecology_governance_summary_v1.csv",
    "edgeiq_ecology_research_ledger_summary_v1.csv",
    "edgeiq_research_command_summary_v1.csv",
    "edgeiq_ecology_master_memory_orchestrator_summary_v2.csv",
    "edgeiq_ecology_master_memory_orchestrator_health_v2.csv",
    "edgeiq_ecology_temporal_drift_summary_v1.csv",
    "edgeiq_ecology_memory_decay_summary_v1.csv",
    "edgeiq_ecology_memory_pressure_summary_v1.csv",
    "edgeiq_ecology_memory_confidence_summary_v1.csv",
    "edgeiq_ecology_memory_maturity_summary_v1.csv",
    "edgeiq_ecology_memory_resilience_summary_v1.csv",
    "edgeiq_ecology_memory_stress_summary_v1.csv",
    "edgeiq_ecology_memory_recovery_summary_v1.csv",
    "edgeiq_ecology_research_ledger_v1.csv",
    "edgeiq_research_command_feed_v1.csv",
]

RUN_LOG_FIELDS = [
    "step_order",
    "script_name",
    "status",
    "returncode",
    "runtime_seconds",
    "rows_generated",
    "outputs_checked",
    "missing_outputs",
    "stdout_tail",
    "stderr_tail",
    "timestamp_utc",
    "research_boundary",
    "live_modelling_yes",
    "live_execution_yes",
    "engine_version",
]

HEALTH_FIELDS = [
    "check_name",
    "status",
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


def tail_text(value: str, limit: int = 700) -> str:
    return value.replace("\r", "").strip()[-limit:]


def metric_map(path: Path) -> dict[str, str]:
    return {clean(row.get("metric")): clean(row.get("value")) for row in safe_read_csv(path) if clean(row.get("metric"))}


def is_zero_flag(value: str) -> bool:
    return clean(value).upper() in {"0", "NO", "FALSE", ""}


def rows_for_outputs(output_names: list[str]) -> int:
    return sum(count_csv_rows_streaming(DATA / output) for output in output_names)


def run_step(step: dict[str, object]) -> dict[str, str]:
    script_name = clean(step["script"])
    output_names = [clean(item) for item in step["outputs"]]  # type: ignore[index]
    started = datetime.now(timezone.utc)
    script_path = SCRIPTS / script_name
    if not script_path.exists():
        return {
            "step_order": str(step["order"]),
            "script_name": script_name,
            "status": "FAIL",
            "returncode": "missing_script",
            "runtime_seconds": "0.00",
            "rows_generated": "0",
            "outputs_checked": "|".join(output_names),
            "missing_outputs": "|".join(output_names),
            "stdout_tail": "",
            "stderr_tail": "Script file missing.",
            "timestamp_utc": utc_now(),
            "research_boundary": BOUNDARY,
            "live_modelling_yes": "0",
            "live_execution_yes": "0",
            "engine_version": ENGINE_VERSION,
        }

    completed = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=360,
    )
    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    missing = [name for name in output_names if not (DATA / name).exists()]
    status = "PASS" if completed.returncode == 0 and not missing else "FAIL"
    return {
        "step_order": str(step["order"]),
        "script_name": script_name,
        "status": status,
        "returncode": str(completed.returncode),
        "runtime_seconds": f"{elapsed:.2f}",
        "rows_generated": str(rows_for_outputs(output_names)),
        "outputs_checked": "|".join(output_names),
        "missing_outputs": "|".join(missing),
        "stdout_tail": tail_text(completed.stdout),
        "stderr_tail": tail_text(completed.stderr),
        "timestamp_utc": utc_now(),
        "research_boundary": BOUNDARY,
        "live_modelling_yes": "0",
        "live_execution_yes": "0",
        "engine_version": ENGINE_VERSION,
    }


def build_health(run_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    timestamp = utc_now()
    health_rows: list[dict[str, str]] = []

    failed = [row for row in run_rows if row["status"] != "PASS"]
    health_rows.append(
        {
            "check_name": "script_execution",
            "status": "FAIL" if failed else "PASS",
            "details": f"{len(failed)} failed scripts",
            "timestamp_utc": timestamp,
            "research_boundary": BOUNDARY,
            "live_modelling_yes": "0",
            "live_execution_yes": "0",
            "engine_version": ENGINE_VERSION,
        }
    )

    for name in REQUIRED_OUTPUTS:
        path = DATA / name
        health_rows.append(
            {
                "check_name": f"output::{name}",
                "status": "PASS" if path.exists() and count_csv_rows_streaming(path) > 0 else "FAIL",
                "details": f"rows={count_csv_rows_streaming(path)}",
                "timestamp_utc": timestamp,
                "research_boundary": BOUNDARY,
                "live_modelling_yes": "0",
                "live_execution_yes": "0",
                "engine_version": ENGINE_VERSION,
            }
        )

    for name in [item for item in REQUIRED_OUTPUTS if item.endswith("_summary_v1.csv") or item.endswith("_summary_v2.csv")]:
        metrics = metric_map(DATA / name)
        offline = clean(metrics.get("offline_research_only")) or clean(metrics.get("research_boundary"))
        live_model = clean(metrics.get("live_modelling_yes"))
        live_exec = clean(metrics.get("live_execution_yes"))
        offline_ok = offline in {"YES", BOUNDARY} or not offline
        live_ok = is_zero_flag(live_model) and is_zero_flag(live_exec)
        health_rows.append(
            {
                "check_name": f"boundary::{name}",
                "status": "PASS" if offline_ok and live_ok else "FAIL",
                "details": f"offline={offline or 'not_declared'};live_model={live_model or '0'};live_execution={live_exec or '0'}",
                "timestamp_utc": timestamp,
                "research_boundary": BOUNDARY,
                "live_modelling_yes": "0",
                "live_execution_yes": "0",
                "engine_version": ENGINE_VERSION,
            }
        )

    return health_rows


def health_status(health_rows: list[dict[str, str]], run_rows: list[dict[str, str]]) -> str:
    failed_checks = sum(1 for row in health_rows if row["status"] != "PASS")
    failed_scripts = sum(1 for row in run_rows if row["status"] != "PASS")
    if failed_scripts or failed_checks >= 3:
        return "FAILED_RESEARCH_STACK"
    if failed_checks:
        return "DEGRADED_RESEARCH_STACK"
    return "HEALTHY_RESEARCH_STACK"


def build_orchestrator() -> None:
    run_rows = [run_step(step) for step in PIPELINE]
    health_rows = build_health(run_rows)
    status = health_status(health_rows, run_rows)
    total_runtime = sum(float(row["runtime_seconds"]) for row in run_rows)
    failed_scripts = sum(1 for row in run_rows if row["status"] != "PASS")
    failed_checks = sum(1 for row in health_rows if row["status"] != "PASS")
    ledger_rows = count_csv_rows_streaming(DATA / "edgeiq_ecology_research_ledger_v1.csv")
    command_rows = count_csv_rows_streaming(DATA / "edgeiq_research_command_feed_v1.csv")
    master_memory = metric_map(DATA / "edgeiq_ecology_master_memory_orchestrator_summary_v2.csv")

    summary = [
        {"metric": "health_status", "value": status},
        {"metric": "steps_run", "value": str(len(run_rows))},
        {"metric": "steps_passed", "value": str(len(run_rows) - failed_scripts)},
        {"metric": "steps_failed", "value": str(failed_scripts)},
        {"metric": "health_checks", "value": str(len(health_rows))},
        {"metric": "health_checks_failed", "value": str(failed_checks)},
        {"metric": "total_runtime_seconds", "value": f"{total_runtime:.2f}"},
        {"metric": "ledger_rows", "value": str(ledger_rows)},
        {"metric": "command_feed_rows", "value": str(command_rows)},
        {"metric": "master_memory_stack_health", "value": clean(master_memory.get("overall_stack_health", "UNKNOWN"))},
        {"metric": "master_memory_steps_passed", "value": clean(master_memory.get("pipeline_passed", "0"))},
        {"metric": "master_memory_steps_failed", "value": clean(master_memory.get("pipeline_failed", "0"))},
        {"metric": "research_ledger_exists", "value": "YES" if ledger_rows else "NO"},
        {"metric": "command_feed_exists", "value": "YES" if command_rows else "NO"},
        {"metric": "offline_research_only", "value": "YES"},
        {"metric": "research_boundary", "value": BOUNDARY},
        {"metric": "live_modelling_yes", "value": "0"},
        {"metric": "live_execution_yes", "value": "0"},
        {"metric": "engine_version", "value": ENGINE_VERSION},
    ]

    write_csv_atomic(OUT_RUN_LOG, run_rows, RUN_LOG_FIELDS)
    write_csv_atomic(OUT_HEALTH, health_rows, HEALTH_FIELDS)
    write_csv_atomic(OUT_SUMMARY, summary, SUMMARY_FIELDS)

    print(f"Ecology orchestrator health: {status}")
    print(f"Steps run: {len(run_rows)}")
    print(f"Failed scripts: {failed_scripts}")
    print("Live modelling: 0")
    print("Live execution: 0")


if __name__ == "__main__":
    build_orchestrator()
