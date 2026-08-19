from __future__ import annotations

import csv
import hashlib
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA = PROJECT_ROOT / "public" / "data"

RUNS_INPUT = DATA / "edgeiq_historical_performance_rating_v3.csv"
CLASS_PARS_INPUT = DATA / "edgeiq_class_pars_v3.csv"
DISTANCE_PARS_INPUT = DATA / "edgeiq_distance_pars_v3.csv"
CONDITION_PARS_INPUT = DATA / "edgeiq_condition_pars_v3.csv"

OUT = DATA / "edgeiq_race_rating_targets_v3.csv"
AUDIT_OUT = DATA / "edgeiq_race_rating_targets_v3_audit.csv"

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
    "race_context_key",
    "race_date",
    "track",
    "distance",
    "distance_band",
    "race_class_clean",
    "class_family",
    "condition_recovered",
    "condition_normalised",
    "source_file",
    "source_race_key",
    "field_size",
    "runner_count",
    "winner_count",
    "target_rating_v3",
    "target_method",
    "target_confidence",
    "class_par_rating",
    "distance_par_rating",
    "condition_par_rating",
    "class_confidence",
    "distance_confidence",
    "condition_confidence",
    "winner_rating",
    "winner_gap_to_target",
    "duplicate_context_risk",
    "notes",
]

AUDIT_FIELDS = [
    "section",
    "metric",
    "value",
    "count",
    "avg_target_rating",
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


def fmt(value: float | None) -> str:
    return "" if value is None else f"{value:.2f}"


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


def first_existing(row: dict[str, str], fields: list[str]) -> str:
    for field in fields:
        value = clean(row.get(field))
        if value:
            return value
    return ""


def context_hash(parts: list[str]) -> str:
    joined = "|".join(parts)
    return hashlib.sha1(joined.encode("utf-8", errors="replace")).hexdigest()[:16]


def confidence_rank(confidence: str) -> int:
    return {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(upper(confidence), 0)


def aggregate_confidence(
    race_class_clean: str,
    class_family: str,
    class_confidence: str,
    distance_confidence: str,
    condition_confidence: str,
    condition_normalised: str,
    duplicate_context_risk: bool,
    missing_components: list[str],
) -> str:
    if missing_components:
        return "NO_TARGET"
    if race_class_clean == "UNKNOWN" or class_family in {"UNKNOWN", "CONDITION_LEAK"}:
        return "LOW"
    if duplicate_context_risk or condition_normalised == "UNKNOWN":
        return "LOW"
    scores = [confidence_rank(class_confidence), confidence_rank(distance_confidence), confidence_rank(condition_confidence)]
    if min(scores) <= 1:
        return "LOW"
    if min(scores) == 2:
        return "MEDIUM"
    return "HIGH"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def audit_row(section: str, metric: str, value: object = "", count: object = "", avg_target_rating: object = "", notes: object = "") -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "count": count,
        "avg_target_rating": avg_target_rating,
        "notes": notes,
    }


def load_class_pars() -> dict[str, dict[str, str]]:
    rows = read_csv(CLASS_PARS_INPUT)
    return {upper(row.get("race_class_clean")): row for row in rows if upper(row.get("race_class_clean"))}


def load_distance_pars() -> dict[str, dict[str, str]]:
    rows = read_csv(DISTANCE_PARS_INPUT)
    return {clean(row.get("distance_band")): row for row in rows if clean(row.get("distance_band"))}


def load_condition_pars() -> dict[str, dict[str, str]]:
    rows = read_csv(CONDITION_PARS_INPUT)
    return {upper(row.get("condition")): row for row in rows if upper(row.get("condition"))}


def main() -> None:
    class_pars = load_class_pars()
    distance_pars = load_distance_pars()
    condition_pars = load_condition_pars()

    rows_loaded = 0
    rows_used = 0
    rows_excluded_confidence = 0
    contexts: dict[str, dict[str, object]] = {}

    with RUNS_INPUT.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows_loaded += 1
            if upper(row.get("recovery_confidence")) not in {"HIGH", "MEDIUM"}:
                rows_excluded_confidence += 1
                continue

            race_date = clean(row.get("race_date"))
            track = upper(row.get("track"))
            distance = as_int(row.get("distance"))
            distance_text = "" if distance is None else str(distance)
            race_class_clean = upper(row.get("race_class_clean")) or "UNKNOWN"
            condition_recovered = clean(row.get("condition_recovered")) or clean(row.get("track_condition"))
            condition_normalised = normalise_condition(condition_recovered)
            source_file = clean(row.get("source_file"))
            source_race_key = first_existing(row, ["source_race_key", "race_key", "race_id", "source_url", "official_result_url", "race_name", "race_entry", "source_race_no", "race_no"])
            field_size = as_int(row.get("real_field_size"))
            field_size_text = "" if field_size is None else str(field_size)

            key_parts = [
                race_date,
                track,
                distance_text,
                race_class_clean,
                condition_recovered,
                condition_normalised,
                source_file,
                source_race_key,
                field_size_text,
            ]
            key = context_hash(key_parts)
            if key not in contexts:
                contexts[key] = {
                    "race_context_key": key,
                    "race_date": race_date,
                    "track": track,
                    "distance": distance_text,
                    "distance_band": distance_band(distance),
                    "race_class_clean": race_class_clean,
                    "condition_recovered": condition_recovered,
                    "condition_normalised": condition_normalised,
                    "source_file": source_file,
                    "source_race_key": source_race_key,
                    "field_size": field_size_text,
                    "runner_count": 0,
                    "winner_ratings": [],
                }

            contexts[key]["runner_count"] = int(contexts[key]["runner_count"]) + 1
            finish_position = as_int(row.get("finish_position"))
            performance_rating = as_float(row.get("performance_rating_v3"))
            if finish_position == 1 and performance_rating is not None:
                contexts[key]["winner_ratings"].append(performance_rating)
            rows_used += 1

    output_rows: list[dict[str, object]] = []
    missing_class_count = 0
    missing_distance_count = 0
    missing_condition_count = 0
    duplicate_context_count = 0

    for context in contexts.values():
        class_row = class_pars.get(str(context["race_class_clean"]))
        distance_row = distance_pars.get(str(context["distance_band"]))
        condition_row = condition_pars.get(str(context["condition_normalised"]))

        class_par = as_float(class_row.get("par_rating") if class_row else "")
        distance_par = as_float(distance_row.get("distance_par_rating") if distance_row else "")
        condition_par = as_float(condition_row.get("condition_par_rating") if condition_row else "")
        class_confidence = upper(class_row.get("confidence") if class_row else "")
        distance_confidence = upper(distance_row.get("confidence") if distance_row else "")
        condition_confidence = upper(condition_row.get("confidence") if condition_row else "")
        class_family = upper(class_row.get("class_family") if class_row else "")

        missing_components: list[str] = []
        if class_par is None:
            missing_class_count += 1
            missing_components.append("CLASS_PAR")
        if distance_par is None:
            missing_distance_count += 1
            missing_components.append("DISTANCE_PAR")
        if condition_par is None:
            missing_condition_count += 1
            missing_components.append("CONDITION_PAR")

        winner_ratings = list(context["winner_ratings"])
        winner_count = len(winner_ratings)
        duplicate_context_risk = winner_count > 1
        if duplicate_context_risk:
            duplicate_context_count += 1

        target_rating = None
        target_method = "MISSING_PAR_COMPONENT"
        if not missing_components:
            target_rating = (0.70 * class_par) + (0.15 * distance_par) + (0.15 * condition_par)
            target_method = "CLASS_70_DISTANCE_15_CONDITION_15_V3"

        target_confidence = aggregate_confidence(
            str(context["race_class_clean"]),
            class_family,
            class_confidence,
            distance_confidence,
            condition_confidence,
            str(context["condition_normalised"]),
            duplicate_context_risk,
            missing_components,
        )

        winner_rating = median(winner_ratings)
        winner_gap_to_target = None
        if winner_rating is not None and target_rating is not None:
            winner_gap_to_target = winner_rating - target_rating

        notes: list[str] = []
        if missing_components:
            notes.append("MISSING_COMPONENTS=" + "|".join(missing_components))
        if duplicate_context_risk:
            notes.append("MULTI_WINNER_AVAILABLE_CONTEXT")
        if not context["source_race_key"]:
            notes.append("NO_SOURCE_RACE_KEY_IN_V3")
        if context["race_class_clean"] == "UNKNOWN":
            notes.append("UNKNOWN_CLASS_CONTEXT")
        if class_family == "CONDITION_LEAK":
            notes.append("CLASS_FIELD_CONDITION_LEAK")
        if context["condition_normalised"] == "UNKNOWN":
            notes.append("UNKNOWN_CONDITION")
        if class_confidence == "LOW":
            notes.append("LOW_CLASS_PAR_CONFIDENCE")
        if distance_confidence == "LOW":
            notes.append("LOW_DISTANCE_PAR_CONFIDENCE")
        if condition_confidence == "LOW":
            notes.append("LOW_CONDITION_PAR_CONFIDENCE")

        output_rows.append(
            {
                "race_context_key": context["race_context_key"],
                "race_date": context["race_date"],
                "track": context["track"],
                "distance": context["distance"],
                "distance_band": context["distance_band"],
                "race_class_clean": context["race_class_clean"],
                "class_family": class_family,
                "condition_recovered": context["condition_recovered"],
                "condition_normalised": context["condition_normalised"],
                "source_file": context["source_file"],
                "source_race_key": context["source_race_key"],
                "field_size": context["field_size"],
                "runner_count": context["runner_count"],
                "winner_count": winner_count,
                "target_rating_v3": fmt(target_rating),
                "target_method": target_method,
                "target_confidence": target_confidence,
                "class_par_rating": fmt(class_par),
                "distance_par_rating": fmt(distance_par),
                "condition_par_rating": fmt(condition_par),
                "class_confidence": class_confidence,
                "distance_confidence": distance_confidence,
                "condition_confidence": condition_confidence,
                "winner_rating": fmt(winner_rating),
                "winner_gap_to_target": fmt(winner_gap_to_target),
                "duplicate_context_risk": "YES" if duplicate_context_risk else "NO",
                "notes": " | ".join(notes) if notes else "Target blended from class/distance/condition pars only.",
            }
        )

    output_rows.sort(key=lambda row: (str(row["race_date"]), str(row["track"]), as_int(row["distance"]) or 0, str(row["race_class_clean"]), str(row["race_context_key"])))

    target_values = [as_float(row["target_rating_v3"]) for row in output_rows if as_float(row["target_rating_v3"]) is not None]
    target_values_float = [float(value) for value in target_values if value is not None]
    confidence_counts = Counter(str(row["target_confidence"]) for row in output_rows)
    class_targets: dict[str, list[float]] = defaultdict(list)
    class_counts: Counter[str] = Counter()
    for row in output_rows:
        klass = str(row["race_class_clean"])
        class_counts[klass] += 1
        target = as_float(row["target_rating_v3"])
        if target is not None:
            class_targets[klass].append(target)

    audit_rows: list[dict[str, object]] = [
        audit_row("summary", "rows_loaded", rows_loaded),
        audit_row("summary", "rows_used", rows_used),
        audit_row("summary", "rows_excluded_confidence_not_high_or_medium", rows_excluded_confidence),
        audit_row("summary", "race_target_rows_written", len(output_rows)),
        audit_row("summary", "missing_class_par_count", missing_class_count),
        audit_row("summary", "missing_distance_par_count", missing_distance_count),
        audit_row("summary", "missing_condition_par_count", missing_condition_count),
        audit_row("summary", "duplicate_context_risk_count", duplicate_context_count),
        audit_row("target_rating_distribution", "minimum", fmt(min(target_values_float) if target_values_float else None)),
        audit_row("target_rating_distribution", "maximum", fmt(max(target_values_float) if target_values_float else None)),
        audit_row("target_rating_distribution", "average", fmt(avg(target_values_float))),
    ]

    for confidence, count in sorted(confidence_counts.items()):
        audit_rows.append(audit_row("confidence_distribution", confidence, count, count))

    for klass, count in class_counts.most_common(40):
        targets = class_targets.get(klass, [])
        audit_rows.append(
            audit_row(
                "sample_targets_by_class",
                klass,
                fmt(avg(targets)),
                count,
                fmt(avg(targets)),
                f"target_rows={count} | target_count={len(targets)}",
            )
        )

    write_csv(OUT, output_rows, OUTPUT_FIELDS)
    write_csv(AUDIT_OUT, audit_rows, AUDIT_FIELDS)

    print("=" * 100)
    print("EDGEIQ RACE RATING TARGETS V3")
    print("=" * 100)
    print(f"rows_loaded={rows_loaded}")
    print(f"rows_used={rows_used}")
    print(f"race_target_rows_written={len(output_rows)}")
    print(f"missing_class_par_count={missing_class_count}")
    print(f"missing_distance_par_count={missing_distance_count}")
    print(f"missing_condition_par_count={missing_condition_count}")
    print(f"duplicate_context_risk_count={duplicate_context_count}")
    print(f"target_min={fmt(min(target_values_float) if target_values_float else None)}")
    print(f"target_max={fmt(max(target_values_float) if target_values_float else None)}")
    print(f"target_avg={fmt(avg(target_values_float))}")
    print()
    print("CONFIDENCE")
    for confidence, count in sorted(confidence_counts.items()):
        print(f"{confidence}: {count}")
    print()
    print("SAVED:")
    print(OUT)
    print(AUDIT_OUT)


if __name__ == "__main__":
    main()
