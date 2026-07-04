from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"

OUTPUT_MAIN = DATA / "edgeiq_race_shape_fallback_engine_v1.csv"
OUTPUT_SUMMARY = DATA / "edgeiq_race_shape_fallback_engine_v1_summary.csv"
OUTPUT_AUDIT = DATA / "edgeiq_race_shape_fallback_engine_v1_audit.csv"


RUN_STYLE_LABELS = {
    "LEADER",
    "ON_PACE",
    "MIDFIELD",
    "BACKMARKER",
    "UNKNOWN",
}

RACE_SHAPE_LABELS = {
    "FORWARD_CONTROL",
    "EVEN_SHAPE",
    "LATE_RUNNERS_INVOLVED",
    "TACTICAL",
    "HIGH_PRESSURE",
}

TEMPO_LABELS = {
    "LOW_PRESSURE",
    "MODERATE_PRESSURE",
    "HIGH_PRESSURE",
}


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def upper(value: object) -> str:
    return clean(value).upper()


def to_float(value: object, default: Optional[float] = None) -> Optional[float]:
    txt = clean(value)
    if txt == "":
        return default
    try:
        return float(txt)
    except Exception:
        return default


def to_int(value: object, default: Optional[int] = None) -> Optional[int]:
    num = to_float(value, None)
    if num is None:
        return default
    try:
        return int(round(num))
    except Exception:
        return default


def race_date_of(row: Dict[str, str]) -> str:
    return clean(row.get("race_date")) or clean(row.get("_date"))


def track_of(row: Dict[str, str]) -> str:
    return upper(row.get("track")) or upper(row.get("_track"))


def race_no_of(row: Dict[str, str]) -> str:
    return clean(row.get("race_no")) or clean(row.get("_race"))


def horse_of(row: Dict[str, str]) -> str:
    return clean(row.get("horse")) or clean(row.get("_horse"))


def is_scratched(row: Dict[str, str]) -> bool:
    flags = [
        upper(row.get("is_scratched")),
        upper(row.get("scratch_status")),
        upper(row.get("runner_status")),
    ]
    return any(flag in {"1", "TRUE", "YES", "Y", "SCRATCHED", "LATE_SCRATCHING"} for flag in flags)


def csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def style_from_text(row: Dict[str, str]) -> str:
    raw = " ".join(
        [
            upper(row.get("settling_band")),
            upper(row.get("run_style")),
            upper(row.get("speed_map_bucket")),
            upper(row.get("early_speed_band")),
        ]
    )

    if any(token in raw for token in ["LEADER", "LEAD", "FRONT", "FORWARD"]):
        return "LEADER"

    if any(token in raw for token in ["ON PACE", "ON-PACE", "ONPACE", "PROMINENT", "PRESSER"]):
        return "ON_PACE"

    if any(token in raw for token in ["MIDFIELD", "MID FIELD", "MID"]):
        return "MIDFIELD"

    if any(token in raw for token in ["BACKMARKER", "BACK MARKER", "BACK", "REAR", "CLOSER"]):
        return "BACKMARKER"

    return "UNKNOWN"


def pace_numeric_value(row: Dict[str, str]) -> Optional[float]:
    for column in ("map_x_pct", "early_speed_rating", "projected_spd"):
        value = to_float(row.get(column), None)
        if value is not None:
            return value
    return None


def derive_run_style(row: Dict[str, str]) -> str:
    text_style = style_from_text(row)
    if text_style != "UNKNOWN":
        return text_style

    pace_value = pace_numeric_value(row)
    if pace_value is None:
        return "UNKNOWN"

    # Current live board pace values mostly sit on a 0-100 style scale.
    if pace_value >= 72:
        return "LEADER"
    if pace_value >= 58:
        return "ON_PACE"
    if pace_value >= 42:
        return "MIDFIELD"
    return "BACKMARKER"


def has_pace_evidence(row: Dict[str, str]) -> bool:
    if style_from_text(row) != "UNKNOWN":
        return True
    return pace_numeric_value(row) is not None


def race_key(row: Dict[str, str]) -> Tuple[str, str, str]:
    return (race_date_of(row), track_of(row), race_no_of(row))


def sort_key_race(row: Dict[str, str]) -> Tuple[str, str, int, str]:
    race_no = to_int(row.get("race_no"), 9999)
    return (clean(row.get("race_date")), clean(row.get("track")), race_no if race_no is not None else 9999, clean(row.get("track")))


def detect_race_shape(
    field_size: int,
    leaders: int,
    on_pace: int,
    midfield: int,
    backmarkers: int,
    known_count: int,
) -> Tuple[float, str, str, str, str, str]:
    if field_size <= 0 or known_count <= 0:
        return 0.0, "", "", "", "", "EVIDENCE_LIMITED"

    pressure_points = (leaders * 4.0) + (on_pace * 2.0) + (midfield * 1.0)
    early_pressure_score = round((pressure_points / field_size) * 10.0, 2)

    if leaders >= 4 or (leaders >= 3 and on_pace >= 4) or early_pressure_score >= 26:
        tempo_label = "HIGH_PRESSURE"
        race_shape_label = "HIGH_PRESSURE"
        pressure_risk = "HIGH"
        pace_advantage_label = "LATE RUNNERS / STALKERS"
    elif leaders <= 1 and on_pace <= 2:
        tempo_label = "LOW_PRESSURE"
        race_shape_label = "FORWARD_CONTROL"
        pressure_risk = "LOW"
        pace_advantage_label = "LEADERS / ON PACE"
    elif backmarkers >= max(leaders + on_pace, 5):
        tempo_label = "MODERATE_PRESSURE"
        race_shape_label = "LATE_RUNNERS_INVOLVED"
        pressure_risk = "MODERATE"
        pace_advantage_label = "CLOSERS / LATE RUNNERS"
    elif leaders == 2 and on_pace >= 2 and backmarkers <= on_pace + 1:
        tempo_label = "MODERATE_PRESSURE"
        race_shape_label = "EVEN_SHAPE"
        pressure_risk = "MODERATE"
        pace_advantage_label = "BALANCED"
    else:
        tempo_label = "MODERATE_PRESSURE"
        race_shape_label = "TACTICAL"
        pressure_risk = "MODERATE"
        pace_advantage_label = "TACTICAL SPEED"

    evidence_status = "READY_FOR_UI" if known_count / max(field_size, 1) >= 0.5 else "EVIDENCE_LIMITED"
    return (
        early_pressure_score,
        race_shape_label,
        tempo_label,
        pressure_risk,
        pace_advantage_label,
        evidence_status,
    )


def build_narrative(
    field_size: int,
    leaders: int,
    on_pace: int,
    midfield: int,
    backmarkers: int,
    race_shape_label: str,
    tempo_label: str,
    pace_advantage_label: str,
    evidence_status: str,
) -> str:
    if evidence_status == "EVIDENCE_LIMITED":
        return (
            f"Pace map evidence is limited, but current runner positioning still points to a "
            f"{tempo_label.replace('_', ' ').lower()} race."
        )

    parts = [
        f"{leaders} leader{'s' if leaders != 1 else ''}",
        f"{on_pace} on-pace",
        f"{midfield} midfield",
        f"{backmarkers} backmarker{'s' if backmarkers != 1 else ''}",
    ]
    profile = ", ".join(parts)
    return (
        f"Field maps with {profile}. Shape reads {race_shape_label.replace('_', ' ').lower()} "
        f"and tempo reads {tempo_label.replace('_', ' ').lower()}, which favours {pace_advantage_label.lower()}."
    )


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    board_rows = csv_rows(INPUT_BOARD)

    grouped: Dict[Tuple[str, str, str], List[Dict[str, str]]] = defaultdict(list)
    for row in board_rows:
        if is_scratched(row):
            continue
        grouped[race_key(row)].append(row)

    output_rows: List[Dict[str, object]] = []
    audit_rows: List[Dict[str, object]] = []

    for key in sorted(grouped.keys()):
        rows = grouped[key]
        active_rows = [row for row in rows if horse_of(row)]
        field_size = len(active_rows)
        known_rows = [row for row in active_rows if has_pace_evidence(row)]
        style_counts = Counter(derive_run_style(row) for row in active_rows)

        leaders = int(style_counts.get("LEADER", 0))
        on_pace = int(style_counts.get("ON_PACE", 0))
        midfield = int(style_counts.get("MIDFIELD", 0))
        backmarkers = int(style_counts.get("BACKMARKER", 0))
        known_count = leaders + on_pace + midfield + backmarkers

        (
            early_pressure_score,
            race_shape_label,
            tempo_label,
            pressure_risk,
            pace_advantage_label,
            evidence_status,
        ) = detect_race_shape(field_size, leaders, on_pace, midfield, backmarkers, known_count)

        if race_shape_label == "" and known_count > 0:
            race_shape_label = "TACTICAL"
        if tempo_label == "" and known_count > 0:
            tempo_label = "MODERATE_PRESSURE"
        if pressure_risk == "" and known_count > 0:
            pressure_risk = "MODERATE"
        if pace_advantage_label == "" and known_count > 0:
            pace_advantage_label = "TACTICAL SPEED"
        if evidence_status == "" and known_count > 0:
            evidence_status = "READY_FOR_UI"

        narrative = build_narrative(
            field_size=field_size,
            leaders=leaders,
            on_pace=on_pace,
            midfield=midfield,
            backmarkers=backmarkers,
            race_shape_label=race_shape_label,
            tempo_label=tempo_label,
            pace_advantage_label=pace_advantage_label,
            evidence_status=evidence_status or "EVIDENCE_LIMITED",
        )

        race_date, track, race_no = key
        output_rows.append(
            {
                "race_date": race_date,
                "track": track,
                "race_no": race_no,
                "field_size": field_size,
                "leaders_count": leaders,
                "on_pace_count": on_pace,
                "midfield_count": midfield,
                "backmarker_count": backmarkers,
                "early_pressure_score": early_pressure_score,
                "race_shape_label": race_shape_label or "TACTICAL",
                "tempo_label": tempo_label or "MODERATE_PRESSURE",
                "pressure_risk": pressure_risk or "MODERATE",
                "pace_advantage_label": pace_advantage_label or "TACTICAL SPEED",
                "race_shape_narrative": narrative,
                "evidence_status": evidence_status or "EVIDENCE_LIMITED",
                "built_at": built_at,
            }
        )

        audit_rows.append(
            {
                "race_date": race_date,
                "track": track,
                "race_no": race_no,
                "active_runner_rows": field_size,
                "pace_evidence_rows": len(known_rows),
                "pace_evidence_pct": round((len(known_rows) / field_size) * 100.0, 2) if field_size else 0.0,
                "leader_rows": leaders,
                "on_pace_rows": on_pace,
                "midfield_rows": midfield,
                "backmarker_rows": backmarkers,
                "race_shape_blank": "YES" if clean(race_shape_label) == "" else "NO",
                "tempo_blank": "YES" if clean(tempo_label) == "" else "NO",
                "bendigo_flag": "YES" if track == "BENDIGO" else "NO",
                "status": evidence_status or "EVIDENCE_LIMITED",
                "built_at": built_at,
            }
        )

    duplicate_race_keys = len(output_rows) - len({(row["race_date"], row["track"], row["race_no"]) for row in output_rows})
    blank_race_shape_count = sum(1 for row in output_rows if clean(row["race_shape_label"]) == "")
    blank_tempo_count = sum(1 for row in output_rows if clean(row["tempo_label"]) == "")
    bendigo_rows = [row for row in output_rows if row["track"] == "BENDIGO"]

    summary_rows = [
        {"metric": "status", "value": "READY_FOR_UI" if output_rows else "FAIL_NO_OUTPUT"},
        {"metric": "input_file", "value": str(INPUT_BOARD)},
        {"metric": "built_at", "value": built_at},
        {"metric": "active_runner_rows", "value": sum(len(rows) for rows in grouped.values())},
        {"metric": "active_race_count", "value": len(output_rows)},
        {"metric": "output_rows", "value": len(output_rows)},
        {"metric": "duplicate_track_race_rows", "value": duplicate_race_keys},
        {"metric": "blank_race_shape_count", "value": blank_race_shape_count},
        {"metric": "blank_tempo_count", "value": blank_tempo_count},
        {"metric": "bendigo_race_count", "value": len(bendigo_rows)},
        {
            "metric": "bendigo_blank_race_shape_count",
            "value": sum(1 for row in bendigo_rows if clean(row["race_shape_label"]) == ""),
        },
        {
            "metric": "bendigo_blank_tempo_count",
            "value": sum(1 for row in bendigo_rows if clean(row["tempo_label"]) == ""),
        },
        {
            "metric": "ready_for_ui_races",
            "value": sum(1 for row in output_rows if row["evidence_status"] == "READY_FOR_UI"),
        },
        {
            "metric": "evidence_limited_races",
            "value": sum(1 for row in output_rows if row["evidence_status"] == "EVIDENCE_LIMITED"),
        },
        {
            "metric": "avg_early_pressure_score",
            "value": round(
                sum(float(row["early_pressure_score"]) for row in output_rows) / len(output_rows),
                3,
            )
            if output_rows
            else 0.0,
        },
    ]

    main_fields = [
        "race_date",
        "track",
        "race_no",
        "field_size",
        "leaders_count",
        "on_pace_count",
        "midfield_count",
        "backmarker_count",
        "early_pressure_score",
        "race_shape_label",
        "tempo_label",
        "pressure_risk",
        "pace_advantage_label",
        "race_shape_narrative",
        "evidence_status",
        "built_at",
    ]
    audit_fields = [
        "race_date",
        "track",
        "race_no",
        "active_runner_rows",
        "pace_evidence_rows",
        "pace_evidence_pct",
        "leader_rows",
        "on_pace_rows",
        "midfield_rows",
        "backmarker_rows",
        "race_shape_blank",
        "tempo_blank",
        "bendigo_flag",
        "status",
        "built_at",
    ]

    write_csv(OUTPUT_MAIN, output_rows, main_fields)
    write_csv(OUTPUT_AUDIT, audit_rows, audit_fields)
    write_csv(OUTPUT_SUMMARY, summary_rows, ["metric", "value"])

    print("[EDGEIQ_RACE_SHAPE_FALLBACK_ENGINE_V1] COMPLETE")
    print(f"wrote={OUTPUT_MAIN}")
    print(f"wrote={OUTPUT_SUMMARY}")
    print(f"wrote={OUTPUT_AUDIT}")
    print(f"active_race_count={len(output_rows)}")
    print(f"blank_race_shape_count={blank_race_shape_count}")
    print(f"blank_tempo_count={blank_tempo_count}")
    print(f"bendigo_race_count={len(bendigo_rows)}")


if __name__ == "__main__":
    main()
