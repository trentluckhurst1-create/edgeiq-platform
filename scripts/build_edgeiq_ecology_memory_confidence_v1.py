from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"

PRESSURE = PUBLIC / "edgeiq_ecology_memory_pressure_v1.csv"
DECAY = PUBLIC / "edgeiq_ecology_memory_decay_v1.csv"
TEMPORAL = PUBLIC / "edgeiq_ecology_temporal_drift_history_v1.csv"
LEDGER = PUBLIC / "edgeiq_ecology_research_ledger_v1.csv"

OUT_CONFIDENCE = PUBLIC / "edgeiq_ecology_memory_confidence_v1.csv"
OUT_ALERTS = PUBLIC / "edgeiq_ecology_memory_confidence_alerts_v1.csv"
OUT_SUMMARY = PUBLIC / "edgeiq_ecology_memory_confidence_summary_v1.csv"

ENGINE_VERSION = "EDGEIQ_ECOLOGY_MEMORY_CONFIDENCE_ENGINE_V1"

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
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

def clean(v):
    return str(v or "").strip()

def upper(v):
    return clean(v).upper()

def safe_int(v):
    try:
        return int(float(v))
    except Exception:
        return 0

def safe_float(v):
    try:
        return float(v)
    except Exception:
        return 0.0

def confidence_band(score):
    if score >= 85:
        return "HIGH_CONFIDENCE"
    if score >= 65:
        return "MODERATE_CONFIDENCE"
    if score >= 40:
        return "FRAGILE_CONFIDENCE"
    return "LOW_CONFIDENCE"

def structure_key(row):
    track = upper(row.get("track"))
    shape = upper(row.get("dominant_transition_shape"))
    if track or shape:
        return f"{track}|{shape}"
    return upper(row.get("structure_key"))

def main():
    print("=" * 88)
    print("EDGEIQ ECOLOGY MEMORY CONFIDENCE ENGINE V1")
    print("=" * 88)

    pressure_rows = read_csv(PRESSURE)
    decay_rows = read_csv(DECAY)
    temporal_rows = read_csv(TEMPORAL)
    ledger_rows = read_csv(LEDGER)

    decay_by_key = {clean(r.get("structure_key")): r for r in decay_rows}
    temporal_by_key = {clean(r.get("structure_key")): r for r in temporal_rows}
    ledger_by_key = {structure_key(r): r for r in ledger_rows}

    confidence_rows = []
    alert_rows = []

    high_count = 0
    moderate_count = 0
    fragile_count = 0
    low_count = 0

    for row in pressure_rows:
        key = clean(row.get("structure_key"))
        track = clean(row.get("track"))
        shape = clean(row.get("dominant_transition_shape"))

        decay = decay_by_key.get(key, {})
        temporal = temporal_by_key.get(key, {})
        ledger = ledger_by_key.get(key, {})

        snapshot_count = safe_int(row.get("snapshot_count"))
        stability_ratio = safe_float(row.get("stability_ratio"))
        pressure_score = safe_float(row.get("pressure_score"))

        mutation_risk = upper(row.get("mutation_risk"))
        governance_status = upper(row.get("governance_status"))
        approved_for_research = upper(row.get("approved_for_research"))
        drift_velocity = upper(row.get("drift_velocity"))

        stable_snapshot_count = safe_int(temporal.get("stable_snapshot_count"))
        possible_transition_count = max(
            safe_int(temporal.get("possible_transition_count")),
            1,
        )

        # Positive confidence
        snapshot_confidence = min(40, snapshot_count * 6)
        stability_confidence = stability_ratio * 35

        survivability_confidence = min(
            20,
            stable_snapshot_count * 8,
        )

        governance_confidence = 0
        if "APPROVED_CORE_RESEARCH" in governance_status:
            governance_confidence = 15
        elif approved_for_research == "YES":
            governance_confidence = 10
        elif approved_for_research == "WATCHLIST":
            governance_confidence = -8

        # Negative confidence
        pressure_penalty = pressure_score * 0.35

        mutation_penalty = 0
        if "ELEVATED" in mutation_risk:
            mutation_penalty = 10
        elif "HIGH" in mutation_risk:
            mutation_penalty = 20

        drift_penalty = 0
        if drift_velocity == "MEDIUM":
            drift_penalty = 8
        elif drift_velocity == "HIGH":
            drift_penalty = 18

        confidence_score = round(
            max(
                0,
                min(
                    100,
                    snapshot_confidence
                    + stability_confidence
                    + survivability_confidence
                    + governance_confidence
                    - pressure_penalty
                    - mutation_penalty
                    - drift_penalty,
                ),
            ),
            2,
        )

        band = confidence_band(confidence_score)

        if band == "HIGH_CONFIDENCE":
            high_count += 1
        elif band == "MODERATE_CONFIDENCE":
            moderate_count += 1
        elif band == "FRAGILE_CONFIDENCE":
            fragile_count += 1
        else:
            low_count += 1

        confidence_sources = []

        if snapshot_count < 5:
            confidence_sources.append("LIMITED_SNAPSHOT_DEPTH")

        if stability_ratio >= 0.90:
            confidence_sources.append("STRONG_STABILITY")

        if pressure_score >= 40:
            confidence_sources.append("PRESSURE_REDUCTION")

        if "ELEVATED" in mutation_risk:
            confidence_sources.append("MUTATION_UNCERTAINTY")

        if "WATCHLIST" in governance_status or approved_for_research == "WATCHLIST":
            confidence_sources.append("WATCHLIST_GOVERNANCE")

        confidence_rows.append({
            "structure_key": key,
            "track": track,
            "dominant_transition_shape": shape,
            "snapshot_count": snapshot_count,
            "stable_snapshot_count": stable_snapshot_count,
            "possible_transition_count": possible_transition_count,
            "stability_ratio": stability_ratio,
            "pressure_score": pressure_score,
            "confidence_score": confidence_score,
            "confidence_band": band,
            "mutation_risk": mutation_risk,
            "governance_status": governance_status,
            "approved_for_research": approved_for_research,
            "confidence_sources": "|".join(confidence_sources),
            "recommended_action": (
                "continue_longitudinal_collection"
                if band in {"LOW_CONFIDENCE", "FRAGILE_CONFIDENCE"}
                else "maintain_monitoring"
            ),
            "research_boundary": "OFFLINE_RESEARCH_ONLY",
            "live_modelling_yes": 0,
            "live_execution_yes": 0,
            "engine_version": ENGINE_VERSION,
            "timestamp_utc": now_iso(),
        })

        if band in {"LOW_CONFIDENCE", "FRAGILE_CONFIDENCE"}:
            alert_rows.append({
                "structure_key": key,
                "track": track,
                "confidence_band": band,
                "confidence_score": confidence_score,
                "confidence_sources": "|".join(confidence_sources),
                "recommended_action": "increase_snapshot_depth",
                "research_boundary": "OFFLINE_RESEARCH_ONLY",
                "live_modelling_yes": 0,
                "live_execution_yes": 0,
                "engine_version": ENGINE_VERSION,
                "timestamp_utc": now_iso(),
            })

    if low_count:
        overall_health = "LOW_CONFIDENCE_MEMORY"
    elif fragile_count:
        overall_health = "FRAGILE_CONFIDENCE_MEMORY"
    else:
        overall_health = "CONFIDENCE_STABLE"

    summary_rows = [
        {"metric": "structures_assessed", "value": len(confidence_rows)},
        {"metric": "high_confidence_rows", "value": high_count},
        {"metric": "moderate_confidence_rows", "value": moderate_count},
        {"metric": "fragile_confidence_rows", "value": fragile_count},
        {"metric": "low_confidence_rows", "value": low_count},
        {"metric": "alert_rows", "value": len(alert_rows)},
        {"metric": "overall_confidence_health", "value": overall_health},
        {"metric": "research_boundary", "value": "OFFLINE_RESEARCH_ONLY"},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
    ]

    write_csv(
        OUT_CONFIDENCE,
        confidence_rows,
        [
            "structure_key",
            "track",
            "dominant_transition_shape",
            "snapshot_count",
            "stable_snapshot_count",
            "possible_transition_count",
            "stability_ratio",
            "pressure_score",
            "confidence_score",
            "confidence_band",
            "mutation_risk",
            "governance_status",
            "approved_for_research",
            "confidence_sources",
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
            "confidence_band",
            "confidence_score",
            "confidence_sources",
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
    print("MEMORY CONFIDENCE")
    print("=" * 88)

    for row in confidence_rows:
        print(
            f"{row['track']} -> "
            f"{row['confidence_band']} "
            f"score={row['confidence_score']} "
            f"sources={row['confidence_sources']}"
        )

if __name__ == "__main__":
    main()
