from __future__ import annotations

import json
from collections import Counter

from edgeiq_beta_intelligence_v1_common import DATA, METRO_WEATHER, canon_track, clean, load_current_runners, normalise_date, write_csv, write_json, write_summary


OUT_JSON = DATA / "edgeiq_race_weather_v1.json"
COVERAGE = DATA / "edgeiq_weather_beta_v1_coverage.csv"
COVERAGE_SUMMARY = DATA / "edgeiq_weather_beta_v1_coverage_summary.txt"
STATION_AUDIT = DATA / "edgeiq_weather_beta_v1_station_mapping_audit.csv"


def load_weather_records() -> dict[str, dict]:
    if not METRO_WEATHER.exists():
        return {}
    payload = json.loads(METRO_WEATHER.read_text(encoding="utf-8"))
    rows = {}
    for row in payload.get("records", []):
        key = canon_track(row.get("meeting") or row.get("course") or row.get("meeting_key"))
        if key:
            rows[key] = row
    return rows


def main() -> None:
    current = load_current_runners()
    weather = load_weather_records()
    races: dict[tuple[str, str], dict] = {}
    for row in current:
        races[(row["raceDate"], row["meeting"])] = row

    coverage_rows = []
    station_rows = []
    output_records = []
    reasons = Counter()
    for (race_date, meeting), sample in sorted(races.items()):
        key = canon_track(meeting)
        record = weather.get(key)
        reason = ""
        if not record:
            reason = "NO_STATION_MAPPING"
        elif clean(record.get("source_status")).upper() not in {"LIVE", "ACTIVE", "OK"}:
            reason = "NO_OBSERVATION"
        if reason:
            reasons[reason] += 1
        weather_object = {
            "raceDate": race_date,
            "meeting": meeting,
            "observedAt": clean((record or {}).get("source_observed_time")) or None,
            "forecastAt": None,
            "condition": clean((record or {}).get("weather_comment")) or None,
            "temperatureC": (record or {}).get("temperature_c"),
            "apparentTemperatureC": None,
            "humidityPct": (record or {}).get("humidity_pct"),
            "windSpeedKmh": (record or {}).get("wind_speed_kmh"),
            "windGustKmh": (record or {}).get("wind_gust_kmh"),
            "windDirection": clean((record or {}).get("wind_direction")) or None,
            "windBearingDeg": None,
            "rainfall24hMm": (record or {}).get("rainfall_24h_mm"),
            "rainfall7dMm": (record or {}).get("rainfall_7day_mm"),
            "irrigation24hMm": None,
            "irrigation7dMm": None,
            "trackCondition": clean(sample.get("trackCondition") or (record or {}).get("official_track_rating")) or None,
            "rail": clean(sample.get("rail") or (record or {}).get("official_rail")) or None,
            "stationName": clean((record or {}).get("wind_station") or (record or {}).get("meeting")) or None,
            "source": clean((record or {}).get("provider")) or "edgeiq_metropolitan_weather_v1",
            "version": "EDGEIQ_RACE_WEATHER_V1",
            "stale": False if record else True,
            "gapReason": reason,
        }
        output_records.append(weather_object)
        coverage_rows.append({"raceDate": race_date, "meeting": meeting, "hasWeather": "YES" if record else "NO", "gapReason": reason, "stationName": weather_object["stationName"] or ""})
        station_rows.append({"raceDate": race_date, "meeting": meeting, "normalisedMeeting": key, "stationMapped": "YES" if record else "NO", "sourceStatus": clean((record or {}).get("source_status")), "gapReason": reason})

    write_json(OUT_JSON, {"schemaVersion": "edgeiq_race_weather_v1", "records": output_records})
    write_csv(COVERAGE, coverage_rows, ["raceDate", "meeting", "hasWeather", "gapReason", "stationName"])
    write_csv(STATION_AUDIT, station_rows, ["raceDate", "meeting", "normalisedMeeting", "stationMapped", "sourceStatus", "gapReason"])
    total = len(coverage_rows)
    populated = sum(1 for row in coverage_rows if row["hasWeather"] == "YES")
    write_summary(COVERAGE_SUMMARY, ["EDGEIQ WEATHER BETA V1 COVERAGE", f"races={total}", f"populated={populated}", f"blank={total - populated}", "gap_counts=" + ", ".join(f"{k}:{v}" for k, v in sorted(reasons.items()))])
    print(f"WEATHER_BETA_V1 races={total} populated={populated} blank={total - populated}")


if __name__ == "__main__":
    main()
