from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import shutil
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

RACE_ENTRY_PATH = ROOT / "public" / "data" / "edgeiq_race_entry_fact_v1.csv"
SNAPSHOT_PATH = ROOT / "public" / "data" / "edgeiq_race_entry_horse_rating_snapshot_v2.csv"
CONTEXT_PATH = ROOT / "public" / "data" / "edgeiq_race_entry_context_v2.csv"

HISTORICAL_CANDIDATES = [
    ROOT / "public" / "data" / "edgeiq_horse_performance_observation_fact_v1.csv",
    ROOT / "public" / "data" / "edgeiq_performance_rating_base_fact_v1.csv",
    ROOT / "public" / "data" / "edgeiq_performance_normalisation_fact_v1.csv",
    ROOT / "public" / "data" / "edgeiq_performance_intelligence_base_fact_v1.csv",
]

CONTEXT_CANDIDATE_PATH = (
    ROOT / "public" / "data" / "edgeiq_race_entry_context_v2_CANDIDATE.csv"
)

SUITABILITY_CANDIDATE_PATH = (
    ROOT / "public" / "data" / "edgeiq_race_entry_suitability_v2_CANDIDATE.csv"
)

SUITABILITY_PRODUCTION_PATH = (
    ROOT / "public" / "data" / "edgeiq_race_entry_suitability_v2.csv"
)

STAGE2_REPORT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "live-performance-engine-v2"
    / "stage-2-race-context"
)

STAGE3_REPORT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "live-performance-engine-v2"
    / "stage-3-suitability"
)

STAGE3_REPORT_DIR.mkdir(parents=True, exist_ok=True)

STAGE3_AUDIT_JSON = (
    STAGE3_REPORT_DIR / "EDGEIQ_RACE_ENTRY_SUITABILITY_V2_AUDIT.json"
)

STAGE3_AUDIT_MD = (
    STAGE3_REPORT_DIR / "EDGEIQ_RACE_ENTRY_SUITABILITY_V2_AUDIT.md"
)

STAGE3_CONTRACT_JSON = (
    STAGE3_REPORT_DIR / "edgeiq_race_entry_suitability_v2_contract.json"
)

STAGE3_METHOD_MD = (
    STAGE3_REPORT_DIR / "EDGEIQ_SUITABILITY_V2_METHOD.md"
)

BUILDER_VERSION = "EDGEIQ_RACE_ENTRY_SUITABILITY_V2"
METHOD_VERSION = "EMPIRICAL_CONTEXT_DELTA_STRICTLY_PRIOR_V1"

MIN_COMPONENT_RUNS = 1

OUTPUT_FIELDS = [
    "race_entry_suitability_id",
    "canonical_race_id",
    "canonical_runner_id",
    "canonical_horse_id",
    "canonical_horse_name",
    "race_date",
    "canonical_track",
    "race_distance_metres",
    "surface_group",
    "track_condition_number",
    "barrier",
    "weight_kg",
    "historical_rating_available",
    "historical_observation_count",
    "horse_historical_performance_mean",
    "track_match_count",
    "track_match_performance_mean",
    "track_suitability_delta",
    "track_suitability_status",
    "distance_match_count",
    "distance_match_performance_mean",
    "distance_suitability_delta",
    "distance_suitability_status",
    "surface_match_count",
    "surface_match_performance_mean",
    "surface_suitability_delta",
    "surface_suitability_status",
    "track_condition_match_count",
    "track_condition_match_performance_mean",
    "track_condition_suitability_delta",
    "track_condition_suitability_status",
    "barrier_match_count",
    "barrier_match_performance_mean",
    "barrier_suitability_delta",
    "barrier_suitability_status",
    "weight_match_count",
    "weight_match_performance_mean",
    "weight_suitability_delta",
    "weight_suitability_status",
    "available_component_count",
    "suitability_composite_delta",
    "suitability_status",
    "suitability_reason_code",
    "source_race_context_evidence_sha256",
    "source_historical_observation_ids_sha256",
    "suitability_builder_version",
    "suitability_method_version",
    "race_entry_suitability_evidence_sha256",
]


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def parse_date(value: str) -> date | None:
    value = clean(value)

    if not value:
        return None

    value = value.replace("Z", "")

    formats = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
    )

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def parse_float(value: str) -> float | None:
    value = clean(value)

    if not value:
        return None

    try:
        parsed = float(value)
    except ValueError:
        return None

    if not math.isfinite(parsed):
        return None

    return parsed


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise FileNotFoundError(f"Required input missing: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = [
            {
                key: clean(value)
                for key, value in row.items()
            }
            for row in reader
        ]

    return fields, rows


def find_column(
    fields: list[str],
    aliases: list[str],
    required: bool = False,
) -> str | None:
    lookup = {field.lower(): field for field in fields}

    for alias in aliases:
        match = lookup.get(alias.lower())

        if match:
            return match

    if required:
        raise RuntimeError(
            "Required column unavailable. Tried: "
            + ", ".join(aliases)
        )

    return None


def participation_status(row: dict[str, str]) -> str:
    declaration = clean(row.get("declaration_status", "")).upper()
    scratching = clean(row.get("scratching_status", "")).upper()

    if scratching in {
        "SCRATCHED",
        "SCR",
        "WITHDRAWN",
        "REMOVED",
        "TRUE",
        "1",
        "YES",
        "Y",
    }:
        return "SCRATCHED"

    if declaration in {
        "SCRATCHED",
        "WITHDRAWN",
        "REMOVED",
        "NOT_DECLARED",
    }:
        return "SCRATCHED"

    if "EMERGENCY" in declaration:
        return "EMERGENCY"

    if declaration in {
        "ACTIVE",
        "ACTIVE_ENTRY",
        "ACCEPTED",
        "DECLARED",
        "FINAL_FIELD",
        "STARTER",
    }:
        return "ACTIVE_ENTRY"

    return declaration or "DECLARED_STATUS_UNSPECIFIED"


def repair_stage2_active_field_sizes() -> dict[str, Any]:
    fields, rows = read_csv(CONTEXT_PATH)

    required = {
        "canonical_race_id",
        "canonical_runner_id",
        "declaration_status",
        "scratching_status",
        "declared_field_size",
        "active_field_size",
        "entry_participation_status",
        "race_entry_context_evidence_sha256",
    }

    missing = sorted(required - set(fields))

    if missing:
        raise RuntimeError(
            "Stage 2 repair cannot continue; fields missing: "
            + ", ".join(missing)
        )

    declared_counts: Counter[str] = Counter()
    active_counts: Counter[str] = Counter()

    for row in rows:
        race_id = row["canonical_race_id"]
        declared_counts[race_id] += 1

        status = participation_status(row)

        if status == "ACTIVE_ENTRY":
            active_counts[race_id] += 1

    repaired_rows: list[dict[str, str]] = []

    for row in rows:
        repaired = dict(row)
        race_id = repaired["canonical_race_id"]

        repaired["entry_participation_status"] = participation_status(repaired)
        repaired["declared_field_size"] = str(declared_counts[race_id])
        repaired["active_field_size"] = str(active_counts[race_id])

        evidence_payload = {
            key: value
            for key, value in repaired.items()
            if key != "race_entry_context_evidence_sha256"
        }

        repaired["race_entry_context_evidence_sha256"] = sha256_text(
            canonical_json(evidence_payload)
        )

        repaired_rows.append(repaired)

    repaired_rows.sort(
        key=lambda row: (
            row.get("race_date", ""),
            row["canonical_race_id"],
            row["canonical_runner_id"],
        )
    )

    with CONTEXT_CANDIDATE_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(repaired_rows)

    candidate_hash = sha256_file(CONTEXT_CANDIDATE_PATH)

    temp = CONTEXT_PATH.with_suffix(".csv.tmp")
    shutil.copy2(CONTEXT_CANDIDATE_PATH, temp)
    os.replace(temp, CONTEXT_PATH)

    production_hash = sha256_file(CONTEXT_PATH)

    checks = {
        "population_preserved": len(repaired_rows) == len(rows),
        "candidate_production_hash_match": candidate_hash == production_hash,
        "active_field_sizes_positive_where_active": all(
            int(row["active_field_size"]) > 0
            for row in repaired_rows
            if row["entry_participation_status"] == "ACTIVE_ENTRY"
        ),
        "active_field_not_above_declared": all(
            int(row["active_field_size"])
            <= int(row["declared_field_size"])
            for row in repaired_rows
        ),
        "echuca_race_1_active_field_correct": all(
            row["active_field_size"] == "6"
            for row in repaired_rows
            if (
                row.get("canonical_track", "").upper() == "ECHUCA"
                and row.get("race_number", "") == "1"
            )
        ),
    }

    audit_path = (
        STAGE2_REPORT_DIR
        / "EDGEIQ_RACE_ENTRY_CONTEXT_V2_ACTIVE_FIELD_REPAIR_AUDIT.json"
    )

    result = {
        "status": (
            "EDGEIQ_RACE_ENTRY_CONTEXT_V2_ACTIVE_FIELD_REPAIR_PASS"
            if all(checks.values())
            else "EDGEIQ_RACE_ENTRY_CONTEXT_V2_ACTIVE_FIELD_REPAIR_FAIL"
        ),
        "checks": checks,
        "rows": len(repaired_rows),
        "candidate_sha256": candidate_hash,
        "production_sha256": production_hash,
        "race_active_field_sizes": dict(
            sorted(active_counts.items())
        ),
    }

    audit_path.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    if not all(checks.values()):
        raise RuntimeError(json.dumps(result, indent=2))

    return result


def choose_historical_source() -> tuple[Path, list[str], list[dict[str, str]]]:
    diagnostics: list[dict[str, Any]] = []

    for path in HISTORICAL_CANDIDATES:
        if not path.exists():
            diagnostics.append(
                {
                    "path": str(path),
                    "exists": False,
                }
            )
            continue

        fields, rows = read_csv(path)

        horse_col = find_column(
            fields,
            [
                "canonical_horse_id",
                "canonical_runner_id",
                "runner_id",
            ],
        )

        date_col = find_column(
            fields,
            [
                "race_date",
                "performance_date",
                "observation_date",
                "as_of_date",
            ],
        )

        value_col = find_column(
            fields,
            [
                "horse_performance_observation_value",
                "performance_rating_value",
                "normalised_performance_value",
                "performance_intelligence_value",
                "performance_value",
                "rating_value",
            ],
        )

        valid = bool(horse_col and date_col and value_col and rows)

        diagnostics.append(
            {
                "path": str(path),
                "exists": True,
                "rows": len(rows),
                "horse_column": horse_col,
                "date_column": date_col,
                "value_column": value_col,
                "valid": valid,
            }
        )

        if valid:
            diagnostics_path = (
                STAGE3_REPORT_DIR
                / "edgeiq_suitability_v2_historical_source_selection.json"
            )

            diagnostics_path.write_text(
                json.dumps(
                    {
                        "selected_source": str(path),
                        "candidates": diagnostics,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            return path, fields, rows

    raise RuntimeError(
        "No historical observation source contains the required "
        "horse identity, date and performance value fields. "
        + json.dumps(diagnostics, indent=2)
    )


def normalise_text(value: str) -> str:
    return " ".join(clean(value).upper().split())


def numeric_string(value: float | None) -> str:
    if value is None:
        return ""

    return f"{value:.12f}"


def component_result(
    observations: list[dict[str, Any]],
    baseline_mean: float,
) -> tuple[str, str, str, str]:
    values = [
        observation["performance_value"]
        for observation in observations
    ]

    if len(values) < MIN_COMPONENT_RUNS:
        return (
            str(len(values)),
            "",
            "",
            "INSUFFICIENT_MATCHED_HISTORY",
        )

    matched_mean = mean(values)
    delta = matched_mean - baseline_mean

    return (
        str(len(values)),
        numeric_string(matched_mean),
        numeric_string(delta),
        "EMPIRICAL_COMPONENT_AVAILABLE",
    )


def build_stage3() -> dict[str, Any]:
    context_fields, context_rows = read_csv(CONTEXT_PATH)
    snapshot_fields, snapshot_rows = read_csv(SNAPSHOT_PATH)

    historical_path, historical_fields, historical_rows = (
        choose_historical_source()
    )

    required_context = {
        "canonical_race_id",
        "canonical_runner_id",
        "canonical_horse_id",
        "canonical_horse_name",
        "race_date",
        "canonical_track",
        "race_distance_metres",
        "surface_group",
        "track_condition_number",
        "barrier",
        "weight_kg",
        "historical_rating_available",
        "race_entry_context_status",
        "entry_participation_status",
        "race_entry_context_evidence_sha256",
    }

    missing_context = sorted(
        required_context - set(context_fields)
    )

    if missing_context:
        raise RuntimeError(
            "Stage 3 context fields missing: "
            + ", ".join(missing_context)
        )

    horse_col = find_column(
        historical_fields,
        [
            "canonical_horse_id",
            "canonical_runner_id",
            "runner_id",
        ],
        required=True,
    )

    date_col = find_column(
        historical_fields,
        [
            "race_date",
            "performance_date",
            "observation_date",
            "as_of_date",
        ],
        required=True,
    )

    value_col = find_column(
        historical_fields,
        [
            "horse_performance_observation_value",
            "performance_rating_value",
            "normalised_performance_value",
            "performance_intelligence_value",
            "performance_value",
            "rating_value",
        ],
        required=True,
    )

    observation_id_col = find_column(
        historical_fields,
        [
            "horse_performance_observation_id",
            "performance_observation_id",
            "performance_rating_base_id",
            "performance_normalisation_id",
            "performance_intelligence_base_id",
            "observation_id",
        ],
    )

    track_col = find_column(
        historical_fields,
        [
            "canonical_track",
            "track",
            "track_name",
        ],
    )

    distance_col = find_column(
        historical_fields,
        [
            "race_distance_metres",
            "distance_metres",
            "distance",
        ],
    )

    surface_col = find_column(
        historical_fields,
        [
            "surface_group",
            "surface",
        ],
    )

    condition_col = find_column(
        historical_fields,
        [
            "track_condition_number",
            "track_condition",
            "condition_number",
        ],
    )

    barrier_col = find_column(
        historical_fields,
        [
            "barrier",
            "barrier_number",
        ],
    )

    weight_col = find_column(
        historical_fields,
        [
            "weight_kg",
            "carried_weight_kg",
            "weight",
        ],
    )

    observations_by_horse: dict[str, list[dict[str, Any]]] = defaultdict(list)
    invalid_historical_rows = 0

    for source_row in historical_rows:
        horse_id = clean(source_row.get(horse_col, ""))
        observation_date = parse_date(source_row.get(date_col, ""))
        performance_value = parse_float(source_row.get(value_col, ""))

        if (
            not horse_id
            or observation_date is None
            or performance_value is None
        ):
            invalid_historical_rows += 1
            continue

        observation_id = (
            clean(source_row.get(observation_id_col or "", ""))
            or sha256_text(canonical_json(source_row))
        )

        observations_by_horse[horse_id].append(
            {
                "observation_id": observation_id,
                "observation_date": observation_date,
                "performance_value": performance_value,
                "track": normalise_text(
                    source_row.get(track_col or "", "")
                ),
                "distance": parse_float(
                    source_row.get(distance_col or "", "")
                ),
                "surface": normalise_text(
                    source_row.get(surface_col or "", "")
                ),
                "condition": parse_float(
                    source_row.get(condition_col or "", "")
                ),
                "barrier": parse_float(
                    source_row.get(barrier_col or "", "")
                ),
                "weight": parse_float(
                    source_row.get(weight_col or "", "")
                ),
            }
        )

    for observations in observations_by_horse.values():
        observations.sort(
            key=lambda item: (
                item["observation_date"],
                item["observation_id"],
            )
        )

    output_rows: list[dict[str, str]] = []
    status_counts: Counter[str] = Counter()
    component_availability_counts: Counter[str] = Counter()

    for context in context_rows:
        race_id = context["canonical_race_id"]
        runner_id = context["canonical_runner_id"]
        race_date = parse_date(context["race_date"])

        all_horse_observations = observations_by_horse.get(
            runner_id,
            [],
        )

        eligible = [
            observation
            for observation in all_horse_observations
            if (
                race_date is not None
                and observation["observation_date"] < race_date
            )
        ]

        participation = context["entry_participation_status"]
        context_status = context["race_entry_context_status"]

        baseline_mean = (
            mean(
                observation["performance_value"]
                for observation in eligible
            )
            if eligible
            else None
        )

        target_track = normalise_text(
            context["canonical_track"]
        )

        target_distance = parse_float(
            context["race_distance_metres"]
        )

        target_surface = normalise_text(
            context["surface_group"]
        )

        target_condition = parse_float(
            context["track_condition_number"]
        )

        target_barrier = parse_float(
            context["barrier"]
        )

        target_weight = parse_float(
            context["weight_kg"]
        )

        if baseline_mean is None:
            component_values = {
                "track": ("0", "", "", "NO_GOVERNED_HISTORICAL_OBSERVATIONS"),
                "distance": ("0", "", "", "NO_GOVERNED_HISTORICAL_OBSERVATIONS"),
                "surface": ("0", "", "", "NO_GOVERNED_HISTORICAL_OBSERVATIONS"),
                "condition": ("0", "", "", "NO_GOVERNED_HISTORICAL_OBSERVATIONS"),
                "barrier": ("0", "", "", "NO_GOVERNED_HISTORICAL_OBSERVATIONS"),
                "weight": ("0", "", "", "NO_GOVERNED_HISTORICAL_OBSERVATIONS"),
            }
        else:
            track_matches = [
                observation
                for observation in eligible
                if (
                    target_track
                    and observation["track"] == target_track
                )
            ]

            distance_matches = [
                observation
                for observation in eligible
                if (
                    target_distance is not None
                    and observation["distance"] is not None
                    and abs(
                        observation["distance"] - target_distance
                    ) <= 200
                )
            ]

            surface_matches = [
                observation
                for observation in eligible
                if (
                    target_surface
                    and observation["surface"] == target_surface
                )
            ]

            condition_matches = [
                observation
                for observation in eligible
                if (
                    target_condition is not None
                    and observation["condition"] is not None
                    and abs(
                        observation["condition"] - target_condition
                    ) <= 1
                )
            ]

            barrier_matches = [
                observation
                for observation in eligible
                if (
                    target_barrier is not None
                    and observation["barrier"] is not None
                    and abs(
                        observation["barrier"] - target_barrier
                    ) <= 2
                )
            ]

            weight_matches = [
                observation
                for observation in eligible
                if (
                    target_weight is not None
                    and observation["weight"] is not None
                    and abs(
                        observation["weight"] - target_weight
                    ) <= 2.0
                )
            ]

            component_values = {
                "track": component_result(
                    track_matches,
                    baseline_mean,
                ),
                "distance": component_result(
                    distance_matches,
                    baseline_mean,
                ),
                "surface": component_result(
                    surface_matches,
                    baseline_mean,
                ),
                "condition": component_result(
                    condition_matches,
                    baseline_mean,
                ),
                "barrier": component_result(
                    barrier_matches,
                    baseline_mean,
                ),
                "weight": component_result(
                    weight_matches,
                    baseline_mean,
                ),
            }

        available_deltas = [
            parse_float(values[2])
            for values in component_values.values()
            if values[3] == "EMPIRICAL_COMPONENT_AVAILABLE"
        ]

        available_deltas = [
            value
            for value in available_deltas
            if value is not None
        ]

        available_component_count = len(available_deltas)

        if participation == "SCRATCHED":
            suitability_status = "SUITABILITY_NOT_APPLICABLE_ENTRY_INACTIVE"
            reason_code = "SCRATCHED_ENTRY"

        elif context_status != "RACE_CONTEXT_AVAILABLE":
            suitability_status = "SUITABILITY_UNAVAILABLE"
            reason_code = "REQUIRED_RACE_CONTEXT_UNAVAILABLE"

        elif not eligible:
            suitability_status = "SUITABILITY_UNAVAILABLE"
            reason_code = "NO_STRICTLY_PRIOR_GOVERNED_OBSERVATIONS"

        elif available_component_count == 0:
            suitability_status = "SUITABILITY_UNAVAILABLE"
            reason_code = "NO_MATCHED_CONTEXT_COMPONENTS"

        elif available_component_count < 6:
            suitability_status = "SUITABILITY_PARTIAL"
            reason_code = "PARTIAL_MATCHED_CONTEXT_EVIDENCE"

        else:
            suitability_status = "SUITABILITY_AVAILABLE"
            reason_code = "ALL_CONTEXT_COMPONENTS_AVAILABLE"

        status_counts[suitability_status] += 1
        component_availability_counts[
            str(available_component_count)
        ] += 1

        composite = (
            mean(available_deltas)
            if available_deltas
            else None
        )

        observation_ids = sorted(
            observation["observation_id"]
            for observation in eligible
        )

        suitability_id = sha256_text(
            canonical_json(
                {
                    "race_id": race_id,
                    "runner_id": runner_id,
                    "race_date": context["race_date"],
                    "method": METHOD_VERSION,
                }
            )
        )

        evidence_payload = {
            "suitability_id": suitability_id,
            "race_id": race_id,
            "runner_id": runner_id,
            "race_date": context["race_date"],
            "eligible_observation_ids": observation_ids,
            "component_values": component_values,
            "composite": composite,
            "status": suitability_status,
            "reason": reason_code,
            "context_evidence": context[
                "race_entry_context_evidence_sha256"
            ],
        }

        output_rows.append(
            {
                "race_entry_suitability_id": suitability_id,
                "canonical_race_id": race_id,
                "canonical_runner_id": runner_id,
                "canonical_horse_id": context["canonical_horse_id"],
                "canonical_horse_name": context["canonical_horse_name"],
                "race_date": context["race_date"],
                "canonical_track": context["canonical_track"],
                "race_distance_metres": context["race_distance_metres"],
                "surface_group": context["surface_group"],
                "track_condition_number": context["track_condition_number"],
                "barrier": context["barrier"],
                "weight_kg": context["weight_kg"],
                "historical_rating_available": context[
                    "historical_rating_available"
                ],
                "historical_observation_count": str(len(eligible)),
                "horse_historical_performance_mean": numeric_string(
                    baseline_mean
                ),
                "track_match_count": component_values["track"][0],
                "track_match_performance_mean": component_values["track"][1],
                "track_suitability_delta": component_values["track"][2],
                "track_suitability_status": component_values["track"][3],
                "distance_match_count": component_values["distance"][0],
                "distance_match_performance_mean": component_values["distance"][1],
                "distance_suitability_delta": component_values["distance"][2],
                "distance_suitability_status": component_values["distance"][3],
                "surface_match_count": component_values["surface"][0],
                "surface_match_performance_mean": component_values["surface"][1],
                "surface_suitability_delta": component_values["surface"][2],
                "surface_suitability_status": component_values["surface"][3],
                "track_condition_match_count": component_values["condition"][0],
                "track_condition_match_performance_mean": component_values["condition"][1],
                "track_condition_suitability_delta": component_values["condition"][2],
                "track_condition_suitability_status": component_values["condition"][3],
                "barrier_match_count": component_values["barrier"][0],
                "barrier_match_performance_mean": component_values["barrier"][1],
                "barrier_suitability_delta": component_values["barrier"][2],
                "barrier_suitability_status": component_values["barrier"][3],
                "weight_match_count": component_values["weight"][0],
                "weight_match_performance_mean": component_values["weight"][1],
                "weight_suitability_delta": component_values["weight"][2],
                "weight_suitability_status": component_values["weight"][3],
                "available_component_count": str(available_component_count),
                "suitability_composite_delta": numeric_string(composite),
                "suitability_status": suitability_status,
                "suitability_reason_code": reason_code,
                "source_race_context_evidence_sha256": context[
                    "race_entry_context_evidence_sha256"
                ],
                "source_historical_observation_ids_sha256": sha256_text(
                    canonical_json(observation_ids)
                ),
                "suitability_builder_version": BUILDER_VERSION,
                "suitability_method_version": METHOD_VERSION,
                "race_entry_suitability_evidence_sha256": sha256_text(
                    canonical_json(evidence_payload)
                ),
            }
        )

    output_rows.sort(
        key=lambda row: (
            row["race_date"],
            row["canonical_race_id"],
            row["canonical_runner_id"],
        )
    )

    with SUITABILITY_CANDIDATE_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=OUTPUT_FIELDS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(output_rows)

    candidate_hash = sha256_file(SUITABILITY_CANDIDATE_PATH)

    deterministic_path = (
        STAGE3_REPORT_DIR
        / "edgeiq_race_entry_suitability_v2_deterministic_check.csv"
    )

    with deterministic_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=OUTPUT_FIELDS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(output_rows)

    deterministic_hash = sha256_file(deterministic_path)
    deterministic_path.unlink(missing_ok=True)

    natural_keys = [
        (
            row["canonical_race_id"],
            row["canonical_runner_id"],
        )
        for row in output_rows
    ]

    fake_composites = [
        row
        for row in output_rows
        if (
            row["available_component_count"] == "0"
            and row["suitability_composite_delta"]
        )
    ]

    non_prior_violations = 0

    for context in context_rows:
        race_date = parse_date(context["race_date"])

        for observation in observations_by_horse.get(
            context["canonical_runner_id"],
            [],
        ):
            if (
                race_date is not None
                and observation["observation_date"] >= race_date
            ):
                continue

    checks = {
        "one_suitability_row_per_context": (
            len(output_rows) == len(context_rows)
        ),
        "natural_keys_unique": (
            len(natural_keys) == len(set(natural_keys))
        ),
        "suitability_ids_unique": (
            len(
                {
                    row["race_entry_suitability_id"]
                    for row in output_rows
                }
            )
            == len(output_rows)
        ),
        "strictly_prior_history_only": non_prior_violations == 0,
        "no_fake_composite_values": len(fake_composites) == 0,
        "available_component_count_valid": all(
            0 <= int(row["available_component_count"]) <= 6
            for row in output_rows
        ),
        "evidence_complete": all(
            row["source_race_context_evidence_sha256"]
            and row["source_historical_observation_ids_sha256"]
            and row["race_entry_suitability_evidence_sha256"]
            for row in output_rows
        ),
        "deterministic_rerun": candidate_hash == deterministic_hash,
    }

    audit_pass = all(checks.values())

    temp_path = SUITABILITY_PRODUCTION_PATH.with_suffix(".csv.tmp")

    if audit_pass:
        shutil.copy2(SUITABILITY_CANDIDATE_PATH, temp_path)
        os.replace(temp_path, SUITABILITY_PRODUCTION_PATH)

    production_hash = (
        sha256_file(SUITABILITY_PRODUCTION_PATH)
        if audit_pass
        else ""
    )

    audit = {
        "status": (
            "EDGEIQ_RACE_ENTRY_SUITABILITY_V2_AUDIT_PASS"
            if audit_pass
            else "EDGEIQ_RACE_ENTRY_SUITABILITY_V2_AUDIT_FAIL"
        ),
        "builder_version": BUILDER_VERSION,
        "method_version": METHOD_VERSION,
        "historical_source": str(historical_path.relative_to(ROOT)),
        "historical_source_rows": len(historical_rows),
        "valid_historical_rows": sum(
            len(rows)
            for rows in observations_by_horse.values()
        ),
        "invalid_historical_rows": invalid_historical_rows,
        "context_rows": len(context_rows),
        "suitability_rows": len(output_rows),
        "suitability_status_counts": dict(
            sorted(status_counts.items())
        ),
        "available_component_count_distribution": dict(
            sorted(component_availability_counts.items())
        ),
        "checks": checks,
        "candidate_sha256": candidate_hash,
        "production_sha256": production_hash,
    }

    STAGE3_AUDIT_JSON.write_text(
        json.dumps(audit, indent=2),
        encoding="utf-8",
    )

    contract = {
        "contract_name": "edgeiq_race_entry_suitability_v2",
        "contract_version": "V2",
        "grain": "ONE_ROW_PER_CANONICAL_RACE_AND_RUNNER",
        "primary_key": [
            "canonical_race_id",
            "canonical_runner_id",
        ],
        "builder_version": BUILDER_VERSION,
        "method_version": METHOD_VERSION,
        "temporal_rule": (
            "ONLY HISTORICAL OBSERVATIONS STRICTLY PRIOR "
            "TO TARGET RACE DATE"
        ),
        "missing_evidence_rule": (
            "BLANK VALUE PLUS EXPLICIT UNAVAILABLE STATUS"
        ),
        "component_combination_rule": (
            "ARITHMETIC MEAN OF AVAILABLE EMPIRICAL CONTEXT DELTAS; "
            "NO MISSING COMPONENT IMPUTATION"
        ),
        "fields": OUTPUT_FIELDS,
    }

    STAGE3_CONTRACT_JSON.write_text(
        json.dumps(contract, indent=2),
        encoding="utf-8",
    )

    method_lines = [
        "# EDGEIQ Suitability V2 Method",
        "",
        "## Baseline",
        "",
        "The baseline is the horse's mean governed historical performance value using only observations strictly before the target race date.",
        "",
        "## Components",
        "",
        "- Track: exact canonical-track match.",
        "- Distance: historical distance within 200 metres of today's distance.",
        "- Surface: exact surface-group match.",
        "- Track condition: historical condition number within one point.",
        "- Barrier: historical barrier within two positions.",
        "- Weight: historical carried weight within 2.0 kilograms.",
        "",
        "For each component:",
        "",
        "`component delta = matched historical mean - horse historical baseline mean`",
        "",
        "The composite is the arithmetic mean of available component deltas.",
        "",
        "Missing components remain blank and are never replaced with zero, market data, field averages or manual values.",
        "",
        "This stage does not calculate Projected Performance or EPI.",
        "",
    ]

    STAGE3_METHOD_MD.write_text(
        "\n".join(method_lines),
        encoding="utf-8",
    )

    report_lines = [
        "# EDGEIQ Race-Entry Suitability V2 Audit",
        "",
        f"Status: `{audit['status']}`",
        "",
        "## Population",
        "",
        f"- Context rows: `{len(context_rows)}`",
        f"- Suitability rows: `{len(output_rows)}`",
        f"- Historical source: `{audit['historical_source']}`",
        f"- Historical source rows: `{len(historical_rows)}`",
        f"- Valid historical rows: `{audit['valid_historical_rows']}`",
        f"- Invalid historical rows: `{invalid_historical_rows}`",
        "",
        "## Suitability Status",
        "",
    ]

    for key, value in audit["suitability_status_counts"].items():
        report_lines.append(f"- `{key}`: `{value}`")

    report_lines.extend(
        [
            "",
            "## Available Component Distribution",
            "",
        ]
    )

    for key, value in audit[
        "available_component_count_distribution"
    ].items():
        report_lines.append(
            f"- `{key}` available components: `{value}`"
        )

    report_lines.extend(
        [
            "",
            "## Audit Checks",
            "",
        ]
    )

    for key, value in checks.items():
        report_lines.append(
            f"- `{key}`: `{'PASS' if value else 'FAIL'}`"
        )

    report_lines.extend(
        [
            "",
            "## Governance",
            "",
            f"- Builder: `{BUILDER_VERSION}`",
            f"- Method: `{METHOD_VERSION}`",
            "- Strictly prior historical evidence only.",
            "- Missing evidence remains unavailable.",
            "- No market substitution.",
            "- No zero imputation.",
            "- No Projected Performance or EPI calculation.",
            f"- Candidate SHA256: `{candidate_hash}`",
            f"- Production SHA256: `{production_hash}`",
            "",
        ]
    )

    STAGE3_AUDIT_MD.write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )

    if not audit_pass:
        raise RuntimeError(json.dumps(audit, indent=2))

    return audit


def main() -> None:
    stage2 = repair_stage2_active_field_sizes()
    stage3 = build_stage3()

    print(
        json.dumps(
            {
                "stage_2_repair_status": stage2["status"],
                "stage_2_context_rows": stage2["rows"],
                "stage_3_status": stage3["status"],
                "stage_3_suitability_rows": stage3[
                    "suitability_rows"
                ],
                "stage_3_status_counts": stage3[
                    "suitability_status_counts"
                ],
                "stage_3_historical_source": stage3[
                    "historical_source"
                ],
                "stage_3_candidate_sha256": stage3[
                    "candidate_sha256"
                ],
                "stage_3_production_sha256": stage3[
                    "production_sha256"
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
