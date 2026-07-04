from __future__ import annotations

from edgeiq_results_common_v1 import DATA, SPEED_RAW_FIELDS, has_value, key_for, numeric_float, read_csv, write_csv
from build_edgeiq_standard_times_v1 import class_band, condition_band, parse_seconds


MASTER = DATA / "edgeiq_results_master_v1.csv"
STANDARDS = DATA / "edgeiq_standard_times_v1.csv"
OUT = DATA / "edgeiq_standardised_sectionals_v1.csv"
SUMMARY = DATA / "edgeiq_standardised_sectionals_summary_v1.csv"
EXAMPLES = DATA / "edgeiq_standardised_sectionals_examples_v1.csv"

SECONDS_PER_LENGTH = 0.17

FIELDS = [
    "benchmark_mode",
    "race_date",
    "track",
    "race_no",
    "runner",
    "position",
    "distance",
    "class",
    "class_band",
    "condition",
    "condition_band",
    "epi_post",
    "benchmark_time_sec",
    "runner_time_sec",
    "std_800_len",
    "std_600_len",
    "std_400_len",
    "std_200_len",
    "std_finish_len",
    "speed_rating",
    "early_rating",
    "mid_rating",
    "late_rating",
    "sectional_status",
    "source_confidence",
    "source_file",
    "benchmark_source",
    "benchmark_sample_races",
    "furlong_labels",
]


def load_standards() -> dict[tuple[str, str, str, str, str], dict[str, str]]:
    lookup = {}
    if not STANDARDS.exists():
        return lookup
    for row in read_csv(STANDARDS):
        key = (
            row.get("benchmark_mode", ""),
            row.get("normalized_track", ""),
            str(int(numeric_float(row.get("distance", "")) or 0)),
            row.get("class_band", ""),
            row.get("condition_band", ""),
        )
        lookup[key] = row
    return lookup


def margin_lengths(row: dict[str, str]) -> float:
    for field in ["beaten_margin", "margin"]:
        value = numeric_float(row.get(field, ""))
        if value is not None:
            return max(0.0, value)
    return 0.0


def rating_to_lengths(value: str, standard: str) -> str:
    num = numeric_float(value)
    base = numeric_float(standard)
    if num is None or base is None:
        return ""
    return f"{round(base - num, 2):.2f}"


def time_to_lengths(value: str, standard_sec: str) -> str:
    num = parse_seconds(value)
    base = numeric_float(standard_sec)
    if num is None or base is None:
        return ""
    return f"{round((num - base) / SECONDS_PER_LENGTH, 2):.2f}"


def finish_lengths(row: dict[str, str], standard: dict[str, str]) -> tuple[str, str]:
    official = parse_seconds(row.get("official_time", ""), row.get("distance", ""))
    benchmark = numeric_float(standard.get("standard_time_sec", ""))
    if official is None or benchmark is None:
        return "", ""
    runner_time = official + margin_lengths(row) * SECONDS_PER_LENGTH
    return f"{runner_time:.3f}", f"{round((runner_time - benchmark) / SECONDS_PER_LENGTH, 2):.2f}"


def standard_for(row: dict[str, str], standards: dict[tuple[str, str, str, str, str], dict[str, str]], mode: str) -> dict[str, str] | None:
    track = row.get("normalized_track", "")
    dist = str(int(numeric_float(row.get("distance", "")) or 0))
    cond = condition_band(row.get("condition", ""))
    c_band = class_band(row.get("class", ""))
    key_class = (mode, track, dist, c_band if mode == "CLASS_BENCHMARK" else "ALL_CLASSES", cond)
    return standards.get(key_class)


def build_output_row(row: dict[str, str], standard: dict[str, str], mode: str) -> dict[str, str]:
    runner_time, std_finish = finish_lengths(row, standard)
    std_800 = rating_to_lengths(row.get("early_raw", ""), standard.get("standard_early_rating", ""))
    std_600 = time_to_lengths(row.get("last_600_raw", ""), standard.get("standard_time_sec", "")) or rating_to_lengths(row.get("mid_raw", ""), standard.get("standard_mid_rating", ""))
    std_400 = time_to_lengths(row.get("last_400_raw", ""), standard.get("standard_time_sec", ""))
    std_200 = time_to_lengths(row.get("last_200_raw", ""), standard.get("standard_time_sec", "")) or rating_to_lengths(row.get("late_raw", ""), standard.get("standard_late_rating", ""))
    any_std = any(has_value(value) for value in [std_800, std_600, std_400, std_200, std_finish])
    if any_std:
        status = "STANDARDISED_LENGTHS"
    elif has_value(row.get("speed_rating_raw", "")) or has_value(row.get("speed_raw", "")):
        status = "SPEED_RATING_ONLY_NO_BENCHMARK_CONVERSION"
    elif any(has_value(row.get(field, "")) for field in SPEED_RAW_FIELDS):
        status = "RAW_SPEED_ONLY_NO_BENCHMARK_CONVERSION"
    else:
        status = "INSUFFICIENT_SPEED_FIELDS"
    return {
        "benchmark_mode": mode,
        "race_date": row.get("race_date", ""),
        "track": row.get("track", ""),
        "race_no": row.get("race_no", ""),
        "runner": row.get("runner", ""),
        "position": row.get("position", ""),
        "distance": row.get("distance", ""),
        "class": row.get("class", ""),
        "class_band": class_band(row.get("class", "")),
        "condition": row.get("condition", ""),
        "condition_band": condition_band(row.get("condition", "")),
        "epi_post": row.get("epi_post", ""),
        "benchmark_time_sec": standard.get("standard_time_sec", ""),
        "runner_time_sec": runner_time,
        "std_800_len": std_800,
        "std_600_len": std_600,
        "std_400_len": std_400,
        "std_200_len": std_200,
        "std_finish_len": std_finish,
        "speed_rating": row.get("speed_rating_raw", ""),
        "early_rating": row.get("early_raw", ""),
        "mid_rating": row.get("mid_raw", ""),
        "late_rating": row.get("late_raw", ""),
        "sectional_status": status,
        "source_confidence": row.get("source_confidence", ""),
        "source_file": row.get("speed_source_file", ""),
        "benchmark_source": "EDGEIQ_STANDARD_TIMES_V1",
        "benchmark_sample_races": standard.get("sample_races", ""),
        "furlong_labels": standard.get("furlong_labels", ""),
    }


def main() -> None:
    rows = list(read_csv(MASTER)) if MASTER.exists() else []
    standards = load_standards()
    out = []
    status_counts: dict[str, int] = {}
    mode_counts = {"CLASS_BENCHMARK": 0, "ALL_CLASSES_BENCHMARK": 0}
    missing_benchmarks = {"CLASS_BENCHMARK": 0, "ALL_CLASSES_BENCHMARK": 0}

    for row in rows:
        for mode in ["CLASS_BENCHMARK", "ALL_CLASSES_BENCHMARK"]:
            standard = standard_for(row, standards, mode)
            if standard is None:
                missing_benchmarks[mode] += 1
                continue
            built = build_output_row(row, standard, mode)
            out.append(built)
            mode_counts[mode] += 1
            status_counts[built["sectional_status"]] = status_counts.get(built["sectional_status"], 0) + 1

    write_csv(OUT, out, FIELDS)
    examples = [row for row in out if row["sectional_status"] == "STANDARDISED_LENGTHS"][:80]
    write_csv(EXAMPLES, examples, FIELDS)
    summary = {
        "input_rows": len(rows),
        "output_rows": len(out),
        "class_benchmark_rows": mode_counts["CLASS_BENCHMARK"],
        "all_classes_benchmark_rows": mode_counts["ALL_CLASSES_BENCHMARK"],
        "missing_class_benchmark_rows": missing_benchmarks["CLASS_BENCHMARK"],
        "missing_all_classes_benchmark_rows": missing_benchmarks["ALL_CLASSES_BENCHMARK"],
        "standardised_lengths_rows": status_counts.get("STANDARDISED_LENGTHS", 0),
        "speed_rating_only_rows": status_counts.get("SPEED_RATING_ONLY_NO_BENCHMARK_CONVERSION", 0),
        "raw_speed_only_rows": status_counts.get("RAW_SPEED_ONLY_NO_BENCHMARK_CONVERSION", 0),
        "insufficient_speed_rows": status_counts.get("INSUFFICIENT_SPEED_FIELDS", 0),
        "class_benchmark_toggle": "SUPPORTED",
        "all_classes_benchmark_toggle": "SUPPORTED",
    }
    write_csv(SUMMARY, [summary], list(summary.keys()))
    print(f"Wrote {OUT} ({len(out)} rows)")


if __name__ == "__main__":
    main()
