import json
from pathlib import Path

RAW = Path(r".\public\data\sportsbet_live_market_raw_events_sample_v1.json")

data = json.loads(RAW.read_text(encoding="utf-8"))

print("=" * 80)
print("TOP LEVEL KEYS")
print("=" * 80)

if isinstance(data, list) and data:
    root = data[0]
elif isinstance(data, dict):
    root = data
else:
    root = {}

for k in root.keys():
    print(k)

print()
print("=" * 80)
print("SEARCHING FOR STATUS FIELDS")
print("=" * 80)

targets = [
    "status",
    "runnerStatus",
    "selectionStatus",
    "entrantStatus",
    "isScratched",
    "withdrawn",
    "deduction",
    "suspended",
    "priceCode",
]

hits = []

def walk(obj, path="root"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}"
            for t in targets:
                if t.lower() in k.lower():
                    hits.append((p, type(v).__name__, str(v)[:120]))
            walk(v, p)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            walk(item, f"{path}[{i}]")

walk(data)

for h in hits[:300]:
    print(h)

print()
print("TOTAL HITS:", len(hits))
