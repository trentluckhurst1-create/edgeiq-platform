from pathlib import Path
import json
import re
import unicodedata

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

NORMALISER = ROOT / "src" / "edgeiq-os" / "race" / "services" / "formGuideNormaliser.ts"
ENRICHED_SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "formGuideEnrichedFeed.ts"

CATALOG = ROOT / "public" / "data" / "edgeiq_three_day_product_catalog_v1.json"
ENRICHED = ROOT / "public" / "data" / "edgeiq_form_guide_enriched_v2.json"

def canonical_text(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^A-Z0-9]+", "", text.upper())

def first_value(mapping, keys):
    if not isinstance(mapping, dict):
        return None
    for key in keys:
        value = mapping.get(key)
        if value not in (None, "", [], {}):
            return value
    return None

def walk_dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_dicts(child)

def likely_runner(node):
    if not isinstance(node, dict):
        return False

    horse = first_value(
        node,
        [
            "horse",
            "horseName",
            "runner",
            "runnerName",
            "name",
        ],
    )

    has_runner_field = any(
        key in node
        for key in [
            "barrier",
            "barrierNumber",
            "jockey",
            "trainer",
            "weight",
            "epi",
            "rating",
            "suitability",
            "recentRuns",
            "recent_runs",
        ]
    )

    return bool(horse and has_runner_field)

def extract_runners(payload):
    output = []

    for node in walk_dicts(payload):
        if not likely_runner(node):
            continue

        horse = first_value(
            node,
            ["horse", "horseName", "runner", "runnerName", "name"],
        )

        race_key = first_value(
            node,
            [
                "raceKey",
                "race_key",
                "canonicalRaceKey",
                "canonical_race_key",
            ],
        )

        meeting = first_value(
            node,
            [
                "meeting",
                "meetingName",
                "track",
                "venue",
            ],
        )

        race_number = first_value(
            node,
            [
                "raceNumber",
                "race_number",
                "raceNo",
                "race_no",
                "number",
            ],
        )

        saddlecloth = first_value(
            node,
            [
                "saddlecloth",
                "saddleclothNumber",
                "runnerNumber",
                "number",
                "no",
            ],
        )

        output.append(
            {
                "horse": str(horse or ""),
                "horse_key": canonical_text(horse),
                "race_key": str(race_key or ""),
                "meeting": str(meeting or ""),
                "race_number": str(race_number or ""),
                "saddlecloth": str(saddlecloth or ""),
                "trainer": first_value(node, ["trainer", "trainerName"]),
                "jockey": first_value(node, ["jockey", "jockeyName"]),
                "weight": first_value(node, ["weight", "weightAllocated"]),
                "barrier": first_value(node, ["barrier", "barrierNumber"]),
                "silk": first_value(node, ["silkUrl", "silk_url", "silks"]),
                "epi": first_value(node, ["epi"]),
                "eri": first_value(node, ["rating", "eri"]),
                "suitability": first_value(node, ["suitability"]),
                "market": first_value(node, ["market", "marketPrice", "market_price"]),
                "edgeiq_price": first_value(
                    node,
                    ["edgeiqPrice", "edgeiq_price", "fairPrice", "fair_price"],
                ),
            }
        )

    deduped = {}
    for runner in output:
        key = (
            runner["horse_key"],
            runner["race_key"],
            runner["meeting"],
            runner["race_number"],
        )

        existing = deduped.get(key)
        if existing is None:
            deduped[key] = runner
            continue

        existing_score = sum(
            value not in (None, "", [], {})
            for value in existing.values()
        )
        new_score = sum(
            value not in (None, "", [], {})
            for value in runner.values()
        )

        if new_score > existing_score:
            deduped[key] = runner

    return list(deduped.values())

def relevant_moe_race_two(runner):
    joined = " ".join(
        [
            runner["race_key"],
            runner["meeting"],
            runner["race_number"],
        ]
    ).upper()

    horse_names = {
        "MIGHTYMYSTIC",
        "PROFFER",
        "ROCKABOUT",
        "BIDU",
        "GALACTICGIRL",
        "HIGHABOVEME",
        "KADESH",
        "LOSTTHEPLOT",
        "LOVELYHEAD",
        "SNITCHY",
        "STORMYSONG",
        "VALORADA",
        "ALPHABET",
        "MAHRAJAN",
    }

    return (
        runner["horse_key"] in horse_names
        or ("MOE" in joined and ("R2" in joined or " 2" in joined))
    )

if not CATALOG.exists():
    raise SystemExit(f"MISSING_CATALOG={CATALOG}")

if not ENRICHED.exists():
    raise SystemExit(f"MISSING_ENRICHED={ENRICHED}")

catalog_payload = json.loads(CATALOG.read_text(encoding="utf-8"))
enriched_payload = json.loads(ENRICHED.read_text(encoding="utf-8"))

catalog_runners = [
    runner
    for runner in extract_runners(catalog_payload)
    if relevant_moe_race_two(runner)
]

enriched_runners = [
    runner
    for runner in extract_runners(enriched_payload)
    if relevant_moe_race_two(runner)
]

print("=== CATALOG MOE R2 RUNNERS ===")
for runner in catalog_runners:
    print(runner)

print()
print("=== ENRICHED MOE R2 RUNNERS ===")
for runner in enriched_runners:
    print(runner)

catalog_by_horse = {
    runner["horse_key"]: runner
    for runner in catalog_runners
    if runner["horse_key"]
}

enriched_by_horse = {
    runner["horse_key"]: runner
    for runner in enriched_runners
    if runner["horse_key"]
}

all_horses = sorted(set(catalog_by_horse) | set(enriched_by_horse))

print()
print("=== HORSE JOIN COMPARISON ===")

matched = 0
catalog_only = 0
enriched_only = 0

for horse_key in all_horses:
    official = catalog_by_horse.get(horse_key)
    enriched = enriched_by_horse.get(horse_key)

    if official and enriched:
        status = "MATCH"
        matched += 1
    elif official:
        status = "CATALOG_ONLY"
        catalog_only += 1
    else:
        status = "ENRICHED_ONLY"
        enriched_only += 1

    print(
        status,
        horse_key,
        {
            "catalog_race_key": official["race_key"] if official else "",
            "enriched_race_key": enriched["race_key"] if enriched else "",
            "catalog_no": official["saddlecloth"] if official else "",
            "enriched_no": enriched["saddlecloth"] if enriched else "",
        },
    )

print()
print(
    "JOIN_SUMMARY",
    {
        "catalog_runners": len(catalog_runners),
        "enriched_runners": len(enriched_runners),
        "matched_by_horse": matched,
        "catalog_only": catalog_only,
        "enriched_only": enriched_only,
    },
)

print()
print("=== NORMALISER JOIN CODE ===")

normaliser_lines = NORMALISER.read_text(encoding="utf-8").splitlines()

for index, line in enumerate(normaliser_lines, start=1):
    if any(
        token in line
        for token in [
            "officialRunner",
            "enrichedRunner",
            ".find(",
            "runnerName",
            "horseName",
            "raceKey",
            "race_key",
            "normaliseFormGuideRace",
        ]
    ):
        start = max(1, index - 3)
        end = min(len(normaliser_lines), index + 5)

        print(f"\n--- lines {start}-{end} ---")
        for line_number in range(start, end + 1):
            print(f"{line_number}: {normaliser_lines[line_number - 1]}")

print()
print("=== ENRICHED RACE MATCH CODE ===")

enriched_lines = ENRICHED_SERVICE.read_text(encoding="utf-8").splitlines()

for index, line in enumerate(enriched_lines, start=1):
    if any(
        token in line
        for token in [
            "findEnrichedFormGuideRace",
            ".find(",
            "raceKey",
            "race_key",
            "meeting",
            "raceNumber",
        ]
    ):
        start = max(1, index - 3)
        end = min(len(enriched_lines), index + 5)

        print(f"\n--- lines {start}-{end} ---")
        for line_number in range(start, end + 1):
            print(f"{line_number}: {enriched_lines[line_number - 1]}")

print()
print("FORM_GUIDE_JOIN_DIAGNOSIS_COMPLETE")
