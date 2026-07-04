from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "public" / "data"

MARKET_TAPE = DATA / "edgeiq_market_tape.csv"
LIVE = DATA / "edgeiq_execution_board_live.csv"
TERMINAL = DATA / "edgeiq_execution_board_terminal.csv"
TEMPORAL = DATA / "edgeiq_temporal_execution_intelligence_v1.csv"
ENVIRONMENT = DATA / "edgeiq_environment_classification_v1.csv"
RESULTS = DATA / "edgeiq_results_master.csv"

OUT_MICRO = DATA / "edgeiq_market_microstructure_v1.csv"
OUT_RANKINGS = DATA / "edgeiq_microstructure_rankings_v1.csv"

MICRO_COLUMNS = [
    "track",
    "race_no",
    "horse",
    "microstructure_type",
    "microstructure_confidence",
    "microstructure_risk_grade",
    "movement_velocity",
    "movement_stability",
    "reversal_flag",
    "exhaustion_flag",
    "recommended_execution_timing",
    "microstructure_reason",
    "microstructure_original_execution_action",
    "microstructure_adjusted_execution_action",
    "microstructure_applied",
]

RANKING_COLUMNS = [
    "ranking_type",
    "microstructure_type",
    "rows",
    "avg_confidence",
    "avg_velocity",
    "avg_stability",
    "risk_grade",
    "recommended_execution_timing",
    "reason",
]


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"[microstructure] missing {path.name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
        print(f"[microstructure] read {path.name}: {len(df)} rows")
        return df
    except pd.errors.EmptyDataError:
        print(f"[microstructure] empty {path.name}")
        return pd.DataFrame()
    except Exception as exc:
        print(f"[microstructure] warning: could not read {path.name}: {exc}")
        return pd.DataFrame()


def text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def upper(value) -> str:
    return text(value).upper()


def num(value, default=None):
    try:
        parsed = float(value)
    except Exception:
        return default
    return parsed if pd.notna(parsed) else default


def runner_key(df: pd.DataFrame) -> pd.Series:
    parts = []
    for col in ["event_id", "horse"]:
        if col in df.columns:
            parts.append(df[col].map(upper))
        else:
            parts.append(pd.Series([""] * len(df), index=df.index))
    return parts[0] + "|" + parts[1]


def full_key(df: pd.DataFrame) -> pd.Series:
    parts = []
    for col in ["track", "race_no", "horse"]:
        if col in df.columns:
            parts.append(df[col].map(upper))
        else:
            parts.append(pd.Series([""] * len(df), index=df.index))
    return parts[0] + "|" + parts[1] + "|" + parts[2]


def coalesce(row: pd.Series, cols: list[str]) -> str:
    for col in cols:
        if col in row.index and text(row.get(col)):
            return text(row.get(col))
    return ""


def parse_flucs(value) -> list[float]:
    raw = text(value)
    if not raw:
        return []
    cleaned = raw.replace("[", "").replace("]", "").replace("\"", "").replace("'", "")
    values = []
    for part in cleaned.split(","):
        parsed = num(part)
        if parsed is not None and parsed > 0:
            values.append(parsed)
    return values


def merge_runner(live: pd.DataFrame, extra: pd.DataFrame, cols: list[str], suffix: str) -> pd.DataFrame:
    if live.empty or extra.empty:
        return live
    if not {"track", "race_no", "horse"}.issubset(live.columns) or not {"track", "race_no", "horse"}.issubset(extra.columns):
        return live
    available = [col for col in cols if col in extra.columns]
    if not available:
        return live
    left = live.copy()
    right = extra.copy()
    left["_micro_key"] = full_key(left)
    right["_micro_key"] = full_key(right)
    right = right[["_micro_key"] + available].drop_duplicates("_micro_key", keep="last")
    merged = left.merge(right, on="_micro_key", how="left", suffixes=("", suffix))
    for col in available:
        extra_col = f"{col}{suffix}"
        if extra_col in merged.columns:
            if col in merged.columns:
                current = merged[col].map(text)
                merged[col] = merged[col].where(current != "", merged[extra_col])
                merged[col] = merged[col].fillna(merged[extra_col])
            else:
                merged[col] = merged[extra_col]
            merged = merged.drop(columns=[extra_col])
    return merged.drop(columns=["_micro_key"], errors="ignore")


def latest_tape_by_runner(tape: pd.DataFrame) -> pd.DataFrame:
    if tape.empty:
        return tape
    out = tape.copy()
    out["_runner_key"] = runner_key(out)
    out["_timestamp"] = pd.to_datetime(out.get("timestamp"), errors="coerce")
    return out.sort_values("_timestamp").drop_duplicates("_runner_key", keep="last").drop(columns=["_runner_key", "_timestamp"], errors="ignore")


def movement_stats(row: pd.Series) -> dict:
    current = num(coalesce(row, ["sportsbet_price", "market_price", "current_price"]), None)
    flucs = parse_flucs(row.get("recent_odds_fluctuations"))
    if current is not None:
        prices = flucs + [current]
    else:
        prices = flucs
    prices = [p for p in prices if p and p > 0]

    if len(prices) < 2:
        return {
            "first": current,
            "last": current,
            "move_pct": 0.0,
            "velocity": 0.0,
            "stability": 100.0 if current else 0.0,
            "reversals": 0,
            "range_pct": 0.0,
            "history_count": len(prices),
        }

    first = prices[0]
    last = prices[-1]
    move_pct = ((first - last) / first) * 100.0 if first else 0.0
    steps = []
    for prev, nxt in zip(prices, prices[1:]):
        steps.append(nxt - prev)
    signs = [1 if step > 0 else -1 if step < 0 else 0 for step in steps]
    nonzero = [s for s in signs if s != 0]
    reversals = sum(1 for a, b in zip(nonzero, nonzero[1:]) if a != b)
    price_range = max(prices) - min(prices)
    range_pct = (price_range / first) * 100.0 if first else 0.0
    velocity = abs(move_pct) / max(1, len(prices) - 1)
    stability = max(0.0, 100.0 - (range_pct * 2.0) - (reversals * 10.0))
    return {
        "first": first,
        "last": last,
        "move_pct": move_pct,
        "velocity": velocity,
        "stability": stability,
        "reversals": reversals,
        "range_pct": range_pct,
        "history_count": len(prices),
    }


def classify(row: pd.Series) -> dict:
    stats = movement_stats(row)
    move = stats["move_pct"]
    velocity = stats["velocity"]
    stability = stats["stability"]
    reversals = stats["reversals"]
    range_pct = stats["range_pct"]
    history_count = stats["history_count"]

    environment = upper(coalesce(row, ["environment_type"]))
    timing_env = upper(coalesce(row, ["timing_environment"]))
    timing_rec = upper(coalesce(row, ["recommended_wait_or_execute"]))
    risk = upper(coalesce(row, ["suppression_risk_grade", "environment_risk_grade"]))
    confidence = upper(coalesce(row, ["calibrated_confidence_label", "confidence_band_v1", "confidence"]))
    action = upper(coalesce(row, ["final_execution_state", "execution_action"]))
    protected = environment == "PROTECTED_EDGE" or "PROTECTED" in timing_rec

    reasons = []
    if history_count < 2:
        micro_type = "UNKNOWN"
        risk_grade = "AMBER"
        recommendation = "WAIT_FOR_MORE_TAPE"
        reasons.append("insufficient movement history")
    elif range_pct < 2 and abs(move) < 2:
        micro_type = "DEAD_MARKET"
        risk_grade = "AMBER"
        recommendation = "WAIT_FOR_MARKET"
        reasons.append("limited price movement")
    elif reversals >= 3 or range_pct >= 40:
        micro_type = "VOLATILITY_CLUSTER"
        risk_grade = "RED"
        recommendation = "WAIT_FOR_STABILITY"
        reasons.append("clustered volatility/reversals")
    elif reversals >= 2:
        micro_type = "REVERSAL"
        risk_grade = "AMBER"
        recommendation = "MONITOR_REVERSAL"
        reasons.append("price reversed multiple times")
    elif move >= 20 and velocity >= 3:
        if risk in {"KILL", "SUPPRESS"} or confidence in {"VERY_LOW", "LOW"}:
            micro_type = "PUBLIC_STEAM"
            risk_grade = "RED"
            recommendation = "REDUCE_OR_WAIT"
            reasons.append("steam with low trust/risk pressure")
        elif stability >= 60:
            micro_type = "SHARP_STEAM"
            risk_grade = "GREEN"
            recommendation = "EXECUTE_ON_CONFIRMATION"
            reasons.append("controlled shortening with stable tape")
        else:
            micro_type = "FALSE_STEAM"
            risk_grade = "RED"
            recommendation = "WAIT_FOR_STABILITY"
            reasons.append("fast shortening with unstable tape")
    elif move >= 5:
        micro_type = "CONTROLLED_FIRMING" if stability >= 60 else "FALSE_STEAM"
        risk_grade = "GREEN" if stability >= 60 else "AMBER"
        recommendation = "EXECUTE_ON_CONFIRMATION" if stability >= 60 else "MONITOR_STEAM"
        reasons.append("moderate firming")
    elif move <= -25:
        if protected:
            micro_type = "VALUE_DRIFT"
            risk_grade = "AMBER"
            recommendation = "PROTECTED_EDGE_WINDOW"
            reasons.append("large drift but protected context")
        else:
            micro_type = "PANIC_DRIFT"
            risk_grade = "RED"
            recommendation = "SUPPRESS_OR_WAIT"
            reasons.append("large drift without protected context")
    elif move <= -5:
        micro_type = "VALUE_DRIFT" if protected or environment == "OVERREACTION" else "PANIC_DRIFT"
        risk_grade = "AMBER" if micro_type == "VALUE_DRIFT" else "RED"
        recommendation = "MONITOR_VALUE_DRIFT" if micro_type == "VALUE_DRIFT" else "SUPPRESS_OR_WAIT"
        reasons.append("drifting price")
    else:
        micro_type = "DEAD_MARKET"
        risk_grade = "AMBER"
        recommendation = "WAIT_FOR_MARKET"
        reasons.append("no decisive movement")

    if "CHAOTIC" in timing_env or "PUBLIC_OVERREACTION" in timing_env:
        if micro_type in {"SHARP_STEAM", "CONTROLLED_FIRMING"}:
            micro_type = "PUBLIC_STEAM"
        risk_grade = "RED" if risk_grade != "GREEN" else "AMBER"
        reasons.append("dangerous timing environment")

    reversal_flag = reversals > 0
    exhaustion_flag = False
    if history_count >= 4:
        recent = parse_flucs(row.get("recent_odds_fluctuations"))[-3:]
        if len(recent) >= 3:
            recent_move = abs(recent[-1] - recent[0]) / recent[0] * 100.0 if recent[0] else 0.0
            exhaustion_flag = abs(move) >= 10 and recent_move < 2
            if exhaustion_flag:
                reasons.append("movement exhaustion")

    adjusted_action = action
    if micro_type in {"FALSE_STEAM", "PUBLIC_STEAM", "VOLATILITY_CLUSTER"} and action in {"MAX_BET", "PRIORITY_EXECUTE", "EXECUTE", "REDUCED_EXECUTE", "BET"}:
        adjusted_action = "WATCH"
    if micro_type == "PANIC_DRIFT" and not protected and action in {"MAX_BET", "PRIORITY_EXECUTE", "EXECUTE", "REDUCED_EXECUTE", "BET", "WATCH"}:
        adjusted_action = "SUPPRESS"
    if micro_type in {"SHARP_STEAM", "CONTROLLED_FIRMING"} and action in {"SUPPRESS", "PASS"} and risk not in {"KILL", "SUPPRESS"}:
        adjusted_action = "WATCH"

    confidence_score = 35 + min(35, abs(move)) + min(20, history_count * 2) + (10 if stability >= 60 else 0)
    confidence_score = max(20, min(95, confidence_score))

    return {
        "microstructure_type": micro_type,
        "microstructure_confidence": round(confidence_score, 2),
        "microstructure_risk_grade": risk_grade,
        "movement_velocity": round(velocity, 4),
        "movement_stability": round(stability, 2),
        "reversal_flag": reversal_flag,
        "exhaustion_flag": exhaustion_flag,
        "recommended_execution_timing": recommendation,
        "microstructure_reason": " | ".join(reasons),
        "microstructure_original_execution_action": action,
        "microstructure_adjusted_execution_action": adjusted_action,
        "microstructure_applied": adjusted_action != action,
    }


def build_microstructure(live: pd.DataFrame, tape: pd.DataFrame, temporal: pd.DataFrame, environment: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    live = merge_runner(live, environment, ["environment_type", "environment_risk_grade"], "_env")
    tape_latest = latest_tape_by_runner(tape)
    if not tape_latest.empty and {"event_id", "horse"}.issubset(live.columns):
        live = live.copy()
        live["_runner_key"] = runner_key(live)
        tape_latest["_runner_key"] = runner_key(tape_latest)
        cols = ["_runner_key", "recent_odds_fluctuations", "sportsbet_price", "timestamp"]
        tape_latest = tape_latest[[c for c in cols if c in tape_latest.columns]].drop_duplicates("_runner_key", keep="last")
        live = live.merge(tape_latest, on="_runner_key", how="left", suffixes=("", "_tape"))
        for col in ["recent_odds_fluctuations", "sportsbet_price", "timestamp"]:
            extra = f"{col}_tape"
            if extra in live.columns:
                current = live[col].map(text) if col in live.columns else pd.Series([""] * len(live), index=live.index)
                live[col] = live[col].where(current != "", live[extra]) if col in live.columns else live[extra]
                live = live.drop(columns=[extra])
        live = live.drop(columns=["_runner_key"], errors="ignore")

    if temporal is not None and not temporal.empty and "timing_window" in live.columns:
        timing_info = temporal[["timing_window", "timing_environment", "recommended_wait_or_execute"]].drop_duplicates("timing_window", keep="last")
        live = live.merge(timing_info, on="timing_window", how="left", suffixes=("", "_timing_micro"))
        for col in ["timing_environment", "recommended_wait_or_execute"]:
            extra = f"{col}_timing_micro"
            if extra in live.columns:
                current = live[col].map(text) if col in live.columns else pd.Series([""] * len(live), index=live.index)
                live[col] = live[col].where(current != "", live[extra]) if col in live.columns else live[extra]
                live = live.drop(columns=[extra])

    rows = []
    output = live.copy()
    for idx, row in output.iterrows():
        classification = classify(row)
        for col, value in classification.items():
            output.at[idx, col] = value
        rows.append({
            "track": row.get("track", ""),
            "race_no": row.get("race_no", ""),
            "horse": row.get("horse", ""),
            **classification,
        })

    return output, pd.DataFrame(rows, columns=MICRO_COLUMNS)


def make_rankings(micro: pd.DataFrame) -> pd.DataFrame:
    if micro.empty:
        return pd.DataFrame(columns=RANKING_COLUMNS)
    rows = []
    for micro_type, group in micro.groupby("microstructure_type", dropna=True):
        risk = group["microstructure_risk_grade"].mode().iloc[0] if len(group["microstructure_risk_grade"].mode()) else ""
        timing = group["recommended_execution_timing"].mode().iloc[0] if len(group["recommended_execution_timing"].mode()) else ""
        rows.append({
            "ranking_type": "MICROSTRUCTURE_SUMMARY",
            "microstructure_type": micro_type,
            "rows": len(group),
            "avg_confidence": round(pd.to_numeric(group["microstructure_confidence"], errors="coerce").mean(), 2),
            "avg_velocity": round(pd.to_numeric(group["movement_velocity"], errors="coerce").mean(), 4),
            "avg_stability": round(pd.to_numeric(group["movement_stability"], errors="coerce").mean(), 2),
            "risk_grade": risk,
            "recommended_execution_timing": timing,
            "reason": "Live movement quality summary",
        })

    ranking = pd.DataFrame(rows, columns=RANKING_COLUMNS)
    risk_score = {"GREEN": 0, "AMBER": 1, "RED": 2}
    ranking["_risk"] = ranking["risk_grade"].map(lambda v: risk_score.get(upper(v), 1))
    strongest = ranking.sort_values(["avg_stability", "avg_confidence"], ascending=[False, False]).head(1)
    dangerous = ranking.sort_values(["_risk", "avg_velocity"], ascending=[False, False]).head(1)
    timing = ranking.sort_values(["_risk", "avg_stability"], ascending=[True, False]).head(1)
    extra = []
    if len(strongest):
        row = strongest.iloc[0].copy()
        row["ranking_type"] = "STRONGEST_MOVEMENT_TYPE"
        row["reason"] = "Highest current movement stability/confidence"
        extra.append(row)
    if len(dangerous):
        row = dangerous.iloc[0].copy()
        row["ranking_type"] = "MOST_DANGEROUS_MOVEMENT_TYPE"
        row["reason"] = "Highest current movement risk"
        extra.append(row)
    if len(timing):
        row = timing.iloc[0].copy()
        row["ranking_type"] = "BEST_EXECUTION_TIMING_SIGNAL"
        row["reason"] = "Best current timing signal from microstructure"
        extra.append(row)
    if extra:
        ranking = pd.concat([ranking, pd.DataFrame(extra)], ignore_index=True)
    return ranking.drop(columns=["_risk"], errors="ignore")


def append_micro_to_terminal(terminal: pd.DataFrame, micro: pd.DataFrame) -> pd.DataFrame:
    if terminal.empty or micro.empty:
        return terminal
    left = terminal.copy()
    right = micro.copy()
    left["_key"] = full_key(left)
    right["_key"] = full_key(right)
    cols = [col for col in MICRO_COLUMNS if col not in {"track", "race_no", "horse"}]
    right = right[["_key"] + cols].drop_duplicates("_key", keep="last")
    merged = left.merge(right, on="_key", how="left", suffixes=("", "_micro"))
    for col in cols:
        extra = f"{col}_micro"
        if extra in merged.columns:
            current = merged[col].map(text) if col in merged.columns else pd.Series([""] * len(merged), index=merged.index)
            merged[col] = merged[col].where(current != "", merged[extra]) if col in merged.columns else merged[extra]
            merged = merged.drop(columns=[extra])
    return merged.drop(columns=["_key"], errors="ignore")


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    tape = read_csv(MARKET_TAPE)
    live = read_csv(LIVE)
    temporal = read_csv(TEMPORAL)
    environment = read_csv(ENVIRONMENT)
    results = read_csv(RESULTS)

    if live.empty:
        pd.DataFrame(columns=MICRO_COLUMNS).to_csv(OUT_MICRO, index=False)
        pd.DataFrame(columns=RANKING_COLUMNS).to_csv(OUT_RANKINGS, index=False)
        print("[microstructure] no live rows; wrote empty outputs")
        return

    live_out, micro = build_microstructure(live, tape, temporal, environment)
    rankings = make_rankings(micro)

    live_out.to_csv(LIVE, index=False)
    if TERMINAL.exists():
        terminal = read_csv(TERMINAL)
        append_micro_to_terminal(terminal, micro).to_csv(TERMINAL, index=False)
    else:
        live_out.to_csv(TERMINAL, index=False)
    micro.to_csv(OUT_MICRO, index=False)
    rankings.to_csv(OUT_RANKINGS, index=False)

    counts = micro["microstructure_type"].value_counts().to_dict() if not micro.empty else {}
    dominant = micro["microstructure_type"].mode().iloc[0] if not micro.empty and len(micro["microstructure_type"].mode()) else "NONE"
    highest_risk = rankings[rankings["ranking_type"] == "MOST_DANGEROUS_MOVEMENT_TYPE"].head(1)

    print("[microstructure] rows processed:", len(micro))
    print("[microstructure] movement types found:", counts)
    print("[microstructure] dominant microstructure:", dominant)
    print("[microstructure] highest risk movement:", highest_risk.iloc[0].to_dict() if len(highest_risk) else "none")
    print("[microstructure] results rows read:", len(results))


if __name__ == "__main__":
    main()
