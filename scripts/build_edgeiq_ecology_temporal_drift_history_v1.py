from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"

SNAPSHOT_ARCHIVE = PUBLIC / "edgeiq_ecology_snapshot_archive_v1.csv"
SNAPSHOT_COMPARISON = PUBLIC / "edgeiq_ecology_snapshot_comparison_v1.csv"
SNAPSHOT_CHANGES = PUBLIC / "edgeiq_ecology_snapshot_drift_changes_v1.csv"
RESEARCH_LEDGER = PUBLIC / "edgeiq_ecology_research_ledger_v1.csv"

OUT_HISTORY = PUBLIC / "edgeiq_ecology_temporal_drift_history_v1.csv"
OUT_DURATION = PUBLIC / "edgeiq_ecology_temporal_stability_duration_v1.csv"
OUT_SUMMARY = PUBLIC / "edgeiq_ecology_temporal_drift_summary_v1.csv"

ENGINE_VERSION = "EDGEIQ_ECOLOGY_TEMPORAL_DRIFT_HISTORY_V1_FIXED_DEDUPED"

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
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

def clean(value) -> str:
    return str(value or "").strip()

def upper(value) -> str:
    return clean(value).upper()

def structure_key(row: dict) -> str:
    track = upper(row.get("track"))
    shape = upper(row.get("dominant_transition_shape"))
    if track or shape:
        return f"{track}|{shape}"
    return upper(row.get("structure_id"))

def classify_drift_velocity(snapshot_count: int, drift_events: int, mutation_events: int, governance_changes: int, boundary_violations: int) -> str:
    if boundary_violations > 0:
        return "BOUNDARY_BREACH"
    if snapshot_count <= 1:
        return "INSUFFICIENT_HISTORY"

    event_load = drift_events + mutation_events + governance_changes

    if event_load == 0:
        return "LOW"
    if event_load / max(snapshot_count - 1, 1) <= 0.25:
        return "MEDIUM"
    return "HIGH"

def classify_memory_trend(snapshot_count: int, stable_transition_count: int, drift_velocity: str) -> str:
    if drift_velocity == "BOUNDARY_BREACH":
        return "GOVERNANCE_BREACH"
    if snapshot_count <= 1:
        return "INSUFFICIENT_HISTORY"

    possible_transitions = max(snapshot_count - 1, 1)
    stability_ratio = stable_transition_count / possible_transitions

    if drift_velocity == "LOW" and stability_ratio >= 0.8:
        return "STRENGTHENING_STABLE_MEMORY"
    if drift_velocity == "LOW":
        return "STABLE_MEMORY"
    if drift_velocity == "MEDIUM":
        return "WATCHLIST_MEMORY"
    return "DEGRADING_MEMORY"

def dominant_value(rows: list[dict], field: str) -> str:
    values = [clean(r.get(field)) for r in rows if clean(r.get(field))]
    if not values:
        return ""
    return Counter(values).most_common(1)[0][0]

def main() -> None:
    print("=" * 88)
    print("EDGEIQ ECOLOGY TEMPORAL DRIFT HISTORY V1 - FIXED DEDUPED")
    print("=" * 88)

    archive = read_csv(SNAPSHOT_ARCHIVE)
    comparison = read_csv(SNAPSHOT_COMPARISON)
    ledger = read_csv(RESEARCH_LEDGER)

    snapshots = sorted(set(clean(r.get("snapshot_id")) for r in archive if clean(r.get("snapshot_id"))))

    archive_by_key = defaultdict(list)
    for row in archive:
        key = structure_key(row)
        if key:
            archive_by_key[key].append(row)

    # Critical fix:
    # Deduplicate comparison rows by structure_key + latest_snapshot_id + previous_snapshot_id.
    deduped_comparisons = {}
    for row in comparison:
        key = clean(row.get("structure_key")) or structure_key(row)
        latest_snapshot_id = clean(row.get("latest_snapshot_id"))
        previous_snapshot_id = clean(row.get("previous_snapshot_id"))
        if not key:
            continue
        dedupe_key = (key, latest_snapshot_id, previous_snapshot_id)
        deduped_comparisons[dedupe_key] = row

    comparison_by_key = defaultdict(list)
    for (key, _latest, _previous), row in deduped_comparisons.items():
        comparison_by_key[key].append(row)

    ledger_by_key = {}
    for row in ledger:
        key = structure_key(row)
        if key:
            ledger_by_key[key] = row

    history_rows = []
    duration_rows = []

    total_drift_events = 0
    total_mutation_events = 0
    total_governance_changes = 0
    total_boundary_violations = 0

    for key, rows in sorted(archive_by_key.items()):
        rows = sorted(rows, key=lambda r: clean(r.get("snapshot_id")))

        snapshot_ids = sorted(set(clean(r.get("snapshot_id")) for r in rows if clean(r.get("snapshot_id"))))
        snapshot_count = len(snapshot_ids)
        possible_transitions = max(snapshot_count - 1, 0)

        latest = rows[-1]
        ledger_row = ledger_by_key.get(key, {})

        track = clean(latest.get("track"))
        shape = clean(latest.get("dominant_transition_shape"))

        stable_transition_count = 0
        drift_event_count = 0
        mutation_event_count = 0
        governance_change_count = 0
        boundary_violation_count = 0

        for row in rows:
            if upper(row.get("approved_for_modelling")) == "YES" or upper(row.get("approved_for_execution")) == "YES":
                boundary_violation_count += 1

        for comp in comparison_by_key.get(key, []):
            change = upper(comp.get("change_classification"))

            if change == "STABLE_NO_CHANGE":
                stable_transition_count += 1
            elif change in {"ECOLOGY_DRIFT", "EVIDENCE_DEGRADING", "EVIDENCE_IMPROVING"}:
                drift_event_count += 1
            elif change == "MUTATION_ESCALATION":
                mutation_event_count += 1
            elif change == "GOVERNANCE_CHANGE":
                governance_change_count += 1
            elif change == "BOUNDARY_VIOLATION":
                boundary_violation_count += 1

        # Clamp counts so they can never exceed actual possible transitions.
        stable_transition_count = min(stable_transition_count, possible_transitions)
        drift_event_count = min(drift_event_count, possible_transitions)
        mutation_event_count = min(mutation_event_count, possible_transitions)
        governance_change_count = min(governance_change_count, possible_transitions)

        if snapshot_count > 1 and not comparison_by_key.get(key):
            stable_transition_count = possible_transitions

        drift_velocity = classify_drift_velocity(
            snapshot_count,
            drift_event_count,
            mutation_event_count,
            governance_change_count,
            boundary_violation_count,
        )

        memory_trend = classify_memory_trend(
            snapshot_count,
            stable_transition_count,
            drift_velocity,
        )

        stability_duration_snapshots = min(snapshot_count, stable_transition_count + 1 if snapshot_count else 0)

        total_drift_events += drift_event_count
        total_mutation_events += mutation_event_count
        total_governance_changes += governance_change_count
        total_boundary_violations += boundary_violation_count

        history_rows.append({
            "structure_key": key,
            "track": track,
            "dominant_transition_shape": shape,
            "snapshot_count": snapshot_count,
            "stable_snapshot_count": stable_transition_count,
            "possible_transition_count": possible_transitions,
            "drift_event_count": drift_event_count,
            "mutation_event_count": mutation_event_count,
            "governance_change_count": governance_change_count,
            "boundary_violation_count": boundary_violation_count,
            "stability_duration_snapshots": stability_duration_snapshots,
            "drift_velocity": drift_velocity,
            "memory_trend": memory_trend,
            "current_lifecycle_phase": clean(latest.get("lifecycle_phase")),
            "current_ecology_climate": clean(latest.get("ecology_climate")),
            "current_governance_status": clean(latest.get("governance_status")),
            "current_mutation_risk": clean(latest.get("mutation_risk")),
            "approved_for_research": clean(latest.get("approved_for_research")) or clean(ledger_row.get("approved_for_research")),
            "approved_for_modelling": "NO",
            "approved_for_execution": "NO",
            "research_boundary": "OFFLINE_RESEARCH_ONLY",
            "live_modelling_yes": 0,
            "live_execution_yes": 0,
            "engine_version": ENGINE_VERSION,
            "timestamp_utc": now_iso(),
        })

        duration_rows.append({
            "structure_key": key,
            "track": track,
            "dominant_transition_shape": shape,
            "first_snapshot_id": snapshot_ids[0] if snapshot_ids else "",
            "latest_snapshot_id": snapshot_ids[-1] if snapshot_ids else "",
            "snapshot_count": snapshot_count,
            "possible_transition_count": possible_transitions,
            "stable_transition_count": stable_transition_count,
            "stability_duration_snapshots": stability_duration_snapshots,
            "dominant_lifecycle_phase": dominant_value(rows, "lifecycle_phase"),
            "dominant_ecology_climate": dominant_value(rows, "ecology_climate"),
            "dominant_governance_status": dominant_value(rows, "governance_status"),
            "dominant_mutation_risk": dominant_value(rows, "mutation_risk"),
            "drift_velocity": drift_velocity,
            "memory_trend": memory_trend,
            "research_boundary": "OFFLINE_RESEARCH_ONLY",
            "live_modelling_yes": 0,
            "live_execution_yes": 0,
            "engine_version": ENGINE_VERSION,
        })

    if total_boundary_violations:
        overall_health = "GOVERNANCE_BREACH"
    elif total_drift_events or total_mutation_events or total_governance_changes:
        overall_health = "DRIFTING_TEMPORAL_MEMORY"
    elif snapshots and history_rows:
        overall_health = "STABLE_TEMPORAL_MEMORY"
    else:
        overall_health = "INSUFFICIENT_TEMPORAL_MEMORY"

    impossible_count_rows = sum(
        1
        for r in history_rows
        if int(r["stable_snapshot_count"]) > int(r["possible_transition_count"])
        or int(r["stability_duration_snapshots"]) > int(r["snapshot_count"])
    )

    summary_rows = [
        {"metric": "snapshot_count", "value": len(snapshots)},
        {"metric": "structures_tracked", "value": len(history_rows)},
        {"metric": "stable_memory_rows", "value": sum(1 for r in history_rows if r["memory_trend"] in {"STRENGTHENING_STABLE_MEMORY", "STABLE_MEMORY"})},
        {"metric": "watchlist_memory_rows", "value": sum(1 for r in history_rows if r["memory_trend"] == "WATCHLIST_MEMORY")},
        {"metric": "degrading_memory_rows", "value": sum(1 for r in history_rows if r["memory_trend"] == "DEGRADING_MEMORY")},
        {"metric": "total_drift_events", "value": total_drift_events},
        {"metric": "total_mutation_events", "value": total_mutation_events},
        {"metric": "total_governance_changes", "value": total_governance_changes},
        {"metric": "total_boundary_violations", "value": total_boundary_violations},
        {"metric": "impossible_count_rows", "value": impossible_count_rows},
        {"metric": "overall_temporal_memory_health", "value": overall_health},
        {"metric": "research_boundary", "value": "OFFLINE_RESEARCH_ONLY"},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
    ]

    write_csv(OUT_HISTORY, history_rows, [
        "structure_key",
        "track",
        "dominant_transition_shape",
        "snapshot_count",
        "stable_snapshot_count",
        "possible_transition_count",
        "drift_event_count",
        "mutation_event_count",
        "governance_change_count",
        "boundary_violation_count",
        "stability_duration_snapshots",
        "drift_velocity",
        "memory_trend",
        "current_lifecycle_phase",
        "current_ecology_climate",
        "current_governance_status",
        "current_mutation_risk",
        "approved_for_research",
        "approved_for_modelling",
        "approved_for_execution",
        "research_boundary",
        "live_modelling_yes",
        "live_execution_yes",
        "engine_version",
        "timestamp_utc",
    ])

    write_csv(OUT_DURATION, duration_rows, [
        "structure_key",
        "track",
        "dominant_transition_shape",
        "first_snapshot_id",
        "latest_snapshot_id",
        "snapshot_count",
        "possible_transition_count",
        "stable_transition_count",
        "stability_duration_snapshots",
        "dominant_lifecycle_phase",
        "dominant_ecology_climate",
        "dominant_governance_status",
        "dominant_mutation_risk",
        "drift_velocity",
        "memory_trend",
        "research_boundary",
        "live_modelling_yes",
        "live_execution_yes",
        "engine_version",
    ])

    write_csv(OUT_SUMMARY, summary_rows, ["metric", "value"])

    for row in summary_rows:
        print(f"{row['metric']}: {row['value']}")

    print("=" * 88)
    print("TEMPORAL MEMORY")
    print("=" * 88)

    for row in history_rows:
        print(
            f"{row['track']} -> {row['memory_trend']} "
            f"snapshots={row['snapshot_count']} "
            f"stable_transitions={row['stable_snapshot_count']}/{row['possible_transition_count']} "
            f"drift={row['drift_velocity']}"
        )

if __name__ == "__main__":
    main()
