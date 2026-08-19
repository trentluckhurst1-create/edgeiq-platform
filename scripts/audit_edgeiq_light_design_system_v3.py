from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
OUT = ROOT / "public" / "data" / "edgeiq_light_design_system_v3_audit.csv"
SUMMARY = ROOT / "public" / "data" / "edgeiq_light_design_system_v3_audit_summary.csv"
text = CSS.read_text(encoding="utf-8")
checks = []

def add(check, status, detail):
    checks.append({"check": check, "status": status, "detail": detail})

required = ["#f4f6f9", "#ffffff", "#fafbfc", "#f7f9fc", "#1f5fd6", "#1a1a1a", "#5c6675", "#7c8798", "#e5e8ee", "#d7dce5"]
marker = "EDGEIQ LIGHT DESIGN SYSTEM, FORM GUIDE TABLE CLEANUP, MAP CONSOLIDATION AND EPI CURRENT RATING V1"
add("light_override_marker", "PASS" if marker in text else "FAIL", marker)
for token in required:
    add(f"token_{token}", "PASS" if token in text.lower() else "FAIL", token)
add("dark_gradient_neutralised", "PASS" if ".edgeiq-os {\n  background: #f4f6f9 !important;" in text else "FAIL", "edgeiq-os light override")
add("active_product_shell_marker", "PASS" if "EDGEIQ LIGHT DESIGN ACTIVE PRODUCT SHELL V1" in text else "FAIL", "active mounted product shell marker")
add("active_product_shell_override", "PASS" if ".eiq-product-shell-v4" in text and "background: #f4f6f9 !important" in text else "FAIL", "eiq-product-shell-v4 light override")
add("active_nav_override", "PASS" if ".eiq-app-nav" in text and "background: #ffffff !important" in text else "FAIL", "eiq-app-nav light override")
add("panel_light_override", "PASS" if ".eiq-workspace-panel," in text and "background: #ffffff !important" in text else "FAIL", "panel/surface override")

OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"]); writer.writeheader(); writer.writerows(checks)
status = "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL"
with SUMMARY.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=["metric", "value"]); writer.writeheader(); writer.writerows([{"metric":"status","value":status},{"metric":"checks","value":len(checks)}])
print(status)
if status != "PASS":
    raise SystemExit(1)
