from __future__ import annotations

import csv
import json
import re
import subprocess
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
TMP = ROOT / "outputs" / "tmp"

OUT_DETAIL = DATA / "racingcom_historical_depth_v1.csv"
OUT_SUMMARY = DATA / "racingcom_historical_depth_v1_summary.csv"

TODAY = date.today()
START_YEAR = 2026
MIN_YEAR = 1990
STOP_AFTER_CONSECUTIVE_EMPTY_YEARS = 2
RACES_PER_MEETING = (1,)
MAX_MEETINGS_PER_TRACK_YEAR = 1

TARGET_TRACKS = [
    "FLEMINGTON",
    "CAULFIELD",
    "MOONEE VALLEY",
    "SANDOWN",
    "BALLARAT",
    "BENDIGO",
    "CRANBOURNE",
    "GEELONG",
    "WARRNAMBOOL",
    "SALE",
]

DETAIL_COLUMNS = [
    "built_at",
    "year",
    "representative_track",
    "meetings_found",
    "first_meeting_found",
    "last_meeting_found",
    "candidate_meetings_considered",
    "candidate_races_considered",
    "sample_meeting_date",
    "sample_meet_status",
    "sample_meeting_url",
    "sample_race_no",
    "sample_race_url",
    "sample_speed_data_url",
    "results_available",
    "sectionals_available",
    "rail_position_available",
    "track_condition_available",
    "barrier_available",
    "sp_available",
    "distance_available",
    "full_bias_available",
    "results_page_loaded",
    "speed_page_loaded",
    "sample_status",
    "notes",
]

SUMMARY_COLUMNS = [
    "built_at",
    "row_type",
    "year",
    "representative_track",
    "tracks_probed",
    "tracks_with_meetings",
    "tracks_with_results",
    "tracks_with_sectionals",
    "tracks_with_rail",
    "tracks_with_track_condition",
    "tracks_with_barrier",
    "tracks_with_sp",
    "tracks_with_full_bias",
    "earliest_results_year",
    "earliest_sectionals_year",
    "earliest_rail_year",
    "earliest_track_condition_year",
    "earliest_barrier_year",
    "earliest_sp_year",
    "earliest_full_bias_year",
    "recommended_harvest_start_date",
    "notes",
]

NODE_HELPER = r"""
const fs = require("fs");

const inputPath = process.argv[2];
const outputPath = process.argv[3];
const rows = JSON.parse(fs.readFileSync(inputPath, "utf8"));
const payload = { results: [], runtime_error: "" };

function writeProgress() {
  fs.writeFileSync(outputPath, JSON.stringify(payload, null, 2));
}

function clean(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function numOnly(value) {
  const match = clean(value).match(/\d+/);
  return match ? String(parseInt(match[0], 10)) : "";
}

function priceLike(value) {
  return /^\$?\d+(?:\.\d{1,2})?$/.test(clean(value));
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

function analyseRacePage(bodyText, html) {
  const distanceMatch = bodyText.match(/\b(\d{3,4}m)\b/i);
  const conditionMatch = bodyText.match(/\b(Good\s*\d|Soft\s*\d|Heavy\s*\d|Synthetic|Firm\s*\d)\b/i);
  const resultsRowMatches = bodyText.match(/\b\d+(?:st|nd|rd|th)\s+\d+\.\s+[A-Z]/g) || [];
  const resultsAvailable = (
    (/\bFinal Result\b/i.test(bodyText) || /\bResults\b/i.test(bodyText)) &&
    /\bPOS\b/i.test(bodyText) &&
    /\bHORSE\b/i.test(bodyText) &&
    resultsRowMatches.length > 0
  );
  const barrierMatches = bodyText.match(/\(\d+\)/g) || [];
  const spMatches = bodyText.match(/\$\d+(?:\.\d+)?/g) || [];
  const resultHeaderBits = [];
  if (/\bPOS\b/i.test(bodyText)) resultHeaderBits.push("POS");
  if (/\bHORSE\b/i.test(bodyText)) resultHeaderBits.push("HORSE");
  if (/\bSP\b/i.test(bodyText)) resultHeaderBits.push("SP");
  if (/\bS-TAB\b/i.test(bodyText)) resultHeaderBits.push("S-TAB");

  return {
    resultsAvailable,
    resultsRowCount: resultsRowMatches.length,
    barrierAvailable: barrierMatches.length > 0,
    barrierCount: barrierMatches.length,
    spAvailable: /\bSP\b/i.test(bodyText) && spMatches.length > 0,
    spValueCount: spMatches.length,
    distanceAvailable: Boolean(distanceMatch),
    distanceText: distanceMatch ? clean(distanceMatch[1]) : "",
    trackConditionAvailable: Boolean(conditionMatch),
    trackConditionText: conditionMatch ? clean(conditionMatch[1]) : "",
    railPositionAvailable: /\bTrack Rail\b/i.test(bodyText),
    resultHeader: resultHeaderBits.join(" / "),
    htmlHasTable: /<table/i.test(html),
  };
}

function analyseSpeedPage(bodyText, html) {
  const last600Available = (
    /\bLast 600m\b/i.test(bodyText) &&
    !/\bLast 600m\s+Not available\b/i.test(bodyText)
  );
  const speedMetricTableVisible = (
    /DIST\s*RUN/i.test(bodyText) &&
    /\bEARLY\b/i.test(bodyText) &&
    /\bMID\b/i.test(bodyText) &&
    /\bLATE\b/i.test(bodyText) &&
    /\bPEAK\b/i.test(bodyText) &&
    /AVG\s*SPEED/i.test(bodyText)
  );
  const splitTimingVisible = (
    /\bOVERALL\b/i.test(bodyText) &&
    (/\b200M\b/i.test(bodyText) || /\b400M\b/i.test(bodyText) || /\b600M\b/i.test(bodyText) || /\d+M-FINISH/i.test(bodyText))
  );
  const runnerMatches = bodyText.match(/\b\d+(?:st|nd|rd|th)\s+\d+\.\s+[A-Z]/g) || [];
  const speedRowMatches = bodyText.match(/\d+(?:\.\d+)?\s*km\/h/gi) || [];
  const splitValueMatches = bodyText.match(/\b\d{2,3}\.\d{1,2}\b/g) || [];
  return {
    speedDataLabelVisible: /\bSpeed Data\b/i.test(bodyText),
    speedMetricTableVisible,
    splitTimingVisible,
    visibleRunnerCount: runnerMatches.length,
    summaryRows: speedRowMatches.length,
    splitRows: splitValueMatches.length,
    sectionalsAvailable: (
      (speedMetricTableVisible && speedRowMatches.length > 0) ||
      (splitTimingVisible && splitValueMatches.length > 10) ||
      last600Available
    ),
    bestHeader: clean([
      speedMetricTableVisible ? "SUMMARY_SPEED_HEADER" : "",
      splitTimingVisible ? "SPLIT_TIMING_HEADER" : "",
      last600Available ? "LAST_600M" : "",
      /Full Replay/i.test(bodyText) ? "FULL_REPLAY" : "",
      /Speed Data/i.test(bodyText) ? "SPEED_DATA" : "",
      /<table/i.test(html) ? "HTML_TABLE" : "",
    ].filter(Boolean).join(" | ")),
  };
}

async function settlePage(page) {
  try {
    await page.waitForLoadState("networkidle", { timeout: 8000 });
  } catch (_err) {}
  await page.waitForTimeout(1000);
  for (let i = 0; i < 2; i += 1) {
    await page.mouse.wheel(0, 900);
    await page.waitForTimeout(120);
  }
  await page.waitForTimeout(200);
}

async function main() {
  let playwright;
  try {
    playwright = require("playwright");
  } catch (err) {
    payload.runtime_error = `playwright_require_failed:${err.message || String(err)}`;
    writeProgress();
    return;
  }

  const browser = await playwright.chromium.launch({
    headless: true,
    args: ["--disable-dev-shm-usage", "--no-sandbox"],
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    userAgent: "EDGEiQ-Racing/1.0 historical-depth-investigation",
  });

  const concurrency = Math.max(1, Math.min(4, rows.length || 1));
  let cursor = 0;

  async function worker() {
    const page = await context.newPage();
    try {
      while (true) {
        const idx = cursor++;
        if (idx >= rows.length) break;
        const row = rows[idx];

        const out = {
          year: row.year || "",
          representative_track: row.representative_track || "",
          meeting_date: row.meeting_date || "",
          meeting_url: row.meeting_url || "",
          race_no: row.race_no || "",
          race_url: row.race_url || "",
          speed_data_url: row.speed_data_url || "",
          meet_status: row.meet_status || "",
          results_page_loaded: "FALSE",
          speed_page_loaded: "FALSE",
          results_available: "FALSE",
          sectionals_available: "FALSE",
          rail_position_available: "FALSE",
          track_condition_available: "FALSE",
          barrier_available: "FALSE",
          sp_available: "FALSE",
          distance_available: "FALSE",
          full_bias_available: "FALSE",
          results_row_count: "0",
          speed_runner_count: "0",
          speed_summary_rows: "0",
          speed_split_rows: "0",
          race_probe_notes: "",
          speed_probe_notes: "",
          probe_status: "",
        };

        try {
          await page.goto(row.race_url, { waitUntil: "load", timeout: 45000 });
          out.results_page_loaded = "TRUE";
          await settlePage(page);
          const raceBodyText = clean(await page.locator("body").innerText().catch(() => ""));
          const raceHtml = await page.content().catch(() => "");
          const raceState = analyseRacePage(raceBodyText, raceHtml);
          out.results_available = raceState.resultsAvailable ? "TRUE" : "FALSE";
          out.rail_position_available = raceState.railPositionAvailable ? "TRUE" : "FALSE";
          out.track_condition_available = raceState.trackConditionAvailable ? "TRUE" : "FALSE";
          out.barrier_available = raceState.barrierAvailable ? "TRUE" : "FALSE";
          out.sp_available = raceState.spAvailable ? "TRUE" : "FALSE";
          out.distance_available = raceState.distanceAvailable ? "TRUE" : "FALSE";
          out.results_row_count = String(raceState.resultsRowCount || 0);
          out.race_probe_notes = clean([
            raceState.distanceText || "",
            raceState.trackConditionText || "",
            raceState.resultHeader || "",
          ].filter(Boolean).join(" | "));
        } catch (err) {
          out.race_probe_notes = `RACE_PAGE_ERROR: ${err && err.message ? err.message : String(err)}`;
        }

        try {
          await page.goto(row.speed_data_url, { waitUntil: "load", timeout: 45000 });
          out.speed_page_loaded = "TRUE";
          await settlePage(page);
          const speedBodyText = clean(await page.locator("body").innerText().catch(() => ""));
          const speedHtml = await page.content().catch(() => "");
          const speedState = analyseSpeedPage(speedBodyText, speedHtml);
          out.sectionals_available = speedState.sectionalsAvailable ? "TRUE" : "FALSE";
          out.speed_runner_count = String(speedState.visibleRunnerCount || 0);
          out.speed_summary_rows = String(speedState.summaryRows || 0);
          out.speed_split_rows = String(speedState.splitRows || 0);
          out.speed_probe_notes = clean([
            speedState.bestHeader || "",
            speedState.speedDataLabelVisible ? "Speed Data label visible" : "",
          ].filter(Boolean).join(" | "));
        } catch (err) {
          out.speed_probe_notes = `SPEED_PAGE_ERROR: ${err && err.message ? err.message : String(err)}`;
        }

        const fullBias = (
          out.results_available === "TRUE" &&
          out.rail_position_available === "TRUE" &&
          out.track_condition_available === "TRUE" &&
          out.barrier_available === "TRUE" &&
          out.distance_available === "TRUE"
        );
        out.full_bias_available = fullBias ? "TRUE" : "FALSE";

        const score = [
          out.results_available,
          out.sectionals_available,
          out.rail_position_available,
          out.track_condition_available,
          out.barrier_available,
          out.sp_available,
          out.distance_available,
        ].filter(value => value === "TRUE").length;

        if (score >= 7) {
          out.probe_status = "FULL_SIGNAL";
        } else if (score >= 5) {
          out.probe_status = "STRONG_SIGNAL";
        } else if (score >= 3) {
          out.probe_status = "PARTIAL_SIGNAL";
        } else if (out.results_page_loaded === "TRUE" || out.speed_page_loaded === "TRUE") {
          out.probe_status = "WEAK_SIGNAL";
        } else {
          out.probe_status = "PAGE_LOAD_FAILED";
        }

        payload.results.push(out);
        writeProgress();
      }
    } finally {
      await page.close().catch(() => {});
    }
  }

  await Promise.all(Array.from({ length: concurrency }, () => worker()));
  await browser.close().catch(() => {});
  writeProgress();
}

main().catch(err => {
  payload.runtime_error = err && err.message ? err.message : String(err);
  writeProgress();
});
"""


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def bool_text(value: Any) -> str:
    return "TRUE" if str(value).strip().upper() in {"TRUE", "1", "YES"} else "FALSE"


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    tmp.replace(path)


def date_key(value: Any) -> str:
    text = clean(value)
    return text[:10] if len(text) >= 10 else ""


def parse_date(value: Any) -> date | None:
    text = date_key(value)
    if not text or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def normalize_track(value: Any) -> str:
    text = clean(value).upper()
    text = text.replace("-", " ")
    text = re.sub(r"[^A-Z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def representative_track(value: Any) -> str | None:
    track = normalize_track(value)
    if not track:
        return None
    if "FLEMINGTON" in track:
        return "FLEMINGTON"
    if "CAULFIELD" in track and "HEATH" not in track:
        return "CAULFIELD"
    if "MOONEE VALLEY" in track or track == "THE VALLEY":
        return "MOONEE VALLEY"
    if "SANDOWN" in track:
        return "SANDOWN"
    if "BALLARAT" in track:
        return "BALLARAT"
    if "BENDIGO" in track:
        return "BENDIGO"
    if "CRANBOURNE" in track:
        return "CRANBOURNE"
    if "GEELONG" in track:
        return "GEELONG"
    if "WARRNAMBOOL" in track:
        return "WARRNAMBOOL"
    if re.search(r"(^| )SALE($| )", track):
        return "SALE"
    return None


def fetch_month(year: int, month: int) -> tuple[list[dict[str, Any]], str]:
    url = f"https://www.racing.com/services/appv2/GetMeetsByMonth/{year}/{month}"
    req = Request(
        url,
        headers={
            "User-Agent": "EDGEiQ-Racing/1.0 historical-depth-investigation",
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://www.racing.com/calendar",
        },
    )
    try:
        with urlopen(req, timeout=60) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read().decode(charset, errors="replace")
            payload = json.loads(body)
        out: list[dict[str, Any]] = []
        for month_row in payload.get("Months") or []:
            out.extend([row for row in month_row.get("CalendarEntries") or [] if isinstance(row, dict)])
            out.extend([row for row in month_row.get("CalendarEntriesList") or [] if isinstance(row, dict)])
        return out, "FETCHED"
    except HTTPError as exc:
        return [], f"HTTP_{exc.code}"
    except URLError as exc:
        return [], f"URL_ERROR_{clean(exc.reason)}"
    except Exception as exc:
        return [], f"ERROR_{exc.__class__.__name__}"


def choose_meeting_samples(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []
    rows_sorted = sorted(rows, key=lambda row: (row["meeting_date"], row["meeting_url"]))
    chosen = [rows_sorted[-1]]
    if len(rows_sorted) > 1:
        earliest = rows_sorted[0]
        if earliest["meeting_url"] != chosen[0]["meeting_url"]:
            chosen.append(earliest)
    return chosen[:MAX_MEETINGS_PER_TRACK_YEAR]


def build_candidate_attempts(
    grouped_rows: dict[tuple[int, str], list[dict[str, Any]]]
) -> tuple[list[dict[str, str]], dict[tuple[int, str], dict[str, Any]]]:
    attempts: list[dict[str, str]] = []
    base_meta: dict[tuple[int, str], dict[str, Any]] = {}

    for year in range(START_YEAR, MIN_YEAR - 1, -1):
        for track in TARGET_TRACKS:
            key = (year, track)
            matches = grouped_rows.get(key, [])
            if matches:
                meetings = sorted({row["meeting_date"] for row in matches})
                sample_meetings = choose_meeting_samples(matches)
                candidate_races = len(sample_meetings) * len(RACES_PER_MEETING)
                base_meta[key] = {
                    "year": str(year),
                    "representative_track": track,
                    "meetings_found": len(meetings),
                    "first_meeting_found": meetings[0],
                    "last_meeting_found": meetings[-1],
                    "candidate_meetings_considered": len(sample_meetings),
                    "candidate_races_considered": candidate_races,
                }
                for meeting in sample_meetings:
                    for race_no in RACES_PER_MEETING:
                        attempts.append({
                            "year": str(year),
                            "representative_track": track,
                            "meeting_date": meeting["meeting_date"],
                            "meeting_url": meeting["meeting_url"],
                            "meet_status": meeting["meet_status"],
                            "race_no": str(race_no),
                            "race_url": f"{meeting['meeting_url']}/race/{race_no}",
                            "speed_data_url": f"{meeting['meeting_url']}/race/{race_no}/speed-data",
                        })
            else:
                base_meta[key] = {
                    "year": str(year),
                    "representative_track": track,
                    "meetings_found": 0,
                    "first_meeting_found": "",
                    "last_meeting_found": "",
                    "candidate_meetings_considered": 0,
                    "candidate_races_considered": 0,
                }

    return attempts, base_meta


def run_node_probe(attempts: list[dict[str, str]]) -> dict[str, Any]:
    TMP.mkdir(parents=True, exist_ok=True)
    helper_path = TMP / "racingcom_historical_depth_v1_helper.cjs"
    input_path = TMP / "racingcom_historical_depth_v1_input.json"
    output_path = TMP / "racingcom_historical_depth_v1_output.json"

    helper_path.write_text(NODE_HELPER, encoding="utf-8")
    input_path.write_text(json.dumps(attempts, ensure_ascii=False), encoding="utf-8")
    output_path.write_text(json.dumps({"results": [], "runtime_error": ""}), encoding="utf-8")

    proc = subprocess.run(
        ["node", str(helper_path), str(input_path), str(output_path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=max(900, len(attempts) * 45),
        check=False,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    if proc.returncode != 0 and not payload.get("runtime_error"):
        payload["runtime_error"] = proc.stderr or proc.stdout or f"node_exit_{proc.returncode}"
    return payload


def score_probe(row: dict[str, str]) -> tuple[int, int, str]:
    booleans = [
        row.get("results_available") == "TRUE",
        row.get("sectionals_available") == "TRUE",
        row.get("rail_position_available") == "TRUE",
        row.get("track_condition_available") == "TRUE",
        row.get("barrier_available") == "TRUE",
        row.get("sp_available") == "TRUE",
        row.get("distance_available") == "TRUE",
    ]
    loaded = [
        row.get("results_page_loaded") == "TRUE",
        row.get("speed_page_loaded") == "TRUE",
    ]
    return sum(1 for item in booleans if item), sum(1 for item in loaded if item), row.get("meeting_date", "")


def yes_count(rows: list[dict[str, Any]], column: str) -> int:
    return sum(1 for row in rows if clean(row.get(column)).upper() == "TRUE")


def earliest_year(rows: list[dict[str, Any]], column: str) -> str:
    years = [int(row["year"]) for row in rows if clean(row.get(column)).upper() == "TRUE" and clean(row.get("year")).isdigit()]
    return str(min(years)) if years else ""


def main() -> None:
    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    calendar_rows: list[dict[str, Any]] = []
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    consecutive_empty_years = 0
    years_probed: list[int] = []

    for year in range(START_YEAR, MIN_YEAR - 1, -1):
        years_probed.append(year)
        year_rows: list[dict[str, Any]] = []
        for month in range(1, 13):
            entries, status = fetch_month(year, month)
            if status != "FETCHED":
                continue
            for entry in entries:
                meeting_date = parse_date(entry.get("Date"))
                if meeting_date is None or meeting_date > TODAY:
                    continue
                if clean(entry.get("State")).upper() != "VIC":
                    continue
                if bool_text(entry.get("IsTrial")) == "TRUE":
                    continue
                if bool_text(entry.get("IsJumpout")) == "TRUE":
                    continue
                if bool_text(entry.get("IsAbandoned")) == "TRUE":
                    continue
                if bool_text(entry.get("HasRaceInformation")) != "TRUE":
                    continue
                rep_track = representative_track(entry.get("Venue") or entry.get("Track"))
                if rep_track not in TARGET_TRACKS:
                    continue
                url_segment = clean(entry.get("UrlSegment")).strip("/")
                if not url_segment:
                    continue
                meeting_url = f"https://www.racing.com/form/{url_segment}"
                year_rows.append({
                    "meeting_date": meeting_date.isoformat(),
                    "representative_track": rep_track,
                    "meet_status": clean(entry.get("MeetStatus")),
                    "meeting_url": meeting_url,
                })

        if year_rows:
            consecutive_empty_years = 0
            calendar_rows.extend(year_rows)
            for row in year_rows:
                grouped[(year, row["representative_track"])].append(row)
        else:
            consecutive_empty_years += 1
            if consecutive_empty_years >= STOP_AFTER_CONSECUTIVE_EMPTY_YEARS:
                break

    attempts, base_meta = build_candidate_attempts(grouped)
    print("Racing.com historical depth live investigation")
    print(f"years_probed={len(years_probed)} from {START_YEAR} down to {years_probed[-1] if years_probed else ''}")
    print(f"calendar_rows_kept={len(calendar_rows)}")
    print(f"candidate_race_attempts={len(attempts)}")

    payload = run_node_probe(attempts) if attempts else {"results": [], "runtime_error": ""}
    if payload.get("runtime_error"):
        print(f"runtime_error={payload['runtime_error']}")

    probe_map: dict[tuple[int, str], list[dict[str, str]]] = defaultdict(list)
    for row in payload.get("results", []):
        year_text = clean(row.get("year"))
        track = clean(row.get("representative_track"))
        if year_text.isdigit() and track:
            probe_map[(int(year_text), track)].append(row)

    detail_rows: list[dict[str, Any]] = []
    for year in sorted({key[0] for key in base_meta.keys()}, reverse=True):
        for track in TARGET_TRACKS:
            key = (year, track)
            meta = base_meta.get(key, {
                "year": str(year),
                "representative_track": track,
                "meetings_found": 0,
                "first_meeting_found": "",
                "last_meeting_found": "",
                "candidate_meetings_considered": 0,
                "candidate_races_considered": 0,
            })
            candidates = probe_map.get(key, [])
            best = sorted(candidates, key=score_probe, reverse=True)[0] if candidates else {}

            if meta["meetings_found"] == 0:
                sample_status = "NO_MEETING_FOUND"
                notes = "No completed VIC meeting discovered live for this representative track/year."
            elif not candidates:
                sample_status = "NO_RACE_PROBE_RESULT"
                notes = "Meeting found but no rendered race probe result returned."
            else:
                score_total, loaded_total, _ = score_probe(best)
                if score_total >= 7:
                    sample_status = "FULL_SIGNAL"
                elif score_total >= 5:
                    sample_status = "STRONG_SIGNAL"
                elif score_total >= 3:
                    sample_status = "PARTIAL_SIGNAL"
                elif loaded_total > 0:
                    sample_status = "WEAK_SIGNAL"
                else:
                    sample_status = "PAGE_LOAD_FAILED"
                notes = clean(" | ".join(filter(None, [
                    clean(best.get("probe_status")),
                    clean(best.get("race_probe_notes")),
                    clean(best.get("speed_probe_notes")),
                ])))

            detail_rows.append({
                "built_at": built_at,
                "year": meta["year"],
                "representative_track": meta["representative_track"],
                "meetings_found": meta["meetings_found"],
                "first_meeting_found": meta["first_meeting_found"],
                "last_meeting_found": meta["last_meeting_found"],
                "candidate_meetings_considered": meta["candidate_meetings_considered"],
                "candidate_races_considered": meta["candidate_races_considered"],
                "sample_meeting_date": clean(best.get("meeting_date")),
                "sample_meet_status": clean(best.get("meet_status")),
                "sample_meeting_url": clean(best.get("meeting_url")),
                "sample_race_no": clean(best.get("race_no")),
                "sample_race_url": clean(best.get("race_url")),
                "sample_speed_data_url": clean(best.get("speed_data_url")),
                "results_available": clean(best.get("results_available")) or "FALSE",
                "sectionals_available": clean(best.get("sectionals_available")) or "FALSE",
                "rail_position_available": clean(best.get("rail_position_available")) or "FALSE",
                "track_condition_available": clean(best.get("track_condition_available")) or "FALSE",
                "barrier_available": clean(best.get("barrier_available")) or "FALSE",
                "sp_available": clean(best.get("sp_available")) or "FALSE",
                "distance_available": clean(best.get("distance_available")) or "FALSE",
                "full_bias_available": clean(best.get("full_bias_available")) or "FALSE",
                "results_page_loaded": clean(best.get("results_page_loaded")) or "FALSE",
                "speed_page_loaded": clean(best.get("speed_page_loaded")) or "FALSE",
                "sample_status": sample_status,
                "notes": notes,
            })

    year_rows: list[dict[str, Any]] = []
    grouped_by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in detail_rows:
        if clean(row.get("year")).isdigit():
            grouped_by_year[int(row["year"])].append(row)

    for year in sorted(grouped_by_year.keys(), reverse=True):
        rows = grouped_by_year[year]
        year_rows.append({
            "built_at": built_at,
            "row_type": "YEAR",
            "year": str(year),
            "representative_track": "",
            "tracks_probed": len(rows),
            "tracks_with_meetings": sum(1 for row in rows if int(row["meetings_found"]) > 0),
            "tracks_with_results": yes_count(rows, "results_available"),
            "tracks_with_sectionals": yes_count(rows, "sectionals_available"),
            "tracks_with_rail": yes_count(rows, "rail_position_available"),
            "tracks_with_track_condition": yes_count(rows, "track_condition_available"),
            "tracks_with_barrier": yes_count(rows, "barrier_available"),
            "tracks_with_sp": yes_count(rows, "sp_available"),
            "tracks_with_full_bias": yes_count(rows, "full_bias_available"),
            "earliest_results_year": "",
            "earliest_sectionals_year": "",
            "earliest_rail_year": "",
            "earliest_track_condition_year": "",
            "earliest_barrier_year": "",
            "earliest_sp_year": "",
            "earliest_full_bias_year": "",
            "recommended_harvest_start_date": "",
            "notes": "Year-level live Racing.com coverage across representative Victorian tracks.",
        })

    global_row = {
        "built_at": built_at,
        "row_type": "GLOBAL",
        "year": "",
        "representative_track": "",
        "tracks_probed": len(detail_rows),
        "tracks_with_meetings": sum(1 for row in detail_rows if int(row["meetings_found"]) > 0),
        "tracks_with_results": yes_count(detail_rows, "results_available"),
        "tracks_with_sectionals": yes_count(detail_rows, "sectionals_available"),
        "tracks_with_rail": yes_count(detail_rows, "rail_position_available"),
        "tracks_with_track_condition": yes_count(detail_rows, "track_condition_available"),
        "tracks_with_barrier": yes_count(detail_rows, "barrier_available"),
        "tracks_with_sp": yes_count(detail_rows, "sp_available"),
        "tracks_with_full_bias": yes_count(detail_rows, "full_bias_available"),
        "earliest_results_year": earliest_year(detail_rows, "results_available"),
        "earliest_sectionals_year": earliest_year(detail_rows, "sectionals_available"),
        "earliest_rail_year": earliest_year(detail_rows, "rail_position_available"),
        "earliest_track_condition_year": earliest_year(detail_rows, "track_condition_available"),
        "earliest_barrier_year": earliest_year(detail_rows, "barrier_available"),
        "earliest_sp_year": earliest_year(detail_rows, "sp_available"),
        "earliest_full_bias_year": earliest_year(detail_rows, "full_bias_available"),
        "recommended_harvest_start_date": "",
        "notes": "",
    }
    if global_row["earliest_full_bias_year"]:
        global_row["recommended_harvest_start_date"] = f"{global_row['earliest_full_bias_year']}-01-01"
        global_row["notes"] = "Recommended harvest start uses earliest year where results, distance, condition, rail, and barrier were all visible together."
    elif global_row["earliest_results_year"]:
        global_row["recommended_harvest_start_date"] = f"{global_row['earliest_results_year']}-01-01"
        global_row["notes"] = "Full bias stack was not confirmed on the sampled live pages; fallback recommendation uses earliest visible results year."
    else:
        global_row["notes"] = "No historical Racing.com meeting coverage was confirmed from live probing."

    summary_rows = [global_row] + year_rows

    write_csv(OUT_DETAIL, detail_rows, DETAIL_COLUMNS)
    write_csv(OUT_SUMMARY, summary_rows, SUMMARY_COLUMNS)

    print(f"saved_detail={OUT_DETAIL}")
    print(f"saved_summary={OUT_SUMMARY}")
    print(f"earliest_results_year={global_row['earliest_results_year'] or 'NONE'}")
    print(f"earliest_sectionals_year={global_row['earliest_sectionals_year'] or 'NONE'}")
    print(f"earliest_rail_year={global_row['earliest_rail_year'] or 'NONE'}")
    print(f"earliest_sp_year={global_row['earliest_sp_year'] or 'NONE'}")
    print(f"earliest_full_bias_year={global_row['earliest_full_bias_year'] or 'NONE'}")
    print(f"recommended_harvest_start_date={global_row['recommended_harvest_start_date'] or 'NONE'}")


if __name__ == "__main__":
    main()
