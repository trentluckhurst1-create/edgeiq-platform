from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
MEETING = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"
WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingResultsWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
OUT_JSON = DATA / "edgeiq_results_visual_structure_v1_audit.json"
OUT_TXT = DATA / "edgeiq_results_visual_structure_v1_audit.txt"


def main() -> None:
    meeting = MEETING.read_text(encoding="utf-8", errors="replace") if MEETING.exists() else ""
    workspace = WORKSPACE.read_text(encoding="utf-8", errors="replace") if WORKSPACE.exists() else ""
    css = CSS.read_text(encoding="utf-8", errors="replace") if CSS.exists() else ""
    results_css = css[css.find(".eiq-results-v1") :] if ".eiq-results-v1" in css else ""
    checks = {
        "component_exists": WORKSPACE.exists(),
        "results_tab_is_not_pending": 'tab === "RESULTS"' in meeting and "MeetingResultsWorkspace" in meeting,
        "required_sections_present": all(
            text in workspace
            for text in ["Meeting Results", "Official race result state", "IndividualRaceResult", "Runner Performance", "DATA STATUS"]
        ),
        "light_css_present": ".eiq-results-v1" in css and "#ffffff" in results_css and "#e5e8ee" in results_css,
        "no_gradient_or_glow": "gradient" not in results_css.lower() and "glow" not in results_css.lower(),
        "no_stars_or_medals": "star" not in workspace.lower() and "medal" not in workspace.lower(),
    }
    status = (
        "EDGEIQ_RESULTS_VISUAL_STRUCTURE_V1_AUDIT_PASS"
        if all(checks.values())
        else "EDGEIQ_RESULTS_VISUAL_STRUCTURE_V1_AUDIT_FAIL"
    )
    payload = {"status": status, "checks": checks}
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_TXT.write_text("\n".join([status, "", *[f"{key}: {value}" for key, value in checks.items()]]) + "\n", encoding="utf-8")
    print(status)
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
