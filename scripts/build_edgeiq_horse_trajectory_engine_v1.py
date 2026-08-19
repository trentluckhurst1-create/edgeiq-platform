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
OUT_PATH = DATA / "edgeiq_horse_trajectory_engine_v1.csv"
SUMMARY_PATH = DATA / "edgeiq_horse_trajectory_engine_v1_summary.csv"


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


def average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def round_or_blank(value: float | None, digits: int = 1) -> str:
    if value is None or not math.isfinite(value):
        return ""
    return f"{value:.{digits}f}"


def value_counts_summary(series: pd.Series) -> str:
    counts = series.value_counts()
    return "; ".join(f"{index}:{int(count)}" for index, count in counts.items())


def first_non_blank(row: pd.Series, columns: list[str]) -> str:
    for column in columns:
        if column in row.index:
            value = safe_text(row[column])
            if value:
                return value
    return ""


def previous_window_average(values: list[float], window: int) -> float | None:
    if len(values) <= window:
        return None
    prior = values[:-window]
    if not prior:
        return None
    segment = prior[-window:] if len(prior) >= window else prior
    return average(segment)


def improvement_delta(values: list[float], window: int) -> float | None:
    recent = average(values[-window:]) if values else None
    prior = previous_window_average(values, window)
    if recent is None or prior is None:
        return None
    return recent - prior


def weighted_momentum(
    improvement_last_3: float | None,
    improvement_last_5: float | None,
    improvement_last_10: float | None,
) -> float:
    weights = []
    if improvement_last_3 is not None:
        weights.append((0.5, improvement_last_3))
    if improvement_last_5 is not None:
        weights.append((0.3, improvement_last_5))
    if improvement_last_10 is not None:
        weights.append((0.2, improvement_last_10))
    if not weights:
        return 0.0
    weighted_total = sum(weight * value for weight, value in weights)
    total_weight = sum(weight for weight, _ in weights)
    return weighted_total / total_weight if total_weight else 0.0


def trajectory_direction(momentum: float, improvement_last_3: float | None) -> str:
    fast_signal = improvement_last_3 if improvement_last_3 is not None else momentum
    if momentum >= 4.0 or fast_signal >= 5.0:
        return "STRONG_UP"
    if momentum >= 1.5 or fast_signal >= 2.0:
        return "UP"
    if momentum <= -4.0 or fast_signal <= -5.0:
        return "STRONG_DOWN"
    if momentum <= -1.5 or fast_signal <= -2.0:
        return "DOWN"
    return "STABLE"


def trajectory_strength(momentum: float, improvement_last_3: float | None) -> str:
    strength_value = max(abs(momentum), abs(improvement_last_3 or 0.0))
    if strength_value >= 5.0:
        return "VERY_HIGH"
    if strength_value >= 3.0:
        return "HIGH"
    if strength_value >= 1.5:
        return "MEDIUM"
    return "LOW"


def breakout_potential_label(
    *,
    career_starts: int,
    direction: str,
    points_off_peak: float | None,
    consistency_score: float | None,
    phase: str,
) -> str:
    if points_off_peak is None:
        return "LOW"
    if phase in {"EMERGING", "ASCENDING"} and direction == "STRONG_UP" and points_off_peak <= 6:
        return "VERY_HIGH"
    if direction in {"STRONG_UP", "UP"} and points_off_peak <= 8 and career_starts <= 10:
        return "HIGH"
    if direction in {"UP", "STABLE"} and points_off_peak <= 5 and (consistency_score is None or consistency_score >= 40):
        return "MEDIUM"
    return "LOW"


def bounce_risk_label(
    *,
    improvement_last_3: float | None,
    points_off_peak: float | None,
    volatility_score: float | None,
) -> str:
    rise = improvement_last_3 or 0.0
    volatility = volatility_score or 0.0
    if rise >= 6.0 and points_off_peak is not None and points_off_peak <= 2 and volatility >= 60:
        return "VERY_HIGH"
    if rise >= 4.0 and volatility >= 45:
        return "HIGH"
    if rise >= 2.0:
        return "MEDIUM"
    return "LOW"


def regression_risk_label(
    *,
    direction: str,
    points_off_peak: float | None,
    runs_since_peak: int,
    regressor_flag: bool,
    volatility_score: float | None,
) -> str:
    points = points_off_peak or 0.0
    volatility = volatility_score or 0.0
    if direction == "STRONG_DOWN" or (points >= 12 and runs_since_peak >= 5):
        return "VERY_HIGH"
    if direction == "DOWN" or regressor_flag or points >= 8:
        return "HIGH"
    if points >= 5 or volatility >= 65:
        return "MEDIUM"
    return "LOW"


def career_phase_label(
    *,
    development_stage: str,
    direction: str,
    points_off_peak: float | None,
    career_starts: int,
) -> str:
    if development_stage == "EMERGING" or career_starts <= 3:
        return "EMERGING"
    if direction in {"STRONG_UP", "UP"} and (points_off_peak or 999.0) > 2:
        return "ASCENDING"
    if points_off_peak is not None and points_off_peak <= 2 and direction not in {"DOWN", "STRONG_DOWN"}:
        return "PEAK"
    if direction == "STABLE" and (points_off_peak or 999.0) <= 8:
        return "PLATEAU"
    return "DECLINING"


def build_projections(
    *,
    latest_rating: float | None,
    last_3_average: float | None,
    last_5_average: float | None,
    last_10_average: float | None,
    peak_rating: float | None,
    momentum: float,
    breakout_potential: str,
    regression_risk: str,
) -> tuple[float | None, float | None, float | None]:
    values = [value for value in [latest_rating, last_3_average, last_5_average, last_10_average] if value is not None]
    if not values:
        return None, None, None

    latest = latest_rating if latest_rating is not None else values[-1]
    last3 = last_3_average if last_3_average is not None else latest
    last5 = last_5_average if last_5_average is not None else last3
    last10 = last_10_average if last_10_average is not None else last5

    base = (latest * 0.45) + (last3 * 0.30) + (last5 * 0.15) + (last10 * 0.10)
    trend_bonus = clamp(momentum * 0.45, -4.0, 4.0)
    next_run = clamp(base + trend_bonus, 20.0, 115.0)

    ceiling = max(peak_rating or next_run, next_run + max(momentum, 0.0) * 0.75)
    if breakout_potential == "VERY_HIGH":
        ceiling += 1.5
    elif breakout_potential == "HIGH":
        ceiling += 0.8

    risk_penalty = 0.0
    if regression_risk == "VERY_HIGH":
        risk_penalty = 4.0
    elif regression_risk == "HIGH":
        risk_penalty = 2.5
    elif regression_risk == "MEDIUM":
        risk_penalty = 1.2

    floor_base = min(values)
    floor = clamp(floor_base - risk_penalty, 15.0, ceiling)
    return next_run, ceiling, floor


def main() -> None:
    for path in [RUN_SOURCE, CAREER_SOURCE, ARCHETYPE_SOURCE]:
        if not path.exists():
            raise FileNotFoundError(f"Missing source file: {path}")

    runs = pd.read_csv(RUN_SOURCE, dtype=str).fillna("")
    career = pd.read_csv(CAREER_SOURCE, dtype=str).fillna("")
    archetype = pd.read_csv(ARCHETYPE_SOURCE, dtype=str).fillna("")

    if runs.empty:
        raise ValueError("Historical ratings master is empty.")
    if career.empty:
        raise ValueError("Horse career intelligence source is empty.")
    if archetype.empty:
        raise ValueError("Horse archetype source is empty.")

    runs["horse_key_norm"] = runs.apply(
        lambda row: normalize_horse(first_non_blank(row, ["horse_key", "horse"])),
        axis=1,
    )
    runs["race_date_dt"] = runs["race_date"].map(parse_date)
    runs["performance_rating_num"] = runs["performance_rating"].map(parse_float)

    career["horse_key_norm"] = career.apply(
        lambda row: normalize_horse(first_non_blank(row, ["horse_key", "horse"])),
        axis=1,
    )
    archetype["horse_key_norm"] = archetype.apply(
        lambda row: normalize_horse(first_non_blank(row, ["horse_key", "horse"])),
        axis=1,
    )

    career_map = {
        row["horse_key_norm"]: row
        for _, row in career.iterrows()
        if safe_text(row["horse_key_norm"])
    }
    archetype_map = {
        row["horse_key_norm"]: row
        for _, row in archetype.iterrows()
        if safe_text(row["horse_key_norm"])
    }

    rows: list[dict[str, object]] = []
    built_at = now_iso()

    for horse_key_norm, frame in runs.groupby("horse_key_norm", sort=False):
        if not horse_key_norm:
            continue

        frame = frame.sort_values(["race_date_dt", "track", "race_no"], kind="stable")
        rated = frame[frame["performance_rating_num"].notna()].copy()
        if rated.empty:
            continue

        ratings = [float(value) for value in rated["performance_rating_num"].tolist() if value is not None]
        career_row = career_map.get(horse_key_norm)
        archetype_row = archetype_map.get(horse_key_norm)

        horse_name = first_non_blank(frame.iloc[-1], ["horse"]) or first_non_blank(frame.iloc[0], ["horse"])
        horse_key = first_non_blank(frame.iloc[-1], ["horse_key"]) or horse_key_norm

        latest_rating = parse_float(career_row["latest_rating"]) if career_row is not None else None
        peak_rating = parse_float(career_row["peak_rating"]) if career_row is not None else None
        average_rating = parse_float(career_row["average_rating"]) if career_row is not None else None
        last_5_average = parse_float(career_row["last_5_average"]) if career_row is not None else None
        last_10_average = parse_float(career_row["last_10_average"]) if career_row is not None else None
        last_3_average = parse_float(archetype_row["last_3_average"]) if archetype_row is not None else None

        latest_rating = latest_rating if latest_rating is not None else ratings[-1]
        peak_rating = peak_rating if peak_rating is not None else max(ratings)
        average_rating = average_rating if average_rating is not None else average(ratings)
        last_3_average = last_3_average if last_3_average is not None else average(ratings[-3:])
        last_5_average = last_5_average if last_5_average is not None else average(ratings[-5:])
        last_10_average = last_10_average if last_10_average is not None else average(ratings[-10:])

        improvement_last_3 = improvement_delta(ratings, 3)
        improvement_last_5 = improvement_delta(ratings, 5)
        improvement_last_10 = improvement_delta(ratings, 10)
        momentum = weighted_momentum(improvement_last_3, improvement_last_5, improvement_last_10)

        points_off_peak = None
        percent_of_peak = None
        if latest_rating is not None and peak_rating is not None and peak_rating > 0:
            points_off_peak = max(0.0, peak_rating - latest_rating)
            percent_of_peak = (latest_rating / peak_rating) * 100.0

        runs_since_peak = parse_int(archetype_row["runs_since_peak"]) if archetype_row is not None else None
        if runs_since_peak is None:
            peak_index = max(range(len(ratings)), key=lambda index: ratings[index])
            runs_since_peak = max(0, len(ratings) - peak_index - 1)

        days_since_peak = parse_int(archetype_row["days_since_peak"]) if archetype_row is not None else None
        if days_since_peak is None and not rated.empty:
            peak_row = rated.loc[rated["performance_rating_num"].astype(float).idxmax()]
            latest_row = rated.iloc[-1]
            peak_date = peak_row["race_date_dt"]
            latest_date = latest_row["race_date_dt"]
            if not pd.isna(peak_date) and not pd.isna(latest_date):
                days_since_peak = int((latest_date - peak_date).days)

        consistency_score = parse_float(career_row["consistency_score"]) if career_row is not None else None
        volatility_score = parse_float(career_row["volatility_score"]) if career_row is not None else None
        development_stage = safe_text(archetype_row["development_stage"]).upper() if archetype_row is not None else ""
        regressor_flag = safe_text(archetype_row["regressor_flag"]).upper() == "YES" if archetype_row is not None else False

        direction = trajectory_direction(momentum, improvement_last_3)
        strength = trajectory_strength(momentum, improvement_last_3)
        phase = career_phase_label(
            development_stage=development_stage,
            direction=direction,
            points_off_peak=points_off_peak,
            career_starts=len(ratings),
        )
        breakout_potential = breakout_potential_label(
            career_starts=len(ratings),
            direction=direction,
            points_off_peak=points_off_peak,
            consistency_score=consistency_score,
            phase=phase,
        )
        bounce_risk = bounce_risk_label(
            improvement_last_3=improvement_last_3,
            points_off_peak=points_off_peak,
            volatility_score=volatility_score,
        )
        regression_risk = regression_risk_label(
            direction=direction,
            points_off_peak=points_off_peak,
            runs_since_peak=runs_since_peak or 0,
            regressor_flag=regressor_flag,
            volatility_score=volatility_score,
        )

        trajectory_score = clamp(
            50.0
            + (momentum * 5.0)
            + (((percent_of_peak or 0.0) - 80.0) * 0.45)
            + (((consistency_score or 50.0) - 50.0) * 0.12)
            - (((volatility_score or 50.0) - 50.0) * 0.08),
            0.0,
            100.0,
        )

        next_run_projection, ceiling_projection, floor_projection = build_projections(
            latest_rating=latest_rating,
            last_3_average=last_3_average,
            last_5_average=last_5_average,
            last_10_average=last_10_average,
            peak_rating=peak_rating,
            momentum=momentum,
            breakout_potential=breakout_potential,
            regression_risk=regression_risk,
        )

        rows.append(
            {
                "horse": horse_name,
                "horse_key": horse_key,
                "latest_rating": round_or_blank(latest_rating, 1),
                "peak_rating": round_or_blank(peak_rating, 1),
                "average_rating": round_or_blank(average_rating, 1),
                "last_3_average": round_or_blank(last_3_average, 1),
                "last_5_average": round_or_blank(last_5_average, 1),
                "last_10_average": round_or_blank(last_10_average, 1),
                "trajectory_direction": direction,
                "trajectory_strength": strength,
                "trajectory_score": round_or_blank(trajectory_score, 1),
                "points_off_peak": round_or_blank(points_off_peak, 1),
                "percent_of_peak": round_or_blank(percent_of_peak, 1),
                "runs_since_peak": "" if runs_since_peak is None else str(runs_since_peak),
                "days_since_peak": "" if days_since_peak is None else str(days_since_peak),
                "improvement_last_3": round_or_blank(improvement_last_3, 1),
                "improvement_last_5": round_or_blank(improvement_last_5, 1),
                "improvement_last_10": round_or_blank(improvement_last_10, 1),
                "bounce_risk": bounce_risk,
                "regression_risk": regression_risk,
                "breakout_potential": breakout_potential,
                "career_phase": phase,
                "next_run_projection": round_or_blank(next_run_projection, 1),
                "ceiling_projection": round_or_blank(ceiling_projection, 1),
                "floor_projection": round_or_blank(floor_projection, 1),
                "built_at": built_at,
            }
        )

    output = pd.DataFrame(rows).sort_values(["horse"]).reset_index(drop=True)
    if output.empty:
        raise ValueError("Horse trajectory engine produced no rows.")

    output.to_csv(OUT_PATH, index=False)

    summary = pd.DataFrame(
        [
            {
                "status": "PASS" if len(output) == output["horse_key"].nunique() else "WARN",
                "rows": len(output),
                "unique_horses": output["horse_key"].nunique(),
                "direction_counts": value_counts_summary(output["trajectory_direction"]),
                "strength_counts": value_counts_summary(output["trajectory_strength"]),
                "phase_counts": value_counts_summary(output["career_phase"]),
                "breakout_potential_counts": value_counts_summary(output["breakout_potential"]),
                "bounce_risk_counts": value_counts_summary(output["bounce_risk"]),
                "regression_risk_counts": value_counts_summary(output["regression_risk"]),
                "null_counts": "; ".join(
                    f"{column}:{int(output[column].astype(str).str.strip().eq('').sum())}"
                    for column in [
                        "latest_rating",
                        "peak_rating",
                        "average_rating",
                        "last_3_average",
                        "last_5_average",
                        "last_10_average",
                        "trajectory_direction",
                        "trajectory_strength",
                        "trajectory_score",
                        "points_off_peak",
                        "percent_of_peak",
                        "runs_since_peak",
                        "days_since_peak",
                        "improvement_last_3",
                        "improvement_last_5",
                        "improvement_last_10",
                        "bounce_risk",
                        "regression_risk",
                        "breakout_potential",
                        "career_phase",
                        "next_run_projection",
                        "ceiling_projection",
                        "floor_projection",
                    ]
                ),
                "source_run_rows": len(runs),
                "source_career_rows": len(career),
                "source_archetype_rows": len(archetype),
                "built_at": built_at,
            }
        ]
    )
    summary.to_csv(SUMMARY_PATH, index=False)

    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
