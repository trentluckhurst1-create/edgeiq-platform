from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


REGISTRY_VERSION = "1.1.0"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

ACTIVE_SOURCE_ROOTS = (
    REPOSITORY_ROOT / "scripts",
    REPOSITORY_ROOT / "src",
)

OUTPUT_ROOT = (
    REPOSITORY_ROOT
    / "docs"
    / "platform-registry-v1"
    / "builder-registry-v1-1"
)

CSV_OUTPUT = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_REGISTRY_V1_1.csv"
JSON_OUTPUT = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_REGISTRY_V1_1.json"
MARKDOWN_OUTPUT = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_REGISTRY_V1_1.md"
SUMMARY_OUTPUT = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_REGISTRY_V1_1_SUMMARY.json"
DEPENDENCIES_OUTPUT = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_DEPENDENCIES_V1_1.csv"
OUTPUT_CLAIMS_OUTPUT = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_OUTPUT_CLAIMS_V1_1.csv"
DUPLICATES_OUTPUT = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_DUPLICATE_OUTPUT_CLAIMS_V1_1.csv"
PARSE_FAILURES_OUTPUT = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_PARSE_FAILURES_V1_1.csv"

EXCLUDED_DIRECTORY_NAMES = {
    ".git", ".idea", ".pytest_cache", ".ruff_cache", ".venv",
    "venv", "env", "node_modules", "dist", "build", "__pycache__",
    "checkpoints", "checkpoint", "archive", "archives", "archived",
    "backup", "backups", "legacy",
}

NONCANONICAL_FILENAME_TOKENS = (
    "checkpoint", "_backup", "_bak", "_old", "_legacy",
    "_deprecated", "_archive", "_archived", "_copy", "_tmp",
    "_temp", "_working_", "_before_", "_pre_",
)

BUILDER_PREFIXES = (
    "build_", "run_", "generate_", "publish_", "refresh_",
    "materialize_", "compile_", "assemble_", "orchestrate_",
)

OUTPUT_SUFFIXES = {
    ".csv", ".json", ".jsonl", ".parquet", ".feather",
    ".sqlite", ".sqlite3", ".db", ".txt", ".md", ".html",
    ".xml", ".yaml", ".yml",
}

DOMAIN_RULES = (
    ("standard_time", "STANDARD_TIME"),
    ("lengths_v_standard", "LENGTHS_V_STANDARD"),
    ("performance", "PERFORMANCE"),
    ("identity", "IDENTITY"),
    ("weather", "WEATHER"),
    ("market", "MARKET"),
    ("meeting", "MEETINGS"),
    ("three_day", "MEETINGS"),
    ("scratch", "MEETINGS"),
    ("result", "RESULTS"),
    ("race_shape", "RACE_SHAPE"),
    ("suitability", "SUITABILITY"),
    ("form_momentum", "FORM_MOMENTUM"),
    ("early_speed", "EARLY_SPEED"),
    ("late_speed", "LATE_SPEED"),
    ("epi", "EPI"),
    ("eri", "ERI"),
    ("form", "FORM"),
    ("field", "FIELD"),
    ("overview", "OVERVIEW"),
    ("insight", "INSIGHTS"),
    ("nexus", "NEXUS"),
    ("track", "TRACK"),
)


@dataclass(frozen=True)
class BuilderRecord:
    builder_id: str
    builder_name: str
    relative_path: str
    source_root: str
    classification: str
    domain: str
    category: str
    lifecycle_status: str
    certification_status: str
    python_import_count: int
    local_dependency_count: int
    input_claim_count: int
    output_claim_count: int
    public_feed_output_count: int
    source_sha256: str
    source_size_bytes: int
    source_modified_utc: str
    parse_status: str
    parse_error_type: str
    parse_error_line: int
    parse_error_message: str


@dataclass(frozen=True)
class DependencyRecord:
    builder_id: str
    builder_path: str
    dependency_type: str
    dependency_value: str
    evidence: str


@dataclass(frozen=True)
class OutputClaim:
    builder_id: str
    builder_path: str
    output_path: str
    output_filename: str
    suffix: str
    is_public_data_feed: bool
    evidence: str


@dataclass(frozen=True)
class ParseFailure:
    builder_id: str
    relative_path: str
    error_type: str
    line: int
    offset: int
    message: str


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def relative_path(path: Path) -> str:
    return path.relative_to(REPOSITORY_ROOT).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def is_excluded(path: Path) -> bool:
    relative = path.relative_to(REPOSITORY_ROOT)

    return any(
        part.lower() in EXCLUDED_DIRECTORY_NAMES
        for part in relative.parts[:-1]
    )


def iter_live_python_files() -> Iterable[Path]:
    seen: set[Path] = set()

    for root in ACTIVE_SOURCE_ROOTS:
        if not root.exists():
            continue

        for path in root.rglob("*.py"):
            resolved = path.resolve()

            if resolved in seen or is_excluded(path):
                continue

            seen.add(resolved)
            yield path


def is_builder_candidate(path: Path) -> bool:
    name = path.name.lower()
    return name.startswith(BUILDER_PREFIXES) or "builder" in name


def classify_builder(path: Path) -> str:
    name = path.name.lower()

    if any(token in name for token in NONCANONICAL_FILENAME_TOKENS):
        return "HISTORICAL"

    return "CANONICAL"


def infer_domain(path: Path) -> str:
    lowered = relative_path(path).lower()

    for token, domain in DOMAIN_RULES:
        if token in lowered:
            return domain

    return "PLATFORM"


def infer_category(path: Path, source: str) -> str:
    name = path.name.lower()
    lowered_source = source.lower()

    if name.startswith("run_") or "orchestrat" in name:
        return "ORCHESTRATOR"

    if "terminal_feed" in name or "public/data" in lowered_source:
        return "PRODUCT_FEED"

    if "warehouse" in name:
        return "WAREHOUSE"

    if "registry" in name:
        return "REGISTRY"

    if "audit" in name or "check" in name:
        return "AUDIT"

    return "BUILDER"


def flatten_attribute(node: ast.AST) -> str:
    parts: list[str] = []
    current = node

    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value

    if isinstance(current, ast.Name):
        parts.append(current.id)

    return ".".join(reversed(parts))


def constant_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value

    if isinstance(node, ast.JoinedStr):
        chunks: list[str] = []

        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                chunks.append(value.value)
            else:
                chunks.append("{expression}")

        return "".join(chunks)

    return None


def expression_to_path_text(node: ast.AST) -> str | None:
    literal = constant_string(node)

    if literal is not None:
        return literal

    if isinstance(node, ast.Name):
        return f"${node.id}"

    if isinstance(node, ast.Attribute):
        value = flatten_attribute(node)
        return f"${value}" if value else None

    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left = expression_to_path_text(node.left)
        right = expression_to_path_text(node.right)

        if left and right:
            return f"{left}/{right}"

    if isinstance(node, ast.Call):
        name = flatten_attribute(node.func)

        if name.endswith("Path") and node.args:
            return expression_to_path_text(node.args[0])

        if name.endswith("join") or name.endswith("joinpath"):
            values = [
                expression_to_path_text(argument)
                for argument in node.args
            ]

            values = [value for value in values if value]

            if values:
                return "/".join(values)

    return None


def clean_path(value: str) -> str:
    cleaned = value.strip().strip("\"'").replace("\\", "/")
    return re.sub(r"/+", "/", cleaned)


def looks_like_data_path(value: str) -> bool:
    return Path(clean_path(value)).suffix.lower() in OUTPUT_SUFFIXES


def extract_assignments(tree: ast.AST) -> dict[str, str]:
    assignments: dict[str, str] = {}

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue

        if node.value is None:
            continue

        value = expression_to_path_text(node.value)

        if not value:
            continue

        targets = node.targets if isinstance(node, ast.Assign) else [node.target]

        for target in targets:
            if isinstance(target, ast.Name):
                assignments[target.id] = clean_path(value)

    return assignments


def resolve_expression(
    node: ast.AST,
    assignments: dict[str, str],
) -> str | None:
    if isinstance(node, ast.Name) and node.id in assignments:
        return assignments[node.id]

    value = expression_to_path_text(node)

    if not value:
        return None

    for name, assignment in assignments.items():
        value = value.replace(f"${name}", assignment)

    return clean_path(value)


def extract_dependencies_and_outputs(
    tree: ast.AST,
    assignments: dict[str, str],
    builder_id: str,
    builder_path: str,
) -> tuple[list[DependencyRecord], list[OutputClaim], int]:
    dependencies: list[DependencyRecord] = []
    outputs: list[OutputClaim] = []
    import_count = 0

    seen_dependencies: set[tuple[str, str]] = set()
    seen_outputs: set[str] = set()

    def add_dependency(kind: str, value: str, evidence: str) -> None:
        cleaned = clean_path(value)
        key = (kind, cleaned)

        if key in seen_dependencies:
            return

        seen_dependencies.add(key)

        dependencies.append(
            DependencyRecord(
                builder_id=builder_id,
                builder_path=builder_path,
                dependency_type=kind,
                dependency_value=cleaned,
                evidence=evidence,
            )
        )

    def add_output(value: str, evidence: str) -> None:
        cleaned = clean_path(value)

        if cleaned in seen_outputs:
            return

        seen_outputs.add(cleaned)

        outputs.append(
            OutputClaim(
                builder_id=builder_id,
                builder_path=builder_path,
                output_path=cleaned,
                output_filename=Path(cleaned).name,
                suffix=Path(cleaned).suffix.lower(),
                is_public_data_feed="public/data/" in cleaned.lower(),
                evidence=evidence,
            )
        )

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                import_count += 1
                add_dependency(
                    "PYTHON_IMPORT",
                    alias.name,
                    f"line:{getattr(node, 'lineno', 0)}",
                )

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""

            for alias in node.names:
                import_count += 1
                value = f"{module}.{alias.name}" if module else alias.name

                add_dependency(
                    "PYTHON_IMPORT",
                    value,
                    f"line:{getattr(node, 'lineno', 0)}",
                )

    for name, value in assignments.items():
        if not looks_like_data_path(value):
            continue

        upper_name = name.upper()

        if any(
            token in upper_name
            for token in (
                "OUTPUT", "DESTINATION", "TARGET",
                "PUBLISH", "FEED", "REPORT",
            )
        ):
            add_output(value, f"assignment:{name}")

        elif any(
            token in upper_name
            for token in (
                "INPUT", "SOURCE", "WAREHOUSE",
                "FACT", "HISTORY", "MASTER",
            )
        ):
            add_dependency("INPUT_FILE", value, f"assignment:{name}")

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        call_name = flatten_attribute(node.func)
        method = call_name.rsplit(".", 1)[-1]
        line = getattr(node, "lineno", 0)
        evidence = f"{call_name}@line:{line}"

        candidate: ast.AST | None = None

        if isinstance(node.func, ast.Attribute):
            candidate = node.func.value
        elif node.args:
            candidate = node.args[0]

        if candidate is None:
            continue

        resolved = resolve_expression(candidate, assignments)

        if not resolved or not looks_like_data_path(resolved):
            continue

        if method in {
            "write_text", "write_bytes", "to_csv", "to_json",
            "to_parquet", "to_feather", "save",
        }:
            add_output(resolved, evidence)

        elif method in {
            "read_text", "read_bytes", "read_csv", "read_json",
            "read_parquet", "read_feather",
        }:
            add_dependency("INPUT_FILE", resolved, evidence)

        elif method == "open":
            mode = ""

            if len(node.args) >= 2:
                mode = constant_string(node.args[1]) or ""

            for keyword in node.keywords:
                if keyword.arg == "mode":
                    mode = constant_string(keyword.value) or mode

            if any(flag in mode for flag in ("w", "a", "x", "+")):
                add_output(resolved, evidence)
            else:
                add_dependency("INPUT_FILE", resolved, evidence)

    return dependencies, outputs, import_count


def build_module_map(paths: list[Path]) -> dict[str, str]:
    module_map: dict[str, str] = {}

    for path in paths:
        rel = relative_path(path)
        stem = path.stem
        module = rel[:-3].replace("/", ".")

        module_map.setdefault(stem, rel)
        module_map.setdefault(module, rel)

        if module.startswith("scripts."):
            module_map.setdefault(module.removeprefix("scripts."), rel)

    return module_map


def add_local_dependencies(
    dependencies: list[DependencyRecord],
    module_map: dict[str, str],
) -> list[DependencyRecord]:
    local: list[DependencyRecord] = []
    seen: set[tuple[str, str]] = set()

    for dependency in dependencies:
        if dependency.dependency_type != "PYTHON_IMPORT":
            continue

        value = dependency.dependency_value

        for candidate in (
            value,
            value.split(".")[0],
            value.split(".")[-1],
        ):
            matched = module_map.get(candidate)

            if not matched:
                continue

            key = (dependency.builder_id, matched)

            if key not in seen:
                seen.add(key)

                local.append(
                    DependencyRecord(
                        builder_id=dependency.builder_id,
                        builder_path=dependency.builder_path,
                        dependency_type="LOCAL_PYTHON_DEPENDENCY",
                        dependency_value=matched,
                        evidence=dependency.evidence,
                    )
                )

            break

    return local


def write_csv(
    path: Path,
    rows: list[dict[str, object]],
    fields: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def build_markdown(
    summary: dict[str, object],
    builders: list[BuilderRecord],
    duplicates: list[dict[str, object]],
    canonical_failures: list[ParseFailure],
) -> str:
    lines = [
        "# EDGEIQ Canonical Builder Registry V1.1",
        "",
        f"- Generated UTC: `{summary['generated_at_utc']}`",
        f"- Verdict: **{summary['verdict']}**",
        f"- Live Python files: **{summary['live_python_file_count']}**",
        f"- Builder candidates: **{summary['total_builder_count']}**",
        f"- Canonical builders: **{summary['canonical_builder_count']}**",
        f"- Historical builders: **{summary['historical_builder_count']}**",
        f"- Canonical parse failures: **{summary['canonical_parse_failure_count']}**",
        f"- Canonical duplicate outputs: **{summary['canonical_duplicate_output_count']}**",
        "",
        "## Canonical Builders",
        "",
        "| ID | Builder | Domain | Category | Inputs | Outputs | Public feeds | Parse |",
        "|---|---|---|---|---:|---:|---:|---|",
    ]

    for builder in builders:
        if builder.classification != "CANONICAL":
            continue

        values = (
            builder.builder_id,
            builder.relative_path,
            builder.domain,
            builder.category,
            builder.input_claim_count,
            builder.output_claim_count,
            builder.public_feed_output_count,
            builder.parse_status,
        )

        lines.append(
            "| "
            + " | ".join(
                str(value).replace("|", "\\|")
                for value in values
            )
            + " |"
        )

    lines.extend(["", "## Canonical Duplicate Output Claims", ""])

    if duplicates:
        lines.extend(
            [
                "| Output | Builder count | Builders |",
                "|---|---:|---|",
            ]
        )

        for duplicate in duplicates:
            lines.append(
                f"| {duplicate['output_path']} | "
                f"{duplicate['builder_count']} | "
                f"{duplicate['builder_paths']} |"
            )
    else:
        lines.append("No canonical duplicate output claims detected.")

    lines.extend(["", "## Canonical Parse Failures", ""])

    if canonical_failures:
        lines.extend(
            [
                "| Builder | Error | Line | Message |",
                "|---|---|---:|---|",
            ]
        )

        for failure in canonical_failures:
            lines.append(
                f"| {failure.relative_path} | "
                f"{failure.error_type} | "
                f"{failure.line} | "
                f"{failure.message} |"
            )
    else:
        lines.append("No canonical parse failures detected.")

    return "\n".join(lines) + "\n"


def main() -> int:
    generated_at = utc_now()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    live_python_files = sorted(
        iter_live_python_files(),
        key=lambda path: relative_path(path).lower(),
    )

    builder_files = [
        path
        for path in live_python_files
        if is_builder_candidate(path)
    ]

    module_map = build_module_map(live_python_files)

    builders: list[BuilderRecord] = []
    dependencies: list[DependencyRecord] = []
    outputs: list[OutputClaim] = []
    parse_failures: list[ParseFailure] = []

    for index, path in enumerate(builder_files, start=1):
        builder_id = f"BLD-{index:05d}"
        rel = relative_path(path)
        classification = classify_builder(path)

        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        parse_status = "PASS"
        error_type = ""
        error_line = 0
        error_message = ""

        builder_dependencies: list[DependencyRecord] = []
        builder_outputs: list[OutputClaim] = []
        import_count = 0

        try:
            tree = ast.parse(source, filename=rel)
            assignments = extract_assignments(tree)

            (
                builder_dependencies,
                builder_outputs,
                import_count,
            ) = extract_dependencies_and_outputs(
                tree,
                assignments,
                builder_id,
                rel,
            )

            builder_dependencies.extend(
                add_local_dependencies(
                    builder_dependencies,
                    module_map,
                )
            )

        except SyntaxError as exc:
            parse_status = "FAIL"
            error_type = type(exc).__name__
            error_line = int(exc.lineno or 0)
            error_message = exc.msg

            parse_failures.append(
                ParseFailure(
                    builder_id=builder_id,
                    relative_path=rel,
                    error_type=error_type,
                    line=error_line,
                    offset=int(exc.offset or 0),
                    message=error_message,
                )
            )

        dependencies.extend(builder_dependencies)
        outputs.extend(builder_outputs)

        stat = path.stat()

        builders.append(
            BuilderRecord(
                builder_id=builder_id,
                builder_name=path.name,
                relative_path=rel,
                source_root=rel.split("/", 1)[0],
                classification=classification,
                domain=infer_domain(path),
                category=infer_category(path, source),
                lifecycle_status=(
                    "DISCOVERED"
                    if classification == "CANONICAL"
                    else classification
                ),
                certification_status="NOT_CERTIFIED",
                python_import_count=import_count,
                local_dependency_count=sum(
                    item.dependency_type
                    == "LOCAL_PYTHON_DEPENDENCY"
                    for item in builder_dependencies
                ),
                input_claim_count=sum(
                    item.dependency_type == "INPUT_FILE"
                    for item in builder_dependencies
                ),
                output_claim_count=len(builder_outputs),
                public_feed_output_count=sum(
                    item.is_public_data_feed
                    for item in builder_outputs
                ),
                source_sha256=sha256_file(path),
                source_size_bytes=stat.st_size,
                source_modified_utc=datetime.fromtimestamp(
                    stat.st_mtime,
                    timezone.utc,
                ).replace(microsecond=0).isoformat(),
                parse_status=parse_status,
                parse_error_type=error_type,
                parse_error_line=error_line,
                parse_error_message=error_message,
            )
        )

    classification_by_id = {
        builder.builder_id: builder.classification
        for builder in builders
    }

    canonical_outputs = [
        output
        for output in outputs
        if classification_by_id.get(output.builder_id) == "CANONICAL"
    ]

    grouped_outputs: dict[str, list[OutputClaim]] = {}

    for output in canonical_outputs:
        grouped_outputs.setdefault(
            output.output_path.lower(),
            [],
        ).append(output)

    duplicates: list[dict[str, object]] = []

    for claims in grouped_outputs.values():
        builder_paths = sorted(
            {claim.builder_path for claim in claims}
        )

        if len(builder_paths) <= 1:
            continue

        duplicates.append(
            {
                "output_path": claims[0].output_path,
                "builder_count": len(builder_paths),
                "claim_count": len(claims),
                "builder_ids": " | ".join(
                    sorted(
                        {claim.builder_id for claim in claims}
                    )
                ),
                "builder_paths": " | ".join(builder_paths),
                "conflict_type": "CANONICAL_CONFLICT",
            }
        )

    duplicates.sort(
        key=lambda row: (
            -int(row["builder_count"]),
            str(row["output_path"]).lower(),
        )
    )

    canonical_builders = [
        builder
        for builder in builders
        if builder.classification == "CANONICAL"
    ]

    historical_builders = [
        builder
        for builder in builders
        if builder.classification != "CANONICAL"
    ]

    canonical_failures = [
        failure
        for failure in parse_failures
        if classification_by_id.get(failure.builder_id)
        == "CANONICAL"
    ]

    historical_failures = [
        failure
        for failure in parse_failures
        if classification_by_id.get(failure.builder_id)
        != "CANONICAL"
    ]

    if not canonical_builders:
        verdict = "FAIL_NO_CANONICAL_BUILDERS"
    elif canonical_failures:
        verdict = "FAIL_CANONICAL_PARSE_FAILURES"
    elif duplicates:
        verdict = "WARNING_CANONICAL_OUTPUT_CONFLICTS"
    else:
        verdict = "PASS"

    summary = {
        "registry_version": REGISTRY_VERSION,
        "generated_at_utc": generated_at,
        "repository_root": str(REPOSITORY_ROOT),
        "active_source_roots": [
            relative_path(root)
            for root in ACTIVE_SOURCE_ROOTS
            if root.exists()
        ],
        "live_python_file_count": len(live_python_files),
        "total_builder_count": len(builders),
        "canonical_builder_count": len(canonical_builders),
        "historical_builder_count": len(historical_builders),
        "canonical_parse_failure_count": len(canonical_failures),
        "historical_parse_failure_count": len(historical_failures),
        "dependency_record_count": len(dependencies),
        "input_claim_count": sum(
            item.dependency_type == "INPUT_FILE"
            for item in dependencies
        ),
        "output_claim_count": len(outputs),
        "canonical_output_claim_count": len(canonical_outputs),
        "canonical_public_feed_output_count": sum(
            item.is_public_data_feed
            for item in canonical_outputs
        ),
        "canonical_duplicate_output_count": len(duplicates),
        "excluded_directory_names": sorted(
            EXCLUDED_DIRECTORY_NAMES
        ),
        "verdict": verdict,
    }

    builder_rows = [asdict(item) for item in builders]
    dependency_rows = [asdict(item) for item in dependencies]
    output_rows = [asdict(item) for item in outputs]
    parse_failure_rows = [asdict(item) for item in parse_failures]

    write_csv(
        CSV_OUTPUT,
        builder_rows,
        list(BuilderRecord.__dataclass_fields__.keys()),
    )

    write_csv(
        DEPENDENCIES_OUTPUT,
        dependency_rows,
        list(DependencyRecord.__dataclass_fields__.keys()),
    )

    write_csv(
        OUTPUT_CLAIMS_OUTPUT,
        output_rows,
        list(OutputClaim.__dataclass_fields__.keys()),
    )

    write_csv(
        DUPLICATES_OUTPUT,
        duplicates,
        [
            "output_path",
            "builder_count",
            "claim_count",
            "builder_ids",
            "builder_paths",
            "conflict_type",
        ],
    )

    write_csv(
        PARSE_FAILURES_OUTPUT,
        parse_failure_rows,
        list(ParseFailure.__dataclass_fields__.keys()),
    )

    JSON_OUTPUT.write_text(
        json.dumps(
            {
                "summary": summary,
                "builders": builder_rows,
                "dependencies": dependency_rows,
                "output_claims": output_rows,
                "canonical_duplicate_output_claims": duplicates,
                "parse_failures": parse_failure_rows,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    SUMMARY_OUTPUT.write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )

    MARKDOWN_OUTPUT.write_text(
        build_markdown(
            summary,
            builders,
            duplicates,
            canonical_failures,
        ),
        encoding="utf-8",
    )

    print("EDGEIQ CANONICAL BUILDER REGISTRY V1.1")
    print(f"VERDICT={verdict}")
    print(f"LIVE_PYTHON_FILES={len(live_python_files)}")
    print(f"TOTAL_BUILDERS={len(builders)}")
    print(f"CANONICAL_BUILDERS={len(canonical_builders)}")
    print(f"HISTORICAL_BUILDERS={len(historical_builders)}")
    print(f"CANONICAL_PARSE_FAILURES={len(canonical_failures)}")
    print(f"HISTORICAL_PARSE_FAILURES={len(historical_failures)}")
    print(f"CANONICAL_OUTPUT_CLAIMS={len(canonical_outputs)}")
    print(
        "CANONICAL_PUBLIC_FEEDS="
        f"{summary['canonical_public_feed_output_count']}"
    )
    print(f"CANONICAL_DUPLICATE_OUTPUTS={len(duplicates)}")
    print(f"OUTPUT_ROOT={OUTPUT_ROOT}")

    return 0 if canonical_builders else 1


if __name__ == "__main__":
    raise SystemExit(main())
