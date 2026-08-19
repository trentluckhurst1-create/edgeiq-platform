from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path.cwd()

INPUT_ROOT = (
    ROOT
    / "docs"
    / "platform-working-tree-reconciliation-v1"
)

OUTPUT_ROOT = (
    ROOT
    / "docs"
    / "repository-recovery-v2"
)

OUTPUT_ROOT.mkdir(
    parents=True,
    exist_ok=True,
)

CLASSIFICATION_CSV = (
    INPUT_ROOT
    / "edgeiq_platform_working_tree_classification_v1.csv"
)

SNAPSHOT_CSV = (
    INPUT_ROOT
    / "edgeiq_snapshot_legacy_source_audit_v1.csv"
)

SOURCE_DOSSIER_CSV = (
    INPUT_ROOT
    / "edgeiq_application_source_reconciliation_dossier_v1.csv"
)

MANIFEST_CSV = (
    OUTPUT_ROOT
    / "edgeiq_repository_recovery_manifest_v1.csv"
)

MANIFEST_JSON = (
    OUTPUT_ROOT
    / "edgeiq_repository_recovery_manifest_v1.json"
)

SUMMARY_JSON = (
    OUTPUT_ROOT
    / "edgeiq_repository_recovery_summary_v1.json"
)

REPORT_MD = (
    OUTPUT_ROOT
    / "EDGEIQ_REPOSITORY_RECOVERY_MANIFEST_V1.md"
)

VALID_PHASES = {
    "PHASE_01_SNAPSHOT",
    "PHASE_02_ACTIVE_SOURCE",
    "PHASE_03_DOCUMENTATION",
    "PHASE_04_GENERATED_OUTPUTS",
    "PHASE_05_DATASETS",
    "PHASE_06_BUILDERS",
    "PHASE_07_PUBLIC_ASSETS",
    "PHASE_08_MISC",
}

VALID_ACTIONS = {
    "KEEP",
    "ARCHIVE",
    "DELETE",
    "REVIEW",
    "COMMIT",
    "IGNORE",
}

VALID_STATUSES = {
    "PENDING",
    "IN_PROGRESS",
    "COMPLETE",
    "BLOCKED",
}

MANDATORY_FIELDS = [
    "recovery_id",
    "repository_path",
    "git_status",
    "current_classification",
    "governed_scope",
    "governed_unit",
    "risk",
    "recommended_action",
    "recovery_phase",
    "commit_group",
    "recovery_status",
    "source_lifecycle",
    "tracked_by_git",
    "snapshot_category",
    "active_counterpart",
    "decision_basis",
]


def normalise_path(value: str) -> str:
    return value.strip().replace("\\", "/")


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def first_value(
    row: dict[str, str],
    *candidate_names: str,
) -> str:
    lowered = {
        key.strip().lower(): clean(value)
        for key, value in row.items()
        if key is not None
    }

    for candidate in candidate_names:
        value = lowered.get(candidate.lower(), "")
        if value:
            return value

    return ""


def read_csv(
    path: Path,
) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Required input not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if not reader.fieldnames:
            raise RuntimeError(
                f"CSV has no header: {path}"
            )

        return [
            {
                clean(key): clean(value)
                for key, value in row.items()
                if key is not None
            }
            for row in reader
        ]


def extract_repository_path(
    row: dict[str, str],
) -> str:
    return normalise_path(
        first_value(
            row,
            "repository_path",
            "path",
            "file_path",
            "relative_path",
            "item_path",
        )
    )


def derive_git_status(
    row: dict[str, str],
) -> str:
    direct = first_value(
        row,
        "git_status",
        "status",
        "porcelain_status",
    )

    if direct:
        return direct

    index_status = first_value(
        row,
        "index_status",
    )

    worktree_status = first_value(
        row,
        "worktree_status",
    )

    combined = f"{index_status}{worktree_status}"

    return combined if combined.strip() else "UNKNOWN"


def stable_recovery_id(
    sequence: int,
    repository_path: str,
) -> str:
    digest = hashlib.sha256(
        repository_path.encode("utf-8")
    ).hexdigest()[:10].upper()

    return (
        f"RRV2-{sequence:04d}-{digest}"
    )


def normalise_scope(
    value: str,
) -> str:
    scope = value.strip().upper()

    aliases = {
        "SOURCE": "APPLICATION_SOURCE",
        "APPLICATION": "APPLICATION_SOURCE",
        "BUILD_SCRIPT": (
            "BUILD_AUDIT_OR_MIGRATION_SCRIPT"
        ),
        "SCRIPT": (
            "BUILD_AUDIT_OR_MIGRATION_SCRIPT"
        ),
        "DOCS": "GOVERNANCE_OR_EVIDENCE",
        "DOCUMENTATION": "GOVERNANCE_OR_EVIDENCE",
        "GENERATED": "GENERATED_OUTPUT",
        "DATA": "DATA_ASSET",
        "PUBLIC": "PUBLIC_RUNTIME_DATA_OR_ASSET",
    }

    return aliases.get(scope, scope)


def derive_scope(
    row: dict[str, str],
    path: str,
) -> str:
    supplied = first_value(
        row,
        "governed_scope",
        "scope",
        "classification_scope",
    )

    if supplied:
        return normalise_scope(supplied)

    lower = path.lower()

    if lower.startswith("src/"):
        return "APPLICATION_SOURCE"

    if lower.startswith("scripts/"):
        return "BUILD_AUDIT_OR_MIGRATION_SCRIPT"

    if lower.startswith("docs/"):
        if any(
            token in lower
            for token in (
                ".csv",
                ".json",
                ".png",
                ".jpg",
                ".jpeg",
                ".webp",
            )
        ):
            return "GENERATED_OUTPUT"

        return "GOVERNANCE_OR_EVIDENCE"

    if lower.startswith("public/"):
        return "PUBLIC_RUNTIME_DATA_OR_ASSET"

    if any(
        lower.endswith(extension)
        for extension in (
            ".csv",
            ".json",
            ".parquet",
            ".feather",
            ".sqlite",
            ".db",
        )
    ):
        return "DATA_ASSET"

    return "ROOT_LEVEL_AUDIT_OR_DATA"


def derive_phase(
    path: str,
    scope: str,
    is_snapshot: bool,
) -> str:
    lower = path.lower()

    if is_snapshot:
        return "PHASE_01_SNAPSHOT"

    if scope == "APPLICATION_SOURCE":
        return "PHASE_02_ACTIVE_SOURCE"

    if scope == "GOVERNANCE_OR_EVIDENCE":
        return "PHASE_03_DOCUMENTATION"

    if scope == "GENERATED_OUTPUT":
        return "PHASE_04_GENERATED_OUTPUTS"

    if scope == "DATA_ASSET":
        return "PHASE_05_DATASETS"

    if scope == "BUILD_AUDIT_OR_MIGRATION_SCRIPT":
        return "PHASE_06_BUILDERS"

    if scope == "PUBLIC_RUNTIME_DATA_OR_ASSET":
        return "PHASE_07_PUBLIC_ASSETS"

    if lower.startswith("public/"):
        return "PHASE_07_PUBLIC_ASSETS"

    return "PHASE_08_MISC"


def derive_active_source_unit(
    path: str,
    dossier_row: dict[str, str] | None,
) -> str:
    if dossier_row:
        supplied = first_value(
            dossier_row,
            "candidate_unit",
            "governed_unit",
            "source_unit",
            "architectural_unit",
        )

        if supplied:
            return supplied.upper()

    lower = path.lower()

    unit_patterns = [
        (
            "APPLICATION_SHELL",
            (
                "src/app.",
                "src/main.",
                "src/edgeiq-os/app",
            ),
        ),
        (
            "MEETINGS_WORKSPACE",
            (
                "/meeting",
                "meetingsworkspace",
            ),
        ),
        (
            "RACE_WORKSPACE",
            (
                "/race/",
                "raceworkspace",
                "racefile",
            ),
        ),
        (
            "FIELD_WORKSPACE",
            (
                "/field/",
                "fieldworkspace",
            ),
        ),
        (
            "PERFORMANCE_WORKSPACE",
            (
                "/performance/",
                "performanceworkspace",
                "performancegraph",
            ),
        ),
        (
            "FORM_WORKSPACE",
            (
                "/form/",
                "formworkspace",
                "formtab",
            ),
        ),
        (
            "MAP_WORKSPACE",
            (
                "/map/",
                "mapworkspace",
                "speedmap",
            ),
        ),
        (
            "MARKET_WORKSPACE",
            (
                "/market/",
                "marketworkspace",
                "markettape",
            ),
        ),
        (
            "RESULTS_WORKSPACE",
            (
                "/result",
                "resultsworkspace",
            ),
        ),
        (
            "WEATHER_WORKSPACE",
            (
                "/weather",
                "weatherworkspace",
            ),
        ),
        (
            "TRACK_WORKSPACE",
            (
                "/track",
                "trackworkspace",
            ),
        ),
        (
            "SHARED_TYPES",
            (
                "src/types/",
                "/types/",
            ),
        ),
        (
            "FRONTEND_DATA_WIRING",
            (
                "src/config/",
                "src/data/",
                "src/lib/",
                "src/utils/",
            ),
        ),
        (
            "APPLICATION_STYLING",
            (
                ".css",
                ".scss",
                ".sass",
            ),
        ),
        (
            "SHARED_UI_COMPONENT",
            (
                "src/components/",
                "/components/",
            ),
        ),
    ]

    for unit, tokens in unit_patterns:
        if any(token in lower for token in tokens):
            return unit

    return "SOURCE_UNIT_UNRESOLVED"


def derive_governed_unit(
    path: str,
    scope: str,
    is_snapshot: bool,
    dossier_row: dict[str, str] | None,
    classification_row: dict[str, str],
) -> str:
    if is_snapshot:
        return "SNAPSHOT_AND_LEGACY_SOURCE"

    supplied = first_value(
        classification_row,
        "governed_unit",
        "unit",
        "candidate_unit",
        "architectural_unit",
    )

    if supplied:
        return supplied.upper()

    if scope == "APPLICATION_SOURCE":
        return derive_active_source_unit(
            path,
            dossier_row,
        )

    if scope == "BUILD_AUDIT_OR_MIGRATION_SCRIPT":
        filename = Path(path).name.lower()

        if filename.startswith("build_"):
            return "BUILDER_SCRIPT"

        if filename.startswith("audit_"):
            return "AUDIT_SCRIPT"

        if filename.startswith("check"):
            return "VALIDATION_SCRIPT"

        if filename.startswith("apply_"):
            return "MIGRATION_OR_PATCH_SCRIPT"

        return "SUPPORT_SCRIPT"

    if scope == "GOVERNANCE_OR_EVIDENCE":
        return "GOVERNANCE_DOCUMENTATION"

    if scope == "GENERATED_OUTPUT":
        return "GENERATED_EVIDENCE_OUTPUT"

    if scope == "DATA_ASSET":
        return "PLATFORM_DATA_ASSET"

    if scope == "PUBLIC_RUNTIME_DATA_OR_ASSET":
        return "PUBLIC_RUNTIME_ASSET"

    return "MISCELLANEOUS_REPOSITORY_ITEM"


def normalise_risk(
    value: str,
    scope: str,
    is_snapshot: bool,
) -> str:
    risk = value.strip().upper()

    if risk in {
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
        "CONTROLLED_UNIT",
        "LOW_REVIEW_REQUIRED",
        "UNRESOLVED",
    }:
        return risk

    if is_snapshot:
        return "MEDIUM"

    if scope == "APPLICATION_SOURCE":
        return "HIGH"

    if scope in {
        "BUILD_AUDIT_OR_MIGRATION_SCRIPT",
        "PUBLIC_RUNTIME_DATA_OR_ASSET",
        "DATA_ASSET",
    }:
        return "MEDIUM"

    return "LOW_REVIEW_REQUIRED"


def derive_recommended_action(
    scope: str,
    is_snapshot: bool,
    snapshot_row: dict[str, str] | None,
    risk: str,
) -> tuple[str, str]:
    if is_snapshot and snapshot_row:
        counterpart_status = first_value(
            snapshot_row,
            "counterpart_status",
        ).upper()

        tracked = first_value(
            snapshot_row,
            "tracked_by_git",
        ).upper()

        if counterpart_status == "ACTIVE_COUNTERPART_FOUND":
            return (
                "ARCHIVE",
                (
                    "Historical snapshot has an active "
                    "counterpart; archive only after "
                    "reference verification."
                ),
            )

        if tracked == "FALSE":
            return (
                "REVIEW",
                (
                    "Untracked historical snapshot has no "
                    "inferred active counterpart."
                ),
            )

        return (
            "REVIEW",
            (
                "Snapshot status is unresolved and requires "
                "architectural review."
            ),
        )

    if scope == "APPLICATION_SOURCE":
        return (
            "COMMIT",
            (
                "Active application source candidate must be "
                "validated and committed in an architectural "
                "recovery unit."
            ),
        )

    if scope == "BUILD_AUDIT_OR_MIGRATION_SCRIPT":
        return (
            "COMMIT",
            (
                "Builder, audit or migration script requires "
                "governed review and commit grouping."
            ),
        )

    if scope == "PUBLIC_RUNTIME_DATA_OR_ASSET":
        return (
            "COMMIT",
            (
                "Public runtime asset requires consumer and "
                "deployment validation before commit."
            ),
        )

    if scope == "DATA_ASSET":
        return (
            "REVIEW",
            (
                "Data asset requires provenance, permanence "
                "and regeneration review."
            ),
        )

    if scope == "GENERATED_OUTPUT":
        return (
            "REVIEW",
            (
                "Generated output requires retention and "
                "reproducibility review."
            ),
        )

    if scope == "GOVERNANCE_OR_EVIDENCE":
        return (
            "KEEP",
            (
                "Governance or evidence item should remain "
                "unless superseded or proven temporary."
            ),
        )

    if risk in {"HIGH", "CRITICAL", "UNRESOLVED"}:
        return (
            "REVIEW",
            "High-risk or unresolved repository item.",
        )

    return (
        "REVIEW",
        "Repository item requires manual disposition.",
    )


def derive_commit_group(
    phase: str,
    governed_unit: str,
    action: str,
) -> str:
    if phase == "PHASE_01_SNAPSHOT":
        return "RRV2_UNIT_005_SNAPSHOT_VERIFICATION"

    if phase == "PHASE_02_ACTIVE_SOURCE":
        safe_unit = re.sub(
            r"[^A-Z0-9]+",
            "_",
            governed_unit.upper(),
        ).strip("_")

        return (
            f"RRV2_ACTIVE_SOURCE_{safe_unit}"
        )

    mapping = {
        "PHASE_03_DOCUMENTATION": (
            "RRV2_DOCUMENTATION_RECOVERY"
        ),
        "PHASE_04_GENERATED_OUTPUTS": (
            "RRV2_GENERATED_OUTPUT_RECOVERY"
        ),
        "PHASE_05_DATASETS": (
            "RRV2_DATASET_RECOVERY"
        ),
        "PHASE_06_BUILDERS": (
            "RRV2_BUILDER_RECOVERY"
        ),
        "PHASE_07_PUBLIC_ASSETS": (
            "RRV2_PUBLIC_ASSET_RECOVERY"
        ),
        "PHASE_08_MISC": (
            "RRV2_MISCELLANEOUS_RECOVERY"
        ),
    }

    group = mapping[phase]

    if action == "IGNORE":
        return f"{group}_IGNORE"

    return group


classification_rows = read_csv(
    CLASSIFICATION_CSV
)

snapshot_rows = read_csv(
    SNAPSHOT_CSV
)

source_dossier_rows = read_csv(
    SOURCE_DOSSIER_CSV
)

snapshot_by_path = {
    extract_repository_path(row): row
    for row in snapshot_rows
    if extract_repository_path(row)
}

dossier_by_path = {
    extract_repository_path(row): row
    for row in source_dossier_rows
    if extract_repository_path(row)
}

classification_by_path: dict[
    str,
    dict[str, str],
] = {}

duplicate_input_paths: list[str] = []

for row in classification_rows:
    path = extract_repository_path(row)

    if not path:
        raise RuntimeError(
            "Classification input contains a row "
            "without a repository path."
        )

    if path in classification_by_path:
        duplicate_input_paths.append(path)
        continue

    classification_by_path[path] = row

if duplicate_input_paths:
    raise RuntimeError(
        "Duplicate paths found in classification input: "
        + ", ".join(
            sorted(set(duplicate_input_paths))[:20]
        )
    )

sorted_paths = sorted(
    classification_by_path,
    key=lambda item: item.lower(),
)

manifest_rows: list[dict[str, str]] = []

for sequence, path in enumerate(
    sorted_paths,
    start=1,
):
    classification_row = (
        classification_by_path[path]
    )

    snapshot_row = snapshot_by_path.get(path)
    dossier_row = dossier_by_path.get(path)

    is_snapshot = snapshot_row is not None

    scope = derive_scope(
        classification_row,
        path,
    )

    phase = derive_phase(
        path,
        scope,
        is_snapshot,
    )

    governed_unit = derive_governed_unit(
        path,
        scope,
        is_snapshot,
        dossier_row,
        classification_row,
    )

    supplied_risk = first_value(
        classification_row,
        "risk",
        "risk_classification",
        "risk_level",
    )

    risk = normalise_risk(
        supplied_risk,
        scope,
        is_snapshot,
    )

    action, decision_basis = (
        derive_recommended_action(
            scope,
            is_snapshot,
            snapshot_row,
            risk,
        )
    )

    commit_group = derive_commit_group(
        phase,
        governed_unit,
        action,
    )

    snapshot_category = ""
    active_counterpart = ""
    tracked_by_git = ""
    source_lifecycle = first_value(
        classification_row,
        "lifecycle",
        "source_lifecycle",
    )

    if snapshot_row:
        snapshot_category = first_value(
            snapshot_row,
            "snapshot_categories",
            "snapshot_category",
        )

        active_counterpart = first_value(
            snapshot_row,
            "counterpart_path",
            "active_counterpart",
        )

        tracked_by_git = first_value(
            snapshot_row,
            "tracked_by_git",
        )

    if not tracked_by_git:
        tracked_by_git = first_value(
            classification_row,
            "tracked_by_git",
            "tracked",
        )

    current_classification = first_value(
        classification_row,
        "classification",
        "current_classification",
        "item_classification",
        "risk",
    )

    if not current_classification:
        current_classification = scope

    manifest_rows.append(
        {
            "recovery_id": stable_recovery_id(
                sequence,
                path,
            ),
            "repository_path": path,
            "git_status": derive_git_status(
                classification_row
            ),
            "current_classification": (
                current_classification
            ),
            "governed_scope": scope,
            "governed_unit": governed_unit,
            "risk": risk,
            "recommended_action": action,
            "recovery_phase": phase,
            "commit_group": commit_group,
            "recovery_status": "PENDING",
            "source_lifecycle": (
                source_lifecycle or "UNSPECIFIED"
            ),
            "tracked_by_git": (
                tracked_by_git or "UNSPECIFIED"
            ),
            "snapshot_category": (
                snapshot_category or "NOT_APPLICABLE"
            ),
            "active_counterpart": (
                active_counterpart or "NOT_APPLICABLE"
            ),
            "decision_basis": decision_basis,
        }
    )


# -----------------------------
# Validation
# -----------------------------

errors: list[str] = []

if len(manifest_rows) != len(
    classification_by_path
):
    errors.append(
        "Manifest row count does not match unique "
        "classification input path count."
    )

manifest_paths = [
    row["repository_path"]
    for row in manifest_rows
]

manifest_ids = [
    row["recovery_id"]
    for row in manifest_rows
]

if len(manifest_paths) != len(
    set(manifest_paths)
):
    errors.append(
        "Duplicate repository paths detected."
    )

if len(manifest_ids) != len(
    set(manifest_ids)
):
    errors.append(
        "Duplicate recovery IDs detected."
    )

if manifest_paths != sorted(
    manifest_paths,
    key=lambda item: item.lower(),
):
    errors.append(
        "Manifest ordering is not deterministic."
    )

for row_index, row in enumerate(
    manifest_rows,
    start=1,
):
    for field in MANDATORY_FIELDS:
        if not clean(row.get(field)):
            errors.append(
                f"Row {row_index} missing mandatory "
                f"field: {field}"
            )

    if row["recovery_phase"] not in VALID_PHASES:
        errors.append(
            f"Row {row_index} has invalid phase: "
            f"{row['recovery_phase']}"
        )

    if (
        row["recommended_action"]
        not in VALID_ACTIONS
    ):
        errors.append(
            f"Row {row_index} has invalid action: "
            f"{row['recommended_action']}"
        )

    if (
        row["recovery_status"]
        not in VALID_STATUSES
    ):
        errors.append(
            f"Row {row_index} has invalid status: "
            f"{row['recovery_status']}"
        )

if errors:
    print("VERDICT=FAIL")
    print(
        f"VALIDATION_ERRORS={len(errors)}"
    )

    for error in errors[:50]:
        print(f"ERROR={error}")

    raise RuntimeError(
        "Repository Recovery Manifest validation "
        "failed."
    )


# -----------------------------
# Summary
# -----------------------------

phase_counts = Counter(
    row["recovery_phase"]
    for row in manifest_rows
)

action_counts = Counter(
    row["recommended_action"]
    for row in manifest_rows
)

risk_counts = Counter(
    row["risk"]
    for row in manifest_rows
)

unit_counts = Counter(
    row["governed_unit"]
    for row in manifest_rows
)

status_counts = Counter(
    row["recovery_status"]
    for row in manifest_rows
)

complete_items = status_counts.get(
    "COMPLETE",
    0,
)

total_items = len(manifest_rows)

completion_percentage = (
    round(
        complete_items / total_items * 100,
        2,
    )
    if total_items
    else 0.0
)

summary = {
    "schema_version": "1.0",
    "repository_recovery_program": (
        "EDGEIQ Repository Recovery V2"
    ),
    "total_repository_items": total_items,
    "items_by_phase": dict(
        sorted(phase_counts.items())
    ),
    "items_by_action": dict(
        sorted(action_counts.items())
    ),
    "items_by_risk": dict(
        sorted(risk_counts.items())
    ),
    "items_by_governed_unit": dict(
        sorted(
            unit_counts.items(),
            key=lambda item: (
                -item[1],
                item[0],
            ),
        )
    ),
    "items_by_status": dict(
        sorted(status_counts.items())
    ),
    "items_pending": status_counts.get(
        "PENDING",
        0,
    ),
    "items_complete": complete_items,
    "repository_recovery_completion_percent": (
        completion_percentage
    ),
    "validation": {
        "verdict": "PASS",
        "unique_repository_paths": len(
            set(manifest_paths)
        ),
        "unique_recovery_ids": len(
            set(manifest_ids)
        ),
        "deterministic_ordering": True,
        "mandatory_fields_populated": True,
    },
}


# -----------------------------
# Outputs
# -----------------------------

with MANIFEST_CSV.open(
    "w",
    encoding="utf-8-sig",
    newline="",
) as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=MANDATORY_FIELDS,
    )
    writer.writeheader()
    writer.writerows(manifest_rows)

with MANIFEST_JSON.open(
    "w",
    encoding="utf-8",
) as handle:
    json.dump(
        {
            "schema_version": "1.0",
            "program": (
                "EDGEIQ Repository Recovery V2"
            ),
            "manifest": manifest_rows,
        },
        handle,
        indent=2,
        ensure_ascii=False,
    )
    handle.write("\n")

with SUMMARY_JSON.open(
    "w",
    encoding="utf-8",
) as handle:
    json.dump(
        summary,
        handle,
        indent=2,
        ensure_ascii=False,
    )
    handle.write("\n")


def markdown_table(
    heading: str,
    counts: Counter[str],
) -> list[str]:
    lines = [
        f"## {heading}",
        "",
        "| Category | Count |",
        "|---|---:|",
    ]

    for label, count in sorted(
        counts.items(),
        key=lambda item: (
            -item[1],
            item[0],
        ),
    ):
        lines.append(
            f"| `{label}` | {count} |"
        )

    lines.append("")
    return lines


report_lines: list[str] = [
    "# EDGEIQ Repository Recovery Manifest V1",
    "",
    "## Repository Recovery V2",
    "",
    (
        "This manifest is the canonical operating "
        "index for the governed recovery of the "
        "EDGEIQ platform repository."
    ),
    "",
    "## Current State",
    "",
    f"- Total repository items: **{total_items}**",
    (
        "- Recovery items pending: "
        f"**{summary['items_pending']}**"
    ),
    (
        "- Recovery items complete: "
        f"**{summary['items_complete']}**"
    ),
    (
        "- Repository recovery completion: "
        f"**{completion_percentage:.2f}%**"
    ),
    "- Validation verdict: **PASS**",
    "",
    "No source file was deleted, moved, renamed, "
    "staged, reset or committed by this builder.",
    "",
    "## Recovery Phases",
    "",
    "1. `PHASE_01_SNAPSHOT` — snapshot and legacy "
    "source verification.",
    "2. `PHASE_02_ACTIVE_SOURCE` — active application "
    "source reconciliation.",
    "3. `PHASE_03_DOCUMENTATION` — governance and "
    "documentation recovery.",
    "4. `PHASE_04_GENERATED_OUTPUTS` — generated "
    "evidence and output review.",
    "5. `PHASE_05_DATASETS` — data provenance and "
    "retention review.",
    "6. `PHASE_06_BUILDERS` — builder, audit and "
    "migration-script reconciliation.",
    "7. `PHASE_07_PUBLIC_ASSETS` — public runtime "
    "asset verification.",
    "8. `PHASE_08_MISC` — unresolved repository "
    "items.",
    "",
]

report_lines.extend(
    markdown_table(
        "Items by Recovery Phase",
        phase_counts,
    )
)

report_lines.extend(
    markdown_table(
        "Items by Recommended Action",
        action_counts,
    )
)

report_lines.extend(
    markdown_table(
        "Items by Risk",
        risk_counts,
    )
)

report_lines.extend(
    markdown_table(
        "Largest Governed Units",
        Counter(
            dict(
                sorted(
                    unit_counts.items(),
                    key=lambda item: (
                        -item[1],
                        item[0],
                    ),
                )[:30]
            )
        ),
    )
)

report_lines.extend(
    [
        "## Recovery Progress",
        "",
        "| Status | Count |",
        "|---|---:|",
    ]
)

for status, count in sorted(
    status_counts.items(),
):
    report_lines.append(
        f"| `{status}` | {count} |"
    )

report_lines.extend(
    [
        "",
        "## Next Recovery Unit",
        "",
        (
            "**RRV2 Unit 005 — Snapshot Reference "
            "Verification**"
        ),
        "",
        (
            "Verify that every snapshot or legacy "
            "source candidate is absent from imports, "
            "runtime configuration, build scripts, "
            "audit scripts and governed generators "
            "before any archival action is authorised."
        ),
        "",
        "## Governance Decision",
        "",
        (
            "The manifest records recommended actions "
            "only. It does not authorise deletion, "
            "archival, movement, staging or commit."
        ),
        "",
    ]
)

REPORT_MD.write_text(
    "\n".join(report_lines),
    encoding="utf-8",
)

print("VERDICT=PASS")
print(
    f"TOTAL_REPOSITORY_ITEMS={total_items}"
)
print(
    f"ITEMS_PENDING="
    f"{summary['items_pending']}"
)
print(
    "REPOSITORY_RECOVERY_COMPLETION_PERCENT="
    f"{completion_percentage:.2f}"
)
print(
    f"PHASE_01_SNAPSHOT="
    f"{phase_counts.get('PHASE_01_SNAPSHOT', 0)}"
)
print(
    f"PHASE_02_ACTIVE_SOURCE="
    f"{phase_counts.get('PHASE_02_ACTIVE_SOURCE', 0)}"
)
print(
    f"MANIFEST_CSV={MANIFEST_CSV}"
)
print(
    f"MANIFEST_JSON={MANIFEST_JSON}"
)
print(
    f"SUMMARY_JSON={SUMMARY_JSON}"
)
print(
    f"REPORT={REPORT_MD}"
)
