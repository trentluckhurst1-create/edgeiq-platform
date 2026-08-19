# EDGEiQ Performance Intelligence Product Integration Final Report V1

Generated: 2026-07-16T10:33:49+00:00
Status: PASS

## Compact Feed Coverage

- race_intelligence_index: 16
- horse_intelligence_index: 211
- historical_performance_intelligence_index: 975
- benchmark_explanation_index: 426

## Integration Scope

- Certified compact feed is served from `public/performance-intelligence`.
- React services load compact product indexes only.
- EPI, Form Guide, Overview, Results, Compare and Insights consume service lookups.
- Unsupported runner-adjusted and sectional benchmark values remain unavailable.

## Audit Checks

- PASS: compact_product_feed_exists - C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\public\performance-intelligence\edgeiq_performance_intelligence_product_feeds_v1.json
- PASS: compact_feed_row_guard - {"benchmark_explanation_index": 426, "historical_performance_intelligence_index": 975, "horse_intelligence_index": 211, "race_intelligence_index": 16}
- PASS: service_file::types.ts - C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\src\edgeiq-os\services\performance-intelligence\types.ts
- PASS: service_file::performanceIntelligenceFeed.ts - C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\src\edgeiq-os\services\performance-intelligence\performanceIntelligenceFeed.ts
- PASS: service_file::PerformanceIntelligenceService.ts - C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\src\edgeiq-os\services\performance-intelligence\PerformanceIntelligenceService.ts
- PASS: service_file::index.ts - C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\src\edgeiq-os\services\performance-intelligence\index.ts
- PASS: ui_wiring::EPI workspace - C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\src\edgeiq-os\race\components\EpiWorkspaceWorkspace.tsx
- PASS: ui_wiring::Form guide - C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\src\edgeiq-os\race\components\RaceFormGuideWorkspace.tsx
- PASS: ui_wiring::Overview - C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\src\edgeiq-os\race\components\OverviewWorkspace.tsx
- PASS: ui_wiring::Results - C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\src\edgeiq-os\race\components\ResultsWorkspace.tsx
- PASS: ui_wiring::Compare - C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\src\edgeiq-os\compare\CompareWorkspace.tsx
- PASS: ui_wiring::Insights - C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\src\edgeiq-os\race\components\InsightsWorkspace.tsx
- PASS: frontend_warehouse_load_block::canonical_performance_facts_v0_2.csv - Frontend source scan
- PASS: frontend_warehouse_load_block::edgeiq_results_master_v1.csv - Frontend source scan
- PASS: frontend_warehouse_load_block::edgeiq_speed_master_v1.csv - Frontend source scan
- PASS: frontend_warehouse_load_block::edgeiq_standardised_sectionals_v1.csv - Frontend source scan
- PASS: frontend_warehouse_load_block::performances view - Frontend source scan
- PASS: frontend_warehouse_load_block::879,784 - Frontend source scan
- PASS: unsupported_field_contract::runner_adjusted_time_seconds - Present in manifest unsupported list and not rendered as a data field.
- PASS: unsupported_field_contract::runner_seconds_vs_benchmark - Present in manifest unsupported list and not rendered as a data field.
- PASS: unsupported_field_contract::runner_lengths_vs_benchmark - Present in manifest unsupported list and not rendered as a data field.
- PASS: unsupported_field_contract::official_sectional_time - Present in manifest unsupported list and not rendered as a data field.
- PASS: unsupported_field_contract::sectional_benchmark_seconds - Present in manifest unsupported list and not rendered as a data field.
- PASS: unsupported_field_contract::sectional_deviation_lengths - Present in manifest unsupported list and not rendered as a data field.
