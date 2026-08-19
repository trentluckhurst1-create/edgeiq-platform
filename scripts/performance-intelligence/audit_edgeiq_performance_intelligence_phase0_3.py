from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "public" / "data"
OUT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "phase0_3"
)

PROGRESS_INTERVAL = 250_000
SAMPLE_LIMIT = 5

CANDIDATES: dict[str, list[str]] = {
    "results_warehouse": [
        "public/data/edgeiq_results_master_v1.csv",
        "public/data/edgeiq_historical_results_warehouse_v2_graphql.csv",
        "public/data/edgeiq_canonical_results_truth_v1.csv",
        "public/data/edgeiq_racingcom_results_warehouse_full_v1.csv",
    ],
    "sectional_warehouse": [
        "public/data/edgeiq_standardised_sectionals_v1.csv",
        "public/data/racingcom_sectional_warehouse_v2.csv",
        "public/data/edgeiq_trusted_sectional_universe_v2.csv",
        "public/data/edgeiq_sectional_schema_v2.csv",
    ],
    "benchmark_engine": [
        "public/data/edgeiq_standard_times_v1.csv",
        "public/data/edgeiq_standardised_sectionals_v1.csv",
        "public/data/edgeiq_race_strength_v1.csv",
        "public/data/edgeiq_race_strength_history_v1.csv",
    ],
    "identity_engine": [
        "public/data/edgeiq_runner_entity_graph_v1.csv",
        "public/data/edgeiq_sectional_identity_engine_v3.csv",
        "public/data/edgeiq_temporal_identity_memory_v1.csv",
        "public/data/edgeiq_canonical_market_entity_graph_v1.csv",
    ],
    "performance_ratings": [
        "public/data/edgeiq_historical_performance_rating_v5_1.csv",
        "public/data/edgeiq_historical_performance_rating_v6_1_research.csv",
        "public/data/edgeiq_runner_history_detail_v1.csv",
        "public/data/edgeiq_race_strength_history_v1.csv",
    ],
    "length_conversion": [
        "public/data/edgeiq_standardised_sectionals_v1.csv",
        "public/data/edgeiq_lengths_per_point_engine_v1.csv",
    ],
}

CREATOR_SCRIPTS: dict[str, list[str]] = {
    "results_warehouse": [
        "scripts/build_edgeiq_results_master_v1.py",
        "scripts/build_edgeiq_results_master.py",
        "scripts/build_edgeiq_historical_results_warehouse_v2_graphql.py",
        "scripts/build_edgeiq_canonical_results_truth_v1.py",
        "scripts/build_edgeiq_racingcom_results_warehouse_all_v1.py",
        "scripts/build_edgeiq_results_warehouse_full_consolidation_v1.py",
    ],
    "sectional_warehouse": [
        "scripts/build_edgeiq_standardised_sectionals_v1.py",
        "scripts/build_racingcom_sectional_warehouse_v2.py",
        "scripts/build_edgeiq_trusted_sectional_universe_v2.py",
        "scripts/build_edgeiq_sectional_schema_v2.py",
        "scripts/build_edgeiq_sectional_normalisation_v1.py",
        "scripts/build_edgeiq_sectional_master_reconciliation_v1.py",
    ],
    "benchmark_engine": [
        "scripts/build_edgeiq_standard_times_v1.py",
        "scripts/build_edgeiq_standardised_sectionals_v1.py",
        "scripts/build_edgeiq_race_strength_v1.py",
        "scripts/build_edgeiq_race_strength_v2.py",
        "scripts/build_edgeiq_race_strength_v3.py",
        "scripts/build_edgeiq_race_strength_history_v1.py",
    ],
    "identity_engine": [
        "scripts/build_edgeiq_runner_entity_graph_v1.py",
        "scripts/build_edgeiq_sectional_identity_engine_v3.py",
        "scripts/build_edgeiq_temporal_identity_memory_v1.py",
        "scripts/build_edgeiq_canonical_market_entity_graph_v1.py",
    ],
    "performance_ratings": [
        "scripts/build_edgeiq_historical_performance_rating_v5_1.py",
        "scripts/build_edgeiq_historical_performance_rating_v6_1_research.py",
        "scripts/build_edgeiq_runner_history_detail_v1.py",
        "scripts/build_edgeiq_race_strength_history_v1.py",
    ],
    "length_conversion": [
        "scripts/build_edgeiq_standardised_sectionals_v1.py",
        "scripts/build_edgeiq_lengths_per_point_engine_v1.py",
    ],
}

KEY_GROUPS: dict[str, tuple[str, ...]] = {
    "race_identity": (
        "race_id",
        "race_key",
        "canonical_race_id",
        "meeting_id",
        "race_no",
        "race_number",
    ),
    "runner_identity": (
        "runner_id",
        "horse_id",
        "horse_key",
        "horse_key_join",
        "canonical_horse_id",
        "horse",
        "horse_name",
    ),
    "performance_identity": (
        "performance_id",
        "run_id",
        "race_runner_id",
        "runner_performance_id",
    ),
    "result_evidence": (
        "finish",
        "finish_pos",
        "position",
        "margin",
        "margin_l",
        "official_time",
        "race_time",
        "starting_price",
        "sp",
    ),
    "sectional_evidence": (
        "last_800",
        "last_600",
        "last_400",
        "last_200",
        "last_800_raw",
        "last_600_raw",
        "last_400_raw",
        "last_200_raw",
        "sectional_800",
        "sectional_600",
        "sectional_400",
        "sectional_200",
        "sectional_finish",
    ),
    "benchmark_governance": (
        "benchmark_id",
        "benchmark_mode",
        "benchmark_level",
        "benchmark_source",
        "benchmark_time_sec",
        "benchmark_sample_races",
        "sample_size",
        "confidence",
        "benchmark_version",
    ),
    "quality_governance": (
        "quality_state",
        "quality_status",
        "sectional_status",
        "race_identity_status",
        "trusted_race_identity",
        "trusted_modelling_identity",
        "source_confidence",
        "excluded",
        "exclusion_reason",
    ),
    "engine_versioning": (
        "engine_version",
        "benchmark_version",
        "conversion_version",
        "pattern_version",
        "fingerprint_version",
        "generated_at",
        "generated_timestamp",
        "built_at",
    ),
    "ratings": (
        "epi",
        "epi_post",
        "eri",
        "race_strength",
        "run_rating",
        "performance_rating",
        "rating",
    ),
    "length_conversion": (
        "seconds_per_length",
        "seconds_difference",
        "lengths_difference",
        "lengths_vs_benchmark",
        "standardised_last_600",
        "standardised_last_400",
        "standardised_last_200",
    ),
}

DATE_COLUMNS = (
    "race_date",
    "run_date_iso",
    "meeting_date",
    "date",
)

TRACK_COLUMNS = (
    "track",
    "track_name",
    "venue_name",
)

RACE_NUMBER_COLUMNS = (
    "race_no",
    "race_number",
)

HORSE_COLUMNS = (
    "runner_id",
    "horse_id",
    "horse_key",
    "horse_key_join",
    "horse",
    "horse_name",
)

REFERENCE_PATTERN = re.compile(
    r"""["']([^"']+\.(?:csv|json|parquet|feather|sqlite|sqlite3|db))["']""",
    re.IGNORECASE,
)

OUTPUT_ASSIGNMENT_PATTERN = re.compile(
    r"""(?P<name>[A-Z][A-Z0-9_]*)\s*=\s*(?:DATA|PUBLIC|ROOT|PROJECT_ROOT)[^
]*?["'](?P<file>[^"']+\.(?:csv|json|parquet|sqlite|db))["']""",
    re.IGNORECASE,
)

CONSTANT_PATTERN = re.compile(
    r"^([A-Z][A-Z0-9_]*)\s*=\s*(.+)$",
    re.MULTILINE,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def clean(value: Any) -> str:
    return str(value or "").strip()


def first_value(
    row: dict[str, str],
    columns: tuple[str, ...],
) -> str:
    for column in columns:
        value = clean(row.get(column))
        if value:
            return value
    return ""


def normalise_date(value: str) -> str:
    value = clean(value)

    if not value:
        return ""

    formats = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    )

    for date_format in formats:
        try:
            parsed = datetime.strptime(
                value[:19],
                date_format,
            )
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    iso_match = re.match(
        r"^(\d{4}-\d{2}-\d{2})",
        value,
    )

    if iso_match:
        return iso_match.group(1)

    return ""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    try:
        with path.open("rb") as handle:
            for block in iter(
                lambda: handle.read(4 * 1024 * 1024),
                b"",
            ):
                digest.update(block)
    except OSError:
        return ""

    return digest.hexdigest()


def field_presence(
    columns: list[str],
) -> dict[str, list[str]]:
    lower_map = {
        column.lower(): column
        for column in columns
    }

    result: dict[str, list[str]] = {}

    for group, candidates in KEY_GROUPS.items():
        result[group] = [
            lower_map[candidate]
            for candidate in candidates
            if candidate in lower_map
        ]

    return result


def build_race_key(
    row: dict[str, str],
) -> str:
    race_id = clean(
        row.get("race_id")
        or row.get("race_key")
        or row.get("canonical_race_id")
    )

    if race_id:
        return race_id.upper()

    race_date = normalise_date(
        first_value(row, DATE_COLUMNS)
    )
    track = first_value(row, TRACK_COLUMNS).upper()
    race_no = first_value(
        row,
        RACE_NUMBER_COLUMNS,
    )

    if race_date and track and race_no:
        return f"{race_date}|{track}|{race_no}"

    return ""


def build_horse_key(
    row: dict[str, str],
) -> str:
    value = first_value(row, HORSE_COLUMNS)
    return value.upper()


def build_performance_key(
    row: dict[str, str],
) -> str:
    explicit = clean(
        row.get("performance_id")
        or row.get("run_id")
        or row.get("race_runner_id")
        or row.get("runner_performance_id")
    )

    if explicit:
        return explicit.upper()

    race_key = build_race_key(row)
    horse_key = build_horse_key(row)

    if race_key and horse_key:
        return f"{race_key}|{horse_key}"

    return ""


def profile_csv(
    domain: str,
    path: Path,
) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "domain": domain,
        "path": rel(path),
        "exists": path.exists(),
        "sha256": "",
        "size_bytes": (
            path.stat().st_size
            if path.exists()
            else 0
        ),
        "modified_utc": (
            datetime.fromtimestamp(
                path.stat().st_mtime,
                tz=timezone.utc,
            ).isoformat()
            if path.exists()
            else ""
        ),
        "rows": 0,
        "columns": [],
        "column_count": 0,
        "min_date": "",
        "max_date": "",
        "unique_races": 0,
        "unique_horses": 0,
        "unique_performances": 0,
        "duplicate_performance_rows": 0,
        "missing_race_key_rows": 0,
        "missing_horse_key_rows": 0,
        "missing_performance_key_rows": 0,
        "field_groups": {},
        "field_non_empty_counts": {},
        "field_non_empty_pct": {},
        "sample_rows": [],
        "error": "",
    }

    if not path.exists():
        profile["error"] = "FILE_NOT_FOUND"
        return profile

    profile["sha256"] = file_sha256(path)

    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            errors="ignore",
            newline="",
        ) as handle:
            reader = csv.DictReader(handle)
            columns = list(reader.fieldnames or [])
            profile["columns"] = columns
            profile["column_count"] = len(columns)
            profile["field_groups"] = field_presence(
                columns
            )

            tracked_fields = sorted({
                field
                for fields in profile[
                    "field_groups"
                ].values()
                for field in fields
            })

            populated = Counter()
            dates: list[str] = []
            race_keys: set[str] = set()
            horse_keys: set[str] = set()
            performance_keys: set[str] = set()

            for row_number, row in enumerate(
                reader,
                start=1,
            ):
                profile["rows"] = row_number

                if (
                    row_number == 1
                    or row_number % PROGRESS_INTERVAL == 0
                ):
                    print(
                        f"FILE_PROGRESS={domain} "
                        f"{path.name} "
                        f"ROWS={row_number}",
                        flush=True,
                    )

                if row_number <= SAMPLE_LIMIT:
                    profile["sample_rows"].append(
                        {
                            column: clean(row.get(column))
                            for column in columns[:25]
                        }
                    )

                date_value = normalise_date(
                    first_value(row, DATE_COLUMNS)
                )

                if date_value:
                    dates.append(date_value)

                race_key = build_race_key(row)
                horse_key = build_horse_key(row)
                performance_key = build_performance_key(
                    row
                )

                if race_key:
                    race_keys.add(race_key)
                else:
                    profile[
                        "missing_race_key_rows"
                    ] += 1

                if horse_key:
                    horse_keys.add(horse_key)
                else:
                    profile[
                        "missing_horse_key_rows"
                    ] += 1

                if performance_key:
                    if performance_key in performance_keys:
                        profile[
                            "duplicate_performance_rows"
                        ] += 1
                    performance_keys.add(
                        performance_key
                    )
                else:
                    profile[
                        "missing_performance_key_rows"
                    ] += 1

                for field in tracked_fields:
                    if clean(row.get(field)):
                        populated[field] += 1

            if dates:
                profile["min_date"] = min(dates)
                profile["max_date"] = max(dates)

            profile["unique_races"] = len(race_keys)
            profile["unique_horses"] = len(
                horse_keys
            )
            profile["unique_performances"] = len(
                performance_keys
            )
            profile["field_non_empty_counts"] = dict(
                populated
            )

            if profile["rows"]:
                profile["field_non_empty_pct"] = {
                    field: round(
                        count
                        / profile["rows"]
                        * 100,
                        4,
                    )
                    for field, count in populated.items()
                }

    except Exception as exc:
        profile["error"] = str(exc)

    return profile


def safe_text(path: Path) -> str:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except OSError:
        return ""


def script_profile(
    domain: str,
    path: Path,
) -> dict[str, Any]:
    content = safe_text(path)

    profile: dict[str, Any] = {
        "domain": domain,
        "path": rel(path),
        "exists": path.exists(),
        "syntax_status": "NOT_PARSED",
        "functions": [],
        "imports": [],
        "constants": [],
        "references": [],
        "candidate_outputs": [],
        "sign_convention_evidence": [],
        "versioning_evidence": [],
        "quality_evidence": [],
        "error": "",
    }

    if not content:
        profile["syntax_status"] = (
            "MISSING_OR_EMPTY"
        )
        return profile

    try:
        tree = ast.parse(content)
        profile["syntax_status"] = "PARSED"

        profile["functions"] = sorted({
            node.name
            for node in ast.walk(tree)
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
        })

        imports: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(
                    alias.name
                    for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)

        profile["imports"] = sorted(imports)

    except SyntaxError as exc:
        profile["syntax_status"] = "SYNTAX_ERROR"
        profile["error"] = str(exc)

    constants = []

    for match in CONSTANT_PATTERN.finditer(
        content
    ):
        name = match.group(1)
        value = match.group(2).strip()

        if any(
            term in name
            for term in (
                "LENGTH",
                "SECOND",
                "BENCHMARK",
                "VERSION",
                "OUT",
                "WAREHOUSE",
                "STANDARD",
            )
        ):
            constants.append(
                {
                    "name": name,
                    "value": value[:500],
                }
            )

    profile["constants"] = constants[:200]

    references: list[str] = []

    for match in REFERENCE_PATTERN.finditer(
        content
    ):
        reference = (
            match.group(1)
            .replace("\\", "/")
        )

        if reference not in references:
            references.append(reference)

    profile["references"] = references

    outputs = []

    for match in OUTPUT_ASSIGNMENT_PATTERN.finditer(
        content
    ):
        outputs.append(
            {
                "constant": match.group("name"),
                "file": match.group("file"),
            }
        )

    profile["candidate_outputs"] = outputs

    lines = content.splitlines()

    for line_number, line in enumerate(
        lines,
        start=1,
    ):
        lowered = line.lower()

        if (
            "negative" in lowered
            and (
                "benchmark" in lowered
                or "faster" in lowered
                or "green" in lowered
            )
        ):
            profile[
                "sign_convention_evidence"
            ].append(
                {
                    "line_number": line_number,
                    "line_text": line.strip()[:500],
                }
            )

        if any(
            term in lowered
            for term in (
                "engine_version",
                "benchmark_version",
                "conversion_version",
                "generated_at",
                "built_at",
                "version",
            )
        ):
            if len(
                profile["versioning_evidence"]
            ) < 30:
                profile[
                    "versioning_evidence"
                ].append(
                    {
                        "line_number": line_number,
                        "line_text": line.strip()[:500],
                    }
                )

        if any(
            term in lowered
            for term in (
                "quality_state",
                "confidence",
                "excluded",
                "mismatch",
                "trusted",
                "unsafe",
            )
        ):
            if len(
                profile["quality_evidence"]
            ) < 30:
                profile[
                    "quality_evidence"
                ].append(
                    {
                        "line_number": line_number,
                        "line_text": line.strip()[:500],
                    }
                )

    return profile


def evaluate_candidate(
    profile: dict[str, Any],
) -> dict[str, Any]:
    rows = profile["rows"]
    groups = profile["field_groups"]

    identity_score = 0
    evidence_score = 0
    governance_score = 0
    versioning_score = 0
    coverage_score = 0

    if groups.get("race_identity"):
        identity_score += 25

    if groups.get("runner_identity"):
        identity_score += 25

    if groups.get("performance_identity"):
        identity_score += 20

    if rows and not profile[
        "missing_performance_key_rows"
    ]:
        identity_score += 15

    if rows and not profile[
        "duplicate_performance_rows"
    ]:
        identity_score += 15

    if groups.get("result_evidence"):
        evidence_score += 30

    if groups.get("sectional_evidence"):
        evidence_score += 30

    if groups.get("ratings"):
        evidence_score += 20

    if groups.get("length_conversion"):
        evidence_score += 20

    if groups.get("benchmark_governance"):
        governance_score += 45

    if groups.get("quality_governance"):
        governance_score += 45

    if profile["error"] == "":
        governance_score += 10

    if groups.get("engine_versioning"):
        versioning_score = 100

    if rows >= 500_000:
        coverage_score = 100
    elif rows >= 100_000:
        coverage_score = 85
    elif rows >= 50_000:
        coverage_score = 70
    elif rows >= 10_000:
        coverage_score = 55
    elif rows >= 1_000:
        coverage_score = 40
    elif rows > 0:
        coverage_score = 20

    total = round(
        identity_score * 0.30
        + evidence_score * 0.25
        + governance_score * 0.20
        + versioning_score * 0.15
        + coverage_score * 0.10,
        2,
    )

    blockers: list[str] = []

    if not groups.get("performance_identity"):
        blockers.append(
            "NO_EXPLICIT_PERFORMANCE_ID"
        )

    if not groups.get("quality_governance"):
        blockers.append(
            "NO_EXPLICIT_QUALITY_GOVERNANCE"
        )

    if not groups.get("engine_versioning"):
        blockers.append(
            "NO_EXPLICIT_ENGINE_VERSIONING"
        )

    if profile[
        "duplicate_performance_rows"
    ] > 0:
        blockers.append(
            "DUPLICATE_PERFORMANCE_KEYS"
        )

    if profile[
        "missing_performance_key_rows"
    ] > 0:
        blockers.append(
            "MISSING_PERFORMANCE_KEYS"
        )

    status = "UNSAFE_TO_DECLARE_CANONICAL"

    if not blockers and total >= 80:
        status = "CANONICAL_CANDIDATE"
    elif total >= 60:
        status = "REUSABLE_AFTER_MIGRATION"
    elif total >= 40:
        status = "REQUIRES_VALIDATION"
    elif rows:
        status = "LEGACY_OR_PARTIAL"
    else:
        status = "MISSING_OR_EMPTY"

    return {
        "domain": profile["domain"],
        "path": profile["path"],
        "rows": rows,
        "min_date": profile["min_date"],
        "max_date": profile["max_date"],
        "unique_races": profile[
            "unique_races"
        ],
        "unique_horses": profile[
            "unique_horses"
        ],
        "unique_performances": profile[
            "unique_performances"
        ],
        "duplicate_performance_rows": profile[
            "duplicate_performance_rows"
        ],
        "missing_performance_key_rows": profile[
            "missing_performance_key_rows"
        ],
        "identity_score": identity_score,
        "evidence_score": evidence_score,
        "governance_score": governance_score,
        "versioning_score": versioning_score,
        "coverage_score": coverage_score,
        "total_score": total,
        "classification": status,
        "blockers": " | ".join(blockers),
        "sha256": profile["sha256"],
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

    fieldnames: list[str] = []

    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


def build_report(
    summary: dict[str, Any],
    evaluations: list[dict[str, Any]],
) -> str:
    lines: list[str] = []

    lines.append(
        "# EDGEiQ Performance Intelligence"
    )
    lines.append(
        "## Phase 0.3 Canonical Candidate Validation"
    )
    lines.append("")
    lines.append(
        f"Generated UTC: `{summary['generated_utc']}`"
    )
    lines.append("")
    lines.append(
        "No candidate is declared canonical solely "
        "from file size, row count, naming, or a prior PASS audit."
    )
    lines.append("")

    for domain in CANDIDATES:
        lines.append(f"## {domain}")
        lines.append("")
        lines.append(
            "| Score | Classification | Path | Rows | "
            "Performances | Duplicates | Blockers |"
        )
        lines.append(
            "|---:|---|---|---:|---:|---:|---|"
        )

        domain_rows = sorted(
            [
                row
                for row in evaluations
                if row["domain"] == domain
            ],
            key=lambda row: (
                -row["total_score"],
                row["path"],
            ),
        )

        for row in domain_rows:
            lines.append(
                f"| {row['total_score']} | "
                f"{row['classification']} | "
                f"`{row['path']}` | "
                f"{row['rows']} | "
                f"{row['unique_performances']} | "
                f"{row['duplicate_performance_rows']} | "
                f"{row['blockers']} |"
            )

        lines.append("")

    lines.append("## Required architectural response")
    lines.append("")
    lines.append(
        "Preserve reusable evidence and transformations, "
        "but migrate all selected assets into an immutable, "
        "versioned canonical performance model with explicit "
        "performance IDs, source lineage, quality states, "
        "engine versions and reproducible derivation records."
    )
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    OUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_profiles: list[dict[str, Any]] = []
    all_evaluations: list[dict[str, Any]] = []
    all_scripts: list[dict[str, Any]] = []

    unique_data_paths: dict[
        str,
        tuple[str, Path],
    ] = {}

    for domain, relative_paths in (
        CANDIDATES.items()
    ):
        for relative_path in relative_paths:
            path = ROOT / relative_path
            key = str(path.resolve()).lower()

            if key not in unique_data_paths:
                unique_data_paths[key] = (
                    domain,
                    path,
                )

    total_files = len(unique_data_paths)

    for file_index, (
        _,
        (primary_domain, path),
    ) in enumerate(
        unique_data_paths.items(),
        start=1,
    ):
        domains = [
            domain
            for domain, relative_paths
            in CANDIDATES.items()
            if rel(path) in relative_paths
        ]

        print(
            f"CANDIDATE_START={file_index}/"
            f"{total_files} "
            f"{rel(path)} "
            f"DOMAINS={','.join(domains)}",
            flush=True,
        )

        base_profile = profile_csv(
            primary_domain,
            path,
        )

        for domain in domains:
            profile = dict(base_profile)
            profile["domain"] = domain
            all_profiles.append(profile)
            all_evaluations.append(
                evaluate_candidate(profile)
            )

        print(
            f"CANDIDATE_COMPLETE="
            f"{rel(path)} "
            f"ROWS={base_profile['rows']} "
            f"PERFORMANCES="
            f"{base_profile['unique_performances']} "
            f"DUPLICATES="
            f"{base_profile['duplicate_performance_rows']}",
            flush=True,
        )

    for domain, script_paths in (
        CREATOR_SCRIPTS.items()
    ):
        for relative_path in script_paths:
            all_scripts.append(
                script_profile(
                    domain,
                    ROOT / relative_path,
                )
            )

    domain_rankings: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    for domain in CANDIDATES:
        domain_rankings[domain] = sorted(
            [
                row
                for row in all_evaluations
                if row["domain"] == domain
            ],
            key=lambda row: (
                -row["total_score"],
                row["path"],
            ),
        )

    top_candidates = {
        domain: (
            rows[0]
            if rows
            else None
        )
        for domain, rows in domain_rankings.items()
    }

    run_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    detail_path = (
        OUT
        / f"edgeiq_performance_intelligence_phase0_3_detail_{run_id}.json"
    )
    evaluation_path = (
        OUT
        / f"edgeiq_performance_intelligence_phase0_3_evaluation_{run_id}.csv"
    )
    summary_path = (
        OUT
        / f"edgeiq_performance_intelligence_phase0_3_summary_{run_id}.json"
    )
    report_path = (
        OUT
        / f"edgeiq_performance_intelligence_phase0_3_report_{run_id}.md"
    )
    latest_path = (
        OUT
        / "edgeiq_performance_intelligence_phase0_3_latest.json"
    )

    detail = {
        "audit_name": (
            "EDGEiQ Performance Intelligence "
            "Phase 0.3 Canonical Candidate Validation"
        ),
        "generated_utc": utc_now(),
        "profiles": all_profiles,
        "evaluations": all_evaluations,
        "script_profiles": all_scripts,
        "domain_rankings": domain_rankings,
        "top_candidates": top_candidates,
    }

    summary = {
        "audit_name": detail["audit_name"],
        "generated_utc": detail[
            "generated_utc"
        ],
        "files_profiled": total_files,
        "domain_evaluations": len(
            all_evaluations
        ),
        "scripts_profiled": len(
            all_scripts
        ),
        "top_candidates": top_candidates,
        "canonical_status": (
            "NO_ASSET_DECLARED_CANONICAL_YET"
        ),
        "next_stage": (
            "Phase 0.4 canonical schema and migration map"
        ),
    }

    write_json(detail_path, detail)
    write_json(summary_path, summary)
    write_json(latest_path, summary)
    write_csv(
        evaluation_path,
        sorted(
            all_evaluations,
            key=lambda row: (
                row["domain"],
                -row["total_score"],
                row["path"],
            ),
        ),
    )

    report_path.write_text(
        build_report(
            summary,
            all_evaluations,
        ),
        encoding="utf-8",
    )

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE0_3_CANONICAL_CANDIDATE_"
        "VALIDATION_PASS",
        flush=True,
    )
    print(
        f"DETAIL={detail_path}",
        flush=True,
    )
    print(
        f"EVALUATION={evaluation_path}",
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
