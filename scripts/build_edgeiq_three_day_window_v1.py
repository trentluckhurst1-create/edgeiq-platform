from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from edgeiq_three_day_window_v1_common import (
    DAY_KEYS,
    TIMEZONE_NAME,
    build_three_day_window,
    parse_override_date,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "public" / "data" / "edgeiq_three_day_window_v1.json"


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    validated = json.loads(
        temporary_path.read_text(encoding="utf-8")
    )

    if not isinstance(validated, dict):
        raise RuntimeError("Generated three-day window is not a JSON object.")

    temporary_path.replace(path)


def validate_payload(payload: dict[str, Any]) -> None:
    if payload.get("schemaVersion") != "edgeiq_three_day_window_v1":
        raise RuntimeError("Unexpected three-day window schema version.")

    if payload.get("timezone") != TIMEZONE_NAME:
        raise RuntimeError(
            f"Timezone must be {TIMEZONE_NAME}."
        )

    dates = payload.get("dates")

    if not isinstance(dates, list) or len(dates) != 3:
        raise RuntimeError(
            "Three-day window must contain exactly three date entries."
        )

    keys = tuple(
        item.get("key")
        for item in dates
        if isinstance(item, dict)
    )

    if keys != DAY_KEYS:
        raise RuntimeError(
            f"Unexpected logical day keys: {keys}"
        )

    iso_dates = [
        item.get("date")
        for item in dates
        if isinstance(item, dict)
    ]

    if len(set(iso_dates)) != 3:
        raise RuntimeError(
            "Three-day window dates must be distinct."
        )

    expected_offsets = [0, 1, 2]
    offsets = [
        item.get("dayOffset")
        for item in dates
        if isinstance(item, dict)
    ]

    if offsets != expected_offsets:
        raise RuntimeError(
            f"Unexpected day offsets: {offsets}"
        )

    if payload.get("today") != iso_dates[0]:
        raise RuntimeError("TODAY date does not match dates[0].")

    if payload.get("tomorrow") != iso_dates[1]:
        raise RuntimeError("TOMORROW date does not match dates[1].")

    if payload.get("dayPlus2") != iso_dates[2]:
        raise RuntimeError("DAY+2 date does not match dates[2].")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the canonical EDGEiQ rolling TODAY, TOMORROW "
            "and DAY+2 date-window contract."
        )
    )

    parser.add_argument(
        "--as-of-date",
        help=(
            "Optional YYYY-MM-DD test override. "
            "Production runs should omit this argument."
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    override_date = parse_override_date(args.as_of_date)

    window = build_three_day_window(override_date)
    payload = window.to_dict()

    validate_payload(payload)
    write_json_atomic(OUTPUT, payload)

    print("[EDGEIQ_THREE_DAY_WINDOW_V1] PASS")
    print(f"timezone={payload['timezone']}")
    print(f"date_source={payload['dateSource']}")
    print(f"today={payload['today']}")
    print(f"tomorrow={payload['tomorrow']}")
    print(f"day_plus_2={payload['dayPlus2']}")
    print(f"generated_at={payload['generatedAt']}")
    print(f"output={OUTPUT}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
