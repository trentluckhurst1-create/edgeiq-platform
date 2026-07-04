from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from edgeiq_memory_safe_io import safe_read_csv, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

IN_ASSET_SCHEMA = DATA / "edgeiq_qld_asset_schema_summary_v1.csv"
IN_ONTOLOGY = DATA / "edgeiq_qld_telemetry_ontology_summary_v1.csv"
IN_TRANSITION = DATA / "edgeiq_qld_race_state_transition_summary_v1.csv"
IN_PERSISTENCE = DATA / "edgeiq_transition_persistence_summary_v1.csv"
IN_ECOLOGY_DRIFT = DATA / "edgeiq_transition_ecology_drift_summary_v1.csv"
IN_ECOLOGY_MEMORY = DATA / "edgeiq_ecology_memory_summary_v1.csv"
IN_ECOLOGY_EVOLUTION = DATA / "edgeiq_ecology_evolution_summary_v1.csv"
IN_ECOLOGY_EVIDENCE = DATA / "edgeiq_ecology_evidence_summary_v1.csv"
IN_GOVERNANCE_SUMMARY = DATA / "edgeiq_ecology_governance_summary_v1.csv"
IN_LEDGER_SUMMARY = DATA / "edgeiq_ecology_research_ledger_summary_v1.csv"
IN_ORCHESTRATOR_SUMMARY = DATA / "edgeiq_ecology_orchestrator_summary_v1.csv"
IN_MASTER_MEMORY_SUMMARY = DATA / "edgeiq_ecology_master_memory_orchestrator_summary_v2.csv"
IN_AUDIT_SUMMARY = DATA / "edgeiq_ecology_research_audit_summary_v1.csv"
IN_SNAPSHOT_SUMMARY = DATA / "edgeiq_ecology_snapshot_summary_v1.csv"
IN_TEMPORAL_DRIFT = DATA / "edgeiq_ecology_temporal_drift_summary_v1.csv"
IN_MEMORY_DECAY = DATA / "edgeiq_ecology_memory_decay_summary_v1.csv"
IN_MEMORY_PRESSURE = DATA / "edgeiq_ecology_memory_pressure_summary_v1.csv"
IN_MEMORY_CONFIDENCE = DATA / "edgeiq_ecology_memory_confidence_summary_v1.csv"
IN_MEMORY_MATURITY = DATA / "edgeiq_ecology_memory_maturity_summary_v1.csv"
IN_MEMORY_RESILIENCE = DATA / "edgeiq_ecology_memory_resilience_summary_v1.csv"
IN_MEMORY_STRESS = DATA / "edgeiq_ecology_memory_stress_summary_v1.csv"
IN_MEMORY_RECOVERY = DATA / "edgeiq_ecology_memory_recovery_summary_v1.csv"

IN_EVOLUTION_ROWS = DATA / "edgeiq_ecology_temporal_evolution_v1.csv"
IN_ALERT_ROWS = DATA / "edgeiq_ecology_evolution_alerts_v1.csv"
IN_STABILITY = DATA / "edgeiq_ecology_stability_index_v1.csv"
IN_EVIDENCE_ROWS = DATA / "edgeiq_ecology_evidence_accumulation_v1.csv"
IN_GOVERNANCE_ROWS = DATA / "edgeiq_ecology_governance_gate_v1.csv"
IN_LEDGER_ROWS = DATA / "edgeiq_ecology_research_ledger_v1.csv"

OUT_FEED = DATA / "edgeiq_research_command_feed_v1.csv"
OUT_CARDS = DATA / "edgeiq_research_command_cards_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_research_command_summary_v1.csv"

ENGINE_VERSION = "EDGEIQ_RESEARCH_COMMAND_FEED_V1"
BOUNDARY = "OFFLINE_RESEARCH_ONLY"

CARD_FIELDS = [
    "card_rank",
    "card_title",
    "card_type",
    "headline_metric",
    "headline_value",
    "secondary_metric",
    "secondary_value",
    "status",
    "severity",
    "recommended_action",
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


def parse_int(value: object) -> int:
    try:
        return int(float(clean(value).replace(",", "") or 0))
    except ValueError:
        return 0


def metric_map(path: Path) -> dict[str, str]:
    return {clean(row.get("metric")): clean(row.get("value")) for row in safe_read_csv(path) if clean(row.get("metric"))}


def metric(metrics: dict[str, str], key: str, default: str = "0") -> str:
    value = metrics.get(key, default)
    return value if clean(value) else default


def severity_for(value: object) -> str:
    status = upper(value)
    warn_tokens = ["SKIPPED", "FAIL", "WARN", "DEGRADED", "WATCHLIST", "HOLD", "MUTATION", "ELEVATED", "DRIFT", "LOW", "FRAGILE", "PRESSURE", "STRESS", "EARLY"]
    if any(token in status for token in warn_tokens):
        return "WARN"
    return "NORMAL"


def card(rank: int, title: str, card_type: str, headline_metric: str, headline_value: str, secondary_metric: str, secondary_value: str, status: str, severity: str, action: str, timestamp: str) -> dict[str, str]:
    return {
        "card_rank": str(rank),
        "card_title": title,
        "card_type": card_type,
        "headline_metric": headline_metric,
        "headline_value": headline_value,
        "secondary_metric": secondary_metric,
        "secondary_value": secondary_value,
        "status": status,
        "severity": severity,
        "recommended_action": action,
        "research_boundary": BOUNDARY,
        "live_modelling_yes": "0",
        "live_execution_yes": "0",
        "engine_version": ENGINE_VERSION,
        "timestamp_utc": timestamp,
    }


def memory_health_cards(start_rank: int, timestamp: str) -> list[dict[str, str]]:
    sources = [
        ("Master Memory Stack", "MASTER_MEMORY_STACK", IN_MASTER_MEMORY_SUMMARY, "overall_stack_health", "pipeline_steps", "pipeline_passed", "Run offline memory stack checks only."),
        ("Temporal Memory", "TEMPORAL_MEMORY_HEALTH", IN_TEMPORAL_DRIFT, "overall_temporal_memory_health", "snapshot_count", "structures_tracked", "Watch temporal drift without operational use."),
        ("Memory Decay", "MEMORY_DECAY_HEALTH", IN_MEMORY_DECAY, "overall_decay_health", "low_decay_risk_rows", "high_decay_risk_rows", "Monitor decay risk across archived ecology structures."),
        ("Memory Pressure", "MEMORY_PRESSURE_HEALTH", IN_MEMORY_PRESSURE, "overall_pressure_health", "low_pressure_rows", "high_pressure_rows", "Track ecology pressure as offline evidence quality."),
        ("Memory Confidence", "MEMORY_CONFIDENCE_HEALTH", IN_MEMORY_CONFIDENCE, "overall_confidence_health", "fragile_confidence_rows", "high_confidence_rows", "Keep confidence state descriptive and bounded."),
        ("Memory Maturity", "MEMORY_MATURITY_HEALTH", IN_MEMORY_MATURITY, "overall_maturity_health", "early_memory_rows", "mature_memory_rows", "Use maturity to prioritise more observations."),
        ("Memory Resilience", "MEMORY_RESILIENCE_HEALTH", IN_MEMORY_RESILIENCE, "overall_resilience_health", "low_resilience_rows", "high_resilience_rows", "Stress resilience remains offline research only."),
        ("Memory Stress", "MEMORY_STRESS_HEALTH", IN_MEMORY_STRESS, "overall_stress_health", "stress_rows", "fails_stress_rows", "Stress scenarios are diagnostics only."),
        ("Memory Recovery", "MEMORY_RECOVERY_HEALTH", IN_MEMORY_RECOVERY, "overall_recovery_health", "low_recovery_rows", "high_recovery_rows", "Recovery state is monitored without promotion."),
    ]
    rows: list[dict[str, str]] = []
    for offset, (title, card_type, path, health_key, primary_key, secondary_key, action) in enumerate(sources):
        metrics = metric_map(path)
        health = metric(metrics, health_key, "UNKNOWN")
        rows.append(
            card(
                start_rank + offset,
                title,
                card_type,
                health_key,
                health,
                primary_key,
                f"{metric(metrics, primary_key)} / {secondary_key} {metric(metrics, secondary_key)}",
                health,
                severity_for(health),
                action,
                timestamp,
            )
        )
    return rows


def build_cards() -> list[dict[str, str]]:
    timestamp = utc_now()
    asset = metric_map(IN_ASSET_SCHEMA)
    ontology = metric_map(IN_ONTOLOGY)
    transition = metric_map(IN_TRANSITION)
    persistence = metric_map(IN_PERSISTENCE)
    ecology_drift = metric_map(IN_ECOLOGY_DRIFT)
    ecology_memory = metric_map(IN_ECOLOGY_MEMORY)
    evolution = metric_map(IN_ECOLOGY_EVOLUTION)
    evidence = metric_map(IN_ECOLOGY_EVIDENCE)
    governance = metric_map(IN_GOVERNANCE_SUMMARY)
    ledger = metric_map(IN_LEDGER_SUMMARY)
    orchestrator = metric_map(IN_ORCHESTRATOR_SUMMARY)
    audit = metric_map(IN_AUDIT_SUMMARY)
    snapshot = metric_map(IN_SNAPSHOT_SUMMARY)

    evolution_rows = safe_read_csv(IN_EVOLUTION_ROWS)
    alert_rows = safe_read_csv(IN_ALERT_ROWS)
    stability_rows = safe_read_csv(IN_STABILITY)
    evidence_rows = safe_read_csv(IN_EVIDENCE_ROWS)
    governance_rows = safe_read_csv(IN_GOVERNANCE_ROWS)
    ledger_rows = safe_read_csv(IN_LEDGER_ROWS)
    rockhampton = next((row for row in evolution_rows if upper(row.get("track")) == "ROCKHAMPTON"), {})
    mackay = next((row for row in evolution_rows if upper(row.get("track")) == "MACKAY"), {})
    top_evidence = next((row for row in evidence_rows if clean(row.get("priority_rank")) == "1"), evidence_rows[0] if evidence_rows else {})
    top_gate = next((row for row in governance_rows if clean(row.get("governance_rank")) == "1"), governance_rows[0] if governance_rows else {})
    top_ledger = next((row for row in ledger_rows if upper(row.get("track")) == upper(metric(ledger, "top_ledger_track"))), ledger_rows[0] if ledger_rows else {})

    cards = [
        card(1, "Ecology Audit", "AUDIT_HEALTH", "status", metric(audit, "overall_status", "UNKNOWN"), "checks", f"{metric(audit, 'pass_count')}/{metric(audit, 'audit_rows')}", metric(audit, "overall_status", "UNKNOWN"), severity_for(metric(audit, "overall_status")), "Use audit health as the boundary and integrity lock.", timestamp),
        card(2, "Snapshot Archive", "SNAPSHOT_ARCHIVE", "status", metric(snapshot, "archive_status", "UNKNOWN"), "rows", metric(snapshot, "snapshot_rows_added"), metric(snapshot, "latest_snapshot_id", "NO_SNAPSHOT"), severity_for(metric(snapshot, "archive_status")), "Use snapshots for time comparison only after audit pass.", timestamp),
        card(3, "Ecology Orchestrator", "ORCHESTRATOR_HEALTH", "health", metric(orchestrator, "health_status", "UNKNOWN"), "scripts", f"{metric(orchestrator, 'steps_passed')}/{metric(orchestrator, 'steps_run')}", metric(orchestrator, "health_status", "UNKNOWN"), severity_for(metric(orchestrator, "health_status")), "Use orchestrator health as the research stack readiness indicator.", timestamp),
        card(4, "QLD Schema Discovery", "SCHEMA", "assets inspected", metric(asset, "assets_inspected"), "candidate rows", metric(asset, "candidate_rows"), "SOURCE MAP READY", "NORMAL", "Keep inspecting only named local/source assets.", timestamp),
        card(5, "Ontology Fragments", "ONTOLOGY", "ontology fragments", metric(ontology, "total_fragments"), "ontology classes", metric(ontology, "ontology_classes"), "FRAGMENT MEMORY ACTIVE", "NORMAL", "Continue fragment classification before any cross-jurisdiction assumptions.", timestamp),
        card(6, "Transition Chains", "TRANSITION", "transition rows", metric(transition, "transition_rows", metric(transition, "transition_chain_rows", metric(transition, "profiles_loaded"))), "profile rows", metric(transition, "transition_profiles", metric(transition, "profiles_loaded")), "CHAIN RESEARCH ONLY", "NORMAL", "Keep transition chains in offline ecology research.", timestamp),
        card(7, "Persistence Memory", "PERSISTENCE", "persistence rows", metric(persistence, "persistence_rows", metric(ecology_drift, "persistence_rows_loaded")), "memory rows", metric(ecology_memory, "memory_rows"), "MEMORY ACCUMULATING", "NORMAL", "Use persistence memory only for research prioritisation.", timestamp),
        card(8, "Ecology Drift", "ECOLOGY_DRIFT", "drift rows", metric(ecology_drift, "drift_rows"), "alert rows", metric(ecology_drift, "alert_rows"), "DRIFT WATCH", "WARN" if parse_int(metric(ecology_drift, "alert_rows")) else "NORMAL", "Watch track ecology drift without creating operational actions.", timestamp),
        card(9, "Ecology Climate", "ECOLOGY_CLIMATE", "climate rows", metric(ecology_memory, "climate_rows"), "stability rows", metric(ecology_memory, "stability_rows"), "CLIMATE MEMORY ACTIVE", "NORMAL", "Maintain Rockhampton and Mackay as transparent climate observations.", timestamp),
        card(10, "Temporal Evolution", "TEMPORAL_EVOLUTION", "PERSISTENCE", clean(rockhampton.get("track")) or metric(evolution, "persistence_tracks"), "STABILISATION", clean(mackay.get("track")) or metric(evolution, "stabilisation_tracks"), "LIFECYCLE CLASSIFIED", "WARN" if alert_rows else "NORMAL", "Continue lifecycle tracking inside the offline research boundary.", timestamp),
        card(11, "Evidence Maturity", "EVIDENCE_MATURITY", "top structure", clean(top_evidence.get("track")) or metric(evidence, "top_research_structure"), "maturity", clean(top_evidence.get("research_maturity_class")) or metric(evidence, "top_research_maturity"), "EVIDENCE PRIORITISED", severity_for(metric(evidence, "mutation_watchlist_top")), "Use maturity scores to schedule more ecology observations.", timestamp),
        card(12, "Governance Gate", "GOVERNANCE_GATE", "core approved", metric(governance, "approved_core_research"), "watch/held", str(parse_int(metric(governance, "watchlist_only")) + parse_int(metric(governance, "hold_for_more_evidence"))), clean(top_gate.get("governance_gate_status")) or metric(governance, "top_governance_status"), severity_for(metric(governance, "watchlist_only")), "Use gate status to control display, watch, hold, and rejection boundaries.", timestamp),
        card(13, "Research Ledger", "RESEARCH_LEDGER", "ledger rows", metric(ledger, "ledger_rows"), "top status", clean(top_ledger.get("governance_status")) or metric(ledger, "top_ledger_status"), "LEDGER SOURCE ACTIVE", severity_for(metric(ledger, "approved_for_research_watchlist")), "Use the ledger as the research command centre audit source.", timestamp),
        card(14, "Governance Boundary", "GOVERNANCE", "research boundary", BOUNDARY, "live flags", "0 / 0", "LOCKED OFFLINE", "NORMAL", "Offline research boundary remains locked.", timestamp),
    ]

    cards.extend(memory_health_cards(len(cards) + 1, timestamp))

    for row in evolution_rows:
        cards.append(card(len(cards) + 1, f"{clean(row.get('track'))} Lifecycle", "TRACK_LIFECYCLE", clean(row.get("lifecycle_phase")), clean(row.get("stability_score")), clean(row.get("mutation_risk")), clean(row.get("evolution_confidence")), clean(row.get("current_climate")), severity_for(row.get("mutation_risk")), clean(row.get("recommended_research_action")), timestamp))
    for row in stability_rows:
        cards.append(card(len(cards) + 1, f"{clean(row.get('track'))} Stability Index", "STABILITY_INDEX", "stability score", clean(row.get("stability_score")), "drift risk", clean(row.get("drift_risk")), clean(row.get("climate")), "WARN" if upper(row.get("drift_risk")) != "LOW" else "NORMAL", "Use stability index for offline monitoring only.", timestamp))
    for row in evidence_rows:
        cards.append(card(len(cards) + 1, f"{clean(row.get('track'))} Evidence", "ECOLOGY_EVIDENCE", clean(row.get("research_maturity_class")), clean(row.get("research_priority_score")), clean(row.get("lifecycle_phase")), clean(row.get("evolution_confidence")), clean(row.get("climate")), severity_for(row.get("research_maturity_class")), clean(row.get("recommended_research_action")), timestamp))
    for row in governance_rows:
        cards.append(card(len(cards) + 1, f"{clean(row.get('track'))} Gate", "ECOLOGY_GOVERNANCE", clean(row.get("governance_gate_status")), clean(row.get("gate_confidence")), "blocked", f"{clean(row.get('blocked_from_modelling'))}/{clean(row.get('blocked_from_execution'))}", clean(row.get("governance_gate_status")), severity_for(row.get("governance_gate_status")), clean(row.get("recommended_research_action")), timestamp))
    for row in ledger_rows:
        cards.append(card(len(cards) + 1, f"{clean(row.get('track'))} Ledger", "ECOLOGY_LEDGER", clean(row.get("approved_for_research")), clean(row.get("evidence_score")), clean(row.get("governance_status")), f"{clean(row.get('approved_for_modelling'))}/{clean(row.get('approved_for_execution'))}", clean(row.get("governance_status")), severity_for(row.get("approved_for_research")), "Read from ecology research ledger; preserve offline boundary.", timestamp))

    return cards


def build_feed() -> None:
    cards = build_cards()
    memory_types = {
        "MASTER_MEMORY_STACK",
        "TEMPORAL_MEMORY_HEALTH",
        "MEMORY_DECAY_HEALTH",
        "MEMORY_PRESSURE_HEALTH",
        "MEMORY_CONFIDENCE_HEALTH",
        "MEMORY_MATURITY_HEALTH",
        "MEMORY_RESILIENCE_HEALTH",
        "MEMORY_STRESS_HEALTH",
        "MEMORY_RECOVERY_HEALTH",
    }
    summary = [
        {"metric": "feed_rows", "value": str(len(cards))},
        {"metric": "card_rows", "value": str(len(cards))},
        {"metric": "audit_health_cards", "value": str(sum(1 for row in cards if row["card_type"] == "AUDIT_HEALTH"))},
        {"metric": "snapshot_archive_cards", "value": str(sum(1 for row in cards if row["card_type"] == "SNAPSHOT_ARCHIVE"))},
        {"metric": "orchestrator_health_cards", "value": str(sum(1 for row in cards if row["card_type"] == "ORCHESTRATOR_HEALTH"))},
        {"metric": "memory_stack_cards", "value": str(sum(1 for row in cards if row["card_type"] in memory_types))},
        {"metric": "memory_stack_warn_cards", "value": str(sum(1 for row in cards if row["card_type"] in memory_types and row["severity"] == "WARN"))},
        {"metric": "governance_cards", "value": str(sum(1 for row in cards if row["card_type"] == "GOVERNANCE"))},
        {"metric": "governance_gate_cards", "value": str(sum(1 for row in cards if row["card_type"] in {"GOVERNANCE_GATE", "ECOLOGY_GOVERNANCE"}))},
        {"metric": "research_ledger_cards", "value": str(sum(1 for row in cards if row["card_type"] in {"RESEARCH_LEDGER", "ECOLOGY_LEDGER"}))},
        {"metric": "temporal_evolution_cards", "value": str(sum(1 for row in cards if row["card_type"] == "TEMPORAL_EVOLUTION"))},
        {"metric": "evidence_maturity_cards", "value": str(sum(1 for row in cards if row["card_type"] in {"EVIDENCE_MATURITY", "ECOLOGY_EVIDENCE"}))},
        {"metric": "track_lifecycle_cards", "value": str(sum(1 for row in cards if row["card_type"] == "TRACK_LIFECYCLE"))},
        {"metric": "stability_index_cards", "value": str(sum(1 for row in cards if row["card_type"] == "STABILITY_INDEX"))},
        {"metric": "warning_cards", "value": str(sum(1 for row in cards if row["severity"] == "WARN"))},
        {"metric": "offline_research_only", "value": "YES"},
        {"metric": "live_modelling_yes", "value": "0"},
        {"metric": "live_execution_yes", "value": "0"},
        {"metric": "engine_version", "value": ENGINE_VERSION},
    ]
    write_csv_atomic(OUT_FEED, cards, CARD_FIELDS)
    write_csv_atomic(OUT_CARDS, cards, CARD_FIELDS)
    write_csv_atomic(OUT_SUMMARY, summary, SUMMARY_FIELDS)
    print(f"Research command feed rows: {len(cards)}")
    print(f"Warning cards: {sum(1 for row in cards if row['severity'] == 'WARN')}")
    print("Live modelling: 0")
    print("Live execution: 0")


if __name__ == "__main__":
    build_feed()
