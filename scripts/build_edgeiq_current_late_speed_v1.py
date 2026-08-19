from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import date
from typing import Any

from edgeiq_current_speed_projection_v1_common import (
    DATA,
    SECTIONAL_PROFILE,
    SPEED_MASTER,
    band_from_score,
    canon_runner,
    clean,
    clamp,
    group_by_race,
    load_current_runners,
    load_profile_starts,
    normalise_date,
    now_utc,
    parse_date,
    round_or_none,
    stats,
    to_float,
    write_csv,
    write_json,
    write_summary,
)


OUT_JSON = DATA / "edgeiq_current_late_speed_v1.json"
OUT_CSV = DATA / "edgeiq_current_late_speed_v1.csv"
COVERAGE = DATA / "edgeiq_current_late_speed_v1_coverage.txt"
GAP_AUDIT = DATA / "edgeiq_current_late_speed_v1_gap_audit.csv"
EVIDENCE_AUDIT = DATA / "edgeiq_current_late_speed_v1_evidence_audit.csv"

VERSION = "CURRENT_LATE_SPEED_V1"
MIN_EVIDENCE_RUNS = 2


def split_map(row: dict[str, Any]) -> dict[str, float]:
    labels = [clean(part).upper() for part in str(row.get("split_labels") or "").split(";")]
    values = str(row.get("split_lengths") or "").split(";")
    out: dict[str, float] = {}
    for label, value in zip(labels, values):
        parsed = to_float(value)
        if label and parsed is not None:
            out[label] = parsed
    return out


def late_esi_from_splits(row: dict[str, Any]) -> tuple[float | None, str]:
    splits = split_map(row)
    final_segments: list[tuple[str, float]] = []
    for label in ("600-400", "400-200", "200-FIN"):
        if label in splits:
            final_segments.append((label, splits[label]))
    if not final_segments:
        return None, "NO_LATE_SPLITS"
    labels = {label for label, _value in final_segments}
    if {"600-400", "400-200", "200-FIN"}.issubset(labels):
        quality = "FINAL_600"
    elif {"400-200", "200-FIN"}.issubset(labels):
        quality = "FINAL_400"
    elif "200-FIN" in labels:
        quality = "FINAL_200"
    else:
        quality = "PARTIAL_FINAL"
    return sum(value for _label, value in final_segments) / len(final_segments), quality


def load_benchmarked_late(current_names: set[str]) -> dict[str, list[dict[str, Any]]]:
    rows_by_runner: dict[str, dict[tuple[str, str, str, str], dict[str, Any]]] = defaultdict(dict)
    priority = {"CLASS_BENCHMARK": 0, "ALL_CLASSES_BENCHMARK": 1}
    if not SECTIONAL_PROFILE.exists():
        return {}
    with SECTIONAL_PROFILE.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        for row in csv.DictReader(handle):
            runner_key = canon_runner(row.get("normalized_runner") or row.get("runner"))
            if runner_key not in current_names:
                continue
            row_date = parse_date(row.get("race_date"))
            if row_date is None:
                continue
            late_esi, quality = late_esi_from_splits(row)
            if late_esi is None:
                continue
            run_key = (
                normalise_date(row.get("race_date")),
                clean(row.get("track")).upper(),
                clean(row.get("race_no")),
                clean(row.get("distance")),
            )
            existing = rows_by_runner[runner_key].get(run_key)
            current_priority = priority.get(clean(row.get("benchmark_mode")).upper(), 9)
            existing_priority = priority.get(clean((existing or {}).get("benchmarkMode")).upper(), 9)
            if existing is None or current_priority < existing_priority:
                rows_by_runner[runner_key][run_key] = {
                    "runner": clean(row.get("runner")),
                    "normalizedRunner": runner_key,
                    "raceDate": row_date,
                    "raceDateText": normalise_date(row.get("race_date")),
                    "track": clean(row.get("track")),
                    "raceNo": clean(row.get("race_no")),
                    "distance": to_float(row.get("distance")),
                    "class": clean(row.get("class")),
                    "condition": clean(row.get("condition")),
                    "benchmarkMode": clean(row.get("benchmark_mode")),
                    "lateEsi": late_esi,
                    "evidenceQuality": quality,
                    "sourceFile": "edgeiq_form_sectional_profile_feed_v1.csv",
                }
    out: dict[str, list[dict[str, Any]]] = {}
    for runner, keyed in rows_by_runner.items():
        rows = list(keyed.values())
        rows.sort(key=lambda item: item["raceDate"], reverse=True)
        out[runner] = rows
    return out


def load_speed_late(current_names: set[str]) -> dict[str, list[dict[str, Any]]]:
    rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if not SPEED_MASTER.exists():
        return rows
    with SPEED_MASTER.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        for row in csv.DictReader(handle):
            runner_key = canon_runner(row.get("normalized_runner") or row.get("runner"))
            if runner_key not in current_names:
                continue
            row_date = parse_date(row.get("race_date"))
            late_raw = to_float(row.get("late_raw"))
            if row_date is None or late_raw is None:
                continue
            rows[runner_key].append(
                {
                    "runner": clean(row.get("runner")),
                    "normalizedRunner": runner_key,
                    "raceDate": row_date,
                    "raceDateText": normalise_date(row.get("race_date")),
                    "track": clean(row.get("track")),
                    "raceNo": clean(row.get("race_no")),
                    "distance": to_float(row.get("distance")),
                    "class": clean(row.get("class")),
                    "condition": clean(row.get("condition")),
                    "lateRaw": late_raw,
                    "sourceFile": "edgeiq_speed_master_v1.csv",
                }
            )
    for bucket in rows.values():
        bucket.sort(key=lambda item: item["raceDate"], reverse=True)
    return rows


def comparable(rows: list[dict[str, Any]], race_date: date, distance: float | None) -> tuple[list[dict[str, Any]], Counter]:
    counters: Counter = Counter()
    asof = [row for row in rows if row["raceDate"] < race_date]
    counters["asof_runs"] = len(asof)
    counters["future_or_selected_excluded"] = len([row for row in rows if row["raceDate"] >= race_date])
    if distance is not None:
        comp = [row for row in asof if row.get("distance") is not None and abs(float(row["distance"]) - distance) <= 400]
    else:
        comp = []
    counters["comparable_distance_runs"] = len(comp)
    selected = comp if comp else asof
    return selected[:8], counters


def score_from_esi(rows: list[dict[str, Any]]) -> float | None:
    values = [float(row["lateEsi"]) for row in rows if row.get("lateEsi") is not None]
    if len(values) < MIN_EVIDENCE_RUNS:
        return None
    # Source convention: negative ESI means faster/inside standard. Convert to a
    # public 0-100 strength score while preserving that sign meaning.
    avg_esi = sum(values) / len(values)
    return clamp(50 - (avg_esi * 10))


def score_from_late_raw(rows: list[dict[str, Any]]) -> float | None:
    values = [float(row["lateRaw"]) for row in rows if row.get("lateRaw") is not None]
    if len(values) < MIN_EVIDENCE_RUNS:
        return None
    return clamp(sum(values) / len(values))


def main() -> None:
    generated_at = now_utc()
    current = load_current_runners()
    current_names = {row["normalizedRunner"] for row in current}
    profile_starts = load_profile_starts()
    benchmarked = load_benchmarked_late(current_names)
    speed_late = load_speed_late(current_names)
    output_rows: list[dict[str, Any]] = []
    gap_rows: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    scores: list[float] = []
    reason_counts: Counter = Counter()

    for runner in current:
        selected_date = parse_date(runner["raceDate"])
        bench_selected: list[dict[str, Any]] = []
        speed_selected: list[dict[str, Any]] = []
        bench_counts: Counter = Counter()
        speed_counts: Counter = Counter()
        if selected_date:
            bench_selected, bench_counts = comparable(benchmarked.get(runner["normalizedRunner"], []), selected_date, runner.get("distance"))
            speed_selected, speed_counts = comparable(speed_late.get(runner["normalizedRunner"], []), selected_date, runner.get("distance"))

        bench_score = score_from_esi(bench_selected)
        raw_score = score_from_late_raw(speed_selected)
        if bench_score is not None:
            score = round_or_none(bench_score, 1)
            join_method = "RUNNER_NAME_ASOF_BENCHMARKED_LATE_SPLITS"
            evidence = bench_selected
            input_field = "split_lengths.final_600_400_200"
        elif raw_score is not None:
            score = round_or_none(raw_score, 1)
            join_method = "RUNNER_NAME_ASOF_SPEED_MASTER_LATE_PROFILE"
            evidence = speed_selected
            input_field = "late_raw"
        else:
            score = None
            join_method = "NO_APPROVED_LATE_SPEED_EVIDENCE"
            evidence = bench_selected or speed_selected
            input_field = "late_raw_or_split_lengths"

        if score is not None:
            scores.append(float(score))
            reason = ""
        else:
            starts = profile_starts.get(runner["normalizedRunner"], 0)
            if starts == 0 and bench_counts.get("asof_runs", 0) == 0 and speed_counts.get("asof_runs", 0) == 0:
                reason = "FIRST_STARTER"
            elif bench_counts.get("asof_runs", 0) == 0 and speed_counts.get("asof_runs", 0) == 0:
                reason = "NO_ASOF_EVIDENCE"
            elif bench_counts.get("asof_runs", 0) == 0 and speed_counts.get("asof_runs", 0) == 0:
                reason = "NO_SECTIONAL_HISTORY"
            elif len(bench_selected) + len(speed_selected) < MIN_EVIDENCE_RUNS:
                reason = "INSUFFICIENT_BENCHMARKED_RUNS"
            elif runner.get("distance") and bench_counts.get("comparable_distance_runs", 0) == 0 and speed_counts.get("comparable_distance_runs", 0) == 0:
                reason = "NO_COMPARABLE_DISTANCE"
            else:
                reason = "OTHER"
            reason_counts[reason] += 1

        recency = None
        if evidence and selected_date:
            recency = (selected_date - evidence[0]["raceDate"]).days
        comparable_runs = max(bench_counts.get("comparable_distance_runs", 0), speed_counts.get("comparable_distance_runs", 0))
        row = {
            "raceDate": runner["raceDate"],
            "meeting": runner["meeting"],
            "raceNumber": runner["raceNumber"],
            "runnerId": runner["runnerId"],
            "runnerNumber": runner["runnerNumber"],
            "runnerName": runner["runnerName"],
            "normalizedRunner": runner["normalizedRunner"],
            "lateSpeed": score,
            "lateSpeedBand": band_from_score(float(score)) if score is not None else None,
            "evidenceRuns": len(evidence),
            "benchmarkedRuns": len(bench_selected),
            "historicalSectionalRuns": speed_counts.get("asof_runs", 0),
            "evidenceRecencyDays": recency,
            "comparableDistanceRuns": comparable_runs,
            "sourceVersion": VERSION,
            "generatedAt": generated_at,
            "joinMethod": join_method,
            "blankReason": reason,
        }
        output_rows.append(row)
        if score is None:
            gap_rows.append(
                {
                    "raceDate": runner["raceDate"],
                    "meeting": runner["meeting"],
                    "raceNumber": runner["raceNumber"],
                    "runnerNumber": runner["runnerNumber"],
                    "runnerName": runner["runnerName"],
                    "blankReason": reason,
                    "benchmarkedRuns": len(bench_selected),
                    "historicalSectionalRuns": speed_counts.get("asof_runs", 0),
                    "comparableDistanceRuns": comparable_runs,
                    "sourceVersion": VERSION,
                }
            )
        for ev in evidence:
            native = ev.get("lateEsi") if "lateEsi" in ev else ev.get("lateRaw")
            evidence_rows.append(
                {
                    "selectedRaceDate": runner["raceDate"],
                    "selectedMeeting": runner["meeting"],
                    "selectedRaceNumber": runner["raceNumber"],
                    "runnerName": runner["runnerName"],
                    "evidenceRaceDate": ev["raceDateText"],
                    "evidenceTrack": ev["track"],
                    "evidenceRaceNo": ev["raceNo"],
                    "evidenceDistance": ev["distance"],
                    "inputField": input_field,
                    "nativeValue": native,
                    "evidenceQuality": ev.get("evidenceQuality", "SPEED_MASTER_LATE_PROFILE"),
                    "benchmarkMode": ev.get("benchmarkMode", ""),
                    "included": "YES",
                    "excludedReason": "",
                    "sourceFile": ev["sourceFile"],
                    "sourceVersion": VERSION,
                    "signConvention": "Negative ESI is faster/inside standard for split_lengths evidence; late_raw is native speed-master higher-is-stronger.",
                    "asOfSafe": "YES" if selected_date and ev["raceDate"] < selected_date else "NO",
                }
            )

    payload = {
        "schemaVersion": "edgeiq_current_late_speed_v1",
        "sourceVersion": VERSION,
        "generatedAt": generated_at,
        "methodology": {
            "inputSources": ["edgeiq_form_sectional_profile_feed_v1.csv:split_lengths", "edgeiq_speed_master_v1.csv:late_raw"],
            "asOfRule": "Only historical rows where historical race_date < selected race date are eligible.",
            "minimumEvidenceRule": f"{MIN_EVIDENCE_RUNS} late-speed observations after as-of filtering.",
            "outputScale": "0-100 strength score where higher means stronger projected late-sectional capability.",
            "normalisation": "Benchmark ESI is converted as 50 - average_late_esi*10; negative ESI therefore increases the score. Native late_raw is already higher-is-stronger and is used only when benchmarked late splits are unavailable.",
            "missingDataTreatment": "Missing segments are ignored, not zero-filled; runners below minimum evidence remain null.",
        },
        "runners": output_rows,
    }
    write_json(OUT_JSON, payload)
    fields = [
        "raceDate",
        "meeting",
        "raceNumber",
        "runnerId",
        "runnerNumber",
        "runnerName",
        "normalizedRunner",
        "lateSpeed",
        "lateSpeedBand",
        "evidenceRuns",
        "benchmarkedRuns",
        "historicalSectionalRuns",
        "evidenceRecencyDays",
        "comparableDistanceRuns",
        "sourceVersion",
        "generatedAt",
        "joinMethod",
        "blankReason",
    ]
    write_csv(OUT_CSV, output_rows, fields)
    write_csv(
        GAP_AUDIT,
        gap_rows,
        ["raceDate", "meeting", "raceNumber", "runnerNumber", "runnerName", "blankReason", "benchmarkedRuns", "historicalSectionalRuns", "comparableDistanceRuns", "sourceVersion"],
    )
    write_csv(
        EVIDENCE_AUDIT,
        evidence_rows,
        ["selectedRaceDate", "selectedMeeting", "selectedRaceNumber", "runnerName", "evidenceRaceDate", "evidenceTrack", "evidenceRaceNo", "evidenceDistance", "inputField", "nativeValue", "evidenceQuality", "benchmarkMode", "included", "excludedReason", "sourceFile", "sourceVersion", "signConvention", "asOfSafe"],
    )
    by_race = group_by_race(output_rows)
    race_lines = []
    for key, rows in sorted(by_race.items()):
        populated = sum(1 for row in rows if row["lateSpeed"] is not None)
        race_lines.append(f"{key}: {populated}/{len(rows)}")
    distribution = stats(scores)
    write_summary(
        COVERAGE,
        [
            "EDGEIQ CURRENT LATE SPEED V1 COVERAGE",
            f"generatedAt={generated_at}",
            f"rows={len(output_rows)}",
            f"populated={len(scores)}",
            f"blank={len(output_rows) - len(scores)}",
            f"distribution={distribution}",
            "gapReasons=" + ", ".join(f"{k}:{v}" for k, v in sorted(reason_counts.items())),
            "",
            "coverageByRace:",
            *race_lines,
            "",
        ],
    )
    print(f"LATE_SPEED_V1 rows={len(output_rows)} populated={len(scores)} blank={len(output_rows)-len(scores)}")
    print(f"LATE_SPEED_V1 distribution={distribution}")


if __name__ == "__main__":
    main()
