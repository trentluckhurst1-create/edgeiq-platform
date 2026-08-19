from pathlib import Path
import json
import re

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

targets = [
    ROOT / "src" / "edgeiq-os" / "race" / "services" / "formGuideNormaliser.ts",
    ROOT / "src" / "edgeiq-os" / "race" / "services" / "formGuideEnrichedFeed.ts",
    ROOT / "src" / "edgeiq-os" / "race" / "services" / "formGuideWorkspaceViewModel.ts",
    ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceFormGuideWorkspace.tsx",
]

patterns = [
    "silkUrl",
    "trainer",
    "jockey",
    "weight",
    "barrier",
    "epi",
    "rating",
    "epiRank",
    "suitabilityScore",
    "formMomentum",
    "marketPrice",
    "edgeiqPrice",
    "shapeFit",
    "careerProfile",
    "conditionProfile",
    "classProfile",
    "jockeyProfile",
    "raceDayPattern",
    "recentRuns",
]

for path in targets:
    print(f"\n=== {path.name} ===")

    if not path.exists():
        print("MISSING")
        continue

    lines = path.read_text(encoding="utf-8").splitlines()

    for index, line in enumerate(lines, start=1):
        if any(pattern in line for pattern in patterns):
            print(f"{index}: {line}")

data_root = ROOT / "public" / "data"

print("\n=== CANDIDATE FORM GUIDE DATA FILES ===")

for path in sorted(data_root.rglob("*.json")):
    name = path.name.lower()

    if any(
        token in name
        for token in [
            "form",
            "runner",
            "field",
            "epi",
            "market",
            "price",
            "catalog",
            "three_day",
        ]
    ):
        print(path.relative_to(ROOT))

print("\n=== SAMPLE JSON FIELD COVERAGE ===")

candidate_files = [
    path
    for path in data_root.rglob("*.json")
    if any(
        token in path.name.lower()
        for token in ["form", "runner", "field", "catalog", "three_day"]
    )
]

field_names = {
    "silk",
    "silk_url",
    "silkUrl",
    "trainer",
    "jockey",
    "weight",
    "barrier",
    "epi",
    "eri",
    "rating",
    "suitability",
    "form_momentum",
    "market",
    "market_price",
    "edgeiq_price",
}

def walk(value, found, depth=0):
    if depth > 8:
        return

    if isinstance(value, dict):
        for key, child in value.items():
            if key in field_names:
                found.add(key)
            walk(child, found, depth + 1)
    elif isinstance(value, list):
        for child in value[:100]:
            walk(child, found, depth + 1)

for path in sorted(candidate_files)[:40]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        continue

    found = set()
    walk(payload, found)

    if found:
        print(f"{path.relative_to(ROOT)} -> {sorted(found)}")

print("\nFORM_GUIDE_DATA_WIRING_PROBE_COMPLETE")
