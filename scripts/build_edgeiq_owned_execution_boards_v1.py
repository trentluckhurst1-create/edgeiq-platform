from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from edgeiq_csv_utils import clean, first, read_csv, runner_key, write_csv


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

TERMINAL = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
LIVE_RUNNER = DATA / "edgeiq_live_runner_board_v1.csv"
EXECUTION_V4 = DATA / "edgeiq_execution_engine_v4.csv"
EXECUTION_V3 = DATA / "edgeiq_execution_board_v3.csv"

LIVE_OUT = DATA / "edgeiq_execution_board_live.csv"
TERMINAL_OUT = DATA / "edgeiq_execution_board_terminal.csv"
DIAG = DATA / "edgeiq_owned_execution_boards_v1_diagnostics.csv"

LOCAL_TZ = timezone(timedelta(hours=10), name="Australia/Sydney")

LIVE_FIELDS = [
    "built_at",
    "meeting_key",
    "race_key",
    "runner_key",
    "race_date",
    "track",
    "race_no",
    "race_time",
    "horse_no",
    "horse",
    "horse_key",
    "barrier",
    "jockey",
    "trainer",
    "sportsbet_event_id",
    "sportsbet_market_id",
    "sportsbet_timestamp",
    "bookmaker",
    "sportsbet_price",
    "market_price",
    "live_price",
    "current_price",
    "fixed_win",
    "rated_price",
    "fair_price",
    "ui_fair_price",
    "edge_pct",
    "overlay_pct",
    "ui_edge_pct",
    "execution_action",
    "final_execution_state",
    "model_execution_decision",
    "v3_execution_action",
    "v4_execution_decision",
    "execution_reason",
    "execution_score",
    "stake",
    "market_state",
    "truth_grade",
    "market_confidence",
    "liquidity_grade",
    "fake_overlay_flag",
    "late_drift_risk",
    "execution_trust_score",
    "suppression_action",
    "suppression_reason",
    "race_state",
    "minutes_to_jump",
    "market_mover",
    "movement_velocity",
    "mobile_silk_image",
    "market_source_status",
    "market_source_ready",
    "market_source_file",
    "terminal_scope",
    "ui_status",
]

TERMINAL_FIELDS = [
    "built_at",
    "race_date",
    "track",
    "race_no",
    "race_time",
    "horse_no",
    "horse",
    "horse_key",
    "runner_key",
    "sportsbet_price",
    "market_price",
    "live_price",
    "rated_price",
    "fair_price",
    "edge_pct",
    "execution_action",
    "final_execution_state",
    "model_execution_decision",
    "execution_reason",
    "execution_score",
    "stake",
    "market_state",
    "truth_grade",
    "market_confidence",
    "market_source_status",
    "market_source_ready",
    "race_state",
    "minutes_to_jump",
    "market_mover",
    "bookmaker",
]

DIAG_FIELDS = [
    "built_at",
    "status",
    "rows_live",
    "rows_terminal",
    "rows_with_live_price",
    "rows_market_blocked",
    "execute_rows",
    "watch_rows",
    "pass_rows",
]


def now_local() -> str:
    return datetime.now(LOCAL_TZ).isoformat(timespec="seconds")


def build_lookup(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for row in rows:
        key = first(row, ["runner_key"]) or runner_key(row)
        if key and key not in lookup:
            lookup[key] = row
    return lookup


def map_execution_action(model_decision: str, market_ready: bool, has_price: bool) -> tuple[str, str]:
    decision = clean(model_decision).upper()
    if not market_ready:
        return "NO LIVE", "market source unavailable; live execution blocked"
    if not has_price:
        return "NO LIVE", "no live market price available"
    if decision in {"EXECUTE"}:
        return "EXECUTE", "execution engine v4 execute"
    if decision in {"ALLOW", "REDUCE"}:
        return "WATCH", f"execution engine v4 {decision.lower()}"
    if decision in {"MONITOR"}:
        return "PASS", "execution engine v4 monitor"
    if decision in {"SUPPRESS", "KILL", "NO_PRICE"}:
        return "PASS", f"execution engine v4 {decision.lower()}"
    if decision in {"SCRATCHED"}:
        return "SCRATCHED", "runner scratched"
    if decision:
        return decision, "execution decision carried through"
    return "PASS", "no owned execution decision available"


def main() -> None:
    terminal_rows = read_csv(TERMINAL)
    live_rows = read_csv(LIVE_RUNNER)
    v4_rows = read_csv(EXECUTION_V4)
    v3_rows = read_csv(EXECUTION_V3)

    live_lookup = build_lookup(live_rows)
    v4_lookup = build_lookup(v4_rows)
    v3_lookup = build_lookup(v3_rows)

    built_at = now_local()
    live_output: list[dict[str, object]] = []
    terminal_output: list[dict[str, object]] = []

    for row in terminal_rows:
        key = first(row, ["runner_key"]) or runner_key(row)
        live = live_lookup.get(key, {})
        v4 = v4_lookup.get(key, {})
        v3 = v3_lookup.get(key, {})

        row_live_price = clean(first(row, ["ui_price", "live_price", "sportsbet_price", "market_price", "fixed_win"]))
        board_live_price = clean(first(live, ["live_price", "sportsbet_price", "market_price", "current_price"]))
        live_price = row_live_price or board_live_price

        market_ready = clean(row.get("market_source_ready")).upper() == "YES" or bool(board_live_price)
        fair_price = clean(first(row, ["ui_fair_price", "rated_price", "fair_price"])) or clean(first(live, ["fair_price", "ui_fair_price"]))
        model_decision = first(v4, ["execution_decision"]) or first(v3, ["execution_action", "v3_execution_action"]) or first(row, ["execution_action"])
        execution_action, action_reason = map_execution_action(model_decision, market_ready, bool(live_price))

        merged = {
            "built_at": built_at,
            "meeting_key": first(row, ["meeting_key"]),
            "race_key": first(row, ["race_key"]),
            "runner_key": key,
            "race_date": first(row, ["race_date"]),
            "track": first(row, ["track"]),
            "race_no": first(row, ["race_no"]),
            "race_time": first(row, ["race_time"]),
            "horse_no": first(row, ["horse_no", "runner_number"]),
            "horse": first(row, ["horse"]),
            "horse_key": first(row, ["horse_key"]),
            "barrier": first(row, ["barrier"]),
            "jockey": first(row, ["jockey"]),
            "trainer": first(row, ["trainer"]),
            "sportsbet_event_id": first(row, ["sportsbet_event_id"]) or first(live, ["sportsbet_event_id", "event_id"]),
            "sportsbet_market_id": first(row, ["sportsbet_market_id"]) or first(live, ["sportsbet_market_id", "market_id"]),
            "sportsbet_timestamp": first(row, ["sportsbet_timestamp", "market_capture_timestamp"]) or first(live, ["sportsbet_timestamp", "timestamp"]),
            "bookmaker": first(row, ["bookmaker"]) or first(live, ["bookmaker"]) or "Sportsbet",
            "sportsbet_price": clean(first(row, ["sportsbet_price"])) or clean(first(live, ["live_price", "sportsbet_price", "market_price"])),
            "market_price": clean(first(row, ["market_price", "ui_price"])) or live_price,
            "live_price": live_price,
            "current_price": live_price,
            "fixed_win": clean(first(row, ["fixed_win"])),
            "rated_price": clean(first(row, ["rated_price", "ui_fair_price"])),
            "fair_price": fair_price,
            "ui_fair_price": fair_price,
            "edge_pct": clean(first(row, ["ui_edge_pct", "edge_pct"])),
            "overlay_pct": clean(first(row, ["ui_edge_pct", "edge_pct"])),
            "ui_edge_pct": clean(first(row, ["ui_edge_pct", "edge_pct"])),
            "execution_action": execution_action,
            "final_execution_state": execution_action,
            "model_execution_decision": model_decision,
            "v3_execution_action": first(v3, ["execution_action", "v3_execution_action"]),
            "v4_execution_decision": first(v4, ["execution_decision"]),
            "execution_reason": action_reason if execution_action != "PASS" or not first(v4, ["reason"]) else first(v4, ["reason"]),
            "execution_score": first(v4, ["execution_score"]) or first(v3, ["execution_score"]),
            "stake": first(v4, ["stake"]) if market_ready else "0.00",
            "market_state": "LIVE_PRICE" if live_price else "NO_LIVE_PRICE",
            "truth_grade": first(row, ["truth_grade"]),
            "market_confidence": first(row, ["market_confidence"]),
            "liquidity_grade": first(row, ["liquidity_grade"]),
            "fake_overlay_flag": first(row, ["fake_overlay_flag"]),
            "late_drift_risk": first(row, ["late_drift_risk"]),
            "execution_trust_score": first(row, ["execution_trust_score"]),
            "suppression_action": first(row, ["suppression_action"]),
            "suppression_reason": first(row, ["suppression_reason"]),
            "race_state": first(row, ["race_state"]),
            "minutes_to_jump": first(row, ["minutes_to_jump"]),
            "market_mover": first(row, ["market_mover"]) or first(live, ["market_mover"]),
            "movement_velocity": first(row, ["movement_velocity"]) or first(live, ["movement_velocity"]),
            "mobile_silk_image": first(row, ["mobile_silk_image", "silkUrl", "silk_url", "local_silk_path"]),
            "market_source_status": first(row, ["market_source_status"]) or ("LIVE_PRICE" if live_price else ""),
            "market_source_ready": first(row, ["market_source_ready"]) or ("YES" if live_price else "NO"),
            "market_source_file": first(row, ["market_source_file"]) or ("edgeiq_live_runner_board_v1.csv" if board_live_price else ""),
            "terminal_scope": first(row, ["terminal_scope"]),
            "ui_status": first(row, ["ui_status"]),
        }
        live_output.append(merged)
        terminal_output.append({field: merged.get(field, "") for field in TERMINAL_FIELDS})

    status = "OK"
    if live_output and all(clean(row.get("market_source_ready")).upper() != "YES" for row in live_output):
        status = "PARTIAL_OK"
    if not live_output:
        status = "BLOCKED_NO_TERMINAL_ROWS"

    write_csv(LIVE_OUT, live_output, LIVE_FIELDS)
    write_csv(TERMINAL_OUT, terminal_output, TERMINAL_FIELDS)

    diag_rows = [{
        "built_at": built_at,
        "status": status,
        "rows_live": len(live_output),
        "rows_terminal": len(terminal_output),
        "rows_with_live_price": sum(1 for row in live_output if clean(row.get("live_price"))),
        "rows_market_blocked": sum(1 for row in live_output if clean(row.get("market_source_ready")).upper() != "YES"),
        "execute_rows": sum(1 for row in live_output if clean(row.get("execution_action")).upper() == "EXECUTE"),
        "watch_rows": sum(1 for row in live_output if clean(row.get("execution_action")).upper() == "WATCH"),
        "pass_rows": sum(1 for row in live_output if clean(row.get("execution_action")).upper() == "PASS"),
    }]
    write_csv(DIAG, diag_rows, DIAG_FIELDS)

    print("=" * 90)
    print("EDGEIQ OWNED EXECUTION BOARDS V1")
    print("=" * 90)
    print("STATUS:", status)
    print("LIVE ROWS:", len(live_output))
    print("TERMINAL ROWS:", len(terminal_output))
    print("OUT:", LIVE_OUT)
    print("OUT:", TERMINAL_OUT)
    print("DIAG:", DIAG)


if __name__ == "__main__":
    main()


