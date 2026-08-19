from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


AUDIT_ID = "EDGEIQ_FULL_PRODUCT_DATA_WIRING_AUDIT_V1"

REPOSITORY_ROOT = Path.cwd().resolve()
SOURCE_ROOT = REPOSITORY_ROOT / "src"
PUBLIC_ROOT = REPOSITORY_ROOT / "public"
SCRIPTS_ROOT = REPOSITORY_ROOT / "scripts"
OUTPUT_ROOT = REPOSITORY_ROOT / "docs" / "full-product-data-wiring-audit-v1"

APPROVED_WORKSPACES = [
    "HOME",
    "MEETINGS",
    "RACE",
    "FIELD",
    "PERFORMANCE",
    "FORM",
    "MAP",
    "NEXUS",
    "MARKET",
    "RESULTS",
    "TRACK",
    "WEATHER",
    "OVERVIEW",
    "INSIGHTS",
    "LAB",
]

SOURCE_SUFFIXES = {
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".py",
    ".ps1",
}

DATA_SUFFIXES = {
    ".json",
    ".csv",
    ".parquet",
    ".sqlite",
    ".sqlite3",
    ".db",
}

IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".idea",
    ".vscode",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
}

HISTORICAL_DIRECTORY_NAMES = {
    "archive",
    "archives",
    "_archive",
    "_archive_pre_git_commit",
    "backup",
    "backups",
    "checkpoint",
    "checkpoints",
    "legacy",
    "old",
    "recovery",
}

PLACEHOLDER_PATTERNS = {
    "HARDCODED_PLACEHOLDER_TEXT": re.compile(
        r"\b(?:placeholder|mock data|sample data|demo data|coming soon|"
        r"not available|unavailable|unknown|tbc|todo|stub)\b",
        re.IGNORECASE,
    ),
    "EXPLICIT_ZERO_FALLBACK": re.compile(
        r"(?:\?\?|\|\|)\s*(?:0|0\.0|['\"]0['\"])",
        re.IGNORECASE,
    ),
    "EMPTY_ARRAY_FALLBACK": re.compile(
        r"(?:\?\?|\|\|)\s*\[\s*\]",
        re.IGNORECASE,
    ),
    "EMPTY_OBJECT_FALLBACK": re.compile(
        r"(?:\?\?|\|\|)\s*\{\s*\}",
        re.IGNORECASE,
    ),
    "STATIC_RUNNER_DATA": re.compile(
        r"\b(?:runner|horse|jockey|trainer)\w*\s*[:=]\s*['\"]"
        r"(?:horse|runner|jockey|trainer)\s*\d*['\"]",
        re.IGNORECASE,
    ),
}

COLUMN_LABEL_PATTERN = re.compile(
    r"""
    (?:
        header\s*:\s*|
        label\s*:\s*|
        title\s*:\s*|
        columnLabel\s*:\s*|
        <th[^>]*>\s*|
        <dt[^>]*>\s*
    )
    ["'`]?
    ([A-Za-z][A-Za-z0-9 %+\-/.&()]{1,48})
    ["'`]?
    """,
    re.IGNORECASE | re.VERBOSE,
)

OBJECT_KEY_PATTERN = re.compile(
    r"""
    (?:
        ^|[,{]\s*
    )
    (?:
        ['"]([A-Za-z_][A-Za-z0-9_]*)['"]|
        ([A-Za-z_][A-Za-z0-9_]*)
    )
    \s*:
    """,
    re.MULTILINE | re.VERBOSE,
)

PROPERTY_ACCESS_PATTERN = re.compile(
    r"\b(?:row|runner|horse|item|record|entry|race|meeting|data|feed|"
    r"result|weather|track|market|form|profile|workspace)\."
    r"([A-Za-z_][A-Za-z0-9_]*)"
)

BRACKET_ACCESS_PATTERN = re.compile(
    r"\[['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\]"
)

FETCH_PATTERN = re.compile(
    r"""
    \bfetch\s*\(
        \s*
        (?:
            ["'`]([^"'`]+)["'`]|
            ([A-Za-z_][A-Za-z0-9_]*)
        )
    """,
    re.IGNORECASE | re.VERBOSE,
)

URL_ASSIGNMENT_PATTERN = re.compile(
    r"""
    \b(?:const|let|var)\s+
    ([A-Za-z_][A-Za-z0-9_]*)
    \s*=\s*
    ["'`]([^"'`]+)["'`]
    """,
    re.IGNORECASE | re.VERBOSE,
)

IMPORT_PATTERN = re.compile(
    r"""
    (?:import|export)\s+
    (?:
        [^;]*?\s+from\s+
    )?
    ["']([^"']+)["']
    """,
    re.MULTILINE | re.VERBOSE,
)

DYNAMIC_IMPORT_PATTERN = re.compile(
    r"""
    import\s*\(\s*["']([^"']+)["']\s*\)
    """,
    re.MULTILINE | re.VERBOSE,
)

ROUTE_PATTERN = re.compile(
    r"""
    (?:path|route|workspace|activeTab|tab|id|key)
    \s*[:=]\s*
    ["'`]([^"'`]{1,80})["'`]
    """,
    re.IGNORECASE | re.VERBOSE,
)

DATA_PATH_PATTERN = re.compile(
    r"""
    ["'`]
    (
        /?
        [A-Za-z0-9_./@\- ]+
        \.(?:json|csv|parquet|sqlite3?|db)
        (?:\?[^"'`]*)?
    )
    ["'`]
    """,
    re.IGNORECASE | re.VERBOSE,
)


@dataclass
class SourceFileRecord:
    relative_path: str
    suffix: str
    source_kind: str
    workspace: str
    file_size: int
    sha256: str
    is_historical_path: bool


@dataclass
class WorkspaceFileRecord:
    workspace: str
    relative_path: str
    source_kind: str
    confidence: str
    evidence: str


@dataclass
class ImportRecord:
    source_file: str
    import_value: str
    resolved_file: str
    resolution_status: str


@dataclass
class FeedReferenceRecord:
    workspace: str
    source_file: str
    reference_type: str
    referenced_value: str
    resolved_path: str
    exists: bool
    file_size: int
    resolution_status: str


@dataclass
class VisibleFieldRecord:
    workspace: str
    component_file: str
    visible_label: str
    normalised_label: str
    evidence_type: str


@dataclass
class BindingRecord:
    workspace: str
    component_file: str
    bound_field: str
    evidence_type: str
    occurrence_count: int


@dataclass
class FeedSchemaRecord:
    feed_path: str
    feed_type: str
    sample_record_path: str
    field_name: str
    value_type: str
    populated_count: int
    sampled_count: int
    population_rate: float


@dataclass
class PlaceholderRecord:
    workspace: str
    source_file: str
    finding_type: str
    line_number: int
    line_text: str


@dataclass
class WiringCandidateRecord:
    workspace: str
    visible_label: str
    candidate_field: str
    candidate_source_file: str
    feed_path: str
    feed_has_field: bool
    field_population_rate: float
    mapping_confidence: str
    status: str
    reason: str


def safe_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPOSITORY_ROOT).as_posix()
    except Exception:
        return path.as_posix()


def is_ignored(path: Path) -> bool:
    lowered_parts = {part.lower() for part in path.parts}
    return bool(lowered_parts & IGNORED_DIRECTORY_NAMES)


def is_historical_path(path: Path) -> bool:
    parts = [part.lower() for part in path.parts]
    return any(part in HISTORICAL_DIRECTORY_NAMES for part in parts)


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
        except OSError:
            return ""
    return ""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return ""


def normalise_workspace(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", value).strip().upper()

    aliases = {
        "MEETING": "MEETINGS",
        "MEETING DETAIL": "MEETINGS",
        "RACE WORKSPACE": "RACE",
        "FIELD WORKSPACE": "FIELD",
        "EPI": "PERFORMANCE",
        "EPI WORKSPACE": "PERFORMANCE",
        "PERFORMANCE INTELLIGENCE": "PERFORMANCE",
        "FORM GUIDE": "FORM",
        "SPEED MAP": "MAP",
        "MARKET TAPE": "MARKET",
        "RACE RESULTS": "RESULTS",
        "TRACK CONDITIONS": "TRACK",
        "RACE OVERVIEW": "OVERVIEW",
        "RACE INSIGHTS": "INSIGHTS",
        "METRICS EXPLORER": "LAB",
    }

    if cleaned in aliases:
        return aliases[cleaned]

    for workspace in APPROVED_WORKSPACES:
        if re.search(rf"\b{re.escape(workspace)}\b", cleaned):
            return workspace

    return "UNASSIGNED"


def infer_workspace(path: Path, text: str = "") -> tuple[str, str, str]:
    relative = safe_relative(path)
    combined = f"{relative}\n{text[:25000]}"

    candidates: list[tuple[str, str]] = []

    file_name = path.stem
    path_parts = " ".join(path.parts)

    for workspace in APPROVED_WORKSPACES:
        workspace_pattern = workspace.lower()

        if workspace_pattern in file_name.lower():
            candidates.append((workspace, f"filename:{path.name}"))

        if re.search(
            rf"(?:^|[^a-z]){re.escape(workspace_pattern)}(?:[^a-z]|$)",
            path_parts.lower(),
        ):
            candidates.append((workspace, f"path:{relative}"))

    route_values = ROUTE_PATTERN.findall(text[:50000])
    for value in route_values:
        workspace = normalise_workspace(value)
        if workspace != "UNASSIGNED":
            candidates.append((workspace, f"route-or-tab:{value}"))

    component_name_match = re.search(
        r"\b(?:function|const|class)\s+([A-Z][A-Za-z0-9_]*)",
        text,
    )
    if component_name_match:
        workspace = normalise_workspace(component_name_match.group(1))
        if workspace != "UNASSIGNED":
            candidates.append(
                (workspace, f"component:{component_name_match.group(1)}")
            )

    if not candidates:
        return "UNASSIGNED", "LOW", "no workspace evidence"

    counts = Counter(workspace for workspace, _ in candidates)
    selected, selected_count = counts.most_common(1)[0]

    evidence = "; ".join(
        sorted({item for workspace, item in candidates if workspace == selected})
    )

    confidence = "HIGH" if selected_count >= 2 else "MEDIUM"

    return selected, confidence, evidence


def source_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    relative = safe_relative(path).lower()

    if suffix in {".tsx", ".jsx"}:
        return "REACT_COMPONENT"

    if suffix in {".ts", ".js"}:
        if "/services/" in f"/{relative}/" or path.stem.lower().endswith(
            ("service", "feed")
        ):
            return "TYPESCRIPT_SERVICE"
        return "TYPESCRIPT_SOURCE"

    if suffix == ".py":
        if path.name.startswith("build_"):
            return "PYTHON_BUILDER"
        if path.name.startswith("audit_"):
            return "PYTHON_AUDIT"
        return "PYTHON_SOURCE"

    if suffix == ".ps1":
        return "POWERSHELL_ORCHESTRATOR"

    return "OTHER_SOURCE"


def iter_source_files() -> Iterable[Path]:
    roots = [SOURCE_ROOT, SCRIPTS_ROOT]

    root_candidates = [
        REPOSITORY_ROOT / "src" / "main.tsx",
        REPOSITORY_ROOT / "src" / "App.tsx",
        REPOSITORY_ROOT / "vite.config.ts",
        REPOSITORY_ROOT / "package.json",
    ]

    yielded: set[Path] = set()

    for candidate in root_candidates:
        if candidate.exists():
            resolved = candidate.resolve()
            yielded.add(resolved)
            yield resolved

    for root in roots:
        if not root.exists():
            continue

        for path in root.rglob("*"):
            if not path.is_file():
                continue

            if is_ignored(path):
                continue

            if is_historical_path(path):
                continue

            if path.suffix.lower() not in SOURCE_SUFFIXES:
                continue

            resolved = path.resolve()

            if resolved in yielded:
                continue

            yielded.add(resolved)
            yield resolved


def resolve_import(source_path: Path, import_value: str) -> tuple[str, str]:
    if not import_value.startswith("."):
        return "", "PACKAGE_OR_ALIAS"

    base = (source_path.parent / import_value).resolve()

    candidates = [
        base,
        base.with_suffix(".ts"),
        base.with_suffix(".tsx"),
        base.with_suffix(".js"),
        base.with_suffix(".jsx"),
        base / "index.ts",
        base / "index.tsx",
        base / "index.js",
        base / "index.jsx",
    ]

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return safe_relative(candidate), "RESOLVED"

    return safe_relative(base), "MISSING"


def resolve_data_reference(value: str) -> tuple[Path | None, str]:
    clean = value.split("?", 1)[0].strip()

    if not clean:
        return None, "EMPTY_REFERENCE"

    if clean.startswith(("http://", "https://")):
        return None, "REMOTE_URL"

    clean_path = clean.replace("\\", "/")

    candidates: list[Path] = []

    if clean_path.startswith("/"):
        candidates.append(PUBLIC_ROOT / clean_path.lstrip("/"))
    else:
        candidates.extend(
            [
                REPOSITORY_ROOT / clean_path,
                PUBLIC_ROOT / clean_path,
                SOURCE_ROOT / clean_path,
            ]
        )

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve(), "RESOLVED"

    return candidates[0].resolve() if candidates else None, "MISSING"


def extract_variable_urls(text: str) -> dict[str, str]:
    values: dict[str, str] = {}

    for variable, value in URL_ASSIGNMENT_PATTERN.findall(text):
        if value.lower().endswith(
            (".json", ".csv", ".parquet", ".sqlite", ".sqlite3", ".db")
        ):
            values[variable] = value

    return values


def discover_sources():
    source_records: list[SourceFileRecord] = []
    workspace_records: list[WorkspaceFileRecord] = []
    source_texts: dict[str, str] = {}
    workspace_by_file: dict[str, str] = {}

    files = sorted(iter_source_files(), key=lambda item: safe_relative(item))

    for index, path in enumerate(files, start=1):
        relative = safe_relative(path)
        text = read_text(path)
        workspace, confidence, evidence = infer_workspace(path, text)

        source_texts[relative] = text
        workspace_by_file[relative] = workspace

        source_records.append(
            SourceFileRecord(
                relative_path=relative,
                suffix=path.suffix.lower(),
                source_kind=source_kind(path),
                workspace=workspace,
                file_size=path.stat().st_size,
                sha256=sha256_file(path),
                is_historical_path=is_historical_path(path),
            )
        )

        workspace_records.append(
            WorkspaceFileRecord(
                workspace=workspace,
                relative_path=relative,
                source_kind=source_kind(path),
                confidence=confidence,
                evidence=evidence,
            )
        )

        if index == 1 or index % 250 == 0:
            print(f"[sources] {index}/{len(files)} {relative}", flush=True)

    return (
        source_records,
        workspace_records,
        source_texts,
        workspace_by_file,
    )


def discover_imports(
    source_texts: dict[str, str],
) -> list[ImportRecord]:
    rows: list[ImportRecord] = []

    for relative, text in source_texts.items():
        path = REPOSITORY_ROOT / relative

        imports = set(IMPORT_PATTERN.findall(text))
        imports.update(DYNAMIC_IMPORT_PATTERN.findall(text))

        for import_value in sorted(imports):
            resolved, status = resolve_import(path, import_value)

            rows.append(
                ImportRecord(
                    source_file=relative,
                    import_value=import_value,
                    resolved_file=resolved,
                    resolution_status=status,
                )
            )

    return rows


def discover_feed_references(
    source_texts: dict[str, str],
    workspace_by_file: dict[str, str],
) -> list[FeedReferenceRecord]:
    rows: list[FeedReferenceRecord] = []
    seen: set[tuple[str, str, str]] = set()

    for relative, text in source_texts.items():
        workspace = workspace_by_file.get(relative, "UNASSIGNED")
        variable_urls = extract_variable_urls(text)

        references: list[tuple[str, str]] = []

        for quoted_value, variable_name in FETCH_PATTERN.findall(text):
            if quoted_value:
                references.append(("FETCH_URL", quoted_value))
            elif variable_name and variable_name in variable_urls:
                references.append(
                    ("FETCH_VARIABLE_URL", variable_urls[variable_name])
                )

        for value in DATA_PATH_PATTERN.findall(text):
            references.append(("QUOTED_DATA_PATH", value))

        for reference_type, value in references:
            key = (relative, reference_type, value)
            if key in seen:
                continue
            seen.add(key)

            resolved, status = resolve_data_reference(value)

            exists = bool(resolved and resolved.exists())
            file_size = (
                resolved.stat().st_size
                if resolved and resolved.exists() and resolved.is_file()
                else 0
            )

            rows.append(
                FeedReferenceRecord(
                    workspace=workspace,
                    source_file=relative,
                    reference_type=reference_type,
                    referenced_value=value,
                    resolved_path=safe_relative(resolved) if resolved else "",
                    exists=exists,
                    file_size=file_size,
                    resolution_status=status,
                )
            )

    return rows


def normalise_label(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    value = value.strip("`'\"")
    return value.upper()


def discover_visible_fields(
    source_texts: dict[str, str],
    workspace_by_file: dict[str, str],
) -> list[VisibleFieldRecord]:
    rows: list[VisibleFieldRecord] = []
    seen: set[tuple[str, str, str]] = set()

    for relative, text in source_texts.items():
        if not relative.lower().endswith((".tsx", ".jsx")):
            continue

        workspace = workspace_by_file.get(relative, "UNASSIGNED")

        for match in COLUMN_LABEL_PATTERN.finditer(text):
            label = match.group(1).strip()
            normalised = normalise_label(label)

            if len(normalised) < 2:
                continue

            if normalised in {
                "TRUE",
                "FALSE",
                "NULL",
                "UNDEFINED",
                "CLASSNAME",
                "STYLE",
                "KEY",
                "VALUE",
            }:
                continue

            key = (workspace, relative, normalised)
            if key in seen:
                continue

            seen.add(key)

            rows.append(
                VisibleFieldRecord(
                    workspace=workspace,
                    component_file=relative,
                    visible_label=label,
                    normalised_label=normalised,
                    evidence_type="COLUMN_OR_DISPLAY_LABEL",
                )
            )

    return rows


def discover_bindings(
    source_texts: dict[str, str],
    workspace_by_file: dict[str, str],
) -> list[BindingRecord]:
    rows: list[BindingRecord] = []

    for relative, text in source_texts.items():
        if not relative.lower().endswith((".tsx", ".jsx")):
            continue

        workspace = workspace_by_file.get(relative, "UNASSIGNED")

        field_counter: Counter[tuple[str, str]] = Counter()

        for field in PROPERTY_ACCESS_PATTERN.findall(text):
            field_counter[(field, "PROPERTY_ACCESS")] += 1

        for field in BRACKET_ACCESS_PATTERN.findall(text):
            field_counter[(field, "BRACKET_ACCESS")] += 1

        for (field, evidence_type), count in sorted(field_counter.items()):
            rows.append(
                BindingRecord(
                    workspace=workspace,
                    component_file=relative,
                    bound_field=field,
                    evidence_type=evidence_type,
                    occurrence_count=count,
                )
            )

    return rows


def discover_placeholders(
    source_texts: dict[str, str],
    workspace_by_file: dict[str, str],
) -> list[PlaceholderRecord]:
    rows: list[PlaceholderRecord] = []

    for relative, text in source_texts.items():
        if not relative.lower().endswith((".ts", ".tsx", ".js", ".jsx")):
            continue

        workspace = workspace_by_file.get(relative, "UNASSIGNED")

        for line_number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()

            if not stripped:
                continue

            if stripped.startswith(("//", "/*", "*")):
                continue

            for finding_type, pattern in PLACEHOLDER_PATTERNS.items():
                if pattern.search(line):
                    rows.append(
                        PlaceholderRecord(
                            workspace=workspace,
                            source_file=relative,
                            finding_type=finding_type,
                            line_number=line_number,
                            line_text=stripped[:500],
                        )
                    )

    return rows


def value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def is_populated(value: Any) -> bool:
    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    if isinstance(value, (list, dict)):
        return len(value) > 0

    return True


def flatten_json_samples(
    value: Any,
    path: str = "$",
    depth: int = 0,
    max_depth: int = 7,
    max_list_items: int = 50,
) -> list[tuple[str, dict[str, Any]]]:
    records: list[tuple[str, dict[str, Any]]] = []

    if depth > max_depth:
        return records

    if isinstance(value, dict):
        scalar_values = {
            key: item
            for key, item in value.items()
            if not isinstance(item, (dict, list))
        }

        if scalar_values:
            records.append((path, scalar_values))

        for key, item in value.items():
            if isinstance(item, dict):
                records.extend(
                    flatten_json_samples(
                        item,
                        path=f"{path}.{key}",
                        depth=depth + 1,
                        max_depth=max_depth,
                        max_list_items=max_list_items,
                    )
                )
            elif isinstance(item, list):
                records.extend(
                    flatten_json_samples(
                        item,
                        path=f"{path}.{key}",
                        depth=depth + 1,
                        max_depth=max_depth,
                        max_list_items=max_list_items,
                    )
                )

    elif isinstance(value, list):
        for index, item in enumerate(value[:max_list_items]):
            records.extend(
                flatten_json_samples(
                    item,
                    path=f"{path}[]",
                    depth=depth + 1,
                    max_depth=max_depth,
                    max_list_items=max_list_items,
                )
            )

    return records


def profile_json_feed(path: Path) -> list[FeedSchemaRecord]:
    try:
        data = json.loads(read_text(path))
    except Exception:
        return []

    samples = flatten_json_samples(data)

    grouped: dict[tuple[str, str], list[Any]] = defaultdict(list)

    for record_path, record in samples:
        for key, value in record.items():
            grouped[(record_path, key)].append(value)

    rows: list[FeedSchemaRecord] = []

    for (record_path, field_name), values in sorted(grouped.items()):
        populated_count = sum(1 for value in values if is_populated(value))
        sampled_count = len(values)
        rate = (
            populated_count / sampled_count
            if sampled_count
            else 0.0
        )

        type_counts = Counter(value_type(value) for value in values)
        dominant_type = (
            type_counts.most_common(1)[0][0]
            if type_counts
            else "unknown"
        )

        rows.append(
            FeedSchemaRecord(
                feed_path=safe_relative(path),
                feed_type="JSON",
                sample_record_path=record_path,
                field_name=field_name,
                value_type=dominant_type,
                populated_count=populated_count,
                sampled_count=sampled_count,
                population_rate=round(rate, 6),
            )
        )

    return rows


def profile_csv_feed(path: Path) -> list[FeedSchemaRecord]:
    rows: list[FeedSchemaRecord] = []

    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            with path.open(
                "r",
                encoding=encoding,
                newline="",
                errors="strict",
            ) as handle:
                reader = csv.DictReader(handle)

                if not reader.fieldnames:
                    return []

                values_by_field: dict[str, list[str]] = {
                    field: [] for field in reader.fieldnames
                }

                for index, record in enumerate(reader):
                    if index >= 250:
                        break

                    for field in reader.fieldnames:
                        values_by_field[field].append(record.get(field, ""))

            for field, values in values_by_field.items():
                populated_count = sum(
                    1 for value in values if value is not None and str(value).strip()
                )
                sampled_count = len(values)
                rate = (
                    populated_count / sampled_count
                    if sampled_count
                    else 0.0
                )

                rows.append(
                    FeedSchemaRecord(
                        feed_path=safe_relative(path),
                        feed_type="CSV",
                        sample_record_path="$[]",
                        field_name=field,
                        value_type="string",
                        populated_count=populated_count,
                        sampled_count=sampled_count,
                        population_rate=round(rate, 6),
                    )
                )

            return rows

        except UnicodeDecodeError:
            continue
        except Exception:
            return []

    return []


def profile_referenced_feeds(
    feed_references: list[FeedReferenceRecord],
) -> list[FeedSchemaRecord]:
    rows: list[FeedSchemaRecord] = []
    seen: set[str] = set()

    resolved_paths = sorted(
        {
            row.resolved_path
            for row in feed_references
            if row.exists and row.resolved_path
        }
    )

    for index, relative in enumerate(resolved_paths, start=1):
        if relative in seen:
            continue
        seen.add(relative)

        path = REPOSITORY_ROOT / relative

        if not path.exists() or not path.is_file():
            continue

        print(
            f"[feed schema] {index}/{len(resolved_paths)} {relative}",
            flush=True,
        )

        if path.suffix.lower() == ".json":
            rows.extend(profile_json_feed(path))
        elif path.suffix.lower() == ".csv":
            rows.extend(profile_csv_feed(path))

    return rows


def normalise_field_name(value: str) -> str:
    lowered = value.lower().strip()

    replacements = {
        "%": " percent ",
        "&": " and ",
        "/": " ",
        "-": " ",
        ".": " ",
        "(": " ",
        ")": " ",
    }

    for before, after in replacements.items():
        lowered = lowered.replace(before, after)

    aliases = {
        "no": "number",
        "num": "number",
        "bar": "barrier",
        "wgt": "weight",
        "wt": "weight",
        "dist": "distance",
        "pos": "position",
        "last 5": "last_five",
        "last5": "last_five",
        "epi spd": "epi_speed",
        "edgeiq price": "edgeiq_price",
        "fair": "edgeiq_price",
        "market price": "market",
        "track rating": "track_rating",
        "early speed": "early_speed",
        "late speed": "late_speed",
        "form momentum": "form_momentum",
    }

    compact = re.sub(r"\s+", " ", lowered).strip()

    if compact in aliases:
        compact = aliases[compact]

    return re.sub(r"[^a-z0-9]+", "_", compact).strip("_")


def field_similarity(label: str, field: str) -> int:
    left = normalise_field_name(label)
    right = normalise_field_name(field)

    if not left or not right:
        return 0

    if left == right:
        return 100

    if left in right or right in left:
        return 80

    left_tokens = set(left.split("_"))
    right_tokens = set(right.split("_"))

    if not left_tokens or not right_tokens:
        return 0

    overlap = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)

    return round((overlap / union) * 70)


def build_wiring_candidates(
    visible_fields: list[VisibleFieldRecord],
    bindings: list[BindingRecord],
    feed_references: list[FeedReferenceRecord],
    feed_schema: list[FeedSchemaRecord],
) -> list[WiringCandidateRecord]:
    rows: list[WiringCandidateRecord] = []

    bindings_by_component: dict[str, list[BindingRecord]] = defaultdict(list)
    feeds_by_source: dict[str, list[FeedReferenceRecord]] = defaultdict(list)
    schema_by_feed: dict[str, list[FeedSchemaRecord]] = defaultdict(list)

    for row in bindings:
        bindings_by_component[row.component_file].append(row)

    for row in feed_references:
        feeds_by_source[row.source_file].append(row)

    for row in feed_schema:
        schema_by_feed[row.feed_path].append(row)

    service_feeds_by_workspace: dict[str, list[FeedReferenceRecord]] = defaultdict(
        list
    )

    for row in feed_references:
        if row.workspace != "UNASSIGNED":
            service_feeds_by_workspace[row.workspace].append(row)

    for visible in visible_fields:
        candidate_bindings = bindings_by_component.get(
            visible.component_file,
            [],
        )

        scored_bindings = sorted(
            (
                (
                    field_similarity(
                        visible.visible_label,
                        binding.bound_field,
                    ),
                    binding,
                )
                for binding in candidate_bindings
            ),
            key=lambda item: (-item[0], item[1].bound_field),
        )

        best_score = scored_bindings[0][0] if scored_bindings else 0
        best_binding = scored_bindings[0][1] if scored_bindings else None

        workspace_feeds = service_feeds_by_workspace.get(
            visible.workspace,
            [],
        )

        feed_matches: list[
            tuple[int, FeedReferenceRecord, FeedSchemaRecord]
        ] = []

        if best_binding:
            for feed in workspace_feeds:
                for schema in schema_by_feed.get(feed.resolved_path, []):
                    score = field_similarity(
                        best_binding.bound_field,
                        schema.field_name,
                    )
                    feed_matches.append((score, feed, schema))

        feed_matches.sort(
            key=lambda item: (
                -item[0],
                item[1].resolved_path,
                item[2].field_name,
            )
        )

        selected_feed = feed_matches[0][1] if feed_matches else None
        selected_schema = feed_matches[0][2] if feed_matches else None
        schema_score = feed_matches[0][0] if feed_matches else 0

        if not best_binding:
            status = "NO_REACT_BINDING_DISCOVERED"
            confidence = "LOW"
            reason = (
                "Visible UI label was discovered but no matching property "
                "binding was found in the same component."
            )
        elif best_score >= 80 and selected_schema and schema_score >= 80:
            if selected_schema.population_rate >= 0.95:
                status = "STATIC_WIRING_PASS_CANDIDATE"
                confidence = "HIGH"
                reason = (
                    "Visible label, React binding and feed schema field "
                    "match strongly and the sampled feed field is populated."
                )
            elif selected_schema.population_rate > 0:
                status = "PARTIALLY_POPULATED_FEED_FIELD"
                confidence = "HIGH"
                reason = (
                    "Wiring match is strong but the sampled feed field "
                    "contains blanks."
                )
            else:
                status = "FEED_FIELD_EMPTY"
                confidence = "HIGH"
                reason = (
                    "Wiring match is strong but the sampled feed field "
                    "is not populated."
                )
        elif best_score >= 80:
            status = "REACT_BINDING_FOUND_FEED_UNPROVEN"
            confidence = "MEDIUM"
            reason = (
                "Visible label and React binding match, but no matching "
                "field was proven in a resolved workspace feed."
            )
        elif best_score >= 50:
            status = "AMBIGUOUS_REACT_BINDING"
            confidence = "LOW"
            reason = (
                "A possible React binding was found, but the field-name "
                "match requires manual review."
            )
        else:
            status = "NO_CONFIDENT_FIELD_MAPPING"
            confidence = "LOW"
            reason = (
                "No confident mapping was found from the visible label "
                "to a React field."
            )

        rows.append(
            WiringCandidateRecord(
                workspace=visible.workspace,
                visible_label=visible.visible_label,
                candidate_field=(
                    best_binding.bound_field if best_binding else ""
                ),
                candidate_source_file=visible.component_file,
                feed_path=(
                    selected_feed.resolved_path if selected_feed else ""
                ),
                feed_has_field=bool(selected_schema and schema_score >= 80),
                field_population_rate=(
                    selected_schema.population_rate
                    if selected_schema
                    else 0.0
                ),
                mapping_confidence=confidence,
                status=status,
                reason=reason,
            )
        )

    return rows


def write_csv(path: Path, rows: list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    dictionaries = [
        asdict(row) if hasattr(row, "__dataclass_fields__") else row
        for row in rows
    ]

    fieldnames = list(dictionaries[0].keys())

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(dictionaries)


def workspace_summary(
    workspace_records: list[WorkspaceFileRecord],
    visible_fields: list[VisibleFieldRecord],
    bindings: list[BindingRecord],
    feed_references: list[FeedReferenceRecord],
    placeholders: list[PlaceholderRecord],
    wiring: list[WiringCandidateRecord],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for workspace in APPROVED_WORKSPACES:
        files = [
            row for row in workspace_records
            if row.workspace == workspace
        ]
        fields = [
            row for row in visible_fields
            if row.workspace == workspace
        ]
        workspace_bindings = [
            row for row in bindings
            if row.workspace == workspace
        ]
        feeds = [
            row for row in feed_references
            if row.workspace == workspace
        ]
        workspace_placeholders = [
            row for row in placeholders
            if row.workspace == workspace
        ]
        workspace_wiring = [
            row for row in wiring
            if row.workspace == workspace
        ]

        resolved_feeds = sum(1 for row in feeds if row.exists)
        missing_feeds = sum(
            1
            for row in feeds
            if row.resolution_status == "MISSING"
        )
        pass_candidates = sum(
            1
            for row in workspace_wiring
            if row.status == "STATIC_WIRING_PASS_CANDIDATE"
        )
        wiring_failures = sum(
            1
            for row in workspace_wiring
            if row.status
            not in {
                "STATIC_WIRING_PASS_CANDIDATE",
            }
        )

        rows.append(
            {
                "workspace": workspace,
                "source_files": len(files),
                "react_components": sum(
                    1
                    for row in files
                    if row.source_kind == "REACT_COMPONENT"
                ),
                "typescript_services": sum(
                    1
                    for row in files
                    if row.source_kind == "TYPESCRIPT_SERVICE"
                ),
                "visible_fields": len(fields),
                "react_bound_fields": len(workspace_bindings),
                "feed_references": len(feeds),
                "resolved_feeds": resolved_feeds,
                "missing_feeds": missing_feeds,
                "placeholder_findings": len(workspace_placeholders),
                "static_wiring_pass_candidates": pass_candidates,
                "wiring_review_items": wiring_failures,
                "static_discovery_status": (
                    "NO_WORKSPACE_FILES"
                    if not files
                    else "REVIEW_REQUIRED"
                    if missing_feeds
                    or workspace_placeholders
                    or wiring_failures
                    else "STATIC_PASS_CANDIDATE"
                ),
            }
        )

    return rows


def write_markdown_summary(
    summary: dict[str, Any],
    workspace_rows: list[dict[str, Any]],
) -> None:
    lines = [
        f"# {AUDIT_ID}",
        "",
        f"Generated: `{summary['generated_at_utc']}`",
        "",
        f"Overall status: **{summary['overall_status']}**",
        "",
        "## Core counts",
        "",
    ]

    for key, value in summary["counts"].items():
        lines.append(f"- `{key}`: **{value}**")

    lines.extend(
        [
            "",
            "## Workspace discovery",
            "",
            "| Workspace | Components | Services | Visible fields | Feeds | Missing feeds | Wiring pass candidates | Review items | Status |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )

    for row in workspace_rows:
        lines.append(
            "| "
            f"{row['workspace']} | "
            f"{row['react_components']} | "
            f"{row['typescript_services']} | "
            f"{row['visible_fields']} | "
            f"{row['feed_references']} | "
            f"{row['missing_feeds']} | "
            f"{row['static_wiring_pass_candidates']} | "
            f"{row['wiring_review_items']} | "
            f"{row['static_discovery_status']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This is a static source-to-feed discovery audit.",
            "- A static pass candidate is not yet a browser-rendered acceptance pass.",
            "- Browser verification must compare rendered values against canonical feed records.",
            "- No existing source, feed, builder or product file was modified.",
            "- No missing field should be repaired until its failure layer is confirmed.",
            "",
        ]
    )

    (OUTPUT_ROOT / f"{AUDIT_ID}_SUMMARY.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> int:
    print(f"=== {AUDIT_ID} ===", flush=True)
    print(f"REPOSITORY_ROOT={REPOSITORY_ROOT}", flush=True)
    print(f"OUTPUT_ROOT={OUTPUT_ROOT}", flush=True)

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    print("\n[1/9] Discovering active source files...", flush=True)

    (
        source_records,
        workspace_records,
        source_texts,
        workspace_by_file,
    ) = discover_sources()

    print("\n[2/9] Resolving TypeScript and JavaScript imports...", flush=True)
    imports = discover_imports(source_texts)

    print("\n[3/9] Discovering runtime feed references...", flush=True)
    feed_references = discover_feed_references(
        source_texts,
        workspace_by_file,
    )

    print("\n[4/9] Extracting visible UI labels and columns...", flush=True)
    visible_fields = discover_visible_fields(
        source_texts,
        workspace_by_file,
    )

    print("\n[5/9] Extracting React field bindings...", flush=True)
    bindings = discover_bindings(
        source_texts,
        workspace_by_file,
    )

    print("\n[6/9] Profiling referenced feeds...", flush=True)
    feed_schema = profile_referenced_feeds(feed_references)

    print("\n[7/9] Detecting placeholders and fallback values...", flush=True)
    placeholders = discover_placeholders(
        source_texts,
        workspace_by_file,
    )

    print("\n[8/9] Building static wiring candidates...", flush=True)
    wiring = build_wiring_candidates(
        visible_fields,
        bindings,
        feed_references,
        feed_schema,
    )

    print("\n[9/9] Writing governed outputs...", flush=True)

    workspace_rows = workspace_summary(
        workspace_records,
        visible_fields,
        bindings,
        feed_references,
        placeholders,
        wiring,
    )

    missing_feed_references = [
        row
        for row in feed_references
        if row.resolution_status == "MISSING"
    ]

    empty_feed_fields = [
        row
        for row in feed_schema
        if row.sampled_count > 0 and row.population_rate == 0
    ]

    partially_populated_feed_fields = [
        row
        for row in feed_schema
        if row.sampled_count > 0
        and 0 < row.population_rate < 1
    ]

    wiring_review = [
        row
        for row in wiring
        if row.status != "STATIC_WIRING_PASS_CANDIDATE"
    ]

    unassigned_sources = [
        row
        for row in source_records
        if row.workspace == "UNASSIGNED"
    ]

    outputs = {
        f"{AUDIT_ID}_SOURCE_FILES.csv": source_records,
        f"{AUDIT_ID}_WORKSPACE_FILES.csv": workspace_records,
        f"{AUDIT_ID}_IMPORTS.csv": imports,
        f"{AUDIT_ID}_FEED_REFERENCES.csv": feed_references,
        f"{AUDIT_ID}_MISSING_FEED_REFERENCES.csv": missing_feed_references,
        f"{AUDIT_ID}_VISIBLE_UI_FIELDS.csv": visible_fields,
        f"{AUDIT_ID}_REACT_BINDINGS.csv": bindings,
        f"{AUDIT_ID}_FEED_SCHEMA.csv": feed_schema,
        f"{AUDIT_ID}_EMPTY_FEED_FIELDS.csv": empty_feed_fields,
        f"{AUDIT_ID}_PARTIALLY_POPULATED_FEED_FIELDS.csv": (
            partially_populated_feed_fields
        ),
        f"{AUDIT_ID}_PLACEHOLDER_FINDINGS.csv": placeholders,
        f"{AUDIT_ID}_STATIC_WIRING_CANDIDATES.csv": wiring,
        f"{AUDIT_ID}_WIRING_REVIEW_ITEMS.csv": wiring_review,
        f"{AUDIT_ID}_UNASSIGNED_SOURCES.csv": unassigned_sources,
        f"{AUDIT_ID}_WORKSPACE_SUMMARY.csv": workspace_rows,
    }

    for filename, rows in outputs.items():
        write_csv(OUTPUT_ROOT / filename, rows)

    counts = {
        "active_source_files_scanned": len(source_records),
        "workspace_assigned_source_files": (
            len(source_records) - len(unassigned_sources)
        ),
        "unassigned_source_files": len(unassigned_sources),
        "imports_discovered": len(imports),
        "missing_relative_imports": sum(
            1
            for row in imports
            if row.resolution_status == "MISSING"
        ),
        "runtime_feed_references": len(feed_references),
        "resolved_runtime_feed_references": sum(
            1 for row in feed_references if row.exists
        ),
        "missing_runtime_feed_references": len(missing_feed_references),
        "visible_ui_fields": len(visible_fields),
        "react_bound_fields": len(bindings),
        "feed_schema_fields": len(feed_schema),
        "empty_feed_fields": len(empty_feed_fields),
        "partially_populated_feed_fields": len(
            partially_populated_feed_fields
        ),
        "placeholder_findings": len(placeholders),
        "static_wiring_pass_candidates": sum(
            1
            for row in wiring
            if row.status == "STATIC_WIRING_PASS_CANDIDATE"
        ),
        "wiring_review_items": len(wiring_review),
    }

    overall_status = (
        "REVIEW_REQUIRED"
        if (
            counts["missing_runtime_feed_references"] > 0
            or counts["missing_relative_imports"] > 0
            or counts["empty_feed_fields"] > 0
            or counts["placeholder_findings"] > 0
            or counts["wiring_review_items"] > 0
        )
        else "STATIC_PASS_CANDIDATE"
    )

    summary = {
        "audit_id": AUDIT_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository_root": str(REPOSITORY_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "overall_status": overall_status,
        "counts": counts,
        "approved_workspaces": APPROVED_WORKSPACES,
        "principles": [
            "No existing repository file is modified.",
            "No field is declared correct solely because a feed exists.",
            "Visible labels, React bindings and feed schemas are assessed separately.",
            "Browser acceptance remains required after static wiring validation.",
            "No placeholder or missing field is repaired without identifying its failure layer.",
            "Builders calculate and React displays.",
        ],
    }

    (OUTPUT_ROOT / f"{AUDIT_ID}_SUMMARY.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    report = {
        "summary": summary,
        "workspace_summary": workspace_rows,
        "missing_feed_references": [
            asdict(row) for row in missing_feed_references
        ],
        "empty_feed_fields": [
            asdict(row) for row in empty_feed_fields
        ],
        "partially_populated_feed_fields": [
            asdict(row)
            for row in partially_populated_feed_fields
        ],
        "placeholder_findings": [
            asdict(row) for row in placeholders
        ],
        "wiring_review_items": [
            asdict(row) for row in wiring_review
        ],
    }

    (OUTPUT_ROOT / f"{AUDIT_ID}_REPORT.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    write_markdown_summary(summary, workspace_rows)

    print("\n=== DATA WIRING AUDIT V1 COMPLETE ===", flush=True)
    print(json.dumps(summary, indent=2), flush=True)
    print(f"\nOUTPUT_ROOT={OUTPUT_ROOT}", flush=True)
    print(f"OVERALL_STATUS={overall_status}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())