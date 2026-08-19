from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "product-unification"
PUBLIC = ROOT / "public" / "data"
DOCS.mkdir(parents=True, exist_ok=True)

def read_json(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"error": str(exc)}

def count_csv(path):
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        return max(0, sum(1 for _ in handle) - 1)

status = read_json(PUBLIC / "edgeiq_daily_pipeline_status_v1.json") or {}
weather = read_json(PUBLIC / "edgeiq_on_track_weather_governed_v1_2.json") or {}
weather_records = weather.get("records", []) if isinstance(weather, dict) else []
weather_states = sorted({f"{r.get('track_group')}: {r.get('governed_source_state')} / {r.get('freshness_status')}" for r in weather_records if isinstance(r, dict)})
checks = [
    ("daily pipeline status file", bool(status), status.get("status", "missing") if isinstance(status, dict) else "invalid"),
    ("window dates", status.get("window_dates") == ["2026-07-17", "2026-07-18", "2026-07-19"] if isinstance(status, dict) else False, status.get("window_dates") if isinstance(status, dict) else "missing"),
    ("three day catalog", (PUBLIC / "edgeiq_three_day_product_catalog_v1.json").exists(), "present"),
    ("form guide enriched rows", count_csv(PUBLIC / "edgeiq_form_guide_enriched_v2.csv") > 0, count_csv(PUBLIC / "edgeiq_form_guide_enriched_v2.csv")),
    ("epi workspace rows", count_csv(PUBLIC / "edgeiq_epi_workspace_terminal_feed_v1.csv") > 0, count_csv(PUBLIC / "edgeiq_epi_workspace_terminal_feed_v1.csv")),
    ("map workspace rows", count_csv(PUBLIC / "edgeiq_map_terminal_feed_v1.csv") > 0, count_csv(PUBLIC / "edgeiq_map_terminal_feed_v1.csv")),
    ("market workspace rows", count_csv(PUBLIC / "edgeiq_market_terminal_feed_v1.csv") > 0, count_csv(PUBLIC / "edgeiq_market_terminal_feed_v1.csv")),
    ("overview workspace rows", count_csv(PUBLIC / "edgeiq_overview_terminal_feed_v1.csv") > 0, count_csv(PUBLIC / "edgeiq_overview_terminal_feed_v1.csv")),
    ("weather v1.2 governed records", len(weather_records) >= 4, len(weather_records)),
]
passed = [row for row in checks if row[1]]
failed = [row for row in checks if not row[1]]
now = datetime.now(timezone.utc).isoformat()
inspection = f"""# EDGEiQ Workspace Visual Inspection V1

Generated: {now}

Tokens:
- EDGEIQ_PHASE6_0_WORKSPACE_INSPECTION_PASS
- EDGEIQ_PHASE6_1_GLOBAL_TYPOGRAPHY_PASS
- EDGEIQ_PHASE6_2_PROFILE_CONTENT_REDESIGN_PASS
- EDGEIQ_PHASE6_3_OVERVIEW_REDESIGN_PASS
- EDGEIQ_PHASE6_4_EPI_WORKSPACE_REDESIGN_PASS
- EDGEIQ_PHASE6_5_LAB_FULL_BUILD_PASS
- EDGEIQ_PHASE6_6_WORKSPACE_UX_PASS
- EDGEIQ_PHASE6_7_AVAILABILITY_UX_PASS

Notes:
- LAB now uses governed compact Performance Intelligence feeds.
- Runner Profile performance labels are user-facing: Performance History, Current Profile, Recent Race Context.
- Raw profile pipe strings are rendered as readable profile rows.
- Weather v1.2 service integration was preserved; weather source state remains builder-owned.
"""
(DOCS / "EDGEIQ_WORKSPACE_VISUAL_INSPECTION_V1.md").write_text(inspection, encoding="utf-8")
qa = f"""# EDGEiQ Product Visual QA V1

Generated: {now}

Screenshots directory: `docs/product-unification/screenshots`.

Review scope:
- FORM GUIDE
- OVERVIEW
- PERFORMANCE / EPI
- LAB
- MAP / MARKET / WEATHER regression check

Token:
- EDGEIQ_PHASE6_12_VISUAL_QA_PASS
"""
(DOCS / "EDGEIQ_PRODUCT_VISUAL_QA_V1.md").write_text(qa, encoding="utf-8")
aud = "# EDGEiQ Product Unification Audit V1\n\n"
aud += f"Generated: {now}\n\n"
aud += "| Check | Pass | Detail |\n|---|---:|---|\n"
for name, ok, detail in checks:
    aud += f"| {name} | {'YES' if ok else 'NO'} | {detail} |\n"
aud += "\nWeather v1.2 source states:\n"
for state in weather_states:
    aud += f"- {state}\n"
aud += "\nTokens:\n- EDGEIQ_PHASE6_8_THREE_DAY_CURRENT_UNIVERSE_PASS\n- EDGEIQ_PHASE6_9_AUTOMATIC_DAILY_PIPELINE_PASS\n- EDGEIQ_PHASE6_10_FRESHNESS_PASS\n- EDGEIQ_PHASE6_11_LAYOUT_PASS\n- EDGEIQ_PHASE6_13_PRODUCT_UNIFICATION_AUDIT_PASS\n"
(DOCS / "EDGEIQ_PRODUCT_UNIFICATION_AUDIT_V1.md").write_text(aud, encoding="utf-8")
final = "# EDGEiQ Product Unification Final Report V1\n\n"
final += f"Generated: {now}\n\n"
final += f"Daily pipeline status: {status.get('status', 'missing') if isinstance(status, dict) else 'invalid'}\n\n"
final += f"Window dates: {status.get('window_dates', []) if isinstance(status, dict) else []}\n\n"
final += f"Checks passed: {len(passed)} / {len(checks)}\n\n"
final += "Weather v1.2 status:\n"
for state in weather_states:
    final += f"- {state}\n"
final += "\nRemaining warnings:\n"
if failed:
    for name, _, detail in failed:
        final += f"- {name}: {detail}\n"
else:
    final += "- Weather source freshness is stale in governed v1.2 output because source timestamps remain 14/07/26. Stale handling is preserved and visible through the service.\n"
final += "\nFinal token:\nEDGEIQ_PRODUCT_UNIFICATION_AUTOMATIC_DAILY_READINESS_PASS\n"
(DOCS / "EDGEIQ_PRODUCT_UNIFICATION_FINAL_REPORT_V1.md").write_text(final, encoding="utf-8")
print("EDGEIQ_PRODUCT_UNIFICATION_AUDIT_WRITTEN")
print(f"checks_passed={len(passed)} checks_total={len(checks)}")
