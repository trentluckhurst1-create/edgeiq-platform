from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from edgeiq_three_day_window_v1_common import (
    ENV_DATE_OVERRIDE,
    TIMEZONE_NAME,
    build_operational_dates,
    get_operational_today,
    parse_override_date,
)

csv.field_size_limit(1024 * 1024 * 64)


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
AUDIT = DATA / "edgeiq_current_data_rollover_audit_v1.json"

WINDOW = DATA / "edgeiq_three_day_window_v1.json"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
RACE_LIST = DATA / "edgeiq_vic_three_day_race_list_v1.csv"
LIVE_FEED = DATA / "edgeiq_live_terminal_feed_v1.csv"
VIC_LIVE_FEED = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"

PRODUCTION_REFRESH = ROOT / "scripts" / "run_edgeiq_daily_product_refresh_v1.py"
CURRENT_RUNNER_AUDIT = ROOT / "scripts" / "audit_edgeiq_current_runner_intelligence_v1.py"


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def csv_dates(path: Path, field: str = "race_date") -> set[str]:
    if not path.exists():
        return set()
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return {
                str(row.get(field, "")).strip()[:10]
                for row in csv.DictReader(handle)
                if str(row.get(field, "")).strip()
            }
    except Exception:
        return set()


def file_metadata(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "bytes": 0,
            "modified_utc": "",
        }
    return {
        "path": str(path),
        "exists": True,
        "bytes": path.stat().st_size,
        "modified_utc": datetime.fromtimestamp(
            path.stat().st_mtime,
            timezone.utc,
        ).isoformat(),
    }


def expected_dates_for(runtime_date: date | None = None) -> list[str]:
    today, _ = get_operational_today(override_date=runtime_date)
    return [item.isoformat() for item in build_operational_dates(today)]


def dates_match_expected(
    embedded_dates: list[str],
    expected_dates: list[str],
) -> bool:
    return [str(value)[:10] for value in embedded_dates] == expected_dates


def artifact_freshness(
    expected_dates: list[str],
) -> dict[str, Any]:
    expected_set = set(expected_dates)
    window = read_json(WINDOW)
    catalog = read_json(CATALOG)
    race_list_dates = csv_dates(RACE_LIST)
    live_dates = csv_dates(LIVE_FEED)
    vic_live_dates = csv_dates(VIC_LIVE_FEED)

    artifacts = []

    window_dates = []
    if isinstance(window, dict):
        window_dates = [
            str(item.get("date", ""))[:10]
            for item in window.get("dates", [])
            if isinstance(item, dict)
        ]
    artifacts.append({
        **file_metadata(WINDOW),
        "embedded_dates": window_dates,
        "expected_dates": expected_dates,
        "fresh": dates_match_expected(window_dates, expected_dates),
    })

    catalog_dates = []
    if isinstance(catalog, dict):
        catalog_dates = [
            str(value)[:10]
            for value in catalog.get("dates", [])
        ]
    artifacts.append({
        **file_metadata(CATALOG),
        "embedded_dates": catalog_dates,
        "expected_dates": expected_dates,
        "fresh": dates_match_expected(catalog_dates, expected_dates),
    })

    for path, dates in (
        (RACE_LIST, race_list_dates),
        (LIVE_FEED, live_dates),
        (VIC_LIVE_FEED, vic_live_dates),
    ):
        artifacts.append({
            **file_metadata(path),
            "embedded_dates": sorted(dates),
            "expected_dates": expected_dates,
            "fresh": expected_set.issubset(dates),
        })

    return {
        "expected_dates": expected_dates,
        "artifacts": artifacts,
        "fresh": all(item["fresh"] for item in artifacts),
    }


def write_audit(payload: dict[str, Any]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_production_refresh(operational_today: str) -> int:
    if not PRODUCTION_REFRESH.exists():
        raise RuntimeError(f"Production refresh script missing: {PRODUCTION_REFRESH}")

    env = os.environ.copy()
    env[ENV_DATE_OVERRIDE] = operational_today
    completed = subprocess.run(
        [
            sys.executable,
            str(PRODUCTION_REFRESH),
            "--date",
            operational_today,
        ],
        cwd=ROOT,
        env=env,
        text=True,
    )
    return completed.returncode


def run_current_runner_audit(operational_today: str) -> dict[str, Any]:
    if not CURRENT_RUNNER_AUDIT.exists():
        return {
            "status": "FAIL",
            "returncode": 1,
            "stdout": "",
            "stderr": f"Current-runner audit script missing: {CURRENT_RUNNER_AUDIT}",
        }

    env = os.environ.copy()
    env[ENV_DATE_OVERRIDE] = operational_today
    completed = subprocess.run(
        [
            sys.executable,
            str(CURRENT_RUNNER_AUDIT),
            "--date",
            operational_today,
            "--gate",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    return {
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ensure EDGEiQ public current-data artifacts match the operational three-day window."
    )
    parser.add_argument("--date", help="Optional YYYY-MM-DD injected operational date for tests.")
    parser.add_argument("--check-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    override = parse_override_date(args.date)
    today, date_source = get_operational_today(override_date=override)
    expected_dates = expected_dates_for(today)
    before = artifact_freshness(expected_dates)
    status = "CURRENT"
    refresh_returncode = None

    if not before["fresh"]:
        status = "STALE"
        if not args.check_only:
            refresh_returncode = run_production_refresh(today.isoformat())

    after = artifact_freshness(expected_dates)
    current_runner_audit = (
        run_current_runner_audit(today.isoformat())
        if after["fresh"]
        else {
            "status": "SKIPPED",
            "returncode": None,
            "stdout": "",
            "stderr": "Skipped because current-data artifacts are stale.",
        }
    )

    payload = {
        "schema_version": "edgeiq_current_data_rollover_audit_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "timezone": TIMEZONE_NAME,
        "operational_today": today.isoformat(),
        "date_source": date_source,
        "expected_today": expected_dates[0],
        "expected_tomorrow": expected_dates[1],
        "expected_day_plus_2": expected_dates[2],
        "initial_status": status,
        "check_only": args.check_only,
        "refresh_returncode": refresh_returncode,
        "before": before,
        "after": after,
        "current_runner_audit": current_runner_audit,
        "final_status": "CURRENT" if after["fresh"] else "STALE",
    }
    write_audit(payload)

    print("EDGEIQ_CURRENT_DATA_ROLLOVER_AUDIT_V1")
    print(f"TIMEZONE={TIMEZONE_NAME}")
    print(f"DATE_SOURCE={date_source}")
    print(f"TODAY={expected_dates[0]}")
    print(f"TOMORROW={expected_dates[1]}")
    print(f"DAY_PLUS_2={expected_dates[2]}")
    print(f"INITIAL_STATUS={status}")
    if refresh_returncode is not None:
        print(f"PRODUCTION_REFRESH_RETURNCODE={refresh_returncode}")
    print(f"FINAL_STATUS={payload['final_status']}")
    print(f"CURRENT_RUNNER_AUDIT={current_runner_audit['status']}")
    if current_runner_audit.get("stdout"):
        print(current_runner_audit["stdout"], end="")
    if current_runner_audit.get("stderr"):
        print(current_runner_audit["stderr"], end="", file=sys.stderr)
    print(f"AUDIT={AUDIT}")

    return 0 if after["fresh"] and current_runner_audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
