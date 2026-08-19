from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from edgeiq_memory_safe_io import safe_read_csv, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

IN_EVIDENCE = DATA / "edgeiq_ecology_evidence_accumulation_v1.csv"
IN_PRIORITY = DATA / "edgeiq_ecology_research_priority_v1.csv"
IN_EVIDENCE_SUMMARY = DATA / "edgeiq_ecology_evidence_summary_v1.csv"
IN_ALERTS = DATA / "edgeiq_ecology_evolution_alerts_v1.csv"
IN_COMMAND_FEED = DATA / "edgeiq_research_command_feed_v1.csv"

OUT_GATE = DATA / "edgeiq_ecology_governance_gate_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_ecology_governance_summary_v1.csv"
OUT_BLOCKED = DATA / "edgeiq_ecology_blocked_structures_v1.csv"
OUT_APPROVED = DATA / "edgeiq_ecology_approved_research_structures_v1.csv"

ENGINE_VERSION = "EDGEIQ_ECOLOGY_GOVERNANCE_GATE_V1"
BOUNDARY = "OFFLINE_RESEARCH_ONLY"

GATE_FIELDS = [
    "governance_rank",
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
    "governance_gate_status",
    "display_as_core_research",
    "watch_status",
    "hold_status",
    "blocked_from_modelling",
    "blocked_from_execution",
    "gate_confidence",
    "governance_reason",
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


def metric_map(path: Path) -> dict[str, str]:
    return {clean(row.get("metric")): clean(row.get("value")) for row in safe_read_csv(path) if clean(row.get("metric"))}


def by_track(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {upper(row.get("track")): row for row in rows if clean(row.get("track"))}


def gate_status(row: dict[str, str], alert_tracks: set[str]) -> tuple[str, str, str]:
    track = upper(row.get("track"))
    maturity = upper(row.get("research_maturity_class"))
    lifecycle = upper(row.get("lifecycle_phase"))
    confidence = upper(row.get("evolution_confidence"))
    drift = upper(row.get("drift_risk"))
    mutation = upper(row.get("mutation_risk"))
    stability = parse_float(row.get("stability_score"))
    observed = parse_int(row.get("observed_transition_profiles"))
    score = parse_float(row.get("research_priority_score"))

    if observed < 3:
        return (
            "REJECTED_INSUFFICIENT_EVIDENCE",
            "LOW",
            "Observed transition evidence is below the minimum governance threshold.",
        )

    if maturity == "CORE_LONGITUDINAL_STRUCTURE" and lifecycle == "PERSISTENCE" and stability >= 90 and drift == "LOW" and "LOW" in mutation and confidence == "HIGH":
        return (
            "APPROVED_CORE_RESEARCH",
            "HIGH",
            "Persistent climate, high stability, low drift, low mutation risk, and high evidence confidence.",
        )

    if track in alert_tracks or maturity == "MUTATION_WATCHLIST" or "ELEVATED" in mutation or "HIGH" in mutation:
        if observed >= 20 and stability >= 50:
            return (
                "WATCHLIST_ONLY",
                "MEDIUM" if confidence != "LOW" else "LOW",
                "Mutation or alert evidence requires watchlist isolation before any broader research display.",
            )
        return (
            "HOLD_FOR_MORE_EVIDENCE",
            "LOW",
            "Mutation evidence exists but supporting sample strength is not yet sufficient.",
        )

    if maturity in {"HIGH_PRIORITY_RESEARCH_STRUCTURE", "ACTIVE_OBSERVATION_STRUCTURE"} and score >= 60 and stability >= 60:
        return (
            "APPROVED_ACTIVE_RESEARCH",
            "MEDIUM" if confidence in {"HIGH", "MEDIUM"} else "LOW",
            "Evidence supports active offline observation but not core research display.",
        )

    if maturity in {"LOW_CONFIDENCE_STRUCTURE", "REJECTED_OR_INSUFFICIENT_EVIDENCE"} or confidence == "LOW":
        return (
            "HOLD_FOR_MORE_EVIDENCE",
            "LOW",
            "Confidence remains below the governance threshold for approved research display.",
        )

    return (
        "BLOCKED_FROM_MODELLING",
        "LOW",
        "Structure remains research-readable but is explicitly blocked from any modelling pathway.",
    )


def research_action(status: str, track: str) -> str:
    if status == "APPROVED_CORE_RESEARCH":
        return f"Display {track} as a core offline ecology research structure and continue repeat observation."
    if status == "APPROVED_ACTIVE_RESEARCH":
        return f"Display {track} as active offline ecology research and accumulate more lifecycle evidence."
    if status == "WATCHLIST_ONLY":
        return f"Keep {track} on the ecology watchlist and separate mutation evidence from stable climate evidence."
    if status == "HOLD_FOR_MORE_EVIDENCE":
        return f"Hold {track} until repeat evidence strengthens."
    if status == "REJECTED_INSUFFICIENT_EVIDENCE":
        return f"Do not display {track} as mature research; evidence is insufficient."
    return f"Block {track} from any modelling or execution pathway."


def build_rows() -> list[dict[str, str]]:
    evidence_rows = safe_read_csv(IN_EVIDENCE)
    priority_rows = by_track(safe_read_csv(IN_PRIORITY))
    alert_tracks = set(by_track(safe_read_csv(IN_ALERTS)))
    command_metrics = safe_read_csv(IN_COMMAND_FEED)
    command_tracks = {upper(row.get("card_title")).replace(" EVIDENCE", "") for row in command_metrics if upper(row.get("card_type")) == "ECOLOGY_EVIDENCE"}
    summary = metric_map(IN_EVIDENCE_SUMMARY)
    timestamp = utc_now()

    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for source in evidence_rows:
        track_key = upper(source.get("track"))
        if not track_key:
            continue
        seen.add(track_key)
        row = dict(source)
        if track_key in priority_rows:
            row.update({key: clean(value) or clean(row.get(key)) for key, value in priority_rows[track_key].items()})
        status, confidence, reason = gate_status(row, alert_tracks)
        track = clean(row.get("track")) or track_key
        rows.append(
            {
                "governance_rank": "0",
                "track": track,
                "ecology_state": clean(row.get("ecology_state")),
                "climate": clean(row.get("climate")),
                "lifecycle_phase": clean(row.get("lifecycle_phase")),
                "dominant_transition_shape": clean(row.get("dominant_transition_shape")),
                "stability_score": clean(row.get("stability_score")),
                "drift_risk": clean(row.get("drift_risk")),
                "mutation_risk": clean(row.get("mutation_risk")),
                "observed_transition_profiles": clean(row.get("observed_transition_profiles")),
                "shape_memory_strength": clean(row.get("shape_memory_strength")),
                "evolution_confidence": clean(row.get("evolution_confidence")),
                "evidence_grade": clean(row.get("evidence_grade")),
                "research_maturity_class": clean(row.get("research_maturity_class")),
                "research_priority_score": clean(row.get("research_priority_score")),
                "governance_gate_status": status,
                "display_as_core_research": "YES" if status == "APPROVED_CORE_RESEARCH" else "NO",
                "watch_status": "YES" if status == "WATCHLIST_ONLY" else "NO",
                "hold_status": "YES" if status in {"HOLD_FOR_MORE_EVIDENCE", "REJECTED_INSUFFICIENT_EVIDENCE"} else "NO",
                "blocked_from_modelling": "YES",
                "blocked_from_execution": "YES",
                "gate_confidence": confidence,
                "governance_reason": reason,
                "recommended_research_action": research_action(status, track),
                "research_boundary": BOUNDARY,
                "live_modelling_yes": "0",
                "live_execution_yes": "0",
                "engine_version": ENGINE_VERSION,
                "timestamp_utc": timestamp,
            }
        )

    for track_key in sorted(command_tracks - seen):
        if not track_key:
            continue
        rows.append(
            {
                "governance_rank": "0",
                "track": track_key,
                "ecology_state": "",
                "climate": "",
                "lifecycle_phase": "",
                "dominant_transition_shape": "",
                "stability_score": "",
                "drift_risk": "",
                "mutation_risk": "",
                "observed_transition_profiles": "0",
                "shape_memory_strength": "",
                "evolution_confidence": "",
                "evidence_grade": "",
                "research_maturity_class": clean(summary.get("top_research_maturity")),
                "research_priority_score": "0",
                "governance_gate_status": "HOLD_FOR_MORE_EVIDENCE",
                "display_as_core_research": "NO",
                "watch_status": "NO",
                "hold_status": "YES",
                "blocked_from_modelling": "YES",
                "blocked_from_execution": "YES",
                "gate_confidence": "LOW",
                "governance_reason": "Track appeared in the command feed but was not present in the evidence accumulation layer.",
                "recommended_research_action": f"Refresh ecology evidence before displaying {track_key}.",
                "research_boundary": BOUNDARY,
                "live_modelling_yes": "0",
                "live_execution_yes": "0",
                "engine_version": ENGINE_VERSION,
                "timestamp_utc": timestamp,
            }
        )

    status_rank = {
        "APPROVED_CORE_RESEARCH": 0,
        "APPROVED_ACTIVE_RESEARCH": 1,
        "WATCHLIST_ONLY": 2,
        "HOLD_FOR_MORE_EVIDENCE": 3,
        "BLOCKED_FROM_MODELLING": 4,
        "REJECTED_INSUFFICIENT_EVIDENCE": 5,
    }
    rows.sort(key=lambda item: (status_rank.get(item["governance_gate_status"], 9), -parse_float(item["research_priority_score"]), item["track"]))
    for index, row in enumerate(rows, start=1):
        row["governance_rank"] = str(index)
    return rows


def build_engine() -> None:
    rows = build_rows()
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["governance_gate_status"]] = counts.get(row["governance_gate_status"], 0) + 1

    approved = [row for row in rows if row["governance_gate_status"] in {"APPROVED_CORE_RESEARCH", "APPROVED_ACTIVE_RESEARCH"}]
    blocked = [row for row in rows if row["governance_gate_status"] in {"WATCHLIST_ONLY", "HOLD_FOR_MORE_EVIDENCE", "BLOCKED_FROM_MODELLING", "REJECTED_INSUFFICIENT_EVIDENCE"}]
    top = rows[0] if rows else {}

    summary = [
        {"metric": "governance_rows", "value": str(len(rows))},
        {"metric": "approved_core_research", "value": str(counts.get("APPROVED_CORE_RESEARCH", 0))},
        {"metric": "approved_active_research", "value": str(counts.get("APPROVED_ACTIVE_RESEARCH", 0))},
        {"metric": "watchlist_only", "value": str(counts.get("WATCHLIST_ONLY", 0))},
        {"metric": "hold_for_more_evidence", "value": str(counts.get("HOLD_FOR_MORE_EVIDENCE", 0))},
        {"metric": "blocked_from_modelling", "value": str(counts.get("BLOCKED_FROM_MODELLING", 0) + counts.get("WATCHLIST_ONLY", 0) + counts.get("HOLD_FOR_MORE_EVIDENCE", 0) + counts.get("REJECTED_INSUFFICIENT_EVIDENCE", 0) + counts.get("APPROVED_CORE_RESEARCH", 0) + counts.get("APPROVED_ACTIVE_RESEARCH", 0))},
        {"metric": "rejected_insufficient_evidence", "value": str(counts.get("REJECTED_INSUFFICIENT_EVIDENCE", 0))},
        {"metric": "approved_research_rows", "value": str(len(approved))},
        {"metric": "blocked_or_held_rows", "value": str(len(blocked))},
        {"metric": "top_governance_track", "value": clean(top.get("track"))},
        {"metric": "top_governance_status", "value": clean(top.get("governance_gate_status"))},
        {"metric": "research_boundary", "value": BOUNDARY},
        {"metric": "live_modelling_yes", "value": "0"},
        {"metric": "live_execution_yes", "value": "0"},
        {"metric": "engine_version", "value": ENGINE_VERSION},
    ]

    write_csv_atomic(OUT_GATE, rows, GATE_FIELDS)
    write_csv_atomic(OUT_SUMMARY, summary, SUMMARY_FIELDS)
    write_csv_atomic(OUT_BLOCKED, blocked, GATE_FIELDS)
    write_csv_atomic(OUT_APPROVED, approved, GATE_FIELDS)

    print(f"Ecology governance rows: {len(rows)}")
    print(f"Approved core research: {counts.get('APPROVED_CORE_RESEARCH', 0)}")
    print(f"Watchlist only: {counts.get('WATCHLIST_ONLY', 0)}")
    print("Live modelling: 0")
    print("Live execution: 0")


if __name__ == "__main__":
    build_engine()
