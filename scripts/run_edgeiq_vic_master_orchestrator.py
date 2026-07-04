from __future__ import annotations

import csv
import gc
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from edgeiq_memory_safe_io import collect_garbage, current_memory_mb, log_memory_usage, write_csv_atomic


REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = REPO_ROOT.parents[1] if (REPO_ROOT.parents[1] / "dashboard" / "racing-dashboard").exists() else REPO_ROOT
DATA_DIR = REPO_ROOT / "public" / "data"
STATUS_PATH = DATA_DIR / "edgeiq_master_orchestrator_status.csv"
STEP_STATUS_PATH = DATA_DIR / "edgeiq_orchestrator_step_status.csv"
LOG_PATH = DATA_DIR / "edgeiq_master_orchestrator_log.txt"
TELEMETRY_PATH = DATA_DIR / "edgeiq_master_orchestrator_telemetry.csv"

POLL_SECONDS = int(os.getenv("EDGEIQ_MASTER_POLL_SECONDS", "60"))
STEP_TIMEOUT_SECONDS = int(os.getenv("EDGEIQ_STEP_TIMEOUT_SECONDS", "240"))
RUN_ONCE = os.getenv("EDGEIQ_MASTER_RUN_ONCE", "").strip().upper() in {"1", "TRUE", "YES", "Y"}
RESEARCH_ENABLED = os.getenv("EDGEIQ_ENABLE_RESEARCH_PIPELINE", "").strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Step:
    order: int
    name: str
    script: str
    output: str
    critical: bool = False
    stale_after_seconds: int = 180
    research: bool = False

    @property
    def path(self) -> Path:
        return REPO_ROOT / "scripts" / self.script

    @property
    def output_path(self) -> Path:
        return DATA_DIR / self.output


STEPS: list[Step] = [
    Step(1, "Three day VIC meeting universe", "build_edgeiq_vic_three_day_meeting_universe.py", "edgeiq_vic_three_day_meeting_universe.csv", True, 300),
    Step(2, "Race clock engine", "build_edgeiq_race_clock_engine.py", "edgeiq_race_clock_engine.csv", True, 240),
    Step(3, "Active race selector", "build_edgeiq_active_race_selector.py", "edgeiq_active_race_selector.csv", True, 240),
    Step(4, "Scratchings enrichment", "enrich_vic_live_feed_scratchings.py", "edgeiq_vic_scratchings_diagnostics.csv", True, 240),
    Step(5, "Real silk lookup", "build_real_silk_lookup.py", "edgeiq_real_silk_lookup.csv", False, 360),
    Step(6, "Silk enrichment", "enrich_vic_live_feed_silks.py", "edgeiq_silk_enrichment_diagnostics.csv", False, 240),
    Step(7, "Race shape engine v2", "build_edgeiq_race_shape_engine_v2.py", "edgeiq_race_shape_engine_v2.csv", False, 360),
    Step(8, "Real speed map positions", "build_edgeiq_real_speed_map_engine.py", "edgeiq_real_speed_map_positions.csv", False, 240),
    Step(9, "Market tape memory", "build_edgeiq_market_tape_memory.py", "edgeiq_market_tape_summary.csv", True, 180),
    Step(10, "Market truth engine v3", "build_edgeiq_market_truth_engine_v3.py", "edgeiq_market_truth_engine_v3.csv", True, 180),
    Step(11, "Execution suppression v2", "build_edgeiq_execution_suppression_engine_v2.py", "edgeiq_execution_suppression_v2.csv", True, 180),
    Step(12, "Execution engine v4", "build_edgeiq_execution_engine_v4.py", "edgeiq_execution_engine_v4.csv", True, 180),
    Step(13, "Results truth loop", "build_edgeiq_results_truth_loop.py", "edgeiq_results_truth_loop.csv", False, 360),
    Step(14, "CLV memory", "build_edgeiq_clv_memory_engine.py", "edgeiq_clv_memory.csv", False, 360),
    Step(15, "Sectional scraper inventory", "build_edgeiq_sectional_scraper_inventory.py", "edgeiq_sectional_scraper_inventory.csv", False, 1800, True),
    Step(16, "Racing.com sectional catalogue", "build_edgeiq_racingcom_sectional_catalogue.py", "edgeiq_racingcom_sectional_catalogue.csv", False, 900, True),
    Step(17, "Sectional schema v2", "build_edgeiq_sectional_schema_v2.py", "edgeiq_sectional_schema_v2.csv", False, 900, True),
    Step(18, "Sectional pipeline audit", "audit_edgeiq_sectional_pipeline.py", "edgeiq_sectional_pipeline_summary.csv", False, 1800, True),
    Step(19, "Sectional validation engine", "build_edgeiq_sectional_validation_engine.py", "edgeiq_sectional_validation_engine.csv", False, 900, True),
    Step(20, "Sectional identity engine v1", "build_edgeiq_sectional_identity_engine_v1.py", "edgeiq_sectional_identity_engine_v1.csv", False, 1800, True),
    Step(21, "Sectional master reconciliation", "build_edgeiq_sectional_master_reconciliation_v1.py", "edgeiq_sectional_master_v1.csv", False, 1800, True),
    Step(22, "Sectional payload reconstruction", "build_edgeiq_sectional_payload_reconstruction_v1.py", "edgeiq_sectional_payload_reconstruction_v1.csv", False, 900, True),
    Step(23, "Sectional physics validation", "build_edgeiq_sectional_physics_validation_v1.py", "edgeiq_sectional_physics_validation_v1.csv", False, 900, True),
    Step(24, "Canonical split schema", "build_edgeiq_canonical_split_schema_v1.py", "edgeiq_canonical_split_schema_v1.csv", False, 900, True),
    Step(25, "Horse alias engine", "build_edgeiq_horse_alias_engine_v1.py", "edgeiq_horse_alias_engine_v1.csv", False, 900, True),
    Step(26, "Track alias engine", "build_edgeiq_track_alias_engine_v1.py", "edgeiq_track_alias_engine_v1.csv", False, 900, True),
    Step(27, "Sectional field composition match", "build_edgeiq_sectional_field_composition_match_v1.py", "edgeiq_sectional_field_composition_match_v1.csv", False, 1200, True),
    Step(28, "Sectional identity engine v2", "build_edgeiq_sectional_identity_engine_v2.py", "edgeiq_sectional_identity_engine_v2.csv", False, 1200, True),
    Step(29, "Runner entity graph", "build_edgeiq_runner_entity_graph_v1.py", "edgeiq_runner_entity_graph_v1.csv", False, 1200, True),
    Step(30, "Runner conflict resolution", "build_edgeiq_runner_conflict_resolution_v1.py", "edgeiq_runner_conflict_resolution_v1.csv", False, 900, True),
    Step(31, "Sectional identity engine v3", "build_edgeiq_sectional_identity_engine_v3.py", "edgeiq_sectional_identity_engine_v3.csv", False, 1200, True),
    Step(32, "Trusted sectional universe", "build_edgeiq_trusted_sectional_universe.py", "edgeiq_trusted_sectional_universe.csv", False, 900, True),
    Step(33, "Sectional health engine", "build_edgeiq_sectional_health_engine.py", "edgeiq_sectional_health_summary.csv", False, 900, True),
    Step(34, "Sectional normalisation v1", "build_edgeiq_sectional_normalisation_v1.py", "edgeiq_sectional_normalisation_v1.csv", False, 900, True),
    Step(35, "Form engine v2", "build_edgeiq_form_engine_v2.py", "edgeiq_form_engine_v2.csv", False, 360, True),
    Step(36, "VIC live fields sync", "build_vic_live_fields_synced.py", "edgeiq_vic_live_fields_synced.csv", True, 240),
    Step(37, "Live terminal feed", "build_edgeiq_live_terminal_feed_v1.py", "edgeiq_live_terminal_feed_v1.csv", True, 180),
    Step(38, "Race state engine", "build_edgeiq_race_state_engine.py", "edgeiq_race_state_engine.csv", False, 180),
    Step(39, "Probability engine v4.1", "build_edgeiq_probability_engine_v4_1.py", "edgeiq_probability_engine_v4_1.csv", False, 360),
    Step(40, "Execution board v3", "build_edgeiq_execution_board_v3.py", "edgeiq_execution_board_v3.csv", True, 360),
    Step(41, "Execution quality v2", "build_edgeiq_execution_quality_engine_v2.py", "edgeiq_execution_quality_v2.csv", False, 360),
    Step(42, "Portfolio risk v1", "build_edgeiq_portfolio_risk_engine_v1.py", "edgeiq_portfolio_risk_v1.csv", False, 360),
    Step(43, "Portfolio throttle v1", "build_edgeiq_portfolio_throttle_engine_v1.py", "edgeiq_portfolio_throttle_v1.csv", False, 360),
    Step(44, "Capital allocation v1", "build_edgeiq_capital_allocation_engine_v1.py", "edgeiq_capital_allocation_v1.csv", False, 360),
    Step(45, "Results auto settlement", "build_edgeiq_results_auto_settlement.py", "edgeiq_results_auto_settlement.csv", False, 360),
    Step(46, "Contextual learning v1", "build_edgeiq_contextual_learning_engine_v1.py", "edgeiq_contextual_learning_engine_v1.csv", False, 360, True),
    Step(47, "Pipeline health monitor", "build_edgeiq_pipeline_health_monitor.py", "edgeiq_pipeline_health.csv", False, 180),
]

STATUS_FIELDS = [
    "timestamp", "cycle_id", "cycle_started_at", "last_heartbeat_at", "current_step", "completed_steps",
    "failed_steps", "cycle_grade", "last_cycle_completed_at", "loop_status", "step_order", "step_name",
    "script", "output", "status", "returncode", "duration_seconds", "started_at", "finished_at",
    "critical", "research_step", "output_age_seconds", "stale_engine", "failure_count", "memory_mb", "message",
]

STEP_STATUS_FIELDS = [
    "timestamp", "cycle_id", "step_order", "step_name", "script", "output", "success", "status",
    "returncode", "duration_seconds", "started_at", "finished_at", "critical", "research_step",
    "output_age_seconds", "stale_engine", "failure_count", "memory_mb", "stdout_tail", "stderr_tail", "message",
]

FAILURE_COUNTS: dict[str, int] = {}
LAST_STEP_ROWS: list[dict[str, object]] = []


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def ensure_outputs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not LOG_PATH.exists():
        LOG_PATH.write_text("", encoding="utf-8")


def tail_file(path: Path, limit: int = 1800) -> str:
    if not path.exists():
        return ""
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - limit))
            return handle.read().decode("utf-8", errors="replace").strip()
    except Exception:
        return ""


def file_age_seconds(path: Path) -> float | None:
    if not path.exists():
        return None
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).astimezone()
    return round((datetime.now(timezone.utc).astimezone() - modified).total_seconds(), 1)


def append_log(message: str) -> None:
    line = f"{now_iso()} | {message}"
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    write_csv_atomic(path, rows, fields)


def cycle_grade(rows: list[dict[str, object]]) -> str:
    critical_failures = sum(1 for row in rows if row.get("critical") == "YES" and row.get("status") not in {"OK", "STALE_WARN", "SKIPPED"})
    failures = sum(1 for row in rows if row.get("status") not in {"OK", "STALE_WARN", "SKIPPED"})
    stale = sum(1 for row in rows if row.get("stale_engine") == "YES" and row.get("status") != "SKIPPED")
    if critical_failures:
        return "RED"
    if failures >= 3 or stale >= 5:
        return "AMBER"
    if failures or stale:
        return "YELLOW"
    return "GREEN"


def status_context(cycle_id: str, cycle_started_at: str, loop_status: str, current_step: str, completed_steps: int, failed_steps: int, grade: str, last_completed: str) -> dict[str, object]:
    return {
        "timestamp": now_iso(),
        "cycle_id": cycle_id,
        "cycle_started_at": cycle_started_at,
        "last_heartbeat_at": now_iso(),
        "current_step": current_step,
        "completed_steps": completed_steps,
        "failed_steps": failed_steps,
        "cycle_grade": grade,
        "last_cycle_completed_at": last_completed,
        "loop_status": loop_status,
    }


def write_status(rows: list[dict[str, object]], context: dict[str, object]) -> None:
    if rows:
        output_rows = [{**context, **row} for row in rows]
    else:
        output_rows = [{
            **context,
            "step_order": "",
            "step_name": "",
            "script": "",
            "output": "",
            "status": context["loop_status"],
            "returncode": "",
            "duration_seconds": "",
            "started_at": context["cycle_started_at"],
            "finished_at": "",
            "critical": "",
            "research_step": "",
            "output_age_seconds": "",
            "stale_engine": "NO",
            "failure_count": "",
            "memory_mb": current_memory_mb(),
            "message": "cycle_initialising",
        }]
    write_csv(STATUS_PATH, output_rows, STATUS_FIELDS)


def write_step_status(rows: list[dict[str, object]]) -> None:
    write_csv(STEP_STATUS_PATH, rows, STEP_STATUS_FIELDS)


def write_telemetry(cycle_id: str, rows: list[dict[str, object]], cycle_seconds: float, grade: str) -> None:
    telemetry = [{
        "timestamp": now_iso(),
        "cycle_id": cycle_id,
        "poll_seconds": POLL_SECONDS,
        "cycle_seconds": round(cycle_seconds, 3),
        "steps": len(rows),
        "ok_steps": sum(1 for row in rows if row.get("status") == "OK"),
        "skipped_steps": sum(1 for row in rows if row.get("status") == "SKIPPED"),
        "failed_steps": sum(1 for row in rows if row.get("status") not in {"OK", "STALE_WARN", "SKIPPED"}),
        "stale_steps": sum(1 for row in rows if row.get("stale_engine") == "YES" and row.get("status") != "SKIPPED"),
        "critical_failures": sum(1 for row in rows if row.get("critical") == "YES" and row.get("status") not in {"OK", "STALE_WARN"}),
        "research_pipeline_enabled": "YES" if RESEARCH_ENABLED else "NO",
        "memory_mb": current_memory_mb(),
        "health_escalation_grade": grade,
        "last_heartbeat_at": now_iso(),
    }]
    write_csv(TELEMETRY_PATH, telemetry, list(telemetry[0].keys()))


def build_step_row(step: Step, cycle_id: str, status: str, returncode: int | str, duration: float | str, started: str, stdout_tail: str, stderr_tail: str, message: str) -> dict[str, object]:
    age = file_age_seconds(step.output_path)
    stale = age is None or age > step.stale_after_seconds
    if status in {"SKIPPED", "MISSING"}:
        stale = False
    row_status = "STALE_WARN" if status == "OK" and stale else status
    return {
        "timestamp": now_iso(),
        "cycle_id": cycle_id,
        "step_order": step.order,
        "step_name": step.name,
        "script": step.script,
        "output": step.output,
        "success": "YES" if row_status in {"OK", "STALE_WARN", "SKIPPED"} else "NO",
        "status": row_status,
        "returncode": returncode,
        "duration_seconds": duration,
        "started_at": started,
        "finished_at": now_iso(),
        "critical": "YES" if step.critical else "NO",
        "research_step": "YES" if step.research else "NO",
        "output_age_seconds": "" if age is None else age,
        "stale_engine": "YES" if stale else "NO",
        "failure_count": FAILURE_COUNTS.get(step.script, 0),
        "memory_mb": current_memory_mb(),
        "stdout_tail": stdout_tail[-1800:],
        "stderr_tail": stderr_tail[-1800:],
        "message": message[:1000],
    }


def skipped_step(step: Step, cycle_id: str, reason: str) -> dict[str, object]:
    started = now_iso()
    append_log(f"SKIP step={step.order} name={step.name} reason={reason}")
    log_memory_usage(f"skip::{step.name}", "OK", reason)
    return build_step_row(step, cycle_id, "SKIPPED", "", 0, started, "", "", reason)


def run_step(step: Step, cycle_id: str) -> dict[str, object]:
    if step.research and not RESEARCH_ENABLED:
        return skipped_step(step, cycle_id, "EDGEIQ_ENABLE_RESEARCH_PIPELINE is OFF")

    started = now_iso()
    start_time = time.perf_counter()
    append_log(f"START step={step.order} name={step.name} script={step.script}")
    log_memory_usage(f"before::{step.name}", "OK", f"research_step={'YES' if step.research else 'NO'}")

    if not step.path.exists():
        FAILURE_COUNTS[step.script] = FAILURE_COUNTS.get(step.script, 0) + 1
        row = build_step_row(step, cycle_id, "MISSING", 127, 0, started, "", "", f"missing script: {step.path}")
        append_log(f"MISSING step={step.order} name={step.name}")
        log_memory_usage(f"missing::{step.name}", "FAIL", f"missing script: {step.path}")
        return row

    stdout_path = Path(tempfile.gettempdir()) / f"edgeiq_{os.getpid()}_{cycle_id}_{step.order}_stdout.log"
    stderr_path = Path(tempfile.gettempdir()) / f"edgeiq_{os.getpid()}_{cycle_id}_{step.order}_stderr.log"
    try:
        with stdout_path.open("w", encoding="utf-8", errors="replace") as stdout_handle, stderr_path.open("w", encoding="utf-8", errors="replace") as stderr_handle:
            result = subprocess.run(
                [sys.executable, str(step.path)],
                cwd=MODEL_ROOT,
                text=True,
                stdout=stdout_handle,
                stderr=stderr_handle,
                timeout=STEP_TIMEOUT_SECONDS,
            )
        duration = round(time.perf_counter() - start_time, 3)
        stdout_tail = tail_file(stdout_path)
        stderr_tail = tail_file(stderr_path)
        message = stderr_tail.splitlines()[-1] if stderr_tail else stdout_tail.splitlines()[-1] if stdout_tail else "OK"
        status = "OK" if result.returncode == 0 else "FAILED"
        FAILURE_COUNTS[step.script] = 0 if status == "OK" else FAILURE_COUNTS.get(step.script, 0) + 1
        append_log(f"{status} step={step.order} name={step.name} returncode={result.returncode} duration={duration}s message={message[:500]}")
        log_memory_usage(f"after::{step.name}", "OK" if status == "OK" else "FAIL", f"returncode={result.returncode} duration={duration}s")
        row = build_step_row(step, cycle_id, status, result.returncode, duration, started, stdout_tail, stderr_tail, message)
    except subprocess.TimeoutExpired as exc:
        duration = round(time.perf_counter() - start_time, 3)
        FAILURE_COUNTS[step.script] = FAILURE_COUNTS.get(step.script, 0) + 1
        stdout_tail = tail_file(stdout_path)
        stderr_tail = tail_file(stderr_path)
        append_log(f"TIMEOUT step={step.order} name={step.name} duration={duration}s")
        log_memory_usage(f"timeout::{step.name}", "FAIL", f"duration={duration}s")
        row = build_step_row(step, cycle_id, "TIMEOUT", 124, duration, started, stdout_tail, stderr_tail, str(exc))
    except Exception as exc:
        duration = round(time.perf_counter() - start_time, 3)
        FAILURE_COUNTS[step.script] = FAILURE_COUNTS.get(step.script, 0) + 1
        append_log(f"FAILED step={step.order} name={step.name} duration={duration}s message={exc}")
        log_memory_usage(f"failed::{step.name}", "FAIL", str(exc))
        row = build_step_row(step, cycle_id, "FAILED", 1, duration, started, "", repr(exc), str(exc))
    finally:
        try:
            stdout_path.unlink(missing_ok=True)
            stderr_path.unlink(missing_ok=True)
        except Exception:
            pass
        gc.collect()
        collect_garbage(f"gc::{step.name}")

    return row


def run_cycle() -> list[dict[str, object]]:
    global LAST_STEP_ROWS
    cycle_id = datetime.now().strftime("%Y%m%d%H%M%S")
    cycle_started_at = now_iso()
    cycle_start = time.perf_counter()
    rows: list[dict[str, object]] = []

    append_log(f"CYCLE_START id={cycle_id} poll_seconds={POLL_SECONDS} research_enabled={RESEARCH_ENABLED} repo={REPO_ROOT} cwd={MODEL_ROOT}")
    log_memory_usage("cycle_start", "OK", f"research_pipeline_enabled={'YES' if RESEARCH_ENABLED else 'NO'}")
    write_status(rows, status_context(cycle_id, cycle_started_at, "RUNNING", "cycle_start", 0, 0, "RUNNING", ""))
    write_step_status([])

    for step in STEPS:
        failed_so_far = sum(1 for row in rows if row.get("status") not in {"OK", "STALE_WARN", "SKIPPED"})
        write_status(rows, status_context(cycle_id, cycle_started_at, "RUNNING", step.name, len(rows), failed_so_far, cycle_grade(rows) if rows else "RUNNING", ""))
        row = run_step(step, cycle_id)
        rows.append(row)
        LAST_STEP_ROWS = rows
        write_step_status(rows)
        failed_so_far = sum(1 for item in rows if item.get("status") not in {"OK", "STALE_WARN", "SKIPPED"})
        write_status(rows, status_context(cycle_id, cycle_started_at, "RUNNING", step.name, len(rows), failed_so_far, cycle_grade(rows), ""))

    cycle_seconds = time.perf_counter() - cycle_start
    grade = cycle_grade(rows)
    completed_at = now_iso()
    failed_steps = sum(1 for row in rows if row.get("status") not in {"OK", "STALE_WARN", "SKIPPED"})
    write_status(rows, status_context(cycle_id, cycle_started_at, "SLEEPING", "sleep", len(rows), failed_steps, grade, completed_at))
    write_step_status(rows)
    write_telemetry(cycle_id, rows, cycle_seconds, grade)
    collect_garbage("cycle_complete_gc")
    append_log(f"CYCLE_COMPLETE id={cycle_id} grade={grade} seconds={round(cycle_seconds, 3)} research_enabled={RESEARCH_ENABLED} step_status_csv={STEP_STATUS_PATH}")
    return rows


def main() -> None:
    ensure_outputs()
    append_log("EDGEIQ VIC MASTER ORCHESTRATOR BOOT")
    append_log("VIC_ONLY=YES")
    append_log(f"EDGEIQ_ENABLE_RESEARCH_PIPELINE={'YES' if RESEARCH_ENABLED else 'NO'}")
    log_memory_usage("master_orchestrator_boot", "OK", f"research_pipeline_enabled={'YES' if RESEARCH_ENABLED else 'NO'}")
    while True:
        run_cycle()
        if RUN_ONCE:
            append_log("RUN_ONCE complete")
            return
        append_log(f"SLEEP seconds={POLL_SECONDS}")
        collect_garbage("sleep_gc")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
