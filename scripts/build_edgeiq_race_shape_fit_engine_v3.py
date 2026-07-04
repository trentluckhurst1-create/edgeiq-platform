from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "public" / "data"

HORSE_DNA_PATH = DATA_DIR / "edgeiq_horse_dna_v1.csv"
LIVE_FEED_PATH = DATA_DIR / "edgeiq_vic_live_terminal_feed_v1.csv"
TACTICAL_BUCKET_PATH = DATA_DIR / "edgeiq_tactical_speed_bucket_v1.csv"

OUTPUT_PATH = DATA_DIR / "edgeiq_race_shape_fit_v3.csv"
AUDIT_PATH = DATA_DIR / "edgeiq_race_shape_fit_v3_audit.csv"

OUTPUT_COLUMNS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "horse_key",
    "sectional_archetype",
    "dna_confidence",
    "tactical_speed_bucket",
    "tactical_position_group",
    "tempo_pressure_role",
    "bucket_confidence",
    "race_tempo",
    "pace_pressure",
    "tempo_fit_score",
    "position_fit_score",
    "raw_race_shape_fit_score",
    "position_conflict_flag",
    "position_conflict_reason",
    "race_shape_fit_score",
    "fit_grade",
    "fit_confidence",
    "fit_reason",
    "risk_reason",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def normalise_key(value: str | None) -> str:
    raw = (value or "").upper().strip()
    raw = re.sub(r"\([A-Z]{2,3}\)$", "", raw).strip()
    return re.sub(r"[^A-Z0-9]+", "", raw)


def normalise_track(value: str | None) -> str:
    raw = (value or "").upper().strip()
    raw = re.sub(r"^(SPORTSBET|SPORTS BET|BET365|LADBROKES|TABTOUCH|TAB)\s+", "", raw).strip()
    raw = re.sub(r"[^A-Z0-9]+", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()


def normalise_race_no(value: str | None) -> str:
    raw = text(value).upper()
    match = re.search(r"\d+", raw)
    return match.group(0) if match else raw


def runner_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        text(row.get("race_date")),
        normalise_track(row.get("track")),
        normalise_race_no(row.get("race_no")),
        normalise_key(row.get("horse_key") or row.get("horse")),
    )


def race_key(row: dict[str, str]) -> tuple[str, str, str]:
    return runner_key(row)[:3]


def to_float(value: Any) -> float | None:
    raw = text(value)
    if not raw or raw.upper() in {"-", "NA", "N/A", "NULL", "NONE"}:
        return None
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        return None


def round_score(value: float | None) -> str:
    if value is None:
        return ""
    bounded = max(0.0, min(100.0, value))
    return f"{bounded:.2f}"


def build_runner_lookup(rows: list[dict[str, str]]) -> dict[tuple[str, str, str, str], dict[str, str]]:
    lookup: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in rows:
        key = runner_key(row)
        if key[-1]:
            lookup[key] = row
    return lookup


def build_dna_lookup(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for row in rows:
        key = normalise_key(row.get("horse_key") or row.get("horse"))
        if key:
            lookup[key] = row
    return lookup


def derive_race_tempo(tactical_rows: list[dict[str, str]]) -> tuple[str, str, dict[str, int]]:
    forward_count = sum(
        1
        for row in tactical_rows
        if text(row.get("tactical_speed_bucket")).upper() in {"LEADER", "ON_PACE"}
    )
    leader_count = sum(
        1
        for row in tactical_rows
        if text(row.get("tactical_speed_bucket")).upper() == "LEADER"
    )
    primary_pressure_count = sum(
        1
        for row in tactical_rows
        if text(row.get("tempo_pressure_role")).upper() == "PRIMARY_PRESSURE"
    )
    pace_presence_count = sum(
        1
        for row in tactical_rows
        if text(row.get("tempo_pressure_role")).upper() == "PACE_PRESENCE"
    )

    if primary_pressure_count >= 2 or (forward_count >= 6 and leader_count >= 2):
        tempo = "FAST"
        pressure = "HIGH"
    elif 3 <= forward_count <= 5:
        tempo = "HONEST"
        pressure = "MODERATE"
    else:
        tempo = "CONTROLLED"
        pressure = "LOW"

    return tempo, pressure, {
        "forward_count": forward_count,
        "leader_count": leader_count,
        "primary_pressure_count": primary_pressure_count,
        "pace_presence_count": pace_presence_count,
    }


def tempo_fit_score(archetype: str, tactical_bucket: str, race_tempo: str, pace_pressure: str) -> float | None:
    if not archetype or archetype == "UNKNOWN_INSUFFICIENT_DATA":
        return None
    bucket = tactical_bucket.upper()

    if race_tempo == "FAST" and pace_pressure == "HIGH":
        scores = {
            "STRONG_CLOSER": 90,
            "MIDFIELD_FINISHER": 86,
            "SUSTAINED_STAYER": 84,
            "EXPLOSIVE_SPRINTER": 76 if bucket in {"MIDFIELD", "OFF_PACE"} else 62,
            "ONE_PACE_GRINDER": 56,
            "ON_PACE_GRINDER": 46 if bucket in {"LEADER", "ON_PACE"} else 58,
            "FRONT_RUNNING_CONTROLLER": 34,
            "PRESSURE_LEADER": 30,
        }
        return scores.get(archetype, 55)

    if race_tempo == "CONTROLLED" and pace_pressure == "LOW":
        scores = {
            "FRONT_RUNNING_CONTROLLER": 92,
            "PRESSURE_LEADER": 88,
            "ON_PACE_GRINDER": 82,
            "ONE_PACE_GRINDER": 64,
            "EXPLOSIVE_SPRINTER": 58,
            "MIDFIELD_FINISHER": 48,
            "SUSTAINED_STAYER": 46,
            "STRONG_CLOSER": 36,
        }
        return scores.get(archetype, 58)

    scores = {
        "ON_PACE_GRINDER": 74,
        "MIDFIELD_FINISHER": 74,
        "SUSTAINED_STAYER": 72,
        "FRONT_RUNNING_CONTROLLER": 72,
        "PRESSURE_LEADER": 70,
        "STRONG_CLOSER": 68,
        "EXPLOSIVE_SPRINTER": 72 if bucket in {"MIDFIELD", "OFF_PACE"} else 64,
        "ONE_PACE_GRINDER": 62,
    }
    return scores.get(archetype, 62)


def position_fit_score(archetype: str, tactical_bucket: str) -> float | None:
    if not archetype or archetype == "UNKNOWN_INSUFFICIENT_DATA":
        return None
    bucket = tactical_bucket.upper()
    if not bucket or bucket == "UNKNOWN":
        return None

    table = {
        "STRONG_CLOSER": {
            "BACKMARKER": 94,
            "OFF_PACE": 90,
            "MIDFIELD": 78,
            "ON_PACE": 34,
            "LEADER": 20,
        },
        "MIDFIELD_FINISHER": {
            "MIDFIELD": 92,
            "OFF_PACE": 84,
            "BACKMARKER": 76,
            "ON_PACE": 56,
            "LEADER": 34,
        },
        "SUSTAINED_STAYER": {
            "MIDFIELD": 84,
            "OFF_PACE": 78,
            "ON_PACE": 74,
            "BACKMARKER": 72,
            "LEADER": 62,
        },
        "FRONT_RUNNING_CONTROLLER": {
            "LEADER": 96,
            "ON_PACE": 84,
            "MIDFIELD": 52,
            "OFF_PACE": 28,
            "BACKMARKER": 20,
        },
        "PRESSURE_LEADER": {
            "LEADER": 94,
            "ON_PACE": 88,
            "MIDFIELD": 44,
            "OFF_PACE": 26,
            "BACKMARKER": 18,
        },
        "ON_PACE_GRINDER": {
            "ON_PACE": 92,
            "MIDFIELD": 84,
            "LEADER": 74,
            "OFF_PACE": 58,
            "BACKMARKER": 36,
        },
        "ONE_PACE_GRINDER": {
            "LEADER": 62,
            "ON_PACE": 66,
            "MIDFIELD": 66,
            "OFF_PACE": 60,
            "BACKMARKER": 56,
        },
        "EXPLOSIVE_SPRINTER": {
            "MIDFIELD": 86,
            "OFF_PACE": 84,
            "BACKMARKER": 74,
            "ON_PACE": 64,
            "LEADER": 54,
        },
    }
    return table.get(archetype, {}).get(bucket, 55)


def conflict_reason(archetype: str, tactical_bucket: str) -> str:
    bucket = tactical_bucket.upper()
    if archetype == "STRONG_CLOSER" and bucket in {"LEADER", "ON_PACE"}:
        return "Strong closer mapped too far forward."
    if archetype == "FRONT_RUNNING_CONTROLLER" and bucket in {"OFF_PACE", "BACKMARKER"}:
        return "Front-running profile mapped rearward."
    if archetype == "PRESSURE_LEADER" and bucket in {"MIDFIELD", "OFF_PACE", "BACKMARKER"}:
        return "Pressure leader may not get preferred forward position."
    if archetype == "ON_PACE_GRINDER" and bucket == "BACKMARKER":
        return "On-pace grinder mapped too far back."
    return ""


def apply_position_caps(
    raw_score: float | None,
    archetype: str,
    tactical_bucket: str,
    late_strength_score: float | None,
    dna_confidence: str,
) -> tuple[float | None, bool, str, bool]:
    if raw_score is None:
        return None, False, "", False

    reason = conflict_reason(archetype, tactical_bucket)
    if not reason:
        return raw_score, False, "", False

    bucket = tactical_bucket.upper()
    score = raw_score
    positive_allowed = False

    if archetype == "STRONG_CLOSER" and bucket in {"LEADER", "ON_PACE"}:
        positive_allowed = bool(
            late_strength_score is not None
            and late_strength_score >= 85
            and dna_confidence.upper() == "HIGH"
        )
        score = min(score, 62.0)
    elif archetype == "FRONT_RUNNING_CONTROLLER" and bucket in {"OFF_PACE", "BACKMARKER"}:
        score = min(score, 55.0)
    elif archetype == "PRESSURE_LEADER" and bucket in {"MIDFIELD", "OFF_PACE", "BACKMARKER"}:
        score = min(score, 50.0)
    elif archetype == "ON_PACE_GRINDER" and bucket == "BACKMARKER":
        score = min(score, 58.0)

    return score, True, reason, positive_allowed


def fit_grade(score: float | None, conflict: bool, positive_allowed: bool) -> str:
    if score is None:
        return ""
    if score >= 85 and not conflict:
        return "ELITE_FIT"
    if score >= 70 and (not conflict or positive_allowed):
        return "POSITIVE_FIT"
    if score >= 50:
        return "NEUTRAL_FIT"
    if score >= 30:
        return "RISK_FIT"
    return "POOR_FIT"


def fit_confidence(
    archetype: str,
    dna_confidence: str,
    bucket_confidence: str,
    tactical_bucket: str,
    position_conflict: bool,
    race_tempo: str,
) -> str:
    dna = dna_confidence.upper()
    bucket = bucket_confidence.upper()
    if dna == "INSUFFICIENT" or archetype == "UNKNOWN_INSUFFICIENT_DATA" or not tactical_bucket or tactical_bucket == "UNKNOWN":
        return "INSUFFICIENT"
    if not race_tempo:
        return "LOW"
    if dna in {"HIGH", "MEDIUM"} and bucket in {"HIGH", "MEDIUM"} and not position_conflict:
        return "HIGH"
    if dna in {"HIGH", "MEDIUM", "LOW"} and bucket in {"HIGH", "MEDIUM", "LOW"}:
        return "MEDIUM" if position_conflict or "LOW" in {dna, bucket} else "HIGH"
    return "LOW"


def readable(value: str) -> str:
    return value.lower().replace("_", " ")


def build_fit_reason(
    archetype: str,
    race_tempo: str,
    pace_pressure: str,
    tactical_bucket: str,
    grade: str,
    conflict: bool,
) -> str:
    if not grade:
        return "Insufficient Horse DNA to assess race-shape fit."
    profile = readable(archetype)
    tempo = f"{race_tempo.lower()}/{pace_pressure.lower()}-pressure"
    if archetype == "ONE_PACE_GRINDER":
        return "One-pace grinder profile is neutral for this race shape."
    if archetype in {"FRONT_RUNNING_CONTROLLER", "PRESSURE_LEADER", "ON_PACE_GRINDER"} and race_tempo == "CONTROLLED":
        return "Forward profile suits controlled tempo."
    if archetype in {"STRONG_CLOSER", "MIDFIELD_FINISHER", "SUSTAINED_STAYER"} and race_tempo == "FAST" and not conflict:
        return f"{profile.title()} profile suits {tempo} race shape."
    if conflict:
        return f"{profile.title()} profile has a tactical position conflict from {readable(tactical_bucket)}."
    if grade in {"ELITE_FIT", "POSITIVE_FIT"}:
        return f"{profile.title()} profile suits {tempo} race shape."
    return f"{profile.title()} profile is broadly neutral for this race shape."


def build_risk_reason(
    archetype: str,
    race_tempo: str,
    pace_pressure: str,
    conflict: bool,
    conflict_text: str,
    dna_confidence: str,
) -> str:
    if not archetype or archetype == "UNKNOWN_INSUFFICIENT_DATA":
        return "Limited DNA evidence."
    if conflict:
        return conflict_text
    if dna_confidence.upper() == "LOW":
        return "Limited DNA evidence."
    if race_tempo == "FAST" and pace_pressure == "HIGH" and archetype in {"PRESSURE_LEADER", "FRONT_RUNNING_CONTROLLER", "ON_PACE_GRINDER"}:
        return "Forward profile may face pressure in fast race shape."
    if race_tempo == "CONTROLLED" and archetype in {"STRONG_CLOSER", "MIDFIELD_FINISHER"}:
        return "Closing profile may need more tempo than this race shape projects."
    return "No major race-shape risk identified."


def build_race_shape_fit_v3() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    live_rows = read_csv(LIVE_FEED_PATH)
    dna_rows = read_csv(HORSE_DNA_PATH)
    tactical_rows = read_csv(TACTICAL_BUCKET_PATH)

    dna_lookup = build_dna_lookup(dna_rows)
    tactical_lookup = build_runner_lookup(tactical_rows)

    tactical_by_race: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in tactical_rows:
        tactical_by_race[race_key(row)].append(row)

    tempo_by_race: dict[tuple[str, str, str], dict[str, Any]] = {}
    race_tempo_labels: dict[tuple[str, str, str], str] = {}
    for key, rows in tactical_by_race.items():
        tempo, pressure, counts = derive_race_tempo(rows)
        tempo_by_race[key] = {
            "race_tempo": tempo,
            "pace_pressure": pressure,
            **counts,
        }
        race_tempo_labels[key] = f"{tempo}/{pressure}"

    output_rows: list[dict[str, Any]] = []
    matched_dna = 0
    unmatched_dna = 0
    usable_fit = 0
    insufficient_fit = 0
    conflict_rows = 0

    for live_row in live_rows:
        key = runner_key(live_row)
        if not key[-1]:
            continue

        tactical = tactical_lookup.get(key, {})
        dna = dna_lookup.get(key[-1], {})
        if dna:
            matched_dna += 1
        else:
            unmatched_dna += 1

        archetype = text(dna.get("sectional_archetype")) or text(tactical.get("sectional_archetype")) or "UNKNOWN_INSUFFICIENT_DATA"
        dna_conf = text(dna.get("dna_confidence")) or text(tactical.get("dna_confidence")) or "INSUFFICIENT"
        tactical_bucket = text(tactical.get("tactical_speed_bucket")) or "UNKNOWN"
        tactical_position_group = text(tactical.get("tactical_position_group")) or "UNKNOWN"
        tempo_pressure_role = text(tactical.get("tempo_pressure_role")) or "UNKNOWN"
        bucket_conf = text(tactical.get("bucket_confidence")) or "INSUFFICIENT"
        late_strength = to_float(dna.get("late_strength_score")) or to_float(tactical.get("late_strength_score"))

        race_info = tempo_by_race.get(key[:3], {"race_tempo": "CONTROLLED", "pace_pressure": "LOW"})
        race_tempo = race_info["race_tempo"]
        pace_pressure = race_info["pace_pressure"]

        if dna_conf.upper() == "INSUFFICIENT" or archetype == "UNKNOWN_INSUFFICIENT_DATA" or tactical_bucket == "UNKNOWN":
            tempo_score = None
            position_score = None
            raw_score = None
            capped_score = None
            position_conflict = False
            position_conflict_reason = ""
            positive_allowed = False
            grade = ""
            confidence = "INSUFFICIENT"
            insufficient_fit += 1
        else:
            tempo_score = tempo_fit_score(archetype, tactical_bucket, race_tempo, pace_pressure)
            position_score = position_fit_score(archetype, tactical_bucket)
            raw_score = None
            if tempo_score is not None and position_score is not None:
                raw_score = (0.50 * tempo_score) + (0.50 * position_score)
            capped_score, position_conflict, position_conflict_reason, positive_allowed = apply_position_caps(
                raw_score,
                archetype,
                tactical_bucket,
                late_strength,
                dna_conf,
            )
            if position_conflict:
                conflict_rows += 1
            grade = fit_grade(capped_score, position_conflict, positive_allowed)
            confidence = fit_confidence(
                archetype,
                dna_conf,
                bucket_conf,
                tactical_bucket,
                position_conflict,
                race_tempo,
            )
            if capped_score is None:
                insufficient_fit += 1
            else:
                usable_fit += 1

        output_rows.append(
            {
                "race_date": text(live_row.get("race_date")),
                "track": text(live_row.get("track")),
                "race_no": text(live_row.get("race_no")),
                "horse": text(live_row.get("horse")),
                "horse_key": key[-1],
                "sectional_archetype": archetype,
                "dna_confidence": dna_conf,
                "tactical_speed_bucket": tactical_bucket,
                "tactical_position_group": tactical_position_group,
                "tempo_pressure_role": tempo_pressure_role,
                "bucket_confidence": bucket_conf,
                "race_tempo": race_tempo,
                "pace_pressure": pace_pressure,
                "tempo_fit_score": round_score(tempo_score),
                "position_fit_score": round_score(position_score),
                "raw_race_shape_fit_score": round_score(raw_score),
                "position_conflict_flag": "TRUE" if position_conflict else "FALSE",
                "position_conflict_reason": position_conflict_reason,
                "race_shape_fit_score": round_score(capped_score),
                "fit_grade": grade,
                "fit_confidence": confidence,
                "fit_reason": build_fit_reason(
                    archetype,
                    race_tempo,
                    pace_pressure,
                    tactical_bucket,
                    grade,
                    position_conflict,
                ),
                "risk_reason": build_risk_reason(
                    archetype,
                    race_tempo,
                    pace_pressure,
                    position_conflict,
                    position_conflict_reason,
                    dna_conf,
                ),
            }
        )

    grade_counts = Counter(row["fit_grade"] or "BLANK" for row in output_rows)
    confidence_counts = Counter(row["fit_confidence"] for row in output_rows)
    tempo_counts = Counter(row["race_tempo"] for row in output_rows)
    pressure_counts = Counter(row["pace_pressure"] for row in output_rows)
    race_tempo_counts = Counter(race_tempo_labels.values())

    strong_closer_on_pace = [
        row
        for row in output_rows
        if row["sectional_archetype"] == "STRONG_CLOSER"
        and row["tactical_speed_bucket"] in {"LEADER", "ON_PACE"}
        and row["fit_confidence"] != "INSUFFICIENT"
    ]
    strong_closer_on_pace_positive = [
        row
        for row in strong_closer_on_pace
        if row["fit_grade"] == "POSITIVE_FIT"
    ]

    audit = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "live_terminal_rows_loaded": len(live_rows),
        "horse_dna_rows_loaded": len(dna_rows),
        "tactical_bucket_rows_loaded": len(tactical_rows),
        "output_rows": len(output_rows),
        "matched_dna_rows": matched_dna,
        "unmatched_dna_rows": unmatched_dna,
        "usable_fit_rows": usable_fit,
        "insufficient_fit_rows": insufficient_fit,
        "position_conflict_rows": conflict_rows,
        "fit_grade_counts": "; ".join(f"{name}:{count}" for name, count in sorted(grade_counts.items())),
        "fit_confidence_counts": "; ".join(f"{name}:{count}" for name, count in sorted(confidence_counts.items())),
        "race_tempo_counts": "; ".join(f"{name}:{count}" for name, count in sorted(tempo_counts.items())),
        "pace_pressure_counts": "; ".join(f"{name}:{count}" for name, count in sorted(pressure_counts.items())),
        "STRONG_CLOSER_ON_PACE_count": len(strong_closer_on_pace),
        "STRONG_CLOSER_ON_PACE_positive_fit_count": len(strong_closer_on_pace_positive),
        "FAST_HIGH_race_count": race_tempo_counts.get("FAST/HIGH", 0),
        "HONEST_MODERATE_race_count": race_tempo_counts.get("HONEST/MODERATE", 0),
        "CONTROLLED_LOW_race_count": race_tempo_counts.get("CONTROLLED/LOW", 0),
        "tempo_rule": "FAST/HIGH only primary_pressure_count>=2 OR forward_count>=6 AND leader_count>=2; HONEST/MODERATE forward_count 3-5; CONTROLLED/LOW <=2.",
        "scoring_method": "Race-shape fit V3 = 50% tempo fit + 50% position fit, followed by position-conflict caps.",
        "status": "RACE_SHAPE_FIT_V3_BUILT" if live_rows and dna_rows and tactical_rows and output_rows else "RACE_SHAPE_FIT_V3_INSUFFICIENT_INPUTS",
    }

    return output_rows, audit


def main() -> None:
    output_rows, audit = build_race_shape_fit_v3()
    write_csv(OUTPUT_PATH, output_rows, OUTPUT_COLUMNS)
    write_csv(AUDIT_PATH, [audit], list(audit.keys()))

    print(f"Race shape fit V3 rows written: {len(output_rows)}")
    print(f"Audit written: {AUDIT_PATH}")
    print(f"Status: {audit['status']}")
    print(f"Usable fit rows: {audit['usable_fit_rows']}")
    print(f"Position conflict rows: {audit['position_conflict_rows']}")
    print(f"Fit grade counts: {audit['fit_grade_counts']}")
    print(f"Race tempo counts: {audit['race_tempo_counts']}")


if __name__ == "__main__":
    main()
