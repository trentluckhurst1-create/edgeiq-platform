from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "full-product-implementation" / "screenshots" / "final-live-runtime"
APPROVED_DIR = ROOT / "docs" / "product-specification" / "EDGEIQ_APPROVED_UI_REBUILD" / "approved-pngs" / "EDGEiQ_APPROVED_TABS"

WORKSPACES = [
    ("01_HOME", "nav", "HOME"),
    ("02_MEETINGS", "nav", "MEETINGS"),
    ("03_RACE_OVERVIEW", "race-nav", "RACE"),
    ("04_FIELD", "race-nav", "FIELD"),
    ("05_FORM_GUIDE", "race-nav", "FORM GUIDE"),
    ("06_PERFORMANCE", "race-nav", "PERFORMANCE"),
    ("07_MAP", "race-nav", "MAP"),
    ("08_EPI", "race-nav", "EPI"),
    ("09_MARKET", "race-nav", "MARKET"),
    ("10_OVERVIEW", "race-nav", "OVERVIEW"),
    ("11_SCRATCHINGS", "meeting-tab", "SCRATCHINGS"),
    ("12_GEAR_CHANGES", "meeting-tab", "GEAR CHANGES"),
    ("13_TRACK", "meeting-tab", "TRACK"),
    ("14_WEATHER", "meeting-tab", "WEATHER"),
    ("15_RESULTS", "race-nav", "RESULTS"),
    ("16_INSIGHTS", "race-nav", "INSIGHTS"),
    ("17_LAB", "nav", "LAB"),
    ("18_COMPARE", "nav", "COMPARE"),
    ("19_REVIEW", "race-nav", "REVIEW"),
]


def approved_path(workspace: str) -> Path:
    src = APPROVED_DIR / f"{workspace}_APPROVED.png"
    if not src.exists():
        raise SystemExit(f"Missing approved image: {src}")
    return src


def write_capture_js(url: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    js_path = OUT_DIR / "edgeiq_capture_final_live_runtime_tmp.mjs"
    payload = json.dumps({"url": url, "outDir": str(OUT_DIR), "workspaces": WORKSPACES})
    js_path.write_text(
        f"""
import {{ chromium }} from 'playwright';
import fs from 'node:fs';

const config = {payload};
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const runtimeResults = [];

async function clickScoped(page, selector, label) {{
  const target = String(label).trim().toUpperCase();
  const items = page.locator(selector);
  const count = await items.count();
  for (let i = 0; i < count; i += 1) {{
    const item = items.nth(i);
    const text = ((await item.innerText().catch(() => '')) || '').trim().toUpperCase();
    if (text === target || text.includes(target)) {{
      await item.click();
      await sleep(900);
      return true;
    }}
  }}
  return false;
}}

async function clickPrimaryNav(page, label) {{
  return await clickScoped(page, '.eiq-app-nav button', label);
}}

async function ensureMeetingsList(page) {{
  await clickPrimaryNav(page, 'MEETINGS');
  await page.waitForLoadState('networkidle').catch(() => {{}});
  await sleep(900);
}}

async function ensureMeetingDetail(page) {{
  await ensureMeetingsList(page);
  if ((await page.locator('.eiq-meeting-workspace').count()) > 0) return true;
  const select = page.locator('.eiq-meetings-approved__select').first();
  if (await select.count()) {{
    await select.click();
    await sleep(500);
  }}
  if (await clickScoped(page, 'button', 'OPEN MEETING')) return true;
  const meeting = page.locator('.eiq-meetings-approved__meeting').first();
  if (await meeting.count()) {{
    await meeting.click();
    await sleep(400);
    if (await clickScoped(page, 'button', 'OPEN MEETING')) return true;
  }}
  return (await page.locator('.eiq-meeting-workspace').count()) > 0;
}}

async function ensureRaceWorkspace(page) {{
  if ((await page.locator('.eiq-race-workspace').count()) > 0) return true;
  await ensureMeetingDetail(page);
  await clickScoped(page, '.eiq-meeting-v1-tabs button', 'RACES');
  const row = page.locator('tr[role="button"][aria-label^="Open"]').first();
  if (await row.count()) {{
    await row.click();
    await sleep(1000);
  }}
  return (await page.locator('.eiq-race-workspace').count()) > 0;
}}

async function metadata(page, workspace, label, errors) {{
  const data = await page.evaluate(() => {{
    const mounted = Array.from(document.querySelectorAll('[data-edgeiq-mounted-component]')).map((node) => {{
      const el = node;
      return {{
        component: el.getAttribute('data-edgeiq-mounted-component'),
        key: el.getAttribute('data-edgeiq-workspace-key'),
        tag: el.tagName,
        className: el.getAttribute('class') || '',
      }};
    }});
    const state = (() => {{
      try {{ return JSON.parse(window.localStorage.getItem('edgeiq-os-racefile-v3-state') || '{{}}'); }} catch {{ return {{}}; }}
    }})();
    const bodyText = document.body.innerText || '';
    return {{
      mounted,
      mountedComponent: mounted.length ? mounted[mounted.length - 1].component : null,
      mountedKey: mounted.length ? mounted[mounted.length - 1].key : null,
      selectedMeeting: state.selectedMeetingKey || null,
      selectedRace: state.selectedRaceKey || null,
      activeSection: state.activeSection || null,
      viewLevel: state.viewLevel || null,
      runnerCount: document.querySelectorAll('tbody tr').length,
      dataAvailability: bodyText.includes('Unavailable') || bodyText.includes('Pending') ? 'PARTIAL_OR_PENDING' : 'AVAILABLE_OR_NOT_STATED',
      bodySample: bodyText.slice(0, 12000),
    }};
  }});
  return {{ workspace, label, captureErrors: errors.slice(), ...data }};
}}

async function capture(page, workspace, label, errors) {{
  await sleep(500);
  const renderedPath = `${{config.outDir}}/${{workspace}}_LIVE_RENDERED.png`;
  await page.screenshot({{ path: renderedPath, fullPage: false }});
  const meta = await metadata(page, workspace, label, errors);
  meta.renderedPath = renderedPath;
  fs.writeFileSync(`${{config.outDir}}/${{workspace}}_LIVE_RUNTIME.json`, JSON.stringify(meta, null, 2));
  runtimeResults.push(meta);
}}

const browser = await chromium.launch({{ headless: true }});
const page = await browser.newPage({{ viewport: {{ width: 1536, height: 1024 }}, deviceScaleFactor: 1 }});
const captureErrors = [];
page.on('pageerror', (error) => captureErrors.push({{ type: 'pageerror', message: String(error) }}));
page.on('console', (message) => {{ if (message.type() === 'error') captureErrors.push({{ type: 'console-error', message: message.text() }}); }});

await page.goto(config.url, {{ waitUntil: 'domcontentloaded', timeout: 60000 }});
await page.evaluate(() => {{
  try {{
    window.localStorage.setItem('edgeiq-os-racefile-v3-state', JSON.stringify({{ activeSection: 'meetings', viewLevel: 'meetings', selectedMeetingsDayKey: 'TODAY' }}));
  }} catch {{}}
}});
await page.reload({{ waitUntil: 'domcontentloaded', timeout: 60000 }});
await sleep(1200);

for (const [workspace, mode, label] of config.workspaces) {{
  if (mode === 'nav') {{
    await clickPrimaryNav(page, label);
  }} else if (mode === 'meeting-tab') {{
    const ok = await ensureMeetingDetail(page);
    if (!ok) captureErrors.push({{ type: 'navigation', workspace, message: 'Meeting detail could not be opened' }});
    await clickScoped(page, '.eiq-meeting-v1-tabs button', label);
  }} else if (mode === 'race-nav') {{
    await ensureRaceWorkspace(page);
    await clickPrimaryNav(page, label);
    await sleep(900);
    if ((await page.locator('.eiq-race-workspace').count()) === 0) {{
      captureErrors.push({{ type: 'navigation', workspace, message: 'Race workspace could not be opened after primary navigation' }});
    }}
  }}
  await page.waitForLoadState('networkidle').catch(() => {{}});
  await capture(page, workspace, label, captureErrors);
}}

await browser.close();
fs.writeFileSync(`${{config.outDir}}/EDGEIQ_FINAL_LIVE_RUNTIME_CAPTURE_V1.json`, JSON.stringify({{
  built_at: new Date().toISOString(),
  url: config.url,
  workspace_count: config.workspaces.length,
  capture_error_count: captureErrors.length,
  capture_errors: captureErrors,
  results: runtimeResults,
}}, null, 2));
""",
        encoding="utf-8",
    )
    return js_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:5182/")
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    js_path = write_capture_js(args.url)
    subprocess.run(["node", str(js_path)], cwd=ROOT, check=True)

    comparisons = []
    for workspace, _, _ in WORKSPACES:
        approved = approved_path(workspace)
        approved_copy = OUT_DIR / f"{workspace}_APPROVED.png"
        shutil.copyfile(approved, approved_copy)
        rendered = OUT_DIR / f"{workspace}_LIVE_RENDERED.png"
        subprocess.run(
            [
                "python",
                str(ROOT / "scripts" / "compare_edgeiq_workspace_to_approved_png_v1.py"),
                "--workspace",
                workspace,
                "--rendered",
                str(rendered),
                "--approved",
                str(approved_copy),
                "--out-dir",
                str(OUT_DIR),
            ],
            cwd=ROOT,
            check=True,
        )
        comparisons.append(json.loads((OUT_DIR / f"{workspace}_COMPARISON.json").read_text(encoding="utf-8")))

    capture = json.loads((OUT_DIR / "EDGEIQ_FINAL_LIVE_RUNTIME_CAPTURE_V1.json").read_text(encoding="utf-8"))
    summary = {
        "built_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "workspace_count": len(WORKSPACES),
        "live_rendered_count": sum((OUT_DIR / f"{workspace}_LIVE_RENDERED.png").exists() for workspace, _, _ in WORKSPACES),
        "approved_copy_count": sum((OUT_DIR / f"{workspace}_APPROVED.png").exists() for workspace, _, _ in WORKSPACES),
        "overlay_count": sum((OUT_DIR / f"{workspace}_OVERLAY.png").exists() for workspace, _, _ in WORKSPACES),
        "diff_count": sum((OUT_DIR / f"{workspace}_DIFF.png").exists() for workspace, _, _ in WORKSPACES),
        "runtime_json_count": sum((OUT_DIR / f"{workspace}_LIVE_RUNTIME.json").exists() for workspace, _, _ in WORKSPACES),
        "comparison_count": len(comparisons),
        "capture_error_count": capture.get("capture_error_count", 0),
        "average_rms_difference": round(sum(item["rms_difference"] for item in comparisons) / max(1, len(comparisons)), 3),
        "status": "EDGEIQ_FINAL_LIVE_RUNTIME_CAPTURE_COMPLETE",
    }
    (OUT_DIR / "EDGEIQ_FINAL_LIVE_RUNTIME_CAPTURE_V1_SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()




