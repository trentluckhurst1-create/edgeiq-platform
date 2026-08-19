from pathlib import Path
import pandas as pd
import re
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_market_source_coverage_expansion_audit_v1.csv"
SUMMARY = DATA / "edgeiq_market_source_coverage_expansion_audit_v1_summary.txt"

KEYWORDS = ["market", "price", "odds", "fixed", "fluc", "sportsbet", "tab", "bookmaker", "snapshot", "tape", "sp"]

def pick_col(df, names):
    lower = {str(c).lower(): c for c in df.columns}
    for n in names:
        if n.lower() in lower:
            return lower[n.lower()]
    return None

def nonblank(s):
    x = s.astype(str).str.strip()
    return int(((s.notna()) & (x != "") & (x.str.lower() != "nan") & (x != "0")).sum())

rows = []

for path in sorted(DATA.glob("*.csv")):
    name = path.name.lower()
    if not any(k in name for k in KEYWORDS):
        continue

    try:
        df = pd.read_csv(path, nrows=5000, low_memory=False)
    except Exception as e:
        rows.append({"source_file": path.name, "read_status": f"ERROR {e}"})
        continue

    cols = list(df.columns)
    date_col = pick_col(df, ["race_date", "date", "meeting_date", "target_race_date"])
    track_col = pick_col(df, ["track", "venue", "target_track"])
    race_no_col = pick_col(df, ["race_no", "race_number", "target_race_no"])
    horse_col = pick_col(df, ["horse", "runner", "runner_name", "horse_name"])
    price_col = pick_col(df, ["price", "odds", "market_price", "fixed_win", "sportsbet_price", "tab_fixed", "live_price", "sp"])
    ts_col = pick_col(df, ["timestamp", "captured_at", "scraped_at", "scraped_at_utc", "snapshot_time", "created_at", "updated_at"])
    race_time_col = pick_col(df, ["race_time", "jump_time", "scheduled_time", "start_time"])

    total_rows = None
    try:
        total_rows = sum(1 for _ in open(path, "r", encoding="utf-8", errors="ignore")) - 1
    except Exception:
        total_rows = len(df)

    date_min = ""
    date_max = ""
    date_nonblank = 0
    if date_col:
        dates = pd.to_datetime(df[date_col], errors="coerce")
        date_nonblank = int(dates.notna().sum())
        if date_nonblank:
            date_min = str(dates.min().date())
            date_max = str(dates.max().date())

    rows.append({
        "source_file": path.name,
        "read_status": "OK",
        "total_rows_est": total_rows,
        "sample_rows": len(df),
        "columns": len(cols),
        "date_col": date_col or "",
        "track_col": track_col or "",
        "race_no_col": race_no_col or "",
        "horse_col": horse_col or "",
        "price_col": price_col or "",
        "timestamp_col": ts_col or "",
        "race_time_col": race_time_col or "",
        "date_nonblank_sample": date_nonblank,
        "date_min_sample": date_min,
        "date_max_sample": date_max,
        "track_nonblank_sample": nonblank(df[track_col]) if track_col else 0,
        "horse_nonblank_sample": nonblank(df[horse_col]) if horse_col else 0,
        "price_nonblank_sample": nonblank(df[price_col]) if price_col else 0,
        "timestamp_nonblank_sample": nonblank(df[ts_col]) if ts_col else 0,
        "race_time_nonblank_sample": nonblank(df[race_time_col]) if race_time_col else 0,
        "safe_candidate_score": sum([
            bool(date_col), bool(track_col), bool(horse_col), bool(price_col), bool(ts_col), bool(race_time_col)
        ])
    })

out = pd.DataFrame(rows)
if not out.empty:
    out = out.sort_values(["safe_candidate_score", "total_rows_est"], ascending=[False, False])
out.to_csv(OUT, index=False)

lines = []
lines.append("EDGEIQ_MARKET_SOURCE_COVERAGE_EXPANSION_AUDIT_V1")
lines.append(f"built_at={datetime.now(timezone.utc).isoformat()}")
lines.append(f"candidate_market_files={len(out)}")
lines.append("")
lines.append("TOP CANDIDATES")
for _, r in out.head(80).iterrows():
    lines.append(
        f"{r['source_file']} | score={r['safe_candidate_score']} | rows={r['total_rows_est']} | date={r['date_col']} {r['date_min_sample']}..{r['date_max_sample']} | price={r['price_col']} | ts={r['timestamp_col']} | race_time={r['race_time_col']}"
    )

SUMMARY.write_text("\n".join(lines), encoding="utf-8")

print("[EDGEIQ_MARKET_SOURCE_COVERAGE_EXPANSION_AUDIT_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(out.head(80).to_string(index=False))
