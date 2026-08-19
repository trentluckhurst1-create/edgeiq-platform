from __future__ import annotations

import csv
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_graphql_master_v2.csv"
OUT = DATA / "edgeiq_graphql_universe_audit_v1.csv"
SUMMARY = DATA / "edgeiq_graphql_universe_audit_v1_summary.csv"

def clean(v):
    return "" if v is None else str(v).strip()

def pct(a, b):
    return round((a / b) * 100, 2) if b else 0

if not SRC.exists():
    raise FileNotFoundError(f"Missing master file: {SRC}")

built_at = datetime.now(timezone.utc).isoformat()

years = {}

with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)

    for r in reader:
        year = clean(r.get("source_year")) or clean(r.get("race_date"))[:4]
        if not year:
            year = "UNKNOWN"

        y = years.setdefault(year, {
            "year": year,
            "months": set(),
            "meetings": set(),
            "races": set(),
            "runners": 0,
            "horses": set(),
            "trainers": set(),
            "jockeys": set(),
            "tracks": set(),
            "sp_rows": 0,
            "rail_rows": 0,
            "trainer_rows": 0,
            "jockey_rows": 0,
            "condition_rows": 0,
            "rating_rows": 0,
            "sectional_flag_rows": 0,
            "speedmap_flag_rows": 0,
        })

        month = clean(r.get("source_month"))
        if month:
            y["months"].add(month)

        race_date = clean(r.get("race_date"))
        track = clean(r.get("track"))
        race_no = clean(r.get("race_no"))
        meet_code = clean(r.get("meet_code"))
        race_id = clean(r.get("race_id"))

        if meet_code:
            y["meetings"].add(meet_code)
        elif race_date and track:
            y["meetings"].add(f"{race_date}|{track}")

        if race_id:
            y["races"].add(race_id)
        elif race_date and track and race_no:
            y["races"].add(f"{race_date}|{track}|{race_no}")

        y["runners"] += 1

        horse = clean(r.get("horse"))
        trainer = clean(r.get("trainer"))
        jockey = clean(r.get("jockey"))

        if horse:
            y["horses"].add(horse.upper())
        if trainer:
            y["trainers"].add(trainer.upper())
            y["trainer_rows"] += 1
        if jockey:
            y["jockeys"].add(jockey.upper())
            y["jockey_rows"] += 1
        if track:
            y["tracks"].add(track.upper())

        if clean(r.get("starting_price_decimal")):
            y["sp_rows"] += 1
        if clean(r.get("rail_position")):
            y["rail_rows"] += 1
        if clean(r.get("track_condition")):
            y["condition_rows"] += 1
        if clean(r.get("track_rating")):
            y["rating_rows"] += 1
        if clean(r.get("has_sectionals")).upper() == "TRUE":
            y["sectional_flag_rows"] += 1
        if clean(r.get("has_speed_map")).upper() == "TRUE":
            y["speedmap_flag_rows"] += 1

rows = []
for year in sorted(years.keys()):
    y = years[year]
    runners = y["runners"]
    rows.append({
        "built_at": built_at,
        "year": year,
        "months_present": len(y["months"]),
        "meetings": len(y["meetings"]),
        "races": len(y["races"]),
        "runners": runners,
        "unique_horses": len(y["horses"]),
        "unique_trainers": len(y["trainers"]),
        "unique_jockeys": len(y["jockeys"]),
        "unique_tracks": len(y["tracks"]),
        "trainer_rows": y["trainer_rows"],
        "trainer_pct": pct(y["trainer_rows"], runners),
        "jockey_rows": y["jockey_rows"],
        "jockey_pct": pct(y["jockey_rows"], runners),
        "sp_rows": y["sp_rows"],
        "sp_pct": pct(y["sp_rows"], runners),
        "rail_rows": y["rail_rows"],
        "rail_pct": pct(y["rail_rows"], runners),
        "condition_rows": y["condition_rows"],
        "condition_pct": pct(y["condition_rows"], runners),
        "track_rating_rows": y["rating_rows"],
        "track_rating_pct": pct(y["rating_rows"], runners),
        "sectional_flag_rows": y["sectional_flag_rows"],
        "sectional_flag_pct": pct(y["sectional_flag_rows"], runners),
        "speedmap_flag_rows": y["speedmap_flag_rows"],
        "speedmap_flag_pct": pct(y["speedmap_flag_rows"], runners),
    })

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    fields = list(rows[0].keys()) if rows else ["built_at","year"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

summary = [
    {"metric": "status", "value": "EDGEIQ_GRAPHQL_UNIVERSE_AUDIT_V1_BUILT"},
    {"metric": "source", "value": str(SRC)},
    {"metric": "years", "value": len(rows)},
    {"metric": "total_runners", "value": sum(int(r["runners"]) for r in rows)},
    {"metric": "total_races", "value": sum(int(r["races"]) for r in rows)},
    {"metric": "total_unique_horses_by_year_sum", "value": sum(int(r["unique_horses"]) for r in rows)},
    {"metric": "output", "value": str(OUT)},
    {"metric": "built_at", "value": built_at},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["metric","value"])
    w.writeheader()
    w.writerows(summary)

print("[GRAPHQL_UNIVERSE_AUDIT_V1] COMPLETE")
print(f"years={len(rows)}")
print(f"runners={sum(int(r['runners']) for r in rows)}")
print(f"output={OUT}")
