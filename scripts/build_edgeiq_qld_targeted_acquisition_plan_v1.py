from __future__ import annotations

from collections import Counter
from pathlib import Path

from edgeiq_memory_safe_io import safe_read_csv, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

IN_TARGETS = DATA / "edgeiq_telemetry_accumulation_targets_v1.csv"
IN_LINEAGE = DATA / "edgeiq_qld_telemetry_lineage_v1.csv"
IN_INGESTION_SUMMARY = DATA / "edgeiq_qld_telemetry_ingestion_summary_v1.csv"
IN_POSITIONAL_SUMMARY = DATA / "edgeiq_qld_positional_telemetry_summary_v1.csv"
IN_PROMOTIONS = DATA / "edgeiq_research_priority_promotions_v1.csv"

OUT_PLAN = DATA / "edgeiq_qld_targeted_acquisition_plan_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_qld_targeted_acquisition_summary_v1.csv"

PLAN_FIELDS = [
    "priority_rank",
    "track",
    "target_reason",
    "source_type",
    "needed_data",
    "linked_regime_archetype",
    "linked_transition_pair",
    "evidence_gap",
    "collection_method",
    "expected_research_value",
    "risk",
    "recommended_action",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

OFFLINE_NOTE = (
    "QLD acquisition planning only. No modelling, predictions, overlays, ratings, betting, live execution, "
    "or cross-jurisdiction merge is enabled."
)


def clean(value: object) -> str:
    return str(value or "").strip()


def upper(value: object) -> str:
    return clean(value).upper()


def parse_int(value: object) -> int:
    try:
        return int(float(clean(value).replace(",", "") or 0))
    except ValueError:
        return 0


def metric_map(rows: list[dict[str, str]]) -> dict[str, str]:
    return {clean(row.get("metric")): clean(row.get("value")) for row in rows if clean(row.get("metric"))}


def priority_weight(priority: str) -> int:
    return {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(upper(priority), 9)


def make_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        upper(row.get("track")),
        upper(row.get("linked_regime_archetype")),
        upper(row.get("linked_transition_pair")),
    )


def infer_collection_method(row: dict[str, str], ingestion: dict[str, str], positional: dict[str, str]) -> str:
    gap = upper(row.get("evidence_gap"))
    regime = upper(row.get("linked_regime_archetype"))
    gps_rows = parse_int(ingestion.get("qld_gps_rows_ingested"))
    explicit_position_rows = parse_int(positional.get("explicit_position_rows"))
    inferred_position_rows = parse_int(positional.get("inferred_position_rows"))
    if "POSITION" in regime or explicit_position_rows == 0 and inferred_position_rows > 0:
        return "STRUCTURED_CSV_PLUS_POSITIONAL_REPAIR"
    if gps_rows > 0 and ("SURVIVAL" in gap or "REINFORCEMENT" in gap):
        return "STRUCTURED_CSV_WITH_GPS_CONTINUITY"
    return "STRUCTURED_SECTIONAL_CSV_COLLECTION"


def infer_needed_data(row: dict[str, str], method: str) -> str:
    base = clean(row.get("needed_data")) or "QLD structured sectional CSV with full split ladders and GPS fields."
    if method == "STRUCTURED_CSV_PLUS_POSITIONAL_REPAIR":
        return f"{base} Add explicit or better reconstructable position-at-split fields to reduce inferred-only positional dependence."
    if method == "STRUCTURED_CSV_WITH_GPS_CONTINUITY":
        return f"{base} Preserve GPS speed continuity, split order, schema signature, and horse-level timing lineage across repeat meetings."
    return f"{base} Preserve complete split ladders, race identifiers, horse identity, and stable schema signature."


def infer_risk(row: dict[str, str], lineage: dict[str, str], ingestion: dict[str, str], positional: dict[str, str]) -> str:
    risks: list[str] = []
    if upper(lineage.get("schema_stability_status")) != "STABLE_SCHEMA":
        risks.append("SCHEMA_STABILITY_RISK")
    if parse_int(ingestion.get("ingestion_failures")) > 0:
        risks.append("INGESTION_FAILURE_REPAIR_REQUIRED")
    if parse_int(positional.get("explicit_position_rows")) == 0:
        risks.append("POSITIONAL_DATA_INFERRED_ONLY")
    if "SURVIVAL_STABILITY_GAP" in upper(row.get("evidence_gap")):
        risks.append("SURVIVAL_SAMPLE_GAP")
    if "REINFORCEMENT_GAP" in upper(row.get("evidence_gap")):
        risks.append("REINFORCEMENT_SAMPLE_GAP")
    return "; ".join(risks) if risks else "LOW_COLLECTION_RISK"


def expected_value(row: dict[str, str]) -> str:
    priority = upper(row.get("priority"))
    value = upper(row.get("research_value"))
    if priority == "CRITICAL" or value == "CORE_EVIDENCE_ACCUMULATION":
        return "CORE_Qld_RESEARCH_VALUE"
    if priority == "HIGH" or value == "HIGH_VALUE_RESEARCH_ACCUMULATION":
        return "HIGH_Qld_RESEARCH_VALUE"
    if priority == "MEDIUM":
        return "SUPPORTING_Qld_RESEARCH_VALUE"
    return "MONITOR_ONLY"


def recommended_action(row: dict[str, str], method: str) -> str:
    track = clean(row.get("track")) or "QLD target track"
    if method == "STRUCTURED_CSV_PLUS_POSITIONAL_REPAIR":
        return f"Collect the next {track} QLD sectional CSV and run positional extraction QA to convert inferred movement into stronger split-rank lineage."
    if method == "STRUCTURED_CSV_WITH_GPS_CONTINUITY":
        return f"Collect repeat {track} QLD CSVs and verify GPS speed continuity, split ladder completeness, and schema signature stability."
    return f"Collect repeat {track} QLD sectional CSVs and preserve direct source lineage before any research refresh."


def dedupe_targets(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict[str, str]] = []
    for row in rows:
        key = make_key(row)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def build_plan() -> None:
    targets = [row for row in safe_read_csv(IN_TARGETS) if upper(row.get("jurisdiction")) == "QLD"]
    promotions = [row for row in safe_read_csv(IN_PROMOTIONS) if upper(row.get("jurisdiction")) == "QLD"]
    lineage_rows = safe_read_csv(IN_LINEAGE)
    ingestion = metric_map(safe_read_csv(IN_INGESTION_SUMMARY))
    positional = metric_map(safe_read_csv(IN_POSITIONAL_SUMMARY))
    lineage = lineage_rows[0] if lineage_rows else {}

    priority_targets = [row for row in targets if upper(row.get("priority")) in {"CRITICAL", "HIGH"}]
    medium_support = [row for row in targets if upper(row.get("priority")) == "MEDIUM"]
    promotion_keys = {make_key(row) for row in promotions}

    combined: list[dict[str, str]] = []
    for row in priority_targets + medium_support:
        if upper(row.get("priority")) == "MEDIUM" and make_key(row) not in promotion_keys:
            continue
        combined.append(row)

    deduped = dedupe_targets(sorted(combined, key=lambda row: (priority_weight(clean(row.get("priority"))), clean(row.get("track")), clean(row.get("linked_regime_archetype")))))

    plan_rows: list[dict[str, str]] = []
    for index, row in enumerate(deduped, start=1):
        method = infer_collection_method(row, ingestion, positional)
        plan_rows.append(
            {
                "priority_rank": str(index),
                "track": clean(row.get("track")),
                "target_reason": clean(row.get("target_reason")),
                "source_type": clean(row.get("source_type")) or "QLD_STRUCTURED_SECTIONAL_CSV",
                "needed_data": infer_needed_data(row, method),
                "linked_regime_archetype": clean(row.get("linked_regime_archetype")),
                "linked_transition_pair": clean(row.get("linked_transition_pair")),
                "evidence_gap": clean(row.get("evidence_gap")),
                "collection_method": method,
                "expected_research_value": expected_value(row),
                "risk": infer_risk(row, lineage, ingestion, positional),
                "recommended_action": recommended_action(row, method),
                "notes": OFFLINE_NOTE,
            }
        )

    priority_counts = Counter(row["expected_research_value"] for row in plan_rows)
    method_counts = Counter(row["collection_method"] for row in plan_rows)
    track_counts = Counter(row["track"] for row in plan_rows)
    risk_counts = Counter()
    for row in plan_rows:
        for risk in row["risk"].split("; "):
            if risk:
                risk_counts[risk] += 1

    summary = [
        {"metric": "qld_plan_rows", "value": str(len(plan_rows))},
        {"metric": "qld_source_targets", "value": str(len(targets))},
        {"metric": "qld_critical_source_targets", "value": str(sum(1 for row in targets if upper(row.get("priority")) == "CRITICAL"))},
        {"metric": "qld_high_source_targets", "value": str(sum(1 for row in targets if upper(row.get("priority")) == "HIGH"))},
        {"metric": "core_research_value_rows", "value": str(priority_counts.get("CORE_Qld_RESEARCH_VALUE", 0))},
        {"metric": "high_research_value_rows", "value": str(priority_counts.get("HIGH_Qld_RESEARCH_VALUE", 0))},
        {"metric": "supporting_research_value_rows", "value": str(priority_counts.get("SUPPORTING_Qld_RESEARCH_VALUE", 0))},
        {"metric": "structured_sectional_collection_rows", "value": str(method_counts.get("STRUCTURED_SECTIONAL_CSV_COLLECTION", 0))},
        {"metric": "gps_continuity_rows", "value": str(method_counts.get("STRUCTURED_CSV_WITH_GPS_CONTINUITY", 0))},
        {"metric": "positional_repair_rows", "value": str(method_counts.get("STRUCTURED_CSV_PLUS_POSITIONAL_REPAIR", 0))},
        {"metric": "tracks_targeted", "value": str(len(track_counts))},
        {"metric": "top_track", "value": track_counts.most_common(1)[0][0] if track_counts else ""},
        {"metric": "qld_rows_ingested", "value": ingestion.get("qld_rows_ingested", "0")},
        {"metric": "qld_split_rows_ingested", "value": ingestion.get("qld_split_rows_ingested", "0")},
        {"metric": "qld_gps_rows_ingested", "value": ingestion.get("qld_gps_rows_ingested", "0")},
        {"metric": "qld_position_rows_ingested", "value": ingestion.get("qld_position_rows_ingested", "0")},
        {"metric": "explicit_position_rows", "value": positional.get("explicit_position_rows", "0")},
        {"metric": "inferred_position_rows", "value": positional.get("inferred_position_rows", "0")},
        {"metric": "position_inferred_only_risk_rows", "value": str(risk_counts.get("POSITIONAL_DATA_INFERRED_ONLY", 0))},
        {"metric": "ingestion_failure_risk_rows", "value": str(risk_counts.get("INGESTION_FAILURE_REPAIR_REQUIRED", 0))},
        {"metric": "live_modelling_yes", "value": "0"},
        {"metric": "live_execution_yes", "value": "0"},
        {"metric": "offline_research_only", "value": "YES"},
    ]

    write_csv_atomic(OUT_PLAN, plan_rows, PLAN_FIELDS)
    write_csv_atomic(OUT_SUMMARY, summary, SUMMARY_FIELDS)

    print(f"QLD acquisition plan rows: {len(plan_rows)}")
    print(f"Tracks targeted: {len(track_counts)}")
    print(f"Positional repair rows: {method_counts.get('STRUCTURED_CSV_PLUS_POSITIONAL_REPAIR', 0)}")
    print("Live modelling: 0")
    print("Live execution: 0")


if __name__ == "__main__":
    build_plan()
