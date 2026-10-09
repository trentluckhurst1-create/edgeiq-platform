# EDGEiQ — New-feature eligibility decision (source-only)

Status: **NO ELIGIBLE FAMILY CERTIFIED; NO FIT AUTHORISED.**
Review of committed scripts only; no outcome data, sealed years, model metrics or SP values read.

## Exclusions established from source
- Stage011 baseline: current distance, history, lengths-versus-standard, margins, distance history, strict-prior clean placing, connection context. See `run_v2_stage011_clean_placing.py`.
- Stage016: current weight, weight change, distance change, prior same-class starts, prior exact-distance starts and missingness indicators. See `run_v2_stage016_context_family.py`.
- Current-class one-hot representation **already fitted** in Stage018B (`run_v2_stage018b_categorical_class.py`). Do not relabel it a new family.
- Absolute class identity/coverage already investigated in Stage022B; `eligible_runner_classification_076p.csv` was not certified as dense clean authority. Prior Grok review reported LAB076P 77.8% coverage, 47 duplicate horse/date keys and mixed trials/picnic/jumps. Not eligible.
- Weight schemas and provenance already investigated in Stage018C/019. Timing/form-line and EPI remain parked or quarantined.

## Potential remaining category, NOT a qualified manifest
A horse age/sex or race-condition/going field could be pre-race information in principle. Australian official race forms display age, sex and track information, but this **does not establish** a point-in-time exact-key join or >=90% coverage in the local certified V2 universe. The Stage018 and Stage022A scripts searched age/sex/going authorities; this inspection has not recovered certified quantitative coverage or leakage lineage.

## Next decision gate
No new fit or run. A future proposal must name a **specific** source file and columns, demonstrate exact certified `(_race,_horse)` identity (or certified alternative), >=90% non-null coverage on the V2 population, source timestamp before race, no outcome/market leakage, and prove the manifest has never been fitted in previous Stage011–Stage044 tests. If none qualifies, STOP; do not manufacture a feature family or silently loosen the threshold.

Source review is insufficient to certify coverage because the V2 warehouse and most historical authorities are stored in the user's local Windows research workspace, not the GitHub tree. This document records exclusions and remaining evidence gaps, not a completed data-level certification.


## LAB089 exact-identity gate — FAIL (user-run 2026-10-09)

Source: `python scripts/research/run_v2_stage017b_lab089_identity.py`, user-provided console output.

- Authority duplicate exact keys: **0**.
- Certified V2 runners: **91,434**; exact matches **30,253**; coverage **33.0872541943%**, below required **90%**.
- Yearly exact matches: 2021 **8,279/22,578 (36.67%)**; 2022 **2,199/7,459 (29.48%)**; 2023 **8,400/30,163 (27.85%)**; 2024 **11,375/31,234 (36.42%)**.
- Race/date overlap: **3,105/7,185 (43.22%)**.

**Decision: REJECT LAB089 going family as an eligible new feature authority in the present V2 certified universe.** Do not fit, relabel unmatched records, or use fuzzy identity matching. These figures measure exact-match coverage, not within-matched-row feature non-null coverage or PIT validity; those checks are unnecessary after this gate fails.
