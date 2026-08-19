import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const outDir = path.resolve("public/data/visual_audits");
await fs.mkdir(outDir, { recursive: true });

const baseUrl = process.env.EDGEIQ_VISUAL_URL || "http://127.0.0.1:5177/";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: 1,
});

const logs = [];
page.on("console", (msg) => logs.push(`${msg.type()}: ${msg.text()}`));
page.on("pageerror", (err) => logs.push(`pageerror: ${err.message}`));

async function safeClick(locator, label) {
  if (!(await locator.count())) {
    logs.push(`missing-click-target: ${label}`);
    return false;
  }
  await locator.first().click({ timeout: 8000 });
  await page.waitForTimeout(1200);
  return true;
}

async function scrollTo(selector, label) {
  const locator = page.locator(selector).first();
  if (await locator.count()) {
    await locator.scrollIntoViewIfNeeded({ timeout: 8000 });
    await page.waitForTimeout(600);
    return true;
  }
  logs.push(`missing-scroll-target: ${label}`);
  return false;
}

try {
  await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(2500);

  await safeClick(page.getByText(/Open Meeting/i), "Open Meeting");
  await safeClick(page.getByText(/Open Race/i), "Open Race");
  await safeClick(page.getByRole("button", { name: /^FORM GUIDE$/i }), "FORM GUIDE tab");
  await page.waitForTimeout(2500);

  await page.screenshot({
    path: path.join(outDir, "edgeiq_form_guide_v3_full_tab.png"),
    fullPage: true,
  });

  const scratchedRow = page.locator(".eiq-form-summary-table--v3 tbody tr.is-scratched").first();
  if (await scratchedRow.count()) {
    await scratchedRow.scrollIntoViewIfNeeded({ timeout: 8000 });
    await page.waitForTimeout(600);
  } else {
    logs.push("no-scratched-rows-visible-in-selected-race");
  }
  await page.screenshot({
    path: path.join(outDir, "edgeiq_form_guide_v3_scratched_rows.png"),
    fullPage: false,
  });

  await scrollTo(".eiq-form-v3-runner-header", "runner profile header");
  await page.screenshot({
    path: path.join(outDir, "edgeiq_form_guide_v3_runner_profile.png"),
    fullPage: false,
  });

  await scrollTo(".eiq-form-v3-recent-form", "recent form");
  await page.screenshot({
    path: path.join(outDir, "edgeiq_form_guide_v3_recent_form.png"),
    fullPage: false,
  });

  const bodyText = await page.locator("body").innerText({ timeout: 8000 });
  await fs.writeFile(
    path.join(outDir, "edgeiq_form_guide_v3_browser_notes.txt"),
    [bodyText.slice(0, 5000), "", "Console:", ...logs.slice(-80)].join("\n"),
    "utf8",
  );

  console.log("EDGEIQ_FORM_GUIDE_V3_SCREENSHOTS_WRITTEN");
} finally {
  await browser.close();
}
