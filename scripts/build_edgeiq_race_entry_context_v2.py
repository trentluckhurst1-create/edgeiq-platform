from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

RACE_ENTRY_PATH = (
    ROOT / "public" / "data" / "edgeiq_race_entry_fact_v1.csv"
)

SNAPSHOT_PATH = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_race_entry_horse_rating_snapshot_v2.csv"
)

CANDIDATE_PATH = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_race_entry_context_v2_CANDIDATE.csv"
)

PRODUCTION_PATH = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_race_entry_context_v2.csv"
)

REPORT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "live-performance-engine-v2"
    / "stage-2-race-context"
)

REPORT_DIR.mkdir(parents=True, exist_ok=True)

AUDIT_JSON = (
    REPORT_DIR
    / "EDGEIQ_RACE_ENTRY_CONTEXT_V2_AUDIT.json"
)

AUDIT_MD = (
    REPORT_DIR
    / "EDGEIQ_RACE_ENTRY_CONTEXT_V2_AUDIT.md"
)

CONTRACT_JSON = (
    REPORT_DIR
    / "edgeiq_race_entry_context_v2_contract.json"
)

BUILDER_VERSION = "EDGEIQ_RACE_ENTRY_CONTEXT_V2"
METHOD_VERSION = "FACTUAL_DECLARED_RACE_CONTEXT_ONLY_V1"

OUTPUT_FIELDS = [
    "race_entry_context_id",
    "canonical_race_id",
    "canonical_runner_id",
    "canonical_horse_id",
    "canonical_horse_name",
    "race_date",
    "meeting_date",
    "canonical_track",
    "course_identity",
    "state",
    "country",
    "race_number",
    "race_name",
    "scheduled_start_time",
    "race_distance_metres",
    "surface_group",
    "track_condition_number",
    "saddlecloth_number",
    "barrier",
    "weight_kg",
    "jockey_name",
    "trainer_name",
    "declared_field_size",
    "active_field_size",
    "declaration_status",
    "scratching_status",
    "entry_participation_status",
    "race_class_code",
    "race_class_context_status",
    "rail_position",
    "rail_context_status",
    "track_context_status",
    "distance_context_status",
    "surface_context_status",
    "track_condition_context_status",
    "barrier_context_status",
    "weight_context_status",
    "horse_rating_snapshot_status",
    "historical_rating_available",
    "selected_horse_performance_rating_value",
    "selected_rating_as_of_date",
    "race_entry_context_status",
    "race_entry_context_reason_code",
    "source_race_entry_evidence_sha256",
    "source_horse_rating_snapshot_evidence_sha256",
    "context_builder_version",
    "context_method_version",
    "race_entry_context_evidence_sha256",
]


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


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


def parse_number(value: str) -> float | None:
    value = clean(value)

    if not value:
        return None

    try:
        number = float(value)
    except ValueError:
        return None

    if number != number:
        return None

    if number in (float("inf"), float("-inf")):
        return None

    return number


def participation_status(row: dict[str, str]) -> str:
    declaration = clean(
        row.get("declaration_status", "")
    ).upper()

    scratching = clean(
        row.get("scratching_status", "")
    ).upper()

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
        "ACCEPTED",
        "DECLARED",
        "FINAL_FIELD",
        "STARTER",
    }:
        return "ACTIVE"

    if declaration:
        return declaration

    return "DECLARED_STATUS_UNSPECIFIED"


def context_status(
    value: str,
    numeric: bool = False,
    positive: bool = False,
) -> str:
    value = clean(value)

    if not value:
        return "CONTEXT_UNAVAILABLE"

    if numeric:
        number = parse_number(value)

        if number is None:
            return "CONTEXT_INVALID"

        if positive and number <= 0:
            return "CONTEXT_INVALID"

    return "FACTUAL_CONTEXT_AVAILABLE"


def main() -> None:
    race_fields, race_rows = read_csv(RACE_ENTRY_PATH)
    snapshot_fields, snapshot_rows = read_csv(SNAPSHOT_PATH)

    required_race_fields = {
        "canonical_race_id",
        "canonical_runner_id",
        "race_date",
        "canonical_track",
        "race_distance_metres",
        "surface_group",
        "track_condition_number",
        "runner_name",
        "barrier",
        "weight_kg",
        "declaration_status",
        "scratching_status",
    }

    missing_required = sorted(
        required_race_fields - set(race_fields)
    )

    if missing_required:
        raise RuntimeError(
            "Current race-entry fact is missing required fields: "
            + ", ".join(missing_required)
        )

    required_snapshot_fields = {
        "canonical_race_id",
        "canonical_runner_id",
        "race_entry_horse_rating_snapshot_status",
        "selected_horse_performance_rating_value",
        "selected_rating_as_of_date",
        "race_entry_horse_rating_snapshot_evidence_sha256",
    }

    missing_snapshot = sorted(
        required_snapshot_fields - set(snapshot_fields)
    )

    if missing_snapshot:
        raise RuntimeError(
            "Stage 1 snapshot is missing required fields: "
            + ", ".join(missing_snapshot)
        )

    snapshot_lookup: dict[tuple[str, str], dict[str, str]] = {}

    for row in snapshot_rows:
        key = (
            row["canonical_race_id"],
            row["canonical_runner_id"],
        )

        if key in snapshot_lookup:
            raise RuntimeError(
                f"Duplicate Stage 1 snapshot key: {key}"
            )

        snapshot_lookup[key] = row

    declared_counts: Counter[str] = Counter()
    active_counts: Counter[str] = Counter()

    for row in race_rows:
        race_id = row["canonical_race_id"]
        declared_counts[race_id] += 1

        if participation_status(row) == "ACTIVE":
            active_counts[race_id] += 1

    output_rows: list[dict[str, str]] = []
    context_status_counts: Counter[str] = Counter()
    participation_counts: Counter[str] = Counter()

    for entry in race_rows:
        race_id = entry["canonical_race_id"]
        runner_id = entry["canonical_runner_id"]
        key = (race_id, runner_id)

        snapshot = snapshot_lookup.get(key)

        if snapshot is None:
            raise RuntimeError(
                "Missing Stage 1 snapshot for race-entry key: "
                f"{key}"
            )

        participation = participation_status(entry)
        participation_counts[participation] += 1

        track_status = context_status(
            entry.get("canonical_track", "")
        )

        distance_status = context_status(
            entry.get("race_distance_metres", ""),
            numeric=True,
            positive=True,
        )

        surface_status = context_status(
            entry.get("surface_group", "")
        )

        condition_status = context_status(
            entry.get("track_condition_number", ""),
            numeric=True,
            positive=True,
        )

        barrier_status = context_status(
            entry.get("barrier", ""),
            numeric=True,
            positive=True,
        )

        weight_status = context_status(
            entry.get("weight_kg", ""),
            numeric=True,
            positive=True,
        )

        factual_required_statuses = [
            track_status,
            distance_status,
            surface_status,
            condition_status,
            barrier_status,
            weight_status,
        ]

        invalid_required = any(
            status == "CONTEXT_INVALID"
            for status in factual_required_statuses
        )

        missing_required_context = any(
            status == "CONTEXT_UNAVAILABLE"
            for status in factual_required_statuses
        )

        if participation == "SCRATCHED":
            overall_status = "RACE_CONTEXT_RECORDED_ENTRY_INACTIVE"
            reason_code = "SCRATCHED_ENTRY_CONTEXT_RETAINED"

        elif invalid_required:
            overall_status = "RACE_CONTEXT_INVALID"
            reason_code = "INVALID_FACTUAL_RACE_CONTEXT"

        elif missing_required_context:
            overall_status = "RACE_CONTEXT_PARTIAL"
            reason_code = "REQUIRED_FACTUAL_CONTEXT_UNAVAILABLE"

        else:
            overall_status = "RACE_CONTEXT_AVAILABLE"
            reason_code = "REQUIRED_FACTUAL_CONTEXT_COMPLETE"

        context_status_counts[overall_status] += 1

        snapshot_status = snapshot[
            "race_entry_horse_rating_snapshot_status"
        ]

        historical_rating_available = (
            "TRUE"
            if snapshot_status
            == "POINT_IN_TIME_HISTORICAL_RATING_AVAILABLE"
            else "FALSE"
        )

        race_class_code = ""
        rail_position = ""

        source_entry_hash = clean(
            entry.get("source_hash", "")
        )

        if not source_entry_hash:
            source_entry_hash = sha256_text(
                canonical_json(entry)
            )

        source_snapshot_hash = snapshot[
            "race_entry_horse_rating_snapshot_evidence_sha256"
        ]

        context_id = sha256_text(
            canonical_json(
                {
                    "race_id": race_id,
                    "runner_id": runner_id,
                    "race_date": entry["race_date"],
                    "method": METHOD_VERSION,
                }
            )
        )

        evidence_payload = {
            "context_id": context_id,
            "race_id": race_id,
            "runner_id": runner_id,
            "race_date": entry["race_date"],
            "track": entry.get("canonical_track", ""),
            "distance": entry.get(
                "race_distance_metres",
                "",
            ),
            "surface": entry.get("surface_group", ""),
            "track_condition": entry.get(
                "track_condition_number",
                "",
            ),
            "barrier": entry.get("barrier", ""),
            "weight": entry.get("weight_kg", ""),
            "declared_field_size": declared_counts[race_id],
            "active_field_size": active_counts[race_id],
            "participation": participation,
            "overall_status": overall_status,
            "reason": reason_code,
            "entry_hash": source_entry_hash,
            "snapshot_hash": source_snapshot_hash,
        }

        output_rows.append(
            {
                "race_entry_context_id": context_id,
                "canonical_race_id": race_id,
                "canonical_runner_id": runner_id,
                "canonical_horse_id": runner_id,
                "canonical_horse_name": entry.get(
                    "runner_name",
                    "",
                ),
                "race_date": entry.get("race_date", ""),
                "meeting_date": entry.get(
                    "meeting_date",
                    "",
                ),
                "canonical_track": entry.get(
                    "canonical_track",
                    "",
                ),
                "course_identity": entry.get(
                    "course_identity",
                    "",
                ),
                "state": entry.get("state", ""),
                "country": entry.get("country", ""),
                "race_number": entry.get(
                    "race_number",
                    "",
                ),
                "race_name": entry.get("race_name", ""),
                "scheduled_start_time": entry.get(
                    "scheduled_start_time",
                    "",
                ),
                "race_distance_metres": entry.get(
                    "race_distance_metres",
                    "",
                ),
                "surface_group": entry.get(
                    "surface_group",
                    "",
                ),
                "track_condition_number": entry.get(
                    "track_condition_number",
                    "",
                ),
                "saddlecloth_number": entry.get(
                    "saddlecloth_number",
                    "",
                ),
                "barrier": entry.get("barrier", ""),
                "weight_kg": entry.get("weight_kg", ""),
                "jockey_name": entry.get(
                    "jockey_name",
                    "",
                ),
                "trainer_name": entry.get(
                    "trainer_name",
                    "",
                ),
                "declared_field_size": str(
                    declared_counts[race_id]
                ),
                "active_field_size": str(
                    active_counts[race_id]
                ),
                "declaration_status": entry.get(
                    "declaration_status",
                    "",
                ),
                "scratching_status": entry.get(
                    "scratching_status",
                    "",
                ),
                "entry_participation_status": participation,
                "race_class_code": race_class_code,
                "race_class_context_status": (
                    "CONTEXT_UNAVAILABLE_NOT_IN_CURRENT_RACE_ENTRY_SCHEMA"
                ),
                "rail_position": rail_position,
                "rail_context_status": (
                    "CONTEXT_UNAVAILABLE_NOT_IN_CURRENT_RACE_ENTRY_SCHEMA"
                ),
                "track_context_status": track_status,
                "distance_context_status": distance_status,
                "surface_context_status": surface_status,
                "track_condition_context_status": condition_status,
                "barrier_context_status": barrier_status,
                "weight_context_status": weight_status,
                "horse_rating_snapshot_status": snapshot_status,
                "historical_rating_available": (
                    historical_rating_available
                ),
                "selected_horse_performance_rating_value": (
                    snapshot[
                        "selected_horse_performance_rating_value"
                    ]
                ),
                "selected_rating_as_of_date": snapshot[
                    "selected_rating_as_of_date"
                ],
                "race_entry_context_status": overall_status,
                "race_entry_context_reason_code": reason_code,
                "source_race_entry_evidence_sha256": (
                    source_entry_hash
                ),
                "source_horse_rating_snapshot_evidence_sha256": (
                    source_snapshot_hash
                ),
                "context_builder_version": BUILDER_VERSION,
                "context_method_version": METHOD_VERSION,
                "race_entry_context_evidence_sha256": (
                    sha256_text(
                        canonical_json(evidence_payload)
                    )
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

    CANDIDATE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with CANDIDATE_PATH.open(
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

    candidate_hash_1 = sha256_file(CANDIDATE_PATH)

    # Deterministic in-memory rewrite check.
    deterministic_copy = (
        REPORT_DIR
        / "edgeiq_race_entry_context_v2_deterministic_check.csv"
    )

    with deterministic_copy.open(
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

    candidate_hash_2 = sha256_file(deterministic_copy)

    natural_keys = [
        (
            row["canonical_race_id"],
            row["canonical_runner_id"],
        )
        for row in output_rows
    ]

    context_ids = [
        row["race_entry_context_id"]
        for row in output_rows
    ]

    fake_rating_rows = [
        row
        for row in output_rows
        if row["historical_rating_available"] == "FALSE"
        and row[
            "selected_horse_performance_rating_value"
        ]
    ]

    checks = {
        "race_entry_schema_valid": not missing_required,
        "stage_1_snapshot_schema_valid": not missing_snapshot,
        "one_context_per_race_entry": (
            len(output_rows) == len(race_rows)
        ),
        "natural_keys_unique": (
            len(natural_keys) == len(set(natural_keys))
        ),
        "context_ids_unique": (
            len(context_ids) == len(set(context_ids))
            and all(context_ids)
        ),
        "snapshot_population_join_exact": (
            len(snapshot_lookup) == len(race_rows)
        ),
        "field_sizes_positive": all(
            int(row["declared_field_size"]) > 0
            for row in output_rows
        ),
        "active_field_not_above_declared": all(
            int(row["active_field_size"])
            <= int(row["declared_field_size"])
            for row in output_rows
        ),
        "no_fake_historical_rating": (
            len(fake_rating_rows) == 0
        ),
        "evidence_complete": all(
            row["source_race_entry_evidence_sha256"]
            and row[
                "source_horse_rating_snapshot_evidence_sha256"
            ]
            and row[
                "race_entry_context_evidence_sha256"
            ]
            for row in output_rows
        ),
        "deterministic_rerun": (
            candidate_hash_1 == candidate_hash_2
        ),
    }

    audit_pass = all(checks.values())

    audit = {
        "status": (
            "EDGEIQ_RACE_ENTRY_CONTEXT_V2_AUDIT_PASS"
            if audit_pass
            else "EDGEIQ_RACE_ENTRY_CONTEXT_V2_AUDIT_FAIL"
        ),
        "builder_version": BUILDER_VERSION,
        "method_version": METHOD_VERSION,
        "race_entry_rows": len(race_rows),
        "snapshot_rows": len(snapshot_rows),
        "context_rows": len(output_rows),
        "participation_status_counts": dict(
            sorted(participation_counts.items())
        ),
        "context_status_counts": dict(
            sorted(context_status_counts.items())
        ),
        "checks": checks,
        "candidate_sha256": candidate_hash_1,
    }

    contract = {
        "contract_name": "edgeiq_race_entry_context_v2",
        "contract_version": "V2",
        "grain": "ONE_ROW_PER_CANONICAL_RACE_AND_RUNNER",
        "purpose": (
            "FACTUAL LIVE RACE CONTEXT ONLY; "
            "NO SUITABILITY OR PROJECTION CALCULATION"
        ),
        "primary_key": [
            "canonical_race_id",
            "canonical_runner_id",
        ],
        "builder_version": BUILDER_VERSION,
        "method_version": METHOD_VERSION,
        "fields": OUTPUT_FIELDS,
        "unavailable_context_policy": (
            "LEAVE VALUE BLANK AND PUBLISH EXPLICIT STATUS"
        ),
    }

    CONTRACT_JSON.write_text(
        json.dumps(contract, indent=2),
        encoding="utf-8",
    )

    AUDIT_JSON.write_text(
        json.dumps(audit, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# EDGEIQ Race-Entry Context V2 Audit",
        "",
        f"Status: `{audit['status']}`",
        "",
        "## Population",
        "",
        f"- Race-entry rows: `{len(race_rows)}`",
        f"- Stage 1 snapshot rows: `{len(snapshot_rows)}`",
        f"- Context rows: `{len(output_rows)}`",
        "",
        "## Participation",
        "",
    ]

    for key, value in audit[
        "participation_status_counts"
    ].items():
        lines.append(f"- `{key}`: `{value}`")

    lines.extend(
        [
            "",
            "## Context Status",
            "",
        ]
    )

    for key, value in audit[
        "context_status_counts"
    ].items():
        lines.append(f"- `{key}`: `{value}`")

    lines.extend(
        [
            "",
            "## Audit Checks",
            "",
        ]
    )

    for key, value in checks.items():
        lines.append(
            f"- `{key}`: `{'PASS' if value else 'FAIL'}`"
        )

    lines.extend(
        [
            "",
            "## Governance",
            "",
            f"- Builder: `{BUILDER_VERSION}`",
            f"- Method: `{METHOD_VERSION}`",
            "- This stage records factual race context only.",
            "- Class and rail remain explicitly unavailable because they are absent from the current canonical race-entry schema.",
            "- No context value is estimated or inferred.",
            "- No suitability, projected performance or EPI is calculated in this stage.",
            f"- Candidate SHA256: `{candidate_hash_1}`",
            "",
        ]
    )

    AUDIT_MD.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    deterministic_copy.unlink(missing_ok=True)

    if not audit_pass:
        print(json.dumps(audit, indent=2))
        raise SystemExit(1)

    temp_path = PRODUCTION_PATH.with_suffix(
        PRODUCTION_PATH.suffix + ".tmp"
    )

    shutil.copy2(CANDIDATE_PATH, temp_path)
    os.replace(temp_path, PRODUCTION_PATH)

    production_hash = sha256_file(PRODUCTION_PATH)

    if production_hash != candidate_hash_1:
        raise RuntimeError(
            "Production promotion hash mismatch."
        )

    audit["production_sha256"] = production_hash
    audit["promotion_status"] = "ATOMIC_PROMOTION_PASS"

    AUDIT_JSON.write_text(
        json.dumps(audit, indent=2),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "status": audit["status"],
                "context_rows": len(output_rows),
                "participation_status_counts": audit[
                    "participation_status_counts"
                ],
                "context_status_counts": audit[
                    "context_status_counts"
                ],
                "candidate_sha256": candidate_hash_1,
                "production_sha256": production_hash,
                "production_path": str(PRODUCTION_PATH),
                "audit_report": str(AUDIT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
