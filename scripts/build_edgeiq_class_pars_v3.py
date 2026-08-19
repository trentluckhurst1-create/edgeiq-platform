from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA = PROJECT_ROOT / "public" / "data"

INPUT = DATA / "edgeiq_historical_performance_rating_v3.csv"
OUT = DATA / "edgeiq_class_pars_v3.csv"
AUDIT_OUT = DATA / "edgeiq_class_pars_v3_audit.csv"

CLASS_CHECKS = ["BM58", "BM64", "BM70", "BM78", "BM84", "LISTED", "GROUP 1", "GROUP 2", "GROUP 3"]

OUTPUT_FIELDS = [
    "race_class_clean",
    "class_family",
    "benchmark_number",
    "race_grade",
    "run_count",
    "winner_count",
    "top3_count",
    "winner_avg",
    "winner_median",
    "top3_avg",
    "top3_median",
    "all_runs_avg",
    "all_runs_median",
    "par_rating",
    "par_method",
    "confidence",
    "recovery_confidence_used",
    "low_confidence_excluded",
    "notes",
]

AUDIT_FIELDS = [
    "section",
    "race_class_clean",
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
    text = clean(value).replace(",", "")
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


def class_family(value: str) -> str:
    text = upper(value)
    if not text or text == "UNKNOWN":
        return "UNKNOWN"
    if re.match(r"^BM\d{2,3}$", text):
        return "BENCHMARK"
    if re.match(r"^\d+\s*-\s*\d+$", text):
        return "BENCHMARK_RANGE"
    if text.startswith("GROUP"):
        return "GROUP"
    if text == "LISTED":
        return "LISTED"
    if text == "MAIDEN":
        return "MAIDEN"
    if text == "HANDICAP":
        return "HANDICAP"
    if text.startswith("CLASS "):
        return "CLASS"
    if re.match(r"^(GOOD|SOFT|HEAVY|FAST|FIRM)\d?$", text):
        return "CONDITION_LEAK"
    return "OTHER"


def benchmark_number(value: str) -> str:
    match = re.search(r"\bBM(\d{2,3})\b", upper(value))
    return match.group(1) if match else ""


def race_grade(value: str) -> str:
    text = upper(value)
    if text.startswith("GROUP 1"):
        return "GROUP 1"
    if text.startswith("GROUP 2"):
        return "GROUP 2"
    if text.startswith("GROUP 3"):
        return "GROUP 3"
    if text == "LISTED":
        return "LISTED"
    if re.match(r"^BM\d{2,3}$", text):
        return "BENCHMARK"
    return class_family(text)


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


def audit_row(section: str, race_class_clean: str, metric: str, value: object = "", count: object = "", avg_rating: object = "", notes: object = "") -> dict[str, object]:
    return {
        "section": section,
        "race_class_clean": race_class_clean,
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
    rows_excluded_low_confidence = 0
    rows_excluded_missing_class = 0
    rows_excluded_invalid_rating = 0
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)

    with INPUT.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows_loaded += 1
            if upper(row.get("recovery_confidence")) == "LOW":
                rows_excluded_low_confidence += 1
                continue

            klass = upper(row.get("race_class_clean")) or "UNKNOWN"
            if not klass:
                rows_excluded_missing_class += 1
                continue

            rating = as_float(row.get("performance_rating_v3"))
            finish = as_int(row.get("finish_position"))
            if rating is None or finish is None:
                rows_excluded_invalid_rating += 1
                continue

            groups[klass].append({"rating": rating, "finish": finish})
            rows_used += 1

    output_rows: list[dict[str, object]] = []
    audit_rows: list[dict[str, object]] = [
        audit_row("summary", "ALL", "rows_loaded", rows_loaded),
        audit_row("summary", "ALL", "rows_used", rows_used),
        audit_row("summary", "ALL", "rows_excluded_low_confidence", rows_excluded_low_confidence),
        audit_row("summary", "ALL", "rows_excluded_missing_class", rows_excluded_missing_class),
        audit_row("summary", "ALL", "rows_excluded_invalid_rating", rows_excluded_invalid_rating),
    ]

    for klass, items in sorted(groups.items()):
        all_values = [float(item["rating"]) for item in items]
        winner_values = [float(item["rating"]) for item in items if int(item["finish"]) == 1]
        top3_values = [float(item["rating"]) for item in items if int(item["finish"]) <= 3]
        par_rating, par_method, confidence = par_for(winner_values, top3_values, all_values)

        row = {
            "race_class_clean": klass,
            "class_family": class_family(klass),
            "benchmark_number": benchmark_number(klass),
            "race_grade": race_grade(klass),
            "run_count": len(all_values),
            "winner_count": len(winner_values),
            "top3_count": len(top3_values),
            "winner_avg": fmt(avg(winner_values)),
            "winner_median": fmt(median(winner_values)),
            "top3_avg": fmt(avg(top3_values)),
            "top3_median": fmt(median(top3_values)),
            "all_runs_avg": fmt(avg(all_values)),
            "all_runs_median": fmt(median(all_values)),
            "par_rating": fmt(par_rating),
            "par_method": par_method,
            "confidence": confidence,
            "recovery_confidence_used": "HIGH | MEDIUM",
            "low_confidence_excluded": rows_excluded_low_confidence,
            "notes": "Observed from performance_rating_v3 only; class not used in V3 rating formula.",
        }
        output_rows.append(row)

        if klass in CLASS_CHECKS:
            audit_rows.append(
                audit_row(
                    "required_class_check",
                    klass,
                    "par_rating",
                    row["par_rating"],
                    row["run_count"],
                    row["all_runs_avg"],
                    f"winner_count={row['winner_count']} | top3_count={row['top3_count']} | method={par_method} | confidence={confidence}",
                )
            )

    observed_required = {row["race_class_clean"] for row in output_rows if row["race_class_clean"] in CLASS_CHECKS}
    for klass in CLASS_CHECKS:
        if klass not in observed_required:
            audit_rows.append(audit_row("required_class_check", klass, "missing_required_class", "", 0, "", "No rows observed in V3 input."))

    output_rows.sort(key=lambda row: (float(row["par_rating"]) if row["par_rating"] else -999.0, row["race_class_clean"]))
    write_csv(OUT, output_rows, OUTPUT_FIELDS)
    write_csv(AUDIT_OUT, audit_rows, AUDIT_FIELDS)

    print("=" * 100)
    print("EDGEIQ CLASS PARS V3")
    print("=" * 100)
    print(f"rows_loaded={rows_loaded}")
    print(f"rows_used={rows_used}")
    print(f"rows_excluded_low_confidence={rows_excluded_low_confidence}")
    print(f"class_rows={len(output_rows)}")
    print()
    print("REQUIRED CLASS CHECK")
    for row in output_rows:
        if row["race_class_clean"] in CLASS_CHECKS:
            print(
                f"{row['race_class_clean']}: par={row['par_rating']} "
                f"runs={row['run_count']} winners={row['winner_count']} top3={row['top3_count']} "
                f"method={row['par_method']} confidence={row['confidence']}"
            )
    print()
    print("SAVED:")
    print(OUT)
    print(AUDIT_OUT)


if __name__ == "__main__":
    main()
