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

async function capture(name, selector = ".eiq-meeting-v1", fullPage = true) {
  const file = path.join(outDir, `edgeiq_meeting_detail_engineering_v1_${name}.png`);
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

  await capture("01_races_default_tab");
  await capture("02_header_condition_strip", ".eiq-meeting-v1-header");
  await capture("03_selected_race_detail", ".eiq-meeting-v1-panel");
  await capture("04_operational_rail", ".eiq-meeting-v1-rail");

  for (const [name, label] of [
    ["05_scratchings_pending", "SCRATCHINGS"],
    ["06_gear_changes_pending", "GEAR CHANGES"],
    ["07_track_pending", "TRACK"],
    ["08_weather_pending", "WEATHER"],
    ["09_results_pending", "RESULTS"],
  ]) {
    await clickFirst(label, [page.getByRole("tab", { name: label })]);
    await capture(name);
  }

  await clickFirst("Back to meetings", [
    page.getByRole("button", { name: /^meetings$/i }).first(),
  ]);
  await capture("10_back_to_meetings_context", ".eiq-meetings-engineering", true);

  await clickFirst("Open first meeting again", [
    page.getByRole("button", { name: /open meeting/i }),
    page.locator(".eiq-meetings-engineering__open").first(),
    page.locator("button").filter({ hasText: /open/i }).first(),
  ]);
  await page.setViewportSize({ width: 1180, height: 900 });
  await page.waitForTimeout(700);
  await capture("11_narrow_desktop");

  await fs.writeFile(
    path.join(outDir, "edgeiq_meeting_detail_engineering_v1_browser_notes.txt"),
    [`URL: ${baseUrl}`, "", "Console / capture notes:", ...logs].join("\n"),
    "utf8",
  );

  console.log("EDGEIQ_MEETING_DETAIL_ENGINEERING_V1_SCREENSHOTS_WRITTEN");
} finally {
  await browser.close();
}
