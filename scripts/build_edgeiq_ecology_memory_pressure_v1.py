from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"

DECAY = PUBLIC / "edgeiq_ecology_memory_decay_v1.csv"
TEMPORAL_HISTORY = PUBLIC / "edgeiq_ecology_temporal_drift_history_v1.csv"
LEDGER = PUBLIC / "edgeiq_ecology_research_ledger_v1.csv"
GOVERNANCE = PUBLIC / "edgeiq_ecology_governance_gate_v1.csv"
MUTATIONS = PUBLIC / "edgeiq_ecology_mutation_events_v1.csv"

OUT_PRESSURE = PUBLIC / "edgeiq_ecology_memory_pressure_v1.csv"
OUT_ALERTS = PUBLIC / "edgeiq_ecology_memory_pressure_alerts_v1.csv"
OUT_SUMMARY = PUBLIC / "edgeiq_ecology_memory_pressure_summary_v1.csv"

ENGINE_VERSION = "EDGEIQ_ECOLOGY_MEMORY_PRESSURE_ENGINE_V1"

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

def clean(value) -> str:
    return str(value or "").strip()

def upper(value) -> str:
    return clean(value).upper()

def safe_int(value) -> int:
    try:
        return int(float(value))
    except Exception:
        return 0

def safe_float(value) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0

def structure_key(row: dict) -> str:
    track = upper(row.get("track"))
    shape = upper(row.get("dominant_transition_shape"))
    if track or shape:
        return f"{track}|{shape}"
    return upper(row.get("structure_key"))

def pressure_band(score: float) -> str:
    if score >= 70:
        return "HIGH_PRESSURE"
    if score >= 40:
        return "MEDIUM_PRESSURE"
    if score >= 20:
        return "LOW_PRESSURE"
    return "MINIMAL_PRESSURE"

def pressure_action(band: str) -> str:
    if band == "HIGH_PRESSURE":
        return "freeze_structure_and_expand_audit"
    if band == "MEDIUM_PRESSURE":
        return "increase_snapshot_frequency"
    if band == "LOW_PRESSURE":
        return "continue_monitoring"
    return "maintain_observation"

def main() -> None:
    print("=" * 88)
    print("EDGEIQ ECOLOGY MEMORY PRESSURE ENGINE V1")
    print("=" * 88)

    decay_rows = read_csv(DECAY)
    temporal_rows = read_csv(TEMPORAL_HISTORY)
    ledger_rows = read_csv(LEDGER)
    governance_rows = read_csv(GOVERNANCE)
    mutation_rows = read_csv(MUTATIONS)

    temporal_by_key = {clean(row.get("structure_key")): row for row in temporal_rows if clean(row.get("structure_key"))}
    ledger_by_key = {structure_key(row): row for row in ledger_rows if structure_key(row)}
    governance_by_key = {structure_key(row): row for row in governance_rows if structure_key(row)}
    mutation_tracks = {upper(row.get("track")) for row in mutation_rows if clean(row.get("track"))}

    pressure_rows = []
    alert_rows = []

    for row in decay_rows:
        key = clean(row.get("structure_key")) or structure_key(row)
        track = clean(row.get("track"))
        shape = clean(row.get("dominant_transition_shape"))

        temporal = temporal_by_key.get(key, {})
        ledger = ledger_by_key.get(key, {})
        governance = governance_by_key.get(key, {})

        snapshot_count = safe_int(row.get("snapshot_count"))
        possible_transition_count = max(safe_int(row.get("possible_transition_count")), 0)
        stability_ratio = safe_float(row.get("stability_ratio"))

        drift_events = safe_int(row.get("drift_event_count"))
        mutation_events = safe_int(row.get("mutation_event_count"))
        governance_changes = safe_int(row.get("governance_change_count"))
        boundary_violations = safe_int(row.get("boundary_violation_count"))

        decay_state = upper(row.get("decay_state"))
        decay_risk = upper(row.get("decay_risk"))
        drift_velocity = upper(row.get("drift_velocity"))

        approved_for_research = upper(ledger.get("approved_for_research"))
        governance_status = upper(ledger.get("governance_status")) or upper(governance.get("governance_gate_status"))
        mutation_risk = upper(ledger.get("mutation_risk")) or upper(temporal.get("current_mutation_risk"))

        sample_pressure = 0
        if snapshot_count < 3:
            sample_pressure = 30
        elif snapshot_count < 6:
            sample_pressure = 18
        elif snapshot_count < 10:
            sample_pressure = 8

        stability_pressure = round(max(0.0, (1.0 - stability_ratio) * 40), 2)

        drift_pressure = 0
        if drift_velocity == "HIGH":
            drift_pressure = 35
        elif drift_velocity == "MEDIUM":
            drift_pressure = 20
        elif drift_velocity == "LOW":
            drift_pressure = 0
        else:
            drift_pressure = 12

        event_pressure = min(35, (drift_events * 8) + (mutation_events * 12) + (governance_changes * 15))

        governance_pressure = 0
        if boundary_violations > 0:
            governance_pressure = 100
        elif approved_for_research == "WATCHLIST" or "WATCHLIST" in governance_status:
            governance_pressure = 20
        elif "HOLD" in governance_status:
            governance_pressure = 30
        elif "BLOCKED" in governance_status or "REJECTED" in governance_status:
            governance_pressure = 45

        mutation_pressure = 0
        if "ELEVATED" in mutation_risk or upper(track) in mutation_tracks:
            mutation_pressure = 18
        elif "HIGH" in mutation_risk:
            mutation_pressure = 35

        decay_pressure = 0
        if decay_risk == "HIGH":
            decay_pressure = 35
        elif decay_risk == "MEDIUM":
            decay_pressure = 20

        raw_pressure_score = (
            sample_pressure
            + stability_pressure
            + drift_pressure
            + event_pressure
            + governance_pressure
            + mutation_pressure
            + decay_pressure
        )

        pressure_score = round(min(100, raw_pressure_score), 2)
        band = pressure_band(pressure_score)

        pressure_sources = []
        if sample_pressure:
            pressure_sources.append("LOW_SAMPLE_SIZE")
        if stability_pressure:
            pressure_sources.append("STABILITY_RATIO_PRESSURE")
        if drift_pressure:
            pressure_sources.append("DRIFT_VELOCITY_PRESSURE")
        if event_pressure:
            pressure_sources.append("EVENT_PRESSURE")
        if governance_pressure:
            pressure_sources.append("GOVERNANCE_PRESSURE")
        if mutation_pressure:
            pressure_sources.append("MUTATION_PRESSURE")
        if decay_pressure:
            pressure_sources.append("DECAY_PRESSURE")

        pressure_rows.append({
            "structure_key": key,
            "track": track,
            "dominant_transition_shape": shape,
            "snapshot_count": snapshot_count,
            "possible_transition_count": possible_transition_count,
            "stability_ratio": stability_ratio,
            "decay_state": clean(row.get("decay_state")),
            "decay_risk": clean(row.get("decay_risk")),
            "drift_velocity": clean(row.get("drift_velocity")),
            "memory_trend": clean(row.get("memory_trend")),
            "mutation_risk": mutation_risk or "UNKNOWN",
            "governance_status": governance_status or "UNKNOWN",
            "approved_for_research": approved_for_research or "UNKNOWN",
            "sample_pressure": sample_pressure,
            "stability_pressure": stability_pressure,
            "drift_pressure": drift_pressure,
            "event_pressure": event_pressure,
            "governance_pressure": governance_pressure,
            "mutation_pressure": mutation_pressure,
            "decay_pressure": decay_pressure,
            "pressure_score": pressure_score,
            "pressure_band": band,
            "pressure_sources": "|".join(pressure_sources) if pressure_sources else "NONE",
            "recommended_action": pressure_action(band),
            "research_boundary": "OFFLINE_RESEARCH_ONLY",
            "live_modelling_yes": 0,
            "live_execution_yes": 0,
            "engine_version": ENGINE_VERSION,
            "timestamp_utc": now_iso(),
        })

        if band in {"HIGH_PRESSURE", "MEDIUM_PRESSURE"}:
            alert_rows.append({
                "structure_key": key,
                "track": track,
                "pressure_band": band,
                "pressure_score": pressure_score,
                "pressure_sources": "|".join(pressure_sources),
                "recommended_action": pressure_action(band),
                "research_boundary": "OFFLINE_RESEARCH_ONLY",
                "live_modelling_yes": 0,
                "live_execution_yes": 0,
                "engine_version": ENGINE_VERSION,
                "timestamp_utc": now_iso(),
            })

    high_count = sum(1 for row in pressure_rows if row["pressure_band"] == "HIGH_PRESSURE")
    medium_count = sum(1 for row in pressure_rows if row["pressure_band"] == "MEDIUM_PRESSURE")
    low_count = sum(1 for row in pressure_rows if row["pressure_band"] == "LOW_PRESSURE")
    minimal_count = sum(1 for row in pressure_rows if row["pressure_band"] == "MINIMAL_PRESSURE")

    if high_count:
        health = "PRESSURE_RISK_ELEVATED"
    elif medium_count:
        health = "PRESSURE_MONITORING_REQUIRED"
    else:
        health = "PRESSURE_STABLE"

    summary_rows = [
        {"metric": "structures_assessed", "value": len(pressure_rows)},
        {"metric": "high_pressure_rows", "value": high_count},
        {"metric": "medium_pressure_rows", "value": medium_count},
        {"metric": "low_pressure_rows", "value": low_count},
        {"metric": "minimal_pressure_rows", "value": minimal_count},
        {"metric": "alert_rows", "value": len(alert_rows)},
        {"metric": "overall_pressure_health", "value": health},
        {"metric": "research_boundary", "value": "OFFLINE_RESEARCH_ONLY"},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
    ]

    write_csv(OUT_PRESSURE, pressure_rows, [
        "structure_key",
        "track",
        "dominant_transition_shape",
        "snapshot_count",
        "possible_transition_count",
        "stability_ratio",
        "decay_state",
        "decay_risk",
        "drift_velocity",
        "memory_trend",
        "mutation_risk",
        "governance_status",
        "approved_for_research",
        "sample_pressure",
        "stability_pressure",
        "drift_pressure",
        "event_pressure",
        "governance_pressure",
        "mutation_pressure",
        "decay_pressure",
        "pressure_score",
        "pressure_band",
        "pressure_sources",
        "recommended_action",
        "research_boundary",
        "live_modelling_yes",
        "live_execution_yes",
        "engine_version",
        "timestamp_utc",
    ])

    write_csv(OUT_ALERTS, alert_rows, [
        "structure_key",
        "track",
        "pressure_band",
        "pressure_score",
        "pressure_sources",
        "recommended_action",
        "research_boundary",
        "live_modelling_yes",
        "live_execution_yes",
        "engine_version",
        "timestamp_utc",
    ])

    write_csv(OUT_SUMMARY, summary_rows, ["metric", "value"])

    for row in summary_rows:
        print(f"{row['metric']}: {row['value']}")

    print("=" * 88)
    print("PRESSURE STATES")
    print("=" * 88)
    for row in pressure_rows:
        print(
            f"{row['track']} -> {row['pressure_band']} "
            f"score={row['pressure_score']} "
            f"sources={row['pressure_sources']}"
        )

if __name__ == "__main__":
    main()
