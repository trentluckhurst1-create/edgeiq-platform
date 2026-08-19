from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RESULTS = DATA / "edgeiq_results_master.csv"
SUPPRESSION = DATA / "edgeiq_suppression_intelligence.csv"
TERMINAL = DATA / "edgeiq_execution_board_terminal.csv"
LIVE = DATA / "edgeiq_execution_board_live.csv"

AUDIT_OUT = DATA / "edgeiq_execution_quality_audit.csv"
REASON_OUT = DATA / "edgeiq_execution_quality_by_reason.csv"

AUDIT_COLUMNS = [
    "total_live_rows",
    "learned_suppression_rows",
    "kill_rows",
    "suppress_rows",
    "reduce_rows",
    "execute_rows_after_learning",
    "suppressed_rows_after_learning",
    "original_execute_now_suppressed",
    "original_priority_now_suppressed",
    "stake_reductions",
    "top_suppression_reason",
    "top_matched_segment",
    "current_live_risk_profile",
    "suppressed_winners",
    "suppressed_losers",
    "suppression_saved_loss",
    "suppression_missed_profit",
    "net_suppression_effect",
    "post_learning_roi",
    "pre_learning_roi",
    "historical_impact_status",
]

REASON_COLUMNS = [
    "reason",
    "rows",
    "suppressed",
    "executed",
    "settled",
    "won",
    "lost",
    "profit_loss",
    "roi_pct",
    "average_clv_pct",
]


def log(message: str) -> None:
    print(f"[edgeiq_execution_quality_audit] {message}")


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


def upper(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.upper()


def text_col(df: pd.DataFrame, column: str) -> pd.Series:
    return df[column] if column in df.columns else pd.Series("", index=df.index)


def num_col(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(pd.NA, index=df.index, dtype="Float64")
    return pd.to_numeric(
        df[column].astype(str).str.replace("$", "", regex=False).str.replace("%", "", regex=False).str.strip(),
        errors="coerce",
    )


def fmt(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{float(value):.4f}"


def pct(numerator: float, denominator: float) -> str:
    if denominator == 0:
        return ""
    return fmt((numerator / denominator) * 100)


def combine_live(live: pd.DataFrame, terminal: pd.DataFrame) -> pd.DataFrame:
    if live.empty:
        return terminal.copy()
    if terminal.empty:
        return live.copy()

    live_cols = set(live.columns)
    important = {
        "suppression_risk_grade",
        "suppression_recommendation",
        "suppression_intelligence_reason",
        "suppression_matched_segments",
        "learned_suppression_applied",
        "original_execution_state",
        "original_stake",
    }
    if important.intersection(live_cols):
        return live.copy()
    return terminal.copy()


def top_value(series: pd.Series) -> str:
    usable = series.astype(str).str.strip()
    usable = usable[usable.ne("")]
    if usable.empty:
        return ""
    return str(usable.value_counts().index[0])


def risk_profile(df: pd.DataFrame) -> str:
    if df.empty or "suppression_risk_grade" not in df.columns:
        return ""
    counts = upper(df["suppression_risk_grade"])
    counts = counts[counts.ne("")]
    if counts.empty:
        return ""
    return "; ".join(f"{grade}:{count}" for grade, count in counts.value_counts().items())


def current_audit(live_rows: pd.DataFrame) -> dict[str, str]:
    if live_rows.empty:
        return {column: "" for column in AUDIT_COLUMNS}

    risk = upper(text_col(live_rows, "suppression_risk_grade"))
    action = upper(text_col(live_rows, "execution_action"))
    original = upper(text_col(live_rows, "original_execution_state"))
    learned = upper(text_col(live_rows, "learned_suppression_applied")).eq("TRUE")
    original_stake = num_col(live_rows, "original_stake")

    stake_cols = [column for column in ["stake", "stake_units", "stake_units_v4_1", "recommended_stake", "kelly_stake"] if column in live_rows.columns]
    current_stake = num_col(live_rows, stake_cols[0]) if stake_cols else pd.Series(pd.NA, index=live_rows.index)
    stake_reductions = int(((original_stake.notna()) & (current_stake.notna()) & (current_stake < original_stake)).sum())

    original_execute = original.isin(["EXECUTE", "BET", "MAX_BET"])
    original_priority = original.isin(["PRIORITY_EXECUTE", "MAX_BET"])
    suppressed = action.isin(["SUPPRESS", "SUPPRESSED"])

    return {
        "total_live_rows": str(len(live_rows)),
        "learned_suppression_rows": str(int(learned.sum())),
        "kill_rows": str(int(risk.eq("KILL").sum())),
        "suppress_rows": str(int(risk.eq("SUPPRESS").sum())),
        "reduce_rows": str(int(risk.eq("REDUCE").sum())),
        "execute_rows_after_learning": str(int(action.isin(["EXECUTE", "REDUCED_EXECUTE", "MAX_BET"]).sum())),
        "suppressed_rows_after_learning": str(int(suppressed.sum())),
        "original_execute_now_suppressed": str(int((original_execute & suppressed).sum())),
        "original_priority_now_suppressed": str(int((original_priority & suppressed).sum())),
        "stake_reductions": str(stake_reductions),
        "top_suppression_reason": top_value(text_col(live_rows, "suppression_intelligence_reason")),
        "top_matched_segment": top_value(text_col(live_rows, "suppression_matched_segments")),
        "current_live_risk_profile": risk_profile(live_rows),
    }


def historical_audit(results: pd.DataFrame) -> dict[str, str]:
    needed = {"original_execution_state", "learned_suppression_applied"}
    if results.empty or not needed.issubset(set(results.columns)):
        return {
            "suppressed_winners": "",
            "suppressed_losers": "",
            "suppression_saved_loss": "",
            "suppression_missed_profit": "",
            "net_suppression_effect": "",
            "post_learning_roi": "",
            "pre_learning_roi": "",
            "historical_impact_status": "Awaiting settled post-learning sample.",
        }

    settled = upper(text_col(results, "result")).isin(["WON", "LOST", "VOID"])
    learned = upper(text_col(results, "learned_suppression_applied")).eq("TRUE")
    action = upper(text_col(results, "execution_state"))
    suppressed = action.isin(["SUPPRESS", "SUPPRESSED"])
    sample = results[settled & learned].copy()

    if sample.empty:
        return {
            "suppressed_winners": "0",
            "suppressed_losers": "0",
            "suppression_saved_loss": "",
            "suppression_missed_profit": "",
            "net_suppression_effect": "",
            "post_learning_roi": "",
            "pre_learning_roi": "",
            "historical_impact_status": "Awaiting settled post-learning sample.",
        }

    result = upper(text_col(sample, "result"))
    profit = num_col(sample, "profit_loss").fillna(0)
    stake = num_col(sample, "stake").fillna(0)
    suppressed_sample = sample[suppressed.loc[sample.index]]
    suppressed_profit = num_col(suppressed_sample, "profit_loss").fillna(0)
    executed_sample = sample[~suppressed.loc[sample.index]]
    executed_profit = num_col(executed_sample, "profit_loss").fillna(0)
    executed_stake = num_col(executed_sample, "stake").fillna(0)
    original_execute_rows = results[settled & upper(text_col(results, "original_execution_state")).isin(["EXECUTE", "BET", "MAX_BET"])]
    original_profit = num_col(original_execute_rows, "profit_loss").fillna(0)
    original_stake = num_col(original_execute_rows, "stake").fillna(0)

    saved_loss = -suppressed_profit[suppressed_profit < 0].sum()
    missed_profit = suppressed_profit[suppressed_profit > 0].sum()

    return {
        "suppressed_winners": str(int((result.eq("WON") & suppressed.loc[sample.index]).sum())),
        "suppressed_losers": str(int((result.eq("LOST") & suppressed.loc[sample.index]).sum())),
        "suppression_saved_loss": fmt(saved_loss),
        "suppression_missed_profit": fmt(missed_profit),
        "net_suppression_effect": fmt(saved_loss - missed_profit),
        "post_learning_roi": pct(executed_profit.sum(), executed_stake.sum()),
        "pre_learning_roi": pct(original_profit.sum(), original_stake.sum()),
        "historical_impact_status": "Measurable settled post-learning sample.",
    }


def reason_groups(live_rows: pd.DataFrame, results: pd.DataFrame) -> pd.DataFrame:
    if not results.empty and {"suppression_intelligence_reason", "suppression_matched_segments"}.intersection(set(results.columns)):
        df = results.copy()
    else:
        df = live_rows.copy()

    if df.empty:
        return pd.DataFrame(columns=REASON_COLUMNS)

    reason = text_col(df, "suppression_intelligence_reason")
    if reason.astype(str).str.strip().eq("").all():
        reason = text_col(df, "suppression_matched_segments")
    if reason.astype(str).str.strip().eq("").all():
        return pd.DataFrame(columns=REASON_COLUMNS)

    working = df.copy()
    working["_reason"] = reason.astype(str).str.strip().replace("", pd.NA)
    working = working.dropna(subset=["_reason"])

    rows = []
    for reason_value, group in working.groupby("_reason", dropna=False):
        action = upper(text_col(group, "execution_action"))
        if "execution_action" not in group.columns:
            action = upper(text_col(group, "execution_state"))
        result = upper(text_col(group, "result"))
        settled = result.isin(["WON", "LOST", "VOID"])
        profit = num_col(group, "profit_loss")
        stake = num_col(group, "stake")
        clv = num_col(group, "clv_pct")
        executed = action.isin(["EXECUTE", "REDUCED_EXECUTE", "MAX_BET", "BET"])
        suppressed = action.isin(["SUPPRESS", "SUPPRESSED"])
        rows.append(
            {
                "reason": str(reason_value),
                "rows": str(len(group)),
                "suppressed": str(int(suppressed.sum())),
                "executed": str(int(executed.sum())),
                "settled": str(int(settled.sum())),
                "won": str(int(result.eq("WON").sum())),
                "lost": str(int(result.eq("LOST").sum())),
                "profit_loss": fmt(profit.dropna().sum()) if profit.notna().any() else "",
                "roi_pct": pct(profit.dropna().sum(), stake[settled & stake.notna()].sum()) if stake.notna().any() else "",
                "average_clv_pct": fmt(clv.dropna().mean()) if clv.notna().any() else "",
            }
        )

    output = pd.DataFrame(rows, columns=REASON_COLUMNS)
    output["_rows"] = pd.to_numeric(output["rows"], errors="coerce").fillna(0)
    return output.sort_values("_rows", ascending=False).drop(columns=["_rows"])


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    results = read_csv(RESULTS)
    read_csv(SUPPRESSION)
    terminal = read_csv(TERMINAL)
    live = read_csv(LIVE)
    live_rows = combine_live(live, terminal)

    audit = {column: "" for column in AUDIT_COLUMNS}
    audit.update(current_audit(live_rows))
    audit.update(historical_audit(results))

    audit_df = pd.DataFrame([audit], columns=AUDIT_COLUMNS)
    reason_df = reason_groups(live_rows, results)

    audit_df.to_csv(AUDIT_OUT, index=False, encoding="utf-8")
    reason_df.to_csv(REASON_OUT, index=False, encoding="utf-8")

    log(f"wrote {AUDIT_OUT.relative_to(ROOT)}: {len(audit_df)} row")
    log(f"wrote {REASON_OUT.relative_to(ROOT)}: {len(reason_df)} rows")
    log(
        "headline: "
        f"live_rows={audit['total_live_rows']}, learned={audit['learned_suppression_rows']}, "
        f"kill={audit['kill_rows']}, suppress={audit['suppress_rows']}, reduce={audit['reduce_rows']}, "
        f"history='{audit['historical_impact_status']}'"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
