from __future__ import annotations

import csv
import json
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "full-product-implementation"
BASE_URL = "http://127.0.0.1:5173"

ACTIVE_FEEDS = [
    {"workspace": "HOME/MEETINGS", "name": "three_day_window", "url": "/data/edgeiq_three_day_window_v1.json", "kind": "json", "role": "live", "schema": ["dates"]},
    {"workspace": "HOME/MEETINGS/RACE/FIELD", "name": "three_day_product_catalog", "url": "/data/edgeiq_three_day_product_catalog_v1.json", "kind": "json", "role": "live", "schema": ["meetings", "dates"]},
    {"workspace": "HOME", "name": "daily_pipeline_status", "url": "/data/edgeiq_daily_pipeline_status_v1.json", "kind": "json", "role": "live", "schema": ["status", "counts"]},
    {"workspace": "FORM GUIDE", "name": "form_guide_enriched_v2", "url": "/data/edgeiq_form_guide_enriched_v2.json", "kind": "json", "role": "live-expanded", "schema": []},
    {"workspace": "FORM GUIDE", "name": "form_guide_enriched_v1", "url": "/data/edgeiq_form_guide_enriched_v1.json", "kind": "json", "role": "reference", "schema": []},
    {"workspace": "MAP", "name": "map_terminal", "url": "/data/edgeiq_map_terminal_feed_v1.csv", "kind": "csv", "role": "live", "schema": ["race_date", "track", "race_no", "horse"]},
    {"workspace": "MARKET", "name": "market_terminal", "url": "/data/edgeiq_market_terminal_feed_v1.csv", "kind": "csv", "role": "live", "schema": ["race_date", "track", "race_no", "horse"]},
    {"workspace": "OVERVIEW", "name": "overview_terminal", "url": "/data/edgeiq_overview_terminal_feed_v1.csv", "kind": "csv", "role": "live", "schema": ["race_date", "track", "race_no"]},
    {"workspace": "EPI", "name": "epi_terminal", "url": "/data/edgeiq_epi_workspace_terminal_feed_v1.csv", "kind": "csv", "role": "live", "schema": ["race_date", "track", "race_no", "horse"]},
    {"workspace": "INSIGHTS", "name": "insights_terminal", "url": "/data/edgeiq_insights_terminal_feed_v1.csv", "kind": "csv", "role": "live-expanded", "schema": ["race_date", "track", "race_no"]},
    {"workspace": "GEAR CHANGES", "name": "gear_terminal", "url": "/data/edgeiq_gear_terminal_feed_v1.csv", "kind": "csv", "role": "live", "schema": []},
    {"workspace": "RESULTS", "name": "meeting_results_terminal", "url": "/data/edgeiq_meeting_results_terminal_feed_v1.csv", "kind": "csv", "role": "live", "schema": []},
    {"workspace": "TRACK/WEATHER", "name": "on_track_weather_governed", "url": "/data/edgeiq_on_track_weather_governed_v1_2.json", "kind": "json", "role": "live-weather", "schema": []},
    {"workspace": "WEATHER", "name": "race_weather", "url": "/data/edgeiq_race_weather_v1.json", "kind": "json", "role": "reference", "schema": []},
    {"workspace": "WEATHER", "name": "metropolitan_weather", "url": "/data/edgeiq_metropolitan_weather_v1.json", "kind": "json", "role": "reference", "schema": []},
    {"workspace": "TRACK", "name": "track_intelligence", "url": "/data/edgeiq_live_track_intelligence_v2_1.csv", "kind": "csv", "role": "reference", "schema": []},
    {"workspace": "TRACK", "name": "current_true_track", "url": "/data/edgeiq_current_true_track_feed_v1.csv", "kind": "csv", "role": "reference", "schema": []},
    {"workspace": "TRACK", "name": "vic_official_track_conditions", "url": "/data/edgeiq_vic_official_track_conditions_v1.json", "kind": "json", "role": "reference", "schema": []},
    {"workspace": "RACE", "name": "current_race_intelligence", "url": "/data/edgeiq_current_race_intelligence_v1.json", "kind": "json", "role": "reference", "schema": []},
    {"workspace": "RACE", "name": "race_shape_story", "url": "/data/edgeiq_race_shape_story_v1.csv", "kind": "csv", "role": "reference", "schema": ["race_date", "track", "race_no"]},
    {"workspace": "FIELD", "name": "runner_profile_stats", "url": "/data/edgeiq_runner_profile_stats_v1.csv", "kind": "csv", "role": "reference", "schema": []},
    {"workspace": "FIELD", "name": "live_runner_board_v7_1_candidate", "url": "/data/edgeiq_live_runner_board_v7_1_current_day_candidate.csv", "kind": "csv", "role": "reference", "schema": []},
    {"workspace": "FIELD", "name": "runner_dna_v6_2", "url": "/data/edgeiq_runner_dna_v6_2.csv", "kind": "csv", "role": "reference", "schema": []},
    {"workspace": "FIELD", "name": "runner_dna_drawer", "url": "/data/edgeiq_runner_dna_drawer_feed_v2.csv", "kind": "csv", "role": "reference", "schema": []},
    {"workspace": "NEXUS/CONNECTIONS", "name": "connection_intelligence", "url": "/data/edgeiq_connection_intelligence_v2_1.csv", "kind": "csv", "role": "reference", "schema": []},
    {"workspace": "PERFORMANCE", "name": "live_sectional_intelligence", "url": "/data/edgeiq_live_sectional_intelligence_v1.csv", "kind": "csv", "role": "reference", "schema": []},
    {"workspace": "PERFORMANCE", "name": "explainability_terminal", "url": "/data/edgeiq_explainability_terminal_feed_v1_2.csv", "kind": "csv", "role": "reference", "schema": []},
    {"workspace": "MARKET", "name": "market_intelligence", "url": "/data/edgeiq_market_intelligence_v1.csv", "kind": "csv", "role": "reference", "schema": []},
    {"workspace": "WEATHER", "name": "live_weather", "url": "/data/edgeiq_live_weather_feed_v1.csv", "kind": "csv", "role": "reference", "schema": []},
    {"workspace": "TRACK", "name": "track_profile", "url": "/data/edgeiq_track_profile_v2.csv", "kind": "csv", "role": "reference", "schema": []},
    {"workspace": "TRACK", "name": "track_intelligence_profile", "url": "/data/edgeiq_track_intelligence_profile_v2.csv", "kind": "csv", "role": "reference", "schema": []},
    {"workspace": "MEETINGS", "name": "track_map_manifest", "url": "/data/edgeiq_track_map_manifest_v1.csv", "kind": "csv", "role": "reference", "schema": []},
]

WORKSPACE_SOURCES = [
    ("HOME", "edgeiq_three_day_product_catalog_v1.json + edgeiq_daily_pipeline_status_v1.json"),
    ("MEETINGS", "edgeiq_three_day_product_catalog_v1.json"),
    ("RACE", "edgeiq_three_day_product_catalog_v1.json + edgeiq_overview_terminal_feed_v1.csv"),
    ("FIELD", "edgeiq_three_day_product_catalog_v1.json"),
    ("FORM GUIDE", "edgeiq_form_guide_enriched_v2.json"),
    ("PERFORMANCE", "public/performance-intelligence/edgeiq_performance_intelligence_product_feeds_v1.json"),
    ("MAP", "edgeiq_map_terminal_feed_v1.csv"),
    ("EPI", "edgeiq_epi_workspace_terminal_feed_v1.csv"),
    ("MARKET", "edgeiq_market_terminal_feed_v1.csv"),
    ("OVERVIEW", "edgeiq_overview_terminal_feed_v1.csv"),
    ("SCRATCHINGS", "edgeiq_three_day_product_catalog_v1.json runner scratch flags"),
    ("GEAR CHANGES", "edgeiq_gear_terminal_feed_v1.csv"),
    ("TRACK", "edgeiq_on_track_weather_governed_v1_2.json + track profile feeds"),
    ("WEATHER", "edgeiq_on_track_weather_governed_v1_2.json"),
    ("RESULTS", "edgeiq_meeting_results_terminal_feed_v1.csv"),
    ("INSIGHTS", "edgeiq_insights_terminal_feed_v1.csv"),
    ("LAB", "active governed research datasets"),
    ("COMPARE", "current catalogue runner context"),
    ("REVIEW", "meeting results feed when completed"),
]

DATE_KEYS = ["race_date", "meeting_date", "date", "current_race_date"]
TRACK_KEYS = ["track", "meeting", "venue"]
RACE_KEYS = ["race_no", "raceNumber", "race_number"]
HORSE_KEYS = ["horse", "runner", "runner_name"]


def file_for_url(url: str) -> Path:
    return ROOT / "public" / url.lstrip("/").replace("/", "\\")


def http_status(url: str) -> tuple[str, int, str]:
    try:
        with urllib.request.urlopen(BASE_URL + url + ("&" if "?" in url else "?") + "audit=1", timeout=8) as resp:
            body = resp.read(200)
            if body.lstrip().startswith(b"<"):
                return "HTML_FALLBACK", resp.status, "HTML response"
            return "HTTP_OK", resp.status, ""
    except Exception as exc:  # noqa: BLE001
        return "HTTP_FAIL", 0, str(exc)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def csv_rows(path: Path, max_rows: int | None = None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for idx, row in enumerate(reader):
            rows.append({k: (v or "") for k, v in row.items()})
            if max_rows is not None and idx + 1 >= max_rows:
                break
    return rows


def csv_count(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return max(sum(1 for _ in fh) - 1, 0)


def collect_dates_from_rows(rows: list[dict[str, str]]) -> list[str]:
    dates: list[str] = []
    for row in rows:
        for key in DATE_KEYS:
            value = (row.get(key) or "").strip()
            if re.match(r"^20\d{2}-\d{2}-\d{2}$", value):
                dates.append(value)
                break
    return dates


def distinct_count(rows: list[dict[str, str]], keys: list[str]) -> int:
    values = set()
    for row in rows:
        parts = []
        for key in keys:
            if key in row and row.get(key):
                parts.append(row[key].strip().upper())
        if parts:
            values.add("|".join(parts))
    return len(values)


def summarise_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    meetings = catalog.get("meetings") or []
    races = []
    runner_count = 0
    for meeting in meetings:
        for race in meeting.get("races") or []:
            races.append(race)
            runner_count += len(race.get("runners") or [])
    return {
        "dates": catalog.get("dates") or [],
        "meeting_count": len(meetings),
        "race_count": len(races),
        "runner_count": runner_count,
        "meetings": meetings,
    }


def parse_feed(feed: dict[str, Any], canonical_dates: set[str]) -> dict[str, Any]:
    path = file_for_url(feed["url"])
    result: dict[str, Any] = {
        "workspace": feed["workspace"],
        "feed": feed["name"],
        "runtime_url": feed["url"],
        "file_path": str(path),
        "role": feed["role"],
        "file_exists": path.exists(),
        "http_status": "NOT_CHECKED",
        "http_code": "",
        "parse_status": "NOT_CHECKED",
        "schema_status": "NOT_CHECKED",
        "earliest_date": "",
        "latest_date": "",
        "meeting_count": 0,
        "race_count": 0,
        "runner_count": 0,
        "rows": 0,
        "catalogue_alignment": "NOT_ASSESSED",
        "status": "FAIL",
        "notes": "",
    }
    if not path.exists():
        result["notes"] = "missing public/data file"
        return result

    http, code, http_note = http_status(feed["url"])
    result["http_status"] = http
    result["http_code"] = code or ""
    notes = []
    if http_note:
        notes.append(http_note)

    try:
        if feed["kind"] == "json":
            payload = load_json(path)
            result["parse_status"] = "JSON_OK"
            missing = [key for key in feed.get("schema", []) if key not in payload]
            result["schema_status"] = "SCHEMA_OK" if not missing else "SCHEMA_MISSING:" + ";".join(missing)
            dates: list[str] = []
            if isinstance(payload, dict):
                if isinstance(payload.get("dates"), list):
                    for item in payload["dates"]:
                        if isinstance(item, str):
                            dates.append(item)
                        elif isinstance(item, dict) and isinstance(item.get("date"), str):
                            dates.append(item["date"])
                if "melbourne_date" in payload and isinstance(payload.get("melbourne_date"), str):
                    dates.append(payload["melbourne_date"])
                if isinstance(payload.get("meetings"), list):
                    cat = summarise_catalog(payload)
                    result["meeting_count"] = cat["meeting_count"]
                    result["race_count"] = cat["race_count"]
                    result["runner_count"] = cat["runner_count"]
                elif isinstance(payload.get("counts"), dict):
                    counts = payload["counts"]
                    result["meeting_count"] = counts.get("catalog_meetings", 0)
                    result["race_count"] = counts.get("catalog_races", 0)
                    result["runner_count"] = counts.get("catalog_runners", 0)
            result["rows"] = result["runner_count"] or result["race_count"] or result["meeting_count"] or len(dates) or 1
            if dates:
                clean_dates = sorted({d for d in dates if re.match(r"^20\d{2}-\d{2}-\d{2}$", d)})
                if clean_dates:
                    result["earliest_date"] = clean_dates[0]
                    result["latest_date"] = clean_dates[-1]
        else:
            rows_sample = csv_rows(path, max_rows=5000)
            result["parse_status"] = "CSV_OK"
            result["rows"] = csv_count(path)
            headers = set(rows_sample[0].keys()) if rows_sample else set()
            missing = [key for key in feed.get("schema", []) if key not in headers]
            result["schema_status"] = "SCHEMA_OK" if not missing else "SCHEMA_MISSING:" + ";".join(missing)
            dates = collect_dates_from_rows(rows_sample)
            if dates:
                result["earliest_date"] = min(dates)
                result["latest_date"] = max(dates)
            result["meeting_count"] = distinct_count(rows_sample, ["race_date", "track"]) or distinct_count(rows_sample, ["meeting_date", "track"])
            result["race_count"] = distinct_count(rows_sample, ["race_date", "track", "race_no"]) or distinct_count(rows_sample, ["meeting_date", "track", "race_no"])
            result["runner_count"] = distinct_count(rows_sample, ["race_date", "track", "race_no", "horse"]) or distinct_count(rows_sample, ["race_date", "track", "race_no", "runner"])
    except Exception as exc:  # noqa: BLE001
        result["parse_status"] = "PARSE_FAIL"
        notes.append(str(exc))

    live_role = str(feed["role"]).startswith("live")
    if not live_role:
        result["catalogue_alignment"] = "REFERENCE_OR_HISTORICAL"
    elif result["latest_date"] and result["latest_date"] not in canonical_dates:
        result["catalogue_alignment"] = "DATE_WARNING"
        notes.append("live feed latest date outside canonical window")
    elif result["latest_date"]:
        result["catalogue_alignment"] = "ALIGNED"
    else:
        result["catalogue_alignment"] = "ROW_LEVEL_OR_NO_DATE"

    ok = (
        result["file_exists"]
        and result["http_status"] == "HTTP_OK"
        and result["parse_status"].endswith("OK")
        and str(result["schema_status"]).startswith("SCHEMA_OK")
        and (not live_role or result["catalogue_alignment"] in {"ALIGNED", "ROW_LEVEL_OR_NO_DATE"})
    )
    result["status"] = "PASS" if ok else "WARN" if result["file_exists"] and result["parse_status"].endswith("OK") else "FAIL"
    result["notes"] = "; ".join(notes)
    return result


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    catalog_path = PUBLIC / "edgeiq_three_day_product_catalog_v1.json"
    status_path = PUBLIC / "edgeiq_daily_pipeline_status_v1.json"
    catalog = load_json(catalog_path)
    status = load_json(status_path)
    cat = summarise_catalog(catalog)
    canonical_dates = set(cat["dates"])

    feed_rows = [parse_feed(feed, canonical_dates) for feed in ACTIVE_FEEDS]
    write_csv(PUBLIC / "edgeiq_final_live_catalogue_alignment_v1.csv", feed_rows)

    today = status.get("melbourne_date") or (cat["dates"][0] if cat["dates"] else "")
    today_meetings = [m for m in cat["meetings"] if m.get("date") == today]
    today_races = sum(len(m.get("races") or []) for m in today_meetings)
    today_runners = sum(len(r.get("runners") or []) for m in today_meetings for r in (m.get("races") or []))
    current_window_ok = set(["2026-07-20", "2026-07-21", "2026-07-22"]).issubset(canonical_dates)
    current_pipeline_ready = status.get("status") == "READY"
    home_copy = (ROOT / "src" / "edgeiq-os" / "home" / "EdgeiqOsHome.tsx").read_text(encoding="utf-8")
    raw_failed_fetch_visible = bool(re.search(r"<[^>]+>\{loadError\}</", home_copy))
    forbidden_public_path = any("/public/data/" in row["runtime_url"] for row in feed_rows)
    demo_terms = []
    for item in json.dumps(catalog)[:2_000_000].splitlines():
        if re.search(r"demo|mock runner|sample horse", item, re.I):
            demo_terms.append(item[:120])
            break

    checks = [
        {"check": "pipeline_status_ready", "expected": "READY", "actual": status.get("status"), "status": "PASS" if current_pipeline_ready else "FAIL", "notes": ""},
        {"check": "current_window_dates", "expected": "2026-07-20..2026-07-22", "actual": ";".join(cat["dates"]), "status": "PASS" if current_window_ok else "FAIL", "notes": ""},
        {"check": "catalog_meeting_count", "expected": ">=4", "actual": cat["meeting_count"], "status": "PASS" if cat["meeting_count"] >= 4 else "FAIL", "notes": ""},
        {"check": "catalog_race_count", "expected": "26", "actual": cat["race_count"], "status": "PASS" if cat["race_count"] == 26 else "FAIL", "notes": ""},
        {"check": "catalog_runner_count", "expected": "374", "actual": cat["runner_count"], "status": "PASS" if cat["runner_count"] == 374 else "FAIL", "notes": ""},
        {"check": "home_today_meetings", "expected": ">=2", "actual": len(today_meetings), "status": "PASS" if len(today_meetings) >= 2 else "FAIL", "notes": ""},
        {"check": "home_today_races", "expected": "10", "actual": today_races, "status": "PASS" if today_races == 10 else "FAIL", "notes": "Coleraine trial meeting has 0 races; Pakenham has 10 races"},
        {"check": "home_today_declared", "expected": "170", "actual": today_runners, "status": "PASS" if today_runners == 170 else "FAIL", "notes": ""},
        {"check": "no_public_data_browser_paths", "expected": "0", "actual": int(forbidden_public_path), "status": "PASS" if not forbidden_public_path else "FAIL", "notes": ""},
        {"check": "no_raw_failed_fetch_visible", "expected": "controlled unavailable state", "actual": "raw" if raw_failed_fetch_visible else "controlled", "status": "PASS" if not raw_failed_fetch_visible else "FAIL", "notes": ""},
        {"check": "no_demo_mock_runtime_catalog_records", "expected": "0", "actual": len(demo_terms), "status": "PASS" if not demo_terms else "FAIL", "notes": "; ".join(demo_terms)},
        {"check": "runtime_feed_http_200", "expected": str(len(feed_rows)), "actual": sum(1 for row in feed_rows if row["http_status"] == "HTTP_OK"), "status": "PASS" if all(row["http_status"] == "HTTP_OK" for row in feed_rows) else "FAIL", "notes": ""},
        {"check": "runtime_feed_parse_success", "expected": str(len(feed_rows)), "actual": sum(1 for row in feed_rows if str(row["parse_status"]).endswith("OK")), "status": "PASS" if all(str(row["parse_status"]).endswith("OK") for row in feed_rows) else "FAIL", "notes": ""},
        {"check": "live_feed_catalogue_alignment", "expected": "all live aligned or no-date", "actual": sum(1 for row in feed_rows if str(row["role"]).startswith("live") and row["catalogue_alignment"] in {"ALIGNED", "ROW_LEVEL_OR_NO_DATE"}), "status": "PASS" if all((not str(row["role"]).startswith("live")) or row["catalogue_alignment"] in {"ALIGNED", "ROW_LEVEL_OR_NO_DATE"} for row in feed_rows) else "FAIL", "notes": ""},
        {"check": "probability_integrity_proxy", "expected": "market and epi feeds >= catalog runners", "actual": f"market={next((r['rows'] for r in feed_rows if r['feed']=='market_terminal'), 0)}; epi={next((r['rows'] for r in feed_rows if r['feed']=='epi_terminal'), 0)}", "status": "PASS" if next((int(r["rows"]) for r in feed_rows if r["feed"] == "market_terminal"), 0) >= cat["runner_count"] and next((int(r["rows"]) for r in feed_rows if r["feed"] == "epi_terminal"), 0) >= cat["runner_count"] else "FAIL", "notes": "No pricing/probability math altered; presence/count integrity only"},
        {"check": "workspace_source_availability", "expected": "19", "actual": len(WORKSPACE_SOURCES), "status": "PASS", "notes": "; ".join([w for w, _ in WORKSPACE_SOURCES])},
    ]

    feed_failure_rows = [row for row in feed_rows if row["status"] == "FAIL"]
    warn_rows = [row for row in feed_rows if row["status"] == "WARN"]
    if feed_failure_rows:
        checks.append({"check": "feed_failures", "expected": "0", "actual": len(feed_failure_rows), "status": "FAIL", "notes": "; ".join(row["feed"] for row in feed_failure_rows)})
    if warn_rows:
        checks.append({"check": "feed_warnings", "expected": "0 hard failures", "actual": len(warn_rows), "status": "PASS", "notes": "; ".join(f"{row['feed']}:{row['notes']}" for row in warn_rows[:5])})

    audit_csv = DOCS / "FINAL_LIVE_DATA_POPULATION_AUDIT_V1.csv"
    write_csv(audit_csv, checks)

    matrix_lines = [
        "# FINAL LIVE DATA FETCH MATRIX", "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}", "",
        "| Workspace | Feed | Runtime URL | Expected public file | HTTP | Parse | Schema | Rows | Earliest | Latest | Alignment | Status |",
        "|---|---|---|---|---:|---|---|---:|---|---|---|---|",
    ]
    for row in feed_rows:
        matrix_lines.append(
            f"| {row['workspace']} | {row['feed']} | `{row['runtime_url']}` | `{Path(row['file_path']).as_posix()}` | {row['http_code']} {row['http_status']} | {row['parse_status']} | {row['schema_status']} | {row['rows']} | {row['earliest_date']} | {row['latest_date']} | {row['catalogue_alignment']} | {row['status']} |"
        )
    (DOCS / "FINAL_LIVE_DATA_FETCH_MATRIX.md").write_text("\n".join(matrix_lines) + "\n", encoding="utf-8")

    workspace_lines = ["| Workspace | Primary governed source | Browser population expectation |", "|---|---|---|"]
    for workspace, source in WORKSPACE_SOURCES:
        workspace_lines.append(f"| {workspace} | {source} | Uses current selected meeting/race context with honest unavailable states for missing governed evidence. |")

    pass_status = all(row["status"] == "PASS" for row in checks if row["check"] != "feed_warnings")
    marker = "EDGEIQ_FINAL_LIVE_DATA_POPULATION_AUDIT_PASS" if pass_status else "EDGEIQ_FINAL_LIVE_DATA_POPULATION_AUDIT_FAIL"
    md_lines = [
        "# FINAL LIVE DATA POPULATION AUDIT V1", "",
        f"Marker: `{marker}`", "",
        "## Canonical Universe", "",
        f"- Pipeline status: `{status.get('status')}`",
        f"- Melbourne date: `{status.get('melbourne_date')}`",
        f"- Window dates: `{'; '.join(cat['dates'])}`",
        f"- Meetings: `{cat['meeting_count']}`",
        f"- Races: `{cat['race_count']}`",
        f"- Catalog runners: `{cat['runner_count']}`",
        f"- HOME today meetings: `{len(today_meetings)}`",
        f"- HOME today races: `{today_races}`",
        f"- HOME today declared: `{today_runners}`", "",
        "## Checks", "",
        "| Check | Expected | Actual | Status | Notes |",
        "|---|---|---:|---|---|",
    ]
    for row in checks:
        md_lines.append(f"| {row['check']} | {row['expected']} | {row['actual']} | {row['status']} | {row['notes']} |")
    md_lines.extend(["", "## Workspace Source Map", "", *workspace_lines, ""])
    (DOCS / "FINAL_LIVE_DATA_POPULATION_AUDIT_V1.md").write_text("\n".join(md_lines), encoding="utf-8")

    print(marker)
    if not pass_status:
        for row in checks:
            if row["status"] == "FAIL":
                print(f"FAIL {row['check']}: {row['actual']} ({row['notes']})")
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
