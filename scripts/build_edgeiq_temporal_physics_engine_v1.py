from __future__ import annotations

import csv
import math
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT = DATA / "edgeiq_real_sectional_physics_features_v1.csv"
OUT = DATA / "edgeiq_temporal_physics_engine_v1.csv"
SUMMARY = DATA / "edgeiq_temporal_physics_summary_v1.csv"

FIELDS = [
    "source_file",
    "race_date",
    "track",
    "race_no",
    "horse",
    "early_phase_value",
    "mid_phase_value",
    "late_phase_value",
    "acceleration_delta",
    "late_retention_delta",
    "energy_decay_index",
    "sectional_volatility",
    "phase_transition_pattern",
    "energy_curve_type",
    "temporal_stability_grade",
    "temporal_physics_score",
    "temporal_physics_label",
    "predictive_use_status",
    "trusted_for_live_modelling",
    "trusted_for_live_execution",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]


def clean(value: object) -> str:
    text = str(value or "").strip()
    if text.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"}:
        return ""
    return text


def number(value: object) -> float:
    text = clean(value).replace(",", "")
    if not text:
        return math.nan
    try:
        return float(text)
    except ValueError:
        return math.nan


def fmt(value: float) -> str:
    if math.isnan(value):
        return ""
    return f"{value:.4f}".rstrip("0").rstrip(".")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except Exception:
        return []


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{int(datetime.now().timestamp() * 1000)}.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def percentile(values: list[float], pct: float, fallback: float) -> float:
    valid = sorted(value for value in values if not math.isnan(value))
    if not valid:
        return fallback
    if len(valid) == 1:
        return valid[0]
    index = (len(valid) - 1) * pct
    low = math.floor(index)
    high = math.ceil(index)
    if low == high:
        return valid[int(index)]
    return valid[low] + (valid[high] - valid[low]) * (index - low)


def bounded(value: float, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(round(value))))


def classify_transition(
    acceleration: float,
    retention: float,
    decay: float,
    volatility: float,
    thresholds: dict[str, float],
) -> str:
    if any(math.isnan(value) for value in [acceleration, retention, decay, volatility]):
        return "NEUTRAL_PHASE_PATTERN"

    transition_force = abs(acceleration) + abs(retention)
    if volatility >= thresholds["volatility_high"] and transition_force >= thresholds["transition_high"]:
        return "VOLATILE_PHASE_PATTERN"
    if retention <= thresholds["retention_collapse"] and decay >= thresholds["decay_high"]:
        return "LATE_COLLAPSE"
    if decay >= thresholds["decay_high"] and acceleration <= thresholds["accel_low"]:
        return "EARLY_SPEED_DECAY"
    if acceleration >= thresholds["accel_high"] and retention >= thresholds["retention_hold"]:
        return "EARLY_TO_LATE_ACCELERATION"
    if retention >= thresholds["retention_hold"] and decay <= thresholds["decay_controlled"]:
        return "MIDRACE_SUSTAIN_TO_LATE_HOLD"
    return "NEUTRAL_PHASE_PATTERN"


def classify_curve(
    acceleration: float,
    retention: float,
    decay: float,
    volatility: float,
    thresholds: dict[str, float],
) -> str:
    if any(math.isnan(value) for value in [acceleration, retention, decay, volatility]):
        return "UNSTABLE_CURVE"
    if volatility >= thresholds["volatility_extreme"]:
        return "UNSTABLE_CURVE"
    if retention <= thresholds["retention_collapse"] and decay >= thresholds["decay_high"]:
        return "COLLAPSE_CURVE"
    if acceleration > 0 and retention >= thresholds["retention_hold"] and decay <= 0:
        return "POSITIVE_ENERGY_CURVE"
    if decay >= thresholds["decay_high"]:
        return "DECAYING_ENERGY_CURVE"
    return "STABLE_ENERGY_CURVE"


def score_temporal_physics(
    acceleration: float,
    retention: float,
    decay: float,
    volatility: float,
    thresholds: dict[str, float],
) -> int:
    if any(math.isnan(value) for value in [acceleration, retention, decay, volatility]):
        return 0

    score = 58.0

    if acceleration > 0:
        score += min(18.0, acceleration * 18.0)
    else:
        score += max(-18.0, acceleration * 8.0)

    if retention >= 0:
        score += min(18.0, retention * 18.0)
    else:
        score += max(-22.0, retention * 0.65)

    if decay <= 0:
        score += min(12.0, abs(decay) * 12.0)
    else:
        score -= min(22.0, decay * 10.0)

    if volatility >= thresholds["volatility_extreme"]:
        score -= 22.0
    elif volatility >= thresholds["volatility_high"]:
        score -= 12.0
    elif volatility <= thresholds["volatility_low"]:
        score += 6.0

    return bounded(score)


def grade(score: int, volatility: float, thresholds: dict[str, float]) -> str:
    if score >= 82 and volatility <= thresholds["volatility_high"]:
        return "A"
    if score >= 68:
        return "B"
    if score >= 52:
        return "C"
    if score >= 35:
        return "D"
    return "F"


def label_for(pattern: str, curve: str, stability_grade: str) -> str:
    if pattern == "EARLY_TO_LATE_ACCELERATION":
        return "MEASURED_TEMPORAL_ACCELERATOR"
    if pattern == "MIDRACE_SUSTAIN_TO_LATE_HOLD":
        return "MEASURED_MIDRACE_HOLD_PROFILE"
    if pattern == "EARLY_SPEED_DECAY":
        return "MEASURED_EARLY_SPEED_DECAY"
    if pattern == "LATE_COLLAPSE":
        return "MEASURED_LATE_COLLAPSE_RISK"
    if pattern == "VOLATILE_PHASE_PATTERN" or curve == "UNSTABLE_CURVE":
        return "MEASURED_VOLATILE_PHASE_PROFILE"
    if stability_grade in {"A", "B"}:
        return "MEASURED_STABLE_TEMPORAL_PROFILE"
    return "MEASURED_NEUTRAL_TEMPORAL_PROFILE"


def predictive_status(score: int, pattern: str, curve: str) -> str:
    if pattern in {"VOLATILE_PHASE_PATTERN", "LATE_COLLAPSE"} or curve in {"UNSTABLE_CURVE", "COLLAPSE_CURVE"}:
        return "RESEARCH_ONLY_RISK_FLAG"
    if score >= 70:
        return "RESEARCH_ONLY_STABLE_SIGNAL"
    if score >= 50:
        return "RESEARCH_ONLY_MONITOR"
    return "RESEARCH_ONLY_WEAK_SIGNAL"


def build_thresholds(rows: list[dict[str, str]]) -> dict[str, float]:
    accelerations = [number(row.get("acceleration_delta")) for row in rows]
    retentions = [number(row.get("late_retention_delta")) for row in rows]
    decays = [number(row.get("energy_decay_index")) for row in rows]
    volatilities = [number(row.get("sectional_volatility")) for row in rows]
    transition_force = [
        abs(number(row.get("acceleration_delta"))) + abs(number(row.get("late_retention_delta")))
        for row in rows
    ]

    return {
        "accel_high": max(0.15, percentile(accelerations, 0.70, 0.25)),
        "accel_low": min(-0.15, percentile(accelerations, 0.30, -0.25)),
        "retention_hold": max(-0.15, percentile(retentions, 0.62, -0.05)),
        "retention_collapse": percentile(retentions, 0.18, -1.00),
        "decay_high": max(0.40, percentile(decays, 0.72, 0.75)),
        "decay_controlled": max(0.20, percentile(decays, 0.45, 0.25)),
        "volatility_low": percentile(volatilities, 0.25, 0.15),
        "volatility_high": percentile(volatilities, 0.78, 1.25),
        "volatility_extreme": percentile(volatilities, 0.92, 2.00),
        "transition_high": percentile(transition_force, 0.82, 1.50),
    }


def build_rows(input_rows: list[dict[str, str]]) -> tuple[list[dict[str, object]], dict[str, float]]:
    thresholds = build_thresholds(input_rows)
    output_rows: list[dict[str, object]] = []

    for row in input_rows:
        early = number(row.get("early_phase_value"))
        mid = number(row.get("mid_phase_value"))
        late = number(row.get("late_phase_value"))
        acceleration = number(row.get("acceleration_delta"))
        retention = number(row.get("late_retention_delta"))
        decay = number(row.get("energy_decay_index"))
        volatility = number(row.get("sectional_volatility"))

        pattern = classify_transition(acceleration, retention, decay, volatility, thresholds)
        curve = classify_curve(acceleration, retention, decay, volatility, thresholds)
        temporal_score = score_temporal_physics(acceleration, retention, decay, volatility, thresholds)
        stability_grade = grade(temporal_score, volatility, thresholds)
        temporal_label = label_for(pattern, curve, stability_grade)
        use_status = predictive_status(temporal_score, pattern, curve)

        notes = (
            "Measured temporal phase-transition profile only. "
            "No market pricing, betting signal, execution impact, or live trust promotion."
        )

        output_rows.append(
            {
                "source_file": clean(row.get("source_file")),
                "race_date": clean(row.get("race_date")),
                "track": clean(row.get("track")),
                "race_no": clean(row.get("race_no")),
                "horse": clean(row.get("horse")),
                "early_phase_value": fmt(early),
                "mid_phase_value": fmt(mid),
                "late_phase_value": fmt(late),
                "acceleration_delta": fmt(acceleration),
                "late_retention_delta": fmt(retention),
                "energy_decay_index": fmt(decay),
                "sectional_volatility": fmt(volatility),
                "phase_transition_pattern": pattern,
                "energy_curve_type": curve,
                "temporal_stability_grade": stability_grade,
                "temporal_physics_score": temporal_score,
                "temporal_physics_label": temporal_label,
                "predictive_use_status": use_status,
                "trusted_for_live_modelling": "NO",
                "trusted_for_live_execution": "NO",
                "notes": notes,
            }
        )

    return output_rows, thresholds


def build_summary(rows: list[dict[str, object]], thresholds: dict[str, float], input_rows: int) -> list[dict[str, object]]:
    patterns = Counter(str(row.get("phase_transition_pattern", "")) for row in rows)
    curves = Counter(str(row.get("energy_curve_type", "")) for row in rows)
    grades = Counter(str(row.get("temporal_stability_grade", "")) for row in rows)
    labels = Counter(str(row.get("temporal_physics_label", "")) for row in rows)
    statuses = Counter(str(row.get("predictive_use_status", "")) for row in rows)
    sources = Counter(str(row.get("source_file", "")) for row in rows)

    summary: list[dict[str, object]] = [
        {"metric": "input_rows", "value": input_rows},
        {"metric": "temporal_physics_rows", "value": len(rows)},
        {"metric": "trusted_for_live_modelling_yes", "value": 0},
        {"metric": "trusted_for_live_execution_yes", "value": 0},
    ]

    for key in [
        "accel_high",
        "accel_low",
        "retention_hold",
        "retention_collapse",
        "decay_high",
        "volatility_high",
        "volatility_extreme",
        "transition_high",
    ]:
        summary.append({"metric": f"threshold::{key}", "value": fmt(thresholds.get(key, math.nan))})

    for key, value in patterns.most_common():
        summary.append({"metric": f"pattern::{key}", "value": value})
    for key, value in curves.most_common():
        summary.append({"metric": f"curve::{key}", "value": value})
    for key, value in grades.most_common():
        summary.append({"metric": f"grade::{key}", "value": value})
    for key, value in labels.most_common():
        summary.append({"metric": f"label::{key}", "value": value})
    for key, value in statuses.most_common():
        summary.append({"metric": f"predictive_use_status::{key}", "value": value})
    for key, value in sources.most_common():
        summary.append({"metric": f"source::{key}", "value": value})

    return summary


def main() -> None:
    input_rows = read_csv(INPUT)
    rows, thresholds = build_rows(input_rows)
    summary = build_summary(rows, thresholds, len(input_rows))

    write_csv(OUT, rows, FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)

    patterns = Counter(row["phase_transition_pattern"] for row in rows)
    curves = Counter(row["energy_curve_type"] for row in rows)
    grades = Counter(row["temporal_stability_grade"] for row in rows)

    print("=" * 88)
    print("EDGEIQ TEMPORAL PHYSICS ENGINE V1")
    print("=" * 88)
    print(f"input rows: {len(input_rows)}")
    print(f"temporal physics rows built: {len(rows)}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print("patterns:")
    for key, value in patterns.most_common():
        print(f"  {key}: {value}")
    print("energy curves:")
    for key, value in curves.most_common():
        print(f"  {key}: {value}")
    print("grades:")
    for key, value in grades.most_common():
        print(f"  {key}: {value}")
    print("live modelling/execution: 0 / 0")


if __name__ == "__main__":
    main()
