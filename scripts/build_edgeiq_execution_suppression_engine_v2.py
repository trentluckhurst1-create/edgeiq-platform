from __future__ import annotations

from datetime import datetime
from pathlib import Path

from edgeiq_csv_utils import boolish, first, merge_rows, num, read_csv, runner_key, write_csv


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUT = DATA / "edgeiq_execution_suppression_v2.csv"

EXECUTION = DATA / "edgeiq_execution_board_v3.csv"
TRUTH = DATA / "edgeiq_market_truth_engine_v3.csv"
MAP = DATA / "edgeiq_real_speed_map_positions.csv"
STATE = DATA / "edgeiq_race_state_engine.csv"

FIELDS = [
    "built_at", "track", "race_no", "horse", "horse_key", "suppression_action", "suppression_score",
    "execution_trust_score", "truth_grade", "liquidity_grade", "race_state", "suppression_reason",
]


def action_for(row: dict[str, str]) -> tuple[str, int, str]:
    reasons: list[str] = []
    score = 100
    truth = first(row, ["truth_grade"]).upper()
    liquidity = first(row, ["liquidity_grade"]).upper()
    race_state = first(row, ["race_state"]).upper()
    trust = num(first(row, ["execution_trust_score"]), 0)
    price = num(first(row, ["market_price", "ui_price", "live_price"]))
    edge = num(first(row, ["edge_pct", "v3_edge_pct", "ui_edge_pct"]), 0)
    barrier = num(first(row, ["barrier"]), 0)
    settling = first(row, ["settling_band"]).upper()

    if boolish(first(row, ["is_scratched", "scratch_status", "runner_status"])):
        return "KILL", 0, "scratched"
    if race_state in {"JUMPING", "INPLAY", "CLOSED", "RESULTED"}:
        return "KILL", 0, f"race_state={race_state}"
    if truth == "REJECT":
        score -= 55
        reasons.append("market_truth_reject")
    elif truth == "QUESTIONABLE":
        score -= 25
        reasons.append("questionable_market")
    if trust < 42:
        score -= 35
        reasons.append("low_execution_trust")
    elif trust < 62:
        score -= 18
        reasons.append("medium_execution_trust")
    if liquidity in {"ILLIQUID", "NO_MARKET"}:
        score -= 35
        reasons.append("liquidity_fail")
    elif liquidity == "THIN":
        score -= 16
        reasons.append("thin_liquidity")
    if first(row, ["fake_overlay_flag"]).upper() == "YES":
        score -= 32
        reasons.append("fake_overlay")
    if first(row, ["late_drift_risk"]).upper() == "HIGH":
        score -= 20
        reasons.append("late_drift")
    if price != price or price <= 1:
        score -= 45
        reasons.append("no_live_price")
    if edge >= 45 and price >= 25:
        score -= 28
        reasons.append("impossible_probability_edge")
    if barrier >= 12 and settling in {"PACE", "LEADER"}:
        score -= 12
        reasons.append("wide_speed_pressure")

    score = max(0, min(100, score))
    if score < 25:
        action = "KILL"
    elif score < 45:
        action = "SUPPRESS"
    elif score < 65:
        action = "REDUCE"
    elif score < 80:
        action = "MONITOR"
    else:
        action = "ALLOW"
    return action, score, "|".join(reasons) or "discipline_clear"


def main() -> None:
    base = read_csv(EXECUTION)
    rows = merge_rows(base, [read_csv(TRUTH), read_csv(MAP), read_csv(STATE)])
    out = []
    for row in rows:
        action, score, reason = action_for(row)
        out.append({
            "built_at": datetime.now().isoformat(timespec="seconds"),
            "track": first(row, ["track"]),
            "race_no": first(row, ["race_no", "race_number"]),
            "horse": first(row, ["horse", "runner", "horse_name"]),
            "horse_key": first(row, ["horse_key"]) or runner_key(row).split("|")[-1],
            "suppression_action": action,
            "suppression_score": score,
            "execution_trust_score": first(row, ["execution_trust_score"]),
            "truth_grade": first(row, ["truth_grade"]),
            "liquidity_grade": first(row, ["liquidity_grade"]),
            "race_state": first(row, ["race_state"]),
            "suppression_reason": reason,
        })
    write_csv(OUT, out, FIELDS)
    print("=" * 100)
    print("EDGEIQ EXECUTION SUPPRESSION ENGINE V2")
    print("=" * 100)
    print("ROWS:", len(out))
    for name in ["KILL", "SUPPRESS", "REDUCE", "MONITOR", "ALLOW"]:
        print(name, sum(1 for row in out if row["suppression_action"] == name))
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
