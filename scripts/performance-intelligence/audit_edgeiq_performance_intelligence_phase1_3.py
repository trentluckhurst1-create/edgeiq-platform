from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

RAW_ROOT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse"
    / "raw"
)

DIMENSION_ROOT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse"
    / "dimensions"
)

AUDIT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "phase1_3"
)

ARCH_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "architecture"
    / "phase1_3"
)

PROTOTYPE_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase1_3"
)

AUDIT_VERSION = (
    "HORSE_IDENTITY_EVIDENCE_AUDIT_V0_1"
)

PROGRESS_INTERVAL = 100_000

COUNTRY_SUFFIX_PATTERN = re.compile(
    r"\s*(?:\((?:AUS|NZ|IRE|GB|USA|FR|JPN|SAF|ARG|BRZ|GER|CAN|CHI|URU|ITY|SWE|DEN|SIN|HK)\)\s*)+$",
    re.IGNORECASE,
)

SUSPICIOUS_TRACK_PREFIXES = (
    "BETDELUXE",
    "PICKLEBET",
    "SOUTHSIDE",
    "NORDCON",
    "PARK",
)

TRACK_ALIAS_CANDIDATES = {
    "BETDELUXEWARRACKNABEAL": (
        "WARRACKNABEAL"
    ),
    "PICKLEBETPARKWERRIBEE": (
        "WERRIBEE"
    ),
    "PARKWERRIBEE": (
        "WERRIBEE"
    ),
    "PICKLEBETPARKWODONGA": (
        "WODONGA"
    ),
    "PARKWODONGA": (
        "WODONGA"
    ),
    "WODONGANORDCONLANDPARK": (
        "WODONGA"
    ),
    "SOUTHSIDECRANBOURNE": (
        "CRANBOURNE"
    ),
    "SOUTHSIDEPAKENHAM": (
        "PAKENHAM"
    ),
    "SOUTHSIDEPAKENHAMSYNTHETIC": (
        "PAKENHAMSYNTHETIC"
    ),
    "PARKKYNETON": (
        "KYNETON"
    ),
}


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def clean(value: Any) -> str:
    return str(value or "").strip()


def normalise_date(value: Any) -> str:
    text = clean(value)

    if not text:
        return ""

    match = re.match(
        r"^(\d{4}-\d{2}-\d{2})",
        text,
    )

    return match.group(1) if match else ""


def normalise_horse_name(
    value: Any,
) -> str:
    text = clean(value).upper()

    text = COUNTRY_SUFFIX_PATTERN.sub(
        "",
        text,
    )

    return re.sub(
        r"[^A-Z0-9]+",
        "",
        text,
    )


def latest_directory(
    root: Path,
    manifest_name: str,
) -> Path:
    candidates = []

    for path in root.iterdir():
        if (
            path.is_dir()
            and not path.name.startswith(".")
            and (
                path / manifest_name
            ).exists()
        ):
            candidates.append(path)

    candidates.sort(
        key=lambda path: (
            path.stat().st_mtime
        ),
        reverse=True,
    )

    if not candidates:
        raise FileNotFoundError(
            f"No warehouse directory found under {root}"
        )

    return candidates[0]


def write_json(
    path: Path,
    payload: Any,
) -> None:
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str] | None = None,
) -> None:
    fields = list(
        fieldnames or []
    )

    if not fields:
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)

    if not fields:
        path.write_text(
            "",
            encoding="utf-8",
        )
        return

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    ARCH_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    PROTOTYPE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    raw_snapshot = latest_directory(
        RAW_ROOT,
        "warehouse_manifest.json",
    )

    dimension_snapshot = latest_directory(
        DIMENSION_ROOT,
        "dimension_manifest.json",
    )

    performance_path = (
        raw_snapshot
        / "canonical_performance_evidence.csv"
    )

    performance_map_path = (
        dimension_snapshot
        / "performance_dimension_map.csv"
    )

    horse_evidence_path = (
        dimension_snapshot
        / "horse_identity_evidence_dimension.csv"
    )

    track_dimension_path = (
        dimension_snapshot
        / "track_dimension.csv"
    )

    run_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    provider_profile_path = (
        PROTOTYPE_DIR
        / (
            "edgeiq_provider_runner_identity_"
            f"profile_v0_1_{run_id}.csv"
        )
    )

    name_profile_path = (
        PROTOTYPE_DIR
        / (
            "edgeiq_horse_name_identity_"
            f"profile_v0_1_{run_id}.csv"
        )
    )

    performance_evidence_path = (
        PROTOTYPE_DIR
        / (
            "edgeiq_performance_horse_identity_"
            f"evidence_v0_1_{run_id}.csv"
        )
    )

    provider_conflicts_path = (
        AUDIT_DIR
        / (
            "edgeiq_provider_runner_identity_"
            f"conflicts_v0_1_{run_id}.csv"
        )
    )

    track_alias_audit_path = (
        AUDIT_DIR
        / (
            "edgeiq_track_alias_candidates_"
            f"v0_1_{run_id}.csv"
        )
    )

    checks_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_3_checks_{run_id}.csv"
        )
    )

    summary_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_3_summary_{run_id}.json"
        )
    )

    latest_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            "phase1_3_latest.json"
        )
    )

    report_path = (
        AUDIT_DIR
        / (
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            f"PHASE1_3_REPORT_{run_id}.md"
        )
    )

    architecture_path = (
        ARCH_DIR
        / (
            "EDGEIQ_CANONICAL_HORSE_"
            "IDENTITY_RESOLUTION_V0_1.md"
        )
    )

    performance_to_evidence: dict[
        str,
        str,
    ] = {}

    print(
        "PHASE1_3_LOAD_PERFORMANCE_MAP_START",
        flush=True,
    )

    with performance_map_path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row_number, row in enumerate(
            reader,
            start=1,
        ):
            if (
                row_number == 1
                or row_number
                % PROGRESS_INTERVAL
                == 0
            ):
                print(
                    "PERFORMANCE_MAP_PROGRESS="
                    f"{row_number}",
                    flush=True,
                )

            performance_id = clean(
                row.get("performance_id")
            )

            evidence_id = clean(
                row.get(
                    "horse_identity_evidence_id"
                )
            )

            if performance_id and evidence_id:
                performance_to_evidence[
                    performance_id
                ] = evidence_id

    evidence_metadata: dict[
        str,
        dict[str, str],
    ] = {}

    with horse_evidence_path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            evidence_id = clean(
                row.get(
                    "horse_identity_evidence_id"
                )
            )

            if evidence_id:
                evidence_metadata[
                    evidence_id
                ] = row

    provider_statistics: dict[
        str,
        dict[str, Any],
    ] = defaultdict(
        lambda: {
            "performances": 0,
            "names": set(),
            "evidence_ids": set(),
            "race_dates": [],
            "tracks": set(),
            "states": set(),
        }
    )

    name_statistics: dict[
        str,
        dict[str, Any],
    ] = defaultdict(
        lambda: {
            "performances": 0,
            "provider_runner_ids": set(),
            "evidence_ids": set(),
            "race_dates": [],
            "tracks": set(),
            "states": set(),
            "raw_names": set(),
        }
    )

    performance_rows = 0
    missing_map_rows = 0
    missing_evidence_rows = 0

    performance_output_fields = [
        "performance_id",
        "horse_identity_evidence_id",
        "provider_runner_id",
        "raw_horse_name",
        "normalised_horse_name",
        "race_date",
        "state",
        "track",
        "identity_evidence_state",
        "canonical_horse_id",
        "audit_version",
    ]

    print(
        "PHASE1_3_PROFILE_PERFORMANCES_START",
        flush=True,
    )

    with performance_path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as source_handle, performance_evidence_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as output_handle:
        reader = csv.DictReader(
            source_handle
        )

        writer = csv.DictWriter(
            output_handle,
            fieldnames=performance_output_fields,
        )
        writer.writeheader()

        for row_number, row in enumerate(
            reader,
            start=1,
        ):
            performance_rows += 1

            if (
                row_number == 1
                or row_number
                % PROGRESS_INTERVAL
                == 0
            ):
                print(
                    "HORSE_IDENTITY_PROFILE_PROGRESS="
                    f"{row_number}",
                    flush=True,
                )

            performance_id = clean(
                row.get("performance_id")
            )

            evidence_id = (
                performance_to_evidence.get(
                    performance_id,
                    "",
                )
            )

            if not evidence_id:
                missing_map_rows += 1
                continue

            metadata = (
                evidence_metadata.get(
                    evidence_id
                )
            )

            if not metadata:
                missing_evidence_rows += 1
                continue

            provider_runner_id = clean(
                metadata.get(
                    "provider_runner_id"
                )
            )

            raw_horse_name = clean(
                row.get("horse_name")
            )

            normalised_name = (
                normalise_horse_name(
                    raw_horse_name
                )
            )

            race_date = normalise_date(
                row.get("race_date")
            )

            track = clean(
                row.get("track")
            )

            state = clean(
                row.get("state")
            )

            provider = (
                provider_statistics[
                    provider_runner_id
                ]
            )

            provider[
                "performances"
            ] += 1

            provider["names"].add(
                normalised_name
            )

            provider[
                "evidence_ids"
            ].add(evidence_id)

            if race_date:
                provider[
                    "race_dates"
                ].append(race_date)

            if track:
                provider[
                    "tracks"
                ].add(track)

            if state:
                provider[
                    "states"
                ].add(state)

            name_profile = (
                name_statistics[
                    normalised_name
                ]
            )

            name_profile[
                "performances"
            ] += 1

            name_profile[
                "provider_runner_ids"
            ].add(
                provider_runner_id
            )

            name_profile[
                "evidence_ids"
            ].add(
                evidence_id
            )

            name_profile[
                "raw_names"
            ].add(
                raw_horse_name
            )

            if race_date:
                name_profile[
                    "race_dates"
                ].append(
                    race_date
                )

            if track:
                name_profile[
                    "tracks"
                ].add(track)

            if state:
                name_profile[
                    "states"
                ].add(state)

            writer.writerow(
                {
                    "performance_id": (
                        performance_id
                    ),
                    "horse_identity_evidence_id": (
                        evidence_id
                    ),
                    "provider_runner_id": (
                        provider_runner_id
                    ),
                    "raw_horse_name": (
                        raw_horse_name
                    ),
                    "normalised_horse_name": (
                        normalised_name
                    ),
                    "race_date": race_date,
                    "state": state,
                    "track": track,
                    "identity_evidence_state": (
                        "PROVIDER_RUNNER_"
                        "EVIDENCE_ONLY"
                    ),
                    "canonical_horse_id": "",
                    "audit_version": (
                        AUDIT_VERSION
                    ),
                }
            )

    provider_rows: list[
        dict[str, Any]
    ] = []

    provider_conflict_rows: list[
        dict[str, Any]
    ] = []

    provider_class_counts = Counter()

    for (
        provider_runner_id,
        statistics,
    ) in sorted(
        provider_statistics.items()
    ):
        names = sorted(
            statistics["names"]
        )

        performances = (
            statistics[
                "performances"
            ]
        )

        if not provider_runner_id:
            classification = (
                "PROVIDER_ID_MISSING"
            )
        elif len(names) > 1:
            classification = (
                "PROVIDER_ID_NAME_CONFLICT"
            )
        elif performances > 1:
            classification = (
                "PROVIDER_ID_REUSED_"
                "NAME_STABLE"
            )
        else:
            classification = (
                "PROVIDER_ID_SINGLE_USE"
            )

        provider_class_counts[
            classification
        ] += 1

        min_date = (
            min(
                statistics[
                    "race_dates"
                ]
            )
            if statistics[
                "race_dates"
            ]
            else ""
        )

        max_date = (
            max(
                statistics[
                    "race_dates"
                ]
            )
            if statistics[
                "race_dates"
            ]
            else ""
        )

        provider_row = {
            "provider_runner_id": (
                provider_runner_id
            ),
            "performance_count": (
                performances
            ),
            "distinct_name_count": (
                len(names)
            ),
            "normalised_names": (
                " | ".join(names)
            ),
            "evidence_record_count": (
                len(
                    statistics[
                        "evidence_ids"
                    ]
                )
            ),
            "min_race_date": min_date,
            "max_race_date": max_date,
            "distinct_track_count": (
                len(
                    statistics["tracks"]
                )
            ),
            "distinct_state_count": (
                len(
                    statistics["states"]
                )
            ),
            "classification": (
                classification
            ),
            "canonical_horse_id": "",
            "automatic_promotion_allowed": (
                False
            ),
            "audit_version": (
                AUDIT_VERSION
            ),
        }

        provider_rows.append(
            provider_row
        )

        if classification in {
            "PROVIDER_ID_NAME_CONFLICT",
            "PROVIDER_ID_MISSING",
        }:
            provider_conflict_rows.append(
                provider_row
            )

    write_csv(
        provider_profile_path,
        provider_rows,
    )

    write_csv(
        provider_conflicts_path,
        provider_conflict_rows,
    )

    name_rows: list[
        dict[str, Any]
    ] = []

    name_class_counts = Counter()

    for (
        normalised_name,
        statistics,
    ) in sorted(
        name_statistics.items()
    ):
        provider_ids = sorted(
            value
            for value
            in statistics[
                "provider_runner_ids"
            ]
            if value
        )

        performances = (
            statistics[
                "performances"
            ]
        )

        if not normalised_name:
            classification = (
                "HORSE_NAME_MISSING"
            )
        elif (
            len(provider_ids) == 1
            and performances > 1
        ):
            classification = (
                "NAME_SINGLE_PROVIDER_"
                "MULTI_RUN_CANDIDATE"
            )
        elif len(provider_ids) == 1:
            classification = (
                "NAME_SINGLE_PROVIDER_"
                "SINGLE_RUN"
            )
        elif len(provider_ids) > 1:
            classification = (
                "NAME_MULTIPLE_PROVIDER_IDS_"
                "REQUIRES_RESOLUTION"
            )
        else:
            classification = (
                "NAME_WITHOUT_PROVIDER_ID"
            )

        name_class_counts[
            classification
        ] += 1

        name_rows.append(
            {
                "normalised_horse_name": (
                    normalised_name
                ),
                "raw_names": (
                    " | ".join(
                        sorted(
                            statistics[
                                "raw_names"
                            ]
                        )
                    )
                ),
                "performance_count": (
                    performances
                ),
                "provider_runner_id_count": (
                    len(provider_ids)
                ),
                "provider_runner_ids": (
                    " | ".join(
                        provider_ids[:100]
                    )
                ),
                "evidence_record_count": (
                    len(
                        statistics[
                            "evidence_ids"
                        ]
                    )
                ),
                "min_race_date": (
                    min(
                        statistics[
                            "race_dates"
                        ]
                    )
                    if statistics[
                        "race_dates"
                    ]
                    else ""
                ),
                "max_race_date": (
                    max(
                        statistics[
                            "race_dates"
                        ]
                    )
                    if statistics[
                        "race_dates"
                    ]
                    else ""
                ),
                "distinct_track_count": (
                    len(
                        statistics[
                            "tracks"
                        ]
                    )
                ),
                "distinct_state_count": (
                    len(
                        statistics[
                            "states"
                        ]
                    )
                ),
                "classification": (
                    classification
                ),
                "canonical_horse_id": "",
                "automatic_promotion_allowed": (
                    False
                ),
                "audit_version": (
                    AUDIT_VERSION
                ),
            }
        )

    write_csv(
        name_profile_path,
        name_rows,
    )

    track_alias_rows: list[
        dict[str, Any]
    ] = []

    with track_dimension_path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            track_name = clean(
                row.get(
                    "canonical_track_name"
                )
            )

            proposed = (
                TRACK_ALIAS_CANDIDATES.get(
                    track_name,
                    "",
                )
            )

            suspicious = (
                bool(proposed)
                or any(
                    track_name.startswith(
                        prefix
                    )
                    for prefix
                    in SUSPICIOUS_TRACK_PREFIXES
                )
            )

            if not suspicious:
                continue

            track_alias_rows.append(
                {
                    "track_id": clean(
                        row.get("track_id")
                    ),
                    "current_track_name": (
                        track_name
                    ),
                    "proposed_canonical_track": (
                        proposed
                    ),
                    "classification": (
                        "EXPLICIT_ALIAS_CANDIDATE"
                        if proposed
                        else
                        "SUSPICIOUS_TRACK_LABEL_"
                        "REQUIRES_REVIEW"
                    ),
                    "automatic_change_allowed": (
                        False
                    ),
                    "evidence_required": (
                        "Meeting history and "
                        "official venue identity"
                    ),
                }
            )

    write_csv(
        track_alias_audit_path,
        track_alias_rows,
    )

    reused_provider_ids = sum(
        1
        for row in provider_rows
        if int(
            row["performance_count"]
        ) > 1
    )

    single_use_provider_ids = sum(
        1
        for row in provider_rows
        if (
            row["classification"]
            == "PROVIDER_ID_SINGLE_USE"
        )
    )

    checks = [
        {
            "check": (
                "PERFORMANCE_EVIDENCE_"
                "ROW_COUNT"
            ),
            "passed": (
                performance_rows
                == 879784
            ),
            "observed": (
                performance_rows
            ),
        },
        {
            "check": (
                "PERFORMANCE_MAP_COMPLETE"
            ),
            "passed": (
                missing_map_rows == 0
            ),
            "observed": (
                missing_map_rows
            ),
        },
        {
            "check": (
                "HORSE_EVIDENCE_COMPLETE"
            ),
            "passed": (
                missing_evidence_rows == 0
            ),
            "observed": (
                missing_evidence_rows
            ),
        },
        {
            "check": (
                "CANONICAL_HORSE_IDS_"
                "NOT_FABRICATED"
            ),
            "passed": all(
                not row[
                    "canonical_horse_id"
                ]
                for row in provider_rows
            )
            and all(
                not row[
                    "canonical_horse_id"
                ]
                for row in name_rows
            ),
            "observed": (
                "ALL_CANONICAL_HORSE_IDS_BLANK"
            ),
        },
        {
            "check": (
                "AUTOMATIC_PROMOTION_DISABLED"
            ),
            "passed": all(
                not row[
                    "automatic_promotion_allowed"
                ]
                for row in provider_rows
            )
            and all(
                not row[
                    "automatic_promotion_allowed"
                ]
                for row in name_rows
            ),
            "observed": (
                "NO_IDENTITY_AUTO_PROMOTION"
            ),
        },
        {
            "check": (
                "TRACK_ALIAS_CHANGES_"
                "NOT_AUTOMATIC"
            ),
            "passed": all(
                not row[
                    "automatic_change_allowed"
                ]
                for row
                in track_alias_rows
            ),
            "observed": (
                len(
                    track_alias_rows
                )
            ),
        },
    ]

    failed_checks = [
        check["check"]
        for check in checks
        if not check["passed"]
    ]

    summary = {
        "audit_name": (
            "EDGEiQ Performance Intelligence "
            "Phase 1.3 Canonical Horse Identity "
            "Evidence and Durability Audit"
        ),
        "generated_utc": utc_now(),
        "audit_version": (
            AUDIT_VERSION
        ),
        "production_data_modified": False,
        "raw_warehouse_snapshot": (
            raw_snapshot.name
        ),
        "dimension_snapshot": (
            dimension_snapshot.name
        ),
        "performance_rows": (
            performance_rows
        ),
        "provider_runner_ids": (
            len(provider_rows)
        ),
        "reused_provider_runner_ids": (
            reused_provider_ids
        ),
        "single_use_provider_runner_ids": (
            single_use_provider_ids
        ),
        "provider_class_counts": dict(
            sorted(
                provider_class_counts.items()
            )
        ),
        "normalised_horse_names": (
            len(name_rows)
        ),
        "name_class_counts": dict(
            sorted(
                name_class_counts.items()
            )
        ),
        "provider_identity_conflicts": (
            len(
                provider_conflict_rows
            )
        ),
        "track_alias_candidates": (
            len(track_alias_rows)
        ),
        "checks": checks,
        "failed_checks": (
            failed_checks
        ),
        "canonical_horse_status": (
            "NOT_MATERIALISED_"
            "INSUFFICIENT_DURABLE_IDENTITY_"
            "EVIDENCE"
        ),
        "finding": (
            "Provider runner identifiers are "
            "predominantly performance-scoped "
            "or single-use evidence and cannot "
            "yet be treated as durable horse IDs."
        ),
        "canonical_status": (
            "HORSE_IDENTITY_EVIDENCE_"
            "AUDIT_PASS"
            if not failed_checks
            else
            "HORSE_IDENTITY_EVIDENCE_"
            "AUDIT_FAIL"
        ),
        "next_stage": (
            "Phase 1.4 audit existing entity "
            "graphs and registration evidence "
            "for durable horse identity."
        ),
        "outputs": {
            "provider_runner_profile": str(
                provider_profile_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "horse_name_profile": str(
                name_profile_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "performance_identity_evidence": str(
                performance_evidence_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "provider_conflicts": str(
                provider_conflicts_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "track_alias_candidates": str(
                track_alias_audit_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
        },
    }

    write_csv(
        checks_path,
        checks,
    )

    write_json(
        summary_path,
        summary,
    )

    write_json(
        latest_path,
        summary,
    )

    architecture_path.write_text(
        """# EDGEiQ Canonical Horse Identity Resolution V0.1

## Current finding

The current provider runner identifier cannot be assumed to represent one horse across its career.

A provider identifier may be:

- performance scoped
- meeting scoped
- reused
- absent
- inconsistent with horse-name evidence

## Evidence retained

Phase 1.3 preserves:

- provider runner identifier
- raw horse name
- normalised horse name
- performance history
- date coverage
- track coverage
- jurisdiction coverage
- provider-ID reuse
- provider-ID/name conflicts

## Canonical promotion requirements

A canonical horse ID requires corroboration from durable evidence such as:

- official registration ID
- Racing Australia horse code
- jurisdiction registration code
- foaling year
- sex
- country
- sire
- dam
- breeder or registration record
- validated temporal identity graph

## Prohibited automatic rules

The following cannot independently create a canonical horse:

- horse name
- normalised horse name
- one provider runner ID
- trainer continuity
- date proximity
- fuzzy spelling similarity

## Track identities

Sponsor and operator labels remain alias candidates until validated against official venue history.

No existing immutable dimension snapshot is edited.
""",
        encoding="utf-8",
    )

    report_path.write_text(
        f"""# EDGEiQ Performance Intelligence
## Phase 1.3 Horse Identity Evidence and Durability Audit

Generated UTC: `{summary['generated_utc']}`

Status: **{summary['canonical_status']}**

- Performance rows audited: **{performance_rows:,}**
- Provider runner IDs: **{len(provider_rows):,}**
- Reused provider runner IDs: **{reused_provider_ids:,}**
- Single-use provider runner IDs: **{single_use_provider_ids:,}**
- Normalised horse names: **{len(name_rows):,}**
- Provider identity conflicts: **{len(provider_conflict_rows):,}**
- Track alias candidates: **{len(track_alias_rows):,}**
- Canonical horse IDs created: **0**
- Failed checks: **{len(failed_checks)}**

Production data was not modified.
""",
        encoding="utf-8",
    )

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE1_3_HORSE_IDENTITY_"
        "EVIDENCE_AUDIT_PASS"
        if not failed_checks
        else
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE1_3_HORSE_IDENTITY_"
        "EVIDENCE_AUDIT_FAIL",
        flush=True,
    )

    print(
        f"PROVIDER_PROFILE="
        f"{provider_profile_path}",
        flush=True,
    )

    print(
        f"NAME_PROFILE="
        f"{name_profile_path}",
        flush=True,
    )

    print(
        f"PERFORMANCE_EVIDENCE="
        f"{performance_evidence_path}",
        flush=True,
    )

    print(
        f"PROVIDER_CONFLICTS="
        f"{provider_conflicts_path}",
        flush=True,
    )

    print(
        f"TRACK_ALIAS_CANDIDATES="
        f"{track_alias_audit_path}",
        flush=True,
    )

    print(
        f"SUMMARY={summary_path}",
        flush=True,
    )

    print(
        f"REPORT={report_path}",
        flush=True,
    )

    if failed_checks:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
