from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from edgeiq_memory_safe_io import safe_read_csv, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

IN_EVOLUTION = DATA / "edgeiq_ecology_temporal_evolution_v1.csv"
IN_LIFECYCLE = DATA / "edgeiq_ecology_lifecycle_phase_v1.csv"
IN_ALERTS = DATA / "edgeiq_ecology_evolution_alerts_v1.csv"
IN_MEMORY = DATA / "edgeiq_ecology_longitudinal_memory_v1.csv"
IN_PERSISTENCE = DATA / "edgeiq_transition_persistence_memory_v1.csv"
IN_COMMAND_FEED = DATA / "edgeiq_research_command_feed_v1.csv"

OUT_EVIDENCE = DATA / "edgeiq_ecology_evidence_accumulation_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_ecology_evidence_summary_v1.csv"
OUT_PRIORITY = DATA / "edgeiq_ecology_research_priority_v1.csv"

ENGINE_VERSION = "EDGEIQ_ECOLOGY_EVIDENCE_ACCUMULATION_V1"
BOUNDARY = "OFFLINE_RESEARCH_ONLY"

EVIDENCE_FIELDS = [
    "priority_rank",
    "track",
    "ecology_state",
    "climate",
    "lifecycle_phase",
    "dominant_transition_shape",
    "stability_score",
    "drift_risk",
    "mutation_risk",
    "observed_transition_profiles",
    "shape_memory_strength",
    "evolution_confidence",
    "evidence_grade",
    "research_maturity_class",
    "research_priority_score",
    "recommended_research_action",
    "research_boundary",
    "live_modelling_yes",
    "live_execution_yes",
    "engine_version",
    "timestamp_utc",
]

SUMMARY_FIELDS = ["metric", "value"]


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


def parse_int(value: object) -> int:
    try:
        return int(float(clean(value).replace(",", "") or 0))
    except ValueError:
        return 0


def by_track(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {upper(row.get("track")): row for row in rows if clean(row.get("track"))}


def memory_by_shape(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {upper(row.get("transition_shape")): row for row in rows if clean(row.get("transition_shape"))}


def classify_maturity(row: dict[str, str], observed: int, memory_strength: str, has_alert: bool) -> str:
    phase = upper(row.get("lifecycle_phase"))
    mutation = upper(row.get("mutation_risk"))
    drift = upper(row.get("drift_risk"))
    confidence = upper(row.get("evolution_confidence"))
    stability = parse_float(row.get("stability_score"))

    if observed < 3:
        return "REJECTED_OR_INSUFFICIENT_EVIDENCE"
    if "ELEVATED" in mutation or "HIGH" in mutation or has_alert:
        return "MUTATION_WATCHLIST"
    if phase == "PERSISTENCE" and stability >= 90 and drift == "LOW" and confidence == "HIGH" and memory_strength in {"HIGH", "ELITE"}:
        return "CORE_LONGITUDINAL_STRUCTURE"
    if phase in {"PERSISTENCE", "STABILISATION"} and stability >= 70 and confidence in {"HIGH", "MEDIUM"}:
        return "HIGH_PRIORITY_RESEARCH_STRUCTURE"
    if phase in {"STABILISATION", "EMERGENCE", "FORMATION"} and stability >= 50:
        return "ACTIVE_OBSERVATION_STRUCTURE"
    if confidence in {"LOW", "INSUFFICIENT"}:
        return "LOW_CONFIDENCE_STRUCTURE"
    return "ACTIVE_OBSERVATION_STRUCTURE"


def priority_score(row: dict[str, str], observed: int, memory_strength: str, maturity: str) -> float:
    score = parse_float(row.get("stability_score")) * 0.55
    score += min(observed, 20) * 1.5
    if upper(row.get("drift_risk")) == "LOW":
        score += 10
    elif upper(row.get("drift_risk")) == "MEDIUM":
        score += 2
    else:
        score -= 12
    if "LOW" in upper(row.get("mutation_risk")):
        score += 8
    elif "ELEVATED" in upper(row.get("mutation_risk")):
        score -= 10
    elif "HIGH" in upper(row.get("mutation_risk")):
        score -= 18
    if memory_strength == "HIGH":
        score += 8
    elif memory_strength == "MEDIUM":
        score += 3
    if maturity == "CORE_LONGITUDINAL_STRUCTURE":
        score += 12
    elif maturity == "MUTATION_WATCHLIST":
        score -= 4
    elif maturity == "REJECTED_OR_INSUFFICIENT_EVIDENCE":
        score -= 25
    return round(max(0.0, min(100.0, score)), 2)


def action_for(maturity: str, track: str, lifecycle_action: str) -> str:
    if maturity == "CORE_LONGITUDINAL_STRUCTURE":
        return f"Keep {track} as the ecology research anchor; continue repeat observations only."
    if maturity == "HIGH_PRIORITY_RESEARCH_STRUCTURE":
        return f"Prioritise {track} for repeat ecology memory snapshots."
    if maturity == "MUTATION_WATCHLIST":
        return f"Watch {track} for ecology mutation; separate stable and emerging transition shapes before promotion."
    if maturity == "LOW_CONFIDENCE_STRUCTURE":
        return f"Collect more evidence for {track}; maturity confidence remains low."
    if maturity == "REJECTED_OR_INSUFFICIENT_EVIDENCE":
        return f"Do not promote {track}; evidence is insufficient."
    return lifecycle_action or f"Continue offline ecology observation for {track}."


def build_rows() -> list[dict[str, str]]:
    evolution = by_track(safe_read_csv(IN_EVOLUTION))
    lifecycle = by_track(safe_read_csv(IN_LIFECYCLE))
    alerts = by_track(safe_read_csv(IN_ALERTS))
    memory = by_track(safe_read_csv(IN_MEMORY))
    persistence = memory_by_shape(safe_read_csv(IN_PERSISTENCE))
    command_rows = safe_read_csv(IN_COMMAND_FEED)
    command_track_cards = {upper(row.get("card_title")).replace(" LIFECYCLE", ""): row for row in command_rows if upper(row.get("card_type")) == "TRACK_LIFECYCLE"}

    tracks = sorted(set(evolution) | set(lifecycle) | set(memory) | set(command_track_cards))
    timestamp = utc_now()
    rows: list[dict[str, str]] = []

    for track_key in tracks:
        evo = evolution.get(track_key, lifecycle.get(track_key, {}))
        mem = memory.get(track_key, {})
        dominant_shape = clean(evo.get("dominant_transition_shape")) or clean(mem.get("dominant_transition_shape")) or "UNKNOWN_SHAPE"
        persistence_row = persistence.get(upper(dominant_shape), {})
        observed = parse_int(mem.get("observed_transition_profiles"))
        if not observed:
            observed = parse_int(command_track_cards.get(track_key, {}).get("headline_value"))
        if not observed:
            observed = 0
        memory_strength = upper(persistence_row.get("memory_strength")) or "UNKNOWN"
        maturity = classify_maturity(evo, observed, memory_strength, track_key in alerts)
        score = priority_score(evo, observed, memory_strength, maturity)
        track = clean(evo.get("track")) or clean(mem.get("track")) or track_key
        rows.append(
            {
                "priority_rank": "0",
                "track": track,
                "ecology_state": clean(evo.get("current_ecology_state")) or clean(mem.get("ecology_state")),
                "climate": clean(evo.get("current_climate")) or clean(mem.get("ecology_climate")),
                "lifecycle_phase": clean(evo.get("lifecycle_phase")),
                "dominant_transition_shape": dominant_shape,
                "stability_score": f"{parse_float(evo.get('stability_score')):.2f}",
                "drift_risk": clean(evo.get("drift_risk")),
                "mutation_risk": clean(evo.get("mutation_risk")),
                "observed_transition_profiles": str(observed),
                "shape_memory_strength": memory_strength,
                "evolution_confidence": clean(evo.get("evolution_confidence")),
                "evidence_grade": clean(evo.get("evidence_grade")),
                "research_maturity_class": maturity,
                "research_priority_score": f"{score:.2f}",
                "recommended_research_action": action_for(maturity, track, clean(evo.get("recommended_research_action"))),
                "research_boundary": BOUNDARY,
                "live_modelling_yes": "0",
                "live_execution_yes": "0",
                "engine_version": ENGINE_VERSION,
                "timestamp_utc": timestamp,
            }
        )

    rows.sort(key=lambda row: (-parse_float(row["research_priority_score"]), row["track"]))
    for index, row in enumerate(rows, start=1):
        row["priority_rank"] = str(index)
    return rows


def build_engine() -> None:
    rows = build_rows()
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["research_maturity_class"]] = counts.get(row["research_maturity_class"], 0) + 1
    top = rows[0] if rows else {}
    mutation = next((row for row in rows if row["research_maturity_class"] == "MUTATION_WATCHLIST"), {})
    summary = [
        {"metric": "evidence_rows", "value": str(len(rows))},
        {"metric": "core_longitudinal_structures", "value": str(counts.get("CORE_LONGITUDINAL_STRUCTURE", 0))},
        {"metric": "high_priority_research_structures", "value": str(counts.get("HIGH_PRIORITY_RESEARCH_STRUCTURE", 0))},
        {"metric": "active_observation_structures", "value": str(counts.get("ACTIVE_OBSERVATION_STRUCTURE", 0))},
        {"metric": "low_confidence_structures", "value": str(counts.get("LOW_CONFIDENCE_STRUCTURE", 0))},
        {"metric": "mutation_watchlist_structures", "value": str(counts.get("MUTATION_WATCHLIST", 0))},
        {"metric": "rejected_or_insufficient_evidence", "value": str(counts.get("REJECTED_OR_INSUFFICIENT_EVIDENCE", 0))},
        {"metric": "top_research_structure", "value": clean(top.get("track"))},
        {"metric": "top_research_maturity", "value": clean(top.get("research_maturity_class"))},
        {"metric": "top_research_score", "value": clean(top.get("research_priority_score"))},
        {"metric": "mutation_watchlist_top", "value": clean(mutation.get("track"))},
        {"metric": "research_boundary", "value": BOUNDARY},
        {"metric": "live_modelling_yes", "value": "0"},
        {"metric": "live_execution_yes", "value": "0"},
        {"metric": "engine_version", "value": ENGINE_VERSION},
    ]
    priority_rows = [row for row in rows if row["research_maturity_class"] in {"CORE_LONGITUDINAL_STRUCTURE", "HIGH_PRIORITY_RESEARCH_STRUCTURE", "MUTATION_WATCHLIST", "ACTIVE_OBSERVATION_STRUCTURE"}]

    write_csv_atomic(OUT_EVIDENCE, rows, EVIDENCE_FIELDS)
    write_csv_atomic(OUT_SUMMARY, summary, SUMMARY_FIELDS)
    write_csv_atomic(OUT_PRIORITY, priority_rows, EVIDENCE_FIELDS)

    print(f"Ecology evidence rows: {len(rows)}")
    print(f"Priority rows: {len(priority_rows)}")
    print(f"Top structure: {clean(top.get('track'))}")
    print("Live modelling: 0")
    print("Live execution: 0")


if __name__ == "__main__":
    build_engine()
