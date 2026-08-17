from __future__ import annotations

from pathlib import Path
import csv
import json
import subprocess
import sys

ROOT = Path(r"C:\EDGEIQ_PLATFORM_FAST")

REFRESH = ROOT / "scripts" / "run_edgeiq_daily_product_refresh_v1.py"
CURRENT_AUDIT = ROOT / "scripts" / "audit_edgeiq_current_runner_intelligence_v1.py"
GLOBAL_AUDIT = ROOT / "scripts" / "audit_edgeiq_global_production_data_completeness_v1.py"

CURRENT_ROW_AUDIT = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_current_runner_intelligence_audit_v1.csv"
)

GLOBAL_SUMMARY = (
    ROOT
    / "outputs"
    / "production-hardening-v1"
    / "edgeiq_global_production_data_completeness_v1_summary.json"
)


def run_stage(label: str, args: list[str]) -> None:
    print()
    print("=" * 124)
    print(label)
    print("=" * 124)

    completed = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
    )

    print(f"{label.replace(' ', '_').upper()}_EXIT_CODE={completed.returncode}")

    if completed.returncode != 0:
        raise SystemExit(
            f"{label}=FAIL"
        )


def read_current_runner_rows() -> list[dict[str, str]]:
    if not CURRENT_ROW_AUDIT.exists():
        raise SystemExit(
            f"CURRENT_RUNNER_ROW_AUDIT_MISSING={CURRENT_ROW_AUDIT}"
        )

    with CURRENT_ROW_AUDIT.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        return list(
            csv.DictReader(handle)
        )


def verify_current_runner_gate() -> None:
    rows = read_current_runner_rows()

    blocking = [
        row
        for row in rows
        if (
            row.get("pipeline_failure") == "YES"
            or row.get("join_failure") == "YES"
            or row.get("temporal_eligibility_failure") == "YES"
            or row.get("unknown_error") == "YES"
        )
    ]

    print()
    print("=" * 124)
    print("VERIFY CURRENT-RUNNER ROW AUDIT")
    print("=" * 124)

    print(f"CURRENT_RUNNER_ROWS={len(rows)}")
    print(f"CURRENT_RUNNER_BLOCKING_ROWS={len(blocking)}")

    if blocking:
        for row in blocking[:50]:
            print(
                "BLOCKING="
                f"{row.get('race_date')}|"
                f"{row.get('meeting')}|"
                f"R{row.get('race')}|"
                f"{row.get('horse')}|"
                f"pipeline={row.get('pipeline_failure')}|"
                f"join={row.get('join_failure')}|"
                f"temporal={row.get('temporal_eligibility_failure')}|"
                f"unknown={row.get('unknown_error')}"
            )

        raise SystemExit(
            "CURRENT_RUNNER_ROW_AUDIT=FAIL"
        )

    print("CURRENT_RUNNER_ROW_AUDIT=PASS")


def verify_global() -> dict:
    if not GLOBAL_SUMMARY.exists():
        raise SystemExit(
            f"GLOBAL_SUMMARY_MISSING={GLOBAL_SUMMARY}"
        )

    payload = json.loads(
        GLOBAL_SUMMARY.read_text(
            encoding="utf-8-sig"
        )
    )

    print()
    print("=" * 124)
    print("VERIFY GLOBAL HARDENING SUMMARY")
    print("=" * 124)

    checks = {
        "HARDENING":
            payload.get("EDGEIQ_PRODUCTION_HARDENING_V1"),
        "UNEXPLAINED_MISSING":
            int(payload.get("UNEXPLAINED_MISSING", -1)),
        "JOIN_FAILURES":
            int(payload.get("JOIN_FAILURES", -1)),
        "TRANSFORM_FAILURES":
            int(payload.get("TRANSFORM_FAILURES", -1)),
        "STALE_ARTIFACTS":
            int(payload.get("STALE_ARTIFACTS", -1)),
        "SOURCE_TO_FEED_DROPS":
            int(payload.get("SOURCE_TO_FEED_DROPS", -1)),
        "FEED_OMISSIONS":
            int(payload.get("FEED_OMISSIONS", -1)),
        "REACT_FIELD_MISMATCHES":
            int(payload.get("REACT_FIELD_MISMATCHES", -1)),
    }

    for key, value in checks.items():
        print(f"{key}={value}")

    failed_gates = list(
        payload.get("FAILED_GATES") or []
    )

    field_failures = dict(
        payload.get("field_failures") or {}
    )

    workspace_failures = dict(
        payload.get("workspace_failures") or {}
    )

    print(
        "FAILED_GATES="
        + "|".join(failed_gates)
    )

    print(
        f"FIELD_FAILURE_COUNT={len(field_failures)}"
    )

    print(
        f"WORKSPACE_FAILURE_COUNT={len(workspace_failures)}"
    )

    if checks["HARDENING"] != "PASS":
        raise SystemExit(
            "GLOBAL_HARDENING=FAIL"
        )

    zero_keys = (
        "UNEXPLAINED_MISSING",
        "JOIN_FAILURES",
        "TRANSFORM_FAILURES",
        "STALE_ARTIFACTS",
        "SOURCE_TO_FEED_DROPS",
        "FEED_OMISSIONS",
        "REACT_FIELD_MISMATCHES",
    )

    for key in zero_keys:
        if checks[key] != 0:
            raise SystemExit(
                f"{key}=FAIL:{checks[key]}"
            )

    if failed_gates:
        raise SystemExit(
            "FAILED_GATES_PRESENT="
            + "|".join(failed_gates)
        )

    if field_failures:
        raise SystemExit(
            f"FIELD_FAILURES_PRESENT={field_failures}"
        )

    if workspace_failures:
        raise SystemExit(
            f"WORKSPACE_FAILURES_PRESENT={workspace_failures}"
        )

    print("GLOBAL_HARDENING_SUMMARY=PASS")

    return payload


def main() -> int:
    for path in (
        REFRESH,
        CURRENT_AUDIT,
        GLOBAL_AUDIT,
    ):
        if not path.exists():
            print(
                f"REQUIRED_SCRIPT_MISSING={path}"
            )
            return 1

    run_stage(
        "DAILY REFRESH",
        [
            sys.executable,
            str(REFRESH),
        ],
    )

    run_stage(
        "CURRENT RUNNER AUDIT",
        [
            sys.executable,
            str(CURRENT_AUDIT),
            "--gate",
        ],
    )

    verify_current_runner_gate()

    run_stage(
        "GLOBAL HARDENING",
        [
            sys.executable,
            str(GLOBAL_AUDIT),
        ],
    )

    payload = verify_global()

    print()
    print("=" * 124)
    print("EDGEIQ DAILY REPEATABILITY V1=PASS")
    print("=" * 124)

    print(
        f"DATE={payload.get('OPERATIONAL_TODAY')}"
    )

    print(
        f"MEETINGS={payload.get('MEETINGS')}"
    )

    print(
        f"RACES={payload.get('RACES')}"
    )

    print(
        f"RUNNERS={payload.get('RUNNERS')}"
    )

    print("DAILY_REFRESH=PASS")
    print("CURRENT_RUNNER_GOVERNANCE=PASS")
    print("GLOBAL_PRODUCTION_HARDENING=PASS")
    print("ZERO_BLOCKING_FAILURES=PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
