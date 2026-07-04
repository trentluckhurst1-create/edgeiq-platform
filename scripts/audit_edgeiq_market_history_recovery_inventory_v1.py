from pathlib import Path
import pandas as pd
import re
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_market_history_recovery_inventory_v1.csv"
SUMMARY = DATA / "edgeiq_market_history_recovery_inventory_v1_summary.txt"

MARKET_TERMS = [
    "market", "price", "odds", "sportsbet", "tab", "bookmaker",
    "tape", "snapshot", "velocity", "fluc", "fixed"
]

def pick_col(df, names):
    lower = {str(c).lower(): c for c in df.columns}
    for n in names:
        if n.lower() in lower:
            return lower[n.lower()]
    return None

def count_nonblank(df, col):
    if not col:
        return 0
    s = df[col].astype(str).str.strip()
    return int((df[col].notna() & (s != "") & (s.str.lower() != "nan") & (s != "0")).sum())

rows = []

for path in sorted(DATA.glob("*.csv")):
    lower_name = path.name.lower()
    if not any(t in lower_name for t in MARKET_TERMS):
        continue

    try:
        sample = pd.read_csv(path, nrows=10000, low_memory=False)
    except Exception as e:
        rows.append({
            "source_file": path.name,
            "read_status": f"ERROR: {e}",
        })
        continue

    total_rows = 0
    try:
        total_rows = sum(1 for _ in open(path, "r", encoding="utf-8", errors="ignore")) - 1
    except Exception:
        total_rows = len(sample)

    date_col = pick_col(sample, ["race_date", "meeting_date", "date", "target_race_date"])
    track_col = pick_col(sample, ["track", "venue", "target_track"])
    race_no_col = pick_col(sample, ["race_no", "race_number", "target_race_no"])
    horse_col = pick_col(sample, ["horse", "runner", "runner_name", "horse_name"])
    price_col = pick_col(sample, [
        "price", "market_price", "live_price", "sportsbet_price",
        "fixed_win", "tab_fixed", "odds", "sp"
    ])
    ts_col = pick_col(sample, [
        "timestamp", "captured_at", "scraped_at", "scraped_at_utc",
        "snapshot_time", "created_at", "updated_at"
    ])
    race_time_col = pick_col(sample, [
        "race_time", "jump_time", "scheduled_time", "start_time"
    ])

    date_min = ""
    date_max = ""
    if date_col:
        dates = pd.to_datetime(sample[date_col], errors="coerce")
        if dates.notna().any():
            date_min = str(dates.min().date())
            date_max = str(dates.max().date())

    safe_score = sum(bool(x) for x in [
        date_col, track_col, race_no_col, horse_col, price_col, ts_col, race_time_col
    ])

    if ts_col and race_time_col:
        recovery_class = "TIMESTAMP_AND_RACE_TIME_READY"
    elif ts_col and not race_time_col:
        recovery_class = "TIMESTAMP_NEEDS_RACE_TIME_JOIN"
    elif not ts_col and race_time_col:
        recovery_class = "RACE_TIME_NO_TIMESTAMP"
    elif price_col:
        recovery_class = "PRICE_ONLY_QUARANTINE"
    else:
        recovery_class = "LOW_VALUE"

    rows.append({
        "source_file": path.name,
        "read_status": "OK",
        "total_rows_est": total_rows,
        "sample_rows": len(sample),
        "columns": len(sample.columns),
        "date_col": date_col or "",
        "track_col": track_col or "",
        "race_no_col": race_no_col or "",
        "horse_col": horse_col or "",
        "price_col": price_col or "",
        "timestamp_col": ts_col or "",
        "race_time_col": race_time_col or "",
        "date_min_sample": date_min,
        "date_max_sample": date_max,
        "date_nonblank_sample": count_nonblank(sample, date_col),
        "track_nonblank_sample": count_nonblank(sample, track_col),
        "race_no_nonblank_sample": count_nonblank(sample, race_no_col),
        "horse_nonblank_sample": count_nonblank(sample, horse_col),
        "price_nonblank_sample": count_nonblank(sample, price_col),
        "timestamp_nonblank_sample": count_nonblank(sample, ts_col),
        "race_time_nonblank_sample": count_nonblank(sample, race_time_col),
        "safe_score": safe_score,
        "recovery_class": recovery_class,
    })

df = pd.DataFrame(rows)
if not df.empty:
    df = df.sort_values(["recovery_class", "safe_score", "total_rows_est"], ascending=[True, False, False])

df.to_csv(OUT, index=False)

lines = []
lines.append("EDGEIQ_MARKET_HISTORY_RECOVERY_INVENTORY_V1")
lines.append(f"built_at={datetime.now(timezone.utc).isoformat()}")
lines.append(f"candidate_files={len(df)}")
lines.append("")
if not df.empty:
    lines.append("RECOVERY CLASS COUNTS")
    for k, v in df["recovery_class"].value_counts().items():
        lines.append(f"{k}: {v}")
    lines.append("")
    lines.append("TOP TIMESTAMP/RACE-TIME READY")
    ready = df[df["recovery_class"] == "TIMESTAMP_AND_RACE_TIME_READY"].head(40)
    for _, r in ready.iterrows():
        lines.append(f"{r['source_file']} | rows={r['total_rows_est']} | dates={r['date_min_sample']}..{r['date_max_sample']} | price={r['price_col']} | ts={r['timestamp_col']} | race_time={r['race_time_col']}")
    lines.append("")
    lines.append("TOP TIMESTAMP NEEDS RACE TIME JOIN")
    needs = df[df["recovery_class"] == "TIMESTAMP_NEEDS_RACE_TIME_JOIN"].head(40)
    for _, r in needs.iterrows():
        lines.append(f"{r['source_file']} | rows={r['total_rows_est']} | dates={r['date_min_sample']}..{r['date_max_sample']} | price={r['price_col']} | ts={r['timestamp_col']}")

SUMMARY.write_text("\n".join(lines), encoding="utf-8")

print("[EDGEIQ_MARKET_HISTORY_RECOVERY_INVENTORY_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(df.head(100).to_string(index=False))
