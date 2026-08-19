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

async function capture(name, selector = null, options = {}) {
  const file = path.join(outDir, `edgeiq_form_guide_engineering_v1_${name}.png`);
  if (selector) {
    const locator = page.locator(selector).first();
    if (await locator.count()) {
      await locator.scrollIntoViewIfNeeded({ timeout: 8000 });
      await page.waitForTimeout(500);
    } else {
      logs.push(`missing-capture-selector: ${name}: ${selector}`);
    }
  }
  await page.screenshot({ path: file, fullPage: options.fullPage ?? false });
  return file;
}

try {
  await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(2500);

  await clickFirst("Open Meeting", [
    page.getByRole("button", { name: /open meeting/i }),
    page.getByText(/open meeting/i),
    page.getByText(/view meeting/i),
  ]);
  await clickFirst("Open Race", [
    page.getByRole("button", { name: /open race/i }),
    page.getByText(/open race/i),
    page.locator(".eiq-race-card button"),
  ]);
  await clickFirst("Form Guide", [
    page.getByRole("button", { name: /^form guide$/i }),
    page.getByText(/^form guide$/i),
  ]);
  await page.waitForTimeout(2000);

  await capture("01_full_form_guide_field_table", ".eiq-race-form-guide", { fullPage: true });
  await capture("02_selected_active_runner", ".eiq-form-v31-runner-sheet");
  await capture("03_current_condition_matches", ".eiq-form-v31-profile-region");
  await capture("04_recent_form_full_width", ".eiq-form-v31-recent-form");

  const sectionalCell = page.locator(".eiq-form-run-table--v3 td.is-negative, .eiq-form-run-table--v3 td.is-positive").first();
  if (await sectionalCell.count()) {
    await sectionalCell.scrollIntoViewIfNeeded({ timeout: 8000 });
  }
  await capture("05_sectional_signed_values", ".eiq-form-v31-recent-form");

  const scratched = page.locator(".eiq-form-summary-table--all-runner tbody tr.is-scratched").first();
  if (await scratched.count()) {
    await scratched.scrollIntoViewIfNeeded({ timeout: 8000 });
  } else {
    logs.push("no-scratched-runner-visible-in-current-race");
  }
  await capture("06_scratched_runner_state", ".eiq-form-summary-table--all-runner");

  const unavailable = page.locator(".eiq-form-v3-metric-band .is-empty, .eiq-form-empty").first();
  if (await unavailable.count()) {
    await unavailable.scrollIntoViewIfNeeded({ timeout: 8000 });
  } else {
    logs.push("no-unavailable-metric-state-visible-in-current-race");
  }
  await capture("07_unavailable_metrics", ".eiq-form-v31-runner-sheet");

  await capture("08_fewer_than_eight_starts_or_current_runner", ".eiq-form-v31-recent-form");
  await capture("09_key_insights_supported_groups", ".eiq-form-v31-insights");

  await page.setViewportSize({ width: 1180, height: 900 });
  await page.waitForTimeout(700);
  await capture("10_narrow_desktop_table_scroll", ".eiq-race-form-guide", { fullPage: true });

  await fs.writeFile(
    path.join(outDir, "edgeiq_form_guide_engineering_v1_browser_notes.txt"),
    [`URL: ${baseUrl}`, "", "Console / capture notes:", ...logs].join("\n"),
    "utf8",
  );

  console.log("EDGEIQ_FORM_GUIDE_ENGINEERING_V1_SCREENSHOTS_WRITTEN");
} finally {
  await browser.close();
}
