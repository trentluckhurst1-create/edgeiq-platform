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

OUT_TXT = DOCS / "FORM_GUIDE_HISTORICAL_EPI_CANONICAL_TRACK_PREFLIGHT.txt"
OUT_CSV = DOCS / "FORM_GUIDE_HISTORICAL_EPI_CANONICAL_TRACK_PREFLIGHT.csv"


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

    "SPORTSBETBALLARATSYNTHETIC": "BRTS",

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


def date_key(value: Any) -> str:
    return text(value)


def distance_key(value: Any) -> str:
    raw = text(value)
    if not raw:
        return ""

    match = re.search(r"\d+(?:\.\d+)?", raw.replace(",", ""))
    if not match:
        return ""

    number = float(match.group(0))
    return str(int(number)) if number.is_integer() else str(number)


with FORM.open(encoding="utf-8") as handle:
    form_payload = json.load(handle)

with HIST.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
    research_rows = list(csv.DictReader(handle))


research_index = defaultdict(list)

for row_number, row in enumerate(research_rows, start=2):
    key = (
        horse_key(row.get("horse")),
        date_key(row.get("race_date")),
        canonical_track(row.get("track")),
        distance_key(row.get("distance")),
    )

    if all(key):
        research_index[key].append(
            {
                "row_number": row_number,
                "horse": text(row.get("horse")),
                "date": text(row.get("race_date")),
                "track": text(row.get("track")),
                "distance": text(row.get("distance")),
                "rating": text(row.get("performance_rating_v6_1_research")),
                "source_file": text(row.get("source_file")),
            }
        )


counts = Counter()
details = []

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
                date_key(run.get("date") or run.get("raceDate")),
                canonical_track(run.get("track")),
                distance_key(run.get("distance")),
            )

            matches = research_index.get(key, [])

            if len(matches) == 1 and matches[0]["rating"]:
                status = "SAFE_UNIQUE_RATED_MATCH"
            elif len(matches) == 1:
                status = "UNIQUE_MATCH_WITHOUT_RATING"
            elif len(matches) > 1:
                status = "AMBIGUOUS_MATCH"
            else:
                status = "UNMATCHED"

            counts[status] += 1

            if status != "UNMATCHED":
                details.append(
                    {
                        "status": status,
                        "runner": runner_name,
                        "run_index": run_index,
                        "form_date": text(run.get("date") or run.get("raceDate")),
                        "form_track": text(run.get("track")),
                        "canonical_track": canonical_track(run.get("track")),
                        "form_distance": distance_key(run.get("distance")),
                        "match_count": len(matches),
                        "matches": json.dumps(matches, ensure_ascii=False),
                    }
                )


fieldnames = [
    "status",
    "runner",
    "run_index",
    "form_date",
    "form_track",
    "canonical_track",
    "form_distance",
    "match_count",
    "matches",
]

OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(details)


lines = [
    "EDGEIQ FORM GUIDE HISTORICAL EPI CANONICAL TRACK PREFLIGHT",
    "=" * 92,
    "",
    f"FORM_HISTORICAL_RUNS={sum(counts.values())}",
    f"SAFE_UNIQUE_RATED_MATCH={counts['SAFE_UNIQUE_RATED_MATCH']}",
    f"UNIQUE_MATCH_WITHOUT_RATING={counts['UNIQUE_MATCH_WITHOUT_RATING']}",
    f"AMBIGUOUS_MATCH={counts['AMBIGUOUS_MATCH']}",
    f"UNMATCHED={counts['UNMATCHED']}",
    "",
]

if counts["AMBIGUOUS_MATCH"] == 0:
    lines.append("DECISION=SAFE_TO_IMPLEMENT_CANONICAL_TRACK_MATCHING")
    marker = "EDGEIQ_FORM_GUIDE_HISTORICAL_EPI_CANONICAL_TRACK_PREFLIGHT_PASS"
else:
    lines.append("DECISION=BLOCKED_AMBIGUOUS_CANONICAL_MATCHES")
    marker = "EDGEIQ_FORM_GUIDE_HISTORICAL_EPI_CANONICAL_TRACK_PREFLIGHT_BLOCKED"

lines.extend(
    [
        f"DETAIL_CSV={OUT_CSV}",
        "",
        marker,
    ]
)

OUT_TXT.write_text("\n".join(lines), encoding="utf-8")

print("\n".join(lines))
