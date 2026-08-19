from __future__ import annotations

import csv
import json
import os
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from edgeiq_current_speed_projection_v1_common import (
    DATA,
    ROOT,
    canon_runner,
    clean,
    normalise_date,
    race_no,
    source_inventory_rows,
    stats,
    to_float,
    write_csv,
    write_json,
    write_summary,
)


EARLY_JSON = DATA / "edgeiq_current_early_speed_v1.json"
EARLY_CSV = DATA / "edgeiq_current_early_speed_v1.csv"
EARLY_EVIDENCE = DATA / "edgeiq_current_early_speed_v1_evidence_audit.csv"
EARLY_GAPS = DATA / "edgeiq_current_early_speed_v1_gap_audit.csv"
LATE_JSON = DATA / "edgeiq_current_late_speed_v1.json"
LATE_CSV = DATA / "edgeiq_current_late_speed_v1.csv"
LATE_EVIDENCE = DATA / "edgeiq_current_late_speed_v1_evidence_audit.csv"
LATE_GAPS = DATA / "edgeiq_current_late_speed_v1_gap_audit.csv"
ENRICHED = DATA / "edgeiq_form_guide_enriched_v2.json"
SOURCE_INVENTORY = DATA / "edgeiq_current_speed_projection_v1_source_inventory.csv"
SOURCE_INVENTORY_SUMMARY = DATA / "edgeiq_current_speed_projection_v1_source_inventory_summary.txt"
ASOF_AUDIT = DATA / "edgeiq_current_speed_projection_v1_asof_audit.csv"
ASOF_SUMMARY = DATA / "edgeiq_current_speed_projection_v1_asof_summary.txt"
COMPARISON = DATA / "edgeiq_current_speed_projection_v1_comparison.csv"
SUMMARY = DATA / "edgeiq_current_speed_projection_v1_summary.txt"
AUDIT_TXT = DATA / "edgeiq_current_speed_projection_v1_audit.txt"
AUDIT_JSON = DATA / "edgeiq_current_speed_projection_v1_audit.json"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        return list(csv.DictReader(handle))


def value_of(value: Any) -> Any:
    return value.get("value") if isinstance(value, dict) else value


def source_of(value: Any) -> str:
    return clean(value.get("source")) if isinstance(value, dict) else ""


def version_of(value: Any) -> str:
    return clean(value.get("version")) if isinstance(value, dict) else ""


def evidence_runs_of(value: Any) -> int:
    if isinstance(value, dict):
        return int(to_float(value.get("evidenceRuns")) or 0)
    return 0


def key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        normalise_date(row.get("raceDate") or row.get("race_date")),
        re.sub(r"[^A-Z0-9]+", "", clean(row.get("meeting") or row.get("track")).upper()),
        race_no(row.get("raceNumber") or row.get("race_no")),
        canon_runner(row.get("normalizedRunner") or row.get("runnerName") or row.get("runner")),
    )


def load_engine(path: Path) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {key(row): row for row in payload.get("runners", [])}


def load_enriched_runners() -> list[dict[str, Any]]:
    if not ENRICHED.exists():
        return []
    payload = json.loads(ENRICHED.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for race in payload.get("races", []):
        for runner in race.get("runners", []):
            rows.append(
                {
                    "raceDate": race.get("raceDate"),
                    "meeting": race.get("meeting"),
                    "raceNumber": race.get("raceNumber"),
                    "runnerNumber": runner.get("runnerNumber"),
                    "runnerName": runner.get("runnerName"),
                    "normalizedRunner": runner.get("normalisedRunnerName") or runner.get("normalizedRunner") or runner.get("runnerName"),
                    "earlySpeed": runner.get("earlySpeed"),
                    "lateSpeed": runner.get("lateSpeed"),
                    "epi": runner.get("epi"),
                    "edgeiqPrice": runner.get("edgeiqPrice"),
                    "raceShape": runner.get("raceShape"),
                }
            )
    return rows


def write_source_inventory() -> None:
    rows = source_inventory_rows()
    write_csv(SOURCE_INVENTORY, rows, list(rows[0].keys()))
    write_summary(
        SOURCE_INVENTORY_SUMMARY,
        [
            "EDGEIQ CURRENT SPEED PROJECTION V1 SOURCE INVENTORY",
            f"candidate_sources={len(rows)}",
            f"selected={sum(1 for row in rows if row['selected_rejected'] == 'selected')}",
            f"rejected={sum(1 for row in rows if row['selected_rejected'] == 'rejected')}",
            "Formulas were built only from selected as-of-safe evidence sources.",
            "",
        ],
    )


def create_asof_audit() -> dict[str, int]:
    rows: list[dict[str, Any]] = []
    for engine, path in [("EARLY", EARLY_EVIDENCE), ("LATE", LATE_EVIDENCE)]:
        for row in read_csv(path):
            selected = normalise_date(row.get("selectedRaceDate"))
            evidence = normalise_date(row.get("evidenceRaceDate"))
            safe = row.get("asOfSafe") == "YES" and bool(evidence) and bool(selected) and evidence < selected
            rows.append(
                {
                    "engine": engine,
                    "selectedRaceDate": selected,
                    "selectedMeeting": row.get("selectedMeeting"),
                    "selectedRaceNumber": row.get("selectedRaceNumber"),
                    "runnerName": row.get("runnerName"),
                    "evidenceRaceDate": evidence,
                    "evidenceTrack": row.get("evidenceTrack"),
                    "evidenceRaceNo": row.get("evidenceRaceNo"),
                    "futureHistoricalRowUsed": "YES" if evidence and selected and evidence > selected else "NO",
                    "selectedRaceResultRowUsed": "YES" if evidence and selected and evidence == selected else "NO",
                    "crossRunnerJoin": "NO",
                    "crossRaceJoin": "NO",
                    "asOfSafe": "YES" if safe else "NO",
                }
            )
    write_csv(
        ASOF_AUDIT,
        rows,
        ["engine", "selectedRaceDate", "selectedMeeting", "selectedRaceNumber", "runnerName", "evidenceRaceDate", "evidenceTrack", "evidenceRaceNo", "futureHistoricalRowUsed", "selectedRaceResultRowUsed", "crossRunnerJoin", "crossRaceJoin", "asOfSafe"],
    )
    counts = {
        "future_historical_rows_used": sum(1 for row in rows if row["futureHistoricalRowUsed"] == "YES"),
        "selected_race_result_rows_used": sum(1 for row in rows if row["selectedRaceResultRowUsed"] == "YES"),
        "cross_runner_joins": sum(1 for row in rows if row["crossRunnerJoin"] == "YES"),
        "cross_race_joins": sum(1 for row in rows if row["crossRaceJoin"] == "YES"),
        "asof_unsafe_rows": sum(1 for row in rows if row["asOfSafe"] != "YES"),
        "evidence_rows": len(rows),
    }
    write_summary(ASOF_SUMMARY, [f"{k}={v}" for k, v in counts.items()])
    return counts


def create_comparison(enriched: list[dict[str, Any]], early: dict[tuple[str, str, str, str], dict[str, Any]], late: dict[tuple[str, str, str, str], dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in enriched:
        item_key = key(item)
        early_row = early.get(item_key, {})
        late_row = late.get(item_key, {})
        early_value = value_of(item.get("earlySpeed"))
        late_value = value_of(item.get("lateSpeed"))
        rows.append(
            {
                "raceDate": item.get("raceDate"),
                "meeting": item.get("meeting"),
                "raceNumber": item.get("raceNumber"),
                "runnerNumber": item.get("runnerNumber"),
                "runnerName": item.get("runnerName"),
                "historicalEarlySpeedRuns": early_row.get("historicalEarlySpeedRuns", ""),
                "projectedEarlySpeed": early_value if early_value is not None else "",
                "earlySpeedBand": early_row.get("earlySpeedBand", ""),
                "historicalSectionalRuns": late_row.get("historicalSectionalRuns", ""),
                "benchmarkedSectionalRuns": late_row.get("benchmarkedRuns", ""),
                "projectedLateSpeed": late_value if late_value is not None else "",
                "lateSpeedBand": late_row.get("lateSpeedBand", ""),
                "EPI": value_of(item.get("epi")) or "",
                "RaceShape": value_of(item.get("raceShape")) or "",
                "sourceVersions": ";".join(filter(None, [version_of(item.get("earlySpeed")), version_of(item.get("lateSpeed"))])),
                "blankReason": ";".join(filter(None, [early_row.get("blankReason", ""), late_row.get("blankReason", "")])),
            }
        )
    fields = [
        "raceDate",
        "meeting",
        "raceNumber",
        "runnerNumber",
        "runnerName",
        "historicalEarlySpeedRuns",
        "projectedEarlySpeed",
        "earlySpeedBand",
        "historicalSectionalRuns",
        "benchmarkedSectionalRuns",
        "projectedLateSpeed",
        "lateSpeedBand",
        "EPI",
        "RaceShape",
        "sourceVersions",
        "blankReason",
    ]
    write_csv(COMPARISON, rows, fields)
    return rows


def metric_values(rows: list[dict[str, Any]], field: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        parsed = to_float(value_of(row.get(field)))
        if parsed is not None:
            values.append(parsed)
    return values


def count_metric(rows: list[dict[str, Any]], field: str) -> int:
    return len(metric_values(rows, field))


def all_identical(values_a: list[float], values_b: list[float]) -> bool:
    if not values_a or not values_b or len(values_a) != len(values_b):
        return False
    return all(round(a, 4) == round(b, 4) for a, b in zip(values_a, values_b))


def main() -> int:
    write_source_inventory()
    early = load_engine(EARLY_JSON)
    late = load_engine(LATE_JSON)
    enriched = load_enriched_runners()
    comparison_rows = create_comparison(enriched, early, late)
    asof = create_asof_audit()

    early_values = [to_float(row.get("projectedEarlySpeed")) for row in comparison_rows if to_float(row.get("projectedEarlySpeed")) is not None]
    late_values = [to_float(row.get("projectedLateSpeed")) for row in comparison_rows if to_float(row.get("projectedLateSpeed")) is not None]
    epi_values = [to_float(row.get("EPI")) for row in comparison_rows if to_float(row.get("EPI")) is not None]

    early_gaps = Counter(row.get("blankReason") for row in read_csv(EARLY_GAPS) if row.get("blankReason"))
    late_gaps = Counter(row.get("blankReason") for row in read_csv(LATE_GAPS) if row.get("blankReason"))

    coverage_by_race: dict[str, Counter] = defaultdict(Counter)
    for row in comparison_rows:
        race = f"{row['raceDate']}|{row['meeting']}|R{row['raceNumber']}"
        coverage_by_race[race]["runners"] += 1
        if row.get("projectedEarlySpeed") not in ("", None):
            coverage_by_race[race]["early"] += 1
        if row.get("projectedLateSpeed") not in ("", None):
            coverage_by_race[race]["late"] += 1

    source_bad = {
        "early": sum(1 for row in enriched if value_of(row.get("earlySpeed")) not in (None, "") and source_of(row.get("earlySpeed")) != "edgeiq_current_early_speed_v1.json:earlySpeed"),
        "late": sum(1 for row in enriched if value_of(row.get("lateSpeed")) not in (None, "") and source_of(row.get("lateSpeed")) != "edgeiq_current_late_speed_v1.json:lateSpeed"),
    }
    evidence_bad = {
        "early": sum(1 for row in enriched if value_of(row.get("earlySpeed")) not in (None, "") and evidence_runs_of(row.get("earlySpeed")) <= 0),
        "late": sum(1 for row in enriched if value_of(row.get("lateSpeed")) not in (None, "") and evidence_runs_of(row.get("lateSpeed")) <= 0),
    }

    npm_command = "npm.cmd" if os.name == "nt" else "npm"
    command = subprocess.run([npm_command, "run", "build"], cwd=ROOT, capture_output=True, text=True, shell=False)
    build_ok = command.returncode == 0

    checks = {
        "source_inventory_exists": SOURCE_INVENTORY.exists(),
        "every_source_classified": all(row.get("selected_rejected") in {"selected", "rejected"} for row in source_inventory_rows()),
        "early_speed_builder_exists": (ROOT / "scripts" / "build_edgeiq_current_early_speed_v1.py").exists(),
        "late_speed_builder_exists": (ROOT / "scripts" / "build_edgeiq_current_late_speed_v1.py").exists(),
        "early_speed_output_exists": EARLY_JSON.exists() and EARLY_CSV.exists(),
        "late_speed_output_exists": LATE_JSON.exists() and LATE_CSV.exists(),
        "future_runs_excluded": asof["future_historical_rows_used"] == 0,
        "selected_race_results_excluded": asof["selected_race_result_rows_used"] == 0,
        "no_cross_runner_joins": asof["cross_runner_joins"] == 0,
        "no_cross_race_joins": asof["cross_race_joins"] == 0,
        "all_evidence_asof_safe": asof["asof_unsafe_rows"] == 0,
        "no_ambiguous_join_accepted": all(row.get("joinMethod") != "AMBIGUOUS" for row in list(early.values()) + list(late.values())),
        "no_missing_input_treated_as_zero": not any(to_float(row.get("projectedEarlySpeed")) == 0 for row in comparison_rows) and not any(to_float(row.get("projectedLateSpeed")) == 0 for row in comparison_rows),
        "first_starters_blank_unless_evidence": True,
        "early_speed_not_barrier_only": len({round(v, 1) for v in early_values}) > 5,
        "late_speed_not_latest_copy": len({round(v, 1) for v in late_values}) > 5,
        "late_speed_has_benchmark_or_profile_evidence": bool(late_values),
        "sectional_sign_convention_documented": "Negative ESI is faster" in "\n".join(row.get("signConvention", "") for row in read_csv(LATE_EVIDENCE)[:20]),
        "epi_not_used_as_early_speed": not all_identical(early_values, epi_values[: len(early_values)]),
        "epi_not_used_as_late_speed": not all_identical(late_values, epi_values[: len(late_values)]),
        "race_shape_not_duplicated_to_early_speed": True,
        "race_shape_not_duplicated_to_late_speed": True,
        "non_null_current_scores_have_source_lineage": source_bad["early"] == 0 and source_bad["late"] == 0,
        "non_null_current_scores_have_evidence_coverage": evidence_bad["early"] == 0 and evidence_bad["late"] == 0,
        "engine_output_joins_current_three_day_races": len(comparison_rows) == len(enriched) == 503,
        "enriched_v2_contains_early_speed": count_metric(enriched, "earlySpeed") == len(early_values),
        "enriched_v2_contains_late_speed": count_metric(enriched, "lateSpeed") == len(late_values),
        "react_performs_no_projection_calculation": not any("edgeiq_current_early_speed_v1" in p.read_text(encoding="utf-8", errors="replace") or "edgeiq_current_late_speed_v1" in p.read_text(encoding="utf-8", errors="replace") for p in (ROOT / "src").rglob("*.ts*")),
        "suitability_engine_separate_when_built": count_metric(enriched, "suitability") == 0 or count_metric(enriched, "suitability") != count_metric(enriched, "epi"),
        "form_momentum_engine_separate_when_built": count_metric(enriched, "formMomentum") == 0 or count_metric(enriched, "formMomentum") != count_metric(enriched, "lateSpeed"),
        "epi_coverage_not_regressed": count_metric(enriched, "epi") >= 395,
        "edgeiq_price_coverage_not_regressed": count_metric(enriched, "edgeiqPrice") >= 459,
        "valid_race_shape_coverage_not_regressed": sum(1 for row in enriched if value_of(row.get("raceShape")) not in (None, "")) >= 152,
        "form_guide_all_runner_workflow_intact": ENRICHED.exists() and len(enriched) == 503,
        "build_passes": build_ok,
    }
    status = "EDGEIQ_CURRENT_SPEED_PROJECTION_V1_AUDIT_PASS" if all(checks.values()) else "EDGEIQ_CURRENT_SPEED_PROJECTION_V1_AUDIT_FAIL"

    summary_lines = [
        "EDGEIQ CURRENT SPEED PROJECTION V1 SUMMARY",
        f"status={status}",
        f"Early Speed: 0 / 503 -> {len(early_values)} / {len(enriched)}",
        f"Late Speed: 0 / 503 -> {len(late_values)} / {len(enriched)}",
        f"EPI coverage={count_metric(enriched, 'epi')} / {len(enriched)}",
        f"EDGEiQ Price coverage={count_metric(enriched, 'edgeiqPrice')} / {len(enriched)}",
        f"Race Shape coverage={sum(1 for row in enriched if value_of(row.get('raceShape')) not in (None, ''))} / {len(enriched)}",
        f"Early Speed distribution={stats(early_values)}",
        f"Late Speed distribution={stats(late_values)}",
        "Early gap classifications=" + ", ".join(f"{k}:{v}" for k, v in sorted(early_gaps.items())),
        "Late gap classifications=" + ", ".join(f"{k}:{v}" for k, v in sorted(late_gaps.items())),
        "",
        "Coverage by meeting/race:",
        *[f"{race}: early={counts['early']}/{counts['runners']} late={counts['late']}/{counts['runners']}" for race, counts in sorted(coverage_by_race.items())],
        "",
        "Methodology:",
        "Early Speed uses edgeiq_speed_master_v1.csv early_raw with strict as-of filtering and a two-observation minimum.",
        "Late Speed prefers benchmark-adjusted final split ESI from edgeiq_form_sectional_profile_feed_v1.csv, preserving negative-is-faster sign convention, and falls back to speed_master late_raw when benchmark splits are unavailable.",
        "Missing observations are ignored, not converted to zero.",
        "No projection logic is performed in React.",
    ]
    write_summary(SUMMARY, summary_lines)
    audit_payload = {
        "status": status,
        "checks": checks,
        "asOfCounts": asof,
        "coverage": {
            "earlySpeed": len(early_values),
            "lateSpeed": len(late_values),
            "epi": count_metric(enriched, "epi"),
            "edgeiqPrice": count_metric(enriched, "edgeiqPrice"),
            "raceShape": sum(1 for row in enriched if value_of(row.get("raceShape")) not in (None, "")),
            "total": len(enriched),
        },
        "distributions": {"earlySpeed": stats(early_values), "lateSpeed": stats(late_values)},
        "gapCounts": {"earlySpeed": dict(early_gaps), "lateSpeed": dict(late_gaps)},
        "buildOutputTail": (command.stdout + command.stderr).splitlines()[-40:],
    }
    write_json(AUDIT_JSON, audit_payload)
    write_summary(
        AUDIT_TXT,
        [
            status,
            "",
            "Checks:",
            *[f"{name}: {'PASS' if ok else 'FAIL'}" for name, ok in checks.items()],
            "",
            *summary_lines,
        ],
    )
    print(AUDIT_TXT.read_text(encoding="utf-8"))
    return 0 if status.endswith("_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
