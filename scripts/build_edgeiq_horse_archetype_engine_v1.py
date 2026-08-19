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
OUT_PATH = DATA / "edgeiq_horse_archetype_engine_v1.csv"
SUMMARY_PATH = DATA / "edgeiq_horse_archetype_engine_v1_summary.csv"


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


def normalize_spaces(value: object) -> str:
    return re.sub(r"\s+", " ", safe_text(value)).strip()


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


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def standard_deviation(values: list[float]) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return 0.0
    avg = average(values)
    if avg is None:
        return None
    variance = sum((value - avg) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


def linear_slope(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    x = list(range(len(values)))
    x_mean = sum(x) / len(x)
    y_mean = sum(values) / len(values)
    denom = sum((xi - x_mean) ** 2 for xi in x)
    if denom <= 0:
        return None
    numer = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, values))
    return numer / denom


def first_non_blank(row: pd.Series, columns: list[str]) -> str:
    for column in columns:
        if column in row.index:
            value = safe_text(row[column])
            if value:
                return value
    return ""


def canonical_condition(value: object) -> str:
    text = upper_text(value)
    if not text:
        return "UNKNOWN"
    if text.startswith("GOOD"):
        return "GOOD"
    if text.startswith("SOFT"):
        return "SOFT"
    if text.startswith("HEAVY"):
        return "HEAVY"
    if text.startswith("FIRM"):
        return "FIRM"
    if "SYNTH" in text or "POLY" in text or "TAPETA" in text:
        return "SYNTH"
    return normalize_spaces(text) or "UNKNOWN"


def canonical_class(value: object) -> str:
    text = normalize_spaces(upper_text(value).replace("-", " "))
    if not text:
        return "UNKNOWN"
    if "GROUP 1" in text or re.search(r"\bG1\b", text):
        return "GROUP 1"
    if "GROUP 2" in text or re.search(r"\bG2\b", text):
        return "GROUP 2"
    if "GROUP 3" in text or re.search(r"\bG3\b", text):
        return "GROUP 3"
    if "LISTED" in text:
        return "LISTED"
    if "MAIDEN" in text or " MDN" in f" {text} ":
        return "MAIDEN"
    bm = re.search(r"\bBM\s?(\d{2,3})\b", text) or re.search(r"\bBENCHMARK\s?(\d{2,3})\b", text)
    if bm:
        return f"BM{bm.group(1)}"
    rating = re.search(r"\bRTG\s?(\d{2,3})\b", text) or re.search(r"\bRATING\s?(\d{2,3})\b", text)
    if rating:
        return f"RTG{rating.group(1)}"
    cls = re.search(r"\bCLASS\s?(\d)\b", text) or re.search(r"\bCL\s?(\d)\b", text)
    if cls:
        return f"CLASS {cls.group(1)}"
    if "HANDICAP" in text or re.search(r"\bHCP\b", text):
        return "HANDICAP"
    if "OPEN" in text:
        return "OPEN"
    return text


def distance_bucket(value: object) -> str:
    distance = parse_float(value)
    if distance is None:
        return "UNKNOWN"
    if distance < 1000:
        return "800-999"
    if distance < 1200:
        return "1000-1199"
    if distance < 1400:
        return "1200-1399"
    if distance < 1600:
        return "1400-1599"
    if distance < 2000:
        return "1600-1999"
    return "2000+"


def season_label(date_value: pd.Timestamp | pd.NaT) -> str:
    if pd.isna(date_value):
        return "UNKNOWN"
    month = int(date_value.month)
    if month in {12, 1, 2}:
        return "SUMMER"
    if month in {3, 4, 5}:
        return "AUTUMN"
    if month in {6, 7, 8}:
        return "WINTER"
    return "SPRING"


def value_counts_summary(series: pd.Series) -> str:
    counts = series.value_counts()
    return "; ".join(f"{index}:{int(count)}" for index, count in counts.items())


def to_yes_no(value: bool) -> str:
    return "YES" if value else "NO"


def round_or_blank(value: float | None, digits: int = 1) -> str:
    if value is None or not math.isfinite(value):
        return ""
    return f"{value:.{digits}f}"


def choose_best_group(
    records: list[dict[str, object]],
    key: str,
    min_starts: int = 1,
) -> tuple[str, int, float | None, float | None]:
    grouped: dict[str, list[float]] = {}
    for record in records:
        label = safe_text(record.get(key))
        rating = record.get("performance_rating_num")
        if not label or rating is None:
            continue
        grouped.setdefault(label, []).append(float(rating))

    if not grouped:
        return "UNKNOWN", 0, None, None

    ranked = sorted(
        (
            (
                label,
                len(values),
                average(values),
            )
            for label, values in grouped.items()
            if len(values) >= min_starts
        ),
        key=lambda item: ((item[2] or -999), item[1]),
        reverse=True,
    )

    if not ranked:
        label, values = max(grouped.items(), key=lambda item: len(item[1]))
        return label, len(values), average(values), None

    best_label, best_count, best_avg = ranked[0]
    second_avg = ranked[1][2] if len(ranked) > 1 else None
    return best_label, best_count, best_avg, second_avg


def build_freshness_profile(records: list[dict[str, object]]) -> str:
    if not records:
        return "NO_PATTERN"

    ordered = sorted(records, key=lambda row: row["race_date_dt"])
    prep_labels: dict[str, list[float]] = {"FIRST_UP": [], "SECOND_UP": [], "PEAK_THIRD_UP": [], "NEEDS_RACING": []}
    previous_date: pd.Timestamp | None = None
    prep_run_number = 0

    for record in ordered:
        race_date = record["race_date_dt"]
        rating = record["performance_rating_num"]
        if pd.isna(race_date) or rating is None:
            continue
        if previous_date is None or (race_date - previous_date).days >= 49:
            prep_run_number = 1
        else:
            prep_run_number += 1

        if prep_run_number == 1:
            prep_labels["FIRST_UP"].append(float(rating))
        elif prep_run_number == 2:
            prep_labels["SECOND_UP"].append(float(rating))
        elif prep_run_number == 3:
            prep_labels["PEAK_THIRD_UP"].append(float(rating))
        else:
            prep_labels["NEEDS_RACING"].append(float(rating))

        previous_date = race_date

    averages = {label: average(values) for label, values in prep_labels.items() if len(values) >= 2}
    if not averages:
        return "NO_PATTERN"

    ranked = sorted(averages.items(), key=lambda item: item[1] or -999, reverse=True)
    top_label, top_avg = ranked[0]
    second_avg = ranked[1][1] if len(ranked) > 1 else None
    if second_avg is None:
        return top_label if len(prep_labels[top_label]) >= 3 else "NO_PATTERN"
    if top_avg is not None and second_avg is not None and top_avg - second_avg >= 2.0:
        return top_label
    return "NO_PATTERN"


def build_distance_profile(records: list[dict[str, object]], overall_avg: float | None) -> tuple[str, bool]:
    if not records:
        return "VERSATILE", False

    grouped: dict[str, list[float]] = {}
    for record in records:
        bucket = safe_text(record.get("distance_bucket"))
        rating = record.get("performance_rating_num")
        if not bucket or rating is None:
            continue
        grouped.setdefault(bucket, []).append(float(rating))

    if not grouped:
        return "VERSATILE", False

    eligible = {bucket: values for bucket, values in grouped.items() if len(values) >= 2}
    averages = {bucket: average(values) for bucket, values in eligible.items()}

    if len(eligible) >= 3:
        avg_values = [value for value in averages.values() if value is not None]
        if avg_values and max(avg_values) - min(avg_values) <= 4.0:
            return "VERSATILE", False

    best_bucket, best_count, best_avg, second_avg = choose_best_group(records, "distance_bucket", min_starts=2)
    if best_bucket == "UNKNOWN":
        return "VERSATILE", False

    specialist = (
        best_count >= 3
        and best_avg is not None
        and overall_avg is not None
        and best_avg - overall_avg >= 3.0
        and (second_avg is None or best_avg - second_avg >= 2.0)
    )

    if best_bucket in {"800-999", "1000-1199", "1200-1399"}:
        return "SPRINTER", specialist
    if best_bucket == "1400-1599":
        return "MILER", specialist
    if best_bucket == "1600-1999":
        return "MIDDLE_DISTANCE", specialist
    if best_bucket == "2000+":
        return "STAYER", specialist
    return "VERSATILE", specialist


def build_seasonality_profile(records: list[dict[str, object]], overall_avg: float | None) -> str:
    best_season, best_count, best_avg, second_avg = choose_best_group(records, "season", min_starts=3)
    if best_season == "UNKNOWN" or best_avg is None or overall_avg is None:
        return "NO_PATTERN"
    if best_avg - overall_avg < 3.0:
        return "NO_PATTERN"
    if second_avg is not None and best_avg - second_avg < 2.0:
        return "NO_PATTERN"
    return best_season


def build_peak_trend(latest_rating: float | None, peak_rating: float | None) -> tuple[str, float | None]:
    if latest_rating is None or peak_rating is None:
        return "UNKNOWN", None
    delta = latest_rating - peak_rating
    if delta >= 0.5:
        return "NEW_PEAK_SIGNAL", delta
    if delta >= -2.0:
        return "AT_PEAK", delta
    if delta >= -5.0:
        return "CLOSE_TO_PEAK", delta
    if delta >= -8.0:
        return "OFF_PEAK", delta
    return "WELL_BELOW_PEAK", delta


def build_improvement_profile(
    latest_ratings: list[float],
    slope: float | None,
    improving_flag: bool,
    regressing_flag: bool,
) -> str:
    last_3 = average(latest_ratings[-3:])
    last_10 = average(latest_ratings[-10:])
    recent_delta = None if last_3 is None or last_10 is None else last_3 - last_10

    if regressing_flag or (slope is not None and slope <= -0.75) or (recent_delta is not None and recent_delta <= -1.5):
        return "DECLINING"
    if (slope is not None and slope >= 2.0) or (recent_delta is not None and recent_delta >= 4.0):
        return "RAPID"
    if improving_flag or (slope is not None and slope >= 0.75) or (recent_delta is not None and recent_delta >= 1.5):
        return "STEADY"
    return "FLAT"


def build_consistency_profile(consistency_score: float | None) -> str:
    if consistency_score is None:
        return "LOW"
    if consistency_score >= 75:
        return "ELITE"
    if consistency_score >= 60:
        return "HIGH"
    if consistency_score >= 40:
        return "MEDIUM"
    return "LOW"


def build_development_stage(
    career_starts: int,
    improvement_profile: str,
    peak_trend: str,
    peak_delta: float | None,
    runs_since_peak: int,
) -> str:
    if career_starts <= 3:
        return "EMERGING"
    if improvement_profile in {"RAPID", "STEADY"} and peak_trend in {"NEW_PEAK_SIGNAL", "AT_PEAK", "CLOSE_TO_PEAK"}:
        return "IMPROVING"
    if peak_trend in {"NEW_PEAK_SIGNAL", "AT_PEAK"} and runs_since_peak <= 3:
        return "PEAK"
    if improvement_profile == "DECLINING" or ((peak_delta or 0.0) <= -6.0 and runs_since_peak >= 5):
        return "DECLINING"
    return "PLATEAU"


def build_peak_age_stage(career_starts: int, peak_start_no: int) -> str:
    if career_starts <= 0 or peak_start_no <= 0:
        return "UNKNOWN"
    ratio = peak_start_no / career_starts
    if ratio <= 0.33:
        return "EARLY"
    if ratio <= 0.66:
        return "MID"
    return "LATE"


def build_track_specialist(records: list[dict[str, object]], overall_avg: float | None) -> bool:
    best_track, best_count, best_avg, second_avg = choose_best_group(records, "track", min_starts=3)
    if best_track == "UNKNOWN" or best_avg is None or overall_avg is None:
        return False
    return best_count >= 3 and best_avg - overall_avg >= 4.0 and (second_avg is None or best_avg - second_avg >= 2.0)


def build_horse_archetype(
    *,
    percentile: float | None,
    peak_rating: float | None,
    average_rating: float | None,
    latest_rating: float | None,
    consistency_profile: str,
    improvement_profile: str,
    development_stage: str,
    distance_specialist: bool,
    track_specialist: bool,
    seasonality_profile: str,
    boom_or_bust_flag: bool,
    late_maturer_flag: bool,
    early_maturer_flag: bool,
    career_starts: int,
    peak_delta: float | None,
    runs_since_peak: int,
) -> str:
    rating_gap = None if peak_rating is None or average_rating is None else peak_rating - average_rating

    if percentile is not None and percentile >= 95 and consistency_profile in {"ELITE", "HIGH"} and (peak_delta is None or peak_delta >= -4):
        return "ELITE_PERFORMER"
    if boom_or_bust_flag:
        return "BOOM_OR_BUST"
    if development_stage == "DECLINING" and career_starts >= 12 and runs_since_peak >= 6 and (peak_delta or 0.0) <= -8.0:
        return "DECLINING_VETERAN"
    if development_stage == "IMPROVING" and career_starts <= 8:
        return "IMPROVING_YOUNGSTER"
    if late_maturer_flag and development_stage in {"IMPROVING", "PEAK"}:
        return "LATE_MATURER"
    if distance_specialist:
        return "DISTANCE_SPECIALIST"
    if track_specialist:
        return "TRACK_SPECIALIST"
    if seasonality_profile != "NO_PATTERN":
        return "SEASONAL_PERFORMER"
    if consistency_profile in {"ELITE", "HIGH"} and career_starts >= 8:
        return "CONSISTENT_GRINDER"
    if rating_gap is not None and rating_gap >= 10.0:
        return "HIGH_CEILING"
    if early_maturer_flag and development_stage == "DECLINING":
        return "DECLINING_VETERAN"
    if improvement_profile in {"RAPID", "STEADY"} and latest_rating is not None and peak_rating is not None and latest_rating >= peak_rating - 3:
        return "IMPROVING_YOUNGSTER"
    return "CONSISTENT_GRINDER" if consistency_profile in {"ELITE", "HIGH"} else "HIGH_CEILING"


def main() -> None:
    if not RUN_SOURCE.exists():
        raise FileNotFoundError(f"Missing historical ratings master: {RUN_SOURCE}")
    if not CAREER_SOURCE.exists():
        raise FileNotFoundError(f"Missing horse career intelligence source: {CAREER_SOURCE}")

    runs = pd.read_csv(RUN_SOURCE, dtype=str).fillna("")
    career = pd.read_csv(CAREER_SOURCE, dtype=str).fillna("")

    if runs.empty:
        raise ValueError("Historical ratings master is empty.")
    if career.empty:
        raise ValueError("Horse career intelligence source is empty.")

    runs["horse_key_norm"] = runs.apply(
        lambda row: normalize_horse(first_non_blank(row, ["horse_key", "horse"])),
        axis=1,
    )
    runs["race_date_dt"] = runs["race_date"].map(parse_date)
    runs["performance_rating_num"] = runs["performance_rating"].map(parse_float)
    runs["distance_bucket"] = runs["distance"].map(distance_bucket)
    runs["condition_group"] = runs["condition"].map(canonical_condition)
    runs["class_group"] = runs["class_name"].map(canonical_class)
    runs["season"] = runs["race_date_dt"].map(season_label)

    career["horse_key_norm"] = career.apply(
        lambda row: normalize_horse(first_non_blank(row, ["horse_key", "horse"])),
        axis=1,
    )
    career_map = {
        row["horse_key_norm"]: row
        for _, row in career.iterrows()
        if safe_text(row["horse_key_norm"])
    }

    rows: list[dict[str, object]] = []

    grouped_runs = runs.groupby("horse_key_norm", sort=False)
    built_at = now_iso()

    for horse_key_norm, frame in grouped_runs:
        if not horse_key_norm:
            continue

        frame = frame.sort_values(["race_date_dt", "track", "race_no"], kind="stable")
        run_records = frame.to_dict("records")
        rated_runs = [record for record in run_records if record.get("performance_rating_num") is not None]
        if not rated_runs:
            continue

        horse_name = first_non_blank(frame.iloc[-1], ["horse"]) or first_non_blank(frame.iloc[0], ["horse"])
        horse_key = first_non_blank(frame.iloc[-1], ["horse_key"]) or horse_key_norm
        career_row = career_map.get(horse_key_norm)

        ratings = [float(record["performance_rating_num"]) for record in rated_runs if record.get("performance_rating_num") is not None]
        career_starts = len(run_records)
        career_wins = sum(1 for record in run_records if parse_int(record.get("finish_pos")) == 1)
        career_places = sum(1 for record in run_records if (parse_int(record.get("finish_pos")) or 999) <= 3)
        average_rating = average(ratings)
        latest_rating = ratings[-1] if ratings else None
        peak_rating = max(ratings) if ratings else None
        median_rating = median(ratings)
        last_3_average = average(ratings[-3:])
        last_5_average = average(ratings[-5:])
        last_10_average = average(ratings[-10:])
        slope = parse_float(career_row["rating_slope"]) if career_row is not None else linear_slope(ratings[-10:])
        career_percentile = parse_float(career_row["career_rating_percentile"]) if career_row is not None else None
        consistency_score = parse_float(career_row["consistency_score"]) if career_row is not None else None
        volatility_score = parse_float(career_row["volatility_score"]) if career_row is not None else None
        if consistency_score is None:
            std_value = standard_deviation(ratings)
            consistency_score = None if std_value is None else clamp(100.0 - (std_value * 7.0), 0.0, 100.0)
        if volatility_score is None:
            std_value = standard_deviation(ratings)
            volatility_score = None if std_value is None else clamp(std_value * 7.0, 0.0, 100.0)

        improving_flag = safe_text(career_row["improving_flag"]).upper() == "YES" if career_row is not None else False
        regressing_flag = safe_text(career_row["regressing_flag"]).upper() == "YES" if career_row is not None else False

        peak_index = max(range(len(rated_runs)), key=lambda idx: float(rated_runs[idx]["performance_rating_num"]))
        peak_start_no = peak_index + 1
        peak_run = rated_runs[peak_index]
        latest_run = rated_runs[-1]
        peak_date = peak_run["race_date_dt"]
        latest_date = latest_run["race_date_dt"]
        days_since_peak = None
        if not pd.isna(peak_date) and not pd.isna(latest_date):
            days_since_peak = int((latest_date - peak_date).days)
        runs_since_peak = max(0, len(rated_runs) - peak_start_no)
        peak_trend, peak_delta = build_peak_trend(latest_rating, peak_rating)
        improvement_profile = build_improvement_profile(ratings, slope, improving_flag, regressing_flag)
        consistency_profile = build_consistency_profile(consistency_score)
        freshness_profile = build_freshness_profile(rated_runs)
        distance_profile, distance_specialist = build_distance_profile(rated_runs, average_rating)
        seasonality_profile = build_seasonality_profile(rated_runs, average_rating)
        development_stage = build_development_stage(career_starts, improvement_profile, peak_trend, peak_delta, runs_since_peak)
        career_peak_age = build_peak_age_stage(career_starts, peak_start_no)
        peak_ratio = peak_start_no / career_starts if career_starts else 0.0
        late_maturer_flag = career_starts >= 8 and peak_ratio >= 0.70
        early_maturer_flag = career_starts >= 8 and peak_ratio <= 0.35 and runs_since_peak >= 3
        boom_or_bust_flag = (
            volatility_score is not None
            and volatility_score >= 70
            and peak_rating is not None
            and average_rating is not None
            and peak_rating - average_rating >= 8
        )
        track_specialist = build_track_specialist(rated_runs, average_rating)
        horse_archetype = build_horse_archetype(
            percentile=career_percentile,
            peak_rating=peak_rating,
            average_rating=average_rating,
            latest_rating=latest_rating,
            consistency_profile=consistency_profile,
            improvement_profile=improvement_profile,
            development_stage=development_stage,
            distance_specialist=distance_specialist,
            track_specialist=track_specialist,
            seasonality_profile=seasonality_profile,
            boom_or_bust_flag=boom_or_bust_flag,
            late_maturer_flag=late_maturer_flag,
            early_maturer_flag=early_maturer_flag,
            career_starts=career_starts,
            peak_delta=peak_delta,
            runs_since_peak=runs_since_peak,
        )

        rows.append(
            {
                "horse": horse_name,
                "horse_key": horse_key,
                "horse_archetype": horse_archetype,
                "development_stage": development_stage,
                "improvement_profile": improvement_profile,
                "consistency_profile": consistency_profile,
                "freshness_profile": freshness_profile,
                "distance_profile": distance_profile,
                "seasonality_profile": seasonality_profile,
                "career_peak_age": career_peak_age,
                "runs_since_peak": str(runs_since_peak),
                "days_since_peak": "" if days_since_peak is None else str(days_since_peak),
                "peak_trend": peak_trend,
                "last_3_average": round_or_blank(last_3_average, 1),
                "last_5_average": round_or_blank(last_5_average, 1),
                "last_10_average": round_or_blank(last_10_average, 1),
                "peak_delta": round_or_blank(peak_delta, 1),
                "career_percentile": round_or_blank(career_percentile, 1),
                "boom_or_bust_flag": to_yes_no(boom_or_bust_flag),
                "improver_flag": to_yes_no(improving_flag or improvement_profile in {"RAPID", "STEADY"}),
                "regressor_flag": to_yes_no(regressing_flag or improvement_profile == "DECLINING"),
                "late_maturer_flag": to_yes_no(late_maturer_flag),
                "early_maturer_flag": to_yes_no(early_maturer_flag),
                "built_at": built_at,
            }
        )

    output = pd.DataFrame(rows)
    if output.empty:
        raise ValueError("Horse archetype engine produced no rows.")

    output = output.sort_values(["horse"]).reset_index(drop=True)
    output.to_csv(OUT_PATH, index=False)

    summary = pd.DataFrame(
        [
            {
                "status": "PASS" if len(output) == output["horse_key"].nunique() else "WARN",
                "rows": len(output),
                "unique_horses": output["horse_key"].nunique(),
                "archetype_counts": value_counts_summary(output["horse_archetype"]),
                "development_stage_counts": value_counts_summary(output["development_stage"]),
                "improvement_profile_counts": value_counts_summary(output["improvement_profile"]),
                "consistency_profile_counts": value_counts_summary(output["consistency_profile"]),
                "freshness_profile_counts": value_counts_summary(output["freshness_profile"]),
                "distance_profile_counts": value_counts_summary(output["distance_profile"]),
                "seasonality_profile_counts": value_counts_summary(output["seasonality_profile"]),
                "null_counts": "; ".join(
                    f"{column}:{int(output[column].astype(str).str.strip().eq('').sum())}"
                    for column in [
                        "horse_archetype",
                        "development_stage",
                        "improvement_profile",
                        "consistency_profile",
                        "freshness_profile",
                        "distance_profile",
                        "seasonality_profile",
                        "career_peak_age",
                        "runs_since_peak",
                        "days_since_peak",
                        "peak_trend",
                        "career_percentile",
                    ]
                ),
                "source_run_rows": len(runs),
                "source_career_rows": len(career),
                "built_at": built_at,
            }
        ]
    )
    summary.to_csv(SUMMARY_PATH, index=False)

    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
