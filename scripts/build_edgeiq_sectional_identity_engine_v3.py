from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
IDENTITY_V2 = DATA / "edgeiq_sectional_identity_engine_v2.csv"
GRAPH = DATA / "edgeiq_runner_entity_graph_v1.csv"
CONFLICTS = DATA / "edgeiq_runner_conflict_resolution_v1.csv"
CANONICAL = DATA / "edgeiq_canonical_split_schema_v1.csv"
PHYSICS = DATA / "edgeiq_sectional_physics_validation_v1.csv"
FIELD_MATCH = DATA / "edgeiq_sectional_field_composition_match_v1.csv"
OUT = DATA / "edgeiq_sectional_identity_engine_v3.csv"
SUMMARY = DATA / "edgeiq_sectional_identity_summary_v3.csv"

FIELDS = [
    "source_lineage", "source_file", "source_row_id", "race_date", "track", "race_no",
    "distance", "horse", "horse_key", "edgeiq_runner", "edgeiq_runner_key",
    "identity_v2_confidence", "identity_v2_status", "runner_entity_confidence",
    "runner_entity_status", "runner_resolution_method", "race_identity_status",
    "field_composition_confidence", "physics_valid", "physics_grade", "physics_confidence",
    "payload_structure_type", "reconstruction_confidence", "conflict_status",
    "identity_v3_confidence", "identity_v3_status", "trusted_runner_identity",
    "trusted_race_identity", "trusted_modelling_identity", "trusted_execution_identity",
    "identity_v3_reason",
]

SUMMARY_FIELDS = ["metric", "value"]


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


def confidence(value: object) -> int:
    try:
        return max(0, min(100, int(round(float(clean(value))))))
    except ValueError:
        return 0


def lineage(row: dict[str, str]) -> str:
    return clean(row.get("source_lineage")) or f"{clean(row.get('source_file'))}#{clean(row.get('source_row_id'))}"


def best_by_lineage(rows: list[dict[str, str]], score_key: str) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        key = lineage(row)
        if not key:
            continue
        if key not in out or confidence(row.get(score_key)) > confidence(out[key].get(score_key)):
            out[key] = row
    return out


def conflict_lookup() -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_csv(CONFLICTS):
        if clean(row.get("source_lineage")):
            out[clean(row.get("source_lineage"))].append(row)
    return out


def decide(id2: dict[str, str], graph: dict[str, str] | None, physics: dict[str, str] | None, conflicts: list[dict[str, str]]) -> tuple[int, str, str, str, str, str, str]:
    reasons: list[str] = []
    id2_conf = confidence(id2.get("identity_v2_confidence"))
    runner_conf = confidence(graph.get("runner_entity_confidence")) if graph else 0
    field_conf = confidence(id2.get("field_composition_confidence"))
    physics_conf = confidence(physics.get("physics_confidence")) if physics else 0
    reconstruction_conf = confidence(physics.get("reconstruction_confidence")) if physics else 0
    physics_valid = physics and clean(physics.get("physics_valid")).upper() == "YES"
    physics_grade = clean(physics.get("physics_grade")).upper() if physics else ""
    runner_status = clean(graph.get("runner_entity_status")).upper() if graph else "UNMATCHED"
    race_status = clean(id2.get("field_composition_status")).upper()
    ambiguous = any(clean(row.get("resolution_action")).upper() == "AMBIGUOUS_BLOCK" for row in conflicts)
    if ambiguous:
        reasons.append("runner graph ambiguity")
    if not physics_valid:
        reasons.append("payload physics failed")
    if physics_grade in {"BROKEN", "WEAK", ""}:
        reasons.append("physics grade blocks trust")
    if runner_status in {"AMBIGUOUS", "UNSAFE", "UNMATCHED", ""}:
        reasons.append("runner entity unresolved")
    if race_status not in {"TRUSTED", "LIKELY"}:
        reasons.append("race identity unresolved")
    if clean(id2.get("suppressed_duplicate")).upper() == "YES":
        reasons.append("unresolved duplicate")
    score = round(id2_conf * 0.16 + runner_conf * 0.34 + field_conf * 0.18 + physics_conf * 0.2 + reconstruction_conf * 0.12)
    if ambiguous:
        score = min(score, 50)
    if not physics_valid:
        score = min(score, 45)
    trusted_runner = "YES" if runner_status == "TRUSTED" and runner_conf >= 90 and not ambiguous else "PARTIAL" if runner_status == "LIKELY" and runner_conf >= 84 and not ambiguous else "NO"
    trusted_race = "YES" if race_status == "TRUSTED" and field_conf >= 88 else "PARTIAL" if race_status == "LIKELY" and field_conf >= 76 else "NO"
    modelling = "NO"
    execution = "NO"
    if trusted_runner == "YES" and trusted_race in {"YES", "PARTIAL"} and physics_valid and physics_grade in {"ELITE", "GOOD", "PARTIAL"} and score >= 84 and not ambiguous:
        modelling = "YES"
    elif trusted_runner == "PARTIAL" and trusted_race == "YES" and physics_valid and physics_grade in {"ELITE", "GOOD"} and score >= 78 and not ambiguous:
        modelling = "PARTIAL"
        reasons.append("runner identity likely only")
    if modelling == "YES" and trusted_runner == "YES" and trusted_race == "YES" and physics_grade in {"ELITE", "GOOD"} and score >= 92:
        execution = "YES"
    elif modelling != "NO":
        reasons.append("execution withheld by stricter identity v3 gate")
    if modelling == "YES" and execution == "YES":
        status = "TRUSTED"
    elif modelling == "YES":
        status = "LIKELY"
    elif modelling == "PARTIAL":
        status = "PARTIAL"
    elif ambiguous:
        status = "AMBIGUOUS"
    elif score > 0:
        status = "UNSAFE"
    else:
        status = "UNMATCHED"
    return max(0, min(100, score)), status, trusted_runner, trusted_race, modelling, execution, "; ".join(dict.fromkeys(reasons)) if reasons else "runner graph, race identity and physics gates passed"


def main() -> None:
    graph_by_lineage = best_by_lineage(read_csv(GRAPH), "runner_entity_confidence")
    physics_by_lineage = {lineage(row): row for row in read_csv(PHYSICS)}
    conflicts_by_lineage = conflict_lookup()
    rows: list[dict[str, object]] = []
    for id2 in read_csv(IDENTITY_V2):
        line = lineage(id2)
        graph = graph_by_lineage.get(line)
        physics = physics_by_lineage.get(line)
        conflicts = conflicts_by_lineage.get(line, [])
        score, status, trusted_runner, trusted_race, modelling, execution, reason = decide(id2, graph, physics, conflicts)
        rows.append({
            "source_lineage": line,
            "source_file": clean(id2.get("source_file")),
            "source_row_id": clean(id2.get("source_row_id")),
            "race_date": clean(id2.get("matched_race_date")) or clean(id2.get("race_date")),
            "track": clean(id2.get("matched_track")) or clean(id2.get("track")),
            "race_no": clean(id2.get("matched_race_no")) or clean(id2.get("race_no")),
            "distance": clean(id2.get("matched_distance")) or clean(id2.get("distance")),
            "horse": clean(id2.get("matched_horse")) or clean(id2.get("horse")),
            "horse_key": clean(id2.get("matched_horse_key")) or clean(id2.get("horse_key")),
            "edgeiq_runner": clean(graph.get("edgeiq_runner")) if graph else "",
            "edgeiq_runner_key": clean(graph.get("edgeiq_runner_key")) if graph else "",
            "identity_v2_confidence": clean(id2.get("identity_v2_confidence")),
            "identity_v2_status": clean(id2.get("identity_v2_status")),
            "runner_entity_confidence": clean(graph.get("runner_entity_confidence")) if graph else "0",
            "runner_entity_status": clean(graph.get("runner_entity_status")) if graph else "UNMATCHED",
            "runner_resolution_method": clean(graph.get("runner_resolution_method")) if graph else "PARTIAL_GRAPH",
            "race_identity_status": clean(id2.get("field_composition_status")),
            "field_composition_confidence": clean(id2.get("field_composition_confidence")),
            "physics_valid": clean(physics.get("physics_valid")) if physics else "NO",
            "physics_grade": clean(physics.get("physics_grade")) if physics else "",
            "physics_confidence": clean(physics.get("physics_confidence")) if physics else "0",
            "payload_structure_type": clean(physics.get("payload_structure_type")) if physics else "",
            "reconstruction_confidence": clean(physics.get("reconstruction_confidence")) if physics else "0",
            "conflict_status": "AMBIGUOUS" if any(clean(row.get("resolution_action")).upper() == "AMBIGUOUS_BLOCK" for row in conflicts) else "CLEAR" if not conflicts else "SUPPRESSED_LOWER_CANDIDATES",
            "identity_v3_confidence": score,
            "identity_v3_status": status,
            "trusted_runner_identity": trusted_runner,
            "trusted_race_identity": trusted_race,
            "trusted_modelling_identity": modelling,
            "trusted_execution_identity": execution,
            "identity_v3_reason": reason,
        })
    counts = Counter(str(row["identity_v3_status"]) for row in rows)
    methods = Counter(str(row["runner_resolution_method"]) for row in rows)
    summary = [
        {"metric": "identity_rows", "value": len(rows)},
        {"metric": "trusted_runner_identities", "value": sum(1 for row in rows if row["trusted_runner_identity"] == "YES")},
        {"metric": "partial_runner_identities", "value": sum(1 for row in rows if row["trusted_runner_identity"] == "PARTIAL")},
        {"metric": "trusted_race_identities", "value": sum(1 for row in rows if row["trusted_race_identity"] == "YES")},
        {"metric": "trusted_modelling_rows", "value": sum(1 for row in rows if row["trusted_modelling_identity"] == "YES")},
        {"metric": "partial_modelling_rows", "value": sum(1 for row in rows if row["trusted_modelling_identity"] == "PARTIAL")},
        {"metric": "trusted_execution_rows", "value": sum(1 for row in rows if row["trusted_execution_identity"] == "YES")},
        {"metric": "ambiguous_rows", "value": counts.get("AMBIGUOUS", 0)},
        {"metric": "unsafe_rows", "value": counts.get("UNSAFE", 0)},
        {"metric": "unmatched_rows", "value": counts.get("UNMATCHED", 0)},
    ]
    summary.extend({"metric": f"status_{key.lower()}", "value": value} for key, value in sorted(counts.items()))
    summary.extend({"metric": f"method_{key.lower()}", "value": value} for key, value in sorted(methods.items()))
    write_csv(OUT, rows, FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    print("=" * 90)
    print("EDGEIQ SECTIONAL IDENTITY ENGINE V3")
    print("=" * 90)
    print("ROWS:", len(rows))
    print("TRUSTED MODELLING:", summary[4]["value"])
    print("TRUSTED EXECUTION:", summary[6]["value"])
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
