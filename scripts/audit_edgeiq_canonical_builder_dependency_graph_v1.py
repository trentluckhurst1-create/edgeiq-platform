from __future__ import annotations

import csv
import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPOSITORY_ROOT / "docs" / "platform-registry-v1" / "builder-dependency-graph-v1"

NODES_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_GRAPH_NODES_V1.csv"
EDGES_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_GRAPH_EDGES_V1.csv"
ORPHANS_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_ORPHANS_V1.csv"
DEAD_ENDS_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_DEAD_ENDS_V1.csv"
CYCLES_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_CYCLES_V1.csv"
SUMMARY_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_DEPENDENCY_GRAPH_SUMMARY_V1.json"
REPORT_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_DEPENDENCY_GRAPH_REPORT_V1.md"

REQUIRED = [
    NODES_PATH, EDGES_PATH, ORPHANS_PATH, DEAD_ENDS_PATH,
    CYCLES_PATH, SUMMARY_PATH, REPORT_PATH,
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def fail(message: str) -> int:
    print("AUDIT_VERDICT=FAIL")
    print(f"AUDIT_FAILURE={message}")
    return 1


def main() -> int:
    for path in REQUIRED:
        if not path.exists():
            return fail(f"Missing output: {path}")
        if path.stat().st_size == 0:
            return fail(f"Empty output: {path}")

    nodes = read_csv(NODES_PATH)
    edges = read_csv(EDGES_PATH)
    orphans = read_csv(ORPHANS_PATH)
    dead_ends = read_csv(DEAD_ENDS_PATH)
    cycles = read_csv(CYCLES_PATH)
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))

    if summary.get("verdict") != "PASS":
        return fail(f"Summary verdict is {summary.get('verdict')}")

    if len(nodes) != int(summary["canonical_builder_node_count"]):
        return fail("Node count mismatch")
    if len(edges) != int(summary["dependency_edge_count"]):
        return fail("Edge count mismatch")
    if len(orphans) != int(summary["orphan_builder_count"]):
        return fail("Orphan count mismatch")
    if len(dead_ends) != int(summary["dead_end_builder_count"]):
        return fail("Dead-end count mismatch")
    if len(cycles) != int(summary["cyclic_component_count"]):
        return fail("Cycle count mismatch")

    node_ids = {row["builder_id"] for row in nodes}
    if len(node_ids) != len(nodes):
        return fail("Duplicate builder_id in node graph")

    for row in edges:
        if row["producer_builder_id"] not in node_ids:
            return fail(f"Unknown producer node: {row['producer_builder_id']}")
        if row["consumer_builder_id"] not in node_ids:
            return fail(f"Unknown consumer node: {row['consumer_builder_id']}")
        if row["producer_builder_id"] == row["consumer_builder_id"]:
            return fail(f"Unexpected self edge: {row['producer_builder_id']}")

    orphan_ids = {row["builder_id"] for row in orphans}
    for row in nodes:
        expected = row["in_degree"] == "0" and row["out_degree"] == "0"
        actual = row["builder_id"] in orphan_ids
        if expected != actual:
            return fail(f"Orphan reconciliation failed: {row['builder_id']}")

    dead_end_ids = {row["builder_id"] for row in dead_ends}
    for row in nodes:
        expected = row["out_degree"] == "0" and int(row["output_path_count"]) > 0
        actual = row["builder_id"] in dead_end_ids
        if expected != actual:
            return fail(f"Dead-end reconciliation failed: {row['builder_id']}")

    report = REPORT_PATH.read_text(encoding="utf-8")
    for heading in [
        "# EDGEIQ Canonical Builder Dependency Graph V1",
        "## Executive Summary",
        "## Graph Method",
        "## Governance Findings",
        "## Acceptance",
    ]:
        if heading not in report:
            return fail(f"Report missing section: {heading}")

    print("EDGEIQ CANONICAL BUILDER DEPENDENCY GRAPH V1 AUDIT")
    print("AUDIT_VERDICT=PASS")
    print(f"NODES={len(nodes)}")
    print(f"EDGES={len(edges)}")
    print(f"ORPHANS={len(orphans)}")
    print(f"DEAD_ENDS={len(dead_ends)}")
    print(f"CYCLES={len(cycles)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
