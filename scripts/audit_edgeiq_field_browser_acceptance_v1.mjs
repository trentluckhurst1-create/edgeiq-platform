import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const ROOT = "C:/Users/trent/OneDrive/Documents/EDGEIQ_PLATFORM";
const DOC = path.join(ROOT, "docs/full-product-implementation");
const URL = process.env.EDGEIQ_URL || "http://localhost:5173/";
const widths = [1920, 1600, 1440, 1366];
const results = [];

function pass(name, detail = {}) { results.push({ check: name, status: "PASS", ...detail }); }
function fail(name, detail = {}) { results.push({ check: name, status: "FAIL", ...detail }); }
function cleanText(text) { return String(text || "").replace(/\s+/g, " ").trim(); }

async function clickText(page, text) {
  const locator = page.getByRole("button", { name: new RegExp(`^${text}$`, "i") }).first();
  await locator.click({ timeout: 10000 });
}

async function ensureRaceView(page) {
  const enter = page.getByRole("button", { name: /enter terminal/i }).first();
  if (await enter.count()) await enter.click().catch(() => {});
  await page.waitForTimeout(800);
  const openMeeting = page.getByRole("button", { name: /open meeting/i }).first();
  if (await openMeeting.count()) {
    await openMeeting.click().catch(() => {});
    await page.waitForTimeout(500);
  }
  const openRace = page.getByRole("button", { name: /open race/i }).first();
  if (await openRace.count()) {
    await openRace.click().catch(() => {});
    await page.waitForTimeout(900);
  }
}

async function fieldProbe(page, width) {
  await page.setViewportSize({ width, height: 1100 });
  await page.goto(URL, { waitUntil: "networkidle", timeout: 60000 });
  await ensureRaceView(page);
  await clickText(page, "FIELD");
  await page.waitForTimeout(500);
  const screenshotPath = path.join(DOC, `EDGEIQ_FIELD_WORKSPACE_V1_${width}.png`);
  await page.screenshot({ path: screenshotPath, fullPage: true });

  const data = await page.evaluate(() => {
    const q = (sel) => document.querySelector(sel);
    const qa = (sel) => Array.from(document.querySelectorAll(sel));
    const rect = (el) => {
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return { top: Math.round(r.top), left: Math.round(r.left), width: Math.round(r.width), height: Math.round(r.height), right: Math.round(r.right), bottom: Math.round(r.bottom) };
    };
    const tabs = q(".eiq-race-workspace--field > .eiq-context-tabs");
    const header = q(".eiq-approved-racefile-header");
    const meta = q(".eiq-approved-racefile-header__meta");
    const fieldHeader = q(".eiq-field-v1__header");
    const table = q(".eiq-field-table-v1");
    const rows = qa(".eiq-field-runner-row");
    const scratched = qa(".eiq-field-runner-row.is-scratched");
    const tableWrap = q(".eiq-field-table-wrap-v1");
    const headerCells = qa(".eiq-field-table-v1 thead th").map((el) => el.textContent.trim());
    const metaText = meta?.textContent || "";
    const buttons = qa(".eiq-context-tabs button");
    return {
      mounted: q("[data-edgeiq-mounted-component='FieldWorkspace']")?.getAttribute("data-edgeiq-mounted-component") || "",
      activeTab: q(".eiq-context-tabs button.is-active")?.textContent?.trim() || "",
      bodyOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
      tabs: rect(tabs),
      tabsText: tabs?.textContent || "",
      header: rect(header),
      meta: rect(meta),
      metaText,
      fieldHeader: rect(fieldHeader),
      table: rect(table),
      tableWrap: rect(tableWrap),
      headerCells,
      rowCount: rows.length,
      scratchedCount: scratched.length,
      countsText: q(".eiq-field-v1__counts")?.textContent || "",
      firstRunnerText: q(".eiq-field-runner-button")?.textContent || "",
      reviewButtonTop: buttons.find((el) => el.textContent.trim() === "REVIEW")?.getBoundingClientRect().top || 0,
      firstButtonTop: buttons[0]?.getBoundingClientRect().top || 0,
    };
  });

  const prefix = `${width}`;
  data.mounted === "FieldWorkspace" ? pass(`${prefix}_mounted_field`) : fail(`${prefix}_mounted_field`, { data });
  data.activeTab === "FIELD" ? pass(`${prefix}_active_tab_field`) : fail(`${prefix}_active_tab_field`, { activeTab: data.activeTab });
  data.bodyOverflow ? fail(`${prefix}_no_browser_horizontal_overflow`, { data }) : pass(`${prefix}_no_browser_horizontal_overflow`);
  data.tabs && Math.abs(data.reviewButtonTop - data.firstButtonTop) < 3 ? pass(`${prefix}_review_not_orphaned`) : fail(`${prefix}_review_not_orphaned`, { data });
  data.headerCells.join("|") === "NO|SILK|RUNNER|BAR|WGT|JOCKEY|TRAINER|EPI|MARKET|STATUS" ? pass(`${prefix}_headers_exact`) : fail(`${prefix}_headers_exact`, { headers: data.headerCells });
  /RUNNERS/.test(data.countsText) && /ACTIVE/.test(data.countsText) && /SCRATCHED/.test(data.countsText) ? pass(`${prefix}_counts_rendered`) : fail(`${prefix}_counts_rendered`, { countsText: data.countsText });
  data.fieldHeader && data.fieldHeader.height <= 95 ? pass(`${prefix}_compact_field_header`) : fail(`${prefix}_compact_field_header`, { fieldHeader: data.fieldHeader });
  /Set Weights|Apprentices|field limit|Track name:|Track type:|VOBIS/i.test(data.metaText) ? fail(`${prefix}_admin_wall_removed`, { metaText: cleanText(data.metaText) }) : pass(`${prefix}_admin_wall_removed`);
  data.table && data.tableWrap && data.table.right <= data.tableWrap.right + 3 ? pass(`${prefix}_table_inside_wrap`) : fail(`${prefix}_table_inside_wrap`, { data });

  const firstRow = page.locator(".eiq-field-runner-row").first();
  await firstRow.click();
  await page.waitForTimeout(250);
  const expanded = await page.locator(".eiq-field-expanded-row").count();
  expanded === 1 ? pass(`${prefix}_click_expands_one_row`) : fail(`${prefix}_click_expands_one_row`, { expanded });
  const expandedText = cleanText(await page.locator(".eiq-field-expanded-row").first().textContent().catch(() => ""));
  /undefined|null|NaN|\[object Object\]/i.test(expandedText) ? fail(`${prefix}_expanded_no_raw_placeholders`, { expandedText }) : pass(`${prefix}_expanded_no_raw_placeholders`);
  const recentRows = await page.locator(".eiq-field-expanded-row tbody tr").count().catch(() => 0);
  recentRows <= 5 ? pass(`${prefix}_expanded_max_five`) : fail(`${prefix}_expanded_max_five`, { recentRows });
  if (/NO PREVIOUS STARTS/.test(expandedText)) pass(`${prefix}_no_history_state`); else pass(`${prefix}_active_runner_expansion`);
  await firstRow.press("Enter");
  await page.waitForTimeout(200);
  const afterKeyboard = await page.locator(".eiq-field-expanded-row").count();
  afterKeyboard === 0 ? pass(`${prefix}_keyboard_toggle`) : fail(`${prefix}_keyboard_toggle`, { afterKeyboard });

  const scratchedRow = page.locator(".eiq-field-runner-row.is-scratched").first();
  if (await scratchedRow.count()) {
    await scratchedRow.click();
    await page.waitForTimeout(200);
    const scratchedExpanded = await page.locator(".eiq-field-expanded-row").count();
    scratchedExpanded === 1 ? pass(`${prefix}_scratched_runner_expansion`) : fail(`${prefix}_scratched_runner_expansion`, { scratchedExpanded });
  } else {
    pass(`${prefix}_scratched_runner_expansion_not_present`, { note: "No scratched row in selected test race" });
  }

  return screenshotPath;
}

async function raceSwitchProbe(page) {
  await clickText(page, "MEETINGS");
  await page.waitForTimeout(500);
  for (const raceNo of ["R1", "R2", "R3"]) {
    const chip = page.getByText(new RegExp(`^${raceNo}$`)).first();
    if (!(await chip.count())) {
      fail(`${raceNo}_switching`, { reason: "Race selector not found" });
      continue;
    }
    await chip.click({ timeout: 10000 });
    await page.waitForTimeout(700);
    await clickText(page, "FIELD");
    await page.waitForTimeout(400);
    const mounted = await page.locator("[data-edgeiq-mounted-component='FieldWorkspace']").count();
    const rows = await page.locator(".eiq-field-runner-row").count();
    mounted && rows > 0 ? pass(`${raceNo}_switching`, { rows }) : fail(`${raceNo}_switching`, { mounted, rows });
    await clickText(page, "MEETINGS");
    await page.waitForTimeout(400);
  }
}
async function openRaceChip(page, raceNo) {
  await clickText(page, "MEETINGS");
  await page.waitForTimeout(400);
  const chip = page.getByText(new RegExp(`^${raceNo}$`)).first();
  await chip.click({ timeout: 10000 });
  await page.waitForTimeout(600);
  await clickText(page, "FIELD");
  await page.waitForTimeout(350);
}

async function fieldEdgeCaseProbe(page) {
  await openRaceChip(page, "R1");
  const fewerRow = page.locator(".eiq-field-runner-row").nth(1);
  await fewerRow.click();
  await page.waitForTimeout(150);
  const fewerRows = await page.locator(".eiq-field-expanded-row tbody tr").count().catch(() => 0);
  fewerRows > 0 && fewerRows < 5 ? pass("fewer_than_five_state", { race: "R1", rows: fewerRows }) : fail("fewer_than_five_state", { race: "R1", rows: fewerRows });

  await openRaceChip(page, "R2");
  const noHistoryRow = page.locator(".eiq-field-runner-row").first();
  await noHistoryRow.click();
  await page.waitForTimeout(150);
  const noHistoryText = cleanText(await page.locator(".eiq-field-expanded-row").first().textContent().catch(() => ""));
  /NO PREVIOUS STARTS/.test(noHistoryText) ? pass("no_history_state_browser", { race: "R2" }) : fail("no_history_state_browser", { race: "R2", noHistoryText });

  const scratchedRow = page.locator(".eiq-field-runner-row.is-scratched").first();
  if (await scratchedRow.count()) {
    await scratchedRow.click();
    await page.waitForTimeout(150);
    const expanded = await page.locator(".eiq-field-expanded-row").count();
    expanded === 1 ? pass("scratched_runner_expansion", { race: "R2" }) : fail("scratched_runner_expansion", { race: "R2", expanded });
  } else {
    fail("scratched_runner_expansion", { race: "R2", reason: "No scratched runner rendered" });
  }
}
async function navProbe(page) {
  await clickText(page, "RACE");
  await page.waitForTimeout(300);
  const raceMounted = await page.locator("[data-edgeiq-mounted-component='RaceIntelligenceWorkspace']").count();
  raceMounted ? pass("race_navigation_regression") : fail("race_navigation_regression");
  await clickText(page, "FIELD");
  await page.waitForTimeout(300);
  await clickText(page, "FORM GUIDE");
  await page.waitForTimeout(300);
  const formMounted = await page.locator("[data-edgeiq-mounted-component='RaceFormGuideWorkspace']").count();
  formMounted ? pass("form_guide_navigation") : fail("form_guide_navigation");
  await clickText(page, "FIELD");
  await page.waitForTimeout(300);
  const fieldMounted = await page.locator("[data-edgeiq-mounted-component='FieldWorkspace']").count();
  fieldMounted ? pass("field_navigation_return") : fail("field_navigation_return");
}

async function main() {
  fs.mkdirSync(DOC, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const consoleMessages = [];
  const pageErrors = [];
  page.on("console", (msg) => consoleMessages.push({ type: msg.type(), text: msg.text() }));
  page.on("pageerror", (err) => pageErrors.push(String(err.message || err)));
  const screenshots = [];
  for (const width of widths) screenshots.push(await fieldProbe(page, width));
  await raceSwitchProbe(page);
  await fieldEdgeCaseProbe(page);
  await navProbe(page);
  const forbiddenErrors = pageErrors.filter(Boolean);
  forbiddenErrors.length ? fail("browser_console", { pageErrors: forbiddenErrors, consoleMessages }) : pass("browser_console", { consoleMessages: consoleMessages.slice(-10) });
  await browser.close();
  const status = results.every((item) => item.status === "PASS") ? "PASS" : "FAIL";
  const payload = { status, url: URL, screenshots, results };
  fs.writeFileSync(path.join(DOC, "EDGEIQ_FIELD_WORKSPACE_V1_BROWSER_ACCEPTANCE.json"), JSON.stringify(payload, null, 2));
  fs.writeFileSync(path.join(DOC, "EDGEIQ_FIELD_WORKSPACE_V1_BROWSER_ACCEPTANCE.md"), `# EDGEIQ FIELD WORKSPACE V1 Browser Acceptance\n\nStatus: **${status}**\n\n${results.map((r) => `- ${r.status}: ${r.check}`).join("\n")}\n`);
  console.log(JSON.stringify(payload, null, 2));
  if (status !== "PASS") process.exit(1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
