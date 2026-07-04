import pandas as pd
from pathlib import Path

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_racingcom_results_warehouse_all_v1.csv"
SUMMARY = DATA / "edgeiq_racingcom_results_warehouse_all_v1_summary.csv"

files = []

for p in DATA.rglob("*.csv"):
    n = p.name.lower()
    if (
        "results" in n
        and (
            n.endswith("_results.csv")
            or "results_warehouse" in n
        )
        and "summary" not in n
        and "profile" not in n
        and "winner_origin" not in n
        and "race_index" not in n
        and "sorted" not in n
        and p.name != OUT.name
    ):
        files.append(p)

frames = []
seen_cols = set()

for p in sorted(files):
    try:
        df = pd.read_csv(p, dtype=str).fillna("")
        if len(df) == 0:
            continue
        df["_source_file"] = str(p.relative_to(ROOT))
        frames.append(df)
        seen_cols.update(df.columns)
        print(f"[READ] {p.relative_to(ROOT)} rows={len(df)}")
    except Exception as e:
        print(f"[SKIP] {p.relative_to(ROOT)} error={e}")

if not frames:
    raise RuntimeError("No result CSV files found to combine.")

all_df = pd.concat(frames, ignore_index=True, sort=False).fillna("")

key_candidates = [
    ["meeting_date", "track", "race_no", "horseName"],
    ["meeting_date", "track", "race_no", "horse"],
    ["race_date", "track", "race_no", "horseName"],
    ["race_date", "track", "race_no", "horse"],
]

dedupe_key = None
for key in key_candidates:
    if all(c in all_df.columns for c in key):
        dedupe_key = key
        break

before = len(all_df)
if dedupe_key:
    all_df = all_df.drop_duplicates(dedupe_key, keep="last")
else:
    all_df = all_df.drop_duplicates(keep="last")

after = len(all_df)

sort_cols = [c for c in ["meeting_date", "race_date", "track", "race_no", "finishPosition", "horseName", "horse"] if c in all_df.columns]
if sort_cols:
    all_df = all_df.sort_values(sort_cols, na_position="last")

all_df.to_csv(OUT, index=False)

date_col = "meeting_date" if "meeting_date" in all_df.columns else ("race_date" if "race_date" in all_df.columns else "")
track_col = "track" if "track" in all_df.columns else ""

summary = pd.DataFrame([
    {"metric": "status", "value": "COMPLETE"},
    {"metric": "files_found", "value": len(files)},
    {"metric": "files_loaded", "value": len(frames)},
    {"metric": "rows_before_dedupe", "value": before},
    {"metric": "rows_after_dedupe", "value": after},
    {"metric": "dedupe_key", "value": "|".join(dedupe_key) if dedupe_key else "FULL_ROW"},
    {"metric": "min_date", "value": all_df[date_col].min() if date_col else ""},
    {"metric": "max_date", "value": all_df[date_col].max() if date_col else ""},
    {"metric": "tracks", "value": all_df[track_col].nunique() if track_col else ""},
    {"metric": "output", "value": OUT.name},
])
summary.to_csv(SUMMARY, index=False)

print("[RESULTS_WAREHOUSE_ALL_V1] COMPLETE")
print(f"files_loaded={len(frames)}")
print(f"rows_before_dedupe={before}")
print(f"rows_after_dedupe={after}")
print(f"wrote={OUT}")
