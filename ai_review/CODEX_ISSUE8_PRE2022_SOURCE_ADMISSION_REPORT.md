# CODEX Issue #8 Pre-2022 Source Admission Report

Date: 2026-10-11  
Branch: `codex/issue-8-pre2022-admission`  
Scope: source admission and experiment design only. No fitting, scoring, profitability testing, market access, production change, or sealed-year access.

## Decision

**BLOCKED. Not ready to run.**

The repository contains useful pre-2021 outcome-inventory evidence, but the admitted evidence does **not** contain a certified pre-2022, all-runner, point-in-time feature matrix with complete race fields, winner labels, canonical identity certification, jockey/trainer coverage, and immutable lineage. Stage011 remains untouched.

## Commands

```powershell
cd C:\EDGEIQ_PROFITABILITY_RESEARCH
python -m py_compile .\scripts\research\run_issue8_pre2022_source_admission.py .\tests\test_issue8_pre2022_source_admission.py
python -m unittest .\tests\test_issue8_pre2022_source_admission.py
.\scripts\research\run_issue8_pre2022_source_admission.ps1
```

Equivalent direct Python command:

```powershell
cd C:\EDGEIQ_PROFITABILITY_RESEARCH
python .\scripts\research\run_issue8_pre2022_source_admission.py --repo-root . --out outputs/research/issue8_pre2022_source_admission
```

## Evidence Reviewed

The admission script inspected named manifests and prior pre-2021 governance reports only. It did not row-scan raw mixed-year warehouses and did not inspect 2025-2026 data.

Key existing evidence:

- Prior Gate 2 inspected **644,364 pre-2021 rows** under column restrictions.
- It found **50,671 provisional flat races**.
- It found **50,209 exactly-one-winner and unique runner-key provisional flat races**, a **99.088236%** eligible-flat rate.
- It still stopped for `NO_CERTIFIED_PRE_RACE_CANDIDATE_BUILDER`.
- Missing years remain **2011** and **2017**.
- **2016** remains sparse in the provisional all-runner inventory.
- LAB245B source-code inspection passed strict-date lineage for `hist_runs` only, subject to upstream input integrity.
- LAB245B identity remains imported/unproven: canonical race/horse IDs were not proven equivalent to historical `race_id` / `runner_id`.

Named source status:

- Issue #5 LAB026 clean placing partition: admitted 2021-2024 only; not pre-2022 expansion evidence.
- Issue #5 LAB031 context partition: admitted 2021-2024 only; not pre-2022 expansion evidence.
- LAB245B compact performance bridge: 91,651 rows / 7,200 races; strict-date precedent only for 2021-2024.
- LAB245B warehouse runner LVS: 39,830 races in manifest, but upstream identity equivalence remains uncertified.
- D45 and Stage006 support the Stage011-era 2021-2024 pipeline; neither certifies pre-2022 all-runner PIT model rows.
- LAB075/LAB076 first-starter artifacts are not all-runner full-field populations and must not be used as the base model universe.

Generated audit artifacts:

- `outputs/research/issue8_pre2022_source_admission/ISSUE8_PRE2022_ADMISSION_AUDIT.json`
- `outputs/research/issue8_pre2022_source_admission/ISSUE8_PRE2022_SOURCE_ADMISSION_SUMMARY.csv`
- `outputs/research/issue8_pre2022_source_admission/ISSUE8_PRE2022_BLOCKERS.csv`

## Blockers

| Blocker | Status | Minimum resolution |
|---|---:|---|
| No certified pre-2022 all-runner PIT matrix | STOP | Produce a sealed-free pre-2022 all-runner PIT matrix with complete fields, winner labels, date bounds, checksums and lineage. |
| Canonical identity imported/unproven | STOP | Certify a one-to-one race/runner identity bridge with zero collisions and explicit duplicate/scratch handling. |
| First-starter artifacts are not all-runner | STOP | Use only complete all-runner race fields as the model population. |
| Missing/sparse historical years | STOP | Document admissible year coverage and freeze train/eval windows that exclude or explicitly handle gaps. |
| No certified pre-2022 jockey/trainer PIT coverage | STOP | Build and audit strict-prior jockey/trainer histories by canonical identity before any model comparison. |
| Licensing/provenance not certified for model use | STOP | Attach allowed-use status and immutable lineage manifest to any historical partition export. |

## Minimal Source-Build Path

1. Authorise a one-time upstream partition export from the named historical results warehouse, with row access limited to pre-2022 candidate fields only.
2. The export must filter by race date before any join, feature construction, model fitting, or scoring.
3. Include only non-market fields required for source admission: race identity, runner identity, race date, finish/winner label, scratch/non-runner status, horse identity, jockey/trainer identity, barrier, distance, class/state/track metadata, and any declared current-race fields proposed for PIT use.
4. Exclude SP, BSP, odds, prices, market, betting, stake and return columns.
5. Produce a manifest with source path, source checksum, output checksum, row count, race count, min/max race date, year counts, required columns, forbidden-column scan, and lineage.
6. Certify canonical identity equivalence from historical `race_id`/`runner_id` to canonical race/horse keys with zero collisions or an explicit quarantine file.
7. Certify complete-field status: exactly one winner per race, no duplicate runner keys, scratches handled deterministically, and field sizes matching declared starters.
8. Extend the strict-date LAB245B `hist_runs` construction to the admitted pre-2022 population only after upstream integrity passes.
9. Build strict-prior jockey/trainer histories using only races before the target race date; same-date starts must be excluded unless an independently timestamped ordering exists.
10. Request Grok review of the partition, identity bridge, feature lineage and coverage before any fit or score.

## Fixed Experiment Plan If Unblocked

If Grok certifies a pre-2022 all-runner PIT matrix, the first model experiment should be a single frozen chronological bake-off, not an open search:

- Population: only certified all-runner flat races with exactly one winner and complete starter fields.
- Features: fixed non-market feature manifest from the certified matrix, including separately flagged first-starter and jockey/trainer coverage diagnostics.
- Exclusions: market/SP/BSP/odds, sealed 2025-2026, and any post-race outcome-derived current-race fields.
- Split: train on older certified years and evaluate on later disjoint pre-2022 years, preserving any genuinely unexposed historical window where possible.
- Metrics: race log loss, Brier score, top-1/top-2/top-3, MRR, calibration buckets, coverage by year, first-starter cohort and jockey/trainer missingness cohorts.
- Stopping rule: one run of the frozen comparison after approval; no threshold tuning, no coefficient optimization, no iterative feature mining.
- Evidence class: development evidence unless Grok confirms the evaluation window was genuinely unexposed.

## Conclusion

Issue #8 cannot proceed to model fitting from the current repository evidence. The shortest compliant path is a governed pre-2022 all-runner source partition plus canonical identity and PIT feature-lineage certification. Until that exists, any backtest would be a fake backtest over an uncertified population.

**READY TO RUN: NO**
