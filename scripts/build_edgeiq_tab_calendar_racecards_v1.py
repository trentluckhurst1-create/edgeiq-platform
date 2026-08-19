from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import pandas as pd

from build_edgeiq_vic_three_day_meeting_calendar_v1 import normalise_track


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
RAW = DATA / "tab_calendar_race_raw_v1"
RAW.mkdir(parents=True, exist_ok=True)

CALENDAR = DATA / "edgeiq_vic_three_day_meeting_calendar_v1.csv"

OUT = DATA / "edgeiq_tab_calendar_racecards_v1.csv"
OUT_VIC = DATA / "edgeiq_tab_calendar_racecards_vic_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_tab_calendar_racecards_summary_v1.csv"

OUTPUT_COLUMNS = [
    "scraped_at",
    "source",
    "api_url",
    "meeting_date",
    "race_date",
    "location",
    "meeting_name",
    "track",
    "venue_mnemonic",
    "race_type",
    "race_no",
    "race_name",
    "race_distance",
    "distance",
    "race_start_time_utc",
    "race_class_conditions",
    "race_class",
    "track_condition",
    "weather_condition",
    "race_status",
    "runner_no",
    "horse_no",
    "horse",
    "barrier",
    "jockey",
    "trainer",
    "weight",
    "claim",
    "last5",
    "tab_fixed_win",
    "tab_fixed_place",
    "tab_fixed_open_win",
    "tab_fixed_betting_status",
    "scratched_time",
    "tab_tote_win",
    "tab_tote_place",
    "tab_tote_betting_status",
    "early_speed_rating",
    "early_speed_band",
    "dfs_form_rating",
    "tech_form_rating",
    "total_rating_points",
    "silk_url",
    "flucs_json",
    "return_history_json",
]

SUMMARY_COLUMNS = [
    "race_date",
    "day_bucket",
    "target_track",
    "meeting_name",
    "matched_track",
    "venue_mnemonic",
    "race_no",
    "status",
    "runners",
    "api_url",
    "error",
]


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def pick(data: object, names: list[str]):
    if not isinstance(data, dict):
        return ""
    for name in names:
        value = data.get(name)
        if value not in [None, ""]:
            return value
    return ""


def fixed_block(runner: dict) -> dict:
    block = pick(runner, ["fixedOdds", "fixed", "fixedOddsPrice"])
    return block if isinstance(block, dict) else {}


def tote_block(runner: dict) -> dict:
    block = pick(runner, ["parimutuel", "tote"])
    return block if isinstance(block, dict) else {}


def fetch_json(url: str):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def with_optional_flags(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    query.setdefault("jurisdiction", ["VIC"])
    query.setdefault("returnPromo", ["true"])
    query.setdefault("returnOffers", ["true"])
    encoded = urllib.parse.urlencode(query, doseq=True)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, encoded, parsed.fragment))


def meetings_url(race_date: str) -> str:
    return f"https://api.beta.tab.com.au/v1/tab-info-service/racing/dates/{race_date}/meetings?jurisdiction=VIC"


def meeting_track_value(meeting: dict) -> str:
    base_name = clean(meeting.get("displayMeetingName") or meeting.get("meetingName"))
    track_condition = clean(meeting.get("trackCondition")).upper()
    combined = base_name
    if base_name and "SYNTHETIC" in track_condition and "SYNTHETIC" not in base_name.upper():
        combined = f"{base_name} SYNTHETIC"
    return normalise_track(combined)


def target_track_value(calendar_row: pd.Series) -> str:
    return normalise_track(clean(calendar_row.get("track")))


def is_vic_racing_meeting(meeting: dict) -> bool:
    return clean(meeting.get("location")).upper() == "VIC" and clean(meeting.get("raceType")).upper() == "R"


def load_meetings_for_date(race_date: str, cache: dict[str, list[dict]]) -> list[dict]:
    if race_date in cache:
        return cache[race_date]
    payload = fetch_json(meetings_url(race_date))
    meetings = payload.get("meetings") if isinstance(payload, dict) else payload
    cache[race_date] = meetings if isinstance(meetings, list) else []
    return cache[race_date]


def load_race_index_for_meeting(meeting: dict, race_index_cache: dict[str, list[dict]]) -> list[dict]:
    races = meeting.get("races") if isinstance(meeting.get("races"), list) else []
    if races and any(isinstance(race.get("_links"), dict) and race.get("_links", {}).get("self") for race in races):
        return races

    meeting_races_url = pick(meeting.get("_links") or {}, ["races"])
    if not meeting_races_url:
        return races

    meeting_races_url = with_optional_flags(clean(meeting_races_url))
    if meeting_races_url in race_index_cache:
        return race_index_cache[meeting_races_url]

    payload = fetch_json(meeting_races_url)
    indexed_races = payload.get("races") if isinstance(payload, dict) else payload
    race_index_cache[meeting_races_url] = indexed_races if isinstance(indexed_races, list) else []
    return race_index_cache[meeting_races_url]


def race_detail_url(race_meta: dict) -> str:
    links = race_meta.get("_links") if isinstance(race_meta.get("_links"), dict) else {}
    self_url = clean(links.get("self"))
    return with_optional_flags(self_url) if self_url else ""


def flatten(payload: dict, api_url: str, meeting_meta: dict, race_meta: dict) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    meeting_payload = payload.get("meeting") if isinstance(payload.get("meeting"), dict) else {}
    runners = payload.get("runners") if isinstance(payload.get("runners"), list) else []

    meeting_name = clean(
        payload.get("meetingName")
        or meeting_payload.get("meetingName")
        or meeting_meta.get("displayMeetingName")
        or meeting_meta.get("meetingName")
    )
    track = meeting_track_value(meeting_meta) or normalise_track(meeting_name)
    location = clean(payload.get("location") or meeting_payload.get("location") or meeting_meta.get("location"))
    venue_mnemonic = clean(
        payload.get("venueMnemonic")
        or meeting_payload.get("venueMnemonic")
        or meeting_meta.get("venueMnemonic")
    )

    for runner in runners:
        fixed = fixed_block(runner)
        tote = tote_block(runner)
        rows.append(
            {
                "scraped_at": datetime.now().isoformat(timespec="seconds"),
                "source": "TAB_API_CALENDAR",
                "api_url": api_url,
                "meeting_date": clean(
                    payload.get("meetingDate")
                    or meeting_payload.get("meetingDate")
                    or meeting_meta.get("meetingDate")
                ),
                "race_date": clean(
                    payload.get("meetingDate")
                    or meeting_payload.get("meetingDate")
                    or meeting_meta.get("meetingDate")
                ),
                "location": location,
                "meeting_name": meeting_name,
                "track": track,
                "venue_mnemonic": venue_mnemonic,
                "race_type": clean(payload.get("raceType") or meeting_meta.get("raceType")),
                "race_no": clean(payload.get("raceNumber") or payload.get("raceNo") or race_meta.get("raceNumber")),
                "race_name": clean(payload.get("raceName") or race_meta.get("raceName")),
                "race_distance": clean(payload.get("raceDistance") or race_meta.get("raceDistance")),
                "distance": clean(payload.get("raceDistance") or race_meta.get("raceDistance")),
                "race_start_time_utc": clean(payload.get("raceStartTime") or race_meta.get("raceStartTime")),
                "race_class_conditions": clean(
                    payload.get("raceClassConditions") or race_meta.get("raceClassConditions")
                ),
                "race_class": clean(payload.get("raceClassConditions") or race_meta.get("raceClassConditions")),
                "track_condition": clean(meeting_payload.get("trackCondition") or meeting_meta.get("trackCondition")),
                "weather_condition": clean(
                    meeting_payload.get("weatherCondition") or meeting_meta.get("weatherCondition")
                ),
                "race_status": clean(payload.get("raceStatus") or race_meta.get("raceStatus")),
                "runner_no": clean(pick(runner, ["runnerNumber", "runner_no", "number"])),
                "horse_no": clean(pick(runner, ["runnerNumber", "runner_no", "number"])),
                "horse": clean(pick(runner, ["runnerName", "name", "runner_name"])).upper(),
                "barrier": clean(pick(runner, ["barrierNumber", "barrier"])),
                "jockey": clean(
                    pick(runner, ["riderDriverFullName", "riderDriverName", "riderName", "jockey"])
                ),
                "trainer": clean(pick(runner, ["trainerFullName", "trainerName", "trainer"])),
                "weight": clean(runner.get("handicapWeight")),
                "claim": clean(runner.get("claimAmount")),
                "last5": clean(runner.get("last5Starts")),
                "tab_fixed_win": clean(pick(fixed, ["returnWin"])),
                "tab_fixed_place": clean(pick(fixed, ["returnPlace"])),
                "tab_fixed_open_win": clean(pick(fixed, ["returnWinOpen"])),
                "tab_fixed_betting_status": clean(pick(fixed, ["bettingStatus"])),
                "scratched_time": clean(pick(fixed, ["scratchedTime"])),
                "tab_tote_win": clean(pick(tote, ["returnWin"])),
                "tab_tote_place": clean(pick(tote, ["returnPlace"])),
                "tab_tote_betting_status": clean(pick(tote, ["bettingStatus"])),
                "early_speed_rating": clean(runner.get("earlySpeedRating")),
                "early_speed_band": clean(runner.get("earlySpeedRatingBand")),
                "dfs_form_rating": clean(runner.get("dfsFormRating")),
                "tech_form_rating": clean(runner.get("techFormRating")),
                "total_rating_points": clean(runner.get("totalRatingPoints")),
                "silk_url": clean(runner.get("silkURL")),
                "flucs_json": json.dumps(fixed.get("flucs", []), ensure_ascii=False),
                "return_history_json": json.dumps(fixed.get("returnHistory", []), ensure_ascii=False),
            }
        )

    return rows


def write_outputs(rows: list[dict[str, object]], attempts: list[dict[str, object]]) -> None:
    df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    if not df.empty:
        df = df.drop_duplicates(subset=["meeting_date", "track", "race_no", "runner_no"])
        df = df.sort_values(["meeting_date", "track", "race_no", "runner_no"])
    df.to_csv(OUT, index=False)

    if df.empty:
        vic = pd.DataFrame(columns=OUTPUT_COLUMNS)
    else:
        vic = df[df["location"].astype(str).str.upper().eq("VIC")].copy()
    vic.to_csv(OUT_VIC, index=False)

    summary_df = pd.DataFrame(attempts, columns=SUMMARY_COLUMNS)
    summary_df.to_csv(OUT_SUMMARY, index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--day-bucket", default="TODAY")
    parser.add_argument("--max-races", type=int, default=12)
    args = parser.parse_args()

    calendar = pd.read_csv(CALENDAR, dtype=str, keep_default_na=False).fillna("")
    targets = calendar[calendar["day_bucket"].astype(str).str.upper().eq(args.day_bucket.upper())].copy()

    meetings_cache: dict[str, list[dict]] = {}
    race_index_cache: dict[str, list[dict]] = {}
    all_rows: list[dict[str, object]] = []
    attempts: list[dict[str, object]] = []
    captured_races = 0

    for _, target in targets.iterrows():
        race_date = clean(target.get("race_date"))
        target_track = target_track_value(target)
        day_bucket = clean(target.get("day_bucket"))

        try:
            meetings = load_meetings_for_date(race_date, meetings_cache)
        except Exception as exc:
            attempts.append(
                {
                    "race_date": race_date,
                    "day_bucket": day_bucket,
                    "target_track": target_track,
                    "meeting_name": "",
                    "matched_track": "",
                    "venue_mnemonic": "",
                    "race_no": "",
                    "status": "MEETINGS_FETCH_FAIL",
                    "runners": 0,
                    "api_url": meetings_url(race_date),
                    "error": repr(exc),
                }
            )
            continue

        matched_meetings = [
            meeting
            for meeting in meetings
            if is_vic_racing_meeting(meeting) and meeting_track_value(meeting) == target_track
        ]

        if not matched_meetings:
            attempts.append(
                {
                    "race_date": race_date,
                    "day_bucket": day_bucket,
                    "target_track": target_track,
                    "meeting_name": "",
                    "matched_track": "",
                    "venue_mnemonic": "",
                    "race_no": "",
                    "status": "MEETING_NOT_FOUND",
                    "runners": 0,
                    "api_url": meetings_url(race_date),
                    "error": "",
                }
            )
            continue

        for meeting in matched_meetings:
            meeting_name = clean(meeting.get("displayMeetingName") or meeting.get("meetingName"))
            matched_track = meeting_track_value(meeting)
            venue_mnemonic = clean(meeting.get("venueMnemonic"))

            try:
                indexed_races = load_race_index_for_meeting(meeting, race_index_cache)
            except Exception as exc:
                attempts.append(
                    {
                        "race_date": race_date,
                        "day_bucket": day_bucket,
                        "target_track": target_track,
                        "meeting_name": meeting_name,
                        "matched_track": matched_track,
                        "venue_mnemonic": venue_mnemonic,
                        "race_no": "",
                        "status": "RACE_INDEX_FETCH_FAIL",
                        "runners": 0,
                        "api_url": clean(pick(meeting.get("_links") or {}, ["races"])),
                        "error": repr(exc),
                    }
                )
                continue

            if not indexed_races:
                attempts.append(
                    {
                        "race_date": race_date,
                        "day_bucket": day_bucket,
                        "target_track": target_track,
                        "meeting_name": meeting_name,
                        "matched_track": matched_track,
                        "venue_mnemonic": venue_mnemonic,
                        "race_no": "",
                        "status": "NO_RACE_INDEX",
                        "runners": 0,
                        "api_url": clean(pick(meeting.get("_links") or {}, ["races"])),
                        "error": "",
                    }
                )
                continue

            for race_meta in indexed_races:
                race_no = int(race_meta.get("raceNumber") or 0)
                if args.max_races and race_no > args.max_races:
                    continue

                detail_url = race_detail_url(race_meta)
                if not detail_url:
                    attempts.append(
                        {
                            "race_date": race_date,
                            "day_bucket": day_bucket,
                            "target_track": target_track,
                            "meeting_name": meeting_name,
                            "matched_track": matched_track,
                            "venue_mnemonic": venue_mnemonic,
                            "race_no": race_no,
                            "status": "RACE_DETAIL_URL_MISSING",
                            "runners": 0,
                            "api_url": "",
                            "error": "",
                        }
                    )
                    continue

                print("[TAB_CALENDAR]", race_date, matched_track, meeting_name, "R", race_no)

                try:
                    payload = fetch_json(detail_url)
                    runners = payload.get("runners") if isinstance(payload.get("runners"), list) else []
                    if not runners:
                        attempts.append(
                            {
                                "race_date": race_date,
                                "day_bucket": day_bucket,
                                "target_track": target_track,
                                "meeting_name": meeting_name,
                                "matched_track": matched_track,
                                "venue_mnemonic": venue_mnemonic,
                                "race_no": race_no,
                                "status": "NO_RUNNERS",
                                "runners": 0,
                                "api_url": detail_url,
                                "error": "",
                            }
                        )
                        continue

                    raw_name = f"{race_date}_{matched_track.replace(' ', '_')}_R{race_no}.json"
                    (RAW / raw_name).write_text(json.dumps(payload, indent=2), encoding="utf-8")

                    rows = flatten(payload, detail_url, meeting, race_meta)
                    all_rows.extend(rows)
                    captured_races += 1
                    attempts.append(
                        {
                            "race_date": race_date,
                            "day_bucket": day_bucket,
                            "target_track": target_track,
                            "meeting_name": meeting_name,
                            "matched_track": matched_track,
                            "venue_mnemonic": venue_mnemonic,
                            "race_no": race_no,
                            "status": "CAPTURED",
                            "runners": len(rows),
                            "api_url": detail_url,
                            "error": "",
                        }
                    )
                except Exception as exc:
                    attempts.append(
                        {
                            "race_date": race_date,
                            "day_bucket": day_bucket,
                            "target_track": target_track,
                            "meeting_name": meeting_name,
                            "matched_track": matched_track,
                            "venue_mnemonic": venue_mnemonic,
                            "race_no": race_no,
                            "status": "FETCH_FAIL",
                            "runners": 0,
                            "api_url": detail_url,
                            "error": repr(exc),
                        }
                    )

    attempts.append(
        {
            "race_date": "",
            "day_bucket": args.day_bucket.upper(),
            "target_track": "SUMMARY",
            "meeting_name": "",
            "matched_track": "",
            "venue_mnemonic": "",
            "race_no": "",
            "status": "SUMMARY",
            "runners": len(all_rows),
            "api_url": str(OUT),
            "error": f"captured_races={captured_races}",
        }
    )

    write_outputs(all_rows, attempts)

    print("[TAB_CALENDAR] captured_races", captured_races)
    print("[TAB_CALENDAR] runner_rows", len(all_rows))
    print("[TAB_CALENDAR] wrote", OUT)
    print("[TAB_CALENDAR] wrote", OUT_VIC)
    print("[TAB_CALENDAR] wrote", OUT_SUMMARY)


if __name__ == "__main__":
    main()
