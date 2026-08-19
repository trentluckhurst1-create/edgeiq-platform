from __future__ import annotations

from collections import Counter
from pathlib import Path

from edgeiq_memory_safe_io import safe_read_csv, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

IN_PLAN = DATA / "edgeiq_qld_targeted_acquisition_plan_v1.csv"
IN_FORENSICS = DATA / "edgeiq_qld_telemetry_schema_forensics_v1.csv"
IN_FIELD_DICTIONARY = DATA / "edgeiq_qld_telemetry_field_dictionary_v1.csv"
IN_POSITIONAL_SUMMARY = DATA / "edgeiq_qld_positional_telemetry_summary_v1.csv"

OUT_DISCOVERY = DATA / "edgeiq_qld_positional_source_discovery_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_qld_positional_source_summary_v1.csv"
OUT_REPAIR = DATA / "edgeiq_qld_positional_repair_targets_v1.csv"

DISCOVERY_FIELDS = [
    "track",
    "source_hint",
    "source_type",
    "positional_signal_type",
    "evidence_gap",
    "expected_value",
    "risk",
    "recommended_followup",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

OFFLINE_NOTE = (
    "QLD positional source discovery only. No aggressive scraping, modelling, predictions, overlays, ratings, "
    "betting, live execution, or cross-jurisdiction merge is enabled."
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


def split_pipe(value: object) -> list[str]:
    return [part.strip() for part in clean(value).split("|") if part.strip()]


def classify_source(source_type: str, signal_type: str, explicit_positions: int) -> str:
    signal = signal_type.upper()
    if explicit_positions > 0 or "RUNNING_ORDER" in signal or "POSITION_RANK" in signal:
        return "EXPLICIT_POSITION_SOURCE_CANDIDATE"
    if "GPS" in signal or "COORDINATE" in signal or "MAP" in signal:
        return "GPS_MAP_SOURCE_CANDIDATE"
    if "REPLAY" in signal:
        return "REPLAY_PAYLOAD_CANDIDATE"
    if "EMPTY_RANK" in signal or "SECTIONAL_RANK" in signal:
        return "WEAK_POSITION_SOURCE"
    return source_type


def expected_value(source_class: str, plan_row: dict[str, str]) -> str:
    plan_value = upper(plan_row.get("expected_research_value"))
    if source_class == "EXPLICIT_POSITION_SOURCE_CANDIDATE":
        return "HIGH_VALUE_POSITIONAL_REPAIR"
    if source_class == "GPS_MAP_SOURCE_CANDIDATE":
        return "HIGH_VALUE_GPS_PATH_DISCOVERY"
    if source_class == "REPLAY_PAYLOAD_CANDIDATE":
        return "TARGETED_REPLAY_PAYLOAD_RESEARCH"
    if plan_value.startswith("CORE"):
        return "CORE_RESEARCH_BLOCKER_REPAIR"
    return "SUPPORTING_SOURCE_DISCOVERY"


def risk_for(source_class: str, positional_summary: dict[str, str], field_notes: str) -> str:
    risks: list[str] = []
    if parse_int(positional_summary.get("explicit_position_rows")) == 0:
        risks.append("NO_EXPLICIT_POSITION_ROWS_CURRENTLY")
    if parse_int(positional_summary.get("inferred_position_rows")) > 0:
        risks.append("CURRENT_POSITIONAL_LAYER_INFERRED_ONLY")
    if "empty" in field_notes.lower() or source_class == "WEAK_POSITION_SOURCE":
        risks.append("SOURCE_FIELDS_EMPTY_OR_LATENT")
    if source_class == "REPLAY_PAYLOAD_CANDIDATE":
        risks.append("REPLAY_PAYLOAD_STRUCTURE_UNPROVEN")
    if source_class == "GPS_MAP_SOURCE_CANDIDATE":
        risks.append("GPS_COORDINATE_ENDPOINT_UNCONFIRMED")
    return "; ".join(risks) if risks else "LOW_DISCOVERY_RISK"


def followup_for(source_class: str, track: str, source_hint: str) -> str:
    if source_class == "EXPLICIT_POSITION_SOURCE_CANDIDATE":
        return f"Inspect QLD source for {track} to confirm position/rank fields are populated and can be linked to split markers."
    if source_class == "GPS_MAP_SOURCE_CANDIDATE":
        return f"Map QLD source URL lineage for {track} and look for non-aggressive GPS map, coordinate, or visualisation payload references."
    if source_class == "REPLAY_PAYLOAD_CANDIDATE":
        return f"Inspect cached/local QLD replay or timing page metadata for {track}; do not brute force endpoints."
    if source_class == "WEAK_POSITION_SOURCE":
        return f"Prioritise alternate download/source inspection for {track}; current hint {source_hint} appears latent or empty."
    return f"Keep {track} on low-intensity source discovery queue."


def make_discovery_row(track: str, source_hint: str, source_type: str, signal_type: str, plan_row: dict[str, str], positional_summary: dict[str, str], field_notes: str) -> dict[str, str]:
    source_class = classify_source(source_type, signal_type, parse_int(positional_summary.get("explicit_position_rows")))
    return {
        "track": track,
        "source_hint": source_hint,
        "source_type": source_class,
        "positional_signal_type": signal_type,
        "evidence_gap": clean(plan_row.get("evidence_gap")) or "POSITIONAL_SOURCE_DISCOVERY_GAP",
        "expected_value": expected_value(source_class, plan_row),
        "risk": risk_for(source_class, positional_summary, field_notes),
        "recommended_followup": followup_for(source_class, track, source_hint),
        "notes": OFFLINE_NOTE,
    }


def build_repair_targets(discovery_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    priority_order = {
        "GPS_MAP_SOURCE_CANDIDATE": 0,
        "REPLAY_PAYLOAD_CANDIDATE": 1,
        "EXPLICIT_POSITION_SOURCE_CANDIDATE": 2,
        "WEAK_POSITION_SOURCE": 3,
        "NO_POSITION_SOURCE_FOUND": 4,
    }
    rows = sorted(
        discovery_rows,
        key=lambda row: (
            priority_order.get(clean(row.get("source_type")), 9),
            clean(row.get("track")),
            clean(row.get("positional_signal_type")),
        ),
    )
    repair_rows: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        key = (clean(row.get("track")), clean(row.get("source_type")), clean(row.get("positional_signal_type")))
        if key in seen:
            continue
        seen.add(key)
        repair_rows.append(row)
    return repair_rows


def build_discovery() -> None:
    plan_rows = safe_read_csv(IN_PLAN)
    forensics_rows = safe_read_csv(IN_FORENSICS)
    dictionary_rows = safe_read_csv(IN_FIELD_DICTIONARY)
    positional_summary = metric_map(safe_read_csv(IN_POSITIONAL_SUMMARY))

    qld_forensics = forensics_rows[0] if forensics_rows else {}
    detected_columns = set(split_pipe(qld_forensics.get("detected_columns")))
    positional_fields = split_pipe(qld_forensics.get("positional_fields"))
    gps_fields = split_pipe(qld_forensics.get("gps_derived_fields"))
    source_url_examples = ""
    for row in dictionary_rows:
        if clean(row.get("field_name")) == "source_url":
            source_url_examples = clean(row.get("observed_examples"))
            break

    field_notes = " | ".join(
        f"{clean(row.get('field_name'))}:{clean(row.get('field_type'))}:{clean(row.get('nullable_rate'))}"
        for row in dictionary_rows
        if any(token in upper(row.get("field_name")) for token in ["RANK", "POSITION", "DISTANCE_TRAVELLED", "SOURCE_URL", "SPEED"])
    )

    track_plan: dict[str, dict[str, str]] = {}
    for row in plan_rows:
        track = clean(row.get("track"))
        if not track:
            continue
        current = track_plan.get(track)
        if current is None or parse_int(row.get("priority_rank")) < parse_int(current.get("priority_rank")):
            track_plan[track] = row

    discovery_rows: list[dict[str, str]] = []
    for track, plan_row in sorted(track_plan.items(), key=lambda item: parse_int(item[1].get("priority_rank"))):
        if positional_fields:
            discovery_rows.append(
                make_discovery_row(
                    track,
                    "Detected but empty QLD rank fields: " + ", ".join(positional_fields),
                    "WEAK_POSITION_SOURCE",
                    "EMPTY_RANK_COLUMNS",
                    plan_row,
                    positional_summary,
                    field_notes,
                )
            )
        if gps_fields:
            discovery_rows.append(
                make_discovery_row(
                    track,
                    "Derived speed/GPS-style fields: " + ", ".join(gps_fields),
                    "GPS_MAP_SOURCE_CANDIDATE",
                    "GPS_SPEED_OR_PATH_PROXY",
                    plan_row,
                    positional_summary,
                    field_notes,
                )
            )
        if "source_url" in detected_columns:
            discovery_rows.append(
                make_discovery_row(
                    track,
                    source_url_examples or "RacingFile.ashx sectional URL lineage",
                    "REPLAY_PAYLOAD_CANDIDATE",
                    "ALTERNATE_DOWNLOAD_OR_EMBEDDED_PAYLOAD_HINT",
                    plan_row,
                    positional_summary,
                    field_notes,
                )
            )
        if not positional_fields and not gps_fields and "source_url" not in detected_columns:
            discovery_rows.append(
                make_discovery_row(
                    track,
                    "No positional field or source URL evidence detected in current QLD schema.",
                    "NO_POSITION_SOURCE_FOUND",
                    "NO_POSITION_SIGNAL",
                    plan_row,
                    positional_summary,
                    field_notes,
                )
            )

    repair_rows = build_repair_targets(discovery_rows)
    source_counts = Counter(clean(row.get("source_type")) for row in discovery_rows)
    signal_counts = Counter(clean(row.get("positional_signal_type")) for row in discovery_rows)
    track_count = len({clean(row.get("track")) for row in discovery_rows if clean(row.get("track"))})

    summary = [
        {"metric": "discovery_rows", "value": str(len(discovery_rows))},
        {"metric": "repair_target_rows", "value": str(len(repair_rows))},
        {"metric": "tracks_covered", "value": str(track_count)},
        {"metric": "explicit_position_rows_current", "value": positional_summary.get("explicit_position_rows", "0")},
        {"metric": "inferred_position_rows_current", "value": positional_summary.get("inferred_position_rows", "0")},
        {"metric": "explicit_position_source_candidates", "value": str(source_counts.get("EXPLICIT_POSITION_SOURCE_CANDIDATE", 0))},
        {"metric": "gps_map_source_candidates", "value": str(source_counts.get("GPS_MAP_SOURCE_CANDIDATE", 0))},
        {"metric": "replay_payload_candidates", "value": str(source_counts.get("REPLAY_PAYLOAD_CANDIDATE", 0))},
        {"metric": "weak_position_sources", "value": str(source_counts.get("WEAK_POSITION_SOURCE", 0))},
        {"metric": "no_position_source_found", "value": str(source_counts.get("NO_POSITION_SOURCE_FOUND", 0))},
        {"metric": "empty_rank_column_signals", "value": str(signal_counts.get("EMPTY_RANK_COLUMNS", 0))},
        {"metric": "gps_proxy_signals", "value": str(signal_counts.get("GPS_SPEED_OR_PATH_PROXY", 0))},
        {"metric": "alternate_payload_hints", "value": str(signal_counts.get("ALTERNATE_DOWNLOAD_OR_EMBEDDED_PAYLOAD_HINT", 0))},
        {"metric": "live_modelling_yes", "value": "0"},
        {"metric": "live_execution_yes", "value": "0"},
        {"metric": "offline_research_only", "value": "YES"},
    ]

    write_csv_atomic(OUT_DISCOVERY, discovery_rows, DISCOVERY_FIELDS)
    write_csv_atomic(OUT_SUMMARY, summary, SUMMARY_FIELDS)
    write_csv_atomic(OUT_REPAIR, repair_rows, DISCOVERY_FIELDS)

    print(f"QLD positional discovery rows: {len(discovery_rows)}")
    print(f"Repair targets: {len(repair_rows)}")
    print(f"GPS candidates: {source_counts.get('GPS_MAP_SOURCE_CANDIDATE', 0)}")
    print(f"Replay candidates: {source_counts.get('REPLAY_PAYLOAD_CANDIDATE', 0)}")
    print("Live modelling: 0")
    print("Live execution: 0")


if __name__ == "__main__":
    build_discovery()
