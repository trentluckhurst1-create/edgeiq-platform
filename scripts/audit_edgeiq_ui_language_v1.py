from __future__ import annotations

from datetime import datetime

from edgeiq_beta_readiness_common_v1 import PUBLIC_DATA, ROOT, read_text, write_json, write_text


PASS_MARKER = "EDGEIQ_UI_LANGUAGE_V1_PASS"
TXT_OUT = PUBLIC_DATA / "edgeiq_ui_language_v1.txt"
JSON_OUT = PUBLIC_DATA / "edgeiq_ui_language_v1.json"

FILES = [
    "src/edgeiq-os/race/components/RaceWorkspace.tsx",
    "src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx",
    "src/edgeiq-os/race/components/MapWorkspace.tsx",
    "src/edgeiq-os/race/components/MarketWorkspace.tsx",
    "src/edgeiq-os/race/components/OverviewWorkspace.tsx",
    "src/edgeiq-os/race/components/InsightsWorkspace.tsx",
    "src/edgeiq-os/race/components/EpiWorkspaceWorkspace.tsx",
]

BANNED_VISIBLE = [
    "Feed Status",
    "Loaded Rows",
    "Matched Rows",
    "Feed Rows",
    "Model Information",
    "Data State",
    "Operational State",
    "Null Handling",
    "builder",
    "workspace builder",
]


def main() -> int:
    generated = datetime.now().isoformat(timespec="seconds")
    findings = []
    for path in FILES:
        source = read_text(ROOT / path)
        for term in BANNED_VISIBLE:
            if term in source:
                findings.append({"file": path, "term": term})
    status = "PASS" if not findings else "FAIL"
    payload = {"audit": "edgeiq_ui_language_v1", "generated_at": generated, "status": status, "pass_marker": PASS_MARKER if status == "PASS" else "", "findings": findings}
    write_json(JSON_OUT, payload)
    lines = ["EDGEiQ UI Language V1", f"Generated: {generated}", f"Status: {status}"]
    if status == "PASS":
        lines.append(PASS_MARKER)
    lines.append("")
    for finding in findings:
        lines.append(f"[FAIL] {finding['file']} contains {finding['term']}")
    if not findings:
        lines.append("No banned user-facing operational phrases found in race workspace components.")
    write_text(TXT_OUT, "\n".join(lines) + "\n")
    print(PASS_MARKER if status == "PASS" else "EDGEIQ_UI_LANGUAGE_V1_FAIL")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
