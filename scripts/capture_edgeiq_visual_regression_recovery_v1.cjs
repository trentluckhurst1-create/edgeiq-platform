const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
(async () => {
  const out = path.resolve('docs/visual-regression-recovery/screenshots');
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1200 }, deviceScaleFactor: 1 });
  page.setDefaultTimeout(120000);
  page.setDefaultNavigationTimeout(120000);
  const shots = [];
  async function shot(name) { await page.waitForTimeout(1500); const file = path.join(out, name + '.png'); await page.screenshot({ path: file, fullPage: false }); shots.push(file); }
  await page.goto('http://127.0.0.1:5176/', { waitUntil: 'load', timeout: 120000 });
  await shot('01_meetings_home');
  const openMeeting = page.getByRole('button', { name: /open meeting/i }).first();
  if (await openMeeting.count()) await openMeeting.click();
  await shot('02_meeting_detail');
  const openRace = page.getByRole('button', { name: /open race/i }).first();
  if (await openRace.count()) await openRace.click();
  await shot('03_race_form_guide');
  for (const tab of ['MARKET','MAP','OVERVIEW']) { const btn = page.getByRole('button', { name: new RegExp('^' + tab + '$', 'i') }).first(); if (await btn.count()) { await btn.click(); await shot('04_' + tab.toLowerCase()); } }
  const lab = page.getByRole('button', { name: /^lab$/i }).first();
  if (await lab.count()) { await lab.click(); await shot('07_lab'); }
  await browser.close();
  console.log(shots.join('\n'));
})().catch((error) => { console.error(error); process.exit(1); });
