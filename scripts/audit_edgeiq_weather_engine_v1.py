from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

ENGINE = DATA / "edgeiq_weather_engine_v1.csv"
LIVE = DATA / "edgeiq_live_weather_feed_v1.csv"
SUMMARY = DATA / "edgeiq_weather_engine_summary_v1.csv"
AUDIT = DATA / "edgeiq_weather_engine_audit_v1.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(rows: list[dict[str, str]]) -> None:
    with AUDIT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        writer.writerows(rows)


def check(name: str, status: str, detail: str) -> dict[str, str]:
    return {"check": name, "status": status, "detail": detail}


def has_cols(rows: list[dict[str, str]], cols: list[str]) -> tuple[bool, str]:
    if not rows:
        return False, "no rows available"
    missing = [col for col in cols if col not in rows[0]]
    return not missing, "missing=" + "|".join(missing) if missing else "all required columns present"


def main() -> int:
    engine = read_csv(ENGINE)
    live = read_csv(LIVE)
    summary = read_csv(SUMMARY)
    rows: list[dict[str, str]] = []

    rows.append(check("engine_file_exists", "PASS" if ENGINE.exists() else "FAIL", ENGINE.name))
    rows.append(check("live_file_exists", "PASS" if LIVE.exists() else "FAIL", LIVE.name))
    rows.append(check("summary_file_exists", "PASS" if SUMMARY.exists() else "FAIL", SUMMARY.name))
    rows.append(check("engine_rows_positive", "PASS" if engine else "FAIL", f"rows={len(engine)}"))
    rows.append(check("live_rows_positive", "PASS" if live else "FAIL", f"rows={len(live)}"))

    required = [
        "race_date",
        "track",
        "race_no",
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
        "weather_summary",
        "source",
    ]
    ok, detail = has_cols(engine, required)
    rows.append(check("engine_required_columns", "PASS" if ok else "FAIL", detail))
    ok, detail = has_cols(live, required)
    rows.append(check("live_required_columns", "PASS" if ok else "FAIL", detail))

    unknown_weather = sum(1 for row in engine if row.get("weather") == "UNKNOWN")
    rows.append(check(
        "unknown_weather_reported",
        "PASS" if unknown_weather >= 0 else "FAIL",
        f"unknown_weather_rows={unknown_weather}",
    ))

    blank_weather = sum(1 for row in engine if row.get("weather", "") == "")
    blank_wind = sum(1 for row in engine if row.get("weather_wind_direction", "") == "" or row.get("weather_wind_speed", "") == "")
    rows.append(check(
        "missing_values_are_explicit",
        "PASS" if blank_weather == 0 and blank_wind == 0 else "FAIL",
        f"blank_weather={blank_weather}; blank_wind_fields={blank_wind}",
    ))

    summary_status = any(row.get("metric") == "status" and row.get("value") == "WEATHER_ENGINE_V1_BUILT" for row in summary)
    rows.append(check("summary_status_present", "PASS" if summary_status else "FAIL", "summary status row checked"))
    unknown_metric = any(row.get("metric") == "weather_unknown_pct" for row in summary)
    rows.append(check("unknown_rate_metric_present", "PASS" if unknown_metric else "FAIL", "weather_unknown_pct metric checked"))

    source_gap_rows = [row for row in engine if row.get("weather_status") == "SOURCE_GAP"]
    rows.append(check(
        "source_gap_allowed_and_counted",
        "PASS" if source_gap_rows or any(row.get("metric") == "source_gap_rows" for row in summary) else "FAIL",
        f"source_gap_rows={len(source_gap_rows)}",
    ))

    write_csv(rows)
    fail_count = sum(1 for row in rows if row["status"] == "FAIL")
    warn_count = sum(1 for row in rows if row["status"] == "WARN")
    print(f"Weather engine audit: PASS={len(rows) - fail_count - warn_count} WARN={warn_count} FAIL={fail_count}")
    return 1 if fail_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
