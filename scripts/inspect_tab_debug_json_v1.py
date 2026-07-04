import json
import re
from pathlib import Path
from collections import Counter

DEBUG_DIR = Path(".\public\data\tab_debug_v1")

KEY_NEEDLES = [
    "runner", "selection", "entrant", "competitor", "horse",
    "price", "odds", "return", "market", "meeting", "race",
    "fixed", "win", "place", "proposition"
]

def walk(x, path=""):
    if isinstance(x, dict):
        yield path, x
        for k, v in x.items():
            yield from walk(v, f"{path}.{k}" if path else str(k))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from walk(v, f"{path}[{i}]")

for fp in sorted(DEBUG_DIR.glob("tab_response_*.json")):
    try:
        payload = json.loads(fp.read_text(encoding="utf-8"))
    except Exception as e:
        print(fp.name, "BAD JSON", e)
        continue

    keys = Counter()
    hits = []
    samples = []

    for path, d in walk(payload):
        if not isinstance(d, dict):
            continue

        for k, v in d.items():
            keys[k] += 1
            lk = str(k).lower()
            if any(n in lk for n in KEY_NEEDLES):
                hits.append((path, k, type(v).__name__, str(v)[:120]))

        text = json.dumps(d, ensure_ascii=False)[:1200].lower()
        if any(n in text for n in KEY_NEEDLES):
            samples.append((path, json.dumps(d, ensure_ascii=False)[:500]))

    print("")
    print("=" * 100)
    print(fp.name, "bytes", fp.stat().st_size)
    print("TOP_KEYS:", keys.most_common(30))
    print("HITS:")
    for h in hits[:30]:
        print(" ", h)
    print("SAMPLES:")
    for s in samples[:5]:
        print(" ", s[0], s[1].replace("\n", " ")[:500])
