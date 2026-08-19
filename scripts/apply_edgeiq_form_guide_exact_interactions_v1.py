from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
TSX = ROOT / "src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx"
REPORT = ROOT / "docs/product-specification/FORM_GUIDE_EXACT_INTERACTIONS_APPLY_V1.json"
REQUIRED = {
    "runner_expand_toggle": "setExpandedRunnerId",
    "scroll_to_runner": "scrollToRunner(runner)",
    "metric_tooltip": "setActiveTooltip",
    "ratings_select": "aria-label=\"Ratings View\"",
    "customise_columns_button": "+ CUSTOMISE COLUMNS",
    "export_button": "EXPORT",
}

def main():
    text = TSX.read_text(encoding="utf-8")
    checks = [{"interaction":k, "present":v in text} for k,v in REQUIRED.items()]
    status = "FORM_GUIDE_EXACT_INTERACTIONS_APPLIED" if all(row["present"] for row in checks) else "FORM_GUIDE_EXACT_INTERACTIONS_REVIEW_REQUIRED"
    REPORT.write_text(json.dumps({"status":status, "checks":checks, "timestamp":datetime.now().isoformat()}, indent=2), encoding="utf-8")
    print(json.dumps({"status":status, "missing":[r for r in checks if not r["present"]]}, indent=2))
if __name__ == "__main__":
    main()
