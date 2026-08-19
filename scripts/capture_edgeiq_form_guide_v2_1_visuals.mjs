import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const outDir = path.resolve("public/data/visual_audits");
await fs.mkdir(outDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({
  viewport: { width: 1600, height: 1000 },
  deviceScaleFactor: 1,
});
const logs = [];
page.on("console", (msg) => logs.push(`${msg.type()}: ${msg.text()}`));
page.on("pageerror", (err) => logs.push(`pageerror: ${err.message}`));

async function clickFirstByText(pattern) {
  const locator = page.getByText(pattern).first();
  if (await locator.count()) {
    await locator.click({ timeout: 5000 });
    await page.waitForTimeout(1200);
    return true;
  }
  return false;
}

try {
  await page.goto("http://127.0.0.1:5177/", {
    waitUntil: "domcontentloaded",
    timeout: 30000,
  });
  await page.waitForTimeout(3000);
  await page.screenshot({
    path: path.join(outDir, "edgeiq_form_guide_v2_1_initial.png"),
    fullPage: true,
  });

  await clickFirstByText(/Open Meeting/i);
  await clickFirstByText(/Open Race/i);
  await clickFirstByText(/FORM GUIDE/i);
  await page.waitForLoadState("domcontentloaded", { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(2500);

  await page.screenshot({
    path: path.join(outDir, "edgeiq_form_guide_v2_1_geelong_r1.png"),
    fullPage: true,
  });

  const priceCell = page.locator(".eiq-cell-market").filter({ hasText: /\$/ }).first();
  if (await priceCell.count()) {
    await priceCell.scrollIntoViewIfNeeded();
  }
  await page.screenshot({
    path: path.join(outDir, "edgeiq_form_guide_v2_1_populated_prices.png"),
    fullPage: false,
  });

  const detail = page.locator(".eiq-form-runner-detail").first();
  if (await detail.count()) {
    await detail.scrollIntoViewIfNeeded();
    await page.waitForTimeout(800);
  }
  await page.screenshot({
    path: path.join(outDir, "edgeiq_form_guide_v2_1_full_form.png"),
    fullPage: false,
  });

  const bodyText = await page.locator("body").innerText({ timeout: 5000 });
  await fs.writeFile(
    path.join(outDir, "edgeiq_form_guide_v2_1_browser_notes.txt"),
    [bodyText.slice(0, 3000), "", "Console:", ...logs.slice(-50)].join("\n"),
    "utf8",
  );
  console.log("SCREENSHOTS_WRITTEN");
} finally {
  await browser.close();
}
