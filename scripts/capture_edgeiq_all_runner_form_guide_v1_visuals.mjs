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
  await page.waitForTimeout(1000);
  return true;
}

async function captureSelector(selector, fileName, label, fullPage = false) {
  const locator = page.locator(selector).first();
  if (await locator.count()) {
    await locator.scrollIntoViewIfNeeded({ timeout: 8000 });
    await page.waitForTimeout(600);
  } else {
    logs.push(`missing-screenshot-target: ${label}`);
  }
  await page.screenshot({ path: path.join(outDir, fileName), fullPage });
}

try {
  await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(2500);

  await safeClick(page.getByText(/Open Meeting/i), "Open Meeting");
  await safeClick(page.getByText(/Open Race/i), "Open Race");
  await safeClick(page.getByRole("button", { name: /^FORM GUIDE$/i }), "FORM GUIDE tab");
  await page.waitForTimeout(2500);

  await captureSelector(
    ".eiq-form-summary-table--all-runner",
    "edgeiq_all_runner_form_guide_full_field.png",
    "full field table",
    false,
  );

  await captureSelector(
    ".eiq-form-v31-runner-sheet:nth-of-type(1)",
    "edgeiq_all_runner_form_guide_runner_1.png",
    "runner 1 profile",
    false,
  );

  await captureSelector(
    ".eiq-form-v31-runner-sheet:nth-of-type(2)",
    "edgeiq_all_runner_form_guide_runner_2.png",
    "runner 2 profile",
    false,
  );

  const scratched = page.locator(".eiq-form-summary-table--all-runner tbody tr.is-scratched").first();
  if (await scratched.count()) {
    await scratched.scrollIntoViewIfNeeded({ timeout: 8000 });
    await page.waitForTimeout(600);
  } else {
    logs.push("no-scratched-row-in-selected-race");
  }
  await page.screenshot({
    path: path.join(outDir, "edgeiq_all_runner_form_guide_scratched.png"),
    fullPage: false,
  });

  const tooltipTrigger = page.locator(".eiq-form-tooltip-trigger").first();
  if (await tooltipTrigger.count()) {
    await tooltipTrigger.hover({ timeout: 8000 });
    await page.waitForTimeout(500);
  } else {
    logs.push("missing-tooltip-trigger");
  }
  await page.screenshot({
    path: path.join(outDir, "edgeiq_all_runner_form_guide_tooltip.png"),
    fullPage: false,
  });

  const secondAnchor = page.locator(".eiq-form-runner-anchor").nth(1);
  if (await secondAnchor.count()) {
    await secondAnchor.click({ timeout: 8000 });
    await page.waitForTimeout(1000);
  } else {
    logs.push("missing-second-horse-anchor");
  }
  await page.screenshot({
    path: path.join(outDir, "edgeiq_all_runner_form_guide_anchor_scroll.png"),
    fullPage: false,
  });

  const runtime = await page.evaluate(() => ({
    runnerProfiles: document.querySelectorAll("[data-runner-profile='true']").length,
    anchors: document.querySelectorAll(".eiq-form-runner-anchor").length,
    recentFormSections: document.querySelectorAll(".eiq-form-v31-recent-form").length,
    scratchedRows: document.querySelectorAll(".eiq-form-summary-table--all-runner tbody tr.is-scratched").length,
    tooltipHeaders: document.querySelectorAll(".eiq-form-tooltip-trigger").length,
    hash: window.location.hash,
  }));

  await fs.writeFile(
    path.join(outDir, "edgeiq_all_runner_form_guide_browser_notes.txt"),
    [
      JSON.stringify(runtime, null, 2),
      "",
      (await page.locator("body").innerText({ timeout: 8000 })).slice(0, 5000),
      "",
      "Console:",
      ...logs.slice(-100),
    ].join("\n"),
    "utf8",
  );

  console.log("EDGEIQ_ALL_RUNNER_FORM_GUIDE_SCREENSHOTS_WRITTEN");
  console.log(JSON.stringify(runtime));
} finally {
  await browser.close();
}
