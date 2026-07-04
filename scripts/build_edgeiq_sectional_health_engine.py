from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RECON = DATA / "edgeiq_sectional_master_reconciliation_v1.csv"
CONFLICTS = DATA / "edgeiq_sectional_duplicate_conflicts_v1.csv"
PAYLOAD_RECON = DATA / "edgeiq_sectional_payload_reconstruction_v1.csv"
PAYLOAD_SUMMARY = DATA / "edgeiq_sectional_payload_reconstruction_summary_v1.csv"
PHYSICS = DATA / "edgeiq_sectional_physics_validation_v1.csv"
PHYSICS_SUMMARY = DATA / "edgeiq_sectional_physics_summary_v1.csv"
TRUSTED = DATA / "edgeiq_trusted_sectional_universe.csv"
IDENTITY_V2_SUMMARY = DATA / "edgeiq_sectional_identity_summary_v2.csv"
IDENTITY_V3 = DATA / "edgeiq_sectional_identity_engine_v3.csv"
IDENTITY_V3_SUMMARY = DATA / "edgeiq_sectional_identity_summary_v3.csv"
RUNNER_GRAPH = DATA / "edgeiq_runner_entity_graph_v1.csv"
RUNNER_GRAPH_SUMMARY = DATA / "edgeiq_runner_entity_graph_summary_v1.csv"
RUNNER_CONFLICTS = DATA / "edgeiq_runner_conflict_resolution_v1.csv"
FIELD_MATCH_SUMMARY = DATA / "edgeiq_sectional_field_composition_summary_v1.csv"
OUT = DATA / "edgeiq_sectional_health_engine.csv"
SUMMARY = DATA / "edgeiq_sectional_health_summary.csv"

FIELDS = ["metric", "category", "value", "status", "notes"]
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


def summary_value(rows: list[dict[str, str]], metric: str) -> str:
    return clean(next((row.get("value") for row in rows if clean(row.get("metric")) == metric), ""))


def as_int(value: object) -> int:
    try:
        return int(float(clean(value)))
    except ValueError:
        return 0


def row(metric: str, category: str, value: object, ok_when_positive: bool, notes: str) -> dict[str, object]:
    numeric = as_int(value)
    status = "OK" if (numeric > 0 if ok_when_positive else numeric == 0) else "WARN"
    return {"metric": metric, "category": category, "value": value, "status": status, "notes": notes}


def main() -> None:
    recon = read_csv(RECON)
    conflicts = read_csv(CONFLICTS)
    payload_recon = read_csv(PAYLOAD_RECON)
    payload_summary = read_csv(PAYLOAD_SUMMARY)
    physics = read_csv(PHYSICS)
    physics_summary = read_csv(PHYSICS_SUMMARY)
    trusted = read_csv(TRUSTED)
    identity_v2_summary = read_csv(IDENTITY_V2_SUMMARY)
    identity_v3 = read_csv(IDENTITY_V3)
    identity_v3_summary = read_csv(IDENTITY_V3_SUMMARY)
    graph = read_csv(RUNNER_GRAPH)
    graph_summary = read_csv(RUNNER_GRAPH_SUMMARY)
    runner_conflicts = read_csv(RUNNER_CONFLICTS)
    field_match_summary = read_csv(FIELD_MATCH_SUMMARY)

    payload_counts = Counter(clean(item.get("payload_structure_type")) or "UNKNOWN" for item in payload_recon)
    physics_counts = Counter(clean(item.get("physics_grade")) or "UNKNOWN" for item in physics)
    graph_counts = Counter(clean(item.get("runner_entity_status")) or "UNKNOWN" for item in graph)
    v3_counts = Counter(clean(item.get("identity_v3_status")) or "UNKNOWN" for item in identity_v3)
    method_counts = Counter(clean(item.get("runner_resolution_method")) or "UNKNOWN" for item in graph)
    trusted_rows = [item for item in trusted if clean(item.get("trusted_for_modelling")).upper() == "YES"]
    execution_rows = [item for item in trusted if clean(item.get("trusted_for_execution")).upper() == "YES"]

    rows = [
        {"metric": "total_sectional_rows", "category": "volume", "value": len(recon), "status": "OK", "notes": "sectional rows entering reconciliation"},
        row("duplicate_conflicts", "conflict", len(conflicts), False, "master duplicate conflicts"),
        row("reconstructed_rows", "reconstruction", summary_value(payload_summary, "reconstructed_rows"), True, "payloads reconstructed without invented splits"),
        row("physics_valid_rows", "physics", summary_value(physics_summary, "physics_valid_rows"), True, "payloads passing physics validation"),
        row("trusted_runner_identities", "runner_entity", summary_value(identity_v3_summary, "trusted_runner_identities"), True, "runner entities trusted by graph v3"),
        row("ambiguous_runners", "runner_entity", summary_value(identity_v3_summary, "ambiguous_rows"), False, "ambiguous runners blocking trust"),
        row("unresolved_conflicts", "runner_entity", len(runner_conflicts), False, "runner graph conflict rows"),
        row("graph_match_success_pct", "runner_entity", summary_value(graph_summary, "graph_match_success_pct"), True, "trusted/likely graph match success percentage"),
        row("trusted_modelling_rows", "trust", summary_value(identity_v3_summary, "trusted_modelling_rows"), True, "identity v3 rows trusted for modelling"),
        row("trusted_execution_rows", "trust", len(execution_rows), True, "strict execution-safe trusted sectionals"),
        row("trusted_sectional_universe_rows", "trust", len(trusted), True, "rows emitted to trusted sectional universe"),
        row("field_composition_matched_races", "composition", as_int(summary_value(field_match_summary, "best_trusted")) + as_int(summary_value(field_match_summary, "best_likely")), True, "trusted/likely field composition race matches"),
        row("identity_v2_trusted_or_likely", "identity", summary_value(identity_v2_summary, "v2_trusted_or_likely"), True, "identity v2 trusted/likely rows"),
        row("identity_v3_trusted_or_likely", "identity", as_int(summary_value(identity_v3_summary, "trusted_modelling_rows")) + as_int(summary_value(identity_v3_summary, "partial_modelling_rows")), True, "identity v3 modelling-safe rows"),
    ]
    for key, value in sorted(payload_counts.items()):
        rows.append({"metric": f"structure_{key.lower()}", "category": "structure", "value": value, "status": "OK" if key not in {"BROKEN", "UNKNOWN"} else "WARN", "notes": "payload structure distribution"})
    for key, value in sorted(physics_counts.items()):
        rows.append({"metric": f"physics_{key.lower()}", "category": "physics", "value": value, "status": "OK" if key in {"ELITE", "GOOD"} else "WARN", "notes": "physics grade distribution"})
    for key, value in sorted(graph_counts.items()):
        rows.append({"metric": f"runner_graph_{key.lower()}", "category": "runner_entity", "value": value, "status": "OK" if key in {"TRUSTED", "LIKELY"} else "WARN", "notes": "runner graph status distribution"})
    for key, value in sorted(v3_counts.items()):
        rows.append({"metric": f"identity_v3_{key.lower()}", "category": "identity_v3", "value": value, "status": "OK" if key in {"TRUSTED", "LIKELY"} else "WARN", "notes": "identity v3 status distribution"})
    for key, value in sorted(method_counts.items()):
        rows.append({"metric": f"runner_method_{key.lower()}", "category": "runner_method", "value": value, "status": "OK" if key in {"EXACT_GRAPH", "HYBRID_GRAPH", "FIELD_GRAPH"} else "WARN", "notes": "runner graph method distribution"})
    summary = [{"metric": item["metric"], "value": item["value"]} for item in rows]
    write_csv(OUT, rows, FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    print("=" * 90)
    print("EDGEIQ SECTIONAL HEALTH ENGINE")
    print("=" * 90)
    print("TRUSTED RUNNERS:", summary_value(identity_v3_summary, "trusted_runner_identities"))
    print("AMBIGUOUS:", summary_value(identity_v3_summary, "ambiguous_rows"))
    print("TRUSTED MODELLING:", summary_value(identity_v3_summary, "trusted_modelling_rows"))
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
