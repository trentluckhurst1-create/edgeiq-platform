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
  parsed.searchParams.set("edgeiqScratchingsFixture", "1");
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

async function openScratchings(url) {
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
  await clickFirst("Scratchings tab", [page.getByRole("tab", { name: /^SCRATCHINGS$/i })]);
}

async function capture(name, selector = ".eiq-scratchings-v1", fullPage = true) {
  const file = path.join(outDir, `edgeiq_scratchings_engineering_v1_${name}.png`);
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
  await openScratchings(baseUrl);
  await capture("01_live_no_scratchings_or_current_state");
  await capture("02_live_data_freshness", ".eiq-scratchings-v1-status-card", false);

  await openScratchings(withFixture(baseUrl));
  await capture("03_fixture_summary_and_table");
  await capture("04_fixture_selected_impact_panel", ".eiq-scratchings-v1-impact", false);

  await clickFirst("Missing barrier fixture row", [
    page.locator(".eiq-scratchings-v1-table tbody tr").nth(1),
  ]);
  await capture("05_fixture_impact_unavailable_state", ".eiq-scratchings-v1-impact", false);

  await clickFirst("Emergency promoted status", [
    page.getByText("EMERGENCY PROMOTED").first(),
    page.locator(".eiq-scratchings-v1-status.is-emergency_promoted").first(),
  ]);
  await capture("06_fixture_emergency_promotion");
  await capture("07_fixture_operational_timeline", ".eiq-scratchings-v1-timeline", false);

  await fs.writeFile(
    path.join(outDir, "edgeiq_scratchings_engineering_v1_browser_notes.txt"),
    [`URL: ${baseUrl}`, "", "Console / capture notes:", ...logs].join("\n"),
    "utf8",
  );

  console.log("EDGEIQ_SCRATCHINGS_ENGINEERING_V1_SCREENSHOTS_WRITTEN");
} finally {
  await browser.close();
}
