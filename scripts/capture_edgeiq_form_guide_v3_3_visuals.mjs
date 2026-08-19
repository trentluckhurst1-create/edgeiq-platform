import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const BASE_URL = process.env.EDGEIQ_CAPTURE_URL || "http://127.0.0.1:5174/";
const OUT_DIR = path.resolve("public", "data");

async function openRace(page) {
  await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Open Meeting" }).click();
  await page.getByRole("button", { name: "Open Race" }).first().click();
  await page.waitForSelector(".eiq-form-summary-table--all-runner tbody tr");
  await page.waitForFunction(
    () =>
      Array.from(document.querySelectorAll(".eiq-form-silk, .eiq-form-detail-silk")).every(
        (item) => !(item instanceof HTMLImageElement) || item.complete,
      ),
    { timeout: 5000 },
  ).catch(() => undefined);
  await page.waitForTimeout(600);
}

async function capture(page, fileName) {
  const filePath = path.join(OUT_DIR, fileName);
  await page.screenshot({ path: filePath, fullPage: false });
  return filePath;
}

async function main() {
  await mkdir(OUT_DIR, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  const shots = [];

  await openRace(page);
  shots.push(await capture(page, "edgeiq_form_guide_v3_3_full_table_1920.png"));

  await page.setViewportSize({ width: 1600, height: 1000 });
  await openRace(page);
  shots.push(await capture(page, "edgeiq_form_guide_v3_3_full_table_1600.png"));

  await page.getByRole("button", {
    name: "DAYS: Calendar days since the runner's most recent official race start, measured against the selected race date.",
  }).click();
  await page.waitForSelector(".eiq-form-header-tooltip");
  shots.push(await capture(page, "edgeiq_form_guide_v3_3_tooltip_above.png"));

  await page.getByRole("button", { name: "Metric Guide" }).click();
  await page.waitForSelector(".eiq-form-metric-guide-popover");
  shots.push(await capture(page, "edgeiq_form_guide_v3_3_metric_guide.png"));

  await page.locator('a[href="#runner-profile-5355786"]').click();
  await page.waitForTimeout(700);
  shots.push(await capture(page, "edgeiq_form_guide_v3_3_runner_1.png"));
  shots.push(await capture(page, "edgeiq_form_guide_v3_3_anchor_scroll.png"));

  await page.mouse.wheel(0, 540);
  await page.waitForTimeout(300);
  shots.push(await capture(page, "edgeiq_form_guide_v3_3_recent_form.png"));

  await page.locator('a[href="#runner-profile-5348516"]').click();
  await page.waitForTimeout(700);
  shots.push(await capture(page, "edgeiq_form_guide_v3_3_runner_2.png"));
  shots.push(await capture(page, "edgeiq_form_guide_v3_3_scratched.png"));

  const verification = await page.evaluate(() => ({
    rows: document.querySelectorAll(".eiq-form-summary-table--all-runner tbody tr").length,
    profiles: document.querySelectorAll('[data-runner-profile="true"]').length,
    oldTooltipIcons: document.querySelectorAll(".eiq-form-tooltip-trigger").length,
    metricGuideButtons: document.querySelectorAll(".eiq-form-metric-guide-button").length,
    tooltipPortal: Boolean(document.querySelector(".eiq-form-header-tooltip")),
    tableMinWidth: getComputedStyle(document.querySelector(".eiq-form-summary-table--all-runner table")).minWidth,
    rowHeight: getComputedStyle(document.querySelector(".eiq-race-form-guide--all-runner")).getPropertyValue("--edgeiq-form-guide-row-height").trim(),
    hash: window.location.hash,
  }));

  await browser.close();
  console.log(JSON.stringify({ status: "EDGEIQ_FORM_GUIDE_V3_3_VISUALS_CAPTURED", shots, verification }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
