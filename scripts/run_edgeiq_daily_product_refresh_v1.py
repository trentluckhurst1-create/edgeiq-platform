from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "operations-readiness"
DAILY = DOCS / "daily-refresh"
LKG = DOCS / "operations" / "last-known-good"
TZ = ZoneInfo("Australia/Melbourne") if ZoneInfo else None

CRITICAL = [
    "edgeiq_three_day_window_v1.json",
    "edgeiq_three_day_product_catalog_v1.json",
    "edgeiq_vic_three_day_race_list_v1.csv",
    "edgeiq_live_terminal_feed_v1.csv",
    "edgeiq_vic_live_terminal_feed_v1.csv",
]

# Build the current live Racing.com meeting/race list before the meeting calendar
# and universe. The calendar consumes that live list as the authoritative current
# three-day supplement, with historical backfill only as fallback.
STAGES = [
    "scripts/build_edgeiq_three_day_window_v1.py",
    "scripts/build_edgeiq_racingcom_three_day_race_list_v1.py",
    "scripts/build_edgeiq_vic_three_day_meeting_calendar_v1.py",
    "scripts/build_edgeiq_vic_three_day_meeting_universe.py",
    "scripts/build_edgeiq_three_day_product_catalog_v1.py",
    "scripts/build_edgeiq_on_track_weather_governed_v1_2.py",
    "scripts/build_edgeiq_victorian_track_weather_v1.py",
    "scripts/audit_edgeiq_victorian_track_weather_v1.py",
    "scripts/enrich_edgeiq_meetings_catalog_metadata_v1.py",
    "scripts/build_edgeiq_current_race_fields_from_product_catalog_v1.py",
    "scripts/build_edgeiq_ladbrokes_active_market_refresh_v1.py",
    "scripts/build_edgeiq_current_market_v1.py",
    "scripts/build_edgeiq_form_guide_current_base_v1.py",
    "scripts/build_edgeiq_current_early_speed_v1.py",
    "scripts/build_edgeiq_current_late_speed_v1.py",
    "scripts/build_edgeiq_current_suitability_v1.py",
    "scripts/build_edgeiq_current_form_momentum_v1.py",
    "scripts/build_edgeiq_current_race_shape_v2.py",
    "scripts/build_edgeiq_current_map_v1.py",
    "scripts/build_edgeiq_form_guide_enriched_v2.py",
    "scripts/build_edgeiq_performance_recovery_current_lineage_v1.py",
    "scripts/build_edgeiq_form_guide_enriched_v2.py",
    "scripts/build_edgeiq_map_terminal_feed_v1.py",
    "scripts/build_edgeiq_market_terminal_feed_v1.py",
    "scripts/build_edgeiq_overview_terminal_feed_v1.py",
    "scripts/build_edgeiq_insights_terminal_feed_v1.py",
    "scripts/build_edgeiq_gear_terminal_feed_v1.py",
    "scripts/build_edgeiq_meeting_results_terminal_feed_v1.py",
    "scripts/performance-intelligence/product-integration/build_edgeiq_performance_intelligence_product_feeds_v1.py",
]


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def today(value: str | None = None) -> str:
    if value:
        return value
    return (datetime.now(TZ).date() if TZ else datetime.now().date()).isoformat()


def count_csv(path: Path) -> int:
    if not path.exists() or path.stat().st_size == 0:
        return 0
    return max(0, sum(1 for _ in path.open("r", encoding="utf-8", errors="ignore")) - 1)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def snap() -> dict:
    LKG.mkdir(parents=True, exist_ok=True)
    files = []
    for name in CRITICAL:
        source = PUBLIC / name
        if source.exists() and source.stat().st_size > 0:
            shutil.copy2(source, LKG / name)
            files.append({"file": name, "bytes": source.stat().st_size})
    manifest = {"generated_utc": utc(), "files": files}
    write_json(DOCS / "operations" / "edgeiq_last_known_good_manifest_v1.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date")
    parser.add_argument("--meeting")
    parser.add_argument("--race")
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--publish-only", action="store_true")
    parser.add_argument("--force-current-refresh", action="store_true")
    parser.add_argument("--no-market", action="store_true")
    parser.add_argument("--no-weather", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    started = time.time()
    operating_date = today(args.date)
    DAILY.mkdir(parents=True, exist_ok=True)
    last_known_good = snap()
    stages: list[dict] = []
    log = DAILY / "edgeiq_daily_product_refresh_v1_run_log.txt"
    env = os.environ.copy()
    env["EDGEIQ_PIPELINE_DATE"] = operating_date

    with log.open("w", encoding="utf-8") as handle:
        handle.write(
            f"EDGEIQ DAILY PRODUCT REFRESH V1\nOPERATING_DATE={operating_date}\nSTARTED_UTC={utc()}\n"
        )
        if args.audit_only:
            handle.write("AUDIT_ONLY\n")
        else:
            for stage in STAGES:
                lower = stage.lower()
                if args.no_market and "market" in lower:
                    stages.append({"stage": stage, "status": "SKIPPED", "reason": "--no-market"})
                    continue
                if args.no_weather and "weather" in lower:
                    stages.append({"stage": stage, "status": "SKIPPED", "reason": "--no-weather"})
                    continue
                path = ROOT / stage
                if not path.exists():
                    stages.append({"stage": stage, "status": "SKIPPED", "reason": "missing"})
                    continue
                handle.write(f"\n--- {stage} ---\n")
                result = subprocess.run(
                    [sys.executable, str(path)],
                    cwd=str(ROOT),
                    env=env,
                    text=True,
                    stdout=handle,
                    stderr=subprocess.STDOUT,
                    timeout=900,
                )
                stages.append(
                    {
                        "stage": stage,
                        "status": "PASS" if result.returncode == 0 else "FAIL",
                        "returncode": result.returncode,
                    }
                )
                if result.returncode != 0:
                    break

    feeds = []
    for name in CRITICAL:
        path = PUBLIC / name
        rows = count_csv(path) if name.endswith(".csv") else (1 if path.exists() and path.stat().st_size > 0 else 0)
        feeds.append(
            {
                "file": name,
                "status": "PASS" if path.exists() and path.stat().st_size > 0 and rows > 0 else "FAIL",
                "rows_or_items": rows,
                "bytes": path.stat().st_size if path.exists() else 0,
            }
        )

    catalog_path = PUBLIC / "edgeiq_three_day_product_catalog_v1.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8")) if catalog_path.exists() else {}
    meetings = catalog.get("meetings", []) if isinstance(catalog, dict) else []
    races = []
    runners = 0
    total_current_scratchings = 0
    active_runners = 0

    def runner_scratched(runner: dict) -> bool:
        official = runner.get("official") if isinstance(runner.get("official"), dict) else {}
        source = runner.get("source") if isinstance(runner.get("source"), dict) else {}
        values = [
            official.get("scratched"),
            source.get("scratched"),
            source.get("is_scratched"),
            official.get("status"),
            source.get("status"),
        ]
        return any(str(value).strip().lower() in {"true", "scr", "scratched", "lscr", "late scratching"} for value in values)

    for meeting in meetings:
        for race in meeting.get("races", []) if isinstance(meeting, dict) else []:
            races.append(race)
            race_runners = race.get("runners", []) if isinstance(race, dict) else []
            runners += len(race_runners)
            race_scratchings = sum(1 for runner in race_runners if runner_scratched(runner))
            total_current_scratchings += race_scratchings
            active_runners += max(0, len(race_runners) - race_scratchings)

    status = "FAIL" if any(item.get("status") == "FAIL" for item in stages) or any(item.get("status") != "PASS" for item in feeds) else "PASS"
    failed_stages = [item.get("stage") for item in stages if item.get("status") == "FAIL"]

    weather_runtime = PUBLIC / "edgeiq_victorian_track_weather_v1.json"
    payload = {
        "schema_version": "edgeiq_daily_product_refresh_v1",
        "generated_utc": utc(),
        "operating_date": operating_date,
        "timezone": "Australia/Melbourne",
        "stages": stages,
        "failed_stages": failed_stages,
        "feed_checks": feeds,
        "meetings_built": len(meetings),
        "races_built": len(races),
        "runners_built": runners,
        "declared_runners": runners,
        "active_runners": active_runners,
        "total_current_scratchings": total_current_scratchings,
        "new_scratchings_this_run": None,
        "scratchings_changes_this_run": None,
        "reinstated_runners_this_run": None,
        "scratchings_metric_deprecated": total_current_scratchings,
        "track_status": "PARTIAL",
        "weather_status": "PASS" if weather_runtime.exists() and weather_runtime.stat().st_size > 0 else "PARTIAL",
        "market_status": "PASS" if (PUBLIC / "edgeiq_market_terminal_feed_v1.csv").exists() else "PARTIAL",
        "results_status": "PASS" if (PUBLIC / "edgeiq_meeting_results_terminal_feed_v1.csv").exists() else "PARTIAL",
        "feeds_published": sum(1 for item in feeds if item["status"] == "PASS"),
        "audit_status": status,
        "last_known_good_preserved": bool(last_known_good.get("files")),
        "elapsed_seconds": round(time.time() - started, 2),
        "exit_code": 0 if status == "PASS" else 1,
    }

    weather_audit_path = DOCS.parent / "weather-intelligence" / "live" / "edgeiq_victorian_track_weather_v1_audit.json"
    try:
        weather_audit = json.loads(weather_audit_path.read_text(encoding="utf-8")) if weather_audit_path.exists() else {}
    except Exception:
        weather_audit = {}

    payload.update(
        {
            "weather_meetings_required": weather_audit.get("meetings_required", 0),
            "weather_direct_source_meetings": weather_audit.get("direct_source_meetings", 0),
            "weather_bom_meetings": weather_audit.get("bom_meetings", 0),
            "weather_current": weather_audit.get("current", 0),
            "weather_regional_proxy": weather_audit.get("regional_proxy", 0),
            "weather_stale": weather_audit.get("stale", 0),
            "weather_unavailable": weather_audit.get("unavailable", 0),
            "weather_licence_blocked": weather_audit.get("licence_blocked", 0),
            "weather_audit_status": weather_audit.get("status", "NOT_RUN"),
        }
    )

    write_json(DAILY / "edgeiq_daily_product_refresh_v1_audit.json", payload)
    write_json(DAILY / "edgeiq_daily_product_refresh_v1_manifest.json", {"critical_feeds": feeds, "last_known_good": last_known_good})
    (DAILY / "edgeiq_daily_product_refresh_v1_report.md").write_text(
        f"# EDGEIQ Daily Product Refresh V1\n\nStatus: {status}\n\nMeetings: {len(meetings)}\nRaces: {len(races)}\nRunners: {runners}\n",
        encoding="utf-8",
    )

    print("============================================================")
    print("EDGEIQ DAILY PRODUCT REFRESH V1")
    print("============================================================")
    print(f"OPERATING_DATE: {operating_date}")
    print("TIMEZONE: Australia/Melbourne")
    print(f"MEETINGS_BUILT: {len(meetings)}")
    print(f"RACES_BUILT: {len(races)}")
    print(f"RUNNERS_BUILT: {runners}")
    print(f"DECLARED_RUNNERS: {runners}")
    print(f"ACTIVE_RUNNERS: {active_runners}")
    print(f"TOTAL_CURRENT_SCRATCHINGS: {total_current_scratchings}")
    print("NEW_SCRATCHINGS_THIS_RUN: NOT_CALCULATED")
    print("SCRATCHING_CHANGES_THIS_RUN: NOT_CALCULATED")
    print("REINSTATED_RUNNERS_THIS_RUN: NOT_CALCULATED")
    print(f"TRACK_STATUS: {payload['track_status']}")
    print(f"WEATHER_STATUS: {payload['weather_status']}")
    print(f"WEATHER_MEETINGS_REQUIRED: {payload.get('weather_meetings_required', 0)}")
    print(f"WEATHER_DIRECT_SOURCE_MEETINGS: {payload.get('weather_direct_source_meetings', 0)}")
    print(f"WEATHER_BOM_MEETINGS: {payload.get('weather_bom_meetings', 0)}")
    print(f"WEATHER_CURRENT: {payload.get('weather_current', 0)}")
    print(f"WEATHER_REGIONAL_PROXY: {payload.get('weather_regional_proxy', 0)}")
    print(f"WEATHER_STALE: {payload.get('weather_stale', 0)}")
    print(f"WEATHER_UNAVAILABLE: {payload.get('weather_unavailable', 0)}")
    print(f"WEATHER_LICENCE_BLOCKED: {payload.get('weather_licence_blocked', 0)}")
    print(f"WEATHER_AUDIT_STATUS: {payload.get('weather_audit_status', 'NOT_RUN')}")
    print(f"MARKET_STATUS: {payload['market_status']}")
    print(f"RESULTS_STATUS: {payload['results_status']}")
    print(f"FEEDS_PUBLISHED: {payload['feeds_published']}")
    print(f"FAILED_STAGES: {','.join(failed_stages) if failed_stages else 'NONE'}")
    print(f"AUDIT_STATUS: {status}")
    print(f"LAST_KNOWN_GOOD_PRESERVED: {str(payload['last_known_good_preserved']).upper()}")
    print(f"ELAPSED_SECONDS: {payload['elapsed_seconds']}")
    print(f"EXIT_CODE: {payload['exit_code']}")
    print("============================================================")
    return payload["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
