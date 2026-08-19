from __future__ import annotations

import csv
import re
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from edgeiq_memory_safe_io import stream_csv_rows, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INGESTION = DATA / "edgeiq_qld_telemetry_ingestion_v1.csv"
FORENSICS = DATA / "edgeiq_qld_telemetry_schema_forensics_v1.csv"
FIELD_DICTIONARY = DATA / "edgeiq_qld_telemetry_field_dictionary_v1.csv"

OUT = DATA / "edgeiq_qld_positional_telemetry_v1.csv"
SUMMARY = DATA / "edgeiq_qld_positional_telemetry_summary_v1.csv"
LINEAGE = DATA / "edgeiq_qld_positional_lineage_v1.csv"
FAILURES = DATA / "edgeiq_qld_positional_extraction_failures_v1.csv"

OUT_FIELDS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "split_marker",
    "distance_marker",
    "position_rank",
    "position_change",
    "running_order_state",
    "early_position_state",
    "mid_position_state",
    "late_position_state",
    "movement_direction",
    "acceleration_signature",
    "spatial_pressure_state",
    "lane_position",
    "gps_speed",
    "telemetry_confidence",
    "lineage_reference",
    "safe_for_qld_temporal_research",
    "safe_for_qld_shadow_research",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

LINEAGE_FIELDS = [
    "jurisdiction",
    "source_file",
    "schema_signature",
    "races_processed",
    "horses_processed",
    "positional_rows_extracted",
    "explicit_position_rows",
    "inferred_position_rows",
    "movement_shift_rows",
    "lineage_status",
    "positional_quality_grade",
    "recommended_next_step",
    "notes",
]

FAILURE_FIELDS = [
    "source_file",
    "failure_type",
    "failure_reason",
    "affected_rows",
    "recommended_repair",
    "notes",
]

GRADE_LABEL = {
    "A": "ELITE_POSITIONAL_TELEMETRY",
    "B": "STRONG_POSITIONAL_TELEMETRY",
    "C": "USABLE_POSITIONAL_TELEMETRY",
    "D": "WEAK_POSITIONAL_TELEMETRY",
    "F": "FAILED_POSITIONAL_TELEMETRY",
}


def clean(value: object) -> str:
    return str(value or "").strip()


def upper(value: object) -> str:
    return clean(value).upper()


def parse_float(value: object) -> float | None:
    text = clean(value).replace(",", "").replace("%", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_int(value: object) -> int | None:
    number = parse_float(value)
    if number is None:
        return None
    return int(round(number))


def normalise_date(value: object) -> str:
    text = clean(value)
    if not text:
        return ""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y%m%d", "%m/%d/%Y"):
        try:
            source = text[:8] if fmt == "%Y%m%d" else text[:10]
            return datetime.strptime(source, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return text[:10]


def normalise_track(value: object) -> str:
    text = upper(value).replace("&", " AND ")
    text = re.sub(r"\b(RACECOURSE|RACING|CLUB|TRACK)\b", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    aliases = {
        "AQUIS PARK GOLD COAST": "GOLD COAST",
        "AQUIS PARK GOLD COAST POLY": "GOLD COAST POLY",
        "LADBROKES CANNON PARK": "CAIRNS",
        "PICKLEBET PARK WARWICK": "WARWICK",
    }
    return aliases.get(text, text)


def normalise_race_no(value: object) -> str:
    text = upper(value)
    match = re.search(r"(\d+)", text)
    return match.group(1) if match else text


def normalise_horse(value: object) -> str:
    text = upper(value)
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        return list(stream_csv_rows(path))
    except Exception:
        return []


def race_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        normalise_date(row.get("race_date")),
        normalise_track(row.get("track")),
        normalise_race_no(row.get("race_no")),
    )


def horse_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return race_key(row) + (normalise_horse(row.get("horse")),)


def rank_desc(values: dict[str, float]) -> dict[str, int]:
    ranked = sorted(values.items(), key=lambda item: (-item[1], item[0]))
    result: dict[str, int] = {}
    last_value: float | None = None
    last_rank = 0
    for index, (key, value) in enumerate(ranked, start=1):
        if last_value is not None and abs(value - last_value) < 0.0001:
            result[key] = last_rank
        else:
            result[key] = index
            last_rank = index
            last_value = value
    return result


def state_from_rank(rank: int | None, field_size: int) -> str:
    if rank is None or field_size <= 0:
        return "UNKNOWN_POSITION_STATE"
    pct = rank / field_size
    if pct <= 0.18:
        return "LEADER_GROUP"
    if pct <= 0.38:
        return "ON_PACE_GROUP"
    if pct <= 0.68:
        return "MIDFIELD_GROUP"
    return "BACKMARKER_GROUP"


def pressure_from_rank(rank: int | None, field_size: int) -> str:
    if rank is None or field_size <= 0:
        return "UNKNOWN_PRESSURE"
    pct = rank / field_size
    if pct <= 0.25:
        return "HIGH_FRONT_PRESSURE"
    if pct <= 0.55:
        return "PACK_PRESSURE"
    return "LOW_REAR_PRESSURE"


def movement_direction(early_rank: int | None, late_rank: int | None) -> tuple[str, int | None]:
    if early_rank is None or late_rank is None:
        return "UNKNOWN_MOVEMENT", None
    change = early_rank - late_rank
    if change >= 3:
        return "ADVANCING_STRONGLY", change
    if change >= 1:
        return "ADVANCING", change
    if change <= -3:
        return "DROPPING_BACK_SHARPLY", change
    if change <= -1:
        return "DROPPING_BACK", change
    return "HOLDING_POSITION", change


def acceleration_signature(early: float | None, mid: float | None, late: float | None) -> str:
    if early is None or mid is None or late is None:
        return "UNKNOWN_ACCELERATION"
    early_to_mid = mid - early
    mid_to_late = late - mid
    if early_to_mid > 0.4 and mid_to_late > 0.1:
        return "SUSTAINED_ACCELERATION"
    if mid_to_late > 0.35:
        return "LATE_ACCELERATION"
    if mid_to_late < -0.55:
        return "LATE_DECELERATION"
    if abs(early_to_mid) <= 0.25 and abs(mid_to_late) <= 0.25:
        return "STABLE_SPEED_PROFILE"
    return "MIXED_ACCELERATION_PROFILE"


def split_phase(split_marker: str) -> str:
    marker = upper(split_marker)
    if "600" in marker:
        return "early"
    if "400" in marker:
        return "mid"
    if "200" in marker:
        return "late"
    return "unknown"


def quality_grade(confidence: float, explicit_rows: int, inferred_rows: int, movement_rows: int) -> str:
    if explicit_rows > 0 and confidence >= 88:
        return "A"
    if explicit_rows > 0 and confidence >= 74:
        return "B"
    if inferred_rows > 0 and confidence >= 64 and movement_rows > 0:
        return "C"
    if inferred_rows > 0 and confidence >= 40:
        return "D"
    return "F"


def main() -> None:
    ingestion_rows = read_csv(INGESTION)
    forensics_rows = read_csv(FORENSICS)
    dictionary_rows = read_csv(FIELD_DICTIONARY)

    field_names = {clean(row.get("field_name")) for row in dictionary_rows}
    explicit_position_fields = sorted(
        field for field in field_names if re.search(r"(position|rank|order|lane|path|pos)", field, flags=re.IGNORECASE)
    )
    schema_signature = clean(forensics_rows[0].get("schema_signature")) if forensics_rows else ""
    source_file = "edgeiq_qld_telemetry_ingestion_v1.csv"

    grouped: dict[tuple[str, str, str], dict[str, list[dict[str, str]]]] = defaultdict(lambda: defaultdict(list))
    for row in ingestion_rows:
        if upper(row.get("jurisdiction")) != "QLD":
            continue
        grouped[race_key(row)][normalise_horse(row.get("horse"))].append(row)

    out_rows: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    explicit_rows = 0
    inferred_rows = 0
    movement_rows = 0

    for rkey, horses in sorted(grouped.items()):
        race_date, track, race_no = rkey
        field_size = len(horses)
        early_values: dict[str, float] = {}
        mid_values: dict[str, float] = {}
        late_values: dict[str, float] = {}
        top_values: dict[str, float] = {}
        horse_display: dict[str, str] = {}
        for hkey, rows in horses.items():
            first = rows[0]
            horse_display[hkey] = clean(first.get("horse"))
            early = parse_float(first.get("early_phase_value"))
            mid = parse_float(first.get("mid_phase_value"))
            late = parse_float(first.get("late_phase_value"))
            top = parse_float(first.get("gps_speed"))
            if early is not None and early > 0:
                early_values[hkey] = early
            if mid is not None and mid > 0:
                mid_values[hkey] = mid
            if late is not None and late > 0:
                late_values[hkey] = late
            if top is not None and top > 0:
                top_values[hkey] = top

        early_rank = rank_desc(early_values)
        mid_rank = rank_desc(mid_values)
        late_rank = rank_desc(late_values)
        top_rank = rank_desc(top_values)

        if not early_rank and not mid_rank and not late_rank:
            failures.append(
                {
                    "source_file": source_file,
                    "failure_type": "NO_PHASE_SPEED_POSITION_PROXY",
                    "failure_reason": "No early/mid/late speed values were available to reconstruct latent positional state.",
                    "affected_rows": sum(len(rows) for rows in horses.values()),
                    "recommended_repair": "Acquire explicit running-order or split-rank fields from Racing Queensland raw payloads.",
                    "notes": f"{race_date}|{track}|R{race_no}",
                }
            )
            continue

        for hkey, rows in sorted(horses.items()):
            first = rows[0]
            er = early_rank.get(hkey)
            mr = mid_rank.get(hkey)
            lr = late_rank.get(hkey)
            tr = top_rank.get(hkey)
            direction, net_change = movement_direction(er, lr)
            if net_change not in (None, 0):
                movement_rows += len(rows)
            early = parse_float(first.get("early_phase_value"))
            mid = parse_float(first.get("mid_phase_value"))
            late = parse_float(first.get("late_phase_value"))
            accel = acceleration_signature(early, mid, late)
            early_state = state_from_rank(er, field_size)
            mid_state = state_from_rank(mr, field_size)
            late_state = state_from_rank(lr, field_size)
            explicit_available = any(clean(first.get(field)) for field in ("position_at_split", "rank_at_split", "lane_position", "gps_position"))
            base_conf = 78.0 if explicit_available else 62.0
            if er and mr and lr:
                base_conf += 10.0
            if tr:
                base_conf += 4.0
            if direction not in {"UNKNOWN_MOVEMENT"}:
                base_conf += 3.0
            confidence = min(100.0, base_conf)
            for row in sorted(rows, key=lambda item: parse_int(item.get("split_distance")) or 9999, reverse=True):
                phase = split_phase(row.get("split_marker"))
                if phase == "early":
                    current_rank = er
                    prev_rank = None
                    current_state = early_state
                elif phase == "mid":
                    current_rank = mr
                    prev_rank = er
                    current_state = mid_state
                elif phase == "late":
                    current_rank = lr
                    prev_rank = mr
                    current_state = late_state
                else:
                    current_rank = tr
                    prev_rank = None
                    current_state = state_from_rank(tr, field_size)
                explicit_rank = parse_int(row.get("rank_at_split")) or parse_int(row.get("position_at_split"))
                if explicit_rank is not None:
                    current_rank = explicit_rank
                    explicit_rows += 1
                    lineage_note = "explicit_position_rank"
                else:
                    inferred_rows += 1
                    lineage_note = "latent_speed_rank_inference"
                position_delta = ""
                if current_rank is not None and prev_rank is not None:
                    position_delta = prev_rank - current_rank
                spatial_pressure = pressure_from_rank(current_rank, field_size)
                lane_position = clean(row.get("gps_position")) or "UNKNOWN_LANE_POSITION"
                temporal_safe = "YES" if confidence >= 55 else "NO"
                shadow_safe = "YES" if explicit_rank is not None and confidence >= 78 else "NO"
                out_rows.append(
                    {
                        "race_date": race_date,
                        "track": track,
                        "race_no": race_no,
                        "horse": horse_display[hkey],
                        "split_marker": clean(row.get("split_marker")),
                        "distance_marker": clean(row.get("split_distance")),
                        "position_rank": current_rank if current_rank is not None else "",
                        "position_change": position_delta,
                        "running_order_state": current_state,
                        "early_position_state": early_state,
                        "mid_position_state": mid_state,
                        "late_position_state": late_state,
                        "movement_direction": direction,
                        "acceleration_signature": accel,
                        "spatial_pressure_state": spatial_pressure,
                        "lane_position": lane_position,
                        "gps_speed": clean(row.get("gps_speed")),
                        "telemetry_confidence": f"{confidence:.2f}",
                        "lineage_reference": f"{clean(row.get('raw_lineage_reference'))}|{lineage_note}",
                        "safe_for_qld_temporal_research": temporal_safe,
                        "safe_for_qld_shadow_research": shadow_safe,
                        "notes": "QLD positional telemetry extraction is isolated and research-only. Position ranks are explicit only when source ranks exist; otherwise speed-rank inferred.",
                    }
                )

    avg_conf = sum(parse_float(row.get("telemetry_confidence")) or 0 for row in out_rows) / len(out_rows) if out_rows else 0.0
    grade = quality_grade(avg_conf, explicit_rows, inferred_rows, movement_rows)
    lineage_rows = [
        {
            "jurisdiction": "QLD",
            "source_file": source_file,
            "schema_signature": schema_signature,
            "races_processed": len(grouped),
            "horses_processed": len({(row["race_date"], row["track"], row["race_no"], normalise_horse(row["horse"])) for row in out_rows}),
            "positional_rows_extracted": len(out_rows),
            "explicit_position_rows": explicit_rows,
            "inferred_position_rows": inferred_rows,
            "movement_shift_rows": movement_rows,
            "lineage_status": GRADE_LABEL[grade],
            "positional_quality_grade": grade,
            "recommended_next_step": "Acquire explicit running-order/lane/path fields before QLD shadow research; current positional rows are speed-rank inferred." if explicit_rows == 0 else "Validate explicit ranks against raw Racing Queensland files before shadow research.",
            "notes": f"Detected position-like fields in dictionary: {'|'.join(explicit_position_fields) or 'NONE'}. QLD remains isolated from VIC telemetry.",
        }
    ]
    statuses = Counter(clean(row.get("movement_direction")) for row in out_rows)
    summary_rows = [
        {"metric": "qld_positional_rows", "value": len(out_rows)},
        {"metric": "qld_races_processed", "value": len(grouped)},
        {"metric": "qld_horses_processed", "value": len({(row["race_date"], row["track"], row["race_no"], normalise_horse(row["horse"])) for row in out_rows})},
        {"metric": "explicit_position_rows", "value": explicit_rows},
        {"metric": "inferred_position_rows", "value": inferred_rows},
        {"metric": "movement_shift_rows", "value": movement_rows},
        {"metric": "safe_for_qld_temporal_research_yes", "value": sum(1 for row in out_rows if row.get("safe_for_qld_temporal_research") == "YES")},
        {"metric": "safe_for_qld_shadow_research_yes", "value": sum(1 for row in out_rows if row.get("safe_for_qld_shadow_research") == "YES")},
        {"metric": "positional_quality_grade", "value": grade},
        {"metric": "positional_quality_label", "value": GRADE_LABEL[grade]},
        {"metric": "extraction_failures", "value": len(failures)},
        {"metric": "merged_into_vic_telemetry", "value": "NO"},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
        {"metric": "offline_research_only", "value": "YES"},
    ]
    for status, count in statuses.most_common():
        summary_rows.append({"metric": f"movement_direction::{status}", "value": count})

    write_csv_atomic(OUT, out_rows, OUT_FIELDS)
    write_csv_atomic(SUMMARY, summary_rows, SUMMARY_FIELDS)
    write_csv_atomic(LINEAGE, lineage_rows, LINEAGE_FIELDS)
    write_csv_atomic(FAILURES, failures, FAILURE_FIELDS)

    print("=" * 88)
    print("EDGEIQ QLD POSITIONAL TELEMETRY EXTRACTION V1")
    print("=" * 88)
    for row in summary_rows[:15]:
        print(f"{row['metric']}: {row['value']}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {LINEAGE}")
    print(f"saved: {FAILURES}")


if __name__ == "__main__":
    main()
