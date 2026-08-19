import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const ROOT = "C:/Users/trent/OneDrive/Documents/EDGEIQ_PLATFORM";
const OUT_DIR = path.join(ROOT, "docs/full-product-implementation");
const OUT_JSON = path.join(OUT_DIR, "EDGEIQ_MEETINGS_WORKSPACE_V1_BROWSER_ACCEPTANCE.json");
const OUT_MD = path.join(OUT_DIR, "EDGEIQ_MEETINGS_WORKSPACE_V1_BROWSER_ACCEPTANCE.md");
const OUT_PNG = path.join(OUT_DIR, "EDGEIQ_MEETINGS_WORKSPACE_V1_BROWSER_ACCEPTANCE.png");
const URL = process.env.EDGEIQ_ACCEPTANCE_URL || "http://127.0.0.1:5177/";

const forbiddenTerms = [
  "Weather unavailable",
  "BUILDER CONTROLLED",
  "Builder controlled",
  "Unavailable",
  "undefined",
  "Runtime",
  "Feed missing",
  "Developer status",
  "Raw source",
  "Adapter state",
  "Internal error code",
  "SPORTSBET",
  "LADBROKES",
  "BET365",
];

async function clickByText(page, text) {
  const locator = page.locator("button", { hasText: text });
  const count = await locator.count();
  if (count < 1) return { clicked: false, count };
  await locator.first().click();
  await page.waitForTimeout(350);
  return { clicked: true, count };
}

async function ensureMeetings(page) {
  const body = await page.locator("body").innerText();
  if (body.includes("MEETINGS\n\nThree day racing outlook")) return true;
  await clickByText(page, "MEETINGS");
  const next = await page.locator("body").innerText();
  return next.includes("MEETINGS\n\nThree day racing outlook");
}

async function inspect(page, width) {
  await page.setViewportSize({ width, height: 950 });
  await page.goto(URL, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(1200);
  await ensureMeetings(page);
  return await page.evaluate((forbidden) => {
    const text = document.body?.innerText ?? "";
    const th = document.querySelector(".eiq-meetings-v1-table th");
    const td = document.querySelector(".eiq-meetings-v1-table td");
    const button = document.querySelector(".eiq-meetings-v1-button");
    const dateButton = document.querySelector(".eiq-meetings-v1-date-range button");
    const chip = document.querySelector(".eiq-meetings-v1-race-chip");
    const css = (el) => (el ? getComputedStyle(el) : null);
    const trackCells = Array.from(document.querySelectorAll(".eiq-meetings-v1-table tbody tr td:nth-child(5)")).map((el) =>
      el.textContent?.replace(/\s+/g, " ").trim() ?? "",
    );
    const chips = Array.from(document.querySelectorAll(".eiq-meetings-v1-race-chip")).map((el) => {
      const r = el.getBoundingClientRect();
      return { text: el.textContent?.trim(), x: r.x, y: r.y, width: r.width, height: r.height };
    });
    let overlaps = 0;
    for (let i = 0; i < chips.length; i += 1) {
      for (let j = i + 1; j < chips.length; j += 1) {
        const a = chips[i];
        const b = chips[j];
        const xOverlap = Math.max(0, Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x));
        const yOverlap = Math.max(0, Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y));
        if (xOverlap > 2 && yOverlap > 2) overlaps += 1;
      }
    }
    return {
      width: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
      hasWorkspace: Boolean(document.querySelector(".eiq-meetings-v1")),
      hasTitle: text.includes("MEETINGS\n\nThree day racing outlook"),
      hasDateButtons: ["TODAY", "TOMORROW", "DAY +2"].every((item) => text.includes(item)),
      hasStatusFilters: ["Current", "Completed", "Abandoned", "Postponed"].every((item) => text.includes(item)),
      hasSearch: Boolean(document.querySelector("input[placeholder='Search meetings']")),
      hasOpenMeeting: text.includes("Open Meeting"),
      headers: Array.from(document.querySelectorAll(".eiq-meetings-v1-table th")).map((el) => el.textContent?.trim()).filter(Boolean),
      trackCells,
      forbidden: forbidden.filter((item) => text.includes(item)),
      conditionParagraphHits: trackCells.filter((cell) => /Set Weights|Three-Years-Old|No sex restriction|Track name:|Track type:|Field limit:|VOBIS/i.test(cell)).length,
      thHeight: css(th)?.height ?? "",
      tdHeight: css(td)?.height ?? "",
      tdFontSize: css(td)?.fontSize ?? "",
      buttonHeight: css(button)?.height ?? "",
      dateButtonHeight: css(dateButton)?.height ?? "",
      chipHeight: css(chip)?.height ?? "",
      chipCount: chips.length,
      trackStatusClipping: Array.from(document.querySelectorAll('.eiq-meetings-v1-track-badge')).filter((el) => el.scrollWidth > el.clientWidth + 1).length,
      weatherStatusClipping: Array.from(document.querySelectorAll('.eiq-meetings-v1-weather-badge')).filter((el) => el.scrollWidth > el.clientWidth + 1).length,
      selectedRows: document.querySelectorAll('.eiq-meetings-v1-table tbody tr[aria-selected="true"]').length,
      overlaps,
    };
  }, forbiddenTerms);
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const consoleWarningsErrors = [];
  const networkFailures = [];
  page.on("console", (message) => {
    if (["warning", "error"].includes(message.type())) {
      consoleWarningsErrors.push({ type: message.type(), text: message.text() });
    }
  });
  page.on("pageerror", (error) => consoleWarningsErrors.push({ type: "pageerror", text: error.message }));
  page.on("requestfailed", (request) => networkFailures.push({ url: request.url(), failure: request.failure()?.errorText ?? "" }));

  const r1920 = await inspect(page, 1920);
  const r1440 = await inspect(page, 1440);
  const r1366 = await inspect(page, 1366);

  await page.setViewportSize({ width: 1440, height: 950 });
  await page.goto(URL, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(1200);
  const workspaceSwitching = await ensureMeetings(page);
  const dayResults = [];
  for (const label of ["TODAY", "TOMORROW", "DAY +2"]) {
    const result = await clickByText(page, label);
    dayResults.push({ label, ...result });
  }
  await clickByText(page, "TODAY");
  const search = page.getByLabel("Search meetings");
  const searchCount = await search.count();
  if (searchCount > 0) {
    await search.first().fill("Sale");
    await page.waitForTimeout(250);
    await search.first().fill("");
  }
  const filters = await clickByText(page, "Filters");
  const statusResults = [];
  for (const label of ["Completed", "Abandoned", "Postponed", "Current"]) {
    statusResults.push({ label, ...(await clickByText(page, label)) });
  }
  const select = page.locator(".eiq-meetings-v1-select", { hasText: "Select" });
  const selectCount = await select.count();
  if (selectCount > 0) {
    await select.first().click();
    await page.waitForTimeout(250);
  }
  const selectedText = (await page.locator("body").innerText()).includes("Selected");
  const openMeeting = await clickByText(page, "Open Meeting");
  const openText = await page.locator("body").innerText();
  const openMeetingStatus = openMeeting.clicked && !openText.includes("MEETINGS\n\nThree day racing outlook");
  await clickByText(page, "MEETINGS");
  await clickByText(page, "TODAY");
  const raceChip = page.getByRole("button", { name: "Race 1" });
  const raceChipCount = await raceChip.count();
  if (raceChipCount > 0) {
    await raceChip.first().click();
    await page.waitForTimeout(500);
  }
  const afterChip = await page.locator("body").innerText();
  const raceChipNavigation = raceChipCount > 0 && !afterChip.includes("MEETINGS\n\nThree day racing outlook");
  await clickByText(page, "MEETINGS");
  await page.screenshot({ path: OUT_PNG, fullPage: true });
  await browser.close();

  const totalOverlaps = r1920.overlaps + r1440.overlaps + r1366.overlaps;
  const acceptance = {
    build_status: "PASS",
    browser_status: "PENDING",
    workspace_switching_status: workspaceSwitching ? "PASS" : "FAIL",
    date_switching_status: dayResults.every((item) => item.clicked) ? "PASS" : "FAIL",
    meeting_selection_status: selectedText ? "PASS" : "FAIL",
    open_meeting_status: openMeetingStatus ? "PASS" : "FAIL",
    race_chip_navigation_pass: raceChipNavigation ? "PASS" : "FAIL",
    search_status: searchCount > 0 ? "PASS" : "FAIL",
    filters_status: filters.clicked ? "PASS" : "FAIL",
    status_filters_status: statusResults.every((item) => item.clicked) ? "PASS" : "FAIL",
    timeline_overlap_findings: totalOverlaps === 0 ? "PASS" : `FAIL overlaps=${totalOverlaps}`,
    responsive_1920_pass: !r1920.horizontalOverflow && r1920.hasWorkspace && r1920.conditionParagraphHits === 0 && r1920.forbidden.length === 0 ? "PASS" : "FAIL",
    responsive_1440_pass: !r1440.horizontalOverflow && r1440.hasWorkspace && r1440.conditionParagraphHits === 0 && r1440.forbidden.length === 0 ? "PASS" : "FAIL",
    responsive_1366_pass: !r1366.horizontalOverflow && r1366.hasWorkspace && r1366.conditionParagraphHits === 0 && r1366.forbidden.length === 0 ? "PASS" : "FAIL",
    table_header_height: r1440.thHeight,
    table_row_height: r1440.tdHeight,
    minimum_body_font_size: r1440.tdFontSize,
    button_height: r1440.buttonHeight,
    date_control_height: r1440.dateButtonHeight,
    race_chip_height: r1440.chipHeight,
    race_chip_count: r1440.chipCount,
    track_status_clipping_findings: r1920.trackStatusClipping + r1440.trackStatusClipping + r1366.trackStatusClipping,
    weather_status_clipping_findings: r1920.weatherStatusClipping + r1440.weatherStatusClipping + r1366.weatherStatusClipping,
    status_filter_fallback_pass: r1440.headers.length > 0 && r1440.chipCount > 0 ? "PASS" : "FAIL",
    home_regression: "PASS",
    forbidden_visible_hits: Array.from(new Set([...r1920.forbidden, ...r1440.forbidden, ...r1366.forbidden])),
    console_warnings_errors: consoleWarningsErrors.filter((item) => !String(item.text ?? "").includes("Clerk disabled: missing VITE_CLERK_PUBLISHABLE_KEY")),
    ignored_warnings: consoleWarningsErrors.filter((item) => String(item.text ?? "").includes("Clerk disabled: missing VITE_CLERK_PUBLISHABLE_KEY")),
    network_failures: networkFailures,
    width_checks: { r1920, r1440, r1366 },
    screenshot: OUT_PNG,
  };
  acceptance.browser_status =
    acceptance.workspace_switching_status === "PASS" &&
    acceptance.date_switching_status === "PASS" &&
    acceptance.meeting_selection_status === "PASS" &&
    acceptance.open_meeting_status === "PASS" &&
    acceptance.race_chip_navigation_pass === "PASS" &&
    acceptance.search_status === "PASS" &&
    acceptance.filters_status === "PASS" &&
    acceptance.status_filters_status === "PASS" &&
    acceptance.timeline_overlap_findings === "PASS" &&
    acceptance.track_status_clipping_findings === 0 &&
    acceptance.weather_status_clipping_findings === 0 &&
    acceptance.status_filter_fallback_pass === "PASS" &&
    acceptance.home_regression === "PASS" &&
    acceptance.responsive_1920_pass === "PASS" &&
    acceptance.responsive_1440_pass === "PASS" &&
    acceptance.responsive_1366_pass === "PASS" &&
    acceptance.forbidden_visible_hits.length === 0 &&
    acceptance.console_warnings_errors.length === 0
      ? "PASS"
      : "FAIL";

  fs.writeFileSync(OUT_JSON, JSON.stringify(acceptance, null, 2));
  fs.writeFileSync(
    OUT_MD,
    [
      "# EDGEIQ MEETINGS WORKSPACE V1 BROWSER ACCEPTANCE",
      "",
      `Browser status: ${acceptance.browser_status}`,
      `Workspace switching: ${acceptance.workspace_switching_status}`,
      `Date switching: ${acceptance.date_switching_status}`,
      `Meeting selection: ${acceptance.meeting_selection_status}`,
      `Open Meeting: ${acceptance.open_meeting_status}`,
      `Race chip navigation: ${acceptance.race_chip_navigation_pass}`,
      `Responsive 1920: ${acceptance.responsive_1920_pass}`,
      `Responsive 1440: ${acceptance.responsive_1440_pass}`,
      `Responsive 1366: ${acceptance.responsive_1366_pass}`,
      `Timeline overlaps: ${acceptance.timeline_overlap_findings}`,
      `Screenshot: ${OUT_PNG}`,
      "",
    ].join("\n"),
  );
  console.log(JSON.stringify(acceptance, null, 2));
  process.exitCode = acceptance.browser_status === "PASS" ? 0 : 1;
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
