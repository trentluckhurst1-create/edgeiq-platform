from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

RACE_ENTRY_PATH = ROOT / "public" / "data" / "edgeiq_race_entry_fact_v1.csv"
RATING_PATH = ROOT / "public" / "data" / "edgeiq_horse_performance_rating_fact_v1.csv"

CANDIDATE_PATH = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_race_entry_horse_rating_snapshot_v2_CANDIDATE.csv"
)

PRODUCTION_PATH = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_race_entry_horse_rating_snapshot_v2.csv"
)

REPORT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "live-performance-engine-v2"
    / "stage-1-horse-rating-snapshot"
)

REPORT_DIR.mkdir(parents=True, exist_ok=True)

AUDIT_JSON = REPORT_DIR / "EDGEIQ_RACE_ENTRY_HORSE_RATING_SNAPSHOT_V2_AUDIT.json"
AUDIT_MD = REPORT_DIR / "EDGEIQ_RACE_ENTRY_HORSE_RATING_SNAPSHOT_V2_AUDIT.md"
CONTRACT_JSON = REPORT_DIR / "edgeiq_race_entry_horse_rating_snapshot_v2_contract.json"

BUILDER_VERSION = "EDGEIQ_RACE_ENTRY_HORSE_RATING_SNAPSHOT_V2"
METHOD_VERSION = "STRICTLY_PRIOR_LATEST_GOVERNED_HORSE_RATING_V1"


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


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalise_name(value: str) -> str:
    return " ".join(clean(value).upper().split())


def parse_date(value: str) -> date | None:
    value = clean(value)
    if not value:
        return None

    candidates = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
    )

    trimmed = value.replace("Z", "")

    for fmt in candidates:
        try:
            return datetime.strptime(trimmed, fmt).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(trimmed).date()
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
    if parsed != parsed or parsed in (float("inf"), float("-inf")):
        return None
    return parsed


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise FileNotFoundError(f"Required file missing: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = [
            {key: clean(value) for key, value in row.items()}
            for row in reader
        ]

    return fieldnames, rows


def first_existing(
    fieldnames: list[str],
    aliases: list[str],
    required: bool = True,
) -> str | None:
    lower_lookup = {name.lower(): name for name in fieldnames}

    for alias in aliases:
        if alias.lower() in lower_lookup:
            return lower_lookup[alias.lower()]

    if required:
        raise KeyError(
            "None of the required columns were found: "
            + ", ".join(aliases)
        )

    return None


def choose_columns(
    race_fields: list[str],
    rating_fields: list[str],
) -> dict[str, str | None]:
    return {
        "entry_race_id": first_existing(
            race_fields,
            ["canonical_race_id", "race_id", "race_key"],
        ),
        "entry_runner_id": first_existing(
            race_fields,
            ["canonical_runner_id", "runner_id", "canonical_horse_id"],
        ),
        "entry_race_date": first_existing(
            race_fields,
            ["race_date", "meeting_date", "target_race_date"],
        ),
        "entry_runner_name": first_existing(
            race_fields,
            ["runner_name", "canonical_horse_name", "horse_name"],
            required=False,
        ),
        "entry_declaration_status": first_existing(
            race_fields,
            ["declaration_status", "entry_status", "runner_status"],
            required=False,
        ),
        "entry_scratching_status": first_existing(
            race_fields,
            ["scratching_status", "scratch_status"],
            required=False,
        ),
        "entry_source_hash": first_existing(
            race_fields,
            ["source_hash", "race_entry_evidence_sha256"],
            required=False,
        ),
        "rating_horse_id": first_existing(
            rating_fields,
            [
                "canonical_horse_id",
                "canonical_runner_id",
                "runner_id",
            ],
        ),
        "rating_horse_name": first_existing(
            rating_fields,
            ["canonical_horse_name", "runner_name", "horse_name"],
            required=False,
        ),
        "rating_as_of_date": first_existing(
            rating_fields,
            [
                "rating_as_of_date",
                "aggregate_as_of_date",
                "as_of_date",
                "race_date",
            ],
        ),
        "rating_value": first_existing(
            rating_fields,
            [
                "horse_performance_rating_value",
                "aggregate_rating_value",
                "rating_value",
            ],
        ),
        "rating_id": first_existing(
            rating_fields,
            [
                "horse_performance_rating_id",
                "rating_id",
                "horse_rating_id",
            ],
            required=False,
        ),
        "rating_status": first_existing(
            rating_fields,
            [
                "horse_performance_rating_status",
                "rating_status",
                "status",
                "audit_status",
            ],
            required=False,
        ),
        "rating_method": first_existing(
            rating_fields,
            [
                "horse_performance_rating_method",
                "rating_method",
                "aggregation_method",
            ],
            required=False,
        ),
        "rating_version": first_existing(
            rating_fields,
            [
                "horse_performance_rating_model_version",
                "rating_model_version",
                "aggregation_model_version",
                "builder_version",
            ],
            required=False,
        ),
        "rating_evidence": first_existing(
            rating_fields,
            [
                "horse_performance_rating_evidence_sha256",
                "rating_evidence_sha256",
                "source_evidence_sha256",
                "evidence_sha256",
            ],
            required=False,
        ),
    }


OUTPUT_FIELDS = [
    "race_entry_horse_rating_snapshot_id",
    "canonical_race_id",
    "canonical_runner_id",
    "canonical_horse_id",
    "canonical_horse_name",
    "race_date",
    "selected_horse_performance_rating_id",
    "selected_rating_as_of_date",
    "selected_horse_performance_rating_value",
    "rating_age_days",
    "eligible_prior_rating_count",
    "first_eligible_rating_date",
    "latest_eligible_rating_date",
    "lowest_eligible_rating_value",
    "highest_eligible_rating_value",
    "average_eligible_rating_value",
    "horse_performance_rating_method",
    "horse_performance_rating_model_version",
    "race_entry_horse_rating_snapshot_status",
    "race_entry_horse_rating_snapshot_reason_code",
    "source_race_entry_evidence_sha256",
    "source_selected_rating_evidence_sha256",
    "source_eligible_rating_ids_sha256",
    "snapshot_builder_version",
    "snapshot_method_version",
    "race_entry_horse_rating_snapshot_evidence_sha256",
]


def is_active_entry(
    row: dict[str, str],
    declaration_col: str | None,
    scratching_col: str | None,
) -> bool:
    declaration = clean(row.get(declaration_col or "", "")).upper()
    scratching = clean(row.get(scratching_col or "", "")).upper()

    scratched_values = {
        "SCRATCHED",
        "SCR",
        "WITHDRAWN",
        "REMOVED",
        "TRUE",
        "1",
        "YES",
        "Y",
    }

    inactive_declarations = {
        "SCRATCHED",
        "WITHDRAWN",
        "REMOVED",
        "NOT_DECLARED",
    }

    return (
        scratching not in scratched_values
        and declaration not in inactive_declarations
    )


def rating_is_governed(
    row: dict[str, str],
    status_col: str | None,
) -> bool:
    if not status_col:
        return True

    status = clean(row.get(status_col, "")).upper()

    if not status:
        return True

    blocked_terms = (
        "FAIL",
        "BLOCK",
        "INVALID",
        "UNAVAILABLE",
        "REJECT",
        "INELIGIBLE",
    )

    return not any(term in status for term in blocked_terms)


def build_snapshot() -> dict[str, Any]:
    race_fields, race_rows = read_csv(RACE_ENTRY_PATH)
    rating_fields, rating_rows = read_csv(RATING_PATH)

    columns = choose_columns(race_fields, rating_fields)

    ratings_by_horse: dict[str, list[dict[str, Any]]] = {}

    invalid_rating_rows = 0

    for source_row in rating_rows:
        horse_id = clean(source_row[columns["rating_horse_id"]])
        as_of_date = parse_date(source_row[columns["rating_as_of_date"]])
        value = parse_float(source_row[columns["rating_value"]])

        if (
            not horse_id
            or as_of_date is None
            or value is None
            or not rating_is_governed(
                source_row,
                columns["rating_status"],
            )
        ):
            invalid_rating_rows += 1
            continue

        rating_id = (
            clean(source_row.get(columns["rating_id"] or "", ""))
            or sha256_text(
                canonical_json(
                    {
                        "horse_id": horse_id,
                        "as_of_date": as_of_date.isoformat(),
                        "value": value,
                    }
                )
            )
        )

        ratings_by_horse.setdefault(horse_id, []).append(
            {
                "horse_id": horse_id,
                "horse_name": clean(
                    source_row.get(columns["rating_horse_name"] or "", "")
                ),
                "as_of_date": as_of_date,
                "value": value,
                "rating_id": rating_id,
                "status": clean(
                    source_row.get(columns["rating_status"] or "", "")
                ),
                "method": clean(
                    source_row.get(columns["rating_method"] or "", "")
                ),
                "version": clean(
                    source_row.get(columns["rating_version"] or "", "")
                ),
                "evidence": clean(
                    source_row.get(columns["rating_evidence"] or "", "")
                ),
            }
        )

    for horse_ratings in ratings_by_horse.values():
        horse_ratings.sort(
            key=lambda item: (
                item["as_of_date"],
                item["rating_id"],
            )
        )

    output_rows: list[dict[str, str]] = []
    status_counts: Counter[str] = Counter()
    duplicate_natural_keys: Counter[tuple[str, str]] = Counter()

    for entry in race_rows:
        race_id = clean(entry[columns["entry_race_id"]])
        runner_id = clean(entry[columns["entry_runner_id"]])
        race_date = parse_date(entry[columns["entry_race_date"]])

        if not race_id or not runner_id:
            continue

        natural_key = (race_id, runner_id)
        duplicate_natural_keys[natural_key] += 1

        runner_name = clean(
            entry.get(columns["entry_runner_name"] or "", "")
        )

        source_entry_hash = clean(
            entry.get(columns["entry_source_hash"] or "", "")
        )

        if not source_entry_hash:
            source_entry_hash = sha256_text(canonical_json(entry))

        active = is_active_entry(
            entry,
            columns["entry_declaration_status"],
            columns["entry_scratching_status"],
        )

        horse_ratings = ratings_by_horse.get(runner_id, [])

        selected: dict[str, Any] | None = None
        eligible: list[dict[str, Any]] = []

        status = ""
        reason = ""

        if not active:
            status = "ENTRY_INACTIVE"
            reason = "SCRATCHED_OR_WITHDRAWN"

        elif race_date is None:
            status = "SNAPSHOT_UNAVAILABLE"
            reason = "INVALID_TARGET_RACE_DATE"

        elif not horse_ratings:
            status = "SNAPSHOT_UNAVAILABLE"
            reason = "NO_GOVERNED_HISTORICAL_RATING"

        else:
            eligible = [
                rating
                for rating in horse_ratings
                if rating["as_of_date"] < race_date
            ]

            if not eligible:
                status = "SNAPSHOT_UNAVAILABLE"
                reason = "NO_STRICTLY_PRIOR_GOVERNED_RATING"
            else:
                selected = eligible[-1]
                status = "POINT_IN_TIME_HISTORICAL_RATING_AVAILABLE"
                reason = "LATEST_STRICTLY_PRIOR_GOVERNED_RATING_SELECTED"

        status_counts[status] += 1

        eligible_values = [item["value"] for item in eligible]
        eligible_dates = [item["as_of_date"] for item in eligible]
        eligible_ids = [item["rating_id"] for item in eligible]

        selected_id = selected["rating_id"] if selected else ""
        selected_date = (
            selected["as_of_date"].isoformat()
            if selected
            else ""
        )
        selected_value = (
            f'{selected["value"]:.12f}'
            if selected
            else ""
        )
        rating_age_days = (
            str((race_date - selected["as_of_date"]).days)
            if selected and race_date
            else ""
        )

        average_value = (
            sum(eligible_values) / len(eligible_values)
            if eligible_values
            else None
        )

        snapshot_id = sha256_text(
            canonical_json(
                {
                    "race_id": race_id,
                    "runner_id": runner_id,
                    "race_date": race_date.isoformat() if race_date else "",
                    "method": METHOD_VERSION,
                }
            )
        )

        evidence_payload = {
            "snapshot_id": snapshot_id,
            "race_id": race_id,
            "runner_id": runner_id,
            "race_date": race_date.isoformat() if race_date else "",
            "selected_rating_id": selected_id,
            "selected_rating_date": selected_date,
            "selected_rating_value": selected_value,
            "status": status,
            "reason": reason,
            "source_entry_hash": source_entry_hash,
            "source_rating_evidence": selected["evidence"] if selected else "",
        }

        output_rows.append(
            {
                "race_entry_horse_rating_snapshot_id": snapshot_id,
                "canonical_race_id": race_id,
                "canonical_runner_id": runner_id,
                "canonical_horse_id": runner_id,
                "canonical_horse_name": (
                    runner_name
                    or (selected["horse_name"] if selected else "")
                ),
                "race_date": race_date.isoformat() if race_date else "",
                "selected_horse_performance_rating_id": selected_id,
                "selected_rating_as_of_date": selected_date,
                "selected_horse_performance_rating_value": selected_value,
                "rating_age_days": rating_age_days,
                "eligible_prior_rating_count": str(len(eligible)),
                "first_eligible_rating_date": (
                    min(eligible_dates).isoformat()
                    if eligible_dates
                    else ""
                ),
                "latest_eligible_rating_date": (
                    max(eligible_dates).isoformat()
                    if eligible_dates
                    else ""
                ),
                "lowest_eligible_rating_value": (
                    f"{min(eligible_values):.12f}"
                    if eligible_values
                    else ""
                ),
                "highest_eligible_rating_value": (
                    f"{max(eligible_values):.12f}"
                    if eligible_values
                    else ""
                ),
                "average_eligible_rating_value": (
                    f"{average_value:.12f}"
                    if average_value is not None
                    else ""
                ),
                "horse_performance_rating_method": (
                    selected["method"] if selected else ""
                ),
                "horse_performance_rating_model_version": (
                    selected["version"] if selected else ""
                ),
                "race_entry_horse_rating_snapshot_status": status,
                "race_entry_horse_rating_snapshot_reason_code": reason,
                "source_race_entry_evidence_sha256": source_entry_hash,
                "source_selected_rating_evidence_sha256": (
                    selected["evidence"] if selected else ""
                ),
                "source_eligible_rating_ids_sha256": sha256_text(
                    canonical_json(sorted(eligible_ids))
                ),
                "snapshot_builder_version": BUILDER_VERSION,
                "snapshot_method_version": METHOD_VERSION,
                "race_entry_horse_rating_snapshot_evidence_sha256": (
                    sha256_text(canonical_json(evidence_payload))
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

    CANDIDATE_PATH.parent.mkdir(parents=True, exist_ok=True)

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

    duplicate_count = sum(
        count - 1
        for count in duplicate_natural_keys.values()
        if count > 1
    )

    active_entries = sum(
        1
        for entry in race_rows
        if is_active_entry(
            entry,
            columns["entry_declaration_status"],
            columns["entry_scratching_status"],
        )
    )

    candidate_hash = sha256_file(CANDIDATE_PATH)

    return {
        "status": "CANDIDATE_BUILT",
        "builder_version": BUILDER_VERSION,
        "method_version": METHOD_VERSION,
        "race_entry_rows": len(race_rows),
        "active_race_entry_rows": active_entries,
        "rating_source_rows": len(rating_rows),
        "valid_rating_rows": sum(len(v) for v in ratings_by_horse.values()),
        "invalid_rating_rows": invalid_rating_rows,
        "snapshot_rows": len(output_rows),
        "status_counts": dict(sorted(status_counts.items())),
        "duplicate_race_runner_rows": duplicate_count,
        "candidate_path": str(CANDIDATE_PATH.relative_to(ROOT)),
        "candidate_sha256": candidate_hash,
        "resolved_columns": columns,
    }


def audit_snapshot(build_result: dict[str, Any]) -> dict[str, Any]:
    fields, rows = read_csv(CANDIDATE_PATH)

    required_fields_present = all(
        field in fields
        for field in OUTPUT_FIELDS
    )

    natural_keys = [
        (
            row["canonical_race_id"],
            row["canonical_runner_id"],
        )
        for row in rows
    ]

    natural_keys_unique = len(natural_keys) == len(set(natural_keys))

    snapshot_ids = [
        row["race_entry_horse_rating_snapshot_id"]
        for row in rows
    ]

    snapshot_ids_unique = (
        len(snapshot_ids) == len(set(snapshot_ids))
        and all(snapshot_ids)
    )

    temporal_violations = 0
    invalid_selected_values = 0
    invalid_available_rows = 0
    invalid_unavailable_rows = 0

    for row in rows:
        status = row["race_entry_horse_rating_snapshot_status"]
        race_date = parse_date(row["race_date"])
        selected_date = parse_date(row["selected_rating_as_of_date"])
        selected_value = parse_float(
            row["selected_horse_performance_rating_value"]
        )

        available = (
            status
            == "POINT_IN_TIME_HISTORICAL_RATING_AVAILABLE"
        )

        if available:
            if (
                race_date is None
                or selected_date is None
                or selected_date >= race_date
            ):
                temporal_violations += 1

            if selected_value is None:
                invalid_selected_values += 1

            if not row["selected_horse_performance_rating_id"]:
                invalid_available_rows += 1
        else:
            if (
                row["selected_horse_performance_rating_id"]
                or row["selected_rating_as_of_date"]
                or row["selected_horse_performance_rating_value"]
            ):
                invalid_unavailable_rows += 1

    evidence_complete = all(
        row["race_entry_horse_rating_snapshot_evidence_sha256"]
        and row["source_race_entry_evidence_sha256"]
        and row["snapshot_builder_version"] == BUILDER_VERSION
        and row["snapshot_method_version"] == METHOD_VERSION
        for row in rows
    )

    row_population_exact = (
        len(rows) == build_result["race_entry_rows"]
    )

    checks = {
        "required_fields_present": required_fields_present,
        "row_population_exact": row_population_exact,
        "natural_keys_unique": natural_keys_unique,
        "snapshot_ids_unique": snapshot_ids_unique,
        "strictly_prior_temporal_rule": temporal_violations == 0,
        "selected_values_finite": invalid_selected_values == 0,
        "available_rows_complete": invalid_available_rows == 0,
        "unavailable_rows_have_no_fake_rating": (
            invalid_unavailable_rows == 0
        ),
        "evidence_complete": evidence_complete,
        "candidate_hash_matches": (
            sha256_file(CANDIDATE_PATH)
            == build_result["candidate_sha256"]
        ),
    }

    audit_pass = all(checks.values())

    result = {
        "status": (
            "EDGEIQ_RACE_ENTRY_HORSE_RATING_SNAPSHOT_V2_AUDIT_PASS"
            if audit_pass
            else "EDGEIQ_RACE_ENTRY_HORSE_RATING_SNAPSHOT_V2_AUDIT_FAIL"
        ),
        "checks": checks,
        "rows": len(rows),
        "temporal_violations": temporal_violations,
        "invalid_selected_values": invalid_selected_values,
        "invalid_available_rows": invalid_available_rows,
        "invalid_unavailable_rows": invalid_unavailable_rows,
        "candidate_sha256": sha256_file(CANDIDATE_PATH),
        "build": build_result,
    }

    return result


def write_contract() -> None:
    contract = {
        "contract_name": "edgeiq_race_entry_horse_rating_snapshot_v2",
        "contract_version": "V2",
        "grain": "ONE_ROW_PER_CANONICAL_RACE_AND_RUNNER",
        "builder_version": BUILDER_VERSION,
        "method_version": METHOD_VERSION,
        "temporal_rule": "RATING_AS_OF_DATE_STRICTLY_PRIOR_TO_TARGET_RACE_DATE",
        "availability_rule": "NO_FABRICATED_OR_FALLBACK_RATING",
        "primary_key": [
            "canonical_race_id",
            "canonical_runner_id",
        ],
        "fields": OUTPUT_FIELDS,
    }

    CONTRACT_JSON.write_text(
        json.dumps(contract, indent=2),
        encoding="utf-8",
    )


def write_reports(audit: dict[str, Any]) -> None:
    AUDIT_JSON.write_text(
        json.dumps(audit, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# EDGEIQ Race-Entry Horse Rating Snapshot V2 Audit",
        "",
        f"Status: `{audit['status']}`",
        "",
        "## Row Counts",
        "",
        f"- Race-entry rows: `{audit['build']['race_entry_rows']}`",
        f"- Active entries: `{audit['build']['active_race_entry_rows']}`",
        f"- Horse-rating source rows: `{audit['build']['rating_source_rows']}`",
        f"- Valid horse-rating rows: `{audit['build']['valid_rating_rows']}`",
        f"- Snapshot rows: `{audit['rows']}`",
        "",
        "## Snapshot Status Counts",
        "",
    ]

    for key, value in audit["build"]["status_counts"].items():
        lines.append(f"- `{key}`: `{value}`")

    lines.extend(
        [
            "",
            "## Audit Checks",
            "",
        ]
    )

    for key, value in audit["checks"].items():
        lines.append(f"- `{key}`: `{'PASS' if value else 'FAIL'}`")

    lines.extend(
        [
            "",
            "## Governance",
            "",
            f"- Builder: `{BUILDER_VERSION}`",
            f"- Method: `{METHOD_VERSION}`",
            "- Temporal rule: rating date must be strictly prior to target race date.",
            "- Missing ratings remain explicitly unavailable.",
            "- No zero, field-average, market-derived or manual rating is created.",
            "",
            f"- Candidate SHA256: `{audit['candidate_sha256']}`",
            "",
        ]
    )

    AUDIT_MD.write_text("\n".join(lines), encoding="utf-8")


def promote(audit: dict[str, Any]) -> str:
    if not audit["status"].endswith("_PASS"):
        raise RuntimeError(
            "Candidate failed audit and was not promoted."
        )

    temp_path = PRODUCTION_PATH.with_suffix(
        PRODUCTION_PATH.suffix + ".tmp"
    )

    shutil.copy2(CANDIDATE_PATH, temp_path)
    os.replace(temp_path, PRODUCTION_PATH)

    return sha256_file(PRODUCTION_PATH)


def deterministic_check() -> dict[str, Any]:
    first_hash = sha256_file(CANDIDATE_PATH)

    second_build = build_snapshot()
    second_hash = sha256_file(CANDIDATE_PATH)

    return {
        "first_hash": first_hash,
        "second_hash": second_hash,
        "pass": first_hash == second_hash,
        "second_build": second_build,
    }


def main() -> None:
    write_contract()

    build_result = build_snapshot()
    audit = audit_snapshot(build_result)

    deterministic = deterministic_check()

    audit["deterministic_rerun"] = deterministic

    if not deterministic["pass"]:
        audit["status"] = (
            "EDGEIQ_RACE_ENTRY_HORSE_RATING_SNAPSHOT_V2_AUDIT_FAIL"
        )
        audit["checks"]["deterministic_rerun"] = False
    else:
        audit["checks"]["deterministic_rerun"] = True

    write_reports(audit)

    if not audit["status"].endswith("_PASS"):
        print(json.dumps(audit, indent=2))
        raise SystemExit(1)

    production_hash = promote(audit)
    audit["production_path"] = str(PRODUCTION_PATH.relative_to(ROOT))
    audit["production_sha256"] = production_hash
    audit["promotion_status"] = "ATOMIC_PROMOTION_PASS"

    write_reports(audit)

    print(
        json.dumps(
            {
                "status": audit["status"],
                "snapshot_rows": audit["rows"],
                "status_counts": audit["build"]["status_counts"],
                "candidate_sha256": audit["candidate_sha256"],
                "production_sha256": production_hash,
                "deterministic_rerun": deterministic["pass"],
                "production_path": str(PRODUCTION_PATH),
                "audit_report": str(AUDIT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
