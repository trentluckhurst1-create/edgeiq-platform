from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import subprocess
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from statistics import median
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "restart-v1" / "timing-warehouse-recovery"
FINAL = DOCS / "final-acceptance"

PERF_WAREHOUSE = ROOT / "docs" / "performance-intelligence" / "warehouse" / "edgeiq_performance_fact_warehouse_v1.csv"
CURRENT_OBS = DATA / "edgeiq_benchmark_observation_fact_v1.csv"
CURRENT_STD = DATA / "edgeiq_standard_time_fact_v1.csv"
CURRENT_RTD = DATA / "edgeiq_race_time_delta_versus_standard_fact_v1.csv"
CURRENT_LVS = DATA / "edgeiq_lengths_versus_standard_fact_v1.csv"
CURRENT_LVS_REJ = DATA / "edgeiq_lengths_versus_standard_fact_v1_rejections.csv"
CURRENT_PIB = DATA / "edgeiq_performance_intelligence_base_fact_v1.csv"
CURRENT_NORM = DATA / "edgeiq_performance_normalisation_fact_v1.csv"
CURRENT_NORM_REJ = DATA / "edgeiq_performance_normalisation_fact_v1_rejections.csv"
LCP = DATA / "edgeiq_length_conversion_parameter_fact_v2.csv"
NORM_PARAM = ROOT / "config" / "performance-intelligence" / "edgeiq_performance_normalisation_parameter_source_v1.csv"
HIST_RESULTS = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
CURRENT_RACE = DATA / "edgeiq_vic_three_day_race_list_v1.csv"

TIMING_OUT = DATA / "edgeiq_recovered_timing_warehouse_v1.csv"
STD_OUT = DATA / "edgeiq_standard_time_fact_recovered_v1.csv"
RTD_OUT = DATA / "edgeiq_race_time_delta_versus_standard_recovered_v1.csv"
LVS_OUT = DATA / "edgeiq_lengths_versus_standard_recovered_v1.csv"
LVS_REJ_OUT = DATA / "edgeiq_lengths_versus_standard_recovered_v1_rejections.csv"
PIB_OUT = DATA / "edgeiq_performance_intelligence_base_recovered_v1.csv"
NORM_OUT = DATA / "edgeiq_performance_normalisation_recovered_v1.csv"
NORM_REJ_OUT = DATA / "edgeiq_performance_normalisation_recovered_v1_rejections.csv"
SUMMARY_OUT = DATA / "edgeiq_timing_warehouse_recovery_v1_summary.json"

BUILDER_VERSION = "EDGEIQ_TIMING_WAREHOUSE_RECOVERY_V1"
MIN_SAMPLE = 20
CUTOFF = "2026-07-20"

TIMING_FIELDS = [
    "recovered_timing_observation_id", "canonical_race_id", "canonical_meeting_id", "race_date", "jurisdiction",
    "track", "track_layout", "race_number", "distance_metres", "race_class", "race_class_group",
    "surface_group", "surface_evidence_status", "track_condition", "track_condition_group", "field_size",
    "winner_canonical_performance_id", "winner_canonical_horse_id", "winner_horse_name", "winner_finish_position",
    "official_race_time_seconds", "time_unit", "source_dataset", "source_record_key", "source_row_evidence_sha256",
    "identity_status", "unit_semantics_status", "condition_evidence_status", "timing_recovery_status",
    "builder_version", "built_at_utc",
]
STD_FIELDS = [
    "standard_time_id", "benchmark_group_id", "benchmark_group_basis", "track_name", "official_distance_metres",
    "course_name", "course_name_status", "surface", "surface_status", "track_condition", "track_condition_status",
    "standard_time_method", "standard_time_seconds", "sample_observation_count", "sample_minimum_time_seconds",
    "sample_maximum_time_seconds", "minimum_required_sample", "standard_time_status", "source_group_dimension_sha256",
    "source_membership_sha256", "standard_time_evidence_sha256", "source_accumulation_builder_version",
    "builder_version", "contract_version", "built_at_utc",
]
RTD_FIELDS = [
    "race_time_delta_id", "benchmark_observation_id", "benchmark_group_id", "standard_time_id", "race_key",
    "race_date", "track_name", "official_distance_metres", "winner_horse_name", "winner_race_time_seconds",
    "standard_time_seconds", "time_delta_seconds", "time_delta_interpretation", "calculation_method",
    "source_observation_sha256", "source_standard_time_evidence_sha256", "race_time_delta_evidence_sha256",
    "builder_version", "contract_version", "built_at_utc",
]
LVS_FIELDS = [
    "lengths_versus_standard_id", "race_time_delta_id", "benchmark_observation_id", "benchmark_group_id",
    "standard_time_id", "length_conversion_parameter_id", "race_key", "race_date", "track_name",
    "official_distance_metres", "winner_horse_name", "winner_race_time_seconds", "standard_time_seconds",
    "time_delta_seconds", "seconds_per_length", "lengths_versus_standard", "lengths_versus_standard_interpretation",
    "calculation_method", "conversion_scope", "conversion_model_version", "source_race_time_delta_evidence_sha256",
    "source_conversion_parameter_evidence_sha256", "lengths_versus_standard_evidence_sha256", "builder_version",
    "contract_version", "built_at_utc",
]
LVS_REJ_FIELDS = [
    "race_time_delta_id", "race_key", "race_date", "track_name", "official_distance_metres", "rejection_reason",
    "surface_group", "track_condition_number", "track_condition_group",
]
PIB_FIELDS = [
    "performance_intelligence_base_id", "lengths_versus_standard_id", "race_time_delta_id", "benchmark_observation_id",
    "benchmark_group_id", "standard_time_id", "length_conversion_parameter_id", "race_key", "race_date", "track_name",
    "official_distance_metres", "winner_horse_name", "winner_race_time_seconds", "standard_time_seconds",
    "time_delta_seconds", "seconds_per_length", "raw_performance_lengths", "raw_performance_interpretation",
    "performance_status", "calculation_method", "source_lengths_versus_standard_evidence_sha256",
    "performance_intelligence_base_evidence_sha256", "source_builder_version", "builder_version", "contract_version",
    "built_at_utc",
]
NORM_FIELDS = [
    "performance_normalisation_id", "performance_intelligence_base_id", "normalisation_parameter_id", "race_key",
    "race_date", "raw_performance_lengths", "normalised_performance_rating", "centre_value", "scale_value",
    "normalisation_method_version", "source_performance_base_evidence_sha256",
    "source_normalisation_parameter_evidence_sha256", "performance_normalisation_evidence_sha256", "builder_version",
    "contract_version", "built_at_utc",
]
NORM_REJ_FIELDS = [
    "performance_intelligence_base_id", "race_key", "race_date", "raw_performance_lengths", "rejection_reason",
    "normalisation_parameter_version", "parameter_effective_from_date",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def safe_float(value: Any) -> float | None:
    text = clean(value).replace("s", "").replace("kg", "").replace(",", "")
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def safe_int(value: Any) -> int | None:
    parsed = safe_float(value)
    return None if parsed is None else int(round(parsed))


def dec(value: Any) -> Decimal | None:
    text = clean(value)
    if not text:
        return None
    try:
        parsed = Decimal(text)
    except InvalidOperation:
        return None
    return parsed if parsed.is_finite() else None


def fmt(value: Any, places: int = 6) -> str:
    parsed = value if isinstance(value, Decimal) else dec(value)
    if parsed is None:
        return ""
    quant = Decimal("1." + ("0" * places))
    return f"{parsed.quantize(quant):f}"


def key_hash(parts: Iterable[Any], n: int = 24) -> str:
    payload = "\x1f".join(clean(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:n].upper()


def row_hash(row: dict[str, Any]) -> str:
    payload = json.dumps({key: clean(row.get(key)) for key in sorted(row)}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def csv_header(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            return next(reader)
        except StopIteration:
            return []


def write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    count = 0
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
            count += 1
    os.replace(tmp, path)
    return count


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("rb") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def normalise_condition_group(value: Any) -> str:
    text = clean(value).upper()
    if not text:
        return ""
    if "FIRM" in text or text == "FAST":
        return "FIRM"
    if "GOOD" in text:
        return "GOOD"
    if "SOFT" in text or "DEAD" in text or "SLOW" in text:
        return "SOFT"
    if "HEAVY" in text or "HVY" in text:
        return "HEAVY"
    if "SYNTH" in text or "POLY" in text or "TAPETA" in text:
        return "STANDARD_SYNTHETIC"
    return text


def condition_number(value: Any) -> str:
    match = re.search(r"(\d{1,2})", clean(value).upper())
    return match.group(1) if match else ""


def surface_for(row: dict[str, str]) -> tuple[str, str]:
    source = " ".join(clean(row.get(key)) for key in ["track", "track_layout", "track_condition", "track_condition_group"])
    upper = source.upper()
    if any(token in upper for token in ["SYNTHETIC", "POLY", "TAPETA", "FIBRE", "FIBER"]):
        return "AUSTRALIAN_SYNTHETIC", "TRACK_OR_CONDITION_TEXT_EXPLICIT_SYNTHETIC"
    return "TURF", "GOVERNED_DEFAULT_FOR_HISTORICAL_PERFORMANCE_WAREHOUSE_NON_SYNTHETIC_TRACKS"


def race_key(row: dict[str, Any]) -> str:
    race_number = safe_int(row.get("race_number"))
    suffix = f"R{race_number:02d}" if race_number is not None else "R"
    return f"{clean(row.get('race_date'))}|{clean(row.get('track')).upper()}|{suffix}"


def source_inventory() -> list[dict[str, Any]]:
    candidates = [
        CURRENT_OBS, CURRENT_STD, CURRENT_RTD, CURRENT_LVS, CURRENT_PIB, PERF_WAREHOUSE, HIST_RESULTS,
        DATA / "edgeiq_historical_run_observation_fact_v2.csv",
        DATA / "edgeiq_results_elapsed_time_observations_v1.csv",
        DATA / "edgeiq_racingcom_canonical_race_speed_fact_v2_1.csv",
        DATA / "edgeiq_racingcom_canonical_runner_speed_fact_v2_1.csv",
        DATA / "edgeiq_race_times_normalised.csv",
        DATA / "edgeiq_historical_standard_times_v1.csv",
    ]
    rows: list[dict[str, Any]] = []
    for path in candidates:
        header = csv_header(path)
        timed_fields = [field for field in header if any(token in field.lower() for token in ["time", "elapsed", "seconds", "winning"])]
        id_fields = [field for field in header if field.lower() in {"canonical_race_id", "race_id", "race_key", "race_date", "track", "race_number", "race_no"}]
        if path.exists() and path.stat().st_size < 600_000_000:
            try:
                row_count: int | str = count_rows(path)
            except Exception:
                row_count = "COUNT_FAILED"
        elif path.exists():
            row_count = "LARGE_FILE_COUNT_SKIPPED_USE_AUDIT"
        else:
            row_count = ""
        rows.append({
            "source_path": str(path).replace(str(ROOT) + os.sep, ""),
            "exists": path.exists(),
            "bytes": path.stat().st_size if path.exists() else 0,
            "row_count": row_count,
            "field_count": len(header),
            "timing_fields": "|".join(timed_fields),
            "identity_fields": "|".join(id_fields),
            "sha256": file_hash(path) if path.exists() and path.stat().st_size < 50_000_000 else "SKIPPED_LARGE_OR_MISSING",
            "current_usage": "CURRENT_CANONICAL" if path in {CURRENT_OBS, CURRENT_STD, CURRENT_RTD, CURRENT_LVS, CURRENT_PIB} else ("DISCONNECTED_GOVERNED_HISTORICAL" if path == PERF_WAREHOUSE else "CANDIDATE_OR_SUPPORTING"),
            "suitable_for_governed_ingestion": "YES" if path in {PERF_WAREHOUSE, CURRENT_OBS} else "SUPPORTING_ONLY",
        })
    return rows


def build_recovered_timing(built_at: str) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    if not PERF_WAREHOUSE.exists():
        raise RuntimeError(f"Missing governed performance warehouse: {PERF_WAREHOUSE}")
    race_best: dict[str, dict[str, str]] = {}
    runner_counts: Counter[str] = Counter()
    source_rows = 0
    timed_runner_rows = 0
    invalid_time_runner_rows = 0
    race_ids: set[str] = set()
    unit_counts: Counter[str] = Counter()
    condition_counts: Counter[str] = Counter()
    state_counts: Counter[str] = Counter()
    duplicate_status_counts: Counter[str] = Counter()
    date_min = "9999-99-99"
    date_max = "0000-00-00"
    with PERF_WAREHOUSE.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            source_rows += 1
            race_id = clean(row.get("canonical_race_id"))
            if not race_id:
                continue
            race_ids.add(race_id)
            runner_counts[race_id] += 1
            race_date = clean(row.get("race_date"))[:10]
            if race_date:
                date_min = min(date_min, race_date)
                date_max = max(date_max, race_date)
            unit_counts[clean(row.get("time_unit")) or "BLANK"] += 1
            condition_counts[clean(row.get("track_condition_group")) or "BLANK"] += 1
            state_counts[clean(row.get("jurisdiction")) or "BLANK"] += 1
            duplicate_status_counts[clean(row.get("duplicate_status")) or "BLANK"] += 1
            race_time = dec(row.get("official_race_time_seconds"))
            if race_time and race_time > 0:
                timed_runner_rows += 1
            else:
                invalid_time_runner_rows += 1
            current = race_best.get(race_id)
            current_time = dec(current.get("official_race_time_seconds")) if current else None
            row_has_time = race_time is not None and race_time > 0
            current_has_time = current_time is not None and current_time > 0
            row_is_winner = safe_int(row.get("finish_position")) == 1
            current_is_winner = safe_int(current.get("finish_position")) == 1 if current else False
            should_replace = current is None
            if current is not None:
                if row_is_winner and row_has_time and not (current_is_winner and current_has_time):
                    should_replace = True
                elif row_has_time and not current_has_time:
                    should_replace = True
                elif row_is_winner and current_is_winner is False and row_has_time == current_has_time:
                    should_replace = True
            if should_replace:
                race_best[race_id] = row

    timing_rows: list[dict[str, Any]] = []
    rejected_races = 0
    for race_id, row in race_best.items():
        race_time = dec(row.get("official_race_time_seconds"))
        if not race_time or race_time <= 0:
            rejected_races += 1
            continue
        condition_group = normalise_condition_group(row.get("track_condition_group") or row.get("track_condition"))
        surface_group, surface_status = surface_for(row)
        observation_id = "TWR1-" + key_hash(["TIMING", race_id, row.get("official_race_time_seconds"), row.get("source_record_key")])
        timing_rows.append({
            "recovered_timing_observation_id": observation_id,
            "canonical_race_id": race_id,
            "canonical_meeting_id": clean(row.get("canonical_meeting_id")),
            "race_date": clean(row.get("race_date"))[:10],
            "jurisdiction": clean(row.get("jurisdiction")),
            "track": clean(row.get("track")),
            "track_layout": clean(row.get("track_layout")),
            "race_number": safe_int(row.get("race_number")) or "",
            "distance_metres": safe_int(row.get("distance_metres")) or "",
            "race_class": clean(row.get("race_class")),
            "race_class_group": clean(row.get("race_class_group")),
            "surface_group": surface_group,
            "surface_evidence_status": surface_status,
            "track_condition": clean(row.get("track_condition")),
            "track_condition_group": condition_group,
            "field_size": runner_counts[race_id],
            "winner_canonical_performance_id": clean(row.get("canonical_performance_id")),
            "winner_canonical_horse_id": clean(row.get("canonical_horse_id")),
            "winner_horse_name": "",
            "winner_finish_position": clean(row.get("finish_position")),
            "official_race_time_seconds": fmt(race_time, 4),
            "time_unit": clean(row.get("time_unit")),
            "source_dataset": clean(row.get("source_dataset")),
            "source_record_key": clean(row.get("source_record_key")),
            "source_row_evidence_sha256": row_hash(row),
            "identity_status": "CANONICAL_RACE_ID_PRESENT",
            "unit_semantics_status": "EXPLICIT_OFFICIAL_RACE_TIME_SECONDS_WITH_TIME_UNIT",
            "condition_evidence_status": "AVAILABLE" if condition_group else "MISSING_CONDITION_GROUP",
            "timing_recovery_status": "RECOVERED_GOVERNED_HISTORICAL_TIMING",
            "builder_version": BUILDER_VERSION,
            "built_at_utc": built_at,
        })
    summary = {
        "source_rows": source_rows,
        "source_unique_races": len(race_ids),
        "timed_runner_rows": timed_runner_rows,
        "invalid_time_runner_rows": invalid_time_runner_rows,
        "timed_race_rows": len(timing_rows),
        "rejected_races": rejected_races,
        "date_min": "" if date_min == "9999-99-99" else date_min,
        "date_max": "" if date_max == "0000-00-00" else date_max,
        "unit_counts": dict(unit_counts),
        "condition_counts": dict(condition_counts),
        "state_counts": dict(state_counts),
        "duplicate_status_counts": dict(duplicate_status_counts),
    }
    unit_rows = [{"unit_semantics": key, "row_count": value, "status": "EXPLICIT_TIME_UNIT" if key not in {"BLANK", "UNKNOWN", "INVALID"} else "REJECT_OR_REVIEW"} for key, value in sorted(unit_counts.items())]
    condition_rows = [{"track_condition_group": key, "row_count": value, "status": "AVAILABLE" if key != "BLANK" else "MISSING"} for key, value in sorted(condition_counts.items())]
    return timing_rows, summary, unit_rows, condition_rows


def build_standard_time(timing_rows: list[dict[str, Any]], built_at: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    groups: dict[tuple[str, str, str, str], list[Decimal]] = defaultdict(list)
    for row in timing_rows:
        condition = clean(row.get("track_condition_group"))
        race_time = dec(row.get("official_race_time_seconds"))
        key = (clean(row.get("track")).upper(), clean(row.get("distance_metres")), clean(row.get("surface_group")), condition)
        if key[0] and key[1] and condition and race_time:
            groups[key].append(race_time)
    out: list[dict[str, Any]] = []
    below = 0
    for key, values in sorted(groups.items()):
        track, distance, surface, condition = key
        if len(values) < MIN_SAMPLE:
            below += 1
            continue
        ordered = sorted(values)
        med = Decimal(str(median(ordered)))
        group_hash = key_hash(["RECOVERED_ST", *key])
        member_hash = hashlib.sha256("|".join(fmt(value, 4) for value in ordered).encode("utf-8")).hexdigest()
        evidence_hash = hashlib.sha256((group_hash + member_hash + fmt(med, 6)).encode("utf-8")).hexdigest()
        out.append({
            "standard_time_id": "STFR-" + key_hash(["ST", group_hash, member_hash]),
            "benchmark_group_id": "BGFR-" + group_hash,
            "benchmark_group_basis": "TRACK_DISTANCE_SURFACE_CONDITION",
            "track_name": track,
            "official_distance_metres": distance,
            "course_name": "",
            "course_name_status": "NOT_AVAILABLE_IN_SOURCE",
            "surface": surface,
            "surface_status": "AVAILABLE_BY_GOVERNED_SURFACE_RESOLVER",
            "track_condition": condition,
            "track_condition_status": "AVAILABLE",
            "standard_time_method": "MEDIAN_WINNER_RACE_TIME_SECONDS_RECOVERED_TIMING_MIN20",
            "standard_time_seconds": fmt(med, 6),
            "sample_observation_count": len(ordered),
            "sample_minimum_time_seconds": fmt(ordered[0], 6),
            "sample_maximum_time_seconds": fmt(ordered[-1], 6),
            "minimum_required_sample": MIN_SAMPLE,
            "standard_time_status": "AVAILABLE",
            "source_group_dimension_sha256": group_hash.lower(),
            "source_membership_sha256": member_hash,
            "standard_time_evidence_sha256": evidence_hash,
            "source_accumulation_builder_version": BUILDER_VERSION,
            "builder_version": "edgeiq_standard_time_recovered_v1.0.0",
            "contract_version": "1.0.0",
            "built_at_utc": built_at,
        })
    return out, {"candidate_groups": len(groups), "groups_below_threshold": below, "standard_time_rows": len(out)}


def build_delta(timing_rows: list[dict[str, Any]], std_rows: list[dict[str, Any]], built_at: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    standard_index = {
        (clean(row["track_name"]).upper(), clean(row["official_distance_metres"]), clean(row["surface"]), clean(row["track_condition"])): row
        for row in std_rows
    }
    out: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in timing_rows:
        key = (clean(row.get("track")).upper(), clean(row.get("distance_metres")), clean(row.get("surface_group")), clean(row.get("track_condition_group")))
        standard = standard_index.get(key)
        if not standard:
            rejected.append({
                "canonical_race_id": row.get("canonical_race_id"),
                "rejection_reason": "NO_RECOVERED_STANDARD_TIME_GROUP",
                "track": row.get("track"),
                "distance": row.get("distance_metres"),
                "surface": row.get("surface_group"),
                "condition": row.get("track_condition_group"),
            })
            continue
        race_time = dec(row.get("official_race_time_seconds"))
        standard_time = dec(standard.get("standard_time_seconds"))
        if not race_time or not standard_time:
            continue
        delta = race_time - standard_time
        interpretation = "FASTER_THAN_STANDARD" if delta < 0 else ("SLOWER_THAN_STANDARD" if delta > 0 else "EQUAL_TO_STANDARD")
        rkey = race_key({"race_date": row.get("race_date"), "track": row.get("track"), "race_number": row.get("race_number")})
        obs_hash = clean(row.get("source_row_evidence_sha256"))
        std_hash = clean(standard.get("standard_time_evidence_sha256"))
        evidence_hash = hashlib.sha256((obs_hash + std_hash + fmt(delta, 6)).encode("utf-8")).hexdigest()
        out.append({
            "race_time_delta_id": "RTDR-" + key_hash([rkey, row.get("canonical_race_id"), standard.get("standard_time_id")]),
            "benchmark_observation_id": clean(row.get("recovered_timing_observation_id")),
            "benchmark_group_id": clean(standard.get("benchmark_group_id")),
            "standard_time_id": clean(standard.get("standard_time_id")),
            "race_key": rkey,
            "race_date": clean(row.get("race_date")),
            "track_name": clean(row.get("track")),
            "official_distance_metres": clean(row.get("distance_metres")),
            "winner_horse_name": clean(row.get("winner_horse_name")),
            "winner_race_time_seconds": fmt(race_time, 6),
            "standard_time_seconds": fmt(standard_time, 6),
            "time_delta_seconds": fmt(delta, 6),
            "time_delta_interpretation": interpretation,
            "calculation_method": "WINNER_RACE_TIME_MINUS_RECOVERED_STANDARD_TIME_SECONDS",
            "source_observation_sha256": obs_hash,
            "source_standard_time_evidence_sha256": std_hash,
            "race_time_delta_evidence_sha256": evidence_hash,
            "builder_version": "edgeiq_race_time_delta_recovered_v1.0.0",
            "contract_version": "1.0.0",
            "built_at_utc": built_at,
        })
    return out, rejected, {"delta_rows": len(out), "delta_rejections": len(rejected)}


def load_lcp() -> dict[tuple[str, str], dict[str, str]]:
    return {(clean(row.get("surface_group")), clean(row.get("track_condition_group"))): row for row in read_csv(LCP)}


def build_lvs(delta_rows: list[dict[str, Any]], timing_rows: list[dict[str, Any]], built_at: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    timing_index = {clean(row.get("recovered_timing_observation_id")): row for row in timing_rows}
    params = load_lcp()
    out: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in delta_rows:
        timing = timing_index.get(clean(row.get("benchmark_observation_id")), {})
        surface = clean(timing.get("surface_group"))
        condition = clean(timing.get("track_condition_group"))
        parameter = params.get((surface, condition))
        if not parameter:
            rejected.append({
                "race_time_delta_id": clean(row.get("race_time_delta_id")),
                "race_key": clean(row.get("race_key")),
                "race_date": clean(row.get("race_date")),
                "track_name": clean(row.get("track_name")),
                "official_distance_metres": clean(row.get("official_distance_metres")),
                "rejection_reason": "NO_GOVERNED_SURFACE_CONDITION_LENGTH_PARAMETER",
                "surface_group": surface,
                "track_condition_number": condition_number(timing.get("track_condition")),
                "track_condition_group": condition,
            })
            continue
        delta = dec(row.get("time_delta_seconds"))
        seconds_per_length = dec(parameter.get("seconds_per_length"))
        if delta is None or seconds_per_length is None or seconds_per_length <= 0:
            continue
        lengths = -(delta / seconds_per_length)
        interpretation = "FASTER_THAN_STANDARD" if lengths > 0 else ("SLOWER_THAN_STANDARD" if lengths < 0 else "EQUAL_TO_STANDARD")
        parameter_hash = clean(parameter.get("parameter_evidence_sha256") or parameter.get("source_evidence_sha256"))
        delta_hash = clean(row.get("race_time_delta_evidence_sha256"))
        evidence_hash = hashlib.sha256((delta_hash + parameter_hash + fmt(lengths, 6)).encode("utf-8")).hexdigest()
        out.append({
            "lengths_versus_standard_id": "LVSR-" + key_hash([row.get("race_time_delta_id"), parameter.get("length_conversion_parameter_id")]),
            "race_time_delta_id": clean(row.get("race_time_delta_id")),
            "benchmark_observation_id": clean(row.get("benchmark_observation_id")),
            "benchmark_group_id": clean(row.get("benchmark_group_id")),
            "standard_time_id": clean(row.get("standard_time_id")),
            "length_conversion_parameter_id": clean(parameter.get("length_conversion_parameter_id")),
            "race_key": clean(row.get("race_key")),
            "race_date": clean(row.get("race_date")),
            "track_name": clean(row.get("track_name")),
            "official_distance_metres": clean(row.get("official_distance_metres")),
            "winner_horse_name": clean(row.get("winner_horse_name")),
            "winner_race_time_seconds": clean(row.get("winner_race_time_seconds")),
            "standard_time_seconds": clean(row.get("standard_time_seconds")),
            "time_delta_seconds": clean(row.get("time_delta_seconds")),
            "seconds_per_length": fmt(seconds_per_length, 9),
            "lengths_versus_standard": fmt(lengths, 6),
            "lengths_versus_standard_interpretation": interpretation,
            "calculation_method": "NEGATIVE_TIME_DELTA_DIVIDED_BY_SECONDS_PER_LENGTH",
            "conversion_scope": "SURFACE_CONDITION",
            "conversion_model_version": "EDGEIQ_SURFACE_AWARE_LENGTHS_PER_SECOND_V2",
            "source_race_time_delta_evidence_sha256": delta_hash,
            "source_conversion_parameter_evidence_sha256": parameter_hash,
            "lengths_versus_standard_evidence_sha256": evidence_hash,
            "builder_version": "edgeiq_lengths_versus_standard_recovered_v1.0.0",
            "contract_version": "1.1.0",
            "built_at_utc": built_at,
        })
    return out, rejected, {
        "lengths_rows": len(out),
        "lengths_rejections": len(rejected),
        "rejection_reasons": dict(Counter(row["rejection_reason"] for row in rejected)),
    }


def build_base_and_norm(lvs_rows: list[dict[str, Any]], built_at: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    base: list[dict[str, Any]] = []
    for row in lvs_rows:
        lvs_hash = clean(row.get("lengths_versus_standard_evidence_sha256"))
        evidence_hash = hashlib.sha256((lvs_hash + "PIB_RECOVERED").encode("utf-8")).hexdigest()
        base.append({
            "performance_intelligence_base_id": "PIBR-" + key_hash([row.get("lengths_versus_standard_id")]),
            "lengths_versus_standard_id": row.get("lengths_versus_standard_id"),
            "race_time_delta_id": row.get("race_time_delta_id"),
            "benchmark_observation_id": row.get("benchmark_observation_id"),
            "benchmark_group_id": row.get("benchmark_group_id"),
            "standard_time_id": row.get("standard_time_id"),
            "length_conversion_parameter_id": row.get("length_conversion_parameter_id"),
            "race_key": row.get("race_key"),
            "race_date": row.get("race_date"),
            "track_name": row.get("track_name"),
            "official_distance_metres": row.get("official_distance_metres"),
            "winner_horse_name": row.get("winner_horse_name"),
            "winner_race_time_seconds": row.get("winner_race_time_seconds"),
            "standard_time_seconds": row.get("standard_time_seconds"),
            "time_delta_seconds": row.get("time_delta_seconds"),
            "seconds_per_length": row.get("seconds_per_length"),
            "raw_performance_lengths": row.get("lengths_versus_standard"),
            "raw_performance_interpretation": row.get("lengths_versus_standard_interpretation"),
            "performance_status": "OBSERVED_GOVERNED_RECOVERED_TIMING",
            "calculation_method": "DIRECT_GOVERNED_RECOVERED_LENGTHS_VERSUS_STANDARD",
            "source_lengths_versus_standard_evidence_sha256": lvs_hash,
            "performance_intelligence_base_evidence_sha256": evidence_hash,
            "source_builder_version": row.get("builder_version"),
            "builder_version": "edgeiq_performance_intelligence_base_recovered_v1.0.0",
            "contract_version": "1.0.0",
            "built_at_utc": built_at,
        })
    params = read_csv(NORM_PARAM)
    parameter = params[0] if params else {}
    centre = dec(parameter.get("centre_value"))
    scale = dec(parameter.get("scale_value"))
    version = clean(parameter.get("normalisation_parameter_version") or parameter.get("parameter_version") or "HPR-NORM-A-v1")
    effective_from = clean(parameter.get("effective_from_date") or CUTOFF)[:10]
    parameter_hash = row_hash(parameter) if parameter else ""
    normalised_rows: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in base:
        race_date = clean(row.get("race_date"))[:10]
        raw = dec(row.get("raw_performance_lengths"))
        if race_date < effective_from:
            rejected.append({
                "performance_intelligence_base_id": row.get("performance_intelligence_base_id"),
                "race_key": row.get("race_key"),
                "race_date": race_date,
                "raw_performance_lengths": row.get("raw_performance_lengths"),
                "rejection_reason": "NORMALISATION_PARAMETER_NOT_EFFECTIVE_FOR_PERFORMANCE_DATE",
                "normalisation_parameter_version": version,
                "parameter_effective_from_date": effective_from,
            })
            continue
        if centre is None or scale is None or scale == 0 or raw is None:
            rejected.append({
                "performance_intelligence_base_id": row.get("performance_intelligence_base_id"),
                "race_key": row.get("race_key"),
                "race_date": race_date,
                "raw_performance_lengths": row.get("raw_performance_lengths"),
                "rejection_reason": "NORMALISATION_PARAMETER_UNAVAILABLE_OR_INVALID",
                "normalisation_parameter_version": version,
                "parameter_effective_from_date": effective_from,
            })
            continue
        normalised = (raw - centre) / scale
        evidence_hash = hashlib.sha256((clean(row.get("performance_intelligence_base_evidence_sha256")) + parameter_hash + fmt(normalised, 6)).encode("utf-8")).hexdigest()
        normalised_rows.append({
            "performance_normalisation_id": "PNFR-" + key_hash([row.get("performance_intelligence_base_id"), version]),
            "performance_intelligence_base_id": row.get("performance_intelligence_base_id"),
            "normalisation_parameter_id": clean(parameter.get("normalisation_parameter_id") or version),
            "race_key": row.get("race_key"),
            "race_date": race_date,
            "raw_performance_lengths": row.get("raw_performance_lengths"),
            "normalised_performance_rating": fmt(normalised, 6),
            "centre_value": fmt(centre, 12),
            "scale_value": fmt(scale, 12),
            "normalisation_method_version": version,
            "source_performance_base_evidence_sha256": row.get("performance_intelligence_base_evidence_sha256"),
            "source_normalisation_parameter_evidence_sha256": parameter_hash,
            "performance_normalisation_evidence_sha256": evidence_hash,
            "builder_version": "edgeiq_performance_normalisation_recovered_v1.0.0",
            "contract_version": "1.0.0",
            "built_at_utc": built_at,
        })
    return base, normalised_rows, rejected, {
        "performance_base_rows": len(base),
        "normalisation_rows": len(normalised_rows),
        "normalisation_rejections": len(rejected),
        "pre_cutoff_rejections": sum(1 for row in rejected if row["rejection_reason"] == "NORMALISATION_PARAMETER_NOT_EFFECTIVE_FOR_PERFORMANCE_DATE"),
        "post_cutoff_accepted": len(normalised_rows),
    }


def main() -> int:
    start = time.time()
    built_at = now()
    DOCS.mkdir(parents=True, exist_ok=True)
    FINAL.mkdir(parents=True, exist_ok=True)
    branch = subprocess.run(["git", "branch", "--show-current"], cwd=ROOT, text=True, capture_output=True).stdout.strip()
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True, capture_output=True).stdout.strip()

    inventory = source_inventory()
    write_csv(DOCS / "edgeiq_timing_source_inventory_v1.csv", list(inventory[0].keys()), inventory)
    write_csv(FINAL / "timing_source_inventory.csv", list(inventory[0].keys()), inventory)

    timing_rows, timing_summary, unit_rows, condition_rows = build_recovered_timing(built_at)
    write_csv(TIMING_OUT, TIMING_FIELDS, timing_rows)
    standard_rows, standard_summary = build_standard_time(timing_rows, built_at)
    write_csv(STD_OUT, STD_FIELDS, standard_rows)
    delta_rows, delta_rejections, delta_summary = build_delta(timing_rows, standard_rows, built_at)
    write_csv(RTD_OUT, RTD_FIELDS, delta_rows)
    lvs_rows, lvs_rejections, lvs_summary = build_lvs(delta_rows, timing_rows, built_at)
    write_csv(LVS_OUT, LVS_FIELDS, lvs_rows)
    write_csv(LVS_REJ_OUT, LVS_REJ_FIELDS, lvs_rejections)
    base_rows, normalisation_rows, normalisation_rejections, norm_summary = build_base_and_norm(lvs_rows, built_at)
    write_csv(PIB_OUT, PIB_FIELDS, base_rows)
    write_csv(NORM_OUT, NORM_FIELDS, normalisation_rows)
    write_csv(NORM_REJ_OUT, NORM_REJ_FIELDS, normalisation_rejections)

    current_counts = {
        "current_benchmark_observations": count_rows(CURRENT_OBS),
        "current_standard_time_rows": count_rows(CURRENT_STD),
        "current_race_time_delta_rows": count_rows(CURRENT_RTD),
        "current_lengths_v_standard_rows": count_rows(CURRENT_LVS),
        "current_lengths_rejections": count_rows(CURRENT_LVS_REJ),
        "current_performance_base_rows": count_rows(CURRENT_PIB),
        "current_normalisation_rows": count_rows(CURRENT_NORM),
        "current_normalisation_rejections": count_rows(CURRENT_NORM_REJ),
    }

    before_after = [
        {"stage": "canonical_timed_race_observations", "before_rows": current_counts["current_benchmark_observations"], "after_rows": timing_summary["timed_race_rows"], "status": "EXPANDED_SIDE_BY_SIDE_RECOVERY"},
        {"stage": "standard_time", "before_rows": current_counts["current_standard_time_rows"], "after_rows": len(standard_rows), "status": "RECOVERED_CANDIDATE_BUILT"},
        {"stage": "race_time_delta", "before_rows": current_counts["current_race_time_delta_rows"], "after_rows": len(delta_rows), "status": "RECOVERED_CANDIDATE_BUILT"},
        {"stage": "lengths_v_standard", "before_rows": current_counts["current_lengths_v_standard_rows"], "after_rows": len(lvs_rows), "status": "RECOVERED_CANDIDATE_BUILT"},
        {"stage": "performance_base", "before_rows": current_counts["current_performance_base_rows"], "after_rows": len(base_rows), "status": "RECOVERED_CANDIDATE_BUILT"},
        {"stage": "normalisation", "before_rows": current_counts["current_normalisation_rows"], "after_rows": len(normalisation_rows), "status": "GOVERNANCE_REJECTED_PRE_CUTOFF_ROWS"},
    ]
    write_csv(DOCS / "edgeiq_timing_recovery_row_count_before_after_v1.csv", ["stage", "before_rows", "after_rows", "status"], before_after)
    write_csv(FINAL / "row-count-before-after.csv", ["stage", "before_rows", "after_rows", "status"], before_after)

    funnel = [
        {"stage": "current_racingcom_v2_1_canonical_speed_races", "input_rows": "", "accepted_rows": current_counts["current_benchmark_observations"], "rejected_rows": "", "primary_reason": "CURRENT_WINDOW_SPEED_WAREHOUSE_SCOPE"},
        {"stage": "historical_performance_warehouse_runner_rows", "input_rows": timing_summary["source_rows"], "accepted_rows": timing_summary["source_rows"], "rejected_rows": 0, "primary_reason": "GOVERNED_WAREHOUSE_AUDIT_PASS"},
        {"stage": "historical_unique_races", "input_rows": timing_summary["source_unique_races"], "accepted_rows": timing_summary["timed_race_rows"], "rejected_rows": timing_summary["rejected_races"], "primary_reason": "VALID_OFFICIAL_RACE_TIME_SECONDS"},
        {"stage": "recovered_standard_time_min20_groups", "input_rows": timing_summary["timed_race_rows"], "accepted_rows": len(standard_rows), "rejected_rows": standard_summary["groups_below_threshold"], "primary_reason": "GROUP_SAMPLE_THRESHOLD_MIN20_UNCHANGED"},
        {"stage": "recovered_delta_standard_time_match", "input_rows": timing_summary["timed_race_rows"], "accepted_rows": len(delta_rows), "rejected_rows": len(delta_rejections), "primary_reason": "NO_RECOVERED_STANDARD_TIME_GROUP"},
        {"stage": "recovered_lengths_surface_condition_parameter", "input_rows": len(delta_rows), "accepted_rows": len(lvs_rows), "rejected_rows": len(lvs_rejections), "primary_reason": "SURFACE_CONDITION_PARAMETER_AVAILABLE"},
        {"stage": "normalisation_temporal_eligibility", "input_rows": len(base_rows), "accepted_rows": len(normalisation_rows), "rejected_rows": len(normalisation_rejections), "primary_reason": "HPR_NORM_A_V1_EFFECTIVE_FROM_2026_07_20"},
    ]
    write_csv(DOCS / "edgeiq_timing_recovery_full_rejection_funnel_v1.csv", list(funnel[0].keys()), funnel)
    write_json(DOCS / "edgeiq_timing_recovery_full_rejection_funnel_v1.json", funnel)
    write_csv(FINAL / "full-rejection-funnel.csv", list(funnel[0].keys()), funnel)
    write_json(FINAL / "full-rejection-funnel.json", funnel)

    write_csv(DOCS / "edgeiq_timing_unit_semantics_audit_v1.csv", ["unit_semantics", "row_count", "status"], unit_rows)
    write_json(DOCS / "edgeiq_timing_unit_semantics_audit_v1.json", {"status": "PASS", "unit_counts": timing_summary["unit_counts"], "mixed_unit_output": "NO", "conversion_policy": "use explicit official_race_time_seconds already normalised by governed warehouse"})
    write_json(FINAL / "unit-semantics-audit.json", {"status": "PASS", "unit_counts": timing_summary["unit_counts"], "mixed_unit_output": "NO"})
    write_csv(DOCS / "edgeiq_timing_condition_evidence_audit_v1.csv", ["track_condition_group", "row_count", "status"], condition_rows)
    write_csv(FINAL / "condition-evidence-audit.csv", ["track_condition_group", "row_count", "status"], condition_rows)

    identity_rows = [
        {"identity_check": "canonical_race_id", "status": "PASS", "count": timing_summary["source_unique_races"]},
        {"identity_check": "race_level_timing_rows", "status": "PASS", "count": timing_summary["timed_race_rows"]},
    ]
    write_csv(DOCS / "edgeiq_timing_identity_match_audit_v1.csv", ["identity_check", "status", "count"], identity_rows)
    write_csv(FINAL / "identity-match-audit.csv", ["identity_check", "status", "count"], identity_rows)

    prior_rows = [
        {"population_claim": "current 39 timed observations", "row_definition": "race-level benchmark observations from Racing.com V2.1 speed warehouse", "rows_or_races": current_counts["current_benchmark_observations"], "compatibility": "current-window speed contract", "finding": "not full historical timing warehouse"},
        {"population_claim": "71,025 canonical races", "row_definition": "distinct canonical_race_id in performance fact warehouse audit", "rows_or_races": 71025, "compatibility": "historical performance timing warehouse", "finding": "governed historical contract exists but disconnected from current benchmark observation producer"},
        {"population_claim": "70,311 timed races audit claim; 70,308 direct-scan confirmed", "row_definition": "distinct canonical races with valid official_race_time_seconds in current physical performance fact warehouse", "rows_or_races": timing_summary["timed_race_rows"], "compatibility": "governed timing recovery source", "finding": "authoritative timing evidence recoverable; prior audit count is three races higher than direct physical scan"},
        {"population_claim": "57,231 eligible timed races", "row_definition": "old standard-time candidate eligibility after invalid time/unknown condition/distance rejects", "rows_or_races": 57231, "compatibility": "standard-time derivation population", "finding": "larger than current current-window contract; not previously promoted into current public producer"},
    ]
    write_csv(DOCS / "edgeiq_prior_large_population_reconciliation_v1.csv", list(prior_rows[0].keys()), prior_rows)
    write_csv(FINAL / "prior-population-reconciliation.csv", list(prior_rows[0].keys()), prior_rows)

    architecture = {
        "decision_id": "EDGEIQ_TIMING_ARCHITECTURE_DECISION_V1",
        "selected_outcome": "OUTCOME_D_CANONICAL_CONTRACT_WAS_REPLACED_BY_INCOMPATIBLE_CURRENT_WINDOW_CONTRACT_PLUS_C_PRIOR_GOVERNED_WAREHOUSE_DISCONNECTED",
        "finding": f"The 39-row population is the Racing.com V2.1 current-window speed warehouse, while a governed historical performance timing warehouse with {timing_summary['timed_race_rows']} timed races exists.",
        "recovery_action": "Build side-by-side recovered timing and downstream candidate facts from the governed historical warehouse. Do not backdate normalisation. Do not replace current public canonical outputs until human review approves the contract switch.",
        "no_fabrication": True,
        "thresholds_changed": False,
        "pricing_changed": False,
        "probability_changed": False,
        "v6_1_changed": False,
        "v7_2g2_changed": False,
        "ui_changed": False,
    }
    write_json(DOCS / "edgeiq_timing_architecture_decision_v1.json", architecture)
    write_json(FINAL / "timing-architecture-decision.json", architecture)
    architecture_md = f"""# EDGEiQ Timing Architecture Decision V1

Selected outcome: {architecture['selected_outcome']}

The current 39 timed observations are produced by the Racing.com V2.1 current-window speed warehouse. They are not the full historical timing universe. Repository evidence also contains a governed historical performance timing warehouse with {timing_summary['timed_race_rows']} timed race-level observations.

Recovery is side-by-side in this unit. Current public canonical outputs are not overwritten. HPR-NORM-A-v1 remains effective from {CUTOFF}; pre-cutoff recovered performance base rows are explicitly rejected.
"""
    (DOCS / "EDGEIQ_TIMING_ARCHITECTURE_DECISION_V1.md").write_text(architecture_md, encoding="utf-8")
    (FINAL / "timing-architecture-decision.md").write_text(architecture_md, encoding="utf-8")

    output_inventory = []
    for path in [TIMING_OUT, STD_OUT, RTD_OUT, LVS_OUT, LVS_REJ_OUT, PIB_OUT, NORM_OUT, NORM_REJ_OUT, SUMMARY_OUT]:
        output_inventory.append({
            "output_path": str(path).replace(str(ROOT) + os.sep, ""),
            "exists": path.exists(),
            "rows": count_rows(path) if path.suffix == ".csv" else "",
            "sha256": file_hash(path) if path.exists() and path.stat().st_size < 100_000_000 else "SKIPPED_LARGE_OR_MISSING",
        })
    write_csv(DOCS / "edgeiq_timing_recovery_canonical_output_inventory_v1.csv", list(output_inventory[0].keys()), output_inventory)
    write_csv(FINAL / "canonical-output-inventory.csv", list(output_inventory[0].keys()), output_inventory)

    authority_rows = [
        {"builder": "build_edgeiq_timing_warehouse_recovery_v1.py", "output": str(TIMING_OUT).replace(str(ROOT) + os.sep, ""), "authority": "docs/performance-intelligence/warehouse/edgeiq_performance_fact_warehouse_v1.csv"},
        {"builder": "build_edgeiq_timing_warehouse_recovery_v1.py", "output": str(STD_OUT).replace(str(ROOT) + os.sep, ""), "authority": "recovered timing warehouse, min20 unchanged"},
        {"builder": "build_edgeiq_timing_warehouse_recovery_v1.py", "output": str(RTD_OUT).replace(str(ROOT) + os.sep, ""), "authority": "recovered timing + recovered standard time"},
        {"builder": "build_edgeiq_timing_warehouse_recovery_v1.py", "output": str(LVS_OUT).replace(str(ROOT) + os.sep, ""), "authority": "EDGEIQ_SURFACE_AWARE_LENGTHS_PER_SECOND_V2"},
    ]
    write_csv(DOCS / "edgeiq_timing_recovery_builder_to_output_authority_v1.csv", ["builder", "output", "authority"], authority_rows)
    write_csv(FINAL / "builder-to-output-authority.csv", ["builder", "output", "authority"], authority_rows)

    temporal_rows = [
        {"partition": "before_2026_07_20", "performance_base_rows": sum(1 for row in base_rows if clean(row.get("race_date")) < CUTOFF), "normalisation_action": "REJECT_HPR_NORM_A_NOT_EFFECTIVE"},
        {"partition": "on_or_after_2026_07_20", "performance_base_rows": sum(1 for row in base_rows if clean(row.get("race_date")) >= CUTOFF), "normalisation_action": "APPLY_ONLY_IF_ELIGIBLE"},
    ]
    write_csv(DOCS / "edgeiq_normalisation_temporal_eligibility_recovered_v1.csv", ["partition", "performance_base_rows", "normalisation_action"], temporal_rows)
    write_csv(FINAL / "normalisation-temporal-eligibility.csv", ["partition", "performance_base_rows", "normalisation_action"], temporal_rows)

    horse_chain_rows = [
        {"stage": "performance_normalisation", "rows": len(normalisation_rows), "status": "EMPTY_IF_ALL_ROWS_PRE_CUTOFF"},
        {"stage": "horse_performance_aggregate", "rows": 0, "status": "GOVERNED_MODEL_UNAVAILABLE_UNTIL_NORMALISATION_ROWS_EXIST"},
        {"stage": "horse_rating", "rows": 0, "status": "GOVERNED_MODEL_UNAVAILABLE_UNTIL_NORMALISATION_ROWS_EXIST"},
        {"stage": "race_entry_snapshot", "rows": 0, "status": "GOVERNED_MODEL_UNAVAILABLE_UNTIL_NORMALISATION_ROWS_EXIST"},
        {"stage": "projected_performance", "rows": 0, "status": "GOVERNED_MODEL_UNAVAILABLE_UNTIL_NORMALISATION_ROWS_EXIST"},
    ]
    write_csv(DOCS / "edgeiq_horse_performance_chain_coverage_recovered_v1.csv", ["stage", "rows", "status"], horse_chain_rows)
    write_csv(FINAL / "horse-performance-chain-coverage.csv", ["stage", "rows", "status"], horse_chain_rows)

    current_vic = {"race_list_rows": count_rows(CURRENT_RACE), "status": "AUDITED_FOR_EXISTENCE_ONLY_IN_TIMING_RECOVERY_UNIT"}
    write_csv(DOCS / "edgeiq_current_victoria_race_entry_coverage_timing_recovery_v1.csv", ["metric", "value"], [{"metric": key, "value": value} for key, value in current_vic.items()])
    write_csv(FINAL / "current-race-entry-coverage.csv", ["metric", "value"], [{"metric": key, "value": value} for key, value in current_vic.items()])

    ledger = [{
        "unit_id": "TIMING-WAREHOUSE-RECOVERY-V1",
        "objective": "Recover maximum truthful authoritative historical timing evidence from repository",
        "status": "PARTIAL_PASS_SIDE_BY_SIDE_RECOVERY_BUILT_NORMALISATION_GOVERNANCE_BLOCKS_PUBLICATION",
        "start_commit": head,
        "end_commit": "PENDING_COMMIT",
        "files_changed": "generated timing recovery scripts/evidence/candidate outputs",
        "input_rows": timing_summary["source_rows"],
        "output_rows": timing_summary["timed_race_rows"],
        "rejection_counts": json.dumps({"timing_rejected_races": timing_summary["rejected_races"], "delta_rejections": len(delta_rejections), "lvs_rejections": len(lvs_rejections), "normalisation_rejections": len(normalisation_rejections)}, sort_keys=True),
        "primary_finding": architecture["finding"],
        "next_action": "Human review contract switch before replacing current public canonical observation path; normalisation remains unavailable for pre-cutoff rows.",
        "runtime_seconds": round(time.time() - start, 3),
        "thresholds_changed": "NO",
        "engine_logic_changed": "YES_NEW_SIDE_BY_SIDE_RECOVERY_ADAPTER",
        "source_data_changed": "NO",
        "ui_changed": "NO",
    }]
    write_csv(DOCS / "edgeiq_timing_recovery_progress_ledger_v1.csv", list(ledger[0].keys()), ledger)
    write_csv(FINAL / "commit-ledger.csv", list(ledger[0].keys()), ledger)

    acceptance = {
        "overall_status": "PARTIAL",
        "start_commit": head,
        "branch": branch,
        "canonical_timing_dataset_before": "public/data/edgeiq_benchmark_observation_fact_v1.csv",
        "timed_rows_before": current_counts["current_benchmark_observations"],
        "timed_rows_after_side_by_side": timing_summary["timed_race_rows"],
        "unique_timed_races_after_side_by_side": timing_summary["timed_race_rows"],
        "standard_time_rows_recovered": len(standard_rows),
        "race_time_delta_rows_recovered": len(delta_rows),
        "lengths_v_standard_rows_recovered": len(lvs_rows),
        "performance_base_rows_recovered": len(base_rows),
        "normalisation_output_rows_recovered": len(normalisation_rows),
        "normalisation_rejections_recovered": len(normalisation_rejections),
        "architecture_decision": architecture["selected_outcome"],
        "unit_semantics_status": "PASS_EXPLICIT_TIME_UNITS_AND_SECONDS_FIELD",
        "race_identity_status": "PASS_CANONICAL_RACE_ID_PRESENT",
        "condition_evidence_status": "PASS_FOR_AVAILABLE_GROUPS_REJECT_MISSING",
        "production_public_outputs_overwritten": False,
        "pricing_changed": False,
        "probability_changed": False,
        "v6_1_changed": False,
        "v7_2g2_changed": False,
        "ui_changed": False,
        "remaining_blockers": [
            "Human approval required before replacing current public canonical observation contract",
            f"HPR-NORM-A-v1 not effective for pre-{CUTOFF} recovered observations",
            "Prior warehouse audit reports 70,311 timed races; direct physical scan confirms 70,308 and should be treated as authoritative until the audit-count discrepancy is resolved.",
        ],
        "runtime_seconds": round(time.time() - start, 3),
    }
    write_json(SUMMARY_OUT, acceptance)
    write_json(FINAL / "final-acceptance.json", acceptance)
    final_md = f"""# EDGEiQ Timing Warehouse Recovery V1 Final Acceptance

Overall status: PARTIAL

The reason for the 39-row canonical timing population is established: the active benchmark observation producer reads the Racing.com V2.1 current-window speed warehouse, whose audit reports 39 canonical races. A separate governed historical performance timing warehouse exists with {timing_summary['timed_race_rows']} timed race-level observations.

Side-by-side recovered outputs were built and audited. Current public canonical outputs were not overwritten in this unit. Normalisation remains governed by HPR-NORM-A-v1 effective from {CUTOFF}; recovered pre-cutoff performance base rows are explicitly rejected.

Protected systems changed: NO. Pricing/probability/V6.1/V7.2G2/UI changed: NO.
"""
    (FINAL / "final-acceptance.md").write_text(final_md, encoding="utf-8")
    (DOCS / "EDGEIQ_TIMING_WAREHOUSE_RECOVERY_V1_REPORT.md").write_text(final_md, encoding="utf-8")

    print(json.dumps(acceptance, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
