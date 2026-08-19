from __future__ import annotations

import csv
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_graphql_master_v2.csv"
SUMMARY = DATA / "edgeiq_graphql_master_v2_summary.csv"

MONTH_RE = re.compile(r"edgeiq_graphql_([a-z]+)_(\d{4})_results_v1\.csv$", re.I)

MONTH_ORDER = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

def clean(v):
    return "" if v is None else str(v).strip()

def norm(v):
    return clean(v).upper()

files = []
for p in DATA.glob("edgeiq_graphql_*_*_results_v1.csv"):
    m = MONTH_RE.match(p.name)
    if not m:
        continue
    month_name = m.group(1).lower()
    year = int(m.group(2))
    files.append((year, MONTH_ORDER.get(month_name, 99), month_name, p))

files.sort()

built_at = datetime.now(timezone.utc).isoformat()

all_rows = []
all_fields = set()
seen = set()
duplicate_count = 0

for year, month_num, month_name, path in files:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            row = dict(r)

            race_date = clean(row.get("race_date"))
            track = clean(row.get("track"))
            race_no = clean(row.get("race_no"))
            horse = clean(row.get("horse"))
            runner_id = clean(row.get("runner_id"))
            race_id = clean(row.get("race_id"))

            dedupe_key = "|".join([
                race_date,
                norm(track),
                race_no,
                runner_id or norm(horse),
                race_id,
            ])

            if dedupe_key in seen:
                duplicate_count += 1
                continue

            seen.add(dedupe_key)

            row["source_year"] = str(year)
            row["source_month"] = month_name
            row["source_month_num"] = str(month_num)
            row["source_file"] = path.name
            row["master_built_at"] = built_at

            all_fields.update(row.keys())
            all_rows.append(row)

preferred = [
    "source_year", "source_month", "source_month_num", "source_file",
    "race_date", "track", "venue_name", "state", "meet_code", "meet_url",
    "race_id", "race_no", "race_status", "race_name", "race_class",
    "distance", "race_time_utc",
    "track_condition", "track_rating", "rail_position",
    "previous_rail_position", "weather", "rainfall", "penetrometer",
    "has_sectionals", "has_results", "has_speed_map",
    "runner_id", "race_entry_number", "horse", "horse_code",
    "trainer", "trainer_code", "jockey", "jockey_code",
    "barrier", "live_barrier", "weight", "scratched",
    "finish", "finish_abv", "margin", "margin_l",
    "starting_price", "starting_price_decimal",
    "winning_time", "comment_short", "comment", "comment_stewards",
    "gear_changes", "source", "built_at", "master_built_at",
]

fields = [c for c in preferred if c in all_fields] + sorted(c for c in all_fields if c not in preferred)

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in all_rows:
        w.writerow({c: r.get(c, "") for c in fields})

years = sorted(set(r.get("source_year", "") for r in all_rows if r.get("source_year")))
summary_rows = [
    {"metric": "status", "value": "EDGEIQ_GRAPHQL_MASTER_V2_BUILT"},
    {"metric": "files_scanned", "value": len(files)},
    {"metric": "output_rows", "value": len(all_rows)},
    {"metric": "duplicates_removed", "value": duplicate_count},
    {"metric": "years_seen", "value": ",".join(years)},
    {"metric": "first_year", "value": years[0] if years else ""},
    {"metric": "last_year", "value": years[-1] if years else ""},
    {"metric": "output", "value": str(OUT)},
    {"metric": "built_at", "value": built_at},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["metric", "value"])
    w.writeheader()
    w.writerows(summary_rows)

print("[GRAPHQL_MASTER_V2] COMPLETE")
print(f"files_scanned={len(files)}")
print(f"rows={len(all_rows)}")
print(f"duplicates_removed={duplicate_count}")
print(f"output={OUT}")
print(f"summary={SUMMARY}")
