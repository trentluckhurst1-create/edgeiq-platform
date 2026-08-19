from __future__ import annotations

import csv
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

MASTER = DATA / "edgeiq_graphql_master_v2.csv"
OUT = DATA / "edgeiq_connection_universe_audit_v1.csv"
SUMMARY = DATA / "edgeiq_connection_universe_audit_v1_summary.csv"

def clean(v):
    return "" if v is None else str(v).strip()

def is_win(v):
    return clean(v).upper() in {"1", "1ST"}

def is_place(v):
    return clean(v).upper() in {"1", "2", "3", "1ST", "2ND", "3RD"}

connections = {}

with MASTER.open("r", encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        trainer = clean(r.get("trainer"))
        jockey = clean(r.get("jockey"))

        if not trainer or not jockey:
            continue

        key = f"{trainer.upper()}|{jockey.upper()}"

        c = connections.setdefault(key, {
            "trainer": trainer,
            "jockey": jockey,
            "starts": 0,
            "wins": 0,
            "places": 0,
            "years": set(),
            "tracks": set(),
            "horses": set(),
            "first_start": "",
            "last_start": "",
            "sp_rows": 0,
            "rail_rows": 0,
        })

        c["starts"] += 1

        if is_win(r.get("finish")):
            c["wins"] += 1

        if is_place(r.get("finish")):
            c["places"] += 1

        d = clean(r.get("race_date"))
        if d:
            c["years"].add(d[:4])
            if not c["first_start"] or d < c["first_start"]:
                c["first_start"] = d
            if not c["last_start"] or d > c["last_start"]:
                c["last_start"] = d

        track = clean(r.get("track"))
        horse = clean(r.get("horse"))

        if track:
            c["tracks"].add(track.upper())
        if horse:
            c["horses"].add(horse.upper())

        if clean(r.get("starting_price_decimal")):
            c["sp_rows"] += 1

        if clean(r.get("rail_position")):
            c["rail_rows"] += 1

rows = []

for c in connections.values():
    starts = c["starts"]
    rows.append({
        "trainer": c["trainer"],
        "jockey": c["jockey"],
        "starts": starts,
        "wins": c["wins"],
        "places": c["places"],
        "win_pct": round((c["wins"] / starts) * 100, 2) if starts else 0,
        "place_pct": round((c["places"] / starts) * 100, 2) if starts else 0,
        "years_seen": len(c["years"]),
        "first_start": c["first_start"],
        "last_start": c["last_start"],
        "tracks_seen": len(c["tracks"]),
        "horses_seen": len(c["horses"]),
        "sp_rows": c["sp_rows"],
        "rail_rows": c["rail_rows"],
    })

rows.sort(key=lambda x: x["starts"], reverse=True)

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    fields = list(rows[0].keys()) if rows else ["trainer","jockey"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

built_at = datetime.now(timezone.utc).isoformat()

summary_rows = [
    {"metric": "status", "value": "EDGEIQ_CONNECTION_UNIVERSE_AUDIT_V1_BUILT"},
    {"metric": "unique_connections", "value": len(rows)},
    {"metric": "total_starts", "value": sum(int(r["starts"]) for r in rows)},
    {"metric": "connections_1_start", "value": sum(1 for r in rows if int(r["starts"]) == 1)},
    {"metric": "connections_5_plus_starts", "value": sum(1 for r in rows if int(r["starts"]) >= 5)},
    {"metric": "connections_10_plus_starts", "value": sum(1 for r in rows if int(r["starts"]) >= 10)},
    {"metric": "connections_25_plus_starts", "value": sum(1 for r in rows if int(r["starts"]) >= 25)},
    {"metric": "connections_50_plus_starts", "value": sum(1 for r in rows if int(r["starts"]) >= 50)},
    {"metric": "connections_100_plus_starts", "value": sum(1 for r in rows if int(r["starts"]) >= 100)},
    {"metric": "output", "value": str(OUT)},
    {"metric": "built_at", "value": built_at},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["metric","value"])
    w.writeheader()
    w.writerows(summary_rows)

print("[CONNECTION_UNIVERSE_AUDIT_V1] COMPLETE")
print(f"connections={len(rows)}")
print(f"output={OUT}")
