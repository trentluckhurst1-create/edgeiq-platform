from pathlib import Path
import json
import re

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
CATALOG = ROOT / "public" / "data" / "edgeiq_three_day_product_catalog_v1.json"

TARGETS = {
    "MIGHTYMYSTIC",
    "PROFFER",
    "ROCKABOUT",
}

def canonical(value):
    return re.sub(r"[^A-Z0-9]+", "", str(value or "").upper())

def walk(value, path="$"):
    if isinstance(value, dict):
        yield path, value

        for key, child in value.items():
            yield from walk(child, f"{path}.{key}")

    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, f"{path}[{index}]")

def candidate_name(node):
    if not isinstance(node, dict):
        return ""

    direct_keys = [
        "horseName",
        "runnerName",
        "runner",
        "name",
        "horse",
    ]

    for key in direct_keys:
        value = node.get(key)

        if isinstance(value, str) and canonical(value) in TARGETS:
            return value

        if isinstance(value, dict):
            for nested_key in [
                "horseName",
                "runnerName",
                "name",
                "fullName",
            ]:
                nested_value = value.get(nested_key)

                if isinstance(nested_value, str) and canonical(nested_value) in TARGETS:
                    return nested_value

    return ""

def print_scalar_paths(value, path="$", depth=0):
    if depth > 6:
        return

    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"

            if isinstance(child, (str, int, float, bool)) or child is None:
                print(f"{child_path} = {child!r}")
            else:
                print_scalar_paths(child, child_path, depth + 1)

    elif isinstance(value, list):
        for index, child in enumerate(value[:12]):
            child_path = f"{path}[{index}]"

            if isinstance(child, (str, int, float, bool)) or child is None:
                print(f"{child_path} = {child!r}")
            else:
                print_scalar_paths(child, child_path, depth + 1)

if not CATALOG.exists():
    raise SystemExit(f"MISSING_CATALOG={CATALOG}")

payload = json.loads(CATALOG.read_text(encoding="utf-8"))

matches = []

for path, node in walk(payload):
    name = candidate_name(node)

    if name:
        matches.append((canonical(name), name, path, node))

print("=== EXACT RUNNER OBJECT LOCATIONS ===")

seen = set()

for horse_key, name, path, node in matches:
    identity = (horse_key, path)

    if identity in seen:
        continue

    seen.add(identity)

    print()
    print("=" * 100)
    print(f"HORSE={name}")
    print(f"PATH={path}")
    print("=" * 100)

    print_scalar_paths(node, path)

print()
print("=== FIELD KEY SEARCH ===")

wanted_tokens = [
    "trainer",
    "jockey",
    "rider",
    "weight",
    "barrier",
    "silk",
    "market",
    "price",
    "runnernumber",
    "saddlecloth",
]

for horse_key, name, path, node in matches:
    print()
    print(f"--- {name} ---")

    for scalar_path, scalar_node in walk(node, path):
        if not isinstance(scalar_node, dict):
            continue

        for key, value in scalar_node.items():
            normalised_key = canonical(key)

            if any(token.upper() in normalised_key for token in wanted_tokens):
                print(f"{scalar_path}.{key} = {value!r}")

print()
print("CATALOG_RUNNER_STRUCTURE_PROBE_COMPLETE")
