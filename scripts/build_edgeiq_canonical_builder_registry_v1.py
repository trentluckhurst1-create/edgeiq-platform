from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


REGISTRY_VERSION = "1.0.0"

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_ROOT = (
    REPOSITORY_ROOT
    / "docs"
    / "platform-registry-v1"
    / "builder-registry"
)

CSV_OUTPUT = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_REGISTRY_V1.csv"
JSON_OUTPUT = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_REGISTRY_V1.json"
MARKDOWN_OUTPUT = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_REGISTRY_V1.md"
SUMMARY_OUTPUT = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_REGISTRY_V1_SUMMARY.json"
DEPENDENCIES_OUTPUT = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_DEPENDENCIES_V1.csv"
OUTPUT_CLAIMS_OUTPUT = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_OUTPUT_CLAIMS_V1.csv"
DUPLICATE_OUTPUTS_OUTPUT = (
    OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_DUPLICATE_OUTPUT_CLAIMS_V1.csv"
)

EXCLUDED_DIRECTORIES = {
    ".git",
    ".idea",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
}

BUILDER_PREFIXES = (
    "build_",
    "run_",
    "generate_",
    "publish_",
    "refresh_",
    "materialize_",
    "compile_",
    "assemble_",
    "orchestrate_",
)

OUTPUT_SUFFIXES = {
    ".csv",
    ".json",
    ".jsonl",
    ".parquet",
    ".feather",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".txt",
    ".md",
    ".html",
    ".xml",
    ".yaml",
    ".yml",
}

WRITE_METHODS = {
    "write_text",
    "write_bytes",
    "to_csv",
    "to_json",
    "to_parquet",
    "to_feather",
    "dump",
    "dumps",
    "writer",
    "writerow",
    "writerows",
    "save",
    "open",
}

READ_METHODS = {
    "read_text",
    "read_bytes",
    "read_csv",
    "read_json",
    "read_parquet",
    "read_feather",
    "load",
    "loads",
    "open",
}

AUDIT_WORDS = (
    "audit",
    "check",
    "validate",
    "validation",
    "regression",
    "acceptance",
    "verify",
)

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
    domain: str
    category: str
    lifecycle_status: str
    certification_status: str
    is_orchestrator: bool
    is_audit_like: bool
    python_import_count: int
    local_dependency_count: int
    input_claim_count: int
    output_claim_count: int
    public_feed_output_count: int
    source_sha256: str
    source_size_bytes: int
    source_modified_utc: str
    parse_status: str
    parse_error: str


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


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalise_relative(path: Path) -> str:
    return path.relative_to(REPOSITORY_ROOT).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def is_excluded(path: Path) -> bool:
    return any(part.lower() in EXCLUDED_DIRECTORIES for part in path.parts)


def iter_python_files() -> Iterable[Path]:
    for path in REPOSITORY_ROOT.rglob("*.py"):
        if is_excluded(path.relative_to(REPOSITORY_ROOT)):
            continue

        yield path


def is_builder_candidate(path: Path) -> bool:
    name = path.name.lower()

    if name.startswith(BUILDER_PREFIXES):
        return True

    if "builder" in name:
        return True

    return False


def infer_domain(relative_path: str) -> str:
    lowered = relative_path.lower()

    for token, domain in DOMAIN_RULES:
        if token in lowered:
            return domain

    return "PLATFORM"


def infer_category(path: Path, source: str) -> str:
    lowered_name = path.name.lower()
    lowered_source = source.lower()

    if lowered_name.startswith("run_") or "orchestrat" in lowered_name:
        return "ORCHESTRATOR"

    if "terminal_feed" in lowered_name or "public/data" in lowered_source:
        return "PRODUCT_FEED"

    if "warehouse" in lowered_name:
        return "WAREHOUSE"

    if "registry" in lowered_name:
        return "REGISTRY"

    if "report" in lowered_name:
        return "REPORT"

    return "BUILDER"


def infer_lifecycle_status(path: Path) -> str:
    lowered = normalise_relative(path).lower()

    if any(
        token in lowered
        for token in (
            "deprecated",
            "archive",
            "archived",
            "legacy",
            "checkpoint",
            "backup",
            "_old",
            ".old",
        )
    ):
        return "DEPRECATED_OR_NONCANONICAL"

    return "DISCOVERED"


def infer_certification_status(path: Path) -> str:
    lowered = normalise_relative(path).lower()

    if "locked" in lowered:
        return "LOCKED"

    if "certified" in lowered:
        return "CERTIFIED"

    return "NOT_CERTIFIED"


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
        call_name = flatten_attribute(node.func)

        if call_name.endswith("Path") and node.args:
            return expression_to_path_text(node.args[0])

        if call_name.endswith("join") or call_name.endswith("joinpath"):
            parts = [
                expression_to_path_text(argument)
                for argument in node.args
            ]
            values = [part for part in parts if part]

            if values:
                return "/".join(values)

    return None


def clean_candidate_path(value: str) -> str:
    cleaned = value.strip().strip("\"'").replace("\\", "/")
    cleaned = re.sub(r"/+", "/", cleaned)
    return cleaned


def looks_like_data_path(value: str) -> bool:
    cleaned = clean_candidate_path(value)
    suffix = Path(cleaned).suffix.lower()

    return suffix in OUTPUT_SUFFIXES


def extract_string_assignments(tree: ast.AST) -> dict[str, str]:
    assignments: dict[str, str] = {}

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue

        value_node = node.value

        if value_node is None:
            continue

        path_text = expression_to_path_text(value_node)

        if not path_text:
            continue

        targets: list[ast.AST]

        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        else:
            targets = [node.target]

        for target in targets:
            if isinstance(target, ast.Name):
                assignments[target.id] = clean_candidate_path(path_text)

    return assignments


def resolve_path_expression(
    node: ast.AST,
    assignments: dict[str, str],
) -> str | None:
    if isinstance(node, ast.Name) and node.id in assignments:
        return assignments[node.id]

    value = expression_to_path_text(node)

    if not value:
        return None

    for name, assigned_value in assignments.items():
        value = value.replace(f"${name}", assigned_value)

    return clean_candidate_path(value)


def classify_open_mode(call: ast.Call) -> str:
    mode: str | None = None

    if len(call.args) >= 2:
        mode = constant_string(call.args[1])

    for keyword in call.keywords:
        if keyword.arg == "mode":
            mode = constant_string(keyword.value)

    if not mode:
        return "READ"

    if any(flag in mode for flag in ("w", "a", "x", "+")):
        return "WRITE"

    return "READ"


def extract_imports(
    tree: ast.AST,
    builder_id: str,
    builder_path: str,
) -> tuple[list[DependencyRecord], int]:
    dependencies: list[DependencyRecord] = []
    import_count = 0

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                import_count += 1
                dependencies.append(
                    DependencyRecord(
                        builder_id=builder_id,
                        builder_path=builder_path,
                        dependency_type="PYTHON_IMPORT",
                        dependency_value=alias.name,
                        evidence=f"line:{getattr(node, 'lineno', 0)}",
                    )
                )

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""

            for alias in node.names:
                import_count += 1
                imported = (
                    f"{module}.{alias.name}"
                    if module
                    else alias.name
                )

                dependencies.append(
                    DependencyRecord(
                        builder_id=builder_id,
                        builder_path=builder_path,
                        dependency_type="PYTHON_IMPORT",
                        dependency_value=imported,
                        evidence=f"line:{getattr(node, 'lineno', 0)}",
                    )
                )

    return dependencies, import_count


def extract_io_claims(
    tree: ast.AST,
    assignments: dict[str, str],
    builder_id: str,
    builder_path: str,
) -> tuple[list[DependencyRecord], list[OutputClaim]]:
    dependencies: list[DependencyRecord] = []
    outputs: list[OutputClaim] = []
    seen_dependencies: set[tuple[str, str]] = set()
    seen_outputs: set[str] = set()

    def add_dependency(
        dependency_type: str,
        value: str,
        evidence: str,
    ) -> None:
        cleaned = clean_candidate_path(value)
        key = (dependency_type, cleaned)

        if key in seen_dependencies:
            return

        seen_dependencies.add(key)

        dependencies.append(
            DependencyRecord(
                builder_id=builder_id,
                builder_path=builder_path,
                dependency_type=dependency_type,
                dependency_value=cleaned,
                evidence=evidence,
            )
        )

    def add_output(
        value: str,
        evidence: str,
    ) -> None:
        cleaned = clean_candidate_path(value)

        if cleaned in seen_outputs:
            return

        seen_outputs.add(cleaned)

        output_filename = Path(cleaned).name
        suffix = Path(cleaned).suffix.lower()
        is_public = (
            "public/data/" in cleaned.lower()
            or cleaned.lower().startswith("public/data/")
        )

        outputs.append(
            OutputClaim(
                builder_id=builder_id,
                builder_path=builder_path,
                output_path=cleaned,
                output_filename=output_filename,
                suffix=suffix,
                is_public_data_feed=is_public,
                evidence=evidence,
            )
        )

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        call_name = flatten_attribute(node.func)
        method_name = call_name.rsplit(".", 1)[-1] if call_name else ""
        line = getattr(node, "lineno", 0)
        evidence = f"{call_name or 'call'}@line:{line}"

        target_node: ast.AST | None = None

        if isinstance(node.func, ast.Attribute):
            target_node = node.func.value

        if method_name == "open":
            if node.args:
                if call_name == "open":
                    target_node = node.args[0]
                elif target_node is None:
                    target_node = node.args[0]

            if target_node is not None:
                resolved = resolve_path_expression(target_node, assignments)

                if resolved and looks_like_data_path(resolved):
                    if classify_open_mode(node) == "WRITE":
                        add_output(resolved, evidence)
                    else:
                        add_dependency("INPUT_FILE", resolved, evidence)

            continue

        if method_name in WRITE_METHODS:
            candidate_nodes: list[ast.AST] = []

            if target_node is not None:
                candidate_nodes.append(target_node)

            candidate_nodes.extend(node.args[:1])

            for candidate_node in candidate_nodes:
                resolved = resolve_path_expression(
                    candidate_node,
                    assignments,
                )

                if resolved and looks_like_data_path(resolved):
                    add_output(resolved, evidence)

        if method_name in READ_METHODS:
            candidate_nodes = []

            if target_node is not None:
                candidate_nodes.append(target_node)

            candidate_nodes.extend(node.args[:1])

            for candidate_node in candidate_nodes:
                resolved = resolve_path_expression(
                    candidate_node,
                    assignments,
                )

                if resolved and looks_like_data_path(resolved):
                    add_dependency("INPUT_FILE", resolved, evidence)

    for name, value in assignments.items():
        if not looks_like_data_path(value):
            continue

        upper_name = name.upper()
        evidence = f"assignment:{name}"

        if any(
            token in upper_name
            for token in (
                "OUTPUT",
                "DESTINATION",
                "TARGET",
                "PUBLISH",
                "FEED",
                "REPORT",
            )
        ):
            add_output(value, evidence)

        elif any(
            token in upper_name
            for token in (
                "INPUT",
                "SOURCE",
                "WAREHOUSE",
                "FACT",
                "HISTORY",
                "MASTER",
            )
        ):
            add_dependency("INPUT_FILE", value, evidence)

    return dependencies, outputs


def discover_local_dependencies(
    dependencies: list[DependencyRecord],
    known_python_modules: dict[str, str],
) -> list[DependencyRecord]:
    discovered: list[DependencyRecord] = []

    for dependency in dependencies:
        if dependency.dependency_type != "PYTHON_IMPORT":
            continue

        parts = dependency.dependency_value.split(".")

        candidates = [
            dependency.dependency_value,
            parts[0],
            parts[-1],
        ]

        matched_path: str | None = None

        for candidate in candidates:
            if candidate in known_python_modules:
                matched_path = known_python_modules[candidate]
                break

        if matched_path:
            discovered.append(
                DependencyRecord(
                    builder_id=dependency.builder_id,
                    builder_path=dependency.builder_path,
                    dependency_type="LOCAL_PYTHON_DEPENDENCY",
                    dependency_value=matched_path,
                    evidence=dependency.evidence,
                )
            )

    return discovered


def build_known_module_map(python_files: list[Path]) -> dict[str, str]:
    module_map: dict[str, str] = {}

    for path in python_files:
        relative = normalise_relative(path)
        stem = path.stem
        module_path = relative[:-3].replace("/", ".")

        module_map.setdefault(stem, relative)
        module_map.setdefault(module_path, relative)

        if module_path.startswith("scripts."):
            module_map.setdefault(
                module_path.removeprefix("scripts."),
                relative,
            )

    return module_map


def detect_orchestrator(
    path: Path,
    source: str,
    local_dependencies: list[DependencyRecord],
) -> bool:
    lowered_name = path.name.lower()
    lowered_source = source.lower()

    if lowered_name.startswith("run_"):
        return True

    if "orchestrat" in lowered_name or "pipeline" in lowered_name:
        return True

    local_builder_dependencies = sum(
        1
        for dependency in local_dependencies
        if Path(dependency.dependency_value).name.lower().startswith(
            BUILDER_PREFIXES
        )
    )

    if local_builder_dependencies >= 2:
        return True

    return (
        "subprocess.run" in lowered_source
        or "subprocess.popen" in lowered_source
    )


def is_audit_like(path: Path) -> bool:
    lowered = path.name.lower()
    return any(word in lowered for word in AUDIT_WORDS)


def write_csv(
    path: Path,
    rows: list[dict[str, object]],
    fieldnames: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()

        for row in rows:
            writer.writerow(row)


def markdown_escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def build_markdown(
    generated_at: str,
    records: list[BuilderRecord],
    outputs: list[OutputClaim],
    duplicate_groups: list[dict[str, object]],
    summary: dict[str, object],
) -> str:
    lines = [
        "# EDGEIQ Canonical Builder Registry V1",
        "",
        f"- Registry version: `{REGISTRY_VERSION}`",
        f"- Generated UTC: `{generated_at}`",
        f"- Repository: `{REPOSITORY_ROOT}`",
        f"- Verdict: **{summary['verdict']}**",
        f"- Builders discovered: **{summary['builder_count']}**",
        f"- Parsed successfully: **{summary['parsed_builder_count']}**",
        f"- Output claims: **{summary['output_claim_count']}**",
        f"- Public feed output claims: **{summary['public_feed_output_claim_count']}**",
        f"- Duplicate output paths: **{summary['duplicate_output_path_count']}**",
        "",
        "## Builder Registry",
        "",
        "| Builder ID | Builder | Domain | Category | Status | Outputs | Public Feeds | Local Dependencies | Parse |",
        "|---|---|---|---|---|---:|---:|---:|---|",
    ]

    for record in records:
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_escape(record.builder_id),
                    markdown_escape(record.relative_path),
                    markdown_escape(record.domain),
                    markdown_escape(record.category),
                    markdown_escape(record.lifecycle_status),
                    markdown_escape(record.output_claim_count),
                    markdown_escape(record.public_feed_output_count),
                    markdown_escape(record.local_dependency_count),
                    markdown_escape(record.parse_status),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Duplicate Output Claims",
            "",
        ]
    )

    if duplicate_groups:
        lines.extend(
            [
                "| Output Path | Claim Count | Builders |",
                "|---|---:|---|",
            ]
        )

        for group in duplicate_groups:
            lines.append(
                "| "
                + " | ".join(
                    [
                        markdown_escape(group["output_path"]),
                        markdown_escape(group["claim_count"]),
                        markdown_escape(group["builder_paths"]),
                    ]
                )
                + " |"
            )
    else:
        lines.append("No duplicate output claims detected.")

    lines.extend(
        [
            "",
            "## Governance Interpretation",
            "",
            "- `DISCOVERED` means the builder has been found but has not yet been individually certified.",
            "- `DEPRECATED_OR_NONCANONICAL` means the path appears to be a checkpoint, archive, backup, legacy or deprecated implementation.",
            "- Output claims are static code evidence. Runtime execution proof will be added in the next governance phase.",
            "- Duplicate output claims require review before a builder can be declared canonical.",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> int:
    generated_at = utc_timestamp()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    python_files = sorted(
        iter_python_files(),
        key=lambda path: normalise_relative(path).lower(),
    )

    builder_files = [
        path
        for path in python_files
        if is_builder_candidate(path)
    ]

    known_modules = build_known_module_map(python_files)

    builders: list[BuilderRecord] = []
    dependencies: list[DependencyRecord] = []
    output_claims: list[OutputClaim] = []

    parsed_count = 0

    for index, path in enumerate(builder_files, start=1):
        builder_id = f"BLD-{index:05d}"
        relative_path = normalise_relative(path)
        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        parse_status = "PASS"
        parse_error = ""
        import_count = 0
        builder_dependencies: list[DependencyRecord] = []
        builder_outputs: list[OutputClaim] = []

        try:
            tree = ast.parse(source, filename=relative_path)
            assignments = extract_string_assignments(tree)

            import_dependencies, import_count = extract_imports(
                tree,
                builder_id,
                relative_path,
            )

            io_dependencies, builder_outputs = extract_io_claims(
                tree,
                assignments,
                builder_id,
                relative_path,
            )

            builder_dependencies.extend(import_dependencies)
            builder_dependencies.extend(io_dependencies)

            local_dependencies = discover_local_dependencies(
                builder_dependencies,
                known_modules,
            )
            builder_dependencies.extend(local_dependencies)

            parsed_count += 1

        except SyntaxError as exc:
            parse_status = "FAIL"
            parse_error = (
                f"{exc.__class__.__name__}: "
                f"{exc.msg} line={exc.lineno}"
            )
            local_dependencies = []

        dependencies.extend(builder_dependencies)
        output_claims.extend(builder_outputs)

        input_claim_count = sum(
            1
            for dependency in builder_dependencies
            if dependency.dependency_type == "INPUT_FILE"
        )

        local_dependency_count = sum(
            1
            for dependency in builder_dependencies
            if dependency.dependency_type == "LOCAL_PYTHON_DEPENDENCY"
        )

        public_feed_count = sum(
            1
            for output in builder_outputs
            if output.is_public_data_feed
        )

        stat = path.stat()

        builders.append(
            BuilderRecord(
                builder_id=builder_id,
                builder_name=path.name,
                relative_path=relative_path,
                domain=infer_domain(relative_path),
                category=infer_category(path, source),
                lifecycle_status=infer_lifecycle_status(path),
                certification_status=infer_certification_status(path),
                is_orchestrator=detect_orchestrator(
                    path,
                    source,
                    local_dependencies,
                ),
                is_audit_like=is_audit_like(path),
                python_import_count=import_count,
                local_dependency_count=local_dependency_count,
                input_claim_count=input_claim_count,
                output_claim_count=len(builder_outputs),
                public_feed_output_count=public_feed_count,
                source_sha256=sha256_file(path),
                source_size_bytes=stat.st_size,
                source_modified_utc=datetime.fromtimestamp(
                    stat.st_mtime,
                    tz=timezone.utc,
                )
                .replace(microsecond=0)
                .isoformat(),
                parse_status=parse_status,
                parse_error=parse_error,
            )
        )

    claims_by_output: dict[str, list[OutputClaim]] = {}

    for claim in output_claims:
        claims_by_output.setdefault(
            claim.output_path.lower(),
            [],
        ).append(claim)

    duplicate_groups: list[dict[str, object]] = []

    for normalised_output, claims in sorted(claims_by_output.items()):
        unique_builders = sorted(
            {
                claim.builder_path
                for claim in claims
            }
        )

        if len(unique_builders) <= 1:
            continue

        duplicate_groups.append(
            {
                "output_path": claims[0].output_path,
                "normalised_output_path": normalised_output,
                "claim_count": len(claims),
                "builder_count": len(unique_builders),
                "builder_paths": " | ".join(unique_builders),
                "builder_ids": " | ".join(
                    sorted(
                        {
                            claim.builder_id
                            for claim in claims
                        }
                    )
                ),
            }
        )

    parse_failures = [
        record
        for record in builders
        if record.parse_status != "PASS"
    ]

    summary = {
        "registry_version": REGISTRY_VERSION,
        "generated_at_utc": generated_at,
        "repository_root": str(REPOSITORY_ROOT),
        "python_file_count": len(python_files),
        "builder_count": len(builders),
        "parsed_builder_count": parsed_count,
        "parse_failure_count": len(parse_failures),
        "dependency_record_count": len(dependencies),
        "local_dependency_count": sum(
            1
            for dependency in dependencies
            if dependency.dependency_type == "LOCAL_PYTHON_DEPENDENCY"
        ),
        "input_claim_count": sum(
            1
            for dependency in dependencies
            if dependency.dependency_type == "INPUT_FILE"
        ),
        "output_claim_count": len(output_claims),
        "public_feed_output_claim_count": sum(
            1
            for claim in output_claims
            if claim.is_public_data_feed
        ),
        "duplicate_output_path_count": len(duplicate_groups),
        "active_builder_count": sum(
            1
            for record in builders
            if record.lifecycle_status == "DISCOVERED"
        ),
        "noncanonical_builder_count": sum(
            1
            for record in builders
            if record.lifecycle_status == "DEPRECATED_OR_NONCANONICAL"
        ),
    }

    if not builders:
        verdict = "FAIL_NO_BUILDERS_DISCOVERED"
    elif parse_failures:
        verdict = "PARTIAL_PARSE_FAILURES"
    elif duplicate_groups:
        verdict = "PASS_WITH_DUPLICATE_OUTPUT_CLAIMS"
    else:
        verdict = "PASS"

    summary["verdict"] = verdict

    builder_rows = [asdict(record) for record in builders]
    dependency_rows = [asdict(record) for record in dependencies]
    output_rows = [asdict(record) for record in output_claims]

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
        DUPLICATE_OUTPUTS_OUTPUT,
        duplicate_groups,
        [
            "output_path",
            "normalised_output_path",
            "claim_count",
            "builder_count",
            "builder_paths",
            "builder_ids",
        ],
    )

    JSON_OUTPUT.write_text(
        json.dumps(
            {
                "summary": summary,
                "builders": builder_rows,
                "dependencies": dependency_rows,
                "output_claims": output_rows,
                "duplicate_output_claims": duplicate_groups,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    SUMMARY_OUTPUT.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    MARKDOWN_OUTPUT.write_text(
        build_markdown(
            generated_at,
            builders,
            output_claims,
            duplicate_groups,
            summary,
        ),
        encoding="utf-8",
    )

    print("EDGEIQ CANONICAL BUILDER REGISTRY V1")
    print(f"VERDICT={verdict}")
    print(f"BUILDERS={len(builders)}")
    print(f"PARSED={parsed_count}")
    print(f"PARSE_FAILURES={len(parse_failures)}")
    print(f"DEPENDENCIES={len(dependencies)}")
    print(f"OUTPUT_CLAIMS={len(output_claims)}")
    print(
        "PUBLIC_FEED_OUTPUT_CLAIMS="
        f"{summary['public_feed_output_claim_count']}"
    )
    print(
        "DUPLICATE_OUTPUT_PATHS="
        f"{len(duplicate_groups)}"
    )
    print(f"OUTPUT_ROOT={OUTPUT_ROOT}")

    if verdict == "FAIL_NO_BUILDERS_DISCOVERED":
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
