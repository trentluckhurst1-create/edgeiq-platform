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

NORMALISED = DATA / "racingcom_rendered_speed_data_normalised_v1.csv"
OUT = DATA / "racingcom_rendered_speed_data_non_harvested_pages_v1.csv"
SUMMARY = DATA / "racingcom_rendered_speed_data_non_harvested_pages_v1_summary.csv"

SOURCE_FILES = [
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

OUT_COLUMNS = [
    "attempted_rank",
    "meeting_date",
    "track",
    "race_no",
    "source_url",
    "page_loaded",
    "speed_data_tab_visible",
    "runner_count_visible",
    "visible_runner_count",
    "table_visible",
    "speed_metric_table_visible",
    "extracted_rows",
    "failure_classification",
    "failure_reason",
]

SUMMARY_COLUMNS = [
    "attempted_pages",
    "harvested_pages",
    "non_harvested_pages",
    "pages_loaded",
    "speed_data_tab_visible",
    "runner_count_visible",
    "table_visible",
    "speed_metric_table_visible",
    "total_extracted_rows",
    "no_speed_data_present",
    "table_layout_variant",
    "extraction_failure",
    "page_error",
    "other",
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

function auditRenderedPage() {
  function cleanInPage(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }
  function rowCells(row) {
    return Array.from(row.querySelectorAll("th,td")).map((cell) => cleanInPage(cell.innerText || cell.textContent || ""));
  }
  const bodyText = cleanInPage(document.body ? document.body.innerText : "");
  const speedDataTabVisible = /\bSpeed Data\b/i.test(bodyText);
  const runnerTextMatches = bodyText.match(/\b\d+(?:st|nd|rd|th)\s+\d+\.\s+[A-Z][A-Za-z' .-]+/g) || [];
  let tableVisible = false;
  let speedMetricTableVisible = false;
  let extractedRows = 0;
  let visibleRunnerCount = 0;
  let bestHeader = "";

  const containers = Array.from(document.querySelectorAll("div.table-container"));
  for (const container of containers) {
    const tables = Array.from(container.querySelectorAll("table"));
    if (tables.length) tableVisible = true;
    if (tables.length < 2) continue;
    const leftRows = Array.from(tables[0].querySelectorAll("tr")).map(rowCells);
    const dataRows = Array.from(tables[1].querySelectorAll("tr")).map(rowCells);
    if (!leftRows.length || !dataRows.length) continue;
    const leftHeader = cleanInPage((leftRows[0] || []).join(" "));
    const metricHeader = cleanInPage((dataRows[0] || []).join(" "));
    if (/POS\s*\/\s*HORSE/i.test(leftHeader)) {
      visibleRunnerCount = Math.max(visibleRunnerCount, leftRows.slice(1).filter((row) => /\d+(?:st|nd|rd|th)/i.test(row.join(" ")) && /\d+\./.test(row.join(" "))).length);
      bestHeader = cleanInPage([leftHeader, metricHeader].join(" | "));
    }
    const hasMetrics = /DIST\s*RUN/i.test(metricHeader)
      && /\bEARLY\b/i.test(metricHeader)
      && /\bMID\b/i.test(metricHeader)
      && /\bLATE\b/i.test(metricHeader)
      && /\bPEAK\b/i.test(metricHeader)
      && /AVG\s*SPEED/i.test(metricHeader);
    if (!/POS\s*\/\s*HORSE/i.test(leftHeader) || !hasMetrics) continue;
    speedMetricTableVisible = true;
    const count = Math.min(leftRows.length - 1, dataRows.length - 1);
    for (let index = 0; index < count; index += 1) {
      const leftText = cleanInPage((leftRows[index + 1] || []).join(" "));
      const metricsText = cleanInPage((dataRows[index + 1] || []).join(" "));
      if (/\d+(?:st|nd|rd|th)/i.test(leftText) && /\d+\./.test(leftText) && /\d+(?:\.\d+)?\s*km\/h/i.test(metricsText)) {
        extractedRows += 1;
      }
    }
  }

  if (!visibleRunnerCount && runnerTextMatches.length) {
    visibleRunnerCount = runnerTextMatches.length;
  }
  return {
    speedDataTabVisible,
    runnerCountVisible: visibleRunnerCount > 0,
    visibleRunnerCount,
    tableVisible,
    speedMetricTableVisible,
    extractedRows,
    bestHeader,
    bodyExcerpt: bodyText.slice(0, 700),
  };
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
      userAgent: "EDGEiQ-Racing/1.0 rendered-speed-data-non-harvested-audit (public page only)",
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
      userAgent: "EDGEiQ-Racing/1.0 rendered-speed-data-non-harvested-audit (public page only)",
    });
    return { browser, context, closeBrowser: false };
  } catch (err) {
    errors.push(`cdp:${err && err.message ? err.message : String(err)}`);
  }
  throw new Error(errors.join(" | "));
}

async function settleAndScroll(page) {
  try {
    await page.waitForLoadState("networkidle", { timeout: 20000 });
  } catch (_err) {}
  await page.waitForTimeout(2500);
  for (let i = 0; i < 10; i += 1) {
    await page.mouse.wheel(0, 1800);
    await page.waitForTimeout(280);
  }
  await page.waitForTimeout(800);
}

function classify(result) {
  if (!result.page_loaded) {
    return ["PAGE_ERROR", result.error || "Page did not load."];
  }
  if (result.extracted_rows > 0) {
    return ["EXTRACTION_FAILURE", "Rendered speed rows are now extractable; previous harvest likely missed them due to timing or extractor state."];
  }
  if (!result.speed_data_tab_visible && !result.runner_count_visible && !result.table_visible) {
    return ["NO_SPEED_DATA_PRESENT", "No Speed Data tab text, runner list, or speed table visible in rendered page."];
  }
  if (result.speed_data_tab_visible && !result.runner_count_visible && !result.speed_metric_table_visible) {
    return ["NO_SPEED_DATA_PRESENT", "Speed Data tab/page exists, but no runner speed table is visible."];
  }
  if (result.runner_count_visible && result.table_visible && !result.speed_metric_table_visible) {
    return ["TABLE_LAYOUT_VARIANT", "Runner/table content is visible, but expected DIST RUN / EARLY / MID / LATE / PEAK / AVG SPEED table was not found."];
  }
  return ["OTHER", "Rendered page loaded but did not match known no-data, table-variant, or extraction-failure patterns."];
}

(async () => {
  const payload = { results: [], runtime_error: "" };
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
  const page = await context.newPage();
  for (const row of rows) {
    const base = {
      attempted_rank: row.attempted_rank || "",
      meeting_date: row.meeting_date || "",
      track: row.track || "",
      race_no: row.race_no || "",
      source_url: row.source_url || "",
      page_loaded: "FALSE",
      speed_data_tab_visible: "FALSE",
      runner_count_visible: "FALSE",
      visible_runner_count: 0,
      table_visible: "FALSE",
      speed_metric_table_visible: "FALSE",
      extracted_rows: 0,
      failure_classification: "PAGE_ERROR",
      failure_reason: "",
    };
    if (!PUBLIC_SPEED_RE.test(row.source_url || "")) {
      payload.results.push({ ...base, failure_classification: "PAGE_ERROR", failure_reason: "Rejected non-public Racing.com speed-data URL." });
      writeProgress();
      continue;
    }
    try {
      await page.goto(row.source_url, { waitUntil: "domcontentloaded", timeout: 90000 });
      await settleAndScroll(page);
      const aggregate = {
        page_loaded: true,
        speed_data_tab_visible: false,
        runner_count_visible: false,
        visible_runner_count: 0,
        table_visible: false,
        speed_metric_table_visible: false,
        extracted_rows: 0,
        error: "",
      };
      for (const frame of page.frames()) {
        try {
          const state = await frame.evaluate(auditRenderedPage);
          aggregate.speed_data_tab_visible = aggregate.speed_data_tab_visible || state.speedDataTabVisible;
          aggregate.runner_count_visible = aggregate.runner_count_visible || state.runnerCountVisible;
          aggregate.visible_runner_count = Math.max(aggregate.visible_runner_count, Number(state.visibleRunnerCount || 0));
          aggregate.table_visible = aggregate.table_visible || state.tableVisible;
          aggregate.speed_metric_table_visible = aggregate.speed_metric_table_visible || state.speedMetricTableVisible;
          aggregate.extracted_rows += Number(state.extractedRows || 0);
        } catch (_err) {}
      }
      const [classification, reason] = classify(aggregate);
      payload.results.push({
        ...base,
        page_loaded: "TRUE",
        speed_data_tab_visible: aggregate.speed_data_tab_visible ? "TRUE" : "FALSE",
        runner_count_visible: aggregate.runner_count_visible ? "TRUE" : "FALSE",
        visible_runner_count: aggregate.visible_runner_count,
        table_visible: aggregate.table_visible ? "TRUE" : "FALSE",
        speed_metric_table_visible: aggregate.speed_metric_table_visible ? "TRUE" : "FALSE",
        extracted_rows: aggregate.extracted_rows,
        failure_classification: classification,
        failure_reason: reason,
      });
      writeProgress();
    } catch (err) {
      const [classification, reason] = classify({ page_loaded: false, error: err && err.message ? err.message : String(err) });
      payload.results.push({ ...base, failure_classification: classification, failure_reason: reason });
      writeProgress();
    }
  }
  await page.close().catch(() => {});
  if (closeBrowser) await browser.close().catch(() => {});
  writeProgress();
})();
"""


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"NAN", "NONE", "NULL", "N/A", "NA", "-"} else re.sub(r"\s+", " ", text)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except UnicodeDecodeError:
        with path.open("r", encoding="latin-1", newline="") as handle:
            return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    tmp.replace(path)


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


def load_candidates() -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()
    for path in SOURCE_FILES:
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
            seen.add(url)
            candidates.append({"meeting_date": meeting_date, "track": track, "race_no": rn, "source_url": url})
    candidates.sort(key=lambda item: (0 if item["source_url"].lower() == PRIORITY_TEST_URL.lower() else 1, item["source_url"]))
    for index, item in enumerate(candidates, start=1):
        item["attempted_rank"] = str(index)
    return candidates


def harvested_urls() -> set[str]:
    return {clean(row.get("source_url")) for row in read_csv(NORMALISED) if clean(row.get("source_url"))}


def run_browser_audit(rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], str]:
    TMP.mkdir(parents=True, exist_ok=True)
    helper = TMP / "audit_racingcom_rendered_speed_data_non_harvested_v1_helper.cjs"
    input_path = TMP / "audit_racingcom_rendered_speed_data_non_harvested_v1_input.json"
    output_path = TMP / "audit_racingcom_rendered_speed_data_non_harvested_v1_output.json"
    helper.write_text(NODE_HELPER, encoding="utf-8")
    input_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def read_partial() -> list[dict[str, Any]]:
        if not output_path.exists():
            return []
        try:
            return list(json.loads(output_path.read_text(encoding="utf-8")).get("results") or [])
        except Exception:
            return []

    try:
        completed = subprocess.run(
            ["node", str(helper), str(input_path), str(output_path)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=max(300, len(rows) * 45),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return read_partial(), f"node_timeout_after_{exc.timeout}_seconds"
    except Exception as exc:  # noqa: BLE001
        return read_partial(), f"node_failed:{exc.__class__.__name__}:{exc}"

    if completed.returncode != 0:
        message = clean(completed.stderr) or clean(completed.stdout) or f"return_code_{completed.returncode}"
        return read_partial(), f"node_returned_error:{message[:500]}"
    if not output_path.exists():
        return [], "node_no_output"
    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [], f"node_output_parse_failed:{exc.__class__.__name__}:{exc}"
    return list(payload.get("results") or []), clean(payload.get("runtime_error"))


def summary_row(results: list[dict[str, Any]], attempted_pages: int, harvested_pages: int) -> dict[str, Any]:
    counts = {
        "no_speed_data_present": sum(1 for row in results if clean(row.get("failure_classification")) == "NO_SPEED_DATA_PRESENT"),
        "table_layout_variant": sum(1 for row in results if clean(row.get("failure_classification")) == "TABLE_LAYOUT_VARIANT"),
        "extraction_failure": sum(1 for row in results if clean(row.get("failure_classification")) == "EXTRACTION_FAILURE"),
        "page_error": sum(1 for row in results if clean(row.get("failure_classification")) == "PAGE_ERROR"),
        "other": sum(1 for row in results if clean(row.get("failure_classification")) == "OTHER"),
    }
    if not results:
        status = "NO_NON_HARVESTED_PAGES"
    elif counts["extraction_failure"]:
        status = "EXTRACTION_FAILURES_FOUND"
    elif counts["table_layout_variant"]:
        status = "TABLE_LAYOUT_VARIANTS_FOUND"
    elif counts["no_speed_data_present"] == len(results):
        status = "NO_SPEED_DATA_PRESENT_ON_NON_HARVESTED"
    else:
        status = "MIXED_FAILURE_REASONS"
    return {
        "attempted_pages": attempted_pages,
        "harvested_pages": harvested_pages,
        "non_harvested_pages": len(results),
        "pages_loaded": sum(1 for row in results if clean(row.get("page_loaded")) == "TRUE"),
        "speed_data_tab_visible": sum(1 for row in results if clean(row.get("speed_data_tab_visible")) == "TRUE"),
        "runner_count_visible": sum(1 for row in results if clean(row.get("runner_count_visible")) == "TRUE"),
        "table_visible": sum(1 for row in results if clean(row.get("table_visible")) == "TRUE"),
        "speed_metric_table_visible": sum(1 for row in results if clean(row.get("speed_metric_table_visible")) == "TRUE"),
        "total_extracted_rows": sum(int(row.get("extracted_rows") or 0) for row in results),
        **counts,
        "graphql_endpoint_called_by_script": "FALSE",
        "api_key_extracted": "FALSE",
        "private_endpoint_used": "FALSE",
        "final_status": status,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Racing.com rendered Speed Data pages that did not harvest.")
    parser.add_argument("--max-races", type=int, default=25)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    candidates = load_candidates()[: max(0, args.max_races)]
    harvested = harvested_urls()
    non_harvested = [row for row in candidates if row["source_url"] not in harvested]
    print(f"[racingcom_non_harvested_v1] attempted_pages={len(candidates)} harvested_pages={len(candidates) - len(non_harvested)} non_harvested={len(non_harvested)}")

    results, runtime_error = run_browser_audit(non_harvested)
    if runtime_error:
        print(f"[racingcom_non_harvested_v1] browser warning: {runtime_error}")
    returned = {clean(row.get("source_url")) for row in results}
    for row in non_harvested:
        if row["source_url"] in returned:
            continue
        results.append(
            {
                "attempted_rank": row["attempted_rank"],
                "meeting_date": row["meeting_date"],
                "track": row["track"],
                "race_no": row["race_no"],
                "source_url": row["source_url"],
                "page_loaded": "FALSE",
                "speed_data_tab_visible": "FALSE",
                "runner_count_visible": "FALSE",
                "visible_runner_count": 0,
                "table_visible": "FALSE",
                "speed_metric_table_visible": "FALSE",
                "extracted_rows": 0,
                "failure_classification": "PAGE_ERROR",
                "failure_reason": runtime_error or "Browser runner did not return this page.",
            }
        )

    results.sort(key=lambda row: int(clean(row.get("attempted_rank")) or 0))
    summary = summary_row(results, len(candidates), len(candidates) - len(non_harvested))
    write_csv(OUT, results, OUT_COLUMNS)
    write_csv(SUMMARY, [summary], SUMMARY_COLUMNS)

    print(
        "[racingcom_non_harvested_v1] "
        f"loaded={summary['pages_loaded']} speed_tab={summary['speed_data_tab_visible']} "
        f"runner_count={summary['runner_count_visible']} table={summary['table_visible']} "
        f"metric_table={summary['speed_metric_table_visible']} extracted_rows={summary['total_extracted_rows']}"
    )
    print(
        "[racingcom_non_harvested_v1] "
        f"NO_SPEED_DATA_PRESENT={summary['no_speed_data_present']} "
        f"TABLE_LAYOUT_VARIANT={summary['table_layout_variant']} "
        f"EXTRACTION_FAILURE={summary['extraction_failure']} "
        f"PAGE_ERROR={summary['page_error']} OTHER={summary['other']}"
    )
    print(f"[racingcom_non_harvested_v1] final_status={summary['final_status']}")
    print(f"[racingcom_non_harvested_v1] wrote {OUT.relative_to(ROOT)}")
    print(f"[racingcom_non_harvested_v1] wrote {SUMMARY.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
