from pathlib import Path
﻿import os
import re
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ROOT = PROJECT_ROOT
DASH = os.path.join(ROOT, "dashboard", "racing-dashboard")
HISTORY = os.path.join(ROOT, "outputs", "markets", "edgeiq_odds_history.csv")
OUT = os.path.join(DASH, "public", "data", "market_signals.csv")

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


def pct_change(current, previous):
    if pd.isna(current) or pd.isna(previous) or previous <= 0:
        return 0.0
    return ((current - previous) / previous) * 100.0


def signal_label(row):
    current = row["current_price"]
    previous = row["previous_price"]
    snapshots = row["snapshots"]
    last_pct = row["price_delta_pct"]
    open_pct = row["move_from_open_pct"]
    if pd.isna(current) or current <= 0 or snapshots <= 0:
        return "NO MARKET"
    if snapshots < 2:
        return "STABLE"
    if last_pct <= -8 or open_pct <= -18:
        return "STEAMER"
    if current < previous or open_pct <= -8:
        return "FIRMING"
    if last_pct >= 10 or open_pct >= 25:
        return "BIG DRIFTER"
    if current > previous or open_pct >= 8:
        return "DRIFTER"
    return "STABLE"


def confidence(row):
    snaps = int(row["snapshots"] or 0)
    if row["market_signal"] == "NO MARKET":
        return "NONE"
    if snaps >= 5:
        return "HIGH"
    if snaps >= 3:
        return "MEDIUM"
    return "LOW"


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    if not os.path.exists(HISTORY):
        pd.DataFrame(columns=[
            "race_date", "track", "race_no", "horse", "horse_key", "opening_price", "previous_price", "current_price",
            "min_price", "max_price", "snapshots", "price_delta", "price_delta_pct", "move_from_open_pct", "market_signal", "market_confidence"
        ]).to_csv(OUT, index=False)
        print("WARN: odds history missing; wrote empty market_signals.csv")
        return

    hist = pd.read_csv(HISTORY, low_memory=False)
    if hist.empty:
        pd.DataFrame().to_csv(OUT, index=False)
        print("WARN: odds history empty; wrote empty market_signals.csv")
        return

    hist["race_date"] = pd.to_datetime(hist.get("race_date"), errors="coerce").dt.strftime("%Y-%m-%d")
    hist["track_key"] = hist.get("track", "").apply(clean_track)
    hist["race_no_num"] = pd.to_numeric(hist.get("race_no"), errors="coerce")
    hist["horse_key_hard"] = hist.apply(lambda r: hard_horse_key(r.get("horse_key")) or hard_horse_key(r.get("horse")), axis=1)
    hist["fixed_win_num"] = pd.to_numeric(hist.get("fixed_win"), errors="coerce")
    hist["captured_sort"] = pd.to_datetime(hist.get("history_captured_at"), errors="coerce")
    fallback_time = pd.to_datetime(hist.get("captured_at"), errors="coerce")
    hist["captured_sort"] = hist["captured_sort"].fillna(fallback_time)

    hist = hist[
        hist["race_date"].notna()
        & hist["track_key"].ne("")
        & hist["race_no_num"].notna()
        & hist["horse_key_hard"].ne("")
        & hist["fixed_win_num"].notna()
        & (hist["fixed_win_num"] > 0)
    ].copy()

    if hist.empty:
        pd.DataFrame().to_csv(OUT, index=False)
        print("WARN: no valid odds rows; wrote empty market_signals.csv")
        return

    hist = hist.sort_values(["race_date", "track_key", "race_no_num", "horse_key_hard", "captured_sort"])
    dedupe_cols = ["race_date", "track_key", "race_no_num", "horse_key_hard", "captured_sort", "fixed_win_num"]
    hist = hist.drop_duplicates(subset=dedupe_cols, keep="last")

    rows = []
    group_cols = ["race_date", "track_key", "race_no_num", "horse_key_hard"]
    for keys, g in hist.groupby(group_cols, dropna=False):
        g = g.sort_values("captured_sort")
        prices = g["fixed_win_num"].dropna().tolist()
        if not prices:
            continue
        opening = prices[0]
        current = prices[-1]
        previous = prices[-2] if len(prices) >= 2 else current
        delta = current - previous
        race_date, track_key, race_no, horse_key = keys
        last = g.iloc[-1]
        rows.append({
            "race_date": race_date,
            "track": str(last.get("track", track_key)).strip(),
            "race_no": int(race_no) if pd.notna(race_no) else race_no,
            "horse": str(last.get("horse", "")).strip(),
            "horse_key": horse_key,
            "opening_price": opening,
            "previous_price": previous,
            "current_price": current,
            "min_price": min(prices),
            "max_price": max(prices),
            "snapshots": len(prices),
            "price_delta": delta,
            "price_delta_pct": pct_change(current, previous),
            "move_from_open_pct": pct_change(current, opening),
        })

    out = pd.DataFrame(rows)
    if out.empty:
        out.to_csv(OUT, index=False)
        print("WARN: no grouped market signals; wrote empty file")
        return

    out["market_signal"] = out.apply(signal_label, axis=1)
    out["market_confidence"] = out.apply(confidence, axis=1)
    out = out.sort_values(["race_date", "track", "race_no", "horse"])
    out.to_csv(OUT, index=False)

    non_flat = int(~out["market_signal"].isin(["STABLE", "NO MARKET"]).sum()) if False else int(out[~out["market_signal"].isin(["STABLE", "NO MARKET"])].shape[0])
    print("SAVED:", OUT)
    print("ROWS:", len(out))
    print("NON-FLAT MARKET SIGNALS:", non_flat)
    print(out["market_signal"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
