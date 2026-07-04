from __future__ import annotations

import csv
import hashlib
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "public" / "data"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

LIVE_FEED_PATH = DATA_DIR / "edgeiq_vic_live_terminal_feed_v1.csv"
HORSE_DNA_PATH = DATA_DIR / "edgeiq_horse_dna_v2.csv"

OUTPUT_PATH = DATA_DIR / "edgeiq_sectional_source_expansion_v1.csv"
SUMMARY_PATH = DATA_DIR / "edgeiq_sectional_source_expansion_v1_summary.csv"

SEARCH_TERMS = (
    "sectional",
    "split",
    "velocity",
    "physics",
    "stride",
    "pace",
    "timing",
)

COUNTRY_SUFFIXES = ("IRE", "USA", "JPN", "GER", "SAF", "NZ", "GB", "FR")

USED_BY_HORSE_DNA_V2 = {
    "edgeiq_sectional_feature_engine_v2.csv",
    "edgeiq_sectional_intelligence_v2.csv",
    "edgeiq_universal_sectional_memory_v1.csv",
    "edgeiq_real_sectional_physics_features_v1.csv",
}

ARCHIVE_TOKENS = (
    "audit",
    "diagnostic",
    "diagnostics",
    "summary",
    "backlog",
    "validation",
    "quality",
    "reconciliation",
    "health",
    "inventory",
    "schema",
    "discovery",
    "catalogue",
    "coverage",
    "acquisition",
    "promotion",
    "ambiguity",
    "resolution",
    "probability",
    "realism",
    "comparison",
    "market",
    "execution",
    "board",
    "calibration",
    "outcome",
    "failure",
)

SOURCE_NAME_TOKENS = (
    "sectional",
    "split",
    "physics",
    "timing",
    "warehouse",
    "trusted",
    "payload",
    "normalisation",
    "master",
    "feature",
    "intelligence",
    "memory",
)

METRIC_COLUMNS = (
    "early_speed_kmh",
    "mid_speed_kmh",
    "late_speed_kmh",
    "peak_speed_kmh",
    "avg_speed_kmh",
    "early_speed",
    "midrace_speed",
    "mid_speed",
    "late_speed",
    "peak_speed",
    "avg_speed",
    "early_mean",
    "mid_mean",
    "late_mean",
    "peak_mean",
    "avg_speed_mean",
    "last_600",
    "last_400",
    "last_200",
    "sectional_200",
    "sectional_400",
    "sectional_600",
    "split_count",
    "early_phase_value",
    "mid_phase_value",
    "late_phase_value",
    "acceleration_delta",
    "late_retention_delta",
    "energy_decay_index",
    "late_vs_mid_delta",
    "peak_vs_avg_delta",
    "late_delta_mean",
    "burst_delta_mean",
    "sectional_score",
    "sectional_weapon_score",
    "sectional_strength_score",
    "sustain_index",
    "burst_index",
    "late_power_index",
    "early_speed_score",
    "mid_race_strength_score",
    "late_strength_score",
    "acceleration_score",
    "sustained_speed_score",
    "pressure_tolerance_score",
    "raw_last_600",
    "raw_last_400",
    "raw_last_200",
    "raw_sectional_600",
    "raw_sectional_400",
    "raw_sectional_200",
    "raw_early_speed",
    "raw_midrace_speed",
    "raw_late_speed",
    "early_velocity",
    "mid_velocity",
    "late_velocity",
    "sustained_velocity",
    "fatigue_index",
    "sectional_rating",
)

COUNT_METRIC_COLUMNS = (
    "split_count",
    "split_depth",
    "usable_numeric_count",
)

BAD_QUALITY_VALUES = {
    "BROKEN",
    "NO_PAYLOAD",
    "NO_SPLITS",
    "UNMATCHED",
    "SUPPRESSED_DUPLICATE",
}

TRUST_COLUMNS = (
    "trusted_for_modelling",
    "trusted_for_execution",
    "trusted_for_live_modelling",
    "trusted_for_live_execution",
)

HORSE_COLUMNS = (
    "canonical_horse_key",
    "horse_key",
    "horse",
    "runner",
    "runner_name",
    "selection_name",
    "name",
)

DATE_COLUMNS = (
    "race_date",
    "meeting_date",
    "date",
    "run_date",
    "latest_run",
    "market_captured_at",
    "built_at",
)

TRACK_COLUMNS = (
    "track",
    "venue",
    "meeting_track",
    "race_track",
)

DETAIL_COLUMNS = [
    "row_type",
    "file",
    "file_type",
    "expansion_category",
    "source_grade_for_theoretical_estimate",
    "rows",
    "unique_horses",
    "metric_nonblank_rows",
    "date_range",
    "tracks",
    "usable_horse_identifiers",
    "current_runner_matches",
    "historical_only_rows",
    "coverage_percentage",
    "current_runner_matches_not_in_dna",
    "meeting",
    "meeting_runners",
    "meeting_dna_matches",
    "meeting_all_available_matches",
    "meeting_theoretical_gain",
    "notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except UnicodeDecodeError:
        with path.open("r", encoding="latin-1", newline="") as handle:
            return list(csv.DictReader(handle))
    except csv.Error:
        return []


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


def source_key(row: dict[str, str]) -> str:
    for column in HORSE_COLUMNS:
        key = canonical_horse_key(row.get(column))
        if key:
            return key
    return ""


def normalise_track(value: str | None) -> str:
    raw = text(value).upper()
    raw = re.sub(r"^(SPORTSBET|SPORTS BET|BET365|LADBROKES|TABTOUCH|TAB)\s+", "", raw).strip()
    raw = re.sub(r"[^A-Z0-9]+", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()


def meeting_name(row: dict[str, str]) -> str:
    track = normalise_track(row.get("track"))
    if "SANDOWN" in track:
        return "Sandown"
    if "KILMORE" in track:
        return "Kilmore"
    if "ECHUCA" in track:
        return "Echuca"
    return track.title() if track else "Unknown"


def matching_files() -> list[Path]:
    files: list[Path] = []
    for root in (DATA_DIR, SCRIPTS_DIR):
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            name = str(path.relative_to(PROJECT_ROOT)).lower()
            if any(term in name for term in SEARCH_TERMS):
                files.append(path)
    if HORSE_DNA_PATH.exists() and HORSE_DNA_PATH not in files:
        files.append(HORSE_DNA_PATH)
    return sorted(files, key=lambda value: str(value.relative_to(PROJECT_ROOT)).lower())


def row_count_for_text_file(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return 0


def compact_values(values: set[str], limit: int = 12) -> str:
    usable = sorted(value for value in values if value)
    if not usable:
        return ""
    clipped = usable[:limit]
    suffix = f" (+{len(usable) - limit} more)" if len(usable) > limit else ""
    return "|".join(clipped) + suffix


def date_value(value: str) -> str:
    raw = text(value)
    if not raw:
        return ""
    iso = re.search(r"\d{4}-\d{2}-\d{2}", raw)
    if iso:
        return iso.group(0)
    slash = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", raw)
    if slash:
        day, month, year = slash.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return raw[:10]


def date_range(rows: list[dict[str, str]]) -> str:
    values: set[str] = set()
    for row in rows:
        for column in DATE_COLUMNS:
            value = date_value(row.get(column, ""))
            if value:
                values.add(value)
                break
    if not values:
        return ""
    ordered = sorted(values)
    return f"{ordered[0]} to {ordered[-1]}" if len(ordered) > 1 else ordered[0]


def track_values(rows: list[dict[str, str]]) -> str:
    tracks: set[str] = set()
    for row in rows:
        for column in TRACK_COLUMNS:
            value = normalise_track(row.get(column))
            if value:
                tracks.add(value)
                break
    return compact_values(tracks)


def usable_identifier_columns(rows: list[dict[str, str]]) -> str:
    if not rows:
        return ""
    columns = set(rows[0].keys())
    return "|".join(column for column in HORSE_COLUMNS if column in columns)


def source_rows_with_keys(rows: list[dict[str, str]]) -> tuple[set[str], list[str]]:
    keys: set[str] = set()
    row_keys: list[str] = []
    for row in rows:
        key = source_key(row)
        row_keys.append(key)
        if key:
            keys.add(key)
    return keys, row_keys


def to_float(value: Any) -> float | None:
    raw = text(value)
    if not raw or raw.upper() in {"-", "NA", "N/A", "NULL", "NONE"}:
        return None
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        return None


def row_has_bad_quality_status(row: dict[str, str]) -> bool:
    for column in (
        "payload_quality_grade",
        "validation_status",
        "identity_status",
        "canonical_status",
        "payload_structure_type",
        "match_method",
    ):
        value = text(row.get(column)).upper()
        if value in BAD_QUALITY_VALUES:
            return True
    return False


def row_is_untrusted(row: dict[str, str]) -> bool:
    for column in TRUST_COLUMNS:
        value = text(row.get(column)).upper()
        if value == "NO":
            return True
    return False


def row_has_usable_metric_payload(row: dict[str, str]) -> bool:
    if row_has_bad_quality_status(row) or row_is_untrusted(row):
        return False
    for column in COUNT_METRIC_COLUMNS:
        if column in row:
            value = to_float(row.get(column))
            if value is not None and value > 0:
                return True
    for column in METRIC_COLUMNS:
        if column in COUNT_METRIC_COLUMNS:
            continue
        if column in row:
            value = to_float(row.get(column))
            if value is not None and abs(value) > 0:
                return True
            if value is None and text(row.get(column)):
                return True
    return False


def metric_rows_and_usable_keys(rows: list[dict[str, str]]) -> tuple[int, set[str], list[str]]:
    if not rows:
        return 0, set(), []
    count = 0
    usable_keys: set[str] = set()
    usable_row_keys: list[str] = []
    for row in rows:
        if row_has_usable_metric_payload(row):
            count += 1
            key = source_key(row)
            usable_row_keys.append(key)
            if key:
                usable_keys.add(key)
    return count, usable_keys, usable_row_keys


def key_signature(keys: set[str]) -> str:
    if not keys:
        return ""
    digest = hashlib.sha1()
    for key in sorted(keys):
        digest.update(key.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def is_archived_or_diagnostic(path: Path) -> bool:
    name = path.name.lower()
    return any(token in name for token in ARCHIVE_TOKENS)


def is_source_named(path: Path) -> bool:
    name = path.name.lower()
    return any(token in name for token in SOURCE_NAME_TOKENS)


def is_source_grade(path: Path, unique_horses: int, usable_keys: set[str]) -> bool:
    if path == HORSE_DNA_PATH:
        return True
    if path.suffix.lower() != ".csv":
        return False
    if path.name in USED_BY_HORSE_DNA_V2:
        return True
    if is_archived_or_diagnostic(path):
        return False
    if not is_source_named(path):
        return False
    if unique_horses <= 0:
        return False
    return bool(usable_keys)


def classify_source(
    path: Path,
    keys: set[str],
    duplicate_count: int,
    current_matches: int,
    not_in_dna: int,
    source_grade: bool,
) -> str:
    categories: list[str] = []
    if path == HORSE_DNA_PATH:
        categories.append("BASELINE_DNA_OUTPUT")
    if path.name in USED_BY_HORSE_DNA_V2:
        categories.append("USED_BY_HORSE_DNA_V2")
    if is_archived_or_diagnostic(path):
        categories.append("ARCHIVED_OR_DIAGNOSTIC")
    if duplicate_count > 1 and keys:
        categories.append("DUPLICATE_DATASET")
    if keys and current_matches == 0:
        categories.append("DORMANT_DATASET")
    if path.suffix.lower() == ".py":
        categories.append("SCRIPT_ASSET")
    if source_grade and path.name not in USED_BY_HORSE_DNA_V2 and path != HORSE_DNA_PATH:
        if not_in_dna > 0:
            categories.append("PARTIALLY_USED_DATASET")
        elif current_matches > 0:
            categories.append("UNUSED_SECTIONAL_DATASET")
        else:
            categories.append("UNUSED_HISTORICAL_SOURCE")
    elif keys and not source_grade and current_matches > 0 and path != HORSE_DNA_PATH:
        categories.append("NOT_SOURCE_GRADE_FOR_COVERAGE_ESTIMATE")
    if not categories:
        categories.append("SECTIONAL_ASSET")
    return "|".join(categories)


def pct(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0.00"
    return f"{(numerator / denominator) * 100.0:.2f}"


def count_live_matches(live_keys: list[str], source_keys: set[str]) -> int:
    return sum(1 for key in live_keys if key in source_keys)


def build_sectional_source_expansion_study() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    live_rows = read_csv(LIVE_FEED_PATH)
    dna_rows = read_csv(HORSE_DNA_PATH)

    live_keys_by_meeting: dict[str, list[str]] = defaultdict(list)
    live_keys: list[str] = []
    for row in live_rows:
        key = source_key(row)
        if key:
            live_keys.append(key)
            live_keys_by_meeting[meeting_name(row)].append(key)

    dna_keys, _ = source_rows_with_keys(dna_rows)
    candidate_files = matching_files()

    raw_inventory: list[dict[str, Any]] = []
    signatures: Counter[str] = Counter()

    for path in candidate_files:
        relative = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        file_type = path.suffix.lower().lstrip(".") or "unknown"
        rows: list[dict[str, str]] = []
        row_count = 0
        keys: set[str] = set()
        row_keys: list[str] = []
        coverage_keys: set[str] = set()
        coverage_row_keys: list[str] = []
        metric_rows = 0
        if path.suffix.lower() == ".csv":
            rows = read_csv(path)
            row_count = len(rows)
            keys, row_keys = source_rows_with_keys(rows)
            metric_rows, usable_keys, usable_row_keys = metric_rows_and_usable_keys(rows)
            if path == HORSE_DNA_PATH or path.name in USED_BY_HORSE_DNA_V2:
                coverage_keys = set(keys)
                coverage_row_keys = list(row_keys)
            else:
                coverage_keys = set(usable_keys)
                coverage_row_keys = list(usable_row_keys)
        else:
            row_count = row_count_for_text_file(path)

        signature = key_signature(keys)
        if signature:
            signatures[signature] += 1

        current_matches = count_live_matches(live_keys, coverage_keys)
        historical_only_rows = sum(1 for key in coverage_row_keys if key and key not in set(live_keys))
        current_not_in_dna = sum(1 for key in live_keys if key in coverage_keys and key not in dna_keys)
        source_grade = is_source_grade(path, len(keys), coverage_keys)

        raw_inventory.append(
            {
                "path": path,
                "file": relative,
                "file_type": file_type,
                "rows": row_count,
                "unique_horses": len(keys),
                "keys": keys,
                "coverage_keys": coverage_keys,
                "signature": signature,
                "date_range": date_range(rows),
                "tracks": track_values(rows),
                "usable_horse_identifiers": usable_identifier_columns(rows),
                "metric_nonblank_rows": metric_rows,
                "current_runner_matches": current_matches,
                "historical_only_rows": historical_only_rows,
                "coverage_percentage": pct(current_matches, len(live_keys)),
                "current_runner_matches_not_in_dna": current_not_in_dna,
                "source_grade": source_grade,
            }
        )

    source_grade_keys: set[str] = set()
    for item in raw_inventory:
        if item["source_grade"]:
            source_grade_keys.update(item["coverage_keys"])

    detail_rows: list[dict[str, Any]] = []
    for item in raw_inventory:
        duplicate_count = signatures[item["signature"]] if item["signature"] else 0
        source_grade = item["source_grade"]
        detail_rows.append(
            {
                "row_type": "SOURCE_INVENTORY",
                "file": item["file"],
                "file_type": item["file_type"],
                "expansion_category": classify_source(
                    item["path"],
                    item["keys"],
                    duplicate_count,
                    item["current_runner_matches"],
                    item["current_runner_matches_not_in_dna"],
                    source_grade,
                ),
                "source_grade_for_theoretical_estimate": "TRUE" if source_grade else "FALSE",
                "rows": item["rows"],
                "unique_horses": item["unique_horses"],
                "metric_nonblank_rows": item["metric_nonblank_rows"],
                "date_range": item["date_range"],
                "tracks": item["tracks"],
                "usable_horse_identifiers": item["usable_horse_identifiers"],
                "current_runner_matches": item["current_runner_matches"],
                "historical_only_rows": item["historical_only_rows"],
                "coverage_percentage": item["coverage_percentage"],
                "current_runner_matches_not_in_dna": item["current_runner_matches_not_in_dna"],
                "notes": "Inventory row. Only source_grade_for_theoretical_estimate=TRUE contributes to theoretical expansion.",
            }
        )

    all_available_current_matches = count_live_matches(live_keys, source_grade_keys)
    dna_current_matches = count_live_matches(live_keys, dna_keys)

    for meeting in ["Sandown", "Kilmore", "Echuca"]:
        meeting_keys = live_keys_by_meeting.get(meeting, [])
        meeting_dna = count_live_matches(meeting_keys, dna_keys)
        meeting_all = count_live_matches(meeting_keys, source_grade_keys)
        detail_rows.append(
            {
                "row_type": "MEETING_THEORETICAL_COVERAGE",
                "meeting": meeting,
                "meeting_runners": len(meeting_keys),
                "meeting_dna_matches": meeting_dna,
                "meeting_all_available_matches": meeting_all,
                "meeting_theoretical_gain": meeting_all - meeting_dna,
                "coverage_percentage": pct(meeting_all, len(meeting_keys)),
                "notes": "Coverage if all source-grade sectional assets were fully utilised. Diagnostic/audit files excluded.",
            }
        )

    candidate_data_sources = [
        item
        for item in raw_inventory
        if item["file_type"] == "csv" and item["unique_horses"] > 0
    ]
    source_grade_sources = [item for item in candidate_data_sources if item["source_grade"]]
    unused_with_current = sum(
        1
        for item in source_grade_sources
        if item["path"].name not in USED_BY_HORSE_DNA_V2
        and item["path"] != HORSE_DNA_PATH
        and item["current_runner_matches"] > 0
    )
    partial_with_increment = sum(
        1
        for item in source_grade_sources
        if item["current_runner_matches_not_in_dna"] > 0
        and item["path"].name not in USED_BY_HORSE_DNA_V2
        and item["path"] != HORSE_DNA_PATH
    )
    dormant_sources = sum(1 for item in source_grade_sources if item["current_runner_matches"] == 0)
    duplicate_sources = sum(
        1
        for item in source_grade_sources
        if item["signature"] and signatures[item["signature"]] > 1
    )

    theoretical_gain = all_available_current_matches - dna_current_matches
    if theoretical_gain >= 100:
        recommendation = "MAJOR_EXPANSION_AVAILABLE"
    elif theoretical_gain >= 30:
        recommendation = "MODERATE_EXPANSION_AVAILABLE"
    elif theoretical_gain >= 5:
        recommendation = "LIMITED_EXPANSION_AVAILABLE"
    else:
        recommendation = "NO_MATERIAL_EXPANSION_AVAILABLE"

    summary = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "files_inventory_count": len(candidate_files),
        "data_sources_inventory_count": sum(1 for item in raw_inventory if item["file_type"] == "csv"),
        "script_assets_inventory_count": sum(1 for item in raw_inventory if item["file_type"] == "py"),
        "source_grade_data_sources_count": len(source_grade_sources),
        "current_runners": len(live_keys),
        "horse_dna_v2_current_matches": dna_current_matches,
        "all_available_sectional_current_matches": all_available_current_matches,
        "theoretical_coverage_if_all_available_assets_used_pct": pct(all_available_current_matches, len(live_keys)),
        "theoretical_coverage_gain_vs_horse_dna_v2": theoretical_gain,
        "current_runners_still_missing_after_all_available_assets": len(live_keys) - all_available_current_matches,
        "unused_source_grade_datasets_with_current_runner_matches": unused_with_current,
        "partially_used_source_grade_datasets_with_incremental_current_matches": partial_with_increment,
        "dormant_source_grade_sectional_datasets": dormant_sources,
        "duplicate_source_grade_sectional_datasets": duplicate_sources,
        "sandown_theoretical_matches": count_live_matches(live_keys_by_meeting.get("Sandown", []), source_grade_keys),
        "kilmore_theoretical_matches": count_live_matches(live_keys_by_meeting.get("Kilmore", []), source_grade_keys),
        "echuca_theoretical_matches": count_live_matches(live_keys_by_meeting.get("Echuca", []), source_grade_keys),
        "recommendation": recommendation,
        "status": "SECTIONAL_SOURCE_EXPANSION_RESEARCH_COMPLETE",
    }

    return detail_rows, [summary]


def main() -> None:
    detail_rows, summary_rows = build_sectional_source_expansion_study()
    write_csv(OUTPUT_PATH, detail_rows, DETAIL_COLUMNS)
    write_csv(SUMMARY_PATH, summary_rows, list(summary_rows[0].keys()))

    summary = summary_rows[0]
    print(f"Sectional source expansion rows written: {len(detail_rows)}")
    print(f"Summary written: {SUMMARY_PATH}")
    print(f"Status: {summary['status']}")
    print(f"Recommendation: {summary['recommendation']}")
    print(f"Horse DNA V2 current matches: {summary['horse_dna_v2_current_matches']}")
    print(f"All source-grade sectional current matches: {summary['all_available_sectional_current_matches']}")
    print(f"Theoretical gain: {summary['theoretical_coverage_gain_vs_horse_dna_v2']}")


if __name__ == "__main__":
    main()
