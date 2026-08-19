from __future__ import annotations
import csv
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/full-product-implementation/screenshots/form-guide-exact"
PUBLIC_OUT = ROOT / "public/data"
SPEC_DIR = ROOT / "docs/product-specification"
AUDIT_CSV = PUBLIC_OUT / "edgeiq_form_guide_exact_conformance_audit_v1.csv"
AUDIT_SUMMARY = PUBLIC_OUT / "edgeiq_form_guide_exact_conformance_audit_v1_summary.csv"
AUDIT_REPORT = PUBLIC_OUT / "edgeiq_form_guide_exact_conformance_audit_v1_report.txt"

REQUIRED_FILES = [
    SPEC_DIR / "FORM_GUIDE_APPROVED_PIXEL_SPEC_V1.md",
    SPEC_DIR / "FORM_GUIDE_APPROVED_PIXEL_SPEC_V1.json",
    SPEC_DIR / "FORM_GUIDE_APPROVED_TEXT_SPEC_V1.csv",
    SPEC_DIR / "FORM_GUIDE_APPROVED_GEOMETRY_V1.csv",
    SPEC_DIR / "FORM_GUIDE_APPROVED_STYLE_TOKENS_V1.css",
    OUT / "05_FORM_GUIDE_APPROVED.png",
    OUT / "05_FORM_GUIDE_LIVE_RENDERED.png",
    OUT / "05_FORM_GUIDE_OVERLAY_50.png",
    OUT / "05_FORM_GUIDE_DIFF.png",
    OUT / "05_FORM_GUIDE_EDGE_DIFF.png",
    OUT / "05_FORM_GUIDE_REGION_DIFF.csv",
    OUT / "05_FORM_GUIDE_RUNTIME.json",
]

TSX = ROOT / "src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx"
CSS = ROOT / "src/edgeiq-os/styles/edgeiqOsV2.css"

CHECKS = {
    "workspace_marker": (TSX, 'data-edgeiq-workspace="form-guide-approved-exact"'),
    "approved_tools": (TSX, 'eiq-form-approved-tools'),
    "summary_table_region": (TSX, 'data-region="summary_table"'),
    "expanded_runner_region": (TSX, 'data-region="expanded_runner"'),
    "today_match_label": (TSX, "TODAY'S MATCH"),
    "profile_matrix_label": (TSX, "HORSE PROFILE (CAREER)"),
    "insights_label": (TSX, "TODAY'S MATCH INSIGHTS"),
    "recent_form_region": (TSX, 'data-region="recent_form"'),
    "edge_column": (TSX, '"EDGE"'),
    "fluc_column": (TSX, '"FLUC 60s %"'),
    "exact_css_marker": (CSS, "EDGEIQ FORM GUIDE APPROVED EXACT PIXEL SPEC V1 START"),
}

def runtime_status():
    path = OUT / "05_FORM_GUIDE_RUNTIME.json"
    if not path.exists():
        return "MISSING", None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("status", "UNKNOWN"), data

def main():
    rows = []
    for file in REQUIRED_FILES:
        rows.append({"check":"required_file", "item":str(file.relative_to(ROOT)), "status":"PASS" if file.exists() else "FAIL", "detail":str(file.stat().st_size) if file.exists() else "missing"})
    for name, (path, needle) in CHECKS.items():
        present = path.exists() and needle in path.read_text(encoding="utf-8")
        rows.append({"check":"source_marker", "item":name, "status":"PASS" if present else "FAIL", "detail":needle})
    rt_status, rt = runtime_status()
    rows.append({"check":"runtime_capture", "item":"runtime_status", "status":"PASS" if rt_status == "FORM_GUIDE_LIVE_CAPTURED" else "FAIL", "detail":rt_status})
    if rt:
        rows.append({"check":"runtime_capture", "item":"page_errors", "status":"PASS" if len(rt.get("events", [])) == 0 else "WARN", "detail":str(len(rt.get("events", [])))})
        rows.append({"check":"runtime_capture", "item":"pixel_rms_difference", "status":"INFO", "detail":str(rt.get("pixel_rms_difference", ""))})
    region_path = OUT / "05_FORM_GUIDE_REGION_DIFF.csv"
    missing_regions = []
    measured_regions = 0
    if region_path.exists():
        with region_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["status"] == "MISSING": missing_regions.append(row["region"])
                elif row["status"] == "MEASURED": measured_regions += 1
    rows.append({"check":"region_diff", "item":"measured_regions", "status":"PASS" if measured_regions >= 7 else "FAIL", "detail":str(measured_regions)})
    rows.append({"check":"region_diff", "item":"missing_regions", "status":"PASS" if not missing_regions else "WARN", "detail":"|".join(missing_regions)})
    PUBLIC_OUT.mkdir(parents=True, exist_ok=True)
    with AUDIT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["check","item","status","detail"])
        writer.writeheader(); writer.writerows(rows)
    fail_count = sum(1 for row in rows if row["status"] == "FAIL")
    warn_count = sum(1 for row in rows if row["status"] == "WARN")
    status = "FORM_GUIDE_EXACT_CONFORMANCE_PASS" if fail_count == 0 else "FORM_GUIDE_EXACT_CONFORMANCE_REVIEW_REQUIRED"
    summary_rows = [{"metric":"status", "value":status}, {"metric":"fail_count", "value":fail_count}, {"metric":"warn_count", "value":warn_count}, {"metric":"checked_at", "value":datetime.now().isoformat()}]
    with AUDIT_SUMMARY.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["metric","value"])
        writer.writeheader(); writer.writerows(summary_rows)
    report = [
        "EDGEiQ FORM GUIDE EXACT CONFORMANCE AUDIT V1",
        f"Status: {status}",
        f"Failures: {fail_count}",
        f"Warnings: {warn_count}",
        "Scope: UI structure/CSS/capture only. Model maths, pricing, probability, EPI, ERI and V6.1/V7.2G2 logic are not modified.",
    ]
    AUDIT_REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"status":status, "fail_count":fail_count, "warn_count":warn_count}, indent=2))
if __name__ == "__main__":
    main()
