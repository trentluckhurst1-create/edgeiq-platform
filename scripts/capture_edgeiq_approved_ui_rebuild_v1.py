from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "full-product-implementation" / "screenshots" / "approved-ui-rebuild"
APPROVED_DIR = (
    ROOT
    / "docs"
    / "product-specification"
    / "EDGEIQ_APPROVED_UI_REBUILD"
    / "approved-pngs"
    / "EDGEiQ_APPROVED_TABS"
)

WORKSPACES = [
    ("01_HOME", "nav", "HOME"),
    ("02_MEETINGS", "nav", "MEETINGS"),
    ("03_RACE_OVERVIEW", "nav", "RACE"),
    ("04_FIELD", "nav", "FIELD"),
    ("05_FORM_GUIDE", "nav", "FORM GUIDE"),
    ("06_PERFORMANCE", "nav", "PERFORMANCE"),
    ("07_MAP", "nav", "MAP"),
    ("08_EPI", "nav", "EPI"),
    ("09_MARKET", "nav", "MARKET"),
    ("10_OVERVIEW", "nav", "OVERVIEW"),
    ("11_SCRATCHINGS", "meeting-tab", "SCRATCHINGS"),
    ("12_GEAR_CHANGES", "meeting-tab", "GEAR CHANGES"),
    ("13_TRACK", "meeting-tab", "TRACK"),
    ("14_WEATHER", "meeting-tab", "WEATHER"),
    ("15_RESULTS", "meeting-tab", "RESULTS"),
    ("16_INSIGHTS", "nav", "INSIGHTS"),
    ("17_LAB", "nav", "LAB"),
    ("18_COMPARE", "nav", "COMPARE"),
    ("19_REVIEW", "nav", "REVIEW"),
]


def write_capture_js(url: str) -> Path:
    js_path = OUT_DIR / "edgeiq_capture_approved_ui_tmp.mjs"
    payload = json.dumps({"url": url, "outDir": str(OUT_DIR), "workspaces": WORKSPACES})
    js_path.write_text(
        f"""
import {{ chromium }} from 'playwright';
import fs from 'node:fs';

const config = {payload};

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function clickButton(page, label) {{
  const exact = page.locator('button').filter({{ hasText: label }}).first();
  if (await exact.count()) {{
    await exact.click();
    await sleep(900);
    return true;
  }}
  return false;
}}

async function ensureMeetingDetail(page) {{
  await clickButton(page, 'MEETINGS');
  await sleep(700);
  if ((await page.locator('text=SCRATCHINGS').count()) > 0) return;
  await clickButton(page, 'OPEN MEETING');
  await sleep(1000);
}}

const browser = await chromium.launch({{ headless: true }});
const page = await browser.newPage({{ viewport: {{ width: 1536, height: 1024 }}, deviceScaleFactor: 1 }});
const results = [];

page.on('pageerror', (error) => {{
  results.push({{ type: 'pageerror', message: String(error) }});
}});
page.on('console', (message) => {{
  if (message.type() === 'error') results.push({{ type: 'console-error', message: message.text() }});
}});

await page.goto(config.url, {{ waitUntil: 'networkidle' }});
await page.evaluate(() => {{
  try {{
    window.localStorage.setItem('edgeiq-os-racefile-v3-state', JSON.stringify({{ activeSection: 'meetings', viewLevel: 'meetings' }}));
  }} catch {{}}
}});
await page.reload({{ waitUntil: 'networkidle' }});
await sleep(1000);

for (const [workspace, mode, label] of config.workspaces) {{
  if (mode === 'nav') {{
    await clickButton(page, label);
  }} else {{
    await ensureMeetingDetail(page);
    await clickButton(page, label);
  }}
  await sleep(900);
  const renderedPath = `${{config.outDir}}/${{workspace}}_RENDERED.png`;
  await page.screenshot({{ path: renderedPath, fullPage: false }});
  const text = (await page.locator('body').innerText()).slice(0, 1600);
  results.push({{ workspace, label, renderedPath, bodySample: text }});
}}

await browser.close();
fs.writeFileSync(`${{config.outDir}}/EDGEIQ_APPROVED_UI_CAPTURE_V1.json`, JSON.stringify({{
  built_at: new Date().toISOString(),
  url: config.url,
  workspace_count: config.workspaces.length,
  results,
}}, null, 2));
""",
        encoding="utf-8",
    )
    return js_path


def copy_approved(workspace: str) -> Path:
    src = APPROVED_DIR / f"{workspace}_APPROVED.png"
    dst = OUT_DIR / f"{workspace}_APPROVED.png"
    if not src.exists():
        raise SystemExit(f"Missing approved PNG: {src}")
    shutil.copyfile(src, dst)
    return dst


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:5181/")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    js_path = write_capture_js(args.url)
    subprocess.run(["node", str(js_path)], cwd=ROOT, check=True)

    comparisons = []
    for workspace, _, _ in WORKSPACES:
      approved = copy_approved(workspace)
      rendered = OUT_DIR / f"{workspace}_RENDERED.png"
      subprocess.run(
          [
              "python",
              str(ROOT / "scripts" / "compare_edgeiq_workspace_to_approved_png_v1.py"),
              "--workspace",
              workspace,
              "--rendered",
              str(rendered),
              "--approved",
              str(approved),
          ],
          cwd=ROOT,
          check=True,
      )
      comparison_path = OUT_DIR / f"{workspace}_COMPARISON.json"
      comparisons.append(json.loads(comparison_path.read_text(encoding="utf-8")))

    summary = {
        "built_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "workspace_count": len(WORKSPACES),
        "rendered_count": sum((OUT_DIR / f"{workspace}_RENDERED.png").exists() for workspace, _, _ in WORKSPACES),
        "approved_copy_count": sum((OUT_DIR / f"{workspace}_APPROVED.png").exists() for workspace, _, _ in WORKSPACES),
        "overlay_count": sum((OUT_DIR / f"{workspace}_OVERLAY.png").exists() for workspace, _, _ in WORKSPACES),
        "diff_count": sum((OUT_DIR / f"{workspace}_DIFF.png").exists() for workspace, _, _ in WORKSPACES),
        "comparison_count": len(comparisons),
        "average_rms_difference": round(sum(item["rms_difference"] for item in comparisons) / max(1, len(comparisons)), 3),
        "status": "EDGEIQ_APPROVED_UI_CAPTURE_AND_COMPARISON_COMPLETE",
    }
    (OUT_DIR / "EDGEIQ_APPROVED_UI_CAPTURE_AND_COMPARISON_V1_SUMMARY.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
