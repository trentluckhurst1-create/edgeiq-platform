from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
TSX = ROOT / "src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx"
REPORT = ROOT / "docs/product-specification/FORM_GUIDE_EXACT_TEXT_APPLY_MUTATIONS_V1.json"

def main():
    text = TSX.read_text(encoding="utf-8")
    replacements = [
        ("<h3>Today's Match</h3>", "<h3>TODAY'S MATCH</h3>"),
        ("<h3>Key Insights</h3>", "<h3>TODAY'S MATCH INSIGHTS</h3>"),
        ("<strong>Last 8 Starts</strong>", "<strong>LAST 8 STARTS</strong>"),
    ]
    applied = []
    for old, new in replacements:
        if old in text:
            text = text.replace(old, new, 1)
            applied.append(old)
    TSX.write_text(text, encoding="utf-8")
    REPORT.write_text(json.dumps({"status":"FORM_GUIDE_EXACT_TEXT_MUTATIONS_APPLIED", "applied":applied, "timestamp":datetime.now().isoformat()}, indent=2), encoding="utf-8")
    print(json.dumps({"status":"FORM_GUIDE_EXACT_TEXT_MUTATIONS_APPLIED", "applied":applied}, indent=2))
if __name__ == "__main__":
    main()
