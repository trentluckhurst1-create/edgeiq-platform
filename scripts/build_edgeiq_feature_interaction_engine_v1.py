from itertools import combinations
from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "public" / "data"

RESULTS = DATA / "edgeiq_results_master.csv"
ATTRIBUTION = DATA / "edgeiq_feature_attribution_v1.csv"
ATTRIBUTION_RANKINGS = DATA / "edgeiq_feature_signal_rankings_v1.csv"
BAYESIAN = DATA / "edgeiq_bayesian_blending_v1.csv"

OUT_INTERACTIONS = DATA / "edgeiq_feature_interactions_v1.csv"
OUT_RANKINGS = DATA / "edgeiq_feature_interaction_rankings_v1.csv"

INTERACTION_COLUMNS = [
    "interaction_key",
    "feature_a",
    "value_a",
    "feature_b",
    "value_b",
    "rows",
    "settled_rows",
    "wins",
    "losses",
    "strike_rate",
    "turnover",
    "profit_loss",
    "roi_pct",
    "average_clv_pct",
    "beat_close_pct",
    "average_market_price",
    "average_overlay_pct",
    "interaction_grade",
    "recommendation",
]

RANKING_COLUMNS = [
    "ranking_type",
    "interaction_key",
    "feature_a",
    "value_a",
    "feature_b",
    "value_b",
    "metric_value",
    "interaction_grade",
    "recommendation",
    "reason",
]


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"[feature_interactions] missing {path.name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
        print(f"[feature_interactions] read {path.name}: {len(df)} rows")
        return df
    except pd.errors.EmptyDataError:
        print(f"[feature_interactions] empty {path.name}")
        return pd.DataFrame()
    except Exception as exc:
        print(f"[feature_interactions] warning: could not read {path.name}: {exc}")
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


def coalesced_text(df: pd.DataFrame, candidates: list[str]) -> pd.Series:
    values = pd.Series([""] * len(df), index=df.index)
    for col in candidates:
        if col not in df.columns:
            continue
        next_values = df[col].map(text)
        values = values.where(values != "", next_values)
    return values


def numeric_bucket(value, buckets: list[tuple[float, str]]) -> str:
    parsed = num(value)
    if parsed is None:
        return ""
    for limit, label in buckets:
        if parsed <= limit:
            return label
    return buckets[-1][1]


def odds_bucket(value) -> str:
    return numeric_bucket(value, [
        (2, "ODDS_<=2"),
        (4, "ODDS_2_TO_4"),
        (8, "ODDS_4_TO_8"),
        (15, "ODDS_8_TO_15"),
        (26, "ODDS_15_TO_26"),
        (9999, "ODDS_26_PLUS"),
    ])


def overlay_bucket(value) -> str:
    parsed = num(value)
    if parsed is None:
        return ""
    if parsed < 0:
        return "NEGATIVE"
    if parsed < 10:
        return "0_TO_10"
    if parsed < 25:
        return "10_TO_25"
    if parsed < 50:
        return "25_TO_50"
    if parsed < 100:
        return "50_TO_100"
    return "100_PLUS"


def distance_bucket(value) -> str:
    parsed = num(str(value).lower().replace("m", ""))
    if parsed is None:
        return ""
    if parsed <= 1100:
        return "SPRINT_<=1100"
    if parsed <= 1400:
        return "SPRINT_1200_1400"
    if parsed <= 1800:
        return "MILE_MIDDLE"
    if parsed <= 2400:
        return "STAYING"
    return "EXTREME_STAYING"


def grade_interaction(settled_rows: int, roi_pct: float | None, beat_close_pct: float | None) -> str:
    if settled_rows < 20:
        return "UNKNOWN"
    roi = roi_pct if roi_pct is not None else 0.0
    beat = beat_close_pct if beat_close_pct is not None else 0.0
    if roi > 0 and beat >= 45:
        return "STRONG_EDGE"
    if roi > -5 or beat >= 40:
        return "POSSIBLE_EDGE"
    if roi < -15 and beat < 35:
        return "TOXIC"
    if roi < -5:
        return "WEAK"
    return "NEUTRAL"


def recommendation_for(grade: str) -> str:
    return {
        "STRONG_EDGE": "PROTECT",
        "POSSIBLE_EDGE": "TEST_MORE",
        "NEUTRAL": "TEST_MORE",
        "WEAK": "DOWNWEIGHT",
        "TOXIC": "SUPPRESS",
        "UNKNOWN": "IGNORE_SMALL_SAMPLE",
    }.get(grade, "IGNORE_SMALL_SAMPLE")


def add_result_flags(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    result = out.get("result", pd.Series([""] * len(out))).map(upper)
    out["_is_win"] = result.isin(["WON", "WIN", "1", "TRUE"])
    out["_is_loss"] = result.isin(["LOST", "LOSS", "LOSE", "0", "FALSE"])
    out["_is_settled"] = out["_is_win"] | out["_is_loss"] | result.isin(["VOID"])
    out["_stake"] = pd.to_numeric(out.get("stake", 0), errors="coerce").fillna(0)
    out["_profit_loss"] = pd.to_numeric(out.get("profit_loss", 0), errors="coerce")
    out["_clv_pct"] = pd.to_numeric(out.get("clv_pct", pd.NA), errors="coerce")
    out["_market_price"] = pd.to_numeric(out.get("market_price", pd.NA), errors="coerce")
    out["_overlay_pct"] = pd.to_numeric(out.get("overlay_pct", pd.NA), errors="coerce")
    return out


def build_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    features = pd.DataFrame(index=df.index)
    feature_sources = {
        "market_regime": ["market_regime_v2", "market_regime", "regime"],
        "confidence": ["calibrated_confidence_label", "confidence_band_v1", "confidence"],
        "suppression_risk_grade": ["suppression_risk_grade"],
        "final_execution_state": ["final_execution_state", "execution_state"],
        "track": ["track"],
        "race_class": ["race_class"],
        "speed_map_bucket": ["speed_map_bucket"],
        "track_condition": ["track_condition"],
        "first_starter_flag": ["first_starter_flag", "first_starter", "is_first_starter"],
    }
    for feature, cols in feature_sources.items():
        values = coalesced_text(df, cols)
        if values.ne("").any():
            features[feature] = values.map(upper)

    if "market_price" in df.columns:
        values = df["market_price"].map(odds_bucket)
        if values.ne("").any():
            features["odds_bucket"] = values
    if "overlay_pct" in df.columns:
        values = df["overlay_pct"].map(overlay_bucket)
        if values.ne("").any():
            features["overlay_bucket"] = values
    if "distance" in df.columns:
        values = df["distance"].map(distance_bucket)
        if values.ne("").any():
            features["distance_bucket"] = values

    return features


def requested_pairs(features: pd.DataFrame) -> list[tuple[str, str]]:
    candidates = [
        ("market_regime", "confidence"),
        ("market_regime", "odds_bucket"),
        ("market_regime", "overlay_bucket"),
        ("confidence", "odds_bucket"),
        ("confidence", "overlay_bucket"),
        ("suppression_risk_grade", "market_regime"),
        ("final_execution_state", "market_regime"),
        ("track", "market_regime"),
        ("race_class", "market_regime"),
        ("distance_bucket", "market_regime"),
        ("speed_map_bucket", "market_regime"),
        ("track_condition", "market_regime"),
        ("first_starter_flag", "market_regime"),
    ]
    available = [(a, b) for a, b in candidates if a in features.columns and b in features.columns]
    if available:
        return available
    return list(combinations(features.columns.tolist(), 2))


def summarise_interaction(df: pd.DataFrame, features: pd.DataFrame, feature_a: str, feature_b: str) -> list[dict]:
    working = df.copy()
    working["_value_a"] = features[feature_a].map(text)
    working["_value_b"] = features[feature_b].map(text)
    working = working[(working["_value_a"] != "") & (working["_value_b"] != "")]
    rows = []

    for (value_a, value_b), group in working.groupby(["_value_a", "_value_b"], dropna=True):
        settled = group[group["_is_settled"]]
        settled_rows = len(settled)
        wins = int(settled["_is_win"].sum()) if settled_rows else 0
        losses = int(settled["_is_loss"].sum()) if settled_rows else 0
        strike = (wins / (wins + losses) * 100.0) if (wins + losses) else 0.0
        turnover = float(settled["_stake"].sum()) if settled_rows else 0.0
        profit = float(settled["_profit_loss"].dropna().sum()) if settled_rows else 0.0
        roi = (profit / turnover * 100.0) if turnover > 0 else None
        clv = settled["_clv_pct"].dropna()
        avg_clv = float(clv.mean()) if len(clv) else None
        beat_close = (float((clv > 0).sum()) / len(clv) * 100.0) if len(clv) else None
        market_price = group["_market_price"].dropna()
        overlay = group["_overlay_pct"].dropna()
        grade = grade_interaction(settled_rows, roi, beat_close)

        rows.append({
            "interaction_key": f"{feature_a}={value_a} | {feature_b}={value_b}",
            "feature_a": feature_a,
            "value_a": value_a,
            "feature_b": feature_b,
            "value_b": value_b,
            "rows": len(group),
            "settled_rows": settled_rows,
            "wins": wins,
            "losses": losses,
            "strike_rate": round(strike, 2),
            "turnover": round(turnover, 2),
            "profit_loss": round(profit, 2),
            "roi_pct": round(roi, 2) if roi is not None else "",
            "average_clv_pct": round(avg_clv, 2) if avg_clv is not None else "",
            "beat_close_pct": round(beat_close, 2) if beat_close is not None else "",
            "average_market_price": round(float(market_price.mean()), 2) if len(market_price) else "",
            "average_overlay_pct": round(float(overlay.mean()), 2) if len(overlay) else "",
            "interaction_grade": grade,
            "recommendation": recommendation_for(grade),
        })

    return rows


def ranking_row(ranking_type: str, row: pd.Series, metric: str, reason: str) -> dict:
    return {
        "ranking_type": ranking_type,
        "interaction_key": row.get("interaction_key", ""),
        "feature_a": row.get("feature_a", ""),
        "value_a": row.get("value_a", ""),
        "feature_b": row.get("feature_b", ""),
        "value_b": row.get("value_b", ""),
        "metric_value": row.get(metric, ""),
        "interaction_grade": row.get("interaction_grade", ""),
        "recommendation": row.get("recommendation", ""),
        "reason": reason,
    }


def make_rankings(interactions: pd.DataFrame) -> pd.DataFrame:
    if interactions.empty:
        return pd.DataFrame(columns=RANKING_COLUMNS)

    rankings = []
    settled = pd.to_numeric(interactions["settled_rows"], errors="coerce").fillna(0)
    enough = interactions[settled >= 20].copy()

    positive = enough[enough["interaction_grade"].isin(["STRONG_EDGE", "POSSIBLE_EDGE"])].copy()
    toxic = enough[enough["interaction_grade"].isin(["TOXIC", "WEAK"])].copy()
    clv = enough[pd.to_numeric(enough["average_clv_pct"], errors="coerce").notna()].copy()
    recs = enough[enough["recommendation"].isin(["PROTECT", "SUPPRESS"])].copy()

    if not positive.empty:
        positive["_metric"] = pd.to_numeric(positive["roi_pct"], errors="coerce")
        for _, row in positive.dropna(subset=["_metric"]).sort_values("_metric", ascending=False).head(5).iterrows():
            rankings.append(ranking_row("TOP_POSITIVE_INTERACTIONS", row, "roi_pct", "Highest settled ROI interaction"))

    if not toxic.empty:
        toxic["_metric"] = pd.to_numeric(toxic["roi_pct"], errors="coerce")
        for _, row in toxic.dropna(subset=["_metric"]).sort_values("_metric", ascending=True).head(5).iterrows():
            rankings.append(ranking_row("WORST_TOXIC_INTERACTIONS", row, "roi_pct", "Worst settled ROI interaction"))

    if not clv.empty:
        clv["_metric"] = pd.to_numeric(clv["average_clv_pct"], errors="coerce")
        for _, row in clv.dropna(subset=["_metric"]).sort_values("_metric", ascending=False).head(5).iterrows():
            rankings.append(ranking_row("TOP_CLV_INTERACTIONS", row, "average_clv_pct", "Highest average CLV interaction"))

    for _, row in recs.head(5).iterrows():
        rankings.append(ranking_row("PROTECT_SUPPRESS_RECOMMENDATIONS", row, "roi_pct", "Actionable interaction recommendation"))

    return pd.DataFrame(rankings, columns=RANKING_COLUMNS)


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    results = read_csv(RESULTS)
    attribution = read_csv(ATTRIBUTION)
    attribution_rankings = read_csv(ATTRIBUTION_RANKINGS)
    bayesian = read_csv(BAYESIAN)

    if results.empty:
        pd.DataFrame(columns=INTERACTION_COLUMNS).to_csv(OUT_INTERACTIONS, index=False)
        pd.DataFrame(columns=RANKING_COLUMNS).to_csv(OUT_RANKINGS, index=False)
        print("[feature_interactions] no results rows; wrote empty outputs")
        return

    results = add_result_flags(results)
    features = build_feature_frame(results)
    pairs = requested_pairs(features)

    rows = []
    for feature_a, feature_b in pairs:
        rows.extend(summarise_interaction(results, features, feature_a, feature_b))

    interactions = pd.DataFrame(rows, columns=INTERACTION_COLUMNS)
    if not interactions.empty:
        interactions = interactions.sort_values(
            ["interaction_grade", "settled_rows", "roi_pct"],
            ascending=[True, False, False],
            na_position="last",
        )

    rankings = make_rankings(interactions)
    interactions.to_csv(OUT_INTERACTIONS, index=False)
    rankings.to_csv(OUT_RANKINGS, index=False)

    strong_edges = int((interactions["interaction_grade"] == "STRONG_EDGE").sum()) if not interactions.empty else 0
    toxic = int((interactions["interaction_grade"] == "TOXIC").sum()) if not interactions.empty else 0
    top_positive = rankings[rankings["ranking_type"] == "TOP_POSITIVE_INTERACTIONS"].head(1)
    worst_toxic = rankings[rankings["ranking_type"] == "WORST_TOXIC_INTERACTIONS"].head(1)

    print("[feature_interactions] feature columns available:", ", ".join(features.columns.tolist()) or "none")
    print("[feature_interactions] pairs tested:", len(pairs))
    print("[feature_interactions] interactions tested:", len(interactions))
    print("[feature_interactions] strong edges:", strong_edges)
    print("[feature_interactions] toxic interactions:", toxic)
    print("[feature_interactions] attribution rows read:", len(attribution))
    print("[feature_interactions] attribution rankings read:", len(attribution_rankings))
    print("[feature_interactions] bayesian rows read:", len(bayesian))
    print("[feature_interactions] top positive interaction:", top_positive.iloc[0].to_dict() if len(top_positive) else "none")
    print("[feature_interactions] worst toxic interaction:", worst_toxic.iloc[0].to_dict() if len(worst_toxic) else "none")


if __name__ == "__main__":
    main()
