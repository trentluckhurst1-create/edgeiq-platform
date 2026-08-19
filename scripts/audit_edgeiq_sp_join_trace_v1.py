from __future__ import annotations

from collections import Counter
from pathlib import Path

from edgeiq_results_common_v1 import DATA, first, has_value, key_for, normalize_race_no, normalized_runner, normalized_track, parse_date, read_csv, write_csv


DOWNSTREAM_FILES = [
    "race_results.csv",
    "runner_form_history.csv",
    "form_card_runs.csv",
    "edgeiq_runner_form_engine_current.csv",
    "edgeiq_ratings_intelligence_heatmap_v1.csv",
    "model_result_review.csv",
    "edgeiq_results_terminal_feed_v1.csv",
]


def row_identity(row: dict[str, str]) -> tuple[str, str, str, str]:
    date = parse_date(first(row, ["race_date", "meeting_date", "date", "run_date"]))
    track = first(row, ["track", "venue_name", "meeting"])
    race_no = first(row, ["race_no", "race_number", "race"])
    runner = first(row, ["runner", "horse", "horse_name", "horseName", "runner_name"])
    return date, track, race_no, runner


def build_indexes(master_rows: list[dict[str, str]]) -> dict[str, set[tuple[str, ...]]]:
    indexes: dict[str, set[tuple[str, ...]]] = {
        "runner_date_race": set(),
        "runner_date_track": set(),
        "runner_track_race": set(),
        "date_track_race": set(),
    }
    for row in master_rows:
        date = row.get("race_date", "")
        track_norm = row.get("normalized_track", "") or normalized_track(row.get("track", ""))
        race = normalize_race_no(row.get("race_no", ""))
        runner_norm = row.get("normalized_runner", "") or normalized_runner(row.get("runner", ""))
        indexes["runner_date_race"].add((runner_norm, date, race))
        indexes["runner_date_track"].add((runner_norm, date, track_norm))
        indexes["runner_track_race"].add((runner_norm, track_norm, race))
        indexes["date_track_race"].add((date, track_norm, race))
    return indexes


def classify_failure(date: str, track: str, race_no: str, runner: str, indexes: dict[str, set[tuple[str, ...]]]) -> str:
    if not runner:
        return "SCRATCHED_OR_NON_RUNNER"
    runner_norm = normalized_runner(runner)
    track_norm = normalized_track(track)
    race = normalize_race_no(race_no)
    if (runner_norm, date, race) in indexes["runner_date_race"]:
        return "TRACK_NAME_MISMATCH"
    if (runner_norm, date, track_norm) in indexes["runner_date_track"]:
        return "RACE_NO_MISMATCH"
    if (runner_norm, track_norm, race) in indexes["runner_track_race"]:
        return "RACE_DATE_MISMATCH"
    if (date, track_norm, race) in indexes["date_track_race"]:
        return "RUNNER_NAME_MISMATCH"
    return "UNKNOWN"


def main() -> None:
    master_rows = list(read_csv(DATA / "edgeiq_results_master_v1.csv"))
    master_by_key = {key_for(row["race_date"], row["track"], row["race_no"], row["runner"]): row for row in master_rows}
    indexes = build_indexes(master_rows)
    trace_rows = []
    reasons = Counter()

    for file_name in DOWNSTREAM_FILES:
        path = DATA / file_name
        if not path.exists():
            continue
        for row in read_csv(path):
            date, track, race_no, runner = row_identity(row)
            if not (date and track and race_no and runner):
                continue
            downstream_sp = first(row, ["sp", "sp_num", "starting_price", "starting_price_decimal", "fixed_win_dividend", "tab_fixed_win"])
            key = key_for(date, track, race_no, runner)
            master = master_by_key.get(key)
            master_sp = first(master or {}, ["sp", "starting_price"])
            if has_value(downstream_sp):
                reason = "OK"
            elif master and has_value(master_sp):
                reason = "OUTPUT_JOIN_MISSING"
            elif master:
                reason = "SOURCE_SP_MISSING"
            else:
                reason = classify_failure(date, track, race_no, runner, indexes)
            reasons[reason] += 1
            trace_rows.append({
                "downstream_file": file_name,
                "race_date": date,
                "track": track,
                "race_no": race_no,
                "runner": runner,
                "master_found": "YES" if master else "NO",
                "master_sp": master_sp,
                "downstream_sp": downstream_sp,
                "failure_reason": reason,
                "responsible_builder": "UNKNOWN_CURRENT_FEED_BUILDER" if reason == "OUTPUT_JOIN_MISSING" else "",
            })

    fields = ["downstream_file", "race_date", "track", "race_no", "runner", "master_found", "master_sp", "downstream_sp", "failure_reason", "responsible_builder"]
    write_csv(DATA / "edgeiq_sp_join_trace_v1.csv", trace_rows, fields)
    summary = [{"failure_reason": reason, "rows": count} for reason, count in reasons.most_common()]
    write_csv(DATA / "edgeiq_sp_join_trace_summary_v1.csv", summary, ["failure_reason", "rows"])
    print(f"Wrote SP join trace ({len(trace_rows)} rows)")


if __name__ == "__main__":
    main()
