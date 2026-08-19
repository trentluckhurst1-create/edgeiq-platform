from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "public" / "data"

RESULTS = DATA / "edgeiq_results_master.csv"
PRICE_TRUTH = DATA / "edgeiq_price_truth_adjustments.csv"
CONFIDENCE = DATA / "edgeiq_confidence_calibration_v1.csv"
DIAGNOSTICS = DATA / "edgeiq_model_diagnostic_by_factor.csv"

OUT_CALIBRATION = DATA / "edgeiq_probability_calibration_v1.csv"
OUT_CURVES = DATA / "edgeiq_probability_calibration_curves.csv"
OUT_BUCKETS = DATA / "edgeiq_probability_bucket_analysis.csv"

OUTPUT_COLUMNS = [
    "bucket_type",
    "bucket_value",
    "rows",
    "settled_rows",
    "wins",
    "actual_win_rate",
    "predicted_win_rate",
    "market_win_rate",
    "calibration_error",
    "market_calibration_error",
    "recommended_probability_adjustment_pct",
    "average_clv_pct",
    "beat_close_pct",
    "turnover",
    "profit_loss",
    "roi_pct",
    "reliability_grade",
    "closer_to_reality",
    "diagnostic_note",
]


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"[probability_calibration] missing {path.name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
        print(f"[probability_calibration] read {path.name}: {len(df)} rows")
        return df
    except pd.errors.EmptyDataError:
        print(f"[probability_calibration] empty {path.name}")
        return pd.DataFrame()
    except Exception as exc:
        print(f"[probability_calibration] warning: could not read {path.name}: {exc}")
        return pd.DataFrame()


def text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def upper(value) -> str:
    return text(value).upper()


def numeric(df: pd.DataFrame, column: str, default=pd.NA) -> pd.Series:
    if column not in df.columns:
        return pd.Series([default] * len(df), index=df.index)
    return pd.to_numeric(df[column], errors="coerce")


def first_existing(df: pd.DataFrame, names: list[str]) -> str | None:
    for name in names:
        if name in df.columns:
            return name
    return None


def probability_bucket(probability) -> str:
    try:
        value = float(probability)
    except Exception:
        return "UNKNOWN"
    if not pd.notna(value):
        return "UNKNOWN"
    pct = value * 100.0
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


def odds_bucket(price) -> str:
    try:
        value = float(price)
    except Exception:
        return "UNKNOWN"
    if not pd.notna(value) or value <= 0:
        return "UNKNOWN"
    if value < 3:
        return "UNDER_3"
    if value < 6:
        return "3_TO_6"
    if value < 12:
        return "6_TO_12"
    if value < 26:
        return "12_TO_26"
    return "26_PLUS"


def overlay_bucket(overlay) -> str:
    try:
        value = float(overlay)
    except Exception:
        return "UNKNOWN"
    if not pd.notna(value):
        return "UNKNOWN"
    if value < 0:
        return "NEGATIVE_OVERLAY"
    if value < 10:
        return "0_TO_10"
    if value < 25:
        return "10_TO_25"
    if value < 50:
        return "25_TO_50"
    if value < 100:
        return "50_TO_100"
    return "100_PLUS"


def confidence_bucket(confidence) -> str:
    label = upper(confidence)
    if label in {"VERY_LOW", "LOW", "MEDIUM", "HIGH", "VERY_HIGH"}:
        return label
    try:
        value = float(confidence)
    except Exception:
        return "UNKNOWN"
    if not pd.notna(value):
        return "UNKNOWN"
    if value <= 20:
        return "VERY_LOW"
    if value <= 40:
        return "LOW"
    if value <= 60:
        return "MEDIUM"
    if value <= 80:
        return "HIGH"
    return "VERY_HIGH"


def make_key(df: pd.DataFrame) -> pd.Series:
    parts = []
    for col in ["race_date", "track", "race_no", "horse"]:
        if col in df.columns:
            parts.append(df[col].map(lambda x: upper(x)))
        else:
            parts.append(pd.Series([""] * len(df), index=df.index))
    return parts[0] + "|" + parts[1] + "|" + parts[2] + "|" + parts[3]


def merge_price_truth(results: pd.DataFrame, price_truth: pd.DataFrame) -> pd.DataFrame:
    if results.empty or price_truth.empty:
        return results.copy()
    required = {"race_date", "track", "race_no", "horse"}
    if not required.issubset(results.columns) or not required.issubset(price_truth.columns):
        return results.copy()

    cols = ["adjusted_overlay_pct", "overlay_realism_grade", "adjusted_rated_price"]
    available = [c for c in cols if c in price_truth.columns]
    if not available:
        return results.copy()

    left = results.copy()
    right = price_truth.copy()
    left["_calibration_key"] = make_key(left)
    right["_calibration_key"] = make_key(right)
    right = right[["_calibration_key"] + available].drop_duplicates("_calibration_key", keep="last")
    merged = left.merge(right, on="_calibration_key", how="left", suffixes=("", "_price_truth"))

    for col in available:
        extra = f"{col}_price_truth"
        if extra in merged.columns:
            if col in merged.columns:
                current = merged[col].astype(str).str.strip()
                merged[col] = merged[col].where(current != "", merged[extra])
                merged[col] = merged[col].fillna(merged[extra])
            else:
                merged[col] = merged[extra]
            merged = merged.drop(columns=[extra])

    return merged.drop(columns=["_calibration_key"], errors="ignore")


def add_factors(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    rated = numeric(out, "rated_price")
    market = numeric(out, "market_price")
    out["model_probability"] = 1.0 / rated.where(rated > 0)
    out["market_probability"] = 1.0 / market.where(market > 0)
    out["model_probability_bucket"] = out["model_probability"].map(probability_bucket)
    out["market_probability_bucket"] = out["market_probability"].map(probability_bucket)
    out["odds_bucket"] = market.map(odds_bucket)

    overlay_col = first_existing(out, ["adjusted_overlay_pct", "overlay_pct"])
    raw_overlay_col = first_existing(out, ["overlay_pct"])
    out["adjusted_overlay_bucket"] = out[overlay_col].map(overlay_bucket) if overlay_col else "UNKNOWN"
    out["raw_overlay_bucket"] = out[raw_overlay_col].map(overlay_bucket) if raw_overlay_col else "UNKNOWN"

    confidence_col = first_existing(out, ["calibrated_confidence_label", "confidence", "confidence_score"])
    out["confidence_bucket"] = out[confidence_col].map(confidence_bucket) if confidence_col else "UNKNOWN"

    if "overlay_realism_grade" in out.columns:
        out["overlay_realism_grade"] = out["overlay_realism_grade"].map(lambda x: upper(x) or "UNKNOWN")
    else:
        out["overlay_realism_grade"] = "UNKNOWN"

    if "race_class" in out.columns:
        out["race_class"] = out["race_class"].map(lambda x: upper(x) or "UNKNOWN")
    else:
        out["race_class"] = "UNKNOWN"

    regime_col = first_existing(out, ["market_regime", "regime"])
    out["market_regime"] = out[regime_col].map(lambda x: upper(x) or "UNKNOWN") if regime_col else "UNKNOWN"

    first_starter_col = first_existing(out, ["official_run_count", "run_count", "career_starts"])
    if first_starter_col:
        starts = numeric(out, first_starter_col)
        out["first_starter"] = starts.map(lambda x: "FIRST_STARTER" if pd.notna(x) and x == 0 else "EXPERIENCED" if pd.notna(x) else "UNKNOWN")
    elif "risk_flags" in out.columns:
        out["first_starter"] = out["risk_flags"].astype(str).str.upper().map(lambda x: "FIRST_STARTER" if "NO_OFFICIAL_FORM" in x or "FIRST" in x else "UNKNOWN")
    else:
        out["first_starter"] = "UNKNOWN"

    return out


def reliability_grade(settled_rows: int, calibration_error: float, roi_pct: float, beat_close_pct: float) -> str:
    abs_error = abs(calibration_error)
    if settled_rows < 20:
        return "UNKNOWN"
    if calibration_error > 10 and (roi_pct < -10 or beat_close_pct < 35):
        return "TOXIC"
    if calibration_error > 5:
        return "OVERCONFIDENT"
    if calibration_error < -5:
        return "UNDERCONFIDENT"
    if abs_error <= 2:
        return "SHARP"
    return "ACCEPTABLE"


def analyse_group(df: pd.DataFrame, bucket_type: str, bucket_value: str) -> dict:
    rows = len(df)
    wins = int(df["actual_win"].sum()) if "actual_win" in df.columns else 0
    settled_rows = rows
    actual = (wins / settled_rows * 100.0) if settled_rows else 0.0
    predicted = float(df["model_probability"].mean() * 100.0) if settled_rows else 0.0
    market = float(df["market_probability"].mean() * 100.0) if settled_rows else 0.0
    error = predicted - actual
    market_error = market - actual
    adjustment = ((actual - predicted) / predicted * 100.0) if predicted else 0.0
    clv = numeric(df, "clv_pct")
    avg_clv = float(clv.dropna().mean()) if int(clv.notna().sum()) else 0.0
    beat_close = (float((clv > 0).sum()) / int(clv.notna().sum()) * 100.0) if int(clv.notna().sum()) else 0.0
    stake = numeric(df, "stake", 0).fillna(0)
    pl = numeric(df, "profit_loss", 0).fillna(0)
    turnover = float(stake.sum())
    profit = float(pl.sum())
    roi = (profit / turnover * 100.0) if turnover else 0.0
    grade = reliability_grade(settled_rows, error, roi, beat_close)
    closer = "MODEL" if abs(error) < abs(market_error) else "MARKET" if abs(market_error) < abs(error) else "TIE"

    if grade == "TOXIC":
        note = "Model probability is materially overconfident and historical execution is poor."
    elif grade == "OVERCONFIDENT":
        note = "Model probability exceeds actual win rate."
    elif grade == "UNDERCONFIDENT":
        note = "Model probability is below actual win rate."
    elif grade == "SHARP":
        note = "Predicted win rate is close to actual win rate."
    else:
        note = "Calibration is within monitored range."

    return {
        "bucket_type": bucket_type,
        "bucket_value": bucket_value,
        "rows": rows,
        "settled_rows": settled_rows,
        "wins": wins,
        "actual_win_rate": round(actual, 2),
        "predicted_win_rate": round(predicted, 2),
        "market_win_rate": round(market, 2),
        "calibration_error": round(error, 2),
        "market_calibration_error": round(market_error, 2),
        "recommended_probability_adjustment_pct": round(adjustment, 2),
        "average_clv_pct": round(avg_clv, 2),
        "beat_close_pct": round(beat_close, 2),
        "turnover": round(turnover, 4),
        "profit_loss": round(profit, 4),
        "roi_pct": round(roi, 2),
        "reliability_grade": grade,
        "closer_to_reality": closer,
        "diagnostic_note": note,
    }


def analyse_buckets(df: pd.DataFrame) -> pd.DataFrame:
    factors = [
        "model_probability_bucket",
        "market_probability_bucket",
        "confidence_bucket",
        "adjusted_overlay_bucket",
        "odds_bucket",
        "overlay_realism_grade",
        "first_starter",
        "race_class",
        "market_regime",
    ]

    rows = [analyse_group(df, "OVERALL", "ALL_SETTLED_ROWS")]
    for factor in factors:
        if factor not in df.columns:
            continue
        for value, group in df.groupby(factor, dropna=False):
            bucket_value = upper(value) or "UNKNOWN"
            if bucket_value == "UNKNOWN":
                continue
            rows.append(analyse_group(group, factor, bucket_value))

    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def build_curves(bucket_analysis: pd.DataFrame) -> pd.DataFrame:
    curves = bucket_analysis[bucket_analysis["bucket_type"].isin(["model_probability_bucket", "market_probability_bucket"])].copy()
    if curves.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    order = {"0_5": 1, "5_10": 2, "10_15": 3, "15_20": 4, "20_30": 5, "30_PLUS": 6}
    curves["_order"] = curves["bucket_value"].map(order).fillna(99)
    return curves.sort_values(["bucket_type", "_order"]).drop(columns=["_order"])


def main():
    DATA.mkdir(parents=True, exist_ok=True)

    results = read_csv(RESULTS)
    price_truth = read_csv(PRICE_TRUTH)
    confidence = read_csv(CONFIDENCE)
    diagnostics = read_csv(DIAGNOSTICS)

    if results.empty:
        empty = pd.DataFrame(columns=OUTPUT_COLUMNS)
        empty.to_csv(OUT_CALIBRATION, index=False)
        empty.to_csv(OUT_CURVES, index=False)
        empty.to_csv(OUT_BUCKETS, index=False)
        print("[probability_calibration] no result rows; wrote empty calibration outputs")
        return

    enriched = merge_price_truth(results, price_truth)
    required = {"rated_price", "market_price", "result"}
    missing = required - set(enriched.columns)
    if missing:
        empty = pd.DataFrame(columns=OUTPUT_COLUMNS)
        empty.to_csv(OUT_CALIBRATION, index=False)
        empty.to_csv(OUT_CURVES, index=False)
        empty.to_csv(OUT_BUCKETS, index=False)
        print(f"[probability_calibration] missing required columns {sorted(missing)}; wrote empty calibration outputs")
        return

    enriched = add_factors(enriched)
    settled = enriched[
        enriched["result"].map(lambda x: upper(x) in {"WON", "WIN", "LOST", "LOSS"}) &
        enriched["model_probability"].notna() &
        enriched["market_probability"].notna()
    ].copy()
    settled["actual_win"] = settled["result"].map(lambda x: 1 if upper(x) in {"WON", "WIN"} else 0)

    if settled.empty:
        empty = pd.DataFrame(columns=OUTPUT_COLUMNS)
        empty.to_csv(OUT_CALIBRATION, index=False)
        empty.to_csv(OUT_CURVES, index=False)
        empty.to_csv(OUT_BUCKETS, index=False)
        print("[probability_calibration] no settled rows with rated/market price; wrote empty calibration outputs")
        return

    bucket_analysis = analyse_buckets(settled)
    curves = build_curves(bucket_analysis)
    calibration = bucket_analysis.sort_values(["bucket_type", "calibration_error"], ascending=[True, False])

    calibration.to_csv(OUT_CALIBRATION, index=False)
    curves.to_csv(OUT_CURVES, index=False)
    bucket_analysis.to_csv(OUT_BUCKETS, index=False)

    non_overall = bucket_analysis[bucket_analysis["bucket_type"] != "OVERALL"].copy()
    overconfident = non_overall.sort_values("calibration_error", ascending=False).head(1)
    sharp = non_overall[non_overall["reliability_grade"] == "SHARP"].sort_values(["settled_rows", "roi_pct"], ascending=[False, False]).head(1)
    biggest_error = non_overall.assign(abs_error=non_overall["calibration_error"].abs()).sort_values("abs_error", ascending=False).head(1)
    overall = bucket_analysis[bucket_analysis["bucket_type"] == "OVERALL"].iloc[0]
    model_abs = abs(float(overall["calibration_error"]))
    market_abs = abs(float(overall["market_calibration_error"]))
    closer = "MODEL" if model_abs < market_abs else "MARKET" if market_abs < model_abs else "TIE"

    over_text = "NONE"
    if len(overconfident):
        row = overconfident.iloc[0]
        over_text = f"{row['bucket_type']}={row['bucket_value']} ({row['calibration_error']} pts)"

    sharp_text = "NONE"
    if len(sharp):
        row = sharp.iloc[0]
        sharp_text = f"{row['bucket_type']}={row['bucket_value']} ({row['calibration_error']} pts)"

    error_text = "NONE"
    if len(biggest_error):
        row = biggest_error.iloc[0]
        error_text = f"{row['bucket_type']}={row['bucket_value']} ({row['calibration_error']} pts; shift {row['recommended_probability_adjustment_pct']}%)"

    print("[probability_calibration] confidence rows available:", len(confidence))
    print("[probability_calibration] diagnostic rows available:", len(diagnostics))
    print("[probability_calibration] rows analysed:", len(settled))
    print("[probability_calibration] most overconfident structure:", over_text)
    print("[probability_calibration] sharpest structure:", sharp_text)
    print("[probability_calibration] model vs market closer:", closer)
    print("[probability_calibration] biggest calibration error:", error_text)
    print("[probability_calibration] recommended overall probability shift:", f"{overall['recommended_probability_adjustment_pct']}%")


if __name__ == "__main__":
    main()
