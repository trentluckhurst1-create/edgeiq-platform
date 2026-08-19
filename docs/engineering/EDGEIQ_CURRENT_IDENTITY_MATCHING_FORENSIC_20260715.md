# EDGEiQ Current Identity Matching Forensic

Generated: 2026-07-15T17:57:45

This audit documents identity alignment only. It does not modify UI, feeds, formulas or governed values.

## Catalogue Universe

- Current races: 16
- Current runners: 211
- Race key style: exact catalogue key such as `2026-07-14|BALLARAT|R1`
- Canonical key style: `2026-07-14|BALLARAT|1`

## Feed Identity Match Summary

| Feed | Rows | Exact race matches | Canonical race matches | Runner matches | Runner unmatched | Unmatched reasons |
| --- | --- | --- | --- | --- | --- | --- |
| MAP | 211 | 16 | 16 | 211 | 0 | {} |
| Insights | 291 | 16 | 16 | 211 | 0 | {} |
| Performance/EPI | 211 | 16 | 16 | 211 | 0 | {} |
| Market | 211 | 16 | 16 | 211 | 0 | {} |

## Required Coverage Counts

| Metric | Covered / Value Rows | Eligible / Rows | Evidence field |
| --- | --- | --- | --- |
| MAP speed/map values | 0 | 211 | terminal feed fields: run_style/early_speed/projected_position |
| Insights | 0 | 291 | terminal feed cards/runner insight values |
| Historical EPI tiles | 0 | 211 | start_10..start_1 tile values |
| Market | 106 | 211 | market field |
| EPI | 0 | 211 | form-guide enriched runner epi/rating |
| Suitability | 0 | 211 | form-guide enriched suitability |
| Form Momentum | 0 | 211 | form-guide enriched formMomentum |
| Early Speed | 0 | 211 | form-guide enriched earlySpeed |
| Late Speed | 0 | 211 | form-guide enriched lateSpeed |

## Exact Mismatch Findings

- Terminal feeds for MAP, Market, Insights and EPI are keyed by exact catalogue-style `race_key`.
- Form Guide enrichment is keyed by canonical `raceDate|normalised track|raceNumber` and then runner identity.
- Identity matching can pass while governed evidence remains empty; this is visible in MAP and Insights pending rows.
- Historical EPI tile matching is separate from current EPI matching; current EPI rows can exist while `start_10..start_1` tiles are empty.

## Feed Samples Of Race-Key Misses

{
  "MAP": [],
  "Insights": [],
  "Performance/EPI": [],
  "Market": []
}
