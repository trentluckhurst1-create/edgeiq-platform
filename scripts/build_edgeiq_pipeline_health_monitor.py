from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUT = DATA / "edgeiq_pipeline_health.csv"
ORCHESTRATOR_STATUS = DATA / "edgeiq_master_orchestrator_status.csv"
STEP_STATUS = DATA / "edgeiq_orchestrator_step_status.csv"

CHECKS = [
    ("three_day_universe", "edgeiq_vic_three_day_meeting_universe.csv", 360, "critical_rows"),
    ("three_day_race_fields", "edgeiq_vic_three_day_race_fields.csv", 360, "critical_rows"),
    ("three_day_diagnostics", "edgeiq_vic_three_day_meeting_diagnostics.csv", 360, "aux"),
    ("vic_live_feed", "edgeiq_vic_live_terminal_feed_v1.csv", 180, "critical_rows"),
    ("vic_live_fields", "edgeiq_vic_live_fields_synced.csv", 240, "aux"),
    ("scratchings_diag", "edgeiq_vic_scratchings_diagnostics.csv", 300, "aux"),
    ("silk_diag", "edgeiq_silk_enrichment_diagnostics.csv", 300, "aux"),
    ("race_state", "edgeiq_race_state_engine.csv", 240, "core"),
    ("race_clock", "edgeiq_race_clock_engine.csv", 240, "critical_rows"),
    ("market_tape_memory", "edgeiq_market_tape_memory.csv", 600, "aux_empty_ok"),
    ("market_tape_summary", "edgeiq_market_tape_summary.csv", 300, "core"),
    ("market_truth", "edgeiq_market_truth_engine_v3.csv", 240, "core"),
    ("suppression", "edgeiq_execution_suppression_v2.csv", 240, "core"),
    ("execution_engine_v4", "edgeiq_execution_engine_v4.csv", 240, "critical_rows"),
    ("results_truth_loop", "edgeiq_results_truth_loop.csv", 600, "aux_empty_ok"),
    ("execution_accountability", "edgeiq_execution_accountability.csv", 600, "aux_empty_ok"),
    ("form_engine_v2", "edgeiq_form_engine_v2.csv", 600, "aux"),
    ("clv_memory", "edgeiq_clv_memory.csv", 600, "aux"),
    ("results_settlement", "edgeiq_results_auto_settlement.csv", 600, "aux_empty_ok"),
    ("live_terminal", "edgeiq_live_terminal_feed_v1.csv", 240, "aux"),
    ("race_shape", "edgeiq_race_shape_engine_v2.csv", 600, "aux"),
    ("probability", "edgeiq_probability_engine_v4_1.csv", 600, "core"),
    ("execution_board", "edgeiq_execution_board_v3.csv", 600, "critical_exists"),
    ("real_speed_map", "edgeiq_real_speed_map_positions.csv", 300, "aux"),
    ("active_selector", "edgeiq_active_race_selector.csv", 300, "critical_rows"),
    ("orchestrator_status", "edgeiq_master_orchestrator_status.csv", 420, "critical_exists"),
    ("orchestrator_step_status", "edgeiq_orchestrator_step_status.csv", 420, "aux"),
    ("orchestrator_telemetry", "edgeiq_master_orchestrator_telemetry.csv", 420, "aux"),
]

FIELDS = ["timestamp", "check_name", "file", "status", "age_seconds", "rows", "message"]


def now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def timestamp() -> str:
    return now().isoformat(timespec="seconds")


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null", "-"} else text


def parse_datetime(value: object) -> datetime | None:
    text = clean(value)
    if not text:
        return None
    for candidate in (text, text.replace("Z", "+00:00")):
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone()
        except ValueError:
            pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y%m%d%H%M%S"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc).astimezone()
        except ValueError:
            pass
    return None


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    except Exception:
        return []


def file_age_seconds(path: Path) -> float | None:
    if not path.exists():
        return None
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).astimezone()
    return round((now() - modified).total_seconds(), 1)


def health_row(name: str, filename: str, status: str, age: float | str, rows: int, message: str) -> dict[str, object]:
    return {
        "timestamp": timestamp(),
        "check_name": name,
        "file": filename,
        "status": status,
        "age_seconds": age,
        "rows": rows,
        "message": message,
    }


def status_for_file(kind: str, exists: bool, rows: int, age: float | None, stale_after: int) -> tuple[str, str]:
    if not exists:
        if kind in {"critical_rows", "critical_exists"}:
            return "FAIL", "missing_critical_file"
        return "WARN", "missing_auxiliary_file"
    if kind == "critical_rows" and rows == 0:
        return "FAIL", "empty_critical_file"
    if kind == "critical_exists" and rows == 0:
        return "WARN", "critical_file_exists_but_empty"
    if kind != "aux_empty_ok" and rows == 0:
        return "WARN", "empty_auxiliary_file"
    if age is not None and age > stale_after:
        return "WARN", f"stale>{stale_after}s"
    return "OK", "healthy"


def check_file(name: str, filename: str, stale_after: int, kind: str) -> dict[str, object]:
    path = DATA / filename
    rows = read_csv(path)
    age = file_age_seconds(path)
    status, message = status_for_file(kind, path.exists(), len(rows), age, stale_after)
    return health_row(name, filename, status, "" if age is None else age, len(rows), message)


def missing_ratio(rows: list[dict[str, str]], columns: list[str]) -> float:
    if not rows:
        return 1.0
    present = [column for column in columns if column in rows[0]]
    if not present:
        return 1.0
    total = len(rows) * len(present)
    missing = sum(1 for row in rows for column in present if not clean(row.get(column)))
    return missing / total if total else 1.0


def latest_orchestrator_time(rows: list[dict[str, str]]) -> datetime | None:
    fields = [
        "last_heartbeat_at",
        "last_cycle_completed_at",
        "cycle_completed_at",
        "completed_at",
        "finished_at",
        "updated_at",
        "timestamp",
        "cycle_started_at",
        "started_at",
    ]
    latest: datetime | None = None
    for row in rows:
        for field in fields:
            parsed = parse_datetime(row.get(field))
            if parsed and (latest is None or parsed > latest):
                latest = parsed
    return latest


def orchestrator_health() -> dict[str, object]:
    if not ORCHESTRATOR_STATUS.exists():
        return health_row("orchestrator_alive", ORCHESTRATOR_STATUS.name, "FAIL", "", 0, "missing_status_file")
    rows = read_csv(ORCHESTRATOR_STATUS)
    age = file_age_seconds(ORCHESTRATOR_STATUS)
    if not rows:
        if age is not None and age <= 180:
            return health_row("orchestrator_alive", ORCHESTRATOR_STATUS.name, "OK", age, 0, "status_file_initialising")
        return health_row("orchestrator_alive", ORCHESTRATOR_STATUS.name, "FAIL", "" if age is None else age, 0, "empty_status_file")

    latest = latest_orchestrator_time(rows)
    if latest is None:
        if age is not None and age <= 180:
            return health_row("orchestrator_alive", ORCHESTRATOR_STATUS.name, "OK", age, len(rows), "recent_status_without_heartbeat")
        return health_row("orchestrator_alive", ORCHESTRATOR_STATUS.name, "WARN", "" if age is None else age, len(rows), "heartbeat_timestamp_missing")

    heartbeat_age = round((now() - latest).total_seconds(), 1)
    if heartbeat_age < 0:
        heartbeat_age = 0.0
    if heartbeat_age <= 180:
        return health_row("orchestrator_alive", ORCHESTRATOR_STATUS.name, "OK", heartbeat_age, len(rows), "heartbeat_fresh")
    if heartbeat_age <= 360:
        return health_row("orchestrator_alive", ORCHESTRATOR_STATUS.name, "WARN", heartbeat_age, len(rows), "heartbeat_lagging")
    return health_row("orchestrator_alive", ORCHESTRATOR_STATUS.name, "FAIL", heartbeat_age, len(rows), "heartbeat_stalled")


def step_status_health() -> list[dict[str, object]]:
    rows = read_csv(STEP_STATUS)
    if not rows:
        return [
            health_row("failed_enrichments", STEP_STATUS.name, "WARN" if STEP_STATUS.exists() else "OK", file_age_seconds(STEP_STATUS) or "", 0, "step_status_pending"),
            health_row("repeated_step_failures", STEP_STATUS.name, "OK", "", 0, "no_repeated_failures_detected"),
        ]

    latest_by_step: dict[str, dict[str, str]] = {}
    for row in rows:
        step = clean(row.get("step_name")) or clean(row.get("script")) or str(len(latest_by_step))
        current = latest_by_step.get(step)
        row_time = parse_datetime(row.get("timestamp") or row.get("finished_at"))
        current_time = parse_datetime(current.get("timestamp") or current.get("finished_at")) if current else None
        if current is None or (row_time and current_time and row_time >= current_time):
            latest_by_step[step] = row

    failed = [row for row in latest_by_step.values() if clean(row.get("success")).upper() == "NO" or clean(row.get("status")).upper() == "FAIL"]
    critical = [row for row in failed if clean(row.get("critical")).upper() == "YES"]
    repeated = []
    for row in rows:
        try:
            count = int(float(clean(row.get("failure_count")) or "0"))
        except ValueError:
            count = 0
        if count > 3:
            repeated.append(row)

    return [
        health_row(
            "failed_enrichments",
            STEP_STATUS.name,
            "WARN" if failed else "OK",
            file_age_seconds(STEP_STATUS) or "",
            len(rows),
            f"latest_failed_steps={len(failed)} critical_latest_failures={len(critical)}",
        ),
        health_row(
            "repeated_step_failures",
            STEP_STATUS.name,
            "FAIL" if repeated else "OK",
            file_age_seconds(STEP_STATUS) or "",
            len(rows),
            f"failure_count_gt_3={len(repeated)}",
        ),
    ]


def data_quality_checks() -> list[dict[str, object]]:
    live = read_csv(DATA / "edgeiq_vic_live_terminal_feed_v1.csv")
    fields = read_csv(DATA / "edgeiq_vic_live_fields_synced.csv")
    silks = read_csv(DATA / "edgeiq_silk_enrichment_diagnostics.csv")
    truth = read_csv(DATA / "edgeiq_market_truth_engine_v3.csv")
    suppression = read_csv(DATA / "edgeiq_execution_suppression_v2.csv")
    selector = read_csv(DATA / "edgeiq_active_race_selector.csv")
    universe = read_csv(DATA / "edgeiq_vic_three_day_meeting_universe.csv")
    clock = read_csv(DATA / "edgeiq_race_clock_engine.csv")
    execution_v4 = read_csv(DATA / "edgeiq_execution_engine_v4.csv")
    tape_summary = read_csv(DATA / "edgeiq_market_tape_summary.csv")
    accountability = read_csv(DATA / "edgeiq_execution_accountability.csv")

    odds_missing = missing_ratio(live, ["ui_price", "sportsbet_price", "live_price", "market_price", "fixed_win"])
    silk_matches = sum(1 for row in silks if clean(row.get("matched")).upper() == "YES")
    silk_missing = 1 - (silk_matches / max(1, len(silks)))
    empty_fields = not fields or missing_ratio(fields, ["track", "race_no", "horse"]) > 0.4
    truth_reject_rate = sum(1 for row in truth if clean(row.get("truth_grade")).upper() == "REJECT") / max(1, len(truth))
    hard_suppression_rate = sum(1 for row in suppression if clean(row.get("suppression_action")).upper() in {"KILL", "SUPPRESS"}) / max(1, len(suppression))
    default_focus = sum(1 for row in selector if clean(row.get("default_ui_focus")).upper() == "YES")
    clock_focus = sum(1 for row in clock if clean(row.get("should_default_focus")).upper() == "YES")
    stale_selector = selector_date_violations(selector, stale=True)
    future_selector = selector_date_violations(selector, stale=False)
    stale_universe = selector_date_violations(universe, stale=True)
    future_universe = selector_date_violations(universe, stale=False)

    return [
        health_row("missing_odds", "edgeiq_vic_live_terminal_feed_v1.csv", "OK" if odds_missing < 0.85 else "WARN", "", len(live), f"missing_ratio={odds_missing:.2f}"),
        health_row("missing_silks", "edgeiq_silk_enrichment_diagnostics.csv", "OK" if silk_missing < 0.35 else "WARN", "", len(silks), f"missing_ratio={silk_missing:.2f}"),
        health_row("empty_fields", "edgeiq_vic_live_fields_synced.csv", "WARN" if empty_fields else "OK", "", len(fields), "field_core_columns_checked"),
        health_row("truth_reject_rate", "edgeiq_market_truth_engine_v3.csv", "OK" if truth_reject_rate >= 0.05 else "WARN", "", len(truth), f"reject_rate={truth_reject_rate:.2f}"),
        health_row("hard_suppression_rate", "edgeiq_execution_suppression_v2.csv", "OK" if hard_suppression_rate >= 0.05 else "WARN", "", len(suppression), f"hard_suppression_rate={hard_suppression_rate:.2f}"),
        health_row("selector_default_focus", "edgeiq_active_race_selector.csv", "OK" if default_focus == 1 else "FAIL", "", len(selector), f"default_focus_rows={default_focus}"),
        health_row("race_clock_default_focus", "edgeiq_race_clock_engine.csv", "OK" if clock_focus == 1 else "FAIL", "", len(clock), f"default_focus_rows={clock_focus}"),
        health_row("execution_v4_full_field", "edgeiq_execution_engine_v4.csv", "OK" if len(execution_v4) >= max(1, int(len(universe) * 0.8)) else "WARN", "", len(execution_v4), f"universe_rows={len(universe)}"),
        health_row("market_tape_summary_rows", "edgeiq_market_tape_summary.csv", "OK" if tape_summary else "WARN", "", len(tape_summary), "summary_rows_present"),
        health_row("execution_accountability_rows", "edgeiq_execution_accountability.csv", "OK" if accountability else "WARN", "", len(accountability), "accountability_rows_present"),
        health_row("selector_stale_dates", "edgeiq_active_race_selector.csv", "FAIL" if stale_selector else "OK", "", len(selector), f"stale_rows={stale_selector}"),
        health_row("selector_future_dates", "edgeiq_active_race_selector.csv", "FAIL" if future_selector else "OK", "", len(selector), f"beyond_next_day_rows={future_selector}"),
        health_row("universe_stale_dates", "edgeiq_vic_three_day_meeting_universe.csv", "FAIL" if stale_universe else "OK", "", len(universe), f"stale_rows={stale_universe}"),
        health_row("universe_future_dates", "edgeiq_vic_three_day_meeting_universe.csv", "FAIL" if future_universe else "OK", "", len(universe), f"beyond_next_day_rows={future_universe}"),
    ]


def selector_date_violations(rows: list[dict[str, str]], stale: bool) -> int:
    today = now().date()
    max_date = today + timedelta(days=2)
    count = 0
    for row in rows:
        parsed = parse_datetime(clean(row.get("race_date")) or clean(row.get("date")))
        if parsed is None:
            continue
        row_date = parsed.date()
        if stale and row_date < today:
            count += 1
        if not stale and row_date > max_date:
            count += 1
    return count


def overall_grade(rows: list[dict[str, object]]) -> str:
    red_names = {
        "three_day_universe",
        "three_day_race_fields",
        "vic_live_feed",
        "execution_board",
        "race_clock",
        "execution_engine_v4",
        "active_selector",
        "orchestrator_status",
        "orchestrator_alive",
        "repeated_step_failures",
        "selector_default_focus",
        "race_clock_default_focus",
        "selector_stale_dates",
        "selector_future_dates",
        "universe_stale_dates",
        "universe_future_dates",
    }
    real_red = any(str(row.get("status")).upper() == "FAIL" and str(row.get("check_name")) in red_names for row in rows)
    if real_red:
        return "RED"
    warnings = [row for row in rows if str(row.get("status")).upper() in {"WARN", "FAIL"}]
    if warnings:
        return "AMBER"
    return "GREEN"


def write_rows(rows: list[dict[str, object]]) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(OUT)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    rows = [check_file(*item) for item in CHECKS]
    rows.extend(data_quality_checks())
    rows.extend(step_status_health())
    rows.append(orchestrator_health())
    grade = overall_grade(rows)
    rows.append(health_row("overall_health_grade", "", grade, "", len(rows), "GREEN=no_failures|AMBER=degraded_nonfatal|RED=dead_core_or_repeated_failures"))
    write_rows(rows)

    print("=" * 90)
    print("EDGEIQ PIPELINE HEALTH MONITOR")
    print("=" * 90)
    print("OVERALL:", grade)
    for row in rows:
        print(row)
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
