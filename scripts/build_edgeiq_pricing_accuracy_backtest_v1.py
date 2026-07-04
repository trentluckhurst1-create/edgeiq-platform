from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "public" / "data"

RESULTS = DATA / "edgeiq_results_master.csv"
PRICE_TRUTH = DATA / "edgeiq_price_truth_adjustments.csv"
SHRINKAGE = DATA / "edgeiq_probability_shrinkage_v1.csv"
CALIBRATION = DATA / "edgeiq_probability_calibration_v1.csv"

OUT_BACKTEST = DATA / "edgeiq_pricing_accuracy_backtest_v1.csv"
OUT_RANKINGS = DATA / "edgeiq_pricing_layer_rankings_v1.csv"

BACKTEST_COLUMNS = [
    "pricing_layer",
    "tracking_basis",
    "rows",
    "settled_rows",
    "predicted_probability",
    "actual_win_rate",
    "calibration_error",
    "roi_pct",
    "average_clv_pct",
    "beat_close_pct",
    "fake_overlay_rate",
    "executable_rate",
    "drawdown",
    "stability_score",
    "confidence_quality",
    "volatility_penalty",
    "overall_layer_score",
    "scientific_note",
]

RANKING_COLUMNS = [
    "ranking_type",
    "pricing_layer",
    "metric_value",
    "answer",
    "reason",
]


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"[pricing_backtest] missing {path.name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
        print(f"[pricing_backtest] read {path.name}: {len(df)} rows")
        return df
    except pd.errors.EmptyDataError:
        print(f"[pricing_backtest] empty {path.name}")
        return pd.DataFrame()
    except Exception as exc:
        print(f"[pricing_backtest] warning: could not read {path.name}: {exc}")
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


def numeric(df: pd.DataFrame, column: str, default=pd.NA) -> pd.Series:
    if column not in df.columns:
        return pd.Series([default] * len(df), index=df.index)
    return pd.to_numeric(df[column], errors="coerce")


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


def make_key(df: pd.DataFrame) -> pd.Series:
    parts = []
    for col in ["race_date", "track", "race_no", "horse"]:
        if col in df.columns:
            parts.append(df[col].map(upper))
        else:
            parts.append(pd.Series([""] * len(df), index=df.index))
    return parts[0] + "|" + parts[1] + "|" + parts[2] + "|" + parts[3]


def merge_price_truth(results: pd.DataFrame, price_truth: pd.DataFrame) -> pd.DataFrame:
    if results.empty or price_truth.empty:
        return results.copy()
    required = {"race_date", "track", "race_no", "horse"}
    if not required.issubset(results.columns) or not required.issubset(price_truth.columns):
        return results.copy()

    available = [c for c in ["adjusted_rated_price", "adjusted_overlay_pct", "overlay_realism_grade"] if c in price_truth.columns]
    if not available:
        return results.copy()

    left = results.copy()
    right = price_truth.copy()
    left["_price_key"] = make_key(left)
    right["_price_key"] = make_key(right)
    right = right[["_price_key"] + available].drop_duplicates("_price_key", keep="last")
    merged = left.merge(right, on="_price_key", how="left", suffixes=("", "_price_truth"))
    return merged.drop(columns=["_price_key"], errors="ignore")


def calibration_lookup(calibration: pd.DataFrame) -> dict:
    lookup = {}
    if calibration.empty or not {"bucket_type", "bucket_value"}.issubset(calibration.columns):
        return lookup
    rows = calibration[calibration["bucket_type"].astype(str) == "model_probability_bucket"]
    for _, row in rows.iterrows():
        lookup[upper(row.get("bucket_value"))] = row.to_dict()
    return lookup


def shrink_probability(raw_probability: float, lookup: dict) -> float:
    bucket = probability_bucket(raw_probability)
    row = lookup.get(bucket, {})
    grade = upper(row.get("reliability_grade"))
    shift = num(row.get("recommended_probability_adjustment_pct"), 0.0) or 0.0
    error = num(row.get("calibration_error"), 0.0) or 0.0

    if grade in {"TOXIC", "OVERCONFIDENT"} or error > 5:
        factor = max(0.25, min(1.0, 1.0 + min(shift, 0.0) / 100.0))
        if shift >= 0:
            factor = max(0.45, 1.0 - min(abs(error), 35.0) / 100.0)
    elif grade == "UNDERCONFIDENT":
        factor = min(1.15, 1.0 + max(shift, 0.0) / 300.0)
    elif grade == "SHARP":
        factor = 0.98
    elif grade == "ACCEPTABLE":
        factor = 0.94
    else:
        factor = 0.9
    return max(0.0025, min(0.95, raw_probability * factor))


def settled_base(results: pd.DataFrame) -> pd.DataFrame:
    if results.empty or not {"rated_price", "market_price", "result"}.issubset(results.columns):
        return pd.DataFrame()
    df = results.copy()
    df["rated_price_num"] = numeric(df, "rated_price")
    df["market_price_num"] = numeric(df, "market_price")
    df = df[
        df["result"].map(lambda x: upper(x) in {"WON", "WIN", "LOST", "LOSS"}) &
        df["rated_price_num"].gt(0) &
        df["market_price_num"].gt(0)
    ].copy()
    df["actual_win"] = df["result"].map(lambda x: 1 if upper(x) in {"WON", "WIN"} else 0)
    return df


def max_drawdown(profit_loss: pd.Series) -> float:
    if profit_loss.empty:
        return 0.0
    equity = profit_loss.fillna(0).cumsum()
    return float((equity - equity.cummax()).min())


def evaluate_layer(name: str, df: pd.DataFrame, probability: pd.Series, basis: str) -> dict:
    layer = df.copy()
    layer["layer_probability"] = pd.to_numeric(probability, errors="coerce")
    layer = layer[layer["layer_probability"].notna() & layer["layer_probability"].gt(0)].copy()
    rows = len(layer)
    wins = int(layer["actual_win"].sum()) if rows else 0
    actual = (wins / rows * 100.0) if rows else 0.0
    predicted = float(layer["layer_probability"].mean() * 100.0) if rows else 0.0
    error = predicted - actual

    fair_price = 1.0 / layer["layer_probability"].clip(lower=0.0025)
    layer["layer_overlay_pct"] = ((layer["market_price_num"] / fair_price) - 1.0) * 100.0
    executable = layer[layer["layer_overlay_pct"] > 0].copy()
    fake_overlay_rate = float(layer["layer_overlay_pct"].gt(100).sum()) / rows * 100.0 if rows else 0.0
    executable_rate = len(executable) / rows * 100.0 if rows else 0.0

    stake = numeric(executable, "stake", 0).fillna(0)
    pl = numeric(executable, "profit_loss", 0).fillna(0)
    clv = numeric(executable, "clv_pct")
    turnover = float(stake.sum()) if len(executable) else 0.0
    profit = float(pl.sum()) if len(executable) else 0.0
    roi = (profit / turnover * 100.0) if turnover else 0.0
    avg_clv = float(clv.dropna().mean()) if int(clv.notna().sum()) else 0.0
    beat_close = (float((clv > 0).sum()) / int(clv.notna().sum()) * 100.0) if int(clv.notna().sum()) else 0.0
    drawdown = max_drawdown(pl)
    volatility = float(pl.std()) if len(pl.dropna()) > 1 else 0.0
    confidence_quality = max(0.0, 100.0 - abs(error) * 4.0 - fake_overlay_rate * 0.4)
    volatility_penalty = volatility * 10.0 + abs(drawdown) * 0.25
    stability = confidence_quality + (avg_clv * 0.5) + (beat_close * 0.15) + roi * 0.2 - volatility_penalty
    overall = stability + executable_rate * 0.05 - fake_overlay_rate * 0.2

    note = "Historical settled backtest."
    if rows < 20:
        note = "Insufficient settled matched rows; do not rank as proven."

    return {
        "pricing_layer": name,
        "tracking_basis": basis,
        "rows": rows,
        "settled_rows": rows,
        "predicted_probability": round(predicted, 2),
        "actual_win_rate": round(actual, 2),
        "calibration_error": round(error, 2),
        "roi_pct": round(roi, 2),
        "average_clv_pct": round(avg_clv, 2),
        "beat_close_pct": round(beat_close, 2),
        "fake_overlay_rate": round(fake_overlay_rate, 2),
        "executable_rate": round(executable_rate, 2),
        "drawdown": round(drawdown, 4),
        "stability_score": round(stability, 2),
        "confidence_quality": round(confidence_quality, 2),
        "volatility_penalty": round(volatility_penalty, 2),
        "overall_layer_score": round(overall, 2),
        "scientific_note": note,
    }


def live_only_layer(name: str, df: pd.DataFrame, probability_col: str, fair_col: str, basis: str) -> dict:
    if df.empty:
        return evaluate_layer(name, pd.DataFrame(), pd.Series(dtype=float), basis)
    live = df.copy()
    if probability_col in live.columns:
        probability = pd.to_numeric(live[probability_col], errors="coerce")
    elif fair_col in live.columns:
        fair = pd.to_numeric(live[fair_col], errors="coerce")
        probability = 1.0 / fair.where(fair > 0)
    else:
        probability = pd.Series([pd.NA] * len(live), index=live.index)
    rows = int(probability.notna().sum())
    fake_rate = 0.0
    executable_rate = 0.0
    if rows and "market_price" in live.columns:
        market = pd.to_numeric(live["market_price"], errors="coerce")
        fair = 1.0 / probability.clip(lower=0.0025)
        overlay = ((market / fair) - 1.0) * 100.0
        fake_rate = float(overlay.gt(100).sum()) / rows * 100.0
        executable_rate = float(overlay.gt(0).sum()) / rows * 100.0
    return {
        "pricing_layer": name,
        "tracking_basis": basis,
        "rows": rows,
        "settled_rows": 0,
        "predicted_probability": round(float(probability.dropna().mean() * 100.0), 2) if rows else 0,
        "actual_win_rate": 0,
        "calibration_error": 0,
        "roi_pct": 0,
        "average_clv_pct": 0,
        "beat_close_pct": 0,
        "fake_overlay_rate": round(fake_rate, 2),
        "executable_rate": round(executable_rate, 2),
        "drawdown": 0,
        "stability_score": 0,
        "confidence_quality": 0,
        "volatility_penalty": 0,
        "overall_layer_score": -999,
        "scientific_note": "Live diagnostic only; no settled accuracy sample yet.",
    }


def rankings(backtest: pd.DataFrame) -> pd.DataFrame:
    proven = backtest[backtest["settled_rows"] >= 20].copy()
    if proven.empty:
        proven = backtest.copy()
    rows = []

    def add(kind: str, row: pd.Series, metric: str, answer: str, reason: str):
        rows.append({
            "ranking_type": kind,
            "pricing_layer": row.get("pricing_layer", ""),
            "metric_value": row.get(metric, ""),
            "answer": answer,
            "reason": reason,
        })

    sharpest = proven.assign(abs_error=proven["calibration_error"].abs()).sort_values("abs_error").iloc[0]
    safest = proven.sort_values("drawdown", ascending=False).iloc[0]
    fake_safe = backtest.sort_values(["fake_overlay_rate", "settled_rows"], ascending=[True, False]).iloc[0]
    executable = backtest.sort_values("executable_rate", ascending=False).iloc[0]
    overall = proven.sort_values("overall_layer_score", ascending=False).iloc[0]
    overaggressive = backtest.sort_values(["fake_overlay_rate", "calibration_error"], ascending=[False, False]).iloc[0]
    exec_quality = proven.sort_values(["beat_close_pct", "average_clv_pct"], ascending=[False, False]).iloc[0]

    shrink = backtest[backtest["pricing_layer"] == "SHRUNK_MODEL"]
    raw = backtest[backtest["pricing_layer"] == "RAW_MODEL"]
    improved = "UNKNOWN"
    reason = "Shrinkage sample unavailable."
    if len(shrink) and len(raw):
        s = shrink.iloc[0]
        r = raw.iloc[0]
        realism = abs(float(s["calibration_error"])) <= abs(float(r["calibration_error"]))
        fake = float(s["fake_overlay_rate"]) <= float(r["fake_overlay_rate"])
        stability = float(s["stability_score"]) >= float(r["stability_score"])
        improved = "YES" if realism and fake and stability else "PARTIAL" if realism or fake or stability else "NO"
        reason = f"realism={realism}; fake_overlay_reduction={fake}; stability={stability}"

    add("TOP_RANKED_LAYER", overall, "overall_layer_score", text(overall["pricing_layer"]), "Highest overall layer score among settled layers.")
    add("SAFEST_PRICING_LAYER", safest, "drawdown", text(safest["pricing_layer"]), "Best drawdown control.")
    add("SHARPEST_PRICING_LAYER", sharpest, "calibration_error", text(sharpest["pricing_layer"]), "Smallest absolute calibration error.")
    add("BIGGEST_FAKE_OVERLAY_REDUCTION", fake_safe, "fake_overlay_rate", text(fake_safe["pricing_layer"]), "Lowest fake overlay rate.")
    add("BEST_EXECUTABLE_PRESERVATION", executable, "executable_rate", text(executable["pricing_layer"]), "Highest executable opportunity rate.")
    add("MOST_OVERAGGRESSIVE_LAYER", overaggressive, "fake_overlay_rate", text(overaggressive["pricing_layer"]), "Highest fake overlay / overconfidence risk.")
    add("BEST_LONG_TERM_CANDIDATE", overall, "overall_layer_score", text(overall["pricing_layer"]), "Best balance of realism, opportunity and stability.")
    add("BEST_EXECUTION_QUALITY_LAYER", exec_quality, "beat_close_pct", text(exec_quality["pricing_layer"]), "Best beat-close and CLV profile.")
    rows.append({
        "ranking_type": "SHRINKAGE_IMPROVEMENT_ANSWER",
        "pricing_layer": "SHRUNK_MODEL",
        "metric_value": improved,
        "answer": improved,
        "reason": reason,
    })

    return pd.DataFrame(rows)


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    results = read_csv(RESULTS)
    price_truth = read_csv(PRICE_TRUTH)
    shrinkage = read_csv(SHRINKAGE)
    calibration = read_csv(CALIBRATION)

    merged = merge_price_truth(results, price_truth)
    base = settled_base(merged)
    if base.empty:
        pd.DataFrame(columns=BACKTEST_COLUMNS).to_csv(OUT_BACKTEST, index=False)
        pd.DataFrame(columns=["ranking_type", "pricing_layer", "metric_value", "answer", "reason"]).to_csv(OUT_RANKINGS, index=False)
        print("[pricing_backtest] no settled rows with prices; wrote empty outputs")
        return

    lookup = calibration_lookup(calibration)
    raw_prob = 1.0 / base["rated_price_num"]
    market_prob = 1.0 / base["market_price_num"]
    shrunk_prob = raw_prob.map(lambda p: shrink_probability(float(p), lookup))

    rows = [
        evaluate_layer("RAW_MODEL", base, raw_prob, "HISTORICAL_SETTLED"),
        evaluate_layer("MARKET_PRICE", base, market_prob, "HISTORICAL_SETTLED"),
        evaluate_layer("SHRUNK_MODEL", base, shrunk_prob, "HISTORICAL_CALIBRATION_SIMULATION"),
    ]

    if "adjusted_rated_price" in base.columns and pd.to_numeric(base["adjusted_rated_price"], errors="coerce").notna().any():
        adjusted = pd.to_numeric(base["adjusted_rated_price"], errors="coerce")
        rows.append(evaluate_layer("PRICE_TRUTH_V2", base[adjusted.gt(0)].copy(), 1.0 / adjusted[adjusted.gt(0)], "MATCHED_SETTLED_PRICE_TRUTH"))
    else:
        rows.append(live_only_layer("PRICE_TRUTH_V2", price_truth, "", "adjusted_rated_price", "LIVE_PRICE_TRUTH_ONLY"))

    backtest = pd.DataFrame(rows, columns=BACKTEST_COLUMNS)
    rank = rankings(backtest)
    backtest.to_csv(OUT_BACKTEST, index=False)
    rank.to_csv(OUT_RANKINGS, index=False)

    top = rank[rank["ranking_type"] == "TOP_RANKED_LAYER"].iloc[0]
    safest = rank[rank["ranking_type"] == "SAFEST_PRICING_LAYER"].iloc[0]
    sharpest = rank[rank["ranking_type"] == "SHARPEST_PRICING_LAYER"].iloc[0]
    fake = rank[rank["ranking_type"] == "BIGGEST_FAKE_OVERLAY_REDUCTION"].iloc[0]
    shrink = rank[rank["ranking_type"] == "SHRINKAGE_IMPROVEMENT_ANSWER"].iloc[0]

    print("[pricing_backtest] layers analysed:", len(backtest))
    print("[pricing_backtest] top ranked layer:", top["answer"])
    print("[pricing_backtest] safest layer:", safest["answer"])
    print("[pricing_backtest] sharpest layer:", sharpest["answer"])
    print("[pricing_backtest] biggest fake overlay reduction:", fake["answer"])
    print("[pricing_backtest] shrinkage improved realism:", shrink["answer"], "-", shrink["reason"])


if __name__ == "__main__":
    main()
