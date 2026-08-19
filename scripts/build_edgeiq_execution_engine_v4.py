from __future__ import annotations

import math
from datetime import datetime, timedelta
from pathlib import Path

from edgeiq_csv_utils import build_lookup, boolish, clean, first, merge_rows, num, read_csv, runner_key, write_csv


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

UNIVERSE = DATA / "edgeiq_vic_three_day_meeting_universe.csv"
TRUTH = DATA / "edgeiq_market_truth_engine_v3.csv"
SUPPRESSION = DATA / "edgeiq_execution_suppression_v2.csv"
CLV = DATA / "edgeiq_clv_memory.csv"
CLOCK = DATA / "edgeiq_race_clock_engine.csv"
TAPE = DATA / "edgeiq_market_tape_summary.csv"
THROTTLE = DATA / "edgeiq_portfolio_throttle_v1.csv"
CAPITAL = DATA / "edgeiq_capital_allocation_v1.csv"
OUT = DATA / "edgeiq_execution_engine_v4.csv"

FIELDS = [
    "built_at", "meeting_key", "race_key", "runner_key", "race_date", "track", "race_no", "horse", "horse_key", "live_price",
    "fair_price", "edge_pct", "truth_grade", "suppression_action", "execution_decision",
    "execution_score", "stake", "confidence", "clv_signal", "market_move_signal",
    "race_lifecycle", "reason",
]


def now_stamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def valid_date(row: dict[str, str]) -> bool:
    raw = clean(row.get("race_date"))
    if not raw:
        return True
    try:
        race_date = datetime.fromisoformat(raw[:10]).date()
    except ValueError:
        return True
    today = datetime.now().astimezone().date()
    return today <= race_date <= today + timedelta(days=2)


def race_key(row: dict[str, str]) -> str:
    return "|".join(runner_key(row).split("|")[:2])


def clean_track(value: object) -> str:
    return " ".join(clean(value).upper().replace("|", " ").replace("_", " ").split())


def meeting_key_value(race_date: object, track: object) -> str:
    return f"{clean(race_date)}_{clean_track(track)}"


def canonical_race_key(race_date: object, track: object, race_no_value: object) -> str:
    race_digits = "".join(ch for ch in clean(race_no_value) if ch.isdigit()) or "0"
    return f"{meeting_key_value(race_date, track)}_R{int(race_digits)}"


def canonical_runner_key(race_date: object, track: object, race_no_value: object, horse_key_value: object, horse: object) -> str:
    return f"{canonical_race_key(race_date, track, race_no_value)}_{clean(horse_key_value) or clean(horse)}"


def race_lookup(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        key = race_key(row)
        if key and key not in out:
            out[key] = row
    return out


def merge_race_rows(rows: list[dict[str, str]], races: list[list[dict[str, str]]]) -> list[dict[str, str]]:
    maps = [race_lookup(source) for source in races]
    out: list[dict[str, str]] = []
    for row in rows:
        merged = dict(row)
        key = race_key(row)
        for mapping in maps:
            extra = mapping.get(key)
            if not extra:
                continue
            for col, value in extra.items():
                if clean(value) and not clean(merged.get(col)):
                    merged[col] = value
                elif clean(value):
                    merged[f"{col}_race"] = value
        out.append(merged)
    return out


def price(row: dict[str, str]) -> float:
    return num(first(row, ["live_price", "ui_price", "sportsbet_price", "market_price", "fixed_win", "last_price"]))


def fair(row: dict[str, str]) -> float:
    return num(first(row, ["fair_price", "ui_fair_price", "rated_price", "model_price", "execution_fair"]))


def edge(row: dict[str, str], live: float, rated: float) -> float:
    supplied = num(first(row, ["edge_pct", "ui_edge_pct", "overlay_pct", "v3_edge_pct", "calibrated_edge_pct"]))
    if not math.isnan(supplied):
        return supplied
    if not math.isnan(live) and not math.isnan(rated) and live > 0 and rated > 0:
        return ((live / rated) - 1) * 100
    return math.nan


def clv_signal(row: dict[str, str]) -> str:
    profile = clean(first(row, ["runner_drift_profile", "steam_drift", "clv_signal"])).upper()
    if profile:
        return profile
    move = num(first(row, ["move_pct", "clv_achieved_pct"]))
    if math.isnan(move):
        return "UNKNOWN"
    if move <= -4:
        return "STEAM_POSITIVE"
    if move >= 7:
        return "DRIFT_NEGATIVE"
    return "STABLE"


def move_signal(row: dict[str, str]) -> str:
    signal = clean(first(row, ["steam_drift", "market_move_signal"])).upper()
    if signal:
        return signal
    move = num(first(row, ["move_pct"]))
    if math.isnan(move):
        return "NO_TAPE"
    if move <= -5:
        return "STEAM"
    if move >= 8:
        return "DRIFT"
    return "FLAT"


def base_stake(decision: str, score: int, edge_pct: float, row: dict[str, str]) -> str:
    supplied = num(first(row, ["allocated_stake", "recommended_stake", "stake", "throttled_stake"]))
    if not math.isnan(supplied) and supplied > 0 and decision in {"EXECUTE", "ALLOW", "REDUCE"}:
        return f"{supplied:.2f}"
    if decision == "EXECUTE":
        stake = 1.0 + max(0.0, min(edge_pct if not math.isnan(edge_pct) else 0.0, 20.0)) / 20
    elif decision == "ALLOW":
        stake = 0.50
    elif decision == "REDUCE":
        stake = 0.25
    else:
        stake = 0.0
    if score < 70:
        stake *= 0.5
    return f"{stake:.2f}"


def decision(row: dict[str, str]) -> tuple[str, int, str, str, str, float, float, float]:
    live = price(row)
    rated = fair(row)
    edge_pct = edge(row, live, rated)
    truth = clean(first(row, ["truth_grade"])).upper()
    suppression = clean(first(row, ["suppression_action"])).upper()
    lifecycle = clean(first(row, ["lifecycle_state", "race_state"])).upper()
    trust = num(first(row, ["execution_trust_score", "market_confidence", "confidence"]), 50)
    liquidity = clean(first(row, ["liquidity_grade"])).upper()
    clv = clv_signal(row)
    move = move_signal(row)
    reasons: list[str] = []
    score = 50

    if boolish(first(row, ["is_scratched", "scratch_status", "runner_status", "scratched"])):
        return "SCRATCHED", 0, "scratched_runner", clv, move, live, rated, edge_pct
    if math.isnan(live) or live <= 1:
        return "NO_PRICE", 0, "no_live_price", clv, move, live, rated, edge_pct
    if suppression in {"KILL", "SUPPRESS"}:
        return suppression, 0 if suppression == "KILL" else 15, f"suppression_override={suppression}", clv, move, live, rated, edge_pct

    if lifecycle in {"CLOSED", "RESULTED", "PHOTO", "INPLAY"}:
        score -= 35
        reasons.append(f"race_lifecycle={lifecycle}")
    elif lifecycle in {"OPEN", "NEXT_UP", "JUMPING"}:
        score += 15
    elif lifecycle == "PREOPEN":
        score += 5
    else:
        score -= 10
        reasons.append("race_clock_uncertain")

    if truth in {"A", "VALID", "VALIDATED", "TRUSTED", "OK"}:
        score += 15
    elif truth in {"REJECT", "INVALID", "FAKE", "QUESTIONABLE"}:
        score -= 30
        reasons.append(f"truth={truth}")

    if trust >= 75:
        score += 15
    elif trust >= 60:
        score += 7
    elif trust < 45:
        score -= 20
        reasons.append("low_execution_trust")

    if liquidity in {"ILLIQUID", "NO_MARKET", "THIN"}:
        score -= 20
        reasons.append(f"liquidity={liquidity}")

    if not math.isnan(edge_pct):
        if edge_pct >= 12:
            score += 18
        elif edge_pct >= 6:
            score += 9
        elif edge_pct < 0:
            score -= 22
            reasons.append("negative_edge")

    if clv in {"DRIFT_NEGATIVE"} or move == "DRIFT":
        score -= 14
        reasons.append("market_drift")
    elif clv in {"STEAM_POSITIVE"} or move == "STEAM":
        score += 7

    if suppression == "REDUCE":
        score -= 15
        reasons.append("suppression_reduce")
    elif suppression == "MONITOR":
        score -= 5
    elif suppression == "ALLOW":
        score += 10

    score = max(0, min(100, round(score)))
    if suppression == "REDUCE":
        final = "REDUCE"
    elif score >= 86 and lifecycle in {"OPEN", "NEXT_UP", "JUMPING"} and not math.isnan(edge_pct) and edge_pct >= 8:
        final = "EXECUTE"
    elif score >= 70:
        final = "ALLOW"
    elif score >= 50:
        final = "MONITOR"
    else:
        final = "SUPPRESS"
    return final, score, "|".join(reasons) or "all_execution_gates_clear", clv, move, live, rated, edge_pct


def main() -> None:
    base = [row for row in read_csv(UNIVERSE) if valid_date(row)]
    runner_merged = merge_rows(base, [
        read_csv(TRUTH),
        read_csv(SUPPRESSION),
        read_csv(CLV),
        read_csv(TAPE),
        read_csv(THROTTLE),
        read_csv(CAPITAL),
    ])
    rows = merge_race_rows(runner_merged, [read_csv(CLOCK)])

    out: list[dict[str, object]] = []
    built_at = now_stamp()
    for row in rows:
        final, score, reason, clv, move, live, rated, edge_pct = decision(row)
        out.append({
            "built_at": built_at,
            "race_date": first(row, ["race_date", "date"]),
            "track": first(row, ["track", "meeting"]),
            "race_no": first(row, ["race_no", "race_number"]),
            "horse": first(row, ["horse", "runner", "horse_name", "runner_name"]),
            "horse_key": first(row, ["horse_key"]) or runner_key(row).split("|")[-1],
            "live_price": "" if math.isnan(live) else f"{live:.2f}",
            "fair_price": "" if math.isnan(rated) else f"{rated:.2f}",
            "edge_pct": "" if math.isnan(edge_pct) else f"{edge_pct:.2f}",
            "truth_grade": first(row, ["truth_grade"]),
            "suppression_action": first(row, ["suppression_action"]),
            "execution_decision": final,
            "execution_score": score,
            "stake": base_stake(final, score, edge_pct, row),
            "confidence": first(row, ["market_confidence", "confidence", "execution_trust_score"]),
            "clv_signal": clv,
            "market_move_signal": move,
            "race_lifecycle": first(row, ["lifecycle_state", "race_state"]),
            "reason": reason,
        })
        out[-1]["meeting_key"] = meeting_key_value(out[-1]["race_date"], out[-1]["track"])
        out[-1]["race_key"] = canonical_race_key(out[-1]["race_date"], out[-1]["track"], out[-1]["race_no"])
        out[-1]["runner_key"] = canonical_runner_key(out[-1]["race_date"], out[-1]["track"], out[-1]["race_no"], out[-1]["horse_key"], out[-1]["horse"])

    write_csv(OUT, out, FIELDS)
    print("=" * 90)
    print("EDGEIQ EXECUTION ENGINE V4")
    print("=" * 90)
    print("ROWS:", len(out))
    for state in ["NO_PRICE", "SCRATCHED", "KILL", "SUPPRESS", "MONITOR", "REDUCE", "ALLOW", "EXECUTE"]:
        print(state, sum(1 for row in out if row["execution_decision"] == state))
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
