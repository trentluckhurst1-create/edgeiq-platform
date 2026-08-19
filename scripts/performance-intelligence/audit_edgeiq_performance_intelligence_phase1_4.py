from __future__ import annotations

import ast
import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

PI_ROOT = (
    ROOT
    / "docs"
    / "performance-intelligence"
)

INVENTORY_DIR = (
    PI_ROOT
    / "inventories"
)

AUDIT_DIR = (
    PI_ROOT
    / "audits"
    / "phase1_4"
)

ARCH_DIR = (
    PI_ROOT
    / "architecture"
    / "phase1_4"
)

PROTOTYPE_DIR = (
    PI_ROOT
    / "prototypes"
    / "phase1_4"
)

AUDIT_VERSION = (
    "DURABLE_HORSE_IDENTITY_"
    "DISCOVERY_AUDIT_V0_1"
)

MAX_CANDIDATES = 500
MAX_SAMPLE_ROWS = 25_000
MAX_TEXT_BYTES = 2_000_000
PROGRESS_INTERVAL = 25

EXCLUDED_PREFIXES = (
    ".git/",
    "node_modules/",
    "dist/",
    "build/",
    "checkpoints/",
    "_archive_pre_git_commit/",
    "docs/performance-intelligence/",
)

EXCLUDED_FRAGMENTS = (
    "_checkpoint_",
    "_backup_",
    "/backups/",
    "/archives/",
)

PATH_TERMS: dict[str, int] = {
    "horse": 15,
    "runner": 6,
    "entity": 14,
    "identity": 18,
    "registration": 28,
    "register": 18,
    "pedigree": 26,
    "sire": 18,
    "dam": 18,
    "foaling": 24,
    "foal": 14,
    "dob": 20,
    "birth": 16,
    "sex": 12,
    "country": 8,
    "suffix": 8,
    "breeder": 14,
    "stud": 10,
    "racing_australia": 28,
    "racingaustralia": 28,
    "graphql": 8,
    "master": 8,
    "profile": 8,
    "history": 8,
    "temporal": 12,
    "alias": 18,
    "canonical": 16,
    "resolve": 16,
    "resolution": 18,
    "code": 6,
}

IDENTITY_FIELD_GROUPS: dict[str, tuple[str, ...]] = {
    "durable_registration_id": (
        "horse_registration_id",
        "registration_id",
        "registration_number",
        "registration_no",
        "horse_code",
        "horsecode",
        "horse_uid",
        "horse_uuid",
        "canonical_horse_id",
        "racing_australia_horse_id",
        "racing_australia_id",
        "ra_horse_id",
        "animal_id",
    ),
    "provider_horse_id": (
        "provider_horse_id",
        "horse_id",
        "horseid",
        "horse_key",
        "horsekey",
        "horse_ref",
        "horse_reference",
        "entity_horse_id",
    ),
    "runner_or_entry_id": (
        "runner_id",
        "runnerid",
        "provider_runner_id",
        "entry_id",
        "nomination_id",
        "acceptance_id",
    ),
    "horse_name": (
        "horse",
        "horse_name",
        "horsename",
        "runner_name",
        "name",
    ),
    "country": (
        "country",
        "country_code",
        "country_suffix",
        "horse_country",
        "bred_country",
    ),
    "foaling_date": (
        "foaling_date",
        "foaled_date",
        "date_of_birth",
        "dob",
        "birth_date",
    ),
    "foaling_year": (
        "foaling_year",
        "foaled_year",
        "year_of_birth",
        "birth_year",
    ),
    "sex": (
        "sex",
        "horse_sex",
        "gender",
    ),
    "sire": (
        "sire",
        "sire_name",
        "sire_id",
        "sire_code",
    ),
    "dam": (
        "dam",
        "dam_name",
        "dam_id",
        "dam_code",
    ),
    "damsire": (
        "damsire",
        "dam_sire",
        "damsire_name",
        "dam_sire_name",
    ),
    "breeder": (
        "breeder",
        "breeder_name",
        "stud",
        "stud_name",
    ),
    "trainer": (
        "trainer",
        "trainer_name",
        "trainer_id",
    ),
    "identity_status": (
        "identity_status",
        "resolution_status",
        "match_status",
        "confidence",
        "identity_confidence",
        "resolution_method",
    ),
}

HIGH_VALUE_CONTENT_TERMS = (
    "registration",
    "pedigree",
    "foaling",
    "date_of_birth",
    "horse_code",
    "sire",
    "dam",
    "breeder",
    "canonical_horse",
    "entity_graph",
    "identity_resolution",
    "provider_horse",
    "racing_australia",
)

REFERENCE_PATTERN = re.compile(
    r"""["']([^"']+\.(?:csv|json|parquet|feather|sqlite|sqlite3|db))["']""",
    re.IGNORECASE,
)


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def clean(value: Any) -> str:
    return str(value or "").strip()


def rel(path: Path) -> str:
    try:
        return str(
            path.relative_to(ROOT)
        ).replace("\\", "/")
    except ValueError:
        return str(path)


def excluded(path_text: str) -> bool:
    value = (
        path_text
        .replace("\\", "/")
        .lower()
    )

    if value.startswith(
        EXCLUDED_PREFIXES
    ):
        return True

    return any(
        fragment in value
        for fragment
        in EXCLUDED_FRAGMENTS
    )


def latest_asset_inventory() -> Path | None:
    candidates = sorted(
        INVENTORY_DIR.glob(
            "edgeiq_performance_intelligence_"
            "asset_inventory_*.csv"
        ),
        key=lambda path: (
            path.stat().st_mtime
        ),
        reverse=True,
    )

    return (
        candidates[0]
        if candidates
        else None
    )


def candidate_score(
    path_text: str,
    columns_text: str = "",
) -> tuple[int, list[str]]:
    value = (
        f"{path_text} {columns_text}"
        .replace("\\", "/")
        .lower()
    )

    score = 0
    reasons: list[str] = []

    if value.startswith("scripts/"):
        score += 10
        reasons.append(
            "active_script"
        )

    if value.startswith(
        "public/data/"
    ):
        score += 12
        reasons.append(
            "active_data"
        )

    if value.startswith("src/"):
        score += 5
        reasons.append(
            "active_source"
        )

    for term, points in (
        PATH_TERMS.items()
    ):
        if term in value:
            score += points
            reasons.append(term)

    return score, reasons


def discover_candidates() -> list[
    dict[str, Any]
]:
    records: dict[
        str,
        dict[str, Any],
    ] = {}

    inventory = (
        latest_asset_inventory()
    )

    if inventory:
        with inventory.open(
            "r",
            encoding="utf-8-sig",
            errors="ignore",
            newline="",
        ) as handle:
            reader = csv.DictReader(
                handle
            )

            for row in reader:
                path_text = clean(
                    row.get("path")
                ).replace("\\", "/")

                if (
                    not path_text
                    or excluded(
                        path_text
                    )
                ):
                    continue

                score, reasons = (
                    candidate_score(
                        path_text,
                        clean(
                            row.get(
                                "columns"
                            )
                        ),
                    )
                )

                if score < 18:
                    continue

                records[
                    path_text.lower()
                ] = {
                    "path": path_text,
                    "score": score,
                    "score_reasons": (
                        " | ".join(
                            reasons
                        )
                    ),
                    "extension": clean(
                        row.get(
                            "extension"
                        )
                    ),
                    "size_bytes": clean(
                        row.get(
                            "size_bytes"
                        )
                    ),
                    "inventory_rows": clean(
                        row.get(
                            "row_count"
                        )
                    ),
                    "inventory_columns": clean(
                        row.get(
                            "columns"
                        )
                    ),
                }

    glob_patterns = (
        "*horse*",
        "*runner*entity*",
        "*identity*",
        "*pedigree*",
        "*registration*",
        "*foal*",
        "*racing*australia*",
        "*canonical*horse*",
        "*temporal*identity*",
    )

    for base in (
        ROOT / "scripts",
        ROOT / "public" / "data",
        ROOT / "src",
    ):
        if not base.exists():
            continue

        for pattern in glob_patterns:
            for path in base.rglob(
                pattern
            ):
                if not path.is_file():
                    continue

                path_text = rel(path)

                if excluded(path_text):
                    continue

                score, reasons = (
                    candidate_score(
                        path_text
                    )
                )

                key = path_text.lower()
                existing = records.get(
                    key
                )

                if (
                    not existing
                    or score
                    > existing["score"]
                ):
                    records[key] = {
                        "path": path_text,
                        "score": score,
                        "score_reasons": (
                            " | ".join(
                                reasons
                            )
                        ),
                        "extension": (
                            path.suffix.lower()
                        ),
                        "size_bytes": (
                            path.stat().st_size
                        ),
                        "inventory_rows": "",
                        "inventory_columns": "",
                    }

    ranked = sorted(
        records.values(),
        key=lambda row: (
            -int(row["score"]),
            row["path"].lower(),
        ),
    )

    return ranked[
        :MAX_CANDIDATES
    ]


def matched_groups(
    columns: list[str],
) -> dict[str, list[str]]:
    lower_map = {
        column.lower(): column
        for column in columns
    }

    groups: dict[
        str,
        list[str],
    ] = {}

    for group, candidates in (
        IDENTITY_FIELD_GROUPS.items()
    ):
        groups[group] = [
            lower_map[candidate]
            for candidate in candidates
            if candidate in lower_map
        ]

    return groups


def classify_schema(
    groups: dict[str, list[str]],
) -> tuple[
    str,
    list[str],
]:
    durable_fields = [
        group
        for group in (
            "durable_registration_id",
            "foaling_date",
            "foaling_year",
            "sex",
            "sire",
            "dam",
            "country",
        )
        if groups.get(group)
    ]

    blockers: list[str] = []

    if groups.get(
        "durable_registration_id"
    ):
        if (
            groups.get("horse_name")
            and (
                groups.get(
                    "foaling_date"
                )
                or groups.get(
                    "foaling_year"
                )
                or (
                    groups.get("sire")
                    and groups.get("dam")
                )
            )
        ):
            return (
                "STRONG_DURABLE_HORSE_"
                "IDENTITY_CANDIDATE",
                blockers,
            )

        blockers.append(
            "REGISTRATION_ID_WITHOUT_"
            "SUFFICIENT_CORROBORATION"
        )

        return (
            "REGISTRATION_EVIDENCE_"
            "REQUIRES_CORROBORATION",
            blockers,
        )

    if (
        groups.get(
            "provider_horse_id"
        )
        and groups.get(
            "horse_name"
        )
        and len(
            durable_fields
        ) >= 2
    ):
        blockers.append(
            "PROVIDER_HORSE_ID_NOT_"
            "PROVEN_GLOBAL"
        )

        return (
            "STRONG_PROVIDER_HORSE_"
            "EVIDENCE_CANDIDATE",
            blockers,
        )

    if (
        groups.get("sire")
        and groups.get("dam")
        and groups.get(
            "horse_name"
        )
    ):
        blockers.append(
            "NO_DURABLE_REGISTRATION_ID"
        )

        return (
            "PEDIGREE_IDENTITY_"
            "EVIDENCE_CANDIDATE",
            blockers,
        )

    if (
        groups.get(
            "runner_or_entry_id"
        )
        and not groups.get(
            "durable_registration_id"
        )
    ):
        blockers.append(
            "RUNNER_OR_ENTRY_ID_ONLY"
        )

        return (
            "PERFORMANCE_SCOPED_"
            "IDENTITY_EVIDENCE",
            blockers,
        )

    if groups.get("horse_name"):
        blockers.append(
            "NAME_ONLY_OR_WEAK_"
            "IDENTITY"
        )

        return (
            "WEAK_HORSE_IDENTITY_"
            "EVIDENCE",
            blockers,
        )

    blockers.append(
        "NO_HORSE_IDENTITY_FIELDS"
    )

    return (
        "NOT_HORSE_IDENTITY_EVIDENCE",
        blockers,
    )


def profile_csv(
    path: Path,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "columns": [],
        "column_count": 0,
        "rows_sampled": 0,
        "identity_groups": {},
        "non_empty_counts": {},
        "distinct_counts_capped": {},
        "classification": "",
        "blockers": [],
        "error": "",
    }

    non_empty = Counter()
    distinct: dict[
        str,
        set[str],
    ] = {}

    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            errors="ignore",
            newline="",
        ) as handle:
            reader = csv.DictReader(
                handle
            )

            columns = list(
                reader.fieldnames or []
            )

            groups = matched_groups(
                columns
            )

            relevant_fields = sorted({
                field
                for values
                in groups.values()
                for field in values
            })

            distinct = {
                field: set()
                for field
                in relevant_fields
            }

            for row_number, row in enumerate(
                reader,
                start=1,
            ):
                if (
                    row_number
                    > MAX_SAMPLE_ROWS
                ):
                    break

                result[
                    "rows_sampled"
                ] = row_number

                for field in (
                    relevant_fields
                ):
                    value = clean(
                        row.get(field)
                    )

                    if not value:
                        continue

                    non_empty[
                        field
                    ] += 1

                    if (
                        len(
                            distinct[field]
                        )
                        < 10_000
                    ):
                        distinct[
                            field
                        ].add(value)

            (
                classification,
                blockers,
            ) = classify_schema(
                groups
            )

            result.update(
                {
                    "columns": columns,
                    "column_count": (
                        len(columns)
                    ),
                    "identity_groups": (
                        groups
                    ),
                    "non_empty_counts": dict(
                        sorted(
                            non_empty.items()
                        )
                    ),
                    "distinct_counts_capped": {
                        field: len(values)
                        for field, values
                        in sorted(
                            distinct.items()
                        )
                    },
                    "classification": (
                        classification
                    ),
                    "blockers": (
                        blockers
                    ),
                }
            )

    except Exception as exc:
        result["error"] = str(
            exc
        )

    return result


def profile_json(
    path: Path,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "top_level_type": "",
        "top_level_keys": [],
        "sample_columns": [],
        "identity_groups": {},
        "classification": "",
        "blockers": [],
        "error": "",
    }

    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8-sig",
                errors="ignore",
            )
        )

        sample: dict[str, Any] = {}

        if isinstance(
            payload,
            list,
        ):
            result[
                "top_level_type"
            ] = "list"

            if (
                payload
                and isinstance(
                    payload[0],
                    dict,
                )
            ):
                sample = payload[0]

        elif isinstance(
            payload,
            dict,
        ):
            result[
                "top_level_type"
            ] = "dict"

            result[
                "top_level_keys"
            ] = list(
                payload.keys()
            )[:100]

            sample = payload

            for value in (
                payload.values()
            ):
                if (
                    isinstance(
                        value,
                        list,
                    )
                    and value
                    and isinstance(
                        value[0],
                        dict,
                    )
                ):
                    sample = value[0]
                    break

        columns = list(
            sample.keys()
        )

        groups = matched_groups(
            columns
        )

        (
            classification,
            blockers,
        ) = classify_schema(
            groups
        )

        result.update(
            {
                "sample_columns": (
                    columns
                ),
                "identity_groups": (
                    groups
                ),
                "classification": (
                    classification
                ),
                "blockers": (
                    blockers
                ),
            }
        )

    except Exception as exc:
        result["error"] = str(
            exc
        )

    return result


def profile_script(
    path: Path,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "syntax_status": "",
        "functions": [],
        "references": [],
        "identity_terms": [],
        "graphql_terms": [],
        "classification": "",
        "error": "",
    }

    try:
        raw = path.read_bytes()
        content = raw.decode(
            "utf-8-sig",
            errors="ignore",
        )[:MAX_TEXT_BYTES]

        try:
            tree = ast.parse(
                content
            )

            result[
                "syntax_status"
            ] = "PARSED"

            result["functions"] = sorted({
                node.name
                for node
                in ast.walk(tree)
                if isinstance(
                    node,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                    ),
                )
            })

        except SyntaxError as exc:
            result[
                "syntax_status"
            ] = "SYNTAX_ERROR"
            result["error"] = str(
                exc
            )

        references: list[str] = []

        for match in (
            REFERENCE_PATTERN.finditer(
                content
            )
        ):
            value = (
                match.group(1)
                .replace("\\", "/")
            )

            if value not in references:
                references.append(
                    value
                )

        result[
            "references"
        ] = references[:300]

        lowered = content.lower()

        identity_terms = [
            term
            for term
            in HIGH_VALUE_CONTENT_TERMS
            if term in lowered
        ]

        graphql_terms = [
            term
            for term in (
                "horse {",
                "sire {",
                "dam {",
                "dateofbirth",
                "foalingdate",
                "registration",
                "horsecode",
                "countrycode",
                "sex",
                "pedigree",
            )
            if term in lowered
        ]

        result[
            "identity_terms"
        ] = identity_terms

        result[
            "graphql_terms"
        ] = graphql_terms

        if (
            "registration" in lowered
            or "horsecode"
            in lowered
            or (
                "sire" in lowered
                and "dam" in lowered
            )
        ):
            result[
                "classification"
            ] = (
                "SCRIPT_WITH_DURABLE_"
                "HORSE_IDENTITY_LOGIC"
            )

        elif (
            "horse" in lowered
            and "identity" in lowered
        ):
            result[
                "classification"
            ] = (
                "SCRIPT_WITH_HORSE_"
                "IDENTITY_LOGIC"
            )

        elif (
            "runner_id" in lowered
            or "provider_runner_id"
            in lowered
        ):
            result[
                "classification"
            ] = (
                "RUNNER_IDENTITY_SCRIPT"
            )

        else:
            result[
                "classification"
            ] = (
                "WEAK_OR_INDIRECT_SCRIPT"
            )

    except Exception as exc:
        result["error"] = str(
            exc
        )

    return result


def flatten_candidate(
    candidate: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    groups = profile.get(
        "identity_groups",
        {},
    )

    return {
        "score": candidate[
            "score"
        ],
        "path": candidate[
            "path"
        ],
        "extension": candidate[
            "extension"
        ],
        "size_bytes": candidate[
            "size_bytes"
        ],
        "inventory_rows": candidate[
            "inventory_rows"
        ],
        "score_reasons": candidate[
            "score_reasons"
        ],
        "classification": profile.get(
            "classification",
            "",
        ),
        "durable_registration_id_fields": (
            " | ".join(
                groups.get(
                    "durable_registration_id",
                    [],
                )
            )
        ),
        "provider_horse_id_fields": (
            " | ".join(
                groups.get(
                    "provider_horse_id",
                    [],
                )
            )
        ),
        "runner_or_entry_id_fields": (
            " | ".join(
                groups.get(
                    "runner_or_entry_id",
                    [],
                )
            )
        ),
        "horse_name_fields": (
            " | ".join(
                groups.get(
                    "horse_name",
                    [],
                )
            )
        ),
        "foaling_fields": (
            " | ".join(
                (
                    groups.get(
                        "foaling_date",
                        [],
                    )
                    + groups.get(
                        "foaling_year",
                        [],
                    )
                )
            )
        ),
        "sex_fields": (
            " | ".join(
                groups.get(
                    "sex",
                    [],
                )
            )
        ),
        "sire_fields": (
            " | ".join(
                groups.get(
                    "sire",
                    [],
                )
            )
        ),
        "dam_fields": (
            " | ".join(
                groups.get(
                    "dam",
                    [],
                )
            )
        ),
        "country_fields": (
            " | ".join(
                groups.get(
                    "country",
                    [],
                )
            )
        ),
        "identity_status_fields": (
            " | ".join(
                groups.get(
                    "identity_status",
                    [],
                )
            )
        ),
        "blockers": (
            " | ".join(
                profile.get(
                    "blockers",
                    [],
                )
            )
        ),
        "rows_sampled": profile.get(
            "rows_sampled",
            "",
        ),
        "syntax_status": profile.get(
            "syntax_status",
            "",
        ),
        "identity_terms": (
            " | ".join(
                profile.get(
                    "identity_terms",
                    [],
                )
            )
        ),
        "graphql_terms": (
            " | ".join(
                profile.get(
                    "graphql_terms",
                    [],
                )
            )
        ),
        "references": (
            " | ".join(
                profile.get(
                    "references",
                    [],
                )[:50]
            )
        ),
        "error": profile.get(
            "error",
            "",
        ),
    }


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
) -> None:
    if not rows:
        path.write_text(
            "",
            encoding="utf-8",
        )
        return

    fields: list[str] = []

    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)

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


def architecture_markdown() -> str:
    return """# EDGEiQ Durable Horse Identity Discovery V0.1

## Purpose

Phase 1.4 discovers whether existing EDGEiQ assets contain enough durable evidence to create canonical horse identities.

## Durable identity evidence

Preferred evidence includes:

- official registration identity
- Racing Australia horse code
- jurisdiction horse identifier
- provider horse identity proven stable across runs
- foaling date or foaling year
- sex
- country
- sire
- dam
- breeder
- temporal alias history

## Non-durable evidence

The following cannot independently define a canonical horse:

- race runner ID
- acceptance ID
- nomination ID
- performance-scoped entry ID
- horse name
- normalised horse name
- trainer continuity
- fuzzy string similarity

## Promotion rule

A canonical horse dimension may only be materialised after:

1. A durable identifier source is discovered.
2. Identifier uniqueness and temporal stability are audited.
3. Conflicts are preserved and classified.
4. Every performance-to-horse assignment is reproducible.
5. No ambiguous record is silently merged.

## Current boundary

Phase 1.4 is discovery only.

No canonical horse IDs are generated and no production data is modified.
"""


def markdown_report(
    summary: dict[str, Any],
) -> str:
    lines = [
        "# EDGEiQ Performance Intelligence",
        "## Phase 1.4 Durable Horse Identity Discovery Audit",
        "",
        f"Generated UTC: `{summary['generated_utc']}`",
        "",
        f"Status: **{summary['status']}**",
        "",
        "## Candidate results",
        "",
        f"- Assets inspected: **{summary['assets_inspected']:,}**",
        f"- Strong durable identity candidates: **{summary['strong_durable_candidates']:,}**",
        f"- Registration evidence candidates: **{summary['registration_evidence_candidates']:,}**",
        f"- Strong provider-horse candidates: **{summary['strong_provider_horse_candidates']:,}**",
        f"- Pedigree evidence candidates: **{summary['pedigree_candidates']:,}**",
        f"- Performance-scoped identity assets: **{summary['performance_scoped_assets']:,}**",
        "",
        "## Canonical horse decision",
        "",
        f"**{summary['canonical_horse_decision']}**",
        "",
        "No canonical horse IDs were generated.",
        "",
        "Production data was not modified.",
        "",
    ]

    return "\n".join(lines)


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

    candidates = (
        discover_candidates()
    )

    detailed_profiles: list[
        dict[str, Any]
    ] = []

    flat_rows: list[
        dict[str, Any]
    ] = []

    classification_counts = (
        Counter()
    )

    for index, candidate in enumerate(
        candidates,
        start=1,
    ):
        if (
            index == 1
            or index
            % PROGRESS_INTERVAL
            == 0
        ):
            print(
                "HORSE_IDENTITY_DISCOVERY_"
                f"PROGRESS={index}/"
                f"{len(candidates)} "
                f"PATH={candidate['path']}",
                flush=True,
            )

        path = (
            ROOT
            / candidate["path"]
        )

        suffix = (
            path.suffix.lower()
        )

        if not path.exists():
            profile = {
                "classification": (
                    "FILE_NOT_FOUND"
                ),
                "error": (
                    "FILE_NOT_FOUND"
                ),
            }

        elif suffix == ".csv":
            profile = profile_csv(
                path
            )

        elif suffix == ".json":
            profile = profile_json(
                path
            )

        elif suffix == ".py":
            profile = profile_script(
                path
            )

        else:
            profile = {
                "classification": (
                    "UNSUPPORTED_FILE_TYPE"
                ),
                "error": "",
            }

        classification = profile.get(
            "classification",
            "UNCLASSIFIED",
        )

        classification_counts[
            classification
        ] += 1

        detailed_profiles.append(
            {
                "candidate": candidate,
                "profile": profile,
            }
        )

        flat_rows.append(
            flatten_candidate(
                candidate,
                profile,
            )
        )

    strong_durable = [
        row
        for row in flat_rows
        if row["classification"]
        == (
            "STRONG_DURABLE_HORSE_"
            "IDENTITY_CANDIDATE"
        )
    ]

    registration_evidence = [
        row
        for row in flat_rows
        if row["classification"]
        == (
            "REGISTRATION_EVIDENCE_"
            "REQUIRES_CORROBORATION"
        )
    ]

    provider_horse = [
        row
        for row in flat_rows
        if row["classification"]
        == (
            "STRONG_PROVIDER_HORSE_"
            "EVIDENCE_CANDIDATE"
        )
    ]

    pedigree = [
        row
        for row in flat_rows
        if row["classification"]
        == (
            "PEDIGREE_IDENTITY_"
            "EVIDENCE_CANDIDATE"
        )
    ]

    performance_scoped = [
        row
        for row in flat_rows
        if (
            row["classification"]
            == (
                "PERFORMANCE_SCOPED_"
                "IDENTITY_EVIDENCE"
            )
            or row[
                "classification"
            ]
            == "RUNNER_IDENTITY_SCRIPT"
        )
    ]

    if strong_durable:
        decision = (
            "DURABLE_IDENTITY_SOURCE_"
            "DISCOVERED_REQUIRES_"
            "UNIQUENESS_AND_TEMPORAL_"
            "VALIDATION"
        )

        next_stage = (
            "Phase 1.4.1 validate durable "
            "registration identity candidates."
        )

    elif (
        registration_evidence
        or provider_horse
        or pedigree
    ):
        decision = (
            "PARTIAL_DURABLE_IDENTITY_"
            "EVIDENCE_DISCOVERED_"
            "CANONICAL_HORSE_REMAINS_"
            "BLOCKED"
        )

        next_stage = (
            "Phase 1.4.1 perform candidate-specific "
            "lineage, uniqueness and coverage audits."
        )

    else:
        decision = (
            "NO_SUFFICIENT_DURABLE_HORSE_"
            "IDENTITY_SOURCE_DISCOVERED_"
            "CANONICAL_HORSE_REMAINS_BLOCKED"
        )

        next_stage = (
            "Acquire or ingest official horse "
            "registration and pedigree evidence "
            "before canonical horse materialisation."
        )

    run_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    candidate_path = (
        PROTOTYPE_DIR
        / (
            "edgeiq_durable_horse_identity_"
            f"candidate_catalog_v0_1_{run_id}.csv"
        )
    )

    detail_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_4_detail_{run_id}.json"
        )
    )

    summary_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_4_summary_{run_id}.json"
        )
    )

    latest_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            "phase1_4_latest.json"
        )
    )

    report_path = (
        AUDIT_DIR
        / (
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            f"PHASE1_4_REPORT_{run_id}.md"
        )
    )

    architecture_path = (
        ARCH_DIR
        / (
            "EDGEIQ_DURABLE_HORSE_"
            "IDENTITY_DISCOVERY_V0_1.md"
        )
    )

    strong_path = (
        AUDIT_DIR
        / (
            "edgeiq_durable_horse_identity_"
            f"strong_candidates_v0_1_{run_id}.csv"
        )
    )

    partial_path = (
        AUDIT_DIR
        / (
            "edgeiq_durable_horse_identity_"
            f"partial_candidates_v0_1_{run_id}.csv"
        )
    )

    write_csv(
        candidate_path,
        flat_rows,
    )

    write_csv(
        strong_path,
        strong_durable,
    )

    write_csv(
        partial_path,
        (
            registration_evidence
            + provider_horse
            + pedigree
        ),
    )

    summary = {
        "audit_name": (
            "EDGEiQ Performance Intelligence "
            "Phase 1.4 Durable Horse Identity "
            "Discovery Audit"
        ),
        "generated_utc": (
            utc_now()
        ),
        "audit_version": (
            AUDIT_VERSION
        ),
        "status": (
            "DURABLE_HORSE_IDENTITY_"
            "DISCOVERY_AUDIT_PASS"
        ),
        "production_data_modified": False,
        "canonical_horse_ids_generated": 0,
        "assets_inspected": (
            len(flat_rows)
        ),
        "classification_counts": dict(
            sorted(
                classification_counts.items()
            )
        ),
        "strong_durable_candidates": (
            len(strong_durable)
        ),
        "registration_evidence_candidates": (
            len(
                registration_evidence
            )
        ),
        "strong_provider_horse_candidates": (
            len(provider_horse)
        ),
        "pedigree_candidates": (
            len(pedigree)
        ),
        "performance_scoped_assets": (
            len(performance_scoped)
        ),
        "canonical_horse_decision": (
            decision
        ),
        "canonical_horse_status": (
            "NOT_MATERIALISED"
        ),
        "next_stage": (
            next_stage
        ),
        "top_strong_candidates": (
            strong_durable[:25]
        ),
        "top_partial_candidates": (
            (
                registration_evidence
                + provider_horse
                + pedigree
            )[:50]
        ),
        "outputs": {
            "candidate_catalog": (
                rel(candidate_path)
            ),
            "strong_candidates": (
                rel(strong_path)
            ),
            "partial_candidates": (
                rel(partial_path)
            ),
            "detail": (
                rel(detail_path)
            ),
            "architecture": (
                rel(
                    architecture_path
                )
            ),
        },
    }

    detail = {
        "summary": summary,
        "candidates": (
            detailed_profiles
        ),
    }

    write_json(
        detail_path,
        detail,
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
        architecture_markdown(),
        encoding="utf-8",
    )

    report_path.write_text(
        markdown_report(summary),
        encoding="utf-8",
    )

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE1_4_DURABLE_HORSE_IDENTITY_"
        "DISCOVERY_AUDIT_PASS",
        flush=True,
    )

    print(
        f"ASSETS_INSPECTED="
        f"{len(flat_rows)}",
        flush=True,
    )

    print(
        f"STRONG_DURABLE_CANDIDATES="
        f"{len(strong_durable)}",
        flush=True,
    )

    print(
        f"PARTIAL_CANDIDATES="
        f"{len(registration_evidence) + len(provider_horse) + len(pedigree)}",
        flush=True,
    )

    print(
        f"CANDIDATE_CATALOG="
        f"{candidate_path}",
        flush=True,
    )

    print(
        f"STRONG_CANDIDATES="
        f"{strong_path}",
        flush=True,
    )

    print(
        f"PARTIAL_CANDIDATES_FILE="
        f"{partial_path}",
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


if __name__ == "__main__":
    main()
