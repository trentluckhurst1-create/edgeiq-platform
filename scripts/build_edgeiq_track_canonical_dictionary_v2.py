from __future__ import annotations

import csv
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_graphql_master_v2.csv"
OUT = DATA / "edgeiq_track_canonical_dictionary_v2.csv"
SUMMARY = DATA / "edgeiq_track_canonical_dictionary_v2_summary.csv"

SPONSORS = [
    "SPORTSBET", "LADBROKES", "BET365", "APIAM", "PICKLEBET",
    "TAB", "MRC", "VRC", "MELBOURNE RACING CLUB", "SOUTHSIDE"
]

def clean(v):
    return "" if v is None else str(v).strip()

def simplify(track):
    t = clean(track).upper()
    t = t.replace("&", " AND ")
    for s in SPONSORS:
        t = re.sub(rf"\b{re.escape(s)}\b", " ", t)
    t = t.replace("-", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t

def canonical(track):
    raw = clean(track).upper()
    t = simplify(raw)

    explicit = {
        "THE VALLEY": "MOONEE VALLEY",
        "VALLEY": "MOONEE VALLEY",
        "MOONEE VALLEY": "MOONEE VALLEY",

        "PARK HILLSIDE": "SANDOWN HILLSIDE",
        "SANDOWN HILLSIDE": "SANDOWN HILLSIDE",
        "PARK LAKESIDE": "SANDOWN LAKESIDE",
        "SANDOWN LAKESIDE": "SANDOWN LAKESIDE",

        "PARK KILMORE": "KILMORE",
        "PARK KYNETON": "KYNETON",
        "PARK WODONGA": "WODONGA",
        "PARK WERRIBEE": "WERRIBEE",

        "CRANBOURNE TRN": "CRANBOURNE TRIAL",
        "CRANBOURNE TRIAL": "CRANBOURNE TRIAL",
    }

    if t in explicit:
        return explicit[t]

    if "CAULFIELD HEATH" in t:
        return "CAULFIELD HEATH"
    if "CAULFIELD" in t:
        return "CAULFIELD"
    if "FLEMINGTON" in t:
        return "FLEMINGTON"
    if "MOONEE" in t and "VALLEY" in t:
        return "MOONEE VALLEY"

    if "SANDOWN" in t and "HILLSIDE" in t:
        return "SANDOWN HILLSIDE"
    if "SANDOWN" in t and "LAKESIDE" in t:
        return "SANDOWN LAKESIDE"
    if "SANDOWN" in t:
        return "SANDOWN"

    if "PAKENHAM" in t and "SYNTHETIC" in t:
        return "PAKENHAM SYNTHETIC"
    if "PAKENHAM" in t:
        return "PAKENHAM"

    if "BALLARAT" in t and "SYNTHETIC" in t:
        return "BALLARAT SYNTHETIC"
    if "BALLARAT" in t:
        return "BALLARAT"

    if "GEELONG" in t and "SYNTHETIC" in t:
        return "GEELONG SYNTHETIC"
    if "GEELONG" in t:
        return "GEELONG"

    known = [
        "BENDIGO", "HAMILTON", "KILMORE", "KYNETON", "WODONGA", "WERRIBEE",
        "WANGARATTA", "SEYMOUR", "BAIRNSDALE", "ARARAT", "SWAN HILL",
        "TERANG", "STAWELL", "COLAC", "MILDURA", "TRARALGON", "BENALLA",
        "YARRA VALLEY", "CASTERTON", "HORSHAM", "TATURA", "STONY CREEK",
        "WARRNAMBOOL", "SALE", "CRANBOURNE", "MORNINGTON", "MOE", "DONALD",
        "WARRACKNABEAL", "WOOLAMAI", "BALNARRING", "MURTOA", "HEALESVILLE",
        "AVOCA", "KERANG", "HANGING ROCK", "COLERAINE", "YEA", "CAMPERDOWN",
        "ALEXANDRA", "EDENHOPE", "BURRUMBEET", "GREAT WESTERN", "TOWONG",
        "GUNBOWER", "ST ARNAUD", "MANSFIELD", "MALLACOOTA", "DUNKELD",
        "BERRIGAN", "PENS HURST", "PENSHURST", "NHILL",
    ]

    for k in known:
        if k in t:
            return "PENSHURST" if k == "PENS HURST" else k

    return t or raw

def track_group(canon):
    if canon in {"FLEMINGTON", "CAULFIELD", "CAULFIELD HEATH", "MOONEE VALLEY", "SANDOWN", "SANDOWN HILLSIDE", "SANDOWN LAKESIDE"}:
        return "METRO"
    if canon in {"PAKENHAM SYNTHETIC", "BALLARAT SYNTHETIC", "GEELONG SYNTHETIC"}:
        return "SYNTHETIC"
    if canon.endswith("TRIAL"):
        return "TRIAL"
    return "COUNTRY"

def surface(canon):
    if "SYNTHETIC" in canon:
        return "SYNTHETIC"
    return "TURF"

def confidence(raw, canon):
    if not raw or not canon:
        return "LOW"
    if raw.upper() == canon:
        return "HIGH"
    if canon in raw.upper():
        return "HIGH"
    return "MEDIUM"

if not SRC.exists():
    raise FileNotFoundError(f"Missing source: {SRC}")

tracks = {}
with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        raw = clean(r.get("track"))
        if raw:
            tracks[raw] = tracks.get(raw, 0) + 1

built_at = datetime.now(timezone.utc).isoformat()

rows = []
for raw, n in sorted(tracks.items(), key=lambda x: (-x[1], x[0])):
    canon = canonical(raw)
    rows.append({
        "built_at": built_at,
        "raw_track": raw,
        "canonical_track": canon,
        "track_group": track_group(canon),
        "surface": surface(canon),
        "rows_seen": n,
        "auto_confidence": confidence(raw, canon),
        "review_status": "AUTO_SEEDED_V2",
    })

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    fields = ["built_at","raw_track","canonical_track","track_group","surface","rows_seen","auto_confidence","review_status"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

summary = [
    {"metric": "status", "value": "EDGEIQ_TRACK_CANONICAL_DICTIONARY_V2_BUILT"},
    {"metric": "raw_tracks", "value": len(rows)},
    {"metric": "canonical_tracks", "value": len(set(r["canonical_track"] for r in rows))},
    {"metric": "metro_raw_rows", "value": sum(int(r["rows_seen"]) for r in rows if r["track_group"] == "METRO")},
    {"metric": "country_raw_rows", "value": sum(int(r["rows_seen"]) for r in rows if r["track_group"] == "COUNTRY")},
    {"metric": "synthetic_raw_rows", "value": sum(int(r["rows_seen"]) for r in rows if r["track_group"] == "SYNTHETIC")},
    {"metric": "output", "value": str(OUT)},
    {"metric": "built_at", "value": built_at},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["metric","value"])
    w.writeheader()
    w.writerows(summary)

print("[TRACK_DICTIONARY_V2] COMPLETE")
print(f"raw_tracks={len(rows)}")
print(f"canonical_tracks={len(set(r['canonical_track'] for r in rows))}")
print(f"output={OUT}")
