from __future__ import annotations

from collections import defaultdict
from statistics import median

from edgeiq_results_common_v1 import DATA, coverage_pct, numeric_float, read_csv, write_csv
from build_edgeiq_standard_times_v1 import class_band, condition_band


INP = DATA / "edgeiq_standardised_sectionals_v1.csv"
OUT = DATA / "edgeiq_lengths_per_point_engine_v1.csv"
SUMMARY = DATA / "edgeiq_lengths_per_point_engine_summary_v1.csv"

FIELDS = ["distance_band", "class_band", "condition_band", "sample_size", "rating_point_to_lengths", "confidence", "fallback_level"]


def distance_band(value: str) -> str:
    dist = numeric_float(value)
    if dist is None:
        return "UNKNOWN"
    start = int(dist // 200) * 200
    end = start + 199
    return f"{start}-{end}"


def confidence(sample: int) -> str:
    if sample >= 1000:
        return "HIGH"
    if sample >= 250:
        return "MEDIUM"
    if sample >= 50:
        return "LOW"
    return "SPARSE"


def build_rows() -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    for row in read_csv(INP):
        if row.get("benchmark_mode") != "CLASS_BENCHMARK":
            continue
        rating = numeric_float(row.get("speed_rating", ""))
        finish = numeric_float(row.get("std_finish_len", ""))
        if rating is None or finish is None:
            continue
        # Convert observed finish deviation and rating deviation into a robust empirical scale.
        # The clamp avoids one-off extreme races dominating future research pricing.
        ratio = abs(finish) / max(1.0, abs(100.0 - rating))
        if 0.02 <= ratio <= 5.0:
            d_band = distance_band(row.get("distance", ""))
            c_band = row.get("class_band", "") or class_band(row.get("class", ""))
            cond = row.get("condition_band", "") or condition_band(row.get("condition", ""))
            groups[(d_band, c_band, cond, "DIST_CLASS_COND")].append(ratio)
            groups[(d_band, c_band, "ALL_CONDITIONS", "DIST_CLASS")].append(ratio)
            groups[(d_band, "ALL_CLASSES", cond, "DIST_COND")].append(ratio)
            groups[(d_band, "ALL_CLASSES", "ALL_CONDITIONS", "DISTANCE")].append(ratio)

    rows = []
    for (d_band, c_band, cond, fallback), values in groups.items():
        if len(values) < 30 and fallback != "DISTANCE":
            continue
        if len(values) < 20:
            continue
        rows.append(
            {
                "distance_band": d_band,
                "class_band": c_band,
                "condition_band": cond,
                "sample_size": len(values),
                "rating_point_to_lengths": round(median(values), 4),
                "confidence": confidence(len(values)),
                "fallback_level": fallback,
            }
        )
    rows.sort(key=lambda r: (r["fallback_level"], r["distance_band"], r["class_band"], r["condition_band"]))
    return rows


def main() -> None:
    rows = build_rows()
    write_csv(OUT, rows, FIELDS)
    summary = {
        "lengths_per_point_rows": len(rows),
        "high_confidence_rows": sum(1 for r in rows if r["confidence"] == "HIGH"),
        "medium_confidence_rows": sum(1 for r in rows if r["confidence"] == "MEDIUM"),
        "low_confidence_rows": sum(1 for r in rows if r["confidence"] == "LOW"),
        "fallback_distance_rows": sum(1 for r in rows if r["fallback_level"] == "DISTANCE"),
    }
    write_csv(SUMMARY, [summary], list(summary.keys()))
    print(f"Wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
