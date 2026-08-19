from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from edgeiq_memory_safe_io import safe_read_csv, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

IN_PROMOTIONS = DATA / "edgeiq_research_priority_promotions_v1.csv"
IN_PRIORITY_BOARD = DATA / "edgeiq_research_priority_board_v1.csv"
IN_LONGITUDINAL = DATA / "edgeiq_longitudinal_evidence_accumulation_v1.csv"
IN_WA_LINEAGE = DATA / "edgeiq_wa_telemetry_lineage_v1.csv"
IN_QLD_LINEAGE = DATA / "edgeiq_qld_telemetry_lineage_v1.csv"
IN_NSW_RANK_SUMMARY = DATA / "edgeiq_nsw_positional_rank_summary_v2.csv"

OUT_TARGETS = DATA / "edgeiq_telemetry_accumulation_targets_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_telemetry_accumulation_summary_v1.csv"

TARGET_FIELDS = [
    "priority",
    "jurisdiction",
    "track",
    "target_reason",
    "source_type",
    "needed_data",
    "linked_regime_archetype",
    "linked_transition_pair",
    "evidence_gap",
    "recommended_collection_action",
    "research_value",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

ALLOWED_JURISDICTIONS = {"VIC", "WA", "QLD", "NSW"}
EXCLUDED_JURISDICTIONS = {"SA", "TAS"}
OFFLINE_NOTE = (
    "Offline telemetry accumulation target only. No predictions, overlays, ratings, live modelling, betting, "
    "or execution are enabled by this file."
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


def parse_float(value: object) -> float:
    try:
        return float(clean(value).replace(",", "") or 0)
    except ValueError:
        return 0.0


def metric_map(rows: list[dict[str, str]]) -> dict[str, str]:
    return {clean(row.get("metric")): clean(row.get("value")) for row in rows if clean(row.get("metric"))}


def priority_rank(value: float) -> str:
    if value >= 85:
        return "CRITICAL"
    if value >= 72:
        return "HIGH"
    if value >= 55:
        return "MEDIUM"
    return "LOW"


def research_value(score: float) -> str:
    if score >= 85:
        return "CORE_EVIDENCE_ACCUMULATION"
    if score >= 72:
        return "HIGH_VALUE_RESEARCH_ACCUMULATION"
    if score >= 55:
        return "USEFUL_LONGITUDINAL_ACCUMULATION"
    return "MONITOR_ONLY"


def source_type_for(jurisdiction: str, track: str, lineage: dict[str, dict[str, str]]) -> str:
    jurisdiction = jurisdiction.upper()
    if jurisdiction == "QLD":
        return "QLD_STRUCTURED_SECTIONAL_CSV"
    if jurisdiction == "WA":
        source_kind = clean(lineage.get("WA", {}).get("source_kind"))
        if "XLSX" in source_kind.upper():
            return "WA_XLSX_SECTIONAL_ARTEFACT"
        return "WA_SECTIONAL_WAREHOUSE_SOURCE"
    if jurisdiction == "NSW":
        return "NSW_ATC_SECTIONAL_PDF_POSITION_RANK"
    if jurisdiction == "VIC":
        return "VIC_RACINGCOM_SECTIONAL_TELEMETRY"
    return f"{jurisdiction}_TELEMETRY_SOURCE"


def needed_data_for(jurisdiction: str, row: dict[str, str]) -> str:
    jurisdiction = jurisdiction.upper()
    category = upper(row.get("research_category"))
    regime = upper(row.get("regime_archetype"))
    if jurisdiction == "NSW":
        return "Targeted PDF sectional reports with bracketed rank ladders, split times, top speed, distance travelled, and finish metadata."
    if jurisdiction == "QLD":
        return "Daily structured sectional CSVs with full split ladders, GPS speed, horse-level timing continuity, and stable schema signatures."
    if jurisdiction == "WA":
        return "WA source artefacts with race/horse identity, split ladders, position rows, and source lineage strong enough for repeat observations."
    if jurisdiction == "VIC":
        return "VIC race telemetry with direct source payloads, complete early/mid/late chains, and repeat evidence for stable regimes."
    if "STRENGTHENING" in category or "HIGH_TRUST" in regime:
        return "Repeat telemetry snapshots with lineage, split ladders, and confidence persistence fields."
    return "Repeat behavioural telemetry evidence with stable identity and source lineage."


def collection_action_for(jurisdiction: str, priority: str, evidence_gap: str) -> str:
    jurisdiction = jurisdiction.upper()
    if jurisdiction == "NSW":
        return "Collect a small targeted sample of ATC/Racing NSW PDF sectionals and rerun positional-rank extraction; keep isolated from VIC/QLD/WA."
    if jurisdiction == "QLD":
        return "Collect next QLD meeting CSVs from existing structured source; prioritise repeat track coverage and schema stability checks."
    if jurisdiction == "WA":
        return "Collect WA sectional artefacts only where lineage can be preserved; prioritise source-specific parser repair before expansion."
    if jurisdiction == "VIC":
        return "Collect VIC Racing.com-style sectionals for high-priority regimes and improve direct payload lineage where available."
    if priority in {"CRITICAL", "HIGH"}:
        return f"Collect targeted telemetry for this environment; evidence gap: {evidence_gap}."
    return "Monitor only until this environment rises in the research priority board."


def evidence_gap_for(row: dict[str, str], longitudinal_index: dict[tuple[str, str, str, str], dict[str, str]]) -> str:
    key = make_key(row)
    evidence = parse_int(row.get("evidence_rows"))
    survival = parse_float(row.get("survival_score"))
    reinforcement = parse_float(row.get("reinforcement_score"))
    confidence_decay = parse_float(row.get("confidence_decay_risk"))
    longitudinal = longitudinal_index.get(key, {})
    status = upper(longitudinal.get("longitudinal_status"))
    gaps: list[str] = []
    if evidence < 1000:
        gaps.append("LOW_REPEAT_EVIDENCE")
    if survival < 75:
        gaps.append("SURVIVAL_STABILITY_GAP")
    if reinforcement < 70:
        gaps.append("REINFORCEMENT_GAP")
    if confidence_decay >= 25:
        gaps.append("CONFIDENCE_DECAY_RISK")
    if status in {"WEAKENING", "DECAYING", "UNSTABLE", "NOISY"}:
        gaps.append(f"LONGITUDINAL_{status}")
    return "; ".join(gaps) if gaps else "REPEAT_SAMPLE_GROWTH"


def make_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        upper(row.get("jurisdiction")),
        upper(row.get("track")),
        upper(row.get("regime_archetype")),
        upper(row.get("transition_pair")),
    )


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str, str, str]] = set()
    deduped: list[dict[str, str]] = []
    for row in rows:
        key = (
            upper(row.get("jurisdiction")),
            upper(row.get("track")),
            upper(row.get("source_type")),
            upper(row.get("linked_regime_archetype")),
            upper(row.get("linked_transition_pair")),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def build_lineage_index(wa_rows: list[dict[str, str]], qld_rows: list[dict[str, str]], nsw_summary: dict[str, str]) -> dict[str, dict[str, str]]:
    lineage: dict[str, dict[str, str]] = {}
    if qld_rows:
        best = max(qld_rows, key=lambda row: parse_int(row.get("rows_ingested")) + parse_int(row.get("split_rows_ingested")))
        lineage["QLD"] = best
    if wa_rows:
        best = max(wa_rows, key=lambda row: parse_int(row.get("rows_ingested")) + parse_int(row.get("position_rows_ingested")))
        lineage["WA"] = best
    if nsw_summary:
        lineage["NSW"] = {
            "source_kind": "NSW_ATC_PDF_POSITIONAL_RANK",
            "rows_ingested": nsw_summary.get("rank_rows_detected", "0"),
            "split_rows_ingested": nsw_summary.get("sectional_rows_processed", "0"),
            "position_rows_ingested": nsw_summary.get("rank_rows_detected", "0"),
            "ingestion_quality_grade": "B" if parse_int(nsw_summary.get("high_confidence_rank_rows")) else "D",
            "lineage_status": "TARGETED_NSW_POSITIONAL_SAMPLE",
            "recommended_next_step": "Collect targeted ATC/Racing NSW PDF samples only; keep isolated.",
        }
    return lineage


def score_target(row: dict[str, str], lineage: dict[str, dict[str, str]]) -> float:
    jurisdiction = upper(row.get("jurisdiction"))
    score = parse_float(row.get("research_priority_score"))
    grade = upper(row.get("priority_grade"))
    category = upper(row.get("research_category"))
    evidence = parse_int(row.get("evidence_rows"))
    repeat = parse_int(row.get("repeat_count"))
    if grade == "A":
        score += 12
    elif grade == "B":
        score += 8
    elif grade == "C":
        score += 3
    if "STRENGTHENING" in category:
        score += 8
    if "DURABLE" in category:
        score += 12
    if evidence < 1000:
        score += 6
    if repeat < 40:
        score += 3
    lineage_grade = upper(lineage.get(jurisdiction, {}).get("ingestion_quality_grade"))
    if lineage_grade in {"A", "B"}:
        score += 5
    elif lineage_grade in {"D", "F"}:
        score -= 5
    if jurisdiction == "NSW":
        score = min(score, 68)
    if jurisdiction in EXCLUDED_JURISDICTIONS:
        score = 0
    return max(0.0, min(100.0, score))


def build_target_from_priority(row: dict[str, str], lineage: dict[str, dict[str, str]], longitudinal_index: dict[tuple[str, str, str, str], dict[str, str]]) -> dict[str, str]:
    jurisdiction = upper(row.get("jurisdiction")) or "VIC"
    track = clean(row.get("track")) or "ALL_TRACKS"
    score = score_target(row, lineage)
    priority = priority_rank(score)
    gap = evidence_gap_for(row, longitudinal_index)
    return {
        "priority": priority,
        "jurisdiction": jurisdiction,
        "track": track,
        "target_reason": f"{clean(row.get('research_category')) or 'RESEARCH_STRUCTURE'} with priority score {parse_float(row.get('research_priority_score')):.2f}.",
        "source_type": source_type_for(jurisdiction, track, lineage),
        "needed_data": needed_data_for(jurisdiction, row),
        "linked_regime_archetype": clean(row.get("regime_archetype")),
        "linked_transition_pair": clean(row.get("transition_pair")),
        "evidence_gap": gap,
        "recommended_collection_action": collection_action_for(jurisdiction, priority, gap),
        "research_value": research_value(score),
        "notes": OFFLINE_NOTE,
    }


def build_gap_targets(longitudinal_rows: list[dict[str, str]], lineage: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in longitudinal_rows:
        jurisdiction = upper(row.get("jurisdiction"))
        if jurisdiction not in ALLOWED_JURISDICTIONS or jurisdiction in EXCLUDED_JURISDICTIONS:
            continue
        status = upper(row.get("longitudinal_status"))
        grade = upper(row.get("longitudinal_grade"))
        if status not in {"SURVIVING", "STRENGTHENING"} and grade not in {"A", "B"}:
            continue
        gap = evidence_gap_for(row, {make_key(row): row})
        score = min(100.0, parse_float(row.get("survival_score")) * 0.45 + parse_float(row.get("reinforcement_score")) * 0.35 + parse_float(row.get("avg_confidence")) * 0.20)
        priority = priority_rank(score)
        rows.append(
            {
                "priority": priority,
                "jurisdiction": jurisdiction,
                "track": clean(row.get("track")) or "ALL_TRACKS",
                "target_reason": f"Longitudinal {status or grade} environment requires repeat evidence accumulation.",
                "source_type": source_type_for(jurisdiction, clean(row.get("track")), lineage),
                "needed_data": needed_data_for(jurisdiction, row),
                "linked_regime_archetype": clean(row.get("regime_archetype")),
                "linked_transition_pair": clean(row.get("transition_pair")),
                "evidence_gap": gap,
                "recommended_collection_action": collection_action_for(jurisdiction, priority, gap),
                "research_value": research_value(score),
                "notes": OFFLINE_NOTE,
            }
        )
    return rows


def build_platform_targets(lineage: dict[str, dict[str, str]], nsw_summary: dict[str, str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = [
        {
            "priority": "HIGH",
            "jurisdiction": "VIC",
            "track": "ALL_VIC_PRIORITY_TRACKS",
            "target_reason": "VIC remains the operational base and needs repeat telemetry for high-priority behavioural structures.",
            "source_type": "VIC_RACINGCOM_SECTIONAL_TELEMETRY",
            "needed_data": "Daily VIC meeting sectionals with full split ladders, runner identity, and direct source payload lineage.",
            "linked_regime_archetype": "HIGH_TRUST_TELEMETRY_REGIME",
            "linked_transition_pair": "",
            "evidence_gap": "VIC_REPEAT_SAMPLE_GROWTH",
            "recommended_collection_action": "Collect VIC priority meetings first, then rerun ontology, validation, and longitudinal accumulation offline.",
            "research_value": "HIGH_VALUE_RESEARCH_ACCUMULATION",
            "notes": OFFLINE_NOTE,
        },
        {
            "priority": "HIGH",
            "jurisdiction": "QLD",
            "track": "ALL_Qld_STRUCTURED_TRACKS",
            "target_reason": "QLD structured CSV lineage is strong and should continue feeding isolated longitudinal evidence.",
            "source_type": "QLD_STRUCTURED_SECTIONAL_CSV",
            "needed_data": "Next QLD downloadable sectional CSVs with schema signature, split ladders, GPS speed, and race identifiers.",
            "linked_regime_archetype": "HIGH_TRUST_TELEMETRY_REGIME",
            "linked_transition_pair": "",
            "evidence_gap": "QLD_REPEAT_SAMPLE_GROWTH",
            "recommended_collection_action": "Collect QLD CSVs meeting-by-meeting and keep isolated until schema stability remains proven across more meetings.",
            "research_value": "HIGH_VALUE_RESEARCH_ACCUMULATION",
            "notes": OFFLINE_NOTE,
        },
        {
            "priority": "MEDIUM",
            "jurisdiction": "WA",
            "track": "WA_SOURCE_REPAIR_TARGETS",
            "target_reason": "WA has position-rich artefacts but mixed lineage quality; targeted repair beats broad collection.",
            "source_type": source_type_for("WA", "", lineage),
            "needed_data": "WA sectional artefacts with stronger race/horse/split field mapping and reproducible source lineage.",
            "linked_regime_archetype": "GENERAL_UNCLASSIFIED_REGIME",
            "linked_transition_pair": "",
            "evidence_gap": "WA_LINEAGE_REPAIR_BEFORE_SCALE",
            "recommended_collection_action": "Prioritise WA source parser repair and collect only artefacts with stable schema evidence.",
            "research_value": "USEFUL_LONGITUDINAL_ACCUMULATION",
            "notes": OFFLINE_NOTE,
        },
    ]
    if parse_int(nsw_summary.get("rank_rows_detected")):
        rows.append(
            {
                "priority": "MEDIUM",
                "jurisdiction": "NSW",
                "track": "ATC_TARGETED_PDF_SAMPLE",
                "target_reason": "NSW PDF rank extraction is promising but must stay sample-based and isolated.",
                "source_type": "NSW_ATC_SECTIONAL_PDF_POSITION_RANK",
                "needed_data": "Small targeted set of ATC/Racing NSW sectional PDFs with bracketed ranks, split ladders, top speed, and distance travelled.",
                "linked_regime_archetype": "POSITIONAL_RANK_TELEMETRY_SAMPLE",
                "linked_transition_pair": "",
                "evidence_gap": "NSW_TARGETED_SAMPLE_GROWTH",
                "recommended_collection_action": "Collect only a controlled PDF sample and rerun NSW extraction for rank continuity checks.",
                "research_value": "USEFUL_LONGITUDINAL_ACCUMULATION",
                "notes": OFFLINE_NOTE,
            }
        )
    return rows


def sort_targets(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    return sorted(
        rows,
        key=lambda row: (
            priority_order.get(clean(row.get("priority")), 9),
            clean(row.get("jurisdiction")),
            clean(row.get("track")),
            clean(row.get("linked_regime_archetype")),
        ),
    )


def build_targets() -> None:
    promotions = safe_read_csv(IN_PROMOTIONS)
    priority_board = safe_read_csv(IN_PRIORITY_BOARD)
    longitudinal_rows = safe_read_csv(IN_LONGITUDINAL)
    wa_lineage = safe_read_csv(IN_WA_LINEAGE)
    qld_lineage = safe_read_csv(IN_QLD_LINEAGE)
    nsw_summary = metric_map(safe_read_csv(IN_NSW_RANK_SUMMARY))

    lineage = build_lineage_index(wa_lineage, qld_lineage, nsw_summary)
    longitudinal_index = {make_key(row): row for row in longitudinal_rows}

    candidate_rows: list[dict[str, str]] = []
    for row in promotions + priority_board:
        jurisdiction = upper(row.get("jurisdiction"))
        if not jurisdiction or jurisdiction in EXCLUDED_JURISDICTIONS:
            continue
        if jurisdiction not in ALLOWED_JURISDICTIONS:
            continue
        grade = upper(row.get("priority_grade"))
        category = upper(row.get("research_category"))
        if grade not in {"A", "B", "C"} and category not in {"DURABLE_STRUCTURE", "STRENGTHENING_STRUCTURE", "SURVIVING_STRUCTURE"}:
            continue
        candidate_rows.append(build_target_from_priority(row, lineage, longitudinal_index))

    candidate_rows.extend(build_gap_targets(longitudinal_rows, lineage))
    candidate_rows.extend(build_platform_targets(lineage, nsw_summary))
    targets = sort_targets(dedupe_rows(candidate_rows))

    counts = Counter(row["priority"] for row in targets)
    jurisdiction_counts = Counter(row["jurisdiction"] for row in targets)
    source_counts = Counter(row["source_type"] for row in targets)
    high_value = sum(1 for row in targets if row["research_value"] in {"CORE_EVIDENCE_ACCUMULATION", "HIGH_VALUE_RESEARCH_ACCUMULATION"})

    summary = [
        {"metric": "target_rows", "value": str(len(targets))},
        {"metric": "critical_targets", "value": str(counts.get("CRITICAL", 0))},
        {"metric": "high_targets", "value": str(counts.get("HIGH", 0))},
        {"metric": "medium_targets", "value": str(counts.get("MEDIUM", 0))},
        {"metric": "low_targets", "value": str(counts.get("LOW", 0))},
        {"metric": "high_value_research_targets", "value": str(high_value)},
        {"metric": "vic_targets", "value": str(jurisdiction_counts.get("VIC", 0))},
        {"metric": "qld_targets", "value": str(jurisdiction_counts.get("QLD", 0))},
        {"metric": "wa_targets", "value": str(jurisdiction_counts.get("WA", 0))},
        {"metric": "nsw_targets", "value": str(jurisdiction_counts.get("NSW", 0))},
        {"metric": "sa_targets", "value": "0"},
        {"metric": "tas_targets", "value": "0"},
        {"metric": "qld_lineage_sources", "value": str(len(qld_lineage))},
        {"metric": "wa_lineage_sources", "value": str(len(wa_lineage))},
        {"metric": "nsw_rank_rows_detected", "value": str(parse_int(nsw_summary.get("rank_rows_detected")))},
        {"metric": "source_types", "value": str(len(source_counts))},
        {"metric": "live_modelling_yes", "value": "0"},
        {"metric": "live_execution_yes", "value": "0"},
        {"metric": "offline_research_only", "value": "YES"},
    ]

    write_csv_atomic(OUT_TARGETS, targets, TARGET_FIELDS)
    write_csv_atomic(OUT_SUMMARY, summary, SUMMARY_FIELDS)

    print(f"Telemetry accumulation targets: {len(targets)}")
    print(f"High targets: {counts.get('HIGH', 0)}")
    print(f"Medium targets: {counts.get('MEDIUM', 0)}")
    print("Live modelling: 0")
    print("Live execution: 0")


if __name__ == "__main__":
    build_targets()
