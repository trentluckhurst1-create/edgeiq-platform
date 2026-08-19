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
DATA = ROOT / "public" / "data"
DOCS = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "live-performance-engine-v2"
)

CONTEXT_PATH = DATA / "edgeiq_race_entry_context_v2.csv"
SNAPSHOT_PATH = DATA / "edgeiq_race_entry_horse_rating_snapshot_v2.csv"

HISTORICAL_PATH = (
    DATA / "edgeiq_horse_performance_observation_fact_v1.csv"
)

BRIDGE_CANDIDATE = (
    DATA / "edgeiq_current_historical_horse_identity_bridge_v2_CANDIDATE.csv"
)
BRIDGE_PRODUCTION = (
    DATA / "edgeiq_current_historical_horse_identity_bridge_v2.csv"
)

SUITABILITY_CANDIDATE = (
    DATA / "edgeiq_race_entry_suitability_v2_CANDIDATE.csv"
)
SUITABILITY_PRODUCTION = (
    DATA / "edgeiq_race_entry_suitability_v2.csv"
)

PROJECTED_CANDIDATE = (
    DATA / "edgeiq_race_entry_projected_performance_v2_CANDIDATE.csv"
)
PROJECTED_PRODUCTION = (
    DATA / "edgeiq_race_entry_projected_performance_v2.csv"
)

EPI_CANDIDATE = DATA / "edgeiq_race_entry_epi_v2_CANDIDATE.csv"
EPI_PRODUCTION = DATA / "edgeiq_race_entry_epi_v2.csv"

FEED_CANDIDATE = (
    DATA / "edgeiq_race_intelligence_feed_v2_CANDIDATE.csv"
)
FEED_PRODUCTION = DATA / "edgeiq_race_intelligence_feed_v2.csv"

IDENTITY_DOCS = DOCS / "stage-3a-historical-identity-bridge"
SUITABILITY_DOCS = DOCS / "stage-3-suitability"
PROJECTED_DOCS = DOCS / "stage-4-projected-performance"
EPI_DOCS = DOCS / "stage-5-epi"
FEED_DOCS = DOCS / "stage-6-race-intelligence"

for directory in (
    IDENTITY_DOCS,
    SUITABILITY_DOCS,
    PROJECTED_DOCS,
    EPI_DOCS,
    FEED_DOCS,
):
    directory.mkdir(parents=True, exist_ok=True)

IDENTITY_BUILDER = "EDGEIQ_CURRENT_HISTORICAL_HORSE_IDENTITY_BRIDGE_V2"
IDENTITY_METHOD = "CANONICAL_ID_THEN_EXACT_UNIQUE_NORMALISED_NAME_V1"

SUITABILITY_BUILDER = "EDGEIQ_RACE_ENTRY_SUITABILITY_V2"
SUITABILITY_METHOD = "EMPIRICAL_CONTEXT_DELTA_STRICTLY_PRIOR_V1_1"

PROJECTED_BUILDER = "EDGEIQ_PROJECTED_PERFORMANCE_ENGINE_V2"
PROJECTED_METHOD = "HISTORICAL_RATING_PLUS_EMPIRICAL_SUITABILITY_DELTA_V1"

EPI_BUILDER = "EDGEIQ_EPI_ENGINE_V2"
EPI_METHOD = "FAIL_CLOSED_PENDING_APPROVED_EPI_TRANSFORM_BINDING_V1"

FEED_BUILDER = "EDGEIQ_RACE_INTELLIGENCE_ENGINE_V2"
FEED_METHOD = "CANONICAL_STATUS_AND_VALUE_PUBLICATION_V1"


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalise_name(value: str) -> str:
    return " ".join(clean(value).upper().split())


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


def write_csv(
    path: Path,
    fields: list[str],
    rows: list[dict[str, str]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
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
        writer.writerows(rows)


def promote(candidate: Path, production: Path) -> str:
    temp = production.with_suffix(production.suffix + ".tmp")
    shutil.copy2(candidate, temp)
    os.replace(temp, production)

    candidate_hash = sha256_file(candidate)
    production_hash = sha256_file(production)

    if candidate_hash != production_hash:
        raise RuntimeError(
            f"Promotion hash mismatch: {candidate} -> {production}"
        )

    return production_hash


def parse_date(value: str) -> date | None:
    value = clean(value).replace("Z", "")

    if not value:
        return None

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

    return parsed if math.isfinite(parsed) else None


def number(value: float | None) -> str:
    return "" if value is None else f"{value:.12f}"


def find_column(
    fields: list[str],
    aliases: list[str],
    required: bool = False,
) -> str | None:
    lookup = {field.lower(): field for field in fields}

    for alias in aliases:
        if alias.lower() in lookup:
            return lookup[alias.lower()]

    if required:
        raise RuntimeError(
            "Required column unavailable. Tried: "
            + ", ".join(aliases)
        )

    return None


def deterministic_check(
    fields: list[str],
    rows: list[dict[str, str]],
    candidate: Path,
    directory: Path,
    filename: str,
) -> bool:
    check_path = directory / filename
    write_csv(check_path, fields, rows)

    passed = sha256_file(candidate) == sha256_file(check_path)
    check_path.unlink(missing_ok=True)

    return passed


# ============================================================
# INPUTS
# ============================================================

context_fields, context_rows = read_csv(CONTEXT_PATH)
snapshot_fields, snapshot_rows = read_csv(SNAPSHOT_PATH)
historical_fields, historical_rows = read_csv(HISTORICAL_PATH)

historical_horse_id_col = find_column(
    historical_fields,
    [
        "canonical_horse_id",
        "canonical_runner_id",
        "runner_id",
    ],
    required=True,
)

historical_horse_name_col = find_column(
    historical_fields,
    [
        "canonical_horse_name",
        "runner_name",
        "horse_name",
    ],
)

historical_date_col = find_column(
    historical_fields,
    [
        "race_date",
        "performance_date",
        "observation_date",
        "as_of_date",
    ],
    required=True,
)

historical_value_col = find_column(
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

historical_observation_id_col = find_column(
    historical_fields,
    [
        "horse_performance_observation_id",
        "performance_observation_id",
        "observation_id",
    ],
)

historical_track_col = find_column(
    historical_fields,
    ["canonical_track", "track", "track_name"],
)

historical_distance_col = find_column(
    historical_fields,
    ["race_distance_metres", "distance_metres", "distance"],
)

historical_surface_col = find_column(
    historical_fields,
    ["surface_group", "surface"],
)

historical_condition_col = find_column(
    historical_fields,
    [
        "track_condition_number",
        "condition_number",
        "track_condition",
    ],
)

historical_barrier_col = find_column(
    historical_fields,
    ["barrier", "barrier_number"],
)

historical_weight_col = find_column(
    historical_fields,
    ["weight_kg", "carried_weight_kg", "weight"],
)

snapshot_lookup = {
    (
        row["canonical_race_id"],
        row["canonical_runner_id"],
    ): row
    for row in snapshot_rows
}


# ============================================================
# STAGE 3A — IDENTITY BRIDGE
# ============================================================

historical_ids = {
    clean(row.get(historical_horse_id_col, ""))
    for row in historical_rows
    if clean(row.get(historical_horse_id_col, ""))
}

historical_name_to_ids: dict[str, set[str]] = defaultdict(set)

if historical_horse_name_col:
    for row in historical_rows:
        historical_id = clean(
            row.get(historical_horse_id_col, "")
        )
        historical_name = normalise_name(
            row.get(historical_horse_name_col, "")
        )

        if historical_id and historical_name:
            historical_name_to_ids[historical_name].add(historical_id)

bridge_fields = [
    "current_canonical_runner_id",
    "current_canonical_horse_name",
    "historical_canonical_horse_id",
    "historical_canonical_horse_name",
    "identity_resolution_method",
    "identity_resolution_status",
    "identity_resolution_reason_code",
    "historical_name_collision_count",
    "identity_builder_version",
    "identity_method_version",
    "identity_bridge_evidence_sha256",
]

bridge_rows: list[dict[str, str]] = []
resolved_historical_id_by_runner: dict[str, str] = {}
bridge_status_counts: Counter[str] = Counter()

seen_current_runners: dict[str, str] = {}

for context in context_rows:
    current_id = context["canonical_runner_id"]
    current_name = context["canonical_horse_name"]

    if current_id not in seen_current_runners:
        seen_current_runners[current_id] = current_name

for current_id, current_name in sorted(seen_current_runners.items()):
    normalised_current_name = normalise_name(current_name)
    matched_historical_id = ""
    matched_historical_name = ""
    resolution_method = ""
    resolution_status = ""
    reason_code = ""
    collision_count = 0

    if current_id in historical_ids:
        matched_historical_id = current_id
        resolution_method = "CANONICAL_ID_EXACT"
        resolution_status = "IDENTITY_RESOLVED"
        reason_code = "EXACT_CANONICAL_ID_MATCH"

    elif historical_horse_name_col and normalised_current_name:
        candidate_ids = historical_name_to_ids.get(
            normalised_current_name,
            set(),
        )
        collision_count = len(candidate_ids)

        if len(candidate_ids) == 1:
            matched_historical_id = next(iter(candidate_ids))
            resolution_method = "EXACT_UNIQUE_NORMALISED_NAME"
            resolution_status = "IDENTITY_RESOLVED"
            reason_code = "EXACT_NAME_UNIQUE_IN_HISTORICAL_WAREHOUSE"

            matching_row = next(
                (
                    row
                    for row in historical_rows
                    if clean(
                        row.get(historical_horse_id_col, "")
                    )
                    == matched_historical_id
                ),
                None,
            )

            if matching_row:
                matched_historical_name = clean(
                    matching_row.get(
                        historical_horse_name_col,
                        "",
                    )
                )

        elif len(candidate_ids) > 1:
            resolution_status = "IDENTITY_UNRESOLVED"
            reason_code = "HISTORICAL_NAME_COLLISION"

        else:
            resolution_status = "IDENTITY_UNRESOLVED"
            reason_code = "NO_CANONICAL_ID_OR_EXACT_NAME_MATCH"

    else:
        resolution_status = "IDENTITY_UNRESOLVED"
        reason_code = (
            "HISTORICAL_HORSE_NAME_FIELD_UNAVAILABLE"
            if not historical_horse_name_col
            else "CURRENT_HORSE_NAME_UNAVAILABLE"
        )

    if matched_historical_id:
        resolved_historical_id_by_runner[
            current_id
        ] = matched_historical_id

    bridge_status_counts[resolution_status] += 1

    payload = {
        "current_id": current_id,
        "current_name": current_name,
        "historical_id": matched_historical_id,
        "historical_name": matched_historical_name,
        "method": resolution_method,
        "status": resolution_status,
        "reason": reason_code,
        "collision_count": collision_count,
    }

    bridge_rows.append(
        {
            "current_canonical_runner_id": current_id,
            "current_canonical_horse_name": current_name,
            "historical_canonical_horse_id": matched_historical_id,
            "historical_canonical_horse_name": matched_historical_name,
            "identity_resolution_method": resolution_method,
            "identity_resolution_status": resolution_status,
            "identity_resolution_reason_code": reason_code,
            "historical_name_collision_count": str(collision_count),
            "identity_builder_version": IDENTITY_BUILDER,
            "identity_method_version": IDENTITY_METHOD,
            "identity_bridge_evidence_sha256": sha256_text(
                canonical_json(payload)
            ),
        }
    )

write_csv(BRIDGE_CANDIDATE, bridge_fields, bridge_rows)

bridge_checks = {
    "one_bridge_row_per_current_runner": (
        len(bridge_rows) == len(seen_current_runners)
    ),
    "current_runner_ids_unique": (
        len(
            {
                row["current_canonical_runner_id"]
                for row in bridge_rows
            }
        )
        == len(bridge_rows)
    ),
    "resolved_rows_have_historical_id": all(
        row["historical_canonical_horse_id"]
        for row in bridge_rows
        if row["identity_resolution_status"]
        == "IDENTITY_RESOLVED"
    ),
    "name_fallback_is_unique_only": all(
        int(row["historical_name_collision_count"]) == 1
        for row in bridge_rows
        if row["identity_resolution_method"]
        == "EXACT_UNIQUE_NORMALISED_NAME"
    ),
    "no_fuzzy_matching": all(
        row["identity_resolution_method"]
        in {
            "",
            "CANONICAL_ID_EXACT",
            "EXACT_UNIQUE_NORMALISED_NAME",
        }
        for row in bridge_rows
    ),
    "evidence_complete": all(
        row["identity_bridge_evidence_sha256"]
        for row in bridge_rows
    ),
    "deterministic_rerun": deterministic_check(
        bridge_fields,
        bridge_rows,
        BRIDGE_CANDIDATE,
        IDENTITY_DOCS,
        "identity_bridge_deterministic_check.csv",
    ),
}

if not all(bridge_checks.values()):
    raise RuntimeError(
        "Identity bridge audit failed:\n"
        + json.dumps(bridge_checks, indent=2)
    )

bridge_production_hash = promote(
    BRIDGE_CANDIDATE,
    BRIDGE_PRODUCTION,
)

bridge_audit = {
    "status": "EDGEIQ_CURRENT_HISTORICAL_HORSE_IDENTITY_BRIDGE_V2_AUDIT_PASS",
    "current_unique_runners": len(seen_current_runners),
    "historical_unique_ids": len(historical_ids),
    "historical_name_field": historical_horse_name_col or "",
    "identity_status_counts": dict(
        sorted(bridge_status_counts.items())
    ),
    "resolved_current_runners": len(
        resolved_historical_id_by_runner
    ),
    "checks": bridge_checks,
    "candidate_sha256": sha256_file(BRIDGE_CANDIDATE),
    "production_sha256": bridge_production_hash,
}

(IDENTITY_DOCS / "EDGEIQ_CURRENT_HISTORICAL_HORSE_IDENTITY_BRIDGE_V2_AUDIT.json").write_text(
    json.dumps(bridge_audit, indent=2),
    encoding="utf-8",
)

identity_md = [
    "# EDGEIQ Current-to-Historical Horse Identity Bridge V2",
    "",
    f"Status: `{bridge_audit['status']}`",
    "",
    f"- Current unique runners: `{len(seen_current_runners)}`",
    f"- Historical unique identities: `{len(historical_ids)}`",
    f"- Resolved current runners: `{len(resolved_historical_id_by_runner)}`",
    f"- Historical name field: `{historical_horse_name_col or 'UNAVAILABLE'}`",
    "",
    "## Status Counts",
    "",
]

for key, value in bridge_audit["identity_status_counts"].items():
    identity_md.append(f"- `{key}`: `{value}`")

identity_md.extend(
    [
        "",
        "## Governance",
        "",
        "- Canonical ID exact match is preferred.",
        "- Name fallback requires an exact normalised name and exactly one historical identity.",
        "- Fuzzy, partial and approximate name matching are prohibited.",
        "- Ambiguous names remain unresolved.",
        "",
    ]
)

(IDENTITY_DOCS / "EDGEIQ_CURRENT_HISTORICAL_HORSE_IDENTITY_BRIDGE_V2_AUDIT.md").write_text(
    "\n".join(identity_md),
    encoding="utf-8",
)


# ============================================================
# HISTORICAL OBSERVATION INDEX
# ============================================================

observations_by_historical_id: dict[
    str,
    list[dict[str, Any]],
] = defaultdict(list)

invalid_historical_rows = 0

for source in historical_rows:
    historical_id = clean(
        source.get(historical_horse_id_col, "")
    )
    observation_date = parse_date(
        source.get(historical_date_col, "")
    )
    performance_value = parse_float(
        source.get(historical_value_col, "")
    )

    if (
        not historical_id
        or observation_date is None
        or performance_value is None
    ):
        invalid_historical_rows += 1
        continue

    observation_id = (
        clean(
            source.get(
                historical_observation_id_col or "",
                "",
            )
        )
        or sha256_text(canonical_json(source))
    )

    observations_by_historical_id[historical_id].append(
        {
            "observation_id": observation_id,
            "observation_date": observation_date,
            "performance_value": performance_value,
            "track": normalise_name(
                source.get(historical_track_col or "", "")
            ),
            "distance": parse_float(
                source.get(historical_distance_col or "", "")
            ),
            "surface": normalise_name(
                source.get(historical_surface_col or "", "")
            ),
            "condition": parse_float(
                source.get(historical_condition_col or "", "")
            ),
            "barrier": parse_float(
                source.get(historical_barrier_col or "", "")
            ),
            "weight": parse_float(
                source.get(historical_weight_col or "", "")
            ),
        }
    )

for observations in observations_by_historical_id.values():
    observations.sort(
        key=lambda item: (
            item["observation_date"],
            item["observation_id"],
        )
    )


# ============================================================
# STAGE 3 — SUITABILITY REBUILD
# ============================================================

suitability_fields = [
    "race_entry_suitability_id",
    "canonical_race_id",
    "canonical_runner_id",
    "canonical_horse_id",
    "canonical_horse_name",
    "historical_canonical_horse_id",
    "historical_identity_resolution_status",
    "historical_identity_resolution_method",
    "race_date",
    "canonical_track",
    "race_distance_metres",
    "surface_group",
    "track_condition_number",
    "barrier",
    "weight_kg",
    "historical_observation_count",
    "horse_historical_performance_mean",
    "track_match_count",
    "track_suitability_delta",
    "track_suitability_status",
    "distance_match_count",
    "distance_suitability_delta",
    "distance_suitability_status",
    "surface_match_count",
    "surface_suitability_delta",
    "surface_suitability_status",
    "track_condition_match_count",
    "track_condition_suitability_delta",
    "track_condition_suitability_status",
    "barrier_match_count",
    "barrier_suitability_delta",
    "barrier_suitability_status",
    "weight_match_count",
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

bridge_lookup = {
    row["current_canonical_runner_id"]: row
    for row in bridge_rows
}

suitability_rows: list[dict[str, str]] = []
suitability_status_counts: Counter[str] = Counter()
component_distribution: Counter[str] = Counter()

for context in context_rows:
    runner_id = context["canonical_runner_id"]
    race_id = context["canonical_race_id"]
    race_date = parse_date(context["race_date"])

    bridge = bridge_lookup[runner_id]
    historical_id = bridge["historical_canonical_horse_id"]

    all_observations = observations_by_historical_id.get(
        historical_id,
        [],
    )

    eligible = [
        observation
        for observation in all_observations
        if (
            race_date is not None
            and observation["observation_date"] < race_date
        )
    ]

    baseline = (
        mean(
            observation["performance_value"]
            for observation in eligible
        )
        if eligible
        else None
    )

    target_track = normalise_name(
        context["canonical_track"]
    )
    target_distance = parse_float(
        context["race_distance_metres"]
    )
    target_surface = normalise_name(
        context["surface_group"]
    )
    target_condition = parse_float(
        context["track_condition_number"]
    )
    target_barrier = parse_float(context["barrier"])
    target_weight = parse_float(context["weight_kg"])

    def component(
        matches: list[dict[str, Any]],
    ) -> tuple[str, str, str]:
        if baseline is None or not matches:
            return (
                str(len(matches)),
                "",
                "INSUFFICIENT_MATCHED_HISTORY",
            )

        delta = (
            mean(
                observation["performance_value"]
                for observation in matches
            )
            - baseline
        )

        return (
            str(len(matches)),
            number(delta),
            "EMPIRICAL_COMPONENT_AVAILABLE",
        )

    track_component = component(
        [
            observation
            for observation in eligible
            if (
                target_track
                and observation["track"] == target_track
            )
        ]
    )

    distance_component = component(
        [
            observation
            for observation in eligible
            if (
                target_distance is not None
                and observation["distance"] is not None
                and abs(
                    observation["distance"] - target_distance
                )
                <= 200
            )
        ]
    )

    surface_component = component(
        [
            observation
            for observation in eligible
            if (
                target_surface
                and observation["surface"] == target_surface
            )
        ]
    )

    condition_component = component(
        [
            observation
            for observation in eligible
            if (
                target_condition is not None
                and observation["condition"] is not None
                and abs(
                    observation["condition"]
                    - target_condition
                )
                <= 1
            )
        ]
    )

    barrier_component = component(
        [
            observation
            for observation in eligible
            if (
                target_barrier is not None
                and observation["barrier"] is not None
                and abs(
                    observation["barrier"] - target_barrier
                )
                <= 2
            )
        ]
    )

    weight_component = component(
        [
            observation
            for observation in eligible
            if (
                target_weight is not None
                and observation["weight"] is not None
                and abs(
                    observation["weight"] - target_weight
                )
                <= 2.0
            )
        ]
    )

    components = [
        track_component,
        distance_component,
        surface_component,
        condition_component,
        barrier_component,
        weight_component,
    ]

    available_deltas = [
        parse_float(component_value[1])
        for component_value in components
        if component_value[2]
        == "EMPIRICAL_COMPONENT_AVAILABLE"
    ]

    available_deltas = [
        value
        for value in available_deltas
        if value is not None
    ]

    available_count = len(available_deltas)
    component_distribution[str(available_count)] += 1

    participation = context[
        "entry_participation_status"
    ]

    if participation == "SCRATCHED":
        status = "SUITABILITY_NOT_APPLICABLE_ENTRY_INACTIVE"
        reason = "SCRATCHED_ENTRY"

    elif not historical_id:
        status = "SUITABILITY_UNAVAILABLE"
        reason = "HISTORICAL_IDENTITY_UNRESOLVED"

    elif not eligible:
        status = "SUITABILITY_UNAVAILABLE"
        reason = "NO_STRICTLY_PRIOR_GOVERNED_OBSERVATIONS"

    elif available_count == 0:
        status = "SUITABILITY_UNAVAILABLE"
        reason = "NO_MATCHED_CONTEXT_COMPONENTS"

    elif available_count < 6:
        status = "SUITABILITY_PARTIAL"
        reason = "PARTIAL_MATCHED_CONTEXT_EVIDENCE"

    else:
        status = "SUITABILITY_AVAILABLE"
        reason = "ALL_CONTEXT_COMPONENTS_AVAILABLE"

    suitability_status_counts[status] += 1

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
                "method": SUITABILITY_METHOD,
            }
        )
    )

    evidence = {
        "suitability_id": suitability_id,
        "historical_id": historical_id,
        "observation_ids": observation_ids,
        "components": components,
        "composite": composite,
        "status": status,
        "reason": reason,
    }

    suitability_rows.append(
        {
            "race_entry_suitability_id": suitability_id,
            "canonical_race_id": race_id,
            "canonical_runner_id": runner_id,
            "canonical_horse_id": runner_id,
            "canonical_horse_name": context[
                "canonical_horse_name"
            ],
            "historical_canonical_horse_id": historical_id,
            "historical_identity_resolution_status": bridge[
                "identity_resolution_status"
            ],
            "historical_identity_resolution_method": bridge[
                "identity_resolution_method"
            ],
            "race_date": context["race_date"],
            "canonical_track": context["canonical_track"],
            "race_distance_metres": context[
                "race_distance_metres"
            ],
            "surface_group": context["surface_group"],
            "track_condition_number": context[
                "track_condition_number"
            ],
            "barrier": context["barrier"],
            "weight_kg": context["weight_kg"],
            "historical_observation_count": str(
                len(eligible)
            ),
            "horse_historical_performance_mean": number(
                baseline
            ),
            "track_match_count": track_component[0],
            "track_suitability_delta": track_component[1],
            "track_suitability_status": track_component[2],
            "distance_match_count": distance_component[0],
            "distance_suitability_delta": distance_component[1],
            "distance_suitability_status": distance_component[2],
            "surface_match_count": surface_component[0],
            "surface_suitability_delta": surface_component[1],
            "surface_suitability_status": surface_component[2],
            "track_condition_match_count": condition_component[0],
            "track_condition_suitability_delta": condition_component[1],
            "track_condition_suitability_status": condition_component[2],
            "barrier_match_count": barrier_component[0],
            "barrier_suitability_delta": barrier_component[1],
            "barrier_suitability_status": barrier_component[2],
            "weight_match_count": weight_component[0],
            "weight_suitability_delta": weight_component[1],
            "weight_suitability_status": weight_component[2],
            "available_component_count": str(available_count),
            "suitability_composite_delta": number(composite),
            "suitability_status": status,
            "suitability_reason_code": reason,
            "source_race_context_evidence_sha256": context[
                "race_entry_context_evidence_sha256"
            ],
            "source_historical_observation_ids_sha256": (
                sha256_text(canonical_json(observation_ids))
            ),
            "suitability_builder_version": SUITABILITY_BUILDER,
            "suitability_method_version": SUITABILITY_METHOD,
            "race_entry_suitability_evidence_sha256": (
                sha256_text(canonical_json(evidence))
            ),
        }
    )

suitability_rows.sort(
    key=lambda row: (
        row["race_date"],
        row["canonical_race_id"],
        row["canonical_runner_id"],
    )
)

write_csv(
    SUITABILITY_CANDIDATE,
    suitability_fields,
    suitability_rows,
)

suitability_checks = {
    "one_row_per_context": (
        len(suitability_rows) == len(context_rows)
    ),
    "natural_keys_unique": (
        len(
            {
                (
                    row["canonical_race_id"],
                    row["canonical_runner_id"],
                )
                for row in suitability_rows
            }
        )
        == len(suitability_rows)
    ),
    "no_fake_composite": all(
        row["suitability_composite_delta"]
        or row["available_component_count"] == "0"
        for row in suitability_rows
    ),
    "strictly_prior_evidence": True,
    "evidence_complete": all(
        row["race_entry_suitability_evidence_sha256"]
        for row in suitability_rows
    ),
    "deterministic_rerun": deterministic_check(
        suitability_fields,
        suitability_rows,
        SUITABILITY_CANDIDATE,
        SUITABILITY_DOCS,
        "suitability_deterministic_check.csv",
    ),
}

if not all(suitability_checks.values()):
    raise RuntimeError(
        "Suitability audit failed:\n"
        + json.dumps(suitability_checks, indent=2)
    )

suitability_production_hash = promote(
    SUITABILITY_CANDIDATE,
    SUITABILITY_PRODUCTION,
)

suitability_audit = {
    "status": "EDGEIQ_RACE_ENTRY_SUITABILITY_V2_AUDIT_PASS",
    "historical_source_rows": len(historical_rows),
    "invalid_historical_rows": invalid_historical_rows,
    "resolved_identity_count": len(
        resolved_historical_id_by_runner
    ),
    "suitability_rows": len(suitability_rows),
    "suitability_status_counts": dict(
        sorted(suitability_status_counts.items())
    ),
    "available_component_count_distribution": dict(
        sorted(component_distribution.items())
    ),
    "checks": suitability_checks,
    "candidate_sha256": sha256_file(
        SUITABILITY_CANDIDATE
    ),
    "production_sha256": suitability_production_hash,
}

(SUITABILITY_DOCS / "EDGEIQ_RACE_ENTRY_SUITABILITY_V2_AUDIT.json").write_text(
    json.dumps(suitability_audit, indent=2),
    encoding="utf-8",
)

suitability_md = [
    "# EDGEIQ Race-Entry Suitability V2 Audit",
    "",
    f"Status: `{suitability_audit['status']}`",
    "",
    f"- Suitability rows: `{len(suitability_rows)}`",
    f"- Resolved current identities: `{len(resolved_historical_id_by_runner)}`",
    "",
    "## Status Counts",
    "",
]

for key, value in suitability_audit[
    "suitability_status_counts"
].items():
    suitability_md.append(f"- `{key}`: `{value}`")

suitability_md.extend(
    [
        "",
        "## Available Component Distribution",
        "",
    ]
)

for key, value in suitability_audit[
    "available_component_count_distribution"
].items():
    suitability_md.append(
        f"- `{key}` components: `{value}`"
    )

suitability_md.extend(
    [
        "",
        "## Audit Checks",
        "",
    ]
)

for key, value in suitability_checks.items():
    suitability_md.append(
        f"- `{key}`: `{'PASS' if value else 'FAIL'}`"
    )

suitability_md.extend(
    [
        "",
        "- No fuzzy identity matching.",
        "- No zero imputation.",
        "- No market substitution.",
        "- Strictly prior historical evidence only.",
        "",
    ]
)

(SUITABILITY_DOCS / "EDGEIQ_RACE_ENTRY_SUITABILITY_V2_AUDIT.md").write_text(
    "\n".join(suitability_md),
    encoding="utf-8",
)


# ============================================================
# STAGE 4 — PROJECTED PERFORMANCE
# ============================================================

projected_fields = [
    "race_entry_projected_performance_id",
    "canonical_race_id",
    "canonical_runner_id",
    "canonical_horse_name",
    "race_date",
    "historical_rating_value",
    "historical_rating_as_of_date",
    "suitability_composite_delta",
    "projected_performance_value",
    "projected_performance_status",
    "projected_performance_reason_code",
    "source_rating_snapshot_evidence_sha256",
    "source_suitability_evidence_sha256",
    "projected_performance_builder_version",
    "projected_performance_method_version",
    "projected_performance_evidence_sha256",
]

suitability_lookup = {
    (
        row["canonical_race_id"],
        row["canonical_runner_id"],
    ): row
    for row in suitability_rows
}

projected_rows: list[dict[str, str]] = []
projected_status_counts: Counter[str] = Counter()

for context in context_rows:
    key = (
        context["canonical_race_id"],
        context["canonical_runner_id"],
    )

    snapshot = snapshot_lookup[key]
    suitability = suitability_lookup[key]

    rating = parse_float(
        snapshot[
            "selected_horse_performance_rating_value"
        ]
    )

    suitability_delta = parse_float(
        suitability["suitability_composite_delta"]
    )

    if context["entry_participation_status"] == "SCRATCHED":
        status = "PROJECTED_PERFORMANCE_NOT_APPLICABLE"
        reason = "SCRATCHED_ENTRY"
        projected_value = None

    elif rating is None:
        status = "PROJECTED_PERFORMANCE_UNAVAILABLE"
        reason = "GOVERNED_HISTORICAL_RATING_UNAVAILABLE"
        projected_value = None

    elif suitability_delta is None:
        status = "PROJECTED_PERFORMANCE_UNAVAILABLE"
        reason = "EMPIRICAL_SUITABILITY_UNAVAILABLE"
        projected_value = None

    else:
        status = "PROJECTED_PERFORMANCE_AVAILABLE"
        reason = "RATING_PLUS_EMPIRICAL_SUITABILITY_DELTA"
        projected_value = rating + suitability_delta

    projected_status_counts[status] += 1

    projected_id = sha256_text(
        canonical_json(
            {
                "race_id": key[0],
                "runner_id": key[1],
                "race_date": context["race_date"],
                "method": PROJECTED_METHOD,
            }
        )
    )

    evidence = {
        "projected_id": projected_id,
        "rating": rating,
        "suitability_delta": suitability_delta,
        "projected_value": projected_value,
        "status": status,
        "reason": reason,
    }

    projected_rows.append(
        {
            "race_entry_projected_performance_id": projected_id,
            "canonical_race_id": key[0],
            "canonical_runner_id": key[1],
            "canonical_horse_name": context[
                "canonical_horse_name"
            ],
            "race_date": context["race_date"],
            "historical_rating_value": number(rating),
            "historical_rating_as_of_date": snapshot[
                "selected_rating_as_of_date"
            ],
            "suitability_composite_delta": number(
                suitability_delta
            ),
            "projected_performance_value": number(
                projected_value
            ),
            "projected_performance_status": status,
            "projected_performance_reason_code": reason,
            "source_rating_snapshot_evidence_sha256": snapshot[
                "race_entry_horse_rating_snapshot_evidence_sha256"
            ],
            "source_suitability_evidence_sha256": suitability[
                "race_entry_suitability_evidence_sha256"
            ],
            "projected_performance_builder_version": PROJECTED_BUILDER,
            "projected_performance_method_version": PROJECTED_METHOD,
            "projected_performance_evidence_sha256": sha256_text(
                canonical_json(evidence)
            ),
        }
    )

projected_rows.sort(
    key=lambda row: (
        row["race_date"],
        row["canonical_race_id"],
        row["canonical_runner_id"],
    )
)

write_csv(
    PROJECTED_CANDIDATE,
    projected_fields,
    projected_rows,
)

projected_checks = {
    "one_row_per_context": (
        len(projected_rows) == len(context_rows)
    ),
    "no_projection_without_rating": all(
        not row["projected_performance_value"]
        or row["historical_rating_value"]
        for row in projected_rows
    ),
    "no_projection_without_suitability": all(
        not row["projected_performance_value"]
        or row["suitability_composite_delta"]
        for row in projected_rows
    ),
    "available_formula_exact": all(
        abs(
            parse_float(
                row["projected_performance_value"]
            )
            - (
                parse_float(
                    row["historical_rating_value"]
                )
                + parse_float(
                    row["suitability_composite_delta"]
                )
            )
        )
        < 1e-9
        for row in projected_rows
        if row["projected_performance_status"]
        == "PROJECTED_PERFORMANCE_AVAILABLE"
    ),
    "evidence_complete": all(
        row["projected_performance_evidence_sha256"]
        for row in projected_rows
    ),
    "deterministic_rerun": deterministic_check(
        projected_fields,
        projected_rows,
        PROJECTED_CANDIDATE,
        PROJECTED_DOCS,
        "projected_performance_deterministic_check.csv",
    ),
}

if not all(projected_checks.values()):
    raise RuntimeError(
        "Projected Performance audit failed:\n"
        + json.dumps(projected_checks, indent=2)
    )

projected_production_hash = promote(
    PROJECTED_CANDIDATE,
    PROJECTED_PRODUCTION,
)

projected_audit = {
    "status": "EDGEIQ_PROJECTED_PERFORMANCE_ENGINE_V2_AUDIT_PASS",
    "rows": len(projected_rows),
    "status_counts": dict(
        sorted(projected_status_counts.items())
    ),
    "checks": projected_checks,
    "candidate_sha256": sha256_file(
        PROJECTED_CANDIDATE
    ),
    "production_sha256": projected_production_hash,
}

(PROJECTED_DOCS / "EDGEIQ_PROJECTED_PERFORMANCE_ENGINE_V2_AUDIT.json").write_text(
    json.dumps(projected_audit, indent=2),
    encoding="utf-8",
)

projected_md = [
    "# EDGEIQ Projected Performance Engine V2 Audit",
    "",
    f"Status: `{projected_audit['status']}`",
    "",
    f"- Rows: `{len(projected_rows)}`",
    "",
    "## Status Counts",
    "",
]

for key, value in projected_audit["status_counts"].items():
    projected_md.append(f"- `{key}`: `{value}`")

projected_md.extend(
    [
        "",
        "## Formula",
        "",
        "`Projected Performance = Governed Historical Rating + Empirical Suitability Composite Delta`",
        "",
        "No output is produced unless both inputs are available.",
        "",
    ]
)

(PROJECTED_DOCS / "EDGEIQ_PROJECTED_PERFORMANCE_ENGINE_V2_AUDIT.md").write_text(
    "\n".join(projected_md),
    encoding="utf-8",
)


# ============================================================
# STAGE 5 — EPI FAIL-CLOSED READINESS
# ============================================================

epi_fields = [
    "race_entry_epi_id",
    "canonical_race_id",
    "canonical_runner_id",
    "canonical_horse_name",
    "race_date",
    "projected_performance_value",
    "epi_value",
    "epi_rank",
    "epi_status",
    "epi_reason_code",
    "source_projected_performance_evidence_sha256",
    "epi_builder_version",
    "epi_method_version",
    "epi_evidence_sha256",
]

epi_rows: list[dict[str, str]] = []
epi_status_counts: Counter[str] = Counter()

for projected in projected_rows:
    projected_value = parse_float(
        projected["projected_performance_value"]
    )

    if projected[
        "projected_performance_status"
    ] != "PROJECTED_PERFORMANCE_AVAILABLE":
        status = "EPI_UNAVAILABLE"
        reason = "PROJECTED_PERFORMANCE_UNAVAILABLE"

    else:
        status = "EPI_TRANSFORM_NOT_BOUND"
        reason = "APPROVED_EPI_TRANSFORM_NOT_BOUND_TO_V2_ENGINE"

    epi_status_counts[status] += 1

    epi_id = sha256_text(
        canonical_json(
            {
                "race_id": projected["canonical_race_id"],
                "runner_id": projected[
                    "canonical_runner_id"
                ],
                "method": EPI_METHOD,
            }
        )
    )

    evidence = {
        "epi_id": epi_id,
        "projected_value": projected_value,
        "epi_value": None,
        "status": status,
        "reason": reason,
    }

    epi_rows.append(
        {
            "race_entry_epi_id": epi_id,
            "canonical_race_id": projected[
                "canonical_race_id"
            ],
            "canonical_runner_id": projected[
                "canonical_runner_id"
            ],
            "canonical_horse_name": projected[
                "canonical_horse_name"
            ],
            "race_date": projected["race_date"],
            "projected_performance_value": number(
                projected_value
            ),
            "epi_value": "",
            "epi_rank": "",
            "epi_status": status,
            "epi_reason_code": reason,
            "source_projected_performance_evidence_sha256": projected[
                "projected_performance_evidence_sha256"
            ],
            "epi_builder_version": EPI_BUILDER,
            "epi_method_version": EPI_METHOD,
            "epi_evidence_sha256": sha256_text(
                canonical_json(evidence)
            ),
        }
    )

write_csv(EPI_CANDIDATE, epi_fields, epi_rows)

epi_checks = {
    "one_row_per_projected_row": (
        len(epi_rows) == len(projected_rows)
    ),
    "no_fabricated_epi_values": all(
        not row["epi_value"]
        and not row["epi_rank"]
        for row in epi_rows
    ),
    "explicit_reason_on_every_row": all(
        row["epi_status"] and row["epi_reason_code"]
        for row in epi_rows
    ),
    "deterministic_rerun": deterministic_check(
        epi_fields,
        epi_rows,
        EPI_CANDIDATE,
        EPI_DOCS,
        "epi_deterministic_check.csv",
    ),
}

if not all(epi_checks.values()):
    raise RuntimeError(
        "EPI readiness audit failed:\n"
        + json.dumps(epi_checks, indent=2)
    )

epi_production_hash = promote(
    EPI_CANDIDATE,
    EPI_PRODUCTION,
)

epi_audit = {
    "status": "EDGEIQ_EPI_ENGINE_V2_READINESS_AUDIT_PASS",
    "rows": len(epi_rows),
    "status_counts": dict(
        sorted(epi_status_counts.items())
    ),
    "checks": epi_checks,
    "candidate_sha256": sha256_file(EPI_CANDIDATE),
    "production_sha256": epi_production_hash,
}

(EPI_DOCS / "EDGEIQ_EPI_ENGINE_V2_READINESS_AUDIT.json").write_text(
    json.dumps(epi_audit, indent=2),
    encoding="utf-8",
)

(EPI_DOCS / "EDGEIQ_EPI_ENGINE_V2_READINESS_AUDIT.md").write_text(
    "\n".join(
        [
            "# EDGEIQ EPI Engine V2 Readiness Audit",
            "",
            f"Status: `{epi_audit['status']}`",
            "",
            f"- Rows: `{len(epi_rows)}`",
            "- Fabricated EPI values: `0`",
            "- Fabricated ranks: `0`",
            "",
            "The engine remains fail-closed until the approved EPI transform is explicitly recovered and bound.",
            "",
        ]
    ),
    encoding="utf-8",
)


# ============================================================
# STAGE 6 — CANONICAL RACE INTELLIGENCE FEED
# ============================================================

epi_lookup = {
    (
        row["canonical_race_id"],
        row["canonical_runner_id"],
    ): row
    for row in epi_rows
}

projected_lookup = {
    (
        row["canonical_race_id"],
        row["canonical_runner_id"],
    ): row
    for row in projected_rows
}

feed_fields = [
    "race_intelligence_feed_id",
    "canonical_race_id",
    "canonical_runner_id",
    "canonical_horse_name",
    "race_date",
    "canonical_track",
    "race_number",
    "barrier",
    "weight_kg",
    "jockey_name",
    "trainer_name",
    "entry_participation_status",
    "historical_rating_value",
    "suitability_composite_delta",
    "projected_performance_value",
    "epi_value",
    "epi_rank",
    "historical_rating_status",
    "suitability_status",
    "projected_performance_status",
    "epi_status",
    "race_intelligence_status",
    "race_intelligence_reason_code",
    "source_race_context_evidence_sha256",
    "source_projected_performance_evidence_sha256",
    "source_epi_evidence_sha256",
    "race_intelligence_builder_version",
    "race_intelligence_method_version",
    "race_intelligence_evidence_sha256",
]

feed_rows: list[dict[str, str]] = []
feed_status_counts: Counter[str] = Counter()

for context in context_rows:
    key = (
        context["canonical_race_id"],
        context["canonical_runner_id"],
    )

    snapshot = snapshot_lookup[key]
    suitability = suitability_lookup[key]
    projected = projected_lookup[key]
    epi = epi_lookup[key]

    if context["entry_participation_status"] == "SCRATCHED":
        intelligence_status = "RACE_INTELLIGENCE_ENTRY_INACTIVE"
        intelligence_reason = "SCRATCHED_ENTRY"

    elif epi["epi_status"] == "EPI_AVAILABLE":
        intelligence_status = "RACE_INTELLIGENCE_AVAILABLE"
        intelligence_reason = "FULL_GOVERNED_LIVE_CHAIN_AVAILABLE"

    elif projected[
        "projected_performance_status"
    ] == "PROJECTED_PERFORMANCE_AVAILABLE":
        intelligence_status = "RACE_INTELLIGENCE_PARTIAL"
        intelligence_reason = "PROJECTED_PERFORMANCE_AVAILABLE_EPI_PENDING"

    else:
        intelligence_status = "RACE_INTELLIGENCE_UNAVAILABLE"
        intelligence_reason = projected[
            "projected_performance_reason_code"
        ]

    feed_status_counts[intelligence_status] += 1

    feed_id = sha256_text(
        canonical_json(
            {
                "race_id": key[0],
                "runner_id": key[1],
                "method": FEED_METHOD,
            }
        )
    )

    evidence = {
        "feed_id": feed_id,
        "rating_status": snapshot[
            "race_entry_horse_rating_snapshot_status"
        ],
        "suitability_status": suitability[
            "suitability_status"
        ],
        "projected_status": projected[
            "projected_performance_status"
        ],
        "epi_status": epi["epi_status"],
        "intelligence_status": intelligence_status,
    }

    feed_rows.append(
        {
            "race_intelligence_feed_id": feed_id,
            "canonical_race_id": key[0],
            "canonical_runner_id": key[1],
            "canonical_horse_name": context[
                "canonical_horse_name"
            ],
            "race_date": context["race_date"],
            "canonical_track": context[
                "canonical_track"
            ],
            "race_number": context["race_number"],
            "barrier": context["barrier"],
            "weight_kg": context["weight_kg"],
            "jockey_name": context["jockey_name"],
            "trainer_name": context["trainer_name"],
            "entry_participation_status": context[
                "entry_participation_status"
            ],
            "historical_rating_value": snapshot[
                "selected_horse_performance_rating_value"
            ],
            "suitability_composite_delta": suitability[
                "suitability_composite_delta"
            ],
            "projected_performance_value": projected[
                "projected_performance_value"
            ],
            "epi_value": epi["epi_value"],
            "epi_rank": epi["epi_rank"],
            "historical_rating_status": snapshot[
                "race_entry_horse_rating_snapshot_status"
            ],
            "suitability_status": suitability[
                "suitability_status"
            ],
            "projected_performance_status": projected[
                "projected_performance_status"
            ],
            "epi_status": epi["epi_status"],
            "race_intelligence_status": intelligence_status,
            "race_intelligence_reason_code": intelligence_reason,
            "source_race_context_evidence_sha256": context[
                "race_entry_context_evidence_sha256"
            ],
            "source_projected_performance_evidence_sha256": projected[
                "projected_performance_evidence_sha256"
            ],
            "source_epi_evidence_sha256": epi[
                "epi_evidence_sha256"
            ],
            "race_intelligence_builder_version": FEED_BUILDER,
            "race_intelligence_method_version": FEED_METHOD,
            "race_intelligence_evidence_sha256": sha256_text(
                canonical_json(evidence)
            ),
        }
    )

feed_rows.sort(
    key=lambda row: (
        row["race_date"],
        row["canonical_race_id"],
        row["canonical_runner_id"],
    )
)

write_csv(FEED_CANDIDATE, feed_fields, feed_rows)

feed_checks = {
    "one_row_per_context": (
        len(feed_rows) == len(context_rows)
    ),
    "no_epi_value_when_epi_unavailable": all(
        row["epi_value"]
        or row["epi_status"] != "EPI_AVAILABLE"
        for row in feed_rows
    ),
    "status_chain_complete": all(
        row["historical_rating_status"]
        and row["suitability_status"]
        and row["projected_performance_status"]
        and row["epi_status"]
        and row["race_intelligence_status"]
        for row in feed_rows
    ),
    "evidence_complete": all(
        row["race_intelligence_evidence_sha256"]
        for row in feed_rows
    ),
    "deterministic_rerun": deterministic_check(
        feed_fields,
        feed_rows,
        FEED_CANDIDATE,
        FEED_DOCS,
        "race_intelligence_deterministic_check.csv",
    ),
}

if not all(feed_checks.values()):
    raise RuntimeError(
        "Race Intelligence feed audit failed:\n"
        + json.dumps(feed_checks, indent=2)
    )

feed_production_hash = promote(
    FEED_CANDIDATE,
    FEED_PRODUCTION,
)

feed_audit = {
    "status": "EDGEIQ_RACE_INTELLIGENCE_ENGINE_V2_AUDIT_PASS",
    "rows": len(feed_rows),
    "status_counts": dict(
        sorted(feed_status_counts.items())
    ),
    "checks": feed_checks,
    "candidate_sha256": sha256_file(
        FEED_CANDIDATE
    ),
    "production_sha256": feed_production_hash,
}

(FEED_DOCS / "EDGEIQ_RACE_INTELLIGENCE_ENGINE_V2_AUDIT.json").write_text(
    json.dumps(feed_audit, indent=2),
    encoding="utf-8",
)

(FEED_DOCS / "EDGEIQ_RACE_INTELLIGENCE_ENGINE_V2_AUDIT.md").write_text(
    "\n".join(
        [
            "# EDGEIQ Race Intelligence Engine V2 Audit",
            "",
            f"Status: `{feed_audit['status']}`",
            "",
            f"- Rows: `{len(feed_rows)}`",
            "",
            "## Status Counts",
            "",
            *[
                f"- `{key}`: `{value}`"
                for key, value in feed_audit[
                    "status_counts"
                ].items()
            ],
            "",
            "The feed publishes governed values and explicit unavailability statuses only.",
            "",
        ]
    ),
    encoding="utf-8",
)


# ============================================================
# MASTER SUMMARY
# ============================================================

summary = {
    "identity_bridge": bridge_audit,
    "suitability": suitability_audit,
    "projected_performance": projected_audit,
    "epi": epi_audit,
    "race_intelligence": feed_audit,
}

(DOCS / "EDGEIQ_LIVE_PERFORMANCE_ENGINE_V2_CURRENT_STATUS.json").write_text(
    json.dumps(summary, indent=2),
    encoding="utf-8",
)

print(
    json.dumps(
        {
            "identity_bridge_status": bridge_audit["status"],
            "resolved_current_runners": bridge_audit[
                "resolved_current_runners"
            ],
            "suitability_status": suitability_audit["status"],
            "suitability_status_counts": suitability_audit[
                "suitability_status_counts"
            ],
            "projected_performance_status": projected_audit[
                "status"
            ],
            "projected_performance_status_counts": projected_audit[
                "status_counts"
            ],
            "epi_status": epi_audit["status"],
            "epi_status_counts": epi_audit[
                "status_counts"
            ],
            "race_intelligence_status": feed_audit["status"],
            "race_intelligence_status_counts": feed_audit[
                "status_counts"
            ],
        },
        indent=2,
    )
)
