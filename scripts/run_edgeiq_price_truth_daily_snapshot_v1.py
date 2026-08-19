from __future__ import annotations

import csv
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUTPUTS = ROOT / "outputs"
AUDITS = OUTPUTS / "audits"
SCRIPTS = ROOT / "scripts"

SUMMARY = DATA / "edgeiq_price_truth_daily_snapshot_v1_summary.csv"
AUDIT = AUDITS / "edgeiq_price_truth_daily_snapshot_v1_audit.txt"

HEALTH_SUMMARY = DATA / "edgeiq_price_truth_history_v1_health_summary.csv"
SETTLEMENT_SUMMARY = DATA / "edgeiq_price_truth_result_settlement_diagnostic_v1_summary.csv"
RESULTS_LOOP_UPDATE_SUMMARY = DATA / "edgeiq_results_truth_loop_update_diagnostic_v1_summary.csv"

SUMMARY_COLUMNS = [
    "snapshot_run_id",
    "built_at",
    "section",
    "step_no",
    "step_name",
    "metric",
    "value",
    "status",
    "path",
    "notes",
]


@dataclass(frozen=True)
class OutputSpec:
    path: Path
    kind: str
    required: bool = True


@dataclass(frozen=True)
class StepSpec:
    step_no: int
    name: str
    script: Path
    outputs: tuple[OutputSpec, ...]


STEPS = [
    StepSpec(
        1,
        "CURRENT_FAIR_PRICES_REVIEW_V5_2",
        SCRIPTS / "build_edgeiq_current_fair_prices_review_v5_2.py",
        (
            OutputSpec(DATA / "edgeiq_current_fair_prices_review_v5_2.csv", "csv"),
            OutputSpec(DATA / "edgeiq_current_fair_prices_review_v5_2_audit.csv", "csv"),
        ),
    ),
    StepSpec(
        2,
        "SPORTSBET_FULL_DAY_RACECARD_CAPTURE_V5_2",
        SCRIPTS / "build_sportsbet_full_day_racecard_capture_v5_2.py",
        (
            OutputSpec(OUTPUTS / "sportsbet_live_real" / "sportsbet_full_day_events_v5_2.json", "json"),
            OutputSpec(OUTPUTS / "sportsbet_live_real" / "sportsbet_full_day_racecards_v5_2.json", "json"),
            OutputSpec(DATA / "sportsbet_live_market_full_day_v5_2.csv", "csv"),
            OutputSpec(AUDITS / "sportsbet_full_day_capture_v5_2_audit.txt", "txt"),
        ),
    ),
    StepSpec(
        3,
        "SPORTSBET_COMPARISON_V5_2",
        SCRIPTS / "build_edgeiq_current_fair_prices_sportsbet_comparison_v5_2.py",
        (
            OutputSpec(DATA / "edgeiq_current_fair_prices_sportsbet_comparison_v5_2.csv", "csv"),
            OutputSpec(DATA / "edgeiq_current_fair_prices_sportsbet_comparison_v5_2_audit.csv", "csv"),
        ),
    ),
    StepSpec(
        4,
        "OVERLAY_QUALITY_AUDIT_V5_2",
        SCRIPTS / "build_edgeiq_overlay_quality_audit_v5_2.py",
        (
            OutputSpec(DATA / "edgeiq_overlay_quality_audit_v5_2.csv", "csv"),
            OutputSpec(DATA / "edgeiq_overlay_quality_audit_v5_2_summary.csv", "csv"),
        ),
    ),
    StepSpec(
        5,
        "CLEAN_OVERLAY_REVIEW_BOARD_V5_2",
        SCRIPTS / "build_edgeiq_clean_overlay_review_board_v5_2.py",
        (
            OutputSpec(DATA / "edgeiq_clean_overlay_review_board_v5_2.csv", "csv"),
            OutputSpec(DATA / "edgeiq_clean_overlay_review_board_v5_2_summary.csv", "csv"),
        ),
    ),
    StepSpec(
        6,
        "OVERLAY_DISCIPLINE_FILTER_V5_2",
        SCRIPTS / "build_edgeiq_overlay_discipline_filter_v5_2.py",
        (
            OutputSpec(DATA / "edgeiq_overlay_discipline_filter_v5_2.csv", "csv"),
            OutputSpec(DATA / "edgeiq_overlay_discipline_filter_v5_2_summary.csv", "csv"),
        ),
    ),
    StepSpec(
        7,
        "PRICE_TRUTH_ENGINE_V1",
        SCRIPTS / "build_edgeiq_price_truth_engine_v1.py",
        (
            OutputSpec(DATA / "edgeiq_price_truth_history_v1.csv", "csv"),
            OutputSpec(DATA / "edgeiq_price_truth_history_v1_audit.csv", "csv"),
        ),
    ),
    StepSpec(
        8,
        "PRICE_TRUTH_HEALTH_AUDIT_V1",
        SCRIPTS / "audit_edgeiq_price_truth_history_v1.py",
        (
            OutputSpec(DATA / "edgeiq_price_truth_history_v1_health.csv", "csv"),
            OutputSpec(HEALTH_SUMMARY, "csv"),
        ),
    ),
    StepSpec(
        9,
        "PRICE_TRUTH_RESULT_SETTLEMENT_DIAGNOSTIC_V1",
        SCRIPTS / "diagnose_edgeiq_price_truth_result_settlement_v1.py",
        (
            OutputSpec(DATA / "edgeiq_price_truth_result_settlement_diagnostic_v1.csv", "csv"),
            OutputSpec(SETTLEMENT_SUMMARY, "csv"),
        ),
    ),
    StepSpec(
        10,
        "RESULTS_TRUTH_LOOP_UPDATE_DIAGNOSTIC_V1",
        SCRIPTS / "diagnose_edgeiq_results_truth_loop_update_v1.py",
        (
            OutputSpec(DATA / "edgeiq_results_truth_loop_update_diagnostic_v1.csv", "csv"),
            OutputSpec(RESULTS_LOOP_UPDATE_SUMMARY, "csv"),
        ),
    ),
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def csv_row_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        rows = list(reader)
    if not rows:
        return 0
    return max(len(rows) - 1, 0)


def json_item_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError:
        return 0
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for key in ("events", "racecards", "markets", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
        return len(payload)
    return 0


def txt_line_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return sum(1 for _ in handle)


def output_count(spec: OutputSpec) -> int:
    if spec.kind == "csv":
        return csv_row_count(spec.path)
    if spec.kind == "json":
        return json_item_count(spec.path)
    if spec.kind == "txt":
        return txt_line_count(spec.path)
    return 0


def summary_row(
    run_id: str,
    section: str,
    metric: str,
    value: object,
    *,
    step: StepSpec | None = None,
    status: str = "",
    path: Path | None = None,
    notes: str = "",
) -> dict[str, object]:
    return {
        "snapshot_run_id": run_id,
        "built_at": now_utc(),
        "section": section,
        "step_no": "" if step is None else step.step_no,
        "step_name": "" if step is None else step.name,
        "metric": metric,
        "value": value,
        "status": status,
        "path": "" if path is None else rel(path),
        "notes": notes,
    }


def write_summary(rows: list[dict[str, object]]) -> None:
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    with SUMMARY.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_audit(lines: list[str]) -> None:
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def tail(text: str, limit: int = 12000) -> str:
    if len(text) <= limit:
        return text.strip()
    return text[-limit:].strip()


def summary_lookup(path: Path, section: str, metric: str) -> str:
    for row in read_csv_rows(path):
        if row.get("section") == section and row.get("metric") == metric:
            return str(row.get("value", "")).strip()
    return ""


def summary_count(path: Path, section: str, metric: str) -> int:
    value = summary_lookup(path, section, metric)
    try:
        return int(float(value))
    except ValueError:
        return 0


def metric_count_from_summary(path: Path, section: str, metric_name: str) -> int:
    for row in read_csv_rows(path):
        if row.get("section") == section and row.get("metric") == metric_name:
            try:
                return int(float(str(row.get("value", "0")).strip()))
            except ValueError:
                return 0
    return 0


def health_status() -> tuple[str, str]:
    rows = read_csv_rows(HEALTH_SUMMARY)
    if not rows:
        return "MISSING_HEALTH_SUMMARY", "Health summary file was not produced."

    fail_rows = 0
    pass_rows = 0
    for row in rows:
        if row.get("section") == "health_status_counts":
            status = str(row.get("metric", "")).strip()
            try:
                count = int(float(str(row.get("value", "0")).strip()))
            except ValueError:
                count = 0
            if status == "PASS_PENDING_RESULTS":
                pass_rows += count
            else:
                fail_rows += count

    low_coverage = summary_lookup(HEALTH_SUMMARY, "warning", "snapshot_low_coverage")
    missing_price = summary_count(HEALTH_SUMMARY, "missing", "missing_edgeiq_price_count")
    missing_market = summary_count(HEALTH_SUMMARY, "missing", "missing_sportsbet_price_count")
    invalid_prob = summary_count(HEALTH_SUMMARY, "invalid", "invalid_probability_any_count")
    invalid_price = summary_count(HEALTH_SUMMARY, "invalid", "invalid_price_any_count")

    if (
        pass_rows > 0
        and fail_rows == 0
        and str(low_coverage).upper() == "FALSE"
        and missing_price == 0
        and missing_market == 0
        and invalid_prob == 0
        and invalid_price == 0
    ):
        return "PASS_PENDING_RESULTS", f"{pass_rows} rows passed price truth health checks."

    return (
        "FAIL_REVIEW_REQUIRED",
        (
            f"pass_rows={pass_rows}; fail_rows={fail_rows}; "
            f"snapshot_low_coverage={low_coverage}; missing_edgeiq_price={missing_price}; "
            f"missing_sportsbet_price={missing_market}; invalid_probabilities={invalid_prob}; "
            f"invalid_prices={invalid_price}"
        ),
    )


def settlement_status() -> tuple[str, str]:
    status = summary_lookup(SETTLEMENT_SUMMARY, "recommendation", "settlement_write_status")
    recommendation = summary_lookup(
        SETTLEMENT_SUMMARY, "recommendation", "safest_result_source_recommendation"
    )
    if not status:
        return "UNKNOWN", "Settlement diagnostic summary was missing status."
    return status, recommendation


def results_loop_update_status() -> tuple[str, str]:
    status = summary_lookup(RESULTS_LOOP_UPDATE_SUMMARY, "recommendation", "status")
    recommendation = summary_lookup(
        RESULTS_LOOP_UPDATE_SUMMARY, "recommendation", "safest_update_source_recommendation"
    )
    if not status:
        return "UNKNOWN", "Results truth loop update diagnostic summary was missing status."
    return status, recommendation


def calibration_status(health: str, settlement: str) -> tuple[str, str]:
    if health != "PASS_PENDING_RESULTS":
        return "NO", "Price truth health audit is not passing."
    if settlement == "SAFE_TO_WRITE":
        return "YES", "Settlement diagnostic says result fields are ready to write."
    return "PENDING_RESULTS", "Price truth base is healthy, but result settlement is not ready."


def final_status(step_failed: bool, health: str, settlement: str) -> str:
    if step_failed or health != "PASS_PENDING_RESULTS":
        return "SNAPSHOT_FAILED"
    if settlement == "SAFE_TO_WRITE":
        return "SNAPSHOT_SETTLEMENT_READY"
    return "SNAPSHOT_HEALTHY_PENDING_RESULTS"


def add_output_rows(
    run_id: str,
    rows: list[dict[str, object]],
    step: StepSpec,
) -> bool:
    missing_required = False
    for spec in step.outputs:
        exists = spec.path.exists()
        count = output_count(spec) if exists else 0
        status = "FOUND" if exists else "MISSING"
        if spec.required and not exists:
            missing_required = True
        rows.append(
            summary_row(
                run_id,
                "output_file",
                f"{spec.kind}_row_or_item_count",
                count,
                step=step,
                status=status,
                path=spec.path,
                notes="required" if spec.required else "optional",
            )
        )
    return missing_required


def run_step(
    run_id: str,
    step: StepSpec,
    rows: list[dict[str, object]],
    audit_lines: list[str],
) -> bool:
    audit_lines.append("")
    audit_lines.append("=" * 96)
    audit_lines.append(f"STEP {step.step_no}: {step.name}")
    audit_lines.append("=" * 96)

    if not step.script.exists():
        rows.append(
            summary_row(
                run_id,
                "step_result",
                "return_code",
                "SCRIPT_MISSING",
                step=step,
                status="FAILED",
                path=step.script,
            )
        )
        audit_lines.append(f"Missing script: {step.script}")
        return False

    command = [sys.executable, str(step.script)]
    audit_lines.append("command: " + " ".join(command))
    started = time.monotonic()
    proc = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    elapsed = time.monotonic() - started

    status = "PASSED" if proc.returncode == 0 else "FAILED"
    rows.append(
        summary_row(
            run_id,
            "step_result",
            "return_code",
            proc.returncode,
            step=step,
            status=status,
            path=step.script,
            notes=f"duration_seconds={elapsed:.2f}",
        )
    )
    rows.append(
        summary_row(
            run_id,
            "step_result",
            "duration_seconds",
            f"{elapsed:.2f}",
            step=step,
            status=status,
            path=step.script,
        )
    )

    audit_lines.append(f"return_code: {proc.returncode}")
    audit_lines.append(f"duration_seconds: {elapsed:.2f}")
    if proc.stdout.strip():
        audit_lines.append("")
        audit_lines.append("stdout_tail:")
        audit_lines.append(tail(proc.stdout))
    if proc.stderr.strip():
        audit_lines.append("")
        audit_lines.append("stderr_tail:")
        audit_lines.append(tail(proc.stderr))

    missing_outputs = add_output_rows(run_id, rows, step)
    if missing_outputs:
        rows.append(
            summary_row(
                run_id,
                "step_result",
                "required_outputs",
                "MISSING",
                step=step,
                status="FAILED",
                notes="One or more required outputs were not found after the step.",
            )
        )
        audit_lines.append("required_output_status: MISSING")
        return False

    if proc.returncode != 0:
        return False

    audit_lines.append("required_output_status: FOUND")
    return True


def append_existing_output_summary(run_id: str, rows: list[dict[str, object]]) -> None:
    checks = [
        ("fair_prices_review_rows", DATA / "edgeiq_current_fair_prices_review_v5_2.csv"),
        ("sportsbet_full_day_market_rows", DATA / "sportsbet_live_market_full_day_v5_2.csv"),
        (
            "sportsbet_comparison_rows",
            DATA / "edgeiq_current_fair_prices_sportsbet_comparison_v5_2.csv",
        ),
        ("overlay_quality_rows", DATA / "edgeiq_overlay_quality_audit_v5_2.csv"),
        ("clean_overlay_review_rows", DATA / "edgeiq_clean_overlay_review_board_v5_2.csv"),
        ("discipline_filter_rows", DATA / "edgeiq_overlay_discipline_filter_v5_2.csv"),
        ("price_truth_history_rows", DATA / "edgeiq_price_truth_history_v1.csv"),
        ("price_truth_health_rows", DATA / "edgeiq_price_truth_history_v1_health.csv"),
        (
            "result_settlement_diagnostic_rows",
            DATA / "edgeiq_price_truth_result_settlement_diagnostic_v1.csv",
        ),
        (
            "results_loop_update_diagnostic_rows",
            DATA / "edgeiq_results_truth_loop_update_diagnostic_v1.csv",
        ),
    ]
    for metric, path in checks:
        rows.append(
            summary_row(
                run_id,
                "final_output_counts",
                metric,
                csv_row_count(path) if path.exists() else 0,
                status="FOUND" if path.exists() else "MISSING",
                path=path,
            )
        )


def add_final_rows(run_id: str, rows: list[dict[str, object]], step_failed: bool) -> str:
    health, health_notes = health_status()
    settlement, settlement_notes = settlement_status()
    loop_status, loop_notes = results_loop_update_status()
    calibration, calibration_notes = calibration_status(health, settlement)
    status = final_status(step_failed, health, settlement)

    final_metrics = [
        ("final_status", status, "FAILED" if status == "SNAPSHOT_FAILED" else "PASSED", ""),
        ("health_status", health, "PASSED" if health == "PASS_PENDING_RESULTS" else "FAILED", health_notes),
        (
            "settlement_ready",
            "TRUE" if settlement == "SAFE_TO_WRITE" else "FALSE",
            "PASSED" if settlement == "SAFE_TO_WRITE" else "PENDING",
            settlement_notes,
        ),
        ("settlement_status", settlement, "INFO", settlement_notes),
        (
            "results_truth_loop_update_ready",
            "TRUE" if loop_status == "SAFE_TO_UPDATE_RESULTS_LOOP" else "FALSE",
            "PASSED" if loop_status == "SAFE_TO_UPDATE_RESULTS_LOOP" else "PENDING",
            loop_notes,
        ),
        ("results_truth_loop_update_status", loop_status, "INFO", loop_notes),
        (
            "calibration_possible",
            calibration,
            "PASSED" if calibration == "YES" else "PENDING" if calibration == "PENDING_RESULTS" else "FAILED",
            calibration_notes,
        ),
    ]
    for metric, value, row_status, notes in final_metrics:
        rows.append(
            summary_row(
                run_id,
                "final",
                metric,
                value,
                status=row_status,
                notes=notes,
            )
        )
    return status


def print_summary(rows: Iterable[dict[str, object]], final: str) -> None:
    print("=" * 96)
    print("EDGEIQ PRICE TRUTH DAILY SNAPSHOT V1")
    print("=" * 96)
    print(f"final_status: {final}")
    for row in rows:
        if row.get("section") == "final":
            print(f"{row.get('metric')}: {row.get('value')} [{row.get('status')}]")
    print(f"summary: {SUMMARY}")
    print(f"audit: {AUDIT}")
    print("=" * 96)


def main() -> int:
    run_id = now_utc()
    AUDITS.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = [
        summary_row(run_id, "run", "runner_script", rel(Path(__file__)), status="STARTED"),
        summary_row(run_id, "run", "mode", "RESEARCH_ONLY", status="INFO"),
        summary_row(run_id, "run", "result_settlement", "DISABLED", status="INFO"),
        summary_row(run_id, "run", "bet_recommendations", "DISABLED", status="INFO"),
    ]
    audit_lines = [
        "EDGEIQ PRICE TRUTH DAILY SNAPSHOT V1",
        f"snapshot_run_id: {run_id}",
        f"root: {ROOT}",
        "mode: RESEARCH_ONLY",
        "result_settlement: DISABLED",
        "bet_recommendations: DISABLED",
    ]

    step_failed = False
    for step in STEPS:
        passed = run_step(run_id, step, rows, audit_lines)
        write_summary(rows)
        write_audit(audit_lines)
        if not passed:
            step_failed = True
            rows.append(
                summary_row(
                    run_id,
                    "final",
                    "final_status",
                    "SNAPSHOT_FAILED",
                    status="FAILED",
                    notes=f"Stopped at step {step.step_no}: {step.name}",
                )
            )
            write_summary(rows)
            write_audit(audit_lines)
            print_summary(rows, "SNAPSHOT_FAILED")
            return 1

    append_existing_output_summary(run_id, rows)
    final = add_final_rows(run_id, rows, step_failed)
    write_summary(rows)

    audit_lines.append("")
    audit_lines.append("=" * 96)
    audit_lines.append("FINAL STATUS")
    audit_lines.append("=" * 96)
    for row in rows:
        if row.get("section") == "final":
            audit_lines.append(f"{row.get('metric')}: {row.get('value')} [{row.get('status')}] {row.get('notes')}")
    write_audit(audit_lines)

    print_summary(rows, final)
    return 0 if final != "SNAPSHOT_FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
