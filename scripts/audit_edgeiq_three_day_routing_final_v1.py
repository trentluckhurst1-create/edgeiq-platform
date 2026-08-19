from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
WEATHER = DATA / "edgeiq_metropolitan_weather_v1.json"
TXT_OUT = DATA / "edgeiq_three_day_routing_final_audit.txt"
JSON_OUT = DATA / "edgeiq_three_day_routing_final_audit.json"

RACE_FILE = ROOT / "src" / "edgeiq-os" / "race" / "RaceFileV3.tsx"
MEETINGS_WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingsWorkspace.tsx"
MEETING_WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"
RACE_WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx"

REQUIRED_DATES = {"2026-07-10", "2026-07-11", "2026-07-12"}
VICTORIAN_KEYS = {
    "ARARAT",
    "BAIRNSDALE",
    "BALLARAT",
    "BALNARRING",
    "BENALLA",
    "BENDIGO",
    "CAULFIELD",
    "COLAC",
    "CRANBOURNE",
    "DONALD",
    "ECHUCA",
    "FLEMINGTON",
    "GEELONG",
    "HAMILTON",
    "HORSHAM",
    "KERANG",
    "KILMORE",
    "KYNETON",
    "MANSFIELD",
    "MOE",
    "MOONEE VALLEY",
    "MORNINGTON",
    "MURTOA",
    "PAKENHAM",
    "SALE",
    "SANDOWN",
    "SEYMOUR",
    "ST ARNAUD",
    "STAWELL",
    "SWAN HILL",
    "TERANG",
    "TOWONG",
    "WANGARATTA",
    "WARRACKNABEAL",
    "WARRNAMBOOL",
    "WERRIBEE",
    "YARRA VALLEY",
    "YEA",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def check(name: str, condition: bool, details: object | None = None) -> dict[str, object]:
    return {
        "name": name,
        "status": "PASS" if condition else "FAIL",
        "details": details,
    }


def normalise_meeting(value: object) -> str:
    text = str(value or "").upper().strip()
    text = re.sub(r"^(SPORTSBET|LADBROKES|BET365)[-\s]+", "", text)
    text = re.sub(r"\s+", " ", text)
    aliases = {
        "CAULFIELD HEATH": "CAULFIELD",
        "SANDOWN HILLSIDE": "SANDOWN",
        "SANDOWN LAKESIDE": "SANDOWN",
        "LADBROKES PARK": "SANDOWN",
        "LADBROKES PARK HILLSIDE": "SANDOWN",
        "LADBROKES PARK LAKESIDE": "SANDOWN",
        "BALLARAT SYNTHETIC": "BALLARAT",
        "GEELONG SYNTHETIC": "GEELONG",
    }
    return aliases.get(text, text)


def main() -> None:
    catalog = load_json(CATALOG)
    weather = load_json(WEATHER)
    race_file_source = read(RACE_FILE)
    meetings_source = read(MEETINGS_WORKSPACE)
    meeting_source = read(MEETING_WORKSPACE)
    race_workspace_source = read(RACE_WORKSPACE)

    meetings = catalog.get("meetings", [])
    meeting_keys = [meeting.get("meetingKey") for meeting in meetings]
    race_keys = [
        race.get("raceKey")
        for meeting in meetings
        for race in meeting.get("races", [])
    ]
    duplicate_meeting_keys = sum(count - 1 for count in Counter(meeting_keys).values() if count > 1)
    duplicate_race_keys = sum(count - 1 for count in Counter(race_keys).values() if count > 1)
    dates = set(catalog.get("dates", []))
    actual_meeting_dates = set(meeting.get("date") for meeting in meetings)
    invalid_meetings = [
        meeting
        for meeting in meetings
        if normalise_meeting(meeting.get("providerMeetingKey") or meeting.get("meeting")) not in VICTORIAN_KEYS
    ]
    caulfield = next(
        (
            meeting
            for meeting in meetings
            if meeting.get("date") == "2026-07-11"
            and normalise_meeting(meeting.get("providerMeetingKey") or meeting.get("meeting")) == "CAULFIELD"
        ),
        None,
    )
    caulfield_races = caulfield.get("races", []) if caulfield else []
    caulfield_runner_count = sum(len(race.get("runners", [])) for race in caulfield_races)
    race_number_failures = [
        race.get("raceKey")
        for meeting in meetings
        for race in meeting.get("races", [])
        if not isinstance(race.get("raceNumber"), int) or race.get("raceNumber") <= 0
    ]
    runner_counts = {
        f"{meeting.get('date')}|{meeting.get('providerMeetingKey')}": sum(
            len(race.get("runners", [])) for race in meeting.get("races", [])
        )
        for meeting in meetings
    }

    weather_records = weather.get("records", [])
    caulfield_weather = next(
        (
            record
            for record in weather_records
            if normalise_meeting(record.get("meeting_key") or record.get("meeting") or record.get("course"))
            == "CAULFIELD"
        ),
        None,
    )
    weather_provider = caulfield_weather.get("provider") if caulfield_weather else None

    checks = [
        check("required dates exist", REQUIRED_DATES.issubset(dates) and REQUIRED_DATES.issubset(actual_meeting_dates), sorted(dates)),
        check("Victorian-only meetings", len(invalid_meetings) == 0, [meeting.get("meeting") for meeting in invalid_meetings]),
        check("Caulfield exists on 2026-07-11", caulfield is not None),
        check("CAULFIELD_RACES_GREATER_THAN_ZERO", len(caulfield_races) > 0, len(caulfield_races)),
        check("runner counts are reported", all(value >= 0 for value in runner_counts.values()), runner_counts),
        check("Caulfield runner count greater than zero", caulfield_runner_count > 0, caulfield_runner_count),
        check("every race has a valid race number", len(race_number_failures) == 0, race_number_failures),
        check("DUPLICATE_MEETING_KEYS_ZERO", duplicate_meeting_keys == 0, duplicate_meeting_keys),
        check("DUPLICATE_RACE_KEYS_ZERO", duplicate_race_keys == 0, duplicate_race_keys),
        check("weather record exists for CAULFIELD", caulfield_weather is not None),
        check("CAULFIELD_WEATHER_ROUTE_PASS", weather_provider == "TURFTRAX_WDV", weather_provider),
        check("RaceFileV3 contains selectedMeeting state", "useState<ThreeDayMeeting | null>" in race_file_source and "setSelectedMeeting" in race_file_source),
        check("RaceFileV3 contains selectedRace state", "useState<ThreeDayRace | null>" in race_file_source and "setSelectedRace" in race_file_source),
        check("RaceFileV3 derives active file from selected race", "buildActiveRaceFile(selectedMeeting, selectedRace)" in race_file_source),
        check("MeetingsWorkspace uses catalogue", "loadThreeDayCatalog" in meetings_source and "edgeiq_three_day_product_catalog" not in meetings_source),
        check("MeetingWorkspace receives selected meeting", "meeting: ThreeDayMeeting" in meeting_source and "MeetingWeatherWorkspace" in meeting_source),
        check("selected race field reaches RaceWorkspace", "field={activeFile.field}" in race_file_source and "<RaceWorkspace" in race_file_source),
        check("selected race field reaches MapWorkspace through RaceWorkspace", "<MapWorkspace" in race_workspace_source and "field={field}" in race_workspace_source),
        check("selected race field reaches Form Guide", 'tab === "FORM GUIDE"' in race_workspace_source and "field.map" in race_workspace_source),
        check("no static old MeetingsWorkspace props remain", "<MeetingsWorkspace" in race_file_source and "raceBook={" not in race_file_source.split("<MeetingsWorkspace", 1)[1].split("/>", 1)[0]),
        check("no static old MeetingWorkspace field prop remains", "<MeetingWorkspace" in race_file_source and "field={" not in race_file_source.split("<MeetingWorkspace", 1)[1].split("/>", 1)[0]),
    ]

    failed = [item for item in checks if item["status"] != "PASS"]
    result = "THREE_DAY_ROUTING_FINAL_AUDIT_PASS" if not failed else "THREE_DAY_ROUTING_FINAL_AUDIT_FAIL"

    output = {
        "result": result,
        "catalogue": {
            "dates": catalog.get("dates", []),
            "meeting_count": len(meetings),
            "race_count": len(race_keys),
            "runner_count": sum(runner_counts.values()),
            "counts_by_date": {
                date: {
                    "meetings": sum(1 for meeting in meetings if meeting.get("date") == date),
                    "races": sum(len(meeting.get("races", [])) for meeting in meetings if meeting.get("date") == date),
                    "runners": sum(
                        len(race.get("runners", []))
                        for meeting in meetings
                        if meeting.get("date") == date
                        for race in meeting.get("races", [])
                    ),
                }
                for date in sorted(REQUIRED_DATES)
            },
            "caulfield_races": len(caulfield_races),
            "caulfield_runners": caulfield_runner_count,
            "duplicate_meeting_keys": duplicate_meeting_keys,
            "duplicate_race_keys": duplicate_race_keys,
        },
        "weather": {
            "caulfield_provider": weather_provider,
            "caulfield_status": caulfield_weather.get("source_status") if caulfield_weather else None,
            "caulfield_track_rating": caulfield_weather.get("official_track_rating") if caulfield_weather else None,
        },
        "checks": checks,
    }

    JSON_OUT.write_text(json.dumps(output, indent=2), encoding="utf-8")

    lines = [
        "EDGEIQ THREE-DAY ROUTING FINAL AUDIT",
        "=" * 44,
        f"RESULT: {result}",
        "",
        f"Meetings: {output['catalogue']['meeting_count']}",
        f"Races: {output['catalogue']['race_count']}",
        f"Runners: {output['catalogue']['runner_count']}",
        f"Caulfield races: {len(caulfield_races)}",
        f"Caulfield runners: {caulfield_runner_count}",
        f"Caulfield weather provider: {weather_provider}",
        "",
    ]

    for item in checks:
        lines.append(f"{item['status']}: {item['name']} | {item['details']}")

    TXT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
