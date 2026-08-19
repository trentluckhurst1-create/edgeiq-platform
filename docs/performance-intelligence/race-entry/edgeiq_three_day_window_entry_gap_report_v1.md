# EDGEiQ Three-Day Window Race Entry Gap Report V1

Audit date: 2026-07-23
Three-day window generatedAt: 2026-07-23T08:17:22+10:00
Three-day window dates: 2026-07-23, 2026-07-24, 2026-07-25

## Coverage
- Race records traced: 64
- Current/future race records: 64
- Runner records traced: 649
- Current/future runner records: 649
- Stale runner records: 0

## Source Shape Decision
- The three-day pipeline contains current/future runner-level entries and can be formalised as the canonical race-entry source after identity audit.

## Field Feed Findings
- edgeiq_vic_three_day_meeting_universe.csv rows: 0
- edgeiq_vic_three_day_race_fields.csv rows: 0
- Both field-feed outputs are the expected downstream runner-level locations, but currently contain zero rows.

## Next Required Action
Trace the authoritative live field source: either repair the existing three-day product/field refresh or establish that no governed live field ingestion exists.
