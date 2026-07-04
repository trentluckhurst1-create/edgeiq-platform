from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
MASTER = DATA / "edgeiq_results_master.csv"
SUMMARY_OUT = DATA / "edgeiq_results_summary.csv"
REGIME_OUT = DATA / "edgeiq_results_by_regime.csv"
CONFIDENCE_OUT = DATA / "edgeiq_results_by_confidence.csv"
EXECUTION_OUT = DATA / "edgeiq_results_by_execution_state.csv"

SUMMARY_COLUMNS = [
    "total_rows",
    "settled_rows",
    "pending_rows",
    "won",
    "lost",
    "strike_rate",
    "turnover",
    "profit_loss",
    "roi_pct",
    "average_odds",
    "average_clv_pct",
    "beat_close_count",
    "beat_close_pct",
    "stake_rows",
    "clv_rows",
    "max_drawdown",
    "current_drawdown",
    "best_regime",
    "worst_regime",
    "best_confidence_bucket",
    "worst_confidence_bucket",
]

BUCKET_COLUMNS = [
    "bucket",
    "total_rows",
    "settled_rows",
    "pending_rows",
    "won",
    "lost",
    "strike_rate",
    "turnover",
    "profit_loss",
    "roi_pct",
    "average_odds",
    "average_clv_pct",
    "beat_close_count",
    "beat_close_pct",
    "stake_rows",
    "clv_rows",
]


def log(message: str) -> None:
    print(f"[edgeiq_results_summary] {message}")


def read_master() -> pd.DataFrame:
    if not MASTER.exists():
        log(f"missing: {MASTER.relative_to(ROOT)}")
        return pd.DataFrame()
    try:
        return pd.read_csv(MASTER, dtype=str, encoding="utf-8-sig", on_bad_lines="skip").fillna("")
    except Exception as exc:
        log(f"warning: failed to read results master: {exc}")
        return pd.DataFrame()


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace("$", "", regex=False).str.replace("%", "", regex=False).str.strip(),
        errors="coerce",
    )


def settled_mask(df: pd.DataFrame) -> pd.Series:
    result = df.get("result", pd.Series("", index=df.index)).astype(str).str.upper()
    return result.isin(["WON", "LOST", "VOID"])


def pending_mask(df: pd.DataFrame) -> pd.Series:
    result = df.get("result", pd.Series("", index=df.index)).astype(str).str.upper()
    return result.eq("PENDING") | result.eq("")


def pct(numerator: float, denominator: float) -> str:
    if denominator == 0:
        return ""
    return f"{(numerator / denominator) * 100:.4f}"


def money(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{float(value):.4f}"


def drawdowns(profit_series: pd.Series) -> tuple[str, str]:
    values = profit_series.dropna()
    if values.empty:
        return "", ""
    equity = values.cumsum()
    peak = equity.cummax()
    drawdown = equity - peak
    return money(drawdown.min()), money(drawdown.iloc[-1])


def metrics(df: pd.DataFrame) -> dict[str, str]:
    if df.empty:
        return {column: "" for column in SUMMARY_COLUMNS}

    result = df.get("result", pd.Series("", index=df.index)).astype(str).str.upper()
    stake = to_num(df.get("stake", pd.Series("", index=df.index)))
    profit = to_num(df.get("profit_loss", pd.Series("", index=df.index)))
    odds = to_num(df.get("market_price", pd.Series("", index=df.index)))
    clv = to_num(df.get("clv_pct", pd.Series("", index=df.index)))
    settled = settled_mask(df)
    pending = pending_mask(df)
    won = result.eq("WON")
    lost = result.eq("LOST")

    settled_count = int(settled.sum())
    won_count = int(won.sum())
    lost_count = int(lost.sum())
    turnover = stake[settled & stake.notna()].sum()
    profit_total = profit[profit.notna()].sum()
    beat_close_count = int((clv > 0).sum())
    clv_rows = int(clv.notna().sum())
    max_drawdown, current_drawdown = drawdowns(profit)

    return {
        "total_rows": str(len(df)),
        "settled_rows": str(settled_count),
        "pending_rows": str(int(pending.sum())),
        "won": str(won_count),
        "lost": str(lost_count),
        "strike_rate": pct(won_count, won_count + lost_count),
        "turnover": money(turnover),
        "profit_loss": money(profit_total),
        "roi_pct": pct(profit_total, turnover),
        "average_odds": money(odds[settled & odds.notna()].mean()),
        "average_clv_pct": money(clv[clv.notna()].mean()),
        "beat_close_count": str(beat_close_count),
        "beat_close_pct": pct(beat_close_count, clv_rows),
        "stake_rows": str(int(stake.notna().sum())),
        "clv_rows": str(clv_rows),
        "max_drawdown": max_drawdown,
        "current_drawdown": current_drawdown,
        "best_regime": "",
        "worst_regime": "",
        "best_confidence_bucket": "",
        "worst_confidence_bucket": "",
    }


def bucket_metrics(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if df.empty or column not in df.columns:
        return pd.DataFrame(columns=BUCKET_COLUMNS)

    rows: list[dict[str, str]] = []
    bucket_values = df[column].astype(str).str.strip().replace("", "UNKNOWN")
    for bucket, group in df.groupby(bucket_values, dropna=False):
        row = metrics(group)
        rows.append({"bucket": str(bucket), **{name: row.get(name, "") for name in BUCKET_COLUMNS if name != "bucket"}})

    output = pd.DataFrame(rows, columns=BUCKET_COLUMNS)
    if not output.empty:
        output["_profit_sort"] = pd.to_numeric(output["profit_loss"], errors="coerce").fillna(0)
        output = output.sort_values(["_profit_sort", "settled_rows"], ascending=[False, False]).drop(columns=["_profit_sort"])
    return output


def best_worst_bucket(bucket_df: pd.DataFrame) -> tuple[str, str]:
    if bucket_df.empty:
        return "", ""
    usable = bucket_df.copy()
    usable["_settled"] = pd.to_numeric(usable["settled_rows"], errors="coerce").fillna(0)
    usable["_profit"] = pd.to_numeric(usable["profit_loss"], errors="coerce")
    usable = usable[(usable["_settled"] > 0) & usable["_profit"].notna()]
    if usable.empty:
        return "", ""
    best = usable.sort_values(["_profit", "_settled"], ascending=[False, False]).iloc[0]["bucket"]
    worst = usable.sort_values(["_profit", "_settled"], ascending=[True, False]).iloc[0]["bucket"]
    return str(best), str(worst)


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    df = read_master()

    if df.empty:
        log("no results master rows; writing empty summary outputs")
        pd.DataFrame(columns=SUMMARY_COLUMNS).to_csv(SUMMARY_OUT, index=False, encoding="utf-8")
        pd.DataFrame(columns=BUCKET_COLUMNS).to_csv(REGIME_OUT, index=False, encoding="utf-8")
        pd.DataFrame(columns=BUCKET_COLUMNS).to_csv(CONFIDENCE_OUT, index=False, encoding="utf-8")
        pd.DataFrame(columns=BUCKET_COLUMNS).to_csv(EXECUTION_OUT, index=False, encoding="utf-8")
        return 0

    summary = metrics(df)
    by_regime = bucket_metrics(df, "regime")
    by_confidence = bucket_metrics(df, "confidence")
    by_execution = bucket_metrics(df, "execution_state")
    summary["best_regime"], summary["worst_regime"] = best_worst_bucket(by_regime)
    summary["best_confidence_bucket"], summary["worst_confidence_bucket"] = best_worst_bucket(by_confidence)

    pd.DataFrame([summary], columns=SUMMARY_COLUMNS).to_csv(SUMMARY_OUT, index=False, encoding="utf-8")
    by_regime.to_csv(REGIME_OUT, index=False, encoding="utf-8")
    by_confidence.to_csv(CONFIDENCE_OUT, index=False, encoding="utf-8")
    by_execution.to_csv(EXECUTION_OUT, index=False, encoding="utf-8")

    log(f"rows read: {len(df)}")
    log(f"wrote {SUMMARY_OUT.relative_to(ROOT)}")
    log(f"wrote {REGIME_OUT.relative_to(ROOT)}: {len(by_regime)} rows")
    log(f"wrote {CONFIDENCE_OUT.relative_to(ROOT)}: {len(by_confidence)} rows")
    log(f"wrote {EXECUTION_OUT.relative_to(ROOT)}: {len(by_execution)} rows")
    log(
        "key metrics: "
        f"settled={summary['settled_rows']}, pending={summary['pending_rows']}, "
        f"strike_rate={summary['strike_rate']}, profit_loss={summary['profit_loss']}, "
        f"roi_pct={summary['roi_pct']}, clv_rows={summary['clv_rows']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
