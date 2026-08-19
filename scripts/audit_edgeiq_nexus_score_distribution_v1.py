from __future__ import annotations

import csv
import math
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
LIVE = DATA / "edgeiq_live_nexus_contextual_feed_v2.csv"
SCORE = DATA / "edgeiq_nexus_contextual_score_v2.csv"
OUT = DATA / "edgeiq_nexus_score_distribution_v1.csv"
SUMMARY = DATA / "edgeiq_nexus_score_distribution_v1_summary.csv"


def text(value: Any) -> str:
    return str(value or "").strip()


def number(value: Any) -> float | None:
    raw = text(value).replace("%", "")
    if not raw:
        return None
    try:
        val = float(raw)
    except ValueError:
        return None
    return val if math.isfinite(val) else None


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * pct
    lower = math.floor(pos)
    upper = math.ceil(pos)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (pos - lower)


def fmt(value: float | None) -> str:
    return "" if value is None else f"{value:.3f}"


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = read_rows(SCORE) or read_rows(LIVE)
    scored = [row for row in rows if number(row.get("nexus_context_score")) is not None]
    values = [number(row.get("nexus_context_score")) for row in scored]
    values = [value for value in values if value is not None]
    row_count = len(scored)
    between_45_55 = sum(1 for value in values if 45 <= value <= 55)
    band_counts: dict[str, int] = {}
    for row in scored:
        band = text(row.get("nexus_context_band")) or "UNKNOWN"
        band_counts[band] = band_counts.get(band, 0) + 1
    negative_poor = band_counts.get("NEGATIVE", 0) + band_counts.get("POOR", 0)
    clustering_flag = row_count > 0 and between_45_55 / row_count > 0.60
    negative_concentration_flag = row_count > 0 and negative_poor / row_count > 0.70

    distribution_rows: list[dict[str, Any]] = []
    for band, count in sorted(band_counts.items()):
        distribution_rows.append({"section": "band_count", "key": band, "runner_name": "", "race": "", "score": "", "band": band, "count": count, "detail": ""})

    sorted_rows = sorted(scored, key=lambda row: number(row.get("nexus_context_score")) or -999, reverse=True)
    for label, subset in [("top_20", sorted_rows[:20]), ("bottom_20", list(reversed(sorted_rows[-20:])))]:
        for row in subset:
            race = f"{text(row.get('track'))} R{text(row.get('race_no'))}".strip()
            distribution_rows.append(
                {
                    "section": label,
                    "key": text(row.get("runner_key")),
                    "runner_name": text(row.get("runner_name")),
                    "race": race,
                    "score": text(row.get("nexus_context_score")),
                    "band": text(row.get("nexus_context_band")),
                    "count": "",
                    "detail": text(row.get("nexus_summary")),
                }
            )

    race_groups: dict[tuple[str, str, str], list[float]] = {}
    for row in scored:
        key = (text(row.get("race_date")), text(row.get("track")), text(row.get("race_no")))
        score = number(row.get("nexus_context_score"))
        if score is not None:
            race_groups.setdefault(key, []).append(score)
    for key, race_values in sorted(race_groups.items()):
        distribution_rows.append(
            {
                "section": "per_race",
                "key": "|".join(key),
                "runner_name": "",
                "race": f"{key[1]} R{key[2]}",
                "score": "",
                "band": "",
                "count": len(race_values),
                "detail": f"min={min(race_values):.3f}; max={max(race_values):.3f}; mean={mean(race_values):.3f}; median={median(race_values):.3f}",
            }
        )

    summary_rows = [
        {"metric": "row_count", "value": row_count},
        {"metric": "min", "value": fmt(min(values) if values else None)},
        {"metric": "max", "value": fmt(max(values) if values else None)},
        {"metric": "mean", "value": fmt(mean(values) if values else None)},
        {"metric": "median", "value": fmt(median(values) if values else None)},
        {"metric": "std", "value": fmt(pstdev(values) if len(values) > 1 else 0.0 if values else None)},
        {"metric": "p10", "value": fmt(percentile(values, 0.10))},
        {"metric": "p25", "value": fmt(percentile(values, 0.25))},
        {"metric": "p75", "value": fmt(percentile(values, 0.75))},
        {"metric": "p90", "value": fmt(percentile(values, 0.90))},
        {"metric": "scores_between_45_and_55", "value": between_45_55},
        {"metric": "scores_between_45_and_55_pct", "value": fmt((between_45_55 / row_count * 100.0) if row_count else None)},
        {"metric": "clustering_flag_gt_60pct_45_55", "value": "YES" if clustering_flag else "NO"},
        {"metric": "negative_poor_count", "value": negative_poor},
        {"metric": "negative_poor_pct", "value": fmt((negative_poor / row_count * 100.0) if row_count else None)},
        {"metric": "negative_band_concentration_flag_gt_70pct", "value": "YES" if negative_concentration_flag else "NO"},
        {"metric": "recommendation", "value": "Review score calibration before UI prominence." if clustering_flag or negative_concentration_flag else "No recalibration recommendation from distribution audit."},
    ]
    for band, count in sorted(band_counts.items()):
        summary_rows.append({"metric": f"band_count_{band}", "value": count})

    write_csv(OUT, distribution_rows, ["section", "key", "runner_name", "race", "score", "band", "count", "detail"])
    write_csv(SUMMARY, summary_rows, ["metric", "value"])
    print(f"Nexus score distribution audit complete: rows={row_count}, clustered={'YES' if clustering_flag else 'NO'}, negative_concentration={'YES' if negative_concentration_flag else 'NO'}")


if __name__ == "__main__":
    main()
