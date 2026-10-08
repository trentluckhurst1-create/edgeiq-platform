# EDGEiQ Model V2 — Review Gate after Stage019

## Governance
- Completely new V2 model; V1 D99/D112 are benchmarks only.
- 2025–2026 remain SEALED and have not been inspected.
- Market/SP excluded from model features.
- Fixed HGB during feature-family discovery: max_iter=200, learning_rate=.05, max_leaf_nodes=5, l2_regularization=1, random_state=42.
- Chronological prior-year training, tests on 2022/2023/2024 development years.
- No threshold mining or architecture shopping.
- EPI is QUARANTINED: downstream lineage exists but original construction formula/no-market provenance could not be certified.

## Certified V2 universe
91,434 runners / 7,185 single-winner races after excluding 15 abnormal/dead-heat/zero-winner races.
2021 22,578 / 1,775 races
2022 7,459 / 612
2023 30,163 / 2,396
2024 31,234 / 2,402

## Progress
Stage007 performance-only baseline:
2022 LL 2.392604 Top1 .15850
2023 LL 2.428795 Top1 .13856
2024 LL 2.435250 Top1 .15862

Stage008 dense connection/context promoted:
2022 LL 2.136264 Top1 .23203
2023 LL 2.158470 Top1 .18948
2024 LL 2.131711 Top1 .22273

Stage011 clean placing promoted:
2022 LL 2.125060 Top1 .22549
2023 LL 2.131427 Top1 .20659
2024 LL 2.102223 Top1 .22981

Stage016 exact LAB031 current weight/change + distance change + class/distance experience:
2022 LL 2.118553 Top1 .22059
2023 LL 2.130119 Top1 .21619
2024 LL 2.097480 Top1 .22606
Consistent LL improvement but mixed Top1. Retained serious challenger, not champion.

Stage017 LAB089 prep/spell:
Identity exact but sparse 30,253/91,434 runners (33.09%), same footprint as timing/form-line.
Whole-race covered test only 34/84/122 races in 2022/23/24.
LL: 2022 worsened 2.40079->2.40817; 2023 improved 2.21783->2.18259; 2024 worsened 2.07139->2.10619.
Parked, no slicing.

Stage018A/B data-estate scan found dense exact authorities:
LAB037 prior jockey/trainer intelligence: 631,102 rows; exact V2 coverage 90,235/91,434 = 98.69%.
LAB045A weight features: 631,102 rows; same 98.69% exact coverage.
LAB045B class strength excluded because EPI-derived.

Stage018C dense LAB045A weight structure on Stage011:
Features:
relative_to_race_mean
relative_to_race_min
relative_to_race_max
weight_rank_in_full_field
weight_pct_in_full_field
full_field_weight_count
previous_start_weight
change_from_previous_start
prior_recent_weight_average
change_from_recent_average

Results:
2022 LL 2.1195909784 Top1 .220588 Top2 .410131 Top3 .522876 MRR .436394
2023 LL 2.1258415268 Top1 .217028 Top2 .385643 Top3 .525042 MRR .428856
2024 LL 2.0955626445 Top1 .231474 Top2 .417152 Top3 .548293 MRR .446605

Decision: PROMOTED. Current V2 champion.

V1 D99 benchmark:
2022 LL 2.099976855
2023 LL 2.129454621
2024 LL 2.084420614
V2 Stage018C now beats D99 in 2023, trails by .01961 in 2022 and .01114 in 2024.

Stage019 LAB037 clean raw/shrunk jockey/trainer win rates on Stage018C:
All metrics bit-for-bit identical to Stage018C. KILLED as no-op. EPI/residual-derived LAB037 fields were explicitly excluded.

## Sparse-family finding
Timing, form-line, and LAB089 appear to share the same 30,253-runner historical footprint. Do not globally judge these as universal features. Later specialist/subpopulation design may be appropriate. Pace is also specialist (no 2021/22 coverage). First-starter identity remains unresolved.

## Current question for independent review
1. Challenge whether Stage018C promotion is scientifically justified.
2. Identify leakage/provenance risks in LAB045A weight features, especially race-relative weight fields. These are current-race declared weights and within-race transforms; assess whether they are legitimate pre-race information.
3. Given EPI quarantine and sparse-family findings, rank the next 2–3 genuinely independent dense feature families to certify/test. Do not propose threshold tuning, temperature fitting, market features, 2025–26 inspection, or architecture bakeoff yet unless you believe feature-family discovery is sufficiently mature.
4. Challenge whether Stage016 should be combined with Stage018C later or treated as overlapping weight information and therefore not combined wholesale.
5. Assess whether the remaining gap to D99 is now small enough that we should prioritize missing information families over more transformations of existing fields.


# V2 UPDATE — STAGES 015A–019 (2026-10-08)

## Governance unchanged
- 2025–2026 remain SEALED.
- No market/SP features in the fundamental model.
- Fixed HGB architecture during family discovery: max_iter=200, learning_rate=.05, max_leaf_nodes=5, l2=1, random_state=42.
- No threshold mining or post-hoc temperature fitting.
- D99 remains old V1 benchmark, not inherited V2 architecture.

## EPI provenance gate
Stage015A/A2 could not recover the original LAB026 construction formula sufficiently to prove EPI was market-free and PIT-safe. EPI and EPI-derived features remain QUARANTINED. No Stage015 EPI model was fitted.

## Stage016 — exact dense current context
LAB031 exact authority coverage: 90,235 / 91,434 = 98.69%.
Family: current weight, weight change, distance change/absolute change, prior same-class starts, prior exact-distance starts, missingness.
Result vs Stage011:
- 2022 LL 2.118552868, Top1 22.06%
- 2023 LL 2.130118818, Top1 21.62%
- 2024 LL 2.097479623, Top1 22.61%
LL improved all 3 years, but Top1 worsened 2022/24. Retained as real signal, not initially promoted.

## Stage017 — LAB089 prep/spell sparse-family design
LAB089 exact horse identity proven but only 30,253 / 91,434 runners = 33.09%; only 34/84/122 fully covered races in 2022/23/24.
Covered-race Stage011 vs prep/spell challenger:
- 2022 LL 2.400789 -> 2.408174 worse
- 2023 LL 2.217834 -> 2.182592 better
- 2024 LL 2.071391 -> 2.106192 worse
Decision: PARK. No slicing.

## Stage018B — LAB037 connection authority
Exact coverage 98.69%, but richer jockey/trainer mean/residual fields are EPI-derived and therefore quarantined. Intended clean prior win/rate fields are entirely blank. Existing Stage008 already contains clean connection rates. No model fitted.

## Stage018D/E — dense relative/recent weight family
LAB045A exact coverage 98.69%; recent weight history 88.0%. Ranges/semantics certified.
Stage018E family: race-relative weight deltas/rank/percentile/full-field count, previous-start weight, change from previous, recent average, change from recent average, missingness.
Result:
- 2022 LL 2.119590978, Top1 22.06%
- 2023 LL 2.125841527, Top1 21.70%
- 2024 LL 2.095562644, Top1 23.15%
Improved Stage011 LL all 3 years. Strong challenger.

## Stage019 — successful dense union
Predeclared non-duplicative union: Stage018E weight-history family + Stage016 NON-WEIGHT distance/class-experience fields only.
Result:
- 2022 LL **2.117554816**, Top1 **23.04%**, Top2 41.50%, Top3 54.58%
- 2023 LL **2.122345191**, Top1 **21.66%**, Top2 38.27%, Top3 52.50%
- 2024 LL **2.094465945**, Top1 **23.15%**, Top2 41.30%, Top3 55.16%
Decision: **PROMOTE — current V2 champion.**

## Comparison to V1 D99
D99 LL:
- 2022 2.099976855
- 2023 2.129454621
- 2024 2.084420614

Stage019:
- 2022 behind D99 by ~0.01758
- 2023 beats D99 by ~0.00711
- 2024 behind D99 by ~0.01005

V2 has now surpassed D99 in 2023 while remaining behind in 2022/2024.

## Requested Grok review
Please review as an independent scientific/governance critic only. Do not write code or alter data.

Questions:
1. Is Stage019 promotion scientifically justified?
2. Should we continue clean feature-family discovery, or is the core mature enough for a predeclared architecture bakeoff?
3. Which remaining certified/non-market information family has the strongest scientific case, given EPI quarantine and sparse timing/form-line/LAB089 coverage?
4. Any leakage/provenance concern in Stage018E/019 weight-history and race-relative fields?
5. How should we treat the 2022 sample (612 races) when deciding architecture/family stability without changing governance post hoc?
6. What exact next experiment would you predeclare?
