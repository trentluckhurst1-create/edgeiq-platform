from __future__ import annotations

from collections import Counter
from typing import Any

from edgeiq_beta_intelligence_v1_common import (
    DATA,
    EARLY_SPEED,
    LATE_SPEED,
    LIVE_BOARD_GOVERNED,
    clean,
    clamp,
    evidence_coverage,
    load_current_projection,
    load_current_runners,
    load_exact_csv,
    load_history_for_current,
    now_utc,
    profile_score,
    round_or_none,
    score_to_band,
    source_rows_for_inventory,
    stats,
    to_float,
    write_csv,
    write_json,
    write_summary,
    asof_history,
)


VERSION = "CURRENT_SUITABILITY_V1"
OUT_JSON = DATA / "edgeiq_current_suitability_v1.json"
OUT_CSV = DATA / "edgeiq_current_suitability_v1.csv"
COVERAGE = DATA / "edgeiq_current_suitability_v1_coverage.csv"
COVERAGE_SUMMARY = DATA / "edgeiq_current_suitability_v1_coverage_summary.txt"
FACTOR_AUDIT = DATA / "edgeiq_current_suitability_v1_factor_audit.csv"
GAP_AUDIT = DATA / "edgeiq_current_suitability_v1_gap_audit.csv"
SOURCE_INVENTORY = DATA / "edgeiq_suitability_v1_source_inventory.csv"
SOURCE_SUMMARY = DATA / "edgeiq_suitability_v1_source_inventory_summary.txt"
ASOF_AUDIT = DATA / "edgeiq_suitability_v1_asof_audit.csv"

MIN_FACTOR_FAMILIES = 4
MIN_HISTORICAL_RUNS = 2


def pct_rank_score(values: list[float], value: float | None) -> float | None:
    if value is None or not values:
        return None
    below = sum(1 for item in values if item <= value)
    return round((below / len(values)) * 100, 1)


def barrier_score(barrier: float | None, field_size: float | None) -> float | None:
    if barrier is None or field_size is None or field_size <= 1:
        return None
    pct = barrier / field_size
    if pct <= 0.25:
        return 66.0
    if pct <= 0.65:
        return 60.0
    return 48.0


def days_score(days: int | None) -> float | None:
    if days is None:
        return None
    if days <= 45:
        return 64.0
    if days <= 90:
        return 56.0
    if days <= 180:
        return 48.0
    return 40.0


def reason_for(name: str, score: float) -> str | None:
    if score < 64:
        return None
    return {
        "distance": "Strong profile at today's distance band.",
        "track": "Track profile supports today's setup.",
        "condition": "Condition profile supports today's track rating.",
        "class": "Class profile is suitable for this race.",
        "earlySpeed": "Current Early Speed projects as a setup asset.",
        "lateSpeed": "Current Late Speed profile is a positive factor.",
        "raceShape": "Projected Race Shape is favourable.",
    }.get(name)


def main() -> None:
    generated_at = now_utc()
    current = load_current_runners()
    histories = load_history_for_current(current)
    early = load_current_projection(EARLY_SPEED, "earlySpeed")
    late = load_current_projection(LATE_SPEED, "lateSpeed")
    race_shape = load_current_projection(DATA / "edgeiq_current_race_shape_v2.json", "raceShape")
    live_board = load_exact_csv(LIVE_BOARD_GOVERNED, "horse")

    inventory = source_rows_for_inventory()
    write_csv(SOURCE_INVENTORY, inventory, list(inventory[0].keys()))
    write_summary(
        SOURCE_SUMMARY,
        [
            "EDGEIQ SUITABILITY V1 SOURCE INVENTORY",
            f"candidate_sources={len(inventory)}",
            "selected_sources=dated historical results; current EPI; current Early Speed V1; current Late Speed V1; current Race Shape V2; barrier context",
            "minimum_evidence=4 independent factor families and 2 dated historical runs",
        ],
    )

    race_epi_values: dict[tuple[str, str, str], list[float]] = {}
    for runner in current:
        epi = to_float(live_board.get(runner["identity"], {}).get("projected_rating_v5_2"))
        if epi is not None:
            race_epi_values.setdefault(runner["raceIdentity"], []).append(epi)

    output: list[dict[str, Any]] = []
    factor_rows: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    asof_rows: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, Any]] = []
    scores: list[float] = []
    gap_counts: Counter = Counter()

    for runner in current:
        history, excluded = asof_history(histories.get(runner["normalizedRunner"], []), runner["raceDate"])
        distance_rows = [row for row in history if row["distanceBand"] and row["distanceBand"] == runner["distanceBand"]]
        track_rows = [row for row in history if row["trackKey"] == runner["meetingKey"]]
        track_distance_rows = [row for row in track_rows if row["distanceBand"] and row["distanceBand"] == runner["distanceBand"]]
        condition_rows = [row for row in history if runner["conditionFamily"] and row["conditionFamily"] == runner["conditionFamily"]]
        class_rows = [row for row in history if runner["classFamily"] and row["classFamily"] == runner["classFamily"]]
        latest = history[0] if history else None
        days_since = None
        if latest:
            selected = next((row for row in current if row is runner), runner)
            from edgeiq_beta_intelligence_v1_common import parse_date
            selected_date = parse_date(selected["raceDate"])
            if selected_date:
                days_since = (selected_date - latest["raceDate"]).days

        early_score = to_float(early.get(runner["identity"], {}).get("earlySpeed"))
        late_score = to_float(late.get(runner["identity"], {}).get("lateSpeed"))
        shape_value = clean(race_shape.get(runner["identity"], {}).get("raceShape"))
        shape_score = {"MAP_ADVANTAGE": 72, "ON_SPEED": 66, "CLOSING_SETUP": 63, "NEUTRAL": 55, "NEEDS_TEMPO": 46, "PRESSURE_RISK": 42}.get(shape_value)
        epi = to_float(live_board.get(runner["identity"], {}).get("projected_rating_v5_2"))
        epi_score = pct_rank_score(race_epi_values.get(runner["raceIdentity"], []), epi)

        factors: list[tuple[str, float | None, int]] = [
            ("distance", profile_score(distance_rows), len(distance_rows)),
            ("track", profile_score(track_rows), len(track_rows)),
            ("trackDistance", profile_score(track_distance_rows), len(track_distance_rows)),
            ("condition", profile_score(condition_rows), len(condition_rows)),
            ("class", profile_score(class_rows), len(class_rows)),
            ("daysSinceRun", days_score(days_since), 1 if days_since is not None else 0),
            ("epi", epi_score, 1 if epi is not None else 0),
            ("earlySpeed", early_score, int(to_float(early.get(runner["identity"], {}).get("evidenceRuns")) or 0)),
            ("lateSpeed", late_score, int(to_float(late.get(runner["identity"], {}).get("evidenceRuns")) or 0)),
            ("raceShape", float(shape_score) if shape_score is not None else None, 1 if shape_value else 0),
            ("barrier", barrier_score(runner.get("barrier"), runner.get("fieldSize")), 1 if runner.get("barrier") is not None else 0),
        ]
        usable = [(name, score, evidence) for name, score, evidence in factors if score is not None]
        available_count = len([item for item in factors if item[2] > 0 or item[1] is not None])
        evidence_runs = len(history)
        score = None
        blank_reason = ""
        if runner["isScratched"]:
            blank_reason = "SCRATCHED"
        elif evidence_runs < MIN_HISTORICAL_RUNS:
            blank_reason = "FIRST_STARTER" if evidence_runs == 0 else "INSUFFICIENT_HISTORICAL_RUNS"
        elif len(usable) < MIN_FACTOR_FAMILIES:
            blank_reason = "INSUFFICIENT_FACTOR_FAMILIES"
        else:
            score = round_or_none(sum(item[1] for item in usable if item[1] is not None) / len(usable), 1)
            if score is not None:
                scores.append(float(score))

        if score is None:
            gap_counts[blank_reason or "OTHER"] += 1
            gaps.append(
                {
                    "raceDate": runner["raceDate"],
                    "meeting": runner["meeting"],
                    "raceNumber": runner["raceNumber"],
                    "runnerNumber": runner["runnerNumber"],
                    "runnerName": runner["runnerName"],
                    "blankReason": blank_reason or "OTHER",
                    "historicalRunsAsOf": evidence_runs,
                    "usableFactorFamilies": len(usable),
                    "availableFactorFamilies": available_count,
                }
            )

        public_reasons: list[str] = []
        for name, factor_score, _evidence in sorted(usable, key=lambda item: item[1] or -999, reverse=True):
            if factor_score is None:
                continue
            reason = reason_for(name, factor_score)
            if reason and reason not in public_reasons:
                public_reasons.append(reason)
            if len(public_reasons) >= 3:
                break

        output.append(
            {
                "raceDate": runner["raceDate"],
                "meeting": runner["meeting"],
                "raceNumber": runner["raceNumber"],
                "runnerId": runner["runnerId"],
                "runnerNumber": runner["runnerNumber"],
                "runnerName": runner["runnerName"],
                "normalizedRunner": runner["normalizedRunner"],
                "suitability": score,
                "suitabilityBand": score_to_band(float(score)) if score is not None else None,
                "evidenceFactorCount": len(usable),
                "availableFactorCount": available_count,
                "evidenceCoverage": evidence_coverage(len(usable), available_count),
                "evidenceRuns": evidence_runs,
                "asOfDate": runner["raceDate"],
                "publicReasons": public_reasons,
                "sourceVersion": VERSION,
                "generatedAt": generated_at,
                "joinMethod": "RUNNER_NAME_STRICT_CURRENT_RACE_PLUS_ASOF_HISTORY" if score is not None else "NO_SCORE",
                "blankReason": blank_reason,
            }
        )
        for name, factor_score, evidence in factors:
            factor_rows.append(
                {
                    "raceDate": runner["raceDate"],
                    "meeting": runner["meeting"],
                    "raceNumber": runner["raceNumber"],
                    "runnerName": runner["runnerName"],
                    "factorFamily": name,
                    "factorPopulated": "YES" if factor_score is not None else "NO",
                    "factorScore": factor_score if factor_score is not None else "",
                    "evidenceCount": evidence,
                    "sourceVersion": VERSION,
                }
            )
        asof_rows.append(
            {
                "raceDate": runner["raceDate"],
                "meeting": runner["meeting"],
                "raceNumber": runner["raceNumber"],
                "runnerName": runner["runnerName"],
                "historicalRowsAsOf": evidence_runs,
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
        grouped[key][1] += 1 if row["suitability"] is not None else 0
    for key, counts in grouped.items():
        coverage_rows.append({"raceDate": key[0], "meeting": key[1], "raceNumber": key[2], "runners": counts[0], "populated": counts[1], "coveragePct": round((counts[1] / counts[0]) * 100, 1) if counts[0] else 0})

    payload = {
        "schemaVersion": "edgeiq_current_suitability_v1",
        "sourceVersion": VERSION,
        "generatedAt": generated_at,
        "methodology": {
            "purpose": "Current-race setup suitability, not EPI or price.",
            "minimumEvidence": f"{MIN_FACTOR_FAMILIES} independent factor families and {MIN_HISTORICAL_RUNS} dated historical runs.",
            "missingData": "Missing factors ignored; not zero-filled.",
            "scoreScale": "0-100 higher is more suitable.",
        },
        "runners": output,
    }
    write_json(OUT_JSON, payload)
    write_csv(OUT_CSV, output, ["raceDate", "meeting", "raceNumber", "runnerId", "runnerNumber", "runnerName", "normalizedRunner", "suitability", "suitabilityBand", "evidenceFactorCount", "availableFactorCount", "evidenceCoverage", "evidenceRuns", "asOfDate", "publicReasons", "sourceVersion", "generatedAt", "joinMethod", "blankReason"])
    write_csv(COVERAGE, coverage_rows, ["raceDate", "meeting", "raceNumber", "runners", "populated", "coveragePct"])
    write_csv(FACTOR_AUDIT, factor_rows)
    write_csv(GAP_AUDIT, gaps)
    write_csv(ASOF_AUDIT, asof_rows)
    s = stats(scores)
    write_summary(
        COVERAGE_SUMMARY,
        [
            "EDGEIQ CURRENT SUITABILITY V1 COVERAGE",
            f"rows={len(output)}",
            f"populated={len(scores)}",
            f"blank={len(output) - len(scores)}",
            f"distribution={s}",
            "gap_counts=" + ", ".join(f"{k}:{v}" for k, v in sorted(gap_counts.items())),
        ],
    )
    print(f"CURRENT_SUITABILITY_V1 rows={len(output)} populated={len(scores)} blank={len(output) - len(scores)}")


if __name__ == "__main__":
    main()
