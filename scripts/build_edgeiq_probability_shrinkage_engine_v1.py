from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "public" / "data"

LIVE = DATA / "edgeiq_execution_board_live.csv"
CALIBRATION = DATA / "edgeiq_probability_calibration_v1.csv"
CURVES = DATA / "edgeiq_probability_calibration_curves.csv"
BUCKETS = DATA / "edgeiq_probability_bucket_analysis.csv"
OUT = DATA / "edgeiq_probability_shrinkage_v1.csv"
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
    "overlay_pct",
    "adjusted_overlay_pct",
    "shrunk_overlay_pct",
    "overlay_realism_grade",
    "price_truth_adjustment_pct",
    "shrinkage_factor",
    "calibration_bucket",
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
        print(f"[probability_shrinkage] missing {path.name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
        print(f"[probability_shrinkage] read {path.name}: {len(df)} rows")
        return df
    except pd.errors.EmptyDataError:
        print(f"[probability_shrinkage] empty {path.name}")
        return pd.DataFrame()
    except Exception as exc:
        print(f"[probability_shrinkage] warning: could not read {path.name}: {exc}")
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


def first_existing(row: pd.Series, names: list[str]):
    for name in names:
        if name in row.index:
            value = num(row.get(name))
            if value is not None and value > 0:
                return value, name
    return None, ""


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


def calibration_lookup(calibration: pd.DataFrame, curves: pd.DataFrame, buckets: pd.DataFrame) -> dict:
    source = pd.concat([curves, calibration, buckets], ignore_index=True)
    lookup = {}
    required = {"bucket_type", "bucket_value"}
    if source.empty or not required.issubset(source.columns):
        return lookup
    for _, row in source.drop_duplicates(["bucket_type", "bucket_value"], keep="first").iterrows():
        key = (upper(row.get("bucket_type")), upper(row.get("bucket_value")))
        lookup[key] = row.to_dict()
    return lookup


def pick_calibration(row: pd.Series, raw_probability: float, lookup: dict) -> tuple[str, dict]:
    model_bucket = probability_bucket(raw_probability)
    candidates = [
        ("model_probability_bucket", model_bucket),
        ("confidence_bucket", upper(row.get("calibrated_confidence_label") or row.get("confidence_band_v1"))),
        ("overlay_realism_grade", upper(row.get("overlay_realism_grade"))),
        ("market_regime", upper(row.get("market_regime") or row.get("market_regime_v2"))),
        ("OVERALL", "ALL_SETTLED_ROWS"),
    ]
    for bucket_type, bucket_value in candidates:
        key = (upper(bucket_type), upper(bucket_value))
        if key in lookup:
            return f"{bucket_type}={bucket_value}", lookup[key]
    return "model_probability_bucket=UNKNOWN", {}


def base_shrinkage_factor(calibration_row: dict) -> tuple[float, list[str]]:
    grade = upper(calibration_row.get("reliability_grade"))
    shift = num(calibration_row.get("recommended_probability_adjustment_pct"), 0.0) or 0.0
    error = num(calibration_row.get("calibration_error"), 0.0) or 0.0
    reasons = []

    if grade in {"TOXIC", "OVERCONFIDENT"} or error > 5:
        factor = max(0.25, min(1.0, 1.0 + min(shift, 0.0) / 100.0))
        if shift >= 0:
            factor = max(0.45, 1.0 - min(abs(error), 35.0) / 100.0)
        reasons.append(f"{grade or 'CALIBRATION'} overconfidence adjustment")
    elif grade == "UNDERCONFIDENT":
        factor = min(1.15, 1.0 + max(shift, 0.0) / 300.0)
        reasons.append("underconfident bucket preserved")
    elif grade == "SHARP":
        factor = 0.98
        reasons.append("sharp bucket gentle preservation")
    elif grade == "ACCEPTABLE":
        factor = 0.94
        reasons.append("acceptable bucket mild shrinkage")
    else:
        factor = 0.9
        reasons.append("unknown calibration cautious shrinkage")
    return factor, reasons


def apply_context_factor(row: pd.Series, factor: float, reasons: list[str]) -> tuple[float, list[str]]:
    regime = upper(row.get("market_regime") or row.get("market_regime_v2"))
    confidence = upper(row.get("calibrated_confidence_label") or row.get("confidence_band_v1"))
    realism = upper(row.get("overlay_realism_grade"))

    if regime == "STABLE":
        factor = 1.0 - ((1.0 - factor) * 0.65)
        reasons.append("stable market gentler shrinkage")
    if confidence in {"VERY_LOW", "LOW"}:
        factor *= 0.85 if confidence == "LOW" else 0.75
        reasons.append(f"{confidence} confidence stronger shrinkage")
    if realism == "FAKE_OVERLAY":
        factor *= 0.75
        reasons.append("fake overlay stronger shrinkage")
    elif realism == "EXTREME_FAKE_OVERLAY":
        factor *= 0.6
        reasons.append("extreme fake overlay stronger shrinkage")

    return max(0.05, min(1.2, factor)), reasons


def downgrade(action: str, shrunk_overlay: float) -> str:
    action = upper(action) or "PASS"
    if shrunk_overlay <= 0:
        if action in {"MAX_BET", "PRIORITY_EXECUTE", "EXECUTE", "REDUCED_EXECUTE", "WATCH"}:
            return "PASS"
        return action
    if shrunk_overlay < 8 and action in {"MAX_BET", "PRIORITY_EXECUTE", "EXECUTE"}:
        return "WATCH"
    if shrunk_overlay < 4 and action == "REDUCED_EXECUTE":
        return "WATCH"
    return action


def terminal_write(df: pd.DataFrame):
    terminal = pd.DataFrame()
    for col in TERMINAL_COLUMNS:
        terminal[col] = df[col] if col in df.columns else ""
    terminal.to_csv(TERMINAL_OUT, index=False)


def main():
    DATA.mkdir(parents=True, exist_ok=True)

    live = read_csv(LIVE)
    calibration = read_csv(CALIBRATION)
    curves = read_csv(CURVES)
    buckets = read_csv(BUCKETS)

    if live.empty:
        pd.DataFrame().to_csv(OUT, index=False)
        print("[probability_shrinkage] no live rows; wrote empty output")
        return

    lookup = calibration_lookup(calibration, curves, buckets)
    output = live.copy()
    if "pre_shrinkage_execution_action" not in output.columns:
        output["pre_shrinkage_execution_action"] = output.get("execution_action", "")

    audit_rows = []
    downgraded = 0
    corrected = 0
    factors = []

    for idx, row in output.iterrows():
        rated_price, price_source = first_existing(row, ["rated_price", "final_price_v5_1", "contextual_price_v5_1", "adjusted_rated_price"])
        explicit_probability, prob_source = first_existing(row, ["rated_probability", "final_probability_v5_1", "contextual_probability_v5_1"])
        market_price, market_source = first_existing(row, ["sportsbet_price", "market_price", "current_price", "fixed_odds", "win_odds"])

        if explicit_probability is not None and explicit_probability <= 1:
            raw_probability = explicit_probability
        elif rated_price:
            raw_probability = 1.0 / rated_price
            prob_source = f"1/{price_source}"
        else:
            raw_probability = 0.0
            prob_source = "missing"

        raw_probability = max(0.0001, min(0.95, raw_probability))
        calibration_bucket, calibration_row = pick_calibration(row, raw_probability, lookup)
        factor, reasons = base_shrinkage_factor(calibration_row)
        factor, reasons = apply_context_factor(row, factor, reasons)

        shrunk_probability = max(0.0025, min(0.95, raw_probability * factor))
        shrunk_fair = min(400.0, max(1.01, 1.0 / shrunk_probability))
        if market_price and market_price > 0:
            shrunk_overlay = ((market_price / shrunk_fair) - 1.0) * 100.0
        else:
            shrunk_overlay = 0.0

        before_action = upper(row.get("execution_action") or row.get("final_execution_state"))
        after_action = downgrade(before_action, shrunk_overlay)
        if after_action != before_action:
            downgraded += 1
        if factor < 0.9:
            corrected += 1
        factors.append(factor)

        output.at[idx, "raw_model_probability"] = round(raw_probability, 6)
        output.at[idx, "calibration_bucket"] = calibration_bucket
        output.at[idx, "recommended_probability_shift"] = round(num(calibration_row.get("recommended_probability_adjustment_pct"), 0.0) or 0.0, 2)
        output.at[idx, "shrinkage_factor"] = round(factor, 4)
        output.at[idx, "shrunk_probability"] = round(shrunk_probability, 6)
        output.at[idx, "shrunk_fair_price"] = round(shrunk_fair, 4)
        output.at[idx, "shrunk_overlay_pct"] = round(shrunk_overlay, 2)
        output.at[idx, "shrinkage_reason"] = " | ".join(reasons)
        output.at[idx, "execution_action"] = after_action
        output.at[idx, "final_execution_state"] = after_action

        audit_rows.append({
            "horse": row.get("horse", ""),
            "track": row.get("track", ""),
            "race_no": row.get("race_no", ""),
            "price_source": price_source,
            "probability_source": prob_source,
            "market_source": market_source,
            "raw_model_probability": round(raw_probability, 6),
            "calibration_bucket": calibration_bucket,
            "recommended_probability_shift": output.at[idx, "recommended_probability_shift"],
            "shrinkage_factor": round(factor, 4),
            "shrunk_probability": round(shrunk_probability, 6),
            "shrunk_fair_price": round(shrunk_fair, 4),
            "shrunk_overlay_pct": round(shrunk_overlay, 2),
            "pre_shrinkage_execution_action": before_action,
            "post_shrinkage_execution_action": after_action,
            "shrinkage_reason": output.at[idx, "shrinkage_reason"],
        })

    output.to_csv(LIVE_OUT, index=False)
    terminal_write(output)
    pd.DataFrame(audit_rows).to_csv(OUT, index=False)

    avg_factor = sum(factors) / len(factors) if factors else 0.0
    executable = int(output["execution_action"].astype(str).str.upper().isin(["MAX_BET", "PRIORITY_EXECUTE", "EXECUTE", "REDUCED_EXECUTE"]).sum())
    print("[probability_shrinkage] rows processed:", len(output))
    print("[probability_shrinkage] overconfident runners corrected:", corrected)
    print("[probability_shrinkage] average shrinkage factor:", f"{avg_factor:.4f}")
    print("[probability_shrinkage] executions downgraded:", downgraded)
    print("[probability_shrinkage] remaining executable runners:", executable)


if __name__ == "__main__":
    main()
