from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
import json
import re
import unicodedata

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
PUBLIC_DATA = ROOT / "public" / "data"
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"

TARGET_RACE_KEY = "2026-07-21|MOE|2"
TARGET_HORSES = {
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

OUTPUT_TEXT = ROOT / "docs" / "builder_integrity_audit_v1.txt"
OUTPUT_JSON = PUBLIC_DATA / "edgeiq_builder_integrity_audit_v1.json"

FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "runner_number": (
        "runnerNumber",
        "runner_number",
        "saddlecloth",
        "saddleclothNumber",
        "number",
        "no",
    ),
    "trainer": (
        "trainer",
        "trainerName",
        "trainer_name",
    ),
    "jockey": (
        "jockey",
        "jockeyName",
        "jockey_name",
        "rider",
        "riderName",
    ),
    "barrier": (
        "barrier",
        "barrierNumber",
        "barrier_number",
        "draw",
    ),
    "weight": (
        "weight",
        "weightAllocated",
        "weight_allocated",
        "allocatedWeight",
    ),
    "silk": (
        "silkUrl",
        "silk_url",
        "silks",
        "silk",
    ),
    "market": (
        "market",
        "marketPrice",
        "market_price",
        "fixedPrice",
        "price",
    ),
    "epi": (
        "epi",
        "historicalEpi",
        "performanceRating",
    ),
    "eri": (
        "eri",
        "rating",
        "raceRating",
    ),
    "suitability": (
        "suitability",
        "suitabilityScore",
        "suitability_score",
    ),
    "edgeiq_price": (
        "edgeiqPrice",
        "edgeiq_price",
        "fairPrice",
        "fair_price",
    ),
    "recent_runs": (
        "recentRuns",
        "recent_runs",
        "form",
        "runs",
    ),
}

HORSE_ALIASES = (
    "horseName",
    "horse_name",
    "runnerName",
    "runner_name",
    "runner",
    "name",
    "horse",
)

RACE_KEY_ALIASES = (
    "raceKey",
    "race_key",
    "canonicalRaceKey",
    "canonical_race_key",
)

DATE_ALIASES = (
    "raceDate",
    "race_date",
    "date",
    "meetingDate",
    "meeting_date",
)

MEETING_ALIASES = (
    "meeting",
    "meetingName",
    "meeting_name",
    "track",
    "venue",
)

RACE_NUMBER_ALIASES = (
    "raceNumber",
    "race_number",
    "raceNo",
    "race_no",
)

def canonical_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^A-Z0-9]+", "", text.upper())

def safe_value(value: Any) -> bool:
    if value is None:
        return False

    if isinstance(value, str):
        return value.strip() not in {"", "-", "—", "N/A", "NA", "NULL", "NONE"}

    if isinstance(value, dict):
        if "value" in value:
            return safe_value(value.get("value"))

        if "display" in value:
            return safe_value(value.get("display"))

        return any(safe_value(child) for child in value.values())

    if isinstance(value, list):
        return len(value) > 0

    return True

def first_value(mapping: Any, keys: Iterable[str]) -> Any:
    if not isinstance(mapping, dict):
        return None

    for key in keys:
        if key in mapping and safe_value(mapping.get(key)):
            return mapping.get(key)

    return None

def walk(value: Any, path: str = "$"):
    if isinstance(value, dict):
        yield path, value

        for key, child in value.items():
            yield from walk(child, f"{path}.{key}")

    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, f"{path}[{index}]")

def text_from_nested(value: Any, keys: Iterable[str]) -> Any:
    if isinstance(value, str):
        return value

    if isinstance(value, dict):
        return first_value(value, keys)

    return None

def horse_name(node: dict[str, Any]) -> str:
    direct = first_value(node, HORSE_ALIASES)

    if isinstance(direct, str):
        return direct

    if isinstance(direct, dict):
        nested = first_value(direct, HORSE_ALIASES)
        return str(nested or "")

    official = node.get("official")
    source = node.get("source")

    for candidate in (official, source):
        if isinstance(candidate, dict):
            value = first_value(candidate, HORSE_ALIASES)

            if isinstance(value, str):
                return value

            if isinstance(value, dict):
                nested = first_value(value, HORSE_ALIASES)
                if nested:
                    return str(nested)

    return ""

def race_key(node: dict[str, Any]) -> str:
    direct = first_value(node, RACE_KEY_ALIASES)

    if direct:
        return str(direct)

    official = node.get("official")
    source = node.get("source")

    for candidate in (official, source):
        if isinstance(candidate, dict):
            direct = first_value(candidate, RACE_KEY_ALIASES)
            if direct:
                return str(direct)

    date = first_value(node, DATE_ALIASES)
    meeting = first_value(node, MEETING_ALIASES)
    number = first_value(node, RACE_NUMBER_ALIASES)

    for candidate in (official, source):
        if not isinstance(candidate, dict):
            continue

        date = date or first_value(candidate, DATE_ALIASES)
        meeting = meeting or first_value(candidate, MEETING_ALIASES)
        number = number or first_value(candidate, RACE_NUMBER_ALIASES)

    if date and meeting and number:
        return f"{str(date).strip()}|{canonical_text(meeting)}|{str(number).strip()}"

    return ""

def field_value(node: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    direct = first_value(node, aliases)

    if safe_value(direct):
        return direct

    for container_key in (
        "official",
        "source",
        "runner",
        "horse",
        "metrics",
        "market",
        "intelligence",
        "profile",
        "history",
    ):
        nested = node.get(container_key)

        if isinstance(nested, dict):
            value = first_value(nested, aliases)

            if safe_value(value):
                return value

            horse = nested.get("horse")
            if isinstance(horse, dict):
                value = first_value(horse, aliases)
                if safe_value(value):
                    return value

    return None

def looks_like_runner(node: dict[str, Any]) -> bool:
    name = horse_name(node)

    if not name:
        return False

    field_hits = sum(
        1
        for aliases in FIELD_ALIASES.values()
        if field_value(node, aliases) is not None
    )

    return field_hits > 0 or canonical_text(name) in TARGET_HORSES

def extract_target_runners(payload: Any) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    for path, node in walk(payload):
        if not isinstance(node, dict) or not looks_like_runner(node):
            continue

        name = horse_name(node)
        horse_key = canonical_text(name)
        node_race_key = race_key(node)

        target_by_name = horse_key in TARGET_HORSES
        target_by_race = canonical_text(node_race_key) == canonical_text(TARGET_RACE_KEY)

        if not target_by_name and not target_by_race:
            continue

        record = {
            "path": path,
            "horse": name,
            "horse_key": horse_key,
            "race_key": node_race_key,
        }

        for field, aliases in FIELD_ALIASES.items():
            value = field_value(node, aliases)
            record[field] = value
            record[f"{field}_present"] = safe_value(value)

        candidates.append(record)

    best_by_horse: dict[str, dict[str, Any]] = {}

    for candidate in candidates:
        key = candidate["horse_key"]

        score = sum(
            1
            for field in FIELD_ALIASES
            if candidate.get(f"{field}_present")
        )

        existing = best_by_horse.get(key)

        if existing is None:
            best_by_horse[key] = candidate
            continue

        existing_score = sum(
            1
            for field in FIELD_ALIASES
            if existing.get(f"{field}_present")
        )

        exact_target_race = canonical_text(candidate["race_key"]) == canonical_text(TARGET_RACE_KEY)
        existing_exact_target_race = canonical_text(existing["race_key"]) == canonical_text(TARGET_RACE_KEY)

        if exact_target_race and not existing_exact_target_race:
            best_by_horse[key] = candidate
        elif exact_target_race == existing_exact_target_race and score > existing_score:
            best_by_horse[key] = candidate

    return sorted(
        best_by_horse.values(),
        key=lambda row: (
            int(row["runner_number"])
            if str(row.get("runner_number") or "").isdigit()
            else 999,
            row["horse"],
        ),
    )

def inspect_json_file(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None

    runners = extract_target_runners(payload)

    if not runners:
        return None

    coverage: dict[str, dict[str, int]] = {}

    for field in FIELD_ALIASES:
        present = sum(1 for runner in runners if runner.get(f"{field}_present"))
        coverage[field] = {
            "present": present,
            "total": len(runners),
        }

    return {
        "path": str(path.relative_to(ROOT)),
        "modified_utc": datetime.fromtimestamp(
            path.stat().st_mtime,
            timezone.utc,
        ).isoformat(),
        "runner_count": len(runners),
        "coverage": coverage,
        "runners": runners,
    }

def candidate_json_files() -> list[Path]:
    preferred_tokens = (
        "three_day",
        "product_catalog",
        "race",
        "runner",
        "form_guide",
        "graphql",
        "racingcom",
        "tab_",
        "field",
        "market",
        "epi",
        "suitability",
    )

    files = []

    for path in PUBLIC_DATA.rglob("*.json"):
        relative = str(path.relative_to(PUBLIC_DATA)).lower()

        if any(token in relative for token in preferred_tokens):
            files.append(path)

    return sorted(
        files,
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

def find_builder_references() -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    patterns = (
        "edgeiq_three_day_product_catalog_v1.json",
        "three_day_product_catalog",
        "official",
        "silkUrl",
        "trainer",
        "jockey",
        "barrier",
        "weight",
    )

    source_files = list(SCRIPTS.rglob("*.py"))

    for path in source_files:
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except Exception:
            continue

        matched_lines = []

        for line_number, line in enumerate(lines, start=1):
            if any(pattern.lower() in line.lower() for pattern in patterns):
                matched_lines.append(
                    {
                        "line": line_number,
                        "text": line.rstrip(),
                    }
                )

        if matched_lines:
            findings.append(
                {
                    "path": str(path.relative_to(ROOT)),
                    "matches": matched_lines[:120],
                }
            )

    return findings

def stage_rank(path_text: str) -> int:
    name = path_text.lower()

    if "raw" in name or "graphql" in name or "racingcom" in name or "tab_" in name:
        return 10

    if "three_day_window" in name:
        return 20

    if "product_catalog" in name:
        return 30

    if "form_guide_enriched" in name:
        return 40

    return 25

results: list[dict[str, Any]] = []

for index, path in enumerate(candidate_json_files(), start=1):
    result = inspect_json_file(path)

    if result:
        result["stage_rank"] = stage_rank(result["path"])
        results.append(result)

results.sort(
    key=lambda result: (
        result["stage_rank"],
        result["path"],
    )
)

builder_references = find_builder_references()

field_first_failure: dict[str, dict[str, Any] | None] = {}

for field in FIELD_ALIASES:
    first_failure = None
    previously_present = False

    for result in results:
        coverage = result["coverage"][field]
        complete = coverage["present"] == coverage["total"] and coverage["total"] > 0

        if complete:
            previously_present = True
            continue

        if previously_present:
            first_failure = {
                "path": result["path"],
                "present": coverage["present"],
                "total": coverage["total"],
            }
            break

    field_first_failure[field] = first_failure

report = {
    "audit": "EDGEIQ_BUILDER_INTEGRITY_AUDIT_V1",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "target_race_key": TARGET_RACE_KEY,
    "target_horses": sorted(TARGET_HORSES),
    "files_with_target_runners": results,
    "field_first_failure": field_first_failure,
    "builder_references": builder_references,
}

OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_TEXT.parent.mkdir(parents=True, exist_ok=True)

OUTPUT_JSON.write_text(
    json.dumps(report, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

lines: list[str] = []

lines.append("EDGEIQ BUILDER INTEGRITY AUDIT V1")
lines.append("=" * 120)
lines.append(f"TARGET_RACE_KEY={TARGET_RACE_KEY}")
lines.append(f"FILES_WITH_TARGET_RUNNERS={len(results)}")
lines.append("")

if not results:
    lines.append("NO_TARGET_RUNNER_DATA_FOUND")
else:
    for result in results:
        lines.append("-" * 120)
        lines.append(f"FILE={result['path']}")
        lines.append(f"MODIFIED_UTC={result['modified_utc']}")
        lines.append(f"RUNNERS={result['runner_count']}")

        summary = []

        for field in FIELD_ALIASES:
            coverage = result["coverage"][field]
            summary.append(
                f"{field}={coverage['present']}/{coverage['total']}"
            )

        lines.append("COVERAGE " + " | ".join(summary))
        lines.append("")

        for runner in result["runners"]:
            field_summary = []

            for field in FIELD_ALIASES:
                value = runner.get(field)
                marker = "Y" if runner.get(f"{field}_present") else "N"

                if field in {"recent_runs"}:
                    if isinstance(value, list):
                        display = f"{len(value)} rows"
                    else:
                        display = str(value or "")
                else:
                    display = str(value or "")

                if len(display) > 80:
                    display = display[:77] + "..."

                field_summary.append(f"{field}:{marker}({display})")

            lines.append(
                f"RUNNER={runner['horse']} | PATH={runner['path']} | "
                + " | ".join(field_summary)
            )

        lines.append("")

lines.append("=" * 120)
lines.append("FIRST STAGE FAILURE")
lines.append("=" * 120)

for field, failure in field_first_failure.items():
    if failure:
        lines.append(
            f"{field}: FIRST_FAILURE={failure['path']} "
            f"COVERAGE={failure['present']}/{failure['total']}"
        )
    else:
        lines.append(
            f"{field}: NO_CONFIRMED_DROP_BETWEEN_DISCOVERED_STAGES"
        )

lines.append("")
lines.append("=" * 120)
lines.append("BUILDER CODE REFERENCES")
lines.append("=" * 120)

for builder in builder_references:
    lines.append("")
    lines.append(f"FILE={builder['path']}")

    for match in builder["matches"]:
        lines.append(
            f"{match['line']}: {match['text']}"
        )

lines.append("")
lines.append("OUTPUT_JSON=" + str(OUTPUT_JSON))
lines.append("OUTPUT_TEXT=" + str(OUTPUT_TEXT))
lines.append("EDGEIQ_BUILDER_INTEGRITY_AUDIT_V1_COMPLETE")

OUTPUT_TEXT.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8",
)

print("\n".join(lines))
