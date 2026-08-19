from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUN_SOURCE = DATA / "edgeiq_historical_run_ratings_master_v1.csv"
CAREER_SOURCE = DATA / "edgeiq_horse_career_intelligence_v1.csv"
ARCHETYPE_SOURCE = DATA / "edgeiq_horse_archetype_engine_v1.csv"
TRAJECTORY_SOURCE = DATA / "edgeiq_horse_trajectory_engine_v1.csv"
OUT_PATH = DATA / "edgeiq_horse_projection_engine_v1.csv"
SUMMARY_PATH = DATA / "edgeiq_horse_projection_engine_v1_summary.csv"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def upper_text(value: object) -> str:
    return safe_text(value).upper()


def normalize_horse(value: object) -> str:
    text = upper_text(value)
    text = re.sub(r"\([^)]*\)", " ", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def parse_float(value: object) -> float | None:
    text = safe_text(value)
    if not text:
        return None
    text = text.replace("$", "").replace(",", "").replace("%", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        number = float(match.group(0))
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def parse_int(value: object) -> int | None:
    number = parse_float(value)
    if number is None:
        return None
    return int(round(number))


def parse_date(value: object) -> pd.Timestamp | pd.NaT:
    text = safe_text(value)
    if not text:
        return pd.NaT
    return pd.to_datetime(text, errors="coerce")


def first_non_blank(row: pd.Series, columns: list[str]) -> str:
    for column in columns:
        if column in row.index:
            value = safe_text(row[column])
            if value:
                return value
    return ""


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def round_or_blank(value: float | None, digits: int = 1) -> str:
    if value is None or not math.isfinite(value):
        return ""
    return f"{value:.{digits}f}"


def value_counts_summary(series: pd.Series) -> str:
    counts = series.value_counts()
    return "; ".join(f"{index}:{int(count)}" for index, count in counts.items())


def join_map(df: pd.DataFrame) -> dict[str, pd.Series]:
    return {
        row["horse_key_norm"]: row
        for _, row in df.iterrows()
        if safe_text(row["horse_key_norm"])
    }


def label_bonus(label: str, mapping: dict[str, float], default: float = 0.0) -> float:
    return mapping.get(upper_text(label), default)


def probability_from_score(score: float, low: float = 5.0, high: float = 95.0) -> float:
    return clamp(score, low, high)


def projection_confidence_label(confidence_score: float) -> str:
    if confidence_score >= 80:
        return "VERY_HIGH"
    if confidence_score >= 65:
        return "HIGH"
    if confidence_score >= 50:
        return "MEDIUM"
    return "LOW"


def projection_band_label(
    *,
    next_run_projection: float | None,
    latest_rating: float | None,
    improvement_probability: float,
    regression_probability: float,
    breakout_probability: float,
    bounce_probability: float,
) -> str:
    expected_improvement = 0.0 if next_run_projection is None or latest_rating is None else next_run_projection - latest_rating
    if regression_probability >= 72 or (bounce_probability >= 68 and improvement_probability <= 52):
        return "HIGH_RISK"
    if improvement_probability >= 70 and breakout_probability >= 58 and expected_improvement >= 1.5:
        return "MAJOR_UPSIDE"
    if improvement_probability >= 56 and expected_improvement >= 0.5:
        return "POSITIVE"
    if abs(expected_improvement) <= 0.75 and regression_probability < 65:
        return "STABLE"
    return "NEGATIVE"


def main() -> None:
    for path in [RUN_SOURCE, CAREER_SOURCE, ARCHETYPE_SOURCE, TRAJECTORY_SOURCE]:
        if not path.exists():
            raise FileNotFoundError(f"Missing source file: {path}")

    runs = pd.read_csv(RUN_SOURCE, dtype=str).fillna("")
    career = pd.read_csv(CAREER_SOURCE, dtype=str).fillna("")
    archetype = pd.read_csv(ARCHETYPE_SOURCE, dtype=str).fillna("")
    trajectory = pd.read_csv(TRAJECTORY_SOURCE, dtype=str).fillna("")

    if trajectory.empty:
        raise ValueError("Horse trajectory source is empty.")

    runs["horse_key_norm"] = runs.apply(
        lambda row: normalize_horse(first_non_blank(row, ["horse_key", "horse"])),
        axis=1,
    )
    runs["race_date_dt"] = runs["race_date"].map(parse_date)

    career["horse_key_norm"] = career.apply(
        lambda row: normalize_horse(first_non_blank(row, ["horse_key", "horse"])),
        axis=1,
    )
    archetype["horse_key_norm"] = archetype.apply(
        lambda row: normalize_horse(first_non_blank(row, ["horse_key", "horse"])),
        axis=1,
    )
    trajectory["horse_key_norm"] = trajectory.apply(
        lambda row: normalize_horse(first_non_blank(row, ["horse_key", "horse"])),
        axis=1,
    )

    career_map = join_map(career)
    archetype_map = join_map(archetype)

    runs_by_horse: dict[str, pd.DataFrame] = {}
    for horse_key_norm, frame in runs.groupby("horse_key_norm", sort=False):
        if horse_key_norm:
            runs_by_horse[horse_key_norm] = frame.sort_values(["race_date_dt", "track", "race_no"], kind="stable")

    rows: list[dict[str, object]] = []
    built_at = now_iso()

    for _, trajectory_row in trajectory.iterrows():
        horse_key_norm = safe_text(trajectory_row["horse_key_norm"])
        if not horse_key_norm:
            continue

        career_row = career_map.get(horse_key_norm)
        archetype_row = archetype_map.get(horse_key_norm)
        history_frame = runs_by_horse.get(horse_key_norm)

        horse = first_non_blank(trajectory_row, ["horse"]) or first_non_blank(career_row, ["horse"]) if career_row is not None else first_non_blank(trajectory_row, ["horse"])
        horse_key = first_non_blank(trajectory_row, ["horse_key"]) or (first_non_blank(career_row, ["horse_key"]) if career_row is not None else "") or horse_key_norm

        latest_rating = parse_float(trajectory_row["latest_rating"])
        peak_rating = parse_float(trajectory_row["peak_rating"])
        average_rating = parse_float(trajectory_row["average_rating"])

        trajectory_next = parse_float(trajectory_row["next_run_projection"])
        trajectory_ceiling = parse_float(trajectory_row["ceiling_projection"])
        trajectory_floor = parse_float(trajectory_row["floor_projection"])

        points_off_peak = parse_float(trajectory_row["points_off_peak"])
        percent_of_peak = parse_float(trajectory_row["percent_of_peak"])
        runs_since_peak = parse_int(trajectory_row["runs_since_peak"])
        days_since_peak = parse_int(trajectory_row["days_since_peak"])

        direction = upper_text(trajectory_row["trajectory_direction"])
        strength = upper_text(trajectory_row["trajectory_strength"])
        career_phase = upper_text(trajectory_row["career_phase"])
        breakout_potential = upper_text(trajectory_row["breakout_potential"])
        bounce_risk_label = upper_text(trajectory_row["bounce_risk"])
        regression_risk_label = upper_text(trajectory_row["regression_risk"])

        improvement_last_3 = parse_float(trajectory_row["improvement_last_3"])
        improvement_last_5 = parse_float(trajectory_row["improvement_last_5"])
        improvement_last_10 = parse_float(trajectory_row["improvement_last_10"])

        improvement_profile = upper_text(archetype_row["improvement_profile"]) if archetype_row is not None else ""
        consistency_profile = upper_text(archetype_row["consistency_profile"]) if archetype_row is not None else ""
        freshness_profile = upper_text(archetype_row["freshness_profile"]) if archetype_row is not None else ""
        distance_profile = upper_text(archetype_row["distance_profile"]) if archetype_row is not None else ""
        archetype_label = upper_text(archetype_row["horse_archetype"]) if archetype_row is not None else ""

        consistency_score = parse_float(career_row["consistency_score"]) if career_row is not None else None
        volatility_score = parse_float(career_row["volatility_score"]) if career_row is not None else None
        career_starts = parse_int(career_row["career_starts"]) if career_row is not None else None

        avg_gap_days_recent = None
        if history_frame is not None and len(history_frame) >= 2:
            gaps = history_frame["race_date_dt"].diff().dt.days.dropna()
            if not gaps.empty:
                recent_gaps = gaps.tail(5).tolist()
                avg_gap_days_recent = average([float(value) for value in recent_gaps])

        confidence_score = 35.0
        starts = career_starts or 0
        if starts >= 12:
            confidence_score += 10
        elif starts >= 8:
            confidence_score += 6
        elif starts >= 5:
            confidence_score += 3

        confidence_score += label_bonus(consistency_profile, {"ELITE": 8, "HIGH": 5, "MEDIUM": 2, "LOW": -4})
        volatility = volatility_score or 50.0
        if volatility <= 20:
            confidence_score += 10
        elif volatility <= 40:
            confidence_score += 6
        elif volatility <= 60:
            confidence_score += 2
        elif volatility <= 80:
            confidence_score -= 4
        else:
            confidence_score -= 8

        if improvement_last_10 is not None:
            confidence_score += 5
        if improvement_last_5 is not None:
            confidence_score += 3
        if improvement_last_3 is not None:
            confidence_score += 2
        if avg_gap_days_recent is not None and avg_gap_days_recent <= 35:
            confidence_score += 2
        if avg_gap_days_recent is not None and avg_gap_days_recent >= 70:
            confidence_score -= 2
        confidence_score = clamp(confidence_score, 20.0, 95.0)

        improvement_score = 50.0
        improvement_score += label_bonus(direction, {"STRONG_UP": 18, "UP": 10, "STABLE": 0, "DOWN": -12, "STRONG_DOWN": -20})
        improvement_score += label_bonus(career_phase, {"EMERGING": 7, "ASCENDING": 12, "PEAK": 2, "PLATEAU": -3, "DECLINING": -12})
        improvement_score += label_bonus(improvement_profile, {"RAPID": 10, "STEADY": 5, "FLAT": 0, "DECLINING": -10})
        improvement_score += label_bonus(consistency_profile, {"ELITE": 4, "HIGH": 3, "MEDIUM": 1, "LOW": -2})
        improvement_score += label_bonus(freshness_profile, {"PEAK_THIRD_UP": 6, "SECOND_UP": 3, "FIRST_UP": 1, "NEEDS_RACING": -4})
        improvement_score += label_bonus(archetype_label, {"IMPROVING_YOUNGSTER": 7, "HIGH_CEILING": 5, "ELITE_PERFORMER": 3, "LATE_MATURER": 4, "DECLINING_VETERAN": -10, "BOOM_OR_BUST": 1})
        if points_off_peak is not None:
            if points_off_peak <= 3:
                improvement_score += 6
            elif points_off_peak <= 6:
                improvement_score += 3
            elif points_off_peak > 25:
                improvement_score -= 10
            elif points_off_peak > 15:
                improvement_score -= 6
        if strength == "VERY_HIGH":
            improvement_score += 4
        elif strength == "HIGH":
            improvement_score += 2
        elif strength == "LOW":
            improvement_score -= 2
        if volatility >= 80:
            improvement_score -= 4
        elif volatility <= 25:
            improvement_score += 2

        improvement_probability = probability_from_score(improvement_score, 5.0, 90.0)

        regression_score = 35.0
        regression_score += label_bonus(direction, {"STRONG_DOWN": 25, "DOWN": 14, "STABLE": 2, "UP": -6, "STRONG_UP": -12})
        regression_score += label_bonus(career_phase, {"DECLINING": 12, "PLATEAU": 6, "PEAK": 4, "ASCENDING": -4, "EMERGING": -2})
        regression_score += label_bonus(improvement_profile, {"DECLINING": 10, "FLAT": 2, "STEADY": -4, "RAPID": -8})
        regression_score += label_bonus(bounce_risk_label, {"VERY_HIGH": 12, "HIGH": 8, "MEDIUM": 3, "LOW": -2})
        regression_score += label_bonus(regression_risk_label, {"VERY_HIGH": 16, "HIGH": 8, "MEDIUM": 3, "LOW": -2})
        if points_off_peak is not None and points_off_peak >= 8:
            regression_score += 6
        if points_off_peak is not None and points_off_peak <= 2:
            regression_score -= 3
        if volatility >= 75:
            regression_score += 6
        elif volatility <= 25:
            regression_score -= 3
        if freshness_profile == "NEEDS_RACING":
            regression_score += 4
        if archetype_label == "DECLINING_VETERAN":
            regression_score += 8
        regression_probability = probability_from_score(regression_score, 5.0, 95.0)

        peak_revisit_score = 45.0
        peak_revisit_score += label_bonus(direction, {"STRONG_UP": 18, "UP": 10, "STABLE": 0, "DOWN": -10, "STRONG_DOWN": -18})
        peak_revisit_score += label_bonus(career_phase, {"PEAK": 10, "ASCENDING": 6, "EMERGING": 4, "PLATEAU": -4, "DECLINING": -12})
        peak_revisit_score += label_bonus(improvement_profile, {"RAPID": 8, "STEADY": 4, "FLAT": 0, "DECLINING": -10})
        if points_off_peak is not None:
            peak_revisit_score -= points_off_peak * 2.2
        if days_since_peak is not None and days_since_peak > 365:
            peak_revisit_score -= 10
        elif days_since_peak is not None and days_since_peak > 180:
            peak_revisit_score -= 6
        peak_revisit_probability = probability_from_score(peak_revisit_score, 1.0, 85.0)

        breakout_probability = label_bonus(breakout_potential, {"VERY_HIGH": 72, "HIGH": 58, "MEDIUM": 42, "LOW": 22}, 22.0)
        breakout_probability += label_bonus(direction, {"STRONG_UP": 6, "UP": 3, "DOWN": -4, "STRONG_DOWN": -8})
        breakout_probability += label_bonus(career_phase, {"EMERGING": 4, "ASCENDING": 6, "PEAK": -2, "DECLINING": -6})
        breakout_probability = probability_from_score(breakout_probability, 5.0, 85.0)

        bounce_probability = label_bonus(bounce_risk_label, {"VERY_HIGH": 72, "HIGH": 58, "MEDIUM": 42, "LOW": 18}, 18.0)
        if improvement_last_3 is not None and improvement_last_3 >= 4.0:
            bounce_probability += 4
        if volatility >= 70:
            bounce_probability += 5
        bounce_probability = probability_from_score(bounce_probability, 5.0, 85.0)

        base_projection = trajectory_next if trajectory_next is not None else latest_rating
        phase_adjust = label_bonus(career_phase, {"EMERGING": 0.6, "ASCENDING": 0.8, "PEAK": 0.2, "PLATEAU": 0.0, "DECLINING": -1.0})
        freshness_adjust = label_bonus(freshness_profile, {"PEAK_THIRD_UP": 0.8, "SECOND_UP": 0.4, "FIRST_UP": 0.2, "NEEDS_RACING": -0.6})
        archetype_adjust = label_bonus(archetype_label, {"IMPROVING_YOUNGSTER": 0.7, "HIGH_CEILING": 0.4, "LATE_MATURER": 0.4, "DECLINING_VETERAN": -0.8, "ELITE_PERFORMER": 0.3})
        direction_adjust = label_bonus(direction, {"STRONG_UP": 0.8, "UP": 0.4, "STABLE": 0.0, "DOWN": -0.5, "STRONG_DOWN": -1.0})
        consistency_adjust = label_bonus(consistency_profile, {"ELITE": 0.3, "HIGH": 0.2, "MEDIUM": 0.0, "LOW": -0.3})
        volatility_adjust = -0.5 if volatility >= 70 else (0.2 if volatility <= 25 else 0.0)

        next_run_projection = None
        if base_projection is not None:
            next_run_projection = clamp(base_projection + phase_adjust + freshness_adjust + archetype_adjust + direction_adjust + consistency_adjust + volatility_adjust, 20.0, 115.0)

        expected_improvement = None if next_run_projection is None or latest_rating is None else max(0.0, next_run_projection - latest_rating)
        expected_regression = None if next_run_projection is None or latest_rating is None else max(0.0, latest_rating - next_run_projection)

        ceiling_projection = trajectory_ceiling
        if ceiling_projection is None and next_run_projection is not None:
            ceiling_projection = next_run_projection + 2.0
        if next_run_projection is not None:
            upside_bonus = 0.0
            if breakout_probability >= 70:
                upside_bonus = 1.5
            elif breakout_probability >= 55:
                upside_bonus = 0.8
            ceiling_projection = max(ceiling_projection or next_run_projection, next_run_projection + upside_bonus)
        if peak_rating is not None:
            peak_allowance = 0.0
            if breakout_probability >= 70:
                peak_allowance = 1.5
            elif breakout_probability >= 55:
                peak_allowance = 0.8
            ceiling_projection = max(ceiling_projection or peak_rating, peak_rating + peak_allowance)

        floor_projection = trajectory_floor
        if floor_projection is None and latest_rating is not None:
            floor_projection = latest_rating - 2.0
        risk_allowance = 0.8
        if regression_probability >= 75:
            risk_allowance = 4.0
        elif regression_probability >= 60:
            risk_allowance = 2.5
        elif regression_probability >= 45:
            risk_allowance = 1.5
        if next_run_projection is not None:
            floor_projection = min(floor_projection or next_run_projection, next_run_projection - risk_allowance)
        if latest_rating is not None:
            floor_projection = min(floor_projection or latest_rating, latest_rating - risk_allowance)
        if floor_projection is not None:
            floor_projection = clamp(floor_projection, 15.0, ceiling_projection if ceiling_projection is not None else 115.0)

        runs_to_peak_estimate = None
        days_to_peak_estimate = None
        improvement_per_run = max(0.5, min(4.0, expected_improvement if expected_improvement is not None and expected_improvement > 0 else 0.8))
        if points_off_peak is not None and points_off_peak > 0 and peak_revisit_probability >= 40 and improvement_probability >= 55:
            runs_to_peak_estimate = int(math.ceil(points_off_peak / improvement_per_run))
            if avg_gap_days_recent is not None:
                days_to_peak_estimate = int(round(runs_to_peak_estimate * avg_gap_days_recent))

        projection_confidence = projection_confidence_label(confidence_score)
        projection_band = projection_band_label(
            next_run_projection=next_run_projection,
            latest_rating=latest_rating,
            improvement_probability=improvement_probability,
            regression_probability=regression_probability,
            breakout_probability=breakout_probability,
            bounce_probability=bounce_probability,
        )

        rows.append(
            {
                "horse": horse,
                "horse_key": horse_key,
                "latest_rating": round_or_blank(latest_rating, 1),
                "peak_rating": round_or_blank(peak_rating, 1),
                "average_rating": round_or_blank(average_rating, 1),
                "next_run_projection": round_or_blank(next_run_projection, 1),
                "expected_improvement": round_or_blank(expected_improvement, 1),
                "expected_regression": round_or_blank(expected_regression, 1),
                "ceiling_projection": round_or_blank(ceiling_projection, 1),
                "floor_projection": round_or_blank(floor_projection, 1),
                "improvement_probability": round_or_blank(improvement_probability, 1),
                "regression_probability": round_or_blank(regression_probability, 1),
                "peak_revisit_probability": round_or_blank(peak_revisit_probability, 1),
                "breakout_probability": round_or_blank(breakout_probability, 1),
                "bounce_probability": round_or_blank(bounce_probability, 1),
                "runs_to_peak_estimate": "" if runs_to_peak_estimate is None else str(runs_to_peak_estimate),
                "days_to_peak_estimate": "" if days_to_peak_estimate is None else str(days_to_peak_estimate),
                "projection_band": projection_band,
                "projection_confidence": projection_confidence,
                "built_at": built_at,
            }
        )

    output = pd.DataFrame(rows).sort_values(["horse"]).reset_index(drop=True)
    if output.empty:
        raise ValueError("Horse projection engine produced no rows.")

    output.to_csv(OUT_PATH, index=False)

    probability_columns = [
        "improvement_probability",
        "regression_probability",
        "peak_revisit_probability",
        "breakout_probability",
        "bounce_probability",
    ]
    probability_ranges = []
    for column in probability_columns:
        values = pd.to_numeric(output[column], errors="coerce").dropna()
        if values.empty:
            probability_ranges.append(f"{column}:NA")
        else:
            probability_ranges.append(f"{column}:{values.min():.1f}-{values.max():.1f}")

    summary = pd.DataFrame(
        [
            {
                "status": "PASS" if len(output) == output["horse_key"].nunique() else "WARN",
                "rows": len(output),
                "unique_horses": output["horse_key"].nunique(),
                "projection_band_counts": value_counts_summary(output["projection_band"]),
                "confidence_counts": value_counts_summary(output["projection_confidence"]),
                "null_counts": "; ".join(
                    f"{column}:{int(output[column].astype(str).str.strip().eq('').sum())}"
                    for column in [
                        "latest_rating",
                        "peak_rating",
                        "average_rating",
                        "next_run_projection",
                        "expected_improvement",
                        "expected_regression",
                        "ceiling_projection",
                        "floor_projection",
                        "improvement_probability",
                        "regression_probability",
                        "peak_revisit_probability",
                        "breakout_probability",
                        "bounce_probability",
                        "runs_to_peak_estimate",
                        "days_to_peak_estimate",
                        "projection_band",
                        "projection_confidence",
                    ]
                ),
                "probability_ranges": "; ".join(probability_ranges),
                "source_run_rows": len(runs),
                "source_career_rows": len(career),
                "source_archetype_rows": len(archetype),
                "source_trajectory_rows": len(trajectory),
                "built_at": built_at,
            }
        ]
    )
    summary.to_csv(SUMMARY_PATH, index=False)

    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
