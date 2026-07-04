from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from edgeiq_results_common_v1 import DATA, first, has_value, normalized_runner, now_iso, read_csv, write_csv


BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
FORM = DATA / "runner_form_history.csv"
RESULTS = DATA / "edgeiq_results_master_v1.csv"
OUT = DATA / "edgeiq_missing_projected_ratings_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_missing_projected_ratings_summary_v1.csv"


RATING_KEYS = ["projected_rating_v5_2", "projected_rating_V6_1_RESEARCH", "epi", "runner_rating"]


def load(path: Path) -> list[dict[str, str]]:
    return list(read_csv(path)) if path.exists() else []


def runner_name(row: dict[str, str]) -> str:
    return first(row, ["horse", "runner", "runner_name"])


def has_rating(row: dict[str, str]) -> bool:
    return has_value(first(row, RATING_KEYS))


def classify(row: dict[str, str], form_count: int, result_count: int) -> str:
    if not has_value(first(row, ["runner_key"])):
        return "MISSING_RUNNER_KEY"
    horse = runner_name(row)
    if not normalized_runner(horse):
        return "MISSING_RUNNER_KEY"
    if form_count == 0 and result_count == 0:
        return "FIRST_STARTER"
    if form_count == 0:
        return "NO_HISTORICAL_RUNS"
    if result_count > 0:
        return "JOIN_FAILURE"
    return "MISSING_RATING_HISTORY"


def main() -> None:
    board = load(BOARD)
    form_rows = load(FORM)

    # Results master is large, but this is a backend audit. Keep only runner counts.
    result_counts: Counter[str] = Counter()
    if RESULTS.exists():
        for row in read_csv(RESULTS):
            key = normalized_runner(first(row, ["runner", "horse", "runner_name", "normalized_runner"]))
            if key:
                result_counts[key] += 1

    form_counts: Counter[str] = Counter()
    for row in form_rows:
        key = normalized_runner(first(row, ["horse", "runner", "runner_name", "horse_key"]))
        if key:
            form_counts[key] += 1

    output: list[dict[str, object]] = []
    for row in board:
        if has_rating(row):
            continue
        horse = runner_name(row)
        key = normalized_runner(horse)
        category = classify(row, form_counts[key], result_counts[key])
        output.append(
            {
                "race_date": first(row, ["race_date"]),
                "track": first(row, ["track"]),
                "race_no": first(row, ["race_no"]),
                "race_key": first(row, ["race_key"]),
                "saddlecloth": first(row, ["saddlecloth", "horse_no", "runner_no"]),
                "runner": horse,
                "normalized_runner": key,
                "runner_key": first(row, ["runner_key"]),
                "jockey": first(row, ["jockey", "rider"]),
                "trainer": first(row, ["trainer"]),
                "rating_source": first(row, RATING_KEYS, "MISSING"),
                "projection_source": first(row, ["projection_band_v5_2", "projection_confidence_v5_2", "projection_band_V6_1_RESEARCH"], "MISSING"),
                "form_history_rows": form_counts[key],
                "results_history_rows": result_counts[key],
                "why_missing": category,
                "built_at": now_iso(),
            }
        )

    fields = [
        "race_date",
        "track",
        "race_no",
        "race_key",
        "saddlecloth",
        "runner",
        "normalized_runner",
        "runner_key",
        "jockey",
        "trainer",
        "rating_source",
        "projection_source",
        "form_history_rows",
        "results_history_rows",
        "why_missing",
        "built_at",
    ]
    write_csv(OUT, output, fields)

    counts = Counter(str(row["why_missing"]) for row in output)
    summary = [{"metric": "missing_projected_rating_rows", "value": len(output)}]
    for key in ["NO_BASE_RATING", "NO_HISTORICAL_RUNS", "JOIN_FAILURE", "FIRST_STARTER", "IMPORT", "MISSING_RUNNER_KEY", "MISSING_RATING_HISTORY"]:
        summary.append({"metric": key, "value": counts.get(key, 0)})
    summary.append({"metric": "built_at", "value": now_iso()})
    write_csv(SUMMARY_OUT, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(output)} rows)")
    print(f"Wrote {SUMMARY_OUT}")


if __name__ == "__main__":
    main()
