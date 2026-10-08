# Grok Independent Review — Stage 014 Handoff

Independent review of `ai_review/CURRENT_STATE.md` at commit `723cde6` on `research/profitability-program-20261004`. Research review only. No code, data, or governance changes.

## VERDICT

Stage 015 is the right next model experiment only after a short provenance gate. Do not fit it until EPI is shown to be a non-market, point-in-time rating. If that gate fails, skip EPI and move to an untouched fundamental family.

Stage 011 as current champion is justified. Stopping the relative-transform micro-slices is also justified. “Killed” for form-line is too strong. “Already close to V1” is true and not a success: D99 still has better log loss in all three test years.

## RISKS

- EPI leakage is the main risk. Same-date exclusion and valid-finish filtering are necessary but not sufficient. EPI must not embed starting price, market rank, or any rating fit on future races. Join on the same identity key that already failed for first-starters. Missing EPI is not random: 510,849 of 700,655 valid-finish rows are non-null, and invalid rates sit around 23–25%. Include an explicit missingness flag. Do not impute from the target race or from later history.
- Peak/worst summaries reward horses with longer histories. History count must sit beside them, and the summary set must stay predeclared. One pass only.
- 2022 is 612 races. A one-year LL move can be noise. Requiring every year to improve will park real signal and promote noise. Keep the rule, but do not treat a 2023-only miss as proof the family is empty.
- Timing and form-line share a 33.09% footprint. A global add-on mixes “feature is useless” with “feature marks a different meeting population.” Stage 009 parking is fair. Stage 010 “killed as core family” overclaims.
- Fixed HGB is still the right control. An architecture bake-off now would confound family conclusions. Do it once, predeclared, after the feature set stabilizes.
- The stated goal is profitability, but every decision is LL and Top-k. That is correct for a fundamental model. Do not sneak market features in to close the gap. Profit stays a later sealed evaluation.

## NEXT EXPERIMENT

Gate, then one Stage 015 fit on top of Stage 011.

Gate, no model: document EPI’s formula and as-of timestamp; confirm no SP or market input; confirm history uses only `race_date < target race_date`; report coverage by year on the certified universe; confirm the identity key.

If the gate passes, one predeclared set only: last EPI, mean of last 3, mean of last 5, best, worst, valid EPI count, missingness flag. No search, no 2025–26, no market.

Promote only if LL improves in at least two of the three test years and does not worsen 2024. If it fails, park it. Do not slice it.

If the gate fails, next family should be spell and trip change if those are not already inside the Stage 007 23 fields: days since last run, distance change, class change, weight carried or weight change. Those are owned, dense, and not the same information as clean placing.

## DISAGREEMENT WITH CHATGPT

1. Stage 015 should not start until the provenance gate is written down. “Clean valid-finish authority” does not prove non-market.
2. Overturn “KILLED” on form-line to “PARKED, same as timing.” Identical sparse coverage means the global test was not a fair emptiness test. Revisit only in a predeclared covered-subpopulation design, not as another core add-on.
3. Do not run an architecture comparison now. HGB stays fixed through family discovery.
4. Do not read Stage 011 vs D99 as near-parity success. Gaps versus D99 are about 0.025 LL in 2022, 0.002 in 2023, and 0.018 in 2024. V2 has not matched the benchmark yet.
5. Agree with not promoting Stage 012 or 013, and with not reopening relative-transform slices. Stage 012’s 2024 LL of 2.0796 beats D99, but the 2023 regression is enough to reject the bundle under the current rule.
