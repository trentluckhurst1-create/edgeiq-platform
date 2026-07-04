from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUT = DATA / "edgeiq_frontend_contract_diagnostics.csv"

SOURCES = [
    {
        "file": "edgeiq_vic_three_day_meeting_universe.csv",
        "required": ["race_date", "track", "race_no", "horse", "meeting_key", "race_key"],
        "horse_required": True,
        "focus_required": False,
    },
    {
        "file": "edgeiq_active_race_selector.csv",
        "required": ["race_date", "track", "race_no", "meeting_key", "race_key", "default_ui_focus"],
        "horse_required": False,
        "focus_required": True,
    },
    {
        "file": "edgeiq_execution_engine_v4.csv",
        "required": ["race_date", "track", "race_no", "horse", "meeting_key", "race_key"],
        "horse_required": True,
        "focus_required": False,
    },
    {
        "file": "edgeiq_real_speed_map_positions.csv",
        "required": ["race_date", "track", "race_no", "horse", "meeting_key", "race_key"],
        "horse_required": True,
        "focus_required": False,
    },
]

FIELDS = [
    "built_at",
    "source_file",
    "rows",
    "required_columns_present",
    "missing_columns",
    "blank_race_date",
    "blank_track",
    "blank_race_no",
    "blank_horse",
    "unique_meetings",
    "unique_races",
    "status",
]


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null", "-"} else text


def clean_track(value: object) -> str:
    return " ".join(clean(value).upper().replace("|", " ").replace("_", " ").split())


def race_no(value: object) -> str:
    digits = "".join(ch for ch in clean(value) if ch.isdigit())
    return str(int(digits)) if digits else ""


def meeting_key(row: dict[str, str]) -> str:
    supplied = clean(row.get("meeting_key"))
    if supplied:
        return supplied
    return f"{clean(row.get('race_date'))}_{clean_track(row.get('track'))}"


def race_key(row: dict[str, str]) -> str:
    supplied = clean(row.get("race_key"))
    if supplied:
        return supplied
    return f"{meeting_key(row)}_R{race_no(row.get('race_no'))}"


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        return [], []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{int(datetime.now().timestamp() * 1000)}.tmp")
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def diagnose(source: dict[str, object]) -> dict[str, object]:
    filename = str(source["file"])
    path = DATA / filename
    rows, headers = read_csv(path)
    required = list(source["required"])
    missing = [column for column in required if column not in headers]
    blank_race_date = sum(1 for row in rows if not clean(row.get("race_date")))
    blank_track = sum(1 for row in rows if not clean(row.get("track")))
    blank_race_no = sum(1 for row in rows if not race_no(row.get("race_no")))
    blank_horse = sum(1 for row in rows if source["horse_required"] and not clean(row.get("horse")))
    meetings = {meeting_key(row) for row in rows if clean(row.get("race_date")) and clean(row.get("track"))}
    races = {race_key(row) for row in rows if clean(row.get("race_date")) and clean(row.get("track")) and race_no(row.get("race_no"))}
    focus_rows = sum(1 for row in rows if clean(row.get("default_ui_focus")).upper() == "YES")

    failures: list[str] = []
    if not rows:
        failures.append("no_rows")
    if missing:
        failures.append("missing_columns")
    if blank_race_date:
        failures.append("blank_race_date")
    if blank_track:
        failures.append("blank_track")
    if blank_race_no:
        failures.append("blank_race_no")
    if blank_horse:
        failures.append("blank_horse")
    if source["focus_required"] and focus_rows != 1:
        failures.append(f"default_focus_rows={focus_rows}")

    return {
        "built_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_file": filename,
        "rows": len(rows),
        "required_columns_present": "YES" if not missing else "NO",
        "missing_columns": "|".join(missing),
        "blank_race_date": blank_race_date,
        "blank_track": blank_track,
        "blank_race_no": blank_race_no,
        "blank_horse": blank_horse,
        "unique_meetings": len(meetings),
        "unique_races": len(races),
        "status": "OK" if not failures else "FAIL:" + "|".join(failures),
    }


def main() -> None:
    rows = [diagnose(source) for source in SOURCES]
    write_csv(OUT, rows)
    print("=" * 90)
    print("EDGEIQ FRONTEND CONTRACT DIAGNOSTICS")
    print("=" * 90)
    for row in rows:
        print(row)
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
