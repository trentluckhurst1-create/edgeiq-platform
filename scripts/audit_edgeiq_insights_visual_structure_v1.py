from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "InsightsWorkspace.tsx"
STYLE = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_insights_visual_structure_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_insights_visual_structure_v1_audit.txt"

component = COMPONENT.read_text(encoding="utf-8", errors="replace") if COMPONENT.exists() else ""
style = STYLE.read_text(encoding="utf-8", errors="replace") if STYLE.exists() else ""
insights_style = style[style.find(".eiq-insights-v1") :] if ".eiq-insights-v1" in style else ""

checks = {
    "component_exists": COMPONENT.exists(),
    "scoped_insights_class": "eiq-insights-v1" in component and ".eiq-insights-v1" in style,
    "top_cards_visible": all(label in component for label in ["KEY INSIGHT", "BEST RATED RUNNER", "VALUE INSIGHT", "MARKET RISER", "RACE SETUP"]),
    "locked_columns_visible": "NO | HORSE | KEY INSIGHT | EDGE | CONFIDENCE" in component,
    "required_sections_visible": all(label in component for label in ["Insight Summary", "Top 5 Insights", "Runner Insights", "Insight Confidence / Evidence Quality", "Model Information", "How To Use These Insights"]),
    "light_design_tokens": "#fff" in insights_style and "#e5e8ee" in insights_style and "#1f5fd6" in insights_style,
    "no_gradients": "linear-gradient" not in insights_style and "radial-gradient" not in insights_style,
    "no_dark_terminal_panel": "#020508" not in insights_style and "#071018" not in insights_style,
    "no_prohibited_ui_language": not re.search(r"\b(TIP|BET|SELECTION|WATCH|AVOID|GUARANTEE|STAR|MEDAL)\b", component, re.IGNORECASE),
}

payload = {
    "status": "EDGEIQ_INSIGHTS_VISUAL_STRUCTURE_V1_AUDIT_PASS" if all(checks.values()) else "EDGEIQ_INSIGHTS_VISUAL_STRUCTURE_V1_AUDIT_FAIL",
    "checks": checks,
}
OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
OUT_TXT.write_text(
    "\n".join([payload["status"], "", *[f"{key}: {value}" for key, value in checks.items()]]),
    encoding="utf-8",
)
print(payload["status"])
if payload["status"].endswith("FAIL"):
    raise SystemExit(1)
