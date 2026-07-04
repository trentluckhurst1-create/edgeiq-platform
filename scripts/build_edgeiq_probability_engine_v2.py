from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "public" / "data"

LIVE = DATA / "edgeiq_execution_board_live.csv"
TERMINAL = DATA / "edgeiq_execution_board_terminal.csv"
RESULTS = DATA / "edgeiq_results_master.csv"
CALIBRATION = DATA / "edgeiq_probability_calibration_v1.csv"
SHRINKAGE = DATA / "edgeiq_probability_shrinkage_v1.csv"
BAYESIAN = DATA / "edgeiq_bayesian_blending_v1.csv"
ENVIRONMENT = DATA / "edgeiq_environment_classification_v1.csv"
MICROSTRUCTURE = DATA / "edgeiq_market_microstructure_v1.csv"
TRANSITIONS = DATA / "edgeiq_market_state_transitions_v1.csv"

OUT = DATA / "edgeiq_probability_engine_v2.csv"
OUT_RANKINGS = DATA / "edgeiq_probability_engine_v2_diagnostics.csv"

OUTPUT_COLUMNS = [
    "track",
    "race_no",
    "horse",
    "market_price",
    "raw_model_probability",
    "market_probability",
    "pre_v2_probability",
    "probability_floor",
    "probability_ceiling",
    "uncertainty_penalty",
    "confidence_dampening",
    "field_strength_compression",
    "market_regime_weight",
    "variance_penalty",
    "v2_probability",
    "v2_fair_price",
    "v2_overlay_pct",
    "v2_probability_realism_grade",
    "v2_pricing_action",
    "v2_reason",
    "pre_v2_execution_action",
    "post_v2_execution_action",
    "v2_applied",
]

DIAGNOSTIC_COLUMNS = [
    "diagnostic_type",
    "rows",
    "avg_pre_v2_probability",
    "avg_v2_probability",
    "avg_probability_change_pct",
    "avg_v2_overlay_pct",
    "fake_overlay_count",
    "downgraded_count",
    "reason",
]


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"[probability_v2] missing {path.name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
        print(f"[probability_v2] read {path.name}: {len(df)} rows")
        return df
    except pd.errors.EmptyDataError:
        print(f"[probability_v2] empty {path.name}")
        return pd.DataFrame()
    except Exception as exc:
        print(f"[probability_v2] warning: could not read {path.name}: {exc}")
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


def merge_by_runner(live: pd.DataFrame, extra: pd.DataFrame, cols: list[str], suffix: str) -> pd.DataFrame:
    if live.empty or extra.empty or not {"track", "race_no", "horse"}.issubset(live.columns) or not {"track", "race_no", "horse"}.issubset(extra.columns):
        return live
    available = [col for col in cols if col in extra.columns]
    if not available:
        return live
    left = live.copy()
    right = extra.copy()
    left["_prob_v2_key"] = full_key(left)
    right["_prob_v2_key"] = full_key(right)
    right = right[["_prob_v2_key"] + available].drop_duplicates("_prob_v2_key", keep="last")
    merged = left.merge(right, on="_prob_v2_key", how="left", suffixes=("", suffix))
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
    return merged.drop(columns=["_prob_v2_key"], errors="ignore")


def probability_from_row(row: pd.Series) -> tuple[float, str]:
    for col in [
        "blended_probability",
        "shrunk_probability",
        "final_probability_v5_1",
        "contextual_probability_v5_1",
        "rated_probability",
        "confidence_adjusted_probability_v1",
    ]:
        value = num(row.get(col), None)
        if value is not None and 0 < value <= 1:
            return value, col
    for col in ["blended_fair_price", "shrunk_fair_price", "adjusted_rated_price", "rated_price", "final_price_v5_1"]:
        value = num(row.get(col), None)
        if value is not None and value > 0:
            return min(0.95, max(0.001, 1.0 / value)), f"1/{col}"
    return 0.001, "fallback_floor"


def market_probability(row: pd.Series) -> tuple[float, float]:
    for col in ["sportsbet_price", "market_price", "current_price", "fixed_odds", "win_odds"]:
        price = num(row.get(col), None)
        if price is not None and price > 0:
            return max(0.001, min(0.95, 1.0 / price)), price
    return 0.001, 0.0


def field_size(row: pd.Series) -> int:
    for col in ["_field_size_active", "field_size", "runner_count"]:
        value = num(row.get(col), None)
        if value is not None and value > 0:
            return int(value)
    return 10


def calibration_lookup(calibration: pd.DataFrame) -> dict[tuple[str, str], dict]:
    lookup = {}
    if calibration.empty or not {"bucket_type", "bucket_value"}.issubset(calibration.columns):
        return lookup
    for _, row in calibration.iterrows():
        lookup[(upper(row.get("bucket_type")), upper(row.get("bucket_value")))] = row.to_dict()
    return lookup


def probability_bucket(probability: float) -> str:
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


def calibration_adjustment(row: pd.Series, probability: float, lookup: dict) -> tuple[float, str]:
    bucket = probability_bucket(probability)
    found = lookup.get(("MODEL_PROBABILITY_BUCKET", upper(bucket)))
    if not found:
        found = lookup.get(("OVERALL", "ALL_SETTLED_ROWS"))
    if not found:
        return 1.0, "no calibration curve"
    shift = num(found.get("recommended_probability_adjustment_pct"), 0.0) or 0.0
    grade = upper(found.get("reliability_grade")) or "UNKNOWN"
    factor = max(0.35, min(1.25, 1.0 + (shift / 100.0)))
    if grade == "TOXIC":
        factor = min(factor, 0.65)
    if grade == "OVERCONFIDENT":
        factor = min(factor, 0.75)
    if grade in {"SHARP", "ACCEPTABLE"}:
        factor = max(0.8, min(1.1, factor))
    return factor, f"calibration {grade} bucket {bucket} factor {factor:.2f}"


def clamp(value: float, floor: float, ceiling: float) -> float:
    return max(floor, min(ceiling, value))


def classify_realism(v2_overlay: float, uncertainty: float, confidence: str, environment: str) -> str:
    if v2_overlay >= 150 or uncertainty >= 0.6:
        return "EXTREME_FAKE_OVERLAY"
    if v2_overlay >= 75 or confidence in {"VERY_LOW", "LOW"} or environment in {"CHAOTIC", "PUBLIC_TRAP", "ILLIQUID"}:
        return "FAKE_OVERLAY"
    if v2_overlay >= 25 or uncertainty >= 0.35:
        return "QUESTIONABLE"
    return "REALISTIC"


def downgrade(action: str, overlay: float, realism: str, risk_grade: str) -> str:
    action = upper(action) or "PASS"
    executable = {"MAX_BET", "PRIORITY_EXECUTE", "EXECUTE", "REDUCED_EXECUTE", "BET"}
    if overlay <= 0 and action in executable | {"WATCH"}:
        return "PASS"
    if realism in {"EXTREME_FAKE_OVERLAY", "FAKE_OVERLAY"} and action in executable:
        return "WATCH" if risk_grade != "RED" else "SUPPRESS"
    if overlay < 6 and action in executable:
        return "WATCH"
    return action


def calculate_row(row: pd.Series, lookup: dict) -> dict:
    raw_prob, prob_source = probability_from_row(row)
    market_prob, market_price = market_probability(row)
    size = field_size(row)
    fair_share = 1.0 / max(1, size)
    confidence = upper(coalesce(row, ["calibrated_confidence_label", "confidence_band_v1", "confidence"]))
    environment = upper(coalesce(row, ["environment_type"]))
    micro = upper(coalesce(row, ["microstructure_type"]))
    transition = upper(coalesce(row, ["transition_type"]))
    transition_risk = upper(coalesce(row, ["transition_risk_grade", "microstructure_risk_grade", "environment_risk_grade"]))
    risk_flags = upper(coalesce(row, ["risk_flags", "rating_notes"]))
    official_runs = num(coalesce(row, ["official_run_count", "official_run_count_v5", "summary_official_run_count"]), None)
    model_rank = num(row.get("model_rank"), None)

    first_starter = "FIRST" in risk_flags or "NO_OFFICIAL_FORM" in risk_flags or official_runs == 0
    lightly_raced = official_runs is not None and official_runs <= 3

    probability_floor = max(0.0025, market_prob * 0.2)
    probability_ceiling = min(0.55, max(0.08, market_prob * 2.5, fair_share * 2.2))
    if size >= 12:
        probability_ceiling = min(probability_ceiling, 0.28)
    if first_starter:
        probability_ceiling = min(probability_ceiling, max(0.08, market_prob * 1.35))
    if confidence in {"VERY_LOW", "LOW"}:
        probability_ceiling = min(probability_ceiling, max(0.06, market_prob * 1.5))

    uncertainty = 0.10
    reasons = [f"source {prob_source}"]
    if confidence == "VERY_LOW":
        uncertainty += 0.30
        reasons.append("very low confidence dampening")
    elif confidence == "LOW":
        uncertainty += 0.20
        reasons.append("low confidence dampening")
    elif confidence == "MEDIUM":
        uncertainty += 0.12
        reasons.append("medium confidence caution")
    if first_starter:
        uncertainty += 0.25
        reasons.append("first starter/no-form penalty")
    elif lightly_raced:
        uncertainty += 0.12
        reasons.append("lightly raced penalty")
    if environment in {"CHAOTIC", "PUBLIC_TRAP", "ILLIQUID"}:
        uncertainty += 0.22
        reasons.append(f"{environment} environment penalty")
    elif environment in {"VOLATILE"}:
        uncertainty += 0.15
        reasons.append("volatile environment penalty")
    if micro in {"VOLATILITY_CLUSTER", "PUBLIC_STEAM", "FALSE_STEAM", "PANIC_DRIFT"}:
        uncertainty += 0.18
        reasons.append(f"{micro} microstructure penalty")
    if transition_risk == "RED":
        uncertainty += 0.12
        reasons.append("red transition risk")
    if model_rank is not None and model_rank > 6:
        uncertainty += 0.06
        reasons.append("lower model rank compression")
    uncertainty = min(0.85, uncertainty)

    calibration_factor, calibration_reason = calibration_adjustment(row, raw_prob, lookup)
    reasons.append(calibration_reason)

    confidence_dampening = max(0.35, 1.0 - (uncertainty * 0.65))
    field_strength_compression = 0.75 if raw_prob > fair_share * 1.8 else 0.9
    if first_starter:
        field_strength_compression = min(field_strength_compression, 0.7)
    market_regime_weight = 0.65 if environment in {"CHAOTIC", "PUBLIC_TRAP", "ILLIQUID"} else 0.5
    if environment in {"CLEAN", "PROTECTED_EDGE"} and confidence in {"HIGH", "VERY_HIGH"}:
        market_regime_weight = 0.35
    if first_starter:
        market_regime_weight = max(market_regime_weight, 0.75)
    variance_penalty = max(0.25, 1.0 - (uncertainty * 0.45))

    adjusted_model_prob = raw_prob * calibration_factor * confidence_dampening * field_strength_compression * variance_penalty
    blended_prob = (adjusted_model_prob * (1.0 - market_regime_weight)) + (market_prob * market_regime_weight)
    v2_probability = clamp(blended_prob, probability_floor, probability_ceiling)
    v2_fair_price = min(400.0, max(1.01, 1.0 / v2_probability))
    v2_overlay = ((market_price / v2_fair_price) - 1.0) * 100.0 if market_price > 0 else 0.0
    realism = classify_realism(v2_overlay, uncertainty, confidence, environment)
    action = upper(coalesce(row, ["final_execution_state", "execution_action"]))
    post_action = downgrade(action, v2_overlay, realism, transition_risk)

    if realism in {"REALISTIC"} and v2_overlay > 6:
        pricing_action = "ALLOW_REALISTIC"
    elif realism == "QUESTIONABLE":
        pricing_action = "REQUIRE_CONFIRMATION"
    else:
        pricing_action = "SUPPRESS_FAKE_OVERLAY"

    return {
        "market_price": round(market_price, 4),
        "raw_model_probability": round(raw_prob, 6),
        "market_probability": round(market_prob, 6),
        "pre_v2_probability": round(raw_prob, 6),
        "probability_floor": round(probability_floor, 6),
        "probability_ceiling": round(probability_ceiling, 6),
        "uncertainty_penalty": round(uncertainty, 4),
        "confidence_dampening": round(confidence_dampening, 4),
        "field_strength_compression": round(field_strength_compression, 4),
        "market_regime_weight": round(market_regime_weight, 4),
        "variance_penalty": round(variance_penalty, 4),
        "v2_probability": round(v2_probability, 6),
        "v2_fair_price": round(v2_fair_price, 4),
        "v2_overlay_pct": round(v2_overlay, 2),
        "v2_probability_realism_grade": realism,
        "v2_pricing_action": pricing_action,
        "v2_reason": " | ".join(reasons),
        "pre_v2_execution_action": action,
        "post_v2_execution_action": post_action,
        "v2_applied": post_action != action or abs(v2_probability - raw_prob) > 0.0001,
    }


def append_to_terminal(terminal: pd.DataFrame, audit: pd.DataFrame) -> pd.DataFrame:
    if terminal.empty or audit.empty:
        return terminal
    left = terminal.copy()
    right = audit.copy()
    left["_key"] = full_key(left)
    right["_key"] = full_key(right)
    cols = [col for col in OUTPUT_COLUMNS if col not in {"track", "race_no", "horse"}]
    right = right[["_key"] + cols].drop_duplicates("_key", keep="last")
    merged = left.merge(right, on="_key", how="left", suffixes=("", "_v2"))
    for col in cols:
        extra = f"{col}_v2"
        if extra in merged.columns:
            current = merged[col].map(text) if col in merged.columns else pd.Series([""] * len(merged), index=merged.index)
            merged[col] = merged[col].where(current != "", merged[extra]) if col in merged.columns else merged[extra]
            merged = merged.drop(columns=[extra])
    return merged.drop(columns=["_key"], errors="ignore")


def diagnostics(audit: pd.DataFrame) -> pd.DataFrame:
    if audit.empty:
        return pd.DataFrame(columns=DIAGNOSTIC_COLUMNS)
    rows = []
    for dtype, frame in [
        ("OVERALL", audit),
        ("FIRST_STARTER_OR_NO_FORM", audit[audit["v2_reason"].str.contains("first starter|no-form", case=False, na=False)]),
        ("FAKE_OVERLAY", audit[audit["v2_probability_realism_grade"].isin(["FAKE_OVERLAY", "EXTREME_FAKE_OVERLAY"])])
    ]:
        if frame.empty:
            rows.append({col: "" for col in DIAGNOSTIC_COLUMNS} | {"diagnostic_type": dtype, "rows": 0})
            continue
        pre = pd.to_numeric(frame["pre_v2_probability"], errors="coerce")
        post = pd.to_numeric(frame["v2_probability"], errors="coerce")
        change = ((post - pre) / pre.replace(0, pd.NA) * 100.0).dropna()
        rows.append({
            "diagnostic_type": dtype,
            "rows": len(frame),
            "avg_pre_v2_probability": round(float(pre.mean()), 6),
            "avg_v2_probability": round(float(post.mean()), 6),
            "avg_probability_change_pct": round(float(change.mean()), 2) if len(change) else "",
            "avg_v2_overlay_pct": round(float(pd.to_numeric(frame["v2_overlay_pct"], errors="coerce").mean()), 2),
            "fake_overlay_count": int(frame["v2_probability_realism_grade"].isin(["FAKE_OVERLAY", "EXTREME_FAKE_OVERLAY"]).sum()),
            "downgraded_count": int((frame["pre_v2_execution_action"] != frame["post_v2_execution_action"]).sum()),
            "reason": "Probability Engine V2 diagnostic summary",
        })
    return pd.DataFrame(rows, columns=DIAGNOSTIC_COLUMNS)


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    live = read_csv(LIVE)
    results = read_csv(RESULTS)
    calibration = read_csv(CALIBRATION)
    shrinkage = read_csv(SHRINKAGE)
    bayesian = read_csv(BAYESIAN)
    environment = read_csv(ENVIRONMENT)
    micro = read_csv(MICROSTRUCTURE)
    transitions = read_csv(TRANSITIONS)

    if live.empty:
        pd.DataFrame(columns=OUTPUT_COLUMNS).to_csv(OUT, index=False)
        pd.DataFrame(columns=DIAGNOSTIC_COLUMNS).to_csv(OUT_RANKINGS, index=False)
        print("[probability_v2] no live rows; wrote empty outputs")
        return

    live = merge_by_runner(live, shrinkage, ["shrunk_probability", "shrunk_fair_price", "shrunk_overlay_pct"], "_shrink")
    live = merge_by_runner(live, bayesian, ["blended_probability", "blended_fair_price", "blended_overlay_pct", "model_weight", "market_weight"], "_bayes")
    live = merge_by_runner(live, environment, ["environment_type", "environment_risk_grade"], "_env")
    live = merge_by_runner(live, micro, ["microstructure_type", "microstructure_risk_grade"], "_micro")
    live = merge_by_runner(live, transitions, ["transition_type", "transition_risk_grade"], "_transition")

    lookup = calibration_lookup(calibration)
    output = live.copy()
    audit_rows = []
    for idx, row in output.iterrows():
        calc = calculate_row(row, lookup)
        for col, value in calc.items():
            output.at[idx, col] = value
        output.at[idx, "final_execution_state"] = calc["post_v2_execution_action"]
        output.at[idx, "execution_action"] = calc["post_v2_execution_action"]
        audit_rows.append({
            "track": row.get("track", ""),
            "race_no": row.get("race_no", ""),
            "horse": row.get("horse", ""),
            **calc,
        })

    audit = pd.DataFrame(audit_rows, columns=OUTPUT_COLUMNS)
    diag = diagnostics(audit)

    output.to_csv(LIVE, index=False)
    if TERMINAL.exists():
        terminal = read_csv(TERMINAL)
        append_to_terminal(terminal, audit).to_csv(TERMINAL, index=False)
    else:
        output.to_csv(TERMINAL, index=False)
    audit.to_csv(OUT, index=False)
    diag.to_csv(OUT_RANKINGS, index=False)

    changes = pd.to_numeric(audit["v2_probability"], errors="coerce") - pd.to_numeric(audit["pre_v2_probability"], errors="coerce")
    reduced = int((changes < -0.0001).sum())
    fake = int(audit["v2_probability_realism_grade"].isin(["FAKE_OVERLAY", "EXTREME_FAKE_OVERLAY"]).sum())
    downgraded = int((audit["pre_v2_execution_action"] != audit["post_v2_execution_action"]).sum())
    avg_change = float(((pd.to_numeric(audit["v2_probability"], errors="coerce") - pd.to_numeric(audit["pre_v2_probability"], errors="coerce")) / pd.to_numeric(audit["pre_v2_probability"], errors="coerce").replace(0, pd.NA) * 100.0).dropna().mean()) if len(audit) else 0.0

    print("[probability_v2] rows processed:", len(audit))
    print("[probability_v2] probabilities reduced:", reduced)
    print("[probability_v2] fake overlays detected:", fake)
    print("[probability_v2] executions downgraded:", downgraded)
    print("[probability_v2] average probability change pct:", f"{avg_change:.2f}")
    print("[probability_v2] results rows read:", len(results))


if __name__ == "__main__":
    main()
