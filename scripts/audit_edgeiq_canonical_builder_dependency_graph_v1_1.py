from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/platform-registry-v1/builder-dependency-graph-v1-1"
NODES = OUT / "EDGEIQ_CANONICAL_BUILDER_GRAPH_NODES_V1_1.csv"
EDGES = OUT / "EDGEIQ_CANONICAL_BUILDER_GRAPH_EDGES_V1_1.csv"
UNRESOLVED = OUT / "EDGEIQ_CANONICAL_BUILDER_UNRESOLVED_DEPENDENCIES_V1_1.csv"
SCHEMA = OUT / "EDGEIQ_CANONICAL_DEPENDENCY_SOURCE_SCHEMA_PROFILE_V1_1.json"
SUMMARY = OUT / "EDGEIQ_CANONICAL_BUILDER_DEPENDENCY_GRAPH_SUMMARY_V1_1.json"
REPORT = OUT / "EDGEIQ_CANONICAL_BUILDER_DEPENDENCY_GRAPH_REPORT_V1_1.md"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fail(message: str) -> int:
    print("AUDIT_VERDICT=FAIL")
    print(f"AUDIT_FAILURE={message}")
    return 1


def main() -> int:
    for path in [NODES, EDGES, UNRESOLVED, SCHEMA, SUMMARY, REPORT]:
        if not path.exists() or path.stat().st_size == 0:
            return fail(f"Missing or empty output: {path}")

    nodes = rows(NODES)
    edges = rows(EDGES)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    if summary.get("verdict") != "PASS":
        return fail(f"Builder verdict is {summary.get('verdict')}")
    if len(edges) == 0:
        return fail("Zero dependency edges are forbidden")
    if len(nodes) != int(summary["canonical_builder_node_count"]):
        return fail("Node count mismatch")
    if len(edges) != int(summary["dependency_edge_count"]):
        return fail("Edge count mismatch")
    if not schema.get("dependency_headers"):
        return fail("Dependency schema headers were not captured")
    if not schema.get("output_claim_headers"):
        return fail("Output-claim schema headers were not captured")

    node_ids = {r["builder_id"] for r in nodes}
    if len(node_ids) != len(nodes):
        return fail("Duplicate node IDs")

    for edge in edges:
        if edge["producer_builder_id"] not in node_ids:
            return fail(f"Unknown producer: {edge['producer_builder_id']}")
        if edge["consumer_builder_id"] not in node_ids:
            return fail(f"Unknown consumer: {edge['consumer_builder_id']}")
        if edge["producer_builder_id"] == edge["consumer_builder_id"]:
            return fail(f"Self-edge detected: {edge['producer_builder_id']}")

    print("EDGEIQ CANONICAL BUILDER DEPENDENCY GRAPH V1.1 AUDIT")
    print("AUDIT_VERDICT=PASS")
    print(f"NODES={len(nodes)}")
    print(f"EDGES={len(edges)}")
    print(f"ORPHANS={summary['orphan_builder_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
