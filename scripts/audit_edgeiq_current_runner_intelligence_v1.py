from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from edgeiq_three_day_window_v1_common import build_three_day_window

csv.field_size_limit(1024 * 1024 * 256)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "operations-readiness" / "current-runner-intelligence"

FORM_GUIDE_JSON = DATA / "edgeiq_form_guide_enriched_v2.json"
FORM_GUIDE_CSV = DATA / "edgeiq_form_guide_enriched_v2.csv"
RACE_FIELDS = DATA / "race_fields.csv"
LIVE_TERMINAL = DATA / "edgeiq_live_terminal_feed_v1.csv"
EPI_JSON = DATA / "edgeiq_epi_current_rating_v1.json"
FAIR_PRICE = DATA / "edgeiq_fair_price_v7_2.csv"
EARLY_SPEED_JSON = DATA / "edgeiq_current_early_speed_v1.json"
EARLY_SPEED_CSV = DATA / "edgeiq_current_early_speed_v1.csv"
LATE_SPEED_JSON = DATA / "edgeiq_current_late_speed_v1.json"
LATE_SPEED_CSV = DATA / "edgeiq_current_late_speed_v1.csv"
SUITABILITY = DATA / "edgeiq_current_suitability_v1.csv"
FORM_MOMENTUM = DATA / "edgeiq_current_form_momentum_v1.csv"
RACE_ENTRY = DATA / "edgeiq_race_entry_fact_v1.csv"
RACE_ENTRY_REJECTED = DATA / "edgeiq_race_entry_fact_v1_rejected_v1.csv"
HISTORICAL_RUN_INTELLIGENCE = DATA / "edgeiq_historical_run_intelligence_fact_v1.csv"
HISTORICAL_EPI = ROOT / "docs" / "performance-intelligence" / "epi" / "edgeiq_epi_performance_fact_v1.csv"
POSITION_SOURCE = HISTORICAL_RUN_INTELLIGENCE
REACT_FORM_GUIDE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceFormGuideWorkspace.tsx"
REACT_NORMALISER = ROOT / "src" / "edgeiq-os" / "race" / "services" / "formGuideNormaliser.ts"

ROW_AUDIT = DATA / "edgeiq_current_runner_intelligence_audit_v1.csv"
SUMMARY_JSON = DATA / "edgeiq_current_runner_intelligence_audit_v1.json"
STAGE_TRACE = DATA / "edgeiq_current_runner_intelligence_stage_trace_v1.csv"
CAULFIELD_G2_AUDIT = DATA / "edgeiq_current_runner_intelligence_caulfield_g2_audit_v1.csv"

ALLOWED_MISSING_CLASSES = {
    "LEGITIMATE_NO_HISTORY",
    "LEGITIMATE_FIRST_STARTER",
    "LEGITIMATE_INSUFFICIENT_HISTORY",
    "SCRATCHED",
    "SOURCE_DATA_UNAVAILABLE",
    "PIPELINE_FAILURE",
    "JOIN_FAILURE",
    "TEMPORAL_ELIGIBILITY_FAILURE",
    "UNKNOWN_ERROR",
}

BLOCKING_CLASSES = {
    "PIPELINE_FAILURE",
    "JOIN_FAILURE",
    "TEMPORAL_ELIGIBILITY_FAILURE",
    "UNKNOWN_ERROR",
}


def clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"", "none", "null", "nan", "n/a", "na", "-"} else text


def norm_name(value: Any) -> str:
    text = clean(value).upper()
    for token in ("'", "\u2019", "`"):
        text = text.replace(token, "")
    return "".join(ch for ch in text if ch.isalnum())


def norm_track(value: Any) -> str:
    text = clean(value).upper()
    for token in ("BET365", "SPORTSBET", "LADBROKES", "PICKLEBET", "PARK", "SOUTHSIDE", "THE", "RACECOURSE", "RACING", "TRACK"):
        text = text.replace(token, " ")
    return "".join(ch for ch in text if ch.isalnum())


def race_no(value: Any) -> str:
    text = clean(value).upper().replace("R", "")
    digits = "".join(ch for ch in text if ch.isdigit())
    return str(int(digits)) if digits else ""


def as_date(value: Any) -> str:
    return clean(value)[:10]


def number(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("value")
    text = clean(value).replace("$", "").replace(",", "")
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def has_value(value: Any) -> bool:
    return number(value) is not None or bool(clean(value) and not isinstance(value, dict))


def values_match(left: Any, right: Any) -> bool:
    left_number = number(left)
    right_number = number(right)
    if left_number is not None or right_number is not None:
        return (
            left_number is not None
            and right_number is not None
            and abs(left_number - right_number) < 0.0001
        )
    return clean(left) == clean(right)


def source_value_parts(value: Any) -> tuple[Any, str, str, str]:
    if isinstance(value, dict):
        return (
            value.get("value"),
            clean(value.get("status")),
            clean(value.get("missingReason")),
            clean(value.get("source")),
        )
    return value, "", "", ""


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def artifact_timestamp(path: Path) -> str:
    if not path.exists():
        return ""
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def artifact_row_count(path: Path) -> int:
    if not path.exists() or path.stat().st_size == 0:
        return 0
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return 0
        if isinstance(payload, dict) and isinstance(payload.get("runners"), list):
            return len(payload["runners"])
        if isinstance(payload, dict) and isinstance(payload.get("races"), list):
            return sum(len(race.get("runners", [])) for race in payload["races"] if isinstance(race, dict))
        return 1
    return len(read_csv(path))


def metric_key(date: Any, meeting: Any, race_number: Any, runner_name: Any) -> tuple[str, str, str, str]:
    return (
        as_date(date),
        norm_track(meeting),
        race_no(race_number),
        norm_name(runner_name),
    )


def csv_metric_index(path: Path, value_field: str) -> dict[tuple[str, str, str, str], dict[str, str]]:
    out = {}
    for row in read_csv(path):
        key = metric_key(
            row.get("raceDate") or row.get("race_date"),
            row.get("meeting") or row.get("track") or row.get("display_track"),
            row.get("raceNumber") or row.get("race_number") or row.get("race_no"),
            row.get("runnerName") or row.get("runner") or row.get("horse"),
        )
        if key[0] and key[3]:
            out[key] = row
    return out


def json_runner_index(path: Path) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("runners", []) if isinstance(payload, dict) else []
    out = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = metric_key(row.get("raceDate"), row.get("meeting"), row.get("raceNumber"), row.get("runnerName"))
        if key[0] and key[3]:
            out[key] = row
    return out


def status_reason(value: Any) -> tuple[str, str]:
    if not isinstance(value, dict):
        return "", ""
    return clean(value.get("status")), clean(value.get("missingReason"))


def history_stats(runner: dict[str, Any]) -> dict[str, int]:
    runs = runner.get("fullForm") or []
    position_source = 0
    position_feed = 0
    sectionals = 0
    historical_epi = 0
    historical_early = 0
    historical_late = 0
    for run in runs:
        if not isinstance(run, dict):
            continue
        pos_map = run.get("positionInRunningBySegment")
        source_status = clean(run.get("positionInRunningStatus"))
        if source_status == "POSITION_POPULATED" or (isinstance(pos_map, dict) and pos_map):
            position_source += 1
        if clean(run.get("positionInRunning")) or (isinstance(pos_map, dict) and pos_map):
            position_feed += 1
        sectionals_payload = run.get("sectionalIndices")
        if isinstance(sectionals_payload, dict):
            if any(number(item) is not None for key, item in sectionals_payload.items() if key.startswith("index")):
                sectionals += 1
        if number(run.get("historicalEpi")) is not None or number(run.get("performanceRating")) is not None:
            historical_epi += 1
        if number(run.get("historicalEarlySpeed")) is not None:
            historical_early += 1
        if number(run.get("historicalLateSpeed")) is not None:
            historical_late += 1
    return {
        "history_count": len(runs),
        "position_source_runs": position_source,
        "position_feed_runs": position_feed,
        "sectional_runs": sectionals,
        "historical_epi_runs": historical_epi,
        "historical_early_runs": historical_early,
        "historical_late_runs": historical_late,
    }


def classify_missing(metric: str, runner: dict[str, Any], value: Any, stats: dict[str, int]) -> str:
    raw, status, reason, _source = source_value_parts(value)
    if number(raw) is not None or clean(raw):
        return ""
    if runner.get("scratched"):
        return "SCRATCHED"
    if runner.get("firstStarter"):
        return "LEGITIMATE_FIRST_STARTER"

    reason_key = (reason or status).upper()
    history_count = stats["history_count"]

    if history_count <= 0 or reason_key in {"NO_HISTORY", "NO_GOVERNED_HISTORY", "ZERO_HISTORICAL_RUNS", "NO_PRIOR_FORM_HISTORY"}:
        return "LEGITIMATE_NO_HISTORY"
    if reason_key in {
        "FIRST_STARTER",
    }:
        return "LEGITIMATE_FIRST_STARTER"
    if reason_key in {
        "INSUFFICIENT_RUNS",
        "INSUFFICIENT_BENCHMARKED_RUNS",
        "INSUFFICIENT_HISTORICAL_RUNS",
        "INSUFFICIENT_FACTOR_FAMILIES",
        "INSUFFICIENT_PERFORMANCE_HISTORY",
        "NO_GOVERNED_PROJECTION",
        "NO_CURRENT_EPR_NO_PRICE",
    }:
        return "LEGITIMATE_INSUFFICIENT_HISTORY"
    if reason_key in {
        "HISTORICAL_RUNS_BUT_NO_SPEED_SOURCE",
        "NO_GOVERNED_SPEED_SOURCE",
        "NO_GOVERNED_PHASE_EVIDENCE",
        "SPEED_SOURCE_PRESENT_BUT_NOT_METHODOLOGY_ELIGIBLE",
        "NO_ERI_SOURCE_RACE",
        "NON_RATEABLE_NO_REQUIRED_EVIDENCE",
        "UNAVAILABLE",
        "NO_SECTIONAL_CHECKPOINT_SOURCE",
    }:
        return "SOURCE_DATA_UNAVAILABLE"

    if metric == "epr" and stats["historical_epi_runs"] > 0:
        return "JOIN_FAILURE"
    if metric == "early_speed" and stats["historical_early_runs"] >= 2:
        return "JOIN_FAILURE"
    if metric == "late_speed" and stats["historical_late_runs"] >= 2:
        return "JOIN_FAILURE"
    if metric == "form_momentum":
        _, momentum_status, momentum_reason, _ = source_value_parts(value)

        governed_momentum_missing = {
            "INSUFFICIENT_HISTORICAL_RUNS",
            "INSUFFICIENT_COMPARABLE_RUNS",
            "NO_APPROVED_TRAJECTORY_EVIDENCE",
        }

        if (
            clean(momentum_status).upper()
            in governed_momentum_missing
            or clean(momentum_reason).upper()
            in governed_momentum_missing
        ):
            return "LEGITIMATE_INSUFFICIENT_HISTORY"

        if history_count >= 3:
            return "PIPELINE_FAILURE"

    if metric == "suitability" and history_count >= 3:
        return "PIPELINE_FAILURE"

    return "UNKNOWN_ERROR"


def metric_row(prefix: str, value: Any, runner: dict[str, Any], stats: dict[str, int]) -> dict[str, Any]:
    raw, status, reason, source = source_value_parts(value)
    classification = classify_missing(prefix, runner, value, stats)
    return {
        f"{prefix}_value": raw if raw is not None else "",
        f"{prefix}_status": status,
        f"{prefix}_reason": reason,
        f"{prefix}_source_artifact": source,
        f"{prefix}_missing_class": classification,
    }


def load_form_guide() -> dict[str, Any]:
    return json.loads(FORM_GUIDE_JSON.read_text(encoding="utf-8"))


def build_audit(current_date: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    payload = load_form_guide()
    early_csv = csv_metric_index(EARLY_SPEED_CSV, "earlySpeed")
    early_json = json_runner_index(EARLY_SPEED_JSON)
    late_csv = csv_metric_index(LATE_SPEED_CSV, "lateSpeed")
    late_json = json_runner_index(LATE_SPEED_JSON)
    caulfield_rows: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    counts = Counter()
    metric_populated = Counter()
    metric_missing_classes = Counter()
    position_counts = Counter()

    for race in payload.get("races", []):
        if as_date(race.get("raceDate")) != current_date:
            continue
        for runner in race.get("runners", []):
            stats = history_stats(runner)
            scratched = bool(runner.get("scratched"))
            active = not scratched
            first_starter = bool(runner.get("firstStarter"))
            counts["total_runners"] += 1
            counts["scratched"] += 1 if scratched else 0
            counts["active_runners"] += 1 if active else 0
            counts["first_starters"] += 1 if active and first_starter else 0
            counts["no_history"] += 1 if active and stats["history_count"] == 0 and not first_starter else 0
            counts["insufficient_history"] += 1 if active and 0 < stats["history_count"] < 3 else 0

            base = {
                "race_date": race.get("raceDate"),
                "meeting": race.get("meeting"),
                "race": race.get("raceNumber"),
                "race_name": race.get("raceName") or "",
                "race_distance": race.get("distance") or "",
                "race_class": race.get("raceClass") or "",
                "runner_number": runner.get("runnerNumber"),
                "horse": runner.get("runnerName"),
                "scratched": "YES" if scratched else "NO",
                "history_count": stats["history_count"],
                "legitimate_first_starter": "YES" if first_starter else "NO",
                "recent_form_run_count": stats["history_count"],
                "position_in_running_source_runs": stats["position_source_runs"],
                "position_in_running_feed_runs": stats["position_feed_runs"],
                "position_in_running_coverage": f"{stats['position_feed_runs']}/{stats['history_count']}",
                "sectionals_coverage": f"{stats['sectional_runs']}/{stats['history_count']}",
            }

            metrics = {
                "epr": runner.get("epr") or runner.get("epi"),
                "early_speed": runner.get("earlySpeed"),
                "late_speed": runner.get("lateSpeed"),
                "suitability": runner.get("suitability"),
                "form_momentum": runner.get("formMomentum"),
            }
            for metric_name, metric_value in metrics.items():
                base.update(metric_row(metric_name, metric_value, runner, stats))
                if not scratched and number(metric_value) is not None:
                    metric_populated[metric_name] += 1
                missing_class = base.get(f"{metric_name}_missing_class", "")
                if missing_class:
                    metric_missing_classes[(metric_name, missing_class)] += 1

            runner_blocking = [
                base.get(f"{metric_name}_missing_class", "")
                for metric_name in metrics
                if base.get(f"{metric_name}_missing_class", "") in BLOCKING_CLASSES
            ]
            base["missingness_legitimate_or_failure"] = "PIPELINE_BLOCKING_FAILURE" if runner_blocking else "GOVERNED_OR_POPULATED"
            base["pipeline_failure"] = "YES" if "PIPELINE_FAILURE" in runner_blocking else "NO"
            base["join_failure"] = "YES" if "JOIN_FAILURE" in runner_blocking else "NO"
            base["temporal_eligibility_failure"] = "YES" if "TEMPORAL_ELIGIBILITY_FAILURE" in runner_blocking else "NO"
            base["unknown_error"] = "YES" if "UNKNOWN_ERROR" in runner_blocking else "NO"

            if active and not first_starter and stats["history_count"] >= 3:
                counts["rateable_active_runners"] += 1

            position_counts["historical_runs_inspected"] += stats["history_count"]
            position_counts["runs_with_source_position_data"] += stats["position_source_runs"]
            position_counts["runs_with_feed_position_data"] += stats["position_feed_runs"]
            position_counts["runs_with_sectionals"] += stats["sectional_runs"]
            if stats["position_source_runs"] > stats["position_feed_runs"]:
                position_counts["position_dropped_rows"] += stats["position_source_runs"] - stats["position_feed_runs"]

            rows.append(base)

            race_name = clean(race.get("raceName")).upper()
            is_caulfield_g2 = (
                race.get("meeting") == "Caulfield"
                and race.get("raceNumber") == 7
                and clean(race.get("distance")) == "1400"
                and clean(race.get("raceClass")).upper() == "GROUP 2"
            )
            if is_caulfield_g2:
                key = metric_key(race.get("raceDate"), race.get("meeting"), race.get("raceNumber"), runner.get("runnerName"))
                early_csv_row = early_csv.get(key, {})
                early_json_row = early_json.get(key, {})
                late_csv_row = late_csv.get(key, {})
                late_json_row = late_json.get(key, {})
                caulfield = dict(base)
                caulfield.update(
                    {
                        "early_csv_value": early_csv_row.get("earlySpeed", ""),
                        "early_json_value": early_json_row.get("earlySpeed", ""),
                        "early_ui_matches_csv": "YES" if values_match(base.get("early_speed_value"), early_csv_row.get("earlySpeed")) else "NO",
                        "late_csv_value": late_csv_row.get("lateSpeed", ""),
                        "late_json_value": late_json_row.get("lateSpeed", ""),
                        "late_ui_matches_csv": "YES" if values_match(base.get("late_speed_value"), late_csv_row.get("lateSpeed")) else "NO",
                    }
                )
                caulfield_rows.append(caulfield)

    blocking_counts = Counter()
    for row in rows:
        for metric_name in ("epr", "early_speed", "late_speed", "suitability", "form_momentum"):
            cls = row.get(f"{metric_name}_missing_class", "")
            if cls:
                counts[f"{metric_name}_{cls}"] += 1
            if cls in BLOCKING_CLASSES:
                blocking_counts[cls] += 1

    summary = {
        "schema_version": "edgeiq_current_runner_intelligence_audit_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "current_date": current_date,
        "counts": dict(counts),
        "metric_populated": dict(metric_populated),
        "metric_missing_classes": {f"{metric}|{cls}": value for (metric, cls), value in metric_missing_classes.items()},
        "position_in_running": dict(position_counts),
        "blocking_counts": dict(blocking_counts),
        "unexplained_missing": sum(blocking_counts.values()),
        "pipeline_failures": blocking_counts.get("PIPELINE_FAILURE", 0),
        "join_failures": blocking_counts.get("JOIN_FAILURE", 0),
        "temporal_eligibility_failures": blocking_counts.get("TEMPORAL_ELIGIBILITY_FAILURE", 0),
        "unknown_errors": blocking_counts.get("UNKNOWN_ERROR", 0),
    }
    summary["status"] = "PASS" if summary["unexplained_missing"] == 0 else "FAIL"
    return rows, caulfield_rows, summary


def stage_trace(current_date: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    active = [row for row in rows if row["scratched"] == "NO"]
    stages = [
        ("historical results / historical performance", HISTORICAL_RUN_INTELLIGENCE, "historical governed result intelligence"),
        ("EPI history", HISTORICAL_EPI, "historical EPI fact rows"),
        ("current runner history resolution", RACE_FIELDS, "current runner authority and fullForm resolution"),
        ("EPR", EPI_JSON, "current EPR/EPI JSON consumed by Form Guide"),
        ("Early Speed", EARLY_SPEED_JSON, "current early speed JSON consumed by Form Guide"),
        ("Late Speed", LATE_SPEED_JSON, "current late speed JSON consumed by Form Guide"),
        ("Suitability", SUITABILITY, "current suitability CSV/JSON projection"),
        ("Form Momentum", FORM_MOMENTUM, "current form momentum CSV/JSON projection"),
        ("Form Guide feed", FORM_GUIDE_JSON, "frontend Form Guide JSON feed"),
        ("React display", REACT_FORM_GUIDE, "RaceFormGuideWorkspace renders normalised Form Guide values"),
        ("React status normaliser", REACT_NORMALISER, "formGuideNormaliser status/missingReason labels"),
    ]
    metric_by_stage = {
        "EPR": "epr",
        "Early Speed": "early_speed",
        "Late Speed": "late_speed",
        "Suitability": "suitability",
        "Form Momentum": "form_momentum",
    }
    output = []
    for stage, artifact, note in stages:
        metric = metric_by_stage.get(stage)
        matched = ""
        unmatched = ""
        failure_reasons = ""
        if metric:
            matched_count = sum(1 for row in active if number(row.get(f"{metric}_value")) is not None)
            missing = [row.get(f"{metric}_missing_class", "") for row in active if row.get(f"{metric}_missing_class")]
            matched = matched_count
            unmatched = len(missing)
            failure_reasons = ";".join(f"{k}:{v}" for k, v in sorted(Counter(missing).items()))
        elif stage == "Form Guide feed":
            matched = len(active)
            unmatched = 0
        elif stage == "current runner history resolution":
            matched = sum(1 for row in active if int(row["history_count"]) > 0)
            unmatched = sum(1 for row in active if int(row["history_count"]) == 0)
            failure_reasons = "LEGITIMATE_NO_HISTORY_OR_FIRST_STARTER"
        output.append(
            {
                "stage": stage,
                "input_artifact": note,
                "output_artifact": str(artifact),
                "row_count": artifact_row_count(artifact),
                "current_runner_count": len(rows),
                "matched_runners": matched,
                "unmatched_runners": unmatched,
                "failure_reasons": failure_reasons,
                "modified_utc": artifact_timestamp(artifact),
                "fresh_for_current_date": "YES" if current_date else "",
            }
        )
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date")
    parser.add_argument("--gate", action="store_true")
    args = parser.parse_args()

    window = build_three_day_window()
    current_date = args.date or window.today

    rows, caulfield_rows, summary = build_audit(current_date)

    fields = [
        "race_date",
        "meeting",
        "race",
        "race_name",
        "race_distance",
        "race_class",
        "runner_number",
        "horse",
        "scratched",
        "history_count",
        "legitimate_first_starter",
        "epr_value",
        "epr_status",
        "epr_reason",
        "epr_source_artifact",
        "epr_missing_class",
        "early_speed_value",
        "early_speed_status",
        "early_speed_reason",
        "early_speed_source_artifact",
        "early_speed_missing_class",
        "late_speed_value",
        "late_speed_status",
        "late_speed_reason",
        "late_speed_source_artifact",
        "late_speed_missing_class",
        "suitability_value",
        "suitability_status",
        "suitability_reason",
        "suitability_source_artifact",
        "suitability_missing_class",
        "form_momentum_value",
        "form_momentum_status",
        "form_momentum_reason",
        "form_momentum_source_artifact",
        "form_momentum_missing_class",
        "recent_form_run_count",
        "position_in_running_source_runs",
        "position_in_running_feed_runs",
        "position_in_running_coverage",
        "sectionals_coverage",
        "missingness_legitimate_or_failure",
        "pipeline_failure",
        "join_failure",
        "temporal_eligibility_failure",
        "unknown_error",
    ]

    write_csv(ROW_AUDIT, rows, fields)
    write_csv(
        CAULFIELD_G2_AUDIT,
        caulfield_rows,
        fields
        + [
            "early_csv_value",
            "early_json_value",
            "early_ui_matches_csv",
            "late_csv_value",
            "late_json_value",
            "late_ui_matches_csv",
        ],
    )
    trace_rows = stage_trace(current_date, rows)
    write_csv(
        STAGE_TRACE,
        trace_rows,
        [
            "stage",
            "input_artifact",
            "output_artifact",
            "row_count",
            "current_runner_count",
            "matched_runners",
            "unmatched_runners",
            "failure_reasons",
            "modified_utc",
            "fresh_for_current_date",
        ],
    )
    write_json(SUMMARY_JSON, summary)

    DOCS.mkdir(parents=True, exist_ok=True)
    write_json(DOCS / SUMMARY_JSON.name, summary)

    print("EDGEIQ_CURRENT_RUNNER_INTELLIGENCE_AUDIT_V1")
    print(f"CURRENT_DATE={current_date}")
    print(f"CURRENT_RUNNER_AUDIT={summary['status']}")
    print(f"ACTIVE_RUNNERS={summary['counts'].get('active_runners', 0)}")
    print(f"SCRATCHED={summary['counts'].get('scratched', 0)}")
    print(f"NO_HISTORY={summary['counts'].get('no_history', 0)}")
    print(f"FIRST_STARTERS={summary['counts'].get('first_starters', 0)}")
    print(f"INSUFFICIENT_HISTORY={summary['counts'].get('insufficient_history', 0)}")
    print(f"RATEABLE_ACTIVE_RUNNERS={summary['counts'].get('rateable_active_runners', 0)}")
    print(f"EPR_POPULATED={summary['metric_populated'].get('epr', 0)}")
    print(f"EARLY_SPEED_POPULATED={summary['metric_populated'].get('early_speed', 0)}")
    print(f"LATE_SPEED_POPULATED={summary['metric_populated'].get('late_speed', 0)}")
    print(f"SUITABILITY_POPULATED={summary['metric_populated'].get('suitability', 0)}")
    print(f"FORM_MOMENTUM_POPULATED={summary['metric_populated'].get('form_momentum', 0)}")
    print(f"UNEXPLAINED_MISSING={summary['unexplained_missing']}")
    print(f"PIPELINE_FAILURES={summary['pipeline_failures']}")
    print(f"JOIN_FAILURES={summary['join_failures']}")
    print(f"TEMPORAL_ELIGIBILITY_FAILURES={summary['temporal_eligibility_failures']}")
    print(f"UNKNOWN_ERRORS={summary['unknown_errors']}")
    print(f"ROW_AUDIT={ROW_AUDIT}")
    print(f"STAGE_TRACE={STAGE_TRACE}")
    print(f"CAULFIELD_G2_AUDIT={CAULFIELD_G2_AUDIT}")

    if args.gate and summary["status"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
