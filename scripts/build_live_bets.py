from pathlib import Path
﻿import os
import re
import subprocess
import sys
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ROOT = PROJECT_ROOT
DASH = os.path.join(ROOT, "dashboard", "racing-dashboard")
RATINGS = os.path.join(DASH, "public", "data", "ratings_final_v2.csv")
SIGNALS = os.path.join(DASH, "public", "data", "market_signals.csv")
OUT = os.path.join(DASH, "public", "data", "edgeiq_live_bets.csv")
COUNTRY_SUFFIX_RE = re.compile(r"\s*\((?:AUS|NZ|IRE|GB|UK|USA|FR|GER|JPN|SAF|ARG|CAN|CHI|ITY|BRZ|UAE|HK|SIN|KOR)\)\s*$", re.I)


def hard_horse_key(value):
    if pd.isna(value):
        return ""
    s = str(value).upper().strip()
    if not s or s in {"NAN", "NONE", "NULL", "<NA>"}:
        return ""
    s = COUNTRY_SUFFIX_RE.sub("", s)
    s = re.sub(r"\([^)]*\)", "", s)
    s = s.replace("’", "").replace("'", "").replace("`", "")
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s


def clean_track(value):
    s = str(value or "").upper().strip()
    s = re.sub(r"\b(BET365|LADBROKES|TAB|RACINGCOM|RACING|MRC|ATC|VRC|BRC)\b", " ", s)
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def key_cols(df):
    df = df.copy()
    df["race_date_key"] = pd.to_datetime(df.get("race_date"), errors="coerce").dt.strftime("%Y-%m-%d")
    df["track_key_live"] = df.get("track", "").apply(clean_track)
    df["race_no_key"] = pd.to_numeric(df.get("race_no"), errors="coerce")
    df["horse_key_live"] = df.apply(lambda r: hard_horse_key(r.get("horse_key")) or hard_horse_key(r.get("horse")), axis=1)
    return df


def ensure_signals():
    if os.path.exists(SIGNALS):
        return
    script = os.path.join(DASH, "scripts", "build_market_signals.py")
    if os.path.exists(script):
        subprocess.run(["python", script], cwd=DASH, check=False)


def price_band(price):
    if pd.isna(price) or price <= 0:
        return "NO MARKET"
    if price < 5:
        return "SHORT"
    if price <= 15:
        return "BETTABLE"
    if price <= 34:
        return "SPEC"
    return "ROUGHIE"


def col_or_default(df, col, default):
    if col in df.columns:
        return df[col]
    return pd.Series(default, index=df.index)


def main():
    print("=" * 80)
    print("LIVE BETS - MARKET SIGNAL SOURCE OF TRUTH")
    print("=" * 80)
    ensure_signals()

    ratings = pd.read_csv(RATINGS, low_memory=False)
    signals = pd.read_csv(SIGNALS, low_memory=False) if os.path.exists(SIGNALS) else pd.DataFrame()
    ratings = key_cols(ratings)
    signals = key_cols(signals) if not signals.empty else pd.DataFrame(columns=["race_date_key", "track_key_live", "race_no_key", "horse_key_live"])

    merge_cols = ["race_date_key", "track_key_live", "race_no_key", "horse_key_live"]
    keep_signal_cols = merge_cols + [
        "opening_price", "previous_price", "current_price", "min_price", "max_price", "snapshots",
        "price_delta", "price_delta_pct", "move_from_open_pct", "market_signal", "market_confidence"
    ]
    signals = signals[[c for c in keep_signal_cols if c in signals.columns]].drop_duplicates(merge_cols, keep="last")
    df = ratings.merge(signals, on=merge_cols, how="left", suffixes=("", "_signal"))

    df["elite_rated_price"] = pd.to_numeric(df.get("elite_rated_price"), errors="coerce")
    df["market_price_clean"] = pd.to_numeric(df.get("current_price"), errors="coerce")
    fallback_market = pd.to_numeric(df.get("fixed_win"), errors="coerce")
    df["market_price_clean"] = df["market_price_clean"].fillna(fallback_market)
    df["fixed_place"] = pd.to_numeric(df.get("fixed_place"), errors="coerce")
    df["edge_pct"] = np.where(
        (df["elite_rated_price"] > 0) & (df["market_price_clean"] > 0),
        ((df["market_price_clean"] / df["elite_rated_price"]) - 1) * 100,
        np.nan,
    )

    df["price_band"] = df["market_price_clean"].apply(price_band)
    df["market_signal"] = col_or_default(df, "market_signal_signal", np.nan).combine_first(col_or_default(df, "market_signal", np.nan)).fillna("NO MARKET")
    df["market_confidence"] = col_or_default(df, "market_confidence_signal", np.nan).combine_first(col_or_default(df, "market_confidence", np.nan)).fillna("NONE")
    df["price_snapshots"] = pd.to_numeric(col_or_default(df, "snapshots", np.nan), errors="coerce").fillna(0).astype(int)
    df["fluc_snapshots"] = df["price_snapshots"]
    df["fluc_direction"] = "flat"
    df.loc[df["market_signal"].isin(["STEAMER", "FIRMING"]), "fluc_direction"] = "firming"
    df.loc[df["market_signal"].isin(["DRIFTER", "BIG DRIFTER"]), "fluc_direction"] = "drifting"
    df["fluc_display"] = df.apply(lambda r: f'{r["previous_price"]:.2f} → {r["current_price"]:.2f}' if pd.notna(r.get("current_price")) else "", axis=1)
    df["fluc_change_display"] = df.apply(lambda r: f'{r["price_delta"]:+.2f} ({r["price_delta_pct"]:+.1f}%)' if pd.notna(r.get("price_delta")) else "", axis=1)

    scratched = df.get("is_scratched", False).astype(str).str.lower().isin(["true", "1", "yes", "y"])
    df["is_scratched_bool"] = scratched
    df["raw_overlay"] = df["edge_pct"] > 0
    df["movement_support"] = df["market_signal"].isin(["STEAMER", "FIRMING"])
    df["movement_negative"] = df["market_signal"].isin(["DRIFTER", "BIG DRIFTER"])

    df["overlay_score"] = 0.0
    df.loc[df["edge_pct"] >= 10, "overlay_score"] += 1
    df.loc[df["edge_pct"] >= 20, "overlay_score"] += 1
    df.loc[df["edge_pct"] >= 35, "overlay_score"] += 1
    df.loc[df["price_band"].eq("BETTABLE"), "overlay_score"] += 2
    df.loc[df["price_band"].eq("SPEC"), "overlay_score"] += 1
    df.loc[df["price_band"].eq("ROUGHIE"), "overlay_score"] -= 2
    df.loc[df["price_band"].eq("SHORT"), "overlay_score"] -= 1
    df.loc[df["movement_support"], "overlay_score"] += 2
    df.loc[df["movement_negative"], "overlay_score"] -= 2
    df.loc[df["price_snapshots"] >= 3, "overlay_score"] += 1
    df.loc[df["price_snapshots"] < 2, "overlay_score"] -= 1
    runs_used = pd.to_numeric(df.get("runs_used"), errors="coerce").fillna(0)
    df.loc[runs_used >= 5, "overlay_score"] += 1
    df.loc[runs_used <= 1, "overlay_score"] -= 1
    df.loc[df["market_price_clean"].isna(), "overlay_score"] = -99
    df.loc[df["is_scratched_bool"], "overlay_score"] = -99

    df["action_grade"] = "NO BET"
    df.loc[df["raw_overlay"] & df["price_band"].eq("BETTABLE") & (df["overlay_score"] >= 5), "action_grade"] = "BET"
    df.loc[df["raw_overlay"] & df["price_band"].eq("SPEC") & (df["overlay_score"] >= 5) & df["movement_support"] & (df["price_snapshots"] >= 3), "action_grade"] = "BET"
    df.loc[df["raw_overlay"] & df["price_band"].isin(["BETTABLE", "SPEC"]) & df["overlay_score"].between(3, 4), "action_grade"] = "WATCH"
    df.loc[df["raw_overlay"] & df["price_band"].eq("ROUGHIE"), "action_grade"] = "REVIEW ONLY"
    df.loc[df["edge_pct"] < 0, "action_grade"] = "UNDER"
    df.loc[df["market_price_clean"].isna(), "action_grade"] = "NO MARKET"
    df.loc[df["is_scratched_bool"], "action_grade"] = "SCRATCHED"

    df["edge_grade"] = "NO MARKET"
    df.loc[df["market_price_clean"].notna(), "edge_grade"] = "FAIR"
    df.loc[df["edge_pct"] >= 35, "edge_grade"] = "A+ OVERLAY"
    df.loc[(df["edge_pct"] >= 20) & (df["edge_pct"] < 35), "edge_grade"] = "A OVERLAY"
    df.loc[(df["edge_pct"] >= 10) & (df["edge_pct"] < 20), "edge_grade"] = "B OVERLAY"
    df.loc[df["edge_pct"] < 0, "edge_grade"] = "UNDER"
    df["market_warning"] = ""
    df.loc[df["action_grade"].eq("BET"), "market_warning"] = "QUALIFIED BET"
    df.loc[df["action_grade"].eq("WATCH"), "market_warning"] = "WATCH - NEEDS CONFIRMATION"
    df.loc[df["action_grade"].eq("REVIEW ONLY"), "market_warning"] = "ROUGHIE EDGE - DO NOT AUTO BET"

    df = df.drop(columns=merge_cols, errors="ignore")
    df.to_csv(OUT, index=False)
    print("SAVED:", OUT)
    print("ROWS:", len(df))
    print("MARKET MATCHED:", int(df["market_price_clean"].notna().sum()), "/", len(df))
    print("NON-FLAT MARKET SIGNALS:", int(df[~df["market_signal"].isin(["STABLE", "NO MARKET"])].shape[0]))
    print("\nACTION GRADE COUNTS:")
    print(df["action_grade"].value_counts(dropna=False).to_string())
    print("\nMARKET SIGNAL SHAPE:")
    print(df["market_signal"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
