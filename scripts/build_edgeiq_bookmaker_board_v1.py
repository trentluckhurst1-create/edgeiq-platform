from __future__ import annotations

from pathlib import Path
from datetime import datetime
import pandas as pd
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

TERMINAL = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
SPORTSBET = DATA / "sportsbet_live_market_v1.csv"
OUT = DATA / "edgeiq_bookmaker_board_v1.csv"

def clean(v):
    if pd.isna(v):
        return ""
    return str(v).strip()

def key(v):
    return re.sub(r"[^A-Z0-9]+", "", clean(v).upper())

def num(v):
    try:
        s = re.sub(r"[^0-9.\-]+", "", clean(v))
        if not s:
            return None
        return float(s)
    except Exception:
        return None

def first(row, cols):
    for c in cols:
        if c in row and clean(row[c]):
            return clean(row[c])
    return ""

def first_num(row, cols):
    for c in cols:
        if c in row:
            n = num(row[c])
            if n is not None and n > 0:
                return n
    return None

terminal = pd.read_csv(TERMINAL, dtype=str).fillna("") if TERMINAL.exists() else pd.DataFrame()
sportsbet = pd.read_csv(SPORTSBET, dtype=str).fillna("") if SPORTSBET.exists() else pd.DataFrame()

rows = []

if not terminal.empty:
    for _, r in terminal.iterrows():
        horse_key = first(r, ["horse_key"]) or key(first(r, ["horse"]))
        live = first_num(r, ["ui_price", "live_price", "market_price", "fixed_win", "sportsbet_price"])
        rows.append({
            "source_priority": 1,
            "race_date": first(r, ["race_date", "date"]),
            "meeting_key": first(r, ["meeting_key"]),
            "race_key": first(r, ["race_key"]),
            "track": first(r, ["track"]),
            "race_no": first(r, ["race_no"]),
            "race_time": first(r, ["race_time"]),
            "horse": first(r, ["horse"]),
            "horse_key": horse_key,
            "barrier": first(r, ["barrier", "bar"]),
            "jockey": first(r, ["jockey", "rider"]),
            "trainer": first(r, ["trainer"]),
            "live_price": live,
            "open_price": first_num(r, ["open_price"]),
            "low_price": first_num(r, ["low_price"]),
            "high_price": first_num(r, ["high_price"]),
            "previous_price": first_num(r, ["mid_price", "sportsbet_price"]),
            "flucs": first(r, ["flucs", "last10", "last_10"]),
            "edge_pct": first_num(r, ["ui_edge_pct", "edge_pct"]),
            "action": first(r, ["execution_action", "suppression_action", "truth_grade"]) or "OBSERVE",
            "bookmaker": first(r, ["bookmaker"]) or "Sportsbet",
            "updated_at": first(r, ["market_capture_timestamp", "sportsbet_timestamp", "built_at"]),
            "is_scratched": first(r, ["is_scratched"]),
            "runner_status": first(r, ["runner_status", "scratch_status"]),
            "selection_status": first(r, ["selection_status"]),
            "status_code": first(r, ["status_code"]),
        })

if not sportsbet.empty:
    for _, r in sportsbet.iterrows():
        horse_key = first(r, ["horse_key"]) or key(first(r, ["horse"]))
        live = first_num(r, ["price_win", "sportsbet_price", "live_price", "market_price", "fixed_win"])
        rows.append({
            "source_priority": 2,
            "race_date": first(r, ["race_date", "date"]),
            "meeting_key": first(r, ["meeting_key"]) or f'{first(r, ["race_date", "date"])}_{first(r, ["track"]).upper()}',
            "race_key": first(r, ["race_id", "race_key"]),
            "track": first(r, ["track", "meeting_name"]),
            "race_no": first(r, ["race_no"]),
            "race_time": first(r, ["race_time"]),
            "horse": first(r, ["horse"]),
            "horse_key": horse_key,
            "barrier": "",
            "jockey": "",
            "trainer": "",
            "live_price": live,
            "open_price": live,
            "low_price": live,
            "high_price": live,
            "previous_price": None,
            "flucs": first(r, ["recent_odds_fluctuations", "market_mover"]),
            "edge_pct": None,
            "action": "OBSERVE",
            "bookmaker": first(r, ["bookmaker"]) or "Sportsbet",
            "updated_at": first(r, ["timestamp", "capture_timestamp_utc"]),
            "is_scratched": "TRUE" if first(r, ["status_code", "selection_status"]).upper() == "S" else first(r, ["is_scratched"]),
            "runner_status": "SCRATCHED" if first(r, ["status_code", "selection_status"]).upper() == "S" else first(r, ["runner_status"]),
            "selection_status": first(r, ["selection_status"]),
            "status_code": first(r, ["status_code"]),
        })

df = pd.DataFrame(rows)

# Prefer fresh Sportsbet meeting/date when available.
if not sportsbet.empty and "race_date" in sportsbet.columns and "track" in sportsbet.columns:
    fresh_dates = set(sportsbet["race_date"].astype(str).str.strip())
    fresh_tracks = set(sportsbet["track"].astype(str).str.upper().str.strip())
    if fresh_dates and fresh_tracks and "race_date" in df.columns and "track" in df.columns:
        df = df[
            df["race_date"].astype(str).str.strip().isin(fresh_dates)
            & df["track"].astype(str).str.upper().str.strip().isin(fresh_tracks)
        ].copy()


if df.empty:
    pd.DataFrame().to_csv(OUT, index=False)
    print("WROTE empty bookmaker board")
    raise SystemExit(0)

# Prefer terminal identity/details, but fill price from Sportsbet where needed.
merged = {}
for _, r in df.sort_values("source_priority").iterrows():
    k = (key(r.get("race_key")), key(r.get("horse_key")))
    if k not in merged:
        merged[k] = r.to_dict()
        continue

    base = merged[k]
    for col in df.columns:
        val = r.get(col)
        if clean(base.get(col)) == "" and clean(val) != "":
            base[col] = val
        if col in {"live_price", "open_price", "low_price", "high_price"} and (base.get(col) is None or clean(base.get(col)) == "") and val is not None:
            base[col] = val

out = pd.DataFrame(list(merged.values()))

# Synthetic market memory until persistent tape is fully restored.
out["live_price"] = pd.to_numeric(out["live_price"], errors="coerce")
out["open_price"] = pd.to_numeric(out["open_price"], errors="coerce").fillna(out["live_price"])
out["low_price"] = pd.to_numeric(out["low_price"], errors="coerce").fillna(out[["open_price", "live_price"]].min(axis=1))
out["high_price"] = pd.to_numeric(out["high_price"], errors="coerce").fillna(out[["open_price", "live_price"]].max(axis=1))
out["previous_price"] = pd.to_numeric(out["previous_price"], errors="coerce").fillna(out["open_price"])
out["move_direction"] = out.apply(
    lambda r: "FIRMING" if pd.notna(r["live_price"]) and pd.notna(r["previous_price"]) and r["live_price"] < r["previous_price"]
    else "DRIFTING" if pd.notna(r["live_price"]) and pd.notna(r["previous_price"]) and r["live_price"] > r["previous_price"]
    else "STABLE",
    axis=1
)
out["move_delta"] = out["live_price"] - out["previous_price"]
out["built_at"] = datetime.now().isoformat(timespec="seconds")

out = out.sort_values(["race_date", "track", "race_no", "live_price", "horse"], na_position="last")
out.to_csv(OUT, index=False)
print(f"WROTE {OUT}")
print(f"rows={len(out)}")
print(out[["track","race_no","horse","live_price","open_price","low_price","high_price","move_direction"]].head(12).to_string(index=False))

