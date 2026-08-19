from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RACE_LIST = DATA / "edgeiq_vic_three_day_race_list_v1.csv"
MEETING_CALENDAR = DATA / "edgeiq_vic_three_day_meeting_calendar_v1.csv"
LIVE_TRACK_BIAS = DATA / "edgeiq_live_track_bias_feed_v1.csv"
LIVE_TRACK_INTELLIGENCE = DATA / "edgeiq_live_track_intelligence_v2_1.csv"

OUT_ENGINE = DATA / "edgeiq_weather_engine_v1.csv"
OUT_LIVE = DATA / "edgeiq_live_weather_feed_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_weather_engine_summary_v1.csv"

FIELDS = [
    "race_date",
    "day_bucket",
    "track",
    "normalised_track",
    "meeting_type",
    "race_no",
    "race_key",
    "distance",
    "track_condition",
    "track_rating",
    "rail_position",
    "weather",
    "weather_wind_direction",
    "weather_wind_speed",
    "weather_rain",
    "weather_min",
    "weather_max",
    "rainfall",
    "weather_status",
    "weather_completeness_pct",
    "track_bias_band",
    "track_bias_confidence",
    "track_fit_band",
    "weather_summary",
    "source",
    "built_at",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def text(value: object) -> str:
    return str(value or "").strip()


def clean(value: object) -> str:
    return "".join(ch for ch in text(value).upper() if ch.isalnum())


def value_or_unknown(value: object) -> str:
    raw = text(value)
    return raw if raw else "UNKNOWN"


def race_key(row: dict[str, str]) -> str:
    existing = text(row.get("race_key"))
    if existing:
        return existing
    return f"{text(row.get('race_date'))}_{clean(row.get('normalised_track') or row.get('track'))}_R{text(row.get('race_no'))}"


def index_meetings() -> dict[tuple[str, str], dict[str, str]]:
    out = {}
    for row in read_csv(MEETING_CALENDAR):
        out[(text(row.get("race_date")), clean(row.get("track")))] = row
    return out


def index_bias() -> dict[tuple[str, str, str], dict[str, str]]:
    out = {}
    for row in read_csv(LIVE_TRACK_BIAS):
        out[(text(row.get("race_date")), clean(row.get("normalised_track") or row.get("track")), text(row.get("race_no")))] = row
    return out


def index_track_fit() -> dict[tuple[str, str, str], list[dict[str, str]]]:
    out: defaultdict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in read_csv(LIVE_TRACK_INTELLIGENCE):
        out[(text(row.get("race_date")), clean(row.get("track")), text(row.get("race_no")))].append(row)
    return out


def completeness(row: dict[str, str]) -> float:
    fields = [
        "weather",
        "weather_wind_direction",
        "weather_wind_speed",
        "weather_rain",
        "weather_min",
        "weather_max",
        "rainfall",
    ]
    known = sum(1 for field in fields if text(row.get(field)))
    return round((known / len(fields)) * 100, 1)


def status_for(row: dict[str, str]) -> str:
    if completeness(row) == 100:
        return "COMPLETE"
    if text(row.get("weather")) or text(row.get("rainfall")) or text(row.get("weather_rain")):
        return "PARTIAL"
    return "SOURCE_GAP"


def track_fit_band(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "UNKNOWN"
    counts: defaultdict[str, int] = defaultdict(int)
    for row in rows:
        band = text(row.get("track_fit_band")) or "UNKNOWN"
        counts[band] += 1
    return max(counts.items(), key=lambda item: item[1])[0]


def build_rows(built_at: str) -> list[dict[str, object]]:
    meetings = index_meetings()
    bias = index_bias()
    track_fit = index_track_fit()
    rows = []
    for row in read_csv(RACE_LIST):
        meeting = meetings.get((text(row.get("race_date")), clean(row.get("normalised_track") or row.get("track"))), {})
        key = (text(row.get("race_date")), clean(row.get("normalised_track") or row.get("track")), text(row.get("race_no")))
        bias_row = bias.get(key, {})
        fit_rows = track_fit.get(key, [])
        status = status_for(row)
        complete = completeness(row)
        weather_bits = [
            f"weather {value_or_unknown(row.get('weather'))}",
            f"rain {value_or_unknown(row.get('weather_rain') or row.get('rainfall'))}",
            f"wind {value_or_unknown(row.get('weather_wind_direction'))} {value_or_unknown(row.get('weather_wind_speed'))}",
        ]
        summary = (
            f"{text(row.get('track'))} R{text(row.get('race_no'))}: "
            f"{', '.join(weather_bits)}; track {value_or_unknown(row.get('track_condition'))} "
            f"{value_or_unknown(row.get('track_rating'))}. Weather source status {status}."
        )
        rows.append({
            "race_date": text(row.get("race_date")),
            "day_bucket": text(row.get("day_bucket") or meeting.get("day_bucket")),
            "track": text(row.get("track")),
            "normalised_track": text(row.get("normalised_track") or row.get("track")),
            "meeting_type": text(meeting.get("meeting_type")),
            "race_no": text(row.get("race_no")),
            "race_key": race_key(row),
            "distance": text(row.get("distance")),
            "track_condition": value_or_unknown(row.get("track_condition")),
            "track_rating": value_or_unknown(row.get("track_rating")),
            "rail_position": value_or_unknown(row.get("rail_position")),
            "weather": value_or_unknown(row.get("weather")),
            "weather_wind_direction": value_or_unknown(row.get("weather_wind_direction")),
            "weather_wind_speed": value_or_unknown(row.get("weather_wind_speed")),
            "weather_rain": value_or_unknown(row.get("weather_rain")),
            "weather_min": value_or_unknown(row.get("weather_min")),
            "weather_max": value_or_unknown(row.get("weather_max")),
            "rainfall": value_or_unknown(row.get("rainfall")),
            "weather_status": status,
            "weather_completeness_pct": complete,
            "track_bias_band": text(bias_row.get("bias_band")) or "UNKNOWN",
            "track_bias_confidence": text(bias_row.get("confidence")) or "UNKNOWN",
            "track_fit_band": track_fit_band(fit_rows),
            "weather_summary": summary,
            "source": text(row.get("source")) or "RACING_COM_RACE_LIST",
            "built_at": built_at,
        })
    return rows


def write_summary(rows: list[dict[str, object]], built_at: str) -> None:
    total = len(rows)
    weather_unknown = sum(1 for row in rows if row["weather"] == "UNKNOWN")
    rain_unknown = sum(1 for row in rows if row["weather_rain"] == "UNKNOWN" and row["rainfall"] == "UNKNOWN")
    wind_unknown = sum(1 for row in rows if row["weather_wind_direction"] == "UNKNOWN" and row["weather_wind_speed"] == "UNKNOWN")
    output = [
        {"metric": "status", "value": "WEATHER_ENGINE_V1_BUILT"},
        {"metric": "race_rows", "value": total},
        {"metric": "weather_unknown_rows", "value": weather_unknown},
        {"metric": "weather_unknown_pct", "value": round((weather_unknown / total) * 100, 2) if total else 0},
        {"metric": "rain_unknown_rows", "value": rain_unknown},
        {"metric": "wind_unknown_rows", "value": wind_unknown},
        {"metric": "partial_or_complete_rows", "value": sum(1 for row in rows if row["weather_status"] in {"PARTIAL", "COMPLETE"})},
        {"metric": "source_gap_rows", "value": sum(1 for row in rows if row["weather_status"] == "SOURCE_GAP")},
        {"metric": "built_at", "value": built_at},
    ]
    write_csv(OUT_SUMMARY, output, ["metric", "value"])


def main() -> None:
    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = build_rows(built_at)
    write_csv(OUT_ENGINE, rows, FIELDS)
    write_csv(OUT_LIVE, rows, FIELDS)
    write_summary(rows, built_at)
    print(f"Weather engine built: rows={len(rows)}")


if __name__ == "__main__":
    main()
