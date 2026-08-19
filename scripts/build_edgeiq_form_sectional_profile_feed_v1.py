from __future__ import annotations

from collections import Counter

from edgeiq_results_common_v1 import DATA, key_for, normalized_runner, read_csv, write_csv


SECTIONALS = DATA / "edgeiq_standardised_sectionals_v1.csv"
TERMINAL = DATA / "edgeiq_results_terminal_feed_v1.csv"
OUT = DATA / "edgeiq_form_sectional_profile_feed_v1.csv"
SUMMARY = DATA / "edgeiq_form_sectional_profile_feed_summary_v1.csv"

FIELDS = [
    "runner",
    "normalized_runner",
    "race_date",
    "track",
    "race_no",
    "race_key",
    "distance",
    "class",
    "condition",
    "position",
    "margin",
    "sp",
    "epi_post",
    "benchmark_mode",
    "split_labels",
    "split_lengths",
    "finish_len",
    "sectional_status",
    "source_confidence",
]


def terminal_lookup() -> dict[str, dict[str, str]]:
    lookup = {}
    if not TERMINAL.exists():
        return lookup
    for row in read_csv(TERMINAL):
        lookup[key_for(row.get("race_date", ""), row.get("track", ""), row.get("race_no", ""), row.get("runner", ""))] = row
    return lookup


def split_lengths(row: dict[str, str]) -> str:
    labels = [label for label in row.get("furlong_labels", "").split(";") if label]
    values = []
    for label in labels:
        start = label.split("-", 1)[0]
        value = ""
        if start == "800":
            value = row.get("std_800_len", "")
        elif start == "600":
            value = row.get("std_600_len", "")
        elif start == "400":
            value = row.get("std_400_len", "")
        elif start == "200":
            value = row.get("std_200_len", "")
        values.append(value)
    return ";".join(values)


def main() -> None:
    base = terminal_lookup()
    rows = []
    mode_counts = Counter()
    status_counts = Counter()
    for sec in read_csv(SECTIONALS):
        key = key_for(sec.get("race_date", ""), sec.get("track", ""), sec.get("race_no", ""), sec.get("runner", ""))
        term = base.get(key, {})
        out = {
            "runner": sec.get("runner", ""),
            "normalized_runner": normalized_runner(sec.get("runner", "")),
            "race_date": sec.get("race_date", ""),
            "track": sec.get("track", ""),
            "race_no": sec.get("race_no", ""),
            "race_key": key_for(sec.get("race_date", ""), sec.get("track", ""), sec.get("race_no", "")),
            "distance": sec.get("distance", ""),
            "class": sec.get("class", ""),
            "condition": sec.get("condition", ""),
            "position": sec.get("position", ""),
            "margin": term.get("margin", ""),
            "sp": term.get("sp", ""),
            "epi_post": sec.get("epi_post", "") or term.get("epi_post", ""),
            "benchmark_mode": sec.get("benchmark_mode", ""),
            "split_labels": sec.get("furlong_labels", ""),
            "split_lengths": split_lengths(sec),
            "finish_len": sec.get("std_finish_len", ""),
            "sectional_status": sec.get("sectional_status", ""),
            "source_confidence": sec.get("source_confidence", ""),
        }
        rows.append(out)
        mode_counts[out["benchmark_mode"]] += 1
        status_counts[out["sectional_status"]] += 1
    write_csv(OUT, rows, FIELDS)
    summary = {
        "rows": len(rows),
        "class_benchmark_rows": mode_counts["CLASS_BENCHMARK"],
        "all_classes_benchmark_rows": mode_counts["ALL_CLASSES_BENCHMARK"],
        "standardised_lengths_rows": status_counts["STANDARDISED_LENGTHS"],
        "speed_rating_only_rows": status_counts["SPEED_RATING_ONLY_NO_BENCHMARK_CONVERSION"],
        "unique_runners": len({row["normalized_runner"] for row in rows if row["normalized_runner"]}),
        "unique_races": len({row["race_key"] for row in rows if row["race_key"]}),
    }
    write_csv(SUMMARY, [summary], list(summary.keys()))
    print(f"Wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
