from __future__ import annotations

import csv
import json
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
TMP = ROOT / "outputs" / "tmp"

INPUT = DATA / "racingcom_rendered_speed_data_non_harvested_pages_v1.csv"
OUT = DATA / "racingcom_speed_data_layout_variants_v1.csv"
AUDIT_OUT = DATA / "racingcom_speed_data_layout_variants_v1_audit.csv"

OUT_COLUMNS = [
    "source_url",
    "meeting_date",
    "track",
    "race_no",
    "layout_type",
    "table_count",
    "runner_count",
    "column_headers",
    "sample_rows",
    "classification_reason",
]

AUDIT_COLUMNS = [
    "pages_audited",
    "standard_speed_table",
    "alternative_speed_table",
    "runner_only_table",
    "no_sectional_metrics",
    "older_layout",
    "unknown_layout",
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

function uniq(values) {
  const seen = new Set();
  const out = [];
  for (const value of values.map(clean).filter(Boolean)) {
    const key = value.toUpperCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(value);
  }
  return out;
}

function inspectFrame() {
  function cleanInPage(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }
  function uniqInPage(values) {
    const seen = new Set();
    const out = [];
    for (const value of values.map(cleanInPage).filter(Boolean)) {
      const key = value.toUpperCase();
      if (seen.has(key)) continue;
      seen.add(key);
      out.push(value);
    }
    return out;
  }
  function cells(row) {
    return Array.from(row.querySelectorAll("th,td")).map((cell) => cleanInPage(cell.innerText || cell.textContent || "")).filter(Boolean);
  }
  const bodyText = cleanInPage(document.body ? document.body.innerText : "");
  const pageTitle = cleanInPage(document.title || "");
  const sectionHeadings = Array.from(document.querySelectorAll("h1,h2,h3,h4,h5,h6,.title,.heading,.tab,.tabs li"))
    .map((el) => cleanInPage(el.innerText || el.textContent || ""))
    .filter(Boolean)
    .slice(0, 80);
  const tables = Array.from(document.querySelectorAll("table"));
  const grids = Array.from(document.querySelectorAll("[role='grid'], .table-container, .grid, .data-grid"));
  const tableBlocks = tables.map((table, tableIndex) => {
    const rows = Array.from(table.querySelectorAll("tr"));
    const headerRows = rows
      .filter((row, index) => index === 0 || /title|head|header/i.test(row.className || ""))
      .map((row) => cells(row).join(" | "))
      .filter(Boolean);
    const sampleRows = rows
      .filter((row) => /data|ng-scope/i.test(row.className || "") || cells(row).length)
      .slice(0, 6)
      .map((row) => cells(row).join(" | "))
      .filter(Boolean);
    return {
      tableIndex,
      className: String(table.className || ""),
      headerRows,
      sampleRows,
    };
  });
  const runnerMatches = bodyText.match(/\b\d+(?:st|nd|rd|th)\s+\d+\.\s+[A-Z][A-Za-z' .-]+/g) || [];
  const metricWords = bodyText.match(/\b(DIST RUN|EARLY|MID|LATE|PEAK|AVG SPEED|AVERAGE SPEED|SPEED|SECTIONALS|SPLITS|OVERALL)\b/gi) || [];
  return {
    pageTitle,
    sectionHeadings,
    tableCount: tables.length,
    gridCount: grids.length,
    runnerCount: runnerMatches.length,
    metricWords: uniqInPage(metricWords),
    tableBlocks,
    bodyHasStandardMetrics: /DIST\s*RUN/i.test(bodyText) && /\bEARLY\b/i.test(bodyText) && /\bMID\b/i.test(bodyText) && /\bLATE\b/i.test(bodyText) && /\bPEAK\b/i.test(bodyText) && /AVG\s*SPEED/i.test(bodyText),
    bodyHasSplitMetrics: /\bOVERALL\b/i.test(bodyText) && /\d+M(?:-\d+M|-FINISH)?/i.test(bodyText),
    bodyHasSectionalText: /\bSectionals\b|\bSplits\b|\bSpeed Data\b/i.test(bodyText),
  };
}

function mergeStates(states) {
  const merged = {
    pageTitle: "",
    sectionHeadings: [],
    tableCount: 0,
    gridCount: 0,
    runnerCount: 0,
    metricWords: [],
    tableBlocks: [],
    bodyHasStandardMetrics: false,
    bodyHasSplitMetrics: false,
    bodyHasSectionalText: false,
  };
  for (const state of states) {
    merged.pageTitle = merged.pageTitle || state.pageTitle || "";
    merged.sectionHeadings.push(...(state.sectionHeadings || []));
    merged.tableCount += Number(state.tableCount || 0);
    merged.gridCount += Number(state.gridCount || 0);
    merged.runnerCount = Math.max(merged.runnerCount, Number(state.runnerCount || 0));
    merged.metricWords.push(...(state.metricWords || []));
    merged.tableBlocks.push(...(state.tableBlocks || []));
    merged.bodyHasStandardMetrics = merged.bodyHasStandardMetrics || Boolean(state.bodyHasStandardMetrics);
    merged.bodyHasSplitMetrics = merged.bodyHasSplitMetrics || Boolean(state.bodyHasSplitMetrics);
    merged.bodyHasSectionalText = merged.bodyHasSectionalText || Boolean(state.bodyHasSectionalText);
  }
  merged.sectionHeadings = uniq(merged.sectionHeadings).slice(0, 30);
  merged.metricWords = uniq(merged.metricWords).slice(0, 30);
  return merged;
}

function classify(state) {
  const headers = state.tableBlocks.flatMap((block) => block.headerRows || []).join(" | ");
  const samples = state.tableBlocks.flatMap((block) => block.sampleRows || []).join(" | ");
  const combined = `${headers} | ${samples}`;
  if (state.bodyHasStandardMetrics || (/DIST\s*RUN/i.test(combined) && /\bEARLY\b/i.test(combined) && /\bMID\b/i.test(combined) && /\bLATE\b/i.test(combined) && /\bPEAK\b/i.test(combined) && /AVG\s*SPEED/i.test(combined))) {
    return ["STANDARD_SPEED_TABLE", "Standard DIST RUN / EARLY / MID / LATE / PEAK / AVG SPEED layout detected."];
  }
  if (state.bodyHasSplitMetrics || /\bOVERALL\b/i.test(combined) || /\d+M(?:-\d+M|-FINISH)/i.test(combined)) {
    return ["ALTERNATIVE_SPEED_TABLE", "Split/sectional timing columns are visible, but standard speed summary columns are absent."];
  }
  if (state.runnerCount > 0 && state.tableCount > 0 && !state.metricWords.length) {
    return ["RUNNER_ONLY_TABLE", "Runner table is visible, but no speed/sectional metric labels were found."];
  }
  if (state.runnerCount > 0 && state.tableCount > 0 && state.bodyHasSectionalText && !state.bodyHasStandardMetrics) {
    return ["NO_SECTIONAL_METRICS", "Speed Data/sectional page is visible with runners, but no usable metric table is exposed."];
  }
  if (state.runnerCount > 0 && state.tableCount > 0) {
    return ["OLDER_LAYOUT", "Runner/table structure exists but does not match standard or split metric layouts."];
  }
  return ["UNKNOWN_LAYOUT", "Rendered page did not expose enough structure to classify the layout."];
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
      userAgent: "EDGEiQ-Racing/1.0 speed-data-layout-variant-audit (public page only)",
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
      userAgent: "EDGEiQ-Racing/1.0 speed-data-layout-variant-audit (public page only)",
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
  await page.waitForTimeout(2600);
  for (let i = 0; i < 10; i += 1) {
    await page.mouse.wheel(0, 1800);
    await page.waitForTimeout(300);
  }
  await page.waitForTimeout(800);
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
      source_url: row.source_url || "",
      meeting_date: row.meeting_date || "",
      track: row.track || "",
      race_no: row.race_no || "",
      layout_type: "UNKNOWN_LAYOUT",
      table_count: 0,
      runner_count: 0,
      column_headers: "",
      sample_rows: "",
      classification_reason: "",
    };
    if (!PUBLIC_SPEED_RE.test(row.source_url || "")) {
      payload.results.push({ ...base, classification_reason: "Rejected non-public Racing.com speed-data URL." });
      writeProgress();
      continue;
    }
    try {
      await page.goto(row.source_url, { waitUntil: "domcontentloaded", timeout: 90000 });
      await settleAndScroll(page);
      const states = [];
      for (const frame of page.frames()) {
        try {
          states.push(await frame.evaluate(inspectFrame));
        } catch (_err) {}
      }
      const state = mergeStates(states);
      const [layoutType, reason] = classify(state);
      const headerParts = [
        state.pageTitle ? `TITLE: ${state.pageTitle}` : "",
        state.sectionHeadings.length ? `HEADINGS: ${state.sectionHeadings.join(" || ")}` : "",
        state.metricWords.length ? `METRICS: ${state.metricWords.join(" || ")}` : "",
        ...state.tableBlocks.flatMap((block) => block.headerRows || []),
      ].filter(Boolean);
      const sampleRows = state.tableBlocks
        .flatMap((block) => block.sampleRows || [])
        .filter(Boolean)
        .slice(0, 5)
        .join(" || ");
      payload.results.push({
        ...base,
        layout_type: layoutType,
        table_count: state.tableCount,
        runner_count: state.runnerCount,
        column_headers: headerParts.join(" || ").slice(0, 4000),
        sample_rows: sampleRows.slice(0, 4000),
        classification_reason: reason,
      });
      writeProgress();
    } catch (err) {
      payload.results.push({
        ...base,
        layout_type: "UNKNOWN_LAYOUT",
        classification_reason: err && err.message ? err.message : String(err),
      });
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


def input_rows() -> list[dict[str, str]]:
    return [row for row in read_csv(INPUT) if clean(row.get("failure_classification")) == "TABLE_LAYOUT_VARIANT"]


def run_browser(rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], str]:
    TMP.mkdir(parents=True, exist_ok=True)
    helper = TMP / "audit_racingcom_speed_data_layout_variants_v1_helper.cjs"
    input_path = TMP / "audit_racingcom_speed_data_layout_variants_v1_input.json"
    output_path = TMP / "audit_racingcom_speed_data_layout_variants_v1_output.json"
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


def audit_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {
        "standard_speed_table": sum(1 for row in rows if clean(row.get("layout_type")) == "STANDARD_SPEED_TABLE"),
        "alternative_speed_table": sum(1 for row in rows if clean(row.get("layout_type")) == "ALTERNATIVE_SPEED_TABLE"),
        "runner_only_table": sum(1 for row in rows if clean(row.get("layout_type")) == "RUNNER_ONLY_TABLE"),
        "no_sectional_metrics": sum(1 for row in rows if clean(row.get("layout_type")) == "NO_SECTIONAL_METRICS"),
        "older_layout": sum(1 for row in rows if clean(row.get("layout_type")) == "OLDER_LAYOUT"),
        "unknown_layout": sum(1 for row in rows if clean(row.get("layout_type")) == "UNKNOWN_LAYOUT"),
    }
    if not rows:
        status = "NO_VARIANT_PAGES_TO_AUDIT"
    elif counts["standard_speed_table"] or counts["alternative_speed_table"]:
        status = "SUPPORTABLE_LAYOUTS_FOUND"
    elif counts["runner_only_table"] == len(rows) or counts["no_sectional_metrics"] == len(rows):
        status = "NO_USABLE_SECTIONAL_METRICS_FOUND"
    else:
        status = "MIXED_LAYOUT_VARIANTS_FOUND"
    return {"pages_audited": len(rows), **counts, "final_status": status}


def main() -> None:
    rows = input_rows()
    print(f"[racingcom_layout_variants_v1] pages_to_audit={len(rows)}")
    results, runtime_error = run_browser(rows)
    if runtime_error:
        print(f"[racingcom_layout_variants_v1] browser warning: {runtime_error}")
    returned = {clean(row.get("source_url")) for row in results}
    for row in rows:
        if clean(row.get("source_url")) in returned:
            continue
        results.append(
            {
                "source_url": clean(row.get("source_url")),
                "meeting_date": clean(row.get("meeting_date")),
                "track": clean(row.get("track")),
                "race_no": clean(row.get("race_no")),
                "layout_type": "UNKNOWN_LAYOUT",
                "table_count": "",
                "runner_count": "",
                "column_headers": "",
                "sample_rows": "",
                "classification_reason": runtime_error or "Browser runner did not return this page.",
            }
        )
    results.sort(key=lambda row: (clean(row.get("meeting_date")), clean(row.get("track")), int(clean(row.get("race_no")) or 0)))
    audit = audit_row(results)
    write_csv(OUT, results, OUT_COLUMNS)
    write_csv(AUDIT_OUT, [audit], AUDIT_COLUMNS)

    print(
        "[racingcom_layout_variants_v1] "
        f"standard={audit['standard_speed_table']} alternative={audit['alternative_speed_table']} "
        f"runner_only={audit['runner_only_table']} no_metrics={audit['no_sectional_metrics']} "
        f"older={audit['older_layout']} unknown={audit['unknown_layout']}"
    )
    print(f"[racingcom_layout_variants_v1] final_status={audit['final_status']}")
    print(f"[racingcom_layout_variants_v1] wrote {OUT.relative_to(ROOT)}")
    print(f"[racingcom_layout_variants_v1] wrote {AUDIT_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
