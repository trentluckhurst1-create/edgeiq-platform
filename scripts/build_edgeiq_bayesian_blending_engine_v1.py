from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "public" / "data"

LIVE = DATA / "edgeiq_execution_board_live.csv"
CALIBRATION = DATA / "edgeiq_probability_calibration_v1.csv"
SHRINKAGE = DATA / "edgeiq_probability_shrinkage_v1.csv"
REGIME = DATA / "edgeiq_market_regime_v2.csv"
POLICY = DATA / "edgeiq_policy_rankings_v1.csv"

OUT = DATA / "edgeiq_bayesian_blending_v1.csv"
LIVE_OUT = DATA / "edgeiq_execution_board_live.csv"
TERMINAL_OUT = DATA / "edgeiq_execution_board_terminal.csv"

TERMINAL_COLUMNS = [
    "timestamp",
    "track",
    "race_no",
    "race_time",
    "horse",
    "runner_number",
    "sportsbet_price",
    "rated_price",
    "adjusted_rated_price",
    "shrunk_fair_price",
    "blended_fair_price",
    "overlay_pct",
    "adjusted_overlay_pct",
    "shrunk_overlay_pct",
    "blended_overlay_pct",
    "overlay_realism_grade",
    "price_truth_adjustment_pct",
    "shrinkage_factor",
    "model_weight",
    "market_weight",
    "calibration_bucket",
    "blending_reason",
    "shrinkage_reason",
    "execution_action",
    "final_execution_state",
    "original_execution_state",
    "policy_original_execution_action",
    "price_truth_original_execution_action",
    "active_policy",
    "policy_decision",
    "policy_reason",
    "policy_stake_multiplier",
    "policy_risk_grade",
    "suppression_risk_grade",
    "suppression_recommendation",
    "suppression_intelligence_reason",
    "price_truth_reason",
    "overlay_tier",
    "final_action_v5_1",
    "cap_note_v5_1",
    "confidence_band_v1",
    "calibrated_confidence_label",
    "risk_flags",
    "market_mover",
    "recent_odds_fluctuations",
    "jockey",
    "trainer",
    "mobile_silk_image",
]


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"[bayesian_blending] missing {path.name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
        print(f"[bayesian_blending] read {path.name}: {len(df)} rows")
        return df
    except pd.errors.EmptyDataError:
        print(f"[bayesian_blending] empty {path.name}")
        return pd.DataFrame()
    except Exception as exc:
        print(f"[bayesian_blending] warning: could not read {path.name}: {exc}")
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


def make_key(df: pd.DataFrame) -> pd.Series:
    parts = []
    for col in ["track", "race_no", "horse"]:
        if col in df.columns:
            parts.append(df[col].map(upper))
        else:
            parts.append(pd.Series([""] * len(df), index=df.index))
    return parts[0] + "|" + parts[1] + "|" + parts[2]


def merge_by_runner(live: pd.DataFrame, extra: pd.DataFrame, cols: list[str], suffix: str) -> pd.DataFrame:
    if live.empty or extra.empty:
        return live
    if not {"track", "race_no", "horse"}.issubset(live.columns) or not {"track", "race_no", "horse"}.issubset(extra.columns):
        return live
    available = [c for c in cols if c in extra.columns]
    if not available:
        return live
    left = live.copy()
    right = extra.copy()
    left["_blend_key"] = make_key(left)
    right["_blend_key"] = make_key(right)
    right = right[["_blend_key"] + available].drop_duplicates("_blend_key", keep="last")
    merged = left.merge(right, on="_blend_key", how="left", suffixes=("", suffix))
    for col in available:
        extra_col = f"{col}{suffix}"
        if extra_col in merged.columns:
            if col in merged.columns:
                current = merged[col].astype(str).str.strip()
                merged[col] = merged[col].where(current != "", merged[extra_col])
                merged[col] = merged[col].fillna(merged[extra_col])
            else:
                merged[col] = merged[extra_col]
            merged = merged.drop(columns=[extra_col])
    return merged.drop(columns=["_blend_key"], errors="ignore")


def probability_from_row(row: pd.Series) -> tuple[float, str]:
    for col in ["shrunk_probability", "raw_model_probability", "rated_probability", "final_probability_v5_1", "contextual_probability_v5_1"]:
        if col in row.index:
            value = num(row.get(col))
            if value is not None and 0 < value <= 1:
                return max(0.0025, min(0.95, value)), col
    for col in ["shrunk_fair_price", "adjusted_rated_price", "rated_price", "final_price_v5_1", "contextual_price_v5_1"]:
        if col in row.index:
            value = num(row.get(col))
            if value is not None and value > 0:
                return max(0.0025, min(0.95, 1.0 / value)), f"1/{col}"
    return 0.0025, "fallback_floor"


def market_probability(row: pd.Series) -> tuple[float, str]:
    for col in ["sportsbet_price", "market_price", "current_price", "fixed_odds", "win_odds"]:
        if col in row.index:
            value = num(row.get(col))
            if value is not None and value > 0:
                return max(0.0025, min(0.95, 1.0 / value)), f"1/{col}"
    return 0.0025, "fallback_floor"


def calibration_lookup(calibration: pd.DataFrame) -> dict:
    lookup = {}
    if calibration.empty or not {"bucket_type", "bucket_value"}.issubset(calibration.columns):
        return lookup
    for _, row in calibration.iterrows():
        lookup[(upper(row.get("bucket_type")), upper(row.get("bucket_value")))] = row.to_dict()
    return lookup


def prob_bucket(probability: float) -> str:
    pct = probability * 100.0
    if pct < 5:
        return "0_5"
    if pct < 10:
        return "5_10"
    if pct < 15:
        return "10_15"
    if pct < 20:
        return "15_20"
    if pct < 30:
        return "20_30"
    return "30_PLUS"


def calibration_grade(row: pd.Series, raw_prob: float, lookup: dict) -> tuple[str, str]:
    bucket = text(row.get("calibration_bucket"))
    if "=" in bucket:
        left, right = bucket.split("=", 1)
        found = lookup.get((upper(left), upper(right)))
        if found:
            return upper(found.get("reliability_grade")), bucket
    model_bucket = prob_bucket(raw_prob)
    found = lookup.get(("MODEL_PROBABILITY_BUCKET", upper(model_bucket)))
    if found:
        return upper(found.get("reliability_grade")), f"model_probability_bucket={model_bucket}"
    found = lookup.get(("OVERALL", "ALL_SETTLED_ROWS"))
    return upper(found.get("reliability_grade")) if found else "UNKNOWN", "OVERALL=ALL_SETTLED_ROWS"


def is_protected_edge(row: pd.Series, policy_rankings: pd.DataFrame) -> bool:
    active_policy = upper(row.get("active_policy"))
    reason = upper(row.get("policy_reason"))
    if "PROTECTED" in active_policy or "PROTECTED" in reason:
        return True
    if not policy_rankings.empty and "recommended_active_policy" in policy_rankings.columns:
        recs = set(policy_rankings["recommended_active_policy"].astype(str).str.upper().dropna().tolist())
        if "PROTECTED_EDGES_ONLY" in recs and upper(row.get("suppression_risk_grade")) in {"ALLOW", ""}:
            return True
    return False


def trust_weights(row: pd.Series, raw_prob: float, calibration: dict, policy_rankings: pd.DataFrame) -> tuple[float, float, float, float, list[str]]:
    grade, bucket = calibration_grade(row, raw_prob, calibration)
    regime = upper(row.get("market_regime_v2") or row.get("market_regime"))
    confidence = upper(row.get("calibrated_confidence_label") or row.get("confidence_band_v1"))
    realism = upper(row.get("overlay_realism_grade"))
    risk = upper(row.get("suppression_risk_grade"))
    flags = upper(row.get("risk_flags"))
    protected = is_protected_edge(row, policy_rankings)

    model_score = 50.0
    market_score = 50.0
    reasons = []

    if grade == "SHARP":
        model_score += 18
        reasons.append("sharp calibration bucket")
    elif grade == "ACCEPTABLE":
        model_score += 8
        reasons.append("acceptable calibration bucket")
    elif grade in {"OVERCONFIDENT", "TOXIC"}:
        market_score += 22
        reasons.append(f"{grade} calibration shifts trust to market")
    elif grade == "UNDERCONFIDENT":
        model_score += 10
        reasons.append("underconfident bucket allows more model trust")

    if "STABLE" in regime:
        model_score += 8
        reasons.append("stable market")
    if any(token in regime for token in ["TOXIC", "VOLATILE", "STEAM", "SHOCK"]):
        market_score += 18
        reasons.append("volatile/toxic regime")

    if confidence in {"HIGH", "VERY_HIGH"}:
        model_score += 12
        reasons.append(f"{confidence} confidence")
    elif confidence in {"VERY_LOW", "LOW"}:
        market_score += 18 if confidence == "VERY_LOW" else 10
        reasons.append(f"{confidence} confidence shifts trust to market")

    if protected:
        model_score += 14
        reasons.append("protected edge context")

    if realism == "FAKE_OVERLAY":
        market_score += 18
        reasons.append("fake overlay shifts trust to market")
    elif realism == "EXTREME_FAKE_OVERLAY":
        market_score += 28
        reasons.append("extreme fake overlay shifts trust to market")

    if risk in {"KILL", "SUPPRESS"}:
        market_score += 18
        reasons.append(f"suppression risk {risk}")
    elif risk == "REDUCE":
        market_score += 8
        reasons.append("reduced risk structure")

    if "NO_OFFICIAL_FORM" in flags or "FIRST" in flags:
        market_score += 12
        reasons.append("first/no-form runner")

    total = max(1.0, model_score + market_score)
    model_weight = max(0.15, min(0.85, model_score / total))
    market_weight = 1.0 - model_weight
    return model_weight, market_weight, model_score, market_score, reasons


def downgrade(action: str, blended_overlay: float, market_weight: float) -> str:
    action = upper(action) or "PASS"
    if blended_overlay <= 0:
        if action in {"MAX_BET", "PRIORITY_EXECUTE", "EXECUTE", "REDUCED_EXECUTE", "WATCH"}:
            return "PASS"
        return action
    if blended_overlay < 6 and action in {"MAX_BET", "PRIORITY_EXECUTE", "EXECUTE", "REDUCED_EXECUTE"}:
        return "WATCH"
    if market_weight >= 0.7 and action in {"MAX_BET", "PRIORITY_EXECUTE"}:
        return "EXECUTE"
    if market_weight >= 0.75 and action == "EXECUTE":
        return "REDUCED_EXECUTE"
    return action


def write_terminal(df: pd.DataFrame):
    terminal = pd.DataFrame()
    for col in TERMINAL_COLUMNS:
        terminal[col] = df[col] if col in df.columns else ""
    terminal.to_csv(TERMINAL_OUT, index=False)


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    live = read_csv(LIVE)
    calibration = read_csv(CALIBRATION)
    shrinkage = read_csv(SHRINKAGE)
    regime = read_csv(REGIME)
    policy = read_csv(POLICY)

    if live.empty:
        pd.DataFrame().to_csv(OUT, index=False)
        print("[bayesian_blending] no live rows; wrote empty output")
        return

    live = merge_by_runner(live, shrinkage, [
        "raw_model_probability",
        "shrunk_probability",
        "shrunk_fair_price",
        "shrunk_overlay_pct",
        "calibration_bucket",
        "shrinkage_factor",
        "shrinkage_reason",
    ], "_shrink")
    live = merge_by_runner(live, regime, [
        "market_regime_v2",
        "market_regime_v2_tags",
        "market_regime_v2_risk",
    ], "_regime")

    lookup = calibration_lookup(calibration)
    output = live.copy()
    if "pre_blending_execution_action" not in output.columns:
        output["pre_blending_execution_action"] = output.get("execution_action", "")

    audit = []
    model_weights = []
    market_weights = []
    downgraded = 0
    protected_preserved = 0

    for idx, row in output.iterrows():
        model_prob, model_source = probability_from_row(row)
        shrunk_prob = num(row.get("shrunk_probability"), model_prob) or model_prob
        market_prob, market_source = market_probability(row)
        model_weight, market_weight, model_score, market_score, reasons = trust_weights(row, model_prob, lookup, policy)

        blended_prob = max(0.0025, min(0.95, (shrunk_prob * model_weight) + (market_prob * market_weight)))
        blended_fair = min(400.0, max(1.01, 1.0 / blended_prob))
        market_price = num(row.get("sportsbet_price"), num(row.get("market_price"), 0.0)) or 0.0
        blended_overlay = ((market_price / blended_fair) - 1.0) * 100.0 if market_price > 0 else 0.0

        before = upper(row.get("execution_action") or row.get("final_execution_state"))
        after = downgrade(before, blended_overlay, market_weight)
        if after != before:
            downgraded += 1
        if is_protected_edge(row, policy) and after in {"MAX_BET", "PRIORITY_EXECUTE", "EXECUTE", "REDUCED_EXECUTE", "WATCH"}:
            protected_preserved += 1

        model_weights.append(model_weight)
        market_weights.append(market_weight)
        reason = " | ".join(reasons) if reasons else "balanced model/market blend"

        output.at[idx, "raw_model_probability"] = round(model_prob, 6)
        output.at[idx, "shrunk_probability"] = round(shrunk_prob, 6)
        output.at[idx, "market_probability"] = round(market_prob, 6)
        output.at[idx, "model_trust_score"] = round(model_score, 2)
        output.at[idx, "market_trust_score"] = round(market_score, 2)
        output.at[idx, "model_weight"] = round(model_weight, 4)
        output.at[idx, "market_weight"] = round(market_weight, 4)
        output.at[idx, "blended_probability"] = round(blended_prob, 6)
        output.at[idx, "blended_fair_price"] = round(blended_fair, 4)
        output.at[idx, "blended_overlay_pct"] = round(blended_overlay, 2)
        output.at[idx, "blending_reason"] = reason
        output.at[idx, "execution_action"] = after
        output.at[idx, "final_execution_state"] = after

        audit.append({
            "horse": row.get("horse", ""),
            "track": row.get("track", ""),
            "race_no": row.get("race_no", ""),
            "raw_model_probability": round(model_prob, 6),
            "shrunk_probability": round(shrunk_prob, 6),
            "market_probability": round(market_prob, 6),
            "model_trust_score": round(model_score, 2),
            "market_trust_score": round(market_score, 2),
            "model_weight": round(model_weight, 4),
            "market_weight": round(market_weight, 4),
            "blended_probability": round(blended_prob, 6),
            "blended_fair_price": round(blended_fair, 4),
            "blended_overlay_pct": round(blended_overlay, 2),
            "pre_blending_execution_action": before,
            "post_blending_execution_action": after,
            "model_source": model_source,
            "market_source": market_source,
            "blending_reason": reason,
        })

    output.to_csv(LIVE_OUT, index=False)
    write_terminal(output)
    pd.DataFrame(audit).to_csv(OUT, index=False)

    avg_model = sum(model_weights) / len(model_weights) if model_weights else 0.0
    avg_market = sum(market_weights) / len(market_weights) if market_weights else 0.0
    print("[bayesian_blending] rows processed:", len(output))
    print("[bayesian_blending] average model weighting:", f"{avg_model:.4f}")
    print("[bayesian_blending] average market weighting:", f"{avg_market:.4f}")
    print("[bayesian_blending] executions downgraded:", downgraded)
    print("[bayesian_blending] protected edges preserved:", protected_preserved)


if __name__ == "__main__":
    main()
