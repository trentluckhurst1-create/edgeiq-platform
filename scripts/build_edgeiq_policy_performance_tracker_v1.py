from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "public" / "data"

POLICY_ENGINE = DATA / "edgeiq_policy_engine_v1.csv"
RESULTS = DATA / "edgeiq_results_master.csv"
COUNTERFACTUAL = DATA / "edgeiq_counterfactual_engine_v1.csv"
LIVE = DATA / "edgeiq_execution_board_live.csv"
OUT_TRACKER = DATA / "edgeiq_policy_performance_tracker_v1.csv"
OUT_RANKINGS = DATA / "edgeiq_policy_rankings_v1.csv"

TRACKER_COLUMNS = [
    "policy_name",
    "tracking_basis",
    "total_rows",
    "settled_rows",
    "wins",
    "losses",
    "strike_rate",
    "turnover",
    "profit_loss",
    "roi_pct",
    "average_clv_pct",
    "beat_close_pct",
    "max_drawdown",
    "volatility",
    "stability_score",
    "suppression_rate",
    "execution_rate",
    "experimental_exposure",
    "policy_survival_score",
    "policy_risk_score",
    "policy_efficiency_score",
]

RANKING_COLUMNS = [
    "ranking_type",
    "policy_name",
    "metric_value",
    "recommended_active_policy",
    "reason",
]


POLICY_TO_COUNTERFACTUAL = {
    "DEFAULT": "ORIGINAL",
    "SAFE_MODE": "HIGH_CONFIDENCE_ONLY",
    "HIGH_CONFIDENCE_ONLY": "HIGH_CONFIDENCE_ONLY",
    "PROTECTED_EDGES_ONLY": "PROTECTED_EDGES_ONLY",
    "LOW_DRAWDOWN_MODE": "HIGH_CONFIDENCE_ONLY",
    "EXPERIMENTAL_MODE": "CLV_FILTER",
}


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"[policy_performance] missing {path.name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
        print(f"[policy_performance] read {path.name}: {len(df)} rows")
        return df
    except Exception as exc:
        print(f"[policy_performance] warning: could not read {path.name}: {exc}")
        return pd.DataFrame()


def text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def upper(value) -> str:
    return text(value).upper()


def num(value, default=0.0) -> float:
    try:
        parsed = float(value)
    except Exception:
        return default
    return parsed if pd.notna(parsed) else default


def numeric(df: pd.DataFrame, column: str, default=0.0) -> pd.Series:
    if column not in df.columns:
        return pd.Series([default] * len(df), index=df.index, dtype="float64")
    return pd.to_numeric(df[column], errors="coerce")


def max_drawdown(profit_loss: pd.Series) -> float:
    if profit_loss.empty:
        return 0.0
    equity = profit_loss.fillna(0).cumsum()
    drawdown = equity - equity.cummax()
    return float(drawdown.min()) if len(drawdown) else 0.0


def original_baseline(results: pd.DataFrame) -> dict:
    if results.empty or "result" not in results.columns:
        return {
            "total_rows": 0,
            "settled_rows": 0,
            "wins": 0,
            "losses": 0,
            "strike_rate": 0,
            "turnover": 0,
            "profit_loss": 0,
            "roi_pct": 0,
            "average_clv_pct": 0,
            "beat_close_pct": 0,
            "max_drawdown": 0,
            "volatility": 0,
            "stability_score": 0,
        }

    settled = results[results["result"].map(lambda x: upper(x) in {"WON", "WIN", "LOST", "LOSS"})].copy()
    if "stake" in settled.columns:
        stake_filter = numeric(settled, "stake", 0).fillna(0) > 0
        if stake_filter.any():
            settled = settled[stake_filter].copy()

    wins = int(settled["result"].map(lambda x: upper(x) in {"WON", "WIN"}).sum()) if len(settled) else 0
    losses = int(settled["result"].map(lambda x: upper(x) in {"LOST", "LOSS"}).sum()) if len(settled) else 0
    stake = numeric(settled, "stake", 0).fillna(0)
    pl = numeric(settled, "profit_loss", 0).fillna(0)
    clv = numeric(settled, "clv_pct", pd.NA)
    turnover = float(stake.sum())
    profit = float(pl.sum())
    roi = (profit / turnover * 100.0) if turnover else 0.0
    beat_close = (float((clv > 0).sum()) / int(clv.notna().sum()) * 100.0) if int(clv.notna().sum()) else 0.0
    avg_clv = float(clv.dropna().mean()) if int(clv.notna().sum()) else 0.0
    dd = max_drawdown(pl)
    vol = float(pl.std()) if len(pl.dropna()) > 1 else 0.0
    stability = roi + (avg_clv * 0.4) + (beat_close * 0.2) + dd

    return {
        "total_rows": len(settled),
        "settled_rows": len(settled),
        "wins": wins,
        "losses": losses,
        "strike_rate": round((wins / (wins + losses) * 100.0), 2) if wins + losses else 0,
        "turnover": round(turnover, 4),
        "profit_loss": round(profit, 4),
        "roi_pct": round(roi, 2),
        "average_clv_pct": round(avg_clv, 2),
        "beat_close_pct": round(beat_close, 2),
        "max_drawdown": round(dd, 4),
        "volatility": round(vol, 4),
        "stability_score": round(stability, 2),
    }


def policy_counterfactual_row(counterfactual: pd.DataFrame, policy_name: str) -> pd.Series | None:
    if counterfactual.empty:
        return None
    mapped = POLICY_TO_COUNTERFACTUAL.get(policy_name, "")
    if not mapped or "policy_name" not in counterfactual.columns:
        return None
    match = counterfactual[counterfactual["policy_name"].astype(str).str.upper() == mapped]
    if match.empty:
        return None
    return match.iloc[0]


def live_environment(live: pd.DataFrame) -> dict:
    total = len(live)
    if total == 0:
        return {
            "suppression_rate": 0.0,
            "execution_rate": 0.0,
            "fake_overlay_rate": 0.0,
            "low_confidence_rate": 0.0,
            "volatility_rate": 0.0,
            "active_policy": "DEFAULT",
            "dominant_regime": "UNKNOWN",
        }

    action_col = "policy_decision" if "policy_decision" in live.columns else "execution_action"
    actions = live[action_col].astype(str).str.upper() if action_col in live.columns else pd.Series([""] * total)
    suppression_rate = float(actions.isin(["SUPPRESS", "PASS"]).sum()) / total * 100.0
    execution_rate = float(actions.isin(["EXECUTE", "MAX_BET", "PRIORITY_EXECUTE", "REDUCED_EXECUTE"]).sum()) / total * 100.0
    realism = live["overlay_realism_grade"].astype(str).str.upper() if "overlay_realism_grade" in live.columns else pd.Series([""] * total)
    fake_overlay_rate = float(realism.str.contains("FAKE", na=False).sum()) / total * 100.0
    confidence = live["calibrated_confidence_label"].astype(str).str.upper() if "calibrated_confidence_label" in live.columns else pd.Series([""] * total)
    low_confidence_rate = float(confidence.isin(["VERY_LOW", "LOW"]).sum()) / total * 100.0
    regime_col = "market_regime_v2" if "market_regime_v2" in live.columns else "market_regime"
    regime = live[regime_col].astype(str).str.upper() if regime_col in live.columns else pd.Series(["UNKNOWN"] * total)
    dominant_regime = text(regime.value_counts().index[0]) if len(regime.value_counts()) else "UNKNOWN"
    volatility_rate = float(regime.str.contains("VOLATILE|TOXIC|STEAM", na=False).sum()) / total * 100.0
    active_policy = text(live["active_policy"].dropna().iloc[0]) if "active_policy" in live.columns and live["active_policy"].notna().any() else "DEFAULT"

    return {
        "suppression_rate": suppression_rate,
        "execution_rate": execution_rate,
        "fake_overlay_rate": fake_overlay_rate,
        "low_confidence_rate": low_confidence_rate,
        "volatility_rate": volatility_rate,
        "active_policy": active_policy,
        "dominant_regime": dominant_regime,
    }


def score_policy(row: dict, policy_def: pd.Series | None, env: dict) -> dict:
    roi = float(row["roi_pct"])
    clv = float(row["average_clv_pct"])
    beat = float(row["beat_close_pct"])
    drawdown = abs(float(row["max_drawdown"]))
    volatility = float(row["volatility"])
    suppression_rate = float(row["suppression_rate"])
    execution_rate = float(row["execution_rate"])

    survival = max(0.0, 100.0 + roi + (clv * 0.5) + (beat * 0.25) - drawdown)
    risk = max(0.0, drawdown + (volatility * 10.0) + max(0.0, 45.0 - beat) + (env["fake_overlay_rate"] * 0.25))
    efficiency = roi + clv + (beat * 0.2) - (suppression_rate * 0.05) + (execution_rate * 0.03)

    if policy_def is not None and text(policy_def.get("drawdown_protection")).upper() in {"HIGH", "MAX"}:
        risk *= 0.9
        survival += 5
    if policy_def is not None and text(policy_def.get("suppression_aggressiveness")).upper() == "LOW":
        risk *= 1.1

    row["policy_survival_score"] = round(survival, 2)
    row["policy_risk_score"] = round(risk, 2)
    row["policy_efficiency_score"] = round(efficiency, 2)
    return row


def build_tracker(policy_engine: pd.DataFrame, results: pd.DataFrame, counterfactual: pd.DataFrame, live: pd.DataFrame) -> pd.DataFrame:
    env = live_environment(live)
    baseline = original_baseline(results)
    rows = []

    if policy_engine.empty or "policy_name" not in policy_engine.columns:
        policy_names = ["DEFAULT"]
        policy_defs = {}
    else:
        policy_names = [text(v) for v in policy_engine["policy_name"].dropna().tolist()]
        policy_defs = {text(row["policy_name"]): row for _, row in policy_engine.iterrows()}

    for policy_name in policy_names:
        cf = policy_counterfactual_row(counterfactual, policy_name)
        if cf is None or policy_name == "DEFAULT":
            metrics = baseline.copy()
            basis = "RESULTS_MASTER_BASELINE"
        else:
            metrics = {
                "total_rows": int(num(cf.get("simulated_rows"), 0)),
                "settled_rows": int(num(cf.get("simulated_rows"), 0)),
                "wins": int(num(cf.get("wins"), 0)),
                "losses": int(num(cf.get("losses"), 0)),
                "strike_rate": num(cf.get("strike_rate"), 0),
                "turnover": num(cf.get("turnover"), 0),
                "profit_loss": num(cf.get("profit_loss"), 0),
                "roi_pct": num(cf.get("roi_pct"), 0),
                "average_clv_pct": num(cf.get("average_clv_pct"), 0),
                "beat_close_pct": num(cf.get("beat_close_pct"), 0),
                "max_drawdown": num(cf.get("max_drawdown"), 0),
                "volatility": num(cf.get("volatility"), 0),
                "stability_score": num(cf.get("edge_stability_score"), 0),
            }
            basis = f"HISTORICAL_SIMULATION:{text(cf.get('policy_name'))}"

        active_live = live[live["active_policy"].astype(str).str.upper() == policy_name.upper()] if "active_policy" in live.columns else pd.DataFrame()
        live_total = len(active_live) if len(active_live) else len(live)
        action_col = "policy_decision" if "policy_decision" in live.columns else "execution_action"
        actions = (active_live[action_col] if len(active_live) and action_col in active_live.columns else live[action_col] if action_col in live.columns else pd.Series(dtype=str)).astype(str).str.upper()
        suppression_rate = float(actions.isin(["SUPPRESS", "PASS"]).sum()) / live_total * 100.0 if live_total else 0.0
        execution_rate = float(actions.isin(["EXECUTE", "MAX_BET", "PRIORITY_EXECUTE", "REDUCED_EXECUTE"]).sum()) / live_total * 100.0 if live_total else 0.0
        experimental_exposure = execution_rate * (1.0 if policy_name == "EXPERIMENTAL_MODE" else 0.25 if "EXPERIMENT" in policy_name else 0.0)

        row = {
            "policy_name": policy_name,
            "tracking_basis": basis,
            **metrics,
            "suppression_rate": round(suppression_rate, 2),
            "execution_rate": round(execution_rate, 2),
            "experimental_exposure": round(experimental_exposure, 2),
        }
        rows.append(score_policy(row, policy_defs.get(policy_name), env))

    return pd.DataFrame(rows, columns=TRACKER_COLUMNS)


def recommended_policy(tracker: pd.DataFrame, env: dict) -> tuple[str, str]:
    if tracker.empty:
        return "DEFAULT", "No policy tracker rows available."

    fake = env["fake_overlay_rate"]
    low_conf = env["low_confidence_rate"]
    suppression = env["suppression_rate"]
    volatility = env["volatility_rate"]

    if fake >= 40 or low_conf >= 70 or volatility >= 40:
        candidate = "SAFE_MODE"
        reason = f"Defensive environment: fake overlays {fake:.1f}%, low confidence {low_conf:.1f}%, volatility {volatility:.1f}%."
    elif suppression >= 70:
        candidate = "PROTECTED_EDGES_ONLY"
        reason = f"High live suppression level {suppression:.1f}%; preserve only historically protected segments."
    else:
        ranked = tracker.sort_values(["policy_efficiency_score", "policy_risk_score"], ascending=[False, True])
        candidate = text(ranked.iloc[0]["policy_name"])
        reason = "Selected by best efficiency score with risk tiebreak."

    if candidate not in set(tracker["policy_name"].astype(str)):
        safest = tracker.sort_values("policy_risk_score", ascending=True).iloc[0]
        return text(safest["policy_name"]), f"{reason} Requested candidate missing, using lowest risk tracked policy."
    return candidate, reason


def build_rankings(tracker: pd.DataFrame, env: dict) -> pd.DataFrame:
    if tracker.empty:
        return pd.DataFrame(columns=RANKING_COLUMNS)

    rec_policy, rec_reason = recommended_policy(tracker, env)
    rows = []

    def add(kind: str, row: pd.Series, metric: str, reason: str):
        rows.append({
            "ranking_type": kind,
            "policy_name": text(row.get("policy_name")),
            "metric_value": row.get(metric, ""),
            "recommended_active_policy": rec_policy,
            "reason": reason,
        })

    add("RECOMMENDED_ACTIVE_POLICY", tracker[tracker["policy_name"] == rec_policy].iloc[0], "policy_efficiency_score", rec_reason)
    add("SAFEST_POLICY", tracker.sort_values("policy_risk_score", ascending=True).iloc[0], "policy_risk_score", "Lowest calculated risk score.")
    add("BEST_ROI_POLICY", tracker.sort_values("roi_pct", ascending=False).iloc[0], "roi_pct", "Highest historical/simulated ROI.")
    add("BEST_CLV_POLICY", tracker.sort_values("average_clv_pct", ascending=False).iloc[0], "average_clv_pct", "Highest average CLV.")
    add("BEST_STABILITY_POLICY", tracker.sort_values("stability_score", ascending=False).iloc[0], "stability_score", "Highest stability score.")
    add("BEST_DRAWDOWN_CONTROL", tracker.sort_values("max_drawdown", ascending=False).iloc[0], "max_drawdown", "Smallest historical/simulated drawdown.")
    add("MOST_DANGEROUS_POLICY", tracker.sort_values("policy_risk_score", ascending=False).iloc[0], "policy_risk_score", "Highest calculated risk score.")

    return pd.DataFrame(rows, columns=RANKING_COLUMNS)


def main():
    DATA.mkdir(parents=True, exist_ok=True)

    policy_engine = read_csv(POLICY_ENGINE)
    results = read_csv(RESULTS)
    counterfactual = read_csv(COUNTERFACTUAL)
    live = read_csv(LIVE)

    tracker = build_tracker(policy_engine, results, counterfactual, live)
    rankings = build_rankings(tracker, live_environment(live))

    tracker.to_csv(OUT_TRACKER, index=False)
    rankings.to_csv(OUT_RANKINGS, index=False)

    rec = rankings[rankings["ranking_type"] == "RECOMMENDED_ACTIVE_POLICY"]
    top = rankings[rankings["ranking_type"] == "BEST_ROI_POLICY"]
    worst = rankings[rankings["ranking_type"] == "MOST_DANGEROUS_POLICY"]

    print("[policy_performance] policies tracked:", len(tracker))
    print("[policy_performance] recommended policy:", text(rec.iloc[0]["policy_name"]) if len(rec) else "NONE")
    print("[policy_performance] top policy:", text(top.iloc[0]["policy_name"]) if len(top) else "NONE")
    print("[policy_performance] worst policy:", text(worst.iloc[0]["policy_name"]) if len(worst) else "NONE")


if __name__ == "__main__":
    main()
