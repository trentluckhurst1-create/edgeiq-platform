import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INFILE = DATA / "edgeiq_overlay_audit_v1.csv"

OUT = DATA / "edgeiq_execution_candidates_v1.csv"
AUDIT = DATA / "edgeiq_execution_candidates_v1_summary.csv"

def num(df, col):
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce")
    return pd.Series(np.nan, index=df.index)

def safe_str(df, col):
    if col in df.columns:
        return df[col].astype(str).str.upper().str.strip()
    return pd.Series("", index=df.index)

def action(row):
    edge = row["overlay_pct_v1"]
    price = row["tab_fixed_win"]
    rank = row["runner_rank_v7_2"]
    score = row["runner_score_v3_1"]

    if row["execution_exclusion_v1"] != "":
        return "NO_BET"

    if edge >= 60 and rank <= 3 and score >= 45 and price <= 41:
        return "EXECUTE"
    if edge >= 35 and rank <= 5 and score >= 40 and price <= 51:
        return "STRONG_WATCH"
    if edge >= 25 and rank <= 5 and score >= 40 and price <= 51:
        return "WATCH"

    return "NO_BET"

def exclusion(row):
    reasons = []

    if row["is_scratched_v1"]:
        reasons.append("SCRATCHED")
    if row["market_match_status_v1"] != "MATCHED":
        reasons.append("NO_MARKET_MATCH")
    if pd.isna(row["tab_fixed_win"]):
        reasons.append("NO_TAB_PRICE")
    if pd.isna(row["fair_price_v7_2"]):
        reasons.append("NO_FAIR_PRICE")
    if pd.isna(row["overlay_pct_v1"]):
        reasons.append("NO_EDGE")
    if row["tab_fixed_win"] > 51:
        reasons.append("PRICE_ABOVE_51")
    if row["runner_rank_v7_2"] > 5:
        reasons.append("RANK_OUTSIDE_TOP_5")
    if row["runner_score_v3_1"] < 40:
        reasons.append("SCORE_BELOW_40")
    if row["overlay_pct_v1"] < 25:
        reasons.append("EDGE_BELOW_25")

    return "|".join(reasons)

def main():
    if not INFILE.exists():
        raise FileNotFoundError(f"Missing input: {INFILE}")

    df = pd.read_csv(INFILE)

    df["runner_score_v3_1"] = num(df, "runner_score_v3_1")
    df["runner_rank_v7_2"] = num(df, "runner_rank_v7_2")
    df["fair_price_v7_2"] = num(df, "fair_price_v7_2")
    df["tab_fixed_win"] = num(df, "tab_fixed_win")
    df["overlay_pct_v1"] = num(df, "overlay_pct_v1")

    status = safe_str(df, "tab_fixed_betting_status")
    band = safe_str(df, "overlay_band_v1")

    df["is_scratched_v1"] = status.str.contains("SCRATCH", na=False) | band.eq("SCRATCHED")

    if "market_match_status_v1" not in df.columns:
        df["market_match_status_v1"] = "UNKNOWN"

    df["execution_exclusion_v1"] = df.apply(exclusion, axis=1)
    df["execution_action_v1"] = df.apply(action, axis=1)

    df["execution_priority_v1"] = 0
    df.loc[df["execution_action_v1"].eq("WATCH"), "execution_priority_v1"] = 1
    df.loc[df["execution_action_v1"].eq("STRONG_WATCH"), "execution_priority_v1"] = 2
    df.loc[df["execution_action_v1"].eq("EXECUTE"), "execution_priority_v1"] = 3

    df["execution_reason_v1"] = (
        "fair $" + df["fair_price_v7_2"].round(2).astype(str) +
        " vs TAB $" + df["tab_fixed_win"].round(2).astype(str) +
        " | edge " + df["overlay_pct_v1"].round(1).astype(str) + "%" +
        " | rank " + df["runner_rank_v7_2"].fillna(-1).astype(int).astype(str) +
        " | score " + df["runner_score_v3_1"].round(1).astype(str)
    )

    df = df.sort_values(
        ["execution_priority_v1", "overlay_pct_v1", "runner_score_v3_1"],
        ascending=[False, False, False],
        na_position="last"
    )

    df.to_csv(OUT, index=False)

    summary = pd.DataFrame([
        {"metric": "rows", "value": len(df)},
        {"metric": "execute", "value": int((df["execution_action_v1"] == "EXECUTE").sum())},
        {"metric": "strong_watch", "value": int((df["execution_action_v1"] == "STRONG_WATCH").sum())},
        {"metric": "watch", "value": int((df["execution_action_v1"] == "WATCH").sum())},
        {"metric": "no_bet", "value": int((df["execution_action_v1"] == "NO_BET").sum())},
        {"metric": "scratched_excluded", "value": int(df["execution_exclusion_v1"].astype(str).str.contains("SCRATCHED", na=False).sum())},
        {"metric": "price_above_51_excluded", "value": int(df["execution_exclusion_v1"].astype(str).str.contains("PRICE_ABOVE_51", na=False).sum())},
        {"metric": "rank_outside_top_5_excluded", "value": int(df["execution_exclusion_v1"].astype(str).str.contains("RANK_OUTSIDE_TOP_5", na=False).sum())},
        {"metric": "score_below_40_excluded", "value": int(df["execution_exclusion_v1"].astype(str).str.contains("SCORE_BELOW_40", na=False).sum())},
    ])

    summary.to_csv(AUDIT, index=False)

    print("[EXECUTION_CANDIDATES_V1] COMPLETE")
    print(f"rows={len(df)}")
    print(f"execute={(df['execution_action_v1'] == 'EXECUTE').sum()}")
    print(f"strong_watch={(df['execution_action_v1'] == 'STRONG_WATCH').sum()}")
    print(f"watch={(df['execution_action_v1'] == 'WATCH').sum()}")
    print(f"wrote={OUT}")
    print(f"audit={AUDIT}")

if __name__ == "__main__":
    main()
