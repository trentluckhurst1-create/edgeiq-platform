# EDGEiQ Performance Intelligence Product Integration Audit V1

Generated: 2026-07-26T03:40:21Z

## Current implementations
- Race workspace: `src/edgeiq-os/race/components/RaceWorkspace.tsx`
- Performance workspace: `src/edgeiq-os/race/components/EpiWorkspaceWorkspace.tsx`
- Form workspace: `src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx`
- Runner profile: `src/edgeiq-os/race/components/RunnerProfileWorkspace.tsx`
- Results workspace: `src/edgeiq-os/race/components/ResultsWorkspace.tsx`
- Compare workspace: `src/edgeiq-os/compare/CompareWorkspace.tsx`
- Insights workspace: `src/edgeiq-os/race/components/InsightsWorkspace.tsx`
- Current catalogue: `public/data/edgeiq_three_day_product_catalog_v1.json`

## Integration points
Compact feed: `/performance-intelligence/edgeiq_performance_intelligence_product_feeds_v1.json`
Service boundary: `src/edgeiq-os/services/performance-intelligence/`

## Fields intentionally unavailable
- runner_adjusted_time_seconds
- runner_seconds_vs_benchmark
- runner_lengths_vs_benchmark
- official_sectional_time
- sectional_benchmark_seconds
- sectional_deviation_lengths

## Identity safety
Horse-code matches are preferred. Name matching is secondary. Unmatched current runners remain unavailable.

Token: `EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE4_0_PRODUCT_FEEDS_PASS`
