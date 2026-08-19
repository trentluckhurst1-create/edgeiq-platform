from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceFormGuideWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
OUT = ROOT / "public" / "data" / "edgeiq_form_guide_table_structure_audit_v1.csv"
SUMMARY = ROOT / "public" / "data" / "edgeiq_form_guide_table_structure_audit_summary_v1.csv"
comp = COMP.read_text(encoding="utf-8")
css = CSS.read_text(encoding="utf-8")
checks=[]

def add(check,status,detail): checks.append({"check":check,"status":status,"detail":detail})
add("last5_compact_join", "PASS" if 'runner.lastFive.join(" ")' in comp else "FAIL", "LAST 5 compact text")
add("last5_no_table_badge_map", "PASS" if 'runner.lastFive.map((item' not in comp else "FAIL", "no LAST 5 chip map in summary table")
add("vertical_dividers_removed", "PASS" if "border-left: 0 !important" in css and "border-right: 0 !important" in css else "FAIL", "table override")
add("ordinary_values_plain", "PASS" if ".eiq-cell-last-five," in css and "background: transparent !important" in css else "FAIL", "plain value cells")
add("scratch_strikethrough", "PASS" if "text-decoration: line-through" in css else "FAIL", "scratching visible/subdued")
add("summary_columns_present", "PASS" if "summaryColumns" in comp and "EDGEiQ PRICE" in comp and "FORM MOMENTUM" in comp else "FAIL", "expected form columns")
OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", newline="", encoding="utf-8") as handle:
    writer=csv.DictWriter(handle, fieldnames=["check","status","detail"]); writer.writeheader(); writer.writerows(checks)
status="PASS" if all(r["status"]=="PASS" for r in checks) else "FAIL"
with SUMMARY.open("w", newline="", encoding="utf-8") as handle:
    writer=csv.DictWriter(handle, fieldnames=["metric","value"]); writer.writeheader(); writer.writerows([{"metric":"status","value":status},{"metric":"checks","value":len(checks)}])
print(status)
if status != "PASS": raise SystemExit(1)
