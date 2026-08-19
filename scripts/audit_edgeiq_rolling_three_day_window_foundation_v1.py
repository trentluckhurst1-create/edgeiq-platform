from __future__ import annotations

import argparse
import csv
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from edgeiq_three_day_window_v1_common import (
    DAY_KEYS,
    TIMEZONE_NAME,
    build_three_day_window,
    parse_override_date,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

WINDOW_PATH = DATA / "edgeiq_three_day_window_v1.json"
AUDIT_JSON = DATA / "edgeiq_rolling_three_day_universe_v1_audit.json"
AUDIT_TEXT = DATA / "edgeiq_rolling_three_day_universe_v1_audit.txt"
COVERAGE_CSV = DATA / "edgeiq_rolling_three_day_universe_v1_coverage.csv"

PASS_STATUS = "EDGEIQ_ROLLING_THREE_DAY_WINDOW_FOUNDATION_V1_AUDIT_PASS"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required file does not exist: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected JSON object in {path}")

    return payload


def validate_window_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append(
            {
                "check": name,
                "status": "PASS" if passed else "FAIL",
                "detail": detail,
            }
        )

    add(
        "schema_version",
        payload.get("schemaVersion") == "edgeiq_three_day_window_v1",
        str(payload.get("schemaVersion")),
    )

    add(
        "timezone",
        payload.get("timezone") == TIMEZONE_NAME,
        str(payload.get("timezone")),
    )

    dates = payload.get("dates")
    dates_valid = isinstance(dates, list) and len(dates) == 3

    add(
        "exactly_three_dates",
        dates_valid,
        f"count={len(dates) if isinstance(dates, list) else 'invalid'}",
    )

    if not dates_valid:
        return checks

    keys = [item.get("key") for item in dates if isinstance(item, dict)]
    values = [item.get("date") for item in dates if isinstance(item, dict)]
    offsets = [item.get("dayOffset") for item in dates if isinstance(item, dict)]

    add(
        "logical_keys",
        tuple(keys) == DAY_KEYS,
        f"keys={keys}",
    )

    add(
        "day_offsets",
        offsets == [0, 1, 2],
        f"offsets={offsets}",
    )

    add(
        "distinct_dates",
        len(values) == 3 and len(set(values)) == 3,
        f"dates={values}",
    )

    parsed_dates: list[date] = []

    try:
        parsed_dates = [date.fromisoformat(str(value)) for value in values]
        parse_pass = True
        parse_detail = "all dates are valid ISO dates"
    except Exception as exc:
        parse_pass = False
        parse_detail = str(exc)

    add(
        "iso_date_parse",
        parse_pass,
        parse_detail,
    )

    if parse_pass:
        add(
            "consecutive_dates",
            parsed_dates[1] == parsed_dates[0] + timedelta(days=1)
            and parsed_dates[2] == parsed_dates[0] + timedelta(days=2),
            f"dates={values}",
        )

    add(
        "top_level_today",
        payload.get("today") == values[0],
        f"today={payload.get('today')} dates[0]={values[0]}",
    )

    add(
        "top_level_tomorrow",
        payload.get("tomorrow") == values[1],
        f"tomorrow={payload.get('tomorrow')} dates[1]={values[1]}",
    )

    add(
        "top_level_day_plus_2",
        payload.get("dayPlus2") == values[2],
        f"dayPlus2={payload.get('dayPlus2')} dates[2]={values[2]}",
    )

    return checks


def simulate_rollover(
    simulation_start: date,
    simulation_days: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for offset in range(simulation_days):
        as_of = simulation_start + timedelta(days=offset)
        window = build_three_day_window(as_of).to_dict()

        dates = window["dates"]

        row = {
            "simulation_day": offset + 1,
            "as_of_date": as_of.isoformat(),
            "today": window["today"],
            "tomorrow": window["tomorrow"],
            "day_plus_2": window["dayPlus2"],
            "date_source": window["dateSource"],
            "timezone": window["timezone"],
            "status": "PASS",
        }

        expected = [
            as_of.isoformat(),
            (as_of + timedelta(days=1)).isoformat(),
            (as_of + timedelta(days=2)).isoformat(),
        ]

        actual = [item["date"] for item in dates]

        if actual != expected:
            row["status"] = "FAIL"

        rows.append(row)

    return rows


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    json.loads(temporary.read_text(encoding="utf-8"))
    temporary.replace(path)


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def write_csv_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")

    fields = [
        "simulation_day",
        "as_of_date",
        "today",
        "tomorrow",
        "day_plus_2",
        "date_source",
        "timezone",
        "status",
    ]

    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit the EDGEiQ canonical rolling three-day window."
    )

    parser.add_argument(
        "--simulation-start",
        default="2026-07-12",
        help="Simulation start date in YYYY-MM-DD format.",
    )

    parser.add_argument(
        "--simulation-days",
        type=int,
        default=5,
        help="Number of consecutive rollover days to simulate.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    simulation_start = parse_override_date(args.simulation_start)

    if simulation_start is None:
        raise RuntimeError("Simulation start date is required.")

    if args.simulation_days < 1:
        raise RuntimeError("Simulation days must be at least 1.")

    payload = read_json(WINDOW_PATH)
    checks = validate_window_payload(payload)

    simulation_rows = simulate_rollover(
        simulation_start,
        args.simulation_days,
    )

    checks_pass = all(item["status"] == "PASS" for item in checks)
    simulation_pass = all(
        item["status"] == "PASS"
        for item in simulation_rows
    )

    overall_pass = checks_pass and simulation_pass

    result = {
        "status": PASS_STATUS if overall_pass else "FAIL",
        "window": {
            "timezone": payload.get("timezone"),
            "dateSource": payload.get("dateSource"),
            "generatedAt": payload.get("generatedAt"),
            "today": payload.get("today"),
            "tomorrow": payload.get("tomorrow"),
            "dayPlus2": payload.get("dayPlus2"),
        },
        "checks": checks,
        "simulation": {
            "start": simulation_start.isoformat(),
            "days": args.simulation_days,
            "status": "PASS" if simulation_pass else "FAIL",
        },
    }

    text_lines = [
        result["status"],
        "",
        f"timezone={payload.get('timezone')}",
        f"date_source={payload.get('dateSource')}",
        f"generated_at={payload.get('generatedAt')}",
        f"today={payload.get('today')}",
        f"tomorrow={payload.get('tomorrow')}",
        f"day_plus_2={payload.get('dayPlus2')}",
        "",
        "CHECKS",
    ]

    for check in checks:
        text_lines.append(
            f"{check['status']} | {check['check']} | {check['detail']}"
        )

    text_lines.extend(
        [
            "",
            "ROLLOVER SIMULATION",
        ]
    )

    for row in simulation_rows:
        text_lines.append(
            " | ".join(
                [
                    row["status"],
                    f"as_of={row['as_of_date']}",
                    f"today={row['today']}",
                    f"tomorrow={row['tomorrow']}",
                    f"day_plus_2={row['day_plus_2']}",
                ]
            )
        )

    write_json_atomic(AUDIT_JSON, result)
    write_text_atomic(AUDIT_TEXT, "\n".join(text_lines) + "\n")
    write_csv_atomic(COVERAGE_CSV, simulation_rows)

    print(result["status"])
    print(f"window={WINDOW_PATH}")
    print(f"audit_json={AUDIT_JSON}")
    print(f"audit_text={AUDIT_TEXT}")
    print(f"coverage={COVERAGE_CSV}")

    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
