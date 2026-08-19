from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "public" / "data"

RESULTS = DATA / "edgeiq_results_master.csv"
LIVE = DATA / "edgeiq_execution_board_live.csv"
BAYESIAN = DATA / "edgeiq_bayesian_blending_v1.csv"
DIAGNOSTICS = DATA / "edgeiq_model_diagnostic_by_factor.csv"

OUT_ATTRIBUTION = DATA / "edgeiq_feature_attribution_v1.csv"
OUT_RANKINGS = DATA / "edgeiq_feature_signal_rankings_v1.csv"

ATTRIBUTION_COLUMNS = [
    "feature",
    "feature_value",
    "rows",
    "settled_rows",
    "wins",
    "losses",
    "strike_rate",
    "profit_loss",
    "roi_pct",
    "average_clv_pct",
    "beat_close_pct",
    "average_model_weight",
    "average_market_weight",
    "reliability_grade",
]

RANKING_COLUMNS = [
    "ranking_type",
    "feature",
    "feature_value",
    "metric_value",
    "reliability_grade",
    "reason",
]


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"[feature_attribution] missing {path.name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
        print(f"[feature_attribution] read {path.name}: {len(df)} rows")
        return df
    except pd.errors.EmptyDataError:
        print(f"[feature_attribution] empty {path.name}")
        return pd.DataFrame()
    except Exception as exc:
        print(f"[feature_attribution] warning: could not read {path.name}: {exc}")
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


def normal_key(df: pd.DataFrame) -> pd.Series:
    parts = []
    for col in ["track", "race_no", "horse"]:
        if col in df.columns:
            parts.append(df[col].map(lambda v: upper(v)))
        else:
            parts.append(pd.Series([""] * len(df), index=df.index))
    return parts[0] + "|" + parts[1] + "|" + parts[2]


def merge_runner_features(base: pd.DataFrame, extra: pd.DataFrame, columns: list[str], suffix: str) -> pd.DataFrame:
    if base.empty or extra.empty:
        return base
    if not {"track", "race_no", "horse"}.issubset(base.columns) or not {"track", "race_no", "horse"}.issubset(extra.columns):
        return base

    available = [col for col in columns if col in extra.columns]
    if not available:
        return base

    left = base.copy()
    right = extra.copy()
    left["_feature_key"] = normal_key(left)
    right["_feature_key"] = normal_key(right)
    right = right[["_feature_key"] + available].drop_duplicates("_feature_key", keep="last")
    merged = left.merge(right, on="_feature_key", how="left", suffixes=("", suffix))

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

    return merged.drop(columns=["_feature_key"], errors="ignore")


def first_existing(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def coalesced_text_series(df: pd.DataFrame, candidates: list[str]) -> pd.Series:
    values = pd.Series([""] * len(df), index=df.index)
    for col in candidates:
        if col not in df.columns:
            continue
        next_values = df[col].map(text)
        values = values.where(values != "", next_values)
    return values


def coalesced_raw_series(df: pd.DataFrame, candidates: list[str]) -> pd.Series | None:
    values = pd.Series([pd.NA] * len(df), index=df.index)
    found = False
    for col in candidates:
        if col not in df.columns:
            continue
        found = True
        next_values = df[col]
        current_text = values.map(text)
        values = values.where(current_text != "", next_values)
    return values if found else None


def numeric_bucket(value, buckets: list[tuple[float, str]]) -> str:
    parsed = num(value)
    if parsed is None:
        return ""
    for limit, label in buckets:
        if parsed <= limit:
            return label
    return buckets[-1][1]


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


def weight_bucket(value) -> str:
    parsed = num(value)
    if parsed is None:
        return ""
    if parsed < 0:
        parsed = abs(parsed)
    if parsed < 0.35:
        return "LOW_TRUST"
    if parsed < 0.5:
        return "MARKET_LEAN"
    if parsed < 0.65:
        return "BALANCED"
    return "MODEL_LEAN"


def rating_bucket(value) -> str:
    return numeric_bucket(value, [
        (40, "LOW_<=40"),
        (55, "MID_41_55"),
        (70, "HIGH_56_70"),
        (999, "ELITE_70_PLUS"),
    ])


def days_bucket(value) -> str:
    return numeric_bucket(value, [
        (7, "QUICK_BACKUP"),
        (21, "NORMAL_8_21"),
        (45, "FRESH_22_45"),
        (9999, "LONG_BREAK"),
    ])


def run_count_bucket(value) -> str:
    return numeric_bucket(value, [
        (0, "NO_OFFICIAL_RUNS"),
        (3, "LIGHTLY_RACED_1_3"),
        (10, "ESTABLISHED_4_10"),
        (999, "EXPOSED_11_PLUS"),
    ])


def result_flags(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    result = out.get("result", pd.Series([""] * len(out))).map(upper)
    out["_is_win"] = result.isin(["WON", "WIN", "1", "TRUE"])
    out["_is_loss"] = result.isin(["LOST", "LOSS", "LOSE", "0", "FALSE"])
    out["_is_settled"] = out["_is_win"] | out["_is_loss"] | result.isin(["VOID"])
    out["_stake"] = pd.to_numeric(out.get("stake", 0), errors="coerce").fillna(0)
    out["_profit_loss"] = pd.to_numeric(out.get("profit_loss", 0), errors="coerce")
    out["_clv_pct"] = pd.to_numeric(out.get("clv_pct", pd.NA), errors="coerce")
    out["_model_weight"] = pd.to_numeric(out.get("model_weight", pd.NA), errors="coerce")
    out["_market_weight"] = pd.to_numeric(out.get("market_weight", pd.NA), errors="coerce")
    return out


def reliability(settled_rows: int, roi_pct: float | None, avg_clv: float | None, beat_close: float | None) -> str:
    if settled_rows < 10:
        return "UNKNOWN"
    roi = roi_pct if roi_pct is not None else 0.0
    clv = avg_clv if avg_clv is not None else 0.0
    beat = beat_close if beat_close is not None else 0.0
    if settled_rows >= 20 and roi > 0 and beat >= 45 and clv >= 0:
        return "VALUE_DRIVER"
    if roi > 0 or (clv > 0 and beat >= 45):
        return "POSSIBLE_EDGE"
    if roi < -15 and beat < 35:
        return "TOXIC"
    if roi < -5 or clv < -5:
        return "WEAK"
    return "NEUTRAL"


def build_feature_values(df: pd.DataFrame) -> dict[str, pd.Series]:
    features: dict[str, pd.Series] = {}

    candidate_map = {
        "gear_changes": ["gear_changes", "gear_change", "gear"],
        "stewards_flags": ["stewards_flags", "stewards", "steward_flags"],
        "speed_map_bucket": ["speed_map_bucket"],
        "barrier": ["barrier"],
        "jockey": ["jockey"],
        "trainer": ["trainer"],
        "track_condition": ["track_condition"],
        "race_class": ["race_class"],
        "market_mover": ["market_mover"],
        "market_regime": ["market_regime_v2", "market_regime", "regime"],
        "overlay_realism_grade": ["overlay_realism_grade"],
        "suppression_risk_grade": ["suppression_risk_grade"],
        "calibrated_confidence": ["calibrated_confidence_label", "confidence_band_v1", "confidence"],
    }

    for feature, candidates in candidate_map.items():
        values = coalesced_text_series(df, candidates)
        if values.ne("").any():
            features[feature] = values

    distance_values = coalesced_raw_series(df, ["distance", "race_distance"])
    if distance_values is not None:
        values = distance_values.map(distance_bucket)
        if values.ne("").any():
            features["distance_bucket"] = values

    days_values = coalesced_raw_series(df, ["days_since_last_run", "days_since_last_flat"])
    if days_values is not None:
        values = days_values.map(days_bucket)
        if values.ne("").any():
            features["days_since_last_run_bucket"] = values

    runs_values = coalesced_raw_series(df, ["official_run_count", "official_run_count_v5", "summary_official_run_count"])
    if runs_values is not None:
        values = runs_values.map(run_count_bucket)
        if values.ne("").any():
            features["official_run_count_bucket"] = values

    peak_values = coalesced_raw_series(df, ["peak_rating", "summary_peak", "peak"])
    if peak_values is not None:
        values = peak_values.map(rating_bucket)
        if values.ne("").any():
            features["peak_rating_bucket"] = values

    last3_values = coalesced_raw_series(df, ["last3_flat_avg", "summary_3lsa", "3lsa"])
    if last3_values is not None:
        values = last3_values.map(rating_bucket)
        if values.ne("").any():
            features["last_3_average_bucket"] = values

    last5_values = coalesced_raw_series(df, ["last5_flat_avg", "summary_5lsa", "5lsa", "context_context_last5"])
    if last5_values is not None:
        values = last5_values.map(rating_bucket)
        if values.ne("").any():
            features["last_5_average_bucket"] = values

    if "model_weight" in df.columns:
        values = df["model_weight"].map(weight_bucket)
        if values.ne("").any():
            features["bayesian_model_weight_bucket"] = values

    if "market_weight" in df.columns:
        values = df["market_weight"].map(weight_bucket)
        if values.ne("").any():
            features["bayesian_market_weight_bucket"] = values

    return features


def summarise_feature(df: pd.DataFrame, feature: str, values: pd.Series) -> list[dict]:
    rows = []
    working = df.copy()
    working["_feature_value"] = values.map(text)
    working = working[working["_feature_value"] != ""]

    for value, group in working.groupby("_feature_value", dropna=True):
        settled = group[group["_is_settled"]]
        settled_rows = len(settled)
        wins = int(settled["_is_win"].sum()) if settled_rows else 0
        losses = int(settled["_is_loss"].sum()) if settled_rows else 0
        strike = (wins / (wins + losses) * 100.0) if (wins + losses) else 0.0
        profit = float(settled["_profit_loss"].dropna().sum()) if settled_rows else 0.0
        turnover = float(settled["_stake"].sum()) if settled_rows else 0.0
        roi = (profit / turnover * 100.0) if turnover > 0 else None
        clv = settled["_clv_pct"].dropna()
        avg_clv = float(clv.mean()) if len(clv) else None
        beat_close = (float((clv > 0).sum()) / len(clv) * 100.0) if len(clv) else None
        model_weight = group["_model_weight"].dropna()
        market_weight = group["_market_weight"].dropna()

        rows.append({
            "feature": feature,
            "feature_value": value,
            "rows": len(group),
            "settled_rows": settled_rows,
            "wins": wins,
            "losses": losses,
            "strike_rate": round(strike, 2),
            "profit_loss": round(profit, 2),
            "roi_pct": round(roi, 2) if roi is not None else "",
            "average_clv_pct": round(avg_clv, 2) if avg_clv is not None else "",
            "beat_close_pct": round(beat_close, 2) if beat_close is not None else "",
            "average_model_weight": round(float(model_weight.mean()), 4) if len(model_weight) else "",
            "average_market_weight": round(float(market_weight.mean()), 4) if len(market_weight) else "",
            "reliability_grade": reliability(settled_rows, roi, avg_clv, beat_close),
        })

    return rows


def metric_value(row: pd.Series, column: str) -> float:
    value = num(row.get(column), None)
    return value if value is not None else -999999.0


def make_rankings(attr: pd.DataFrame) -> pd.DataFrame:
    if attr.empty:
        return pd.DataFrame(columns=RANKING_COLUMNS)

    enough = attr[pd.to_numeric(attr["settled_rows"], errors="coerce").fillna(0) >= 10].copy()
    rankings = []

    def add_rows(ranking_type: str, frame: pd.DataFrame, metric: str, reason: str, ascending: bool = False, limit: int = 5):
        if frame.empty:
            return
        ranked = frame.copy()
        ranked["_metric"] = pd.to_numeric(ranked[metric], errors="coerce")
        ranked = ranked.dropna(subset=["_metric"]).sort_values("_metric", ascending=ascending).head(limit)
        for _, row in ranked.iterrows():
            rankings.append({
                "ranking_type": ranking_type,
                "feature": row.get("feature", ""),
                "feature_value": row.get("feature_value", ""),
                "metric_value": round(float(row["_metric"]), 4),
                "reliability_grade": row.get("reliability_grade", ""),
                "reason": reason,
            })

    positive = enough[enough["reliability_grade"].isin(["VALUE_DRIVER", "POSSIBLE_EDGE"])]
    toxic = enough[enough["reliability_grade"].isin(["TOXIC", "WEAK"])]
    clv = enough[pd.to_numeric(enough["average_clv_pct"], errors="coerce").notna()]
    model_trust = attr[pd.to_numeric(attr["average_model_weight"], errors="coerce").notna()].copy()
    downweight = toxic.copy()

    add_rows("STRONGEST_POSITIVE_DRIVERS", positive, "roi_pct", "Observational positive ROI/CLV segment")
    add_rows("STRONGEST_TOXIC_DRIVERS", toxic, "roi_pct", "Observational weak or toxic historical segment", ascending=True)
    add_rows("STRONGEST_CLV_DRIVERS", clv, "average_clv_pct", "Highest average CLV segment")
    add_rows("STRONGEST_MODEL_TRUST_DRIVERS", model_trust, "average_model_weight", "Highest Bayesian model-weight segment")
    add_rows("FEATURES_TO_DOWNWEIGHT", downweight, "roi_pct", "Candidate downweight segment based on settled results", ascending=True)
    add_rows("DEEPER_MODELLING_CANDIDATES", enough, "settled_rows", "Largest samples suitable for deeper modelling")

    return pd.DataFrame(rankings, columns=RANKING_COLUMNS)


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    results = read_csv(RESULTS)
    live = read_csv(LIVE)
    bayesian = read_csv(BAYESIAN)
    diagnostics = read_csv(DIAGNOSTICS)

    if results.empty:
        pd.DataFrame(columns=ATTRIBUTION_COLUMNS).to_csv(OUT_ATTRIBUTION, index=False)
        pd.DataFrame(columns=RANKING_COLUMNS).to_csv(OUT_RANKINGS, index=False)
        print("[feature_attribution] no results rows; wrote empty outputs")
        return

    live_feature_cols = [
        "gear_changes",
        "gear_change",
        "gear",
        "stewards_flags",
        "stewards",
        "steward_flags",
        "speed_map_bucket",
        "barrier",
        "jockey",
        "trainer",
        "track_condition",
        "race_class",
        "distance",
        "days_since_last_run",
        "days_since_last_flat",
        "official_run_count",
        "official_run_count_v5",
        "summary_official_run_count",
        "peak_rating",
        "summary_peak",
        "peak",
        "last3_flat_avg",
        "last5_flat_avg",
        "summary_3lsa",
        "summary_5lsa",
        "3lsa",
        "5lsa",
        "market_mover",
        "market_regime_v2",
        "market_regime",
        "overlay_realism_grade",
        "suppression_risk_grade",
        "calibrated_confidence_label",
        "confidence_band_v1",
    ]

    bayesian_cols = ["model_weight", "market_weight", "blended_overlay_pct", "blending_reason"]

    combined = merge_runner_features(results, live, live_feature_cols, "_live")
    combined = merge_runner_features(combined, bayesian, bayesian_cols, "_bayes")
    combined = result_flags(combined)

    features = build_feature_values(combined)
    rows = []
    for feature, values in features.items():
        rows.extend(summarise_feature(combined, feature, values))

    attribution = pd.DataFrame(rows, columns=ATTRIBUTION_COLUMNS)
    if not attribution.empty:
        attribution = attribution.sort_values(
            ["reliability_grade", "settled_rows", "roi_pct"],
            ascending=[True, False, False],
            na_position="last",
        )

    rankings = make_rankings(attribution)

    attribution.to_csv(OUT_ATTRIBUTION, index=False)
    rankings.to_csv(OUT_RANKINGS, index=False)

    strongest_positive = rankings[rankings["ranking_type"] == "STRONGEST_POSITIVE_DRIVERS"].head(1)
    strongest_toxic = rankings[rankings["ranking_type"] == "STRONGEST_TOXIC_DRIVERS"].head(1)
    strongest_clv = rankings[rankings["ranking_type"] == "STRONGEST_CLV_DRIVERS"].head(1)

    print("[feature_attribution] features analysed:", len(features))
    print("[feature_attribution] attribution rows:", len(attribution))
    print("[feature_attribution] rankings rows:", len(rankings))
    print("[feature_attribution] diagnostic factor rows read:", len(diagnostics))
    print("[feature_attribution] strongest positive driver:", strongest_positive.iloc[0].to_dict() if len(strongest_positive) else "none")
    print("[feature_attribution] strongest toxic driver:", strongest_toxic.iloc[0].to_dict() if len(strongest_toxic) else "none")
    print("[feature_attribution] strongest CLV driver:", strongest_clv.iloc[0].to_dict() if len(strongest_clv) else "none")


if __name__ == "__main__":
    main()
