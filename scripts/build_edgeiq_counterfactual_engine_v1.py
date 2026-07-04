from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "public" / "data"

RESULTS = DATA / "edgeiq_results_master.csv"
HYPOTHESES = DATA / "edgeiq_hypothesis_engine_v1.csv"
DIAGNOSTICS = DATA / "edgeiq_model_diagnostic_by_factor.csv"
SUPPRESSION = DATA / "edgeiq_suppression_intelligence.csv"
OUT = DATA / "edgeiq_counterfactual_engine_v1.csv"

OUT_COLUMNS = [
    "policy_id",
    "policy_name",
    "policy_rule",
    "original_rows",
    "simulated_rows",
    "removed_rows",
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
    "edge_stability_score",
    "delta_vs_original_roi",
    "delta_vs_original_clv",
    "delta_vs_original_drawdown",
    "roi_rank",
    "drawdown_rank",
    "clv_rank",
    "stability_rank",
]


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"[counterfactual_engine] missing {path.name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
        print(f"[counterfactual_engine] read {path.name}: {len(df)} rows")
        return df
    except Exception as exc:
        print(f"[counterfactual_engine] warning: could not read {path.name}: {exc}")
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


def numeric(df: pd.DataFrame, column: str, default=0.0) -> pd.Series:
    if column not in df.columns:
        return pd.Series([default] * len(df), index=df.index, dtype="float64")
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


def enrich_results(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        return out

    price_col = first_existing(out, ["market_price", "sportsbet_price", "current_price", "fixed_odds", "win_odds"])
    overlay_col = first_existing(out, ["overlay_pct", "edge_pct"])
    adjusted_overlay_col = first_existing(out, ["adjusted_overlay_pct"])
    confidence_col = first_existing(out, ["calibrated_confidence_score", "confidence_score", "confidence"])

    out["odds_bucket"] = out[price_col].map(odds_bucket) if price_col else "UNKNOWN"
    out["overlay_bucket"] = out[overlay_col].map(overlay_bucket) if overlay_col else "UNKNOWN"
    out["adjusted_overlay_bucket"] = out[adjusted_overlay_col].map(overlay_bucket) if adjusted_overlay_col else "UNKNOWN"
    out["confidence_bucket"] = out[confidence_col].map(confidence_bucket) if confidence_col else "UNKNOWN"

    aliases = {
        "market_regime": ["market_regime", "regime"],
        "market_regime_v2": ["market_regime_v2"],
        "calibrated_confidence_label": ["calibrated_confidence_label", "confidence"],
        "overlay_realism_grade": ["overlay_realism_grade"],
        "suppression_risk_grade": ["suppression_risk_grade"],
        "final_execution_state": ["final_execution_state", "execution_state"],
        "original_execution_state": ["original_execution_state", "execution_state"],
    }

    for target, names in aliases.items():
        source = first_existing(out, names)
        out[target] = out[source].map(lambda x: upper(x) or "UNKNOWN") if source else "UNKNOWN"

    return out


def settled_executions(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "result" not in df.columns:
        return pd.DataFrame(columns=df.columns)
    settled = df[df["result"].map(lambda x: upper(x) in {"WON", "WIN", "LOST", "LOSS"})].copy()
    if "stake" in settled.columns:
        stake = numeric(settled, "stake", 0).fillna(0)
        if stake.gt(0).any():
            settled = settled[stake > 0].copy()
    return settled


def max_drawdown(profit_loss: pd.Series) -> float:
    if profit_loss.empty:
        return 0.0
    equity = profit_loss.fillna(0).cumsum()
    peak = equity.cummax()
    drawdown = equity - peak
    return float(drawdown.min()) if len(drawdown) else 0.0


def metrics(df: pd.DataFrame, original_rows: int, policy_id: str, policy_name: str, policy_rule: str) -> dict:
    wins = int(df["result"].map(lambda x: upper(x) in {"WON", "WIN"}).sum()) if "result" in df.columns else 0
    losses = int(df["result"].map(lambda x: upper(x) in {"LOST", "LOSS"}).sum()) if "result" in df.columns else 0
    settled = wins + losses
    stake = numeric(df, "stake", 0).fillna(0)
    pl = numeric(df, "profit_loss", 0).fillna(0)
    clv = numeric(df, "clv_pct", pd.NA)

    turnover = float(stake.sum()) if len(df) else 0.0
    profit = float(pl.sum()) if len(df) else 0.0
    roi = (profit / turnover * 100.0) if turnover else 0.0
    strike = (wins / settled * 100.0) if settled else 0.0
    avg_clv = float(clv.dropna().mean()) if int(clv.notna().sum()) else 0.0
    beat_close = (float((clv > 0).sum()) / int(clv.notna().sum()) * 100.0) if int(clv.notna().sum()) else 0.0
    dd = max_drawdown(pl)
    volatility = float(pl.std()) if len(pl.dropna()) > 1 else 0.0
    stability = roi + (avg_clv * 0.4) + (beat_close * 0.2) + dd

    return {
        "policy_id": policy_id,
        "policy_name": policy_name,
        "policy_rule": policy_rule,
        "original_rows": original_rows,
        "simulated_rows": len(df),
        "removed_rows": original_rows - len(df),
        "wins": wins,
        "losses": losses,
        "strike_rate": round(strike, 2),
        "turnover": round(turnover, 4),
        "profit_loss": round(profit, 4),
        "roi_pct": round(roi, 2),
        "average_clv_pct": round(avg_clv, 2),
        "beat_close_pct": round(beat_close, 2),
        "max_drawdown": round(dd, 4),
        "volatility": round(volatility, 4),
        "edge_stability_score": round(stability, 2),
    }


def positive_clv_structures(diagnostics: pd.DataFrame) -> dict[str, set[str]]:
    if diagnostics.empty:
        return {}
    required = {"factor", "factor_value", "average_clv_pct", "settled_rows"}
    if not required.issubset(diagnostics.columns):
        return {}
    d = diagnostics.copy()
    d["average_clv_pct"] = pd.to_numeric(d["average_clv_pct"], errors="coerce").fillna(0)
    d["settled_rows"] = pd.to_numeric(d["settled_rows"], errors="coerce").fillna(0)
    good = d[(d["average_clv_pct"] > 0) & (d["settled_rows"] >= 20)]
    out: dict[str, set[str]] = {}
    for factor, group in good.groupby("factor"):
        out[str(factor)] = {upper(v) for v in group["factor_value"].dropna().tolist()}
    return out


def protected_segments(hypotheses: pd.DataFrame) -> dict[str, set[str]]:
    if hypotheses.empty:
        return {}
    if not {"trigger_factor", "trigger_value", "status"}.issubset(hypotheses.columns):
        return {}
    protected = hypotheses[hypotheses["status"].astype(str).str.upper() == "PROTECT_EDGE"]
    out: dict[str, set[str]] = {}
    for factor, group in protected.groupby("trigger_factor"):
        out[str(factor)] = {upper(v) for v in group["trigger_value"].dropna().tolist()}
    return out


def in_any_structure(df: pd.DataFrame, structures: dict[str, set[str]]) -> pd.Series:
    if df.empty or not structures:
        return pd.Series([False] * len(df), index=df.index)
    mask = pd.Series([False] * len(df), index=df.index)
    for factor, values in structures.items():
        if factor in df.columns:
            mask = mask | df[factor].astype(str).str.upper().isin(values)
    return mask


def simulate_policies(base: pd.DataFrame, hypotheses: pd.DataFrame, diagnostics: pd.DataFrame) -> list[dict]:
    original_rows = len(base)
    policies = []

    policies.append(metrics(
        base[base["market_regime"] != "STEAMER"].copy(),
        original_rows,
        "POL-001",
        "NO_STEAMERS",
        "Suppress market_regime=STEAMER.",
    ))
    policies.append(metrics(
        base[base["overlay_bucket"] != "25_TO_50"].copy(),
        original_rows,
        "POL-002",
        "NO_25_TO_50_OVERLAYS",
        "Suppress overlay_bucket=25_TO_50.",
    ))
    policies.append(metrics(
        base[base["calibrated_confidence_label"].isin(["HIGH", "VERY_HIGH"]) | base["confidence_bucket"].isin(["HIGH", "VERY_HIGH"])].copy(),
        original_rows,
        "POL-003",
        "HIGH_CONFIDENCE_ONLY",
        "Only allow calibrated HIGH+ confidence rows.",
    ))
    policies.append(metrics(
        base[base["odds_bucket"] != "26_PLUS"].copy(),
        original_rows,
        "POL-004",
        "NO_ROUGHIES",
        "Suppress odds_bucket=26_PLUS.",
    ))
    policies.append(metrics(
        base[base["overlay_realism_grade"].isin(["REALISTIC", "UNKNOWN"])].copy(),
        original_rows,
        "POL-005",
        "PRICE_TRUTH_ONLY",
        "Only execute REALISTIC overlays where price truth exists; keep unknown historical rows.",
    ))

    reduced = base.copy()
    reduce_mask = reduced["suppression_risk_grade"].isin(["REDUCE", "KILL", "SUPPRESS"])
    if "stake" in reduced.columns:
        reduced.loc[reduce_mask, "stake"] = numeric(reduced.loc[reduce_mask], "stake", 0).fillna(0) * 0.5
        reduced.loc[reduce_mask, "profit_loss"] = numeric(reduced.loc[reduce_mask], "profit_loss", 0).fillna(0) * 0.5
    policies.append(metrics(
        reduced,
        original_rows,
        "POL-006",
        "REDUCED_RISK",
        "Halve stake on REDUCE/KILL/SUPPRESS structures.",
    ))

    clv_structures = positive_clv_structures(diagnostics)
    clv_mask = in_any_structure(base, clv_structures)
    policies.append(metrics(
        base[clv_mask].copy(),
        original_rows,
        "POL-007",
        "CLV_FILTER",
        "Only allow structures with historically positive average CLV and at least 20 settled rows.",
    ))

    protected = protected_segments(hypotheses)
    protected_mask = in_any_structure(base, protected)
    policies.append(metrics(
        base[protected_mask].copy(),
        original_rows,
        "POL-008",
        "PROTECTED_EDGES_ONLY",
        "Only allow PROTECT_EDGE hypothesis segments.",
    ))

    return policies


def add_deltas_and_ranks(df: pd.DataFrame, original: dict) -> pd.DataFrame:
    out = df.copy()
    out["delta_vs_original_roi"] = (out["roi_pct"] - float(original["roi_pct"])).round(2)
    out["delta_vs_original_clv"] = (out["average_clv_pct"] - float(original["average_clv_pct"])).round(2)
    out["delta_vs_original_drawdown"] = (out["max_drawdown"] - float(original["max_drawdown"])).round(4)
    out["roi_rank"] = out["delta_vs_original_roi"].rank(method="dense", ascending=False).astype(int)
    out["drawdown_rank"] = out["delta_vs_original_drawdown"].rank(method="dense", ascending=False).astype(int)
    out["clv_rank"] = out["delta_vs_original_clv"].rank(method="dense", ascending=False).astype(int)
    out["stability_rank"] = out["edge_stability_score"].rank(method="dense", ascending=False).astype(int)
    return out


def main():
    DATA.mkdir(parents=True, exist_ok=True)

    results = enrich_results(read_csv(RESULTS))
    hypotheses = read_csv(HYPOTHESES)
    diagnostics = read_csv(DIAGNOSTICS)
    suppression = read_csv(SUPPRESSION)

    base = settled_executions(results)
    if base.empty:
        pd.DataFrame(columns=OUT_COLUMNS).to_csv(OUT, index=False)
        print("[counterfactual_engine] no settled execution rows; wrote empty simulation file")
        return

    original = metrics(base, len(base), "BASE", "ORIGINAL", "Original settled execution history.")
    policy_rows = simulate_policies(base, hypotheses, diagnostics)
    out = pd.DataFrame(policy_rows)
    out = add_deltas_and_ranks(out, original)
    out = out[OUT_COLUMNS]
    out.to_csv(OUT, index=False)

    best_roi = out.sort_values("delta_vs_original_roi", ascending=False).iloc[0]
    best_dd = out.sort_values("delta_vs_original_drawdown", ascending=False).iloc[0]
    best_stability = out.sort_values("edge_stability_score", ascending=False).iloc[0]

    print("[counterfactual_engine] suppression rows available:", len(suppression))
    print("[counterfactual_engine] original settled rows:", len(base))
    print("[counterfactual_engine] policies simulated:", len(out))
    print("[counterfactual_engine] best ROI improvement:", f"{best_roi['policy_name']} ({best_roi['delta_vs_original_roi']} pts)")
    print("[counterfactual_engine] best drawdown improvement:", f"{best_dd['policy_name']} ({best_dd['delta_vs_original_drawdown']})")
    print("[counterfactual_engine] best stability improvement:", f"{best_stability['policy_name']} ({best_stability['edge_stability_score']})")


if __name__ == "__main__":
    main()
