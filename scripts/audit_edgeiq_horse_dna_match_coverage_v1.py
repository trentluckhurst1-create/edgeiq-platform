from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "public" / "data"

LIVE_FEED_PATH = DATA_DIR / "edgeiq_vic_live_terminal_feed_v1.csv"
HORSE_DNA_PATH = DATA_DIR / "edgeiq_horse_dna_v1.csv"
SECTIONAL_FEATURE_PATH = DATA_DIR / "edgeiq_sectional_feature_engine_v2.csv"
SECTIONAL_INTELLIGENCE_PATH = DATA_DIR / "edgeiq_sectional_intelligence_v2.csv"
UNIVERSAL_MEMORY_PATH = DATA_DIR / "edgeiq_universal_sectional_memory_v1.csv"
REAL_PHYSICS_PATH = DATA_DIR / "edgeiq_real_sectional_physics_features_v1.csv"

OUTPUT_PATH = DATA_DIR / "edgeiq_horse_dna_match_coverage_v1.csv"
SUMMARY_PATH = DATA_DIR / "edgeiq_horse_dna_match_coverage_v1_summary.csv"

FUZZY_THRESHOLD = 0.88

OUTPUT_COLUMNS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "horse_key",
    "normalised_horse_name",
    "dna_direct_key_match",
    "dna_normalised_name_match",
    "sectional_source_match",
    "best_match_type",
    "best_match_horse",
    "best_match_horse_key",
    "match_confidence",
    "match_issue",
    "recommendation",
    "horse_dna_output_match",
    "sectional_feature_match",
    "sectional_intelligence_match",
    "universal_sectional_memory_match",
    "real_sectional_physics_match",
    "fuzzy_match_score",
    "fuzzy_match_horse",
    "fuzzy_match_horse_key",
]

SUMMARY_COLUMNS = [
    "audit_section",
    "built_at",
    "status",
    "recommendation",
    "current_runners",
    "direct_dna_key_matches",
    "normalised_dna_name_matches",
    "source_sectional_matches_not_in_dna",
    "true_missing_sectional_history",
    "likely_key_mismatch_count",
    "likely_suffix_name_mismatch_count",
    "fuzzy_only_possible_matches",
    "no_match_count",
    "live_terminal_rows_loaded",
    "horse_dna_rows_loaded",
    "sectional_feature_rows_loaded",
    "sectional_intelligence_rows_loaded",
    "universal_sectional_memory_rows_loaded",
    "real_sectional_physics_rows_loaded",
    "race_date",
    "track",
    "race_no",
    "runners",
    "dna_matches",
    "possible_recoverable_matches",
    "true_missing",
    "match_coverage_pct",
    "notes",
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


def strip_country_suffix(value: str) -> str:
    return re.sub(r"\s*\(([A-Z]{2,4})\)\s*$", "", value, flags=re.IGNORECASE).strip()


def ascii_fold(value: str) -> str:
    normalised = unicodedata.normalize("NFKD", value)
    return normalised.encode("ascii", "ignore").decode("ascii")


def canonical_name(value: str | None) -> str:
    raw = text(value).upper()
    raw = strip_country_suffix(raw)
    raw = ascii_fold(raw)
    return re.sub(r"[^A-Z0-9]+", "", raw)


def direct_key(value: str | None) -> str:
    return text(value).upper()


def canonical_key(value: str | None) -> str:
    return canonical_name(value)


def normalise_track(value: str | None) -> str:
    raw = text(value).upper()
    raw = re.sub(r"^(SPORTSBET|SPORTS BET|BET365|LADBROKES|TABTOUCH|TAB)\s+", "", raw).strip()
    raw = re.sub(r"[^A-Z0-9]+", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()


def race_key(row: dict[str, str]) -> tuple[str, str, str]:
    race_no = text(row.get("race_no"))
    match = re.search(r"\d+", race_no)
    return (
        text(row.get("race_date")),
        normalise_track(row.get("track")),
        match.group(0) if match else race_no,
    )


def yes_no(value: bool) -> str:
    return "YES" if value else "NO"


def build_source_lookup(rows: list[dict[str, str]]) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    by_key: dict[str, dict[str, str]] = {}
    by_name: dict[str, dict[str, str]] = {}
    for row in rows:
        key = canonical_key(row.get("horse_key"))
        name = canonical_name(row.get("horse"))
        if key:
            by_key[key] = row
        if name:
            by_name[name] = row
    return by_key, by_name


def build_dna_indexes(rows: list[dict[str, str]]) -> dict[str, Any]:
    exact_key: dict[str, dict[str, str]] = {}
    canonical_key_index: dict[str, dict[str, str]] = {}
    canonical_name_index: dict[str, dict[str, str]] = {}
    fuzzy_candidates: list[tuple[str, dict[str, str]]] = []

    for row in rows:
        raw_key = direct_key(row.get("horse_key"))
        key = canonical_key(row.get("horse_key"))
        name = canonical_name(row.get("horse"))
        if raw_key:
            exact_key[raw_key] = row
        if key:
            canonical_key_index[key] = row
            fuzzy_candidates.append((key, row))
        if name:
            canonical_name_index[name] = row
            fuzzy_candidates.append((name, row))

    return {
        "exact_key": exact_key,
        "canonical_key": canonical_key_index,
        "canonical_name": canonical_name_index,
        "fuzzy_candidates": fuzzy_candidates,
    }


def find_source_match(
    live_key: str,
    live_name: str,
    source_key_lookup: dict[str, dict[str, str]],
    source_name_lookup: dict[str, dict[str, str]],
) -> dict[str, str] | None:
    return source_key_lookup.get(live_key) or source_name_lookup.get(live_name)


def fuzzy_match(
    live_key: str,
    live_name: str,
    candidates: list[tuple[str, dict[str, str]]],
) -> tuple[float, dict[str, str] | None]:
    best_score = 0.0
    best_row: dict[str, str] | None = None
    probes = [probe for probe in {live_key, live_name} if probe]
    if not probes:
        return best_score, best_row

    for candidate_key, row in candidates:
        for probe in probes:
            score = SequenceMatcher(None, probe, candidate_key).ratio()
            if score > best_score:
                best_score = score
                best_row = row
    if best_score < FUZZY_THRESHOLD:
        return best_score, None
    return best_score, best_row


def classify_runner(
    live_row: dict[str, str],
    dna_indexes: dict[str, Any],
    feature_indexes: tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]],
    intelligence_indexes: tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]],
    memory_indexes: tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]],
    physics_indexes: tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]],
) -> dict[str, Any]:
    horse = text(live_row.get("horse"))
    raw_key = direct_key(live_row.get("horse_key"))
    live_key = canonical_key(live_row.get("horse_key"))
    live_name = canonical_name(horse)

    direct_dna = dna_indexes["exact_key"].get(raw_key)
    canonical_key_dna = dna_indexes["canonical_key"].get(live_key)
    canonical_name_dna = dna_indexes["canonical_name"].get(live_name)
    normalised_dna = canonical_name_dna or (canonical_key_dna if not direct_dna else None)

    feature_match = find_source_match(live_key, live_name, *feature_indexes)
    intelligence_match = find_source_match(live_key, live_name, *intelligence_indexes)
    memory_match = find_source_match(live_key, live_name, *memory_indexes)
    physics_match = find_source_match(live_key, live_name, *physics_indexes)

    source_matches = []
    if feature_match:
        source_matches.append("sectional_feature_engine_v2")
    if intelligence_match:
        source_matches.append("sectional_intelligence_v2")
    if memory_match:
        source_matches.append("universal_sectional_memory_v1")
    if physics_match:
        source_matches.append("real_sectional_physics_features_v1")

    fuzzy_score, fuzzy_row = (0.0, None)
    if not direct_dna and not normalised_dna:
        fuzzy_score, fuzzy_row = fuzzy_match(live_key, live_name, dna_indexes["fuzzy_candidates"])

    best_match = direct_dna or normalised_dna or feature_match or intelligence_match or memory_match or physics_match or fuzzy_row
    best_match_horse = text(best_match.get("horse")) if best_match else ""
    best_match_horse_key = text(best_match.get("horse_key")) if best_match else ""

    if direct_dna:
        best_match_type = "DIRECT_DNA_KEY"
        match_confidence = "HIGH"
        match_issue = "MATCHED_DNA_DIRECT"
        recommendation = "NO_ACTION"
    elif normalised_dna:
        best_match_type = "DNA_NORMALISED_NAME"
        match_confidence = "HIGH"
        if live_name == canonical_name(best_match_horse) and live_name != live_key:
            match_issue = "LIKELY_SUFFIX_OR_PUNCTUATION_MATCH"
            recommendation = "ADD_NAME_NORMALISATION_LAYER"
        else:
            match_issue = "LIKELY_KEY_NORMALISATION_MATCH"
            recommendation = "ADD_NAME_NORMALISATION_LAYER"
    elif source_matches:
        best_match_type = "SECTIONAL_SOURCE_ONLY"
        match_confidence = "MEDIUM"
        match_issue = "SOURCE_HAS_SECTIONAL_DATA_BUT_DNA_OUTPUT_MISSING"
        recommendation = "REBUILD_DNA_WITH_BETTER_KEYS"
    elif fuzzy_row:
        best_match_type = "FUZZY_DNA_CANDIDATE"
        match_confidence = "LOW"
        match_issue = "FUZZY_ONLY_POSSIBLE_NAME_MATCH"
        recommendation = "MANUAL_ENTITY_REVIEW"
    else:
        best_match_type = "NO_MATCH"
        match_confidence = "NONE"
        match_issue = "NO_SECTIONAL_SOURCE_MATCH_FOUND"
        recommendation = "SECTIONAL_SOURCE_COVERAGE_LOW"

    sectional_source_match = ";".join(source_matches) if source_matches else "NONE"

    return {
        "race_date": text(live_row.get("race_date")),
        "track": text(live_row.get("track")),
        "race_no": text(live_row.get("race_no")),
        "horse": horse,
        "horse_key": raw_key,
        "normalised_horse_name": live_name,
        "dna_direct_key_match": yes_no(bool(direct_dna)),
        "dna_normalised_name_match": yes_no(bool(normalised_dna)),
        "sectional_source_match": sectional_source_match,
        "best_match_type": best_match_type,
        "best_match_horse": best_match_horse,
        "best_match_horse_key": best_match_horse_key,
        "match_confidence": match_confidence,
        "match_issue": match_issue,
        "recommendation": recommendation,
        "horse_dna_output_match": yes_no(bool(direct_dna or normalised_dna)),
        "sectional_feature_match": yes_no(bool(feature_match)),
        "sectional_intelligence_match": yes_no(bool(intelligence_match)),
        "universal_sectional_memory_match": yes_no(bool(memory_match)),
        "real_sectional_physics_match": yes_no(bool(physics_match)),
        "fuzzy_match_score": f"{fuzzy_score:.3f}" if fuzzy_score else "",
        "fuzzy_match_horse": text(fuzzy_row.get("horse")) if fuzzy_row else "",
        "fuzzy_match_horse_key": text(fuzzy_row.get("horse_key")) if fuzzy_row else "",
    }


def choose_recommendation(metrics: Counter[str], current_runners: int) -> str:
    direct = metrics.get("DIRECT_DNA_KEY", 0)
    normalised = metrics.get("DNA_NORMALISED_NAME", 0)
    source_only = metrics.get("SECTIONAL_SOURCE_ONLY", 0)
    fuzzy_only = metrics.get("FUZZY_DNA_CANDIDATE", 0)
    no_match = metrics.get("NO_MATCH", 0)
    direct_pct = direct / current_runners if current_runners else 0.0
    no_match_pct = no_match / current_runners if current_runners else 0.0

    issue_types = sum(1 for value in (normalised, source_only, fuzzy_only, no_match) if value > 0)
    if direct_pct >= 0.70:
        return "DNA_COVERAGE_HEALTHY"
    if no_match_pct >= 0.60 and normalised + source_only + fuzzy_only >= 10:
        return "MIXED_ISSUES_REVIEW_REQUIRED"
    if no_match_pct >= 0.60:
        return "SECTIONAL_SOURCE_COVERAGE_LOW"
    if issue_types >= 2 and no_match_pct < 0.60:
        return "MIXED_ISSUES_REVIEW_REQUIRED"
    if source_only >= max(10, normalised + fuzzy_only):
        return "REBUILD_DNA_WITH_BETTER_KEYS"
    if normalised + fuzzy_only >= max(10, source_only):
        return "ADD_NAME_NORMALISATION_LAYER"
    return "MIXED_ISSUES_REVIEW_REQUIRED"


def build_audit() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    live_rows = read_csv(LIVE_FEED_PATH)
    dna_rows = read_csv(HORSE_DNA_PATH)
    feature_rows = read_csv(SECTIONAL_FEATURE_PATH)
    intelligence_rows = read_csv(SECTIONAL_INTELLIGENCE_PATH)
    memory_rows = read_csv(UNIVERSAL_MEMORY_PATH)
    physics_rows = read_csv(REAL_PHYSICS_PATH)

    dna_indexes = build_dna_indexes(dna_rows)
    feature_indexes = build_source_lookup(feature_rows)
    intelligence_indexes = build_source_lookup(intelligence_rows)
    memory_indexes = build_source_lookup(memory_rows)
    physics_indexes = build_source_lookup(physics_rows)

    output_rows = [
        classify_runner(
            live_row,
            dna_indexes,
            feature_indexes,
            intelligence_indexes,
            memory_indexes,
            physics_indexes,
        )
        for live_row in live_rows
    ]

    type_counts = Counter(row["best_match_type"] for row in output_rows)
    recommendation = choose_recommendation(type_counts, len(output_rows))
    built_at = datetime.now(timezone.utc).isoformat()

    direct_matches = type_counts.get("DIRECT_DNA_KEY", 0)
    normalised_matches = type_counts.get("DNA_NORMALISED_NAME", 0)
    source_only = type_counts.get("SECTIONAL_SOURCE_ONLY", 0)
    fuzzy_only = type_counts.get("FUZZY_DNA_CANDIDATE", 0)
    no_match = type_counts.get("NO_MATCH", 0)

    likely_suffix = sum(1 for row in output_rows if row["match_issue"] == "LIKELY_SUFFIX_OR_PUNCTUATION_MATCH")
    likely_key_mismatch = normalised_matches + source_only
    true_missing = no_match

    summary_rows: list[dict[str, Any]] = [
        {
            "audit_section": "OVERALL",
            "built_at": built_at,
            "status": "HORSE_DNA_MATCH_COVERAGE_AUDITED",
            "recommendation": recommendation,
            "current_runners": len(output_rows),
            "direct_dna_key_matches": direct_matches,
            "normalised_dna_name_matches": normalised_matches,
            "source_sectional_matches_not_in_dna": source_only,
            "true_missing_sectional_history": true_missing,
            "likely_key_mismatch_count": likely_key_mismatch,
            "likely_suffix_name_mismatch_count": likely_suffix,
            "fuzzy_only_possible_matches": fuzzy_only,
            "no_match_count": no_match,
            "live_terminal_rows_loaded": len(live_rows),
            "horse_dna_rows_loaded": len(dna_rows),
            "sectional_feature_rows_loaded": len(feature_rows),
            "sectional_intelligence_rows_loaded": len(intelligence_rows),
            "universal_sectional_memory_rows_loaded": len(memory_rows),
            "real_sectional_physics_rows_loaded": len(physics_rows),
            "notes": "Primary issue is low sectional source coverage; secondary recoverable issue is normalised name/key matching. Fuzzy matches are audit-only and are not promoted to production entity matches.",
        }
    ]

    by_race: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    live_by_key = {id(row): source_row for row, source_row in zip(output_rows, live_rows)}
    for output_row in output_rows:
        source_row = next((row for row in live_rows if text(row.get("race_date")) == output_row["race_date"] and text(row.get("track")) == output_row["track"] and text(row.get("race_no")) == output_row["race_no"] and direct_key(row.get("horse_key")) == output_row["horse_key"]), None)
        key = race_key(source_row or output_row)
        by_race[key].append(output_row)

    for key in sorted(by_race, key=lambda item: (item[0], item[1], int(item[2]) if str(item[2]).isdigit() else item[2])):
        rows = by_race[key]
        runners = len(rows)
        dna_matches = sum(1 for row in rows if row["best_match_type"] in {"DIRECT_DNA_KEY", "DNA_NORMALISED_NAME"})
        possible_recoverable = sum(1 for row in rows if row["best_match_type"] in {"DNA_NORMALISED_NAME", "SECTIONAL_SOURCE_ONLY", "FUZZY_DNA_CANDIDATE"})
        race_true_missing = sum(1 for row in rows if row["best_match_type"] == "NO_MATCH")
        coverage_pct = (dna_matches / runners * 100.0) if runners else 0.0
        summary_rows.append(
            {
                "audit_section": "BY_RACE",
                "built_at": built_at,
                "status": "HORSE_DNA_MATCH_COVERAGE_AUDITED",
                "recommendation": recommendation,
                "race_date": key[0],
                "track": key[1],
                "race_no": key[2],
                "runners": runners,
                "dna_matches": dna_matches,
                "possible_recoverable_matches": possible_recoverable,
                "true_missing": race_true_missing,
                "match_coverage_pct": f"{coverage_pct:.2f}",
            }
        )

    return output_rows, summary_rows


def main() -> None:
    output_rows, summary_rows = build_audit()
    write_csv(OUTPUT_PATH, output_rows, OUTPUT_COLUMNS)
    write_csv(SUMMARY_PATH, summary_rows, SUMMARY_COLUMNS)

    overall = summary_rows[0] if summary_rows else {}
    print(f"Horse DNA match coverage rows written: {len(output_rows)}")
    print(f"Summary rows written: {len(summary_rows)}")
    print(f"Status: {overall.get('status')}")
    print(f"Recommendation: {overall.get('recommendation')}")
    print(f"Direct DNA matches: {overall.get('direct_dna_key_matches')}")
    print(f"No match count: {overall.get('no_match_count')}")


if __name__ == "__main__":
    main()
