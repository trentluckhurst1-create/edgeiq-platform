import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const outDir = path.resolve("public/data/visual_audits");
await fs.mkdir(outDir, { recursive: true });

const baseUrl = process.env.EDGEIQ_VISUAL_URL || "http://127.0.0.1:5173/";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: 1,
});

const logs = [];
page.on("console", (msg) => logs.push(`${msg.type()}: ${msg.text()}`));
page.on("pageerror", (err) => logs.push(`pageerror: ${err.message}`));

async function clickFirst(label, locators) {
  for (const locator of locators) {
    try {
      if (await locator.count()) {
        await locator.first().click({ timeout: 8000 });
        await page.waitForTimeout(900);
        logs.push(`clicked: ${label}`);
        return true;
      }
    } catch (error) {
      logs.push(`click-failed: ${label}: ${error.message}`);
    }
  }
  logs.push(`missing-click-target: ${label}`);
  return false;
}

async function capture(name, selector = ".eiq-market-v1", fullPage = true) {
  const file = path.join(outDir, `edgeiq_market_engineering_v1_${name}.png`);
  const locator = page.locator(selector).first();
  if (await locator.count()) {
    await locator.scrollIntoViewIfNeeded({ timeout: 8000 });
    await page.waitForTimeout(350);
  } else {
    logs.push(`missing-capture-selector: ${name}: ${selector}`);
  }
  await page.screenshot({ path: file, fullPage });
  return file;
}

try {
  await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(2200);
  await clickFirst("Meetings", [
    page.getByRole("button", { name: /^meetings$/i }),
    page.getByText(/^meetings$/i),
  ]);
  await clickFirst("Open first meeting", [
    page.getByRole("button", { name: /open meeting/i }),
    page.locator(".eiq-meetings-engineering__open").first(),
    page.locator("button").filter({ hasText: /open/i }).first(),
  ]);
  await clickFirst("Open first race", [
    page.getByRole("button", { name: /open race/i }),
    page.locator("button").filter({ hasText: /open race/i }).first(),
  ]);
  await clickFirst("Market tab", [
    page.getByRole("tab", { name: /^MARKET$/i }),
    page.getByRole("button", { name: /^MARKET$/i }),
  ]);

  await capture("01_race_market");
  await capture("02_market_table", ".eiq-market-v1-table-scroll", false);

  await page.setViewportSize({ width: 1180, height: 900 });
  await page.waitForTimeout(600);
  await capture("03_narrow_desktop");

  await fs.writeFile(
    path.join(outDir, "edgeiq_market_engineering_v1_browser_notes.txt"),
    [`URL: ${baseUrl}`, "", "Console / capture notes:", ...logs].join("\n"),
    "utf8",
  );

  console.log("EDGEIQ_MARKET_ENGINEERING_V1_SCREENSHOTS_WRITTEN");
} finally {
  await browser.close();
}
