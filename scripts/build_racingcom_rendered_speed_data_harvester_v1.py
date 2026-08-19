from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
TMP = ROOT / "outputs" / "tmp"

RAW_OUT = DATA / "racingcom_rendered_speed_data_raw_v1.csv"
NORMALISED_OUT = DATA / "racingcom_rendered_speed_data_normalised_v1.csv"
SPLITS_OUT = DATA / "racingcom_rendered_speed_data_splits_v1.csv"
AUDIT_OUT = DATA / "racingcom_rendered_speed_data_harvester_v1_audit.csv"
BATCH_DIR = DATA / "racingcom_rendered_speed_data_batches"

DISCOVERY_SOURCE = DATA / "racingcom_historical_meeting_discovery_v1.csv"
FALLBACK_SOURCE_FILES = [
    DATA / "racingcom_sectional_history_harvest_v1_manifest.csv",
    DATA / "racingcom_form_speed_data_url_audit_v1.csv",
    DATA / "edgeiq_vic_live_terminal_feed_v1.csv",
    DATA / "edgeiq_vic_three_day_meeting_universe.csv",
]

PRIORITY_TEST_URL = "https://www.racing.com/form/2026-05-31/sportsbet-sandown-lakeside/race/3/speed-data"

TRACK_SLUG_ALIASES = {
    "SANDOWN LAKESIDE": "sandown-lakeside",
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
    "BET365 YARRA VALLEY": "bet365-yarra-valley",
    "YARRA VALLEY": "yarra-valley",
    "WERRIBEE": "werribee",
    "PICKLEBET PARK WERRIBEE": "picklebet-park-werribee",
    "DONALD": "donald",
}

RAW_COLUMNS = [
    "meeting_date",
    "track",
    "race_no",
    "source_url",
    "row_index",
    "raw_row_text",
    "visible_column_headers",
    "extract_status",
]

NORMALISED_COLUMNS = [
    "meeting_date",
    "track",
    "race_no",
    "source_url",
    "horse_name",
    "horse_key",
    "position",
    "dist_run",
    "early_speed",
    "mid_speed",
    "late_speed",
    "peak_speed",
    "avg_speed",
    "sectional_count",
    "layout_type",
    "normalise_status",
]

SPLIT_COLUMNS = [
    "meeting_date",
    "track",
    "race_no",
    "source_url",
    "horse_name",
    "horse_key",
    "position",
    "layout_type",
    "metric_name",
    "metric_value",
    "metric_type",
]

AUDIT_COLUMNS = [
    "candidate_races_available",
    "batch_size",
    "offset",
    "candidate_urls_loaded",
    "attempted_pages",
    "pages_loaded",
    "pages_with_visible_speed_data",
    "layout_a_pages",
    "layout_b_pages",
    "layout_a_summary_speed_pages",
    "layout_b_split_timing_pages",
    "raw_rows_extracted",
    "normalised_rows_output",
    "split_metric_rows_output",
    "unique_horses",
    "unique_races",
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

function findRenderedSpeedData() {
  function cleanInPage(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }
  function rowCells(row) {
    return Array.from(row.querySelectorAll("th,td")).map((cell) => cleanInPage(cell.innerText || cell.textContent || ""));
  }
  function numberText(value) {
    const match = cleanInPage(value).match(/-?\d+(?:\.\d+)?/);
    return match ? match[0] : "";
  }
  function horseKey(value) {
    return cleanInPage(value)
      .toUpperCase()
      .replace(/\s*\((NZ|IRE|GB|FR|USA|JPN|GER|SAF)\)\s*$/i, "")
      .replace(/[^A-Z0-9]+/g, "");
  }
  function parseHorse(cells) {
    const position = cleanInPage(cells.find((cell) => /\d+(?:st|nd|rd|th)/i.test(cell)) || cells[0] || "");
    const horseCell = cells.find((cell) => /^\d+\.\s+/.test(cell)) || cells[2] || cells[1] || cells.join(" ");
    let horseName = cleanInPage(horseCell);
    horseName = horseName.replace(/\s+T:\s*.*$/i, "").trim();
    horseName = horseName.replace(/^\d+\.\s*/, "").trim();
    horseName = horseName.replace(/\s+\(\d+\)\s*$/, "").trim();
    return { position, horseName, horseKey: horseKey(horseName) };
  }
  function metricType(metricName) {
    const name = cleanInPage(metricName).toUpperCase();
    if (name === "OVERALL") return "OVERALL_TIME";
    if (/^\d+M$/.test(name)) return "CUMULATIVE_MARKER_TIME";
    if (/^\d+M-\d+M$/.test(name) || /^\d+M-FINISH$/.test(name)) return "SECTIONAL_SPLIT_TIME";
    return "UNKNOWN";
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

  const result = {
    layoutA: [],
    layoutBNormalised: [],
    layoutBSplits: [],
    rawRows: [],
    hasLayoutA: false,
    hasLayoutB: false,
  };
  const seenLayoutBNormalised = new Set();
  const seenSplitMetrics = new Set();
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
    const headers = ["POS / HORSE", ...dataHeader];
    const rowCount = Math.min(leftRows.length - 1, dataRows.length - 1);

    if (hasSummaryHeader(headerText)) {
      result.hasLayoutA = true;
      for (let index = 0; index < rowCount; index += 1) {
        const left = leftRows[index + 1] || [];
        const metrics = dataRows[index + 1] || [];
        const horse = parseHorse(left);
        if (!horse.horseKey) continue;
        const speeds = {
          early: numberText(metrics[1]),
          mid: numberText(metrics[2]),
          late: numberText(metrics[3]),
          peak: numberText(metrics[4]),
          avg: numberText(metrics[5]),
        };
        const speedCount = Object.values(speeds).filter((value) => value !== "").length;
        const row = {
          rawRowText: cleanInPage([...left, ...metrics].join(" | ")),
          visibleColumnHeaders: cleanInPage(headers.join(" | ")),
          horseName: horse.horseName,
          horseKey: horse.horseKey,
          position: horse.position,
          distRun: cleanInPage(metrics[0] || ""),
          earlySpeed: speeds.early,
          midSpeed: speeds.mid,
          lateSpeed: speeds.late,
          peakSpeed: speeds.peak,
          avgSpeed: speeds.avg,
          sectionalCount: speedCount,
          layoutType: "LAYOUT_A_SUMMARY_SPEED",
          status: speedCount ? "RENDERED_LAYOUT_A_SUMMARY_SPEED_EXTRACTED" : "RENDERED_LAYOUT_A_MISSING_SPEEDS",
        };
        result.layoutA.push(row);
        result.rawRows.push(row);
      }
      continue;
    }

    if (hasSplitHeader(headerText)) {
      result.hasLayoutB = true;
      for (let index = 0; index < rowCount; index += 1) {
        const left = leftRows[index + 1] || [];
        const metrics = dataRows[index + 1] || [];
        const horse = parseHorse(left);
        if (!horse.horseKey) continue;
        const normalisedKey = `${horse.horseKey}|${horse.position}`;
        const rawRow = {
          rawRowText: cleanInPage([...left, ...metrics].join(" | ")),
          visibleColumnHeaders: cleanInPage(headers.join(" | ")),
          horseName: horse.horseName,
          horseKey: horse.horseKey,
          position: horse.position,
          distRun: "",
          earlySpeed: "",
          midSpeed: "",
          lateSpeed: "",
          peakSpeed: "",
          avgSpeed: "",
          sectionalCount: Math.max(0, metrics.filter((value) => cleanInPage(value)).length),
          layoutType: "LAYOUT_B_SPLIT_TIMING",
          status: "RENDERED_LAYOUT_B_SPLIT_TIMING_ROW_EXTRACTED",
        };
        result.rawRows.push(rawRow);
        if (!seenLayoutBNormalised.has(normalisedKey)) {
          seenLayoutBNormalised.add(normalisedKey);
          result.layoutBNormalised.push({
            ...rawRow,
            rawRowText: "",
            visibleColumnHeaders: "",
            sectionalCount: "",
            status: "NORMALISED_SPLIT_TIMING",
          });
        }
        for (let metricIndex = 0; metricIndex < dataHeader.length; metricIndex += 1) {
          const metricName = cleanInPage(dataHeader[metricIndex]);
          const metricValue = cleanInPage(metrics[metricIndex]);
          if (!metricName || !metricValue) continue;
          const splitKey = `${normalisedKey}|${metricName}|${metricValue}`;
          if (seenSplitMetrics.has(splitKey)) continue;
          seenSplitMetrics.add(splitKey);
          result.layoutBSplits.push({
            horseName: horse.horseName,
            horseKey: horse.horseKey,
            position: horse.position,
            layoutType: "LAYOUT_B_SPLIT_TIMING",
            metricName,
            metricValue,
            metricType: metricType(metricName),
          });
        }
      }
    }
  }
  return result;
}

async function createBrowser(playwright) {
  const errors = [];
  try {
    const browser = await playwright.chromium.launch({
      headless: true,
      args: ["--disable-dev-shm-usage", "--no-sandbox"],
    });
    const context = await browser.newContext({
      acceptDownloads: false,
      viewport: { width: 1440, height: 1000 },
      userAgent: "EDGEiQ-Racing/1.0 rendered-speed-data-harvest-v1 (public page only)",
    });
    return { browser, context, closeBrowser: true };
  } catch (err) {
    errors.push(`launch:${err && err.message ? err.message : String(err)}`);
  }

  try {
    const browser = await playwright.chromium.connectOverCDP("http://127.0.0.1:9222");
    const context = browser.contexts()[0] || await browser.newContext({
      acceptDownloads: false,
      viewport: { width: 1440, height: 1000 },
      userAgent: "EDGEiQ-Racing/1.0 rendered-speed-data-harvest-v1 (public page only)",
    });
    return { browser, context, closeBrowser: false };
  } catch (err) {
    errors.push(`cdp:${err && err.message ? err.message : String(err)}`);
  }

  throw new Error(errors.join(" | "));
}

async function settleAndScroll(page) {
  try {
    await page.waitForLoadState("networkidle", { timeout: 6000 });
  } catch (_err) {}
  await page.waitForTimeout(900);
  for (let i = 0; i < 6; i += 1) {
    await page.mouse.wheel(0, 2200);
    await page.waitForTimeout(140);
  }
  await page.waitForTimeout(350);
}

async function extractPage(page, row) {
  if (!PUBLIC_SPEED_RE.test(row.source_url || "")) {
    return {
      pageLoaded: false,
      visibleSpeedData: false,
      hasLayoutA: false,
      hasLayoutB: false,
      rawRows: [],
      normalisedRows: [],
      splitRows: [],
      status: "SAFETY_BLOCKED",
      error: "Rejected non-public Racing.com speed-data URL.",
    };
  }

  try {
    await page.goto(row.source_url, { waitUntil: "domcontentloaded", timeout: 90000 });
    await settleAndScroll(page);
  } catch (err) {
    return {
      pageLoaded: false,
      visibleSpeedData: false,
      hasLayoutA: false,
      hasLayoutB: false,
      rawRows: [],
      normalisedRows: [],
      splitRows: [],
      status: "NO_RENDERED_PAGE_ACCESS",
      error: err && err.message ? err.message : String(err),
    };
  }

  let extracted = null;
  for (const frame of page.frames()) {
    try {
      const data = await frame.evaluate(findRenderedSpeedData);
      if (data && ((data.layoutA || []).length || (data.layoutBNormalised || []).length || (data.layoutBSplits || []).length)) {
        extracted = data;
        break;
      }
    } catch (_err) {}
  }

  const data = extracted || {
    layoutA: [],
    layoutBNormalised: [],
    layoutBSplits: [],
    rawRows: [],
    hasLayoutA: false,
    hasLayoutB: false,
  };
  const useLayoutA = Boolean((data.layoutA || []).length);
  const useLayoutB = !useLayoutA && Boolean((data.layoutBNormalised || []).length || (data.layoutBSplits || []).length);
  const visibleSpeedData = Boolean(useLayoutA || useLayoutB);
  const rawRows = [];
  const normalisedRows = [];
  const splitRows = [];

  for (let index = 0; index < (data.rawRows || []).length; index += 1) {
    const item = data.rawRows[index];
    rawRows.push({
      meeting_date: row.meeting_date || "",
      track: row.track || "",
      race_no: row.race_no || "",
      source_url: row.source_url || "",
      row_index: index + 1,
      raw_row_text: item.rawRowText || "",
      visible_column_headers: item.visibleColumnHeaders || "",
      extract_status: item.status || "RENDERED_SPEED_DATA_ROW_EXTRACTED",
    });
  }

  const normalisedSourceRows = useLayoutA ? (data.layoutA || []) : (data.layoutBNormalised || []);
  for (const item of normalisedSourceRows) {
    normalisedRows.push({
      meeting_date: row.meeting_date || "",
      track: row.track || "",
      race_no: row.race_no || "",
      source_url: row.source_url || "",
      horse_name: item.horseName || "",
      horse_key: item.horseKey || "",
      position: item.position || "",
      dist_run: item.distRun || "",
      early_speed: item.earlySpeed || "",
      mid_speed: item.midSpeed || "",
      late_speed: item.lateSpeed || "",
      peak_speed: item.peakSpeed || "",
      avg_speed: item.avgSpeed || "",
      sectional_count: item.sectionalCount || "",
      layout_type: item.layoutType || "",
      normalise_status: item.layoutType === "LAYOUT_B_SPLIT_TIMING"
        ? "NORMALISED_SPLIT_TIMING"
        : (item.horseName && item.avgSpeed ? "NORMALISED_SUMMARY_SPEED" : "NORMALISED_WITH_MISSING_FIELDS"),
    });
  }

  for (const item of (useLayoutB ? data.layoutBSplits || [] : [])) {
    splitRows.push({
      meeting_date: row.meeting_date || "",
      track: row.track || "",
      race_no: row.race_no || "",
      source_url: row.source_url || "",
      horse_name: item.horseName || "",
      horse_key: item.horseKey || "",
      position: item.position || "",
      layout_type: item.layoutType || "LAYOUT_B_SPLIT_TIMING",
      metric_name: item.metricName || "",
      metric_value: item.metricValue || "",
      metric_type: item.metricType || "UNKNOWN",
    });
  }

  return {
    pageLoaded: true,
    visibleSpeedData,
    hasLayoutA: useLayoutA,
    hasLayoutB: useLayoutB,
    rawRows,
    normalisedRows,
    splitRows,
    status: visibleSpeedData ? "RENDERED_SPEED_DATA_EXTRACTED" : "NO_RENDERED_SPEED_DATA_FOUND",
    error: "",
  };
}

(async () => {
  const payload = {
    pages: [],
    rawRows: [],
    normalisedRows: [],
    splitRows: [],
    runtime_error: "",
  };
  function writeProgress() {
    fs.writeFileSync(outputPath, JSON.stringify(payload, null, 2));
  }

  let playwright;
  try {
    playwright = require("playwright");
  } catch (err) {
    payload.runtime_error = `playwright_require_failed:${err.message || String(err)}`;
    writeProgress();
    return;
  }

  let bundle;
  try {
    bundle = await createBrowser(playwright);
  } catch (err) {
    payload.runtime_error = `browser_start_failed:${err.message || String(err)}`;
    writeProgress();
    return;
  }

  const { browser, context, closeBrowser } = bundle;
  const concurrency = Math.max(1, Math.min(4, Number(process.env.EDGEIQ_RENDERED_SPEED_CONCURRENCY || 4), rows.length));
  let cursor = 0;

  async function worker() {
    const page = await context.newPage();
    try {
      while (true) {
        const index = cursor;
        cursor += 1;
        if (index >= rows.length) break;
        const row = rows[index];
        let result;
        try {
          result = await extractPage(page, row);
        } catch (err) {
          result = {
            pageLoaded: false,
            visibleSpeedData: false,
            hasLayoutA: false,
            hasLayoutB: false,
            rawRows: [],
            normalisedRows: [],
            splitRows: [],
            status: "NO_RENDERED_PAGE_ACCESS",
            error: err && err.message ? err.message : String(err),
          };
        }
        payload.pages.push({
          source_url: row.source_url || "",
          meeting_date: row.meeting_date || "",
          track: row.track || "",
          race_no: row.race_no || "",
          page_loaded: result.pageLoaded ? "TRUE" : "FALSE",
          visible_speed_data: result.visibleSpeedData ? "TRUE" : "FALSE",
          has_layout_a: result.hasLayoutA ? "TRUE" : "FALSE",
          has_layout_b: result.hasLayoutB ? "TRUE" : "FALSE",
          raw_rows: result.rawRows.length,
          normalised_rows: result.normalisedRows.length,
          split_rows: result.splitRows.length,
          status: result.status,
          error: result.error || "",
        });
        payload.rawRows.push(...result.rawRows);
        payload.normalisedRows.push(...result.normalisedRows);
        payload.splitRows.push(...result.splitRows);
        writeProgress();
      }
    } finally {
      await page.close().catch(() => {});
    }
  }

  await Promise.all(Array.from({ length: concurrency }, () => worker()));
  if (closeBrowser) await browser.close().catch(() => {});
  writeProgress();
})();
"""


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"NAN", "NONE", "NULL", "N/A", "NA", "-"} else re.sub(r"\s+", " ", text)


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    tmp.replace(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except UnicodeDecodeError:
        with path.open("r", encoding="latin-1", newline="") as handle:
            return list(csv.DictReader(handle))


def public_speed_url(url: Any) -> str:
    text = clean(url)
    return text if re.fullmatch(r"https://www\.racing\.com/form/\d{4}-\d{2}-\d{2}/[^/]+/race/\d+/speed-data(?:[?#].*)?", text, flags=re.IGNORECASE) else ""


def date_from_text(value: Any) -> str:
    match = re.search(r"\d{4}-\d{2}-\d{2}", clean(value))
    return match.group(0) if match else ""


def race_no(value: Any) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def normalise_track(value: Any) -> str:
    text = clean(value).upper()
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def track_slug(track: str) -> str:
    key = normalise_track(track)
    if key in TRACK_SLUG_ALIASES:
        return TRACK_SLUG_ALIASES[key]
    slug = clean(track).lower().replace("&", "and")
    slug = re.sub(r"[']", "", slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return re.sub(r"-+", "-", slug).strip("-")


def construct_url(meeting_date: str, track: str, rn: str) -> str:
    if not meeting_date or not track or not rn:
        return ""
    return f"https://www.racing.com/form/{meeting_date}/{track_slug(track)}/race/{rn}/speed-data"


def first(row: dict[str, str], columns: tuple[str, ...]) -> str:
    for column in columns:
        value = clean(row.get(column))
        if value:
            return value
    return ""


def load_discovery_candidates(start_date: str, end_date: str) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()
    if not DISCOVERY_SOURCE.exists():
        return candidates
    for row in read_csv(DISCOVERY_SOURCE):
        if clean(row.get("excluded_flag")).upper() == "TRUE":
            continue
        url = public_speed_url(row.get("speed_data_url"))
        meeting_date = date_from_text(row.get("meeting_date")) or date_from_text(url)
        track = clean(row.get("track"))
        rn = race_no(row.get("race_no"))
        if not url or url in seen:
            continue
        if not rn:
            match = re.search(r"/race/(\d+)/", url)
            rn = race_no(match.group(1) if match else "")
        if start_date and meeting_date and meeting_date < start_date:
            continue
        if end_date and meeting_date and meeting_date > end_date:
            continue
        seen.add(url)
        candidates.append(
            {
                "meeting_date": meeting_date,
                "track": track,
                "race_no": rn,
                "source_url": url,
            }
        )
    candidates.sort(key=lambda item: (item["meeting_date"], track_slug(item["track"]), int(item["race_no"] or 0), item["source_url"]))
    return candidates


def load_fallback_candidates(start_date: str, end_date: str) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()
    for path in FALLBACK_SOURCE_FILES:
        for row in read_csv(path):
            url = public_speed_url(first(row, ("speed_data_url", "source_url", "source_speed_data_url")))
            meeting_date = date_from_text(first(row, ("meeting_date", "race_date", "date")))
            track = first(row, ("track", "venue", "track_name"))
            rn = race_no(first(row, ("race_no", "race_number", "race")))
            if not url:
                url = public_speed_url(construct_url(meeting_date, track, rn))
            if not url or url in seen:
                continue
            if not meeting_date:
                meeting_date = date_from_text(url)
            if not rn:
                match = re.search(r"/race/(\d+)/", url)
                rn = race_no(match.group(1) if match else "")
            if start_date and meeting_date and meeting_date < start_date:
                continue
            if end_date and meeting_date and meeting_date > end_date:
                continue
            seen.add(url)
            candidates.append(
                {
                    "meeting_date": meeting_date,
                    "track": track,
                    "race_no": rn,
                    "source_url": url,
                }
            )
    candidates.sort(key=lambda item: (0 if item["source_url"].lower() == PRIORITY_TEST_URL.lower() else 1, item["source_url"]))
    return candidates


def load_candidates(start_date: str, end_date: str) -> list[dict[str, str]]:
    discovery_candidates = load_discovery_candidates(start_date, end_date)
    if discovery_candidates:
        return discovery_candidates
    return load_fallback_candidates(start_date, end_date)


def run_node_harvester(candidates: list[dict[str, str]]) -> tuple[dict[str, Any], str]:
    TMP.mkdir(parents=True, exist_ok=True)
    helper = TMP / "build_racingcom_rendered_speed_data_harvester_v1_helper.cjs"
    input_path = TMP / "build_racingcom_rendered_speed_data_harvester_v1_input.json"
    output_path = TMP / "build_racingcom_rendered_speed_data_harvester_v1_output.json"
    helper.write_text(NODE_HELPER, encoding="utf-8")
    input_path.write_text(json.dumps(candidates, indent=2), encoding="utf-8")

    def read_partial() -> dict[str, Any]:
        if not output_path.exists():
            return {"pages": [], "rawRows": [], "normalisedRows": [], "splitRows": [], "runtime_error": ""}
        try:
            return json.loads(output_path.read_text(encoding="utf-8"))
        except Exception:
            return {"pages": [], "rawRows": [], "normalisedRows": [], "splitRows": [], "runtime_error": "output_parse_failed"}

    try:
        completed = subprocess.run(
            ["node", str(helper), str(input_path), str(output_path)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=max(600, len(candidates) * 45),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return read_partial(), f"node_timeout_after_{exc.timeout}_seconds"
    except Exception as exc:  # noqa: BLE001
        return read_partial(), f"node_failed:{exc.__class__.__name__}:{exc}"

    payload = read_partial()
    if completed.returncode != 0:
        message = clean(completed.stderr) or clean(completed.stdout) or f"return_code_{completed.returncode}"
        return payload, f"node_returned_error:{message[:500]}"
    return payload, clean(payload.get("runtime_error"))


def final_status(attempted: int, pages_loaded: int, visible_pages: int, normalised_rows: int, safety_blocked: bool) -> str:
    if safety_blocked:
        return "SAFETY_BLOCKED"
    if attempted == 0:
        return "NO_CANDIDATE_URLS"
    if normalised_rows == 0:
        return "NO_RENDERED_SPEED_DATA_FOUND"
    if pages_loaded == attempted and visible_pages == attempted:
        return "RENDERED_SPEED_DATA_HARVEST_SUCCESS"
    return "RENDERED_SPEED_DATA_HARVEST_PARTIAL"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Harvest visible rendered Racing.com Speed Data rows from public pages.")
    parser.add_argument("--max-races", type=int, default=None, help="Backward-compatible alias for --batch-size.")
    parser.add_argument("--batch-size", type=int, default=250)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--start-date", default="")
    parser.add_argument("--end-date", default="")
    parser.add_argument("--force", action="store_true", help="Accepted for repeatability; rendered outputs are rebuilt for the selected candidate set.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    candidates = load_candidates(date_from_text(args.start_date), date_from_text(args.end_date))
    batch_size = max(0, args.max_races if args.max_races is not None else args.batch_size)
    offset = max(0, args.offset)
    selected = candidates[offset : offset + batch_size]
    print(
        f"[racingcom_rendered_speed_v1] candidate_races_available={len(candidates)} "
        f"batch_size={batch_size} offset={offset} selected={len(selected)}"
    )
    if selected:
        print(f"[racingcom_rendered_speed_v1] first_url={selected[0]['source_url']}")

    if not selected:
        write_csv(RAW_OUT, [], RAW_COLUMNS)
        write_csv(NORMALISED_OUT, [], NORMALISED_COLUMNS)
        write_csv(SPLITS_OUT, [], SPLIT_COLUMNS)
        write_csv(
            AUDIT_OUT,
            [
                {
                    "candidate_urls_loaded": 0,
                    "candidate_races_available": len(candidates),
                    "batch_size": batch_size,
                    "offset": offset,
                    "attempted_pages": 0,
                    "pages_loaded": 0,
                    "pages_with_visible_speed_data": 0,
                    "layout_a_pages": 0,
                    "layout_b_pages": 0,
                    "layout_a_summary_speed_pages": 0,
                    "layout_b_split_timing_pages": 0,
                    "raw_rows_extracted": 0,
                    "normalised_rows_output": 0,
                    "split_metric_rows_output": 0,
                    "unique_horses": 0,
                    "unique_races": 0,
                    "graphql_endpoint_called_by_script": "FALSE",
                    "api_key_extracted": "FALSE",
                    "private_endpoint_used": "FALSE",
                    "final_status": "NO_CANDIDATE_URLS",
                }
            ],
            AUDIT_COLUMNS,
        )
        return

    payload, runtime_error = run_node_harvester(selected)
    if runtime_error:
        print(f"[racingcom_rendered_speed_v1] browser warning: {runtime_error}")
    raw_rows = list(payload.get("rawRows") or [])
    normalised_rows = list(payload.get("normalisedRows") or [])
    split_rows = list(payload.get("splitRows") or [])
    pages = list(payload.get("pages") or [])
    pages_by_url = {clean(row.get("source_url")): row for row in pages}
    safety_blocked = False

    for item in selected:
        if item["source_url"] in pages_by_url:
            if clean(pages_by_url[item["source_url"]].get("status")) == "SAFETY_BLOCKED":
                safety_blocked = True
            continue
        pages.append(
            {
                "source_url": item["source_url"],
                "meeting_date": item["meeting_date"],
                "track": item["track"],
                "race_no": item["race_no"],
                "page_loaded": "FALSE",
                "visible_speed_data": "FALSE",
                "has_layout_a": "FALSE",
                "has_layout_b": "FALSE",
                "raw_rows": 0,
                "normalised_rows": 0,
                "split_rows": 0,
                "status": "NO_RENDERED_PAGE_ACCESS",
                "error": runtime_error or "Browser runner did not return this page.",
            }
        )

    pages_loaded = sum(1 for row in pages if clean(row.get("page_loaded")) == "TRUE")
    visible_pages = sum(1 for row in pages if clean(row.get("visible_speed_data")) == "TRUE")
    layout_a_pages = sum(1 for row in pages if clean(row.get("has_layout_a")) == "TRUE")
    layout_b_pages = sum(1 for row in pages if clean(row.get("has_layout_b")) == "TRUE")
    unique_horses = len({clean(row.get("horse_key")) for row in normalised_rows if clean(row.get("horse_key"))})
    unique_races = len(
        {
            "|".join([clean(row.get("meeting_date")), clean(row.get("track")), clean(row.get("race_no"))])
            for row in normalised_rows
            if clean(row.get("meeting_date")) and clean(row.get("track")) and clean(row.get("race_no"))
        }
    )
    status = final_status(len(selected), pages_loaded, visible_pages, len(normalised_rows), safety_blocked)
    batch_prefix = f"batch_{offset:04d}"
    batch_raw_out = BATCH_DIR / f"{batch_prefix}_raw.csv"
    batch_normalised_out = BATCH_DIR / f"{batch_prefix}_normalised.csv"
    batch_splits_out = BATCH_DIR / f"{batch_prefix}_splits.csv"
    batch_audit_out = BATCH_DIR / f"{batch_prefix}_audit.csv"
    audit_row = {
        "candidate_races_available": len(candidates),
        "batch_size": batch_size,
        "offset": offset,
        "candidate_urls_loaded": len(candidates),
        "attempted_pages": len(selected),
        "pages_loaded": pages_loaded,
        "pages_with_visible_speed_data": visible_pages,
        "layout_a_pages": layout_a_pages,
        "layout_b_pages": layout_b_pages,
        "layout_a_summary_speed_pages": layout_a_pages,
        "layout_b_split_timing_pages": layout_b_pages,
        "raw_rows_extracted": len(raw_rows),
        "normalised_rows_output": len(normalised_rows),
        "split_metric_rows_output": len(split_rows),
        "unique_horses": unique_horses,
        "unique_races": unique_races,
        "graphql_endpoint_called_by_script": "FALSE",
        "api_key_extracted": "FALSE",
        "private_endpoint_used": "FALSE",
        "final_status": status,
    }

    write_csv(RAW_OUT, raw_rows, RAW_COLUMNS)
    write_csv(NORMALISED_OUT, normalised_rows, NORMALISED_COLUMNS)
    write_csv(SPLITS_OUT, split_rows, SPLIT_COLUMNS)
    write_csv(AUDIT_OUT, [audit_row], AUDIT_COLUMNS)
    write_csv(batch_raw_out, raw_rows, RAW_COLUMNS)
    write_csv(batch_normalised_out, normalised_rows, NORMALISED_COLUMNS)
    write_csv(batch_splits_out, split_rows, SPLIT_COLUMNS)
    write_csv(batch_audit_out, [audit_row], AUDIT_COLUMNS)

    print(
        f"[racingcom_rendered_speed_v1] pages_loaded={pages_loaded} visible_pages={visible_pages} "
        f"layout_a={layout_a_pages} layout_b={layout_b_pages}"
    )
    print(
        f"[racingcom_rendered_speed_v1] normalised_rows={len(normalised_rows)} "
        f"split_metric_rows={len(split_rows)} unique_races={unique_races}"
    )
    print(f"[racingcom_rendered_speed_v1] final_status={status}")
    print(f"[racingcom_rendered_speed_v1] wrote {RAW_OUT.relative_to(ROOT)}")
    print(f"[racingcom_rendered_speed_v1] wrote {NORMALISED_OUT.relative_to(ROOT)}")
    print(f"[racingcom_rendered_speed_v1] wrote {SPLITS_OUT.relative_to(ROOT)}")
    print(f"[racingcom_rendered_speed_v1] wrote {AUDIT_OUT.relative_to(ROOT)}")
    print(f"[racingcom_rendered_speed_v1] archived batch {offset} to {BATCH_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
