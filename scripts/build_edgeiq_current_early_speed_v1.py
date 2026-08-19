from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from edgeiq_current_speed_projection_v1_common import (
    DATA,
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
    source_inventory_rows,
    stats,
    to_float,
    write_csv,
    write_json,
    write_summary,
)


OUT_JSON = DATA / "edgeiq_current_early_speed_v1.json"
OUT_CSV = DATA / "edgeiq_current_early_speed_v1.csv"
COVERAGE = DATA / "edgeiq_current_early_speed_v1_coverage.txt"
GAP_AUDIT = DATA / "edgeiq_current_early_speed_v1_gap_audit.csv"
EVIDENCE_AUDIT = DATA / "edgeiq_current_early_speed_v1_evidence_audit.csv"
SOURCE_INVENTORY = DATA / "edgeiq_current_speed_projection_v1_source_inventory.csv"
SOURCE_INVENTORY_SUMMARY = DATA / "edgeiq_current_speed_projection_v1_source_inventory_summary.txt"

VERSION = "CURRENT_EARLY_SPEED_V1"
MIN_EVIDENCE_RUNS = 2


def write_source_inventory() -> None:
    rows = source_inventory_rows()
    write_csv(SOURCE_INVENTORY, rows, list(rows[0].keys()))
    write_summary(
        SOURCE_INVENTORY_SUMMARY,
        [
            "EDGEIQ CURRENT SPEED PROJECTION V1 SOURCE INVENTORY",
            f"candidate_sources={len(rows)}",
            "selected_sources=edgeiq_speed_master_v1.csv early_raw; edgeiq_speed_master_v1.csv late_raw; edgeiq_form_sectional_profile_feed_v1.csv split_lengths; edgeiq_runner_profile_stats_v1.csv gap classification only",
            "rejected_direct_sources=live_speed_map_v3.csv late_power_index; edgeiq_current_field_projection_v5_2.csv EPI; sectional finish_len as late-specific score",
            "as_of_rule=historical race_date must be strictly less than selected race date",
            "",
        ],
    )


def speed_rows_for_current(current_names: set[str]) -> dict[str, list[dict[str, Any]]]:
    rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if not SPEED_MASTER.exists():
        return rows
    with SPEED_MASTER.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        for row in csv.DictReader(handle):
            runner_key = canon_runner(row.get("normalized_runner") or row.get("runner"))
            if runner_key not in current_names:
                continue
            row_date = parse_date(row.get("race_date"))
            early = to_float(row.get("early_raw"))
            if row_date is None:
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
                    "earlyRaw": early,
                    "sourceFile": "edgeiq_speed_master_v1.csv",
                }
            )
    for bucket in rows.values():
        bucket.sort(key=lambda item: item["raceDate"], reverse=True)
    return rows


def select_evidence(history: list[dict[str, Any]], race_date: date, distance: float | None) -> tuple[list[dict[str, Any]], str, Counter]:
    counters: Counter = Counter()
    asof = [row for row in history if row["raceDate"] < race_date]
    counters["historical_runs_asof"] = len(asof)
    future = [row for row in history if row["raceDate"] >= race_date]
    counters["future_or_selected_excluded"] = len(future)
    scored = [row for row in asof if row.get("earlyRaw") is not None]
    counters["early_speed_observations"] = len(scored)
    if distance is not None:
        comparable = [row for row in scored if row.get("distance") is not None and abs(float(row["distance"]) - distance) <= 400]
    else:
        comparable = []
    counters["comparable_distance_runs"] = len(comparable)
    selected = comparable if comparable else scored
    selected = selected[:8]
    method = "RUNNER_NAME_ASOF_COMPARABLE_DISTANCE" if comparable else "RUNNER_NAME_ASOF_BROADER_HISTORY"
    return selected, method, counters


def project_score(evidence: list[dict[str, Any]]) -> float | None:
    values = [float(row["earlyRaw"]) for row in evidence if row.get("earlyRaw") is not None]
    if len(values) < MIN_EVIDENCE_RUNS:
        return None
    return clamp(sum(values) / len(values))


def main() -> None:
    generated_at = now_utc()
    write_source_inventory()
    current = load_current_runners()
    profile_starts = load_profile_starts()
    histories = speed_rows_for_current({row["normalizedRunner"] for row in current})
    output_rows: list[dict[str, Any]] = []
    gap_rows: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    scores: list[float] = []
    reason_counts: Counter = Counter()

    for runner in current:
        selected_date = parse_date(runner["raceDate"])
        history = histories.get(runner["normalizedRunner"], [])
        if selected_date is None:
            evidence = []
            method = "NO_SELECTED_RACE_DATE"
            counters = Counter()
        else:
            evidence, method, counters = select_evidence(history, selected_date, runner.get("distance"))

        score = round_or_none(project_score(evidence), 1)
        if score is not None:
            scores.append(float(score))

        if score is None:
            starts = profile_starts.get(runner["normalizedRunner"], 0)
            if starts == 0 and counters.get("historical_runs_asof", 0) == 0:
                reason = "FIRST_STARTER"
            elif counters.get("historical_runs_asof", 0) == 0:
                reason = "NO_ASOF_EVIDENCE"
            elif counters.get("early_speed_observations", 0) == 0:
                reason = "NO_HISTORICAL_EARLY_SPEED"
            elif counters.get("early_speed_observations", 0) < MIN_EVIDENCE_RUNS:
                reason = "INSUFFICIENT_RUNS"
            else:
                reason = "OTHER"
            reason_counts[reason] += 1
        else:
            reason = ""

        recency = None
        if evidence and selected_date:
            recency = (selected_date - evidence[0]["raceDate"]).days
        coverage = round(min(100, (len(evidence) / 5) * 100), 1) if evidence else None
        row = {
            "raceDate": runner["raceDate"],
            "meeting": runner["meeting"],
            "raceNumber": runner["raceNumber"],
            "runnerId": runner["runnerId"],
            "runnerNumber": runner["runnerNumber"],
            "runnerName": runner["runnerName"],
            "normalizedRunner": runner["normalizedRunner"],
            "earlySpeed": score,
            "earlySpeedBand": band_from_score(float(score)) if score is not None else None,
            "evidenceRuns": len(evidence),
            "historicalEarlySpeedRuns": counters.get("early_speed_observations", 0),
            "evidenceRecencyDays": recency,
            "evidenceCoverage": coverage,
            "sourceVersion": VERSION,
            "generatedAt": generated_at,
            "joinMethod": method,
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
                    "historicalRunsAsOf": counters.get("historical_runs_asof", 0),
                    "earlySpeedObservations": counters.get("early_speed_observations", 0),
                    "futureOrSelectedRowsExcluded": counters.get("future_or_selected_excluded", 0),
                    "sourceVersion": VERSION,
                }
            )
        for ev in evidence:
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
                    "inputField": "early_raw",
                    "nativeValue": ev["earlyRaw"],
                    "included": "YES",
                    "excludedReason": "",
                    "sourceFile": ev["sourceFile"],
                    "sourceVersion": VERSION,
                    "asOfSafe": "YES" if selected_date and ev["raceDate"] < selected_date else "NO",
                }
            )

    payload = {
        "schemaVersion": "edgeiq_current_early_speed_v1",
        "sourceVersion": VERSION,
        "generatedAt": generated_at,
        "methodology": {
            "inputSources": ["edgeiq_speed_master_v1.csv:early_raw", "edgeiq_runner_profile_stats_v1.csv:career_starts for gap classification"],
            "asOfRule": "Only historical rows where historical race_date < selected race date are eligible.",
            "minimumEvidenceRule": f"{MIN_EVIDENCE_RUNS} historical early-speed observations after as-of filtering.",
            "outputScale": "Native speed-master public 0-100 style score; higher means stronger projected early-position speed.",
            "projection": "Average of up to eight most recent comparable-distance observations when available, otherwise broader as-of history.",
            "missingDataTreatment": "Missing observations are ignored, not converted to zero; runners below minimum evidence remain null.",
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
        "earlySpeed",
        "earlySpeedBand",
        "evidenceRuns",
        "historicalEarlySpeedRuns",
        "evidenceRecencyDays",
        "evidenceCoverage",
        "sourceVersion",
        "generatedAt",
        "joinMethod",
        "blankReason",
    ]
    write_csv(OUT_CSV, output_rows, fields)
    write_csv(
        GAP_AUDIT,
        gap_rows,
        ["raceDate", "meeting", "raceNumber", "runnerNumber", "runnerName", "blankReason", "historicalRunsAsOf", "earlySpeedObservations", "futureOrSelectedRowsExcluded", "sourceVersion"],
    )
    write_csv(
        EVIDENCE_AUDIT,
        evidence_rows,
        ["selectedRaceDate", "selectedMeeting", "selectedRaceNumber", "runnerName", "evidenceRaceDate", "evidenceTrack", "evidenceRaceNo", "evidenceDistance", "inputField", "nativeValue", "included", "excludedReason", "sourceFile", "sourceVersion", "asOfSafe"],
    )
    by_race = group_by_race(output_rows)
    race_lines = []
    for key, rows in sorted(by_race.items()):
        populated = sum(1 for row in rows if row["earlySpeed"] is not None)
        race_lines.append(f"{key}: {populated}/{len(rows)}")
    populated_total = len(scores)
    distribution = stats(scores)
    write_summary(
        COVERAGE,
        [
            "EDGEIQ CURRENT EARLY SPEED V1 COVERAGE",
            f"generatedAt={generated_at}",
            f"rows={len(output_rows)}",
            f"populated={populated_total}",
            f"blank={len(output_rows) - populated_total}",
            f"distribution={distribution}",
            "gapReasons=" + ", ".join(f"{k}:{v}" for k, v in sorted(reason_counts.items())),
            "",
            "coverageByRace:",
            *race_lines,
            "",
        ],
    )
    print(f"EARLY_SPEED_V1 rows={len(output_rows)} populated={populated_total} blank={len(output_rows)-populated_total}")
    print(f"EARLY_SPEED_V1 distribution={distribution}")


if __name__ == "__main__":
    main()
