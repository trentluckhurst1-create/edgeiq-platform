from __future__ import annotations

import csv
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA = PROJECT_ROOT / "public" / "data"

HISTORICAL_RATINGS_INPUT = DATA / "edgeiq_historical_performance_rating_v3.csv"
RACE_TARGETS_INPUT = DATA / "edgeiq_race_rating_targets_v3.csv"

CURRENT_RUNNER_CANDIDATES = [
    DATA / "edgeiq_vic_live_terminal_feed_v1.csv",
    DATA / "edgeiq_live_runner_board_v1.csv",
    DATA / "edgeiq_vic_three_day_race_fields.csv",
    DATA / "race_fields.csv",
    DATA / "race_card_report.csv",
]

OUT = DATA / "edgeiq_runner_projection_v3.csv"
AUDIT_OUT = DATA / "edgeiq_runner_projection_v3_audit.csv"

DISTANCE_BANDS = [
    ("800-999", 800, 999),
    ("1000-1199", 1000, 1199),
    ("1200-1399", 1200, 1399),
    ("1400-1599", 1400, 1599),
    ("1600-1799", 1600, 1799),
    ("1800-1999", 1800, 1999),
    ("2000-2199", 2000, 2199),
    ("2200-2399", 2200, 2399),
    ("2400-2799", 2400, 2799),
    ("2800+", 2800, None),
]

OUTPUT_FIELDS = [
    "projection_source",
    "race_date",
    "day_bucket",
    "track",
    "race_no",
    "race_time",
    "horse_no",
    "saddlecloth",
    "horse",
    "horse_key",
    "is_scratched",
    "distance",
    "distance_band",
    "race_class_clean",
    "condition_normalised",
    "field_size",
    "last_rating_v3",
    "avg_last_3_v3",
    "avg_last_5_v3",
    "peak_last_6_v3",
    "starts_found",
    "days_since_last_run",
    "distance_profile_rating",
    "distance_profile_starts",
    "condition_profile_rating",
    "condition_profile_starts",
    "projected_rating_v3",
    "projection_confidence",
    "projection_reason",
    "target_rating_v3",
    "target_confidence",
    "rating_gap_v3",
    "gap_band",
    "target_join_method",
    "target_sample_size",
]

AUDIT_FIELDS = [
    "section",
    "metric",
    "value",
    "count",
    "notes",
]


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null", "na", "n/a"} else text


def upper(value: object) -> str:
    return clean(value).upper()


def as_float(value: object) -> float | None:
    text = clean(value).replace(",", "").replace("m", "").replace("M", "")
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def as_int(value: object) -> int | None:
    number = as_float(value)
    if number is None:
        return None
    return int(round(number))


def fmt(value: float | None) -> str:
    return "" if value is None else f"{value:.2f}"


def fmt_int(value: int | None) -> str:
    return "" if value is None else str(value)


def avg(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def parse_date(value: object) -> date | None:
    text = clean(value)
    if not text:
        return None
    for fmt_string in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt_string).date()
        except ValueError:
            continue
    return None


def normalise_horse(value: object) -> str:
    text = clean(value)
    text = re.sub(r"\([^)]*\)", "", text)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def normalise_track(value: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", upper(value))


def normalise_condition(value: object) -> str:
    text = upper(value)
    compact = re.sub(r"[^A-Z0-9]", "", text)
    if not compact:
        return "UNKNOWN"
    if compact.startswith("SYNTHETIC"):
        return "SYNTHETIC"
    if compact.startswith("FIRM"):
        return "FIRM"
    if compact.startswith("GOOD"):
        return "GOOD"
    if compact.startswith("SOFT"):
        return "SOFT"
    if compact.startswith("HEAVY"):
        return "HEAVY"
    return "UNKNOWN"


def distance_band(distance: int | None) -> str:
    if distance is None:
        return ""
    for label, minimum, maximum in DISTANCE_BANDS:
        if maximum is None and distance >= minimum:
            return label
        if maximum is not None and minimum <= distance <= maximum:
            return label
    return ""


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def audit_row(section: str, metric: str, value: object = "", count: object = "", notes: object = "") -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "count": count,
        "notes": notes,
    }


def row_has_columns(row: dict[str, str], columns: set[str]) -> bool:
    return columns.issubset(set(row.keys()))


def select_current_runner_source() -> tuple[Path, list[dict[str, object]]]:
    required = {"horse", "track", "race_no"}
    audit_rows: list[dict[str, object]] = []
    selected: Path | None = None

    for path in CURRENT_RUNNER_CANDIDATES:
        if not path.exists():
            audit_rows.append(audit_row("current_source_candidate", path.name, "MISSING", 0, "Candidate file not found."))
            continue

        rows = read_csv(path)
        headers = set(rows[0].keys()) if rows else set()
        today_rows = [row for row in rows if upper(row.get("day_bucket")) == "TODAY"]
        has_required = rows and row_has_columns(rows[0], required)
        audit_rows.append(
            audit_row(
                "current_source_candidate",
                path.name,
                "SELECTABLE" if has_required else "MISSING_REQUIRED_COLUMNS",
                len(today_rows) if today_rows else len(rows),
                f"rows={len(rows)} | today_rows={len(today_rows)} | required_columns={','.join(sorted(required))}",
            )
        )
        if selected is None and has_required:
            selected = path

    if selected is None:
        raise RuntimeError("No current runner source found with horse, track, and race_no columns.")

    return selected, audit_rows


def confidence_rank(value: str) -> int:
    return {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(upper(value), 0)


def cap_confidence(value: str, maximum: str) -> str:
    rank_to_conf = {3: "HIGH", 2: "MEDIUM", 1: "LOW", 0: "NO_TARGET"}
    return rank_to_conf[min(confidence_rank(value), confidence_rank(maximum))]


def target_group_confidence(rows: list[dict[str, str]], method: str, race_class_clean: str, condition_normalised: str) -> str:
    if not rows:
        return "NO_TARGET"
    confidences = [upper(row.get("target_confidence")) for row in rows if upper(row.get("target_confidence"))]
    if not confidences:
        return "LOW"
    if race_class_clean == "UNKNOWN" or condition_normalised == "UNKNOWN":
        return "LOW"
    if any(confidence == "NO_TARGET" for confidence in confidences):
        return "LOW"
    lowest = min(confidences, key=confidence_rank)
    if method == "EXACT_CONTEXT":
        return lowest
    if len(rows) < 5:
        return "LOW"
    if method in {"CLASS_DISTANCE_CONDITION_FIELD", "CLASS_DISTANCE_CONDITION"}:
        return cap_confidence(lowest, "MEDIUM")
    return "LOW"


class TargetJoiner:
    def __init__(self, rows: list[dict[str, str]]) -> None:
        self.indexes: dict[str, dict[str, list[dict[str, str]]]] = {
            "EXACT_CONTEXT": defaultdict(list),
            "CLASS_DISTANCE_CONDITION_FIELD": defaultdict(list),
            "CLASS_DISTANCE_CONDITION": defaultdict(list),
            "CLASS_DISTANCE": defaultdict(list),
            "CLASS_CONDITION": defaultdict(list),
            "CLASS_ONLY": defaultdict(list),
        }
        for row in rows:
            target = as_float(row.get("target_rating_v3"))
            if target is None:
                continue
            race_date = clean(row.get("race_date"))
            track = normalise_track(row.get("track"))
            distance = clean(row.get("distance"))
            distance_band_value = clean(row.get("distance_band"))
            klass = upper(row.get("race_class_clean")) or "UNKNOWN"
            condition = upper(row.get("condition_normalised")) or "UNKNOWN"
            field_size = clean(row.get("field_size"))

            keys = {
                "EXACT_CONTEXT": "|".join([race_date, track, distance, klass, condition, field_size]),
                "CLASS_DISTANCE_CONDITION_FIELD": "|".join([klass, distance, condition, field_size]),
                "CLASS_DISTANCE_CONDITION": "|".join([klass, distance_band_value, condition]),
                "CLASS_DISTANCE": "|".join([klass, distance_band_value]),
                "CLASS_CONDITION": "|".join([klass, condition]),
                "CLASS_ONLY": klass,
            }
            for method, key in keys.items():
                self.indexes[method][key].append(row)

    def join(self, current: dict[str, object]) -> dict[str, object]:
        race_date = clean(current.get("race_date"))
        track = normalise_track(current.get("track"))
        distance = clean(current.get("distance"))
        distance_band_value = clean(current.get("distance_band"))
        klass = upper(current.get("race_class_clean")) or "UNKNOWN"
        condition = upper(current.get("condition_normalised")) or "UNKNOWN"
        field_size = clean(current.get("field_size"))

        candidates = [
            ("EXACT_CONTEXT", "|".join([race_date, track, distance, klass, condition, field_size])),
            ("CLASS_DISTANCE_CONDITION_FIELD", "|".join([klass, distance, condition, field_size])),
            ("CLASS_DISTANCE_CONDITION", "|".join([klass, distance_band_value, condition])),
            ("CLASS_DISTANCE", "|".join([klass, distance_band_value])),
            ("CLASS_CONDITION", "|".join([klass, condition])),
            ("CLASS_ONLY", klass),
        ]

        for method, key in candidates:
            rows = self.indexes[method].get(key, [])
            if not rows:
                continue
            targets = [float(value) for value in (as_float(row.get("target_rating_v3")) for row in rows) if value is not None]
            if not targets:
                continue
            target = median(targets)
            return {
                "target_rating_v3": target,
                "target_confidence": target_group_confidence(rows, method, klass, condition),
                "target_join_method": method,
                "target_sample_size": len(targets),
            }

        return {
            "target_rating_v3": None,
            "target_confidence": "NO_TARGET",
            "target_join_method": "NO_TARGET",
            "target_sample_size": 0,
        }


def projection_for(ratings: list[float]) -> tuple[float | None, str, str]:
    starts = len(ratings)
    if starts == 0:
        return None, "NO_HISTORY", "NO_HISTORY"

    last = ratings[0]
    avg3 = avg(ratings[:3])
    avg5 = avg(ratings[:5])
    peak6 = max(ratings[:6])

    if starts >= 5 and avg3 is not None and avg5 is not None:
        projected = (0.35 * last) + (0.35 * avg3) + (0.20 * peak6) + (0.10 * avg5)
        return projected, "HIGH", "STARTS_GE_5 | 0.35_LAST + 0.35_AVG3 + 0.20_PEAK6 + 0.10_AVG5"
    if starts >= 3 and avg3 is not None:
        projected = (0.45 * last) + (0.40 * avg3) + (0.15 * peak6)
        return projected, "MEDIUM", "STARTS_3_TO_4 | 0.45_LAST + 0.40_AVG3 + 0.15_PEAK"

    projected = avg(ratings)
    confidence = "MEDIUM" if starts == 2 else "LOW"
    return projected, confidence, "STARTS_1_TO_2 | AVERAGE_AVAILABLE"


def gap_band(projected: float | None, target: float | None) -> str:
    if projected is None:
        return "NO_HISTORY"
    if target is None:
        return "NO_TARGET"
    gap = projected - target
    if gap >= 5:
        return "STRONG_ABOVE_TARGET"
    if gap >= 2:
        return "ABOVE_TARGET"
    if gap > -2:
        return "NEAR_TARGET"
    if gap >= -5:
        return "BELOW_TARGET"
    return "WELL_BELOW_TARGET"


def main() -> None:
    current_source, source_audit_rows = select_current_runner_source()
    current_rows_all = read_csv(current_source)
    current_rows = [row for row in current_rows_all if upper(row.get("day_bucket")) == "TODAY"] or current_rows_all

    race_field_sizes: Counter[tuple[str, str, str]] = Counter()
    for row in current_rows:
        race_key = (clean(row.get("race_date") or row.get("date")), normalise_track(row.get("track")), clean(row.get("race_no") or row.get("race_number")))
        race_field_sizes[race_key] += 1

    historical_rows_loaded = 0
    historical_rows_used = 0
    history_by_horse: dict[str, list[dict[str, object]]] = defaultdict(list)
    with HISTORICAL_RATINGS_INPUT.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            historical_rows_loaded += 1
            if upper(row.get("recovery_confidence")) not in {"HIGH", "MEDIUM"}:
                continue
            rating = as_float(row.get("performance_rating_v3"))
            if rating is None:
                continue
            horse_key = normalise_horse(row.get("horse"))
            if not horse_key:
                continue
            distance = as_int(row.get("distance"))
            run = {
                "horse": clean(row.get("horse")),
                "race_date": clean(row.get("race_date")),
                "race_date_dt": parse_date(row.get("race_date")),
                "track": clean(row.get("track")),
                "distance": distance,
                "distance_band": distance_band(distance),
                "condition": normalise_condition(row.get("condition_recovered") or row.get("track_condition")),
                "rating": rating,
            }
            history_by_horse[horse_key].append(run)
            historical_rows_used += 1

    for runs in history_by_horse.values():
        runs.sort(key=lambda item: item["race_date_dt"] or date.min, reverse=True)

    target_joiner = TargetJoiner(read_csv(RACE_TARGETS_INPUT))

    output_rows: list[dict[str, object]] = []
    no_history_examples: list[str] = []
    target_join_success = 0
    target_join_failed = 0

    for current in current_rows:
        race_date = clean(current.get("race_date") or current.get("date"))
        race_date_dt = parse_date(race_date)
        track = upper(current.get("track"))
        race_no = clean(current.get("race_no") or current.get("race_number"))
        distance = as_int(current.get("distance"))
        distance_text = fmt_int(distance)
        distance_band_value = distance_band(distance)
        race_class_clean = upper(current.get("race_class_clean") or current.get("race_class")) or "UNKNOWN"
        condition_normalised = normalise_condition(current.get("track_condition") or current.get("condition"))
        race_key = (race_date, normalise_track(track), race_no)
        field_size = race_field_sizes.get(race_key, 0)

        horse = clean(current.get("horse"))
        candidate_horse_keys = [
            normalise_horse(current.get("horse_key")),
            normalise_horse(horse),
        ]
        candidate_horse_keys = [key for key in candidate_horse_keys if key]

        history: list[dict[str, object]] = []
        seen_history_ids: set[tuple[str, str, str, float]] = set()
        for horse_key in candidate_horse_keys:
            for run in history_by_horse.get(horse_key, []):
                run_date = run["race_date_dt"]
                if race_date_dt is not None and run_date is not None and run_date >= race_date_dt:
                    continue
                identity = (str(run["race_date"]), str(run["track"]), str(run["distance"]), float(run["rating"]))
                if identity in seen_history_ids:
                    continue
                seen_history_ids.add(identity)
                history.append(run)
        history.sort(key=lambda item: item["race_date_dt"] or date.min, reverse=True)

        ratings = [float(run["rating"]) for run in history]
        projected, projection_confidence, projection_reason = projection_for(ratings)

        last_rating = ratings[0] if ratings else None
        avg_last_3 = avg(ratings[:3])
        avg_last_5 = avg(ratings[:5])
        peak_last_6 = max(ratings[:6]) if ratings else None

        last_run_date = history[0]["race_date_dt"] if history else None
        days_since_last_run = None
        if race_date_dt is not None and last_run_date is not None:
            days_since_last_run = (race_date_dt - last_run_date).days

        distance_profile_values = [float(run["rating"]) for run in history if run["distance_band"] == distance_band_value and distance_band_value]
        condition_profile_values = [float(run["rating"]) for run in history if run["condition"] == condition_normalised and condition_normalised]
        distance_profile_rating = median(distance_profile_values)
        condition_profile_rating = median(condition_profile_values)

        current_target_context = {
            "race_date": race_date,
            "track": track,
            "distance": distance_text,
            "distance_band": distance_band_value,
            "race_class_clean": race_class_clean,
            "condition_normalised": condition_normalised,
            "field_size": field_size,
        }
        target = target_joiner.join(current_target_context)
        target_rating = target["target_rating_v3"]
        target_confidence = str(target["target_confidence"])
        if target_rating is None:
            target_join_failed += 1
        else:
            target_join_success += 1

        rating_gap = None
        if projected is not None and target_rating is not None:
            rating_gap = projected - float(target_rating)

        if not history and len(no_history_examples) < 12:
            no_history_examples.append(horse)

        output_rows.append(
            {
                "projection_source": current_source.name,
                "race_date": race_date,
                "day_bucket": clean(current.get("day_bucket")),
                "track": track,
                "race_no": race_no,
                "race_time": clean(current.get("race_time")),
                "horse_no": clean(current.get("horse_no") or current.get("saddlecloth")),
                "saddlecloth": clean(current.get("saddlecloth") or current.get("horse_no")),
                "horse": horse,
                "horse_key": clean(current.get("horse_key")),
                "is_scratched": clean(current.get("is_scratched") or current.get("scratched")),
                "distance": distance_text,
                "distance_band": distance_band_value,
                "race_class_clean": race_class_clean,
                "condition_normalised": condition_normalised,
                "field_size": field_size,
                "last_rating_v3": fmt(last_rating),
                "avg_last_3_v3": fmt(avg_last_3),
                "avg_last_5_v3": fmt(avg_last_5),
                "peak_last_6_v3": fmt(peak_last_6),
                "starts_found": len(history),
                "days_since_last_run": fmt_int(days_since_last_run),
                "distance_profile_rating": fmt(distance_profile_rating),
                "distance_profile_starts": len(distance_profile_values),
                "condition_profile_rating": fmt(condition_profile_rating),
                "condition_profile_starts": len(condition_profile_values),
                "projected_rating_v3": fmt(projected),
                "projection_confidence": projection_confidence,
                "projection_reason": projection_reason,
                "target_rating_v3": fmt(target_rating if isinstance(target_rating, float) else None),
                "target_confidence": target_confidence,
                "rating_gap_v3": fmt(rating_gap),
                "gap_band": gap_band(projected, target_rating if isinstance(target_rating, float) else None),
                "target_join_method": target["target_join_method"],
                "target_sample_size": target["target_sample_size"],
            }
        )

    output_rows.sort(key=lambda row: (str(row["race_date"]), str(row["track"]), as_int(row["race_no"]) or 0, as_int(row["horse_no"]) or 999, str(row["horse"])))

    projection_confidence_counts = Counter(str(row["projection_confidence"]) for row in output_rows)
    target_confidence_counts = Counter(str(row["target_confidence"]) for row in output_rows)
    gap_band_counts = Counter(str(row["gap_band"]) for row in output_rows)
    target_join_method_counts = Counter(str(row["target_join_method"]) for row in output_rows)
    gap_values = [as_float(row["rating_gap_v3"]) for row in output_rows if as_float(row["rating_gap_v3"]) is not None]
    projected_count = sum(1 for row in output_rows if clean(row["projected_rating_v3"]))
    no_history_count = projection_confidence_counts.get("NO_HISTORY", 0)

    audit_rows: list[dict[str, object]] = []
    audit_rows.extend(source_audit_rows)
    audit_rows.extend(
        [
            audit_row("summary", "current_runner_source_selected", current_source.name),
            audit_row("summary", "current_runners_loaded", len(current_rows)),
            audit_row("summary", "historical_rows_loaded", historical_rows_loaded),
            audit_row("summary", "historical_rows_used", historical_rows_used),
            audit_row("summary", "runners_projected", projected_count),
            audit_row("summary", "runners_no_history", no_history_count, no_history_count, "Examples: " + "; ".join(no_history_examples)),
            audit_row("summary", "target_join_success", target_join_success),
            audit_row("summary", "target_join_failed", target_join_failed),
            audit_row("rating_gap_distribution", "minimum", fmt(min(gap_values) if gap_values else None)),
            audit_row("rating_gap_distribution", "maximum", fmt(max(gap_values) if gap_values else None)),
            audit_row("rating_gap_distribution", "average", fmt(avg([float(value) for value in gap_values if value is not None]))),
        ]
    )

    for name, count in sorted(projection_confidence_counts.items()):
        audit_rows.append(audit_row("projection_confidence_counts", name, count, count))
    for name, count in sorted(target_confidence_counts.items()):
        audit_rows.append(audit_row("target_confidence_counts", name, count, count))
    for name, count in sorted(gap_band_counts.items()):
        audit_rows.append(audit_row("gap_band_counts", name, count, count))
    for name, count in sorted(target_join_method_counts.items()):
        audit_rows.append(audit_row("target_join_method_counts", name, count, count))

    write_csv(OUT, output_rows, OUTPUT_FIELDS)
    write_csv(AUDIT_OUT, audit_rows, AUDIT_FIELDS)

    print("=" * 100)
    print("EDGEIQ RUNNER PROJECTION V3")
    print("=" * 100)
    print(f"current_runner_source_selected={current_source.name}")
    print(f"current_runners_loaded={len(current_rows)}")
    print(f"historical_rows_loaded={historical_rows_loaded}")
    print(f"historical_rows_used={historical_rows_used}")
    print(f"runners_projected={projected_count}")
    print(f"runners_no_history={no_history_count}")
    print(f"target_join_success={target_join_success}")
    print(f"target_join_failed={target_join_failed}")
    print()
    print("PROJECTION CONFIDENCE")
    for name, count in sorted(projection_confidence_counts.items()):
        print(f"{name}: {count}")
    print()
    print("TARGET CONFIDENCE")
    for name, count in sorted(target_confidence_counts.items()):
        print(f"{name}: {count}")
    print()
    print("GAP BANDS")
    for name, count in sorted(gap_band_counts.items()):
        print(f"{name}: {count}")
    print()
    print("SAVED:")
    print(OUT)
    print(AUDIT_OUT)


if __name__ == "__main__":
    main()
