import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const ROOT = "C:/Users/trent/OneDrive/Documents/EDGEIQ_PLATFORM";
const DOCS = path.join(ROOT, "docs/full-product-implementation");
const URL = process.env.EDGEIQ_ACCEPTANCE_URL || "http://127.0.0.1:4179/";
const viewports = [
  { name: "1920", width: 1920, height: 1080 },
  { name: "1600", width: 1600, height: 900 },
  { name: "1440", width: 1440, height: 900 },
  { name: "1366", width: 1366, height: 768 },
];
const tabs = ["FIELD", "FORM GUIDE", "PERFORMANCE", "MAP", "MARKET", "OVERVIEW", "INSIGHTS", "EPI", "RESULTS", "REVIEW", "RACE"];
const forbiddenVisible = ["Unavailable", "Builder", "Runtime", "Internal", "Feed missing", "Raw", "Null", "Undefined", "Adapter", "Developer", "Book Now", "Bet Now"];
const knownConsole = ["Clerk disabled: missing VITE_CLERK_PUBLISHABLE_KEY"];

function cleanConsole(messages) {
  return messages.filter((item) => !knownConsole.some((known) => item.text.includes(known)));
}

async function bodyText(page) {
  return (await page.locator("body").innerText({ timeout: 15000 })).replace(/\s+/g, " ").trim();
}

async function firstVisible(locator) {
  const count = await locator.count();
  for (let index = 0; index < count; index += 1) {
    const item = locator.nth(index);
    if (await item.isVisible().catch(() => false)) return item;
  }
  return null;
}

async function enterMeetings(page) {
  await page.goto(URL, { waitUntil: "networkidle", timeout: 60000 });
  const viewMeetings = await firstVisible(page.getByRole("button", { name: /View Meetings/i }));
  if (viewMeetings) await viewMeetings.click();
  await page.getByRole("button", { name: /^MEETINGS$/ }).click({ timeout: 15000 }).catch(() => {});
  await page.waitForSelector('[data-edgeiq-workspace-key="MEETINGS"], .eiq-meetings-v1', { timeout: 20000 });
}

async function openRaceFromMeetings(page, raceNo) {
  const chip = await firstVisible(page.getByRole("button", { name: new RegExp(`^Race ${raceNo}$`, "i") }));
  if (!chip) return false;
  await chip.click();
  await page.waitForSelector('[data-edgeiq-race-workspace-v1="locked"]', { timeout: 20000 });
  return true;
}

async function clickRaceSelector(page, raceNo) {
  const buttons = page.locator(".eiq-race-v1__selector button");
  const count = await buttons.count();
  let selector = null;
  for (let index = 0; index < count; index += 1) {
    const button = buttons.nth(index);
    const text = await button.innerText().catch(() => "");
    if (text.trim().toUpperCase().startsWith(`R${raceNo}`)) {
      selector = button;
      break;
    }
  }
  if (!selector) return false;
  await selector.click();
  await page.waitForTimeout(700);
  return true;
}

async function raceSnapshot(page) {
  const title = await page.locator(".eiq-race-v1__identity h1").first().innerText().catch(() => "");
  const rows = await page.locator(".eiq-race-v1__table tbody tr").count().catch(() => 0);
  const activeTab = await page.locator(".eiq-context-tabs button.is-active").first().innerText().catch(() => "");
  const text = await bodyText(page);
  return {
    title,
    rows,
    activeTab,
    forbiddenHits: forbiddenVisible.filter((word) => text.includes(word)),
    hasRunnerBoard: text.includes("RUNNER BOARD"),
    hasEpiTop3: text.includes("EPI TOP 3"),
    hasSpeedMap: text.includes("SPEED MAP PREVIEW"),
  };
}

async function viewportCheck(page, viewport) {
  await page.setViewportSize({ width: viewport.width, height: viewport.height });
  await page.waitForTimeout(300);
  const metrics = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    brokenImages: Array.from(document.images).filter((img) => img.complete && img.naturalWidth === 0).length,
    raceCardCount: document.querySelectorAll(".eiq-race-v1__summary-card").length,
    tableHeaderHeight: getComputedStyle(document.querySelector(".eiq-race-v1__table thead th") || document.body).height,
    tableRowHeight: getComputedStyle(document.querySelector(".eiq-race-v1__table tbody td") || document.body).height,
  }));
  const screenshot = path.join(DOCS, `EDGEIQ_RACE_WORKSPACE_V1_${viewport.name}.png`);
  await page.screenshot({ path: screenshot, fullPage: true });
  return {
    viewport: viewport.name,
    horizontalOverflow: metrics.scrollWidth > metrics.clientWidth + 2,
    brokenImages: metrics.brokenImages,
    raceCardCount: metrics.raceCardCount,
    tableHeaderHeight: metrics.tableHeaderHeight,
    tableRowHeight: metrics.tableRowHeight,
    screenshot,
    pass: metrics.scrollWidth <= metrics.clientWidth + 2 && metrics.brokenImages === 0 && metrics.raceCardCount === 4,
  };
}

async function main() {
  fs.mkdirSync(DOCS, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const consoleMessages = [];
  const pageErrors = [];
  const networkFailures = [];
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) consoleMessages.push({ type: message.type(), text: message.text() });
  });
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("requestfailed", (request) => {
    if (!request.url().startsWith("data:")) networkFailures.push({ url: request.url(), error: request.failure()?.errorText || "" });
  });

  await enterMeetings(page);
  const meetingsText = await bodyText(page);
  const meetingsRegression = meetingsText.includes("MEETINGS") && meetingsText.includes("Open Meeting");
  const raceOpened = await openRaceFromMeetings(page, 1);
  const firstRace = await raceSnapshot(page);

  const raceSnapshots = [firstRace];
  const raceSelectorEvidence = {
    count: await page.locator(".eiq-race-v1__selector button").count().catch(() => 0),
    text: await page.locator(".eiq-race-v1__selector").innerText().catch(() => ""),
  };
  for (const raceNo of [2, 3]) {
    if (await clickRaceSelector(page, raceNo)) raceSnapshots.push(await raceSnapshot(page));
  }

  const workspaceTabs = {};
  for (const tab of tabs) {
    const button = await firstVisible(page.getByRole("button", { name: new RegExp(`^${tab}$`, "i") }));
    if (!button) {
      workspaceTabs[tab] = "MISSING";
      continue;
    }
    await button.click();
    await page.waitForTimeout(700);
    workspaceTabs[tab] = await page.locator("[data-edgeiq-workspace-key]").first().getAttribute("data-edgeiq-workspace-key").catch(() => "");
  }

  const back = await firstVisible(page.getByRole("button", { name: /Back to Races/i }));
  let backToRaces = false;
  if (back) {
    await back.click();
    await page.waitForTimeout(700);
    backToRaces = (await bodyText(page)).includes("RACES") || (await bodyText(page)).includes("MEETING");
    await page.getByRole("button", { name: /^RACE$/ }).click({ timeout: 10000 }).catch(() => {});
    await page.waitForSelector('[data-edgeiq-race-workspace-v1="locked"]', { timeout: 15000 }).catch(() => {});
  }

  const viewportResults = [];
  for (const viewport of viewports) viewportResults.push(await viewportCheck(page, viewport));

  await page.getByRole("button", { name: /^HOME$/ }).click({ timeout: 10000 }).catch(() => {});
  await page.waitForTimeout(700);
  const homeRegression = (await bodyText(page)).includes("EDGEiQ");
  await browser.close();

  const filteredConsole = cleanConsole(consoleMessages);
  const uniqueRaceTitles = new Set(raceSnapshots.map((item) => item.title).filter(Boolean));
  const result = {
    url: URL,
    browser_status: "PASS",
    race_opened: raceOpened,
    races_tested: raceSnapshots.length,
    unique_race_titles: uniqueRaceTitles.size,
    race_switching_status: raceSnapshots.length >= 3 && uniqueRaceTitles.size >= 3 ? "PASS" : "WARN",
    workspace_switching_status: Object.values(workspaceTabs).every((value) => value && value !== "MISSING") ? "PASS" : "FAIL",
    workspace_tabs: workspaceTabs,
    back_to_races_status: backToRaces ? "PASS" : "FAIL",
    race_snapshots: raceSnapshots,
    race_selector_evidence: raceSelectorEvidence,
    forbidden_visible_hits: [...new Set(raceSnapshots.flatMap((item) => item.forbiddenHits))],
    page_errors: pageErrors,
    console_messages: filteredConsole,
    known_console_messages: consoleMessages.filter((item) => knownConsole.some((known) => item.text.includes(known))),
    network_failures: networkFailures,
    viewport_results: viewportResults,
    responsive_all_pass: viewportResults.every((item) => item.pass) ? "PASS" : "FAIL",
    home_regression_status: homeRegression ? "PASS" : "FAIL",
    meetings_regression_status: meetingsRegression ? "PASS" : "FAIL",
  };
  result.overall_status =
    result.race_opened &&
    result.workspace_switching_status === "PASS" &&
    result.back_to_races_status === "PASS" &&
    result.forbidden_visible_hits.length === 0 &&
    result.page_errors.length === 0 &&
    result.console_messages.length === 0 &&
    result.network_failures.length === 0 &&
    result.responsive_all_pass === "PASS" &&
    result.home_regression_status === "PASS" &&
    result.meetings_regression_status === "PASS"
      ? "PASS"
      : "FAIL";

  fs.writeFileSync(path.join(DOCS, "EDGEIQ_RACE_WORKSPACE_V1_BROWSER_ACCEPTANCE.json"), JSON.stringify(result, null, 2));
  const markdown = [
    "# EDGEiQ Race Workspace V1 Browser Acceptance",
    "",
    `Overall status: **${result.overall_status}**`,
    `Races tested: ${result.races_tested}`,
    `Race switching: ${result.race_switching_status}`,
    `Workspace switching: ${result.workspace_switching_status}`,
    `Back to Races: ${result.back_to_races_status}`,
    `Responsive: ${result.responsive_all_pass}`,
    `Home regression: ${result.home_regression_status}`,
    `Meetings regression: ${result.meetings_regression_status}`,
    `Console messages: ${result.console_messages.length}`,
    `Known unrelated console messages: ${result.known_console_messages.length}`,
    `Page errors: ${result.page_errors.length}`,
    `Network failures: ${result.network_failures.length}`,
    "",
  ].join("\n");
  fs.writeFileSync(path.join(DOCS, "EDGEIQ_RACE_WORKSPACE_V1_BROWSER_ACCEPTANCE.md"), markdown);
  console.log(JSON.stringify(result, null, 2));
  if (result.overall_status !== "PASS") process.exitCode = 1;
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
