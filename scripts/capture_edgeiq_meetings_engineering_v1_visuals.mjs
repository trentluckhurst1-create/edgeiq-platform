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
        await locator.first().click({ timeout: 7000 });
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

async function capture(name, selector = null, fullPage = false) {
  const file = path.join(outDir, `edgeiq_meetings_engineering_v1_${name}.png`);
  if (selector) {
    const locator = page.locator(selector).first();
    if (await locator.count()) {
      await locator.scrollIntoViewIfNeeded({ timeout: 8000 });
      await page.waitForTimeout(400);
    } else {
      logs.push(`missing-capture-selector: ${name}: ${selector}`);
    }
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

  await capture("01_today_full_workspace", ".eiq-meetings-engineering", true);

  await clickFirst("Tomorrow", [
    page.getByRole("button", { name: /tomorrow/i }),
    page.locator(".eiq-meetings-engineering__days button").nth(1),
  ]);
  await capture("02_tomorrow_workspace", ".eiq-meetings-engineering", true);

  await clickFirst("Day plus two", [
    page.getByRole("button", { name: /day \+2/i }),
    page.locator(".eiq-meetings-engineering__days button").nth(2),
  ]);
  await capture("03_day_plus_2_workspace", ".eiq-meetings-engineering", true);

  await clickFirst("Select second meeting", [
    page.locator(".eiq-meetings-engineering__select").nth(1),
  ]);
  await capture("04_selected_meeting_rail", ".eiq-meetings-engineering__grid");
  await capture("05_race_strip", ".eiq-meetings-engineering__race-strip");

  await page.setViewportSize({ width: 1180, height: 900 });
  await page.waitForTimeout(700);
  await capture("06_narrow_desktop", ".eiq-meetings-engineering", true);

  await fs.writeFile(
    path.join(outDir, "edgeiq_meetings_engineering_v1_browser_notes.txt"),
    [`URL: ${baseUrl}`, "", "Console / capture notes:", ...logs].join("\n"),
    "utf8",
  );

  console.log("EDGEIQ_MEETINGS_ENGINEERING_V1_SCREENSHOTS_WRITTEN");
} finally {
  await browser.close();
}
