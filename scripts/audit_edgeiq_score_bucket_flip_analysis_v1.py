from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_historical_replay_settled_v1.csv"
BY_RACE = DATA / "edgeiq_runner_dna_weight_ladder_v1_by_race.csv"

VERSION = "MEDIUM"

def num(x):
    try:
        s = str(x).replace("$", "").replace("%", "").strip()
        if s == "" or s.lower() == "nan":
            return np.nan
        return float(s)
    except Exception:
        return np.nan

def bucket(x):
    if pd.isna(x):
        return "UNKNOWN"
    if x < 20:
        return "00_20"
    if x < 40:
        return "20_40"
    if x < 60:
        return "40_60"
    if x < 80:
        return "60_80"
    return "80_PLUS"

def build_factor(factor_name, factor_col):
    out_path = DATA / f"edgeiq_{factor_name}_score_bucket_flip_analysis_v1.csv"
    summary_path = DATA / f"edgeiq_{factor_name}_score_bucket_flip_analysis_v1_summary.csv"

    hist = pd.read_csv(SRC, dtype=str).fillna("")
    races = pd.read_csv(BY_RACE, dtype=str).fillna("")

    required_cols = [
        "race_key",
        "version",
        "top_changed_vs_base",
        "base_top",
        "version_top",
        "base_top_won",
        "version_top_won",
        "base_top_placed",
        "version_top_placed"
    ]

    missing = [c for c in required_cols if c not in races.columns]
    if missing:
        raise RuntimeError(f"Missing required columns from by-race replay: {missing}")

    if factor_col not in hist.columns:
        raise RuntimeError(f"Missing factor column from historical replay source: {factor_col}")

    changed = races[
        (races["version"] == VERSION) &
        (races["top_changed_vs_base"].astype(str).str.lower() == "true")
    ].copy()

    rows = []
    for _, r in changed.iterrows():
        race_key = r["race_key"]
        base_top = r["base_top"]
        new_top = r["version_top"]

        race_df = hist[hist["race_key"] == race_key].copy()

        b = race_df[race_df["horse"] == base_top]
        n = race_df[race_df["horse"] == new_top]

        if b.empty or n.empty:
            continue

        b = b.iloc[0]
        n = n.iloc[0]

        base_score = num(b.get(factor_col, ""))
        new_score = num(n.get(factor_col, ""))

        base_won = int(num(r.get("base_top_won", 0)) or 0)
        new_won = int(num(r.get("version_top_won", 0)) or 0)
        base_placed = int(num(r.get("base_top_placed", 0)) or 0)
        new_placed = int(num(r.get("version_top_placed", 0)) or 0)

        if base_won == 0 and new_won == 1:
            flip_result = "IMPROVED_WIN"
        elif base_won == 1 and new_won == 0:
            flip_result = "WORSENED_WIN"
        elif base_placed == 0 and new_placed == 1:
            flip_result = "IMPROVED_PLACE"
        elif base_placed == 1 and new_placed == 0:
            flip_result = "WORSENED_PLACE"
        else:
            flip_result = "NEUTRAL"

        rows.append({
            "race_key": race_key,
            "meeting_date": r.get("meeting_date", ""),
            "track": r.get("track", ""),
            "race_no": r.get("race_no", ""),
            "base_top": base_top,
            "new_top": new_top,
            "base_score": round(base_score, 4) if not pd.isna(base_score) else "",
            "new_score": round(new_score, 4) if not pd.isna(new_score) else "",
            "score_delta": round(new_score - base_score, 4) if not pd.isna(base_score) and not pd.isna(new_score) else "",
            "base_bucket": bucket(base_score),
            "new_bucket": bucket(new_score),
            "base_top_won": base_won,
            "new_top_won": new_won,
            "base_top_placed": base_placed,
            "new_top_placed": new_placed,
            "flip_result": flip_result,
            "factor": factor_name.upper(),
            "factor_col": factor_col,
            "research_only": "YES",
            "built_at": datetime.now(timezone.utc).isoformat(),
        })

    out = pd.DataFrame(rows)
    out.to_csv(out_path, index=False)

    if len(out):
        summary = (
            out.groupby(["base_bucket", "new_bucket", "flip_result"])
            .agg(
                races=("race_key", "count"),
                avg_score_delta=("score_delta", lambda s: pd.to_numeric(s, errors="coerce").mean()),
            )
            .reset_index()
            .sort_values(["flip_result", "races"], ascending=[True, False])
        )
        summary["avg_score_delta"] = summary["avg_score_delta"].round(4)

        pivot = (
            out.groupby(["base_bucket", "new_bucket"])
            .agg(
                races=("race_key", "count"),
                improved_wins=("flip_result", lambda s: (s == "IMPROVED_WIN").sum()),
                worsened_wins=("flip_result", lambda s: (s == "WORSENED_WIN").sum()),
                improved_places=("flip_result", lambda s: (s == "IMPROVED_PLACE").sum()),
                worsened_places=("flip_result", lambda s: (s == "WORSENED_PLACE").sum()),
                neutral=("flip_result", lambda s: (s == "NEUTRAL").sum()),
                avg_score_delta=("score_delta", lambda s: pd.to_numeric(s, errors="coerce").mean()),
            )
            .reset_index()
        )
        pivot["net_win_gain"] = pivot["improved_wins"] - pivot["worsened_wins"]
        pivot["net_place_gain"] = pivot["improved_places"] - pivot["worsened_places"]
        pivot["avg_score_delta"] = pivot["avg_score_delta"].round(4)
        pivot = pivot.sort_values(["net_win_gain", "net_place_gain", "races"], ascending=[False, False, False])
    else:
        pivot = pd.DataFrame()

    pivot.to_csv(summary_path, index=False)

    print(f"[{factor_name.upper()}_SCORE_BUCKET_FLIP_ANALYSIS_V1] COMPLETE")
    print(f"detail={out_path}")
    print(f"summary={summary_path}")
    print(f"rows={len(out)}")
    if len(pivot):
        print(pivot.head(30).to_string(index=False))

build_factor("jockey", "jockey_score")
build_factor("connection", "connection_score")
