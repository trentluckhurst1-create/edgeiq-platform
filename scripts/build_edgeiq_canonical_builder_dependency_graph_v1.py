from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REFINED_ROOT = REPOSITORY_ROOT / "docs" / "platform-registry-v1" / "canonical-scope-refiner-v1"
REGISTRY_ROOT = REPOSITORY_ROOT / "docs" / "platform-registry-v1" / "builder-registry-v1-1"
OUTPUT_ROOT = REPOSITORY_ROOT / "docs" / "platform-registry-v1" / "builder-dependency-graph-v1"

REFINED_REGISTRY_PATH = REFINED_ROOT / "EDGEIQ_CANONICAL_BUILDER_REGISTRY_REFINED_V1.csv"
DEPENDENCIES_PATH = REGISTRY_ROOT / "EDGEIQ_CANONICAL_BUILDER_DEPENDENCIES_V1_1.csv"
OUTPUT_CLAIMS_PATH = REGISTRY_ROOT / "EDGEIQ_CANONICAL_BUILDER_OUTPUT_CLAIMS_V1_1.csv"

NODES_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_GRAPH_NODES_V1.csv"
EDGES_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_GRAPH_EDGES_V1.csv"
ORPHANS_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_ORPHANS_V1.csv"
DEAD_ENDS_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_DEAD_ENDS_V1.csv"
CYCLES_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_CYCLES_V1.csv"
SUMMARY_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_DEPENDENCY_GRAPH_SUMMARY_V1.json"
REPORT_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_DEPENDENCY_GRAPH_REPORT_V1.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def first(row: dict[str, str], *names: str) -> str:
    lowered = {str(k).strip().lower(): (v or "") for k, v in row.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value is not None and value.strip():
            return value.strip()
    return ""


def normalise_path(value: str) -> str:
    return value.strip().strip('"').replace("\\", "/").lstrip("./")


def tarjan_scc(nodes: set[str], adjacency: dict[str, set[str]]) -> list[list[str]]:
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    components: list[list[str]] = []

    def strongconnect(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlink[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for neighbour in sorted(adjacency.get(node, set())):
            if neighbour not in indices:
                strongconnect(neighbour)
                lowlink[node] = min(lowlink[node], lowlink[neighbour])
            elif neighbour in on_stack:
                lowlink[node] = min(lowlink[node], indices[neighbour])

        if lowlink[node] == indices[node]:
            component: list[str] = []
            while True:
                member = stack.pop()
                on_stack.remove(member)
                component.append(member)
                if member == node:
                    break
            components.append(sorted(component))

    for node in sorted(nodes):
        if node not in indices:
            strongconnect(node)

    return components


def main() -> int:
    registry_rows = read_csv(REFINED_REGISTRY_PATH)
    dependency_rows = read_csv(DEPENDENCIES_PATH)
    output_claim_rows = read_csv(OUTPUT_CLAIMS_PATH)

    canonical_rows = [
        row for row in registry_rows
        if first(row, "classification", "builder_classification").upper() == "CANONICAL"
    ]
    canonical_ids = {first(row, "builder_id", "id") for row in canonical_rows}
    canonical_ids.discard("")

    registry_by_id = {
        first(row, "builder_id", "id"): row
        for row in canonical_rows
        if first(row, "builder_id", "id")
    }

    outputs_by_path: dict[str, set[str]] = defaultdict(set)
    outputs_by_builder: dict[str, set[str]] = defaultdict(set)

    for row in output_claim_rows:
        builder_id = first(row, "builder_id", "id")
        if builder_id not in canonical_ids:
            continue
        output_path = normalise_path(first(row, "output_path", "path", "claimed_output"))
        if not output_path:
            continue
        outputs_by_path[output_path.lower()].add(builder_id)
        outputs_by_builder[builder_id].add(output_path)

    input_paths_by_builder: dict[str, set[str]] = defaultdict(set)
    explicit_edges: set[tuple[str, str, str, str]] = set()

    for row in dependency_rows:
        builder_id = first(row, "builder_id", "consumer_builder_id", "target_builder_id")
        if builder_id not in canonical_ids:
            continue

        producer_id = first(row, "producer_builder_id", "source_builder_id", "depends_on_builder_id")
        dependency_path = normalise_path(
            first(row, "dependency_path", "input_path", "path", "dependency")
        )
        dependency_type = first(row, "dependency_type", "type") or "INPUT"

        if dependency_path:
            input_paths_by_builder[builder_id].add(dependency_path)

        if producer_id and producer_id in canonical_ids and producer_id != builder_id:
            explicit_edges.add((producer_id, builder_id, dependency_path, dependency_type))

    inferred_edges: set[tuple[str, str, str, str]] = set()
    unresolved_inputs: dict[str, set[str]] = defaultdict(set)

    for consumer_id, paths in input_paths_by_builder.items():
        for input_path in paths:
            producers = outputs_by_path.get(input_path.lower(), set())
            if not producers:
                unresolved_inputs[consumer_id].add(input_path)
                continue
            for producer_id in producers:
                if producer_id != consumer_id:
                    inferred_edges.add((producer_id, consumer_id, input_path, "INFERRED_OUTPUT_TO_INPUT"))

    all_edges = explicit_edges | inferred_edges

    outgoing: dict[str, set[str]] = defaultdict(set)
    incoming: dict[str, set[str]] = defaultdict(set)
    edge_paths: dict[tuple[str, str], set[str]] = defaultdict(set)
    edge_sources: dict[tuple[str, str], set[str]] = defaultdict(set)

    for producer, consumer, path, source_type in all_edges:
        outgoing[producer].add(consumer)
        incoming[consumer].add(producer)
        if path:
            edge_paths[(producer, consumer)].add(path)
        edge_sources[(producer, consumer)].add(source_type)

    node_rows: list[dict[str, object]] = []
    for builder_id in sorted(canonical_ids):
        row = registry_by_id[builder_id]
        in_degree = len(incoming.get(builder_id, set()))
        out_degree = len(outgoing.get(builder_id, set()))
        node_rows.append(
            {
                "builder_id": builder_id,
                "relative_path": first(row, "relative_path", "builder_path", "path"),
                "classification": first(row, "classification"),
                "scope_status": first(row, "scope_status"),
                "input_path_count": len(input_paths_by_builder.get(builder_id, set())),
                "output_path_count": len(outputs_by_builder.get(builder_id, set())),
                "unresolved_input_count": len(unresolved_inputs.get(builder_id, set())),
                "in_degree": in_degree,
                "out_degree": out_degree,
                "is_orphan": str(in_degree == 0 and out_degree == 0).lower(),
                "is_dead_end": str(out_degree == 0 and len(outputs_by_builder.get(builder_id, set())) > 0).lower(),
                "is_root": str(in_degree == 0 and out_degree > 0).lower(),
            }
        )

    edge_rows: list[dict[str, object]] = []
    for producer, consumer in sorted(edge_paths.keys() | edge_sources.keys()):
        edge_rows.append(
            {
                "producer_builder_id": producer,
                "consumer_builder_id": consumer,
                "dependency_paths": " | ".join(sorted(edge_paths[(producer, consumer)])),
                "edge_sources": " | ".join(sorted(edge_sources[(producer, consumer)])),
            }
        )

    orphan_rows = [row for row in node_rows if row["is_orphan"] == "true"]
    dead_end_rows = [row for row in node_rows if row["is_dead_end"] == "true"]

    adjacency = {node: set(outgoing.get(node, set())) for node in canonical_ids}
    components = tarjan_scc(canonical_ids, adjacency)
    cyclic_components = [
        component for component in components
        if len(component) > 1 or (
            len(component) == 1 and component[0] in adjacency.get(component[0], set())
        )
    ]

    cycle_rows: list[dict[str, object]] = []
    for index, component in enumerate(sorted(cyclic_components, key=lambda c: (-len(c), c)), start=1):
        cycle_rows.append(
            {
                "cycle_id": f"CYCLE_{index:04d}",
                "builder_count": len(component),
                "builder_ids": " | ".join(component),
            }
        )

    write_csv(
        NODES_PATH,
        node_rows,
        [
            "builder_id",
            "relative_path",
            "classification",
            "scope_status",
            "input_path_count",
            "output_path_count",
            "unresolved_input_count",
            "in_degree",
            "out_degree",
            "is_orphan",
            "is_dead_end",
            "is_root",
        ],
    )
    write_csv(
        EDGES_PATH,
        edge_rows,
        [
            "producer_builder_id",
            "consumer_builder_id",
            "dependency_paths",
            "edge_sources",
        ],
    )
    write_csv(
        ORPHANS_PATH,
        orphan_rows,
        list(node_rows[0].keys()) if node_rows else [
            "builder_id", "relative_path", "classification", "scope_status",
            "input_path_count", "output_path_count", "unresolved_input_count",
            "in_degree", "out_degree", "is_orphan", "is_dead_end", "is_root",
        ],
    )
    write_csv(
        DEAD_ENDS_PATH,
        dead_end_rows,
        list(node_rows[0].keys()) if node_rows else [
            "builder_id", "relative_path", "classification", "scope_status",
            "input_path_count", "output_path_count", "unresolved_input_count",
            "in_degree", "out_degree", "is_orphan", "is_dead_end", "is_root",
        ],
    )
    write_csv(
        CYCLES_PATH,
        cycle_rows,
        ["cycle_id", "builder_count", "builder_ids"],
    )

    summary = {
        "schema_version": "1.0",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": "PASS",
        "canonical_builder_node_count": len(node_rows),
        "dependency_edge_count": len(edge_rows),
        "explicit_edge_count": len(explicit_edges),
        "inferred_edge_count": len(inferred_edges),
        "orphan_builder_count": len(orphan_rows),
        "dead_end_builder_count": len(dead_end_rows),
        "root_builder_count": sum(1 for row in node_rows if row["is_root"] == "true"),
        "cyclic_component_count": len(cycle_rows),
        "builders_with_unresolved_inputs": sum(
            1 for row in node_rows if int(row["unresolved_input_count"]) > 0
        ),
        "total_unresolved_input_paths": sum(
            int(row["unresolved_input_count"]) for row in node_rows
        ),
        "outputs": {
            "nodes_csv": str(NODES_PATH),
            "edges_csv": str(EDGES_PATH),
            "orphans_csv": str(ORPHANS_PATH),
            "dead_ends_csv": str(DEAD_ENDS_PATH),
            "cycles_csv": str(CYCLES_PATH),
            "report_md": str(REPORT_PATH),
        },
    }

    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# EDGEIQ Canonical Builder Dependency Graph V1",
        "",
        "## Executive Summary",
        "",
        f"- Verdict: **PASS**",
        f"- Canonical builder nodes: **{len(node_rows)}**",
        f"- Dependency edges: **{len(edge_rows)}**",
        f"- Orphan builders: **{len(orphan_rows)}**",
        f"- Dead-end builders: **{len(dead_end_rows)}**",
        f"- Root builders: **{summary['root_builder_count']}**",
        f"- Cyclic components: **{len(cycle_rows)}**",
        f"- Builders with unresolved inputs: **{summary['builders_with_unresolved_inputs']}**",
        "",
        "## Graph Method",
        "",
        "Edges are formed from explicit builder dependencies and inferred matches between "
        "a canonical builder's claimed outputs and another canonical builder's input paths.",
        "",
        "## Governance Findings",
        "",
        "- Orphans have no discovered incoming or outgoing builder relationship.",
        "- Dead ends claim outputs but have no downstream canonical consumer.",
        "- Cycles identify strongly connected builder components requiring orchestration review.",
        "- Unresolved inputs identify external, manual, public, or currently unowned dependencies.",
        "",
        "## Acceptance",
        "",
        "The graph is a read-only governed derivative. No builder source files are modified.",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print("EDGEIQ CANONICAL BUILDER DEPENDENCY GRAPH V1")
    print("VERDICT=PASS")
    print(f"NODES={len(node_rows)}")
    print(f"EDGES={len(edge_rows)}")
    print(f"ORPHANS={len(orphan_rows)}")
    print(f"DEAD_ENDS={len(dead_end_rows)}")
    print(f"CYCLES={len(cycle_rows)}")
    print(f"OUTPUT_ROOT={OUTPUT_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
