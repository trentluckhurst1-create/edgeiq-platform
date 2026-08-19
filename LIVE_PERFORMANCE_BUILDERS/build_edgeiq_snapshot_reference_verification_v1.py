from __future__ import annotations

import csv
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path.cwd()

RECONCILIATION_ROOT = (
    ROOT
    / "docs"
    / "platform-working-tree-reconciliation-v1"
)

RECOVERY_ROOT = (
    ROOT
    / "docs"
    / "repository-recovery-v2"
)

SNAPSHOT_CSV = (
    RECONCILIATION_ROOT
    / "edgeiq_snapshot_legacy_source_audit_v1.csv"
)

MANIFEST_CSV = (
    RECOVERY_ROOT
    / "edgeiq_repository_recovery_manifest_v1.csv"
)

OUTPUT_CSV = (
    RECOVERY_ROOT
    / "edgeiq_snapshot_reference_verification_v1.csv"
)

OUTPUT_JSON = (
    RECOVERY_ROOT
    / "edgeiq_snapshot_reference_verification_v1.json"
)

REPORT_MD = (
    RECOVERY_ROOT
    / "EDGEIQ_SNAPSHOT_REFERENCE_VERIFICATION_V1.md"
)

TEXT_EXTENSIONS = {
    ".css",
    ".csv",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".mjs",
    ".ps1",
    ".py",
    ".scss",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

ROOT_TEXT_FILES = {
    ".gitignore",
    ".npmignore",
    "package.json",
    "package-lock.json",
    "tsconfig.json",
    "tsconfig.app.json",
    "tsconfig.node.json",
    "vite.config.js",
    "vite.config.mjs",
    "vite.config.ts",
}

IGNORED_DIRECTORY_PARTS = {
    ".git",
    ".idea",
    ".next",
    ".turbo",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "out",
    "target",
    "venv",
}

# These folders necessarily contain inventory and audit references
# to the snapshot paths. They are treated as governance evidence,
# not as operational dependencies.
EVIDENCE_PREFIXES = (
    "docs/platform-working-tree-reconciliation-v1/",
    "docs/repository-recovery-v2/",
)

OPERATIONAL_PREFIXES = (
    "src/",
    "scripts/",
    "public/",
    "config/",
    "tests/",
    "test/",
)

OPERATIONAL_ROOT_FILES = {
    "package.json",
    "package-lock.json",
    "tsconfig.json",
    "tsconfig.app.json",
    "tsconfig.node.json",
    "vite.config.js",
    "vite.config.mjs",
    "vite.config.ts",
}

IMPORT_PATTERNS = (
    re.compile(
        r"\bimport\s+.*?\s+from\s+['\"]([^'\"]+)['\"]",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bimport\s*[(]\s*['\"]([^'\"]+)['\"]\s*[)]",
        re.IGNORECASE,
    ),
    re.compile(
        r"\brequire\s*[(]\s*['\"]([^'\"]+)['\"]\s*[)]",
        re.IGNORECASE,
    ),
    re.compile(
        r"@import\s+(?:url[(])?\s*['\"]?([^'\"\s;)]+)",
        re.IGNORECASE,
    ),
)


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalise_path(value: str) -> str:
    return clean(value).replace("\\", "/")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Required input missing: {path}"
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


def first_value(
    row: dict[str, str],
    *names: str,
) -> str:
    lowered = {
        key.lower(): clean(value)
        for key, value in row.items()
    }

    for name in names:
        value = lowered.get(name.lower(), "")
        if value:
            return value

    return ""


def run_git(
    *arguments: str,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )


def repository_files() -> list[str]:
    result = run_git(
        "-c",
        "core.quotepath=false",
        "ls-files",
        "-co",
        "--exclude-standard",
        "-z",
    )

    paths: set[str] = set()

    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue

        path = normalise_path(
            raw.decode(
                "utf-8",
                errors="surrogateescape",
            )
        )

        if not path:
            continue

        pure = Path(path)

        if any(
            part.lower() in IGNORED_DIRECTORY_PARTS
            for part in pure.parts
        ):
            continue

        paths.add(path)

    return sorted(
        paths,
        key=lambda item: item.lower(),
    )


def is_text_candidate(path: str) -> bool:
    pure = Path(path)

    if pure.name in ROOT_TEXT_FILES:
        return True

    return pure.suffix.lower() in TEXT_EXTENSIONS


def safe_read_lines(
    repository_path: str,
) -> list[str] | None:
    absolute_path = ROOT / Path(repository_path)

    if not absolute_path.is_file():
        return None

    try:
        if absolute_path.stat().st_size > 8 * 1024 * 1024:
            return None
    except OSError:
        return None

    try:
        raw = absolute_path.read_bytes()
    except OSError:
        return None

    if b"\0" in raw[:4096]:
        return None

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode(
            "utf-8",
            errors="replace",
        )

    return text.splitlines()


def without_extension(path: str) -> str:
    pure = Path(path)
    suffix = pure.suffix

    if not suffix:
        return normalise_path(path)

    return normalise_path(
        str(pure.with_suffix(""))
    )


def search_terms(
    snapshot_path: str,
) -> dict[str, str]:
    pure = Path(snapshot_path)

    return {
        "full_path": normalise_path(snapshot_path),
        "path_without_extension": without_extension(
            snapshot_path
        ),
        "basename": pure.name,
        "stem": pure.stem,
    }


def is_evidence_path(path: str) -> bool:
    lower = path.lower()

    return any(
        lower.startswith(prefix.lower())
        for prefix in EVIDENCE_PREFIXES
    )


def is_operational_path(path: str) -> bool:
    lower = path.lower()

    if path in OPERATIONAL_ROOT_FILES:
        return True

    return any(
        lower.startswith(prefix)
        for prefix in OPERATIONAL_PREFIXES
    )


def line_is_import_reference(
    line: str,
    terms: dict[str, str],
) -> bool:
    targets = {
        terms["full_path"].lower(),
        terms["path_without_extension"].lower(),
        terms["basename"].lower(),
        terms["stem"].lower(),
    }

    for pattern in IMPORT_PATTERNS:
        for match in pattern.finditer(line):
            imported = normalise_path(
                match.group(1)
            ).lower()

            imported_name = Path(imported).name.lower()
            imported_stem = Path(imported).stem.lower()

            if (
                imported in targets
                or imported_name in targets
                or imported_stem in targets
            ):
                return True

            for target in targets:
                if imported.endswith(target):
                    return True

    return False


def matched_term(
    line: str,
    terms: dict[str, str],
) -> str:
    lower_line = line.lower()

    ordered_terms = (
        ("full_path", terms["full_path"]),
        (
            "path_without_extension",
            terms["path_without_extension"],
        ),
        ("basename", terms["basename"]),
        ("stem", terms["stem"]),
    )

    for term_type, term in ordered_terms:
        if term and term.lower() in lower_line:
            return term_type

    return ""


snapshot_rows = read_csv(SNAPSHOT_CSV)
manifest_rows = read_csv(MANIFEST_CSV)

manifest_by_path = {
    normalise_path(
        first_value(
            row,
            "repository_path",
            "path",
        )
    ): row
    for row in manifest_rows
    if first_value(
        row,
        "repository_path",
        "path",
    )
}

snapshots: list[dict[str, str]] = []

for row in snapshot_rows:
    path = normalise_path(
        first_value(
            row,
            "path",
            "repository_path",
        )
    )

    if not path:
        raise RuntimeError(
            "Snapshot audit contains a row "
            "without a path."
        )

    snapshots.append(
        {
            "snapshot_path": path,
            "snapshot_categories": first_value(
                row,
                "snapshot_categories",
                "snapshot_category",
            ),
            "tracked_by_git": first_value(
                row,
                "tracked_by_git",
            ),
            "counterpart_status": first_value(
                row,
                "counterpart_status",
            ),
            "active_counterpart": normalise_path(
                first_value(
                    row,
                    "counterpart_path",
                    "active_counterpart",
                )
            ),
        }
    )

snapshots.sort(
    key=lambda row: row["snapshot_path"].lower()
)

all_repository_files = repository_files()

searchable_files = [
    path
    for path in all_repository_files
    if is_text_candidate(path)
]

text_cache: dict[str, list[str]] = {}

skipped_text_candidates: list[str] = []

for repository_path in searchable_files:
    lines = safe_read_lines(repository_path)

    if lines is None:
        skipped_text_candidates.append(
            repository_path
        )
        continue

    text_cache[repository_path] = lines

reference_rows: list[dict[str, str]] = []
summary_rows: list[dict[str, str]] = []

for snapshot in snapshots:
    snapshot_path = snapshot["snapshot_path"]
    terms = search_terms(snapshot_path)

    operational_hits = 0
    import_hits = 0
    script_hits = 0
    evidence_hits = 0
    other_hits = 0

    referencing_files: set[str] = set()
    operational_reference_files: set[str] = set()
    evidence_reference_files: set[str] = set()

    for repository_path, lines in text_cache.items():
        # A snapshot containing its own component name is not
        # evidence that another file depends on the snapshot.
        if repository_path == snapshot_path:
            continue

        for line_number, line in enumerate(
            lines,
            start=1,
        ):
            term_type = matched_term(
                line,
                terms,
            )

            if not term_type:
                continue

            evidence_path = is_evidence_path(
                repository_path
            )

            operational_path = is_operational_path(
                repository_path
            )

            import_reference = (
                line_is_import_reference(
                    line,
                    terms,
                )
            )

            if evidence_path:
                reference_class = (
                    "GOVERNANCE_EVIDENCE_REFERENCE"
                )
                evidence_hits += 1
                evidence_reference_files.add(
                    repository_path
                )
            elif import_reference:
                reference_class = (
                    "OPERATIONAL_IMPORT_REFERENCE"
                )
                operational_hits += 1
                import_hits += 1
                operational_reference_files.add(
                    repository_path
                )
            elif operational_path:
                reference_class = (
                    "OPERATIONAL_TEXT_REFERENCE"
                )
                operational_hits += 1

                if repository_path.startswith(
                    "scripts/"
                ):
                    script_hits += 1

                operational_reference_files.add(
                    repository_path
                )
            else:
                reference_class = (
                    "OTHER_TEXT_REFERENCE"
                )
                other_hits += 1

            referencing_files.add(repository_path)

            excerpt = line.strip()

            if len(excerpt) > 400:
                excerpt = excerpt[:397] + "..."

            reference_rows.append(
                {
                    "snapshot_path": snapshot_path,
                    "reference_class": reference_class,
                    "referencing_file": repository_path,
                    "line_number": str(line_number),
                    "matched_term_type": term_type,
                    "line_excerpt": excerpt,
                }
            )

    counterpart_status = (
        snapshot["counterpart_status"].upper()
    )

    active_counterpart = (
        snapshot["active_counterpart"]
    )

    if operational_hits > 0:
        verification_status = (
            "OPERATIONAL_REFERENCE_FOUND"
        )
        archive_authorisation = "BLOCKED"
        recommended_disposition = (
            "RETAIN_AND_REVIEW_REFERENCES"
        )
        decision_basis = (
            "One or more operational references to the "
            "snapshot were detected."
        )
    elif (
        counterpart_status
        == "ACTIVE_COUNTERPART_FOUND"
        and active_counterpart
    ):
        verification_status = (
            "NO_OPERATIONAL_REFERENCE"
        )
        archive_authorisation = (
            "ELIGIBLE_AFTER_BUILD_VALIDATION"
        )
        recommended_disposition = (
            "ARCHIVE_CANDIDATE"
        )
        decision_basis = (
            "No operational references were detected and "
            "an active counterpart exists. Build and test "
            "validation is still required."
        )
    else:
        verification_status = (
            "NO_OPERATIONAL_REFERENCE"
        )
        archive_authorisation = (
            "BLOCKED_NO_ACTIVE_COUNTERPART"
        )
        recommended_disposition = (
            "MANUAL_ARCHITECTURAL_REVIEW"
        )
        decision_basis = (
            "No operational references were detected, "
            "but no active counterpart was established."
        )

    manifest_row = manifest_by_path.get(
        snapshot_path,
        {},
    )

    summary_rows.append(
        {
            "recovery_id": first_value(
                manifest_row,
                "recovery_id",
            ),
            "snapshot_path": snapshot_path,
            "snapshot_categories": (
                snapshot["snapshot_categories"]
            ),
            "tracked_by_git": (
                snapshot["tracked_by_git"]
            ),
            "counterpart_status": (
                snapshot["counterpart_status"]
            ),
            "active_counterpart": active_counterpart,
            "operational_reference_count": str(
                operational_hits
            ),
            "operational_import_count": str(
                import_hits
            ),
            "operational_script_reference_count": str(
                script_hits
            ),
            "governance_evidence_reference_count": str(
                evidence_hits
            ),
            "other_reference_count": str(
                other_hits
            ),
            "referencing_file_count": str(
                len(referencing_files)
            ),
            "operational_referencing_files": "|".join(
                sorted(
                    operational_reference_files,
                    key=str.lower,
                )
            ),
            "governance_evidence_files": "|".join(
                sorted(
                    evidence_reference_files,
                    key=str.lower,
                )
            ),
            "verification_status": (
                verification_status
            ),
            "archive_authorisation": (
                archive_authorisation
            ),
            "recommended_disposition": (
                recommended_disposition
            ),
            "decision_basis": decision_basis,
        }
    )


# ---------------------------------------
# Validation
# ---------------------------------------

errors: list[str] = []

if len(summary_rows) != len(snapshots):
    errors.append(
        "Snapshot verification row count does not "
        "match snapshot audit row count."
    )

snapshot_paths = [
    row["snapshot_path"]
    for row in summary_rows
]

if len(snapshot_paths) != len(
    set(snapshot_paths)
):
    errors.append(
        "Duplicate snapshot paths found in results."
    )

if snapshot_paths != sorted(
    snapshot_paths,
    key=str.lower,
):
    errors.append(
        "Snapshot verification ordering is not "
        "deterministic."
    )

for row in summary_rows:
    if not row["snapshot_path"]:
        errors.append(
            "Verification row missing snapshot path."
        )

    if not row["verification_status"]:
        errors.append(
            f"Missing verification status: "
            f"{row['snapshot_path']}"
        )

    if not row["archive_authorisation"]:
        errors.append(
            f"Missing archive authorisation: "
            f"{row['snapshot_path']}"
        )

if errors:
    print("VERDICT=FAIL")
    print(
        f"VALIDATION_ERRORS={len(errors)}"
    )

    for error in errors[:50]:
        print(f"ERROR={error}")

    raise RuntimeError(
        "Snapshot Reference Verification failed."
    )


# ---------------------------------------
# Counts
# ---------------------------------------

verification_counts = Counter(
    row["verification_status"]
    for row in summary_rows
)

authorisation_counts = Counter(
    row["archive_authorisation"]
    for row in summary_rows
)

disposition_counts = Counter(
    row["recommended_disposition"]
    for row in summary_rows
)

total_operational_references = sum(
    int(row["operational_reference_count"])
    for row in summary_rows
)

snapshots_with_operational_references = sum(
    1
    for row in summary_rows
    if int(
        row["operational_reference_count"]
    ) > 0
)

archive_candidates = (
    authorisation_counts.get(
        "ELIGIBLE_AFTER_BUILD_VALIDATION",
        0,
    )
)

blocked_referenced = (
    authorisation_counts.get(
        "BLOCKED",
        0,
    )
)

blocked_without_counterpart = (
    authorisation_counts.get(
        "BLOCKED_NO_ACTIVE_COUNTERPART",
        0,
    )
)

summary_payload = {
    "schema_version": "1.0",
    "program": "EDGEIQ Repository Recovery V2",
    "recovery_unit": (
        "RRV2 Unit 005 - Snapshot Reference Verification"
    ),
    "verdict": "PASS",
    "snapshot_candidates": len(summary_rows),
    "repository_files_examined": len(
        all_repository_files
    ),
    "text_files_examined": len(text_cache),
    "text_candidates_skipped": len(
        skipped_text_candidates
    ),
    "snapshots_with_operational_references": (
        snapshots_with_operational_references
    ),
    "total_operational_references": (
        total_operational_references
    ),
    "archive_candidates_after_build_validation": (
        archive_candidates
    ),
    "blocked_due_to_operational_references": (
        blocked_referenced
    ),
    "blocked_due_to_missing_counterpart": (
        blocked_without_counterpart
    ),
    "verification_status_counts": dict(
        sorted(verification_counts.items())
    ),
    "archive_authorisation_counts": dict(
        sorted(authorisation_counts.items())
    ),
    "recommended_disposition_counts": dict(
        sorted(disposition_counts.items())
    ),
    "skipped_text_candidates": (
        skipped_text_candidates
    ),
}


# ---------------------------------------
# Outputs
# ---------------------------------------

summary_fields = [
    "recovery_id",
    "snapshot_path",
    "snapshot_categories",
    "tracked_by_git",
    "counterpart_status",
    "active_counterpart",
    "operational_reference_count",
    "operational_import_count",
    "operational_script_reference_count",
    "governance_evidence_reference_count",
    "other_reference_count",
    "referencing_file_count",
    "operational_referencing_files",
    "governance_evidence_files",
    "verification_status",
    "archive_authorisation",
    "recommended_disposition",
    "decision_basis",
]

with OUTPUT_CSV.open(
    "w",
    encoding="utf-8-sig",
    newline="",
) as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=summary_fields,
    )
    writer.writeheader()
    writer.writerows(summary_rows)

with OUTPUT_JSON.open(
    "w",
    encoding="utf-8",
) as handle:
    json.dump(
        {
            "summary": summary_payload,
            "snapshot_verification": summary_rows,
            "reference_evidence": reference_rows,
        },
        handle,
        indent=2,
        ensure_ascii=False,
    )
    handle.write("\n")


def add_count_table(
    lines: list[str],
    heading: str,
    values: Counter[str],
) -> None:
    lines.extend(
        [
            f"## {heading}",
            "",
            "| Category | Count |",
            "|---|---:|",
        ]
    )

    for label, count in sorted(
        values.items(),
        key=lambda item: (
            -item[1],
            item[0],
        ),
    ):
        lines.append(
            f"| `{label}` | {count} |"
        )

    lines.append("")


report_lines: list[str] = [
    "# EDGEIQ Snapshot Reference Verification V1",
    "",
    "## Status",
    "",
    "**VERDICT: PASS**",
    "",
    (
        "The 77 snapshot and legacy source candidates "
        "were checked for references across tracked and "
        "untracked repository text files."
    ),
    "",
    (
        "Governance reports and recovery inventories "
        "were classified separately from operational "
        "source, build and configuration references."
    ),
    "",
    "No file was deleted, moved, renamed, staged or "
    "committed.",
    "",
    "## Summary",
    "",
    (
        f"- Snapshot candidates: "
        f"**{len(summary_rows)}**"
    ),
    (
        f"- Repository files examined: "
        f"**{len(all_repository_files)}**"
    ),
    (
        f"- Text files examined: "
        f"**{len(text_cache)}**"
    ),
    (
        "- Snapshots with operational references: "
        f"**{snapshots_with_operational_references}**"
    ),
    (
        "- Total operational references: "
        f"**{total_operational_references}**"
    ),
    (
        "- Archive candidates after build validation: "
        f"**{archive_candidates}**"
    ),
    (
        "- Blocked by operational references: "
        f"**{blocked_referenced}**"
    ),
    (
        "- Blocked because no active counterpart exists: "
        f"**{blocked_without_counterpart}**"
    ),
    "",
]

add_count_table(
    report_lines,
    "Verification Status",
    verification_counts,
)

add_count_table(
    report_lines,
    "Archive Authorisation",
    authorisation_counts,
)

report_lines.extend(
    [
        "## Operational References",
        "",
    ]
)

referenced_rows = [
    row
    for row in summary_rows
    if int(
        row["operational_reference_count"]
    ) > 0
]

if referenced_rows:
    for row in referenced_rows:
        report_lines.extend(
            [
                f"### `{row['snapshot_path']}`",
                "",
                (
                    "- Operational references: "
                    f"**{row['operational_reference_count']}**"
                ),
                (
                    "- Import references: "
                    f"**{row['operational_import_count']}**"
                ),
                (
                    "- Script references: "
                    f"**{row['operational_script_reference_count']}**"
                ),
                (
                    "- Referencing files: "
                    f"`{row['operational_referencing_files']}`"
                ),
                (
                    "- Decision: "
                    f"`{row['recommended_disposition']}`"
                ),
                "",
            ]
        )
else:
    report_lines.extend(
        [
            (
                "No operational references to snapshot "
                "or legacy source files were detected."
            ),
            "",
        ]
    )

report_lines.extend(
    [
        "## Missing Active Counterpart",
        "",
    ]
)

missing_counterpart_rows = [
    row
    for row in summary_rows
    if row["archive_authorisation"]
    == "BLOCKED_NO_ACTIVE_COUNTERPART"
]

if missing_counterpart_rows:
    for row in missing_counterpart_rows:
        report_lines.append(
            f"- `{row['snapshot_path']}`"
        )
else:
    report_lines.append("- None.")

report_lines.extend(
    [
        "",
        "## Archive Candidates",
        "",
        (
            "Files classified as "
            "`ELIGIBLE_AFTER_BUILD_VALIDATION` are not "
            "yet authorised for archival. They must pass "
            "the application build, TypeScript validation "
            "and governed regression checks after a "
            "proposed archive operation is simulated."
        ),
        "",
        "## Next Recovery Unit",
        "",
        (
            "**RRV2 Unit 006 - Snapshot Archive "
            "Simulation and Build Validation**"
        ),
        "",
        (
            "Create a reversible simulation of removing "
            "archive-eligible snapshots from the active "
            "source surface, then run governed application "
            "validation before any real movement or deletion."
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
    f"SNAPSHOT_CANDIDATES={len(summary_rows)}"
)
print(
    "SNAPSHOTS_WITH_OPERATIONAL_REFERENCES="
    f"{snapshots_with_operational_references}"
)
print(
    "TOTAL_OPERATIONAL_REFERENCES="
    f"{total_operational_references}"
)
print(
    "ARCHIVE_CANDIDATES_AFTER_BUILD_VALIDATION="
    f"{archive_candidates}"
)
print(
    "BLOCKED_DUE_TO_OPERATIONAL_REFERENCES="
    f"{blocked_referenced}"
)
print(
    "BLOCKED_DUE_TO_MISSING_COUNTERPART="
    f"{blocked_without_counterpart}"
)
print(
    f"REPOSITORY_FILES_EXAMINED="
    f"{len(all_repository_files)}"
)
print(
    f"TEXT_FILES_EXAMINED={len(text_cache)}"
)
print(f"CSV={OUTPUT_CSV}")
print(f"JSON={OUTPUT_JSON}")
print(f"REPORT={REPORT_MD}")
