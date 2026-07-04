from __future__ import annotations

import csv
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"

ARCHIVE = PUBLIC / "edgeiq_ecology_snapshot_archive_v1.csv"

OUT_COMPARISON = PUBLIC / "edgeiq_ecology_snapshot_comparison_v1.csv"
OUT_CHANGES = PUBLIC / "edgeiq_ecology_snapshot_drift_changes_v1.csv"
OUT_SUMMARY = PUBLIC / "edgeiq_ecology_snapshot_comparison_summary_v1.csv"

ENGINE_VERSION = "EDGEIQ_ECOLOGY_SNAPSHOT_COMPARISON_V1"

COMPARE_FIELDS = [
    "stability_score",
    "lifecycle_phase",
    "governance_status",
    "evidence_score",
    "mutation_risk",
    "ecology_climate",
    "dominant_transition_shape",
    "approved_for_research",
    "approved_for_modelling",
    "approved_for_execution",
]

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path, rows, fieldnames):
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

def safe_float(v):
    try:
        return float(v)
    except Exception:
        return None

def structure_key(row):
    track = upper(row.get("track"))
    shape = upper(row.get("dominant_transition_shape"))
    if track or shape:
        return f"{track}|{shape}"
    return upper(row.get("structure_id"))

def classify_change(latest, previous):
    if not previous:
        return "NO_PRIOR_SNAPSHOT"

    if upper(latest.get("approved_for_modelling")) == "YES" or upper(latest.get("approved_for_execution")) == "YES":
        return "BOUNDARY_VIOLATION"

    if upper(previous.get("approved_for_modelling")) == "YES" or upper(previous.get("approved_for_execution")) == "YES":
        return "BOUNDARY_VIOLATION"

    if upper(latest.get("governance_status")) != upper(previous.get("governance_status")):
        return "GOVERNANCE_CHANGE"

    if upper(latest.get("mutation_risk")) != upper(previous.get("mutation_risk")):
        return "MUTATION_ESCALATION"

    if upper(latest.get("ecology_climate")) != upper(previous.get("ecology_climate")) or upper(latest.get("lifecycle_phase")) != upper(previous.get("lifecycle_phase")):
        return "ECOLOGY_DRIFT"

    latest_score = safe_float(latest.get("evidence_score"))
    previous_score = safe_float(previous.get("evidence_score"))

    if latest_score is not None and previous_score is not None:
        delta = latest_score - previous_score
        if delta >= 2:
            return "EVIDENCE_IMPROVING"
        if delta <= -2:
            return "EVIDENCE_DEGRADING"

    return "STABLE_NO_CHANGE"

def main():
    print("=" * 88)
    print("EDGEIQ ECOLOGY SNAPSHOT COMPARISON V1")
    print("=" * 88)

    rows = read_csv(ARCHIVE)

    snapshot_ids = sorted(set(clean(r.get("snapshot_id")) for r in rows if clean(r.get("snapshot_id"))))

    comparison_rows = []
    change_rows = []

    if len(snapshot_ids) < 2:
        latest_id = snapshot_ids[-1] if snapshot_ids else ""
        summary_rows = [
            {"metric": "latest_snapshot_id", "value": latest_id},
            {"metric": "previous_snapshot_id", "value": ""},
            {"metric": "compared_rows", "value": 0},
            {"metric": "stable_rows", "value": 0},
            {"metric": "drift_rows", "value": 0},
            {"metric": "mutation_rows", "value": 0},
            {"metric": "governance_changes", "value": 0},
            {"metric": "boundary_violations", "value": 0},
            {"metric": "overall_comparison_health", "value": "NO_PRIOR_SNAPSHOT"},
            {"metric": "research_boundary", "value": "OFFLINE_RESEARCH_ONLY"},
            {"metric": "live_modelling_yes", "value": 0},
            {"metric": "live_execution_yes", "value": 0},
        ]
    else:
        previous_id = snapshot_ids[-2]
        latest_id = snapshot_ids[-1]

        latest_rows = [r for r in rows if clean(r.get("snapshot_id")) == latest_id]
        previous_rows = [r for r in rows if clean(r.get("snapshot_id")) == previous_id]

        previous_by_key = {structure_key(r): r for r in previous_rows if structure_key(r)}

        for latest in latest_rows:
            key = structure_key(latest)
            previous = previous_by_key.get(key)
            change_type = classify_change(latest, previous)

            latest_score = safe_float(latest.get("evidence_score"))
            previous_score = safe_float(previous.get("evidence_score")) if previous else None
            score_delta = ""
            if latest_score is not None and previous_score is not None:
                score_delta = round(latest_score - previous_score, 4)

            comparison_rows.append({
                "structure_key": key,
                "track": clean(latest.get("track")),
                "latest_snapshot_id": latest_id,
                "previous_snapshot_id": previous_id,
                "change_classification": change_type,
                "latest_lifecycle_phase": clean(latest.get("lifecycle_phase")),
                "previous_lifecycle_phase": clean(previous.get("lifecycle_phase")) if previous else "",
                "latest_governance_status": clean(latest.get("governance_status")),
                "previous_governance_status": clean(previous.get("governance_status")) if previous else "",
                "latest_evidence_score": clean(latest.get("evidence_score")),
                "previous_evidence_score": clean(previous.get("evidence_score")) if previous else "",
                "evidence_score_delta": score_delta,
                "latest_mutation_risk": clean(latest.get("mutation_risk")),
                "previous_mutation_risk": clean(previous.get("mutation_risk")) if previous else "",
                "latest_ecology_climate": clean(latest.get("ecology_climate")),
                "previous_ecology_climate": clean(previous.get("ecology_climate")) if previous else "",
                "approved_for_modelling": clean(latest.get("approved_for_modelling")),
                "approved_for_execution": clean(latest.get("approved_for_execution")),
                "research_boundary": "OFFLINE_RESEARCH_ONLY",
                "live_modelling_yes": 0,
                "live_execution_yes": 0,
                "engine_version": ENGINE_VERSION,
                "timestamp_utc": now_iso(),
            })

            if change_type != "STABLE_NO_CHANGE":
                change_rows.append(comparison_rows[-1])

        stable = sum(1 for r in comparison_rows if r["change_classification"] == "STABLE_NO_CHANGE")
        drift = sum(1 for r in comparison_rows if r["change_classification"] in {"ECOLOGY_DRIFT", "EVIDENCE_DEGRADING", "EVIDENCE_IMPROVING"})
        mutation = sum(1 for r in comparison_rows if r["change_classification"] == "MUTATION_ESCALATION")
        governance = sum(1 for r in comparison_rows if r["change_classification"] == "GOVERNANCE_CHANGE")
        boundary = sum(1 for r in comparison_rows if r["change_classification"] == "BOUNDARY_VIOLATION")

        if boundary:
            health = "GOVERNANCE_BREACH"
        elif drift or mutation or governance:
            health = "DRIFTING_RESEARCH_MEMORY"
        else:
            health = "STABLE_RESEARCH_MEMORY"

        summary_rows = [
            {"metric": "latest_snapshot_id", "value": latest_id},
            {"metric": "previous_snapshot_id", "value": previous_id},
            {"metric": "compared_rows", "value": len(comparison_rows)},
            {"metric": "stable_rows", "value": stable},
            {"metric": "drift_rows", "value": drift},
            {"metric": "mutation_rows", "value": mutation},
            {"metric": "governance_changes", "value": governance},
            {"metric": "boundary_violations", "value": boundary},
            {"metric": "overall_comparison_health", "value": health},
            {"metric": "research_boundary", "value": "OFFLINE_RESEARCH_ONLY"},
            {"metric": "live_modelling_yes", "value": 0},
            {"metric": "live_execution_yes", "value": 0},
        ]

    write_csv(OUT_COMPARISON, comparison_rows, [
        "structure_key",
        "track",
        "latest_snapshot_id",
        "previous_snapshot_id",
        "change_classification",
        "latest_lifecycle_phase",
        "previous_lifecycle_phase",
        "latest_governance_status",
        "previous_governance_status",
        "latest_evidence_score",
        "previous_evidence_score",
        "evidence_score_delta",
        "latest_mutation_risk",
        "previous_mutation_risk",
        "latest_ecology_climate",
        "previous_ecology_climate",
        "approved_for_modelling",
        "approved_for_execution",
        "research_boundary",
        "live_modelling_yes",
        "live_execution_yes",
        "engine_version",
        "timestamp_utc",
    ])

    write_csv(OUT_CHANGES, change_rows, [
        "structure_key",
        "track",
        "latest_snapshot_id",
        "previous_snapshot_id",
        "change_classification",
        "latest_lifecycle_phase",
        "previous_lifecycle_phase",
        "latest_governance_status",
        "previous_governance_status",
        "latest_evidence_score",
        "previous_evidence_score",
        "evidence_score_delta",
        "latest_mutation_risk",
        "previous_mutation_risk",
        "latest_ecology_climate",
        "previous_ecology_climate",
        "approved_for_modelling",
        "approved_for_execution",
        "research_boundary",
        "live_modelling_yes",
        "live_execution_yes",
        "engine_version",
        "timestamp_utc",
    ])

    write_csv(OUT_SUMMARY, summary_rows, ["metric", "value"])

    for r in summary_rows:
        print(f"{r['metric']}: {r['value']}")

if __name__ == "__main__":
    main()
