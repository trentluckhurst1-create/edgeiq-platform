# EDGEiQ Product Service Consolidation Audit V1

Generated: 2026-07-16T17:55:58+00:00

## Consolidation Completed

- Added `ProductFeedCache.ts` for JSON feed caching, pending request de-duplication and size guards.
- `threeDayCatalog.ts` now uses the canonical JSON feed cache.
- `performanceIntelligenceFeed.ts` now uses the canonical JSON feed cache.

## Remaining Duplicates

- Services with direct fetch calls: 15
- Services with local CSV parser helpers: 11

These are mostly CSV terminal feeds and should be consolidated into a typed CSV feed loader in a future low-risk pass.

## Product Cache Users

- src/edgeiq-os/services/feed-loader/index.ts
- src/edgeiq-os/services/performance-intelligence/performanceIntelligenceFeed.ts
- src/edgeiq-os/race/services/threeDayCatalog.ts
