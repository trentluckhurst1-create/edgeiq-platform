from __future__ import annotations

import csv
import json
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DATA.mkdir(parents=True, exist_ok=True)

OUT_MEETING = DATA / "edgeiq_graphql_meeting_replay_v1.json"
OUT_RACELIST = DATA / "edgeiq_graphql_racelist_replay_v1.json"
OUT_RACES = DATA / "edgeiq_graphql_races_replay_v1.json"
OUT_RESULTS = DATA / "edgeiq_graphql_results_replay_v1.json"
OUT_SUMMARY = DATA / "edgeiq_graphql_endpoint_replay_v1_summary.csv"
OUT_RUNNERS = DATA / "edgeiq_graphql_flemington_20250101_results_sample_v1.csv"

GRAPHQL = "https://graphql.rmdprod.racing.com/"

VENUE_SLUG = "flemington"
RACE_DATE = "2025-01-01"
RACE_NO = 1

HEADERS = {
    "User-Agent": "EDGEiQ-Racing/1.0 graphql-replay-audit",
    "Accept": "application/json,text/plain,*/*",
    "Referer": f"https://www.racing.com/form/{RACE_DATE}/{VENUE_SLUG}/race/{RACE_NO}",
}


def gql(query: str, variables: dict) -> dict:
    params = {
        "query": query,
        "variables": json.dumps(variables, separators=(",", ":")),
    }
    url = GRAPHQL + "?" + urllib.parse.urlencode(params)
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return r.json()


def save_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def clean(v):
    return "" if v is None else str(v).strip()


def main():
    built_at = datetime.now(timezone.utc).isoformat()

    q_meet_lookup = """
    query GetMeetingByVenueDateTrial($venueName: String, $date: String, $isTrial: Int, $isJumpOut: Int) {
      GetMeetingByVenueDateTrial(venueName: $venueName, date: $date, isTrial: $isTrial, isJumpOut: $isJumpOut) {
        id date venueName venueCode meetUrl isTrial isJumpOut
      }
    }
    """

    meet_lookup = gql(q_meet_lookup, {
        "venueName": VENUE_SLUG,
        "date": RACE_DATE,
        "isTrial": 0,
        "isJumpOut": 0,
    })

    meet_obj = (meet_lookup.get("data") or {}).get("GetMeetingByVenueDateTrial") or {}
    meet_code = clean(meet_obj.get("id"))

    q_meeting = """
    query getMeeting_CD($meetCode: ID!) {
      getMeeting(id: $meetCode) {
        id track venue venueName venueCode venueAbbr trackName state date
        trackRating trackCondition railPosition previousRailPosition
        weather weatherAirTemp weatherRain weatherWindDirection weatherWindSpeed
        penetrometer rainfall trackInfo stewardsReportUrl
        hasRunners hasRaceList hasStewards status
        trackConditions { raceNumber condition arrowIndicator }
        previousRailPositions { meetCode meetDate railPosition trackCondition trackRating comments }
      }
    }
    """

    q_racelist = """
    query getRaceNumberList_CD($meetCode: ID!) {
      getNoCacheRacesForMeet(meetCode: $meetCode) {
        id raceNumber raceStatus distance time name nameForm
        trackCondition trackRating condition rdcClass class group
        prizeMoney totalPrizeMoney hasSectionals hasTips hasSpeedMap
        hasResults hasStewards hasHistory hasField hasFullForm
        trackCode raceTime standardTimeDifference stewardsReportUrl
        formRaceEntries { horseName position winningTime standardTimeDifference }
      }
    }
    """

    q_races = """
    query getRacesForMeet_CD($meetCode: ID!) {
      getRacesForMeet(meetCode: $meetCode) {
        id condition rdcClass class group raceNumber raceStatus distance time name nameForm
        isTrial isJumpOut
        meet {
          meetUrl trackMap trackCondition straight trackRating railPosition previousRailPosition weather state
        }
        formRaceEntries {
          id meetCode raceNumber position barrierNumber liveBarrierNumber scratched
          raceEntryNumber weight finish finishAbv horseName horseCountry emergency emergencyNumber
          horseCode trainerName jockeyName trainerCode jockeyCode margin winningTime startingPrice
          apprenticeCanClaim apprenticeAllowedClaim gearChanges
          horse { id lastFive silkUrl stats { starts firsts seconds thirds } }
          odds { providerCode oddsPlace oddsWin oddsIsFavouriteWin oddsIsMarketMover flucsWin { updateTime amount } }
        }
      }
    }
    """

    q_results = """
    query getRaceResults_CD($meetCode: ID!, $raceNumber: Int!) {
      getRaceForm(meetCode: $meetCode, raceNumber: $raceNumber) {
        id meetCode raceNumber raceStatus rdcClass isTrial isJumpOut photoFinish
        venue { venueName state }
        videoItems { id contenttype poster }
        formRaceEntries {
          id meetCode raceNumber position barrierNumber liveBarrierNumber prizeMoney scratched
          startingPrice raceEntryNumber weight margin winningTime finish finishAbv
          horseName horseCode horseCountry horseUrl silkUrl
          jockeyName jockeyCode jockeyUrl trainerName trainerCode trainerUrl
          positionAt400 positionAt400Abv positionAt800 positionAt800Abv
          bettingFluctuationsPriceOpen bettingFluctuationsPriceMoveOne bettingFluctuationsPriceMoveTwo
          comment commentShort commentStewards gearChanges
          odds { providerCode oddsPlace oddsWin oddsIsFavouriteWin oddsIsMarketMover flucsWin { updateTime amount } }
          horse { id lastFive silkUrl stats { key starts firsts seconds thirds } }
        }
      }
      GetBettingData(meetCode: $meetCode, raceNumber: $raceNumber) {
        exotics { poolStatusCode wageringProduct selections amount }
      }
    }
    """

    meeting = gql(q_meeting, {"meetCode": meet_code})
    racelist = gql(q_racelist, {"meetCode": meet_code})
    races = gql(q_races, {"meetCode": meet_code})
    results = gql(q_results, {"meetCode": meet_code, "raceNumber": RACE_NO})

    save_json(OUT_MEETING, {"meet_lookup": meet_lookup, "meeting": meeting})
    save_json(OUT_RACELIST, racelist)
    save_json(OUT_RACES, races)
    save_json(OUT_RESULTS, results)

    meeting_obj = (meeting.get("data") or {}).get("getMeeting") or {}
    race_list = (racelist.get("data") or {}).get("getNoCacheRacesForMeet") or []
    race_full = (results.get("data") or {}).get("getRaceForm") or {}
    entries = race_full.get("formRaceEntries") or []

    runner_fields = [
        "race_date","track","meet_code","race_no","horse","horse_code",
        "finish","margin","starting_price","barrier","jockey","trainer",
        "position_800","position_400","weight","scratched","winning_time",
        "race_entry_number","built_at"
    ]

    with OUT_RUNNERS.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=runner_fields)
        w.writeheader()
        for e in entries:
            w.writerow({
                "race_date": RACE_DATE,
                "track": clean(meeting_obj.get("venueName") or meeting_obj.get("trackName") or meeting_obj.get("venue")),
                "meet_code": meet_code,
                "race_no": RACE_NO,
                "horse": clean(e.get("horseName")),
                "horse_code": clean(e.get("horseCode")),
                "finish": clean(e.get("finish") or e.get("position")),
                "margin": clean(e.get("margin")),
                "starting_price": clean(e.get("startingPrice")),
                "barrier": clean(e.get("barrierNumber") or e.get("liveBarrierNumber")),
                "jockey": clean(e.get("jockeyName")),
                "trainer": clean(e.get("trainerName")),
                "position_800": clean(e.get("positionAt800")),
                "position_400": clean(e.get("positionAt400")),
                "weight": clean(e.get("weight")),
                "scratched": clean(e.get("scratched")),
                "winning_time": clean(e.get("winningTime")),
                "race_entry_number": clean(e.get("raceEntryNumber")),
                "built_at": built_at,
            })

    summary = [
        {"metric": "status", "value": "EDGEIQ_GRAPHQL_ENDPOINT_REPLAY_V1_BUILT"},
        {"metric": "venue_slug", "value": VENUE_SLUG},
        {"metric": "race_date", "value": RACE_DATE},
        {"metric": "meet_code", "value": meet_code},
        {"metric": "meeting_venue", "value": clean(meeting_obj.get("venueName") or meeting_obj.get("trackName"))},
        {"metric": "track_condition", "value": clean(meeting_obj.get("trackCondition"))},
        {"metric": "track_rating", "value": clean(meeting_obj.get("trackRating"))},
        {"metric": "rail_position", "value": clean(meeting_obj.get("railPosition"))},
        {"metric": "previous_rail_position", "value": clean(meeting_obj.get("previousRailPosition"))},
        {"metric": "weather", "value": clean(meeting_obj.get("weather"))},
        {"metric": "penetrometer", "value": clean(meeting_obj.get("penetrometer"))},
        {"metric": "rainfall", "value": clean(meeting_obj.get("rainfall"))},
        {"metric": "race_count", "value": len(race_list)},
        {"metric": "race_numbers", "value": "|".join(str(r.get("raceNumber")) for r in race_list)},
        {"metric": "race_1_runner_rows", "value": len(entries)},
        {"metric": "rows_with_horse", "value": sum(1 for e in entries if clean(e.get("horseName")))},
        {"metric": "rows_with_trainer", "value": sum(1 for e in entries if clean(e.get("trainerName")))},
        {"metric": "rows_with_jockey", "value": sum(1 for e in entries if clean(e.get("jockeyName")))},
        {"metric": "rows_with_sp", "value": sum(1 for e in entries if clean(e.get("startingPrice")))},
        {"metric": "rows_with_barrier", "value": sum(1 for e in entries if clean(e.get("barrierNumber") or e.get("liveBarrierNumber")))},
        {"metric": "rows_with_finish", "value": sum(1 for e in entries if clean(e.get("finish") or e.get("position")))},
        {"metric": "rows_with_margin", "value": sum(1 for e in entries if clean(e.get("margin")))},
        {"metric": "rows_with_position_800", "value": sum(1 for e in entries if clean(e.get("positionAt800")))},
        {"metric": "rows_with_position_400", "value": sum(1 for e in entries if clean(e.get("positionAt400")))},
        {"metric": "out_meeting_json", "value": str(OUT_MEETING)},
        {"metric": "out_racelist_json", "value": str(OUT_RACELIST)},
        {"metric": "out_races_json", "value": str(OUT_RACES)},
        {"metric": "out_results_json", "value": str(OUT_RESULTS)},
        {"metric": "out_runner_sample_csv", "value": str(OUT_RUNNERS)},
        {"metric": "built_at", "value": built_at},
    ]

    with OUT_SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("[EDGEIQ_GRAPHQL_ENDPOINT_REPLAY_V1] COMPLETE")
    print(f"meet_code={meet_code}")
    print(f"race_count={len(race_list)}")
    print(f"race_1_runners={len(entries)}")
    print(f"summary={OUT_SUMMARY}")
    print(f"runner_sample={OUT_RUNNERS}")


if __name__ == "__main__":
    main()
