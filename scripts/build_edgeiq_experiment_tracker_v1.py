from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "public" / "data"

HYPOTHESES = DATA / "edgeiq_hypothesis_engine_v1.csv"
RESULTS = DATA / "edgeiq_results_master.csv"
LIVE = DATA / "edgeiq_execution_board_live.csv"
OUT = DATA / "edgeiq_experiment_tracker_v1.csv"

OUT_COLUMNS = [
    "hypothesis_id",
    "proposed_rule",
    "status",
    "matched_historical_rows",
    "matched_live_rows",
    "post_test_settled_rows",
    "post_test_profit_loss",
    "post_test_roi_pct",
    "post_test_clv_pct",
    "post_test_beat_close_pct",
    "current_verdict",
]


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"[experiment_tracker] missing {path.name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
        print(f"[experiment_tracker] read {path.name}: {len(df)} rows")
        return df
    except Exception as exc:
        print(f"[experiment_tracker] warning: could not read {path.name}: {exc}")
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


def num_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series([pd.NA] * len(df), index=df.index)
    return pd.to_numeric(df[column], errors="coerce")


def first_existing(df: pd.DataFrame, names: list[str]) -> str | None:
    for name in names:
        if name in df.columns:
            return name
    return None


def odds_bucket(price) -> str:
    value = num(price)
    if value is None or value <= 0:
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
    value = num(overlay)
    if value is None:
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
    value = num(confidence)
    if value is None:
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


def distance_bucket(distance) -> str:
    value = num(distance)
    if value is None or value <= 0:
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
    value = num(field_size)
    if value is None or value <= 0:
        return "UNKNOWN"
    if value <= 7:
        return "SMALL_FIELD"
    if value <= 11:
        return "MEDIUM_FIELD"
    if value <= 15:
        return "LARGE_FIELD"
    return "MAX_FIELD"


def enrich_factors(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        return out

    market_price_col = first_existing(out, ["market_price", "sportsbet_price", "current_price", "fixed_odds", "win_odds"])
    overlay_col = first_existing(out, ["overlay_pct", "edge_pct", "final_edge_pct_v4_1", "final_edge_v5_1"])
    adjusted_overlay_col = first_existing(out, ["adjusted_overlay_pct"])
    confidence_col = first_existing(out, ["confidence", "confidence_score", "calibrated_confidence_score", "confidence_score_v1"])
    distance_col = first_existing(out, ["distance", "race_distance", "distance_m"])
    field_col = first_existing(out, ["field_size", "_field_size_active", "runners", "runner_count"])

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
        "market_regime": ["market_regime", "regime"],
        "market_regime_v2": ["market_regime_v2"],
        "overlay_realism_grade": ["overlay_realism_grade"],
        "track": ["track"],
        "race_class": ["race_class", "class", "race_grade"],
    }

    for target, names in aliases.items():
        existing = first_existing(out, names)
        out[target] = out[existing].map(lambda x: upper(x) or "UNKNOWN") if existing else "UNKNOWN"

    return out


def settled_mask(df: pd.DataFrame) -> pd.Series:
    if "result" not in df.columns:
        return pd.Series([False] * len(df), index=df.index)
    return df["result"].map(lambda x: upper(x) in {"WON", "WIN", "LOST", "LOSS"})


def post_test_mask(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series([], dtype=bool)

    mask = pd.Series([False] * len(df), index=df.index)
    if "learned_suppression_applied" in df.columns:
        mask = mask | df["learned_suppression_applied"].astype(str).str.upper().isin(["TRUE", "1", "YES"])
    if "source_signal_file" in df.columns:
        mask = mask | df["source_signal_file"].astype(str).str.contains("execution_board_live|execution_board_terminal", case=False, na=False)
    if "final_execution_state" in df.columns and "execution_state" in df.columns:
        mask = mask | (df["final_execution_state"].astype(str).str.upper() != df["execution_state"].astype(str).str.upper())
    return mask


def match_rows(df: pd.DataFrame, factor: str, value: str) -> pd.DataFrame:
    if df.empty or factor not in df.columns:
        return pd.DataFrame(columns=df.columns)
    return df[df[factor].astype(str).str.upper() == upper(value)].copy()


def calculate_verdict(hypothesis: pd.Series, post_rows: pd.DataFrame, live_rows: int) -> str:
    status = upper(hypothesis.get("status"))
    priority = upper(hypothesis.get("priority"))
    if status == "PROTECT_EDGE" or priority == "PROTECT":
        return "PROTECT_EDGE"

    settled = len(post_rows)
    if settled < 10:
        return "AWAITING_SAMPLE"

    stake = num_series(post_rows, "stake").fillna(0)
    pl = num_series(post_rows, "profit_loss").fillna(0)
    turnover = float(stake.sum())
    profit = float(pl.sum())
    roi = (profit / turnover * 100.0) if turnover else 0.0
    clv = num_series(post_rows, "clv_pct")
    beat_close = (float((clv > 0).sum()) / int(clv.notna().sum()) * 100.0) if int(clv.notna().sum()) else 0.0

    if roi > 0 and beat_close >= 45:
        return "PROMISING"
    if roi >= -5 or beat_close >= 40:
        return "IMPROVING"
    if roi < -15 and beat_close < 35 and settled >= 20:
        return "RETIRE_RULE"
    if roi < 0:
        return "FAILING"
    if live_rows:
        return "AWAITING_SAMPLE"
    return "AWAITING_SAMPLE"


def main():
    DATA.mkdir(parents=True, exist_ok=True)

    hypotheses = read_csv(HYPOTHESES)
    results = enrich_factors(read_csv(RESULTS))
    live = enrich_factors(read_csv(LIVE))

    if hypotheses.empty:
        pd.DataFrame(columns=OUT_COLUMNS).to_csv(OUT, index=False)
        print("[experiment_tracker] no hypotheses; wrote empty tracker")
        return

    rows = []
    for _, hyp in hypotheses.iterrows():
        factor = text(hyp.get("trigger_factor"))
        value = text(hyp.get("trigger_value"))
        historical = match_rows(results, factor, value)
        live_matches = match_rows(live, factor, value)
        post_rows = historical[settled_mask(historical) & post_test_mask(historical)].copy()

        stake = num_series(post_rows, "stake").fillna(0)
        pl = num_series(post_rows, "profit_loss").fillna(0)
        clv = num_series(post_rows, "clv_pct")
        turnover = float(stake.sum()) if len(post_rows) else 0.0
        profit = float(pl.sum()) if len(post_rows) else 0.0
        roi = (profit / turnover * 100.0) if turnover else 0.0
        avg_clv = float(clv.dropna().mean()) if int(clv.notna().sum()) else 0.0
        beat_close = (float((clv > 0).sum()) / int(clv.notna().sum()) * 100.0) if int(clv.notna().sum()) else 0.0

        rows.append({
            "hypothesis_id": text(hyp.get("hypothesis_id")),
            "proposed_rule": text(hyp.get("proposed_rule")),
            "status": text(hyp.get("status")),
            "matched_historical_rows": len(historical),
            "matched_live_rows": len(live_matches),
            "post_test_settled_rows": len(post_rows),
            "post_test_profit_loss": round(profit, 4),
            "post_test_roi_pct": round(roi, 2),
            "post_test_clv_pct": round(avg_clv, 2),
            "post_test_beat_close_pct": round(beat_close, 2),
            "current_verdict": calculate_verdict(hyp, post_rows, len(live_matches)),
        })

    out = pd.DataFrame(rows, columns=OUT_COLUMNS)
    out.to_csv(OUT, index=False)

    verdict_counts = out["current_verdict"].value_counts(dropna=False).to_dict() if len(out) else {}
    print("[experiment_tracker] hypotheses tracked:", len(out))
    print("[experiment_tracker] matched live rows:", int(out["matched_live_rows"].sum()) if len(out) else 0)
    print("[experiment_tracker] post-test settled rows:", int(out["post_test_settled_rows"].sum()) if len(out) else 0)
    print("[experiment_tracker] verdict counts:", verdict_counts)
    if len(out):
        print("[experiment_tracker] top tracker rows:")
        print(out.head(8)[["hypothesis_id", "matched_live_rows", "post_test_settled_rows", "current_verdict"]].to_string(index=False))


if __name__ == "__main__":
    main()
