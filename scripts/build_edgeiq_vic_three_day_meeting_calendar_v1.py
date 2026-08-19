from __future__ import annotations

import csv
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from edgeiq_three_day_window_v1_common import (
    TIMEZONE,
    build_three_day_window,
)


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SOURCE = DATA / "edgeiq_racingcom_historical_calendar_backfill_v1.csv"
CALENDAR_OUT = DATA / "edgeiq_vic_three_day_meeting_calendar_v1.csv"

FIELDS = [
    "race_date",
    "track",
    "meeting_type",
    "day_bucket",
]

LOCAL_TZ = TIMEZONE

VIC_TRACKS = {
    "ARARAT",
    "AVOCA",
    "BAIRNSDALE",
    "BALLARAT",
    "BALLARAT SYNTHETIC",
    "BALNARRING",
    "BENDIGO",
    "BENALLA",
    "BET365 STAWELL",
    "CAULFIELD",
    "CAULFIELD HEATH",
    "CASTERTON",
    "COLAC",
    "CRANBOURNE",
    "DONALD",
    "DUNKELD",
    "ECHUCA",
    "FLEMINGTON",
    "GEELONG",
    "HAMILTON",
    "HANGING ROCK",
    "HORSHAM",
    "KILMORE",
    "KYNETON",
    "MILDURA",
    "MOE",
    "MOONEE VALLEY",
    "MORNINGTON",
    "MORTLAKE",
    "MURTOA",
    "PAKENHAM",
    "PAKENHAM SYNTHETIC",
    "PENSHURST",
    "SALE",
    "SANDOWN",
    "SEYMOUR",
    "ST ARNAUD",
    "STAWELL",
    "SWAN HILL",
    "TERANG",
    "THE VALLEY",
    "TOWONG",
    "TRARALGON",
    "WANGARATTA",
    "WARRACKNABEAL",
    "WARRNAMBOOL",
    "WERRIBEE",
    "WODONGA",
    "YARRA VALLEY",
}

TRACK_ALIASES = {
    "SPORTSBET BALLARAT SYN": "BALLARAT SYNTHETIC",
    "SPORTSBET BALLARAT SYNTHETIC": "BALLARAT SYNTHETIC",
    "SPORTSBET-BALLARAT SYN": "BALLARAT SYNTHETIC",
    "SPORTSBET-BALLARAT SYNTHETIC": "BALLARAT SYNTHETIC",
    "BALLARAT SYN": "BALLARAT SYNTHETIC",
    "BALLARAT SYNTHETIC": "BALLARAT SYNTHETIC",
    "SOUTHSIDE PAKENHAM SYNTHETIC": "PAKENHAM SYNTHETIC",
    "PAKENHAM SYNTHETIC": "PAKENHAM SYNTHETIC",
}

MEETING_TYPE_MAP = {
    "COUNTRYMEET": "COUNTRY",
    "METROMEET": "METRO",
    "PROVINCIALMEET": "PROVINCIAL",
    "PICNICMEET": "PICNIC",
    "JUMPSMEET": "JUMPS",
}


def now_local() -> datetime:
    return datetime.now(LOCAL_TZ)


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"", "nan", "none", "null", "undefined"} else text


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    except Exception:
        return []


def write_calendar_output(rows: list[dict[str, object]], path: Path = CALENDAR_OUT) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{int(datetime.now().timestamp() * 1000)}.tmp")
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def parse_date(value: object) -> date | None:
    text = clean(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=LOCAL_TZ)
        return parsed.astimezone(LOCAL_TZ).date()
    except ValueError:
        return None


def normalise_track(value: object) -> str:
    text = clean(value).upper()
    if not text:
        return ""
    text = text.replace("_", " ").replace("|", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if text in TRACK_ALIASES:
        return TRACK_ALIASES[text]
    if "BALLARAT" in text and ("SYN" in text or "SYNTHETIC" in text):
        return "BALLARAT SYNTHETIC"
    if "PAKENHAM" in text and ("SYN" in text or "SYNTHETIC" in text):
        return "PAKENHAM SYNTHETIC"
    text = re.sub(r"\b(SPORTSBET|BET365|LADBROKES|TAB|RACING\.COM|RACING|SOUTHSIDE)\b", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return TRACK_ALIASES.get(text, text)


def meeting_key_value(race_date: object, track: object) -> str:
    return f"{clean(race_date)}_{normalise_track(track)}"


def day_bucket_for_date(race_date: date, today: date | None = None) -> str:
    local_today = today or now_local().date()
    delta = (race_date - local_today).days
    if delta == 0:
        return "TODAY"
    if delta == 1:
        return "TOMORROW"
    if delta == 2:
        return "DAY+2"
    return "OUTSIDE_WINDOW"


def meeting_type_value(row: dict[str, str]) -> str:
    raw = clean(row.get("meeting_type") or row.get("event_type") or row.get("meet_type")).upper()
    if not raw:
        return "UNKNOWN"
    compact = re.sub(r"[^A-Z0-9]", "", raw)
    if compact in MEETING_TYPE_MAP:
        return MEETING_TYPE_MAP[compact]
    return raw.replace("_", " ").strip()


def is_victorian_meeting(row: dict[str, str], track: str) -> bool:
    state = clean(row.get("state")).upper()
    if state == "VIC":
        return True
    return track in VIC_TRACKS


def is_usable_meeting(row: dict[str, str]) -> bool:
    if clean(row.get("is_trial")).upper() == "TRUE":
        return False
    if clean(row.get("is_jumpout")).upper() == "TRUE":
        return False
    if clean(row.get("is_abandoned")).upper() == "TRUE":
        return False
    return True


def build_calendar_rows(today: date | None = None) -> list[dict[str, object]]:
    local_today = today or now_local().date()
    max_date = local_today + timedelta(days=2)
    rows = read_csv(SOURCE)
    deduped: dict[tuple[str, str], dict[str, object]] = {}

    for row in rows:
        race_date = parse_date(row.get("meeting_date") or row.get("race_date") or row.get("date"))
        if race_date is None or race_date < local_today or race_date > max_date:
            continue

        track = normalise_track(row.get("track"))
        if not track or not is_victorian_meeting(row, track) or not is_usable_meeting(row):
            continue

        key = (race_date.isoformat(), track)
        current = deduped.get(key)
        candidate = {
            "race_date": race_date.isoformat(),
            "track": track,
            "meeting_type": meeting_type_value(row),
            "day_bucket": day_bucket_for_date(race_date, local_today),
        }
        if current is None:
            deduped[key] = candidate
            continue
        if current["meeting_type"] == "UNKNOWN" and candidate["meeting_type"] != "UNKNOWN":
            deduped[key] = candidate

    output = list(deduped.values())
    output.sort(
        key=lambda row: (
            {"TODAY": 0, "TOMORROW": 1, "DAY+2": 2}.get(str(row["day_bucket"]), 9),
            str(row["race_date"]),
            str(row["track"]),
        )
    )
    return output


def main() -> None:
    rows = build_calendar_rows()
    write_calendar_output(rows)

    print("=" * 90)
    print("EDGEIQ VIC THREE DAY MEETING CALENDAR V1")
    print("=" * 90)
    print(f"meetings={len(rows)}")
    print(f"today={sum(1 for row in rows if row['day_bucket'] == 'TODAY')}")
    print(f"tomorrow={sum(1 for row in rows if row['day_bucket'] == 'TOMORROW')}")
    print(f"day_plus_2={sum(1 for row in rows if row['day_bucket'] == 'DAY+2')}")
    print(f"wrote={CALENDAR_OUT}")


if __name__ == "__main__":
    main()
