from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

IN_REPLAY = DATA / "edgeiq_graphql_playwright_replay_flemington_20250101_v1.json"

OUT = DATA / "edgeiq_graphql_results_warehouse_sample_v1.csv"
SUMMARY = DATA / "edgeiq_graphql_results_warehouse_sample_v1_summary.csv"


def clean(v):
    return "" if v is None else str(v).strip()


def money_to_float(v):
    txt = clean(v).replace("$", "").replace(",", "")
    try:
        return float(txt)
    except Exception:
        return ""


def margin_to_float(v):
    txt = clean(v).upper().replace("L", "").strip()
    try:
        return float(txt)
    except Exception:
        return ""


def find_capture(payload, op_name):
    for item in payload:
        if clean(item.get("operation")) == op_name:
            return json.loads(item.get("body") or "{}")
    return {}


def main():
    built_at = datetime.now(timezone.utc).isoformat()

    replay = json.loads(IN_REPLAY.read_text(encoding="utf-8"))

    meeting_payload = find_capture(replay, "getMeeting_CD")
    racelist_payload = find_capture(replay, "getRaceNumberList_CD")
    results_payload = find_capture(replay, "getRaceResults_CD")

    meeting = ((meeting_payload.get("data") or {}).get("getMeeting") or {})
    race_list = ((racelist_payload.get("data") or {}).get("getNoCacheRacesForMeet") or [])
    race_form = ((results_payload.get("data") or {}).get("getRaceForm") or {})

    race_number = race_form.get("raceNumber")
    race_meta = None
    for r in race_list:
        if str(r.get("raceNumber")) == str(race_number):
            race_meta = r
            break
    race_meta = race_meta or {}

    entries = race_form.get("formRaceEntries") or []

    rows = []

    for e in entries:
        odds = e.get("odds") or []
        odds_map = {}
        for o in odds:
            provider = clean(o.get("providerCode"))
            if provider:
                odds_map[provider] = {
                    "win": clean(o.get("oddsWin")),
                    "place": clean(o.get("oddsPlace")),
                    "is_fav": clean(o.get("oddsIsFavouriteWin")),
                    "fluc_count": len(o.get("flucsWin") or []),
                }

        row = {
            "race_date": clean(meeting.get("date")),
            "track": clean(meeting.get("trackName") or meeting.get("venue")),
            "venue_name": clean(meeting.get("venueName")),
            "state": clean(meeting.get("state")),
            "meet_code": clean(race_form.get("meetCode") or meeting.get("id")),
            "race_id": clean(race_form.get("id")),
            "race_no": clean(race_number),
            "race_status": clean(race_form.get("raceStatus")),
            "race_name": clean(race_meta.get("name")),
            "race_class": clean(race_form.get("rdcClass") or race_meta.get("rdcClass")),
            "race_condition_text": clean(race_meta.get("condition")),
            "distance": clean(race_meta.get("distance")),
            "race_time_utc": clean(race_meta.get("time")),
            "track_condition": clean(meeting.get("trackCondition") or race_meta.get("trackCondition")),
            "track_rating": clean(meeting.get("trackRating") or race_meta.get("trackRating")),
            "rail_position": clean(meeting.get("railPosition")),
            "previous_rail_position": clean(meeting.get("previousRailPosition")),
            "weather": clean(meeting.get("weather")),
            "weather_air_temp": clean(meeting.get("weatherAirTemp")),
            "weather_wind_direction": clean(meeting.get("weatherWindDirection")),
            "weather_wind_speed": clean(meeting.get("weatherWindSpeed")),
            "rainfall": clean(meeting.get("rainfall")),
            "penetrometer": clean(meeting.get("penetrometer")),

            "runner_id": clean(e.get("id")),
            "race_entry_number": clean(e.get("raceEntryNumber")),
            "horse": clean(e.get("horseName")),
            "horse_code": clean(e.get("horseCode")),
            "trainer": clean(e.get("trainerName")),
            "trainer_code": clean(e.get("trainerCode")),
            "jockey": clean(e.get("jockeyName")),
            "jockey_code": clean(e.get("jockeyCode")),
            "barrier": clean(e.get("barrierNumber")),
            "live_barrier": clean(e.get("liveBarrierNumber")),
            "weight": clean(e.get("weight")),
            "scratched": clean(e.get("scratched")),
            "finish": clean(e.get("finish")),
            "finish_abv": clean(e.get("finishAbv")),
            "margin": clean(e.get("margin")),
            "margin_l": margin_to_float(e.get("margin")),
            "starting_price": clean(e.get("startingPrice")),
            "starting_price_decimal": money_to_float(e.get("startingPrice")),
            "winning_time": clean(e.get("winningTime")),
            "standard_time_difference": clean(e.get("standardTimeDifference")),
            "position_800": clean(e.get("positionAt800")),
            "position_800_abv": clean(e.get("positionAt800Abv")),
            "position_400": clean(e.get("positionAt400")),
            "position_400_abv": clean(e.get("positionAt400Abv")),
            "betting_open": clean(e.get("bettingFluctuationsPriceOpen")),
            "betting_move_1": clean(e.get("bettingFluctuationsPriceMoveOne")),
            "betting_move_2": clean(e.get("bettingFluctuationsPriceMoveTwo")),
            "comment_short": clean(e.get("commentShort")),
            "comment": clean(e.get("comment")),
            "comment_stewards": clean(e.get("commentStewards")),
            "gear_changes": clean(e.get("gearChanges")),

            "odds_lb2_win": odds_map.get("LB2", {}).get("win", ""),
            "odds_sb2_win": odds_map.get("SB2", {}).get("win", ""),
            "odds_op_win": odds_map.get("OP", {}).get("win", ""),
            "odds_btote_win": odds_map.get("BTOTE", {}).get("win", ""),
            "odds_btotesp_win": odds_map.get("BTOTESP", {}).get("win", ""),
            "fluc_count_lb2": odds_map.get("LB2", {}).get("fluc_count", ""),
            "fluc_count_sb2": odds_map.get("SB2", {}).get("fluc_count", ""),
            "fluc_count_op": odds_map.get("OP", {}).get("fluc_count", ""),
            "source": "RACING_COM_GRAPHQL_PLAYWRIGHT_REPLAY",
            "built_at": built_at,
        }
        rows.append(row)

    fields = list(rows[0].keys()) if rows else []

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    summary = [
        {"metric": "status", "value": "EDGEIQ_GRAPHQL_RESULTS_WAREHOUSE_SAMPLE_V1_BUILT"},
        {"metric": "input_replay", "value": str(IN_REPLAY)},
        {"metric": "output_rows", "value": len(rows)},
        {"metric": "race_date", "value": clean(meeting.get("date"))},
        {"metric": "track", "value": clean(meeting.get("trackName") or meeting.get("venue"))},
        {"metric": "meet_code", "value": clean(race_form.get("meetCode") or meeting.get("id"))},
        {"metric": "race_id", "value": clean(race_form.get("id"))},
        {"metric": "race_no", "value": clean(race_number)},
        {"metric": "race_count_in_meeting", "value": len(race_list)},
        {"metric": "race_name", "value": clean(race_meta.get("name"))},
        {"metric": "distance", "value": clean(race_meta.get("distance"))},
        {"metric": "race_class", "value": clean(race_form.get("rdcClass") or race_meta.get("rdcClass"))},
        {"metric": "track_condition", "value": clean(meeting.get("trackCondition"))},
        {"metric": "track_rating", "value": clean(meeting.get("trackRating"))},
        {"metric": "rail_position", "value": clean(meeting.get("railPosition"))},
        {"metric": "weather", "value": clean(meeting.get("weather"))},
        {"metric": "rainfall", "value": clean(meeting.get("rainfall"))},
        {"metric": "penetrometer", "value": clean(meeting.get("penetrometer"))},
        {"metric": "rows_with_horse", "value": sum(1 for r in rows if r["horse"])},
        {"metric": "rows_with_trainer", "value": sum(1 for r in rows if r["trainer"])},
        {"metric": "rows_with_jockey", "value": sum(1 for r in rows if r["jockey"])},
        {"metric": "rows_with_sp", "value": sum(1 for r in rows if r["starting_price"])},
        {"metric": "rows_with_barrier", "value": sum(1 for r in rows if r["barrier"])},
        {"metric": "rows_with_finish", "value": sum(1 for r in rows if r["finish"])},
        {"metric": "rows_with_margin", "value": sum(1 for r in rows if r["margin"])},
        {"metric": "rows_with_position_800", "value": sum(1 for r in rows if r["position_800"])},
        {"metric": "rows_with_position_400", "value": sum(1 for r in rows if r["position_400"])},
        {"metric": "built_at", "value": built_at},
    ]

    with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("[EDGEIQ_GRAPHQL_RESULTS_WAREHOUSE_SAMPLE_V1] COMPLETE")
    print(f"rows={len(rows)}")
    print(f"output={OUT}")
    print(f"summary={SUMMARY}")


if __name__ == "__main__":
    main()
