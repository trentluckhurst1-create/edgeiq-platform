from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
import csv
import json
import re

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs"

TARGET_DATE = "2026-07-21"
TARGET_MEETING = "MOE"
TARGET_RACE = 2
TARGET_HORSES = {
    "MIGHTY MYSTIC",
    "PROFFER",
    "ROCK ABOUT",
}

OUTPUT_TEXT = DOCS / "moe_r2_runner_source_trace_v1.txt"
OUTPUT_JSON = DATA / "edgeiq_moe_r2_runner_source_trace_v1.json"

DATE_KEYS = (
    "date",
    "raceDate",
    "race_date",
    "meetingDate",
    "meeting_date",
    "startDate",
    "start_date",
)

MEETING_KEYS = (
    "meeting",
    "meetingName",
    "meeting_name",
    "venue",
    "venueName",
    "venue_name",
    "track",
    "trackName",
    "track_name",
    "racecourse",
)

RACE_KEYS = (
    "raceNumber",
    "race_number",
    "raceNo",
    "race_no",
    "raceNum",
    "number",
)

HORSE_KEYS = (
    "horseName",
    "horse_name",
    "runnerName",
    "runner_name",
    "runner",
    "horse",
    "name",
)

OFFICIAL_KEYS = {
    "number": (
        "raceEntryNumber",
        "race_entry_number",
        "runnerNumber",
        "runner_number",
        "saddlecloth",
        "tabNumber",
        "number",
    ),
    "barrier": (
        "barrier",
        "barrierNumber",
        "barrier_number",
        "liveBarrierNumber",
        "draw",
    ),
    "jockey": (
        "jockey",
        "jockeyName",
        "jockey_name",
        "rider",
    ),
    "trainer": (
        "trainer",
        "trainerName",
        "trainer_name",
    ),
    "weight": (
        "weight",
        "allocatedWeight",
        "allocated_weight",
        "weightAllocated",
    ),
    "market": (
        "market",
        "price",
        "fixedWin",
        "fixed_win",
        "oddsWin",
        "winOdds",
    ),
    "silk": (
        "silkUrl",
        "silk_url",
        "silk",
        "silks",
    ),
}

def clean(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, (dict, list)):
        return ""

    text = re.sub(r"\s+", " ", str(value)).strip()

    if text.upper() in {"", "NONE", "NULL", "N/A", "NA", "-"}:
        return ""

    return text

def normalise(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", clean(value).upper()).strip()

def first(mapping: dict[str, Any], keys: tuple[str, ...]) -> Any:
    lowered = {
        str(key).lower(): key
        for key in mapping
    }

    for key in keys:
        actual = key if key in mapping else lowered.get(key.lower())

        if actual is None:
            continue

        value = mapping.get(actual)

        if clean(value):
            return value

    return None

def parse_date(value: Any) -> str:
    text = clean(value)

    match = re.search(
        r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b",
        text,
    )

    if match:
        return (
            f"{int(match.group(1)):04d}-"
            f"{int(match.group(2)):02d}-"
            f"{int(match.group(3)):02d}"
        )

    for pattern in (
        "%d/%m/%Y",
        "%d/%m/%y",
        "%d-%m-%Y",
    ):
        try:
            return datetime.strptime(text[:10], pattern).date().isoformat()
        except ValueError:
            pass

    return ""

def integer(value: Any) -> int | None:
    try:
        return int(float(clean(value)))
    except (TypeError, ValueError):
        return None

def horse_from(mapping: dict[str, Any]) -> str:
    value = first(mapping, HORSE_KEYS)

    if isinstance(value, dict):
        return clean(first(value, HORSE_KEYS))

    return clean(value)

def relevant_row(row: dict[str, Any]) -> bool:
    horse = normalise(horse_from(row))

    if horse in TARGET_HORSES:
        return True

    date_value = parse_date(first(row, DATE_KEYS))
    meeting_value = normalise(first(row, MEETING_KEYS))
    race_value = integer(first(row, RACE_KEYS))

    return (
        date_value == TARGET_DATE
        and meeting_value == TARGET_MEETING
        and race_value == TARGET_RACE
    )

def non_empty_values(row: dict[str, Any]) -> dict[str, Any]:
    return {
        str(key): value
        for key, value in row.items()
        if clean(value)
    }

def official_values(row: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}

    for field, keys in OFFICIAL_KEYS.items():
        value = first(row, keys)
        result[field] = clean(value)

    return result

def completeness(values: dict[str, str]) -> int:
    return sum(
        1
        for value in values.values()
        if clean(value)
    )

def inspect_csv(path: Path) -> dict[str, Any] | None:
    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
            errors="replace",
        ) as handle:
            reader = csv.DictReader(handle)
            headers = reader.fieldnames or []
            matches = []

            for row_number, row in enumerate(reader, start=2):
                if not relevant_row(row):
                    continue

                official = official_values(row)

                matches.append({
                    "rowNumber": row_number,
                    "horse": horse_from(row),
                    "date": parse_date(first(row, DATE_KEYS)),
                    "meeting": clean(first(row, MEETING_KEYS)),
                    "raceNumber": integer(first(row, RACE_KEYS)),
                    "official": official,
                    "officialCompleteness": completeness(official),
                    "nonEmpty": non_empty_values(row),
                })

    except Exception as exc:
        return {
            "path": str(path.relative_to(ROOT)),
            "type": "csv",
            "error": repr(exc),
            "matches": [],
        }

    if not matches:
        return None

    return {
        "path": str(path.relative_to(ROOT)),
        "type": "csv",
        "headers": headers,
        "headerCount": len(headers),
        "matches": matches,
        "bestCompleteness": max(
            match["officialCompleteness"]
            for match in matches
        ),
    }

def walk_json(value: Any, path: str = "$"):
    if isinstance(value, dict):
        yield path, value

        for key, child in value.items():
            yield from walk_json(child, f"{path}.{key}")

    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_json(child, f"{path}[{index}]")

def inspect_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8-sig",
                errors="replace",
            )
        )
    except Exception as exc:
        return {
            "path": str(path.relative_to(ROOT)),
            "type": "json",
            "error": repr(exc),
            "matches": [],
        }

    matches = []

    for json_path, node in walk_json(payload):
        if not isinstance(node, dict):
            continue

        if not relevant_row(node):
            continue

        official = official_values(node)

        matches.append({
            "jsonPath": json_path,
            "horse": horse_from(node),
            "date": parse_date(first(node, DATE_KEYS)),
            "meeting": clean(first(node, MEETING_KEYS)),
            "raceNumber": integer(first(node, RACE_KEYS)),
            "official": official,
            "officialCompleteness": completeness(official),
            "nonEmpty": non_empty_values(node),
        })

    if not matches:
        return None

    return {
        "path": str(path.relative_to(ROOT)),
        "type": "json",
        "matches": matches,
        "bestCompleteness": max(
            match["officialCompleteness"]
            for match in matches
        ),
    }

priority_names = {
    "edgeiq_racingcom_three_day_raw_meetings_v1.json",
    "edgeiq_vic_three_day_race_list_v1.csv",
    "race_fields.csv",
    "edgeiq_vic_three_day_race_fields.csv",
    "edgeiq_vic_three_day_meeting_universe.csv",
    "edgeiq_tab_calendar_racecards_vic_v1.csv",
}

candidate_tokens = (
    "field",
    "accept",
    "racecard",
    "runner",
    "three_day",
    "racingcom",
    "meeting",
    "declaration",
    "nomination",
    "entry",
)

candidates: list[Path] = []

for path in DATA.iterdir():
    if not path.is_file():
        continue

    lower_name = path.name.lower()

    if path.name in priority_names:
        candidates.append(path)
        continue

    if path.suffix.lower() not in {".csv", ".json"}:
        continue

    if any(token in lower_name for token in candidate_tokens):
        candidates.append(path)

candidates = sorted(
    set(candidates),
    key=lambda path: (
        0 if path.name in priority_names else 1,
        path.name.lower(),
    ),
)

results = []

for path in candidates:
    if path.suffix.lower() == ".csv":
        result = inspect_csv(path)
    else:
        result = inspect_json(path)

    if result:
        results.append(result)

results.sort(
    key=lambda result: (
        -result.get("bestCompleteness", -1),
        result["path"],
    )
)

report = {
    "audit": "EDGEIQ_MOE_R2_RUNNER_SOURCE_TRACE_V1",
    "target": {
        "date": TARGET_DATE,
        "meeting": TARGET_MEETING,
        "raceNumber": TARGET_RACE,
        "horses": sorted(TARGET_HORSES),
    },
    "candidateFilesScanned": len(candidates),
    "filesWithMatches": len(results),
    "results": results,
}

OUTPUT_JSON.write_text(
    json.dumps(report, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

lines = [
    "EDGEIQ MOE R2 RUNNER SOURCE TRACE V1",
    "=" * 120,
    f"TARGET={TARGET_DATE}|{TARGET_MEETING}|R{TARGET_RACE}",
    f"CANDIDATE_FILES_SCANNED={len(candidates)}",
    f"FILES_WITH_MATCHES={len(results)}",
    "",
]

for result in results:
    lines.extend([
        "=" * 120,
        f"FILE={result['path']}",
        f"TYPE={result['type']}",
        f"BEST_OFFICIAL_COMPLETENESS={result.get('bestCompleteness', 0)}/7",
    ])

    if result.get("error"):
        lines.append(f"ERROR={result['error']}")
        continue

    if result["type"] == "csv":
        lines.append(f"HEADER_COUNT={result.get('headerCount', 0)}")
        lines.append(
            "HEADERS="
            + " | ".join(result.get("headers", []))
        )

    for match in result.get("matches", []):
        lines.append("")
        lines.append("-" * 120)

        if "rowNumber" in match:
            lines.append(f"ROW={match['rowNumber']}")

        if "jsonPath" in match:
            lines.append(f"JSON_PATH={match['jsonPath']}")

        lines.append(f"HORSE={match['horse']}")
        lines.append(
            f"IDENTITY={match['date']}|"
            f"{match['meeting']}|"
            f"R{match['raceNumber']}"
        )
        lines.append(
            "OFFICIAL="
            + " | ".join(
                f"{key}={value or '<EMPTY>'}"
                for key, value in match["official"].items()
            )
        )
        lines.append(
            f"OFFICIAL_COMPLETENESS="
            f"{match['officialCompleteness']}/7"
        )
        lines.append("NON_EMPTY_VALUES:")

        for key, value in match["nonEmpty"].items():
            display = str(value)

            if len(display) > 500:
                display = display[:497] + "..."

            lines.append(f"  {key}={display}")

    lines.append("")

lines.extend([
    "=" * 120,
    "RANKED SOURCE SUMMARY",
    "=" * 120,
])

for result in results:
    lines.append(
        f"{result.get('bestCompleteness', 0)}/7 | "
        f"{result['path']} | "
        f"matches={len(result.get('matches', []))}"
    )

lines.extend([
    "",
    f"OUTPUT_JSON={OUTPUT_JSON}",
    f"OUTPUT_TEXT={OUTPUT_TEXT}",
    "EDGEIQ_MOE_R2_RUNNER_SOURCE_TRACE_V1_COMPLETE",
])

OUTPUT_TEXT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_TEXT.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8",
)

print("\n".join(lines))
