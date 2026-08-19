from __future__ import annotations

import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SOURCE_PATH = DATA / "edgeiq_historical_run_ratings_master_v1.csv"
OUT_PATH = DATA / "edgeiq_horse_career_intelligence_v1.csv"
SUMMARY_PATH = DATA / "edgeiq_horse_career_intelligence_v1_summary.csv"


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


def parse_finish(value: object) -> int | None:
    text = upper_text(value)
    if not text:
        return None
    if text in {"SCR", "SCRATCHED", "DNS", "DNF", "VAC"}:
        return None
    match = re.search(r"\d+", text)
    if not match:
        return None
    try:
        return int(match.group(0))
    except ValueError:
        return None


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def render_metric(value: float | None, digits: int = 1) -> str:
    if value is None or not math.isfinite(value):
        return ""
    return f"{value:.{digits}f}"


def average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
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


def consecutive_swings(values: list[float]) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return 0.0
    swings = [abs(curr - prev) for prev, curr in zip(values[:-1], values[1:])]
    return average(swings)


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
    if "SYNTH" in text or "POLY" in text or "TAPETA" in text:
        return "SYNTH"
    if text.startswith("FIRM"):
        return "FIRM"
    return normalize_spaces(text) or "UNKNOWN"


def canonical_class(value: object) -> str:
    text = upper_text(value)
    if not text:
        return "UNKNOWN"
    text = normalize_spaces(text.replace("-", " "))
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
    cl = re.search(r"\bCLASS\s?(\d)\b", text) or re.search(r"\bCL\s?(\d)\b", text)
    if cl:
        return f"CLASS {cl.group(1)}"
    if "HANDICAP" in text or re.search(r"\bHCP\b", text):
        return "HANDICAP"
    if "OPEN" in text:
        return "OPEN"
    return text or "UNKNOWN"


def score_from_volatility(value: float | None, scale: float) -> float | None:
    if value is None:
        return None
    return clamp(100.0 - (value * scale), 0.0, 100.0)


def percentile_band(percentile: float | None) -> str:
    if percentile is None:
        return "POOR"
    if percentile >= 95:
        return "ELITE"
    if percentile >= 80:
        return "STRONG"
    if percentile >= 60:
        return "ABOVE_AVERAGE"
    if percentile >= 40:
        return "AVERAGE"
    if percentile >= 20:
        return "BELOW_AVERAGE"
    return "POOR"


def compute_trend(ratings: list[float]) -> tuple[str, float | None, str, str]:
    if not ratings:
        return "STABLE", None, "NO", "NO"

    recent = ratings[-10:]
    recent5 = recent[-5:]
    prior5 = recent[:-5]
    slope = linear_slope(recent)
    recent5_avg = average(recent5)
    prior5_avg = average(prior5) if prior5 else average(recent[:-1]) if len(recent) > 2 else None
    delta = None if recent5_avg is None or prior5_avg is None else recent5_avg - prior5_avg
    std_recent = standard_deviation(recent) or 0.0

    improving = False
    regressing = False
    trend = "STABLE"

    if delta is not None and slope is not None:
        if delta >= 2.0 and slope >= 0.35:
            improving = True
            trend = "IMPROVING"
        elif delta <= -2.0 and slope <= -0.35:
            regressing = True
            trend = "REGRESSING"

    if not improving and not regressing and std_recent >= 7.5 and len(recent) >= 5:
        trend = "INCONSISTENT"

    return trend, slope, "YES" if improving else "NO", "YES" if regressing else "NO"


def build_group_stats(records: list[dict[str, object]], field: str) -> dict[str, dict[str, float]]:
    stats: dict[str, dict[str, float]] = {}
    for record in records:
        label = safe_text(record.get(field))
        rating = record.get("performance_rating_num")
        if not label or rating is None:
            continue
        if label not in stats:
            stats[label] = {"starts": 0.0, "sum_rating": 0.0, "wins": 0.0}
        stats[label]["starts"] += 1.0
        stats[label]["sum_rating"] += float(rating)
        stats[label]["wins"] += float(record.get("won_flag", 0.0))
    return stats


def pick_group_label(records: list[dict[str, object]], field: str, mode: str) -> str:
    stats = build_group_stats(records, field)
    if not stats:
        return ""

    eligible_floor = 2 if any(item["starts"] >= 2 for item in stats.values()) else 1
    ranked: list[tuple[str, float, float, float]] = []
    for label, item in stats.items():
        starts = item["starts"]
        if starts < eligible_floor:
            continue
        avg_rating = item["sum_rating"] / starts if starts else 0.0
        win_rate = item["wins"] / starts if starts else 0.0
        sample_penalty = 0.0 if starts >= 3 else 0.6
        score = avg_rating - sample_penalty
        ranked.append((label, score, win_rate, starts))

    if not ranked:
        return ""

    ranked.sort(
        key=lambda item: (
            -item[1] if mode == "best" else item[1],
            -item[2] if mode == "best" else item[2],
            -item[3],
            item[0],
        )
    )
    return ranked[0][0]


def prepare_records() -> list[dict[str, object]]:
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(f"Missing source file: {SOURCE_PATH}")

    df = pd.read_csv(SOURCE_PATH, dtype=str).fillna("")
    if df.empty:
        raise ValueError("Historical run ratings master is empty.")

    records: list[dict[str, object]] = []
    for row in df.to_dict("records"):
        horse_name = safe_text(row.get("horse"))
        horse_key = safe_text(row.get("horse_key")) or normalize_horse(horse_name)
        rating = parse_float(row.get("performance_rating"))
        if not horse_key or rating is None:
            continue

        race_date_text = safe_text(row.get("race_date"))
        race_date_dt = pd.to_datetime(race_date_text, errors="coerce")
        finish_pos = parse_finish(row.get("finish_pos"))
        records.append(
            {
                "horse": horse_name,
                "horse_key": horse_key,
                "race_date": race_date_text,
                "race_date_dt": race_date_dt,
                "track": normalize_spaces(row.get("track")),
                "race_no": safe_text(row.get("race_no")),
                "distance": safe_text(row.get("distance")),
                "class_name": safe_text(row.get("class_name")),
                "condition": safe_text(row.get("condition")),
                "performance_rating_num": rating,
                "finish_pos": finish_pos,
                "won_flag": 1 if finish_pos == 1 else 0,
                "placed_flag": 1 if finish_pos is not None and finish_pos <= 3 else 0,
                "distance_bucket": distance_bucket(row.get("distance")),
                "condition_bucket": canonical_condition(row.get("condition")),
                "class_bucket": canonical_class(row.get("class_name")),
                "track_bucket": normalize_spaces(row.get("track")),
            }
        )
    return records


def build_career_intelligence() -> tuple[pd.DataFrame, pd.DataFrame]:
    input_records = prepare_records()
    if not input_records:
        raise ValueError("No historical run rating records available.")

    built_at = now_iso()
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in input_records:
        grouped[str(record["horse_key"])].append(record)

    rows: list[dict[str, object]] = []
    for horse_key, records in grouped.items():
        ordered = sorted(
            records,
            key=lambda record: (
                record["race_date_dt"].value if pd.notna(record["race_date_dt"]) else -1,
                str(record["race_date"]),
                str(record["track"]),
                str(record["race_no"]),
                str(record["distance"]),
            ),
        )

        ratings = [float(record["performance_rating_num"]) for record in ordered]
        if not ratings:
            continue

        starts = len(ordered)
        wins = int(sum(int(record["won_flag"]) for record in ordered))
        places = int(sum(int(record["placed_flag"]) for record in ordered))
        latest_record = ordered[-1]
        peak_record = max(
            ordered,
            key=lambda record: (
                float(record["performance_rating_num"]),
                record["race_date_dt"].value if pd.notna(record["race_date_dt"]) else -1,
            ),
        )

        peak_rating = float(peak_record["performance_rating_num"])
        average_rating_value = average(ratings)
        median_rating_value = median(ratings)
        latest_rating = float(latest_record["performance_rating_num"])
        top_three = sorted(ratings, reverse=True)[:3]
        last_five_avg = average(ratings[-5:])
        last_ten_avg = average(ratings[-10:])
        trend, slope, improving_flag, regressing_flag = compute_trend(ratings)
        consistency_score = score_from_volatility(standard_deviation(ratings), 7.5)
        volatility_score = score_from_volatility(consecutive_swings(ratings), 8.5)

        days_since_peak = None
        latest_date = latest_record["race_date_dt"]
        peak_date = peak_record["race_date_dt"]
        if pd.notna(latest_date) and pd.notna(peak_date):
            days_since_peak = int((latest_date - peak_date).days)

        rows.append(
            {
                "horse": safe_text(latest_record["horse"]),
                "horse_key": horse_key,
                "career_starts": starts,
                "career_wins": wins,
                "career_places": places,
                "peak_rating": render_metric(peak_rating, 1),
                "average_rating": render_metric(average_rating_value, 1),
                "median_rating": render_metric(median_rating_value, 1),
                "latest_rating": render_metric(latest_rating, 1),
                "best_track": pick_group_label(ordered, "track_bucket", "best"),
                "best_distance": pick_group_label(ordered, "distance_bucket", "best"),
                "best_condition": pick_group_label(ordered, "condition_bucket", "best"),
                "best_class": pick_group_label(ordered, "class_bucket", "best"),
                "worst_track": pick_group_label(ordered, "track_bucket", "worst"),
                "worst_distance": pick_group_label(ordered, "distance_bucket", "worst"),
                "worst_condition": pick_group_label(ordered, "condition_bucket", "worst"),
                "peak_date": safe_text(peak_record["race_date"]),
                "peak_track": safe_text(peak_record["track"]),
                "peak_distance": safe_text(peak_record["distance"]),
                "peak_class": safe_text(peak_record["class_name"]),
                "career_trend": trend,
                "rating_slope": render_metric(slope, 3),
                "improving_flag": improving_flag,
                "regressing_flag": regressing_flag,
                "days_since_peak": "" if days_since_peak is None else str(days_since_peak),
                "top_3_ratings": "|".join(render_metric(value, 1) for value in top_three),
                "last_5_average": render_metric(last_five_avg, 1),
                "last_10_average": render_metric(last_ten_avg, 1),
                "career_rating_percentile": "",
                "consistency_score": render_metric(consistency_score, 0),
                "volatility_score": render_metric(volatility_score, 0),
                "rating_band": "",
                "built_at": built_at,
            }
        )

    career_df = pd.DataFrame(rows)
    if career_df.empty:
        raise ValueError("No horse career intelligence rows were built.")

    average_series = pd.to_numeric(career_df["average_rating"], errors="coerce")
    percentile_series = (average_series.rank(method="average", pct=True).fillna(0.0) * 100.0).round(1)
    career_df["career_rating_percentile"] = percentile_series.map(lambda value: render_metric(value, 1))
    career_df["rating_band"] = percentile_series.apply(percentile_band)

    summary = pd.DataFrame(
        [
            {
                "status": "PASS",
                "input_rows": len(input_records),
                "output_rows": len(career_df),
                "unique_horses": career_df["horse_key"].nunique(),
                "missing_peak": int((career_df["peak_rating"] == "").sum()),
                "missing_latest": int((career_df["latest_rating"] == "").sum()),
                "missing_average": int((career_df["average_rating"] == "").sum()),
                "avg_consistency_score": render_metric(pd.to_numeric(career_df["consistency_score"], errors="coerce").mean(), 1),
                "avg_volatility_score": render_metric(pd.to_numeric(career_df["volatility_score"], errors="coerce").mean(), 1),
                "band_counts": "; ".join(
                    f"{band}:{count}" for band, count in career_df["rating_band"].value_counts().sort_index().items()
                ),
                "trend_counts": "; ".join(
                    f"{trend}:{count}" for trend, count in career_df["career_trend"].value_counts().sort_index().items()
                ),
                "built_at": built_at,
            }
        ]
    )
    return career_df, summary


def main() -> None:
    career_df, summary = build_career_intelligence()
    career_df.to_csv(OUT_PATH, index=False)
    summary.to_csv(SUMMARY_PATH, index=False)

    print(f"[career-intel] rows={len(career_df)} unique_horses={career_df['horse_key'].nunique()}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
