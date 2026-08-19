# EDGEIQ Performance Intelligence

## Phase 1A.1 Active Source Forensics V1

- Program ID: `EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE1A_1_ACTIVE_SOURCE_FORENSICS_V1`
- Generated UTC: `2026-07-27T03:10:59+00:00`
- Overall status: **PASS**

## Purpose

This unit removes checkpoint, archive, backup, legacy and UI noise from the Phase 1A repository discovery and produces a governed shortlist of active Performance Intelligence source candidates.

No source is promoted to canonical status by this report.

## Summary

- Phase 1A dataset records reviewed: 16,656
- Active-path dataset records: 8,664
- Shortlisted candidates: 2,853
- High-priority candidates: 714

## Candidate Classes

| Class | Count |
|---|---:|
| BENCHMARK_OBSERVATION | 7 |
| HISTORICAL_OBSERVATION | 16 |
| LEGACY_RATING | 41 |
| LENGTHS_V_STANDARD | 66 |
| OTHER_PERFORMANCE | 1,702 |
| PERFORMANCE_WAREHOUSE | 61 |
| RACE_STRENGTH | 41 |
| RESULT_HISTORY | 122 |
| SECTIONALS | 708 |
| STANDARD_TIME | 73 |
| TIMING | 16 |

## Top Active Candidates

| Rank | Score | Class | Rows | Coverage | Path |
|---:|---:|---|---:|---:|---|
| 1 | 172 | PERFORMANCE_WAREHOUSE | 879,784 | 10 | `docs/performance-intelligence/warehouse/edgeiq_performance_fact_warehouse_v1.csv` |
| 2 | 170 | PERFORMANCE_WAREHOUSE | 879,784 | 11 | `docs/performance-intelligence/warehouse/performance-facts/eiq_performance_facts_snapshot_23704301541550b883a8a05d3419c3a1/canonical_performance_facts.csv` |
| 3 | 152 | PERFORMANCE_WAREHOUSE | 879,784 | 10 | `docs/performance-intelligence/warehouse/performance-facts-corrected/eiq_performance_facts_v0_2_a0c3715ab506d19f9301d8a4/canonical_performance_facts_v0_2.csv` |
| 4 | 145 | LENGTHS_V_STANDARD | SKIPPED_OVERSIZE | 11 | `public/data/edgeiq_historical_run_observation_fact_v2.csv` |
| 5 | 145 | LENGTHS_V_STANDARD | SKIPPED_OVERSIZE | 11 | `public/data/edgeiq_historical_run_observation_fact_v2_CANDIDATE.csv` |
| 6 | 126 | STANDARD_TIME | 39 | 7 | `public/data/edgeiq_benchmark_eligibility_fact_v1.csv` |
| 7 | 126 | STANDARD_TIME | 51,769 | 3 | `docs/performance-intelligence/lengths-v-standard/edgeiq_race_lengths_v_standard_fact_v1.csv` |
| 8 | 125 | SECTIONALS | 879,784 | 11 | `public/data/edgeiq_historical_results_warehouse_v2_graphql.csv` |
| 9 | 125 | SECTIONALS | 227,804 | 11 | `public/data/edgeiq_graphql_master_v2.csv` |
| 10 | 125 | LENGTHS_V_STANDARD | 533,387 | 4 | `docs/performance-intelligence/epi/edgeiq_epi_performance_fact_v1.csv` |
| 11 | 123 | SECTIONALS | 12,418 | 11 | `public/data/edgeiq_graphql_q1_apr_2025_MASTER_v1.csv` |
| 12 | 121 | SECTIONALS | 5,424 | 11 | `public/data/edgeiq_graphql_november_2024_results_v1.csv` |
| 13 | 121 | SECTIONALS | 5,420 | 11 | `public/data/edgeiq_graphql_november_2025_results_v1.csv` |
| 14 | 121 | SECTIONALS | 5,336 | 11 | `public/data/edgeiq_graphql_june_2024_results_v1.csv` |
| 15 | 121 | SECTIONALS | 5,305 | 11 | `public/data/edgeiq_graphql_may_2025_results_v1.csv` |
| 16 | 121 | SECTIONALS | 5,272 | 11 | `public/data/edgeiq_graphql_june_2025_results_v1.csv` |
| 17 | 121 | SECTIONALS | 5,160 | 11 | `public/data/edgeiq_graphql_may_2024_results_v1.csv` |
| 18 | 121 | SECTIONALS | 5,147 | 11 | `public/data/edgeiq_graphql_october_2024_results_v1.csv` |
| 19 | 121 | SECTIONALS | 5,141 | 11 | `public/data/edgeiq_graphql_october_2025_results_v1.csv` |
| 20 | 121 | SECTIONALS | 5,085 | 11 | `public/data/edgeiq_graphql_may_2026_results_v1.csv` |
| 21 | 121 | SECTIONALS | 5,083 | 11 | `public/data/edgeiq_graphql_december_2024_results_v1.csv` |
| 22 | 121 | SECTIONALS | 4,933 | 11 | `public/data/edgeiq_graphql_august_2024_results_v1.csv` |
| 23 | 121 | SECTIONALS | 4,910 | 11 | `public/data/edgeiq_graphql_july_2024_results_v1.csv` |
| 24 | 121 | SECTIONALS | 4,877 | 11 | `public/data/edgeiq_graphql_september_2024_results_v1.csv` |
| 25 | 121 | SECTIONALS | 4,872 | 11 | `public/data/edgeiq_graphql_july_2025_results_v1.csv` |
| 26 | 121 | SECTIONALS | 4,832 | 11 | `public/data/edgeiq_graphql_december_2025_results_v1.csv` |
| 27 | 121 | SECTIONALS | 4,777 | 11 | `public/data/edgeiq_graphql_july_2023_results_v1.csv` |
| 28 | 121 | SECTIONALS | 4,768 | 11 | `public/data/edgeiq_graphql_march_2026_results_v1.csv` |
| 29 | 121 | SECTIONALS | 4,743 | 11 | `public/data/edgeiq_graphql_march_2024_results_v1.csv` |
| 30 | 121 | SECTIONALS | 4,731 | 11 | `public/data/edgeiq_graphql_march_2023_results_v1.csv` |
| 31 | 121 | SECTIONALS | 4,718 | 11 | `public/data/edgeiq_graphql_september_2007_results_v1.csv` |
| 32 | 121 | SECTIONALS | 4,688 | 11 | `public/data/edgeiq_graphql_april_2026_results_v1.csv` |
| 33 | 121 | SECTIONALS | 4,655 | 11 | `public/data/edgeiq_graphql_january_2026_results_v1.csv` |
| 34 | 121 | SECTIONALS | 4,640 | 11 | `public/data/edgeiq_graphql_september_2025_results_v1.csv` |
| 35 | 121 | SECTIONALS | 4,634 | 11 | `public/data/edgeiq_graphql_november_2023_results_v1.csv` |
| 36 | 121 | SECTIONALS | 4,620 | 11 | `public/data/edgeiq_graphql_august_2025_results_v1.csv` |
| 37 | 121 | SECTIONALS | 4,571 | 11 | `public/data/edgeiq_graphql_june_2023_results_v1.csv` |
| 38 | 121 | SECTIONALS | 4,562 | 11 | `public/data/edgeiq_graphql_may_2023_results_v1.csv` |
| 39 | 121 | SECTIONALS | 4,498 | 11 | `public/data/edgeiq_graphql_april_2023_results_v1.csv` |
| 40 | 121 | SECTIONALS | 4,465 | 11 | `public/data/edgeiq_graphql_january_2024_results_v1.csv` |
| 41 | 121 | SECTIONALS | 4,405 | 11 | `public/data/edgeiq_graphql_april_2024_results_v1.csv` |
| 42 | 121 | SECTIONALS | 4,332 | 11 | `public/data/edgeiq_graphql_february_2023_results_v1.csv` |
| 43 | 121 | SECTIONALS | 4,329 | 11 | `public/data/edgeiq_graphql_may_2007_results_v1.csv` |
| 44 | 121 | SECTIONALS | 4,322 | 11 | `public/data/edgeiq_graphql_january_2023_results_v1.csv` |
| 45 | 121 | SECTIONALS | 4,293 | 11 | `public/data/edgeiq_graphql_february_2026_results_v1.csv` |
| 46 | 121 | SECTIONALS | 4,265 | 11 | `public/data/edgeiq_graphql_june_2008_results_v1.csv` |
| 47 | 121 | SECTIONALS | 4,249 | 11 | `public/data/edgeiq_graphql_december_2023_results_v1.csv` |
| 48 | 121 | SECTIONALS | 4,245 | 11 | `public/data/edgeiq_graphql_may_2020_results_v1.csv` |
| 49 | 121 | SECTIONALS | 4,225 | 11 | `public/data/edgeiq_graphql_october_2023_results_v1.csv` |
| 50 | 121 | SECTIONALS | 4,223 | 11 | `public/data/edgeiq_graphql_june_2026_results_v1.csv` |
| 51 | 121 | SECTIONALS | 4,192 | 11 | `public/data/edgeiq_graphql_may_2003_results_v1.csv` |
| 52 | 121 | SECTIONALS | 4,169 | 11 | `public/data/edgeiq_graphql_june_2007_results_v1.csv` |
| 53 | 121 | SECTIONALS | 4,144 | 11 | `public/data/edgeiq_graphql_may_2008_results_v1.csv` |
| 54 | 121 | SECTIONALS | 4,143 | 11 | `public/data/edgeiq_graphql_february_2024_results_v1.csv` |
| 55 | 121 | SECTIONALS | 4,097 | 11 | `public/data/edgeiq_graphql_april_2006_results_v1.csv` |
| 56 | 121 | SECTIONALS | 4,089 | 11 | `public/data/edgeiq_graphql_september_2023_results_v1.csv` |
| 57 | 121 | SECTIONALS | 4,048 | 11 | `public/data/edgeiq_graphql_november_2013_results_v1.csv` |
| 58 | 121 | SECTIONALS | 4,038 | 11 | `public/data/edgeiq_graphql_may_2021_results_v1.csv` |
| 59 | 121 | SECTIONALS | 4,018 | 11 | `public/data/edgeiq_graphql_november_2004_results_v1.csv` |
| 60 | 121 | SECTIONALS | 3,976 | 11 | `public/data/edgeiq_graphql_april_2007_results_v1.csv` |
| 61 | 121 | SECTIONALS | 3,967 | 11 | `public/data/edgeiq_graphql_november_2002_results_v1.csv` |
| 62 | 121 | SECTIONALS | 3,963 | 11 | `public/data/edgeiq_graphql_october_2013_results_v1.csv` |
| 63 | 121 | SECTIONALS | 3,960 | 11 | `public/data/edgeiq_graphql_august_2023_results_v1.csv` |
| 64 | 121 | SECTIONALS | 3,947 | 11 | `public/data/edgeiq_graphql_october_2020_results_v1.csv` |
| 65 | 121 | SECTIONALS | 3,932 | 11 | `public/data/edgeiq_graphql_august_2008_results_v1.csv` |
| 66 | 121 | SECTIONALS | 3,912 | 11 | `public/data/edgeiq_graphql_may_2006_results_v1.csv` |
| 67 | 121 | SECTIONALS | 3,910 | 11 | `public/data/edgeiq_graphql_november_2007_results_v1.csv` |
| 68 | 121 | SECTIONALS | 3,884 | 11 | `public/data/edgeiq_graphql_may_2019_results_v1.csv` |
| 69 | 121 | SECTIONALS | 3,872 | 11 | `public/data/edgeiq_graphql_june_2013_results_v1.csv` |
| 70 | 121 | SECTIONALS | 3,869 | 11 | `public/data/edgeiq_graphql_may_2012_results_v1.csv` |
| 71 | 121 | SECTIONALS | 3,853 | 11 | `public/data/edgeiq_graphql_march_2008_results_v1.csv` |
| 72 | 121 | SECTIONALS | 3,851 | 11 | `public/data/edgeiq_graphql_may_2005_results_v1.csv` |
| 73 | 121 | SECTIONALS | 3,832 | 11 | `public/data/edgeiq_graphql_october_2005_results_v1.csv` |
| 74 | 121 | SECTIONALS | 3,811 | 11 | `public/data/edgeiq_graphql_november_2005_results_v1.csv` |
| 75 | 121 | SECTIONALS | 3,780 | 11 | `public/data/edgeiq_graphql_june_2005_results_v1.csv` |
| 76 | 121 | SECTIONALS | 3,765 | 11 | `public/data/edgeiq_graphql_october_2012_results_v1.csv` |
| 77 | 121 | SECTIONALS | 3,760 | 11 | `public/data/edgeiq_graphql_august_2005_results_v1.csv` |
| 78 | 121 | SECTIONALS | 3,758 | 11 | `public/data/edgeiq_graphql_january_2008_results_v1.csv` |
| 79 | 121 | SECTIONALS | 3,757 | 11 | `public/data/edgeiq_graphql_june_2021_results_v1.csv` |
| 80 | 121 | SECTIONALS | 3,752 | 11 | `public/data/edgeiq_graphql_june_2006_results_v1.csv` |
| 81 | 121 | SECTIONALS | 3,750 | 11 | `public/data/edgeiq_graphql_april_2008_results_v1.csv` |
| 82 | 121 | SECTIONALS | 3,749 | 11 | `public/data/edgeiq_graphql_july_2005_results_v1.csv` |
| 83 | 121 | SECTIONALS | 3,741 | 11 | `public/data/edgeiq_graphql_july_2010_results_v1.csv` |
| 84 | 121 | SECTIONALS | 3,736 | 11 | `public/data/edgeiq_graphql_may_2010_results_v1.csv` |
| 85 | 121 | SECTIONALS | 3,723 | 11 | `public/data/edgeiq_graphql_october_2004_results_v1.csv` |
| 86 | 121 | SECTIONALS | 3,710 | 11 | `public/data/edgeiq_graphql_october_2007_results_v1.csv` |
| 87 | 121 | SECTIONALS | 3,708 | 11 | `public/data/edgeiq_graphql_october_2018_results_v1.csv` |
| 88 | 121 | SECTIONALS | 3,699 | 11 | `public/data/edgeiq_graphql_june_2010_results_v1.csv` |
| 89 | 121 | SECTIONALS | 3,692 | 11 | `public/data/edgeiq_graphql_july_2013_results_v1.csv` |
| 90 | 121 | SECTIONALS | 3,685 | 11 | `public/data/edgeiq_graphql_july_2008_results_v1.csv` |
| 91 | 121 | SECTIONALS | 3,679 | 11 | `public/data/edgeiq_graphql_november_2018_results_v1.csv` |
| 92 | 121 | SECTIONALS | 3,656 | 11 | `public/data/edgeiq_graphql_september_2008_results_v1.csv` |
| 93 | 121 | SECTIONALS | 3,642 | 11 | `public/data/edgeiq_graphql_june_2018_results_v1.csv` |
| 94 | 121 | SECTIONALS | 3,609 | 11 | `public/data/edgeiq_graphql_november_2014_results_v1.csv` |
| 95 | 121 | SECTIONALS | 3,607 | 11 | `public/data/edgeiq_graphql_december_2009_results_v1.csv` |
| 96 | 121 | SECTIONALS | 3,604 | 11 | `public/data/edgeiq_graphql_june_2012_results_v1.csv` |
| 97 | 121 | SECTIONALS | 3,603 | 11 | `public/data/edgeiq_graphql_january_2005_results_v1.csv` |
| 98 | 121 | SECTIONALS | 3,602 | 11 | `public/data/edgeiq_graphql_november_2020_results_v1.csv` |
| 99 | 121 | SECTIONALS | 3,596 | 11 | `public/data/edgeiq_graphql_january_2007_results_v1.csv` |
| 100 | 121 | SECTIONALS | 3,581 | 11 | `public/data/edgeiq_graphql_september_2013_results_v1.csv` |

## Audit

- **PASS** — `phase1a_inputs_available`: Both Phase 1A inventory inputs exist.
- **PASS** — `checkpoint_archive_exclusion`: Checkpoint, archive, backup and legacy paths excluded.
- **PASS** — `active_candidates_detected`: shortlisted_candidates=2853
- **PASS** — `high_priority_candidates_detected`: high_priority_candidates=714
- **PASS** — `essential_candidate_classes`: all essential classes detected

## Governance

- Production datasets were not modified.
- No builder was executed.
- No source was declared canonical.
- No benchmark threshold was changed.
- No synthetic rows were created.
