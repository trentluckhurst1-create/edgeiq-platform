import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const baseUrl = process.env.EDGEIQ_CAPTURE_URL || "http://127.0.0.1:5173";
const outDir = path.resolve("public/data/visual_audits");
fs.mkdirSync(outDir, { recursive: true });

async function save(page, name, options = {}) {
  if (options.viewport) await page.setViewportSize(options.viewport);
  await page.waitForLoadState("domcontentloaded", { timeout: 20000 }).catch(() => {});
  const target = path.join(outDir, `edgeiq_light_design_v3_${name}.png`);
  await page.screenshot({ path: target, fullPage: true });
  console.log(target);
}

async function clickFirstButton(page, name) {
  const locator = page.getByRole("button", { name });
  const count = await locator.count();
  if (!count) return false;
  await locator.first().click();
  await page.waitForLoadState("domcontentloaded", { timeout: 10000 }).catch(() => {});
  await page.waitForTimeout(300);
  return true;
}

async function clickTab(page, label) {
  const exact = page.getByRole("button", { name: label, exact: true });
  if (await exact.count()) {
    await exact.first().click();
    await page.waitForTimeout(250);
    return true;
  }
  const text = page.getByText(label, { exact: true });
  if (await text.count()) {
    await text.first().click();
    await page.waitForTimeout(250);
    return true;
  }
  return false;
}

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1200 }, deviceScaleFactor: 1 });
  await page.goto(baseUrl, { waitUntil: "networkidle", timeout: 45000 });
  await save(page, "meetings");

  await clickFirstButton(page, "Open Meeting");
  await save(page, "meeting_detail");

  await clickTab(page, "WEATHER");
  await save(page, "meeting_weather");
  await clickTab(page, "RACES");

  await clickFirstButton(page, "Open Race");
  await save(page, "form");

  for (const tab of ["MAP", "MARKET", "OVERVIEW", "REVIEW"]) {
    await clickTab(page, tab);
    await save(page, tab.toLowerCase());
  }

  await clickTab(page, "FORM GUIDE");
  await save(page, "narrow", { viewport: { width: 1120, height: 900 } });
} finally {
  await browser.close();
}
