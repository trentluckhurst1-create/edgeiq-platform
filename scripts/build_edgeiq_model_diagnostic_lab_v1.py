from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "public" / "data"

RESULTS = DATA / "edgeiq_results_master.csv"
PRICE_TRUTH = DATA / "edgeiq_price_truth_adjustments.csv"
SUPPRESSION = DATA / "edgeiq_suppression_intelligence.csv"
CONFIDENCE = DATA / "edgeiq_confidence_calibration_v1.csv"

OUT_LAB = DATA / "edgeiq_model_diagnostic_lab_v1.csv"
OUT_FACTOR = DATA / "edgeiq_model_diagnostic_by_factor.csv"
OUT_RECS = DATA / "edgeiq_model_diagnostic_recommendations.csv"


LAB_COLUMNS = [
    "factor",
    "factor_value",
    "rows",
    "settled_rows",
    "wins",
    "losses",
    "strike_rate",
    "turnover",
    "profit_loss",
    "roi_pct",
    "average_odds",
    "average_clv_pct",
    "beat_close_pct",
    "average_raw_overlay",
    "average_adjusted_overlay",
    "drawdown_contribution",
    "reliability_grade",
    "recommendation",
    "reason",
]

REC_COLUMNS = [
    "recommendation_type",
    "factor",
    "factor_value",
    "reliability_grade",
    "settled_rows",
    "roi_pct",
    "beat_close_pct",
    "average_clv_pct",
    "profit_loss",
    "recommendation",
    "reason",
]


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"[model_diagnostic_lab] missing {path.name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
        print(f"[model_diagnostic_lab] read {path.name}: {len(df)} rows")
        return df
    except Exception as exc:
        print(f"[model_diagnostic_lab] warning: could not read {path.name}: {exc}")
        return pd.DataFrame()


def clean_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def norm_key(value) -> str:
    return clean_text(value).upper().replace("  ", " ")


def num_series(df: pd.DataFrame, column: str, default=0.0) -> pd.Series:
    if column not in df.columns:
        return pd.Series([default] * len(df), index=df.index, dtype="float64")
    return pd.to_numeric(df[column], errors="coerce")


def first_existing(df: pd.DataFrame, names: list[str]) -> str | None:
    for name in names:
        if name in df.columns:
            return name
    return None


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


def distance_bucket(distance) -> str:
    try:
        value = float(distance)
    except Exception:
        return "UNKNOWN"
    if not pd.notna(value) or value <= 0:
        return "UNKNOWN"
    if value < 1100:
        return "SPRINT_UNDER_1100"
    if value < 1400:
        return "SPRINT_1100_1399"
    if value < 1800:
        return "MILE_1400_1799"
    if value < 2200:
        return "MIDDLE_1800_2199"
    return "STAYING_2200_PLUS"


def field_size_bucket(field_size) -> str:
    try:
        value = float(field_size)
    except Exception:
        return "UNKNOWN"
    if not pd.notna(value) or value <= 0:
        return "UNKNOWN"
    if value <= 7:
        return "SMALL_FIELD"
    if value <= 11:
        return "MEDIUM_FIELD"
    if value <= 15:
        return "LARGE_FIELD"
    return "MAX_FIELD"


def confidence_bucket(confidence) -> str:
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


def result_is_won(value) -> bool:
    return clean_text(value).upper() in {"WON", "WIN"}


def result_is_lost(value) -> bool:
    return clean_text(value).upper() in {"LOST", "LOSS"}


def reliability_grade(settled_rows, roi_pct, beat_close_pct) -> str:
    if settled_rows < 20:
        return "UNKNOWN"
    if roi_pct < -15 and beat_close_pct < 35:
        return "TOXIC"
    if roi_pct > 0 and beat_close_pct >= 45:
        return "PROMISING"
    if roi_pct < -5:
        return "WEAK"
    if roi_pct > -5 or beat_close_pct >= 40:
        return "WATCH"
    return "WEAK"


def recommendation_for(row: dict) -> tuple[str, str]:
    grade = clean_text(row.get("reliability_grade")).upper()
    settled = int(row.get("settled_rows") or 0)
    roi = float(row.get("roi_pct") or 0)
    beat = float(row.get("beat_close_pct") or 0)
    clv = float(row.get("average_clv_pct") or 0)

    if settled < 20:
        return "IGNORE_UNTIL_MORE_SAMPLE", f"Only {settled} settled rows; sample is below diagnostic threshold."
    if grade == "TOXIC":
        return "KILL", f"ROI {roi:.1f}% and beat-close {beat:.1f}% are both below toxic thresholds."
    if roi < -15 or clv < -8:
        return "SUPPRESS", f"ROI {roi:.1f}% / CLV {clv:.1f}% indicates persistent negative expectancy."
    if grade == "WEAK":
        return "REDUCE_STAKE", f"ROI {roi:.1f}% is below model tolerance."
    if beat < 40:
        return "REQUIRE_HIGHER_CONFIDENCE", f"Beat-close {beat:.1f}% is below 40%."
    return "ALLOW", "Segment is not showing a data-backed suppression case."


def make_key(df: pd.DataFrame) -> pd.Series:
    parts = []
    for col in ["race_date", "track", "race_no", "horse"]:
        if col in df.columns:
            parts.append(df[col].map(norm_key))
        else:
            parts.append(pd.Series([""] * len(df), index=df.index))
    return parts[0] + "|" + parts[1] + "|" + parts[2] + "|" + parts[3]


def merge_price_truth(results: pd.DataFrame, price_truth: pd.DataFrame) -> pd.DataFrame:
    if results.empty or price_truth.empty:
        return results

    required = {"race_date", "track", "race_no", "horse"}
    if not required.issubset(results.columns) or not required.issubset(price_truth.columns):
        return results

    enrich_cols = [
        "adjusted_overlay_pct",
        "adjusted_rated_price",
        "overlay_realism_grade",
        "price_truth_adjustment_pct",
        "price_truth_execution_action",
    ]
    available = [c for c in enrich_cols if c in price_truth.columns]
    if not available:
        return results

    left = results.copy()
    right = price_truth.copy()
    left["_diagnostic_key"] = make_key(left)
    right["_diagnostic_key"] = make_key(right)
    right = right[["_diagnostic_key"] + available].drop_duplicates("_diagnostic_key", keep="last")

    merged = left.merge(right, on="_diagnostic_key", how="left", suffixes=("", "_price_truth"))
    for col in available:
        price_col = f"{col}_price_truth"
        if price_col in merged.columns:
            if col in merged.columns:
                merged[col] = merged[col].where(merged[col].astype(str).str.strip() != "", merged[price_col])
                merged[col] = merged[col].fillna(merged[price_col])
            else:
                merged[col] = merged[price_col]
            merged = merged.drop(columns=[price_col])
    return merged.drop(columns=["_diagnostic_key"], errors="ignore")


def add_factor_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    market_price_col = first_existing(out, ["market_price", "sportsbet_price", "price"])
    overlay_col = first_existing(out, ["overlay_pct", "raw_overlay_pct"])
    adjusted_overlay_col = first_existing(out, ["adjusted_overlay_pct", "price_truth_adjusted_overlay_pct"])
    confidence_col = first_existing(out, ["confidence", "confidence_score", "calibrated_confidence_score"])
    distance_col = first_existing(out, ["distance", "race_distance", "distance_m"])
    field_col = first_existing(out, ["field_size", "runners", "runner_count"])

    out["odds_bucket"] = out[market_price_col].map(odds_bucket) if market_price_col else "UNKNOWN"
    out["overlay_bucket"] = out[overlay_col].map(overlay_bucket) if overlay_col else "UNKNOWN"
    out["adjusted_overlay_bucket"] = out[adjusted_overlay_col].map(overlay_bucket) if adjusted_overlay_col else "UNKNOWN"
    out["confidence_bucket"] = out[confidence_col].map(confidence_bucket) if confidence_col else "UNKNOWN"
    out["distance_bucket"] = out[distance_col].map(distance_bucket) if distance_col else "UNKNOWN"
    out["field_size_bucket"] = out[field_col].map(field_size_bucket) if field_col else "UNKNOWN"

    aliases = {
        "calibrated_confidence_label": ["calibrated_confidence_label", "confidence_label"],
        "suppression_risk_grade": ["suppression_risk_grade", "risk_grade"],
        "final_execution_state": ["final_execution_state", "execution_action"],
        "original_execution_state": ["original_execution_state", "price_truth_original_execution_action"],
        "market_regime": ["regime", "market_regime"],
        "market_regime_v2": ["market_regime_v2"],
        "overlay_realism_grade": ["overlay_realism_grade"],
        "track": ["track"],
        "race_class": ["race_class", "class", "race_grade"],
    }

    for target, names in aliases.items():
        existing = first_existing(out, names)
        out[target] = out[existing].map(lambda x: clean_text(x).upper() or "UNKNOWN") if existing else "UNKNOWN"

    return out


def analyse_factor(df: pd.DataFrame, factor: str) -> list[dict]:
    if factor not in df.columns:
        return []

    rows = []
    for value, group in df.groupby(factor, dropna=False):
        factor_value = clean_text(value) or "UNKNOWN"
        if factor_value == "UNKNOWN":
            continue

        result_col = group["result"] if "result" in group.columns else pd.Series([""] * len(group), index=group.index)
        settled_mask = result_col.map(lambda x: result_is_won(x) or result_is_lost(x))
        settled = group[settled_mask].copy()
        settled_rows = len(settled)
        wins = int(settled["result"].map(result_is_won).sum()) if "result" in settled.columns else 0
        losses = int(settled["result"].map(result_is_lost).sum()) if "result" in settled.columns else 0

        stake = num_series(settled, "stake", 0.0).fillna(0)
        pl = num_series(settled, "profit_loss", 0.0).fillna(0)
        clv = num_series(settled, "clv_pct", pd.NA)
        odds = num_series(settled, "market_price", pd.NA)
        raw_overlay = num_series(group, "overlay_pct", pd.NA)
        adjusted_overlay = num_series(group, "adjusted_overlay_pct", pd.NA)

        turnover = float(stake.sum()) if settled_rows else 0.0
        profit_loss = float(pl.sum()) if settled_rows else 0.0
        roi = (profit_loss / turnover * 100.0) if turnover else 0.0
        strike = (wins / settled_rows * 100.0) if settled_rows else 0.0
        beat_close = (float((clv > 0).sum()) / int(clv.notna().sum()) * 100.0) if int(clv.notna().sum()) else 0.0
        avg_clv = float(clv.dropna().mean()) if int(clv.notna().sum()) else 0.0
        avg_odds = float(odds.dropna().mean()) if int(odds.notna().sum()) else 0.0
        avg_raw_overlay = float(raw_overlay.dropna().mean()) if int(raw_overlay.notna().sum()) else 0.0
        avg_adjusted_overlay = float(adjusted_overlay.dropna().mean()) if int(adjusted_overlay.notna().sum()) else 0.0
        drawdown_contribution = profit_loss if profit_loss < 0 else 0.0

        grade = reliability_grade(settled_rows, roi, beat_close)
        row = {
            "factor": factor,
            "factor_value": factor_value,
            "rows": len(group),
            "settled_rows": settled_rows,
            "wins": wins,
            "losses": losses,
            "strike_rate": round(strike, 2),
            "turnover": round(turnover, 4),
            "profit_loss": round(profit_loss, 4),
            "roi_pct": round(roi, 2),
            "average_odds": round(avg_odds, 4),
            "average_clv_pct": round(avg_clv, 2),
            "beat_close_pct": round(beat_close, 2),
            "average_raw_overlay": round(avg_raw_overlay, 2),
            "average_adjusted_overlay": round(avg_adjusted_overlay, 2),
            "drawdown_contribution": round(drawdown_contribution, 4),
            "reliability_grade": grade,
        }
        rec, reason = recommendation_for(row)
        row["recommendation"] = rec
        row["reason"] = reason
        rows.append(row)

    return rows


def overall_recommendations(lab: pd.DataFrame) -> pd.DataFrame:
    recs = []
    if lab.empty:
        return pd.DataFrame(columns=REC_COLUMNS)

    actionable = lab[lab["reliability_grade"].isin(["TOXIC", "WEAK", "PROMISING"])].copy()
    if actionable.empty:
        actionable = lab.copy()

    negative = lab[lab["profit_loss"] < 0].sort_values(["profit_loss", "settled_rows"], ascending=[True, False])
    positive = lab[(lab["reliability_grade"] == "PROMISING")].sort_values(["roi_pct", "settled_rows"], ascending=[False, False])
    fake = lab[
        (lab["factor"].isin(["overlay_realism_grade", "overlay_bucket", "adjusted_overlay_bucket"])) &
        (lab["profit_loss"] < 0)
    ].sort_values(["profit_loss", "average_raw_overlay"], ascending=[True, False])

    def add(kind: str, row: pd.Series, recommendation: str, reason: str):
        if row is None or row.empty:
            return
        recs.append({
            "recommendation_type": kind,
            "factor": row.get("factor", ""),
            "factor_value": row.get("factor_value", ""),
            "reliability_grade": row.get("reliability_grade", ""),
            "settled_rows": row.get("settled_rows", 0),
            "roi_pct": row.get("roi_pct", 0),
            "beat_close_pct": row.get("beat_close_pct", 0),
            "average_clv_pct": row.get("average_clv_pct", 0),
            "profit_loss": row.get("profit_loss", 0),
            "recommendation": recommendation,
            "reason": reason,
        })

    if len(negative):
        row = negative.iloc[0]
        add("BIGGEST_LOSS_DRIVER", row, row.get("recommendation", "REDUCE_STAKE"), f"{row['factor']}={row['factor_value']} has the largest loss contribution ({row['profit_loss']}).")
    if len(positive):
        row = positive.iloc[0]
        add("BEST_PROMISING_SEGMENT", row, "ALLOW", f"{row['factor']}={row['factor_value']} is profitable with {row['beat_close_pct']}% beat-close.")
    if len(fake):
        row = fake.iloc[0]
        add("WORST_FAKE_OVERLAY_PATTERN", row, row.get("recommendation", "SUPPRESS"), f"{row['factor']}={row['factor_value']} is the weakest overlay-related loss pattern.")

    raw_overlay = lab[lab["factor"] == "overlay_bucket"]
    adjusted_overlay = lab[lab["factor"] == "adjusted_overlay_bucket"]
    raw_bad = int(raw_overlay[raw_overlay["reliability_grade"].isin(["TOXIC", "WEAK"])].shape[0]) if len(raw_overlay) else 0
    adjusted_bad = int(adjusted_overlay[adjusted_overlay["reliability_grade"].isin(["TOXIC", "WEAK"])].shape[0]) if len(adjusted_overlay) else 0

    recs.append({
        "recommendation_type": "RAW_RATED_PRICE_DIAGNOSIS",
        "factor": "overlay_bucket",
        "factor_value": "RAW_OVERLAY_STRUCTURE",
        "reliability_grade": "DIAGNOSTIC",
        "settled_rows": int(raw_overlay["settled_rows"].sum()) if len(raw_overlay) else 0,
        "roi_pct": round(float(raw_overlay["profit_loss"].sum()) / float(raw_overlay["turnover"].sum()) * 100, 2) if len(raw_overlay) and float(raw_overlay["turnover"].sum()) else 0,
        "beat_close_pct": round(float(raw_overlay["beat_close_pct"].mean()), 2) if len(raw_overlay) else 0,
        "average_clv_pct": round(float(raw_overlay["average_clv_pct"].mean()), 2) if len(raw_overlay) else 0,
        "profit_loss": round(float(raw_overlay["profit_loss"].sum()), 4) if len(raw_overlay) else 0,
        "recommendation": "REVIEW_RATED_PRICE_AGGRESSION" if raw_bad else "ALLOW",
        "reason": f"Raw overlay buckets contain {raw_bad} weak/toxic segments.",
    })

    recs.append({
        "recommendation_type": "ADJUSTED_OVERLAY_DIAGNOSIS",
        "factor": "adjusted_overlay_bucket",
        "factor_value": "PRICE_TRUTH_OVERLAY_STRUCTURE",
        "reliability_grade": "DIAGNOSTIC",
        "settled_rows": int(adjusted_overlay["settled_rows"].sum()) if len(adjusted_overlay) else 0,
        "roi_pct": round(float(adjusted_overlay["profit_loss"].sum()) / float(adjusted_overlay["turnover"].sum()) * 100, 2) if len(adjusted_overlay) and float(adjusted_overlay["turnover"].sum()) else 0,
        "beat_close_pct": round(float(adjusted_overlay["beat_close_pct"].mean()), 2) if len(adjusted_overlay) else 0,
        "average_clv_pct": round(float(adjusted_overlay["average_clv_pct"].mean()), 2) if len(adjusted_overlay) else 0,
        "profit_loss": round(float(adjusted_overlay["profit_loss"].sum()), 4) if len(adjusted_overlay) else 0,
        "recommendation": "PRICE_TRUTH_IMPROVING" if adjusted_bad < raw_bad else "KEEP_MONITORING_PRICE_TRUTH",
        "reason": f"Adjusted overlay buckets contain {adjusted_bad} weak/toxic segments versus {raw_bad} raw overlay weak/toxic segments.",
    })

    for _, row in actionable[actionable["reliability_grade"].isin(["TOXIC", "WEAK"])].head(20).iterrows():
        recs.append({
            "recommendation_type": "FACTOR_RECOMMENDATION",
            "factor": row.get("factor", ""),
            "factor_value": row.get("factor_value", ""),
            "reliability_grade": row.get("reliability_grade", ""),
            "settled_rows": row.get("settled_rows", 0),
            "roi_pct": row.get("roi_pct", 0),
            "beat_close_pct": row.get("beat_close_pct", 0),
            "average_clv_pct": row.get("average_clv_pct", 0),
            "profit_loss": row.get("profit_loss", 0),
            "recommendation": row.get("recommendation", ""),
            "reason": row.get("reason", ""),
        })

    return pd.DataFrame(recs, columns=REC_COLUMNS)


def main():
    DATA.mkdir(parents=True, exist_ok=True)

    results = read_csv(RESULTS)
    price_truth = read_csv(PRICE_TRUTH)
    suppression = read_csv(SUPPRESSION)
    confidence = read_csv(CONFIDENCE)

    if results.empty:
        pd.DataFrame(columns=LAB_COLUMNS).to_csv(OUT_LAB, index=False)
        pd.DataFrame(columns=LAB_COLUMNS).to_csv(OUT_FACTOR, index=False)
        pd.DataFrame(columns=REC_COLUMNS).to_csv(OUT_RECS, index=False)
        print("[model_diagnostic_lab] no results master rows; wrote empty diagnostic outputs")
        return

    enriched = merge_price_truth(results, price_truth)
    enriched = add_factor_columns(enriched)

    factors = [
        "odds_bucket",
        "overlay_bucket",
        "adjusted_overlay_bucket",
        "confidence_bucket",
        "calibrated_confidence_label",
        "suppression_risk_grade",
        "final_execution_state",
        "original_execution_state",
        "market_regime",
        "market_regime_v2",
        "overlay_realism_grade",
        "track",
        "race_class",
        "distance_bucket",
        "field_size_bucket",
    ]

    lab_rows = []
    for factor in factors:
        lab_rows.extend(analyse_factor(enriched, factor))

    lab = pd.DataFrame(lab_rows, columns=LAB_COLUMNS)
    if not lab.empty:
        lab = lab.sort_values(["reliability_grade", "profit_loss", "settled_rows"], ascending=[True, True, False])

    recommendations = overall_recommendations(lab)

    lab.to_csv(OUT_LAB, index=False)
    lab.to_csv(OUT_FACTOR, index=False)
    recommendations.to_csv(OUT_RECS, index=False)

    toxic = int((lab["reliability_grade"] == "TOXIC").sum()) if not lab.empty else 0
    promising = int((lab["reliability_grade"] == "PROMISING").sum()) if not lab.empty else 0
    biggest = recommendations[recommendations["recommendation_type"] == "BIGGEST_LOSS_DRIVER"]
    biggest_text = "NONE"
    if len(biggest):
        row = biggest.iloc[0]
        biggest_text = f"{row['factor']}={row['factor_value']} ({row['profit_loss']})"

    print("[model_diagnostic_lab] rows analysed:", len(enriched))
    print("[model_diagnostic_lab] factor rows:", len(lab))
    print("[model_diagnostic_lab] recommendations:", len(recommendations))
    print("[model_diagnostic_lab] toxic factors:", toxic)
    print("[model_diagnostic_lab] promising factors:", promising)
    print("[model_diagnostic_lab] biggest loss driver:", biggest_text)
    print("[model_diagnostic_lab] suppression rows available:", len(suppression))
    print("[model_diagnostic_lab] confidence rows available:", len(confidence))


if __name__ == "__main__":
    main()
