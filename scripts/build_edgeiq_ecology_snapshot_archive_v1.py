from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from edgeiq_memory_safe_io import count_csv_rows_streaming, safe_read_csv, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

IN_AUDIT = DATA / "edgeiq_ecology_research_audit_summary_v1.csv"
IN_ORCHESTRATOR = DATA / "edgeiq_ecology_orchestrator_summary_v1.csv"
IN_LEDGER = DATA / "edgeiq_ecology_research_ledger_v1.csv"
IN_MEMORY = DATA / "edgeiq_ecology_longitudinal_memory_v1.csv"
IN_STABILITY = DATA / "edgeiq_ecology_stability_index_v1.csv"
IN_MUTATION = DATA / "edgeiq_ecology_mutation_events_v1.csv"
IN_EVOLUTION = DATA / "edgeiq_ecology_temporal_evolution_v1.csv"

OUT_ARCHIVE = DATA / "edgeiq_ecology_snapshot_archive_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_ecology_snapshot_summary_v1.csv"
OUT_MANIFEST = DATA / "edgeiq_ecology_snapshot_manifest_v1.csv"

ENGINE_VERSION = "EDGEIQ_ECOLOGY_SNAPSHOT_ARCHIVE_V1"
BOUNDARY = "OFFLINE_RESEARCH_ONLY"

ARCHIVE_FIELDS = [
    "snapshot_id",
    "timestamp_utc",
    "source_file",
    "track",
    "dominant_transition_shape",
    "lifecycle_phase",
    "ecology_climate",
    "evidence_score",
    "evidence_class",
    "governance_status",
    "stability_score",
    "mutation_risk",
    "drift_risk",
    "approved_for_research",
    "approved_for_modelling",
    "approved_for_execution",
    "research_boundary",
    "live_modelling_yes",
    "live_execution_yes",
    "engine_version",
]

SUMMARY_FIELDS = ["metric", "value"]

MANIFEST_FIELDS = [
    "snapshot_id",
    "timestamp_utc",
    "archive_status",
    "source_file",
    "source_rows",
    "snapshot_rows_added",
    "audit_status",
    "orchestrator_status",
    "research_boundary",
    "live_modelling_yes",
    "live_execution_yes",
    "engine_version",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean(value: object) -> str:
    return str(value or "").strip()


def upper(value: object) -> str:
    return clean(value).upper()


def metric_map(path: Path) -> dict[str, str]:
    return {clean(row.get("metric")): clean(row.get("value")) for row in safe_read_csv(path) if clean(row.get("metric"))}


def by_track(path: Path) -> dict[str, dict[str, str]]:
    return {upper(row.get("track")): row for row in safe_read_csv(path) if clean(row.get("track"))}


def snapshot_id(timestamp: str) -> str:
    return f"ECOLOGY_SNAPSHOT_{timestamp.replace('-', '').replace(':', '').replace('+', 'Z')}"


def base_row(snapshot: str, timestamp: str, source_file: str, track: str) -> dict[str, str]:
    return {
        "snapshot_id": snapshot,
        "timestamp_utc": timestamp,
        "source_file": source_file,
        "track": track,
        "dominant_transition_shape": "",
        "lifecycle_phase": "",
        "ecology_climate": "",
        "evidence_score": "",
        "evidence_class": "",
        "governance_status": "",
        "stability_score": "",
        "mutation_risk": "",
        "drift_risk": "",
        "approved_for_research": "",
        "approved_for_modelling": "NO",
        "approved_for_execution": "NO",
        "research_boundary": BOUNDARY,
        "live_modelling_yes": "0",
        "live_execution_yes": "0",
        "engine_version": ENGINE_VERSION,
    }


def from_ledger(snapshot: str, timestamp: str, row: dict[str, str]) -> dict[str, str]:
    output = base_row(snapshot, timestamp, IN_LEDGER.name, clean(row.get("track")))
    output.update(
        {
            "dominant_transition_shape": clean(row.get("dominant_transition_shape")),
            "lifecycle_phase": clean(row.get("lifecycle_phase")),
            "ecology_climate": clean(row.get("ecology_climate")),
            "evidence_score": clean(row.get("evidence_score")),
            "evidence_class": clean(row.get("evidence_class")),
            "governance_status": clean(row.get("governance_status")),
            "stability_score": clean(row.get("stability_score")),
            "mutation_risk": clean(row.get("mutation_risk")),
            "drift_risk": clean(row.get("drift_risk")),
            "approved_for_research": clean(row.get("approved_for_research")),
            "approved_for_modelling": "NO",
            "approved_for_execution": "NO",
        }
    )
    return output


def from_memory(snapshot: str, timestamp: str, row: dict[str, str], ledger: dict[str, dict[str, str]]) -> dict[str, str]:
    track = clean(row.get("track"))
    led = ledger.get(upper(track), {})
    output = base_row(snapshot, timestamp, IN_MEMORY.name, track)
    output.update(
        {
            "dominant_transition_shape": clean(row.get("dominant_transition_shape")) or clean(led.get("dominant_transition_shape")),
            "lifecycle_phase": clean(led.get("lifecycle_phase")),
            "ecology_climate": clean(row.get("ecology_climate")) or clean(led.get("ecology_climate")),
            "evidence_score": clean(led.get("evidence_score")),
            "evidence_class": clean(led.get("evidence_class")),
            "governance_status": clean(led.get("governance_status")),
            "stability_score": clean(led.get("stability_score")),
            "mutation_risk": clean(led.get("mutation_risk")),
            "drift_risk": clean(led.get("drift_risk")),
            "approved_for_research": clean(led.get("approved_for_research")),
        }
    )
    return output


def from_stability(snapshot: str, timestamp: str, row: dict[str, str], ledger: dict[str, dict[str, str]]) -> dict[str, str]:
    track = clean(row.get("track"))
    led = ledger.get(upper(track), {})
    output = base_row(snapshot, timestamp, IN_STABILITY.name, track)
    output.update(
        {
            "dominant_transition_shape": clean(led.get("dominant_transition_shape")),
            "lifecycle_phase": clean(led.get("lifecycle_phase")),
            "ecology_climate": clean(row.get("climate")) or clean(led.get("ecology_climate")),
            "evidence_score": clean(led.get("evidence_score")),
            "evidence_class": clean(led.get("evidence_class")),
            "governance_status": clean(led.get("governance_status")),
            "stability_score": clean(row.get("stability_score")) or clean(led.get("stability_score")),
            "mutation_risk": clean(led.get("mutation_risk")),
            "drift_risk": clean(row.get("drift_risk")) or clean(led.get("drift_risk")),
            "approved_for_research": clean(led.get("approved_for_research")),
        }
    )
    return output


def from_mutation(snapshot: str, timestamp: str, row: dict[str, str], ledger: dict[str, dict[str, str]]) -> dict[str, str]:
    track = clean(row.get("track"))
    led = ledger.get(upper(track), {})
    output = base_row(snapshot, timestamp, IN_MUTATION.name, track)
    output.update(
        {
            "dominant_transition_shape": clean(row.get("dominant_transition_shape")) or clean(led.get("dominant_transition_shape")),
            "lifecycle_phase": clean(led.get("lifecycle_phase")),
            "ecology_climate": clean(row.get("ecology_climate")) or clean(led.get("ecology_climate")),
            "evidence_score": clean(led.get("evidence_score")),
            "evidence_class": clean(led.get("evidence_class")),
            "governance_status": clean(led.get("governance_status")),
            "stability_score": clean(led.get("stability_score")),
            "mutation_risk": clean(row.get("mutation_risk")) or clean(led.get("mutation_risk")),
            "drift_risk": clean(led.get("drift_risk")),
            "approved_for_research": clean(led.get("approved_for_research")),
        }
    )
    return output


def from_evolution(snapshot: str, timestamp: str, row: dict[str, str], ledger: dict[str, dict[str, str]]) -> dict[str, str]:
    track = clean(row.get("track"))
    led = ledger.get(upper(track), {})
    output = base_row(snapshot, timestamp, IN_EVOLUTION.name, track)
    output.update(
        {
            "dominant_transition_shape": clean(row.get("dominant_transition_shape")) or clean(led.get("dominant_transition_shape")),
            "lifecycle_phase": clean(row.get("lifecycle_phase")) or clean(led.get("lifecycle_phase")),
            "ecology_climate": clean(row.get("current_climate")) or clean(led.get("ecology_climate")),
            "evidence_score": clean(led.get("evidence_score")),
            "evidence_class": clean(row.get("evidence_grade")) or clean(led.get("evidence_class")),
            "governance_status": clean(led.get("governance_status")),
            "stability_score": clean(row.get("stability_score")) or clean(led.get("stability_score")),
            "mutation_risk": clean(row.get("mutation_risk")) or clean(led.get("mutation_risk")),
            "drift_risk": clean(row.get("drift_risk")) or clean(led.get("drift_risk")),
            "approved_for_research": clean(led.get("approved_for_research")),
        }
    )
    return output


def dedupe(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    output: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in rows:
        key = (row["snapshot_id"], row["source_file"], upper(row["track"]))
        output[key] = row
    return list(output.values())


def build_archive() -> None:
    audit = metric_map(IN_AUDIT)
    orchestrator = metric_map(IN_ORCHESTRATOR)
    timestamp = utc_now()
    sid = snapshot_id(timestamp)
    existing = safe_read_csv(OUT_ARCHIVE)

    audit_status = clean(audit.get("overall_status"))
    orchestrator_status = clean(orchestrator.get("health_status"))
    if audit_status != "AUDIT_PASS":
        summary = [
            {"metric": "archive_status", "value": "SKIPPED_AUDIT_NOT_PASS"},
            {"metric": "latest_snapshot_id", "value": ""},
            {"metric": "snapshot_rows_added", "value": "0"},
            {"metric": "archive_rows_total", "value": str(len(existing))},
            {"metric": "audit_status", "value": audit_status},
            {"metric": "orchestrator_status", "value": orchestrator_status},
            {"metric": "offline_research_only", "value": "YES"},
            {"metric": "research_boundary", "value": BOUNDARY},
            {"metric": "live_modelling_yes", "value": "0"},
            {"metric": "live_execution_yes", "value": "0"},
            {"metric": "engine_version", "value": ENGINE_VERSION},
        ]
        write_csv_atomic(OUT_SUMMARY, summary, SUMMARY_FIELDS)
        write_csv_atomic(OUT_MANIFEST, [], MANIFEST_FIELDS)
        print("Ecology snapshot archive skipped: audit not pass")
        return

    ledger_rows = safe_read_csv(IN_LEDGER)
    ledger = {upper(row.get("track")): row for row in ledger_rows if clean(row.get("track"))}
    new_rows: list[dict[str, str]] = []
    new_rows.extend(from_ledger(sid, timestamp, row) for row in ledger_rows)
    new_rows.extend(from_memory(sid, timestamp, row, ledger) for row in safe_read_csv(IN_MEMORY) if clean(row.get("track")))
    new_rows.extend(from_stability(sid, timestamp, row, ledger) for row in safe_read_csv(IN_STABILITY) if clean(row.get("track")))
    new_rows.extend(from_mutation(sid, timestamp, row, ledger) for row in safe_read_csv(IN_MUTATION) if clean(row.get("track")))
    new_rows.extend(from_evolution(sid, timestamp, row, ledger) for row in safe_read_csv(IN_EVOLUTION) if clean(row.get("track")))
    new_rows = dedupe(new_rows)
    archive_rows = dedupe(existing + new_rows)

    manifest_rows = []
    for path in [IN_LEDGER, IN_MEMORY, IN_STABILITY, IN_MUTATION, IN_EVOLUTION]:
        manifest_rows.append(
            {
                "snapshot_id": sid,
                "timestamp_utc": timestamp,
                "archive_status": "ARCHIVED",
                "source_file": path.name,
                "source_rows": str(count_csv_rows_streaming(path)),
                "snapshot_rows_added": str(sum(1 for row in new_rows if row["source_file"] == path.name)),
                "audit_status": audit_status,
                "orchestrator_status": orchestrator_status,
                "research_boundary": BOUNDARY,
                "live_modelling_yes": "0",
                "live_execution_yes": "0",
                "engine_version": ENGINE_VERSION,
            }
        )

    summary = [
        {"metric": "archive_status", "value": "ARCHIVED"},
        {"metric": "latest_snapshot_id", "value": sid},
        {"metric": "snapshot_rows_added", "value": str(len(new_rows))},
        {"metric": "archive_rows_total", "value": str(len(archive_rows))},
        {"metric": "manifest_rows", "value": str(len(manifest_rows))},
        {"metric": "audit_status", "value": audit_status},
        {"metric": "orchestrator_status", "value": orchestrator_status},
        {"metric": "offline_research_only", "value": "YES"},
        {"metric": "research_boundary", "value": BOUNDARY},
        {"metric": "live_modelling_yes", "value": "0"},
        {"metric": "live_execution_yes", "value": "0"},
        {"metric": "engine_version", "value": ENGINE_VERSION},
    ]

    write_csv_atomic(OUT_ARCHIVE, archive_rows, ARCHIVE_FIELDS)
    write_csv_atomic(OUT_SUMMARY, summary, SUMMARY_FIELDS)
    write_csv_atomic(OUT_MANIFEST, manifest_rows, MANIFEST_FIELDS)

    print("Ecology snapshot archive status: ARCHIVED")
    print(f"Snapshot id: {sid}")
    print(f"Snapshot rows added: {len(new_rows)}")
    print("Live modelling: 0")
    print("Live execution: 0")


if __name__ == "__main__":
    build_archive()
