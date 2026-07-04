from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from edgeiq_memory_safe_io import safe_read_csv, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

IN_GOVERNANCE = DATA / "edgeiq_ecology_governance_gate_v1.csv"
IN_EVIDENCE = DATA / "edgeiq_ecology_evidence_accumulation_v1.csv"
IN_EVOLUTION = DATA / "edgeiq_ecology_temporal_evolution_v1.csv"
IN_MEMORY = DATA / "edgeiq_ecology_longitudinal_memory_v1.csv"
IN_MUTATION = DATA / "edgeiq_ecology_mutation_events_v1.csv"
IN_TRACK_STATE = DATA / "edgeiq_transition_track_ecology_state_v1.csv"
IN_PERSISTENCE = DATA / "edgeiq_transition_persistence_memory_v1.csv"

OUT_LEDGER = DATA / "edgeiq_ecology_research_ledger_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_ecology_research_ledger_summary_v1.csv"
OUT_LINEAGE = DATA / "edgeiq_ecology_research_lineage_v1.csv"

ENGINE_VERSION = "EDGEIQ_ECOLOGY_RESEARCH_LEDGER_V1"
BOUNDARY = "OFFLINE_RESEARCH_ONLY"

LEDGER_FIELDS = [
    "structure_id",
    "track",
    "dominant_transition_shape",
    "lifecycle_phase",
    "ecology_climate",
    "evidence_score",
    "evidence_class",
    "governance_status",
    "mutation_risk",
    "drift_risk",
    "stability_score",
    "approved_for_research",
    "approved_for_modelling",
    "approved_for_execution",
    "research_boundary",
    "lineage_sources",
    "engine_version",
    "timestamp_utc",
]

SUMMARY_FIELDS = ["metric", "value"]

LINEAGE_FIELDS = [
    "structure_id",
    "track",
    "source_file",
    "source_present",
    "source_rows",
    "source_role",
    "lineage_status",
    "notes",
    "engine_version",
    "timestamp_utc",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(value: object) -> str:
    return str(value or "").strip()


def upper(value: object) -> str:
    return clean(value).upper()


def parse_float(value: object) -> float:
    try:
        return float(clean(value).replace(",", "") or 0)
    except ValueError:
        return 0.0


def by_track(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {upper(row.get("track")): row for row in rows if clean(row.get("track"))}


def by_shape(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    output: dict[str, dict[str, str]] = {}
    for row in rows:
        shape = upper(row.get("transition_shape")) or upper(row.get("dominant_transition_shape"))
        if shape and shape not in output:
            output[shape] = row
    return output


def structure_id(track: str, shape: str) -> str:
    safe_track = upper(track).replace(" ", "_") or "UNKNOWN_TRACK"
    safe_shape = upper(shape).replace(" ", "_") or "UNKNOWN_SHAPE"
    return f"ECOLOGY::{safe_track}::{safe_shape}"


def approved_for_research(status: str) -> str:
    if status == "APPROVED_CORE_RESEARCH":
        return "YES"
    if status == "APPROVED_ACTIVE_RESEARCH":
        return "YES"
    if status == "WATCHLIST_ONLY":
        return "WATCHLIST"
    return "NO"


def lineage_sources_for(track_key: str, shape_key: str, sources: dict[str, dict[str, dict[str, str]]]) -> list[str]:
    present: list[str] = []
    for label, rows in sources.items():
        if track_key in rows or shape_key in rows:
            present.append(label)
    return present


def source_count(track_key: str, shape_key: str, rows: dict[str, dict[str, str]]) -> int:
    count = 0
    if track_key in rows:
        count += 1
    if shape_key and shape_key in rows and shape_key != track_key:
        count += 1
    return count


def build_ledger() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    governance = by_track(safe_read_csv(IN_GOVERNANCE))
    evidence = by_track(safe_read_csv(IN_EVIDENCE))
    evolution = by_track(safe_read_csv(IN_EVOLUTION))
    memory = by_track(safe_read_csv(IN_MEMORY))
    mutation = by_track(safe_read_csv(IN_MUTATION))
    track_state = by_track(safe_read_csv(IN_TRACK_STATE))
    persistence = by_shape(safe_read_csv(IN_PERSISTENCE))
    timestamp = utc_now()

    track_sources = {
        "governance_gate": governance,
        "evidence_accumulation": evidence,
        "temporal_evolution": evolution,
        "longitudinal_memory": memory,
        "mutation_events": mutation,
        "track_ecology_state": track_state,
    }
    shape_sources = {"transition_persistence_memory": persistence}
    all_track_keys = sorted(set().union(*(set(rows) for rows in track_sources.values())))

    ledger_rows: list[dict[str, str]] = []
    lineage_rows: list[dict[str, str]] = []
    source_paths = {
        "governance_gate": IN_GOVERNANCE.name,
        "evidence_accumulation": IN_EVIDENCE.name,
        "temporal_evolution": IN_EVOLUTION.name,
        "longitudinal_memory": IN_MEMORY.name,
        "mutation_events": IN_MUTATION.name,
        "track_ecology_state": IN_TRACK_STATE.name,
        "transition_persistence_memory": IN_PERSISTENCE.name,
    }

    for track_key in all_track_keys:
        gate = governance.get(track_key, {})
        ev = evidence.get(track_key, {})
        evo = evolution.get(track_key, {})
        mem = memory.get(track_key, {})
        state = track_state.get(track_key, {})
        mut = mutation.get(track_key, {})

        track = clean(gate.get("track")) or clean(ev.get("track")) or clean(evo.get("track")) or clean(mem.get("track")) or track_key
        shape = clean(gate.get("dominant_transition_shape")) or clean(ev.get("dominant_transition_shape")) or clean(evo.get("dominant_transition_shape")) or clean(mem.get("dominant_transition_shape")) or "UNKNOWN_SHAPE"
        shape_key = upper(shape)
        persistence_row = persistence.get(shape_key, {})
        sid = structure_id(track, shape)
        status = upper(gate.get("governance_gate_status")) or "HOLD_FOR_MORE_EVIDENCE"
        sources = lineage_sources_for(track_key, shape_key, track_sources | shape_sources)

        ledger_rows.append(
            {
                "structure_id": sid,
                "track": track,
                "dominant_transition_shape": shape,
                "lifecycle_phase": clean(gate.get("lifecycle_phase")) or clean(ev.get("lifecycle_phase")) or clean(evo.get("lifecycle_phase")),
                "ecology_climate": clean(gate.get("climate")) or clean(evo.get("current_climate")) or clean(mem.get("ecology_climate")) or clean(state.get("ecology_climate")),
                "evidence_score": f"{parse_float(gate.get('research_priority_score') or ev.get('research_priority_score') or evo.get('stability_score')):.2f}",
                "evidence_class": clean(gate.get("research_maturity_class")) or clean(ev.get("research_maturity_class")) or clean(evo.get("evidence_grade")),
                "governance_status": status,
                "mutation_risk": clean(gate.get("mutation_risk")) or clean(ev.get("mutation_risk")) or clean(evo.get("mutation_risk")) or clean(mut.get("mutation_risk")),
                "drift_risk": clean(gate.get("drift_risk")) or clean(ev.get("drift_risk")) or clean(evo.get("drift_risk")),
                "stability_score": clean(gate.get("stability_score")) or clean(ev.get("stability_score")) or clean(evo.get("stability_score")),
                "approved_for_research": approved_for_research(status),
                "approved_for_modelling": "NO",
                "approved_for_execution": "NO",
                "research_boundary": BOUNDARY,
                "lineage_sources": "|".join(sources),
                "engine_version": ENGINE_VERSION,
                "timestamp_utc": timestamp,
            }
        )

        for label, rows in track_sources.items():
            present = track_key in rows
            lineage_rows.append(
                {
                    "structure_id": sid,
                    "track": track,
                    "source_file": source_paths[label],
                    "source_present": "YES" if present else "NO",
                    "source_rows": str(source_count(track_key, "", rows)),
                    "source_role": label,
                    "lineage_status": "PRESENT" if present else "MISSING",
                    "notes": "Track-level source evidence.",
                    "engine_version": ENGINE_VERSION,
                    "timestamp_utc": timestamp,
                }
            )
        for label, rows in shape_sources.items():
            present = shape_key in rows
            lineage_rows.append(
                {
                    "structure_id": sid,
                    "track": track,
                    "source_file": source_paths[label],
                    "source_present": "YES" if present else "NO",
                    "source_rows": str(1 if present else 0),
                    "source_role": label,
                    "lineage_status": "PRESENT" if present else "MISSING",
                    "notes": clean(persistence_row.get("memory_strength")) or "Shape-level source evidence.",
                    "engine_version": ENGINE_VERSION,
                    "timestamp_utc": timestamp,
                }
            )

    ledger_rows.sort(key=lambda row: (row["approved_for_research"] != "YES", row["approved_for_research"] != "WATCHLIST", -parse_float(row["evidence_score"]), row["track"]))
    return ledger_rows, lineage_rows


def build_engine() -> None:
    ledger_rows, lineage_rows = build_ledger()
    approved_research = sum(1 for row in ledger_rows if row["approved_for_research"] == "YES")
    watchlist = sum(1 for row in ledger_rows if row["approved_for_research"] == "WATCHLIST")
    blocked = sum(1 for row in ledger_rows if row["approved_for_research"] == "NO")
    source_present = sum(1 for row in lineage_rows if row["source_present"] == "YES")
    source_missing = sum(1 for row in lineage_rows if row["source_present"] == "NO")
    top = ledger_rows[0] if ledger_rows else {}
    summary = [
        {"metric": "ledger_rows", "value": str(len(ledger_rows))},
        {"metric": "lineage_rows", "value": str(len(lineage_rows))},
        {"metric": "approved_for_research_yes", "value": str(approved_research)},
        {"metric": "approved_for_research_watchlist", "value": str(watchlist)},
        {"metric": "approved_for_research_no", "value": str(blocked)},
        {"metric": "approved_for_modelling_yes", "value": "0"},
        {"metric": "approved_for_execution_yes", "value": "0"},
        {"metric": "lineage_sources_present", "value": str(source_present)},
        {"metric": "lineage_sources_missing", "value": str(source_missing)},
        {"metric": "top_ledger_track", "value": clean(top.get("track"))},
        {"metric": "top_ledger_status", "value": clean(top.get("governance_status"))},
        {"metric": "research_boundary", "value": BOUNDARY},
        {"metric": "live_modelling_yes", "value": "0"},
        {"metric": "live_execution_yes", "value": "0"},
        {"metric": "engine_version", "value": ENGINE_VERSION},
    ]

    write_csv_atomic(OUT_LEDGER, ledger_rows, LEDGER_FIELDS)
    write_csv_atomic(OUT_SUMMARY, summary, SUMMARY_FIELDS)
    write_csv_atomic(OUT_LINEAGE, lineage_rows, LINEAGE_FIELDS)

    print(f"Ecology ledger rows: {len(ledger_rows)}")
    print(f"Approved research rows: {approved_research}")
    print(f"Watchlist rows: {watchlist}")
    print("Live modelling: 0")
    print("Live execution: 0")


if __name__ == "__main__":
    build_engine()
