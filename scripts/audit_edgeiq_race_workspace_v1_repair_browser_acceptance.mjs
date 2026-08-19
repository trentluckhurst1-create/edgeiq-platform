import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const ROOT = 'C:/Users/trent/OneDrive/Documents/EDGEIQ_PLATFORM';
const DOCS = path.join(ROOT, 'docs/full-product-implementation');
const URL = 'http://localhost:5173/';
const WIDTHS = [1920, 1600, 1440, 1366];

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
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForSelector('.eiq-approved-shell', { timeout: 30000 });
  await clickExactButton(page, 'RACE');
  await page.waitForTimeout(750);
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
  return await page.evaluate((width) => {
    const txt = (el) => (el?.innerText || el?.textContent || '').replace(/\s+/g, ' ').trim();
    const styleOf = (sel) => {
      const el = document.querySelector(sel);
      if (!el) return { selector: sel, exists: false };
      const cs = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      return { selector: sel, exists: true, display: cs.display, width: Math.round(r.width), height: Math.round(r.height), background: cs.backgroundColor, border: cs.border, gridTemplateColumns: cs.gridTemplateColumns, text: txt(el).slice(0, 500) };
    };
    const race = document.querySelector('.eiq-race-v1');
    const shell = document.querySelector('.eiq-approved-shell__content');
    const raceRect = race?.getBoundingClientRect();
    const shellRect = shell?.getBoundingClientRect();
    const headers = Array.from(document.querySelectorAll('.eiq-race-v1__table th')).map((th) => txt(th));
    const result = {
      width,
      activeWorkspaceKey: document.querySelector('[data-edgeiq-workspace-key]')?.getAttribute('data-edgeiq-workspace-key') || null,
      mountedComponent: document.querySelector('[data-edgeiq-mounted-component]')?.getAttribute('data-edgeiq-mounted-component') || null,
      raceAttr: race?.getAttribute('data-edgeiq-race-workspace-v1') || null,
      edgeiqOsPresent: !!document.querySelector('.edgeiq-os'),
      approvedShellPresent: !!document.querySelector('.eiq-approved-shell'),
      raceWidth: raceRect ? Math.round(raceRect.width) : 0,
      shellWidth: shellRect ? Math.round(shellRect.width) : 0,
      summaryCardCount: document.querySelectorAll('.eiq-race-v1__summary-card').length,
      selectorButtonCount: document.querySelectorAll('.eiq-race-v1__selector button').length,
      contextTabDisplay: getComputedStyle(document.querySelector('.eiq-context-tabs')).display,
      summaryDisplay: getComputedStyle(document.querySelector('.eiq-race-v1__summary')).display,
      speedExists: !!document.querySelector('.eiq-race-v1__speed'),
      epiExists: !!document.querySelector('.eiq-race-v1__epi'),
      runnerBoardExists: !!document.querySelector('.eiq-race-v1__board'),
      runnerBoardHeaders: headers,
      badEncoding: /â|Â|œ|™/.test(document.body.innerText),
      forbiddenDump: /R1Time Not PublishedR2Time Not Published/.test(txt(document.querySelector('.eiq-race-v1'))),
      selectors: ['.eiq-context-tabs','.eiq-race-v1','.eiq-race-v1__identity','.eiq-race-v1__metadata','.eiq-race-v1__selector','.eiq-race-v1__summary','.eiq-race-v1__summary-card','.eiq-race-v1__matters','.eiq-race-v1__midrow','.eiq-race-v1__speed','.eiq-race-v1__epi','.eiq-race-v1__conditions','.eiq-race-v1__board','.eiq-race-v1__table'].map(styleOf),
    };
    result.pass = result.activeWorkspaceKey === 'RACE' && result.mountedComponent === 'RaceIntelligenceWorkspace' && result.raceAttr === 'repair-v1' && result.raceWidth >= Math.min(900, result.shellWidth * 0.85) && result.summaryCardCount === 4 && result.contextTabDisplay === 'grid' && result.summaryDisplay === 'grid' && result.speedExists && result.epiExists && result.runnerBoardExists && headers.join('|') === 'NO|SILK|RUNNER|BAR|WGT|JOCKEY|TRAINER|EPI|SPD|EDGEIQ|MARKET|STATUS' && !result.badEncoding && !result.forbiddenDump;
    return result;
  }, width);
}

async function regression(page, tabName, expected) {
  const clicked = await clickExactButton(page, tabName);
  await page.waitForTimeout(600);
  return await page.evaluate(({ tabName, expected, clicked }) => {
    const body = document.body.innerText || '';
    return {
      tabName,
      clicked,
      activeWorkspaceKey: document.querySelector('[data-edgeiq-workspace-key]')?.getAttribute('data-edgeiq-workspace-key') || null,
      selectorExists: expected ? !!document.querySelector(expected) : true,
      bodyHasEdgeiq: /EDGEiQ/i.test(body),
      bodyHasMeetings: /MEETINGS/i.test(body),
      bodyHasField: /NO\s+SILK\s+RUNNER/i.test(body),
    };
  }, { tabName, expected, clicked });
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
const results = [];
const consoleMessages = [];
for (const width of WIDTHS) {
  const page = await browser.newPage({ viewport: { width, height: 1100 } });
  page.on('console', (msg) => { if (['error', 'warning'].includes(msg.type())) consoleMessages.push({ width, type: msg.type(), text: msg.text() }); });
  page.on('pageerror', (err) => consoleMessages.push({ width, type: 'pageerror', text: err.message }));
  await openRace(page);
  const data = await inspect(page, width);
  await page.screenshot({ path: path.join(DOCS, `EDGEIQ_RACE_WORKSPACE_V1_REPAIR_${width}.png`), fullPage: true });
  results.push(data);
  await page.close();
}
const regPage = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
await regPage.goto(URL, { waitUntil: 'domcontentloaded', timeout: 45000 });
const home = await regression(regPage, 'HOME', null);
const meetings = await regression(regPage, 'MEETINGS', '.eiq-meetings-v1');
await openRace(regPage);
const field = await regression(regPage, 'FIELD', '.eiq-field-workspace-v1');
const switches = await raceSwitching(regPage);
await regPage.close();
await browser.close();
const hardErrors = consoleMessages.filter((item) => item.type === 'pageerror' || item.type === 'error');
const payload = {
  overall_status: results.every((item) => item.pass) && home.bodyHasEdgeiq && meetings.selectorExists && field.selectorExists && switches.every((item) => item.pass) && hardErrors.length === 0 ? 'PASS' : 'FAIL',
  tested_url: URL,
  viewports: results,
  console: consoleMessages,
  home_regression_status: home.bodyHasEdgeiq ? 'PASS' : 'FAIL',
  meetings_regression_status: meetings.selectorExists ? 'PASS' : 'FAIL',
  field_regression_status: field.selectorExists ? 'PASS' : 'FAIL',
  race_switching_status: switches.every((item) => item.pass) ? 'PASS' : 'FAIL',
  home,
  meetings,
  field,
  switches,
};
writeJson('EDGEIQ_RACE_WORKSPACE_V1_REPAIR_BROWSER_ACCEPTANCE.json', payload);
writeText('EDGEIQ_RACE_WORKSPACE_V1_REPAIR_BROWSER_ACCEPTANCE.md', `# EDGEiQ Race Workspace V1 Repair Browser Acceptance\n\nOverall status: **${payload.overall_status}**\n\n- URL: ${URL}\n- 1920: ${results[0].pass ? 'PASS' : 'FAIL'}\n- 1600: ${results[1].pass ? 'PASS' : 'FAIL'}\n- 1440: ${results[2].pass ? 'PASS' : 'FAIL'}\n- 1366: ${results[3].pass ? 'PASS' : 'FAIL'}\n- R1/R2/R3 switching: ${payload.race_switching_status}\n- HOME regression: ${payload.home_regression_status}\n- MEETINGS regression: ${payload.meetings_regression_status}\n- FIELD regression: ${payload.field_regression_status}\n- Console hard errors: ${hardErrors.length}\n`);
console.log(JSON.stringify(payload, null, 2));
