import re
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RESULTS = DATA / "edgeiq_racingcom_results_warehouse_full_v1.csv"

OUT = DATA / "edgeiq_historical_runner_scores_v1.csv"
AUDIT = DATA / "edgeiq_historical_runner_scores_v1_audit.csv"

def canon(x):
    s = "" if pd.isna(x) else str(x).upper().strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]+", "", s)
    return s

def pos_num(x):
    s = "" if pd.isna(x) else str(x).upper().strip()
    if s in ["", "SCR", "SCRATCHED", "NAN", "NONE"]:
        return np.nan
    m = re.search(r"\d+", s)
    return float(m.group(0)) if m else np.nan

def price_num(x):
    s = "" if pd.isna(x) else str(x).replace("$", "").replace(",", "").strip()
    try:
        return float(s)
    except:
        return np.nan

def gov_band(starts):
    if starts >= 5:
        return "PROVEN"
    if starts >= 3:
        return "LIMITED_DATA_3_4_STARTS"
    if starts == 2:
        return "LIMITED_DATA_2_STARTS"
    if starts == 1:
        return "LIMITED_DATA_1_START"
    return "FIRST_STARTER_OR_UNKNOWN"

def main():
    df = pd.read_csv(RESULTS)

    horse_col = "horseName" if "horseName" in df.columns else "horse"
    finish_col = "finishPosition" if "finishPosition" in df.columns else "finish_position"

    df["meeting_date"] = df["meeting_date"].astype(str).str.slice(0, 10)
    df["horse"] = df[horse_col].astype(str)
    df["horse_key"] = df["horse"].map(canon)
    df["finish_position"] = df[finish_col].apply(pos_num)
    df["sp_num"] = df["sp"].apply(price_num) if "sp" in df.columns else np.nan
    df["race_key"] = df["meeting_date"] + "|" + df["track"].astype(str) + "|" + df["race_no"].astype(str)

    df = df[df["finish_position"].notna()].copy()
    df = df.sort_values(["horse_key", "meeting_date", "race_key"]).reset_index(drop=True)

    field = df.groupby("race_key")["horse_key"].count().rename("field_size").reset_index()
    df = df.merge(field, on="race_key", how="left")

    df["finish_pct"] = np.where(
        df["field_size"] > 1,
        1.0 - ((df["finish_position"] - 1.0) / (df["field_size"] - 1.0)),
        0.5
    )
    df["won"] = df["finish_position"].eq(1).astype(int)
    df["placed"] = df["finish_position"].le(3).astype(int)
    df["top4"] = df["finish_position"].le(4).astype(int)

    parts = []

    for horse_key, g in df.groupby("horse_key", sort=False):
        g = g.sort_values(["meeting_date", "race_key"]).copy()

        g["starts_before"] = np.arange(len(g))
        g["wins_before"] = g["won"].cumsum().shift(1).fillna(0)
        g["places_before"] = g["placed"].cumsum().shift(1).fillna(0)
        g["top4_before"] = g["top4"].cumsum().shift(1).fillna(0)

        g["avg_finish_pct_before"] = g["finish_pct"].expanding().mean().shift(1)
        g["best_finish_pct_before"] = g["finish_pct"].expanding().max().shift(1)
        g["recent_avg_finish_pct_before"] = g["finish_pct"].rolling(5, min_periods=1).mean().shift(1)

        g["win_rate_before"] = np.where(g["starts_before"] > 0, g["wins_before"] / g["starts_before"], 0)
        g["place_rate_before"] = np.where(g["starts_before"] > 0, g["places_before"] / g["starts_before"], 0)
        g["top4_rate_before"] = np.where(g["starts_before"] > 0, g["top4_before"] / g["starts_before"], 0)

        parts.append(g)

    out = pd.concat(parts, ignore_index=True)

    out["governance_band_hist_v1"] = out["starts_before"].apply(gov_band)

    out["historical_ability_score_v1"] = (
        100.0 * (
            0.34 * out["avg_finish_pct_before"].fillna(0.42) +
            0.28 * out["recent_avg_finish_pct_before"].fillna(out["avg_finish_pct_before"]).fillna(0.42) +
            0.16 * out["place_rate_before"].fillna(0) +
            0.10 * out["win_rate_before"].fillna(0) +
            0.08 * out["top4_rate_before"].fillna(0) +
            0.04 * out["best_finish_pct_before"].fillna(0.42)
        )
    ).clip(0,100)

    # Mild ability-only governance calibration from live V6 lesson.
    mult = {
        "PROVEN": 0.98,
        "LIMITED_DATA_3_4_STARTS": 0.98,
        "LIMITED_DATA_2_STARTS": 1.045,
        "LIMITED_DATA_1_START": 0.98,
        "FIRST_STARTER_OR_UNKNOWN": 1.02,
    }
    out["ability_multiplier_hist_v1"] = out["governance_band_hist_v1"].map(mult).fillna(0.96)

    out["runner_score_hist_v1"] = (
        out["historical_ability_score_v1"] * out["ability_multiplier_hist_v1"]
    ).clip(0,100).round(3)

    out = out.sort_values(["race_key", "runner_score_hist_v1"], ascending=[True, False])
    out["runner_rank_hist_v1"] = out.groupby("race_key").cumcount() + 1

    out["won"] = out["finish_position"].eq(1).astype(int)
    out["placed"] = out["finish_position"].le(3).astype(int)

    out.to_csv(OUT, index=False)

    audit = pd.DataFrame([
        {"metric":"built_at","value":datetime.now().isoformat(timespec="seconds")},
        {"metric":"rows","value":len(out)},
        {"metric":"races","value":out["race_key"].nunique()},
        {"metric":"horses","value":out["horse_key"].nunique()},
        {"metric":"date_min","value":out["meeting_date"].min()},
        {"metric":"date_max","value":out["meeting_date"].max()},
        {"metric":"avg_score","value":round(out["runner_score_hist_v1"].mean(),3)},
        {"metric":"max_score","value":round(out["runner_score_hist_v1"].max(),3)},
    ])
    audit.to_csv(AUDIT, index=False)

    print("[HISTORICAL_RUNNER_SCORES_V1] COMPLETE")
    print(f"rows={len(out)}")
    print(f"races={out['race_key'].nunique()}")
    print(f"horses={out['horse_key'].nunique()}")
    print(f"wrote={OUT}")
    print(f"audit={AUDIT}")

if __name__ == "__main__":
    main()
