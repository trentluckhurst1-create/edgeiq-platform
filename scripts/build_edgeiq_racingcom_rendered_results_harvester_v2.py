from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
TMP = ROOT / "outputs" / "tmp"

SOURCE = DATA / "edgeiq_racingcom_historical_calendar_backfill_v1.csv"

OUT = DATA / "edgeiq_racingcom_results_warehouse_v2.csv"
AUDIT = DATA / "edgeiq_racingcom_results_warehouse_v2_audit.csv"
BATCH_DIR = DATA / "edgeiq_racingcom_results_batches_v2"

OUT_COLUMNS = [
    "built_at","meeting_date","track","race_no","race_key","source_url",
    "page_loaded","visible_results",
    "race_name","distance","race_class","track_condition","race_time",
    "finish_position","horse_no","horse_name","horse_key","barrier",
    "trainer","jockey","weight","prizemoney_earned","in_run","margin","sp",
    "status","error"
]

AUDIT_COLUMNS = [
    "built_at","candidate_races_available","batch_size","offset",
    "attempted_pages","pages_loaded","visible_result_pages",
    "runner_rows_output","unique_races","unique_horses",
    "graphql_endpoint_called_by_script","api_key_extracted","private_endpoint_used",
    "final_status"
]

NODE_HELPER = r"""
const fs = require("fs");

const inputPath = process.argv[2];
const outputPath = process.argv[3];

const rows = JSON.parse(fs.readFileSync(inputPath, "utf8"));
const payload = { pages: [], rows: [], runtime_error: "" };

function writeProgress() {
  fs.writeFileSync(outputPath, JSON.stringify(payload, null, 2));
}

function safeText(v) {
  return String(v || "").replace(/\s+/g, " ").trim();
}

function horseKey(v) {
  return safeText(v).toUpperCase().replace(/\([^)]*\)/g, "").replace(/[^A-Z0-9]+/g, "");
}

function numOnly(v) {
  const m = safeText(v).match(/\d+/);
  return m ? String(parseInt(m[0], 10)) : "";
}

function parseHorseCell(text) {
  const raw = safeText(text);
  let horseNo = "";
  let horseName = "";
  let barrier = "";
  let trainer = "";
  let jockey = "";

  const t = raw.match(/\bT:\s*(.*?)(?:\s+\bJ:|$)/);
  if (t) trainer = safeText(t[1]);

  const j = raw.match(/\bJ:\s*(.*?)$/);
  if (j) jockey = safeText(j[1]);

  const top = raw.split(/\bT:/)[0].split(/\bJ:/)[0].trim();

  let m = top.match(/^(\d+)\.?\s+(.+?)\s*\((\d+)\)\s*$/);
  if (m) {
    horseNo = m[1];
    horseName = safeText(m[2]);
    barrier = m[3];
  } else {
    m = top.match(/^(\d+)\.?\s+(.+)$/);
    if (m) {
      horseNo = m[1];
      horseName = safeText(m[2]).replace(/\s*\(\d+\)\s*$/, "");
      const b = top.match(/\((\d+)\)\s*$/);
      barrier = b ? b[1] : "";
    } else {
      horseName = top;
    }
  }

  return { horseNo, horseName, barrier, trainer, jockey };
}

function extractRenderedResults(row) {
  const PUBLIC_RACE_RE = /^https:\/\/www\.racing\.com\/form\/\d{4}-\d{2}-\d{2}\/[^/]+\/race\/\d+(?:[?#].*)?$/i;

  function safeText(v) {
    return String(v || "").replace(/\s+/g, " ").trim();
  }

  function horseKey(v) {
    return safeText(v).toUpperCase().replace(/\([^)]*\)/g, "").replace(/[^A-Z0-9]+/g, "");
  }

  function numOnly(v) {
    const m = safeText(v).match(/\d+/);
    return m ? String(parseInt(m[0], 10)) : "";
  }

  function parseHorseCell(text) {
    const raw = safeText(text);
    let horseNo = "";
    let horseName = "";
    let barrier = "";
    let trainer = "";
    let jockey = "";

    const t = raw.match(/\bT:\s*(.*?)(?:\s+\bJ:|$)/);
    if (t) trainer = safeText(t[1]);

    const j = raw.match(/\bJ:\s*(.*?)$/);
    if (j) jockey = safeText(j[1]);

    const top = raw.split(/\bT:/)[0].split(/\bJ:/)[0].trim();

    let m = top.match(/^(\d+)\.?\s+(.+?)\s*\((\d+)\)\s*$/);
    if (m) {
      horseNo = m[1];
      horseName = safeText(m[2]);
      barrier = m[3];
    } else {
      m = top.match(/^(\d+)\.?\s+(.+)$/);
      if (m) {
        horseNo = m[1];
        horseName = safeText(m[2]).replace(/\s*\(\d+\)\s*$/, "");
        const b = top.match(/\((\d+)\)\s*$/);
        barrier = b ? b[1] : "";
      } else {
        horseName = top;
      }
    }

    return { horseNo, horseName, barrier, trainer, jockey };
  }

  if (!PUBLIC_RACE_RE.test(row.source_url || "")) {
    return {
      pageLoaded: true,
      visibleResults: false,
      rows: [],
      status: "SAFETY_BLOCKED",
      error: "Rejected non-public Racing.com race URL."
    };
  }

  const bodyText = safeText(document.body ? document.body.innerText : "");
  const bodyUpper = bodyText.toUpperCase();

  /*
   * EDGEiQ V38 rendered-race identity gate.
   *
   * Racing.com has been proven capable of accepting a requested race URL
   * while rendering another race from the same meeting. A successful page
   * load and plausible result rows are therefore NOT sufficient evidence
   * that the requested race was actually rendered.
   *
   * Capture the browser's post-navigation URL so Python/Node orchestration
   * can validate the actual rendered race identity before any runner rows
   * are admitted to the warehouse.
   */
  const renderedUrl = safeText(
    (window.location && window.location.href) || ""
  );

  /*
   * Canonical completed-results warehouse safety gate.
   *
   * Racing.com can render provisional placings before the result is
   * officially final. Examples include pages containing:
   *
   *   "Full Race Results Pending"
   *   "Abnd"
   *
   * A page must contain "Final Result" before runner rows may be
   * accepted into the completed-results warehouse.
   */
  const hasFinalResult = bodyUpper.includes("FINAL RESULT");

  const hasPendingResults =
    bodyUpper.includes("FULL RACE RESULTS PENDING");

  const hasAbndStatus =
    /(^|\n)ABND(\n|$)/i.test(bodyText);

  if (
    !hasFinalResult
    || hasPendingResults
    || hasAbndStatus
  ) {
    return {
      pageLoaded: true,
      visibleResults: false,
      rows: [],
      status: hasPendingResults
        ? "RESULTS_PENDING"
        : hasAbndStatus
          ? "RACE_ABANDONED_OR_NON_FINAL"
          : "RESULT_NOT_FINAL",
      error: ""
    };
  }

  const raceName =
    safeText((document.querySelector("h1, h2, h3, .race-title") || {}).innerText || "");

  function find(pattern) {
    const m = bodyText.match(pattern);
    return m ? safeText(m[1]) : "";
  }

  const meta = {
    raceName,
    distance: find(/\b(\d{3,4}m)\b/i),
    raceClass: find(/\b(BM\d+|MAIDEN|MDN|GROUP\s*\d|LISTED|OPEN|HANDICAP|CLASS\s*\d|NO METRO WINS)\b/i),
    trackCondition: find(/\b(Good\s*\d|Soft\s*\d|Heavy\s*\d|Synthetic|Firm\s*\d)\b/i),
    raceTime: find(/\bRace Time:\s*([0-9:.]+)/i)
  };

  const out = [];
  const tables = Array.from(document.querySelectorAll("table"));

  for (const table of tables) {
    const trs = Array.from(table.querySelectorAll("tr"));
    if (trs.length < 2) continue;

    const headerCells = Array.from(trs[0].querySelectorAll("th,td")).map(c => safeText(c.innerText || c.textContent));
    const headerText = headerCells.join(" ").toUpperCase();

    if (!headerText.includes("POS") || !headerText.includes("HORSE")) continue;

    for (const tr of trs.slice(1)) {
      const cells = Array.from(tr.querySelectorAll("td,th")).map(c => safeText(c.innerText || c.textContent));
      if (cells.length < 2) continue;

      const finishPosition = numOnly(cells[0]);
      if (!finishPosition) continue;

      const hp = parseHorseCell(cells[1]);
      if (!hp.horseName) continue;

      const joined = cells.join(" | ");

      out.push({
        ...meta,
        finishPosition,
        horseNo: hp.horseNo,
        horseName: hp.horseName,
        horseKey: horseKey(hp.horseName),
        barrier: hp.barrier,
        trainer: hp.trainer,
        jockey: hp.jockey,
        weight: cells.find(x => /\b\d{2,3}kg\b/i.test(x)) || "",
        prizemoneyEarned: cells.find(x => /^\$[0-9,]+$/.test(x)) || "",
        inRun: cells.find(x => /^\d+(?:st|nd|rd|th)?\/\d+(?:st|nd|rd|th)?$/i.test(x)) || "",
        margin: cells.find(x => /^\d+(?:\.\d+)?L$/i.test(x)) || "",
        sp: cells.slice().reverse().find(x => /^\$?\d+(?:\.\d{1,2})?$/.test(x) && !/kg/i.test(x)) || "",
        rawText: joined
      });
    }
  }


  /*
   * Racing.com currently renders the Results grid with div-based markup,
   * not semantic <table> rows. The complete official result is still
   * present in document.body.innerText, so use that as the fallback when
   * the legacy table parser above produces no runners.
   */
  if (!out.length && bodyText) {

    const lines = String(
      document.body ? document.body.innerText : ""
    )
      .split(/\r?\n/)
      .map(v => safeText(v))
      .filter(Boolean);

    const posIndex = lines.findIndex(
      v => v.toUpperCase() === "POS"
    );

    const horseHeaderIndex = lines.findIndex(
      (v, idx) =>
        idx > posIndex &&
        v.toUpperCase().includes("HORSE") &&
        v.toUpperCase().includes("BARRIER")
    );

    const isFinish = v =>
      /^\d+(?:st|nd|rd|th)$/i.test(v);

    const isScratch = v =>
      /^SCR$/i.test(v);

    const isRunnerStart = v =>
      isFinish(v) || isScratch(v);

    const isWeight = v =>
      /^\d+(?:\.\d+)?kg$/i.test(v);

    const isPrize = v =>
      /^\$[\d,]+(?:\.\d+)?$/.test(v);

    const isInRun = v =>
      /^\d+(?:st|nd|rd|th)\/\d+(?:st|nd|rd|th)$/i.test(v);

    const isMargin = v =>
      /^\d+(?:\.\d+)?L$/i.test(v);

    const isRaceTime = v =>
      /^\d+:\d{2}(?:\.\d+)?$/.test(v);

    const isPrice = v =>
      /^\$\d+(?:\.\d+)?$/.test(v);

      const isDash = v =>
        v === "-" ||
        v === String.fromCharCode(8211) ||
        v === String.fromCharCode(8212);

    const stopText = v => {
      const s = safeText(v).toLowerCase();

      return (
        s.startsWith("personalise your racing experience") ||
        s.startsWith("we use cookies") ||
        s.startsWith("accept all cookies") ||
        s.startsWith("decline non-essential cookies")
      );
    };

    let i = -1;

    if (horseHeaderIndex >= 0) {
      for (
        let x = horseHeaderIndex + 1;
        x < lines.length;
        x++
      ) {
        if (isRunnerStart(lines[x])) {
          i = x;
          break;
        }
      }
    }

    while (i >= 0 && i < lines.length) {

      if (stopText(lines[i])) {
        break;
      }

      if (!isRunnerStart(lines[i])) {
        i++;
        continue;
      }

      const positionToken = lines[i];

      const scratched = isScratch(
        positionToken
      );

      const finishPosition = scratched
        ? ""
        : numOnly(positionToken);

      i++;

      if (i >= lines.length) {
        break;
      }

      const horseLine = lines[i];

      /*
       * Examples:
       *
       * 5. The Victorious (NZ) (3)
       * 1. Charlie Messy Hair (5)
       *
       * Final numeric parentheses = barrier.
       * Country suffix such as (NZ) remains in horse name.
       */
      const horseMatch = horseLine.match(
        /^(\d+)\.?\s+(.+?)\s+\((\d+)\)$/
      );

      if (!horseMatch) {
        i++;
        continue;
      }

      const horseNo = horseMatch[1] || "";
      const horseName = safeText(
        horseMatch[2] || ""
      );
      const barrier = horseMatch[3] || "";

      i++;

      const block = [];

      while (
        i < lines.length &&
        !isRunnerStart(lines[i]) &&
        !stopText(lines[i])
      ) {
        block.push(lines[i]);
        i++;
      }

      let trainer = "";
      let jockey = "";
      let weight = "";
      let prizemoneyEarned = "";
      let inRun = "";
      let margin = "";

      for (
        let j = 0;
        j < block.length;
        j++
      ) {

        const value = block[j];

        if (
          /^T:\s*$/i.test(value) &&
          j + 1 < block.length
        ) {
          trainer = safeText(
            block[j + 1]
          );
          continue;
        }

        if (
          /^J:\s*$/i.test(value) &&
          j + 1 < block.length
        ) {
          jockey = safeText(
            block[j + 1]
          );
          continue;
        }

        const trainerInline = value.match(
          /^T:\s*(.+)$/i
        );

        if (trainerInline) {
          trainer = safeText(
            trainerInline[1]
          );
          continue;
        }

        const jockeyInline = value.match(
          /^J:\s*(.+)$/i
        );

        if (jockeyInline) {
          jockey = safeText(
            jockeyInline[1]
          );
          continue;
        }

        if (
          !weight &&
          isWeight(value)
        ) {
          weight = value;
          continue;
        }

        if (
          !prizemoneyEarned &&
          isPrize(value)
        ) {
          prizemoneyEarned = value;
          continue;
        }

        if (
          !inRun &&
          isInRun(value)
        ) {
          inRun = value;
          continue;
        }

        if (
          !margin &&
          (
            isMargin(value) ||
            isRaceTime(value)
          )
        ) {
          margin = value;
          continue;
        }
      }

      /*
       * Current visible columns end:
       *
       * BB | SP | S-TAB
       *
       * Pull the final three price/dash tokens from the runner block
       * and use the middle one as SP.
       */
      const priceTail = block.filter(
        v => isPrice(v) || isDash(v)
      );

      let sp = "";

      if (priceTail.length >= 3) {
        const spToken =
          priceTail[
            priceTail.length - 2
          ];

        if (isPrice(spToken)) {
          sp = spToken;
        }
      }

      out.push({
        ...meta,
        finishPosition,
        horseNo,
        horseName,
        horseKey: horseKey(
          horseName
        ),
        barrier,
        trainer,
        jockey,
        weight,
        prizemoneyEarned,
        inRun,
        margin,
        sp,
        rawText: block.join(" | "),
        status: scratched
          ? "SCRATCHED"
          : "RESULT"
      });
    }
  }

  return {
    pageLoaded: true,
    visibleResults: out.length > 0,
    renderedUrl,
    rows: out,
    status: out.length ? "RENDERED_RESULTS_EXTRACTED" : "NO_RENDERED_RESULTS_FOUND",
    error: ""
  };
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
    args: ["--disable-dev-shm-usage", "--no-sandbox"]
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    userAgent: "EDGEiQ-Racing/1.0 rendered-results-harvest-public"
  });

  const concurrency = Math.max(1, Math.min(4, Number(process.env.EDGEIQ_RESULTS_CONCURRENCY || 4), rows.length));
  let cursor = 0;

  async function worker() {
    const page = await context.newPage();
    let capturedRaceForms = [];

    page.on("response", async response => {
      const url = response.url();
      const decodedUrl = decodeURIComponent(url);

      if (
        !url.includes("graphql.rmdprod.racing.com") ||
        !decodedUrl.includes("getRaceResults_CD")
      ) {
        return;
      }

      let body = "";

      try {
        body = await response.text();
      } catch (_e) {
        return;
      }

      try {
        const raceForm = JSON.parse(body)?.data?.getRaceForm;

        if (raceForm) {
          capturedRaceForms.push({
            raceId: safeText(raceForm.id),
            raceNumber: safeText(raceForm.raceNumber),
            meetCode: safeText(raceForm.meetCode),
            isTrial: safeText(raceForm.isTrial),
            isJumpOut: safeText(raceForm.isJumpOut),
            venueName: safeText(raceForm.venue && raceForm.venue.venueName)
          });
        }
      } catch (_e) {}
    });

    try {
      while (true) {
        const idx = cursor++;
        if (idx >= rows.length) break;

        const row = rows[idx];
        let result;
        capturedRaceForms = [];

        try {
          await page.goto(row.source_url, { waitUntil: "domcontentloaded", timeout: 90000 });
          try { await page.waitForLoadState("networkidle", { timeout: 8000 }); } catch (_e) {}

          /*
           * Racing.com hydrates the result grid after initial DOM load.
           * A page may already be HTTP 200 / Final Result while the POS
           * runner content is still arriving. Wait for the rendered result
           * headers where possible, then retry extraction before declaring
           * NO_RENDERED_RESULTS_FOUND.
           */
          try {
            await page.waitForFunction(
              () => {
                const text = document.body ? document.body.innerText : "";
                return (
                  /(^|\n)POS(\n|$)/i.test(text) &&
                  /HORSE\s*\/\s*BARRIER/i.test(text)
                );
              },
              { timeout: 7000 }
            );
          } catch (_e) {}

          await page.waitForTimeout(1200);

          for (let i = 0; i < 5; i++) {
            await page.mouse.wheel(0, 1800);
            await page.waitForTimeout(150);
          }

          result = await page.evaluate(extractRenderedResults, row);

          if (!result.visibleResults || !result.rows.length) {
            for (let retry = 1; retry <= 2; retry++) {
              await page.waitForTimeout(2500);

              try {
                await page.waitForFunction(
                  () => {
                    const text = document.body ? document.body.innerText : "";
                    return (
                      /(^|\n)POS(\n|$)/i.test(text) &&
                      /HORSE\s*\/\s*BARRIER/i.test(text)
                    );
                  },
                  { timeout: 4000 }
                );
              } catch (_e) {}

              result = await page.evaluate(
                extractRenderedResults,
                row
              );

              if (
                result.visibleResults &&
                result.rows.length
              ) {
                break;
              }
            }
          }

          const raceFormIdentity = capturedRaceForms.find(
            item => item.raceNumber
          ) || {};

          result = {
            ...result,
            actualRaceNo: raceFormIdentity.raceNumber || "",
            actualRaceId: raceFormIdentity.raceId || "",
            actualMeetCode: raceFormIdentity.meetCode || "",
            actualIsTrial: raceFormIdentity.isTrial || "",
            actualIsJumpOut: raceFormIdentity.isJumpOut || "",
            actualVenueName: raceFormIdentity.venueName || ""
          };
        } catch (err) {
          result = {
            pageLoaded: false,
            visibleResults: false,
            rows: [],
            status: "NO_RENDERED_PAGE_ACCESS",
            error: err && err.message ? err.message : String(err)
          };
        }

        /*
         * EDGEiQ V38 authoritative rendered-race identity validation.
         *
         * Never trust row.race_no alone: it represents the requested race,
         * not necessarily the race Racing.com actually rendered.
         */
        const requestedRaceMatch = String(
          row.source_url || ""
        ).match(/\/race\/(\d+)(?:[/?#]|$)/i);

        const renderedRaceMatch = String(
          result.renderedUrl || ""
        ).match(/\/race\/(\d+)(?:[/?#]|$)/i);

        const requestedRaceNo = requestedRaceMatch
          ? requestedRaceMatch[1]
          : "";

        const renderedRaceNo = renderedRaceMatch
          ? renderedRaceMatch[1]
          : "";

        if (
          requestedRaceNo &&
          result.actualRaceNo &&
          requestedRaceNo !== result.actualRaceNo
        ) {
          result = {
            ...result,
            visibleResults: false,
            rows: [],
            status: "GRAPHQL_RACE_IDENTITY_MISMATCH",
            error:
              `Requested race ${requestedRaceNo} but Racing.com returned race ${result.actualRaceNo}.`
          };
        }

        if (
          requestedRaceNo &&
          renderedRaceNo &&
          requestedRaceNo !== renderedRaceNo
        ) {
          result = {
            ...result,
            visibleResults: false,
            rows: [],
            status: "RENDERED_RACE_IDENTITY_MISMATCH",
            error:
              `Requested race ${requestedRaceNo} but Racing.com rendered race ${renderedRaceNo}.`
          };
        }

        if (
          requestedRaceNo &&
          !renderedRaceNo &&
          result.rows &&
          result.rows.length
        ) {
          result = {
            ...result,
            visibleResults: false,
            rows: [],
            status: "RENDERED_RACE_IDENTITY_UNVERIFIED",
            error:
              `Could not verify rendered race identity for requested race ${requestedRaceNo}.`
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
          actual_race_no: result.actualRaceNo || "",
          actual_race_id: result.actualRaceId || "",
          actual_meet_code: result.actualMeetCode || "",
          status: result.status,
          error: result.error || ""
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

            /*
             * Preserve runner-level classifications such as SCR.
             * Previously result.status overwrote item.status, causing
             * scratched runners to become RENDERED_RESULTS_EXTRACTED.
             */
            status: item.status || result.status,

            error: result.error || ""
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
}

main().catch(err => {
  payload.runtime_error = err && err.message ? err.message : String(err);
  writeProgress();
});
"""

def clean(v: Any) -> str:
    return "" if v is None else str(v).strip()

def horse_key(v: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", re.sub(r"\([^)]*\)", "", clean(v).upper()))

def race_fingerprint(rows: list[dict[str, Any]]) -> str:
    parts = []
    for row in sorted(
        rows,
        key=lambda r: (
            clean(r.get("finish_position")),
            clean(r.get("horse_no")),
            clean(r.get("horse_name")),
        ),
    ):
        parts.append(
            "|".join(
                [
                    clean(row.get("finish_position")),
                    clean(row.get("horse_no")),
                    horse_key(clean(row.get("horse_name"))),
                    clean(row.get("barrier")),
                    clean(row.get("trainer")),
                    clean(row.get("jockey")),
                    clean(row.get("weight")),
                    clean(row.get("margin")).upper().replace(" ", ""),
                    clean(row.get("sp")),
                    clean(row.get("status")).upper(),
                ]
            )
        )
    return "\n".join(parts)

def assert_no_cross_race_fingerprint_duplicates(rows: list[dict[str, Any]]) -> None:
    by_meeting: dict[tuple[str, str], dict[str, list[dict[str, Any]]]] = {}

    for row in rows:
        meeting = (clean(row.get("meeting_date")), clean(row.get("track")).upper())
        race_no = clean(row.get("race_no"))
        by_meeting.setdefault(meeting, {}).setdefault(race_no, []).append(row)

    failures = []

    for (meeting_date, track), races in by_meeting.items():
        by_fingerprint: dict[str, list[str]] = {}

        for race_no, race_rows in races.items():
            fp = race_fingerprint(race_rows)
            if fp:
                by_fingerprint.setdefault(fp, []).append(race_no)

        for race_numbers in by_fingerprint.values():
            if len(set(race_numbers)) > 1:
                failures.append(
                    f"{meeting_date}|{track}|RACES={','.join(sorted(set(race_numbers)))}"
                )

    if failures:
        raise RuntimeError(
            "CROSS_RACE_EXACT_FINGERPRINT_DUPLICATE:" + ";".join(failures[:20])
        )

def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows: list[dict[str, Any]], cols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    tmp.replace(path)

def load_candidates(start_date: str, end_date: str) -> list[dict[str, str]]:
    out = []
    seen = set()

    for r in read_csv(SOURCE):
        meeting_date = clean(r.get("meeting_date"))
        track = clean(r.get("track"))
        race_no = clean(r.get("race_no"))
        race_url = clean(r.get("race_url")) or clean(r.get("speed_data_url")).replace("/speed-data", "")

        if not meeting_date or not track or not race_no or not race_url:
            continue

        # ------------------------------------------------------------
        # Official-results safety filter
        #
        # Upstream calendar flags can be wrong. Racing.com URLs are
        # authoritative enough to identify trial/jumpout meetings:
        #
        #   .../bet365-traralgon-trial/...
        #   .../some-track-jumpout/...
        #
        # These must never enter the official race-results candidate set.
        # ------------------------------------------------------------

        meeting_url = clean(r.get("meeting_url"))
        url_check = " ".join([
            meeting_url,
            race_url,
            clean(r.get("speed_data_url")),
        ]).lower()

        is_trial_flag = clean(
            r.get("is_trial")
        ).lower() in {"true", "1", "yes", "y"}

        is_jumpout_flag = clean(
            r.get("is_jumpout")
        ).lower() in {"true", "1", "yes", "y"}

        is_abandoned_flag = clean(
            r.get("is_abandoned")
        ).lower() in {"true", "1", "yes", "y"}

        meeting_status_text = " ".join([
            clean(r.get("meet_status")),
            clean(r.get("status")),
            clean(r.get("full_status")),
            clean(r.get("discovery_status")),
        ]).lower()

        is_abandoned_status = (
            "abandon" in meeting_status_text
        )

        is_trial_url = (
            "/trial" in url_check
            or "-trial" in url_check
            or "/trials" in url_check
        )

        is_jumpout_url = (
            "/jumpout" in url_check
            or "-jumpout" in url_check
            or "/jumpouts" in url_check
        )

        if (
            is_trial_flag
            or is_jumpout_flag
            or is_abandoned_flag
            or is_abandoned_status
            or is_trial_url
            or is_jumpout_url
        ):
            continue
        if start_date and meeting_date < start_date:
            continue
        if end_date and meeting_date > end_date:
            continue

        key = (meeting_date, track, race_no, race_url)
        if key in seen:
            continue
        seen.add(key)

        out.append({
            "meeting_date": meeting_date,
            "track": track,
            "race_no": race_no,
            "source_url": race_url
        })

    out.sort(key=lambda x: (x["meeting_date"], x["track"], int(float(x["race_no"]))))
    return out

def run_node(selected: list[dict[str, str]]) -> dict[str, Any]:
    TMP.mkdir(parents=True, exist_ok=True)
    helper = TMP / "edgeiq_results_v2_helper.cjs"
    input_path = TMP / "edgeiq_results_v2_input.json"
    output_path = TMP / "edgeiq_results_v2_output.json"

    helper.write_text(NODE_HELPER, encoding="utf-8")
    input_path.write_text(json.dumps(selected, ensure_ascii=False), encoding="utf-8")
    output_path.write_text(json.dumps({"pages": [], "rows": [], "runtime_error": ""}), encoding="utf-8")

    p = subprocess.run(
        ["node", str(helper), str(input_path), str(output_path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=max(900, len(selected) * 60),
        check=False
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    if p.returncode != 0 and not payload.get("runtime_error"):
        payload["runtime_error"] = p.stderr or p.stdout or f"node_exit_{p.returncode}"

    return payload

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--start-date", default="")
    p.add_argument("--end-date", default="")
    p.add_argument("--batch-size", type=int, default=250)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--force", action="store_true")
    return p.parse_args()

def main() -> None:
    args = parse_args()
    built_at = datetime.now(timezone.utc).isoformat()

    candidates = load_candidates(args.start_date, args.end_date)
    selected = candidates[max(0, args.offset): max(0, args.offset) + max(0, args.batch_size)]

    print(f"[edgeiq_results_v2] candidate_races_available={len(candidates)} batch_size={args.batch_size} offset={args.offset} selected={len(selected)}")
    if selected:
        print(f"[edgeiq_results_v2] first_url={selected[0]['source_url']}")

    payload = run_node(selected) if selected else {"pages": [], "rows": [], "runtime_error": ""}

    rows = []
    for r in payload.get("rows", []):
        rows.append({
            "built_at": built_at,
            "meeting_date": clean(r.get("meeting_date")),
            "track": clean(r.get("track")),
            "race_no": clean(r.get("race_no")),
            "race_key": clean(r.get("race_key")),
            "source_url": clean(r.get("source_url")),
            "page_loaded": clean(r.get("page_loaded")),
            "visible_results": clean(r.get("visible_results")),
            "race_name": clean(r.get("raceName")),
            "distance": clean(r.get("distance")),
            "race_class": clean(r.get("raceClass")),
            "track_condition": clean(r.get("trackCondition")),
            "race_time": clean(r.get("raceTime")),
            "finish_position": clean(r.get("finishPosition")),
            "horse_no": clean(r.get("horseNo")),
            "horse_name": clean(r.get("horseName")),
            "horse_key": clean(r.get("horseKey")) or horse_key(r.get("horseName")),
            "barrier": clean(r.get("barrier")),
            "trainer": clean(r.get("trainer")),
            "jockey": clean(r.get("jockey")),
            "weight": clean(r.get("weight")),
            "prizemoney_earned": clean(r.get("prizemoneyEarned")),
            "in_run": clean(r.get("inRun")),
            "margin": clean(r.get("margin")),
            "sp": clean(r.get("sp")),
            "status": clean(r.get("status")),
            "error": clean(r.get("error")),
        })

    pages = payload.get("pages", [])
    pages_loaded = sum(1 for p in pages if clean(p.get("page_loaded")) == "TRUE")
    visible_pages = sum(1 for p in pages if clean(p.get("visible_results")) == "TRUE")
    unique_races = len({r["race_key"] for r in rows if r["race_key"]})
    unique_horses = len({r["horse_key"] for r in rows if r["horse_key"]})

    status = "RENDERED_RESULTS_HARVEST_BUILT" if rows else "NO_RENDERED_RESULTS_FOUND"

    audit = [{
        "built_at": built_at,
        "candidate_races_available": len(candidates),
        "batch_size": args.batch_size,
        "offset": args.offset,
        "attempted_pages": len(selected),
        "pages_loaded": pages_loaded,
        "visible_result_pages": visible_pages,
        "runner_rows_output": len(rows),
        "unique_races": unique_races,
        "unique_horses": unique_horses,
        "graphql_endpoint_called_by_script": "FALSE",
        "api_key_extracted": "FALSE",
        "private_endpoint_used": "FALSE",
        "final_status": status,
    }]

    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    batch_prefix = f"batch_{args.offset:04d}"

    # ------------------------------------------------------------
    # Canonical warehouse upsert
    #
    # Batch files contain ONLY the current batch.
    # OUT is cumulative and must never be replaced by one batch.
    #
    # For every successfully harvested race in this batch:
    #   1. remove the previous version of that entire race
    #   2. insert the newly harvested version
    #
    # Empty/failed batches preserve the existing warehouse.
    # ------------------------------------------------------------

    existing_rows = read_csv(OUT)

    successful_race_keys = {
        clean(r.get("race_key"))
        for r in rows
        if clean(r.get("race_key"))
    }

    if rows and successful_race_keys:
        retained_rows = [
            r for r in existing_rows
            if clean(r.get("race_key")) not in successful_race_keys
        ]

        warehouse_rows = retained_rows + rows
        assert_no_cross_race_fingerprint_duplicates(warehouse_rows)

        def warehouse_sort_key(r):
            race_no = clean(r.get("race_no"))
            finish = clean(r.get("finish_position"))
            horse_no = clean(r.get("horse_no"))

            try:
                race_num = int(float(race_no))
            except Exception:
                race_num = 999999

            try:
                finish_num = int(float(finish))
            except Exception:
                finish_num = 999999

            try:
                horse_num = int(float(horse_no))
            except Exception:
                horse_num = 999999

            return (
                clean(r.get("meeting_date")),
                clean(r.get("track")),
                race_num,
                finish_num,
                horse_num,
                clean(r.get("horse_name")),
            )

        warehouse_rows.sort(key=warehouse_sort_key)

        write_csv(OUT, warehouse_rows, OUT_COLUMNS)
    else:
        warehouse_rows = existing_rows

        if not OUT.exists():
            write_csv(OUT, [], OUT_COLUMNS)

    # Audit describes this invocation.
    write_csv(AUDIT, audit, AUDIT_COLUMNS)

    # Batch archive always contains only this invocation.
    write_csv(
        BATCH_DIR / f"{batch_prefix}_results.csv",
        rows,
        OUT_COLUMNS
    )
    write_csv(
        BATCH_DIR / f"{batch_prefix}_audit.csv",
        audit,
        AUDIT_COLUMNS
    )

    if payload.get("runtime_error"):
        print(f"[edgeiq_results_v2] runtime_error={payload.get('runtime_error')}")

    print(f"[edgeiq_results_v2] pages_loaded={pages_loaded} visible_pages={visible_pages} rows={len(rows)} unique_races={unique_races}")
    print(f"[edgeiq_results_v2] final_status={status}")
    print(f"[edgeiq_results_v2] wrote {OUT.relative_to(ROOT)}")
    print(f"[edgeiq_results_v2] archived batch {args.offset} to {BATCH_DIR.relative_to(ROOT)}")

if __name__ == "__main__":
    main()

