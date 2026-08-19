from __future__ import annotations

import csv
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
TMP = ROOT / "outputs" / "tmp"

INPUT = DATA / "racingcom_form_speed_data_url_audit_v1.csv"
DOWNLOAD_DIR = DATA / "racingcom_sectionals_downloads_v1"
MANIFEST = DATA / "racingcom_speed_data_csv_download_manifest_v1.csv"
AUDIT = DATA / "racingcom_speed_data_csv_download_manifest_v1_audit.csv"

PRIORITY_TEST_URL = "https://www.racing.com/form/2026-05-31/sportsbet-sandown-lakeside/race/3/speed-data"
MAX_URLS = int(os.environ.get("EDGEIQ_RACINGCOM_BROWSER_CSV_MAX_URLS", "48"))

MANIFEST_COLUMNS = [
    "source_speed_data_url",
    "track",
    "race_no",
    "page_loaded",
    "download_text_visible",
    "csv_clickable_found",
    "csv_download_success",
    "downloaded_filename",
    "local_path",
    "file_size_bytes",
    "status",
    "error",
]

AUDIT_COLUMNS = [
    "input_urls",
    "pages_attempted",
    "pages_loaded",
    "download_text_visible_count",
    "csv_clickable_found_count",
    "csv_download_success_count",
    "csv_download_failed_count",
    "graphql_endpoint_called_by_script",
    "api_key_extracted",
    "private_endpoint_used",
    "final_status",
]

NODE_HELPER = r"""
const fs = require("fs");
const path = require("path");

const inputPath = process.argv[2];
const outputPath = process.argv[3];
const downloadDir = process.argv[4];
const rows = JSON.parse(fs.readFileSync(inputPath, "utf8"));
const REUSE_EXISTING = process.env.EDGEIQ_RACINGCOM_BROWSER_CSV_REUSE_EXISTING !== "0";

fs.mkdirSync(downloadDir, { recursive: true });

const PUBLIC_SPEED_RE = /^https:\/\/www\.racing\.com\/form\/\d{4}-\d{2}-\d{2}\/[^/]+\/race\/\d+\/speed-data(?:[?#].*)?$/i;

function clean(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function safeFilePart(value) {
  return clean(value).replace(/[^A-Za-z0-9._-]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 140) || "racingcom";
}

function filePrefix(row) {
  const url = clean(row.speed_data_url);
  const match = url.match(/\/form\/(\d{4}-\d{2}-\d{2})\/([^/]+)\/race\/(\d+)\/speed-data/i);
  if (match) {
    return safeFilePart(`${match[1]}_${match[2]}_R${match[3]}`);
  }
  return safeFilePart(`${row.track || "track"}_R${row.race_no || "race"}`);
}

function existingDownload(row, dir) {
  const prefix = filePrefix(row);
  const files = fs.readdirSync(dir)
    .filter((name) => name.toLowerCase().endsWith(".csv") && name.startsWith(prefix))
    .map((name) => {
      const fullPath = path.join(dir, name);
      const stat = fs.statSync(fullPath);
      return { name, fullPath, size: stat.size, mtimeMs: stat.mtimeMs };
    })
    .filter((item) => item.size > 0)
    .sort((a, b) => b.mtimeMs - a.mtimeMs);
  return files[0] || null;
}

function uniquePath(dir, name) {
  const parsed = path.parse(name);
  let candidate = path.join(dir, name);
  let counter = 2;
  while (fs.existsSync(candidate)) {
    candidate = path.join(dir, `${parsed.name}_${counter}${parsed.ext || ".csv"}`);
    counter += 1;
  }
  return candidate;
}

async function createBrowser(playwright) {
  const errors = [];
  try {
    const browser = await playwright.chromium.launch({
      headless: true,
      args: ["--disable-dev-shm-usage", "--no-sandbox"],
    });
    const context = await browser.newContext({
      acceptDownloads: true,
      userAgent: "EDGEiQ-Racing/1.0 visible-csv-download-discovery (public page only)",
      viewport: { width: 1440, height: 1000 },
    });
    return { browser, context, closeBrowser: true };
  } catch (err) {
    errors.push(`launch:${err && err.message ? err.message : String(err)}`);
  }

  try {
    const browser = await playwright.chromium.connectOverCDP("http://127.0.0.1:9222");
    const context = browser.contexts()[0] || await browser.newContext({
      acceptDownloads: true,
      userAgent: "EDGEiQ-Racing/1.0 visible-csv-download-discovery (public page only)",
      viewport: { width: 1440, height: 1000 },
    });
    return { browser, context, closeBrowser: false };
  } catch (err) {
    errors.push(`cdp:${err && err.message ? err.message : String(err)}`);
  }

  throw new Error(errors.join(" | "));
}

async function acceptCookiesIfVisible(page) {
  const texts = ["Accept All Cookies", "Accept All", "I Accept", "Accept"];
  for (const text of texts) {
    try {
      const loc = page.getByText(text, { exact: false }).first();
      if (await loc.count()) {
        await loc.click({ timeout: 2500, force: true });
        await page.waitForTimeout(800);
        return true;
      }
    } catch (_err) {}
  }
  return false;
}

async function settleAndScroll(page) {
  try {
    await page.waitForLoadState("networkidle", { timeout: 18000 });
  } catch (_err) {}
  await page.waitForTimeout(3000);
  await acceptCookiesIfVisible(page);
  for (let i = 0; i < 10; i += 1) {
    await page.mouse.wheel(0, 2200);
    await page.waitForTimeout(450);
  }
  await page.waitForTimeout(1200);
}

async function renderedDownloadState(page) {
  const frameStates = [];
  for (const frame of page.frames()) {
    try {
      const state = await frame.evaluate(() => {
        function clean(value) {
          return String(value || "").replace(/\s+/g, " ").trim();
        }
        function visible(el) {
          const style = window.getComputedStyle(el);
          const rect = el.getBoundingClientRect();
          return style && style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
        }
        const bodyText = clean(document.body ? document.body.innerText : "");
        const elements = Array.from(document.querySelectorAll("a, button, [role='button'], span, div, p, li, td, th"));
        const candidates = [];
        for (let index = 0; index < elements.length; index += 1) {
          const el = elements[index];
          const text = clean(el.innerText || el.textContent || "");
          if (!text || !/(Download Race Sectional Data|CSV|PDF)/i.test(text)) continue;
          if (!visible(el)) continue;
          const rect = el.getBoundingClientRect();
          const clickable = el.closest("a,button,[role='button'],[onclick]") || el;
          candidates.push({
            index,
            tag: el.tagName,
            clickableTag: clickable.tagName,
            text,
            href: clickable.href || clickable.getAttribute("href") || "",
            x: Math.round(rect.x),
            y: Math.round(rect.y),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
          });
        }
        return {
          bodyHasDownloadText: /Download Race Sectional Data/i.test(bodyText),
          bodyHasCsvText: /(^|\b|[^A-Z])CSV([^A-Z]|$)/i.test(bodyText.toUpperCase()),
          bodyHasPdfText: /(^|\b|[^A-Z])PDF([^A-Z]|$)/i.test(bodyText.toUpperCase()),
          candidates,
        };
      });
      frameStates.push({
        url: frame.url(),
        ...state,
      });
    } catch (_err) {}
  }
  return frameStates;
}

async function clickCsvInFrame(page, frame) {
  const jsClick = async (mode) => {
    return await frame.evaluate((clickMode) => {
      function clean(value) {
        return String(value || "").replace(/\s+/g, " ").trim();
      }
      function visible(el) {
        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        return style && style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
      }
      function clickableTarget(el) {
        let current = el;
        for (let depth = 0; current && depth < 7; depth += 1) {
          const tag = current.tagName || "";
          if (/^(A|BUTTON)$/i.test(tag) || current.getAttribute("role") === "button" || current.getAttribute("onclick")) {
            return current;
          }
          current = current.parentElement;
        }
        return el;
      }
      const elements = Array.from(document.querySelectorAll("a, button, [role='button'], span, div, p, li, td, th"));
      const candidates = elements.filter((el) => {
        const text = clean(el.innerText || el.textContent || "");
        if (clickMode === "exact") return text.toUpperCase() === "CSV" && visible(el);
        return /\bCSV\b/i.test(text) && visible(el);
      });
      const preferred = candidates[candidates.length - 1];
      if (!preferred) {
        return { clicked: false, reason: `NO_${clickMode.toUpperCase()}_CSV_ELEMENT` };
      }
      const target = clickableTarget(preferred);
      target.scrollIntoView({ block: "center", inline: "center" });
      const rect = target.getBoundingClientRect();
      const eventOptions = {
        bubbles: true,
        cancelable: true,
        view: window,
        clientX: rect.left + rect.width / 2,
        clientY: rect.top + rect.height / 2,
      };
      target.dispatchEvent(new MouseEvent("mouseover", eventOptions));
      target.dispatchEvent(new MouseEvent("mousedown", eventOptions));
      target.dispatchEvent(new MouseEvent("mouseup", eventOptions));
      target.dispatchEvent(new MouseEvent("click", eventOptions));
      return {
        clicked: true,
        text: clean(preferred.innerText || preferred.textContent || ""),
        tag: preferred.tagName,
        targetTag: target.tagName,
        href: target.href || target.getAttribute("href") || "",
      };
    }, mode);
  };

  for (const mode of ["exact", "contains"]) {
    const downloadPromise = page.waitForEvent("download", { timeout: 12000 }).catch((err) => ({ __downloadError: err.message || String(err) }));
    const clickResult = await jsClick(mode).catch((err) => ({ clicked: false, reason: err.message || String(err) }));
    if (!clickResult.clicked) {
      continue;
    }
    const download = await downloadPromise;
    if (download && !download.__downloadError) {
      return { download, clickResult, clickMode: `JS_${mode.toUpperCase()}_CSV_CLICK` };
    }
  }

  return { download: null, clickResult: null, clickMode: "" };
}

async function captureCsvDownload(page, row, downloadDir) {
  const state = await renderedDownloadState(page);
  const downloadTextVisible = state.some((item) => item.bodyHasDownloadText || item.bodyHasCsvText || item.bodyHasPdfText || (item.candidates || []).length > 0);
  const csvClickableFound = state.some((item) => (item.candidates || []).some((candidate) => /\bCSV\b/i.test(candidate.text || "")));

  if (!csvClickableFound) {
    return {
      downloadTextVisible,
      csvClickableFound,
      success: false,
      filename: "",
      localPath: "",
      fileSizeBytes: 0,
      status: downloadTextVisible ? "DOWNLOAD_TEXT_VISIBLE_NO_CSV_CLICKABLE" : "NO_VISIBLE_CSV_FOUND",
      error: "",
    };
  }

  for (const frame of page.frames()) {
    const result = await clickCsvInFrame(page, frame);
    if (!result.download) continue;
    const suggested = result.download.suggestedFilename() || "racingcom_sectionals.csv";
    const filename = safeFilePart(`${filePrefix(row)}_${suggested.endsWith(".csv") ? suggested : `${suggested}.csv`}`);
    const target = uniquePath(downloadDir, filename);
    await result.download.saveAs(target);
    const stat = fs.statSync(target);
    return {
      downloadTextVisible,
      csvClickableFound,
      success: true,
      filename: path.basename(target),
      localPath: target,
      fileSizeBytes: stat.size,
      status: "CSV_DOWNLOAD_SUCCESS",
      error: "",
    };
  }

  return {
    downloadTextVisible,
    csvClickableFound,
    success: false,
    filename: "",
    localPath: "",
    fileSizeBytes: 0,
    status: "VISIBLE_CSV_BUT_DOWNLOAD_FAILED",
    error: "CSV element was visible/clickable but no browser download event was captured.",
  };
}

(async () => {
  const results = [];
  function writeProgress() {
    fs.writeFileSync(outputPath, JSON.stringify({ results, runtime_error: "" }, null, 2));
  }
  let playwright;
  try {
    playwright = require("playwright");
  } catch (err) {
    for (const row of rows) {
      results.push({
        source_speed_data_url: row.speed_data_url || "",
        track: row.track || "",
        race_no: row.race_no || "",
        page_loaded: "FALSE",
        download_text_visible: "FALSE",
        csv_clickable_found: "FALSE",
        csv_download_success: "FALSE",
        downloaded_filename: "",
        local_path: "",
        file_size_bytes: 0,
        status: "BROWSER_RUNTIME_UNAVAILABLE",
        error: `playwright_require_failed:${err.message || String(err)}`,
      });
    }
    fs.writeFileSync(outputPath, JSON.stringify({ results, runtime_error: "playwright_require_failed" }, null, 2));
    return;
  }

  let bundle;
  try {
    bundle = await createBrowser(playwright);
  } catch (err) {
    for (const row of rows) {
      results.push({
        source_speed_data_url: row.speed_data_url || "",
        track: row.track || "",
        race_no: row.race_no || "",
        page_loaded: "FALSE",
        download_text_visible: "FALSE",
        csv_clickable_found: "FALSE",
        csv_download_success: "FALSE",
        downloaded_filename: "",
        local_path: "",
        file_size_bytes: 0,
        status: "BROWSER_RUNTIME_UNAVAILABLE",
        error: `browser_start_failed:${err.message || String(err)}`,
      });
    }
    fs.writeFileSync(outputPath, JSON.stringify({ results, runtime_error: "browser_start_failed" }, null, 2));
    return;
  }

  const { browser, context, closeBrowser } = bundle;
  const page = await context.newPage();

  for (const row of rows) {
    const url = clean(row.speed_data_url);
    if (REUSE_EXISTING) {
      const existing = existingDownload(row, downloadDir);
      if (existing) {
        results.push({
          source_speed_data_url: url,
          track: row.track || "",
          race_no: row.race_no || "",
          page_loaded: "TRUE",
          download_text_visible: "TRUE",
          csv_clickable_found: "TRUE",
          csv_download_success: "TRUE",
          downloaded_filename: existing.name,
          local_path: existing.fullPath,
          file_size_bytes: existing.size,
          status: "CSV_DOWNLOAD_SUCCESS_EXISTING_FILE",
          error: "",
        });
        writeProgress();
        continue;
      }
    }

    if (!PUBLIC_SPEED_RE.test(url)) {
      results.push({
        source_speed_data_url: url,
        track: row.track || "",
        race_no: row.race_no || "",
        page_loaded: "FALSE",
        download_text_visible: "FALSE",
        csv_clickable_found: "FALSE",
        csv_download_success: "FALSE",
        downloaded_filename: "",
        local_path: "",
        file_size_bytes: 0,
        status: "SAFETY_BLOCKED",
        error: "Non-public Racing.com speed-data URL rejected.",
      });
      writeProgress();
      continue;
    }

    try {
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 90000 });
      await settleAndScroll(page);
      const capture = await captureCsvDownload(page, row, downloadDir);
      results.push({
        source_speed_data_url: url,
        track: row.track || "",
        race_no: row.race_no || "",
        page_loaded: "TRUE",
        download_text_visible: capture.downloadTextVisible ? "TRUE" : "FALSE",
        csv_clickable_found: capture.csvClickableFound ? "TRUE" : "FALSE",
        csv_download_success: capture.success ? "TRUE" : "FALSE",
        downloaded_filename: capture.filename,
        local_path: capture.localPath,
        file_size_bytes: capture.fileSizeBytes,
        status: capture.status,
        error: capture.error,
      });
      writeProgress();
    } catch (err) {
      results.push({
        source_speed_data_url: url,
        track: row.track || "",
        race_no: row.race_no || "",
        page_loaded: "FALSE",
        download_text_visible: "FALSE",
        csv_clickable_found: "FALSE",
        csv_download_success: "FALSE",
        downloaded_filename: "",
        local_path: "",
        file_size_bytes: 0,
        status: "NO_RENDERED_PAGE_ACCESS",
        error: err && err.message ? err.message : String(err),
      });
      writeProgress();
    }
  }

  await page.close().catch(() => {});
  if (closeBrowser) {
    await browser.close().catch(() => {});
  }
  writeProgress();
})();
"""


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
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


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    tmp.replace(path)


def is_public_speed_url(url: str) -> bool:
    return bool(
        re.fullmatch(
            r"https://www\.racing\.com/form/\d{4}-\d{2}-\d{2}/[^/]+/race/\d+/speed-data(?:[?#].*)?",
            clean(url),
            flags=re.IGNORECASE,
        )
    )


def load_input_rows() -> tuple[list[dict[str, str]], int]:
    rows = read_csv(INPUT)
    seen: set[str] = set()
    selected: list[dict[str, str]] = []
    for row in rows:
        url = clean(row.get("speed_data_url"))
        if not url or url in seen or not is_public_speed_url(url):
            continue
        seen.add(url)
        selected.append(
            {
                "speed_data_url": url,
                "track": clean(row.get("track")),
                "race_no": clean(row.get("race_no")),
            }
        )

    selected.sort(key=lambda item: (0 if item["speed_data_url"].lower() == PRIORITY_TEST_URL.lower() else 1, item["speed_data_url"]))
    return selected[:MAX_URLS], len(rows)


def run_node_browser(input_rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], str]:
    TMP.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    helper_path = TMP / "discover_racingcom_speed_data_csv_browser_v1_helper.cjs"
    input_path = TMP / "discover_racingcom_speed_data_csv_browser_v1_input.json"
    output_path = TMP / "discover_racingcom_speed_data_csv_browser_v1_output.json"

    helper_path.write_text(NODE_HELPER, encoding="utf-8")
    input_path.write_text(json.dumps(input_rows, indent=2), encoding="utf-8")

    def read_partial_output() -> list[dict[str, Any]]:
        if not output_path.exists():
            return []
        try:
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            return list(payload.get("results") or [])
        except Exception:
            return []

    try:
        completed = subprocess.run(
            ["node", str(helper_path), str(input_path), str(output_path), str(DOWNLOAD_DIR)],
            cwd=str(ROOT),
            check=False,
            capture_output=True,
            text=True,
            timeout=2700,
        )
    except subprocess.TimeoutExpired as exc:
        return read_partial_output(), f"node_subprocess_timeout_after_{exc.timeout}_seconds"
    except Exception as exc:  # noqa: BLE001 - keep output auditable.
        return read_partial_output(), f"node_subprocess_failed:{exc.__class__.__name__}:{exc}"

    if completed.returncode != 0:
        message = clean(completed.stderr) or clean(completed.stdout) or f"node_return_code_{completed.returncode}"
        return read_partial_output(), f"node_browser_failed:{message[:700]}"

    if not output_path.exists():
        return [], "node_browser_failed:no_output_json"

    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [], f"node_output_parse_failed:{exc.__class__.__name__}:{exc}"

    return list(payload.get("results") or []), clean(payload.get("runtime_error"))


def fallback_rows(input_rows: list[dict[str, str]], status: str, error: str) -> list[dict[str, Any]]:
    return [
        {
            "source_speed_data_url": row["speed_data_url"],
            "track": row.get("track", ""),
            "race_no": row.get("race_no", ""),
            "page_loaded": "FALSE",
            "download_text_visible": "FALSE",
            "csv_clickable_found": "FALSE",
            "csv_download_success": "FALSE",
            "downloaded_filename": "",
            "local_path": "",
            "file_size_bytes": 0,
            "status": status,
            "error": error,
        }
        for row in input_rows
    ]


def final_status(rows: list[dict[str, Any]]) -> str:
    if any(clean(row.get("status")) == "SAFETY_BLOCKED" for row in rows):
        return "SAFETY_BLOCKED"
    successes = sum(1 for row in rows if clean(row.get("csv_download_success")) == "TRUE")
    if successes == len(rows) and rows:
        return "CSV_DOWNLOADS_SUCCESS"
    if successes:
        return "PARTIAL_CSV_DOWNLOADS"
    if any(clean(row.get("csv_clickable_found")) == "TRUE" or clean(row.get("download_text_visible")) == "TRUE" for row in rows):
        return "VISIBLE_CSV_BUT_DOWNLOAD_FAILED"
    return "NO_VISIBLE_CSV_FOUND"


def main() -> None:
    input_rows, input_urls = load_input_rows()
    print(f"[racingcom_browser_csv_v1] input_urls={input_urls}; unique_public_speed_urls={len(input_rows)}")
    if input_rows:
        print(f"[racingcom_browser_csv_v1] priority_test_first={input_rows[0]['speed_data_url']}")

    rows, runtime_error = run_node_browser(input_rows)
    if runtime_error:
        print(f"[racingcom_browser_csv_v1] browser runtime warning: {runtime_error}")
    if not rows:
        rows = fallback_rows(input_rows, "NO_VISIBLE_CSV_FOUND", runtime_error or "Browser runner returned no rows.")
    else:
        completed_urls = {clean(row.get("source_speed_data_url")) for row in rows}
        missing_rows = [row for row in input_rows if row["speed_data_url"] not in completed_urls]
        if missing_rows:
            rows.extend(fallback_rows(missing_rows, "NO_VISIBLE_CSV_FOUND", runtime_error or "Browser runner did not return this URL."))

    pages_attempted = len(input_rows)
    pages_loaded = sum(1 for row in rows if clean(row.get("page_loaded")) == "TRUE")
    download_text_visible_count = sum(1 for row in rows if clean(row.get("download_text_visible")) == "TRUE")
    csv_clickable_found_count = sum(1 for row in rows if clean(row.get("csv_clickable_found")) == "TRUE")
    csv_download_success_count = sum(1 for row in rows if clean(row.get("csv_download_success")) == "TRUE")
    csv_download_failed_count = pages_attempted - csv_download_success_count
    status = final_status(rows)

    audit_row = {
        "input_urls": input_urls,
        "pages_attempted": pages_attempted,
        "pages_loaded": pages_loaded,
        "download_text_visible_count": download_text_visible_count,
        "csv_clickable_found_count": csv_clickable_found_count,
        "csv_download_success_count": csv_download_success_count,
        "csv_download_failed_count": csv_download_failed_count,
        "graphql_endpoint_called_by_script": "FALSE",
        "api_key_extracted": "FALSE",
        "private_endpoint_used": "FALSE",
        "final_status": status,
    }

    write_csv(MANIFEST, rows, MANIFEST_COLUMNS)
    write_csv(AUDIT, [audit_row], AUDIT_COLUMNS)

    print(f"[racingcom_browser_csv_v1] wrote {MANIFEST.relative_to(ROOT)} rows={len(rows)}")
    print(f"[racingcom_browser_csv_v1] wrote {AUDIT.relative_to(ROOT)} final_status={status}; csv_download_success={csv_download_success_count}")


if __name__ == "__main__":
    main()
