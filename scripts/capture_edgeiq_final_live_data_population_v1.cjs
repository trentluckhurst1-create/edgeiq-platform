const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const ROOT = process.cwd();
const OUT_DIR = path.join(ROOT, 'docs', 'full-product-implementation', 'screenshots', 'final-live-data');
fs.mkdirSync(OUT_DIR, { recursive: true });

const BASE = 'http://127.0.0.1:5173/?dev-preview=1';
const STORAGE_KEY = 'edgeiq-os-racefile-v3-state';
const selectedContext = {
  activeSection: 'home',
  viewLevel: 'race',
  selectedMeetingsDayKey: 'TODAY',
  selectedMeetingKey: '2026-07-20|PAKENHAM',
  selectedRaceKey: '2026-07-20|PAKENHAM|R1',
  selectedRunnerIndex: 0,
};

const workspaces = [
  ['HOME', 'home', 'HOME_POPULATED.png'],
  ['MEETINGS', 'meetings', 'MEETINGS_POPULATED.png'],
  ['RACE', 'race', 'RACE_POPULATED.png'],
  ['FIELD', 'field', 'FIELD_POPULATED.png'],
  ['FORM GUIDE', 'formGuide', 'FORM_GUIDE_POPULATED.png'],
  ['PERFORMANCE', 'performance', 'PERFORMANCE_POPULATED.png'],
  ['MAP', 'map', 'MAP_POPULATED.png'],
  ['EPI', 'epi', 'EPI_POPULATED.png'],
  ['MARKET', 'market', 'MARKET_POPULATED.png'],
  ['OVERVIEW', 'overview', 'OVERVIEW_POPULATED.png'],
  ['INSIGHTS', 'insights', 'INSIGHTS_POPULATED.png'],
  ['RESULTS', 'results', 'RESULTS_POPULATED.png'],
  ['LAB', 'lab', 'LAB_POPULATED.png'],
  ['COMPARE', 'compare', 'COMPARE_POPULATED.png'],
  ['REVIEW', 'review', 'REVIEW_POPULATED.png'],
  ['SETTINGS', 'settings', 'SETTINGS_POPULATED.png'],
];

function compactText(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 }, deviceScaleFactor: 1 });
  const network = [];
  const consoleRows = [];
  const pageErrors = [];

  page.on('response', async (response) => {
    const url = response.url();
    if (url.includes('/data/') || url.includes('/performance-intelligence/edgeiq')) {
      network.push({ url, status: response.status(), ok: response.ok(), contentType: response.headers()['content-type'] || '' });
    }
  });
  page.on('requestfailed', (request) => {
    const url = request.url();
    if (url.includes('/data/') || url.includes('/performance-intelligence/edgeiq')) {
      network.push({ url, status: 0, ok: false, failure: request.failure()?.errorText || 'request failed' });
    }
  });
  page.on('console', (msg) => {
    consoleRows.push({ type: msg.type(), text: msg.text() });
  });
  page.on('pageerror', (error) => {
    pageErrors.push({ message: error.message, stack: error.stack });
  });

  await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(1200);

  const workspaceReports = [];
  for (const [label, section, screenshotName] of workspaces) {
    await page.evaluate(({ key, baseState, activeSection }) => {
      const next = { ...baseState, activeSection };
      if (activeSection === 'home' || activeSection === 'meetings') {
        next.viewLevel = 'meetings';
      } else {
        next.viewLevel = 'race';
      }
      window.localStorage.setItem(key, JSON.stringify(next));
    }, { key: STORAGE_KEY, baseState: selectedContext, activeSection: section });
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(1800);

    const bodyText = compactText(await page.locator('body').innerText({ timeout: 10000 }).catch(() => ''));
    const screenshotPath = path.join(OUT_DIR, screenshotName);
    let screenshotStatus = 'SAVED';
    try {
      await page.screenshot({ path: screenshotPath, fullPage: false, timeout: 15000 });
    } catch (error) {
      screenshotStatus = `FAILED: ${error.message}`;
    }
    workspaceReports.push({
      workspace: label,
      activeSection: section,
      screenshot: screenshotPath,
      screenshotStatus,
      bodyLength: bodyText.length,
      hasFailedToFetch: /Failed to fetch/i.test(bodyText),
      hasPakenham: /Pakenham Synthetic/i.test(bodyText),
      hasRaceContext: /Pakenham|R1|Race 1|FORM GUIDE|PERFORMANCE|MAP|EPI|MARKET|OVERVIEW/i.test(bodyText),
      bodySample: bodyText.slice(0, 1200),
    });
  }

  await browser.close();

  const dataNetwork = network.filter((row) => row.url.includes('/data/') || row.url.includes('/performance-intelligence/edgeiq'));
  const networkSummary = {
    generatedAt: new Date().toISOString(),
    url: BASE,
    selectedContext,
    totalDataRequests: dataNetwork.length,
    failedDataRequests: dataNetwork.filter((row) => !row.ok).length,
    requests: dataNetwork,
  };
  const consoleSummary = {
    generatedAt: new Date().toISOString(),
    url: BASE,
    selectedContext,
    pageErrors,
    console: consoleRows,
    uncaughtErrorCount: pageErrors.length,
    consoleErrorCount: consoleRows.filter((row) => row.type === 'error').length,
    workspaceReports,
  };

  fs.writeFileSync(path.join(OUT_DIR, 'LIVE_NETWORK_REPORT.json'), JSON.stringify(networkSummary, null, 2));
  fs.writeFileSync(path.join(OUT_DIR, 'LIVE_CONSOLE_REPORT.json'), JSON.stringify(consoleSummary, null, 2));
  fs.writeFileSync(path.join(OUT_DIR, 'LIVE_WORKSPACE_POPULATION_REPORT.json'), JSON.stringify({ generatedAt: new Date().toISOString(), workspaceReports }, null, 2));

  const hardFailures = [];
  if (networkSummary.failedDataRequests > 0) hardFailures.push(`failed data requests ${networkSummary.failedDataRequests}`);
  if (consoleSummary.uncaughtErrorCount > 0) hardFailures.push(`page errors ${consoleSummary.uncaughtErrorCount}`);
  const rawFetchScreens = workspaceReports.filter((row) => row.hasFailedToFetch).map((row) => row.workspace);
  if (rawFetchScreens.length) hardFailures.push(`raw Failed to fetch in ${rawFetchScreens.join(', ')}`);
  const emptyScreens = workspaceReports.filter((row) => row.bodyLength < 200).map((row) => row.workspace);
  if (emptyScreens.length) hardFailures.push(`low body text in ${emptyScreens.join(', ')}`);

  if (hardFailures.length) {
    console.error('EDGEIQ_FINAL_LIVE_DATA_BROWSER_CAPTURE_FAIL ' + hardFailures.join('; '));
    process.exit(1);
  }
  console.log('EDGEIQ_FINAL_LIVE_DATA_BROWSER_CAPTURE_PASS');
})();
