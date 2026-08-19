import json
from pathlib import Path

RAW = Path(r".\public\data\sportsbet_live_market_raw_events_sample_v1.json")

data = json.loads(RAW.read_text(encoding="utf-8"))

print("=" * 80)
print("ROOT TYPES")
print("=" * 80)

for k, v in data.items():
    print(k, type(v).__name__)

print()
print("=" * 80)
print("RACECARD SAMPLE 1 KEYS")
print("=" * 80)

sample = data.get("racecard_sample_1", {})

if isinstance(sample, dict):
    for k in sample.keys():
        print(k)

print()
print("=" * 80)
print("RACECARD SAMPLE 2 KEYS")
print("=" * 80)

sample2 = data.get("racecard_sample_2", {})

if isinstance(sample2, dict):
    for k in sample2.keys():
        print(k)

print()
print("=" * 80)
print("DEEP SEARCH FOR RUNNERS / SELECTIONS")
print("=" * 80)

targets = [
    "runner",
    "selection",
    "entrant",
    "competitor",
    "status",
    "scr",
    "withdraw",
]

hits = []

def walk(obj, path="root"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}"

            for t in targets:
                if t.lower() in k.lower():
                    hits.append((p, type(v).__name__))

            walk(v, p)

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            walk(item, f"{path}[{i}]")

walk(data)

for h in hits[:500]:
    print(h)

print()
print("TOTAL:", len(hits))
