from __future__ import annotations

import csv
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "public" / "data"

HORSE_DNA_PATH = DATA_DIR / "edgeiq_horse_dna_v2.csv"
FEATURE_PATH = DATA_DIR / "edgeiq_sectional_feature_engine_v2.csv"
INTELLIGENCE_PATH = DATA_DIR / "edgeiq_sectional_intelligence_v2.csv"
MEMORY_PATH = DATA_DIR / "edgeiq_universal_sectional_memory_v1.csv"
PHYSICS_PATH = DATA_DIR / "edgeiq_real_sectional_physics_features_v1.csv"
LIVE_FEED_PATH = DATA_DIR / "edgeiq_vic_live_terminal_feed_v1.csv"

OUTPUT_PATH = DATA_DIR / "edgeiq_sectional_coverage_strategy_v1.csv"
SUMMARY_PATH = DATA_DIR / "edgeiq_sectional_coverage_strategy_v1_summary.csv"

COUNTRY_SUFFIXES = ("IRE", "USA", "JPN", "GER", "SAF", "NZ", "GB", "FR")

DETAIL_COLUMNS = [
    "row_type",
    "meeting",
    "source_file",
    "race_date",
    "track",
    "race_no",
    "horse",
    "horse_key",
    "canonical_horse_key",
    "runners",
    "dna_matches",
    "usable_dna_matches",
    "sectional_source_matches",
    "source_matches_not_in_dna",
    "true_missing_history",
    "unique_horses",
    "current_runner_matches",
    "historical_horses_only",
    "source_match_files",
    "coverage_issue",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def canonical_horse_key(value: str | None) -> str:
    raw = text(value).upper()
    pattern = "|".join(COUNTRY_SUFFIXES)
    raw = re.sub(rf"\s*\(({pattern})\)\s*$", "", raw, flags=re.IGNORECASE).strip()
    raw = re.sub(r"[^A-Z0-9]+", "", raw)
    for suffix in COUNTRY_SUFFIXES:
        if raw.endswith(suffix) and len(raw) > len(suffix) + 3:
            return raw[: -len(suffix)]
    return raw


def normalise_race_no(value: str | None) -> str:
    raw = text(value).upper()
    match = re.search(r"\d+", raw)
    return match.group(0) if match else raw


def meeting_name(row: dict[str, str]) -> str:
    track = text(row.get("track")).upper()
    if "SANDOWN" in track:
        return "Sandown"
    if "KILMORE" in track:
        return "Kilmore"
    if "ECHUCA" in track:
        return "Echuca"
    return track.title() if track else "Unknown"


def source_key(row: dict[str, str]) -> str:
    return canonical_horse_key(row.get("canonical_horse_key") or row.get("horse_key") or row.get("horse"))


def build_source_keyset(rows: list[dict[str, str]], source_name: str) -> dict[str, set[str]]:
    matches: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        key = source_key(row)
        if key:
            matches[key].add(source_name)
    return matches


def merge_source_keysets(sources: list[dict[str, set[str]]]) -> dict[str, set[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for source in sources:
        for key, source_names in source.items():
            merged[key].update(source_names)
    return merged


def is_usable_dna(row: dict[str, str] | None) -> bool:
    if not row:
        return False
    confidence = text(row.get("dna_confidence")).upper()
    archetype = text(row.get("sectional_archetype")).upper()
    return confidence in {"HIGH", "MEDIUM", "LOW"} and archetype != "UNKNOWN_INSUFFICIENT_DATA"


def classify_runner_issue(dna_match: bool, usable_dna: bool, source_match: bool) -> str:
    if usable_dna:
        return "USABLE_DNA_AVAILABLE"
    if dna_match and source_match:
        return "DNA_EXISTS_BUT_INSUFFICIENT_SAMPLE"
    if source_match and not dna_match:
        return "SOURCE_AVAILABLE_NOT_IN_DNA"
    return "NO_SECTIONAL_SOURCE_MATCH"


def pct(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0.00"
    return f"{(numerator / denominator) * 100.0:.2f}"


def build_sectional_coverage_strategy_audit() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    live_rows = read_csv(LIVE_FEED_PATH)
    dna_rows = read_csv(HORSE_DNA_PATH)
    feature_rows = read_csv(FEATURE_PATH)
    intelligence_rows = read_csv(INTELLIGENCE_PATH)
    memory_rows = read_csv(MEMORY_PATH)
    physics_rows = read_csv(PHYSICS_PATH)

    source_maps = {
        FEATURE_PATH.name: build_source_keyset(feature_rows, FEATURE_PATH.name),
        INTELLIGENCE_PATH.name: build_source_keyset(intelligence_rows, INTELLIGENCE_PATH.name),
        MEMORY_PATH.name: build_source_keyset(memory_rows, MEMORY_PATH.name),
        PHYSICS_PATH.name: build_source_keyset(physics_rows, PHYSICS_PATH.name),
    }
    all_source_keys = merge_source_keysets(list(source_maps.values()))

    dna_lookup = {
        source_key(row): row
        for row in dna_rows
        if source_key(row)
    }
    live_keys = {
        source_key(row)
        for row in live_rows
        if source_key(row)
    }

    runner_audits: list[dict[str, Any]] = []
    for row in live_rows:
        key = source_key(row)
        if not key:
            continue
        dna_row = dna_lookup.get(key)
        dna_match = bool(dna_row)
        usable_dna = is_usable_dna(dna_row)
        source_files = sorted(all_source_keys.get(key, set()))
        source_match = bool(source_files)
        runner_audits.append(
            {
                "race_date": text(row.get("race_date")),
                "track": text(row.get("track")),
                "race_no": normalise_race_no(row.get("race_no")),
                "meeting": meeting_name(row),
                "horse": text(row.get("horse")),
                "horse_key": text(row.get("horse_key")),
                "canonical_horse_key": key,
                "dna_match": dna_match,
                "usable_dna": usable_dna,
                "source_match": source_match,
                "source_files": source_files,
                "coverage_issue": classify_runner_issue(dna_match, usable_dna, source_match),
            }
        )

    detail_rows: list[dict[str, Any]] = []
    for meeting in ["Sandown", "Kilmore", "Echuca"]:
        meeting_rows = [row for row in runner_audits if row["meeting"] == meeting]
        runners = len(meeting_rows)
        dna_matches = sum(1 for row in meeting_rows if row["dna_match"])
        usable_dna_matches = sum(1 for row in meeting_rows if row["usable_dna"])
        source_matches = sum(1 for row in meeting_rows if row["source_match"])
        source_not_dna = sum(1 for row in meeting_rows if row["source_match"] and not row["dna_match"])
        true_missing = sum(1 for row in meeting_rows if not row["source_match"] and not row["dna_match"])
        detail_rows.append(
            {
                "row_type": "MEETING_SUMMARY",
                "meeting": meeting,
                "runners": runners,
                "dna_matches": dna_matches,
                "usable_dna_matches": usable_dna_matches,
                "sectional_source_matches": source_matches,
                "source_matches_not_in_dna": source_not_dna,
                "true_missing_history": true_missing,
            }
        )

    for source_name, key_map in source_maps.items():
        source_keys = set(key_map)
        current_matches = len(source_keys & live_keys)
        detail_rows.append(
            {
                "row_type": "SOURCE_SUMMARY",
                "source_file": source_name,
                "unique_horses": len(source_keys),
                "current_runner_matches": current_matches,
                "historical_horses_only": len(source_keys - live_keys),
            }
        )

    no_coverage_rows = [
        row
        for row in runner_audits
        if not row["source_match"] and not row["dna_match"]
    ]
    no_coverage_rows.sort(key=lambda row: (row["meeting"], int(row["race_no"] or 0), row["horse"]))
    for row in no_coverage_rows[:100]:
        detail_rows.append(
            {
                "row_type": "TOP_100_NO_SECTIONAL_COVERAGE",
                "meeting": row["meeting"],
                "race_date": row["race_date"],
                "track": row["track"],
                "race_no": row["race_no"],
                "horse": row["horse"],
                "horse_key": row["horse_key"],
                "canonical_horse_key": row["canonical_horse_key"],
                "source_match_files": "",
                "coverage_issue": row["coverage_issue"],
            }
        )

    current_runners = len(runner_audits)
    dna_matches = sum(1 for row in runner_audits if row["dna_match"])
    usable_dna_matches = sum(1 for row in runner_audits if row["usable_dna"])
    source_matches = sum(1 for row in runner_audits if row["source_match"])
    source_matches_not_in_dna = sum(1 for row in runner_audits if row["source_match"] and not row["dna_match"])
    true_missing = sum(1 for row in runner_audits if not row["source_match"] and not row["dna_match"])
    insufficient_dna = sum(1 for row in runner_audits if row["coverage_issue"] == "DNA_EXISTS_BUT_INSUFFICIENT_SAMPLE")

    if current_runners and source_matches_not_in_dna / current_runners >= 0.10:
        recommendation = "DNA_PIPELINE_MISSING_AVAILABLE_DATA"
    elif current_runners and source_matches / current_runners >= 0.70 and usable_dna_matches / current_runners >= 0.50:
        recommendation = "SUFFICIENT_COVERAGE_FOR_NEXT_PHASE"
    elif current_runners and source_matches / current_runners < 0.50:
        recommendation = "SECTIONAL_SOURCE_EXPANSION_REQUIRED"
    else:
        recommendation = "SECTIONAL_COVERAGE_LIMITED"

    summary_rows = [
        {
            "built_at": datetime.now(timezone.utc).isoformat(),
            "current_runners": current_runners,
            "dna_matches": dna_matches,
            "usable_dna_matches": usable_dna_matches,
            "sectional_source_matches": source_matches,
            "true_missing_history": true_missing,
            "source_matches_not_in_dna": source_matches_not_in_dna,
            "dna_exists_but_insufficient_sample": insufficient_dna,
            "dna_match_coverage_pct": pct(dna_matches, current_runners),
            "usable_dna_coverage_pct": pct(usable_dna_matches, current_runners),
            "sectional_source_coverage_pct": pct(source_matches, current_runners),
            "true_missing_history_pct": pct(true_missing, current_runners),
            "horse_dna_rows_loaded": len(dna_rows),
            "feature_rows_loaded": len(feature_rows),
            "intelligence_rows_loaded": len(intelligence_rows),
            "memory_rows_loaded": len(memory_rows),
            "physics_rows_loaded": len(physics_rows),
            "recommendation": recommendation,
            "status": "SECTIONAL_COVERAGE_STRATEGY_AUDITED",
        }
    ]

    return detail_rows, summary_rows


def main() -> None:
    detail_rows, summary_rows = build_sectional_coverage_strategy_audit()
    write_csv(OUTPUT_PATH, detail_rows, DETAIL_COLUMNS)
    write_csv(SUMMARY_PATH, summary_rows, list(summary_rows[0].keys()))

    summary = summary_rows[0]
    print(f"Sectional coverage strategy rows written: {len(detail_rows)}")
    print(f"Summary written: {SUMMARY_PATH}")
    print(f"Status: {summary['status']}")
    print(f"Recommendation: {summary['recommendation']}")
    print(f"Current runners: {summary['current_runners']}")
    print(f"DNA matches: {summary['dna_matches']}")
    print(f"Sectional source matches: {summary['sectional_source_matches']}")
    print(f"True missing history: {summary['true_missing_history']}")


if __name__ == "__main__":
    main()
