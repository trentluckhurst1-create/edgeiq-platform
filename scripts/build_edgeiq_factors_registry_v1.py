import csv
from pathlib import Path
from datetime import datetime

BASE = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = BASE / "public" / "data"

WAREHOUSE = DATA / "edgeiq_context_warehouse_v1.csv"
HORSE_VIEW = DATA / "edgeiq_horse_view_engine_v1.csv"
JOCKEY_VIEW = DATA / "edgeiq_jockey_view_engine_v1.csv"
CONNECTION_VIEW = DATA / "edgeiq_connection_view_engine_v1.csv"

OUT = DATA / "edgeiq_factors_registry_v1.csv"
SUMMARY = DATA / "edgeiq_factors_registry_v1_summary.csv"

def clean(v):
    return (v or "").strip()

def load_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

rows = []

for r in load_csv(HORSE_VIEW):
    rows.append({
        "entity_type": "HORSE",
        "entity_name": clean(r.get("entity_name")),
        "factor_label": clean(r.get("factor_label")),
        "customer_tone": clean(r.get("customer_tone")),
        "context_type": clean(r.get("context_type")),
        "context_value": clean(r.get("context_value")),
        "starts": clean(r.get("starts")),
        "win_pct": clean(r.get("win_pct")),
        "base_win_pct": clean(r.get("base_win_pct")),
        "view_headline": clean(r.get("view_headline")),
        "view_detail": clean(r.get("view_detail")),
        "key_insight": clean(r.get("key_insight")),
        "source_file": HORSE_VIEW.name,
    })

for r in load_csv(JOCKEY_VIEW):
    rows.append({
        "entity_type": "JOCKEY",
        "entity_name": clean(r.get("entity_name")),
        "factor_label": clean(r.get("factor_label")),
        "customer_tone": clean(r.get("customer_tone")),
        "context_type": clean(r.get("context_type")),
        "context_value": clean(r.get("context_value")),
        "starts": clean(r.get("starts")),
        "win_pct": clean(r.get("win_pct")),
        "base_win_pct": "",
        "view_headline": clean(r.get("view_headline")),
        "view_detail": clean(r.get("view_detail")),
        "key_insight": clean(r.get("key_insight")),
        "source_file": JOCKEY_VIEW.name,
    })

for r in load_csv(CONNECTION_VIEW):
    rows.append({
        "entity_type": "CONNECTION",
        "entity_name": clean(r.get("entity_name")),
        "factor_label": clean(r.get("factor_label")),
        "customer_tone": clean(r.get("customer_tone")),
        "context_type": "CONNECTION",
        "context_value": clean(r.get("evidence_band")),
        "starts": clean(r.get("starts")),
        "win_pct": clean(r.get("combo_win_pct")),
        "base_win_pct": clean(r.get("trainer_base_win_pct")),
        "view_headline": clean(r.get("view_headline")),
        "view_detail": clean(r.get("view_detail")),
        "key_insight": clean(r.get("key_insight")),
        "source_file": CONNECTION_VIEW.name,
    })

tone_order = {
    "POSITIVE": 0,
    "CAUTION": 1
}

rows.sort(
    key=lambda r: (
        r["entity_type"],
        r["entity_name"],
        tone_order.get(r["customer_tone"], 9),
        r["factor_label"],
        r["context_type"],
        r["context_value"]
    )
)

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "entity_type",
            "entity_name",
            "factor_label",
            "customer_tone",
            "context_type",
            "context_value",
            "starts",
            "win_pct",
            "base_win_pct",
            "view_headline",
            "view_detail",
            "key_insight",
            "source_file",
        ]
    )
    writer.writeheader()
    writer.writerows(rows)

summary = [
    {"metric":"status","value":"COMPLETE"},
    {"metric":"registry_rows","value":len(rows)},
    {"metric":"horse_rows","value":sum(1 for r in rows if r["entity_type"]=="HORSE")},
    {"metric":"jockey_rows","value":sum(1 for r in rows if r["entity_type"]=="JOCKEY")},
    {"metric":"connection_rows","value":sum(1 for r in rows if r["entity_type"]=="CONNECTION")},
    {"metric":"positive_rows","value":sum(1 for r in rows if r["customer_tone"]=="POSITIVE")},
    {"metric":"caution_rows","value":sum(1 for r in rows if r["customer_tone"]=="CAUTION")},
    {"metric":"built_at","value":datetime.now().isoformat()},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric","value"])
    writer.writeheader()
    writer.writerows(summary)

print("[EDGEIQ_FACTORS_REGISTRY_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
