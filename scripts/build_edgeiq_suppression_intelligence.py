from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
MASTER = DATA / "edgeiq_results_master.csv"
INPUTS = [
    DATA / "edgeiq_results_by_regime.csv",
    DATA / "edgeiq_results_by_confidence.csv",
    DATA / "edgeiq_results_by_execution_state.csv",
]
OUT = DATA / "edgeiq_suppression_intelligence.csv"

COLUMNS = [
    "segment_type",
    "segment_value",
    "rows",
    "settled_rows",
    "turnover",
    "profit_loss",
    "roi_pct",
    "average_clv_pct",
    "beat_close_pct",
    "strike_rate",
    "risk_grade",
    "suppression_recommendation",
    "reason",
]


def log(message: str) -> None:
    print(f"[edgeiq_suppression_intelligence] {message}")


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        log(f"missing: {path.relative_to(ROOT)}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig", on_bad_lines="skip").fillna("")
        log(f"read {path.relative_to(ROOT)}: {len(df)} rows")
        return df
    except Exception as exc:
        log(f"warning: failed to read {path.name}: {exc}")
        return pd.DataFrame()


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace("$", "", regex=False).str.replace("%", "", regex=False).str.strip(),
        errors="coerce",
    )


def pct(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return (numerator / denominator) * 100


def fmt(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{float(value):.4f}"


def overlay_bucket(value: float | None) -> str:
    if value is None or pd.isna(value):
        return ""
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


def odds_bucket(value: float | None) -> str:
    if value is None or pd.isna(value) or value <= 0:
        return ""
    if value < 3:
        return "UNDER_3"
    if value < 6:
        return "3_TO_6"
    if value < 12:
        return "6_TO_12"
    if value < 26:
        return "12_TO_26"
    return "26_PLUS"


def grade_segment(
    rows: int,
    settled_rows: int,
    roi_value: float | None,
    avg_clv: float | None,
    beat_close: float | None,
) -> tuple[str, str, str]:
    if settled_rows < 30:
        return "MONITOR", "MONITOR_ONLY", f"Small settled sample ({settled_rows}); do not hard suppress yet."

    clv_available = beat_close is not None and avg_clv is not None
    if roi_value is not None and roi_value < -15 and clv_available and beat_close < 35:
        return "KILL", "DO_NOT_EXECUTE", f"ROI {roi_value:.1f}% and beat-close {beat_close:.1f}% are both below kill thresholds."
    if roi_value is not None and roi_value < -8:
        return "SUPPRESS", "SUPPRESS_BEFORE_EXECUTION", f"ROI {roi_value:.1f}% is below -8%."
    if avg_clv is not None and avg_clv < -5:
        return "SUPPRESS", "SUPPRESS_BEFORE_EXECUTION", f"Average CLV {avg_clv:.1f}% is below -5%."
    if roi_value is not None and roi_value < 0:
        return "REDUCE", "REDUCE_SIZE", f"ROI {roi_value:.1f}% is negative."
    if beat_close is not None and beat_close < 45:
        return "REDUCE", "REDUCE_SIZE", f"Beat-close {beat_close:.1f}% is below 45%."
    if roi_value is not None and roi_value >= 0 and beat_close is not None and beat_close >= 45:
        return "ALLOW", "ALLOW_NORMAL_EXECUTION", f"ROI {roi_value:.1f}% and beat-close {beat_close:.1f}% meet allow thresholds."
    return "MONITOR", "MONITOR_ONLY", f"Rows {rows}; available ROI/CLV evidence is incomplete."


def segment_metrics(df: pd.DataFrame, segment_type: str, segment_value: str) -> dict[str, str]:
    result = df.get("result", pd.Series("", index=df.index)).astype(str).str.upper()
    stake = to_num(df.get("stake", pd.Series("", index=df.index)))
    profit = to_num(df.get("profit_loss", pd.Series("", index=df.index)))
    clv = to_num(df.get("clv_pct", pd.Series("", index=df.index)))

    settled = result.isin(["WON", "LOST", "VOID"])
    won = result.eq("WON")
    lost = result.eq("LOST")
    settled_rows = int(settled.sum())
    turnover = stake[settled & stake.notna()].sum()
    profit_loss = profit[profit.notna()].sum()
    roi_value = pct(profit_loss, turnover) if turnover > 0 else None
    clv_rows = int(clv.notna().sum())
    avg_clv = clv[clv.notna()].mean() if clv_rows else None
    beat_close = pct(float((clv > 0).sum()), float(clv_rows)) if clv_rows else None
    strike_rate = pct(float(won.sum()), float(won.sum() + lost.sum()))
    grade, recommendation, reason = grade_segment(len(df), settled_rows, roi_value, avg_clv, beat_close)

    return {
        "segment_type": segment_type,
        "segment_value": segment_value,
        "rows": str(len(df)),
        "settled_rows": str(settled_rows),
        "turnover": fmt(turnover),
        "profit_loss": fmt(profit_loss),
        "roi_pct": fmt(roi_value),
        "average_clv_pct": fmt(avg_clv),
        "beat_close_pct": fmt(beat_close),
        "strike_rate": fmt(strike_rate),
        "risk_grade": grade,
        "suppression_recommendation": recommendation,
        "reason": reason,
    }


def add_segment_rows(rows: list[dict[str, str]], df: pd.DataFrame, segment_type: str, series: pd.Series) -> None:
    labels = series.astype(str).str.strip().replace("", pd.NA)
    working = df.copy()
    working["_segment_value"] = labels
    working = working.dropna(subset=["_segment_value"])
    for value, group in working.groupby("_segment_value", dropna=False):
        rows.append(segment_metrics(group.drop(columns=["_segment_value"]), segment_type, str(value)))


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    for path in INPUTS:
        read_csv(path)

    df = read_csv(MASTER)
    if df.empty:
        log("no results master rows; writing empty suppression intelligence")
        pd.DataFrame(columns=COLUMNS).to_csv(OUT, index=False, encoding="utf-8")
        return 0

    rows: list[dict[str, str]] = []
    if "regime" in df.columns:
        add_segment_rows(rows, df, "regime", df["regime"])
    if "confidence" in df.columns:
        add_segment_rows(rows, df, "confidence_bucket", df["confidence"])
    if "execution_state" in df.columns:
        add_segment_rows(rows, df, "execution_state", df["execution_state"])
    if "volatility" in df.columns and df["volatility"].astype(str).str.strip().ne("").any():
        add_segment_rows(rows, df, "volatility", df["volatility"])
    if "overlay_pct" in df.columns:
        overlays = to_num(df["overlay_pct"]).map(overlay_bucket)
        add_segment_rows(rows, df, "overlay_bucket", overlays)
    if "market_price" in df.columns:
        odds = to_num(df["market_price"]).map(odds_bucket)
        add_segment_rows(rows, df, "odds_bucket", odds)

    output = pd.DataFrame(rows, columns=COLUMNS)
    if not output.empty:
        risk_order = {"KILL": 0, "SUPPRESS": 1, "REDUCE": 2, "MONITOR": 3, "ALLOW": 4}
        output["_risk_order"] = output["risk_grade"].map(risk_order).fillna(9)
        output["_settled"] = pd.to_numeric(output["settled_rows"], errors="coerce").fillna(0)
        output["_roi"] = pd.to_numeric(output["roi_pct"], errors="coerce").fillna(0)
        output = (
            output.sort_values(["_risk_order", "_settled", "_roi"], ascending=[True, False, True])
            .drop(columns=["_risk_order", "_settled", "_roi"])
            .reset_index(drop=True)
        )

    output.to_csv(OUT, index=False, encoding="utf-8")
    counts = output["risk_grade"].value_counts().to_dict() if not output.empty else {}
    log(f"wrote {OUT.relative_to(ROOT)}: {len(output)} rows")
    log(f"risk counts: {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
