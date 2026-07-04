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
SPEED_MAP_PATH = DATA_DIR / "edgeiq_real_speed_map_positions.csv"

OUTPUT_PATH = DATA_DIR / "edgeiq_race_shape_fit_v1.csv"
AUDIT_PATH = DATA_DIR / "edgeiq_race_shape_fit_v1_audit.csv"

OUTPUT_COLUMNS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "horse_key",
    "sectional_archetype",
    "dna_confidence",
    "race_tempo",
    "pace_pressure",
    "run_style",
    "settling_band",
    "speed_map_bucket",
    "map_x_pct",
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
    return re.sub(r"\s+", " ", (value or "").upper().strip())


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


def race_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        text(row.get("race_date")),
        normalise_track(row.get("track")),
        text(row.get("race_no")),
    )


def runner_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (*race_key(row), normalise_key(row.get("horse_key") or row.get("horse")))


def build_lookup(rows: list[dict[str, str]], key_column: str = "horse_key") -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for row in rows:
        key = normalise_key(row.get(key_column) or row.get("horse"))
        if key:
            lookup[key] = row
    return lookup


def build_speed_map_lookup(rows: list[dict[str, str]]) -> dict[tuple[str, str, str, str], dict[str, str]]:
    lookup: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in rows:
        key = runner_key(row)
        if key[-1]:
            lookup[key] = row
    return lookup


def canonical_position(value: str | None) -> str:
    raw = re.sub(r"[_\-]+", " ", text(value).upper())
    raw = re.sub(r"\s+", " ", raw).strip()
    if not raw:
        return ""
    if "OFF PACE" in raw or "OFFPACE" in raw:
        return "OFF_PACE"
    if "BACK" in raw or "CLOSER" in raw or "REAR" in raw:
        return "BACKMARKER"
    if "LEADER" in raw or "FRONT" in raw:
        return "LEADER"
    if raw == "PACE" or "ON PACE" in raw or "ONPACE" in raw or "PRESSURE" in raw:
        return "ON_PACE"
    if "MID" in raw:
        return "MIDFIELD"
    return raw.replace(" ", "_")


def derive_run_style(live_row: dict[str, str], settling_band: str, speed_map_bucket: str) -> str:
    for column in ("run_style", "pace_profile", "map_position"):
        raw = canonical_position(live_row.get(column))
        if raw:
            return raw
    for raw_value in (settling_band, speed_map_bucket):
        raw = canonical_position(raw_value)
        if raw:
            return raw
    return ""


def is_pace_runner(row: dict[str, str], speed_row: dict[str, str] | None = None) -> bool:
    values = [
        row.get("settling_band"),
        row.get("speed_map_bucket"),
        row.get("run_style"),
        row.get("pace_profile"),
    ]
    if speed_row:
        values.extend([speed_row.get("settling_band"), speed_row.get("settling_reason")])
    categories = {canonical_position(value) for value in values if text(value)}
    return "LEADER" in categories or "ON_PACE" in categories


def derive_race_tempo(pace_runner_count: int) -> tuple[str, str]:
    if pace_runner_count >= 4:
        return "FAST", "HIGH"
    if pace_runner_count >= 2:
        return "HONEST", "MODERATE"
    return "CONTROLLED", "LOW"


def tempo_fit(archetype: str, race_tempo: str, pace_pressure: str) -> float | None:
    if not archetype or archetype == "UNKNOWN_INSUFFICIENT_DATA":
        return None

    tempo = race_tempo.upper()
    pressure = pace_pressure.upper()

    if tempo == "FAST":
        scores = {
            "STRONG_CLOSER": 90,
            "MIDFIELD_FINISHER": 86,
            "SUSTAINED_STAYER": 84,
            "EXPLOSIVE_SPRINTER": 74,
            "ONE_PACE_GRINDER": 56,
            "ON_PACE_GRINDER": 54,
            "FRONT_RUNNING_CONTROLLER": 38,
            "PRESSURE_LEADER": 34,
        }
        score = scores.get(archetype, 55)
        if pressure == "HIGH" and archetype in {"PRESSURE_LEADER", "FRONT_RUNNING_CONTROLLER"}:
            score -= 8
        return max(0, score)

    if tempo == "CONTROLLED":
        scores = {
            "FRONT_RUNNING_CONTROLLER": 90,
            "PRESSURE_LEADER": 84,
            "ON_PACE_GRINDER": 80,
            "ONE_PACE_GRINDER": 62,
            "EXPLOSIVE_SPRINTER": 60,
            "MIDFIELD_FINISHER": 50,
            "SUSTAINED_STAYER": 48,
            "STRONG_CLOSER": 38,
        }
        return scores.get(archetype, 58)

    scores = {
        "ON_PACE_GRINDER": 76,
        "MIDFIELD_FINISHER": 74,
        "SUSTAINED_STAYER": 72,
        "FRONT_RUNNING_CONTROLLER": 70,
        "PRESSURE_LEADER": 68,
        "STRONG_CLOSER": 66,
        "EXPLOSIVE_SPRINTER": 64,
        "ONE_PACE_GRINDER": 60,
    }
    return scores.get(archetype, 62)


def position_fit(archetype: str, position: str) -> float | None:
    if not archetype or archetype == "UNKNOWN_INSUFFICIENT_DATA":
        return None
    pos = canonical_position(position)
    if not pos:
        return None

    table = {
        "STRONG_CLOSER": {
            "BACKMARKER": 92,
            "OFF_PACE": 86,
            "MIDFIELD": 76,
            "ON_PACE": 36,
            "LEADER": 22,
        },
        "MIDFIELD_FINISHER": {
            "MIDFIELD": 90,
            "OFF_PACE": 84,
            "BACKMARKER": 76,
            "ON_PACE": 56,
            "LEADER": 36,
        },
        "SUSTAINED_STAYER": {
            "MIDFIELD": 82,
            "ON_PACE": 76,
            "OFF_PACE": 74,
            "BACKMARKER": 70,
            "LEADER": 62,
        },
        "FRONT_RUNNING_CONTROLLER": {
            "LEADER": 94,
            "ON_PACE": 86,
            "MIDFIELD": 56,
            "OFF_PACE": 32,
            "BACKMARKER": 24,
        },
        "PRESSURE_LEADER": {
            "LEADER": 92,
            "ON_PACE": 84,
            "MIDFIELD": 46,
            "OFF_PACE": 28,
            "BACKMARKER": 20,
        },
        "ON_PACE_GRINDER": {
            "ON_PACE": 90,
            "MIDFIELD": 82,
            "LEADER": 76,
            "OFF_PACE": 58,
            "BACKMARKER": 38,
        },
        "ONE_PACE_GRINDER": {
            "ON_PACE": 66,
            "MIDFIELD": 64,
            "LEADER": 60,
            "OFF_PACE": 58,
            "BACKMARKER": 54,
        },
        "EXPLOSIVE_SPRINTER": {
            "MIDFIELD": 82,
            "OFF_PACE": 80,
            "BACKMARKER": 74,
            "ON_PACE": 66,
            "LEADER": 56,
        },
    }
    return table.get(archetype, {}).get(pos, 55)


def fit_grade(score: float | None) -> str:
    if score is None:
        return "INSUFFICIENT"
    if score >= 85:
        return "ELITE_FIT"
    if score >= 70:
        return "POSITIVE_FIT"
    if score >= 50:
        return "NEUTRAL_FIT"
    if score >= 30:
        return "RISK_FIT"
    return "POOR_FIT"


def fit_confidence(dna_confidence: str, shape_missing_count: int) -> str:
    dna = dna_confidence.upper()
    if dna == "INSUFFICIENT":
        return "INSUFFICIENT"
    if dna == "HIGH" and shape_missing_count == 0:
        return "HIGH"
    if dna == "MEDIUM" or shape_missing_count <= 1:
        return "MEDIUM"
    if dna == "LOW" or shape_missing_count >= 2:
        return "LOW"
    return "LOW"


def describe_archetype(archetype: str) -> str:
    return archetype.lower().replace("_", " ")


def build_fit_reason(archetype: str, tempo: str, position: str, grade: str) -> str:
    if not archetype or archetype == "UNKNOWN_INSUFFICIENT_DATA":
        return "No usable Horse DNA profile for reliable race-shape fit."
    profile = describe_archetype(archetype)
    pos = canonical_position(position).replace("_", " ").lower() or "unknown map"
    if grade in {"ELITE_FIT", "POSITIVE_FIT"}:
        return f"{profile.title()} profile suits projected {tempo.lower()} tempo and {pos} map."
    if grade == "NEUTRAL_FIT":
        return f"{profile.title()} profile is broadly neutral against projected {tempo.lower()} tempo and {pos} map."
    return f"{profile.title()} profile does not cleanly match projected {tempo.lower()} tempo and {pos} map."


def build_risk_reason(archetype: str, tempo: str, pressure: str, position_score: float | None) -> str:
    if not archetype or archetype == "UNKNOWN_INSUFFICIENT_DATA":
        return "Insufficient sectional evidence to identify race-shape risk."
    if tempo == "FAST" and pressure == "HIGH" and archetype in {"PRESSURE_LEADER", "FRONT_RUNNING_CONTROLLER"}:
        return "On-pace profile may face pressure in fast tempo."
    if tempo == "CONTROLLED" and archetype in {"STRONG_CLOSER", "MIDFIELD_FINISHER"}:
        return "Closing profile may need more tempo than this race projects."
    if position_score is not None and position_score < 45:
        return "Sectional profile is poorly matched to projected settling position."
    if archetype == "ONE_PACE_GRINDER":
        return "One-pace profile may need the race to avoid sharp acceleration points."
    return "No major race-shape risk identified."


def build_race_shape_fit() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    live_rows = read_csv(LIVE_FEED_PATH)
    dna_rows = read_csv(HORSE_DNA_PATH)
    speed_map_rows = read_csv(SPEED_MAP_PATH)

    dna_lookup = build_lookup(dna_rows)
    speed_lookup = build_speed_map_lookup(speed_map_rows)

    live_by_race: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in live_rows:
        if text(row.get("race_date")) and text(row.get("track")) and text(row.get("race_no")) and (row.get("horse_key") or row.get("horse")):
            live_by_race[race_key(row)].append(row)

    race_shape: dict[tuple[str, str, str], dict[str, Any]] = {}
    for key, rows in live_by_race.items():
        pace_count = 0
        for row in rows:
            pace_count += 1 if is_pace_runner(row, speed_lookup.get(runner_key(row))) else 0
        tempo, pressure = derive_race_tempo(pace_count)
        race_shape[key] = {
            "pace_runner_count": pace_count,
            "race_tempo": tempo,
            "pace_pressure": pressure,
        }

    output_rows: list[dict[str, Any]] = []
    matched_dna = 0
    unmatched_dna = 0

    for live_row in live_rows:
        horse_key = normalise_key(live_row.get("horse_key") or live_row.get("horse"))
        if not horse_key:
            continue

        speed_row = speed_lookup.get(runner_key(live_row))
        dna = dna_lookup.get(horse_key)
        if dna:
            matched_dna += 1
        else:
            unmatched_dna += 1

        race_info = race_shape.get(race_key(live_row), {})
        race_tempo = text(race_info.get("race_tempo")) or "HONEST"
        pace_pressure = text(race_info.get("pace_pressure")) or "MODERATE"

        settling_band = text(speed_row.get("settling_band")) if speed_row else ""
        if not settling_band:
            settling_band = text(live_row.get("settling_band"))

        speed_map_bucket = text(live_row.get("speed_map_bucket"))
        if not speed_map_bucket:
            speed_map_bucket = canonical_position(settling_band)

        map_x = text(speed_row.get("map_x_pct")) if speed_row else ""
        if not map_x:
            map_x = text(live_row.get("map_x_pct"))

        run_style = derive_run_style(live_row, settling_band, speed_map_bucket)
        position_source = settling_band or speed_map_bucket or run_style

        archetype = text(dna.get("sectional_archetype")) if dna else "UNKNOWN_INSUFFICIENT_DATA"
        dna_confidence = text(dna.get("dna_confidence")) if dna else "INSUFFICIENT"

        tempo_score = tempo_fit(archetype, race_tempo, pace_pressure)
        position_score = position_fit(archetype, position_source)
        overall_score = None
        if tempo_score is not None and position_score is not None:
            overall_score = (0.60 * tempo_score) + (0.40 * position_score)

        grade = fit_grade(overall_score)
        shape_missing_count = sum(
            1
            for value in (settling_band, speed_map_bucket, map_x, run_style)
            if not text(value)
        )
        confidence = fit_confidence(dna_confidence, shape_missing_count)

        output_rows.append(
            {
                "race_date": text(live_row.get("race_date")),
                "track": text(live_row.get("track")),
                "race_no": text(live_row.get("race_no")),
                "horse": text(live_row.get("horse")),
                "horse_key": horse_key,
                "sectional_archetype": archetype,
                "dna_confidence": dna_confidence,
                "race_tempo": race_tempo,
                "pace_pressure": pace_pressure,
                "run_style": run_style,
                "settling_band": settling_band,
                "speed_map_bucket": speed_map_bucket,
                "map_x_pct": map_x,
                "tempo_fit_score": round_score(tempo_score),
                "position_fit_score": round_score(position_score),
                "race_shape_fit_score": round_score(overall_score),
                "fit_grade": grade,
                "fit_confidence": confidence,
                "fit_reason": build_fit_reason(archetype, race_tempo, position_source, grade),
                "risk_reason": build_risk_reason(archetype, race_tempo, pace_pressure, position_score),
            }
        )

    grade_counts = Counter(row["fit_grade"] for row in output_rows)
    confidence_counts = Counter(row["fit_confidence"] for row in output_rows)
    tempo_counts = Counter(row["race_tempo"] for row in output_rows)

    audit = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "live_terminal_rows_loaded": len(live_rows),
        "horse_dna_rows_loaded": len(dna_rows),
        "speed_map_rows_loaded": len(speed_map_rows),
        "output_rows": len(output_rows),
        "matched_dna_rows": matched_dna,
        "unmatched_dna_rows": unmatched_dna,
        "fit_grade_counts": "; ".join(f"{name}:{count}" for name, count in sorted(grade_counts.items())),
        "fit_confidence_counts": "; ".join(f"{name}:{count}" for name, count in sorted(confidence_counts.items())),
        "race_tempo_counts": "; ".join(f"{name}:{count}" for name, count in sorted(tempo_counts.items())),
        "race_count": len(live_by_race),
        "pace_rule": "4+ pace runners=FAST/HIGH; 2-3=HONEST/MODERATE; 0-1=CONTROLLED/LOW",
        "scoring_method": "Race-shape fit = 60% tempo fit + 40% position fit; blank scores emitted where Horse DNA is insufficient.",
        "status": "RACE_SHAPE_FIT_BUILT" if live_rows and dna_rows and output_rows else "RACE_SHAPE_FIT_INSUFFICIENT_INPUTS",
    }

    return output_rows, audit


def main() -> None:
    output_rows, audit = build_race_shape_fit()
    write_csv(OUTPUT_PATH, output_rows, OUTPUT_COLUMNS)
    write_csv(AUDIT_PATH, [audit], list(audit.keys()))

    print(f"Race shape fit rows written: {len(output_rows)}")
    print(f"Audit written: {AUDIT_PATH}")
    print(f"Status: {audit['status']}")
    print(f"Fit grade counts: {audit['fit_grade_counts']}")
    print(f"Fit confidence counts: {audit['fit_confidence_counts']}")
    print(f"Race tempo counts: {audit['race_tempo_counts']}")


if __name__ == "__main__":
    main()
