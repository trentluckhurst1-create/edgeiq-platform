# EDGEiQ Stale Audit Reconciliation - 2026-07-15

## Policy

Do not restore rejected UI or provider/source diagnostics to satisfy old audits. Current-valid audits are retained; superseded audits are documented and controlled by this reconciliation layer.

## Classification

| Audit | Status | Classification | Action |
| --- | --- | --- | --- |
| edgeiq_results_engineering_build_v1_audit.json | FAIL | REQUIRES_UPSTREAM_DATA | do not restore superseded UI; handle through current-app data readiness |
| edgeiq_track_engineering_build_v1_audit.json | FAIL | STALE_UI_REQUIREMENT | do not restore superseded UI; handle through current-app data readiness |
| edgeiq_weather_engineering_build_v1_audit.json | FAIL | SUPERSEDED_ARCHITECTURE | do not restore superseded UI; handle through current-app data readiness |
| edgeiq_scratchings_engineering_build_v1_audit.json | FAIL | SUPERSEDED_ARCHITECTURE | do not restore superseded UI; handle through current-app data readiness |
| edgeiq_meetings_engineering_build_v1_audit.json | FAIL | SUPERSEDED_ARCHITECTURE | do not restore superseded UI; handle through current-app data readiness |
| edgeiq_form_guide_engineering_build_v1_audit.json | PASS | CURRENT_VALID | retain current audit |
| edgeiq_map_engineering_build_v1_audit.json | PASS | CURRENT_VALID | retain current audit |
| edgeiq_market_engineering_build_v1_audit.json | PASS | CURRENT_VALID | retain current audit |
| edgeiq_insights_engineering_build_v1_audit.json | PASS | REQUIRES_UPSTREAM_DATA | do not restore superseded UI; handle through current-app data readiness |
| edgeiq_gear_changes_engineering_build_v1_audit.json | PASS | CURRENT_VALID | retain current audit |

## Preserved Rejections

- Data Freshness panels were not restored.
- Source/provider labels were not restored.
- Removed columns and old Results controls were not restored.
- Locked Meeting tabs remain governed by current-valid audits.