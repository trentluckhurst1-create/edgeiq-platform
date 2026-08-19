from __future__ import annotations

from collections import Counter
from typing import Any

from edgeiq_beta_intelligence_v1_common import (
    DATA,
    asof_history,
    clean,
    load_current_runners,
    load_history_for_current,
    momentum_band,
    now_utc,
    round_or_none,
    source_rows_for_inventory,
    stats,
    to_float,
    write_csv,
    write_json,
    write_summary,
)


VERSION = "CURRENT_FORM_MOMENTUM_V1"
OUT_JSON = DATA / "edgeiq_current_form_momentum_v1.json"
OUT_CSV = DATA / "edgeiq_current_form_momentum_v1.csv"
COVERAGE = DATA / "edgeiq_current_form_momentum_v1_coverage.csv"
COVERAGE_SUMMARY = DATA / "edgeiq_current_form_momentum_v1_coverage_summary.txt"
EVIDENCE_AUDIT = DATA / "edgeiq_current_form_momentum_v1_evidence_audit.csv"
GAP_AUDIT = DATA / "edgeiq_current_form_momentum_v1_gap_audit.csv"
SOURCE_INVENTORY = DATA / "edgeiq_form_momentum_v1_source_inventory.csv"
SOURCE_SUMMARY = DATA / "edgeiq_form_momentum_v1_source_inventory_summary.txt"
ASOF_AUDIT = DATA / "edgeiq_form_momentum_v1_asof_audit.csv"

MIN_RUNS = 3
MIN_NUMERIC_EVIDENCE = 2


def evidence_value(row: dict[str, Any]) -> tuple[float | None, str]:
    epi = to_float(row.get("epiPost"))
    if epi is not None:
        return epi, "epi_post"
    finish_len = to_float(row.get("finishLen"))
    if finish_len is not None:
        return 50 - finish_len * 6, "benchmark_finish_len"
    margin = to_float(row.get("margin"))
    if margin is not None:
        return 58 - min(12, max(0, margin)) * 2.6, "margin"
    return None, ""


def project_momentum(rows: list[dict[str, Any]]) -> tuple[float | None, list[dict[str, Any]], str]:
    window = rows[:5]
    evidence: list[dict[str, Any]] = []
    for row in window:
        value, source = evidence_value(row)
        if value is not None:
            evidence.append({**row, "momentumValue": value, "momentumSource": source})
    if len(rows) < MIN_RUNS:
        return None, evidence, "INSUFFICIENT_HISTORICAL_RUNS"
    if len(evidence) < MIN_NUMERIC_EVIDENCE:
        return None, evidence, "NO_APPROVED_TRAJECTORY_EVIDENCE"
    if len(evidence) < 3:
        return None, evidence, "INSUFFICIENT_COMPARABLE_RUNS"
    recent = evidence[:2]
    older = evidence[2:5]
    if not older:
        return None, evidence, "INSUFFICIENT_COMPARABLE_RUNS"
    recent_avg = sum(row["momentumValue"] for row in recent) / len(recent)
    older_avg = sum(row["momentumValue"] for row in older) / len(older)
    raw = (recent_avg - older_avg) / 4.0
    if evidence[0].get("raceDate") and evidence[-1].get("raceDate"):
        # Keep the public scale compact; this is a trajectory indicator, not a rating.
        raw = max(-8.0, min(8.0, raw))
    return round(raw, 1), evidence, ""


def reasons(score: float | None, evidence: list[dict[str, Any]]) -> list[str]:
    if score is None:
        return []
    out: list[str] = []
    sources = {row.get("momentumSource") for row in evidence}
    if "epi_post" in sources:
        out.append("Recent EPI trajectory is included.")
    if "benchmark_finish_len" in sources:
        out.append("Benchmark-adjusted sectional evidence is included.")
    if "margin" in sources:
        out.append("Recent beaten-margin trajectory is included.")
    direction, _band = momentum_band(score)
    if direction == "IMPROVING":
        out.insert(0, "Recent performance trajectory is improving.")
    elif direction == "DECLINING":
        out.insert(0, "Recent performance trajectory is declining.")
    else:
        out.insert(0, "Recent performance trajectory is holding.")
    return out[:3]


def main() -> None:
    generated_at = now_utc()
    current = load_current_runners()
    histories = load_history_for_current(current)
    inventory = [row for row in source_rows_for_inventory() if "results_master" in row["source_file"] or "current_early" not in row["source_file"]]
    write_csv(SOURCE_INVENTORY, inventory, list(inventory[0].keys()))
    write_summary(
        SOURCE_SUMMARY,
        [
            "EDGEIQ FORM MOMENTUM V1 SOURCE INVENTORY",
            "selected_sources=dated historical results: epi_post, benchmark finish length, beaten margin",
            f"minimum_runs={MIN_RUNS}",
            f"minimum_numeric_evidence={MIN_NUMERIC_EVIDENCE}",
            "as_of_rule=historical race_date must be strictly less than selected race date",
        ],
    )

    output: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    gap_rows: list[dict[str, Any]] = []
    asof_rows: list[dict[str, Any]] = []
    scores: list[float] = []
    gap_counts: Counter = Counter()

    for runner in current:
        history, excluded = asof_history(histories.get(runner["normalizedRunner"], []), runner["raceDate"])
        score, evidence, blank_reason = project_momentum(history)
        if runner["isScratched"]:
            score = None
            blank_reason = "SCRATCHED"
            evidence = []
        direction, band = momentum_band(score)
        if score is not None:
            scores.append(float(score))
        else:
            gap_counts[blank_reason or "OTHER"] += 1
            gap_rows.append(
                {
                    "raceDate": runner["raceDate"],
                    "meeting": runner["meeting"],
                    "raceNumber": runner["raceNumber"],
                    "runnerNumber": runner["runnerNumber"],
                    "runnerName": runner["runnerName"],
                    "blankReason": blank_reason or "OTHER",
                    "historicalRunsAsOf": len(history),
                    "numericEvidenceRuns": len(evidence),
                }
            )

        recency = None
        if evidence:
            from edgeiq_beta_intelligence_v1_common import parse_date
            selected_date = parse_date(runner["raceDate"])
            if selected_date:
                recency = (selected_date - evidence[0]["raceDate"]).days
        output.append(
            {
                "raceDate": runner["raceDate"],
                "meeting": runner["meeting"],
                "raceNumber": runner["raceNumber"],
                "runnerId": runner["runnerId"],
                "runnerNumber": runner["runnerNumber"],
                "runnerName": runner["runnerName"],
                "normalizedRunner": runner["normalizedRunner"],
                "formMomentum": score,
                "formMomentumBand": band,
                "direction": direction,
                "evidenceRuns": len(evidence),
                "comparableRuns": len(evidence),
                "evidenceCoverage": round((len(evidence) / 5) * 100, 1) if evidence else None,
                "evidenceRecencyDays": recency,
                "publicReasons": reasons(score, evidence),
                "sourceVersion": VERSION,
                "generatedAt": generated_at,
                "joinMethod": "RUNNER_NAME_ASOF_TRAJECTORY" if score is not None else "NO_SCORE",
                "blankReason": blank_reason,
            }
        )
        for item in evidence:
            evidence_rows.append(
                {
                    "selectedRaceDate": runner["raceDate"],
                    "meeting": runner["meeting"],
                    "raceNumber": runner["raceNumber"],
                    "runnerName": runner["runnerName"],
                    "evidenceRaceDate": item["raceDateText"],
                    "evidenceTrack": item["track"],
                    "evidenceRaceNo": item["raceNo"],
                    "evidenceSource": item["momentumSource"],
                    "evidenceValue": round(item["momentumValue"], 3),
                    "asOfSafe": "YES",
                }
            )
        asof_rows.append(
            {
                "raceDate": runner["raceDate"],
                "meeting": runner["meeting"],
                "raceNumber": runner["raceNumber"],
                "runnerName": runner["runnerName"],
                "historicalRowsAsOf": len(history),
                "futureOrSelectedRowsExcluded": excluded,
                "futureRowsUsed": 0,
                "selectedRaceOutcomeRowsUsed": 0,
                "crossRunnerJoins": 0,
                "crossRaceJoins": 0,
                "ambiguousAcceptedJoins": 0,
            }
        )

    grouped = {}
    for row in output:
        key = (row["raceDate"], row["meeting"], row["raceNumber"])
        grouped.setdefault(key, [0, 0])
        grouped[key][0] += 1
        grouped[key][1] += 1 if row["formMomentum"] is not None else 0
    for key, counts in grouped.items():
        coverage_rows.append({"raceDate": key[0], "meeting": key[1], "raceNumber": key[2], "runners": counts[0], "populated": counts[1], "coveragePct": round((counts[1] / counts[0]) * 100, 1) if counts[0] else 0})

    payload = {
        "schemaVersion": "edgeiq_current_form_momentum_v1",
        "sourceVersion": VERSION,
        "generatedAt": generated_at,
        "methodology": {
            "definition": "Point-in-time current performance trajectory.",
            "minimumEvidence": f"{MIN_RUNS} historical runs and {MIN_NUMERIC_EVIDENCE} numeric EPI/sectional/margin evidence points.",
            "outputScale": "Centred around zero; positive improving, negative declining.",
            "exclusions": "Not finish-position-only and not current EPI.",
        },
        "runners": output,
    }
    write_json(OUT_JSON, payload)
    write_csv(OUT_CSV, output, ["raceDate", "meeting", "raceNumber", "runnerId", "runnerNumber", "runnerName", "normalizedRunner", "formMomentum", "formMomentumBand", "direction", "evidenceRuns", "comparableRuns", "evidenceCoverage", "evidenceRecencyDays", "publicReasons", "sourceVersion", "generatedAt", "joinMethod", "blankReason"])
    write_csv(COVERAGE, coverage_rows, ["raceDate", "meeting", "raceNumber", "runners", "populated", "coveragePct"])
    write_csv(EVIDENCE_AUDIT, evidence_rows)
    write_csv(GAP_AUDIT, gap_rows)
    write_csv(ASOF_AUDIT, asof_rows)
    s = stats(scores)
    write_summary(
        COVERAGE_SUMMARY,
        [
            "EDGEIQ CURRENT FORM MOMENTUM V1 COVERAGE",
            f"rows={len(output)}",
            f"populated={len(scores)}",
            f"blank={len(output) - len(scores)}",
            f"distribution={s}",
            "gap_counts=" + ", ".join(f"{k}:{v}" for k, v in sorted(gap_counts.items())),
        ],
    )
    print(f"CURRENT_FORM_MOMENTUM_V1 rows={len(output)} populated={len(scores)} blank={len(output) - len(scores)}")


if __name__ == "__main__":
    main()
