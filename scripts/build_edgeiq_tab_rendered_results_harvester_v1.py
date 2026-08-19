import json
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RACECARDS = DATA / "edgeiq_tab_vic_racecards_v1.csv"
OUT = DATA / "edgeiq_tab_results_warehouse_v1.csv"
AUDIT = DATA / "edgeiq_tab_results_warehouse_v1_audit.csv"
RAW_DIR = DATA / "edgeiq_tab_rendered_results_raw_v1"
HELPER = ROOT / "scripts" / "edgeiq_tab_rendered_results_helper_v1.cjs"

RAW_DIR.mkdir(parents=True, exist_ok=True)

COLUMNS = [
    "scraped_at","source","meeting_date","track","race_no","horse","horse_canon",
    "runner_no","finish_position_raw","finish_position","result_status",
    "tab_fixed_win","tab_fixed_place","fixed_win_dividend","fixed_place_dividend",
    "tab_fixed_betting_status","tab_url","extract_method"
]

HELPER_CODE = r"""
const { chromium } = require("playwright");
const fs = require("fs");

async function main() {
  const url = process.argv[2];
  const outPath = process.argv[3];

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 2200 },
    userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 EDGEiQ"
  });

  const payload = {
    url,
    ok: false,
    error: "",
    title: "",
    text: "",
    scripts: [],
    htmlSnippet: ""
  };

  try {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 });
    await page.waitForTimeout(7000);

    payload.title = await page.title().catch(() => "");
    payload.text = await page.locator("body").innerText({ timeout: 10000 }).catch(() => "");

    const scripts = await page.locator("script").evaluateAll(nodes =>
      nodes.map(n => n.textContent || "").filter(t => t && t.length > 100)
    ).catch(() => []);

    payload.scripts = scripts.slice(0, 80);
    payload.htmlSnippet = (await page.content()).slice(0, 500000);
    payload.ok = true;
  } catch (e) {
    payload.error = String(e && e.stack ? e.stack : e);
  }

  fs.writeFileSync(outPath, JSON.stringify(payload, null, 2), "utf8");
  await browser.close();
}

main().catch(e => {
  fs.writeFileSync(process.argv[3], JSON.stringify({ ok:false, error:String(e && e.stack ? e.stack : e) }, null, 2), "utf8");
  process.exit(0);
});
"""

def canon(x):
    s = "" if pd.isna(x) else str(x).upper().strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]+", "", s)
    return s

def safe(x):
    if x is None:
        return ""
    if isinstance(x, float) and pd.isna(x):
        return ""
    return str(x).strip()

def num(x):
    try:
        s = safe(x).replace("$", "").strip()
        return float(s) if s else np.nan
    except Exception:
        return np.nan

def build_tab_url(meeting_date, track, race_no):
    track_url = re.sub(r"[^A-Z0-9]+", "-", safe(track).upper()).strip("-")
    return f"https://www.tab.com.au/racing/{meeting_date}/{track_url}/M/R/{race_no}"

def extract_positions_from_text(text, card_runners):
    text_up = text.upper()
    rows = []

    # Direct nearby-text method. TAB often renders runner names around result labels.
    for _, r in card_runners.iterrows():
        horse = safe(r.get("horse"))
        hcanon = canon(horse)
        if not hcanon:
            continue

        # Search original text chunks around the horse name.
        horse_pattern = re.escape(horse.upper())
        finish = np.nan
        raw = ""

        idx = text_up.find(horse.upper())
        if idx >= 0:
            chunk = text_up[max(0, idx - 500): idx + 800]
            patterns = [
                r"(?:1ST|1\s*ST|FIRST|PLACE\s*1|POSITION\s*1)",
                r"(?:2ND|2\s*ND|SECOND|PLACE\s*2|POSITION\s*2)",
                r"(?:3RD|3\s*RD|THIRD|PLACE\s*3|POSITION\s*3)",
                r"(?:4TH|4\s*TH|FOURTH|PLACE\s*4|POSITION\s*4)",
            ]

            for i, p in enumerate(patterns, start=1):
                if re.search(p, chunk):
                    finish = float(i)
                    raw = str(i)
                    break

            # Some pages show "1  HORSE", "2  HORSE" in result lists.
            if pd.isna(finish):
                compact = re.sub(r"\s+", " ", chunk)
                for i in range(1, 5):
                    if re.search(rf"\b{i}\b\s+{horse_pattern}", compact):
                        finish = float(i)
                        raw = str(i)
                        break

        if pd.notna(finish):
            rows.append((hcanon, raw, finish))

    return rows

def extract_positions_from_jsonish(payload, card_runners):
    blob = json.dumps(payload, ensure_ascii=False)
    rows = []

    for _, r in card_runners.iterrows():
        horse = safe(r.get("horse"))
        hcanon = canon(horse)
        if not hcanon:
            continue

        # Look for the horse inside script/json blobs and nearby position fields.
        for m in re.finditer(re.escape(horse), blob, flags=re.I):
            chunk = blob[max(0, m.start() - 1200): m.end() + 1200]

            pats = [
                r'"(?:finishPosition|finish_position|resultPosition|placing|position)"\s*:\s*"?([1-4])"?',
                r'"(?:place|rank)"\s*:\s*"?([1-4])"?',
                r'(?:finishPosition|resultPosition|placing|position)[^0-9]{0,20}([1-4])',
            ]

            for p in pats:
                mm = re.search(p, chunk, flags=re.I)
                if mm:
                    rows.append((hcanon, mm.group(1), float(mm.group(1))))
                    break

            if rows and rows[-1][0] == hcanon:
                break

    return rows

def main():
    if not RACECARDS.exists():
        raise FileNotFoundError(f"Missing racecards: {RACECARDS}")

    HELPER.write_text(HELPER_CODE, encoding="utf-8")

    cards = pd.read_csv(RACECARDS)

    races = (
        cards[["meeting_date","meeting_name","race_no"]]
        .drop_duplicates()
        .sort_values(["meeting_date","meeting_name","race_no"])
        .reset_index(drop=True)
    )

    all_rows = []
    audit_rows = []

    for _, race in races.iterrows():
        meeting_date = safe(race["meeting_date"])[:10]
        track = safe(race["meeting_name"]).upper()
        race_no = safe(race["race_no"])

        url = build_tab_url(meeting_date, track, race_no)
        raw_path = RAW_DIR / f"{meeting_date}_{track}_R{race_no}.json".replace(" ", "_")

        status = "UNKNOWN"
        error = ""
        before = len(all_rows)

        try:
            subprocess.run(
                ["node", str(HELPER), url, str(raw_path)],
                cwd=str(ROOT),
                timeout=80,
                check=False
            )

            if not raw_path.exists():
                status = "NO_RAW_OUTPUT"
                error = "helper produced no file"
            else:
                payload = json.loads(raw_path.read_text(encoding="utf-8"))
                if not payload.get("ok"):
                    status = "RENDER_ERROR"
                    error = safe(payload.get("error"))[:500]
                else:
                    race_cards = cards[
                        (cards["meeting_date"].astype(str).str.slice(0, 10) == meeting_date) &
                        (cards["meeting_name"].astype(str).str.upper().str.strip() == track) &
                        (cards["race_no"].astype(str) == str(race_no))
                    ].copy()

                    found = extract_positions_from_jsonish(payload, race_cards)
                    method = "JSONISH"

                    if not found:
                        found = extract_positions_from_text(payload.get("text", ""), race_cards)
                        method = "VISIBLE_TEXT"

                    found_map = {}
                    for hcanon, raw, fp in found:
                        if hcanon not in found_map:
                            found_map[hcanon] = (raw, fp)

                    for _, runner in race_cards.iterrows():
                        horse = safe(runner.get("horse"))
                        hcanon = canon(horse)
                        raw, fp = found_map.get(hcanon, ("", np.nan))

                        bet_status = safe(runner.get("tab_fixed_betting_status"))
                        result_status = "RESULT" if pd.notna(fp) else "PENDING_OR_NO_POSITION"

                        if "SCRATCH" in bet_status.upper():
                            result_status = "SCRATCHED"

                        all_rows.append({
                            "scraped_at": datetime.now().isoformat(timespec="seconds"),
                            "source": "TAB_RENDERED",
                            "meeting_date": meeting_date,
                            "track": track,
                            "race_no": race_no,
                            "horse": horse,
                            "horse_canon": hcanon,
                            "runner_no": safe(runner.get("runner_no")),
                            "finish_position_raw": raw,
                            "finish_position": fp,
                            "result_status": result_status,
                            "tab_fixed_win": num(runner.get("tab_fixed_win")),
                            "tab_fixed_place": num(runner.get("tab_fixed_place")),
                            "fixed_win_dividend": num(runner.get("tab_fixed_win")),
                            "fixed_place_dividend": num(runner.get("tab_fixed_place")),
                            "tab_fixed_betting_status": bet_status,
                            "tab_url": url,
                            "extract_method": method,
                        })

                    status = "ROWS_BUILT"

        except subprocess.TimeoutExpired:
            status = "TIMEOUT"
            error = "node helper timed out"
        except Exception as e:
            status = "ERROR"
            error = repr(e)

        audit_rows.append({
            "meeting_date": meeting_date,
            "track": track,
            "race_no": race_no,
            "tab_url": url,
            "status": status,
            "rows_added": len(all_rows) - before,
            "error": error,
        })

    new = pd.DataFrame(all_rows, columns=COLUMNS)

    if OUT.exists():
        try:
            old = pd.read_csv(OUT)
        except Exception:
            old = pd.DataFrame(columns=COLUMNS)
        combined = pd.concat([old, new], ignore_index=True)
        if len(combined):
            combined = combined.drop_duplicates(["meeting_date","track","race_no","horse_canon"], keep="last")
    else:
        combined = new

    combined = combined.reindex(columns=COLUMNS)
    combined.to_csv(OUT, index=False)

    summary = pd.DataFrame([
        {"metric": "races_checked", "value": len(races)},
        {"metric": "rows_built_this_run", "value": len(new)},
        {"metric": "warehouse_total_rows", "value": len(combined)},
        {"metric": "finish_positions", "value": int(pd.to_numeric(combined["finish_position"], errors="coerce").notna().sum()) if len(combined) else 0},
        {"metric": "result_rows", "value": int((combined["result_status"].astype(str) == "RESULT").sum()) if len(combined) else 0},
    ])

    audit = pd.concat([summary, pd.DataFrame(audit_rows)], ignore_index=True)
    audit.to_csv(AUDIT, index=False)

    print("[TAB_RENDERED_RESULTS_HARVESTER_V1] COMPLETE")
    print(f"races_checked={len(races)}")
    print(f"rows_built_this_run={len(new)}")
    print(f"warehouse_total_rows={len(combined)}")
    print(f"finish_positions={int(pd.to_numeric(combined['finish_position'], errors='coerce').notna().sum()) if len(combined) else 0}")
    print(f"wrote={OUT}")
    print(f"audit={AUDIT}")

if __name__ == "__main__":
    main()
