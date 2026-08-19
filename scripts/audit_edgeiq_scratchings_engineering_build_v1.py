from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "public" / "data" / "edgeiq_scratchings_engineering_build_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_scratchings_engineering_build_v1_audit.txt"
CATALOG = ROOT / "public" / "data" / "edgeiq_three_day_product_catalog_v1.json"

audits = [
    "audit_edgeiq_scratchings_data_contract_v1.py",
    "audit_edgeiq_effective_barriers_v1.py",
    "audit_edgeiq_scratchings_downstream_refresh_v1.py",
    "audit_edgeiq_scratchings_visual_structure_v1.py",
]

results = {}
for audit in audits:
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / audit)], cwd=ROOT, text=True, capture_output=True)
    results[audit] = {
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "passed": proc.returncode == 0 and "PASS" in proc.stdout,
    }

catalog_summary = {"meetings": 0, "races": 0, "runners": 0, "official_scratched_flags": 0, "current_scratchings": 0}
if CATALOG.exists():
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    meetings = data.get("meetings", [])
    catalog_summary["meetings"] = len(meetings)
    for meeting in meetings:
        for race in meeting.get("races", []):
            catalog_summary["races"] += 1
            for runner in race.get("runners", []):
                catalog_summary["runners"] += 1
                official = runner.get("official", {})
                if "scratched" in official:
                    catalog_summary["official_scratched_flags"] += 1
                if official.get("scratched") is True:
                    catalog_summary["current_scratchings"] += 1

checks = {
    "all_new_audits_passed": all(item["passed"] for item in results.values()),
    "catalog_exists": CATALOG.exists(),
    "live_catalog_loaded": catalog_summary["meetings"] > 0 and catalog_summary["runners"] > 0,
}

payload = {
    "status": "EDGEIQ_SCRATCHINGS_ENGINEERING_BUILD_V1_AUDIT_PASS"
    if all(checks.values())
    else "EDGEIQ_SCRATCHINGS_ENGINEERING_BUILD_V1_AUDIT_FAIL",
    "checks": checks,
    "catalog_summary": catalog_summary,
    "audits": results,
}

OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
OUT_TXT.write_text(
    "\n".join(
        [
            payload["status"],
            "",
            "Checks:",
            *[f"{key}: {value}" for key, value in checks.items()],
            "",
            "Catalog:",
            *[f"{key}: {value}" for key, value in catalog_summary.items()],
            "",
            "Child audits:",
            *[f"{name}: {result['stdout'] or result['stderr']}" for name, result in results.items()],
        ]
    ),
    encoding="utf-8",
)
print(payload["status"])
