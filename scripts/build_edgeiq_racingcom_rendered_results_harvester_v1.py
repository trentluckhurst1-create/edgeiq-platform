from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "public" / "data" / "edgeiq_racingcom_historical_calendar_backfill_v1.csv"
OUT = ROOT / "public" / "data" / "edgeiq_racingcom_results_warehouse_v1.csv"
BATCH_DIR = ROOT / "public" / "data" / "edgeiq_racingcom_results_batches_v1"
TMP = ROOT / "outputs" / "tmp"
HELPER = TMP / "build_edgeiq_racingcom_rendered_results_harvester_v1_helper.cjs"
HELPER_INPUT = TMP / "build_edgeiq_racingcom_rendered_results_harvester_v1_input.json"
HELPER_OUTPUT = TMP / "build_edgeiq_racingcom_rendered_results_harvester_v1_output.json"


COLUMNS = [
    "meeting_date", "track", "race_no", "race_key", "source_url",
    "page_loaded", "visible_results",
    "raceName", "distance", "raceClass", "trackCondition", "raceTime", "prizeMoney",
    "finishPosition", "horseNo", "horseName", "horseKey", "barrier",
    "trainer", "jockey", "weight", "prizemoneyEarned", "inRun",
    "margin", "bb", "sp", "stab", "rawText", "status", "error",
]


PLAYWRIGHT_SCRIPT = r"""
const fs = require("fs");

const inputPath = process.argv[2];
const outputPath = process.argv[3];
const rows = JSON.parse(fs.readFileSync(inputPath, "utf8"));

function clean(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function horseKey(value) {
  return clean(value).toUpperCase().replace(/\([^)]*\)/g, "").replace(/[^A-Z0-9]+/g, "");
}

function extractResults(row) {
  function clean(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  function horseKey(value) {
    return clean(value).toUpperCase().replace(/\([^)]*\)/g, "").replace(/[^A-Z0-9]+/g, "");
  }

  const PUBLIC_RACE_RE = /^https:\/\/www\.racing\.com\/form\/\d{4}-\d{2}-\d{2}\/[^/]+\/race\/\d+(?:[?#].*)?$/i;
  if (!PUBLIC_RACE_RE.test(row.source_url || "")) {
    return {
      pageLoaded: false,
      visibleResults: false,
      rows: [],
      status: "SAFETY_BLOCKED",
      error: "Rejected non-public Racing.com race URL.",
    };
  }

  const root = document.querySelector("#id-full-form-v2-root") || document.body;
  const text = clean(root ? root.innerText : "");

  function find(pattern) {
    const m = text.match(pattern);
    return m ? clean(m[1]) : "";
  }

  const meta = {
    raceName: find(/All\s+(?:\d+\s+)+(.+?)\s+\d{1,2}:\d{2}(?:am|pm)\s+\d{3,4}m/i),
    distance: find(/\b(\d{3,4}m)\b/i),
    raceClass: find(/\b(BenchMark\s*\d+|BM\s*\d+|Handicap|Maiden|MDN|Open|Listed|Group\s*\d|Class\s*\d)\b/i),
    trackCondition: find(/\b(Good\s*\d|Soft\s*\d|Heavy\s*\d|Synthetic|Firm\s*\d)\b/i),
    raceTime: find(/\bRace Time:\s*([0-9:.]+)/i),
    prizeMoney: find(/\bPrize Money:\s*\$?([0-9,]+)/i),
  };

  const markerRe = /\b(1st|2nd|3rd|\d+th|SCR)\s+(\d+)\.\s+/g;
  const markers = [];
  let m;
  while ((m = markerRe.exec(text)) !== null) {
    markers.push({
      index: m.index,
      pos: m[1],
      horseNo: m[2],
    });
  }

  const rows = [];

  for (let i = 0; i < markers.length; i += 1) {
    const start = markers[i].index;
    const end = i + 1 < markers.length ? markers[i + 1].index : text.length;
    const block = clean(text.slice(start, end));

    if (!block || !/\bT:\s*/.test(block) || !/\bJ:\s*/.test(block)) continue;

    const top = block.match(/^(1st|2nd|3rd|\d+th|SCR)\s+(\d+)\.\s+(.+?)\s+\((\d+)\)\s+T:\s*(.+?)\s+J:\s*(.+?)\s+(\d+(?:\.\d+)?kg)\s*(.*)$/i);
    if (!top) continue;

    const finishPosition = top[1].toUpperCase() === "SCR" ? "SCR" : String(parseInt(top[1], 10));
    const horseNo = clean(top[2]);
    const horseName = clean(top[3]);
    const barrier = clean(top[4]);
    const trainer = clean(top[5]);
    const jockey = clean(top[6]);
    const weight = clean(top[7]);
    const tail = clean(top[8]);

    const prize = (tail.match(/\$[0-9,]+/) || [""])[0];
    const inRun = (tail.match(/\b\d+(?:st|nd|rd|th)\/\d+(?:st|nd|rd|th)\b/i) || [""])[0];
    const margin = (tail.match(/\b\d+(?:\.\d+)?L\b/i) || [""])[0];

    let oddsZone = tail;
    if (inRun) oddsZone = oddsZone.slice(oddsZone.indexOf(inRun) + inRun.length);
    if (margin) oddsZone = oddsZone.slice(oddsZone.indexOf(margin) + margin.length);

    const oddsVals = oddsZone.match(/\$\d+(?:\.\d{1,2})?/g) || [];

    const bb = oddsVals[0] || "";
    const sp = oddsVals[1] || "";
    const stab = oddsVals[2] || "";

    rows.push({
      raceName: meta.raceName,
      distance: meta.distance,
      raceClass: meta.raceClass,
      trackCondition: meta.trackCondition,
      raceTime: meta.raceTime,
      prizeMoney: meta.prizeMoney,
      finishPosition,
      horseNo,
      horseName,
      horseKey: horseKey(horseName),
      barrier,
      trainer,
      jockey,
      weight,
      prizemoneyEarned: prize.replace(/,/g, ""),
      inRun,
      margin,
      bb,
      sp,
      stab,
      rawText: block,
    });
  }

  return {
    pageLoaded: true,
    visibleResults: rows.length > 0,
    rows,
    status: rows.length ? "RENDERED_TEXT_RESULTS_EXTRACTED" : "NO_RENDERED_RESULTS_FOUND",
    error: "",
  };
}

function extractDebug() {
  function clean(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  const root = document.querySelector("#id-full-form-v2-root") || document.body;
  const bodyText = clean(root ? root.innerText : "");
  return {
    title: document.title || "",
    url: location.href,
    body_length: bodyText.length,
    body_head: bodyText.slice(0, 8000),
    table_count: document.querySelectorAll("table").length,
    root_found: document.querySelector("#id-full-form-v2-root") ? "TRUE" : "FALSE",
  };
}

async function createBrowser(playwright) {
  const browser = await playwright.chromium.launch({
    headless: true,
    args: ["--disable-dev-shm-usage", "--no-sandbox"],
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 1200 },
    userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 EDGEiQ-Racing/1.0",
  });

  return { browser, context };
}

async function settle(page) {
  try { await page.waitForLoadState("domcontentloaded", { timeout: 30000 }); } catch (_err) {}
  try { await page.waitForLoadState("networkidle", { timeout: 10000 }); } catch (_err) {}
  await page.waitForTimeout(2500);
  for (let i = 0; i < 6; i += 1) {
    await page.mouse.wheel(0, 1800);
    await page.waitForTimeout(350);
  }
  await page.waitForTimeout(1000);
}

(async () => {
  const payload = { pages: [], rows: [], debug: [], runtime_error: "" };

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

  let browser, context;
  try {
    const bundle = await createBrowser(playwright);
    browser = bundle.browser;
    context = bundle.context;
  } catch (err) {
    payload.runtime_error = `browser_launch_failed:${err.message || String(err)}`;
    writeProgress();
    return;
  }

  const concurrency = Math.max(1, Math.min(4, Number(process.env.EDGEIQ_RESULTS_CONCURRENCY || 4), rows.length));
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
          await page.goto(row.source_url, { waitUntil: "domcontentloaded", timeout: 90000 });
          await settle(page);
          result = await page.evaluate(extractResults, row);

          if (!result.visibleResults) {
            const debug = await page.evaluate(extractDebug);
            debug.source_url = row.source_url || "";
            debug.meeting_date = row.meeting_date || "";
            debug.track = row.track || "";
            debug.race_no = row.race_no || "";
            payload.debug.push(debug);
          }
        } catch (err) {
          result = {
            pageLoaded: false,
            visibleResults: false,
            rows: [],
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
          visible_results: result.visibleResults ? "TRUE" : "FALSE",
          runner_rows: result.rows.length,
          status: result.status,
          error: result.error || "",
        });

        for (const item of result.rows) {
          payload.rows.push({
            meeting_date: row.meeting_date || "",
            track: row.track || "",
            race_no: row.race_no || "",
            race_key: `${row.meeting_date || ""}|${row.track || ""}|${row.race_no || ""}`,
            source_url: row.source_url || "",
            page_loaded: result.pageLoaded ? "TRUE" : "FALSE",
            visible_results: result.visibleResults ? "TRUE" : "FALSE",
            ...item,
            status: result.status,
            error: result.error || "",
          });
        }

        writeProgress();
      }
    } finally {
      await page.close().catch(() => {});
    }
  }

  await Promise.all(Array.from({ length: concurrency }, () => worker()));
  await browser.close().catch(() => {});
  writeProgress();
})();
"""


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})
    tmp.replace(path)


def load_candidates(start_date: str, end_date: str) -> list[dict[str, str]]:
    rows = []
    seen = set()

    for row in read_csv(SOURCE):
        meeting_date = clean(row.get("meeting_date"))
        track = clean(row.get("track"))
        race_no = clean(row.get("race_no"))
        race_url = clean(row.get("race_url")) or clean(row.get("speed_data_url")).replace("/speed-data", "")

        if not meeting_date or not track or not race_no or not race_url:
            continue
        if start_date and meeting_date < start_date:
            continue
        if end_date and meeting_date > end_date:
            continue

        key = (meeting_date, track, race_no, race_url)
        if key in seen:
            continue
        seen.add(key)

        rows.append({
            "meeting_date": meeting_date,
            "track": track,
            "race_no": race_no,
            "source_url": race_url,
        })

    rows.sort(key=lambda r: (r["meeting_date"], r["track"], int(re.sub(r"[^0-9]", "", r["race_no"]) or 0)))
    return rows


def run_browser(rows: list[dict[str, str]]) -> dict[str, Any]:
    TMP.mkdir(parents=True, exist_ok=True)
    HELPER.write_text(PLAYWRIGHT_SCRIPT, encoding="utf-8")
    HELPER_INPUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    HELPER_OUTPUT.write_text(json.dumps({"pages": [], "rows": [], "debug": [], "runtime_error": ""}, indent=2), encoding="utf-8")

    proc = subprocess.run(
        ["node", str(HELPER), str(HELPER_INPUT), str(HELPER_OUTPUT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        print("[edgeiq_results_v1] browser warning:", (proc.stderr or proc.stdout).strip())

    try:
        return json.loads(HELPER_OUTPUT.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"pages": [], "rows": [], "debug": [], "runtime_error": f"helper_output_json_failed:{exc}"}


def merge_rows(existing: list[dict[str, Any]], new_rows: list[dict[str, Any]], force: bool) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str, str, str], dict[str, Any]] = {}

    for row in existing:
        key = (
            clean(row.get("meeting_date")),
            clean(row.get("track")),
            clean(row.get("race_no")),
            clean(row.get("horseKey")) or clean(row.get("horseName")),
        )
        if all(key):
            merged[key] = row

    for row in new_rows:
        key = (
            clean(row.get("meeting_date")),
            clean(row.get("track")),
            clean(row.get("race_no")),
            clean(row.get("horseKey")) or clean(row.get("horseName")),
        )
        if not all(key):
            continue
        if force or key not in merged:
            merged[key] = row

    return sorted(
        merged.values(),
        key=lambda r: (
            clean(r.get("meeting_date")),
            clean(r.get("track")),
            int(re.sub(r"[^0-9]", "", clean(r.get("race_no"))) or 0),
            999 if clean(r.get("finishPosition")) == "SCR" else int(re.sub(r"[^0-9]", "", clean(r.get("finishPosition"))) or 999),
            clean(r.get("horseName")),
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", default="")
    parser.add_argument("--end-date", default="")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    candidates = load_candidates(args.start_date, args.end_date)
    selected = candidates[args.offset: args.offset + args.batch_size]

    print(f"[edgeiq_results_v1] candidate_races_available={len(candidates)} batch_size={args.batch_size} offset={args.offset} selected={len(selected)}")
    if selected:
        print(f"[edgeiq_results_v1] first_url={selected[0]['source_url']}")

    payload = run_browser(selected)
    pages = payload.get("pages", [])
    rows = payload.get("rows", [])

    existing = [] if args.force else read_csv(OUT)
    merged = merge_rows(existing, rows, args.force)

    write_csv(OUT, merged, COLUMNS)

    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    batch_out = BATCH_DIR / f"edgeiq_racingcom_results_batch_offset_{args.offset:05d}.csv"
    write_csv(batch_out, rows, COLUMNS)

    pages_loaded = sum(1 for p in pages if clean(p.get("page_loaded")) == "TRUE")
    visible_pages = sum(1 for p in pages if clean(p.get("visible_results")) == "TRUE")
    unique_races = len({clean(r.get("race_key")) for r in rows if clean(r.get("race_key"))})

    print(f"[edgeiq_results_v1] pages_loaded={pages_loaded} visible_pages={visible_pages} rows={len(rows)} unique_races={unique_races}")

    if payload.get("runtime_error"):
        print(f"[edgeiq_results_v1] runtime_error={payload.get('runtime_error')}")

    status = "RESULTS_WAREHOUSE_BUILT" if rows else "NO_RENDERED_RESULTS_FOUND"
    print(f"[edgeiq_results_v1] final_status={status}")
    print(f"[edgeiq_results_v1] wrote {OUT.relative_to(ROOT)}")
    print(f"[edgeiq_results_v1] archived batch {args.offset} to {batch_out.relative_to(ROOT).parent}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


