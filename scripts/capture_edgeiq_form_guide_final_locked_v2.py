from __future__ import annotations
from pathlib import Path
import json, subprocess, time, os, signal, csv, urllib.request
from datetime import datetime
from PIL import Image, ImageChops, ImageFilter, ImageEnhance

ROOT = Path(__file__).resolve().parents[1]
SHOT_DIR = ROOT / 'docs' / 'full-product-implementation' / 'screenshots' / 'form-guide-final-locked'
APPROVED = SHOT_DIR / '05_FORM_GUIDE_APPROVED.png'
LIVE = SHOT_DIR / '05_FORM_GUIDE_LIVE_1536x1024.png'
OVERLAY = SHOT_DIR / '05_FORM_GUIDE_OVERLAY_50.png'
DIFF = SHOT_DIR / '05_FORM_GUIDE_DIFF.png'
EDGE_DIFF = SHOT_DIR / '05_FORM_GUIDE_EDGE_DIFF.png'
REGION_DIFF = SHOT_DIR / '05_FORM_GUIDE_REGION_DIFF.csv'
DOM_GEOMETRY = SHOT_DIR / '05_FORM_GUIDE_DOM_GEOMETRY.json'
RUNTIME = SHOT_DIR / '05_FORM_GUIDE_RUNTIME.json'
CONSOLE = SHOT_DIR / '05_FORM_GUIDE_CONSOLE.json'
NETWORK = SHOT_DIR / '05_FORM_GUIDE_NETWORK.json'
CAPTURE_JS = SHOT_DIR / 'capture_form_guide_final_locked_v2.mjs'
URL = 'http://127.0.0.1:5173/'

JS = f'''
import {{ chromium }} from 'playwright';
import fs from 'node:fs';
const events = [];
const network = [];
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
async function clickText(page, text) {{
  const locator = page.locator('button, a, [role="button"]').filter({{ hasText: text }}).first();
  if (await locator.count()) {{ await locator.click(); await sleep(900); return true; }}
  return false;
}}
async function firstButtonContaining(page, text) {{
  const locator = page.locator('button').filter({{ hasText: text }}).first();
  if (await locator.count()) {{ await locator.click(); await sleep(1000); return true; }}
  return false;
}}
const browser = await chromium.launch({{ headless: true }});
const page = await browser.newPage({{ viewport: {{ width: 1536, height: 1024 }}, deviceScaleFactor: 1 }});\npage.setDefaultTimeout(120000);
page.on('console', (msg) => {{ events.push({{ type: msg.type(), text: msg.text() }}); }});
page.on('pageerror', (err) => events.push({{ type: 'pageerror', text: String(err) }}));
page.on('requestfailed', (request) => network.push({{ type: 'requestfailed', url: request.url(), failure: request.failure()?.errorText }}));
page.on('response', (response) => {{ if (response.status() >= 400) network.push({{ type: 'response', url: response.url(), status: response.status() }}); }});
await page.goto('{URL}', {{ waitUntil: 'commit', timeout: 90000 }});
await page.waitForSelector('#root', {{ state: 'attached', timeout: 90000 }});
await page.evaluate(() => {{
  try {{
    window.localStorage.setItem('edgeiq-os-racefile-v3-state', JSON.stringify({{ activeSection: 'formGuide', viewLevel: 'race', selectedMeetingsDayKey: 'TODAY', selectedMeetingKey: null, selectedRaceKey: null, selectedRunnerIndex: 0 }}));
  }} catch {{}}
}});
await page.reload({{ waitUntil: 'commit', timeout: 90000 }});
await page.waitForSelector('#root', {{ state: 'attached', timeout: 90000 }});
for (let i = 0; i < 90; i += 1) {{
  const len = await page.evaluate(() => (document.body?.innerText || '').trim().length);
  if (len > 20) break;
  await sleep(1000);
}}
await sleep(1600);
if (!(await page.locator('[data-edgeiq-workspace="form-guide-final-locked"]').count())) {{
  await clickText(page, 'ENTER TERMINAL');
  await sleep(900);
  await clickText(page, 'FORM GUIDE');
  await sleep(1400);
}}
if (!(await page.locator('[data-edgeiq-workspace="form-guide-final-locked"]').count())) {{
  if (!(await firstButtonContaining(page, 'OPEN RACE'))) {{
    await firstButtonContaining(page, 'OPEN MEETING');
    await firstButtonContaining(page, 'OPEN RACE');
  }}
  await clickText(page, 'FORM GUIDE');
  await sleep(1600);
}}
await page.evaluate(() => {{ window.scrollTo(0, 0); }});
await sleep(500);
await page.evaluate(() => {{ try {{ Object.defineProperty(document, 'fonts', {{ value: {{ ready: Promise.resolve(), status: 'loaded', check: () => true, addEventListener: () => undefined, removeEventListener: () => undefined }}, configurable: true }}); }} catch {{}} }});
const markerCount = await page.locator('[data-edgeiq-workspace="form-guide-final-locked"]').count();
const oldMarkerCount = await page.locator('[data-edgeiq-workspace="form-guide-approved-exact"]').count();
const dom = await page.evaluate(() => {{
  const rows = [];
  document.querySelectorAll('[data-region], [data-edgeiq-workspace="form-guide-final-locked"], [data-runner-profile="true"]').forEach((node) => {{
    const rect = node.getBoundingClientRect();
    rows.push({{ region: node.getAttribute('data-region') || node.getAttribute('data-edgeiq-workspace') || node.getAttribute('data-runner-profile'), x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height), visible: rect.width > 0 && rect.height > 0, tag: node.tagName.toLowerCase(), className: String(node.getAttribute('class') || '') }});
  }});
  return rows;
}});
const runtime = await page.evaluate(() => {{
  const root = document.querySelector('[data-edgeiq-workspace="form-guide-final-locked"]');
  const columns = root?.querySelector('[data-region="summary_table"]')?.getAttribute('data-columns') || '';
  const recentColumns = root?.querySelector('[data-region="recent_form"] table')?.getAttribute('data-columns') || '';
  const expanded = root?.querySelector('[data-runner-profile="true"]');
  const recentRows = root?.querySelectorAll('[data-region="recent_form"] tbody tr').length || 0;
  const matrixCells = root?.querySelectorAll('.eiq-form-final-profile-cell').length || 0;
  const bodyText = document.body.innerText || '';
  return {{
    url: location.href,
    markerCount: document.querySelectorAll('[data-edgeiq-workspace="form-guide-final-locked"]').length,
    oldMarkerCount: document.querySelectorAll('[data-edgeiq-workspace="form-guide-approved-exact"]').length,
    title: document.title,
    viewport: {{ width: window.innerWidth, height: window.innerHeight, devicePixelRatio: window.devicePixelRatio }},
    columns,
    recentColumns,
    recentRows,
    matrixCells,
    expandedRunner: expanded?.getAttribute('data-runner-no') || null,
    bodySample: bodyText.slice(0, 2500),
    forbiddenVisibleHits: ['UNKNOWN','NOT LOADED','SOURCE GAP','null','undefined','NaN','Metric Guide'].filter((term) => bodyText.includes(term)),
  }};
}});
const cdp = await page.context().newCDPSession(page);
const shot = await cdp.send('Page.captureScreenshot', {{ format: 'png', fromSurface: true, captureBeyondViewport: false }});
fs.writeFileSync({json.dumps(str(LIVE))}, Buffer.from(shot.data, 'base64'));
fs.writeFileSync({json.dumps(str(DOM_GEOMETRY))}, JSON.stringify(dom, null, 2));
fs.writeFileSync({json.dumps(str(RUNTIME))}, JSON.stringify({{ status: markerCount ? 'FORM_GUIDE_FINAL_LOCKED_LIVE_CAPTURED' : 'FORM_GUIDE_FINAL_LOCKED_NOT_FOUND', captured_at: new Date().toISOString(), markerCount, oldMarkerCount, ...runtime }}, null, 2));
fs.writeFileSync({json.dumps(str(CONSOLE))}, JSON.stringify(events, null, 2));
fs.writeFileSync({json.dumps(str(NETWORK))}, JSON.stringify(network, null, 2));
await browser.close();
if (!markerCount) process.exitCode = 2;
'''

def run_server():
    env = os.environ.copy()
    env['BROWSER'] = 'none'
    return subprocess.Popen(['npm.cmd','run','dev','--','--host','127.0.0.1','--port','5173'], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)

def wait_for_server(proc):
    started = time.time()
    log = []
    while time.time() - started < 75:
        if proc.poll() is not None:
            if proc.stdout:
                try:
                    log.extend([line.rstrip() for line in proc.stdout.readlines()])
                except Exception:
                    pass
            return log
        try:
            with urllib.request.urlopen(URL, timeout=2) as response:
                if response.status < 500:
                    return log + [f"HTTP_READY {response.status}"]
        except Exception as exc:
            if len(log) < 8:
                log.append(f"WAIT {type(exc).__name__}")
        time.sleep(1)
    return log + ['HTTP_WAIT_TIMEOUT']

def make_diffs():
    if not APPROVED.exists() or not LIVE.exists():
        return {'status':'DIFF_SKIPPED_MISSING_IMAGE'}
    approved = Image.open(APPROVED).convert('RGB').resize((1536, 1024))
    live = Image.open(LIVE).convert('RGB')
    if live.size != (1536, 1024):
        live = live.resize((1536, 1024))
    Image.blend(approved, live, 0.5).save(OVERLAY)
    raw_diff = ImageChops.difference(approved, live)
    diff_score = sum(raw_diff.convert('L').histogram()[i] * i for i in range(256)) / (1536*1024*255)
    ImageEnhance.Contrast(raw_diff).enhance(3.0).save(DIFF)
    edge = raw_diff.convert('L').filter(ImageFilter.FIND_EDGES)
    edge.save(EDGE_DIFF)
    regions = [
        ('header',0,0,1536,125),('summary_table',0,125,1536,390),('runner_hero',0,390,1536,540),('profile_matrix',0,540,1536,760),('recent_form',0,760,1536,1024)
    ]
    with REGION_DIFF.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(['region','x','y','w','h','mean_diff_pct'])
        for name,x,y,w,h in regions:
            crop = raw_diff.crop((x,y,x+w,y+h)).convert('L')
            score = sum(crop.histogram()[i] * i for i in range(256)) / (w*h*255)
            writer.writerow([name,x,y,w,h,round(score*100,4)])
    return {'status':'DIFF_BUILT','mean_diff_pct':round(diff_score*100,4)}

def main():
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    CAPTURE_JS.write_text(JS, encoding='utf-8')
    proc = run_server()
    log = wait_for_server(proc)
    capture_status = 1
    try:
        completed = subprocess.run(['node', str(CAPTURE_JS)], cwd=ROOT, text=True, capture_output=True, timeout=300)
        capture_status = completed.returncode
        server_runtime = {'server_log': log, 'capture_stdout': completed.stdout, 'capture_stderr': completed.stderr, 'capture_returncode': capture_status}
    finally:
        try:
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        except Exception:
            proc.terminate()
        try:
            proc.wait(timeout=8)
        except Exception:
            proc.kill()
    diff_info = make_diffs()
    summary = {'status':'FORM_GUIDE_CAPTURE_COMPLETE' if capture_status == 0 else 'FORM_GUIDE_CAPTURE_REVIEW_REQUIRED','timestamp':datetime.now().isoformat(timespec='seconds'), **server_runtime, 'diff':diff_info}
    (SHOT_DIR / '05_FORM_GUIDE_CAPTURE_SUMMARY.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(summary['status'])
    if capture_status != 0:
        raise SystemExit(capture_status)

if __name__ == '__main__':
    main()
