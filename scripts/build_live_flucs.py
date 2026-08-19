from pathlib import Path
import os
import re
import subprocess
import sys
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ROOT = PROJECT_ROOT
DASH = os.path.join(ROOT, "dashboard", "racing-dashboard")
LIVE = os.path.join(DASH, "public", "data", "edgeiq_live_bets.csv")
SIGNALS = os.path.join(DASH, "public", "data", "market_signals.csv")
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


def series(df, name, default=""):
    if name in df.columns:
        return df[name]
    return pd.Series([default] * len(df), index=df.index)

def ensure_signals():
    if os.path.exists(SIGNALS):
        return
    script = os.path.join(DASH, "scripts", "build_market_signals.py")
    if os.path.exists(script):
        subprocess.run(["python", script], cwd=DASH, check=False)


def main():
    ensure_signals()
    live = pd.read_csv(LIVE, low_memory=False)
    signals = pd.read_csv(SIGNALS, low_memory=False) if os.path.exists(SIGNALS) else pd.DataFrame()

    derived_cols = [
        "previous_price", "current_price", "price_delta", "price_delta_pct", "move_from_open_pct",
        "fluc_snapshots", "fluc_direction", "fluc_display", "fluc_change_display",
        "market_signal", "market_confidence", "opening_price", "min_price", "max_price"
    ]
    live = live.drop(columns=[c for c in derived_cols if c in live.columns], errors="ignore")

    if signals.empty:
        live["fluc_direction"] = "flat"
        live["fluc_display"] = ""
        live["fluc_change_display"] = ""
        live.to_csv(LIVE, index=False)
        print("WARN: no market_signals rows; live flucs set flat")
        return

    live = key_cols(live)
    signals = key_cols(signals)
    merge_cols = ["race_date_key", "track_key_live", "race_no_key", "horse_key_live"]
    keep = merge_cols + [
        "opening_price", "previous_price", "current_price", "min_price", "max_price", "snapshots",
        "price_delta", "price_delta_pct", "move_from_open_pct", "market_signal", "market_confidence"
    ]
    signals = signals[[c for c in keep if c in signals.columns]].drop_duplicates(merge_cols, keep="last")
    out = live.merge(signals, on=merge_cols, how="left")

    market_col = "market_price_clean" if "market_price_clean" in out.columns else "fixed_win"
    fallback = pd.to_numeric(out.get(market_col), errors="coerce")
    out["previous_price"] = pd.to_numeric(out.get("previous_price"), errors="coerce").fillna(fallback)
    out["current_price"] = pd.to_numeric(out.get("current_price"), errors="coerce").fillna(fallback)
    out["price_delta"] = pd.to_numeric(out.get("price_delta"), errors="coerce").fillna(0)
    out["price_delta_pct"] = pd.to_numeric(out.get("price_delta_pct"), errors="coerce").fillna(0)
    out["move_from_open_pct"] = pd.to_numeric(out.get("move_from_open_pct"), errors="coerce").fillna(0)
    out["fluc_snapshots"] = pd.to_numeric(series(out, "snapshots", 0), errors="coerce").fillna(0).astype(int)
    out["market_signal"] = series(out, "market_signal", "NO MARKET").fillna("NO MARKET")
    out["market_confidence"] = series(out, "market_confidence", "NONE").fillna("NONE")
    out["fluc_direction"] = "flat"
    out.loc[out["price_delta"] < 0, "fluc_direction"] = "firming"
    out.loc[out["price_delta"] > 0, "fluc_direction"] = "drifting"
    out["fluc_display"] = out.apply(lambda r: f'{r["previous_price"]:.2f} → {r["current_price"]:.2f}' if pd.notna(r["current_price"]) else "", axis=1)
    out["fluc_change_display"] = out.apply(lambda r: f'{r["price_delta"]:+.2f} ({r["price_delta_pct"]:+.1f}%)' if pd.notna(r["current_price"]) else "", axis=1)

    out = out.drop(columns=merge_cols, errors="ignore")
    out.to_csv(LIVE, index=False)
    print("UPDATED:", LIVE)
    print("ROWS:", len(out))
    print("NON-FLAT FLUCS:", int(out["fluc_direction"].ne("flat").sum()))
    print(out[["track", "race_no", "horse", "previous_price", "current_price", "price_delta", "price_delta_pct", "market_signal", "fluc_direction", "fluc_display", "fluc_change_display"]].head(40).to_string(index=False))


if __name__ == "__main__":
    main()



