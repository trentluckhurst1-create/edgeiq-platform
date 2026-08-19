from __future__ import annotations

from collections import defaultdict

from edgeiq_results_common_v1 import DATA, first, now_iso, numeric_float, read_csv, write_csv


OUT = DATA / "edgeiq_true_track_rating_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_true_track_rating_summary_v1.csv"


def official_base(condition: str) -> float:
    raw = condition.upper()
    for token in raw.replace("-", " ").split():
        try:
            return float(token)
        except ValueError:
            pass
    if "GOOD" in raw:
        return 4.0
    if "SOFT" in raw:
        return 6.0
    if "HEAVY" in raw:
        return 9.0
    if "SYNTH" in raw:
        return 5.0
    return 5.0


def main() -> None:
    source = DATA / "edgeiq_standardised_sectionals_v1.csv"
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_csv(source) if source.exists() else []:
        key = first(row, ["race_date"]) + "|" + first(row, ["track"]) + "|" + first(row, ["race_no"])
        if key:
            grouped[key].append(row)
    rows = []
    for key, group in grouped.items():
        first_row = group[0]
        finish_values = [numeric_float(first(row, ["std_finish_len", "finish_len"])) for row in group]
        finish_values = [value for value in finish_values if value is not None]
        speed_values = [numeric_float(first(row, ["speed_rating"])) for row in group]
        speed_values = [value for value in speed_values if value is not None]
        base = official_base(first(first_row, ["condition"]))
        avg_finish = sum(finish_values) / len(finish_values) if finish_values else 0
        avg_speed = sum(speed_values) / len(speed_values) if speed_values else 0
        # Positive finish lengths imply slower-than-standard conditions.
        edgeiq_rating = max(1.0, min(10.0, base + (avg_finish / 8.0) - (avg_speed / 40.0)))
        rows.append({
            "race_date": first(first_row, ["race_date"]),
            "track": first(first_row, ["track"]),
            "race_no": first(first_row, ["race_no"]),
            "official_condition": first(first_row, ["condition"]),
            "edgeiq_true_track_rating": round(edgeiq_rating, 2),
            "avg_finish_len_vs_standard": round(avg_finish, 2),
            "avg_speed_rating": round(avg_speed, 2) if speed_values else "",
            "sample_runners": len(group),
            "source": "EDGEIQ_STANDARDISED_SECTIONALS_V1",
            "built_at": now_iso(),
        })
    fields = ["race_date", "track", "race_no", "official_condition", "edgeiq_true_track_rating", "avg_finish_len_vs_standard", "avg_speed_rating", "sample_runners", "source", "built_at"]
    write_csv(OUT, rows, fields)
    summary = {"races_rated": len(rows), "avg_true_rating": round(sum(float(row["edgeiq_true_track_rating"]) for row in rows) / len(rows), 2) if rows else "", "built_at": now_iso()}
    write_csv(SUMMARY_OUT, [summary], list(summary.keys()))
    print(f"Wrote {OUT} ({len(rows)} rows)")
    print(f"Wrote {SUMMARY_OUT}")


if __name__ == "__main__":
    main()
