from __future__ import annotations

import os
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

ENV_DATE_OVERRIDE = "EDGEIQ_PIPELINE_DATE"


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
        payload = asdict(self)
        payload["dates"] = list(payload["dates"])
        return payload


def melbourne_now() -> datetime:
    return datetime.now(TIMEZONE)


def get_operational_today(
    *,
    now: datetime | None = None,
    override_date: date | None = None,
) -> tuple[date, str]:
    if override_date is not None:
        return override_date, "EXPLICIT_OVERRIDE"

    env_value = os.environ.get(ENV_DATE_OVERRIDE)
    env_override = parse_override_date(env_value)

    if env_override is not None:
        return env_override, f"ENV_OVERRIDE_{ENV_DATE_OVERRIDE}"

    runtime_now = now or melbourne_now()

    if runtime_now.tzinfo is None:
        runtime_now = runtime_now.replace(tzinfo=TIMEZONE)
    else:
        runtime_now = runtime_now.astimezone(TIMEZONE)

    return runtime_now.date(), "AUSTRALIA_MELBOURNE_CLOCK"


def build_operational_dates(today: date) -> tuple[date, date, date]:
    return (
        today,
        today + timedelta(days=1),
        today + timedelta(days=2),
    )


def resolve_as_of_date(as_of_date: date | None = None) -> tuple[date, str]:
    if as_of_date is not None:
        return get_operational_today(override_date=as_of_date)

    return get_operational_today()


def build_three_day_window(
    as_of_date: date | None = None,
) -> EdgeiqThreeDayWindow:
    today, date_source = resolve_as_of_date(as_of_date)

    today, tomorrow, day_plus_2 = build_operational_dates(today)

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
