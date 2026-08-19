import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const ROOT = 'C:/Users/trent/OneDrive/Documents/EDGEIQ_PLATFORM';
const DOCS = path.join(ROOT, 'docs/full-product-implementation');
const TARGET_URL = 'http://localhost:5173/';
const WIDTHS = [1920, 1600, 1440, 1366];
const BEFORE = { speedPanelHeight: 236, speedEmptyHeight: 162, runnerBoardTop: 1016 };

function writeJson(name, data) { fs.writeFileSync(path.join(DOCS, name), JSON.stringify(data, null, 2), 'utf8'); }
function writeText(name, data) { fs.writeFileSync(path.join(DOCS, name), data, 'utf8'); }

async function clickExactButton(page, label) {
  return await page.evaluate((label) => {
    const buttons = Array.from(document.querySelectorAll('button'));
    const button = buttons.find((item) => (item.innerText || item.textContent || '').replace(/\s+/g, ' ').trim() === label);
    if (!button) return false;
    button.click();
    return true;
  }, label);
}

async function openRace(page) {
  await page.goto(TARGET_URL, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForSelector('.eiq-approved-shell', { timeout: 30000 });
  await clickExactButton(page, 'RACE');
  await page.waitForTimeout(800);
  if (!(await page.locator('.eiq-race-v1').count())) {
    await clickExactButton(page, 'Open Meeting');
    await page.waitForTimeout(500);
    await clickExactButton(page, 'R1');
    await page.waitForTimeout(500);
    await clickExactButton(page, 'RACE');
  }
  await page.waitForSelector('.eiq-race-v1', { timeout: 30000 });
}

async function inspect(page, width) {
  return await page.evaluate(({ width, BEFORE }) => {
    const txt = (el) => (el?.innerText || el?.textContent || '').replace(/\s+/g, ' ').trim();
    const rect = (selector) => {
      const el = document.querySelector(selector);
      if (!el) return null;
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      return { selector, exists: true, top: Math.round(r.top), height: Math.round(r.height), width: Math.round(r.width), display: cs.display, text: txt(el) };
    };
    const headers = Array.from(document.querySelectorAll('.eiq-race-v1__table th')).map((th) => txt(th));
    const mattersText = txt(document.querySelector('.eiq-race-v1__matters header span'));
    const visibleMatterItems = document.querySelectorAll('.eiq-race-v1__matters p').length;
    const visibleMatterCount = Number((mattersText.match(/\d+/) || ['-1'])[0]);
    const speedEmpty = rect('.eiq-race-v1__empty');
    const speed = rect('.eiq-race-v1__speed');
    const board = rect('.eiq-race-v1__board');
    const tabs = rect('.eiq-context-tabs');
    const race = rect('.eiq-race-v1');
    const bodyText = document.body.innerText || '';
    const epiStatuses = Array.from(document.querySelectorAll('.eiq-race-v1__epi-row small')).map((item) => txt(item)).filter(Boolean);
    const noOverlap = Array.from(document.querySelectorAll('.eiq-race-v1 *')).every((el) => {
      const r = el.getBoundingClientRect();
      return Number.isFinite(r.width) && Number.isFinite(r.height) && r.width >= 0 && r.height >= 0;
    });
    const horizontalOverflow = document.documentElement.scrollWidth > window.innerWidth + 8;
    return {
      width,
      activeWorkspaceKey: document.querySelector('[data-edgeiq-workspace-key]')?.getAttribute('data-edgeiq-workspace-key') || null,
      mountedComponent: document.querySelector('[data-edgeiq-mounted-component]')?.getAttribute('data-edgeiq-mounted-component') || null,
      raceAttr: document.querySelector('.eiq-race-v1')?.getAttribute('data-edgeiq-race-workspace-v1') || null,
      tabs,
      race,
      speed,
      speedEmpty,
      board,
      mattersText,
      visibleMatterItems,
      visibleMatterCount,
      epiStatuses,
      headers,
      conditionsPanelCount: document.querySelectorAll('.eiq-race-v1__conditions').length,
      approvedShellPresent: !!document.querySelector('.eiq-approved-shell'),
      edgeiqOsPresent: !!document.querySelector('.edgeiq-os'),
      badDump: /R1Time Not PublishedR2Time Not Published/.test(txt(document.querySelector('.eiq-race-v1'))),
      badEncoding: ['\u00e2', '\u00c2', '\u0153', '\u2122'].some((ch) => bodyText.includes(ch)),
      noOverlap,
      horizontalOverflow,
      runnerBoardMovedUp: board ? board.top < BEFORE.runnerBoardTop : false,
      speedEmptyReduced: speedEmpty ? speedEmpty.height < BEFORE.speedEmptyHeight : false,
      speedPanelReduced: speed ? speed.height < BEFORE.speedPanelHeight : false,
    };
  }, { width, BEFORE });
}

async function regression(page, tabName, selector) {
  const clicked = await clickExactButton(page, tabName);
  await page.waitForTimeout(700);
  return await page.evaluate(({ tabName, selector, clicked }) => ({
    tabName,
    clicked,
    activeWorkspaceKey: document.querySelector('[data-edgeiq-workspace-key]')?.getAttribute('data-edgeiq-workspace-key') || null,
    selectorExists: selector ? !!document.querySelector(selector) : true,
    bodyText: (document.body.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 800),
  }), { tabName, selector, clicked });
}

async function raceSwitching(page) {
  await openRace(page);
  const outcomes = [];
  for (const label of ['R1', 'R2', 'R3']) {
    const clicked = await page.evaluate((label) => {
      const buttons = Array.from(document.querySelectorAll('.eiq-race-v1__selector button'));
      const button = buttons.find((item) => (item.innerText || '').replace(/\s+/g, ' ').trim().startsWith(label + ' '));
      if (!button) return false;
      button.click();
      return true;
    }, label);
    await page.waitForTimeout(500);
    const state = await page.evaluate(() => ({
      activeWorkspaceKey: document.querySelector('[data-edgeiq-workspace-key]')?.getAttribute('data-edgeiq-workspace-key') || null,
      identity: (document.querySelector('.eiq-race-v1__identity')?.innerText || '').replace(/\s+/g, ' ').trim(),
      activeSelector: (document.querySelector('.eiq-race-v1__selector button.is-active')?.innerText || '').replace(/\s+/g, ' ').trim(),
    }));
    outcomes.push({ label, clicked, ...state, pass: clicked && state.activeWorkspaceKey === 'RACE' && state.identity.includes(`Race ${label.slice(1)}`) });
  }
  return outcomes;
}

const browser = await chromium.launch({ headless: true });
const consoleMessages = [];
const viewports = [];
for (const width of WIDTHS) {
  const page = await browser.newPage({ viewport: { width, height: 1100 } });
  page.on('console', (msg) => { if (['error', 'warning'].includes(msg.type())) consoleMessages.push({ width, type: msg.type(), text: msg.text() }); });
  page.on('pageerror', (err) => consoleMessages.push({ width, type: 'pageerror', text: err.message }));
  await openRace(page);
  const data = await inspect(page, width);
  data.pass = data.activeWorkspaceKey === 'RACE'
    && data.mountedComponent === 'RaceIntelligenceWorkspace'
    && data.raceAttr === 'repair-v1'
    && data.tabs?.display === 'grid'
    && data.tabs?.height >= 44
    && data.visibleMatterCount === data.visibleMatterItems
    && data.conditionsPanelCount === 0
    && data.headers.includes('EDGEiQ PRICE')
    && !data.headers.includes('EDGEIQ')
    && !data.epiStatuses.includes('Available')
    && data.speedEmptyReduced
    && data.speedPanelReduced
    && data.runnerBoardMovedUp
    && !data.badDump
    && !data.badEncoding
    && data.noOverlap
    && !data.horizontalOverflow;
  await page.screenshot({ path: path.join(DOCS, `EDGEIQ_RACE_WORKSPACE_V1_FINAL_POLISH_${width}.png`), fullPage: true });
  viewports.push(data);
  await page.close();
}
const regPage = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
await regPage.goto(TARGET_URL, { waitUntil: 'domcontentloaded', timeout: 45000 });
await regPage.waitForSelector('.eiq-approved-shell', { timeout: 30000 });
const home = await regression(regPage, 'HOME', null);
const meetings = await regression(regPage, 'MEETINGS', '.eiq-meetings-v1');
await openRace(regPage);
const field = await regression(regPage, 'FIELD', '.eiq-field-workspace-v1');
const switches = await raceSwitching(regPage);
await regPage.close();
await browser.close();

const hardErrors = consoleMessages.filter((item) => item.type === 'pageerror' || item.type === 'error');
const payload = {
  overall_status: viewports.every((item) => item.pass) && home.clicked && meetings.selectorExists && field.selectorExists && switches.every((item) => item.pass) && hardErrors.length === 0 ? 'PASS' : 'FAIL',
  tested_url: TARGET_URL,
  before_metrics: BEFORE,
  viewports,
  console: consoleMessages,
  hard_error_count: hardErrors.length,
  home_regression_status: home.clicked ? 'PASS' : 'FAIL',
  meetings_regression_status: meetings.selectorExists ? 'PASS' : 'FAIL',
  field_regression_status: field.selectorExists ? 'PASS' : 'FAIL',
  race_switching_status: switches.every((item) => item.pass) ? 'PASS' : 'FAIL',
  home,
  meetings,
  field,
  switches,
};
writeJson('EDGEIQ_RACE_WORKSPACE_V1_FINAL_POLISH_BROWSER_ACCEPTANCE.json', payload);
writeText('EDGEIQ_RACE_WORKSPACE_V1_FINAL_POLISH_BROWSER_ACCEPTANCE.md', `# EDGEiQ Race Workspace V1 Final Polish Browser Acceptance\n\nOverall status: **${payload.overall_status}**\n\n- URL: ${TARGET_URL}\n- Before speed panel height: ${BEFORE.speedPanelHeight}px\n- Before empty speed height: ${BEFORE.speedEmptyHeight}px\n- Before runner board top: ${BEFORE.runnerBoardTop}px\n- 1920: ${viewports[0].pass ? 'PASS' : 'FAIL'}\n- 1600: ${viewports[1].pass ? 'PASS' : 'FAIL'}\n- 1440: ${viewports[2].pass ? 'PASS' : 'FAIL'}\n- 1366: ${viewports[3].pass ? 'PASS' : 'FAIL'}\n- What Matters visible count at 1920: ${viewports[0].visibleMatterCount}\n- Speed panel height at 1920: ${viewports[0].speed?.height ?? 'n/a'}px\n- Empty speed height at 1920: ${viewports[0].speedEmpty?.height ?? 'n/a'}px\n- Runner board top at 1920: ${viewports[0].board?.top ?? 'n/a'}px\n- R1/R2/R3 switching: ${payload.race_switching_status}\n- HOME regression: ${payload.home_regression_status}\n- MEETINGS regression: ${payload.meetings_regression_status}\n- FIELD regression: ${payload.field_regression_status}\n- Console hard errors: ${hardErrors.length}\n`);
console.log(JSON.stringify(payload, null, 2));
if (payload.overall_status !== 'PASS') process.exit(1);
