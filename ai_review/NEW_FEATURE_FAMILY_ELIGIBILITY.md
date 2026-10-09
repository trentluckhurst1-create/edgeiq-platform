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
