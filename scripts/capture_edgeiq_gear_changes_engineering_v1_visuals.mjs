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

function withFixture(url) {
  const parsed = new URL(url);
  parsed.searchParams.set("edgeiqGearFixture", "1");
  return parsed.toString();
}

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

async function openGear(url) {
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });
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
  await clickFirst("Gear Changes tab", [page.getByRole("tab", { name: /^GEAR CHANGES$/i })]);
}

async function capture(name, selector = ".eiq-gear-v1", fullPage = true) {
  const file = path.join(outDir, `edgeiq_gear_changes_engineering_v1_${name}.png`);
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
  await openGear(baseUrl);
  await capture("01_live_empty_or_current_state");
  await capture("02_live_data_freshness", ".eiq-gear-v1-status-card", false);

  await openGear(withFixture(baseUrl));
  await capture("03_fixture_populated_view");
  await capture("04_fixture_first_time_gear", ".eiq-gear-v1-table-card", false);

  await clickFirst("Gear removed row", [
    page.getByText("Winkers OFF").first(),
    page.locator(".eiq-gear-v1-table tbody tr").nth(1),
  ]);
  await capture("05_fixture_gear_removed");
  await capture("06_fixture_historical_panel", ".eiq-gear-v1-history", false);

  await page.setViewportSize({ width: 1180, height: 900 });
  await page.waitForTimeout(600);
  await capture("07_narrow_desktop");

  await fs.writeFile(
    path.join(outDir, "edgeiq_gear_changes_engineering_v1_browser_notes.txt"),
    [`URL: ${baseUrl}`, "", "Console / capture notes:", ...logs].join("\n"),
    "utf8",
  );

  console.log("EDGEIQ_GEAR_CHANGES_ENGINEERING_V1_SCREENSHOTS_WRITTEN");
} finally {
  await browser.close();
}
