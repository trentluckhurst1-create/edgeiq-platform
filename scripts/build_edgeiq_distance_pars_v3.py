from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA = PROJECT_ROOT / "public" / "data"

INPUT = DATA / "edgeiq_historical_performance_rating_v3.csv"
OUT = DATA / "edgeiq_distance_pars_v3.csv"
AUDIT_OUT = DATA / "edgeiq_distance_pars_v3_audit.csv"

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
    "distance_band",
    "distance_min",
    "distance_max",
    "run_count",
    "winner_count",
    "top3_count",
    "winner_avg",
    "winner_median",
    "top3_avg",
    "top3_median",
    "all_runs_avg",
    "all_runs_median",
    "distance_par_rating",
    "par_method",
    "confidence",
    "recovery_confidence_used",
    "suspicious_flag",
    "notes",
]

AUDIT_FIELDS = [
    "section",
    "distance_band",
    "metric",
    "value",
    "count",
    "avg_rating",
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


def distance_band(distance: int) -> tuple[str, int, int | None] | None:
    for label, minimum, maximum in DISTANCE_BANDS:
        if maximum is None and distance >= minimum:
            return label, minimum, maximum
        if maximum is not None and minimum <= distance <= maximum:
            return label, minimum, maximum
    return None


def confidence_for(method: str, run_count: int, winner_count: int, top3_count: int) -> str:
    if method == "WINNER_TOP3_BLEND":
        if winner_count >= 50 and top3_count >= 120 and run_count >= 250:
            return "HIGH"
        return "MEDIUM"
    if method == "TOP3_MEDIAN":
        return "MEDIUM" if top3_count >= 60 else "LOW"
    return "LOW"


def par_for(winner_values: list[float], top3_values: list[float], all_values: list[float]) -> tuple[float | None, str, str]:
    winner_count = len(winner_values)
    top3_count = len(top3_values)
    run_count = len(all_values)
    winner_med = median(winner_values)
    top3_med = median(top3_values)
    all_med = median(all_values)

    if winner_count >= 20 and winner_med is not None and top3_med is not None:
        par = (winner_med * 0.72) + (top3_med * 0.28)
        method = "WINNER_TOP3_BLEND"
    elif top3_count >= 30 and top3_med is not None:
        par = top3_med
        method = "TOP3_MEDIAN"
    else:
        par = all_med
        method = "ALL_RUNS_MEDIAN_LOW_SAMPLE"

    confidence = confidence_for(method, run_count, winner_count, top3_count)
    return (round(par, 2) if par is not None else None), method, confidence


def suspicious_notes(run_count: int, winner_count: int, top3_count: int, par_rating: float | None) -> list[str]:
    notes: list[str] = []
    if run_count < 250:
        notes.append("LOW_RUN_SAMPLE")
    if winner_count < 20:
        notes.append("LOW_WINNER_SAMPLE")
    if top3_count < 30:
        notes.append("LOW_TOP3_SAMPLE")
    if par_rating is not None and par_rating < 85:
        notes.append("LOW_PAR_CHECK")
    if par_rating is not None and par_rating > 98:
        notes.append("HIGH_PAR_CHECK")
    return notes


def audit_row(section: str, distance_band_value: str, metric: str, value: object = "", count: object = "", avg_rating: object = "", notes: object = "") -> dict[str, object]:
    return {
        "section": section,
        "distance_band": distance_band_value,
        "metric": metric,
        "value": value,
        "count": count,
        "avg_rating": avg_rating,
        "notes": notes,
    }


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows_loaded = 0
    rows_used = 0
    rows_excluded_confidence = 0
    rows_excluded_invalid_distance = 0
    rows_excluded_out_of_scope_distance = 0
    rows_excluded_invalid_rating_or_finish = 0
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    band_bounds = {label: (minimum, maximum) for label, minimum, maximum in DISTANCE_BANDS}

    with INPUT.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows_loaded += 1

            if upper(row.get("recovery_confidence")) not in {"HIGH", "MEDIUM"}:
                rows_excluded_confidence += 1
                continue

            distance = as_int(row.get("distance"))
            if distance is None or distance <= 0:
                rows_excluded_invalid_distance += 1
                continue

            band = distance_band(distance)
            if band is None:
                rows_excluded_out_of_scope_distance += 1
                continue

            rating = as_float(row.get("performance_rating_v3"))
            finish = as_int(row.get("finish_position"))
            if rating is None or finish is None or finish <= 0:
                rows_excluded_invalid_rating_or_finish += 1
                continue

            groups[band[0]].append({"rating": rating, "finish": finish, "distance": distance})
            rows_used += 1

    output_rows: list[dict[str, object]] = []
    audit_rows: list[dict[str, object]] = [
        audit_row("summary", "ALL", "rows_loaded", rows_loaded),
        audit_row("summary", "ALL", "rows_used", rows_used),
        audit_row("summary", "ALL", "rows_excluded_confidence_not_high_or_medium", rows_excluded_confidence),
        audit_row("summary", "ALL", "rows_excluded_invalid_distance", rows_excluded_invalid_distance),
        audit_row("summary", "ALL", "rows_excluded_out_of_scope_distance", rows_excluded_out_of_scope_distance),
        audit_row("summary", "ALL", "rows_excluded_invalid_rating_or_finish", rows_excluded_invalid_rating_or_finish),
    ]

    for label, minimum, maximum in DISTANCE_BANDS:
        items = groups.get(label, [])
        all_values = [float(item["rating"]) for item in items]
        winner_values = [float(item["rating"]) for item in items if int(item["finish"]) == 1]
        top3_values = [float(item["rating"]) for item in items if int(item["finish"]) <= 3]
        par_rating, par_method, confidence = par_for(winner_values, top3_values, all_values)
        notes = suspicious_notes(len(all_values), len(winner_values), len(top3_values), par_rating)

        output_row = {
            "distance_band": label,
            "distance_min": minimum,
            "distance_max": "" if maximum is None else maximum,
            "run_count": len(all_values),
            "winner_count": len(winner_values),
            "top3_count": len(top3_values),
            "winner_avg": fmt(avg(winner_values)),
            "winner_median": fmt(median(winner_values)),
            "top3_avg": fmt(avg(top3_values)),
            "top3_median": fmt(median(top3_values)),
            "all_runs_avg": fmt(avg(all_values)),
            "all_runs_median": fmt(median(all_values)),
            "distance_par_rating": fmt(par_rating),
            "par_method": par_method,
            "confidence": confidence,
            "recovery_confidence_used": "HIGH | MEDIUM",
            "suspicious_flag": "YES" if notes else "NO",
            "notes": " | ".join(notes) if notes else "Observed from performance_rating_v3 only; distance used only for banding.",
        }
        output_rows.append(output_row)

        audit_rows.append(
            audit_row(
                "distribution_by_distance_band",
                label,
                "run_count",
                len(all_values),
                len(all_values),
                fmt(avg(all_values)),
                f"distance_min={minimum} | distance_max={maximum or ''}",
            )
        )
        audit_rows.append(
            audit_row(
                "par_rating_by_distance_band",
                label,
                "distance_par_rating",
                output_row["distance_par_rating"],
                len(all_values),
                output_row["all_runs_avg"],
                f"method={par_method} | confidence={confidence}",
            )
        )
        audit_rows.append(
            audit_row(
                "sample_counts",
                label,
                "winner_top3_counts",
                f"winners={len(winner_values)} | top3={len(top3_values)}",
                len(all_values),
                output_row["all_runs_avg"],
                f"winner_median={output_row['winner_median']} | top3_median={output_row['top3_median']}",
            )
        )
        if notes:
            audit_rows.append(
                audit_row(
                    "suspicious_band",
                    label,
                    "suspicious_checks",
                    "YES",
                    len(all_values),
                    output_row["distance_par_rating"],
                    " | ".join(notes),
                )
            )

    for label in sorted(set(groups) - set(band_bounds)):
        audit_rows.append(audit_row("unexpected_band", label, "unexpected_group", "", len(groups[label]), "", "Band was not in configured distance bands."))

    write_csv(OUT, output_rows, OUTPUT_FIELDS)
    write_csv(AUDIT_OUT, audit_rows, AUDIT_FIELDS)

    print("=" * 100)
    print("EDGEIQ DISTANCE PARS V3")
    print("=" * 100)
    print(f"rows_loaded={rows_loaded}")
    print(f"rows_used={rows_used}")
    print(f"rows_excluded_confidence_not_high_or_medium={rows_excluded_confidence}")
    print(f"rows_excluded_invalid_distance={rows_excluded_invalid_distance}")
    print(f"rows_excluded_out_of_scope_distance={rows_excluded_out_of_scope_distance}")
    print(f"rows_excluded_invalid_rating_or_finish={rows_excluded_invalid_rating_or_finish}")
    print(f"distance_band_rows={len(output_rows)}")
    print()
    print("DISTANCE PAR CHECK")
    for row in output_rows:
        print(
            f"{row['distance_band']}: par={row['distance_par_rating']} "
            f"runs={row['run_count']} winners={row['winner_count']} top3={row['top3_count']} "
            f"method={row['par_method']} confidence={row['confidence']} suspicious={row['suspicious_flag']}"
        )
    print()
    print("SAVED:")
    print(OUT)
    print(AUDIT_OUT)


if __name__ == "__main__":
    main()
