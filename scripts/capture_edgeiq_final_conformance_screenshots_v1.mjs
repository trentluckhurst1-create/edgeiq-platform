import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const root = process.cwd();
const outDir = path.join(root, "docs", "full-product-implementation", "screenshots", "final-conformance");
const baseUrl = process.env.EDGEIQ_BASE_URL || "http://127.0.0.1:5177/";

async function ensureDir(dir) {
  await fs.mkdir(dir, { recursive: true });
}

function safeName(name) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

async function visibleText(page) {
  return page.evaluate(() => {
    const text = document.body?.innerText || "";
    return text.replace(/\s+/g, " ").trim().slice(0, 12000);
  });
}

async function capture(page, name, route, notes = []) {
  const fileName = `${safeName(name)}.png`;
  const filePath = path.join(outDir, fileName);
  await page.screenshot({ path: filePath, fullPage: true });
  return {
    name,
    status: "CAPTURED",
    route,
    path: filePath,
    viewport: page.viewportSize(),
    headings: await page.locator("h1,h2,h3,strong").evaluateAll((nodes) =>
      nodes.slice(0, 40).map((node) => (node.textContent || "").trim()).filter(Boolean),
    ).catch(() => []),
    tableHeaders: await page.locator("th").evaluateAll((nodes) =>
      nodes.slice(0, 80).map((node) => (node.textContent || "").trim()).filter(Boolean),
    ).catch(() => []),
    notes,
  };
}

async function tryClick(page, label, options = {}) {
  const exact = options.exact ?? true;
  const timeout = options.timeout ?? 2500;
  const candidates = [
    page.getByRole("button", { name: label, exact }),
    page.getByRole("link", { name: label, exact }),
    page.getByText(label, { exact }),
  ];
  for (const candidate of candidates) {
    try {
      const count = await candidate.count();
      if (count > 0) {
        await candidate.first().click({ timeout });
        await page.waitForTimeout(options.wait ?? 500);
        return true;
      }
    } catch {
      // try next selector
    }
  }
  return false;
}

async function clickFirstByText(page, regex, wait = 500) {
  try {
    const locator = page.getByText(regex);
    if ((await locator.count()) > 0) {
      await locator.first().click({ timeout: 2500 });
      await page.waitForTimeout(wait);
      return true;
    }
  } catch {
    // caller records failure
  }
  return false;
}

async function selectMeetingAndRace(page, evidence) {
  await tryClick(page, "MEETINGS");
  await tryClick(page, "TOMORROW");

  let meetingOpened = false;
  try {
    const flemingtonRow = page.locator("tr", { hasText: /Flemington/i }).first();
    if ((await flemingtonRow.count()) > 0) {
      const rowButton = flemingtonRow.locator("button").last();
      if ((await rowButton.count()) > 0) {
        await rowButton.click({ timeout: 2500 });
        await page.waitForTimeout(600);
        meetingOpened = true;
      }
    }
  } catch {
    meetingOpened = false;
  }
  if (!meetingOpened) {
    meetingOpened =
      (await clickFirstByText(page, /Open Meeting|VIEW MEETING|View Meeting/i)) ||
      (await clickFirstByText(page, /Flemington|Geelong|Ballarat|Caulfield/i));
  }
  if (!meetingOpened) {
    evidence.push({ name: "meeting-select", status: "NOT_TESTED", reason: "No meeting open control found", text: await visibleText(page) });
    return false;
  }

  let raceOpened = false;
  try {
    const raceRow = page.locator("tr", { hasText: /\bR1\b/i }).first();
    if ((await raceRow.count()) > 0) {
      const rowButton = raceRow.locator("button").last();
      if ((await rowButton.count()) > 0) {
        await rowButton.click({ timeout: 2500 });
        await page.waitForTimeout(700);
        raceOpened = true;
      }
    }
  } catch {
    raceOpened = false;
  }
  if (!raceOpened) {
    raceOpened =
      (await clickFirstByText(page, /Open Race|VIEW RACE|View Race/i)) ||
      (await tryClick(page, "R1")) ||
      (await clickFirstByText(page, /^R1\b/i));
  }
  if (!raceOpened) {
    evidence.push({ name: "race-select", status: "NOT_TESTED", reason: "No race open control found", text: await visibleText(page) });
    return false;
  }
  return true;
}

async function main() {
  await ensureDir(outDir);
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  const evidence = [];

  try {
    await page.goto(baseUrl, { waitUntil: "networkidle", timeout: 60000 });
    await tryClick(page, "HOME");
    evidence.push(await capture(page, "HOME", baseUrl));

    await tryClick(page, "MEETINGS");
    evidence.push(await capture(page, "MEETINGS", baseUrl));

    const raceReady = await selectMeetingAndRace(page, evidence);
    evidence.push(await capture(page, "MEETING DETAIL", baseUrl, [raceReady ? "Meeting/race selection attempted through visible controls." : "Meeting/race selection incomplete."]));

    const meetingTabs = [
      "SCRATCHINGS",
      "GEAR CHANGES",
      "TRACK",
      "WEATHER",
    ];
    for (const tab of meetingTabs) {
      await tryClick(page, "MEETINGS");
      await clickFirstByText(page, /Open Meeting|VIEW MEETING|View Meeting/i);
      const clicked = await tryClick(page, tab) || await clickFirstByText(page, new RegExp(tab.replace(/\s+/g, "\\s+"), "i"));
      evidence.push(await capture(page, tab, baseUrl, [clicked ? "Tab opened." : "Tab control not found; captured current visible state."]));
    }

    await selectMeetingAndRace(page, evidence);
    const raceTabs = [
      "RACE",
      "FIELD",
      "FORM GUIDE",
      "PERFORMANCE",
      "EPI",
      "MAP",
      "MARKET",
      "OVERVIEW",
      "INSIGHTS",
    ];
    for (const tab of raceTabs) {
      const clicked = await tryClick(page, tab);
      evidence.push(await capture(page, tab, baseUrl, [clicked ? "Workspace opened." : "Workspace control not found; captured current visible state."]));
      if (tab === "FIELD") {
        await clickFirstByText(page, /[A-Z][A-Z '\-]+/);
        evidence.push(await capture(page, "FIELD expanded", baseUrl, ["Attempted first visible runner expansion/open."]));
      }
      if (tab === "FORM GUIDE") {
        await clickFirstByText(page, /[A-Z][A-Z '\-]+/);
        evidence.push(await capture(page, "FORM GUIDE expanded", baseUrl, ["Attempted first visible runner expansion/open."]));
      }
    }

    await tryClick(page, "RESULTS");
    evidence.push(await capture(page, "RESULTS", baseUrl));
    await clickFirstByText(page, /Open|View|R1|Race/i);
    evidence.push(await capture(page, "RESULTS expanded", baseUrl, ["Attempted first result expansion."]));

    await tryClick(page, "LAB");
    await tryClick(page, "Run Query", { exact: false });
    evidence.push(await capture(page, "LAB", baseUrl));
    evidence.push(await capture(page, "LAB query result", baseUrl));

    await tryClick(page, "COMPARE");
    evidence.push(await capture(page, "COMPARE", baseUrl));

    await tryClick(page, "REVIEW");
    evidence.push(await capture(page, "REVIEW", baseUrl));

    await tryClick(page, "SETTINGS");
    evidence.push(await capture(page, "SETTINGS", baseUrl));

    await fs.writeFile(
      path.join(outDir, "screenshot_evidence_v1.json"),
      JSON.stringify({ baseUrl, generatedAt: new Date().toISOString(), evidence }, null, 2),
      "utf-8",
    );
  } finally {
    await browser.close();
  }

  console.log(`EDGEIQ_FINAL_CONFORMANCE_SCREENSHOTS_CAPTURED ${evidence.length}`);
}

main().catch(async (error) => {
  await ensureDir(outDir);
  await fs.writeFile(
    path.join(outDir, "screenshot_failure_v1.json"),
    JSON.stringify({
      baseUrl,
      generatedAt: new Date().toISOString(),
      attemptedApi: "playwright.chromium.launch().newPage().screenshot({ path, fullPage: true })",
      error: error instanceof Error ? error.stack : String(error),
    }, null, 2),
    "utf-8",
  );
  console.error(error);
  process.exit(1);
});
