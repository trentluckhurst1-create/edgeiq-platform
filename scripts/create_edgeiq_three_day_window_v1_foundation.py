from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
DATA = ROOT / "public" / "data"

COMMON_PATH = SCRIPTS / "edgeiq_three_day_window_v1_common.py"
BUILDER_PATH = SCRIPTS / "build_edgeiq_three_day_window_v1.py"

COMMON_SOURCE = r'''from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TIMEZONE_NAME = "Australia/Melbourne"
TIMEZONE = ZoneInfo(TIMEZONE_NAME)

DAY_KEYS = (
    "TODAY",
    "TOMORROW",
    "DAY_PLUS_2",
)


@dataclass(frozen=True)
class EdgeiqThreeDayDate:
    key: str
    date: str
    dayOffset: int


@dataclass(frozen=True)
class EdgeiqThreeDayWindow:
    schemaVersion: str
    timezone: str
    generatedAt: str
    dateSource: str
    today: str
    tomorrow: str
    dayPlus2: str
    dates: tuple[EdgeiqThreeDayDate, EdgeiqThreeDayDate, EdgeiqThreeDayDate]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def melbourne_now() -> datetime:
    return datetime.now(TIMEZONE)


def resolve_as_of_date(as_of_date: date | None = None) -> tuple[date, str]:
    if as_of_date is not None:
        return as_of_date, "TEST_OVERRIDE"

    return melbourne_now().date(), "AUSTRALIA_MELBOURNE_CLOCK"


def build_three_day_window(
    as_of_date: date | None = None,
) -> EdgeiqThreeDayWindow:
    today, date_source = resolve_as_of_date(as_of_date)

    tomorrow = today + timedelta(days=1)
    day_plus_2 = today + timedelta(days=2)

    generated_at = melbourne_now().isoformat(timespec="seconds")

    return EdgeiqThreeDayWindow(
        schemaVersion="edgeiq_three_day_window_v1",
        timezone=TIMEZONE_NAME,
        generatedAt=generated_at,
        dateSource=date_source,
        today=today.isoformat(),
        tomorrow=tomorrow.isoformat(),
        dayPlus2=day_plus_2.isoformat(),
        dates=(
            EdgeiqThreeDayDate(
                key="TODAY",
                date=today.isoformat(),
                dayOffset=0,
            ),
            EdgeiqThreeDayDate(
                key="TOMORROW",
                date=tomorrow.isoformat(),
                dayOffset=1,
            ),
            EdgeiqThreeDayDate(
                key="DAY_PLUS_2",
                date=day_plus_2.isoformat(),
                dayOffset=2,
            ),
        ),
    )


def parse_override_date(value: str | None) -> date | None:
    if value is None:
        return None

    cleaned = value.strip()

    if not cleaned:
        return None

    return date.fromisoformat(cleaned)
'''

BUILDER_SOURCE = r'''from __future__ import annotations

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
'''


def write_new_file(path: Path, content: str) -> None:
    if path.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing file: {path}"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    write_new_file(COMMON_PATH, COMMON_SOURCE)
    write_new_file(BUILDER_PATH, BUILDER_SOURCE)

    print("[EDGEIQ_THREE_DAY_WINDOW_V1_FOUNDATION] CREATED")
    print(f"common={COMMON_PATH}")
    print(f"builder={BUILDER_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
