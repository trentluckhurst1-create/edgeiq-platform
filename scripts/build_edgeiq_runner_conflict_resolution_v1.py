from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
GRAPH = DATA / "edgeiq_runner_entity_graph_v1.csv"
OUT = DATA / "edgeiq_runner_conflict_resolution_v1.csv"

FIELDS = [
    "source_lineage", "edgeiq_runner_key", "conflict_type", "conflict_severity",
    "resolution_action", "suppressed_candidate", "preferred_candidate", "conflict_notes",
]


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"} else text


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    except Exception:
        return []


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{int(datetime.now().timestamp() * 1000)}.tmp")
    try:
        with tmp.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        tmp.replace(path)
    except PermissionError:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)


def score(row: dict[str, str]) -> int:
    try:
        return int(float(clean(row.get("runner_entity_confidence"))))
    except ValueError:
        return 0


def main() -> None:
    graph = read_csv(GRAPH)
    by_lineage: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_edgeiq: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in graph:
        if clean(row.get("source_lineage")):
            by_lineage[clean(row.get("source_lineage"))].append(row)
        if clean(row.get("edgeiq_runner_key")):
            by_edgeiq[clean(row.get("edgeiq_runner_key"))].append(row)
    rows: list[dict[str, object]] = []
    for lineage, candidates in by_lineage.items():
        ranked = sorted(candidates, key=score, reverse=True)
        if len(ranked) > 1 and score(ranked[0]) - score(ranked[1]) < 8 and score(ranked[1]) >= 50:
            for row in ranked:
                rows.append({
                    "source_lineage": lineage,
                    "edgeiq_runner_key": clean(row.get("edgeiq_runner_key")),
                    "conflict_type": "ONE_SECTIONAL_TO_MULTIPLE_EDGEIQ",
                    "conflict_severity": "HIGH",
                    "resolution_action": "AMBIGUOUS_BLOCK",
                    "suppressed_candidate": "NO",
                    "preferred_candidate": "NO",
                    "conflict_notes": "top runner graph candidates are too close to safely resolve",
                })
        elif ranked and len(ranked) > 1:
            winner = ranked[0]
            for row in ranked[1:]:
                rows.append({
                    "source_lineage": lineage,
                    "edgeiq_runner_key": clean(row.get("edgeiq_runner_key")),
                    "conflict_type": "LOWER_RANKED_CANDIDATE",
                    "conflict_severity": "LOW",
                    "resolution_action": "SUPPRESS_CANDIDATE",
                    "suppressed_candidate": "YES",
                    "preferred_candidate": clean(winner.get("edgeiq_runner_key")),
                    "conflict_notes": "candidate retained for lineage diagnostics but suppressed by graph rank",
                })
    for edgeiq_key, candidates in by_edgeiq.items():
        strong = [row for row in candidates if score(row) >= 68]
        lineages = {clean(row.get("source_lineage")) for row in strong}
        if len(lineages) > 1:
            for row in strong:
                rows.append({
                    "source_lineage": clean(row.get("source_lineage")),
                    "edgeiq_runner_key": edgeiq_key,
                    "conflict_type": "MULTIPLE_SECTIONAL_TO_ONE_EDGEIQ",
                    "conflict_severity": "HIGH",
                    "resolution_action": "AMBIGUOUS_BLOCK",
                    "suppressed_candidate": "NO",
                    "preferred_candidate": "NO",
                    "conflict_notes": "multiple sectional lineages compete for same EDGEiQ runner",
                })
    write_csv(OUT, rows, FIELDS)
    print("=" * 90)
    print("EDGEIQ RUNNER CONFLICT RESOLUTION V1")
    print("=" * 90)
    print("CONFLICTS:", len(rows))
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
