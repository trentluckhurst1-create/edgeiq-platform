from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MarketWorkspace.tsx"
STYLE = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_market_visual_structure_v1_audit.json"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_market_visual_structure_v1_audit.txt"

component = COMPONENT.read_text(encoding="utf-8", errors="replace") if COMPONENT.exists() else ""
style = STYLE.read_text(encoding="utf-8", errors="replace") if STYLE.exists() else ""
market_style = style[style.find(".eiq-market-v1") :] if ".eiq-market-v1" in style else ""

checks = {
    "component_exists": COMPONENT.exists(),
    "scoped_market_class": "eiq-market-v1" in component and ".eiq-market-v1" in style,
    "locked_columns_visible": "NO | HORSE | EPI | MARKET | OPEN | HIGH | LOW | MOVE | EDGEiQ PRICE | EDGE | STATUS" in component,
    "light_design_tokens": "#fff" in market_style and "#e5e8ee" in market_style and "#1f5fd6" in market_style,
    "no_gradients": "linear-gradient" not in market_style and "radial-gradient" not in market_style,
    "no_dark_terminal_panel": "#020508" not in market_style and "#071018" not in market_style,
    "no_prohibited_ui_language": not re.search(r"\b(BACK|LAY|EXCHANGE|ORDER BOOK|TIP|BET|SELECTION|WATCH)\b", component, re.IGNORECASE),
}

payload = {
    "status": "EDGEIQ_MARKET_VISUAL_STRUCTURE_V1_AUDIT_PASS" if all(checks.values()) else "EDGEIQ_MARKET_VISUAL_STRUCTURE_V1_AUDIT_FAIL",
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
