from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingResultsWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
OUT_JSON = DATA / "edgeiq_results_sectionals_v1_audit.json"
OUT_TXT = DATA / "edgeiq_results_sectionals_v1_audit.txt"


def main() -> None:
    source = WORKSPACE.read_text(encoding="utf-8", errors="replace") if WORKSPACE.exists() else ""
    css = CSS.read_text(encoding="utf-8", errors="replace") if CSS.exists() else ""
    checks = {
        "signed_value_component": "function SignedValue" in source,
        "pending_speed_data_copy": "Pending speed data" in source,
        "negative_is_inside_standard_copy": "Negative is inside standard; positive is outside standard." in source,
        "sectional_columns_present": all(text in source for text in ["800m</th>", "600m</th>", "400m</th>", "200m</th>"]),
        "negative_positive_neutral_classes": all(text in source for text in ["is-negative", "is-positive", "is-neutral"]),
        "negative_green_positive_red_css": ".eiq-results-v1-sectional.is-negative" in css
        and "#027a48" in css
        and ".eiq-results-v1-sectional.is-positive" in css
        and "#b42318" in css,
    }
    status = "EDGEIQ_RESULTS_SECTIONALS_V1_AUDIT_PASS" if all(checks.values()) else "EDGEIQ_RESULTS_SECTIONALS_V1_AUDIT_FAIL"
    payload = {"status": status, "checks": checks}
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_TXT.write_text("\n".join([status, "", *[f"{key}: {value}" for key, value in checks.items()]]) + "\n", encoding="utf-8")
    print(status)
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
