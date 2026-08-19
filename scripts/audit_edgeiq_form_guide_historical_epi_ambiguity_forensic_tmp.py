import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "full-product-implementation"

FORM = DATA / "edgeiq_form_guide_enriched_v2.json"
HIST = DATA / "edgeiq_historical_performance_rating_v6_1_research.csv"

OUT_TXT = DOCS / "FORM_GUIDE_HISTORICAL_EPI_AMBIGUITY_FORENSIC_AUDIT.txt"
OUT_CSV = DOCS / "FORM_GUIDE_HISTORICAL_EPI_AMBIGUITY_FORENSIC_AUDIT.csv"


TRACK_ALIASES = {
    "WARRNAMBOOL": "WNBL",
    "WNBL": "WNBL",
    "LADBROKESGEELONG": "GEEL",
    "BET365GEELONG": "GEEL",
    "GEELONG": "GEEL",
    "GEEL": "GEEL",
    "SPORTSBETBALLARAT": "BRAT",
    "BALLARAT": "BRAT",
    "BRAT": "BRAT",
    "SPORTSBETBALLARATSYNTHETIC": "BRTS",
    "BALLARATSYNTHETIC": "BRTS",
    "BRTS": "BRTS",
    "FLEMINGTON": "FLEM",
    "FLEM": "FLEM",
    "CASTERTON": "CAST",
    "CAST": "CAST",
    "BET365TERANG": "TER",
    "TERANG": "TER",
    "TER": "TER",
    "SPORTSBETSANDOWNLAKESIDE": "SANL",
    "LADBROKESPARKLAKESIDE": "SANL",
    "SANDOWNLAKESIDE": "SANL",
    "SANL": "SANL",
    "SPORTSBETSANDOWNHILLSIDE": "SANH",
    "SANDOWNHILLSIDE": "SANH",
    "SANH": "SANH",
    "BET365HAMILTON": "HTON",
    "HAMILTON": "HTON",
    "HTON": "HTON",
    "CAULFIELD": "CAUL",
    "CAUL": "CAUL",
    "CAULFIELDHEATH": "CAUH",
    "CAUH": "CAUH",
    "MORNINGTON": "MORN",
    "MORN": "MORN",
    "BET365SEYMOUR": "SEYM",
    "SEYMOUR": "SEYM",
    "SEYM": "SEYM",
    "APIAMBENDIGO": "BDGO",
    "BENDIGO": "BDGO",
    "BDGO": "BDGO",
    "SPORTSBETPAKENHAM": "PAKM",
    "SOUTHSIDEPAKENHAM": "PAKM",
    "PAKENHAM": "PAKM",
    "PAKM": "PAKM",
    "SPORTSBETPAKENHAMSYNTHETIC": "PAKS",
    "SOUTHSIDEPAKENHAMSYNTHETIC": "PAKS",
    "PAKENHAMSYNTHETIC": "PAKS",
    "PAKS": "PAKS",
    "BET365ECHUCA": "ECHA",
    "ECHUCA": "ECHA",
    "ECHA": "ECHA",
    "BET365PARKKILMORE": "KILM",
    "KILMORE": "KILM",
    "KILM": "KILM",
    "ARARAT": "ARAT",
    "ARAT": "ARAT",
    "BET365PARKKYNETON": "KYNE",
    "KYNETON": "KYNE",
    "KYNE": "KYNE",
    "SPORTSBETWANGARATTA": "WANG",
    "WANGARATTA": "WANG",
    "WANG": "WANG",
    "BET365MILDURA": "MILD",
    "MILDURA": "MILD",
    "MILD": "MILD",
    "PICKLEBETPARKWERRIBEE": "WERR",
    "TABPARKWERRIBEE": "WERR",
    "WERRIBEE": "WERR",
    "WERR": "WERR",
    "BET365SWANHILL": "SWH",
    "SWANHILL": "SWH",
    "SWH": "SWH",
    "COLERAINE": "COLR",
    "COLR": "COLR",
    "CRANBOURNE": "CRAN",
    "SOUTHSIDECRANBOURNE": "CRAN",
    "CRAN": "CRAN",
    "DONALD": "DON",
    "DON": "DON",
    "HORSHAM": "HSHM",
    "HSHM": "HSHM",
    "WARRACKNABEAL": "WKBL",
    "BETDELUXEWARRACKNABEAL": "WKBL",
    "WKBL": "WKBL",
    "BET365STAWELL": "STAW",
    "STAWELL": "STAW",
    "STAW": "STAW",
    "THEVALLEY": "MV",
    "MOONEEVALLEY": "MV",
    "MV": "MV",
    "BET365BAIRNSDALE": "BDLE",
    "BAIRNSDALE": "BDLE",
    "BDLE": "BDLE",
    "TATURA": "TAT",
    "TAT": "TAT",
    "BET365BENALLA": "BLLA",
    "BENALLA": "BLLA",
    "BLLA": "BLLA",
    "BET365COLAC": "CLAC",
    "COLAC": "CLAC",
    "CLAC": "CLAC",
    "BET365YARRAVALLEY": "YVL",
    "YARRAVALLEY": "YVL",
    "YVL": "YVL",
    "BET365PARKWODONGA": "WOD",
    "PICKLEBETPARKWODONGA": "WOD",
    "WODONGA": "WOD",
    "WOD": "WOD",
    "BET365CAMPERDOWN": "CAMP",
    "CAMPERDOWN": "CAMP",
    "CAMP": "CAMP",
}


def text(value: Any) -> str:
    if value is None:
        return ""
    output = str(value).strip()
    if output.lower() in {"", "-", "none", "null", "undefined", "n/a", "na"}:
        return ""
    return output


def compact(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", text(value).upper())


def canonical_track(value: Any) -> str:
    key = compact(value)
    return TRACK_ALIASES.get(key, key)


def horse_key(value: Any) -> str:
    output = compact(value)

    for suffix in ("AUS", "NZ", "GB", "IRE", "USA", "FR", "JPN"):
        if output.endswith(suffix) and len(output) > len(suffix) + 2:
            output = output[:-len(suffix)]

    return output


def distance_key(value: Any) -> str:
    raw = text(value)
    if not raw:
        return ""

    match = re.search(r"\d+(?:\.\d+)?", raw.replace(",", ""))
    if not match:
        return ""

    number = float(match.group(0))
    return str(int(number)) if number.is_integer() else str(number)


def rating_value(value: Any) -> float | None:
    raw = text(value)

    if not raw:
        return None

    try:
        return round(float(raw), 8)
    except ValueError:
        return None


with FORM.open(encoding="utf-8") as handle:
    form_payload = json.load(handle)

with HIST.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
    research_rows = list(csv.DictReader(handle))


research_index = defaultdict(list)

for row_number, row in enumerate(research_rows, start=2):
    key = (
        horse_key(row.get("horse")),
        text(row.get("race_date")),
        canonical_track(row.get("track")),
        distance_key(row.get("distance")),
    )

    if not all(key):
        continue

    research_index[key].append(
        {
            "row_number": row_number,
            "horse": text(row.get("horse")),
            "race_date": text(row.get("race_date")),
            "track": text(row.get("track")),
            "canonical_track": canonical_track(row.get("track")),
            "distance": distance_key(row.get("distance")),
            "rating": rating_value(row.get("performance_rating_v6_1_research")),
            "rating_raw": text(row.get("performance_rating_v6_1_research")),
            "source_file": text(row.get("source_file")),
        }
    )


counts = Counter()
source_pairs = Counter()
records = []

seen_form_keys = set()

for race in form_payload.get("races", []) or []:
    for runner in race.get("runners", []) or []:
        runner_name = text(
            runner.get("runnerName")
            or runner.get("runner")
            or runner.get("horse")
            or runner.get("name")
        )

        for run_index, run in enumerate(runner.get("fullForm", []) or [], start=1):
            key = (
                horse_key(runner_name),
                text(run.get("date") or run.get("raceDate")),
                canonical_track(run.get("track")),
                distance_key(run.get("distance")),
            )

            matches = research_index.get(key, [])

            if len(matches) <= 1:
                continue

            ratings = sorted(
                {
                    match["rating"]
                    for match in matches
                    if match["rating"] is not None
                }
            )

            sources = sorted(
                {
                    match["source_file"]
                    for match in matches
                    if match["source_file"]
                }
            )

            raw_tracks = sorted(
                {
                    match["track"]
                    for match in matches
                    if match["track"]
                }
            )

            exact_duplicate_signatures = {
                (
                    match["horse"],
                    match["race_date"],
                    match["track"],
                    match["distance"],
                    match["rating"],
                    match["source_file"],
                )
                for match in matches
            }

            if len(ratings) == 1:
                category = "SAME_RATING_MULTIPLE_ROWS"
            elif len(ratings) > 1:
                category = "CONFLICTING_RATINGS"
            else:
                category = "NO_RATED_ROWS"

            if len(exact_duplicate_signatures) == 1:
                duplicate_type = "EXACT_DUPLICATE"
            else:
                duplicate_type = "DISTINCT_SOURCE_ROWS"

            counts[category] += 1
            counts[duplicate_type] += 1
            counts["AMBIGUOUS_FORM_RUNS"] += 1
            counts["AMBIGUOUS_RESEARCH_ROWS"] += len(matches)

            for left_index, left in enumerate(sources):
                for right in sources[left_index + 1:]:
                    source_pairs[(left, right)] += 1

            form_key_signature = (
                runner_name,
                key[1],
                key[2],
                key[3],
            )

            if form_key_signature in seen_form_keys:
                repeated_form_key = "YES"
            else:
                repeated_form_key = "NO"
                seen_form_keys.add(form_key_signature)

            records.append(
                {
                    "category": category,
                    "duplicate_type": duplicate_type,
                    "runner": runner_name,
                    "run_index": run_index,
                    "form_date": key[1],
                    "form_track": text(run.get("track")),
                    "canonical_track": key[2],
                    "form_distance": key[3],
                    "match_count": len(matches),
                    "rating_count": len(ratings),
                    "ratings": " | ".join(str(value) for value in ratings),
                    "sources": " | ".join(sources),
                    "research_tracks": " | ".join(raw_tracks),
                    "repeated_form_key": repeated_form_key,
                    "matches_json": json.dumps(matches, ensure_ascii=False),
                }
            )


fieldnames = [
    "category",
    "duplicate_type",
    "runner",
    "run_index",
    "form_date",
    "form_track",
    "canonical_track",
    "form_distance",
    "match_count",
    "rating_count",
    "ratings",
    "sources",
    "research_tracks",
    "repeated_form_key",
    "matches_json",
]

OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(records)


lines = [
    "EDGEIQ FORM GUIDE HISTORICAL EPI AMBIGUITY FORENSIC AUDIT",
    "=" * 96,
    "",
    f"AMBIGUOUS_FORM_RUNS={counts['AMBIGUOUS_FORM_RUNS']}",
    f"AMBIGUOUS_RESEARCH_ROWS={counts['AMBIGUOUS_RESEARCH_ROWS']}",
    f"SAME_RATING_MULTIPLE_ROWS={counts['SAME_RATING_MULTIPLE_ROWS']}",
    f"CONFLICTING_RATINGS={counts['CONFLICTING_RATINGS']}",
    f"NO_RATED_ROWS={counts['NO_RATED_ROWS']}",
    f"EXACT_DUPLICATE={counts['EXACT_DUPLICATE']}",
    f"DISTINCT_SOURCE_ROWS={counts['DISTINCT_SOURCE_ROWS']}",
    "",
    "SOURCE PAIRS",
    "-" * 96,
]

for (left, right), count in source_pairs.most_common():
    lines.append(f"{count:>5} | {left} <> {right}")

lines.extend(
    [
        "",
        "AMBIGUOUS RUN DETAILS",
        "-" * 96,
    ]
)

for record in records[:200]:
    lines.append(
        f"{record['category']} | "
        f"{record['runner']} | "
        f"{record['form_date']} | "
        f"{record['form_track']} -> {record['canonical_track']} | "
        f"{record['form_distance']}m | "
        f"matches={record['match_count']} | "
        f"ratings={record['ratings']} | "
        f"sources={record['sources']}"
    )

lines.extend(
    [
        "",
        f"DETAIL_CSV={OUT_CSV}",
        "",
        "EDGEIQ_FORM_GUIDE_HISTORICAL_EPI_AMBIGUITY_FORENSIC_AUDIT_PASS",
    ]
)

OUT_TXT.write_text("\n".join(lines), encoding="utf-8")

print("\n".join(lines))
print()
print(f"WROTE_TXT={OUT_TXT}")
print(f"WROTE_CSV={OUT_CSV}")
