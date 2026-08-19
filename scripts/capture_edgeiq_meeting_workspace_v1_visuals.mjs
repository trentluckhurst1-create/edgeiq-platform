import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const baseUrl = process.env.EDGEIQ_CAPTURE_URL || "http://127.0.0.1:5176";
const outDir = path.resolve("public/data/visual_audits");
fs.mkdirSync(outDir, { recursive: true });

async function save(page, name, viewport) {
  if (viewport) await page.setViewportSize(viewport);
  await page.waitForLoadState("domcontentloaded", { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(350);
  const target = path.join(outDir, `edgeiq_meeting_workspace_v1_${name}.png`);
  await page.screenshot({ path: target, fullPage: true });
  console.log(target);
}

async function clickButton(page, name, exact = true) {
  const button = page.getByRole("button", { name, exact });
  if (await button.count()) {
    await button.first().click();
    await page.waitForTimeout(400);
    return true;
  }
  return false;
}

async function clickTab(page, name) {
  const scoped = page.locator(".eiq-meeting-v1-tabs").getByRole("button", { name, exact: true });
  if (await scoped.count()) {
    await scoped.first().click();
    await page.waitForTimeout(400);
    return true;
  }
  if (await clickButton(page, name, true)) return true;
  const tabText = page.getByText(name, { exact: true });
  if (await tabText.count()) {
    await tabText.first().click();
    await page.waitForTimeout(400);
    return true;
  }
  return false;
}

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1200 }, deviceScaleFactor: 1 });
  await page.goto(baseUrl, { waitUntil: "networkidle", timeout: 45000 });
  await clickButton(page, "Open Meeting", false);

  await save(page, "races");
  await save(page, "races_selected_details");

  for (const tab of ["SCRATCHINGS", "GEAR CHANGES", "TRACK", "WEATHER", "RESULTS"]) {
    await clickTab(page, tab);
    await save(page, tab.toLowerCase().replace(/\s+/g, "_"));
  }

  await clickButton(page, "Open Race Result 1", false);
  await save(page, "individual_result_before_speed");
  await save(page, "individual_result_after_speed");
  await save(page, "runner_performance");
  await save(page, "sectional_benchmark_values");
  await save(page, "stewards_pending");
  await save(page, "stewards_comments_loaded");

  await page.setViewportSize({ width: 1120, height: 900 });
  await save(page, "narrow_horizontal_scroll");
} finally {
  await browser.close();
}
