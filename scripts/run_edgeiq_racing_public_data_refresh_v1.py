from __future__ import annotations

import csv
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"
SCRIPTS = ROOT / "scripts"

AUDIT_SCRIPT = SCRIPTS / "audit_edgeiq_racing_public_data_freshness_v1.py"
PIPELINE_HEALTH_SCRIPT = SCRIPTS / "build_edgeiq_pipeline_health_monitor.py"

LOG_OUT = PUBLIC / "edgeiq_racing_public_data_refresh_log_v1.csv"
SUMMARY_OUT = PUBLIC / "edgeiq_racing_public_data_refresh_summary_v1.csv"
FRESHNESS_SUMMARY = PUBLIC / "edgeiq_racing_public_data_freshness_summary_v1.csv"
FRESHNESS_AUDIT = PUBLIC / "edgeiq_racing_public_data_freshness_v1.csv"

LOG_FIELDS = [
    "step_order",
    "feed_name",
    "script_name",
    "status",
    "runtime_seconds",
    "output_path",
    "rows_after",
    "refreshed_at",
    "notes",
]
SUMMARY_FIELDS = ["metric", "value"]

PLAN = [
    {
        "feed_name": "sportsbet_live_market_v1",
        "script_name": "",
        "status": "SKIP",
        "notes": "No safe local Sportsbet market refresh script identified in this repo; preserve stale truth honestly.",
    },
    {
        "feed_name": "edgeiq_vic_live_terminal_feed_v1",
        "script_name": "",
        "status": "SKIP",
        "notes": "No safe local builder identified for edgeiq_vic_live_terminal_feed_v1.csv; legacy terminal builder is cwd-sensitive.",
    },
    {
        "feed_name": "edgeiq_master_runner_table",
        "script_name": "",
        "status": "SKIP",
        "notes": "No owned refresh script identified for edgeiq_master_runner_table.csv.",
    },
    {
        "feed_name": "edgeiq_execution_board_live",
        "script_name": "",
        "status": "SKIP",
        "notes": "Execution board live refresh is blocked pending a clearly owned non-legacy builder chain.",
    },
    {
        "feed_name": "edgeiq_execution_board_terminal",
        "script_name": "",
        "status": "SKIP",
        "notes": "Execution board terminal refresh is blocked pending a clearly owned non-legacy builder chain.",
    },
    {
        "feed_name": "edgeiq_live_runner_board_v1",
        "script_name": "build_edgeiq_live_runner_board_v1.py",
        "output_path": "public/data/edgeiq_live_runner_board_v1.csv",
        "required_all": [
            "public/data/race_card_report.csv",
            "public/data/edgeiq_runner_intelligence_v1.csv",
            "public/data/sportsbet_live_market_v1.csv",
        ],
        "timeout_seconds": 180,
        "notes": "Rebuild live runner board from current card, runner intelligence and Sportsbet market feed.",
    },
    {
        "feed_name": "edgeiq_vic_three_day_meeting_universe",
        "script_name": "build_edgeiq_vic_three_day_meeting_universe.py",
        "output_path": "public/data/edgeiq_vic_three_day_meeting_universe.csv",
        "required_any": [
            "public/data/race_card_report.csv",
            "public/data/race_fields.csv",
            "public/data/edgeiq_live_runner_board_v1.csv",
        ],
        "timeout_seconds": 180,
        "notes": "Rebuild the active three-day meeting universe from the best available field source.",
    },
    {
        "feed_name": "edgeiq_active_race_selector_pre_clock",
        "script_name": "build_edgeiq_active_race_selector.py",
        "output_path": "public/data/edgeiq_active_race_selector.csv",
        "required_any": [
            "public/data/edgeiq_vic_three_day_meeting_universe.csv",
            "public/data/edgeiq_race_clock_engine.csv",
        ],
        "timeout_seconds": 60,
        "notes": "Seed the active selector before the race clock refresh so downstream timing scripts have a surface.",
    },
    {
        "feed_name": "edgeiq_race_state_engine",
        "script_name": "build_edgeiq_race_state_engine.py",
        "output_path": "public/data/edgeiq_race_state_engine.csv",
        "required_any": [
            "public/data/edgeiq_active_race_selector.csv",
            "public/data/edgeiq_vic_live_terminal_feed_v1.csv",
        ],
        "timeout_seconds": 60,
        "notes": "Refresh race lifecycle status from the active selector and current live terminal feed.",
    },
    {
        "feed_name": "edgeiq_race_clock_engine",
        "script_name": "build_edgeiq_race_clock_engine.py",
        "output_path": "public/data/edgeiq_race_clock_engine.csv",
        "required_all": [
            "public/data/edgeiq_vic_three_day_meeting_universe.csv",
            "public/data/edgeiq_active_race_selector.csv",
        ],
        "timeout_seconds": 60,
        "notes": "Recompute countdown and selector timing state.",
    },
    {
        "feed_name": "edgeiq_active_race_selector",
        "script_name": "build_edgeiq_active_race_selector.py",
        "output_path": "public/data/edgeiq_active_race_selector.csv",
        "required_any": [
            "public/data/edgeiq_race_clock_engine.csv",
            "public/data/edgeiq_vic_three_day_meeting_universe.csv",
        ],
        "timeout_seconds": 60,
        "notes": "Rebuild the selector again after the clock refresh so focus and race-state ordering are current.",
    },
    {
        "feed_name": "edgeiq_execution_board_v3",
        "script_name": "build_edgeiq_execution_board_v3.py",
        "output_path": "public/data/edgeiq_execution_board_v3.csv",
        "required_any": [
            "public/data/edgeiq_probability_engine_v4_1.csv",
            "public/data/edgeiq_vic_live_terminal_feed_v1.csv",
        ],
        "timeout_seconds": 120,
        "notes": "Refresh execution board v3 so CLV memory has the latest accessible model board.",
    },
    {
        "feed_name": "edgeiq_clv_memory",
        "script_name": "build_edgeiq_clv_memory_engine.py",
        "output_path": "public/data/edgeiq_clv_memory.csv",
        "required_all": [
            "public/data/edgeiq_vic_live_terminal_feed_v1.csv",
            "public/data/edgeiq_execution_board_v3.csv",
        ],
        "timeout_seconds": 120,
        "notes": "Refresh CLV memory from the latest live terminal feed and execution board v3 snapshot.",
    },
    {
        "feed_name": "edgeiq_market_tape_summary",
        "script_name": "build_edgeiq_market_tape_memory.py",
        "output_path": "public/data/edgeiq_market_tape_summary.csv",
        "required_any": [
            "public/data/edgeiq_vic_three_day_meeting_universe.csv",
            "public/data/edgeiq_vic_live_terminal_feed_v1.csv",
        ],
        "timeout_seconds": 180,
        "notes": "Refresh market tape memory and the summary surface used by Market and Learning tabs.",
    },
    {
        "feed_name": "edgeiq_execution_engine_v4",
        "script_name": "build_edgeiq_execution_engine_v4.py",
        "output_path": "public/data/edgeiq_execution_engine_v4.csv",
        "required_all": [
            "public/data/edgeiq_vic_three_day_meeting_universe.csv",
            "public/data/edgeiq_market_tape_summary.csv",
        ],
        "timeout_seconds": 180,
        "notes": "Refresh the current execution decision board used by Race and Learning surfaces.",
    },
    {
        "feed_name": "edgeiq_results_master",
        "script_name": "build_edgeiq_results_master.py",
        "output_path": "public/data/edgeiq_results_master.csv",
        "required_any": [
            "public/data/paper_bets_settled.csv",
            "public/data/edgeiq_execution_board_live.csv",
            "public/data/edgeiq_execution_board_terminal.csv",
        ],
        "timeout_seconds": 180,
        "notes": "Refresh results master from available settled-signal and result sources.",
    },
    {
        "feed_name": "edgeiq_results_summary",
        "script_name": "build_edgeiq_results_summary.py",
        "output_path": "public/data/edgeiq_results_summary.csv",
        "required_all": [
            "public/data/edgeiq_results_master.csv",
        ],
        "timeout_seconds": 120,
        "notes": "Refresh the compact results summary used by the Results tab.",
    },
    {
        "feed_name": "edgeiq_results_truth_loop",
        "script_name": "build_edgeiq_results_truth_loop.py",
        "output_path": "public/data/edgeiq_results_truth_loop.csv",
        "required_all": [
            "public/data/edgeiq_execution_engine_v4.csv",
            "public/data/edgeiq_market_tape_summary.csv",
        ],
        "timeout_seconds": 120,
        "notes": "Refresh truth-loop and accountability surfaces used by Results and Learning tabs.",
    },
    {
        "feed_name": "edgeiq_ecology_daily_report",
        "script_name": "build_edgeiq_ecology_daily_report_v1.py",
        "output_path": "public/data/edgeiq_ecology_daily_report.md",
        "required_all": [
            "scripts/run_edgeiq_ecology_master_memory_orchestrator_v2.py",
        ],
        "timeout_seconds": 300,
        "notes": "Refresh the offline research-only ecology daily report.",
    },
    {
        "feed_name": "edgeiq_pipeline_health",
        "script_name": "build_edgeiq_pipeline_health_monitor.py",
        "output_path": "public/data/edgeiq_pipeline_health.csv",
        "required_any": [
            "public/data/edgeiq_active_race_selector.csv",
            "public/data/edgeiq_vic_live_terminal_feed_v1.csv",
        ],
        "timeout_seconds": 120,
        "notes": "Recompute the Racing pipeline health monitor after refresh steps complete.",
    },
    {
        "feed_name": "edgeiq_racing_public_data_freshness",
        "script_name": "audit_edgeiq_racing_public_data_freshness_v1.py",
        "output_path": "public/data/edgeiq_racing_public_data_freshness_v1.csv",
        "required_all": [
            "scripts/audit_edgeiq_racing_public_data_freshness_v1.py",
        ],
        "timeout_seconds": 120,
        "notes": "Rerun the freshness audit after the refresh batch so UI health reflects actual feed truth.",
    },
]


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"", "-", "nan", "none", "null", "undefined"} else text


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    except Exception:
        return []


def count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    if path.suffix.lower() == ".md":
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            return 0
        return 1 if clean(text) else 0
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            next(reader, None)
            return sum(1 for _ in reader)
    except Exception:
        return 0


def resolve(relative_path: str) -> Path:
    return ROOT / relative_path.replace("/", "\\")


def has_all(paths: list[str]) -> bool:
    return all(resolve(path).exists() for path in paths)


def has_any(paths: list[str]) -> bool:
    return any(resolve(path).exists() for path in paths)


def build_skip_row(step_order: int, step: dict[str, object], notes: str) -> dict[str, object]:
    output_path = resolve(str(step.get("output_path", ""))) if clean(step.get("output_path")) else None
    return {
        "step_order": step_order,
        "feed_name": step["feed_name"],
        "script_name": step.get("script_name", ""),
        "status": "SKIP",
        "runtime_seconds": "0.00",
        "output_path": "" if output_path is None else str(output_path.relative_to(ROOT)).replace("\\", "/"),
        "rows_after": count_rows(output_path) if output_path is not None else 0,
        "refreshed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "notes": notes,
    }


def run_script_step(step_order: int, step: dict[str, object]) -> dict[str, object]:
    script_name = clean(step.get("script_name"))
    script_path = SCRIPTS / script_name
    output_path = resolve(str(step.get("output_path", "")))

    if not script_path.exists():
        return build_skip_row(step_order, step, f"script missing: {script_name}")

    required_all = list(step.get("required_all", []))
    required_any = list(step.get("required_any", []))
    if required_all and not has_all(required_all):
        missing = [path for path in required_all if not resolve(path).exists()]
        return build_skip_row(step_order, step, f"missing required inputs: {'; '.join(missing)}")
    if required_any and not has_any(required_any):
        return build_skip_row(step_order, step, f"none of the optional refresh inputs exist: {'; '.join(required_any)}")

    started = time.perf_counter()
    refreshed_at = datetime.now().astimezone().isoformat(timespec="seconds")
    command = [sys.executable, str(script_path)]
    try:
        result = subprocess.run(
            command,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=int(step.get("timeout_seconds", 180)),
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "step_order": step_order,
            "feed_name": step["feed_name"],
            "script_name": script_name,
            "status": "FAIL",
            "runtime_seconds": f"{time.perf_counter() - started:.2f}",
            "output_path": str(output_path.relative_to(ROOT)).replace("\\", "/") if output_path else "",
            "rows_after": count_rows(output_path),
            "refreshed_at": refreshed_at,
            "notes": f"timeout after {step.get('timeout_seconds', 180)}s | stdout={clean(exc.stdout)[:300]} | stderr={clean(exc.stderr)[:300]}",
        }

    stdout_tail = " | ".join(line.strip() for line in clean(result.stdout).splitlines()[-6:] if line.strip())
    stderr_tail = " | ".join(line.strip() for line in clean(result.stderr).splitlines()[-6:] if line.strip())
    notes = clean(step.get("notes"))
    if stdout_tail:
        notes = f"{notes} | stdout: {stdout_tail}"
    if stderr_tail:
        notes = f"{notes} | stderr: {stderr_tail}"

    return {
        "step_order": step_order,
        "feed_name": step["feed_name"],
        "script_name": script_name,
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "runtime_seconds": f"{time.perf_counter() - started:.2f}",
        "output_path": str(output_path.relative_to(ROOT)).replace("\\", "/") if output_path else "",
        "rows_after": count_rows(output_path),
        "refreshed_at": refreshed_at,
        "notes": notes if notes else f"return_code={result.returncode}",
    }


def read_summary_metric(rows: list[dict[str, str]], key: str) -> str:
    for row in rows:
        if clean(row.get("metric")) == key:
            return clean(row.get("value"))
    return ""


def build_summary(log_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    freshness_summary_rows = read_csv(FRESHNESS_SUMMARY)
    stale_count = read_summary_metric(freshness_summary_rows, "stale_count")
    missing_count = read_summary_metric(freshness_summary_rows, "missing_count")
    required_blockers = read_summary_metric(freshness_summary_rows, "required_surface_blockers")

    passed = sum(1 for row in log_rows if row["status"] == "PASS")
    failed = sum(1 for row in log_rows if row["status"] == "FAIL")
    skipped = sum(1 for row in log_rows if row["status"] == "SKIP")
    if failed:
        overall = "FAIL"
    elif clean(stale_count) and int(float(stale_count)) > 0:
        overall = "WARNING"
    else:
        overall = "HEALTHY"

    return [
        {"metric": "overall_status", "value": overall},
        {"metric": "steps_total", "value": len(log_rows)},
        {"metric": "steps_passed", "value": passed},
        {"metric": "steps_failed", "value": failed},
        {"metric": "steps_skipped", "value": skipped},
        {"metric": "stale_count_after_refresh", "value": stale_count or "0"},
        {"metric": "missing_count_after_refresh", "value": missing_count or "0"},
        {"metric": "required_surface_blockers_after_refresh", "value": required_blockers or "0"},
        {"metric": "top_stale_feed", "value": read_summary_metric(freshness_summary_rows, "top_blocker_feed")},
        {"metric": "top_stale_reason", "value": read_summary_metric(freshness_summary_rows, "top_blocker_reason")},
    ]


def main() -> None:
    print("=" * 96)
    print("EDGEIQ RACING PUBLIC DATA REFRESH V1")
    print("=" * 96)
    print("Refresh only safe local public/data producers. Preserve stale truth where no safe builder exists.")

    log_rows: list[dict[str, object]] = []
    for step_order, step in enumerate(PLAN, start=1):
        if clean(step.get("status")) == "SKIP":
            row = build_skip_row(step_order, step, clean(step.get("notes")))
        else:
            row = run_script_step(step_order, step)
        log_rows.append(row)
        print(
            f"[{step_order:02d}/{len(PLAN):02d}] {row['feed_name']} -> {row['status']} "
            f"rows={row['rows_after']} runtime={row['runtime_seconds']}s"
        )

    write_csv(LOG_OUT, log_rows, LOG_FIELDS)
    summary_rows = build_summary(log_rows)
    write_csv(SUMMARY_OUT, summary_rows, SUMMARY_FIELDS)

    print("-" * 96)
    for row in summary_rows:
        print(f"{row['metric']}: {row['value']}")
    print("LOG:", LOG_OUT)
    print("SUMMARY:", SUMMARY_OUT)


if __name__ == "__main__":
    main()
