from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ROOT / "src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx",
    ROOT / "src/edgeiq-os/race/services/formGuideNormaliser.ts",
    ROOT / "src/edgeiq-os/race/services/formGuideWorkspaceViewModel.ts",
]
REPORT = ROOT / "docs/product-specification/FORM_GUIDE_EXACT_VIEW_MODEL_APPLY_V1.json"
REQUIRED = {
    "summary_columns": ["NO", "SILKS", "LAST 5", "HORSE", "TRAINER", "JOCKEY", "WT", "BAR", "DAYS", "EPI", "EARLY SPEED", "LATE SPEED", "SUITABILITY", "FORM MOMENTUM", "MARKET", "EDGEiQ PRICE", "EDGE", "FLUC 60s %"],
    "runner_fields": ["careerProfile", "conditionProfile", "classProfile", "jockeyProfile", "raceDayPattern", "recentRuns", "epiRank", "epiFieldAverage", "epiDifference"],
    "live_feed_functions": ["loadFormGuideEnrichedFeed", "findEnrichedFormGuideRace", "normaliseFormGuideRace"],
}

def main():
    text = "\n".join(path.read_text(encoding="utf-8") for path in FILES if path.exists())
    checks = []
    for category, values in REQUIRED.items():
        for value in values:
            checks.append({"category": category, "item": value, "present": value in text})
    status = "FORM_GUIDE_VIEW_MODEL_COMPLETE" if all(row["present"] for row in checks) else "FORM_GUIDE_VIEW_MODEL_REVIEW_REQUIRED"
    REPORT.write_text(json.dumps({"status":status, "checks":checks, "timestamp":datetime.now().isoformat()}, indent=2), encoding="utf-8")
    print(json.dumps({"status":status, "missing":[r for r in checks if not r["present"]]}, indent=2))
if __name__ == "__main__":
    main()
