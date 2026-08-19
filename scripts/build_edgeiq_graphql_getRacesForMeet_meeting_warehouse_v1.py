from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INFILE = DATA / "edgeiq_graphql_getRacesForMeet_payload_v1.json"
OUT = DATA / "edgeiq_graphql_getRacesForMeet_meeting_warehouse_v1.csv"
SUMMARY = DATA / "edgeiq_graphql_getRacesForMeet_meeting_warehouse_v1_summary.csv"


def clean(v):
    return "" if v is None else str(v).strip()


def money(v):
    txt = clean(v).replace("$", "").replace(",", "")
    try:
        return float(txt)
    except Exception:
        return ""


def margin(v):
    txt = clean(v).upper().replace("L", "")
    try:
        return float(txt)
    except Exception:
        return ""


def main():
    built_at = datetime.now(timezone.utc).isoformat()
    payload = json.loads(INFILE.read_text(encoding="utf-8"))
    races = (((payload.get("data") or {}).get("getRacesForMeet")) or [])

    rows = []

    for race in races:
        meet = race.get("meet") or {}
        entries = race.get("formRaceEntries") or []

        for e in entries:
            odds = e.get("odds") or []
            odds_map = {}
            for o in odds:
                p = clean(o.get("providerCode"))
                if p:
                    odds_map[p] = {
                        "win": clean(o.get("oddsWin")),
                        "place": clean(o.get("oddsPlace")),
                        "fluc_count": len(o.get("flucsWin") or []),
                    }

            rows.append({
                "race_date": "",
                "track": "",
                "meet_url": clean(meet.get("meetUrl")),
                "state": clean(meet.get("state")),
                "race_id": clean(race.get("id")),
                "race_no": clean(race.get("raceNumber")),
                "race_status": clean(race.get("raceStatus")),
                "race_name": clean(race.get("name")),
                "race_class": clean(race.get("rdcClass") or race.get("class")),
                "distance": clean(race.get("distance")),
                "race_time_utc": clean(race.get("time")),
                "track_condition": clean(meet.get("trackCondition")),
                "track_rating": clean(meet.get("trackRating")),
                "rail_position": clean(meet.get("railPosition")),
                "previous_rail_position": clean(meet.get("previousRailPosition")),
                "weather": clean(meet.get("weather")),
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
                "margin_l": margin(e.get("margin")),
                "starting_price": clean(e.get("startingPrice")),
                "starting_price_decimal": money(e.get("startingPrice")),
                "winning_time": clean(e.get("winningTime")),
                "comment_short": clean(e.get("commentShort")),
                "comment": clean(e.get("comment")),
                "comment_stewards": clean(e.get("commentStewards")),
                "gear_changes": clean(e.get("gearChanges")),
                "odds_lb2_win": odds_map.get("LB2", {}).get("win", ""),
                "odds_sb2_win": odds_map.get("SB2", {}).get("win", ""),
                "odds_op_win": odds_map.get("OP", {}).get("win", ""),
                "odds_btote_win": odds_map.get("BTOTE", {}).get("win", ""),
                "fluc_count_lb2": odds_map.get("LB2", {}).get("fluc_count", ""),
                "fluc_count_sb2": odds_map.get("SB2", {}).get("fluc_count", ""),
                "fluc_count_op": odds_map.get("OP", {}).get("fluc_count", ""),
                "source": "RACING_COM_GRAPHQL_GET_RACES_FOR_MEET",
                "built_at": built_at,
            })

    fields = list(rows[0].keys()) if rows else []

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    summary = [
        {"metric": "status", "value": "EDGEIQ_GRAPHQL_GET_RACES_FOR_MEET_WAREHOUSE_V1_BUILT"},
        {"metric": "input", "value": str(INFILE)},
        {"metric": "races", "value": len(races)},
        {"metric": "rows", "value": len(rows)},
        {"metric": "unique_races", "value": len(set(r["race_no"] for r in rows))},
        {"metric": "rows_with_horse", "value": sum(1 for r in rows if r["horse"])},
        {"metric": "rows_with_trainer", "value": sum(1 for r in rows if r["trainer"])},
        {"metric": "rows_with_jockey", "value": sum(1 for r in rows if r["jockey"])},
        {"metric": "rows_with_sp", "value": sum(1 for r in rows if r["starting_price"])},
        {"metric": "rows_with_barrier", "value": sum(1 for r in rows if r["barrier"])},
        {"metric": "rows_with_finish", "value": sum(1 for r in rows if r["finish"])},
        {"metric": "rows_with_margin", "value": sum(1 for r in rows if r["margin"])},
        {"metric": "built_at", "value": built_at},
    ]

    with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("[EDGEIQ_GRAPHQL_GET_RACES_FOR_MEET_WAREHOUSE_V1] COMPLETE")
    print(f"races={len(races)}")
    print(f"rows={len(rows)}")
    print(f"output={OUT}")
    print(f"summary={SUMMARY}")


if __name__ == "__main__":
    main()
