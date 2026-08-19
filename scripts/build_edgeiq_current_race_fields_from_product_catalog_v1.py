
from __future__ import annotations

import csv
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
OUTPUTS = [
    DATA / "race_fields.csv",
    DATA / "edgeiq_live_terminal_feed_v1.csv",
    DATA / "edgeiq_vic_live_terminal_feed_v1.csv",
]
SUMMARY = DATA / "edgeiq_current_race_fields_from_product_catalog_v1_summary.csv"
REPORT = DATA / "edgeiq_current_race_fields_from_product_catalog_v1_report.txt"

FIELDNAMES = [
    "race_date", "day_bucket", "meeting_key", "race_key", "runner_key", "track", "display_track",
    "race_no", "race_number", "race_name", "race_class", "class", "distance", "distance_m", "race_time",
    "track_condition", "track_rating", "rail_position", "rail", "field_size", "horse_no", "saddlecloth",
    "runner_number", "horse", "runner", "horse_key", "horse_canon", "runner_id", "barrier", "jockey",
    "trainer", "weight", "silkUrl", "silk_url", "mobile_silk_image", "last_five", "current_gear",
    "gear_changes", "is_scratched", "scratch_status", "runner_status", "market", "ui_price", "sportsbet_price",
    "live_price", "market_price", "fixed_win", "bookmaker", "event_id", "market_id", "timestamp",
    "market_source_status", "weather", "weather_wind_speed", "weather_wind_direction", "weather_rain", "source",
    "source_confidence", "built_at", "horse_age", "horse_sex", "horse_colour", "comment", "last_race_date",
    "career_stats", "track_stats", "distance_stats", "jockey_stats", "class_stats",
]


def clean(value: Any) -> str:
    if value is None or isinstance(value, (dict, list, tuple)):
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return "" if text.lower() in {"", "-", "none", "null", "n/a", "na", "unknown"} else text


def canon_runner(value: Any) -> str:
    text = clean(value).upper()
    text = re.sub(r"\s*\([A-Z]{2,3}\)\s*$", "", text)
    text = text.replace("'", "").replace("?", "").replace("&", "AND")
    return re.sub(r"[^A-Z0-9]+", "", text)


def canon_track(value: Any) -> str:
    text = clean(value).upper()
    text = re.sub(r"\b(BET365|SPORTSBET|LADBROKES|TAB|THE)\b", " ", text)
    text = re.sub(r"\b(RACECOURSE|RACING|TRACK)\b", " ", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def race_no(value: Any) -> str:
    match = re.search(r"\d+", clean(value).upper().replace("R", ""))
    return str(int(match.group(0))) if match else ""


def distance_text(value: Any) -> tuple[str, str]:
    text = clean(value)
    match = re.search(r"\d+", text)
    metres = match.group(0) if match else ""
    return (f"{metres}m" if metres else text, metres)


def price_to_text(value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    if text.startswith("$"):
        return text
    try:
        parsed = float(str(text).replace("$", "").replace(",", ""))
    except ValueError:
        return text
    if not math.isfinite(parsed) or parsed <= 0:
        return ""
    return f"${parsed:.2f}"


def best_market(source: dict[str, Any], official: dict[str, Any]) -> tuple[str, str, str, str]:
    # Prefer the official display value, then the Racing.com supplied odds list without converting it to EDGEiQ price.
    official_market = price_to_text(official.get("market"))
    if official_market:
        return official_market, official_market, "RACING_COM_MARKET", "SNAPSHOT"
    odds = source.get("odds") if isinstance(source.get("odds"), list) else []
    preferred = ["LB2", "SB2", "BT", "PB3", "BTOTE", "BTOTESP"]
    by_provider = {clean(row.get("providerCode")): row for row in odds if isinstance(row, dict)}
    for provider in preferred:
        row = by_provider.get(provider)
        if not row:
            continue
        price = price_to_text(row.get("oddsWin"))
        if price:
            return price, price, provider, "SNAPSHOT"
    for row in odds:
        if isinstance(row, dict):
            price = price_to_text(row.get("oddsWin"))
            if price:
                return price, price, clean(row.get("providerCode")) or "RACING_COM_MARKET", "SNAPSHOT"
    return "", "", "", "UNAVAILABLE"


def is_scratched(official: dict[str, Any], source: dict[str, Any]) -> bool:
    vals = [official.get("scratched"), source.get("scratched"), source.get("is_scratched"), official.get("status"), source.get("status")]
    return any(str(v).strip().lower() in {"true", "1", "yes", "scr", "scratched", "lscr", "late scratching"} for v in vals)


def day_bucket(index: int) -> str:
    return ["TODAY", "TOMORROW", "DAY+2"][index] if index < 3 else f"DAY+{index}"


def build_rows() -> list[dict[str, Any]]:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for meeting_index, meeting in enumerate(catalog.get("meetings", [])):
        meeting_date = clean(meeting.get("date"))
        track = clean(meeting.get("meeting"))
        track_key = canon_track(track)
        meeting_key = f"{meeting_date}|{track_key}"
        for race in meeting.get("races", []):
            rno = race_no(race.get("raceNumber"))
            race_key = clean(race.get("raceKey")) or f"{meeting_key}|R{rno}"
            runners = race.get("runners") or []
            distance, distance_m = distance_text(race.get("distance"))
            race_class = clean(race.get("raceClass") or race.get("class"))
            track_condition = clean(race.get("trackCondition") or meeting.get("trackCondition"))
            rail = clean(race.get("rail") or meeting.get("rail"))
            for runner in runners:
                official = runner.get("official") if isinstance(runner.get("official"), dict) else {}
                source = runner.get("source") if isinstance(runner.get("source"), dict) else {}
                horse = clean(official.get("runner") or source.get("horseName"))
                horse_key = canon_runner(horse)
                runner_no = race_no(official.get("no") or official.get("number") or source.get("raceEntryNumber"))
                barrier = clean(official.get("barrier") or source.get("liveBarrierNumber") or source.get("barrierNumber") or source.get("barrier"))
                jockey = clean(official.get("jockey") or source.get("jockeyName"))
                trainer = clean(official.get("trainer") or source.get("trainerName"))
                weight = clean(official.get("weight") or source.get("weight"))
                market, ui_price, provider, market_state = best_market(source, official)
                scratched = is_scratched(official, source)
                horse_obj = source.get("horse") if isinstance(source.get("horse"), dict) else {}
                last_five = official.get("lastFive") or horse_obj.get("lastFive") or []
                if isinstance(last_five, str):
                    try:
                        parsed = json.loads(last_five)
                        last_five = parsed if isinstance(parsed, list) else [last_five]
                    except Exception:
                        last_five = [last_five]
                last_five_text = "".join(clean(x) for x in last_five if clean(x) and clean(x) != "-")
                runner_key = f"{race_key}|{horse_key}"
                rows.append({
                    "race_date": meeting_date,
                    "day_bucket": day_bucket(meeting_index),
                    "meeting_key": meeting_key,
                    "race_key": race_key,
                    "runner_key": runner_key,
                    "track": track_key,
                    "display_track": track,
                    "race_no": rno,
                    "race_number": rno,
                    "race_name": clean(race.get("raceName")),
                    "race_class": race_class,
                    "class": race_class,
                    "distance": distance,
                    "distance_m": distance_m,
                    "race_time": clean(race.get("raceTime") or race.get("startTime")),
                    "track_condition": track_condition,
                    "track_rating": track_condition,
                    "rail_position": rail,
                    "rail": rail,
                    "field_size": str(len(runners)),
                    "horse_no": runner_no,
                    "saddlecloth": runner_no,
                    "runner_number": runner_no,
                    "horse": horse,
                    "runner": horse,
                    "horse_key": horse_key,
                    "horse_canon": horse_key,
                    "runner_id": clean(source.get("id") or source.get("runnerId") or source.get("horseCode") or horse_obj.get("id")),
                    "barrier": barrier,
                    "jockey": jockey,
                    "trainer": trainer,
                    "weight": weight,
                    "silkUrl": clean(official.get("silkUrl") or source.get("silkUrl") or horse_obj.get("silkUrl")),
                    "silk_url": clean(official.get("silkUrl") or source.get("silkUrl") or horse_obj.get("silkUrl")),
                    "mobile_silk_image": clean(official.get("silkUrl") or source.get("silkUrl") or horse_obj.get("silkUrl")),
                    "last_five": last_five_text,
                    "current_gear": clean(official.get("currentGear") or source.get("gearChanges")),
                    "gear_changes": clean(source.get("gearChanges") or official.get("currentGear")),
                    "is_scratched": "true" if scratched else "false",
                    "scratch_status": "SCRATCHED" if scratched else "ACTIVE",
                    "runner_status": "SCRATCHED" if scratched else "ACTIVE",
                    "market": market,
                    "ui_price": ui_price,
                    "sportsbet_price": market,
                    "live_price": market,
                    "market_price": market,
                    "fixed_win": market,
                    "bookmaker": provider,
                    "event_id": clean(source.get("raceCode")),
                    "market_id": clean(source.get("meetCode")),
                    "timestamp": built_at,
                    "market_source_status": market_state,
                    "weather": "",
                    "weather_wind_speed": "",
                    "weather_wind_direction": "",
                    "weather_rain": "",
                    "source": "edgeiq_three_day_product_catalog_v1",
                    "source_confidence": "CURRENT_PRODUCT_CATALOG",
                    "built_at": built_at,
                    "horse_age": clean(horse_obj.get("age")),
                    "horse_sex": clean(horse_obj.get("sex")),
                    "horse_colour": clean(horse_obj.get("colour")),
                    "comment": clean(source.get("comment") or (source.get("bestBets") or {}).get("overview") if isinstance(source.get("bestBets"), dict) else ""),
                    "last_race_date": clean(source.get("lastRaceDate") or horse_obj.get("lastRaceDate")),
                    "career_stats": clean(horse_obj.get("lastTenStats") or horse_obj.get("lastTwelveMonthsStats")),
                    "track_stats": clean(source.get("trackStats") or horse_obj.get("trackStats")),
                    "distance_stats": clean(source.get("distanceStats") or horse_obj.get("distanceStats")),
                    "jockey_stats": clean(source.get("jockeyStats")),
                    "class_stats": clean(source.get("atThisClassStats")),
                })
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    rows = build_rows()
    for output in OUTPUTS:
        if output.exists():
            checkpoint = output.with_name(output.stem + "_CHECKPOINT_PRE_FULL_PRODUCT_POPULATION_REPAIR_20260726" + output.suffix)
            if not checkpoint.exists():
                checkpoint.write_bytes(output.read_bytes())
        write_csv(output, rows, FIELDNAMES)
    races = {(r["race_date"], r["track"], r["race_no"]) for r in rows}
    meetings = {(r["race_date"], r["track"]) for r in rows}
    active = sum(1 for r in rows if r.get("runner_status") != "SCRATCHED")
    scratched = len(rows) - active
    write_csv(SUMMARY, [{
        "status": "CURRENT_RACE_FIELDS_BUILT_FROM_PRODUCT_CATALOG",
        "rows": len(rows),
        "meetings": len(meetings),
        "races": len(races),
        "active_runners": active,
        "scratched_runners": scratched,
        "outputs": ";".join(str(p.relative_to(ROOT)) for p in OUTPUTS),
    }], ["status", "rows", "meetings", "races", "active_runners", "scratched_runners", "outputs"])
    REPORT.write_text("\n".join([
        "EDGEIQ CURRENT RACE FIELDS FROM PRODUCT CATALOG V1",
        f"status=CURRENT_RACE_FIELDS_BUILT_FROM_PRODUCT_CATALOG",
        f"rows={len(rows)}",
        f"meetings={len(meetings)}",
        f"races={len(races)}",
        f"active_runners={active}",
        f"scratched_runners={scratched}",
        "production_model_math_changed=NO",
        "pricing_math_changed=NO",
    ]) + "\n", encoding="utf-8")
    print(REPORT.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
