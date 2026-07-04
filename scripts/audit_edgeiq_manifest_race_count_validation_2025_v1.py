from __future__ import annotations

import csv
import json
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
TMP = ROOT / "outputs" / "tmp"
TMP.mkdir(parents=True, exist_ok=True)

INFILE = DATA / "edgeiq_vic_historical_backfill_manifest_2025_TEST.csv"
OUT = DATA / "edgeiq_manifest_race_count_validation_2025_v1.csv"
SUMMARY = DATA / "edgeiq_manifest_race_count_validation_2025_v1_summary.csv"

NODE = TMP / "edgeiq_validate_racingcom_race_counts_v1.cjs"
NODE_IN = TMP / "edgeiq_validate_racingcom_race_counts_v1_input.json"
NODE_OUT = TMP / "edgeiq_validate_racingcom_race_counts_v1_output.json"

MAX_MEETINGS = 120


def clean(v):
    return "" if v is None else str(v).strip()


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def meeting_key(r):
    return (clean(r.get("meeting_date")), clean(r.get("track")), clean(r.get("meeting_url")))


def main():
    built_at = datetime.now(timezone.utc).isoformat()
    rows = read_csv(INFILE)

    meetings = {}
    for r in rows:
        k = meeting_key(r)
        if k not in meetings:
            meetings[k] = {
                "meeting_date": k[0],
                "track": k[1],
                "meeting_url": k[2],
                "manifest_race_count": 0,
            }
        meetings[k]["manifest_race_count"] += 1

    sample = list(meetings.values())[:MAX_MEETINGS]

    NODE_IN.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")

    NODE.write_text(r'''
const fs = require("fs");
const { chromium } = require("playwright");

const inputPath = process.argv[2];
const outputPath = process.argv[3];
const meetings = JSON.parse(fs.readFileSync(inputPath, "utf8"));

function uniq(arr) {
  return [...new Set(arr)];
}

function extractRaceNumbersFromText(text) {
  const nums = [];
  const patterns = [
    /Race\s+(\d{1,2})\b/gi,
    /\/race\/(\d{1,2})\b/gi
  ];
  for (const p of patterns) {
    let m;
    while ((m = p.exec(text)) !== null) {
      const n = Number(m[1]);
      if (n >= 1 && n <= 20) nums.push(n);
    }
  }
  return uniq(nums).sort((a,b) => a-b);
}

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: ["--disable-dev-shm-usage", "--no-sandbox"]
  });

  const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });
  const results = [];

  for (const m of meetings) {
    const url = m.meeting_url;
    let out = {
      meeting_date: m.meeting_date,
      track: m.track,
      meeting_url: url,
      manifest_race_count: m.manifest_race_count,
      page_status: "UNKNOWN",
      actual_race_count: 0,
      actual_race_numbers: "",
      race_links_found: 0,
      notes: ""
    };

    try {
      await page.goto(url, { waitUntil: "load", timeout: 60000 });
      await page.waitForTimeout(2500);

      const bodyText = await page.locator("body").innerText({ timeout: 8000 }).catch(() => "");
      const hrefs = await page.locator("a").evaluateAll(els => els.map(a => a.href || "")).catch(() => []);

      const fromLinks = hrefs
        .map(h => {
          const mm = h.match(/\/race\/(\d{1,2})(?:\b|$|[/?#])/i);
          return mm ? Number(mm[1]) : null;
        })
        .filter(n => n !== null && n >= 1 && n <= 20);

      const fromText = extractRaceNumbersFromText(bodyText);
      const raceNumbers = uniq([...fromLinks, ...fromText]).sort((a,b) => a-b);

      out.page_status = bodyText.length > 200 ? "LOADED" : "LOW_TEXT";
      out.actual_race_count = raceNumbers.length;
      out.actual_race_numbers = raceNumbers.join("|");
      out.race_links_found = uniq(fromLinks).length;

      if (raceNumbers.length === 0) {
        out.notes = "NO_RACE_NUMBERS_FOUND_ON_MEETING_PAGE";
      } else if (raceNumbers.length !== Number(m.manifest_race_count)) {
        out.notes = "MANIFEST_COUNT_DIFFERS_FROM_RENDERED_MEETING";
      } else {
        out.notes = "COUNT_MATCH";
      }
    } catch (err) {
      out.page_status = "ERROR";
      out.notes = String(err).slice(0, 250);
    }

    results.push(out);
    console.log(`[VALIDATE] ${out.meeting_date} ${out.track} manifest=${out.manifest_race_count} actual=${out.actual_race_count} ${out.notes}`);
  }

  await browser.close();
  fs.writeFileSync(outputPath, JSON.stringify(results, null, 2), "utf8");
})();
''', encoding="utf-8")

    subprocess.run(
        ["node", str(NODE), str(NODE_IN), str(NODE_OUT)],
        cwd=str(ROOT),
        check=True,
    )

    validated = json.loads(NODE_OUT.read_text(encoding="utf-8"))

    fields = [
        "meeting_date", "track", "meeting_url", "manifest_race_count",
        "page_status", "actual_race_count", "actual_race_numbers",
        "race_links_found", "notes", "built_at",
    ]

    for r in validated:
        r["built_at"] = built_at

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(validated)

    loaded = sum(1 for r in validated if r["page_status"] == "LOADED")
    matched = sum(1 for r in validated if r["notes"] == "COUNT_MATCH")
    diff = sum(1 for r in validated if r["notes"] == "MANIFEST_COUNT_DIFFERS_FROM_RENDERED_MEETING")
    zero = sum(1 for r in validated if int(r["actual_race_count"] or 0) == 0)

    summary = [
        {"metric": "status", "value": "EDGEIQ_MANIFEST_RACE_COUNT_VALIDATION_2025_V1_BUILT"},
        {"metric": "input_manifest_rows", "value": len(rows)},
        {"metric": "unique_meetings_2025", "value": len(meetings)},
        {"metric": "sample_meetings_validated", "value": len(validated)},
        {"metric": "loaded_pages", "value": loaded},
        {"metric": "count_matches", "value": matched},
        {"metric": "count_differences", "value": diff},
        {"metric": "zero_actual_race_count", "value": zero},
        {"metric": "built_at", "value": built_at},
    ]

    with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("[EDGEIQ_MANIFEST_RACE_COUNT_VALIDATION_2025_V1] COMPLETE")
    print(f"output={OUT}")
    print(f"summary={SUMMARY}")


if __name__ == "__main__":
    main()
