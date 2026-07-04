import csv
import re
from pathlib import Path
from datetime import datetime

BASE = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = BASE / "public" / "data"

SRC = DATA / "edgeiq_trainer_jockey_runner_history_canonical_v1.csv"

OUT = DATA / "edgeiq_entity_resolution_master_v1.csv"
SUMMARY = DATA / "edgeiq_entity_resolution_master_v1_summary.csv"

def clean(v):
    return (v or "").strip()

def norm(v):
    return re.sub(r"[^A-Z0-9]", "", clean(v).upper())

rows = []
with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

entities = {}

def add_entity(entity_type, display_name, canonical_name, canonical_key):
    display_name = clean(display_name)
    canonical_name = clean(canonical_name)
    canonical_key = clean(canonical_key)

    if not display_name and not canonical_name:
        return

    display_norm = norm(display_name)
    canonical_norm = norm(canonical_name)
    key_norm = norm(canonical_key)

    candidates = set()
    for v in [display_norm, canonical_norm, key_norm]:
        if v:
            candidates.add(v)

    if not candidates:
        return

    entity_id = f"{entity_type}|{canonical_key or canonical_norm or display_norm}"

    if entity_id not in entities:
        entities[entity_id] = {
            "entity_type": entity_type,
            "display_names": set(),
            "canonical_name": canonical_name,
            "canonical_key": canonical_key,
            "match_keys": set(),
            "rows_seen": 0,
        }

    e = entities[entity_id]

    if display_name:
        e["display_names"].add(display_name)
    if canonical_name and not e["canonical_name"]:
        e["canonical_name"] = canonical_name
    if canonical_key and not e["canonical_key"]:
        e["canonical_key"] = canonical_key

    e["match_keys"].update(candidates)
    e["rows_seen"] += 1

for r in rows:
    add_entity(
        "TRAINER",
        r.get("trainer"),
        r.get("trainer_canonical"),
        r.get("trainer_canonical_key") or r.get("trainer_key"),
    )

    add_entity(
        "JOCKEY",
        r.get("jockey"),
        r.get("jockey_canonical"),
        r.get("jockey_canonical_key") or r.get("jockey_key"),
    )

out_rows = []

for entity_id, e in entities.items():
    for mk in sorted(e["match_keys"]):
        out_rows.append({
            "entity_type": e["entity_type"],
            "match_key": mk,
            "canonical_name": e["canonical_name"],
            "canonical_key": e["canonical_key"],
            "display_names": " | ".join(sorted(e["display_names"])),
            "rows_seen": e["rows_seen"],
            "built_at": datetime.now().isoformat(),
        })

out_rows.sort(key=lambda r: (r["entity_type"], r["canonical_key"], r["match_key"]))

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "entity_type",
            "match_key",
            "canonical_name",
            "canonical_key",
            "display_names",
            "rows_seen",
            "built_at",
        ]
    )
    writer.writeheader()
    writer.writerows(out_rows)

summary = [
    {"metric":"status","value":"COMPLETE"},
    {"metric":"source_rows","value":len(rows)},
    {"metric":"unique_entities","value":len(entities)},
    {"metric":"resolution_rows","value":len(out_rows)},
    {"metric":"trainer_entities","value":sum(1 for e in entities.values() if e["entity_type"]=="TRAINER")},
    {"metric":"jockey_entities","value":sum(1 for e in entities.values() if e["entity_type"]=="JOCKEY")},
    {"metric":"built_at","value":datetime.now().isoformat()},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric","value"])
    writer.writeheader()
    writer.writerows(summary)

print("[EDGEIQ_ENTITY_RESOLUTION_MASTER_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
