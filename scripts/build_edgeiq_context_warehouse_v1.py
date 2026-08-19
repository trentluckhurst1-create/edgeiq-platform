import csv
from pathlib import Path
from datetime import datetime

BASE = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = BASE / "public" / "data"

HORSE = DATA / "edgeiq_horse_context_research_v1.csv"
JOCKEY = DATA / "edgeiq_jockey_context_research_v1.csv"
TRAINER = DATA / "edgeiq_trainer_context_research_v2.csv"
CONNECTION = DATA / "edgeiq_connection_context_research_v2_stability.csv"

OUT = DATA / "edgeiq_context_warehouse_v1.csv"
SUMMARY = DATA / "edgeiq_context_warehouse_v1_summary.csv"

warehouse = []

def load_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

for r in load_csv(HORSE):

    warehouse.append({
        "entity_type":"HORSE",
        "entity_name":r.get("horse_key",""),
        "context_type":r.get("context_type",""),
        "context_value":r.get("context_value",""),
        "signal":r.get("signal",""),
        "starts":r.get("starts",""),
        "win_pct":r.get("win_pct",""),
        "place_pct":r.get("place_pct",""),
        "insight":r.get("insight","")
    })

for r in load_csv(JOCKEY):

    warehouse.append({
        "entity_type":"JOCKEY",
        "entity_name":r.get("jockey",""),
        "context_type":r.get("context_type",""),
        "context_value":r.get("context_value",""),
        "signal":r.get("signal",""),
        "starts":r.get("starts",""),
        "win_pct":r.get("win_pct",""),
        "place_pct":r.get("place_pct",""),
        "insight":""
    })

for r in load_csv(TRAINER):

    warehouse.append({
        "entity_type":"TRAINER",
        "entity_name":r.get("trainer",""),
        "context_type":r.get("context_type",""),
        "context_value":r.get("context_value",""),
        "signal":r.get("signal",""),
        "starts":r.get("starts",""),
        "win_pct":r.get("win_pct",""),
        "place_pct":r.get("place_pct",""),
        "insight":r.get("insight","")
    })

for r in load_csv(CONNECTION):

    warehouse.append({
        "entity_type":"CONNECTION",
        "entity_name":r.get("connection",""),
        "context_type":"CONNECTION",
        "context_value":r.get("evidence_band",""),
        "signal":r.get("signal",""),
        "starts":r.get("starts",""),
        "win_pct":r.get("combo_win_pct",""),
        "place_pct":r.get("combo_place_pct",""),
        "insight":r.get("insight","")
    })

warehouse.sort(
    key=lambda r: (
        r["entity_type"],
        r["entity_name"],
        r["context_type"]
    )
)

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "entity_type",
            "entity_name",
            "context_type",
            "context_value",
            "signal",
            "starts",
            "win_pct",
            "place_pct",
            "insight"
        ]
    )
    writer.writeheader()
    writer.writerows(warehouse)

summary = [
    {"metric":"status","value":"COMPLETE"},
    {"metric":"warehouse_rows","value":len(warehouse)},
    {"metric":"horse_rows","value":sum(1 for r in warehouse if r["entity_type"]=="HORSE")},
    {"metric":"jockey_rows","value":sum(1 for r in warehouse if r["entity_type"]=="JOCKEY")},
    {"metric":"trainer_rows","value":sum(1 for r in warehouse if r["entity_type"]=="TRAINER")},
    {"metric":"connection_rows","value":sum(1 for r in warehouse if r["entity_type"]=="CONNECTION")},
    {"metric":"built_at","value":datetime.now().isoformat()},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric","value"])
    writer.writeheader()
    writer.writerows(summary)

print("[EDGEIQ_CONTEXT_WAREHOUSE_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
