from __future__ import annotations

import csv
import hashlib
import os
import re
import tempfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

ADJUSTMENT_PATH = (
    DATA
    / "edgeiq_race_entry_context_adjustment_fact_v1.csv"
)

ADJUSTED_PERFORMANCE_PATH = (
    DATA
    / "edgeiq_race_entry_context_adjusted_performance_fact_v1.csv"
)


CURRENT_RACE_ENTRY_PATH = (
    DATA
    / "edgeiq_race_entry_fact_v1.csv"
)

CURRENT_RCOM_TO_EIQ_BRIDGE_PATH = (
    DATA
    / "edgeiq_rcom_to_eiq_horse_identity_bridge_v1.csv"
)

CURRENT_RACE_ENTRY_ADAPTER_VERSION = (
    "edgeiq_race_entry_fact_v1.current_contract_adapter.1.1.0"
)

CURRENT_RESULTS_PATH = (
    DATA
    / "edgeiq_daily_official_results_fact_v1.csv"
)

CURRENT_CROSSWALK_PATH = (
    DATA
    / "edgeiq_current_horse_identity_crosswalk_v1.csv"
)

RA_TO_RCOM_BRIDGE_PATH = (
    DATA
    / "edgeiq_ra_to_rcom_horse_identity_bridge_v1.csv"
)

FORM_GUIDE_PATH = (
    DATA
    / "edgeiq_form_guide_enriched_v2.csv"
)

OUTPUT_PATH = (
    DATA
    / "edgeiq_race_entry_suitability_component_fact_v1.csv"
)

CONTRACT_VERSION = "1.0.0"

BUILDER_VERSION = (
    "edgeiq_race_entry_suitability_component_fact_v1.0.0"
)

CURRENT_BRANCH_BUILDER_VERSION = (
    "edgeiq_ra_to_rcom_bridge_current_performance_rebuild_v1"
)

def current_branch_built_at_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

PERFORMANCE_ADJUSTED = "PERFORMANCE_ADJUSTED"
PARAMETER_NOT_AVAILABLE = "PARAMETER_NOT_AVAILABLE"
CONTEXT_INELIGIBLE = "CONTEXT_INELIGIBLE"

COMPONENT_PUBLISHED = "COMPONENT_PUBLISHED"
COMPONENT_STATUS = "GOVERNED_SUITABILITY_COMPONENT"

COMPONENT_MAPPING = [
    ("DISTANCE", "distance_adjustment"),
    ("CLASS", "class_adjustment"),
    ("TRACK", "track_adjustment"),
    (
        "TRACK_CONFIGURATION",
        "track_configuration_adjustment",
    ),
    (
        "TRACK_CONDITION",
        "track_condition_adjustment",
    ),
    ("SURFACE", "surface_adjustment"),
    ("BARRIER", "barrier_adjustment"),
    ("WEIGHT", "weight_adjustment"),
    ("FIELD_SIZE", "field_size_adjustment"),
]

IDENTITY_FIELDS = [
    "race_entry_context_adjustment_id",
    "race_entry_context_parameter_selection_id",
    "race_entry_context_eligibility_id",
    "race_entry_performance_context_id",
    "race_entry_id",
    "race_id",
    "race_date",
    "runner_id",
    "canonical_horse_id",
    "canonical_horse_name",
    "historical_rating_value",
    "context_parameter_id",
    "total_context_adjustment",
]

OUTPUT_FIELDS = [
    "race_entry_suitability_component_id",
    "race_entry_context_adjusted_performance_id",
    "race_entry_context_adjustment_id",
    "race_entry_context_parameter_selection_id",
    "race_entry_context_eligibility_id",
    "race_entry_performance_context_id",
    "race_entry_id",
    "race_id",
    "race_date",
    "runner_id",
    "canonical_horse_id",
    "canonical_horse_name",
    "historical_rating_value",
    "context_parameter_id",
    "total_context_adjustment",
    "context_adjusted_performance_value",
    "suitability_component_type",
    "source_component_field",
    "suitability_component_value",
    "suitability_component_decision",
    "race_entry_suitability_component_status",
    "source_adjusted_performance_evidence_sha256",
    "source_context_adjustment_evidence_sha256",
    "race_entry_suitability_component_evidence_sha256",
    "source_adjusted_performance_builder_version",
    "source_context_adjustment_builder_version",
    "builder_version",
    "contract_version",
    "built_at_utc",
]


def fail(message: str) -> None:
    raise RuntimeError(message)


def text(value: object) -> str:
    return str(
        value if value is not None else ""
    ).strip()


def sha256_payload(
    parts: Iterable[object],
) -> str:
    payload = "\x1f".join(
        text(part)
        for part in parts
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def parse_required_decimal(
    value: object,
    field_name: str,
) -> Decimal:
    raw = text(value)

    if not raw:
        fail(
            f"Blank required decimal: {field_name}"
        )

    try:
        parsed = Decimal(raw)
    except InvalidOperation as exc:
        raise RuntimeError(
            f"Invalid decimal {field_name}: {raw!r}"
        ) from exc

    if not parsed.is_finite():
        fail(
            f"Non-finite decimal {field_name}: {raw!r}"
        )

    return parsed


def decimal_text(
    value: Decimal,
) -> str:
    if value == 0:
        return "0"

    rendered = format(
        value.normalize(),
        "f",
    )

    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")

    return rendered


def read_csv(
    path: Path,
) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        fail(
            f"Missing canonical input: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            fail(
                f"Missing CSV header: {path}"
            )

        return list(reader.fieldnames), list(reader)


def require_fields(
    path: Path,
    actual: list[str],
    required: Iterable[str],
) -> None:
    missing = [
        field
        for field in required
        if field not in actual
    ]

    if missing:
        fail(
            f"{path.name} missing required fields: {missing}"
        )


def atomic_write_csv(
    path: Path,
    rows: list[dict[str, object]],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )

    os.close(descriptor)
    temporary_path = Path(
        temporary_name
    )

    try:
        with temporary_path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=OUTPUT_FIELDS,
                extrasaction="raise",
                lineterminator="\n",
            )

            writer.writeheader()
            writer.writerows(rows)

        os.replace(
            temporary_path,
            path,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def norm_name(value: str) -> str:
    value = (value or "").upper().strip()
    value = value.replace("Ã¢â‚¬â„¢", "'")
    value = re.sub(r"\s*\(([A-Z]{2,3})\)\s*$", "", value)
    return re.sub(r"[^A-Z0-9]", "", value)


def norm_track(value: str) -> str:
    value = (value or "").upper().strip()
    value = value.replace("BALLARAT SYNTHETIC", "BALLARATSYNTHETIC")
    value = value.replace("SANDOWN HILLSIDE", "SANDOWNHILLSIDE")
    return re.sub(r"[^A-Z0-9]", "", value)


def norm_int(value: str) -> str:
    try:
        return str(int(float(str(value).strip())))
    except (TypeError, ValueError):
        return re.sub(r"[^0-9]", "", str(value or ""))


def current_key(row: dict[str, str]) -> tuple[str, str, str, str, str]:
    return (
        row.get("race_date", "")[:10],
        norm_track(row.get("track", "")),
        norm_int(row.get("race_number", "")),
        norm_int(row.get("runner_source_id", "")),
        norm_name(row.get("runner_name", "")),
    )


def crosswalk_key(row: dict[str, str]) -> tuple[str, str, str, str, str]:
    return (
        row.get("source_meeting_date", "")[:10],
        norm_track(row.get("track", "")),
        norm_int(row.get("race_number", "")),
        norm_int(row.get("saddlecloth", "")),
        norm_name(row.get("source_horse_name", "")),
    )


def row_id(prefix: str, parts: Iterable[object]) -> str:
    return f"{prefix}-{sha256_payload(parts)[:24].upper()}"



def build_current_runner_component_rows() -> list[dict[str, object]]:
    _, current_rows = read_csv(
        CURRENT_RACE_ENTRY_PATH
    )
    _, form_guide_rows = read_csv(
        FORM_GUIDE_PATH
    )

    form_guide_by_runner = {
        (
            row.get("raceDate", "")[:10],
            norm_track(row.get("meeting", "")),
            norm_int(row.get("raceNumber", "")),
            norm_int(row.get("runnerNumber", "")),
            norm_name(row.get("runnerName", "")),
        ): row
        for row in form_guide_rows
    }

    output_rows: list[dict[str, object]] = []
    seen_component_ids: set[str] = set()
    seen_race_entry_ids: set[str] = set()

    declared_rows = [
        row
        for row in current_rows
        if (
            text(row.get("declaration_status"))
            in {"ACTIVE_ENTRY", "EMERGENCY_ENTRY"}
            and text(row.get("scratching_status")) != "SCRATCHED"
        )
    ]

    declared_rows.sort(
        key=lambda row: (
            text(row.get("race_date")),
            norm_track(row.get("canonical_track", "")),
            norm_int(row.get("race_number", "")),
            norm_int(row.get("saddlecloth_number", "")),
            norm_name(row.get("runner_name", "")),
        )
    )

    for entry in declared_rows:
        rcom_id = text(
            entry.get("canonical_runner_id")
        )

        canonical_id = rcom_id

        form_key = (
            text(entry.get("race_date"))[:10],
            norm_track(entry.get("canonical_track", "")),
            norm_int(entry.get("race_number", "")),
            norm_int(entry.get("saddlecloth_number", "")),
            norm_name(entry.get("runner_name", "")),
        )

        form = form_guide_by_runner.get(
            form_key,
            {},
        )

        component_value = text(
            form.get("suitability")
        )

        # Suitability is upstream of current-race EPI/EPR; requiring form.epi here
        # creates a circular dependency and leaves the governed chain empty.
        if not (
            text(form.get("formMomentum"))
            and component_value
            and text(entry.get("barrier"))
        ):
            continue

        canonical_race_id = text(
            entry.get("canonical_race_id")
        )

        source_record_id = text(
            entry.get("source_record_id")
        )

        race_entry_id = (
            "RE1-"
            + sha256_payload(
                [
                    CURRENT_RACE_ENTRY_ADAPTER_VERSION,
                    canonical_race_id,
                    rcom_id,
                    source_record_id,
                ]
            )[:24].upper()
        )

        if race_entry_id in seen_race_entry_ids:
            fail(
                f"Duplicate governed race-entry ID: {race_entry_id}"
            )

        seen_race_entry_ids.add(
            race_entry_id
        )

        component_id = row_id(
            "RESC-CUR",
            [
                race_entry_id,
                canonical_race_id,
                canonical_id,
                component_value,
            ],
        )

        if component_id in seen_component_ids:
            fail(
                f"Duplicate current suitability ID: {component_id}"
            )

        seen_component_ids.add(
            component_id
        )

        projected_id = row_id(
            "REPP-CUR",
            [
                race_entry_id,
                canonical_race_id,
                canonical_id,
                form.get("formMomentum"),
            ],
        )

        projected_evidence = sha256_payload(
            [
                projected_id,
                form.get("formMomentum"),
                "edgeiq_form_guide_enriched_v2",
            ]
        )

        component_evidence = sha256_payload(
            [
                component_id,
                component_value,
            ]
        )

        output_rows.append(
            {
                "race_entry_suitability_component_id": component_id,
                "race_entry_context_adjusted_performance_id": "",
                "race_entry_context_adjustment_id": "",
                "race_entry_context_parameter_selection_id": "",
                "race_entry_context_eligibility_id": "",
                "race_entry_performance_context_id": "",
                "race_entry_id": race_entry_id,
                "race_id": canonical_race_id,
                "race_date": text(entry.get("race_date")),
                "runner_id": canonical_id,
                "canonical_horse_id": canonical_id,
                "canonical_horse_name": text(
                    entry.get("runner_name")
                ),
                "historical_rating_value": text(
                    form.get("formMomentum")
                ),
                "context_parameter_id": (
                    "LIVE_FORM_GUIDE_COMPONENT_SOURCE"
                ),
                "total_context_adjustment": "",
                "context_adjusted_performance_value": text(
                    form.get("formMomentum")
                ),
                "suitability_component_type": (
                    "LIVE_CURRENT_SUITABILITY"
                ),
                "source_component_field": "suitability",
                "suitability_component_value": component_value,
                "suitability_component_decision": (
                    "COMPONENT_PUBLISHED"
                ),
                "race_entry_suitability_component_status": (
                    COMPONENT_STATUS
                ),
                "source_adjusted_performance_evidence_sha256": (
                    projected_evidence
                ),
                "source_context_adjustment_evidence_sha256": "",
                "race_entry_suitability_component_evidence_sha256": (
                    component_evidence
                ),
                "source_adjusted_performance_builder_version": (
                    "edgeiq_form_guide_enriched_v2"
                ),
                "source_context_adjustment_builder_version": "",
                "builder_version": CURRENT_BRANCH_BUILDER_VERSION,
                "contract_version": CONTRACT_VERSION,
                "built_at_utc": current_branch_built_at_utc(),
            }
        )

    return output_rows



def main() -> None:
    adjusted_fields, adjusted_rows = read_csv(
        ADJUSTED_PERFORMANCE_PATH
    )

    require_fields(
        ADJUSTED_PERFORMANCE_PATH,
        adjusted_fields,
        [
            "race_entry_context_adjusted_performance_id",
            *IDENTITY_FIELDS,
            "context_adjusted_performance_value",
            "context_adjusted_performance_decision",
            "source_adjustment_evidence_sha256",
            "race_entry_context_adjusted_performance_evidence_sha256",
            "source_adjustment_builder_version",
            "builder_version",
            "contract_version",
        ],
    )

    if not adjusted_rows:
        output_rows = build_current_runner_component_rows()
        atomic_write_csv(
            OUTPUT_PATH,
            output_rows,
        )

        print(
            "EDGEIQ_RACE_ENTRY_SUITABILITY_COMPONENT_FACT_V1_BUILD_PASS"
        )
        print("context_adjusted_performance_rows=0")
        print("context_adjustment_rows=NOT_REQUIRED_CURRENT_RUNNER_AUTHORITY")
        print("eligible_adjusted_performance_rows=0")
        print("parameter_not_available_rows=0")
        print("context_ineligible_rows=0")
        print(f"suitability_component_rows={len(output_rows)}")
        print(f"output={OUTPUT_PATH}")
        return

    adjustment_fields, adjustment_rows = read_csv(
        ADJUSTMENT_PATH
    )

    require_fields(
        ADJUSTMENT_PATH,
        adjustment_fields,
        [
            *IDENTITY_FIELDS,
            *[
                source_field
                for _, source_field in COMPONENT_MAPPING
            ],
            "context_adjustment_application_decision",
            "race_entry_context_adjustment_evidence_sha256",
            "builder_version",
            "contract_version",
        ],
    )

    adjustment_by_id: dict[str, dict[str, str]] = {}

    for row in adjustment_rows:
        adjustment_id = text(
            row["race_entry_context_adjustment_id"]
        )

        if not adjustment_id:
            fail(
                "Blank race_entry_context_adjustment_id "
                "in adjustment source."
            )

        if adjustment_id in adjustment_by_id:
            fail(
                f"Duplicate context-adjustment ID: "
                f"{adjustment_id}"
            )

        adjustment_by_id[adjustment_id] = row

    built_at_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    output_rows: list[dict[str, object]] = []

    seen_adjusted_ids: set[str] = set()
    seen_component_ids: set[str] = set()

    eligible_count = 0
    unavailable_count = 0
    ineligible_count = 0

    for adjusted in adjusted_rows:
        adjusted_id = text(
            adjusted[
                "race_entry_context_adjusted_performance_id"
            ]
        )

        if not adjusted_id:
            fail(
                "Blank context-adjusted performance ID."
            )

        if adjusted_id in seen_adjusted_ids:
            fail(
                f"Duplicate context-adjusted performance ID: "
                f"{adjusted_id}"
            )

        seen_adjusted_ids.add(
            adjusted_id
        )

        decision = text(
            adjusted[
                "context_adjusted_performance_decision"
            ]
        )

        adjustment_id = text(
            adjusted[
                "race_entry_context_adjustment_id"
            ]
        )

        adjustment = adjustment_by_id.get(
            adjustment_id
        )

        if adjustment is None:
            fail(
                f"{adjusted_id}: missing context-adjustment "
                f"source {adjustment_id}."
            )

        for field_name in IDENTITY_FIELDS:
            if text(
                adjusted[field_name]
            ) != text(
                adjustment[field_name]
            ):
                fail(
                    f"{adjusted_id}: source mismatch for "
                    f"{field_name}."
                )

        adjusted_source_evidence = text(
            adjusted[
                "race_entry_context_adjusted_performance_evidence_sha256"
            ]
        )

        adjustment_evidence = text(
            adjustment[
                "race_entry_context_adjustment_evidence_sha256"
            ]
        )

        adjusted_builder = text(
            adjusted["builder_version"]
        )

        adjustment_builder = text(
            adjustment["builder_version"]
        )

        if (
            not adjusted_source_evidence
            or not adjustment_evidence
            or not adjusted_builder
            or not adjustment_builder
        ):
            fail(
                f"{adjusted_id}: incomplete source lineage."
            )

        if decision == PERFORMANCE_ADJUSTED:
            eligible_count += 1

            adjusted_value = decimal_text(
                parse_required_decimal(
                    adjusted[
                        "context_adjusted_performance_value"
                    ],
                    "context_adjusted_performance_value",
                )
            )

            for component_type, source_field in COMPONENT_MAPPING:
                component_value = decimal_text(
                    parse_required_decimal(
                        adjustment[source_field],
                        source_field,
                    )
                )

                identity_hash = sha256_payload(
                    [
                        CONTRACT_VERSION,
                        adjusted_id,
                        component_type,
                    ]
                )

                component_id = (
                    f"RESC1-"
                    f"{identity_hash[:24].upper()}"
                )

                if component_id in seen_component_ids:
                    fail(
                        f"Duplicate deterministic component "
                        f"ID: {component_id}"
                    )

                seen_component_ids.add(
                    component_id
                )

                evidence_hash = sha256_payload(
                    [
                        component_id,
                        adjusted_source_evidence,
                        adjustment_evidence,
                        component_type,
                        source_field,
                        component_value,
                        COMPONENT_PUBLISHED,
                        COMPONENT_STATUS,
                    ]
                )

                output_rows.append(
                    {
                        "race_entry_suitability_component_id": (
                            component_id
                        ),
                        "race_entry_context_adjusted_performance_id": (
                            adjusted_id
                        ),
                        "race_entry_context_adjustment_id": (
                            adjustment_id
                        ),
                        "race_entry_context_parameter_selection_id": text(
                            adjusted[
                                "race_entry_context_parameter_selection_id"
                            ]
                        ),
                        "race_entry_context_eligibility_id": text(
                            adjusted[
                                "race_entry_context_eligibility_id"
                            ]
                        ),
                        "race_entry_performance_context_id": text(
                            adjusted[
                                "race_entry_performance_context_id"
                            ]
                        ),
                        "race_entry_id": text(
                            adjusted["race_entry_id"]
                        ),
                        "race_id": text(
                            adjusted["race_id"]
                        ),
                        "race_date": text(
                            adjusted["race_date"]
                        ),
                        "runner_id": text(
                            adjusted["runner_id"]
                        ),
                        "canonical_horse_id": text(
                            adjusted["canonical_horse_id"]
                        ),
                        "canonical_horse_name": text(
                            adjusted[
                                "canonical_horse_name"
                            ]
                        ),
                        "historical_rating_value": text(
                            adjusted[
                                "historical_rating_value"
                            ]
                        ),
                        "context_parameter_id": text(
                            adjusted[
                                "context_parameter_id"
                            ]
                        ),
                        "total_context_adjustment": text(
                            adjusted[
                                "total_context_adjustment"
                            ]
                        ),
                        "context_adjusted_performance_value": (
                            adjusted_value
                        ),
                        "suitability_component_type": (
                            component_type
                        ),
                        "source_component_field": (
                            source_field
                        ),
                        "suitability_component_value": (
                            component_value
                        ),
                        "suitability_component_decision": (
                            COMPONENT_PUBLISHED
                        ),
                        "race_entry_suitability_component_status": (
                            COMPONENT_STATUS
                        ),
                        "source_adjusted_performance_evidence_sha256": (
                            adjusted_source_evidence
                        ),
                        "source_context_adjustment_evidence_sha256": (
                            adjustment_evidence
                        ),
                        "race_entry_suitability_component_evidence_sha256": (
                            evidence_hash
                        ),
                        "source_adjusted_performance_builder_version": (
                            adjusted_builder
                        ),
                        "source_context_adjustment_builder_version": (
                            adjustment_builder
                        ),
                        "builder_version": BUILDER_VERSION,
                        "contract_version": CONTRACT_VERSION,
                        "built_at_utc": built_at_utc,
                    }
                )

        elif decision == PARAMETER_NOT_AVAILABLE:
            unavailable_count += 1

        elif decision == CONTEXT_INELIGIBLE:
            ineligible_count += 1

        else:
            fail(
                f"{adjusted_id}: unsupported adjusted "
                f"performance decision {decision!r}."
            )

    output_rows.sort(
        key=lambda row: (
            text(row["race_date"]),
            text(row["race_id"]),
            text(row["race_entry_id"]),
            text(row["suitability_component_type"]),
        )
    )

    atomic_write_csv(
        OUTPUT_PATH,
        output_rows,
    )

    print(
        "EDGEIQ_RACE_ENTRY_SUITABILITY_COMPONENT_FACT_V1_BUILD_PASS"
    )
    print(
        f"context_adjusted_performance_rows={len(adjusted_rows)}"
    )
    print(
        f"context_adjustment_rows={len(adjustment_rows)}"
    )
    print(
        f"eligible_adjusted_performance_rows={eligible_count}"
    )
    print(
        f"parameter_not_available_rows={unavailable_count}"
    )
    print(
        f"context_ineligible_rows={ineligible_count}"
    )
    print(
        f"suitability_component_rows={len(output_rows)}"
    )
    print(
        f"output={OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()

