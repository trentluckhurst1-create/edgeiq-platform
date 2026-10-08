# EDGEiQ Model V2 — Independent AI Review Handoff

## Review role
You are the independent second researcher. Challenge the proposed direction. Look for leakage, overfitting, weak design, missing feature families, invalid conclusions, or governance violations. Do not change code/data/governance. 2025–2026 are SEALED. No market/SP features in the fundamental model. No retroactive thresholds or endless micro-tuning.

## Goal
Build a genuinely new, reproducible, profitable horse-racing fundamental probability model from the certified data estate. V1 models D99/D112 are benchmarks only, not V2 architecture.

## Certified V2 universe
Stage004: 91,434 runners / 7,185 single-winner races after excluding 14 dead-heats and one zero-winner race.
2021: 1,775 races
2022: 612
2023: 2,396
2024: 2,402
2025–2026 untouched/sealed.

## Data-estate findings
Performance bridge exact coverage: 100%.
Timing exact usable coverage: 33.09%, present all 2021–24.
Dynamic form-line exact coverage: same 33.09% footprint as timing.
Pace: 0% 2021–22; 16.2% 2023; 26.0% 2024.
First-starter authority: zero exact date+horse match under tested identity key; quarantined pending identity proof.

## V2 experiments
### Stage007 — performance-only baseline
23 clean performance-history fields; HGB fixed architecture; chronological train < test year; within-race softmax.
2022 LL 2.3926035 Top1 15.85%
2023 LL 2.4287955 Top1 13.86%
2024 LL 2.4352504 Top1 15.86%

### Stage008 — add 7 universal connection/context fields
Added barrier_position_pct; jockey prior starts/win/top3; trainer prior starts/win/top3.
2022 LL 2.1362636 Top1 23.20%
2023 LL 2.1584698 Top1 18.95%
2024 LL 2.1317114 Top1 22.27%
Decision: PROMOTED. Large consistent information gain.

### Stage009 — isolated sparse timing on Stage008
2022 LL 2.1304893 Top1 24.18%
2023 LL 2.1561811 Top1 19.66%
2024 LL 2.1341780 Top1 22.11%
Decision: PARKED. Improves 2022/23 but worsens 2024 LL.

### Stage010 — isolated dynamic form-line on Stage008
2022 LL 2.1315145 Top1 22.71%
2023 LL 2.1612744 Top1 18.45%
2024 LL 2.1338887 Top1 21.69%
Decision: KILLED as core family; 2023/24 LL worse and Top1 lower all years.

### Stage011 — clean strict-prior placing rebuilt directly from PERF026
Invalid finish/status codes excluded. Same-date ambiguous histories excluded. Five clean features: mean last5 finish, last finish, last won, last top3, valid history count. Coverage 79,166/91,434 = 86.6%.
2022 LL 2.1250604 Top1 22.55% Top2 41.83% Top3 53.27%
2023 LL 2.1314274 Top1 20.66% Top2 37.02% Top3 50.42%
2024 LL 2.1022229 Top1 22.98% Top2 40.55% Top3 53.79%
Decision: PROMOTED. Current V2 champion.

### Stage012 — seven race-relative transforms on Stage011
Trainer/jockey quality, barrier, clean placing relative to field median.
2022 LL 2.1074981
2023 LL 2.1336640
2024 LL 2.0796487
Decision: NOT promoted as bundle; 2023 LL worsened.

### Stage013 — connection-quality relative subset only
2022 LL 2.1129487 Top1 24.02%
2023 LL 2.1330208 Top1 21.79%
2024 LL 2.0902414 Top1 22.65%
Decision: NOT promoted; 2023 LL still worse. Stopped micro-slicing.

### Stage014 — clean EPI lineage forensic
PERF026 rows 863,755.
Valid finish rows: 700,655.
Invalid/non-finish placing rows: 163,100.
EPI non-null on valid rows: 510,849.
EPI non-null on invalid rows: 120,253.
Recent invalid rates: 2020 25.40%, 2021 23.35%, 2022 23.59%, 2023 23.10%, 2024 24.10%.
A clean 700,655-row valid-finish EPI history authority has been created.

## V1 benchmark context
D99 clean-place benchmark:
2022 LL 2.0999769 Top1 24.03%
2023 LL 2.1294546 Top1 20.24%
2024 LL 2.0844206 Top1 22.92%
D112 final passing V1 challenger:
2022 LL 2.0967366 Top1 25.00%
2023 LL 2.1282046 Top1 21.57%
2024 LL 2.0853921 Top1 22.46%
D112 was not adopted because 2024 deteriorated vs D99 and V1 was closed.

V2 Stage011 is already close to V1 while independently rebuilt and without several inherited/contaminated fields.

## Proposed next direction
Stage015 would construct strict-prior clean EPI history features from Stage014's valid-finish authority and test that family ONCE on top of Stage011. Candidate summaries should be predeclared (e.g. last1, mean3, mean5, peak/worst, history count), using only history race_date < target race_date. No market. No parameter search. No 2025–26.

After clean EPI, the program should continue to genuinely independent data families rather than repeatedly slice relative transforms. Sparse timing may later be revisited only in a principled missingness/subpopulation design.

## Questions for independent review
1. Is Stage015 clean EPI the best next experiment? If not, what should precede it and why?
2. Does the proposed strict-prior EPI construction have any leakage or selection-bias risk not addressed here?
3. Are Stage009 timing and Stage010 form-line conclusions scientifically fair given sparse identical coverage?
4. Should V2 retain the fixed HGB learner during feature-family discovery, or is architecture now confounding feature conclusions enough to require a predeclared architecture comparison?
5. What major owned data family appears missing from the current sequence?
6. Identify any conclusion above you would overturn.

Return a concise research review with: VERDICT, RISKS, NEXT EXPERIMENT, and any DISAGREEMENT WITH CHATGPT.
