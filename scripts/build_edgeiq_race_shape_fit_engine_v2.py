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

OUTPUT_PATH = DATA_DIR / "edgeiq_race_shape_fit_v2.csv"
AUDIT_PATH = DATA_DIR / "edgeiq_race_shape_fit_v2_audit.csv"

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
    forward_count = sum(1 for row in tactical_rows if text(row.get("tactical_speed_bucket")).upper() in {"LEADER", "ON_PACE"})
    primary_pressure_count = sum(1 for row in tactical_rows if text(row.get("tempo_pressure_role")).upper() == "PRIMARY_PRESSURE")
    pace_presence_count = sum(1 for row in tactical_rows if text(row.get("tempo_pressure_role")).upper() == "PACE_PRESENCE")

    if forward_count >= 5 or primary_pressure_count >= 2:
        tempo = "FAST"
        pressure = "HIGH"
    elif forward_count >= 3:
        tempo = "HONEST"
        pressure = "MODERATE"
    else:
        tempo = "CONTROLLED"
        pressure = "LOW"

    return tempo, pressure, {
        "forward_count": forward_count,
        "primary_pressure_count": primary_pressure_count,
        "pace_presence_count": pace_presence_count,
    }


def tempo_fit_score(archetype: str, race_tempo: str, pace_pressure: str) -> float | None:
    if not archetype or archetype == "UNKNOWN_INSUFFICIENT_DATA":
        return None

    if race_tempo == "FAST" and pace_pressure == "HIGH":
        scores = {
            "STRONG_CLOSER": 92,
            "MIDFIELD_FINISHER": 88,
            "SUSTAINED_STAYER": 84,
            "EXPLOSIVE_SPRINTER": 78,
            "ONE_PACE_GRINDER": 56,
            "ON_PACE_GRINDER": 52,
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
            "EXPLOSIVE_SPRINTER": 60,
            "MIDFIELD_FINISHER": 48,
            "SUSTAINED_STAYER": 46,
            "STRONG_CLOSER": 36,
        }
        return scores.get(archetype, 58)

    scores = {
        "ON_PACE_GRINDER": 78,
        "MIDFIELD_FINISHER": 76,
        "SUSTAINED_STAYER": 74,
        "FRONT_RUNNING_CONTROLLER": 72,
        "PRESSURE_LEADER": 70,
        "STRONG_CLOSER": 68,
        "EXPLOSIVE_SPRINTER": 68,
        "ONE_PACE_GRINDER": 62,
    }
    return scores.get(archetype, 62)


def position_fit_score(archetype: str, tactical_bucket: str, race_tempo: str) -> float | None:
    if not archetype or archetype == "UNKNOWN_INSUFFICIENT_DATA":
        return None
    bucket = tactical_bucket.upper()
    if not bucket or bucket == "UNKNOWN":
        return None

    table = {
        "STRONG_CLOSER": {
            "BACKMARKER": 92,
            "OFF_PACE": 88,
            "MIDFIELD": 78,
            "ON_PACE": 38,
            "LEADER": 22,
        },
        "MIDFIELD_FINISHER": {
            "MIDFIELD": 92,
            "OFF_PACE": 86,
            "BACKMARKER": 78,
            "ON_PACE": 58,
            "LEADER": 36,
        },
        "SUSTAINED_STAYER": {
            "MIDFIELD": 84,
            "OFF_PACE": 78,
            "ON_PACE": 76,
            "BACKMARKER": 72,
            "LEADER": 64,
        },
        "FRONT_RUNNING_CONTROLLER": {
            "LEADER": 96,
            "ON_PACE": 82,
            "MIDFIELD": 52,
            "OFF_PACE": 30,
            "BACKMARKER": 22,
        },
        "PRESSURE_LEADER": {
            "LEADER": 94,
            "ON_PACE": 88,
            "MIDFIELD": 46,
            "OFF_PACE": 28,
            "BACKMARKER": 20,
        },
        "ON_PACE_GRINDER": {
            "ON_PACE": 92,
            "MIDFIELD": 84,
            "LEADER": 76,
            "OFF_PACE": 58,
            "BACKMARKER": 38,
        },
        "ONE_PACE_GRINDER": {
            "LEADER": 62,
            "ON_PACE": 66,
            "MIDFIELD": 66,
            "OFF_PACE": 60,
            "BACKMARKER": 56,
        },
        "EXPLOSIVE_SPRINTER": {
            "MIDFIELD": 84,
            "OFF_PACE": 82,
            "BACKMARKER": 76,
            "ON_PACE": 68,
            "LEADER": 56,
        },
    }
    score = table.get(archetype, {}).get(bucket, 55)
    if archetype == "EXPLOSIVE_SPRINTER" and race_tempo in {"FAST", "HONEST"} and bucket in {"MIDFIELD", "OFF_PACE"}:
        score += 4
    return score


def fit_grade(score: float | None) -> str:
    if score is None:
        return ""
    if score >= 85:
        return "ELITE_FIT"
    if score >= 70:
        return "POSITIVE_FIT"
    if score >= 50:
        return "NEUTRAL_FIT"
    if score >= 30:
        return "RISK_FIT"
    return "POOR_FIT"


def fit_confidence(archetype: str, dna_confidence: str, bucket_confidence: str, tactical_bucket: str) -> str:
    dna = dna_confidence.upper()
    bucket = bucket_confidence.upper()
    if dna == "INSUFFICIENT" or archetype == "UNKNOWN_INSUFFICIENT_DATA" or not tactical_bucket or tactical_bucket == "UNKNOWN":
        return "INSUFFICIENT"
    if dna in {"HIGH", "MEDIUM"} and bucket in {"HIGH", "MEDIUM"}:
        return "HIGH"
    if "LOW" in {dna, bucket} and "INSUFFICIENT" not in {dna, bucket}:
        if dna == "LOW" and bucket == "LOW":
            return "LOW"
        return "MEDIUM"
    return "LOW"


def readable(value: str) -> str:
    return value.lower().replace("_", " ")


def build_fit_reason(archetype: str, race_tempo: str, pace_pressure: str, tactical_bucket: str, grade: str) -> str:
    if not grade:
        return "Insufficient Horse DNA to assess race-shape fit."
    profile = readable(archetype)
    bucket = readable(tactical_bucket)
    tempo = f"{race_tempo.lower()}/{pace_pressure.lower()}-pressure"
    if grade in {"ELITE_FIT", "POSITIVE_FIT"}:
        return f"{profile.title()} profile suits {tempo} race shape from {bucket}."
    if grade == "NEUTRAL_FIT":
        return f"{profile.title()} profile is neutral against {tempo} race shape from {bucket}."
    return f"{profile.title()} profile is not ideally suited to {tempo} race shape from {bucket}."


def build_risk_reason(archetype: str, race_tempo: str, pace_pressure: str, tactical_bucket: str, position_score: float | None) -> str:
    if not archetype or archetype == "UNKNOWN_INSUFFICIENT_DATA":
        return "Insufficient sectional evidence to identify race-shape risk."
    if race_tempo == "FAST" and pace_pressure == "HIGH" and archetype in {"PRESSURE_LEADER", "FRONT_RUNNING_CONTROLLER"}:
        return "Forward profile may face pressure in fast race shape."
    if race_tempo == "CONTROLLED" and archetype in {"STRONG_CLOSER", "MIDFIELD_FINISHER"}:
        return "Closing profile may need more tempo than this race shape projects."
    if position_score is not None and position_score < 45:
        return "Sectional profile is poorly matched to tactical position."
    if archetype == "ONE_PACE_GRINDER":
        return "One-pace profile may need the race to avoid sharp acceleration points."
    if tactical_bucket in {"OFF_PACE", "BACKMARKER"} and archetype in {"FRONT_RUNNING_CONTROLLER", "PRESSURE_LEADER"}:
        return "Forward-type profile is mapped rearward."
    return "No major race-shape risk identified."


def build_race_shape_fit_v2() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    live_rows = read_csv(LIVE_FEED_PATH)
    dna_rows = read_csv(HORSE_DNA_PATH)
    tactical_rows = read_csv(TACTICAL_BUCKET_PATH)

    dna_lookup = build_dna_lookup(dna_rows)
    tactical_lookup = build_runner_lookup(tactical_rows)

    tactical_by_race: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in tactical_rows:
        tactical_by_race[race_key(row)].append(row)

    tempo_by_race: dict[tuple[str, str, str], dict[str, Any]] = {}
    for key, rows in tactical_by_race.items():
        tempo, pressure, counts = derive_race_tempo(rows)
        tempo_by_race[key] = {
            "race_tempo": tempo,
            "pace_pressure": pressure,
            **counts,
        }

    output_rows: list[dict[str, Any]] = []
    matched_dna = 0
    unmatched_dna = 0
    usable_fit = 0
    insufficient_fit = 0

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

        race_info = tempo_by_race.get(key[:3], {"race_tempo": "CONTROLLED", "pace_pressure": "LOW"})
        race_tempo = race_info["race_tempo"]
        pace_pressure = race_info["pace_pressure"]

        confidence = fit_confidence(archetype, dna_conf, bucket_conf, tactical_bucket)
        if confidence == "INSUFFICIENT":
            tempo_score = None
            position_score = None
            fit_score = None
            grade = ""
            insufficient_fit += 1
        else:
            tempo_score = tempo_fit_score(archetype, race_tempo, pace_pressure)
            position_score = position_fit_score(archetype, tactical_bucket, race_tempo)
            fit_score = None
            if tempo_score is not None and position_score is not None:
                fit_score = (0.60 * tempo_score) + (0.40 * position_score)
            grade = fit_grade(fit_score)
            if fit_score is None:
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
                "race_shape_fit_score": round_score(fit_score),
                "fit_grade": grade,
                "fit_confidence": confidence,
                "fit_reason": build_fit_reason(archetype, race_tempo, pace_pressure, tactical_bucket, grade),
                "risk_reason": build_risk_reason(archetype, race_tempo, pace_pressure, tactical_bucket, position_score),
            }
        )

    grade_counts = Counter(row["fit_grade"] or "BLANK" for row in output_rows)
    confidence_counts = Counter(row["fit_confidence"] for row in output_rows)
    tempo_counts = Counter(row["race_tempo"] for row in output_rows)
    pressure_counts = Counter(row["pace_pressure"] for row in output_rows)

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
        "fit_grade_counts": "; ".join(f"{name}:{count}" for name, count in sorted(grade_counts.items())),
        "fit_confidence_counts": "; ".join(f"{name}:{count}" for name, count in sorted(confidence_counts.items())),
        "race_tempo_counts": "; ".join(f"{name}:{count}" for name, count in sorted(tempo_counts.items())),
        "pace_pressure_counts": "; ".join(f"{name}:{count}" for name, count in sorted(pressure_counts.items())),
        "tempo_rule": "forward_count>=5 or primary_pressure_count>=2 => FAST/HIGH; forward_count 3-4 => HONEST/MODERATE; <=2 => CONTROLLED/LOW",
        "scoring_method": "Race-shape fit V2 = 60% tempo fit + 40% tactical position fit using edgeiq_tactical_speed_bucket_v1.",
        "status": "RACE_SHAPE_FIT_V2_BUILT" if live_rows and dna_rows and tactical_rows and output_rows else "RACE_SHAPE_FIT_V2_INSUFFICIENT_INPUTS",
    }

    return output_rows, audit


def main() -> None:
    output_rows, audit = build_race_shape_fit_v2()
    write_csv(OUTPUT_PATH, output_rows, OUTPUT_COLUMNS)
    write_csv(AUDIT_PATH, [audit], list(audit.keys()))

    print(f"Race shape fit V2 rows written: {len(output_rows)}")
    print(f"Audit written: {AUDIT_PATH}")
    print(f"Status: {audit['status']}")
    print(f"Usable fit rows: {audit['usable_fit_rows']}")
    print(f"Fit grade counts: {audit['fit_grade_counts']}")
    print(f"Race tempo counts: {audit['race_tempo_counts']}")


if __name__ == "__main__":
    main()
