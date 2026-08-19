from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFINED = ROOT / "docs/platform-registry-v1/canonical-scope-refiner-v1/EDGEIQ_CANONICAL_BUILDER_REGISTRY_REFINED_V1.csv"
DEPS = ROOT / "docs/platform-registry-v1/builder-registry-v1-1/EDGEIQ_CANONICAL_BUILDER_DEPENDENCIES_V1_1.csv"
CLAIMS = ROOT / "docs/platform-registry-v1/builder-registry-v1-1/EDGEIQ_CANONICAL_BUILDER_OUTPUT_CLAIMS_V1_1.csv"
OUT = ROOT / "docs/platform-registry-v1/builder-dependency-graph-v1-1"

NODES = OUT / "EDGEIQ_CANONICAL_BUILDER_GRAPH_NODES_V1_1.csv"
EDGES = OUT / "EDGEIQ_CANONICAL_BUILDER_GRAPH_EDGES_V1_1.csv"
UNRESOLVED = OUT / "EDGEIQ_CANONICAL_BUILDER_UNRESOLVED_DEPENDENCIES_V1_1.csv"
SCHEMA = OUT / "EDGEIQ_CANONICAL_DEPENDENCY_SOURCE_SCHEMA_PROFILE_V1_1.json"
SUMMARY = OUT / "EDGEIQ_CANONICAL_BUILDER_DEPENDENCY_GRAPH_SUMMARY_V1_1.json"
REPORT = OUT / "EDGEIQ_CANONICAL_BUILDER_DEPENDENCY_GRAPH_REPORT_V1_1.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def first(row: dict[str, str], names: list[str]) -> str:
    lowered = {str(k).strip().lower(): str(v or "").strip() for k, v in row.items()}
    for name in names:
        if lowered.get(name.lower()):
            return lowered[name.lower()]
    return ""


def norm(value: str) -> str:
    value = value.strip().strip("'\"").replace("\\", "/")
    root = ROOT.as_posix().rstrip("/") + "/"
    if value.lower().startswith(root.lower()):
        value = value[len(root):]
    while value.startswith("./"):
        value = value[2:]
    return value.lower()


def path_like(value: str) -> bool:
    v = value.lower()
    return any(x in v for x in (".csv", ".json", ".parquet", ".md", ".txt", ".sqlite", ".db", ".py"))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def resolve_builder(row: dict[str, str], ids: set[str], path_to_id: dict[str, str]) -> str:
    preferred = [
        "builder_id", "consumer_builder_id", "producer_builder_id",
        "source_builder_id", "target_builder_id", "depends_on_builder_id",
        "builder", "script", "script_path", "builder_path", "relative_path",
    ]
    for name in preferred:
        value = first(row, [name])
        if value in ids:
            return value
        n = norm(value)
        if n in path_to_id:
            return path_to_id[n]

    for value in row.values():
        text = str(value or "").strip()
        if text in ids:
            return text
        n = norm(text)
        if n in path_to_id:
            return path_to_id[n]
    return ""


def candidate_paths(row: dict[str, str], mode: str) -> list[str]:
    scored: list[tuple[int, str]] = []
    for key, raw in row.items():
        value = str(raw or "").strip()
        if not value or not path_like(value):
            continue
        k = str(key).lower()
        score = 0
        if mode == "output":
            if any(t in k for t in ("output", "claim", "artifact", "feed", "write", "target")):
                score += 10
            if any(t in k for t in ("input", "dependency", "read")):
                score -= 5
        else:
            if any(t in k for t in ("input", "dependency", "source", "read", "upstream")):
                score += 10
            if any(t in k for t in ("output", "claim", "write")):
                score -= 5
        scored.append((score, norm(value)))
    if not scored:
        return []
    best = max(score for score, _ in scored)
    return sorted({value for score, value in scored if score == best and value})


def main() -> int:
    registry = read_csv(REFINED)
    deps = read_csv(DEPS)
    claims = read_csv(CLAIMS)

    canonical = [
        r for r in registry
        if first(r, ["classification", "builder_classification"]).upper() == "CANONICAL"
    ]
    ids = {first(r, ["builder_id", "id"]) for r in canonical}
    ids.discard("")

    by_id = {first(r, ["builder_id", "id"]): r for r in canonical}
    path_to_id: dict[str, str] = {}
    for builder_id, row in by_id.items():
        p = first(row, ["relative_path", "builder_path", "path", "script_path"])
        if p:
            path_to_id[norm(p)] = builder_id

    outputs_by_path: dict[str, set[str]] = defaultdict(set)
    outputs_by_builder: dict[str, set[str]] = defaultdict(set)
    unresolved_claim_rows = 0

    for row in claims:
        producer = resolve_builder(row, ids, path_to_id)
        paths = candidate_paths(row, "output")
        if not producer or not paths:
            unresolved_claim_rows += 1
            continue
        for p in paths:
            outputs_by_path[p].add(producer)
            outputs_by_builder[producer].add(p)

    inputs_by_builder: dict[str, set[str]] = defaultdict(set)
    unresolved_rows: list[dict[str, object]] = []

    for index, row in enumerate(deps, start=2):
        consumer = resolve_builder(row, ids, path_to_id)
        paths = candidate_paths(row, "input")
        if not consumer or not paths:
            unresolved_rows.append({
                "source_row": index,
                "consumer_builder_id": consumer,
                "dependency_path": "",
                "reason": "UNRESOLVED_CONSUMER_OR_PATH",
                "raw_row_json": json.dumps(row, sort_keys=True),
            })
            continue
        for p in paths:
            inputs_by_builder[consumer].add(p)

    edge_evidence: dict[tuple[str, str], set[str]] = defaultdict(set)
    for consumer, paths in inputs_by_builder.items():
        for p in paths:
            producers = outputs_by_path.get(p, set())
            if not producers:
                unresolved_rows.append({
                    "source_row": "",
                    "consumer_builder_id": consumer,
                    "dependency_path": p,
                    "reason": "NO_CANONICAL_OUTPUT_OWNER",
                    "raw_row_json": "",
                })
                continue
            for producer in producers:
                if producer != consumer:
                    edge_evidence[(producer, consumer)].add(p)

    incoming: dict[str, set[str]] = defaultdict(set)
    outgoing: dict[str, set[str]] = defaultdict(set)
    for producer, consumer in edge_evidence:
        outgoing[producer].add(consumer)
        incoming[consumer].add(producer)

    node_rows = []
    for builder_id in sorted(ids):
        row = by_id[builder_id]
        node_rows.append({
            "builder_id": builder_id,
            "relative_path": first(row, ["relative_path", "builder_path", "path", "script_path"]),
            "input_path_count": len(inputs_by_builder.get(builder_id, set())),
            "output_path_count": len(outputs_by_builder.get(builder_id, set())),
            "in_degree": len(incoming.get(builder_id, set())),
            "out_degree": len(outgoing.get(builder_id, set())),
            "is_orphan": str(not incoming.get(builder_id) and not outgoing.get(builder_id)).lower(),
        })

    edge_rows = [
        {
            "producer_builder_id": producer,
            "consumer_builder_id": consumer,
            "dependency_path_count": len(paths),
            "dependency_paths": " | ".join(sorted(paths)),
        }
        for (producer, consumer), paths in sorted(edge_evidence.items())
    ]

    write_csv(NODES, node_rows, [
        "builder_id", "relative_path", "input_path_count", "output_path_count",
        "in_degree", "out_degree", "is_orphan",
    ])
    write_csv(EDGES, edge_rows, [
        "producer_builder_id", "consumer_builder_id",
        "dependency_path_count", "dependency_paths",
    ])
    write_csv(UNRESOLVED, unresolved_rows, [
        "source_row", "consumer_builder_id", "dependency_path", "reason", "raw_row_json",
    ])

    schema_profile = {
        "dependency_headers": list(deps[0].keys()) if deps else [],
        "output_claim_headers": list(claims[0].keys()) if claims else [],
        "dependency_row_count": len(deps),
        "output_claim_row_count": len(claims),
        "resolved_output_owner_count": len(outputs_by_builder),
        "resolved_output_path_count": len(outputs_by_path),
        "resolved_input_consumer_count": len(inputs_by_builder),
        "resolved_input_path_count": sum(len(v) for v in inputs_by_builder.values()),
        "unresolved_output_claim_rows": unresolved_claim_rows,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    SCHEMA.write_text(json.dumps(schema_profile, indent=2) + "\n", encoding="utf-8")

    edge_count = len(edge_rows)
    verdict = "PASS" if edge_count > 0 else "FAIL_ZERO_EDGES"
    summary = {
        "schema_version": "1.1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "canonical_builder_node_count": len(node_rows),
        "dependency_edge_count": edge_count,
        "orphan_builder_count": sum(1 for r in node_rows if r["is_orphan"] == "true"),
        "builders_with_inputs": sum(1 for r in node_rows if int(r["input_path_count"]) > 0),
        "builders_with_outputs": sum(1 for r in node_rows if int(r["output_path_count"]) > 0),
        "resolved_output_path_count": len(outputs_by_path),
        "unresolved_dependency_record_count": len(unresolved_rows),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    REPORT.write_text(
        "\n".join([
            "# EDGEIQ Canonical Builder Dependency Graph V1.1",
            "",
            "## Executive Summary",
            "",
            f"- Verdict: **{verdict}**",
            f"- Canonical nodes: **{len(node_rows)}**",
            f"- Resolved dependency edges: **{edge_count}**",
            f"- Orphan builders: **{summary['orphan_builder_count']}**",
            f"- Builders with discovered inputs: **{summary['builders_with_inputs']}**",
            f"- Builders with claimed outputs: **{summary['builders_with_outputs']}**",
            "",
            "## Correction from V1",
            "",
            "V1 passed structural reconciliation while producing zero edges. V1.1 adds "
            "source-schema profiling, dynamic builder resolution, path-column scoring, "
            "and a mandatory non-zero-edge acceptance criterion.",
            "",
            "## Governance Rule",
            "",
            "The unit fails when zero producer-to-consumer edges are resolved.",
            "",
        ]),
        encoding="utf-8",
    )

    print("EDGEIQ CANONICAL BUILDER DEPENDENCY GRAPH V1.1")
    print(f"VERDICT={verdict}")
    print(f"NODES={len(node_rows)}")
    print(f"EDGES={edge_count}")
    print(f"ORPHANS={summary['orphan_builder_count']}")
    print(f"BUILDERS_WITH_INPUTS={summary['builders_with_inputs']}")
    print(f"BUILDERS_WITH_OUTPUTS={summary['builders_with_outputs']}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
