from __future__ import annotations
import argparse
import csv
import json
import subprocess
from datetime import datetime
from pathlib import Path
from shutil import copy2

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/full-product-implementation/screenshots/form-guide-exact"
APPROVED = OUT / "05_FORM_GUIDE_APPROVED.png"
LIVE = OUT / "05_FORM_GUIDE_LIVE_RENDERED.png"
OVERLAY = OUT / "05_FORM_GUIDE_OVERLAY_50.png"
DIFF = OUT / "05_FORM_GUIDE_DIFF.png"
EDGE_DIFF = OUT / "05_FORM_GUIDE_EDGE_DIFF.png"
REGION_DIFF = OUT / "05_FORM_GUIDE_REGION_DIFF.csv"
RUNTIME = OUT / "05_FORM_GUIDE_RUNTIME.json"
SPEC = ROOT / "docs/product-specification/FORM_GUIDE_APPROVED_PIXEL_SPEC_V1.json"

def write_js(url: str) -> Path:
    js = OUT / "edgeiq_form_guide_exact_capture_tmp.mjs"
    payload = json.dumps({"url": url, "live": str(LIVE), "runtime": str(RUNTIME).replace('\\', '\\\\')})
    js.write_text(f"""
import {{ chromium }} from 'playwright';
import fs from 'node:fs';
const config = {payload};
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const events = [];
async function clickText(page, text) {{
  const locator = page.locator('button, a, [role="button"]').filter({{ hasText: text }}).first();
  if (await locator.count()) {{ await locator.click(); await sleep(800); return true; }}
  return false;
}}
async function firstButtonContaining(page, text) {{
  const locator = page.locator('button').filter({{ hasText: text }}).first();
  if (await locator.count()) {{ await locator.click(); await sleep(1000); return true; }}
  return false;
}}
const browser = await chromium.launch({{ headless: true }});
const page = await browser.newPage({{ viewport: {{ width: 1536, height: 1024 }}, deviceScaleFactor: 1 }});
page.on('console', (msg) => {{ if (msg.type() === 'error') events.push({{ type: 'console-error', text: msg.text() }}); }});
page.on('pageerror', (err) => events.push({{ type: 'pageerror', text: String(err) }}));
page.on('requestfailed', (request) => events.push({{ type: 'requestfailed', url: request.url(), failure: request.failure()?.errorText }}));
await page.goto(config.url, {{ waitUntil: 'domcontentloaded', timeout: 90000 }});
await page.evaluate(() => {{
  try {{ window.localStorage.setItem('edgeiq-os-racefile-v3-state', JSON.stringify({{ activeSection: 'meetings', viewLevel: 'meetings', selectedMeetingsDayKey: 'TODAY' }})); }} catch {{}}
}});
await page.reload({{ waitUntil: 'domcontentloaded', timeout: 90000 }});
await sleep(1400);
await clickText(page, 'ENTER TERMINAL');
await sleep(900);
if (!(await firstButtonContaining(page, 'OPEN RACE'))) {{
  await firstButtonContaining(page, 'OPEN MEETING');
  await sleep(900);
  await firstButtonContaining(page, 'OPEN RACE');
}}
await sleep(1200);
await clickText(page, 'FORM GUIDE');
await sleep(1800);
let exactCount = await page.locator('[data-edgeiq-workspace="form-guide-approved-exact"]').count();
if (!exactCount) {{
  await clickText(page, 'FORM GUIDE');
  await sleep(1000);
  exactCount = await page.locator('[data-edgeiq-workspace="form-guide-approved-exact"]').count();
}}
const regions = await page.evaluate(() => {{
  const rows = [];
  document.querySelectorAll('[data-region]').forEach((node) => {{
    const rect = node.getBoundingClientRect();
    rows.push({{
      region: node.getAttribute('data-region'),
      x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height),
      visible: rect.width > 0 && rect.height > 0,
      tag: node.tagName.toLowerCase(),
      className: String(node.getAttribute('class') || '')
    }});
  }});
  return rows;
}});
const bodyText = await page.locator('body').innerText().catch(() => '');
await page.screenshot({{ path: config.live, fullPage: false }});
const runtime = {{
  status: exactCount ? 'FORM_GUIDE_LIVE_CAPTURED' : 'FORM_GUIDE_WORKSPACE_NOT_FOUND',
  url: config.url,
  captured_at: new Date().toISOString(),
  exactWorkspaceCount: exactCount,
  bodySample: bodyText.slice(0, 2000),
  regions,
  events,
}};
fs.writeFileSync(config.runtime, JSON.stringify(runtime, null, 2));
await browser.close();
if (!exactCount) process.exitCode = 2;
""", encoding="utf-8")
    return js

def make_images():
    from PIL import Image, ImageChops, ImageFilter, ImageOps
    approved = Image.open(APPROVED).convert("RGB")
    live = Image.open(LIVE).convert("RGB")
    if live.size != approved.size:
        live = live.resize(approved.size)
        live.save(LIVE)
    Image.blend(approved, live, 0.5).save(OVERLAY)
    diff = ImageChops.difference(approved, live)
    diff.save(DIFF)
    a_edge = ImageOps.grayscale(approved).filter(ImageFilter.FIND_EDGES)
    l_edge = ImageOps.grayscale(live).filter(ImageFilter.FIND_EDGES)
    ImageChops.difference(a_edge, l_edge).save(EDGE_DIFF)
    hist = diff.histogram()
    sq = sum((i % 256) ** 2 * count for i, count in enumerate(hist))
    total = approved.size[0] * approved.size[1] * 3
    rms = (sq / max(1, total)) ** 0.5
    return rms

def write_region_diff():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    runtime = json.loads(RUNTIME.read_text(encoding="utf-8"))
    live_by_region = {}
    for row in runtime.get("regions", []):
        live_by_region.setdefault(row.get("region"), row)
    rows = []
    for region in spec.get("regions", []):
        rid = region["id"]
        live = live_by_region.get(rid) or live_by_region.get(rid.replace("canvas", ""))
        if rid == "canvas":
            continue
        if not live:
            rows.append({"region":rid, "status":"MISSING", "spec_x":region["x"], "spec_y":region["y"], "spec_w":region["w"], "spec_h":region["h"], "live_x":"", "live_y":"", "live_w":"", "live_h":"", "delta_total":""})
            continue
        delta = abs(int(live["x"]) - region["x"]) + abs(int(live["y"]) - region["y"]) + abs(int(live["w"]) - region["w"]) + abs(int(live["h"]) - region["h"])
        rows.append({"region":rid, "status":"MEASURED", "spec_x":region["x"], "spec_y":region["y"], "spec_w":region["w"], "spec_h":region["h"], "live_x":live["x"], "live_y":live["y"], "live_w":live["w"], "live_h":live["h"], "delta_total":delta})
    with REGION_DIFF.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["region","status","spec_x","spec_y","spec_w","spec_h","live_x","live_y","live_w","live_h","delta_total"])
        writer.writeheader(); writer.writerows(rows)
    return rows

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:5173/")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if not APPROVED.exists():
        src = ROOT / "docs/full-product-implementation/screenshots/approved-ui-rebuild/05_FORM_GUIDE_APPROVED.png"
        copy2(src, APPROVED)
    js = write_js(args.url)
    subprocess.run(["node", str(js)], cwd=ROOT, check=False)
    if not LIVE.exists():
        raise SystemExit("Live screenshot was not captured")
    rms = make_images()
    rows = write_region_diff()
    runtime = json.loads(RUNTIME.read_text(encoding="utf-8"))
    runtime["pixel_rms_difference"] = round(rms, 3)
    runtime["region_diff_rows"] = len(rows)
    runtime["outputs"] = [str(APPROVED), str(LIVE), str(OVERLAY), str(DIFF), str(EDGE_DIFF), str(REGION_DIFF), str(RUNTIME)]
    RUNTIME.write_text(json.dumps(runtime, indent=2), encoding="utf-8")
    print(json.dumps({"status": runtime.get("status"), "pixel_rms_difference": round(rms,3), "region_rows": len(rows), "events": len(runtime.get("events", []))}, indent=2))

if __name__ == "__main__":
    main()


