from pathlib import Path
import csv
import json

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DOC = ROOT / "docs" / "full-product-implementation"
FILES = {
    "RaceWorkspace": ROOT / "src/edgeiq-os/race/components/RaceWorkspace.tsx",
    "FieldWorkspace": ROOT / "src/edgeiq-os/race/components/FieldWorkspace.tsx",
    "ViewModel": ROOT / "src/edgeiq-os/race/services/fieldWorkspaceViewModel.ts",
    "CSS": ROOT / "src/edgeiq-os/styles/edgeiqOsV2.css",
}
OUT_CSV = DOC / "EDGEIQ_FIELD_WORKSPACE_V1_AUDIT.csv"
OUT_JSON = DOC / "EDGEIQ_FIELD_WORKSPACE_V1_AUDIT.json"
OUT_MD = DOC / "EDGEIQ_FIELD_WORKSPACE_V1_AUDIT.md"

CHECKS = [
    ("render_path_field_tab", "RaceWorkspace", "FIELD: \"FieldWorkspace\"", True),
    ("shared_header_present", "RaceWorkspace", "eiq-approved-racefile-header", True),
    ("admin_wall_filter_present", "RaceWorkspace", "Set Weights|Apprentices|VOBIS|field limit", True),
    ("header_meta_has_track_rail_weather", "RaceWorkspace", "[\"TRACK\", trackCondition]", True),
    ("surface_meta_removed", "RaceWorkspace", "[\"SURFACE\", surface]", False),
    ("field_compact_header", "FieldWorkspace", "Official declared runners", True),
    ("generic_header_removed", "FieldWorkspace", "Official runners with governed EDGEiQ fields", False),
    ("epi_label_present", "FieldWorkspace", "<th>EPI</th>", True),
    ("generic_edgeiq_header_removed", "FieldWorkspace", "<th>EDGEiQ</th>", False),
    ("row_click_expansion", "FieldWorkspace", "onClick={() => toggleRunner(runner.key)}", True),
    ("keyboard_expansion", "FieldWorkspace", "handleRunnerKeyDown", True),
    ("no_history_state", "FieldWorkspace", "NO PREVIOUS STARTS", True),
    ("open_profile_removed", "FieldWorkspace", "Open runner profile", False),
    ("recent_runs_limited_to_five", "FieldWorkspace", "recentRuns.slice(0, 5)", True),
    ("scratch_from_market", "ViewModel", "marketScratched", True),
    ("scratched_flag_output", "ViewModel", "isScratched", True),
    ("expanded_css_scoped", "CSS", ".eiq-approved-shell .eiq-field-recent-panel", True),
    ("field_tabs_compact_css", "CSS", ".eiq-race-workspace--field > .eiq-context-tabs", True),
]

def main():
    rows = []
    for name, file_key, needle, expected in CHECKS:
        text = FILES[file_key].read_text(encoding="utf-8", errors="replace")
        found = needle in text
        passed = found if expected else not found
        rows.append({"check": name, "file": str(FILES[file_key].relative_to(ROOT)), "expected_present": expected, "status": "PASS" if passed else "FAIL"})
    bad_terms = ["Governed recent-start rows are not published", "Official runners with governed EDGEiQ fields"]
    fw = FILES["FieldWorkspace"].read_text(encoding="utf-8", errors="replace")
    for term in bad_terms:
        rows.append({"check": f"no_raw_copy_{term}", "file": "src/edgeiq-os/race/components/FieldWorkspace.tsx", "expected_present": False, "status": "PASS" if term not in fw else "FAIL"})
    status = "PASS" if all(r["status"] == "PASS" for r in rows) else "FAIL"
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["check", "file", "expected_present", "status"])
        writer.writeheader()
        writer.writerows(rows)
    OUT_JSON.write_text(json.dumps({"status": status, "checks": rows}, indent=2), encoding="utf-8")
    OUT_MD.write_text("# EDGEIQ FIELD WORKSPACE V1 Audit\n\nStatus: **{}**\n\n{}\n".format(status, "\n".join(f"- {r['status']}: {r['check']}" for r in rows)), encoding="utf-8")
    print(status)

if __name__ == "__main__":
    main()
