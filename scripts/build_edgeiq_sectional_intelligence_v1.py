from __future__ import annotations

from bisect import bisect_right
from statistics import mean

from edgeiq_results_common_v1 import DATA, first, normalized_runner, now_iso, numeric_float, read_csv, write_csv


OUT = DATA / "edgeiq_sectional_intelligence_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_sectional_intelligence_summary_v1.csv"


def score_from_lengths(value: float | None) -> float:
    if value is None:
        return 50.0
    # Negative lengths are faster than standard.
    return max(1.0, min(99.0, 50.0 - value * 6.0))


def grade(score: float) -> str:
    if score >= 85:
        return "A"
    if score >= 72:
        return "B"
    if score >= 60:
        return "C"
    if score >= 48:
        return "D"
    return "E"


def main() -> None:
    source = DATA / "edgeiq_standardised_sectionals_v1.csv"
    rows = []
    raw_rows = list(read_csv(source)) if source.exists() else []
    figures = []
    for row in raw_rows:
        s800 = numeric_float(first(row, ["std_800_len"]))
        s600 = numeric_float(first(row, ["std_600_len"]))
        s400 = numeric_float(first(row, ["std_400_len"]))
        s200 = numeric_float(first(row, ["std_200_len"]))
        finish = numeric_float(first(row, ["std_finish_len"]))
        speed_rating = numeric_float(first(row, ["speed_rating"]))
        early = score_from_lengths(s800)
        mid = score_from_lengths(s600 if s600 is not None else s400)
        closing = score_from_lengths(finish if finish is not None else s200)
        turn = max(closing - mid + 50, 1)
        sustained = mean([early, mid, closing])
        pressure = max(1.0, min(99.0, 100.0 - abs(early - closing) * 1.4))
        tempo_resilience = mean([mid, closing, pressure])
        dependency = abs(closing - early)
        sectional_figure = speed_rating if speed_rating is not None else sustained
        figures.append(sectional_figure)
        rows.append({
            "race_date": first(row, ["race_date"]),
            "track": first(row, ["track"]),
            "race_no": first(row, ["race_no"]),
            "runner": first(row, ["runner"]),
            "normalized_runner": normalized_runner(first(row, ["runner", "normalized_runner"])),
            "early_speed_score": round(early, 2),
            "mid_speed_score": round(mid, 2),
            "closing_speed_score": round(closing, 2),
            "turn_of_foot_score": round(turn, 2),
            "sustained_speed_score": round(sustained, 2),
            "pressure_rating": round(pressure, 2),
            "tempo_resilience": round(tempo_resilience, 2),
            "race_shape_dependency": round(dependency, 2),
            "sectional_figure": round(sectional_figure, 2),
            "sectional_percentile": "",
            "sectional_grade": "",
            "source_status": first(row, ["sectional_status"]),
            "built_at": now_iso(),
        })
    sorted_figures = sorted(figures)
    figure_count = len(sorted_figures)
    for row in rows:
        figure = float(row["sectional_figure"])
        percentile = round((bisect_right(sorted_figures, figure) / figure_count) * 100, 2) if figure_count else 0
        row["sectional_percentile"] = percentile
        row["sectional_grade"] = grade(figure if figure <= 99 else percentile)
    fields = ["race_date", "track", "race_no", "runner", "normalized_runner", "early_speed_score", "mid_speed_score", "closing_speed_score", "turn_of_foot_score", "sustained_speed_score", "pressure_rating", "tempo_resilience", "race_shape_dependency", "sectional_figure", "sectional_percentile", "sectional_grade", "source_status", "built_at"]
    write_csv(OUT, rows, fields)
    summary = {"rows": len(rows), "graded_rows": sum(1 for row in rows if row["sectional_grade"]), "built_at": now_iso()}
    write_csv(SUMMARY_OUT, [summary], list(summary.keys()))
    print(f"Wrote {OUT} ({len(rows)} rows)")
    print(f"Wrote {SUMMARY_OUT}")


if __name__ == "__main__":
    main()
