from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from edgeiq_csv_utils import clean, file_age_seconds, read_csv
from edgeiq_memory_safe_io import count_csv_rows_streaming, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SCRIPTS = ROOT / "scripts"

SPORTSBET = DATA / "sportsbet_live_market_v1.csv"
SPORTSBET_STATUS = DATA / "sportsbet_live_market_status_v1.csv"
TAB_RACECARDS = DATA / "edgeiq_tab_vic_racecards_v1.csv"
TAB_MARKET = DATA / "edgeiq_tab_market_v1.csv"
MARKET_WAREHOUSE = DATA / "edgeiq_pre_result_market_history_warehouse_v1.csv"
MARKET_WAREHOUSE_BATCH = DATA / "edgeiq_pre_result_market_history_warehouse_v1_latest_batch.csv"
MARKET_WAREHOUSE_WATCH = DATA / "edgeiq_pre_result_market_history_warehouse_v1_coverage_watch.csv"

CAPTURE_SCRIPT = SCRIPTS / "capture_sportsbet_live_market_v1.py"
TAB_MARKET_SCRIPT = SCRIPTS / "build_edgeiq_tab_market_v1.py"
MARKET_WAREHOUSE_SCRIPT = SCRIPTS / "build_edgeiq_pre_result_market_history_warehouse_v1.py"
MARKET_JOIN_AUDIT_SCRIPT = SCRIPTS / "build_edgeiq_pre_result_market_rank1_join_audit_v1.py"
MARKET_COVERAGE_WATCH_SCRIPT = SCRIPTS / "build_edgeiq_pre_result_market_history_warehouse_v1_coverage_watch.py"
RUNNER_BOARD_SCRIPT = SCRIPTS / "build_edgeiq_live_runner_board_v1.py"
TERMINAL_SCRIPT = SCRIPTS / "build_edgeiq_live_terminal_feed_v1.py"
EXECUTION_V3_SCRIPT = SCRIPTS / "build_edgeiq_execution_board_v3.py"
EXECUTION_V4_SCRIPT = SCRIPTS / "build_edgeiq_execution_engine_v4.py"
OWNED_EXECUTION_SCRIPT = SCRIPTS / "build_edgeiq_owned_execution_boards_v1.py"
AUDIT_SCRIPT = SCRIPTS / "audit_edgeiq_racing_public_data_freshness_v1.py"

LOG_OUT = DATA / "edgeiq_racing_owned_live_market_refresh_log_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_racing_owned_live_market_refresh_summary_v1.csv"
STATUS_OUT = DATA / "edgeiq_racing_owned_live_market_status_v1.csv"

LOG_FIELDS = [
    "step_order",
    "step_name",
    "status",
    "runtime_seconds",
    "rows_after",
    "refreshed_at",
    "notes",
]
STATUS_FIELDS = [
    "feed_name",
    "status",
    "rows",
    "age_minutes",
    "source_used",
    "notes",
]
SUMMARY_FIELDS = ["metric", "value"]

LOCAL_TZ = timezone(timedelta(hours=10), name="Australia/Sydney")
MARKET_FRESHNESS_MINUTES = 240


def now_local() -> str:
    return datetime.now(LOCAL_TZ).isoformat(timespec="seconds")


def parse_date(value: object):
    text = clean(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text[:10]).date()
    except ValueError:
        return None


def age_minutes(path: Path) -> float | None:
    seconds = file_age_seconds(path)
    return None if seconds is None else round(seconds / 60.0, 1)


def count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    if path.suffix.lower() == ".md":
        text = path.read_text(encoding="utf-8", errors="ignore")
        return 1 if clean(text) else 0
    return count_csv_rows_streaming(path)


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    write_csv_atomic(path, rows, fields)


def first_non_empty(row: dict[str, str], names: list[str]) -> str:
    for name in names:
        value = clean(row.get(name))
        if value:
            return value
    return ""


def fresh_market_candidate(path: Path) -> tuple[bool, int, float | None, str]:
    rows = read_csv(path)
    age = age_minutes(path)
    if not rows:
        return False, 0, age, "missing_or_empty"

    priced_rows = [
        row
        for row in rows
        if clean(first_non_empty(row, ["sportsbet_price", "price_win", "market_price", "current_price", "raw_win_price", "fixed_win"]))
    ]
    if not priced_rows:
        return False, 0, age, "no_priced_rows"

    today = datetime.now(LOCAL_TZ).date()
    max_date = today + timedelta(days=2)
    active_rows = 0
    for row in priced_rows:
        race_date = parse_date(row.get("race_date") or row.get("date") or row.get("race_time"))
        if race_date is not None and today <= race_date <= max_date:
            active_rows += 1

    if age is not None and age <= MARKET_FRESHNESS_MINUTES and active_rows > 0:
        return True, len(priced_rows), age, "fresh_active_window"
    if active_rows > 0:
        return False, len(priced_rows), age, "stale_active_window"
    return False, len(priced_rows), age, "stale_out_of_window"


def latest_capture_status() -> tuple[str, str]:
    rows = read_csv(SPORTSBET_STATUS)
    if not rows:
        return "UNAVAILABLE", ""
    latest = rows[-1]
    return clean(latest.get("source_status")) or "UNAVAILABLE", clean(latest.get("notes"))


def run_python_script(script_path: Path, step_name: str, output_path: Path | None, notes: str) -> dict[str, object]:
    started = time.perf_counter()
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    runtime = time.perf_counter() - started
    status = "PASS" if result.returncode == 0 else "FAIL"
    output_lines = (result.stdout or "").splitlines()[-8:]
    tail = clean(" | ".join(line.strip() for line in output_lines if line.strip()))
    if result.returncode != 0:
        error_lines = (result.stderr or "").splitlines()[-8:]
        tail = clean(" | ".join(line.strip() for line in error_lines if line.strip())) or tail
    return {
        "step_name": step_name,
        "status": status,
        "runtime_seconds": f"{runtime:.2f}",
        "rows_after": count_rows(output_path) if output_path is not None else 0,
        "refreshed_at": now_local(),
        "notes": f"{notes} {tail}".strip(),
    }


def skip_step(step_name: str, output_path: Path | None, notes: str) -> dict[str, object]:
    return {
        "step_name": step_name,
        "status": "SKIP",
        "runtime_seconds": "0.00",
        "rows_after": count_rows(output_path) if output_path is not None else 0,
        "refreshed_at": now_local(),
        "notes": notes,
    }


def main() -> None:
    log_rows: list[dict[str, object]] = []
    status_rows: list[dict[str, object]] = []

    log_rows.append({
        "step_order": 1,
        **run_python_script(
            CAPTURE_SCRIPT,
            "capture_sportsbet_live_market_v1",
            SPORTSBET,
            "owned Sportsbet NextEvents -> Racecard capture attempted before downstream rebuilds",
        ),
    })

    sportsbet_ready, sportsbet_rows, sportsbet_age, sportsbet_reason = fresh_market_candidate(SPORTSBET)
    source_status, source_notes = latest_capture_status()
    source_used = SPORTSBET.name if sportsbet_ready else ""

    status_rows.append({
        "feed_name": SPORTSBET.name,
        "status": "FRESH" if sportsbet_ready else source_status or "BLOCKED",
        "rows": sportsbet_rows,
        "age_minutes": "" if sportsbet_age is None else sportsbet_age,
        "source_used": source_used,
        "notes": clean(source_notes) or sportsbet_reason,
    })

    if TAB_RACECARDS.exists() and count_rows(TAB_RACECARDS) > 0:
        tab_step = run_python_script(
            TAB_MARKET_SCRIPT,
            "build_edgeiq_tab_market_v1",
            TAB_MARKET,
            "TAB market surface rebuilt from current VIC racecards before warehouse append",
        )
    else:
        tab_step = skip_step(
            "build_edgeiq_tab_market_v1",
            TAB_MARKET,
            "TAB VIC racecards source missing or empty; TAB market rebuild skipped",
        )
    log_rows.append({"step_order": 2, **tab_step})

    log_rows.append({
        "step_order": 3,
        **run_python_script(
            MARKET_WAREHOUSE_SCRIPT,
            "build_edgeiq_pre_result_market_history_warehouse_v1",
            MARKET_WAREHOUSE,
            "append-only pre-result market warehouse refreshed from current TAB and Sportsbet surfaces",
        ),
    })
    log_rows.append({
        "step_order": 4,
        **run_python_script(
            MARKET_JOIN_AUDIT_SCRIPT,
            "build_edgeiq_pre_result_market_rank1_join_audit_v1",
            DATA / "edgeiq_pre_result_market_rank1_join_audit_v1.csv",
            "rank1 join audit refreshed after warehouse append",
        ),
    })
    log_rows.append({
        "step_order": 5,
        **run_python_script(
            MARKET_COVERAGE_WATCH_SCRIPT,
            "build_edgeiq_pre_result_market_history_warehouse_v1_coverage_watch",
            MARKET_WAREHOUSE_WATCH,
            "coverage watch appended after warehouse and rank1 join audit refresh",
        ),
    })

    status_rows.append({
        "feed_name": TAB_MARKET.name,
        "status": "FRESH" if count_rows(TAB_MARKET) > 0 else "BLOCKED",
        "rows": count_rows(TAB_MARKET),
        "age_minutes": "" if age_minutes(TAB_MARKET) is None else age_minutes(TAB_MARKET),
        "source_used": TAB_RACECARDS.name if TAB_RACECARDS.exists() else "",
        "notes": "current TAB market surface available for warehouse append" if count_rows(TAB_MARKET) > 0 else "TAB market surface unavailable",
    })
    status_rows.append({
        "feed_name": MARKET_WAREHOUSE.name,
        "status": "FRESH" if count_rows(MARKET_WAREHOUSE) > 0 else "BLOCKED",
        "rows": count_rows(MARKET_WAREHOUSE),
        "age_minutes": "" if age_minutes(MARKET_WAREHOUSE) is None else age_minutes(MARKET_WAREHOUSE),
        "source_used": "TAB|SPORTSBET",
        "notes": "append-only pre-result market warehouse",
    })
    status_rows.append({
        "feed_name": MARKET_WAREHOUSE_WATCH.name,
        "status": "FRESH" if count_rows(MARKET_WAREHOUSE_WATCH) > 0 else "BLOCKED",
        "rows": count_rows(MARKET_WAREHOUSE_WATCH),
        "age_minutes": "" if age_minutes(MARKET_WAREHOUSE_WATCH) is None else age_minutes(MARKET_WAREHOUSE_WATCH),
        "source_used": "warehouse_join_watch",
        "notes": "warehouse coverage growth watch",
    })

    if sportsbet_ready:
        step = run_python_script(
            RUNNER_BOARD_SCRIPT,
            "build_edgeiq_live_runner_board_v1",
            DATA / "edgeiq_live_runner_board_v1.csv",
            f"runner board rebuilt from owned Sportsbet source ({SPORTSBET.name})",
        )
    else:
        step = skip_step(
            "build_edgeiq_live_runner_board_v1",
            DATA / "edgeiq_live_runner_board_v1.csv",
            f"sportsbet source unavailable or stale; live runner board not rebuilt ({source_status or sportsbet_reason})",
        )
    log_rows.append({"step_order": 6, **step})

    log_rows.append({
        "step_order": 7,
        **run_python_script(
            TERMINAL_SCRIPT,
            "build_edgeiq_live_terminal_feed_v1",
            DATA / "edgeiq_vic_live_terminal_feed_v1.csv",
            "active-selector scoped terminal feed rebuilt with honest market-source gating",
        ),
    })
    log_rows.append({
        "step_order": 8,
        **run_python_script(
            EXECUTION_V3_SCRIPT,
            "build_edgeiq_execution_board_v3",
            DATA / "edgeiq_execution_board_v3.csv",
            "execution board v3 rebuilt for owned compatibility chain",
        ),
    })
    log_rows.append({
        "step_order": 9,
        **run_python_script(
            EXECUTION_V4_SCRIPT,
            "build_edgeiq_execution_engine_v4",
            DATA / "edgeiq_execution_engine_v4.csv",
            "execution engine v4 refreshed before owned board projection",
        ),
    })
    log_rows.append({
        "step_order": 10,
        **run_python_script(
            OWNED_EXECUTION_SCRIPT,
            "build_edgeiq_owned_execution_boards_v1",
            DATA / "edgeiq_execution_board_terminal.csv",
            "owned live and terminal execution boards rebuilt from current terminal scope",
        ),
    })
    log_rows.append({
        "step_order": 11,
        **run_python_script(
            AUDIT_SCRIPT,
            "audit_edgeiq_racing_public_data_freshness_v1",
            DATA / "edgeiq_racing_public_data_freshness_v1.csv",
            "freshness audit rerun after owned live-feed refresh",
        ),
    })

    for feed_path in [
        DATA / "edgeiq_vic_live_terminal_feed_v1.csv",
        DATA / "edgeiq_execution_board_live.csv",
        DATA / "edgeiq_execution_board_terminal.csv",
    ]:
        rows = count_rows(feed_path)
        age = age_minutes(feed_path)
        status_rows.append({
            "feed_name": feed_path.name,
            "status": "FRESH" if rows > 0 and age is not None and age <= 30 else "PARTIAL_OK" if rows > 0 else "BLOCKED",
            "rows": rows,
            "age_minutes": "" if age is None else age,
            "source_used": "owned_refresh_chain",
            "notes": "",
        })

    overall_status = "OK"
    if not sportsbet_ready:
        overall_status = "PARTIAL_OK"
    if any(clean(row.get("status")).upper() == "FAIL" for row in log_rows):
        overall_status = "FAIL"

    write_csv(LOG_OUT, log_rows, LOG_FIELDS)
    write_csv(STATUS_OUT, status_rows, STATUS_FIELDS)
    write_csv(
        SUMMARY_OUT,
        [
            {"metric": "overall_status", "value": overall_status},
            {"metric": "sportsbet_source_ready", "value": "YES" if sportsbet_ready else "NO"},
            {"metric": "sportsbet_source_status", "value": source_status or "UNAVAILABLE"},
            {"metric": "sportsbet_source_used", "value": source_used},
            {"metric": "steps_total", "value": len(log_rows)},
            {"metric": "steps_passed", "value": sum(1 for row in log_rows if clean(row.get("status")).upper() == "PASS")},
            {"metric": "steps_failed", "value": sum(1 for row in log_rows if clean(row.get("status")).upper() == "FAIL")},
            {"metric": "steps_skipped", "value": sum(1 for row in log_rows if clean(row.get("status")).upper() == "SKIP")},
            {"metric": "tab_market_rows", "value": count_rows(TAB_MARKET)},
            {"metric": "market_warehouse_rows", "value": count_rows(MARKET_WAREHOUSE)},
            {"metric": "market_warehouse_latest_batch_rows", "value": count_rows(MARKET_WAREHOUSE_BATCH)},
            {"metric": "market_coverage_watch_rows", "value": count_rows(MARKET_WAREHOUSE_WATCH)},
            {"metric": "terminal_rows", "value": count_rows(DATA / "edgeiq_vic_live_terminal_feed_v1.csv")},
            {"metric": "execution_live_rows", "value": count_rows(DATA / "edgeiq_execution_board_live.csv")},
            {"metric": "execution_terminal_rows", "value": count_rows(DATA / "edgeiq_execution_board_terminal.csv")},
        ],
        SUMMARY_FIELDS,
    )

    print("=" * 90)
    print("EDGEIQ RACING OWNED LIVE MARKET REFRESH")
    print("=" * 90)
    print("OVERALL STATUS:", overall_status)
    print("SPORTSBET SOURCE READY:", "YES" if sportsbet_ready else "NO")
    print("SPORTSBET SOURCE STATUS:", source_status or "UNAVAILABLE")
    print("TAB MARKET ROWS:", count_rows(TAB_MARKET))
    print("MARKET WAREHOUSE ROWS:", count_rows(MARKET_WAREHOUSE))
    print("MARKET COVERAGE WATCH ROWS:", count_rows(MARKET_WAREHOUSE_WATCH))
    print("LOG:", LOG_OUT)
    print("STATUS:", STATUS_OUT)
    print("SUMMARY:", SUMMARY_OUT)
    for row in log_rows:
        print(row)


if __name__ == "__main__":
    main()
