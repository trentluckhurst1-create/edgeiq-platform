from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "public" / "data"

MARKET_TAPE = DATA / "edgeiq_market_tape.csv"
LIVE = DATA / "edgeiq_execution_board_live.csv"
TERMINAL = DATA / "edgeiq_execution_board_terminal.csv"
ENVIRONMENT = DATA / "edgeiq_environment_classification_v1.csv"
TEMPORAL = DATA / "edgeiq_temporal_execution_intelligence_v1.csv"
MICROSTRUCTURE = DATA / "edgeiq_market_microstructure_v1.csv"
RESULTS = DATA / "edgeiq_results_master.csv"

OUT_TRANSITIONS = DATA / "edgeiq_market_state_transitions_v1.csv"
OUT_RANKINGS = DATA / "edgeiq_market_transition_rankings_v1.csv"

TRANSITION_COLUMNS = [
    "track",
    "race_no",
    "horse",
    "previous_state",
    "current_state",
    "transition_type",
    "transition_direction",
    "transition_risk_grade",
    "transition_confidence",
    "execution_window_status",
    "transition_reason",
    "transition_original_execution_action",
    "transition_adjusted_execution_action",
    "transition_applied",
]

RANKING_COLUMNS = [
    "ranking_type",
    "transition_type",
    "rows",
    "avg_confidence",
    "transition_risk_grade",
    "execution_window_status",
    "reason",
]


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"[transitions] missing {path.name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
        print(f"[transitions] read {path.name}: {len(df)} rows")
        return df
    except pd.errors.EmptyDataError:
        print(f"[transitions] empty {path.name}")
        return pd.DataFrame()
    except Exception as exc:
        print(f"[transitions] warning: could not read {path.name}: {exc}")
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
    prices = []
    for part in cleaned.split(","):
        parsed = num(part)
        if parsed is not None and parsed > 0:
            prices.append(parsed)
    return prices


def prior_state_from_prices(prices: list[float]) -> str:
    if len(prices) < 3:
        return "UNKNOWN"
    midpoint = max(2, len(prices) // 2)
    early = prices[:midpoint]
    if len(early) < 2:
        return "UNKNOWN"
    first = early[0]
    last = early[-1]
    move_pct = ((first - last) / first) * 100.0 if first else 0.0
    range_pct = ((max(early) - min(early)) / first) * 100.0 if first else 0.0
    signs = []
    for prev, nxt in zip(early, early[1:]):
        step = nxt - prev
        signs.append(1 if step > 0 else -1 if step < 0 else 0)
    nonzero = [s for s in signs if s]
    reversals = sum(1 for a, b in zip(nonzero, nonzero[1:]) if a != b)

    if range_pct >= 25 or reversals >= 2:
        return "VOLATILITY_CLUSTER"
    if move_pct >= 8:
        return "CONTROLLED_FIRMING"
    if move_pct <= -8:
        return "PANIC_DRIFT"
    if range_pct < 3:
        return "STABLE"
    return "NEUTRAL"


def merge_by_full_key(live: pd.DataFrame, extra: pd.DataFrame, cols: list[str], suffix: str) -> pd.DataFrame:
    if live.empty or extra.empty or not {"track", "race_no", "horse"}.issubset(live.columns) or not {"track", "race_no", "horse"}.issubset(extra.columns):
        return live
    available = [col for col in cols if col in extra.columns]
    if not available:
        return live
    left = live.copy()
    right = extra.copy()
    left["_transition_key"] = full_key(left)
    right["_transition_key"] = full_key(right)
    right = right[["_transition_key"] + available].drop_duplicates("_transition_key", keep="last")
    merged = left.merge(right, on="_transition_key", how="left", suffixes=("", suffix))
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
    return merged.drop(columns=["_transition_key"], errors="ignore")


def attach_prior_state(live: pd.DataFrame, tape: pd.DataFrame) -> pd.DataFrame:
    out = live.copy()
    if tape.empty or not {"event_id", "horse"}.issubset(out.columns):
        out["previous_state"] = "UNKNOWN"
        return out

    latest = tape.copy()
    latest["_runner_key"] = runner_key(latest)
    latest["_timestamp"] = pd.to_datetime(latest.get("timestamp"), errors="coerce")
    latest = latest.sort_values("_timestamp").drop_duplicates("_runner_key", keep="last")
    latest["previous_state"] = latest.get("recent_odds_fluctuations", "").map(lambda v: prior_state_from_prices(parse_flucs(v)))
    latest = latest[["_runner_key", "previous_state"]]
    out["_runner_key"] = runner_key(out)
    out = out.merge(latest, on="_runner_key", how="left", suffixes=("", "_prior"))
    if "previous_state_prior" in out.columns:
        current = out["previous_state"].map(text) if "previous_state" in out.columns else pd.Series([""] * len(out), index=out.index)
        out["previous_state"] = out["previous_state"].where(current != "", out["previous_state_prior"]) if "previous_state" in out.columns else out["previous_state_prior"]
        out = out.drop(columns=["previous_state_prior"])
    if "previous_state" not in out.columns:
        out["previous_state"] = "UNKNOWN"
    out["previous_state"] = out["previous_state"].fillna("UNKNOWN")
    return out.drop(columns=["_runner_key"], errors="ignore")


def state_score(state: str) -> int:
    state = upper(state)
    if state in {"SHARP", "CLEAN", "CONTROLLED_FIRMING", "SHARP_STEAM", "PROTECTED_EDGE", "LIQUIDITY_STABLE"}:
        return 2
    if state in {"STABLE", "NEUTRAL", "DEAD_MARKET", "UNKNOWN"}:
        return 1
    if state in {"PUBLIC_TRAP", "PUBLIC_STEAM", "OVERREACTION", "PANIC_DRIFT", "FALSE_STEAM", "VOLATILE"}:
        return 0
    if state in {"CHAOTIC", "VOLATILITY_CLUSTER", "TRAP_WINDOW", "CHAOTIC_LATE"}:
        return -1
    return 1


def classify_transition(row: pd.Series) -> dict:
    previous = upper(row.get("previous_state")) or "UNKNOWN"
    current_micro = upper(coalesce(row, ["microstructure_type"]))
    current_env = upper(coalesce(row, ["environment_type"]))
    current_timing = upper(coalesce(row, ["timing_environment"]))
    current = current_micro or current_env or current_timing or "UNKNOWN"
    action = upper(coalesce(row, ["final_execution_state", "execution_action"]))
    timing_rec = upper(coalesce(row, ["recommended_execution_timing", "recommended_wait_or_execute"]))
    micro_risk = upper(coalesce(row, ["microstructure_risk_grade", "environment_risk_grade", "timing_risk_grade"]))

    prev_score = state_score(previous)
    curr_score = min(state_score(current), state_score(current_env or current), state_score(current_timing or current))
    reasons = []
    if previous == "UNKNOWN":
        reasons.append("prior state inferred weakly from tape")
    if current_micro:
        reasons.append(f"current microstructure {current_micro}")
    if current_env:
        reasons.append(f"environment {current_env}")
    if current_timing:
        reasons.append(f"timing {current_timing}")

    if curr_score > prev_score:
        direction = "IMPROVING"
    elif curr_score < prev_score:
        direction = "DETERIORATING"
    else:
        direction = "UNCHANGED"

    if previous == "STABLE" and current_env == "CHAOTIC":
        transition_type = "STABLE_TO_CHAOTIC"
    elif previous in {"CHAOTIC", "VOLATILITY_CLUSTER"} and current in {"STABLE", "CONTROLLED_FIRMING", "SHARP_STEAM"}:
        transition_type = "CHAOTIC_TO_STABLE"
    elif previous == "VOLATILITY_CLUSTER" and current == "CONTROLLED_FIRMING":
        transition_type = "VOLATILITY_CLUSTER_TO_CONTROLLED_FIRMING"
    elif previous == "PUBLIC_TRAP" and current_env == "SHARP":
        transition_type = "PUBLIC_TRAP_TO_SHARP"
    elif previous == "SHARP" and current_env == "OVERREACTION":
        transition_type = "SHARP_TO_OVERREACTION"
    elif previous == "CLEAN" and current_timing == "TRAP_WINDOW":
        transition_type = "CLEAN_TO_TRAP_WINDOW"
    elif timing_rec in {"EXECUTE_ON_CONFIRMATION", "EXECUTE_NOW", "PROTECTED_EDGE_WINDOW"}:
        transition_type = "WAIT_FOR_STABILITY_TO_EXECUTE_WINDOW"
    elif timing_rec in {"WAIT_FOR_STABILITY", "SUPPRESS_OR_WAIT", "AVOID_LATE_CHAOS"}:
        transition_type = "EXECUTE_WINDOW_TO_AVOID"
    else:
        transition_type = f"{previous}_TO_{current}"

    if direction == "IMPROVING":
        risk_grade = "GREEN" if micro_risk != "RED" else "AMBER"
        status = "OPEN" if timing_rec in {"EXECUTE_ON_CONFIRMATION", "EXECUTE_NOW", "PROTECTED_EDGE_WINDOW"} else "WAIT"
    elif direction == "DETERIORATING":
        risk_grade = "RED"
        status = "AVOID" if "AVOID" in transition_type or timing_rec in {"SUPPRESS_OR_WAIT", "AVOID_LATE_CHAOS"} else "CLOSING"
    else:
        risk_grade = micro_risk or "AMBER"
        status = "CLOSED" if risk_grade == "RED" else "WAIT"

    if current in {"VOLATILITY_CLUSTER", "PUBLIC_STEAM", "FALSE_STEAM", "PANIC_DRIFT"}:
        risk_grade = "RED"
        status = "AVOID" if current == "PANIC_DRIFT" else "CLOSING"

    adjusted_action = action
    if direction == "DETERIORATING" and action in {"MAX_BET", "PRIORITY_EXECUTE", "EXECUTE", "REDUCED_EXECUTE", "BET"}:
        adjusted_action = "WATCH"
    if status == "AVOID" and action in {"MAX_BET", "PRIORITY_EXECUTE", "EXECUTE", "REDUCED_EXECUTE", "BET", "WATCH"}:
        adjusted_action = "SUPPRESS"
    if direction == "IMPROVING" and status == "OPEN" and action in {"SUPPRESS", "PASS"} and micro_risk != "RED":
        adjusted_action = "WATCH"

    confidence = 45
    if previous != "UNKNOWN":
        confidence += 20
    if current_micro:
        confidence += 15
    if current_env:
        confidence += 10
    if current_timing:
        confidence += 10
    confidence = max(20, min(95, confidence))

    return {
        "previous_state": previous,
        "current_state": current,
        "transition_type": transition_type,
        "transition_direction": direction,
        "transition_risk_grade": risk_grade,
        "transition_confidence": confidence,
        "execution_window_status": status,
        "transition_reason": " | ".join(reasons) if reasons else "state transition unavailable",
        "transition_original_execution_action": action,
        "transition_adjusted_execution_action": adjusted_action,
        "transition_applied": adjusted_action != action,
    }


def build_transitions(live: pd.DataFrame, tape: pd.DataFrame, environment: pd.DataFrame, temporal: pd.DataFrame, micro: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    output = live.copy()
    output = merge_by_full_key(output, environment, ["environment_type", "environment_risk_grade"], "_env")
    output = merge_by_full_key(output, micro, ["microstructure_type", "microstructure_risk_grade", "recommended_execution_timing"], "_micro")
    output = attach_prior_state(output, tape)

    rows = []
    for idx, row in output.iterrows():
        classification = classify_transition(row)
        for col, value in classification.items():
            output.at[idx, col] = value
        rows.append({
            "track": row.get("track", ""),
            "race_no": row.get("race_no", ""),
            "horse": row.get("horse", ""),
            **classification,
        })
    return output, pd.DataFrame(rows, columns=TRANSITION_COLUMNS)


def make_rankings(transitions: pd.DataFrame) -> pd.DataFrame:
    if transitions.empty:
        return pd.DataFrame(columns=RANKING_COLUMNS)
    rows = []
    for transition_type, group in transitions.groupby("transition_type", dropna=True):
        risk = group["transition_risk_grade"].mode().iloc[0] if len(group["transition_risk_grade"].mode()) else ""
        status = group["execution_window_status"].mode().iloc[0] if len(group["execution_window_status"].mode()) else ""
        rows.append({
            "ranking_type": "TRANSITION_SUMMARY",
            "transition_type": transition_type,
            "rows": len(group),
            "avg_confidence": round(pd.to_numeric(group["transition_confidence"], errors="coerce").mean(), 2),
            "transition_risk_grade": risk,
            "execution_window_status": status,
            "reason": "Live market state transition summary",
        })
    ranking = pd.DataFrame(rows, columns=RANKING_COLUMNS)
    risk_score = {"GREEN": 0, "AMBER": 1, "RED": 2}
    status_score = {"OPEN": 0, "WAIT": 1, "CLOSING": 2, "CLOSED": 3, "AVOID": 4}
    ranking["_risk"] = ranking["transition_risk_grade"].map(lambda v: risk_score.get(upper(v), 1))
    ranking["_status"] = ranking["execution_window_status"].map(lambda v: status_score.get(upper(v), 1))
    extra = []
    common = ranking.sort_values("rows", ascending=False).head(1)
    safest = ranking.sort_values(["_risk", "_status", "avg_confidence"], ascending=[True, True, False]).head(1)
    dangerous = ranking.sort_values(["_risk", "_status", "rows"], ascending=[False, False, False]).head(1)
    open_rows = ranking[ranking["execution_window_status"] == "OPEN"]
    if len(common):
        row = common.iloc[0].copy()
        row["ranking_type"] = "MOST_COMMON_TRANSITION"
        row["reason"] = "Most common current transition"
        extra.append(row)
    if len(safest):
        row = safest.iloc[0].copy()
        row["ranking_type"] = "SAFEST_TRANSITION"
        row["reason"] = "Lowest transition risk"
        extra.append(row)
    if len(dangerous):
        row = dangerous.iloc[0].copy()
        row["ranking_type"] = "MOST_DANGEROUS_TRANSITION"
        row["reason"] = "Highest transition risk"
        extra.append(row)
    if len(open_rows):
        row = open_rows.sort_values("avg_confidence", ascending=False).iloc[0].copy()
        row["ranking_type"] = "EXECUTION_WINDOW_OPEN"
        row["reason"] = "Open execution window detected"
        extra.append(row)
    if extra:
        ranking = pd.concat([ranking, pd.DataFrame(extra)], ignore_index=True)
    return ranking.drop(columns=["_risk", "_status"], errors="ignore")


def append_to_terminal(terminal: pd.DataFrame, transitions: pd.DataFrame) -> pd.DataFrame:
    if terminal.empty or transitions.empty:
        return terminal
    left = terminal.copy()
    right = transitions.copy()
    left["_key"] = full_key(left)
    right["_key"] = full_key(right)
    cols = [col for col in TRANSITION_COLUMNS if col not in {"track", "race_no", "horse"}]
    right = right[["_key"] + cols].drop_duplicates("_key", keep="last")
    merged = left.merge(right, on="_key", how="left", suffixes=("", "_transition"))
    for col in cols:
        extra = f"{col}_transition"
        if extra in merged.columns:
            current = merged[col].map(text) if col in merged.columns else pd.Series([""] * len(merged), index=merged.index)
            merged[col] = merged[col].where(current != "", merged[extra]) if col in merged.columns else merged[extra]
            merged = merged.drop(columns=[extra])
    return merged.drop(columns=["_key"], errors="ignore")


def preserve_live_uncertainty_fields(terminal: pd.DataFrame, live: pd.DataFrame) -> pd.DataFrame:
    if terminal.empty or live.empty:
        return terminal

    cols = [
        col for col in live.columns
        if (
            "uncertainty" in col
            or "first_starter" in col
            or "adaptive_" in col
            or "trainer_jockey" in col
            or "form_depth" in col
            or "market_confirmation" in col
            or "suitability_score" in col
            or col in {
                "trainer_sample_size",
                "jockey_sample_size",
                "total_form_runs",
                "recent_official_runs",
                "last3_rating_avg",
                "last5_rating_avg",
                "rating_consistency_score",
                "exposed_ability_score",
                "ability_confidence_grade",
                "confirmed_price_support",
                "drift_rejection_flag",
                "chaotic_noise_flag",
                "volatility_discount",
                "first_starter_market_support",
            }
            or "debut_" in col
            or col in {
                "recommended_probability_shrinkage",
                "lightly_raced_engine_flag",
                "no_official_form_engine_flag",
                "trial_run_count",
                "jumpout_run_count",
            }
        )
    ]
    if not cols:
        return terminal

    left = terminal.copy()
    right = live.copy()
    left["_key"] = full_key(left)
    right["_key"] = full_key(right)
    right = right[["_key"] + cols].drop_duplicates("_key", keep="last")
    merged = left.merge(right, on="_key", how="left", suffixes=("", "_live"))

    for col in cols:
        extra = f"{col}_live"
        if extra in merged.columns:
            current = merged[col].map(text) if col in merged.columns else pd.Series([""] * len(merged), index=merged.index)
            merged[col] = merged[col].where(current != "", merged[extra]) if col in merged.columns else merged[extra]
            merged = merged.drop(columns=[extra])

    return merged.drop(columns=["_key"], errors="ignore")


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    tape = read_csv(MARKET_TAPE)
    live = read_csv(LIVE)
    environment = read_csv(ENVIRONMENT)
    temporal = read_csv(TEMPORAL)
    micro = read_csv(MICROSTRUCTURE)
    results = read_csv(RESULTS)

    if live.empty:
        pd.DataFrame(columns=TRANSITION_COLUMNS).to_csv(OUT_TRANSITIONS, index=False)
        pd.DataFrame(columns=RANKING_COLUMNS).to_csv(OUT_RANKINGS, index=False)
        print("[transitions] no live rows; wrote empty outputs")
        return

    live_out, transitions = build_transitions(live, tape, environment, temporal, micro)
    rankings = make_rankings(transitions)

    live_out.to_csv(LIVE, index=False)
    if TERMINAL.exists():
        terminal = read_csv(TERMINAL)
        terminal = append_to_terminal(terminal, transitions)
        terminal = preserve_live_uncertainty_fields(terminal, live_out)
        terminal.to_csv(TERMINAL, index=False)
    else:
        live_out.to_csv(TERMINAL, index=False)
    transitions.to_csv(OUT_TRANSITIONS, index=False)
    rankings.to_csv(OUT_RANKINGS, index=False)

    counts = transitions["transition_type"].value_counts().to_dict() if not transitions.empty else {}
    dominant = transitions["transition_type"].mode().iloc[0] if not transitions.empty and len(transitions["transition_type"].mode()) else "NONE"
    open_count = int((transitions["execution_window_status"] == "OPEN").sum()) if not transitions.empty else 0
    dangerous = rankings[rankings["ranking_type"] == "MOST_DANGEROUS_TRANSITION"].head(1)

    print("[transitions] rows processed:", len(transitions))
    print("[transitions] transitions detected:", counts)
    print("[transitions] dominant transition:", dominant)
    print("[transitions] execution windows open:", open_count)
    print("[transitions] most dangerous transition:", dangerous.iloc[0].to_dict() if len(dangerous) else "none")
    print("[transitions] temporal rows read:", len(temporal))
    print("[transitions] results rows read:", len(results))


if __name__ == "__main__":
    main()
