import csv
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"

OUTPUTS = [
    DATA / "edgeiq_vic_three_day_meeting_universe.csv",
    DATA / "edgeiq_vic_three_day_race_fields.csv",
    DATA / "race_fields.csv",
    DATA / "race_card_report.csv",
    DATA / "edgeiq_vic_live_terminal_feed_v1.csv",
    DATA / "edgeiq_live_terminal_feed_v1.csv",
    DATA / "sportsbet_live_market_v1.csv",
]

SUMMARY_CSV = DATA / "edgeiq_current_intelligence_catalog_bridge_v1_summary.csv"
SUMMARY_TXT = DATA / "edgeiq_current_intelligence_catalog_bridge_v1_summary.txt"


def safe(value):
    if value is None:
        return ""
    return str(value).strip()


def digits(value):
    text = safe(value)
    match = re.search(r"\d+", text)
    return match.group(0) if match else ""


def canon_runner(value):
    text = safe(value).upper()
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = re.sub(r"\([A-Z]{2,3}\)", "", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def numeric_price(value):
    text = safe(value)
    if not text:
        return ""
    text = text.replace("$", "").replace(",", "")
    try:
        number = float(text)
    except ValueError:
        return ""
    if number <= 0:
        return ""
    return f"{number:.2f}"


def best_catalog_price(official, source):
    price = numeric_price((official or {}).get("market"))
    if price:
        return price
    odds = (source or {}).get("odds") or []
    prices = []
    for item in odds:
        if not isinstance(item, dict):
            continue
        for key in ["oddsWin", "price", "fixedWin", "winOdds"]:
            candidate = numeric_price(item.get(key))
            if candidate:
                prices.append(float(candidate))
    if not prices:
        return ""
    return f"{min(prices):.2f}"


def checkpoint(path, stamp):
    if path.exists():
        backup = path.with_name(f"{path.stem}_CHECKPOINT_BEFORE_CURRENT_INTEL_BRIDGE_{stamp}{path.suffix}")
        shutil.copy2(path, backup)
        return backup
    return None


def write_csv(path, rows, columns):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    if not CATALOG.exists():
        raise FileNotFoundError(f"Missing product catalog: {CATALOG}")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    generated_at = datetime.now(timezone.utc).isoformat()
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    day_labels = catalog.get("dayLabels") or {}

    rows = []
    market_rows = []
    for meeting in catalog.get("meetings", []):
        meeting_name = safe(meeting.get("meeting"))
        race_date = safe(meeting.get("date"))
        meeting_key = safe(meeting.get("meetingKey")) or f"{race_date}|{meeting_name.upper()}"
        for race in meeting.get("races", []):
            race_source = race.get("source") or {}
            track = safe(race_source.get("normalised_track")) or meeting_name.upper()
            display_track = safe(race_source.get("track")) or meeting_name
            race_no = digits(race_source.get("race_no") or race.get("raceNumber"))
            race_key = safe(race.get("raceKey")) or f"{race_date}|{track}|R{race_no}"
            distance = digits(race_source.get("distance") or race.get("distance"))
            race_class = safe(race_source.get("race_class") or race.get("raceClass"))
            race_time = safe(race_source.get("race_time_utc") or race.get("raceTime"))
            track_condition = safe(race_source.get("track_condition") or race.get("trackCondition") or meeting.get("trackCondition"))
            rail_position = safe(race_source.get("rail_position") or race.get("rail") or meeting.get("rail"))
            runners = race.get("runners") or []
            for runner in runners:
                official = runner.get("official") or {}
                source = runner.get("source") or {}
                horse = safe(official.get("runner") or source.get("horseName") or source.get("horse"))
                horse_canon = canon_runner(horse)
                saddlecloth = safe(official.get("no") or official.get("number") or source.get("raceEntryNumber"))
                barrier = safe(official.get("barrier") or source.get("barrierNumber") or source.get("liveBarrierNumber"))
                jockey = safe(official.get("jockey") or source.get("jockeyName"))
                trainer = safe(official.get("trainer") or source.get("trainerName"))
                weight = safe(official.get("weight") or source.get("weight"))
                silk = safe(official.get("silkUrl") or source.get("silkUrl"))
                price = best_catalog_price(official, source)
                scratched = bool(official.get("scratched") or source.get("scratched"))
                runner_status = "SCRATCHED" if scratched else "ACTIVE"
                source_confidence = "HIGH" if horse and race_date and track and race_no else "LOW"

                row = {
                    "race_date": race_date,
                    "day_bucket": safe(day_labels.get(race_date) or race_source.get("day_bucket")),
                    "meeting_key": meeting_key,
                    "race_key": race_key,
                    "runner_key": f"{race_date}|{track}|R{race_no}|{horse_canon}",
                    "track": track,
                    "display_track": display_track,
                    "race_no": race_no,
                    "race_number": race_no,
                    "race_name": safe(race_source.get("race_name") or race.get("raceName")),
                    "race_class": race_class,
                    "class": race_class,
                    "distance": distance,
                    "distance_m": distance,
                    "race_time": race_time,
                    "track_condition": track_condition,
                    "track_rating": safe(race_source.get("track_rating")),
                    "rail_position": rail_position,
                    "rail": rail_position,
                    "field_size": str(len(runners)),
                    "horse_no": saddlecloth,
                    "saddlecloth": saddlecloth,
                    "runner_number": saddlecloth,
                    "horse": horse,
                    "runner": horse,
                    "horse_key": horse_canon,
                    "horse_canon": horse_canon,
                    "runner_id": safe(source.get("horseCode") or source.get("id")),
                    "barrier": barrier,
                    "jockey": jockey,
                    "trainer": trainer,
                    "weight": weight,
                    "silkUrl": silk,
                    "silk_url": silk,
                    "mobile_silk_image": silk,
                    "last_five": " ".join([safe(x) for x in official.get("lastFive") or []]),
                    "current_gear": safe(official.get("currentGear")),
                    "gear_changes": safe(source.get("gearChanges")),
                    "is_scratched": "TRUE" if scratched else "FALSE",
                    "scratch_status": runner_status,
                    "runner_status": runner_status,
                    "market": price,
                    "ui_price": price,
                    "sportsbet_price": price,
                    "live_price": price,
                    "market_price": price,
                    "fixed_win": price,
                    "bookmaker": "Sportsbet",
                    "event_id": safe(race_source.get("race_id")),
                    "market_id": safe(source.get("id")),
                    "timestamp": safe(catalog.get("generatedAt")) or generated_at,
                    "market_source_status": "CATALOG_EMBEDDED_ODDS" if price else "PENDING_MARKET",
                    "weather": safe(race_source.get("weather")),
                    "weather_wind_speed": safe(race_source.get("weather_wind_speed")),
                    "weather_wind_direction": safe(race_source.get("weather_wind_direction")),
                    "weather_rain": safe(race_source.get("weather_rain")),
                    "source": "edgeiq_three_day_product_catalog_v1",
                    "source_confidence": source_confidence,
                    "built_at": generated_at,
                }
                rows.append(row)
                market_rows.append({
                    "race_date": race_date,
                    "track": track,
                    "race_no": race_no,
                    "horse": horse,
                    "runner": horse,
                    "horse_key": horse_canon,
                    "saddlecloth": saddlecloth,
                    "sportsbet_price": price,
                    "live_price": price,
                    "market": price,
                    "bookmaker": "Sportsbet",
                    "event_id": safe(race_source.get("race_id")),
                    "market_id": safe(source.get("id")),
                    "timestamp": safe(catalog.get("generatedAt")) or generated_at,
                    "mobile_silk_image": silk,
                    "runner_status": runner_status,
                    "market_source_status": "CATALOG_EMBEDDED_ODDS" if price else "PENDING_MARKET",
                    "source": "edgeiq_three_day_product_catalog_v1",
                    "built_at": generated_at,
                })

    if not rows:
        raise RuntimeError("Product catalog produced zero runner rows; refusing to overwrite current feeds.")

    columns = list(rows[0].keys())
    market_columns = list(market_rows[0].keys())
    checkpoints = []
    for path in OUTPUTS + [SUMMARY_CSV, SUMMARY_TXT]:
        backup = checkpoint(path, stamp)
        if backup:
            checkpoints.append(str(backup))

    for path in OUTPUTS:
        if path.name == "sportsbet_live_market_v1.csv":
            write_csv(path, market_rows, market_columns)
        else:
            write_csv(path, rows, columns)

    dates = sorted({row["race_date"] for row in rows})
    tracks = sorted({row["track"] for row in rows})
    races = sorted({(row["race_date"], row["track"], row["race_no"]) for row in rows})
    priced = sum(1 for row in rows if row["live_price"])
    active = sum(1 for row in rows if row["runner_status"] == "ACTIVE")
    scratched = sum(1 for row in rows if row["runner_status"] == "SCRATCHED")

    summary = [
        {"metric": "runner_rows", "value": len(rows)},
        {"metric": "active_rows", "value": active},
        {"metric": "scratched_rows", "value": scratched},
        {"metric": "priced_rows", "value": priced},
        {"metric": "race_count", "value": len(races)},
        {"metric": "dates", "value": "|".join(dates)},
        {"metric": "tracks", "value": "|".join(tracks)},
        {"metric": "checkpoints", "value": len(checkpoints)},
    ]
    write_csv(SUMMARY_CSV, summary, ["metric", "value"])
    SUMMARY_TXT.write_text(
        "\n".join([
            "EDGEIQ_CURRENT_INTELLIGENCE_CATALOG_BRIDGE_COMPLETE",
            f"runner_rows={len(rows)}",
            f"active_rows={active}",
            f"scratched_rows={scratched}",
            f"priced_rows={priced}",
            f"race_count={len(races)}",
            f"dates={','.join(dates)}",
            f"tracks={','.join(tracks)}",
            f"checkpoints={len(checkpoints)}",
        ]),
        encoding="utf-8",
    )

    print("EDGEIQ_CURRENT_INTELLIGENCE_CATALOG_BRIDGE_COMPLETE")
    print(f"runner_rows={len(rows)}")
    print(f"active_rows={active}")
    print(f"scratched_rows={scratched}")
    print(f"priced_rows={priced}")
    print(f"race_count={len(races)}")
    print(f"dates={','.join(dates)}")
    print(f"tracks={','.join(tracks)}")
    print(f"checkpoints={len(checkpoints)}")


if __name__ == "__main__":
    main()
