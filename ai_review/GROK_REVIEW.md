# Independent Grok Review — Issue #23 / Stage011

**Review date:** 2026-10-13
**Source:** Grok review supplied verbatim in substance by the project owner; the PR comment preserves its summary. Grok does not have GitHub write access through this workflow.

## Verdict

**NO-GO** on model promotion, scorer enablement and profitability claims. Stage011 remains frozen champion; reused 2022–2024 Top-1 experiments provide no new holdout confirmation.

## Engineering blockers

1. Stage006 `_horse` and LAB245B `canonical_horse_id` are not yet proven identical via an authorised, deterministic crosswalk. Stage037B/038 exact normalized name + race_date evidence is not a certified horse-key mapping.
2. Strict-prior chronological identity is required for all LVS aggregations, including same-date ambiguities. Full runner LVS source ends 2026-06-21, leaving a gap before the 2026-10-14 target.
3. Exact training-builder feature semantics for all 35 Stage011 fields must match, including career peak, distance-window calculations, jockey/trainer priors and current race context.
4. Fail-closed 104-runner completeness. Genuine quote freshness, side, commission, depth, liability, suspension and joins are independently required before even a dry-run BACK/LAY readiness assessment.

## Confirmed quantitative evidence (from project operator)

- LAB245B runner LVS warehouse 502,268 rows, current maximum date 2026-06-21.
- 42/42 linked target horses have nonempty 2025–26 historical LVS records.
- On 30,918 mature-history comparisons in the compact training bridge, `lvs_last1`, `lvs_mean3`, `lvs_mean5`, `lvs_median5`, `lvs_std5`, and `lvs_worst5` reproduce at 100%; `lvs_peak` matches 91.2931%, likely affected by earlier career records but **not yet proven**.
- 27 same-date chronological ambiguities reported.

## Reusable identity-governance evidence already discovered on branch

- `LIVE_PERFORMANCE_BUILDERS/build_edgeiq_horse_performance_identity_map_v1.py`
- `LIVE_PERFORMANCE_BUILDERS/build_edgeiq_current_ra_horse_identity_crosswalk_v1.py`
- `config/performance-intelligence/edgeiq_horse_performance_identity_map_v1.csv`
- `docs/performance-intelligence/horse-performance-rating/method-governance/EDGEIQ_HORSE_PERFORMANCE_IDENTITY_MAP_RECOVERY_V1.md`

**Caution:** Existing map contains evidence-backed `RCOM_HORSE_...` and `RA_HORSE_...` namespaces; these are not automatically the `EIQ_HORSE_...` training IDs or LAB245B `canonical_horse_id`. Do not join simply on similar names.

## Constraints

No sealed 2025–26 evaluation, market/SP training features, model promotion, betting recommendations, production mutation, deployment, or merge. Keep scorer fail closed until complete audited 35-feature parity and authorisation.
