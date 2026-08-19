from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
TMP = ROOT / "outputs" / "tmp"

DISCOVERY_OUT = DATA / "racingcom_historical_meeting_discovery_v1.csv"
AUDIT_OUT = DATA / "racingcom_historical_meeting_discovery_v1_audit.csv"

CURRENT_LOADER_SOURCE_FILES = [
    DATA / "edgeiq_racingcom_historical_calendar_backfill_v1.csv",
    DATA / "racingcom_sectional_history_harvest_v1_manifest.csv",
    DATA / "racingcom_form_speed_data_url_audit_v1.csv",
    DATA / "edgeiq_vic_live_terminal_feed_v1.csv",
    DATA / "edgeiq_vic_three_day_meeting_universe.csv",
]

DATE_COLUMNS = ("race_date", "date", "meeting_date", "run_date", "date_k")
TRACK_COLUMNS = ("track", "venue", "track_name", "race_track", "meeting_track")
RACE_NO_COLUMNS = ("race_no", "race_number", "race", "source_race_no")
URL_COLUMNS = ("speed_data_url", "source_url", "source_speed_data_url")
STATE_COLUMNS = ("state", "venue_state", "track_state")
TYPE_COLUMNS = ("meeting_type", "meeting_kind", "race_type", "run_type")
TEXT_COLUMNS = ("race_name", "event_name", "race_class", "class", "class_name")

VIC_TRACK_SLUGS = {
    "SANDOWN LAKESIDE": "sportsbet-sandown-lakeside",
    "SPORTSBET SANDOWN LAKESIDE": "sportsbet-sandown-lakeside",
    "SANDOWN": "sandown",
    "CAULFIELD": "caulfield",
    "CAULFIELD HEATH": "caulfield-heath",
    "FLEMINGTON": "flemington",
    "MOONEE VALLEY": "moonee-valley",
    "PAKENHAM": "pakenham",
    "SOUTHSIDE PAKENHAM": "southside-pakenham",
    "CRANBOURNE": "cranbourne",
    "BALLARAT": "ballarat",
    "SPORTSBET BALLARAT": "sportsbet-ballarat",
    "BENDIGO": "bendigo",
    "WARRNAMBOOL": "warrnambool",
    "SALE": "sale",
    "MORNINGTON": "mornington",
    "SEYMOUR": "seymour",
    "BET365 SEYMOUR": "bet365-seymour",
    "WANGARATTA": "wangaratta",
    "WODONGA": "wodonga",
    "KILMORE": "kilmore",
    "BET365 PARK KILMORE": "bet365-park-kilmore",
    "KYNETON": "kyneton",
    "BET365 PARK KYNETON": "bet365-park-kyneton",
    "CASTERTON": "casterton",
    "COLAC": "colac",
    "HAMILTON": "hamilton",
    "ARARAT": "ararat",
    "TERANG": "terang",
    "SWAN HILL": "swan-hill",
    "ECHUCA": "echuca",
    "BET365 ECHUCA": "bet365-echuca",
    "BENALLA": "benalla",
    "MILDURA": "mildura",
    "MOE": "moe",
    "STAWELL": "stawell",
    "HORSHAM": "horsham",
    "GEELONG": "geelong",
    "LADBROKES GEELONG": "ladbrokes-geelong",
    "YARRA VALLEY": "yarra-valley",
    "BET365 YARRA VALLEY": "bet365-yarra-valley",
    "WERRIBEE": "werribee",
    "PICKLEBET PARK WERRIBEE": "picklebet-park-werribee",
    "DONALD": "donald",
}

VIC_TRACK_TOKENS = tuple(sorted(VIC_TRACK_SLUGS))
EXCLUDE_PATTERNS = ("TRIAL", "TRIALS", "JUMPOUT", "JUMPOUTS", "PICNIC", "PICNICS")

DISCOVERY_COLUMNS = [
    "meeting_date",
    "track",
    "track_slug",
    "race_no",
    "speed_data_url",
    "source_files",
    "source_file_count",
    "source_rows",
    "meeting_type",
    "excluded_flag",
    "excluded_reason",
    "page_probe_status",
    "page_loaded",
    "speed_data_visible",
    "rendered_layout",
    "runner_rows_visible",
    "reachability_status",
    "error",
]

AUDIT_COLUMNS = [
    "source_files_inspected",
    "source_files_with_candidate_columns",
    "known_rendered_pages",
    "current_loader_candidate_races",
    "discovered_candidate_races",
    "candidate_dates",
    "candidate_tracks",
    "candidate_races",
    "earliest_date",
    "latest_date",
    "current_loader_earliest_date",
    "current_loader_latest_date",
    "current_loader_tracks",
    "reachable_probe_limit",
    "probed_pages",
    "pages_loaded",
    "reachable_speed_data_pages",
    "reachable_rendered_layouts",
    "layout_a_pages",
    "layout_b_pages",
    "mixed_layout_pages",
    "no_visible_speed_data_pages",
    "page_errors",
    "source_file_limitation",
    "meeting_discovery_limitation",
    "date_range_limitation",
    "track_limitation",
    "root_cause",
    "graphql_endpoint_called_by_script",
    "api_key_extracted",
    "private_endpoint_used",
    "final_status",
]

NODE_HELPER = r"""
const fs = require("fs");

const inputPath = process.argv[2];
const outputPath = process.argv[3];
const rows = JSON.parse(fs.readFileSync(inputPath, "utf8"));
const PUBLIC_SPEED_RE = /^https:\/\/www\.racing\.com\/form\/\d{4}-\d{2}-\d{2}\/[^/]+\/race\/\d+\/speed-data(?:[?#].*)?$/i;

function clean(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function inspectRenderedSpeedData() {
  function cleanInPage(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }
  function rowCells(row) {
    return Array.from(row.querySelectorAll("th,td")).map((cell) => cleanInPage(cell.innerText || cell.textContent || ""));
  }
  function hasSummaryHeader(headerText) {
    return /DIST\s*RUN/i.test(headerText)
      && /\bEARLY\b/i.test(headerText)
      && /\bMID\b/i.test(headerText)
      && /\bLATE\b/i.test(headerText)
      && /\bPEAK\b/i.test(headerText)
      && /AVG\s*SPEED/i.test(headerText);
  }
  function hasSplitHeader(headerText) {
    return /\bOVERALL\b/i.test(headerText)
      || /\b\d+M\b/i.test(headerText)
      || /\b\d+M-\d+M\b/i.test(headerText)
      || /\b\d+M-FINISH\b/i.test(headerText);
  }

  let hasLayoutA = false;
  let hasLayoutB = false;
  let runnerRows = 0;
  const containers = Array.from(document.querySelectorAll("div.table-container"));

  for (const container of containers) {
    const tables = Array.from(container.querySelectorAll("table"));
    if (tables.length < 2) continue;
    const leftRows = Array.from(tables[0].querySelectorAll("tr")).map(rowCells);
    const dataRows = Array.from(tables[1].querySelectorAll("tr")).map(rowCells);
    if (!leftRows.length || !dataRows.length) continue;
    const leftHeader = cleanInPage((leftRows[0] || []).join(" "));
    const dataHeader = dataRows[0] || [];
    const headerText = cleanInPage(dataHeader.join(" "));
    if (!/POS\s*\/\s*HORSE/i.test(leftHeader)) continue;
    const count = Math.max(0, Math.min(leftRows.length - 1, dataRows.length - 1));
    if (hasSummaryHeader(headerText)) {
      hasLayoutA = true;
      runnerRows += count;
    } else if (hasSplitHeader(headerText)) {
      hasLayoutB = true;
      runnerRows += count;
    }
  }

  let layout = "";
  if (hasLayoutA && hasLayoutB) layout = "MIXED_RENDERED_LAYOUTS";
  else if (hasLayoutA) layout = "LAYOUT_A_SUMMARY_SPEED";
  else if (hasLayoutB) layout = "LAYOUT_B_SPLIT_TIMING";
  return {
    visibleSpeedData: Boolean(hasLayoutA || hasLayoutB),
    hasLayoutA,
    hasLayoutB,
    renderedLayout: layout,
    runnerRows,
  };
}

async function createBrowser(playwright) {
  try {
    const browser = await playwright.chromium.launch({
      headless: true,
      args: ["--disable-dev-shm-usage", "--no-sandbox"],
    });
    const context = await browser.newContext({
      acceptDownloads: false,
      viewport: { width: 1440, height: 1000 },
      userAgent: "EDGEiQ-Racing/1.0 historical-meeting-discovery-v1 (public page only)",
    });
    return { browser, context };
  } catch (err) {
    throw new Error(`browser_launch_failed:${err && err.message ? err.message : String(err)}`);
  }
}

async function settleAndScroll(page) {
  try {
    await page.waitForLoadState("networkidle", { timeout: 18000 });
  } catch (_err) {}
  await page.waitForTimeout(2200);
  for (let i = 0; i < 8; i += 1) {
    await page.mouse.wheel(0, 1800);
    await page.waitForTimeout(240);
  }
  await page.waitForTimeout(700);
}

async function probePage(page, row) {
  if (!PUBLIC_SPEED_RE.test(row.speed_data_url || "")) {
    return {
      speed_data_url: row.speed_data_url || "",
      page_loaded: "FALSE",
      speed_data_visible: "FALSE",
      rendered_layout: "",
      runner_rows_visible: "0",
      reachability_status: "SAFETY_BLOCKED",
      error: "Rejected non-public Racing.com speed-data URL.",
    };
  }
  try {
    await page.goto(row.speed_data_url, { waitUntil: "domcontentloaded", timeout: 90000 });
    await settleAndScroll(page);
  } catch (err) {
    return {
      speed_data_url: row.speed_data_url || "",
      page_loaded: "FALSE",
      speed_data_visible: "FALSE",
      rendered_layout: "",
      runner_rows_visible: "0",
      reachability_status: "PAGE_ERROR",
      error: err && err.message ? err.message : String(err),
    };
  }

  let rendered = null;
  for (const frame of page.frames()) {
    try {
      const data = await frame.evaluate(inspectRenderedSpeedData);
      if (data && data.visibleSpeedData) {
        rendered = data;
        break;
      }
    } catch (_err) {}
  }
  const result = rendered || {
    visibleSpeedData: false,
    renderedLayout: "",
    runnerRows: 0,
    hasLayoutA: false,
    hasLayoutB: false,
  };
  return {
    speed_data_url: row.speed_data_url || "",
    page_loaded: "TRUE",
    speed_data_visible: result.visibleSpeedData ? "TRUE" : "FALSE",
    rendered_layout: result.renderedLayout || "",
    runner_rows_visible: String(result.runnerRows || 0),
    reachability_status: result.visibleSpeedData ? "RENDERED_SPEED_DATA_VISIBLE" : "NO_RENDERED_SPEED_DATA_FOUND",
    error: "",
  };
}

(async () => {
  let playwright;
  try {
    playwright = require("playwright");
  } catch (err) {
    fs.writeFileSync(outputPath, JSON.stringify({ rows: [], runtime_error: `playwright_require_failed:${err && err.message ? err.message : String(err)}` }, null, 2));
    return;
  }

  const output = [];
  let browserBundle = null;
  try {
    browserBundle = await createBrowser(playwright);
    const page = await browserBundle.context.newPage();
    for (const row of rows) {
      const result = await probePage(page, row);
      output.push(result);
      fs.writeFileSync(outputPath, JSON.stringify({ rows: output, runtime_error: "" }, null, 2));
    }
  } catch (err) {
    fs.writeFileSync(outputPath, JSON.stringify({ rows: output, runtime_error: err && err.message ? err.message : String(err) }, null, 2));
  } finally {
    if (browserBundle && browserBundle.browser) {
      await browserBundle.browser.close().catch(() => {});
    }
  }
})();
"""

try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:
    csv.field_size_limit(2_147_483_647)


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return "" if text.upper() in {"NAN", "NONE", "NULL", "N/A", "NA", "-"} else text


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except UnicodeDecodeError:
        with path.open("r", encoding="latin-1", newline="") as handle:
            return list(csv.DictReader(handle))


def stream_csv(path: Path):
    if not path.exists():
        return
    try:
        handle = path.open("r", encoding="utf-8-sig", newline="")
    except UnicodeDecodeError:
        handle = path.open("r", encoding="latin-1", newline="")
    with handle:
        yield from csv.DictReader(handle)


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    tmp.replace(path)


def first(row: dict[str, str], columns: tuple[str, ...]) -> str:
    for column in columns:
        value = clean(row.get(column))
        if value:
            return value
    return ""


def date_from_text(value: Any) -> str:
    text = clean(value)
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        return match.group(0)
    match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if match:
        day, month, year = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    match = re.search(r"/form/(\d{4}-\d{2}-\d{2})/", text)
    return match.group(1) if match else ""


def race_no(value: Any) -> str:
    text = clean(value)
    match = re.search(r"\d+", text)
    return str(int(match.group(0))) if match else ""


def normalise_track(value: Any) -> str:
    track = clean(value).upper()
    track = re.sub(r"^(SPORTSBET|LADBROKES|BET365|PICKLEBET PARK|SOUTHSIDE)\s+", "", track)
    track = re.sub(r"[^A-Z0-9]+", " ", track)
    return re.sub(r"\s+", " ", track).strip()


def track_slug(track: str) -> str:
    raw = clean(track).upper()
    normalised = normalise_track(track)
    if raw in VIC_TRACK_SLUGS:
        return VIC_TRACK_SLUGS[raw]
    if normalised in VIC_TRACK_SLUGS:
        return VIC_TRACK_SLUGS[normalised]
    slug = clean(track).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return re.sub(r"-+", "-", slug).strip("-")


def track_from_url(value: Any) -> str:
    match = re.search(r"/form/\d{4}-\d{2}-\d{2}/([^/]+)/race/", clean(value))
    if not match:
        return ""
    return match.group(1).replace("-", " ").upper()


def race_no_from_url(value: Any) -> str:
    match = re.search(r"/race/(\d+)/", clean(value))
    return str(int(match.group(1))) if match else ""


def public_speed_url(value: Any) -> str:
    url = clean(value)
    if not url:
        return ""
    if url.startswith("/"):
        url = f"https://www.racing.com{url}"
    if not re.match(r"^https://www\.racing\.com/form/\d{4}-\d{2}-\d{2}/[^/]+/race/\d+/speed-data", url, re.I):
        return ""
    return url.split("#", 1)[0]


def construct_speed_url(meeting_date: str, track: str, rn: str) -> str:
    if not meeting_date or not track or not rn:
        return ""
    return f"https://www.racing.com/form/{meeting_date}/{track_slug(track)}/race/{rn}/speed-data"


def is_vic(row: dict[str, str], track: str) -> bool:
    state = first(row, STATE_COLUMNS).upper()
    if state:
        return state == "VIC"
    track_key = normalise_track(track)
    return any(token in track_key or track_key in token for token in VIC_TRACK_TOKENS)


def exclusion_reason(row: dict[str, str], track: str) -> str:
    context = " ".join(first(row, columns) for columns in (TYPE_COLUMNS, TEXT_COLUMNS))
    context = f"{context} {track}".upper()
    for token in EXCLUDE_PATTERNS:
        if token in context:
            return token
    return ""


def has_candidate_columns(header: list[str]) -> bool:
    columns = {clean(column).lower() for column in header}
    has_url = bool(columns.intersection(URL_COLUMNS))
    has_date = bool(columns.intersection(DATE_COLUMNS))
    has_track = bool(columns.intersection(TRACK_COLUMNS))
    has_race = bool(columns.intersection(RACE_NO_COLUMNS))
    return has_url or (has_date and has_track and has_race)


def input_csv_files() -> list[Path]:
    return sorted(
        path
        for path in DATA.glob("*.csv")
        if path.name not in {DISCOVERY_OUT.name, AUDIT_OUT.name}
    )


def discover_from_files(paths: list[Path]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    metrics = {
        "source_files_inspected": 0,
        "source_files_with_candidate_columns": 0,
        "excluded_rows": 0,
        "candidate_rows_seen": 0,
    }

    for path in paths:
        metrics["source_files_inspected"] += 1
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                header = list(reader.fieldnames or [])
        except UnicodeDecodeError:
            with path.open("r", encoding="latin-1", newline="") as handle:
                reader = csv.DictReader(handle)
                header = list(reader.fieldnames or [])
        except OSError:
            continue
        if not has_candidate_columns(header):
            continue
        metrics["source_files_with_candidate_columns"] += 1

        for row in stream_csv(path) or []:
            url = public_speed_url(first(row, URL_COLUMNS))
            meeting_date = date_from_text(first(row, DATE_COLUMNS)) or date_from_text(url)
            track = first(row, TRACK_COLUMNS) or track_from_url(url)
            rn = race_no(first(row, RACE_NO_COLUMNS)) or race_no_from_url(url)
            if not url:
                url = public_speed_url(construct_speed_url(meeting_date, track, rn))
            if not meeting_date or not track or not rn or not url:
                continue
            if not is_vic(row, track):
                continue
            reason = exclusion_reason(row, track)
            if reason:
                metrics["excluded_rows"] += 1
                continue

            metrics["candidate_rows_seen"] += 1
            slug = track_slug(track)
            key = (meeting_date, slug, rn)
            existing = by_key.get(key)
            if existing is None:
                by_key[key] = {
                    "meeting_date": meeting_date,
                    "track": normalise_track(track) or clean(track).upper(),
                    "track_slug": slug,
                    "race_no": rn,
                    "speed_data_url": url,
                    "source_files": path.name,
                    "source_file_count": 1,
                    "source_rows": 1,
                    "meeting_type": first(row, TYPE_COLUMNS) or "STANDARD_RACE_MEETING",
                    "excluded_flag": "FALSE",
                    "excluded_reason": "",
                    "page_probe_status": "NOT_PROBED",
                    "page_loaded": "",
                    "speed_data_visible": "",
                    "rendered_layout": "",
                    "runner_rows_visible": "",
                    "reachability_status": "NOT_PROBED",
                    "error": "",
                }
                continue
            source_files = set(clean(existing.get("source_files")).split(";"))
            source_files.add(path.name)
            existing["source_files"] = ";".join(sorted(source for source in source_files if source))
            existing["source_file_count"] = len([source for source in existing["source_files"].split(";") if source])
            existing["source_rows"] = int(existing.get("source_rows") or 0) + 1

    rows = sorted(by_key.values(), key=lambda item: (item["meeting_date"], item["track_slug"], int(item["race_no"])))
    return rows, metrics


def current_loader_candidates() -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in CURRENT_LOADER_SOURCE_FILES:
        for row in stream_csv(path) or []:
            url = public_speed_url(first(row, URL_COLUMNS))
            meeting_date = date_from_text(first(row, DATE_COLUMNS))
            track = first(row, TRACK_COLUMNS)
            rn = race_no(first(row, RACE_NO_COLUMNS))
            if not url:
                url = public_speed_url(construct_speed_url(meeting_date, track, rn))
            if not url or url in seen:
                continue
            if not meeting_date:
                meeting_date = date_from_text(url)
            if not track:
                track = track_from_url(url)
            if not rn:
                rn = race_no_from_url(url)
            seen.add(url)
            candidates.append(
                {
                    "meeting_date": meeting_date,
                    "track": normalise_track(track) or clean(track).upper(),
                    "track_slug": track_slug(track),
                    "race_no": rn,
                    "speed_data_url": url,
                }
            )
    candidates.sort(key=lambda item: clean(item.get("speed_data_url")))
    return candidates


def run_probe(candidates: list[dict[str, Any]], max_probe: int) -> tuple[dict[str, dict[str, str]], str]:
    selected = candidates[: max(0, max_probe)]
    if not selected:
        return {}, ""
    TMP.mkdir(parents=True, exist_ok=True)
    helper = TMP / "build_racingcom_historical_meeting_discovery_v1_helper.cjs"
    input_path = TMP / "build_racingcom_historical_meeting_discovery_v1_input.json"
    output_path = TMP / "build_racingcom_historical_meeting_discovery_v1_output.json"
    helper.write_text(NODE_HELPER, encoding="utf-8")
    input_path.write_text(json.dumps(selected, indent=2), encoding="utf-8")
    try:
        completed = subprocess.run(
            ["node", str(helper), str(input_path), str(output_path)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=max(600, len(selected) * 45),
            check=False,
        )
        runtime_error = clean(completed.stderr)
    except subprocess.TimeoutExpired as exc:
        runtime_error = f"node_timeout_after_{exc.timeout}_seconds"
    except Exception as exc:  # noqa: BLE001
        runtime_error = str(exc)

    if not output_path.exists():
        return {}, runtime_error or "probe_output_missing"
    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, f"probe_output_parse_failed:{exc}"
    runtime_error = clean(payload.get("runtime_error")) or runtime_error
    by_url = {clean(row.get("speed_data_url")): row for row in payload.get("rows", []) if clean(row.get("speed_data_url"))}
    return by_url, runtime_error


def known_rendered_results() -> dict[str, dict[str, str]]:
    by_url: dict[str, dict[str, Any]] = {}
    for row in read_csv(DATA / "racingcom_rendered_speed_data_normalised_v1.csv"):
        url = public_speed_url(row.get("source_url"))
        if not url:
            continue
        item = by_url.setdefault(url, {"layouts": set(), "runner_rows": 0})
        layout = clean(row.get("layout_type"))
        if layout:
            item["layouts"].add(layout)
        item["runner_rows"] += 1

    results: dict[str, dict[str, str]] = {}
    for url, item in by_url.items():
        layouts = sorted(item["layouts"])
        if len(layouts) > 1:
            rendered_layout = "MIXED_RENDERED_LAYOUTS"
        else:
            rendered_layout = layouts[0] if layouts else ""
        results[url] = {
            "speed_data_url": url,
            "page_loaded": "TRUE",
            "speed_data_visible": "TRUE",
            "rendered_layout": rendered_layout,
            "runner_rows_visible": str(item["runner_rows"]),
            "reachability_status": "KNOWN_RENDERED_SPEED_DATA_VISIBLE",
            "error": "",
        }
    return results


def apply_known_rendered_results(rows: list[dict[str, Any]], known_results: dict[str, dict[str, str]]) -> None:
    for row in rows:
        result = known_results.get(clean(row.get("speed_data_url")))
        if not result:
            continue
        row["page_probe_status"] = "KNOWN_RENDERED_OUTPUT"
        row["page_loaded"] = result["page_loaded"]
        row["speed_data_visible"] = result["speed_data_visible"]
        row["rendered_layout"] = result["rendered_layout"]
        row["runner_rows_visible"] = result["runner_rows_visible"]
        row["reachability_status"] = result["reachability_status"]
        row["error"] = ""


def apply_probe_results(rows: list[dict[str, Any]], probe_results: dict[str, dict[str, str]], max_probe: int) -> None:
    unverified = [row for row in rows if clean(row.get("page_probe_status")) == "NOT_PROBED"]
    selected_urls = {clean(row.get("speed_data_url")) for row in unverified[: max(0, max_probe)]}
    for row in rows:
        url = clean(row.get("speed_data_url"))
        if url not in selected_urls:
            continue
        result = probe_results.get(url)
        row["page_probe_status"] = "PROBED"
        if not result:
            row["reachability_status"] = "PROBE_RESULT_MISSING"
            row["error"] = "No probe result returned for selected URL."
            continue
        row["page_loaded"] = result.get("page_loaded", "")
        row["speed_data_visible"] = result.get("speed_data_visible", "")
        row["rendered_layout"] = result.get("rendered_layout", "")
        row["runner_rows_visible"] = result.get("runner_rows_visible", "")
        row["reachability_status"] = result.get("reachability_status", "")
        row["error"] = result.get("error", "")


def bool_text(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def audit_rows(rows: list[dict[str, Any]], metrics: dict[str, Any], current_rows: list[dict[str, Any]], max_probe: int) -> list[dict[str, Any]]:
    candidate_dates = sorted({clean(row.get("meeting_date")) for row in rows if clean(row.get("meeting_date"))})
    candidate_tracks = sorted({clean(row.get("track")) for row in rows if clean(row.get("track"))})
    current_dates = sorted({clean(row.get("meeting_date")) for row in current_rows if clean(row.get("meeting_date"))})
    current_tracks = sorted({clean(row.get("track")) for row in current_rows if clean(row.get("track"))})
    probed = [row for row in rows if clean(row.get("page_probe_status")) == "PROBED"]
    known = [row for row in rows if clean(row.get("page_probe_status")) == "KNOWN_RENDERED_OUTPUT"]
    checked = probed + known
    pages_loaded = [row for row in checked if clean(row.get("page_loaded")) == "TRUE"]
    visible = [row for row in checked if clean(row.get("speed_data_visible")) == "TRUE"]
    layout_a = [row for row in visible if clean(row.get("rendered_layout")) == "LAYOUT_A_SUMMARY_SPEED"]
    layout_b = [row for row in visible if clean(row.get("rendered_layout")) == "LAYOUT_B_SPLIT_TIMING"]
    mixed = [row for row in visible if clean(row.get("rendered_layout")) == "MIXED_RENDERED_LAYOUTS"]
    no_visible = [row for row in checked if clean(row.get("reachability_status")) == "NO_RENDERED_SPEED_DATA_FOUND"]
    errors = [row for row in checked if clean(row.get("reachability_status")) in {"PAGE_ERROR", "PROBE_RESULT_MISSING", "SAFETY_BLOCKED"}]

    source_file_limitation = len(rows) > len(current_rows)
    date_range_limitation = bool(candidate_dates and current_dates and (candidate_dates[0] < current_dates[0] or candidate_dates[-1] > current_dates[-1]))
    track_limitation = len(candidate_tracks) > len(current_tracks)
    meeting_discovery_limitation = source_file_limitation

    causes: list[str] = []
    if source_file_limitation:
        causes.append("SOURCE_FILE_LIMITATION")
    if meeting_discovery_limitation:
        causes.append("MEETING_DISCOVERY_LIMITATION")
    if date_range_limitation:
        causes.append("DATE_RANGE_LIMITATION")
    if track_limitation:
        causes.append("TRACK_LIMITATION")
    root_cause = ";".join(causes) if causes else "NO_LIMITATION_FOUND"

    final_status = "NO_CANDIDATE_RACES"
    if rows and visible:
        final_status = "HISTORICAL_MEETING_DISCOVERY_BUILT"
    elif rows and probed:
        final_status = "HISTORICAL_MEETING_DISCOVERY_PARTIAL"
    elif rows:
        final_status = "HISTORICAL_MEETING_DISCOVERY_UNPROBED"

    return [
        {
            "source_files_inspected": metrics.get("source_files_inspected", 0),
            "source_files_with_candidate_columns": metrics.get("source_files_with_candidate_columns", 0),
            "known_rendered_pages": len(known),
            "current_loader_candidate_races": len(current_rows),
            "discovered_candidate_races": len(rows),
            "candidate_dates": len(candidate_dates),
            "candidate_tracks": len(candidate_tracks),
            "candidate_races": len(rows),
            "earliest_date": candidate_dates[0] if candidate_dates else "",
            "latest_date": candidate_dates[-1] if candidate_dates else "",
            "current_loader_earliest_date": current_dates[0] if current_dates else "",
            "current_loader_latest_date": current_dates[-1] if current_dates else "",
            "current_loader_tracks": len(current_tracks),
            "reachable_probe_limit": max_probe,
            "probed_pages": len(probed),
            "pages_loaded": len(pages_loaded),
            "reachable_speed_data_pages": len(pages_loaded),
            "reachable_rendered_layouts": len(visible),
            "layout_a_pages": len(layout_a),
            "layout_b_pages": len(layout_b),
            "mixed_layout_pages": len(mixed),
            "no_visible_speed_data_pages": len(no_visible),
            "page_errors": len(errors),
            "source_file_limitation": bool_text(source_file_limitation),
            "meeting_discovery_limitation": bool_text(meeting_discovery_limitation),
            "date_range_limitation": bool_text(date_range_limitation),
            "track_limitation": bool_text(track_limitation),
            "root_cause": root_cause,
            "graphql_endpoint_called_by_script": "FALSE",
            "api_key_extracted": "FALSE",
            "private_endpoint_used": "FALSE",
            "final_status": final_status,
        }
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover historical Racing.com VIC speed-data race contexts.")
    parser.add_argument("--max-probe", type=int, default=0, help="Maximum additional public speed-data pages to render-probe after known rendered outputs are applied.")
    parser.add_argument("--start-date", default="", help="Optional YYYY-MM-DD discovery lower bound.")
    parser.add_argument("--end-date", default="", help="Optional YYYY-MM-DD discovery upper bound. Defaults to yesterday for historical discovery.")
    args = parser.parse_args()

    rows, metrics = discover_from_files(input_csv_files())
    start_date = date_from_text(args.start_date)
    end_date = date_from_text(args.end_date) or (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    if start_date:
        rows = [row for row in rows if clean(row.get("meeting_date")) >= start_date]
    if end_date:
        rows = [row for row in rows if clean(row.get("meeting_date")) <= end_date]

    # Probe recent contexts first because Racing.com rendered Speed Data is most reliable for current layouts.
    rows.sort(key=lambda item: (item["meeting_date"], item["track_slug"], int(item["race_no"])), reverse=True)
    current_rows = current_loader_candidates()

    known_results = known_rendered_results()
    apply_known_rendered_results(rows, known_results)

    probe_results, runtime_error = run_probe(
        [row for row in rows if clean(row.get("page_probe_status")) == "NOT_PROBED"],
        args.max_probe,
    )
    apply_probe_results(rows, probe_results, args.max_probe)
    if runtime_error:
        for row in rows[: max(0, args.max_probe)]:
            if clean(row.get("page_probe_status")) != "PROBED":
                continue
            if not clean(row.get("error")):
                row["error"] = runtime_error

    rows.sort(key=lambda item: (item["meeting_date"], item["track_slug"], int(item["race_no"])))
    audit = audit_rows(rows, metrics, current_rows, args.max_probe)

    write_csv(DISCOVERY_OUT, rows, DISCOVERY_COLUMNS)
    write_csv(AUDIT_OUT, audit, AUDIT_COLUMNS)

    summary = audit[0]
    print("Racing.com historical meeting discovery V1 built")
    print(f"candidate_dates={summary['candidate_dates']}")
    print(f"candidate_tracks={summary['candidate_tracks']}")
    print(f"candidate_races={summary['candidate_races']}")
    print(f"earliest_date={summary['earliest_date']}")
    print(f"latest_date={summary['latest_date']}")
    print(f"current_loader_candidate_races={summary['current_loader_candidate_races']}")
    print(f"reachable_rendered_layouts={summary['reachable_rendered_layouts']}")
    print(f"root_cause={summary['root_cause']}")
    print(f"final_status={summary['final_status']}")


if __name__ == "__main__":
    main()

