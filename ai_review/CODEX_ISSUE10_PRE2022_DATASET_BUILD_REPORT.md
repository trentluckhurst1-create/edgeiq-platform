# CODEX Issue #10 Pre-2022 Dataset Build Report

Date: 2026-10-11  
Branch: `codex/issue-10-pre2022-partition-builder`  
Scope: local source partition and strict-prior feature construction only. No model fitting, scoring, market access, production change, or sealed-year access.

## Decision

**PASS for Grok review package. NOT authorised for modelling.**

The mixed consolidated warehouse was not scanned because its companion summary reports `date_max=2026-06-24`. Instead, the builder used the underlying monthly GraphQL result files and selected only filenames with years <= 2021. This creates a deterministic local pre-2022 all-runner partition and strict-prior horse/jockey/trainer feature matrix without reading 2022-2026 source files.

## Exact Commands

```powershell
cd C:\EDGEIQ_PROFITABILITY_RESEARCH
python -m py_compile .\scripts\research\build_issue10_pre2022_pit_partition.py .\tests\test_issue10_pre2022_partition.py
python -m unittest .\tests\test_issue10_pre2022_partition.py
.\scripts\research\build_issue10_pre2022_pit_partition.ps1
```

Equivalent direct command:

```powershell
cd C:\EDGEIQ_PROFITABILITY_RESEARCH
python .\scripts\research\build_issue10_pre2022_pit_partition.py --source-dir "C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\public\data" --out outputs/research/issue10_pre2022_partition --cutoff-date 2022-01-01 --allow-local-pre2022-monthly-export
```

## Source Selection

Rejected source:

- `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\public\data\edgeiq_historical_results_warehouse_v2_graphql.csv`
- Reason: mixed consolidated CSV includes rows through 2026-06-24 according to `edgeiq_historical_results_warehouse_v2_graphql_summary.csv`; scanning it would violate the sealed-year boundary.

Accepted local partition route:

- Directory: `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\public\data`
- Pattern: `edgeiq_graphql_*_results_v1.csv`
- Selection rule: filename year <= 2021 only.
- Selected source files: **257**
- Read source files: **220**
- Skipped empty-like/schema-less monthly files: **37**
- Sealed 2025-2026 file access: **NO**
- Market/SP/BSP/odds columns read: **NO**

## Build Results

Local generated artifacts:

- `outputs/research/issue10_pre2022_partition/ISSUE10_PRE2022_RUNNER_PARTITION.csv`
- `outputs/research/issue10_pre2022_partition/ISSUE10_PRE2022_PIT_FEATURE_MATRIX.csv`
- `outputs/research/issue10_pre2022_partition/ISSUE10_RACE_AUDIT.csv`
- `outputs/research/issue10_pre2022_partition/ISSUE10_BUILD_MANIFEST.json`

Large CSVs are intentionally not committed.

Key manifest results:

| Metric | Value |
|---|---:|
| Source rows read | 678,857 |
| Invalid date rows | 0 |
| Post-cutoff rows in selected files | 0 |
| Runner partition rows | 678,857 |
| Total races | 54,831 |
| Eligible races | 52,828 |
| Eligible PIT runner rows | 550,720 |
| Non-flat provisional excluded races | 1,500 |
| Not-exactly-one-winner excluded races | 509 |
| No-starter excluded races | 1 |

Large local output checksums:

- Runner partition SHA256: `07f52642028934be058a91899534e0192960da18628f0e7996ca2bf6dfcd75b2`
- PIT feature matrix SHA256: `34add48ff515cd53237c8d83238ea69cc5a9d108ee0f39dadd3bc594e17ba3c1`
- Race audit SHA256: `c98213067e7b65ca679ff8e23b6028ba02fb3d1d65cbfd645288222d473d55f9`

## Year Coverage

| Year | Source rows | Races | Eligible races | Eligible starters | Flag |
|---:|---:|---:|---:|---:|---|
| 2000 | 15,088 | 1,396 | 1,339 | 14,538 |  |
| 2001 | 34,374 | 3,159 | 3,023 | 33,100 |  |
| 2002 | 38,065 | 3,378 | 3,240 | 35,249 |  |
| 2003 | 36,995 | 2,912 | 2,798 | 30,484 |  |
| 2004 | 32,700 | 2,685 | 2,574 | 26,938 |  |
| 2005 | 43,376 | 3,560 | 3,417 | 35,705 |  |
| 2006 | 39,570 | 3,215 | 3,081 | 32,390 |  |
| 2007 | 44,221 | 3,476 | 3,306 | 35,006 |  |
| 2008 | 42,136 | 3,346 | 3,205 | 33,396 |  |
| 2009 | 30,070 | 2,371 | 2,299 | 23,886 |  |
| 2010 | 27,721 | 2,183 | 2,117 | 21,606 |  |
| 2011 | 0 | 0 | 0 | 0 | Missing; all monthly files empty-like |
| 2012 | 39,398 | 3,135 | 3,059 | 31,135 |  |
| 2013 | 41,278 | 3,279 | 3,206 | 32,425 |  |
| 2014 | 36,589 | 2,959 | 2,884 | 29,163 |  |
| 2015 | 26,324 | 2,053 | 1,991 | 20,781 |  |
| 2016 | 4,842 | 399 | 398 | 3,927 | Sparse; only Jan/Feb non-empty |
| 2017 | 0 | 0 | 0 | 0 | Missing; all monthly files empty-like |
| 2018 | 38,441 | 3,033 | 2,926 | 29,820 |  |
| 2019 | 34,485 | 2,701 | 2,590 | 26,652 |  |
| 2020 | 38,691 | 2,869 | 2,756 | 28,548 |  |
| 2021 | 34,493 | 2,722 | 2,619 | 25,971 | Reused-development-era year; not independent validation |

## Identity and Completeness

Runner identity:

- Eligible races passed internal `source_race_id + source_runner_id` uniqueness.
- Race eligibility required exactly one non-scratched winner.
- Scratched runners are retained in the runner partition but excluded from eligible PIT starters.

Horse identity:

- Uses `horse_code` when present, otherwise normalised horse name.
- This is sufficient for a local source partition review, but it is **not** proof of equivalence to Stage011 canonical horse IDs.

Jockey/trainer identity:

- Uses `jockey_code` / `trainer_code` when present, otherwise normalised names.
- Missing jockey/trainer ID is explicitly distinguished from zero prior history.

Outstanding identity limitation:

- Canonical EDGEiQ race/horse identity equivalence remains unproven and must be reviewed before this dataset can be connected to Stage011 or any promoted model pipeline.

## PIT Feature Construction

The feature matrix contains only strict-prior race-date aggregates:

- Horse prior starts/wins/top3/rates/mean finish/days since last run.
- Trainer prior starts/wins/top3/rates.
- Jockey prior starts/wins/top3/rates.
- Current declared non-market fields from the source partition: field size, barrier position percentage, distance and weight.

Same-date rule:

- For all races on the same date, features are computed before any rows from that date are added to entity histories.
- Unit test `test_same_date_rows_do_not_feed_prior_history` verifies this rule synthetically.

## Governance Status

- Model fitting: **NO**
- Model scoring: **NO**
- Stage011 modification: **NO**
- Production modification: **NO**
- Market/SP/BSP/odds access: **NO**
- Sealed 2025-2026 file access: **NO**
- Permissible-use status: **REQUIRES_GROK_AND_OWNER_REVIEW_BEFORE_MODEL_USE**

## Remaining Review Questions

1. Does Grok accept filename-year monthly source selection as a valid sealed-year-safe partition method?
2. Are `horse_code`, `jockey_code`, and `trainer_code` acceptable identity anchors for pre-2022 modelling, or is canonical crosswalk certification required first?
3. Should 2021 be included only as training history, excluded from evaluation, or excluded entirely because it overlaps the Stage011 development era?
4. Should sparse 2016 be excluded from future train/evaluation windows?
5. Is source licensing/provenance sufficient for research model use?

## Recommendation

Submit this package for Grok review. If accepted, the next authorised step should be a **design-only** fixed chronological pre-2022 experiment protocol using this dataset, not immediate fitting. A reasonable candidate protocol would train on older complete years and evaluate only on later certified pre-2022 years, with 2011/2017 excluded and 2016 handled explicitly as sparse.
