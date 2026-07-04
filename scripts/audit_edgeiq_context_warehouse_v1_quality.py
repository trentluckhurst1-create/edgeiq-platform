import csv
from pathlib import Path
from datetime import datetime

BASE = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = BASE / "public" / "data"

SRC = DATA / "edgeiq_context_warehouse_v1.csv"
OUT = DATA / "edgeiq_context_warehouse_v1_quality_audit.csv"
SUMMARY = DATA / "edgeiq_context_warehouse_v1_quality_audit_summary.csv"

rows = []
with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

def clean(v):
    return (v or "").strip()

summary_counts = {}

for r in rows:
    et = clean(r.get("entity_type"))
    sig = clean(r.get("signal"))
    key = (et, sig)
    summary_counts[key] = summary_counts.get(key, 0) + 1

audit_rows = []
for (entity_type, signal), count in sorted(summary_counts.items()):
    audit_rows.append({
        "entity_type": entity_type,
        "signal": signal,
        "rows": count
    })

blank_entity = sum(1 for r in rows if not clean(r.get("entity_name")))
blank_signal = sum(1 for r in rows if not clean(r.get("signal")))
blank_context = sum(1 for r in rows if not clean(r.get("context_type")))

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["entity_type","signal","rows"])
    writer.writeheader()
    writer.writerows(audit_rows)

summary = [
    {"metric":"status","value":"COMPLETE"},
    {"metric":"source_rows","value":len(rows)},
    {"metric":"blank_entity_name","value":blank_entity},
    {"metric":"blank_signal","value":blank_signal},
    {"metric":"blank_context_type","value":blank_context},
    {"metric":"positive_like_rows","value":sum(1 for r in rows if clean(r.get("signal")) in ["POSITIVE_PROFILE","STRONG_POSITIVE","POSITIVE","CONTEXT_EDGE","MILD_CONTEXT_EDGE","CONNECTION_EDGE","MILD_CONNECTION_EDGE"])},
    {"metric":"caution_like_rows","value":sum(1 for r in rows if clean(r.get("signal")) in ["CAUTION_PROFILE","NEGATIVE","CONTEXT_RISK","CONNECTION_RISK"])},
    {"metric":"built_at","value":datetime.now().isoformat()},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric","value"])
    writer.writeheader()
    writer.writerows(summary)

print("[EDGEIQ_CONTEXT_WAREHOUSE_V1_QUALITY_AUDIT] COMPLETE")
print(f"audit={OUT}")
print(f"summary={SUMMARY}")
