from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


AUDIT_ID = "EDGEIQ_RUNTIME_FEED_DISCOVERY_V1"

SOURCE_EXTENSIONS = (
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
)

FEED_EXTENSIONS = (
    ".csv",
    ".json",
    ".parquet",
    ".sqlite",
    ".sqlite3",
    ".db",
)

IGNORED_DIRECTORY_NAMES = {
    "node_modules",
    "dist",
    "build",
    ".git",
    ".vite",
    "coverage",
    "__pycache__",
    "archive",
    "archives",
    "checkpoint",
    "checkpoints",
    "backup",
    "backups",
}

IGNORED_FILE_MARKERS = (
    "_legacy",
    ".legacy",
    "_checkpoint",
    ".checkpoint",
    "_backup",
    ".backup",
    "_old",
    ".old",
    "_archived",
    ".archived",
)

ENTRYPOINT_CANDIDATES = (
    "src/main.tsx",
    "src/main.ts",
    "src/main.jsx",
    "src/main.js",
    "src/index.tsx",
    "src/index.ts",
    "src/index.jsx",
    "src/index.js",
)

WORKSPACE_RULES = (
    ("MEETINGS", ("meeting", "meetings", "scratchings", "gear")),
    ("PERFORMANCE", ("performance", "epiworkspace", "epi-workspace", "ratings")),
    ("OVERVIEW", ("overview",)),
    ("INSIGHTS", ("insight",)),
    ("WEATHER", ("weather",)),
    ("RESULTS", ("result",)),
    ("MARKET", ("market", "price", "odds", "fluc")),
    ("NEXUS", ("nexus",)),
    ("FORM", ("formguide", "form-guide", "/form/", "\\form\\", "formworkspace")),
    ("FIELD", ("fieldworkspace", "field-workspace", "/field/", "\\field\\")),
    ("MAP", ("speedmap", "speed-map", "mapworkspace", "map-workspace")),
    ("TRACK", ("trackworkspace", "track-workspace", "trackcondition")),
    ("RACE", ("raceworkspace", "race-workspace", "racefile", "/race/", "\\race\\")),
    ("HOME", ("homeworkspace", "home-workspace", "/home/", "\\home\\")),
    ("LAB", ("labworkspace", "lab-workspace", "/lab/", "\\lab\\")),
)

IMPORT_PATTERNS = (
    re.compile(
        r"""(?:import|export)\s+(?:type\s+)?(?:[\s\S]*?\s+from\s+)?["']([^"']+)["']""",
        re.MULTILINE,
    ),
    re.compile(
        r"""import\s*\(\s*["']([^"']+)["']\s*\)""",
        re.MULTILINE,
    ),
    re.compile(
        r"""require\s*\(\s*["']([^"']+)["']\s*\)""",
        re.MULTILINE,
    ),
)

RUNTIME_REFERENCE_PATTERNS = (
    (
        "FETCH",
        re.compile(
            r"""fetch\s*\(\s*(?:new\s+Request\s*\(\s*)?["'`]([^"'`]+)["'`]""",
            re.IGNORECASE,
        ),
    ),
    (
        "AXIOS",
        re.compile(
            r"""axios(?:\.(?:get|post|put|patch|delete))?\s*\(\s*["'`]([^"'`]+)["'`]""",
            re.IGNORECASE,
        ),
    ),
    (
        "D3_CSV",
        re.compile(
            r"""(?:d3\.)?csv\s*\(\s*["'`]([^"'`]+)["'`]""",
            re.IGNORECASE,
        ),
    ),
    (
        "D3_JSON",
        re.compile(
            r"""(?:d3\.)?json\s*\(\s*["'`]([^"'`]+)["'`]""",
            re.IGNORECASE,
        ),
    ),
    (
        "PAPA_PARSE",
        re.compile(
            r"""Papa\.parse\s*\(\s*["'`]([^"'`]+)["'`]""",
            re.IGNORECASE,
        ),
    ),
    (
        "NEW_URL",
        re.compile(
            r"""new\s+URL\s*\(\s*["'`]([^"'`]+)["'`]""",
            re.IGNORECASE,
        ),
    ),
)


@dataclass(frozen=True)
class ImportEdge:
    source_file: str
    import_value: str
    import_kind: str
    resolution_status: str
    resolved_file: str


@dataclass(frozen=True)
class RuntimeSource:
    source_file: str
    workspace: str
    graph_depth: int
    imported_by_count: int
    imports_count: int
    runtime_feed_reference_count: int


@dataclass(frozen=True)
class RuntimeFeedReference:
    workspace: str
    source_file: str
    reference_type: str
    referenced_value: str
    resolution_status: str
    resolved_feed: str
    feed_extension: str
    exists: bool
    file_size_bytes: int
    graph_depth: int


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalise_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def should_ignore(path: Path, root: Path) -> bool:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return True

    for part in relative.parts[:-1]:
        if part.lower() in IGNORED_DIRECTORY_NAMES:
            return True

    lowered_name = path.name.lower()

    return any(marker in lowered_name for marker in IGNORED_FILE_MARKERS)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig", errors="replace")


def infer_workspace(path: Path) -> str:
    lowered = path.as_posix().lower()

    for workspace, markers in WORKSPACE_RULES:
        if any(marker in lowered for marker in markers):
            return workspace

    if "/services/" in lowered or "/service/" in lowered:
        return "SHARED_SERVICE"

    if "/components/" in lowered:
        return "SHARED_COMPONENT"

    return "APP_SHELL"


def discover_entrypoints(root: Path) -> list[Path]:
    entries: list[Path] = []

    for relative in ENTRYPOINT_CANDIDATES:
        candidate = root / relative

        if candidate.exists() and candidate.is_file():
            entries.append(candidate.resolve())

    if entries:
        return sorted(set(entries))

    src_root = root / "src"

    for extension in SOURCE_EXTENSIONS:
        for candidate in src_root.glob(f"**/main{extension}"):
            if candidate.is_file() and not should_ignore(candidate, root):
                entries.append(candidate.resolve())

    return sorted(set(entries))


def extract_import_values(text: str) -> list[tuple[str, str]]:
    discovered: list[tuple[str, str]] = []

    for pattern_index, pattern in enumerate(IMPORT_PATTERNS):
        import_kind = (
            "STATIC_IMPORT_EXPORT"
            if pattern_index == 0
            else "DYNAMIC_IMPORT"
            if pattern_index == 1
            else "REQUIRE"
        )

        for match in pattern.finditer(text):
            value = match.group(1).strip()

            if value:
                discovered.append((import_kind, value))

    return sorted(set(discovered))


def candidate_source_paths(base: Path) -> Iterable[Path]:
    if base.suffix.lower() in SOURCE_EXTENSIONS:
        yield base

    for extension in SOURCE_EXTENSIONS:
        yield Path(str(base) + extension)

    for extension in SOURCE_EXTENSIONS:
        yield base / f"index{extension}"


def resolve_source_import(
    importing_file: Path,
    import_value: str,
    root: Path,
) -> tuple[str, Path | None]:
    cleaned = import_value.split("?")[0].split("#")[0].strip()

    if not cleaned:
        return "EMPTY_IMPORT", None

    if cleaned.startswith("@/"):
        base = root / "src" / cleaned[2:]
    elif cleaned.startswith("src/"):
        base = root / cleaned
    elif cleaned.startswith("."):
        base = importing_file.parent / cleaned
    else:
        return "PACKAGE_OR_ALIAS", None

    for candidate in candidate_source_paths(base):
        if (
            candidate.exists()
            and candidate.is_file()
            and not should_ignore(candidate, root)
        ):
            return "RESOLVED", candidate.resolve()

    return "MISSING_LOCAL_SOURCE", None


def discover_runtime_graph(
    root: Path,
    entrypoints: list[Path],
) -> tuple[
    dict[Path, int],
    list[ImportEdge],
    dict[Path, set[Path]],
    dict[Path, set[Path]],
]:
    depth_by_file: dict[Path, int] = {}
    outgoing: dict[Path, set[Path]] = defaultdict(set)
    incoming: dict[Path, set[Path]] = defaultdict(set)
    import_edges: list[ImportEdge] = []

    queue: deque[tuple[Path, int]] = deque(
        (entrypoint.resolve(), 0)
        for entrypoint in entrypoints
    )

    processed: set[Path] = set()

    while queue:
        current, depth = queue.popleft()

        existing_depth = depth_by_file.get(current)

        if existing_depth is None or depth < existing_depth:
            depth_by_file[current] = depth

        if current in processed:
            continue

        processed.add(current)

        if len(processed) == 1 or len(processed) % 100 == 0:
            print(
                f"[runtime graph] processed={len(processed)} "
                f"queued={len(queue)} file={normalise_relative(current, root)}",
                flush=True,
            )

        try:
            text = read_text(current)
        except OSError as exc:
            print(
                f"[runtime graph warning] unable to read "
                f"{normalise_relative(current, root)}: {exc}",
                flush=True,
            )
            continue

        for import_kind, import_value in extract_import_values(text):
            status, resolved = resolve_source_import(
                current,
                import_value,
                root,
            )

            import_edges.append(
                ImportEdge(
                    source_file=normalise_relative(current, root),
                    import_value=import_value,
                    import_kind=import_kind,
                    resolution_status=status,
                    resolved_file=(
                        normalise_relative(resolved, root)
                        if resolved is not None
                        else ""
                    ),
                )
            )

            if resolved is None:
                continue

            outgoing[current].add(resolved)
            incoming[resolved].add(current)

            next_depth = depth + 1

            previous_depth = depth_by_file.get(resolved)

            if previous_depth is None or next_depth < previous_depth:
                depth_by_file[resolved] = next_depth

            if resolved not in processed:
                queue.append((resolved, next_depth))

    return depth_by_file, import_edges, outgoing, incoming


def extract_runtime_references(text: str) -> list[tuple[str, str]]:
    references: list[tuple[str, str]] = []

    for reference_type, pattern in RUNTIME_REFERENCE_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1).strip()

            if value:
                references.append((reference_type, value))

    for pattern in IMPORT_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1).strip()
            suffix = Path(value.split("?")[0].split("#")[0]).suffix.lower()

            if suffix in FEED_EXTENSIONS:
                references.append(("DIRECT_ASSET_IMPORT", value))

    quoted_asset_pattern = re.compile(
        r"""["'`]([^"'`]*(?:\.csv|\.json|\.parquet|\.sqlite3?|\.db)(?:\?[^"'`]*)?)["'`]""",
        re.IGNORECASE,
    )

    for match in quoted_asset_pattern.finditer(text):
        value = match.group(1).strip()

        if value:
            references.append(("QUOTED_FEED_ASSET", value))

    return sorted(set(references))


def resolve_runtime_feed(
    source_file: Path,
    reference_value: str,
    root: Path,
) -> tuple[str, Path | None]:
    value = reference_value.strip()

    if not value:
        return "EMPTY_REFERENCE", None

    if "${" in value or "{" in value or "}" in value:
        return "DYNAMIC_REFERENCE", None

    if re.match(r"^https?://", value, flags=re.IGNORECASE):
        return "REMOTE_URL", None

    cleaned = value.split("?")[0].split("#")[0].strip()

    if not cleaned:
        return "EMPTY_REFERENCE", None

    candidates: list[Path] = []

    if cleaned.startswith("/"):
        candidates.extend(
            (
                root / "public" / cleaned.lstrip("/"),
                root / cleaned.lstrip("/"),
            )
        )
    elif cleaned.startswith("@/"):
        candidates.append(root / "src" / cleaned[2:])
    elif cleaned.startswith("src/"):
        candidates.append(root / cleaned)
    elif cleaned.startswith("public/"):
        candidates.append(root / cleaned)
    elif cleaned.startswith("."):
        candidates.append(source_file.parent / cleaned)
    else:
        candidates.extend(
            (
                source_file.parent / cleaned,
                root / "public" / cleaned,
                root / cleaned,
            )
        )

    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue

        if resolved.exists() and resolved.is_file():
            return "RESOLVED", resolved

    suffix = Path(cleaned).suffix.lower()

    if suffix in FEED_EXTENSIONS:
        return "MISSING_RUNTIME_FEED", None

    return "NON_FEED_REFERENCE", None


def build_runtime_feed_references(
    root: Path,
    depth_by_file: dict[Path, int],
) -> list[RuntimeFeedReference]:
    results: list[RuntimeFeedReference] = []

    runtime_files = sorted(
        depth_by_file,
        key=lambda path: normalise_relative(path, root),
    )

    for index, source_file in enumerate(runtime_files, start=1):
        if index == 1 or index % 100 == 0 or index == len(runtime_files):
            print(
                f"[feed discovery] {index}/{len(runtime_files)} "
                f"{normalise_relative(source_file, root)}",
                flush=True,
            )

        try:
            text = read_text(source_file)
        except OSError:
            continue

        workspace = infer_workspace(source_file)
        graph_depth = depth_by_file[source_file]

        for reference_type, reference_value in extract_runtime_references(text):
            status, resolved = resolve_runtime_feed(
                source_file,
                reference_value,
                root,
            )

            if status == "NON_FEED_REFERENCE":
                continue

            suffix = (
                resolved.suffix.lower()
                if resolved is not None
                else Path(
                    reference_value.split("?")[0].split("#")[0]
                ).suffix.lower()
            )

            if (
                suffix not in FEED_EXTENSIONS
                and status not in {"DYNAMIC_REFERENCE", "REMOTE_URL"}
            ):
                continue

            exists = bool(resolved is not None and resolved.exists())

            file_size = (
                resolved.stat().st_size
                if exists and resolved is not None
                else 0
            )

            results.append(
                RuntimeFeedReference(
                    workspace=workspace,
                    source_file=normalise_relative(source_file, root),
                    reference_type=reference_type,
                    referenced_value=reference_value,
                    resolution_status=status,
                    resolved_feed=(
                        normalise_relative(resolved, root)
                        if resolved is not None
                        else ""
                    ),
                    feed_extension=suffix,
                    exists=exists,
                    file_size_bytes=file_size,
                    graph_depth=graph_depth,
                )
            )

    unique = {
        (
            row.workspace,
            row.source_file,
            row.reference_type,
            row.referenced_value,
            row.resolution_status,
            row.resolved_feed,
        ): row
        for row in results
    }

    return sorted(
        unique.values(),
        key=lambda row: (
            row.workspace,
            row.source_file,
            row.resolved_feed,
            row.referenced_value,
            row.reference_type,
        ),
    )


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()

        for row in rows:
            writer.writerow(row)


def main() -> int:
    root = Path.cwd().resolve()

    if not (root / "src").exists():
        print(
            "ERROR: Run this audit from the EDGEIQ repository root.",
            file=sys.stderr,
        )
        return 2

    output_root = (
        root
        / "docs"
        / "runtime-data-wiring-audit-v1"
        / "phase-a-runtime-feed-discovery"
    )
    output_root.mkdir(parents=True, exist_ok=True)

    print(f"=== {AUDIT_ID} ===", flush=True)
    print(f"REPOSITORY_ROOT={root}", flush=True)
    print(f"OUTPUT_ROOT={output_root}", flush=True)

    print("\n[1/5] Discovering React application entrypoints...", flush=True)

    entrypoints = discover_entrypoints(root)

    if not entrypoints:
        print(
            "ERROR: No React/TypeScript application entrypoint found.",
            file=sys.stderr,
        )
        return 3

    for entrypoint in entrypoints:
        print(
            f"[entrypoint] {normalise_relative(entrypoint, root)}",
            flush=True,
        )

    print("\n[2/5] Traversing reachable runtime imports...", flush=True)

    (
        depth_by_file,
        import_edges,
        outgoing,
        incoming,
    ) = discover_runtime_graph(root, entrypoints)

    print(
        f"[runtime graph complete] reachable_source_files={len(depth_by_file)} "
        f"import_edges={len(import_edges)}",
        flush=True,
    )

    print("\n[3/5] Discovering runtime feed references...", flush=True)

    feed_references = build_runtime_feed_references(
        root,
        depth_by_file,
    )

    print(
        f"[feed discovery complete] references={len(feed_references)}",
        flush=True,
    )

    feed_count_by_source: dict[str, int] = defaultdict(int)

    for reference in feed_references:
        feed_count_by_source[reference.source_file] += 1

    runtime_sources: list[RuntimeSource] = []

    for source_file, depth in sorted(
        depth_by_file.items(),
        key=lambda item: normalise_relative(item[0], root),
    ):
        relative = normalise_relative(source_file, root)

        runtime_sources.append(
            RuntimeSource(
                source_file=relative,
                workspace=infer_workspace(source_file),
                graph_depth=depth,
                imported_by_count=len(incoming.get(source_file, set())),
                imports_count=len(outgoing.get(source_file, set())),
                runtime_feed_reference_count=feed_count_by_source.get(
                    relative,
                    0,
                ),
            )
        )

    print("\n[4/5] Building governed runtime summaries...", flush=True)

    unique_resolved_feeds = sorted(
        {
            reference.resolved_feed
            for reference in feed_references
            if reference.resolution_status == "RESOLVED"
            and reference.resolved_feed
        }
    )

    missing_references = [
        reference
        for reference in feed_references
        if reference.resolution_status == "MISSING_RUNTIME_FEED"
    ]

    dynamic_references = [
        reference
        for reference in feed_references
        if reference.resolution_status == "DYNAMIC_REFERENCE"
    ]

    remote_references = [
        reference
        for reference in feed_references
        if reference.resolution_status == "REMOTE_URL"
    ]

    workspace_summary: list[dict] = []

    workspaces = sorted(
        {
            source.workspace
            for source in runtime_sources
        }
        | {
            reference.workspace
            for reference in feed_references
        }
    )

    for workspace in workspaces:
        workspace_sources = [
            source
            for source in runtime_sources
            if source.workspace == workspace
        ]
        workspace_refs = [
            reference
            for reference in feed_references
            if reference.workspace == workspace
        ]

        workspace_summary.append(
            {
                "workspace": workspace,
                "reachable_source_files": len(workspace_sources),
                "feed_references": len(workspace_refs),
                "resolved_feed_references": sum(
                    1
                    for row in workspace_refs
                    if row.resolution_status == "RESOLVED"
                ),
                "unique_resolved_feeds": len(
                    {
                        row.resolved_feed
                        for row in workspace_refs
                        if row.resolution_status == "RESOLVED"
                        and row.resolved_feed
                    }
                ),
                "missing_feed_references": sum(
                    1
                    for row in workspace_refs
                    if row.resolution_status == "MISSING_RUNTIME_FEED"
                ),
                "dynamic_feed_references": sum(
                    1
                    for row in workspace_refs
                    if row.resolution_status == "DYNAMIC_REFERENCE"
                ),
                "remote_feed_references": sum(
                    1
                    for row in workspace_refs
                    if row.resolution_status == "REMOTE_URL"
                ),
            }
        )

    summary = {
        "audit_id": AUDIT_ID,
        "generated_at_utc": utc_now_iso(),
        "repository_root": str(root),
        "entrypoints": [
            normalise_relative(path, root)
            for path in entrypoints
        ],
        "reachable_source_files": len(runtime_sources),
        "import_edges": len(import_edges),
        "runtime_feed_references": len(feed_references),
        "unique_resolved_runtime_feeds": len(unique_resolved_feeds),
        "missing_runtime_feed_references": len(missing_references),
        "dynamic_runtime_feed_references": len(dynamic_references),
        "remote_runtime_feed_references": len(remote_references),
        "status": (
            "REVIEW_REQUIRED"
            if missing_references or dynamic_references
            else "PASS_STATIC_DISCOVERY"
        ),
    }

    print("\n[5/5] Writing governed outputs...", flush=True)

    write_csv(
        output_root / f"{AUDIT_ID}_RUNTIME_SOURCES.csv",
        [asdict(row) for row in runtime_sources],
        [
            "source_file",
            "workspace",
            "graph_depth",
            "imported_by_count",
            "imports_count",
            "runtime_feed_reference_count",
        ],
    )

    write_csv(
        output_root / f"{AUDIT_ID}_IMPORT_EDGES.csv",
        [asdict(row) for row in import_edges],
        [
            "source_file",
            "import_value",
            "import_kind",
            "resolution_status",
            "resolved_file",
        ],
    )

    write_csv(
        output_root / f"{AUDIT_ID}_RUNTIME_FEED_REFERENCES.csv",
        [asdict(row) for row in feed_references],
        [
            "workspace",
            "source_file",
            "reference_type",
            "referenced_value",
            "resolution_status",
            "resolved_feed",
            "feed_extension",
            "exists",
            "file_size_bytes",
            "graph_depth",
        ],
    )

    write_csv(
        output_root / f"{AUDIT_ID}_RESOLVED_RUNTIME_FEEDS.csv",
        [
            {
                "resolved_feed": feed,
                "file_size_bytes": (root / feed).stat().st_size,
            }
            for feed in unique_resolved_feeds
        ],
        [
            "resolved_feed",
            "file_size_bytes",
        ],
    )

    write_csv(
        output_root / f"{AUDIT_ID}_MISSING_RUNTIME_FEEDS.csv",
        [asdict(row) for row in missing_references],
        [
            "workspace",
            "source_file",
            "reference_type",
            "referenced_value",
            "resolution_status",
            "resolved_feed",
            "feed_extension",
            "exists",
            "file_size_bytes",
            "graph_depth",
        ],
    )

    write_csv(
        output_root / f"{AUDIT_ID}_DYNAMIC_RUNTIME_FEEDS.csv",
        [asdict(row) for row in dynamic_references],
        [
            "workspace",
            "source_file",
            "reference_type",
            "referenced_value",
            "resolution_status",
            "resolved_feed",
            "feed_extension",
            "exists",
            "file_size_bytes",
            "graph_depth",
        ],
    )

    write_csv(
        output_root / f"{AUDIT_ID}_WORKSPACE_SUMMARY.csv",
        workspace_summary,
        [
            "workspace",
            "reachable_source_files",
            "feed_references",
            "resolved_feed_references",
            "unique_resolved_feeds",
            "missing_feed_references",
            "dynamic_feed_references",
            "remote_feed_references",
        ],
    )

    (
        output_root / f"{AUDIT_ID}_SUMMARY.json"
    ).write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    report_lines = [
        f"# {AUDIT_ID}",
        "",
        f"- Generated: `{summary['generated_at_utc']}`",
        f"- Status: **{summary['status']}**",
        f"- Reachable runtime source files: **{summary['reachable_source_files']}**",
        f"- Import edges: **{summary['import_edges']}**",
        f"- Runtime feed references: **{summary['runtime_feed_references']}**",
        f"- Unique resolved runtime feeds: **{summary['unique_resolved_runtime_feeds']}**",
        f"- Missing runtime feed references: **{summary['missing_runtime_feed_references']}**",
        f"- Dynamic runtime feed references: **{summary['dynamic_runtime_feed_references']}**",
        f"- Remote runtime feed references: **{summary['remote_runtime_feed_references']}**",
        "",
        "## Entrypoints",
        "",
    ]

    report_lines.extend(
        f"- `{entrypoint}`"
        for entrypoint in summary["entrypoints"]
    )

    report_lines.extend(
        (
            "",
            "## Scope",
            "",
            "This phase follows only source files reachable from the live application entrypoint.",
            "It excludes inactive scripts, checkpoints, archives, backups and unrelated repository artefacts.",
            "",
            "It does not yet prove that each displayed column receives the correct field.",
            "That mapping is handled by the later runtime UI mapping phase.",
            "",
        )
    )

    (
        output_root / f"{AUDIT_ID}_REPORT.md"
    ).write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )

    print("\n=== PHASE A COMPLETE ===", flush=True)
    print(json.dumps(summary, indent=2), flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())