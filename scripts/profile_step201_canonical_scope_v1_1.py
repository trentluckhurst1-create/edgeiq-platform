from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


STEP_NAME = "STEP201 V1.1 Canonical Scope Profile"

GENERATED_NAME_TOKENS = (
    "audit",
    "acceptance",
    "browser",
    "candidate",
    "checkpoint",
    "comparison",
    "coverage",
    "diagnostic",
    "evidence",
    "latest",
    "manifest",
    "output",
    "profile",
    "report",
    "result",
    "run",
    "snapshot",
    "summary",
    "validation",
)

SOURCE_NAME_TOKENS = (
    "architecture",
    "builder",
    "common",
    "config",
    "contract",
    "design",
    "engine",
    "implementation",
    "model",
    "policy",
    "registry",
    "schema",
    "spec",
    "specification",
)

DATE_PATTERN = re.compile(
    r"(?:19|20)\d{2}[-_]?\d{2}[-_]?\d{2}"
    r"|(?:19|20)\d{6}"
    r"|T\d{6}Z",
    re.IGNORECASE,
)

VERSION_PATTERN = re.compile(
    r"(?:^|[_-])v\d+(?:[_\.-]\d+)*(?:$|[_\.-])",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Profile the retained STEP201 V1.1 canonical scope."
    )
    parser.add_argument(
        "--repository-root",
        default=".",
    )
    parser.add_argument(
        "--input-census",
        default=(
            "docs/performance-intelligence-discovery/"
            "STEP201_REPOSITORY_CENSUS_V1_1.csv"
        ),
    )
    parser.add_argument(
        "--output-root",
        default="docs/performance-intelligence-discovery",
    )
    return parser.parse_args()


def normalise(value: str) -> str:
    return str(value or "").replace("\\", "/").lstrip("./")


def path_at_depth(path_text: str, depth: int) -> str:
    parts = Path(normalise(path_text)).parts
    if not parts:
        return "<root>"
    return "/".join(parts[:depth])


def classify_shape(row: dict[str, str]) -> tuple[str, list[str]]:
    path_text = normalise(row.get("repository_path", ""))
    lowered = path_text.lower()
    name = row.get("name", "").lower()
    extension = row.get("extension", "").lower()
    asset_type = row.get("asset_type", "Unknown")

    signals: list[str] = []

    generated_hits = [
        token
        for token in GENERATED_NAME_TOKENS
        if token in name
    ]
    source_hits = [
        token
        for token in SOURCE_NAME_TOKENS
        if token in name
    ]

    if generated_hits:
        signals.append(
            "generated-name-token:" + ",".join(generated_hits)
        )

    if source_hits:
        signals.append(
            "source-name-token:" + ",".join(source_hits)
        )

    if DATE_PATTERN.search(name):
        signals.append("dated-name")

    if VERSION_PATTERN.search(name):
        signals.append("versioned-name")

    if "/runs/" in f"/{lowered}/":
        signals.append("runs-directory")

    if "/reports/" in f"/{lowered}/":
        signals.append("reports-directory")

    if "/evidence/" in f"/{lowered}/":
        signals.append("evidence-directory")

    if "/latest/" in f"/{lowered}/":
        signals.append("latest-directory")

    if "/snapshots/" in f"/{lowered}/":
        signals.append("snapshots-directory")

    if asset_type in {
        "Contract",
        "Specification",
        "Builder",
        "Validation",
    }:
        return "CANONICAL_GOVERNANCE", signals

    if lowered.startswith(
        (
            "contracts/performance-intelligence/",
            "config/performance-intelligence/",
            "scripts/performance-intelligence/",
        )
    ):
        return "CANONICAL_PATH", signals

    if (
        asset_type == "Dataset"
        and lowered.startswith("docs/performance-intelligence/")
    ):
        return "DOC_TREE_DATASET", signals

    if generated_hits or DATE_PATTERN.search(name):
        return "LIKELY_GENERATED", signals

    if source_hits:
        return "LIKELY_SOURCE", signals

    if extension in {".csv", ".json", ".txt"}:
        return "STRUCTURED_OR_EVIDENCE", signals

    if asset_type in {"Documentation", "Audit"}:
        return "DOCUMENT_OR_AUDIT", signals

    return "UNRESOLVED", signals


def markdown_counter(
    title: str,
    heading: str,
    counter: Counter[str],
    limit: int,
) -> list[str]:
    lines = [
        f"## {title}",
        "",
        f"| {heading} | Count |",
        "|---|---:|",
    ]

    for key, value in counter.most_common(limit):
        safe_key = str(key).replace("|", "\\|")
        lines.append(f"| {safe_key} | {value:,} |")

    lines.append("")
    return lines


def main() -> int:
    args = parse_args()

    root = Path(args.repository_root).resolve()
    input_path = (root / args.input_census).resolve()
    output_root = (root / args.output_root).resolve()

    if not input_path.exists():
        print(f"ERROR: Input not found: {input_path}", file=sys.stderr)
        return 2

    output_root.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    if not rows:
        print("ERROR: V1.1 census contains zero rows.", file=sys.stderr)
        return 3

    shape_counts: Counter[str] = Counter()
    root_counts: Counter[str] = Counter()
    depth_two_counts: Counter[str] = Counter()
    depth_three_counts: Counter[str] = Counter()
    extension_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    inclusion_counts: Counter[str] = Counter()
    doc_dataset_depth_counts: Counter[str] = Counter()
    doc_dataset_extension_counts: Counter[str] = Counter()
    signal_counts: Counter[str] = Counter()

    profiled_rows: list[dict[str, str]] = []

    for row in rows:
        shape, signals = classify_shape(row)
        path_text = normalise(row.get("repository_path", ""))

        shape_counts[shape] += 1
        root_counts[path_at_depth(path_text, 1)] += 1
        depth_two_counts[path_at_depth(path_text, 2)] += 1
        depth_three_counts[path_at_depth(path_text, 3)] += 1
        extension_counts[row.get("extension", "<none>")] += 1
        type_counts[row.get("asset_type", "Unknown")] += 1
        inclusion_counts[
            row.get("inclusion_reason", "Unknown")
        ] += 1

        for signal in signals:
            signal_counts[signal] += 1

        if shape == "DOC_TREE_DATASET":
            doc_dataset_depth_counts[
                path_at_depth(path_text, 4)
            ] += 1
            doc_dataset_extension_counts[
                row.get("extension", "<none>")
            ] += 1

        profiled = dict(row)
        profiled["scope_shape"] = shape
        profiled["scope_signals"] = "; ".join(signals)
        profiled_rows.append(profiled)

    csv_path = (
        output_root /
        "STEP201_CANONICAL_SCOPE_PROFILE_V1_1.csv"
    )
    json_path = (
        output_root /
        "STEP201_CANONICAL_SCOPE_PROFILE_V1_1.json"
    )
    markdown_path = (
        output_root /
        "STEP201_CANONICAL_SCOPE_PROFILE_V1_1.md"
    )

    output_fields = list(rows[0].keys()) + [
        "scope_shape",
        "scope_signals",
    ]

    with csv_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=output_fields,
        )
        writer.writeheader()
        writer.writerows(
            sorted(
                profiled_rows,
                key=lambda item: (
                    item["scope_shape"],
                    item["repository_path"],
                ),
            )
        )

    payload = {
        "step": STEP_NAME,
        "generated_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "asset_count": len(rows),
        "scope_shapes": dict(shape_counts),
        "top_level_paths": dict(root_counts),
        "second_level_paths": dict(depth_two_counts),
        "third_level_paths": dict(depth_three_counts),
        "extensions": dict(extension_counts),
        "asset_types": dict(type_counts),
        "inclusion_reasons": dict(inclusion_counts),
        "doc_tree_dataset_paths": dict(
            doc_dataset_depth_counts
        ),
        "doc_tree_dataset_extensions": dict(
            doc_dataset_extension_counts
        ),
        "signals": dict(signal_counts),
    }

    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    lines = [
        f"# {STEP_NAME}",
        "",
        f"- Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        f"- V1.1 assets profiled: {len(rows):,}",
        "",
        "This profile does not alter the V1.1 census.",
        "It identifies generated-document and dataset concentrations",
        "before the final STEP201 scope decision.",
        "",
    ]

    lines.extend(
        markdown_counter(
            "Scope Shape",
            "Classification",
            shape_counts,
            30,
        )
    )
    lines.extend(
        markdown_counter(
            "Second-Level Paths",
            "Path",
            depth_two_counts,
            50,
        )
    )
    lines.extend(
        markdown_counter(
            "Third-Level Paths",
            "Path",
            depth_three_counts,
            80,
        )
    )
    lines.extend(
        markdown_counter(
            "Documentation-Tree Dataset Paths",
            "Path",
            doc_dataset_depth_counts,
            80,
        )
    )
    lines.extend(
        markdown_counter(
            "Documentation-Tree Dataset Extensions",
            "Extension",
            doc_dataset_extension_counts,
            20,
        )
    )
    lines.extend(
        markdown_counter(
            "Scope Signals",
            "Signal",
            signal_counts,
            50,
        )
    )
    lines.extend(
        markdown_counter(
            "Inclusion Reasons",
            "Reason",
            inclusion_counts,
            50,
        )
    )

    markdown_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print(f"STEP: {STEP_NAME}")
    print(f"V1.1 ASSETS PROFILED: {len(rows):,}")

    for key, value in shape_counts.most_common():
        print(f"{key}: {value:,}")

    print("")
    print("TOP 30 THIRD-LEVEL PATHS")

    for key, value in depth_three_counts.most_common(30):
        print(f"{key}: {value:,}")

    print("")
    print("TOP 30 DOCUMENTATION-TREE DATASET PATHS")

    for key, value in doc_dataset_depth_counts.most_common(30):
        print(f"{key}: {value:,}")

    print(f"CREATED: {csv_path}")
    print(f"CREATED: {json_path}")
    print(f"CREATED: {markdown_path}")
    print("SCOPE PROFILE STATUS: PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
