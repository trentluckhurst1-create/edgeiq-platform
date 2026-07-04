from __future__ import annotations

import re
from collections import defaultdict
from statistics import median

from edgeiq_results_common_v1 import DATA, coverage_pct, has_value, normalized_track, numeric_float, read_csv, write_csv


MASTER = DATA / "edgeiq_results_master_v1.csv"
OUT = DATA / "edgeiq_standard_times_v1.csv"
SUMMARY = DATA / "edgeiq_standard_times_summary_v1.csv"
EXAMPLES = DATA / "edgeiq_standard_times_examples_v1.csv"

MIN_CLASS_RACES = 5
MIN_ALL_CLASS_RACES = 8

FIELDS = [
    "benchmark_mode",
    "track",
    "normalized_track",
    "distance",
    "class_band",
    "condition_band",
    "sample_races",
    "standard_time_sec",
    "standard_early_rating",
    "standard_mid_rating",
    "standard_late_rating",
    "standard_speed_rating",
    "first_date",
    "last_date",
    "furlong_labels",
]


def parse_seconds(value: object, distance: object = "") -> float | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if ":" in raw:
        parts = raw.split(":")
        try:
            return int(parts[-2]) * 60 + float(parts[-1])
        except Exception:
            return None
    num = numeric_float(raw)
    if num is None:
        return None
    dist = numeric_float(distance)
    if num > 1000:
        num = num / 100.0
    if dist:
        sec_per_200 = num / max(1.0, dist / 200.0)
        if sec_per_200 < 8.0 or sec_per_200 > 22.0:
            return None
    return num


def class_band(value: str) -> str:
    raw = (value or "").upper().replace("-", " ")
    raw = re.sub(r"\s+", " ", raw).strip()
    if not raw:
        return "UNKNOWN"
    bm = re.search(r"\bBM\s*(\d+)\b", raw)
    if bm:
        rating = int(bm.group(1))
        if rating < 58:
            return "BM_LOW"
        if rating < 70:
            return "BM_58_69"
        if rating < 80:
            return "BM_70_79"
        if rating < 90:
            return "BM_80_89"
        return "BM_90_PLUS"
    if "MAIDEN" in raw or raw == "MDN":
        return "MAIDEN"
    if "GROUP 1" in raw or "G1" in raw:
        return "GROUP_1"
    if "GROUP 2" in raw or "G2" in raw:
        return "GROUP_2"
    if "GROUP 3" in raw or "G3" in raw:
        return "GROUP_3"
    if "LISTED" in raw or raw == "LR":
        return "LISTED"
    if "OPEN" in raw:
        return "OPEN"
    if "HANDICAP" in raw or raw == "HCP":
        return "HANDICAP"
    if "CLASS" in raw:
        return raw.replace(" ", "_")[:30]
    return raw[:30].replace(" ", "_")


def condition_band(value: str) -> str:
    raw = (value or "").upper()
    if "SYNTH" in raw or "POLY" in raw:
        return "SYNTHETIC"
    if "HEAVY" in raw:
        return "HEAVY"
    if "SOFT" in raw:
        return "SOFT"
    if "GOOD" in raw:
        return "GOOD"
    if "FIRM" in raw:
        return "FIRM"
    if "SLOW" in raw:
        return "SOFT"
    if "DEAD" in raw:
        return "GOOD"
    return "UNKNOWN"


def furlong_labels(distance: object) -> str:
    dist = numeric_float(distance)
    if dist is None:
        return ""
    start = int(round(dist / 200.0) * 200)
    labels = []
    current = start
    while current > 200:
        labels.append(f"{current}-{current - 200}")
        current -= 200
    labels.append("200-FIN")
    return ";".join(labels)


def add_value(groups: dict[tuple[str, ...], dict[str, object]], key: tuple[str, ...], row: dict[str, str], time_sec: float) -> None:
    item = groups.setdefault(
        key,
        {
            "times": [],
            "early": [],
            "mid": [],
            "late": [],
            "speed": [],
            "dates": [],
            "track": row.get("track", ""),
            "normalized_track": row.get("normalized_track", "") or normalized_track(row.get("track", "")),
            "distance": row.get("distance", ""),
            "class_band": key[3],
            "condition_band": key[4],
        },
    )
    item["times"].append(time_sec)
    item["dates"].append(row.get("race_date", ""))
    for field, bucket in [("early_raw", "early"), ("mid_raw", "mid"), ("late_raw", "late"), ("speed_rating_raw", "speed")]:
        value = numeric_float(row.get(field, ""))
        if value is not None and 0 <= value <= 150:
            item[bucket].append(value)


def build_rows(groups: dict[tuple[str, ...], dict[str, object]], mode: str, min_races: int) -> list[dict[str, object]]:
    rows = []
    for key, item in groups.items():
        times = item["times"]
        if len(times) < min_races:
            continue
        rows.append(
            {
                "benchmark_mode": mode,
                "track": item["track"],
                "normalized_track": item["normalized_track"],
                "distance": item["distance"],
                "class_band": item["class_band"],
                "condition_band": item["condition_band"],
                "sample_races": len(times),
                "standard_time_sec": round(median(times), 3),
                "standard_early_rating": round(median(item["early"]), 3) if item["early"] else "",
                "standard_mid_rating": round(median(item["mid"]), 3) if item["mid"] else "",
                "standard_late_rating": round(median(item["late"]), 3) if item["late"] else "",
                "standard_speed_rating": round(median(item["speed"]), 3) if item["speed"] else "",
                "first_date": min(d for d in item["dates"] if d) if item["dates"] else "",
                "last_date": max(d for d in item["dates"] if d) if item["dates"] else "",
                "furlong_labels": furlong_labels(item["distance"]),
            }
        )
    return rows


def main() -> None:
    class_groups: dict[tuple[str, ...], dict[str, object]] = {}
    all_class_groups: dict[tuple[str, ...], dict[str, object]] = {}
    seen_races = set()
    input_races = 0

    for row in read_csv(MASTER):
        if row.get("position") not in {"1", "1.0"}:
            continue
        race_key = row.get("race_key", "")
        if not race_key or race_key in seen_races:
            continue
        seen_races.add(race_key)
        time_sec = parse_seconds(row.get("official_time", ""), row.get("distance", ""))
        if time_sec is None:
            continue
        input_races += 1
        track_norm = row.get("normalized_track", "") or normalized_track(row.get("track", ""))
        dist = str(int(numeric_float(row.get("distance", "")) or 0))
        c_band = class_band(row.get("class", ""))
        cond = condition_band(row.get("condition", ""))
        class_key = (track_norm, dist, "CLASS", c_band, cond)
        all_key = (track_norm, dist, "ALL", "ALL_CLASSES", cond)
        add_value(class_groups, class_key, row, time_sec)
        add_value(all_class_groups, all_key, row, time_sec)

    class_rows = build_rows(class_groups, "CLASS_BENCHMARK", MIN_CLASS_RACES)
    all_rows = build_rows(all_class_groups, "ALL_CLASSES_BENCHMARK", MIN_ALL_CLASS_RACES)
    rows = sorted(class_rows + all_rows, key=lambda r: (r["normalized_track"], int(r["distance"]) if str(r["distance"]).isdigit() else 99999, r["condition_band"], r["benchmark_mode"], r["class_band"]))
    write_csv(OUT, rows, FIELDS)

    summary = {
        "input_winner_time_races": input_races,
        "class_benchmark_rows": len(class_rows),
        "all_classes_benchmark_rows": len(all_rows),
        "total_standard_rows": len(rows),
        "track_count": len({row["normalized_track"] for row in rows}),
        "distance_count": len({row["distance"] for row in rows}),
        "class_benchmark_min_races": MIN_CLASS_RACES,
        "all_classes_min_races": MIN_ALL_CLASS_RACES,
    }
    write_csv(SUMMARY, [summary], list(summary.keys()))
    write_csv(EXAMPLES, rows[:50], FIELDS)
    print(f"Wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
