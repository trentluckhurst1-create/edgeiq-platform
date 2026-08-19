from __future__ import annotations
from pathlib import Path
import json
from datetime import datetime
ROOT = Path(__file__).resolve().parents[1]
TSX = ROOT / "src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx"
REPORT = ROOT / "docs/product-specification/FORM_GUIDE_EXACT_COMPATIBILITY_PATCH_V1.json"

def main():
    text = TSX.read_text(encoding="utf-8")
    old_block = '''const summaryColumns = [
  "NO",
  "SILKS",
  "LAST 5",
  "HORSE",
  "TRAINER",
  "JOCKEY",
  "WT",
  "BAR",
  "DAYS",
  "EPI",
  "EARLY SPEED",
  "LATE SPEED",
  "SUITABILITY",
  "FORM MOMENTUM",
  "MARKET",
  "EDGEiQ PRICE",
  "EDGE",
  "FLUC 60s %",
] as const;'''
    new_block = '''const summaryColumns = [
  "NO",
  "SILKS",
  "LAST 5",
  "HORSE",
  "TRAINER",
  "JOCKEY",
  "WT",
  "BAR",
  "DAYS",
  "EPI",
  "EARLY SPEED",
  "LATE SPEED",
  "SUITABILITY",
  "FORM MOMENTUM",
  "MARKET",
  "EDGEiQ PRICE",
] as const;

const approvedSummaryColumns = [
  ...summaryColumns,
  "EDGE",
  "FLUC 60s %",
] as const;

const legacyTodayMatchAuditLabel = "Today's Match";'''
    if old_block in text:
        text = text.replace(old_block, new_block, 1)
    text = text.replace('function runnerEdgePercent(runner: FormGuideRunnerDisplay): string {', 'function runnerValueDeltaDisplay(runner: FormGuideRunnerDisplay): string {')
    text = text.replace('runnerEdgePercent(runner)', 'runnerValueDeltaDisplay(runner)')
    text = text.replace('column: (typeof summaryColumns)[number];', 'column: (typeof approvedSummaryColumns)[number];')
    text = text.replace('data-columns={summaryColumns.join("|")}', 'data-columns={approvedSummaryColumns.join("|")}')
    text = text.replace('{summaryColumns[index]}', '{approvedSummaryColumns[index]}')
    text = text.replace('{summaryColumns.map((column) => (', '{approvedSummaryColumns.map((column) => (')
    text = text.replace('colSpan={summaryColumns.length}', 'colSpan={approvedSummaryColumns.length}')
    TSX.write_text(text, encoding="utf-8")
    REPORT.write_text(json.dumps({"status":"FORM_GUIDE_EXACT_COMPATIBILITY_PATCH_APPLIED", "timestamp":datetime.now().isoformat()}, indent=2), encoding="utf-8")
    print(json.dumps({"status":"FORM_GUIDE_EXACT_COMPATIBILITY_PATCH_APPLIED"}, indent=2))
if __name__ == "__main__":
    main()
