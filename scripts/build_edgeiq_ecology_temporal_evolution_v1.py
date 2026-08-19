from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from edgeiq_memory_safe_io import safe_read_csv, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

IN_MEMORY = DATA / "edgeiq_ecology_longitudinal_memory_v1.csv"
IN_STABILITY = DATA / "edgeiq_ecology_stability_index_v1.csv"
IN_MUTATIONS = DATA / "edgeiq_ecology_mutation_events_v1.csv"
IN_TRACK_STATE = DATA / "edgeiq_transition_track_ecology_state_v1.csv"
IN_DRIFT = DATA / "edgeiq_transition_ecology_drift_v1.csv"
IN_PERSISTENCE = DATA / "edgeiq_transition_persistence_memory_v1.csv"

OUT_EVOLUTION = DATA / "edgeiq_ecology_temporal_evolution_v1.csv"
OUT_LIFECYCLE = DATA / "edgeiq_ecology_lifecycle_phase_v1.csv"
OUT_ALERTS = DATA / "edgeiq_ecology_evolution_alerts_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_ecology_evolution_summary_v1.csv"

ENGINE_VERSION = "EDGEIQ_ECOLOGY_TEMPORAL_EVOLUTION_ENGINE_V1"
BOUNDARY = "OFFLINE_RESEARCH_ONLY"

EVOLUTION_FIELDS = [
    "track",
    "current_ecology_state",
    "current_climate",
    "stability_score",
    "drift_risk",
    "mutation_risk",
    "dominant_transition_shape",
    "lifecycle_phase",
    "evolution_confidence",
    "evidence_grade",
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


def evidence_grade(observed_profiles: int, shape_count: int, stability_score: float) -> str:
    if observed_profiles >= 20 and shape_count <= 2 and stability_score >= 85:
        return "A"
    if observed_profiles >= 9 and stability_score >= 70:
        return "B"
    if observed_profiles >= 5:
        return "C"
    if observed_profiles >= 2:
        return "D"
    return "F"


def confidence_from(grade: str, stability_score: float, drift_risk: str, mutation_risk: str, shape_count: int) -> str:
    score = stability_score
    if grade == "A":
        score += 8
    elif grade == "B":
        score += 2
    elif grade in {"D", "F"}:
        score -= 18
    if drift_risk == "LOW":
        score += 5
    elif drift_risk == "HIGH":
        score -= 20
    elif drift_risk == "MEDIUM":
        score -= 8
    if "LOW" in mutation_risk:
        score += 5
    elif "ELEVATED" in mutation_risk:
        score -= 14
    elif "HIGH" in mutation_risk:
        score -= 24
    if shape_count >= 4:
        score -= 8
    score = max(0, min(100, score))
    if score >= 85:
        return "HIGH"
    if score >= 65:
        return "MEDIUM"
    if score >= 40:
        return "LOW"
    return "INSUFFICIENT"


def lifecycle_phase(state: str, climate: str, stability_score: float, drift_risk: str, mutation_risk: str, observed_profiles: int, shape_count: int) -> str:
    if observed_profiles < 3:
        return "INSUFFICIENT_EVIDENCE"
    if "COLLAPSE" in state or stability_score < 25:
        return "COLLAPSE"
    if "HIGH" in mutation_risk or ("ELEVATED" in mutation_risk and shape_count >= 5):
        return "MUTATION"
    if drift_risk == "HIGH" or (shape_count >= 5 and stability_score < 55):
        return "FRAGMENTATION"
    if stability_score >= 90 and drift_risk == "LOW" and "LOW" in mutation_risk:
        return "PERSISTENCE"
    if stability_score >= 70 and drift_risk in {"LOW", "MEDIUM"}:
        if "EMERGING" in climate or "EMERGING" in state:
            return "STABILISATION"
        return "PERSISTENCE"
    if stability_score >= 50:
        return "EMERGENCE"
    return "FORMATION"


def action_for(phase: str, track: str, mutation_risk: str, evidence: str) -> str:
    if phase == "PERSISTENCE":
        return f"Keep {track} under longitudinal observation; use as a research anchor only."
    if phase == "STABILISATION":
        return f"Increase repeat observations for {track} and monitor whether the dominant shape holds."
    if phase == "MUTATION":
        return f"Prioritise mutation follow-up for {track}; separate stable and emerging transition shapes."
    if phase == "FRAGMENTATION":
        return f"Audit source/shape mix for {track}; ecology may be splitting into competing profiles."
    if phase == "COLLAPSE":
        return f"Quarantine {track} from research promotion until stability recovers."
    if phase == "INSUFFICIENT_EVIDENCE" or evidence in {"D", "F"}:
        return f"Collect more evidence for {track}; confidence is not sufficient for lifecycle claims."
    return f"Track {track} through continued offline ecology memory accumulation."


def build_rows() -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    memory = by_track(safe_read_csv(IN_MEMORY))
    stability = by_track(safe_read_csv(IN_STABILITY))
    mutations = by_track(safe_read_csv(IN_MUTATIONS))
    states = by_track(safe_read_csv(IN_TRACK_STATE))
    drift_rows = safe_read_csv(IN_DRIFT)
    persistence_rows = safe_read_csv(IN_PERSISTENCE)
    persistence_by_shape = {upper(row.get("transition_shape")): row for row in persistence_rows}

    tracks = sorted(set(memory) | set(stability) | set(states) | {upper(row.get("track")) for row in drift_rows if clean(row.get("track"))})
    timestamp = utc_now()
    evolution_rows: list[dict[str, str]] = []
    alert_rows: list[dict[str, str]] = []

    for track_key in tracks:
        memory_row = memory.get(track_key, {})
        stability_row = stability.get(track_key, {})
        state_row = states.get(track_key, {})
        mutation_row = mutations.get(track_key, {})

        track = clean(memory_row.get("track")) or clean(stability_row.get("track")) or clean(state_row.get("track")) or track_key
        ecology_state = clean(memory_row.get("ecology_state")) or clean(state_row.get("ecology_state")) or "UNKNOWN_ECOLOGY_STATE"
        climate = clean(memory_row.get("ecology_climate")) or clean(stability_row.get("climate")) or "UNKNOWN_CLIMATE"
        stability_score = parse_float(memory_row.get("ecology_stability_score") or stability_row.get("stability_score"))
        drift_risk = upper(stability_row.get("drift_risk") or state_row.get("drift_risk")) or "UNKNOWN"
        mutation_risk = clean(memory_row.get("mutation_risk")) or clean(mutation_row.get("mutation_risk")) or "LOW_MUTATION_RISK"
        dominant_shape = clean(memory_row.get("dominant_transition_shape")) or clean(stability_row.get("dominant_transition_shape")) or clean(state_row.get("dominant_transition_shape")) or "UNKNOWN_SHAPE"
        shape_count = parse_int(stability_row.get("shape_count") or state_row.get("transition_shape_count"))
        observed_profiles = parse_int(state_row.get("observed_transition_profiles"))
        if not observed_profiles:
            observed_profiles = sum(parse_int(row.get("observed_count")) for row in drift_rows if upper(row.get("track")) == track_key)
        grade = evidence_grade(observed_profiles, shape_count, stability_score)
        phase = lifecycle_phase(ecology_state, climate, stability_score, drift_risk, upper(mutation_risk), observed_profiles, shape_count)
        confidence = confidence_from(grade, stability_score, drift_risk, upper(mutation_risk), shape_count)

        persistence = persistence_by_shape.get(upper(dominant_shape), {})
        action = action_for(phase, track, mutation_risk, grade)
        if persistence:
            action = f"{action} Dominant shape memory strength: {clean(persistence.get('memory_strength')) or 'UNKNOWN'}."

        row = {
            "track": track,
            "current_ecology_state": ecology_state,
            "current_climate": climate,
            "stability_score": f"{stability_score:.2f}",
            "drift_risk": drift_risk,
            "mutation_risk": mutation_risk,
            "dominant_transition_shape": dominant_shape,
            "lifecycle_phase": phase,
            "evolution_confidence": confidence,
            "evidence_grade": grade,
            "recommended_research_action": action,
            "research_boundary": BOUNDARY,
            "live_modelling_yes": "0",
            "live_execution_yes": "0",
            "engine_version": ENGINE_VERSION,
            "timestamp_utc": timestamp,
        }
        evolution_rows.append(row)
        if phase in {"MUTATION", "FRAGMENTATION", "COLLAPSE"} or "ELEVATED" in upper(mutation_risk) or grade in {"D", "F"}:
            alert_rows.append(row)

    lifecycle_rows = sorted(evolution_rows, key=lambda row: (row["lifecycle_phase"], row["track"]))
    evolution_rows = sorted(evolution_rows, key=lambda row: (-parse_float(row["stability_score"]), row["track"]))
    return evolution_rows, lifecycle_rows, alert_rows


def build_engine() -> None:
    evolution_rows, lifecycle_rows, alert_rows = build_rows()
    phase_counts: dict[str, int] = {}
    confidence_counts: dict[str, int] = {}
    grade_counts: dict[str, int] = {}
    for row in evolution_rows:
        phase_counts[row["lifecycle_phase"]] = phase_counts.get(row["lifecycle_phase"], 0) + 1
        confidence_counts[row["evolution_confidence"]] = confidence_counts.get(row["evolution_confidence"], 0) + 1
        grade_counts[row["evidence_grade"]] = grade_counts.get(row["evidence_grade"], 0) + 1

    summary_rows = [
        {"metric": "evolution_rows", "value": str(len(evolution_rows))},
        {"metric": "lifecycle_rows", "value": str(len(lifecycle_rows))},
        {"metric": "alert_rows", "value": str(len(alert_rows))},
        {"metric": "persistence_tracks", "value": str(phase_counts.get("PERSISTENCE", 0))},
        {"metric": "stabilisation_tracks", "value": str(phase_counts.get("STABILISATION", 0))},
        {"metric": "emergence_tracks", "value": str(phase_counts.get("EMERGENCE", 0))},
        {"metric": "formation_tracks", "value": str(phase_counts.get("FORMATION", 0))},
        {"metric": "fragmentation_tracks", "value": str(phase_counts.get("FRAGMENTATION", 0))},
        {"metric": "mutation_tracks", "value": str(phase_counts.get("MUTATION", 0))},
        {"metric": "collapse_tracks", "value": str(phase_counts.get("COLLAPSE", 0))},
        {"metric": "insufficient_evidence_tracks", "value": str(phase_counts.get("INSUFFICIENT_EVIDENCE", 0))},
        {"metric": "high_confidence_tracks", "value": str(confidence_counts.get("HIGH", 0))},
        {"metric": "medium_confidence_tracks", "value": str(confidence_counts.get("MEDIUM", 0))},
        {"metric": "low_confidence_tracks", "value": str(confidence_counts.get("LOW", 0))},
        {"metric": "grade_a_tracks", "value": str(grade_counts.get("A", 0))},
        {"metric": "grade_b_tracks", "value": str(grade_counts.get("B", 0))},
        {"metric": "grade_c_tracks", "value": str(grade_counts.get("C", 0))},
        {"metric": "research_boundary", "value": BOUNDARY},
        {"metric": "live_modelling_yes", "value": "0"},
        {"metric": "live_execution_yes", "value": "0"},
        {"metric": "engine_version", "value": ENGINE_VERSION},
    ]

    write_csv_atomic(OUT_EVOLUTION, evolution_rows, EVOLUTION_FIELDS)
    write_csv_atomic(OUT_LIFECYCLE, lifecycle_rows, EVOLUTION_FIELDS)
    write_csv_atomic(OUT_ALERTS, alert_rows, EVOLUTION_FIELDS)
    write_csv_atomic(OUT_SUMMARY, summary_rows, SUMMARY_FIELDS)

    print(f"Ecology temporal evolution rows: {len(evolution_rows)}")
    print(f"Lifecycle rows: {len(lifecycle_rows)}")
    print(f"Alert rows: {len(alert_rows)}")
    print("Live modelling: 0")
    print("Live execution: 0")


if __name__ == "__main__":
    build_engine()
