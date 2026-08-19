from __future__ import annotations
import argparse, json, os, subprocess, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DATA = ROOT / "public" / "data"
LOG_DIR = ROOT / "logs" / "daily-pipeline"
STATUS_PATH = PUBLIC_DATA / "edgeiq_daily_pipeline_status_v1.json"
LAST_GOOD_PATH = PUBLIC_DATA / "edgeiq_daily_pipeline_status_last_good_v1.json"
LOCK_PATH = LOG_DIR / "edgeiq_daily_pipeline.lock"
STAGES = [
    "scripts/build_edgeiq_three_day_window_v1.py",
    "scripts/build_edgeiq_vic_three_day_meeting_universe.py",
    "scripts/build_edgeiq_vic_three_day_meeting_calendar_v1.py",
    "scripts/build_edgeiq_racingcom_three_day_race_list_v1.py",
    "scripts/build_edgeiq_three_day_product_catalog_v1.py",
    "scripts/build_edgeiq_form_guide_enriched_v2.py",
    "scripts/build_edgeiq_current_early_speed_v1.py",
    "scripts/build_edgeiq_current_late_speed_v1.py",
    "scripts/build_edgeiq_current_suitability_v1.py",
    "scripts/build_edgeiq_current_form_momentum_v1.py",
    "scripts/build_edgeiq_current_race_shape_v2.py",
    "scripts/build_edgeiq_map_terminal_feed_v1.py",
    "scripts/build_edgeiq_market_terminal_feed_v1.py",
    "scripts/build_edgeiq_overview_terminal_feed_v1.py",
    "scripts/build_edgeiq_epi_workspace_terminal_feed_v1.py",
    "scripts/build_edgeiq_insights_terminal_feed_v1.py",
    "scripts/build_edgeiq_gear_terminal_feed_v1.py",
    "scripts/build_edgeiq_meeting_results_terminal_feed_v1.py",
    "scripts/performance-intelligence/product-integration/build_edgeiq_performance_intelligence_product_feeds_v1.py",
    "scripts/build_edgeiq_on_track_weather_governed_v1_2.py",
]

def melbourne_today(override=None):
    if override:
        return override
    if ZoneInfo:
        return datetime.now(ZoneInfo("Australia/Melbourne")).date().isoformat()
    return datetime.now().date().isoformat()

def window_dates(start):
    base = datetime.fromisoformat(start).date()
    return [(base + timedelta(days=i)).isoformat() for i in range(3)]

def read_json(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def count_csv(path):
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        return max(0, sum(1 for _ in handle) - 1)

def collect_counts():
    counts = {}
    catalog = read_json(PUBLIC_DATA / "edgeiq_three_day_product_catalog_v1.json")
    if isinstance(catalog, dict):
        meetings = catalog.get("meetings") if isinstance(catalog.get("meetings"), list) else []
        races, runners = [], 0
        for meeting in meetings:
            meeting_races = meeting.get("races") if isinstance(meeting, dict) and isinstance(meeting.get("races"), list) else []
            races.extend(meeting_races)
            for race in meeting_races:
                if isinstance(race, dict) and isinstance(race.get("runners"), list):
                    runners += len(race["runners"])
        counts.update({"catalog_meetings": len(meetings), "catalog_races": len(races), "catalog_runners": runners})
    for name in ["edgeiq_form_guide_enriched_v2.csv", "edgeiq_epi_workspace_terminal_feed_v1.csv", "edgeiq_map_terminal_feed_v1.csv", "edgeiq_market_terminal_feed_v1.csv", "edgeiq_overview_terminal_feed_v1.csv", "edgeiq_insights_terminal_feed_v1.csv"]:
        counts[name] = count_csv(PUBLIC_DATA / name)
    return counts

def run_stage(script, env, log_path):
    path = ROOT / script
    if not path.exists():
        return {"name": script, "status": "SKIPPED", "detail": "Script not present"}
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"\n\n--- {script} ---\n")
        completed = subprocess.run([sys.executable, str(path)], cwd=str(ROOT), env=env, text=True, stdout=log, stderr=subprocess.STDOUT)
    if completed.returncode != 0:
        return {"name": script, "status": "FAIL", "detail": f"Exit {completed.returncode}; see {log_path}"}
    return {"name": script, "status": "READY", "detail": "Completed"}

def write_status(status):
    PUBLIC_DATA.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status, indent=2), encoding="utf-8")
    if status.get("status") == "READY":
        LAST_GOOD_PATH.write_text(json.dumps(status, indent=2), encoding="utf-8")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=os.environ.get("EDGEIQ_PIPELINE_DATE"))
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    start_date = melbourne_today(args.date)
    dates = window_dates(start_date)
    if LOCK_PATH.exists():
        stale_age = datetime.now(timezone.utc).timestamp() - LOCK_PATH.stat().st_mtime
        if stale_age < 60 * 60 * 3:
            write_status({"status": "WARN", "generated_at": datetime.now(timezone.utc).isoformat(), "melbourne_date": start_date, "window_dates": dates, "stages": [{"name": "lock", "status": "WARN", "detail": "Another pipeline run appears active"}], "last_successful_status": read_json(LAST_GOOD_PATH)})
            return 2
        LOCK_PATH.unlink(missing_ok=True)
    LOCK_PATH.write_text(str(os.getpid()), encoding="utf-8")
    log_path = LOG_DIR / f"edgeiq_daily_pipeline_{start_date}_{datetime.now().strftime('%H%M%S')}.log"
    env = os.environ.copy()
    env["EDGEIQ_PIPELINE_DATE"] = start_date
    env["EDGEIQ_PIPELINE_WINDOW_DATES"] = ",".join(dates)
    stages = []
    try:
        for script in STAGES:
            result = run_stage(script, env, log_path)
            stages.append(result)
            print(f"{result['status']} {script}")
            if result["status"] == "FAIL" and not args.continue_on_error:
                break
        failed = [s for s in stages if s["status"] == "FAIL"]
        status = {
            "status": "FAIL" if failed else "READY",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "melbourne_date": start_date,
            "window_dates": dates,
            "log_path": str(log_path),
            "stages": stages,
            "counts": collect_counts(),
            "last_successful_status": None if not failed else read_json(LAST_GOOD_PATH),
        }
        write_status(status)
        return 1 if failed else 0
    finally:
        LOCK_PATH.unlink(missing_ok=True)

if __name__ == "__main__":
    raise SystemExit(main())
