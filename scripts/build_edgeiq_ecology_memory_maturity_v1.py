from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"

CONFIDENCE = PUBLIC / "edgeiq_ecology_memory_confidence_v1.csv"
PRESSURE = PUBLIC / "edgeiq_ecology_memory_pressure_v1.csv"
DECAY = PUBLIC / "edgeiq_ecology_memory_decay_v1.csv"
TEMPORAL = PUBLIC / "edgeiq_ecology_temporal_drift_history_v1.csv"
LEDGER = PUBLIC / "edgeiq_ecology_research_ledger_v1.csv"

OUT_MATURITY = PUBLIC / "edgeiq_ecology_memory_maturity_v1.csv"
OUT_ALERTS = PUBLIC / "edgeiq_ecology_memory_maturity_alerts_v1.csv"
OUT_SUMMARY = PUBLIC / "edgeiq_ecology_memory_maturity_summary_v1.csv"

ENGINE_VERSION = "EDGEIQ_ECOLOGY_MEMORY_MATURITY_ENGINE_V1"

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def read_csv(path: Path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

def clean(value):
    return str(value or "").strip()

def upper(value):
    return clean(value).upper()

def safe_float(value):
    try:
        return float(value)
    except Exception:
        return 0.0

def safe_int(value):
    try:
        return int(float(value))
    except Exception:
        return 0

def structure_key(row):
    track = upper(row.get("track"))
    shape = upper(row.get("dominant_transition_shape"))
    if track or shape:
        return f"{track}|{shape}"
    return upper(row.get("structure_key"))

def maturity_band(score):
    if score >= 85:
        return "MATURE_LONGITUDINAL_MEMORY"
    if score >= 65:
        return "DEVELOPING_LONGITUDINAL_MEMORY"
    if score >= 40:
        return "EARLY_STAGE_MEMORY"
    return "IMMATURE_MEMORY"

def maturity_action(band):
    if band == "MATURE_LONGITUDINAL_MEMORY":
        return "maintain_governed_observation"
    if band == "DEVELOPING_LONGITUDINAL_MEMORY":
        return "continue_snapshot_accumulation"
    if band == "EARLY_STAGE_MEMORY":
        return "expand_snapshot_depth_before_promotion"
    return "collect_more_evidence_only"

def main():
    print("=" * 88)
    print("EDGEIQ ECOLOGY MEMORY MATURITY ENGINE V1")
    print("=" * 88)

    confidence_rows = read_csv(CONFIDENCE)
    pressure_rows = read_csv(PRESSURE)
    decay_rows = read_csv(DECAY)
    temporal_rows = read_csv(TEMPORAL)
    ledger_rows = read_csv(LEDGER)

    pressure_by_key = {clean(row.get("structure_key")): row for row in pressure_rows}
    decay_by_key = {clean(row.get("structure_key")): row for row in decay_rows}
    temporal_by_key = {clean(row.get("structure_key")): row for row in temporal_rows}
    ledger_by_key = {structure_key(row): row for row in ledger_rows}

    maturity_rows = []
    alert_rows = []

    for row in confidence_rows:
        key = clean(row.get("structure_key"))
        track = clean(row.get("track"))
        shape = clean(row.get("dominant_transition_shape"))

        pressure = pressure_by_key.get(key, {})
        decay = decay_by_key.get(key, {})
        temporal = temporal_by_key.get(key, {})
        ledger = ledger_by_key.get(key, {})

        snapshot_count = safe_int(row.get("snapshot_count"))
        stable_snapshot_count = safe_int(row.get("stable_snapshot_count"))
        possible_transition_count = max(safe_int(row.get("possible_transition_count")), 1)

        confidence_score = safe_float(row.get("confidence_score"))
        pressure_score = safe_float(row.get("pressure_score"))
        stability_ratio = safe_float(row.get("stability_ratio"))

        drift_events = safe_int(temporal.get("drift_event_count"))
        mutation_events = safe_int(temporal.get("mutation_event_count"))
        governance_changes = safe_int(temporal.get("governance_change_count"))
        boundary_violations = safe_int(temporal.get("boundary_violation_count"))

        governance_status = upper(ledger.get("governance_status"))
        approved_for_research = upper(ledger.get("approved_for_research"))
        mutation_risk = upper(ledger.get("mutation_risk")) or upper(row.get("mutation_risk"))

        snapshot_depth_score = min(30, snapshot_count * 4)
        stability_survival_score = min(25, stable_snapshot_count * 10)
        confidence_component = min(25, confidence_score * 0.25)
        governance_component = 0

        if "APPROVED_CORE_RESEARCH" in governance_status:
            governance_component = 15
        elif approved_for_research == "YES":
            governance_component = 10
        elif approved_for_research == "WATCHLIST":
            governance_component = 3

        resilience_component = 0
        if stability_ratio >= 0.95 and pressure_score < 40:
            resilience_component = 10
        elif stability_ratio >= 0.80:
            resilience_component = 5

        penalties = 0
        penalties += min(20, pressure_score * 0.20)
        penalties += drift_events * 6
        penalties += mutation_events * 8
        penalties += governance_changes * 10
        penalties += boundary_violations * 100

        if "ELEVATED" in mutation_risk:
            penalties += 6
        if snapshot_count < 3:
            penalties += 10

        maturity_score = round(
            max(
                0,
                min(
                    100,
                    snapshot_depth_score
                    + stability_survival_score
                    + confidence_component
                    + governance_component
                    + resilience_component
                    - penalties,
                ),
            ),
            2,
        )

        band = maturity_band(maturity_score)

        sources = []
        if snapshot_count < 3:
            sources.append("VERY_EARLY_SNAPSHOT_HISTORY")
        if stability_ratio >= 0.95:
            sources.append("STABLE_SURVIVAL")
        if confidence_score < 65:
            sources.append("CONFIDENCE_NOT_MATURE")
        if pressure_score >= 40:
            sources.append("PRESSURE_LIMITING_MATURITY")
        if approved_for_research == "WATCHLIST":
            sources.append("WATCHLIST_LIMITING_MATURITY")
        if "APPROVED_CORE_RESEARCH" in governance_status:
            sources.append("CORE_RESEARCH_GOVERNANCE")

        maturity_rows.append({
            "structure_key": key,
            "track": track,
            "dominant_transition_shape": shape,
            "snapshot_count": snapshot_count,
            "stable_snapshot_count": stable_snapshot_count,
            "possible_transition_count": possible_transition_count,
            "stability_ratio": stability_ratio,
            "confidence_score": confidence_score,
            "pressure_score": pressure_score,
            "maturity_score": maturity_score,
            "maturity_band": band,
            "governance_status": governance_status or "UNKNOWN",
            "approved_for_research": approved_for_research or "UNKNOWN",
            "mutation_risk": mutation_risk or "UNKNOWN",
            "maturity_sources": "|".join(sources),
            "recommended_action": maturity_action(band),
            "research_boundary": "OFFLINE_RESEARCH_ONLY",
            "live_modelling_yes": 0,
            "live_execution_yes": 0,
            "engine_version": ENGINE_VERSION,
            "timestamp_utc": now_iso(),
        })

        if band in {"IMMATURE_MEMORY", "EARLY_STAGE_MEMORY"}:
            alert_rows.append({
                "structure_key": key,
                "track": track,
                "maturity_band": band,
                "maturity_score": maturity_score,
                "maturity_sources": "|".join(sources),
                "recommended_action": maturity_action(band),
                "research_boundary": "OFFLINE_RESEARCH_ONLY",
                "live_modelling_yes": 0,
                "live_execution_yes": 0,
                "engine_version": ENGINE_VERSION,
                "timestamp_utc": now_iso(),
            })

    mature = sum(1 for r in maturity_rows if r["maturity_band"] == "MATURE_LONGITUDINAL_MEMORY")
    developing = sum(1 for r in maturity_rows if r["maturity_band"] == "DEVELOPING_LONGITUDINAL_MEMORY")
    early = sum(1 for r in maturity_rows if r["maturity_band"] == "EARLY_STAGE_MEMORY")
    immature = sum(1 for r in maturity_rows if r["maturity_band"] == "IMMATURE_MEMORY")

    if mature:
        health = "MATURE_MEMORY_PRESENT"
    elif developing:
        health = "MEMORY_DEVELOPING"
    elif early:
        health = "EARLY_MEMORY_ONLY"
    else:
        health = "IMMATURE_MEMORY_ONLY"

    summary_rows = [
        {"metric": "structures_assessed", "value": len(maturity_rows)},
        {"metric": "mature_memory_rows", "value": mature},
        {"metric": "developing_memory_rows", "value": developing},
        {"metric": "early_memory_rows", "value": early},
        {"metric": "immature_memory_rows", "value": immature},
        {"metric": "alert_rows", "value": len(alert_rows)},
        {"metric": "overall_maturity_health", "value": health},
        {"metric": "research_boundary", "value": "OFFLINE_RESEARCH_ONLY"},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
    ]

    write_csv(
        OUT_MATURITY,
        maturity_rows,
        [
            "structure_key",
            "track",
            "dominant_transition_shape",
            "snapshot_count",
            "stable_snapshot_count",
            "possible_transition_count",
            "stability_ratio",
            "confidence_score",
            "pressure_score",
            "maturity_score",
            "maturity_band",
            "governance_status",
            "approved_for_research",
            "mutation_risk",
            "maturity_sources",
            "recommended_action",
            "research_boundary",
            "live_modelling_yes",
            "live_execution_yes",
            "engine_version",
            "timestamp_utc",
        ],
    )

    write_csv(
        OUT_ALERTS,
        alert_rows,
        [
            "structure_key",
            "track",
            "maturity_band",
            "maturity_score",
            "maturity_sources",
            "recommended_action",
            "research_boundary",
            "live_modelling_yes",
            "live_execution_yes",
            "engine_version",
            "timestamp_utc",
        ],
    )

    write_csv(
        OUT_SUMMARY,
        summary_rows,
        ["metric", "value"],
    )

    for row in summary_rows:
        print(f"{row['metric']}: {row['value']}")

    print("=" * 88)
    print("MEMORY MATURITY")
    print("=" * 88)

    for row in maturity_rows:
        print(
            f"{row['track']} -> "
            f"{row['maturity_band']} "
            f"score={row['maturity_score']} "
            f"sources={row['maturity_sources']}"
        )

if __name__ == "__main__":
    main()
