from __future__ import annotations
import csv
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
TSX = ROOT / "src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx"
TEXT_SPEC = ROOT / "docs/product-specification/FORM_GUIDE_APPROVED_TEXT_SPEC_V1.csv"
REPORT = ROOT / "docs/product-specification/FORM_GUIDE_EXACT_TEXT_APPLY_V1.json"

REQUIRED_LABELS = [
    "FORM GUIDE", "Ratings View", "CUSTOMISE COLUMNS", "EXPORT", "TODAY'S MATCH", "HORSE PROFILE (CAREER)", "TODAY'S MATCH INSIGHTS", "RECENT FORM", "EPI", "EDGEiQ PRICE", "MARKET"
]

def main():
    text = TSX.read_text(encoding="utf-8")
    with TEXT_SPEC.open(newline="", encoding="utf-8") as f:
        spec_rows = list(csv.DictReader(f))
    checks = [{"label": label, "present": label in text} for label in REQUIRED_LABELS]
    status = "FORM_GUIDE_EXACT_TEXT_APPLIED" if all(row["present"] for row in checks) else "FORM_GUIDE_EXACT_TEXT_REVIEW_REQUIRED"
    REPORT.write_text(json.dumps({"status":status, "required_label_checks":checks, "text_spec_rows":len(spec_rows), "timestamp":datetime.now().isoformat()}, indent=2), encoding="utf-8")
    print(json.dumps({"status":status, "missing":[r for r in checks if not r["present"]]}, indent=2))
if __name__ == "__main__":
    main()
