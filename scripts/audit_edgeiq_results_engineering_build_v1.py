from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUT_JSON = DATA / "edgeiq_results_engineering_build_v1_audit.json"
OUT_TXT = DATA / "edgeiq_results_engineering_build_v1_audit.txt"
MEETING = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"
WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingResultsWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "resultsFeed.ts"

AUDITS = [
    "audit_edgeiq_results_data_contract_v1.py",
    "audit_edgeiq_results_runner_performance_v1.py",
    "audit_edgeiq_results_sectionals_v1.py",
    "audit_edgeiq_results_visual_structure_v1.py",
    "audit_edgeiq_meeting_results_tab_v1.py",
    "audit_edgeiq_individual_race_results_v1.py",
]


def main() -> None:
    results = {}
    for audit in AUDITS:
      proc = subprocess.run([sys.executable, str(ROOT / "scripts" / audit)], cwd=ROOT, text=True, capture_output=True)
      results[audit] = {
          "returncode": proc.returncode,
          "stdout": proc.stdout.strip(),
          "stderr": proc.stderr.strip(),
          "passed": proc.returncode == 0 and "PASS" in proc.stdout,
      }

    meeting = MEETING.read_text(encoding="utf-8", errors="replace") if MEETING.exists() else ""
    checks = {
        "component_exists": WORKSPACE.exists(),
        "service_exists": SERVICE.exists(),
        "meeting_mounts_results": 'tab === "RESULTS"' in meeting and "MeetingResultsWorkspace" in meeting,
        "all_child_audits_passed": all(item["passed"] for item in results.values()),
    }
    status = "EDGEIQ_RESULTS_ENGINEERING_BUILD_V1_AUDIT_PASS" if all(checks.values()) else "EDGEIQ_RESULTS_ENGINEERING_BUILD_V1_AUDIT_FAIL"
    payload = {"status": status, "checks": checks, "audits": results}
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_TXT.write_text(
        "\n".join(
            [
                status,
                "",
                "Checks:",
                *[f"{key}: {value}" for key, value in checks.items()],
                "",
                "Child audits:",
                *[f"{name}: {result['stdout'] or result['stderr']}" for name, result in results.items()],
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(status)
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
