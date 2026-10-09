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


## Stage 016 / Stage 017 independent review

VERDICT: Keep Stage011 as conservative champion; Stage016 retained challenger. Park Stage017 at family level; do not kill or slice it.

Key controls adopted:
- Stage016 LL gains are consistent but small and not established confirmation.
- 2022-2024 remain development evidence, not fresh OOS confirmation.
- Stage017C is conditional covered-subpopulation evidence only; 34/84/122 races are too small for promotion or rejection.
- Do not test LAB089 going/gear next.
- Before further Stage016 use, certify LAB031 change/count features exclude target-race and same-date information.
- Highest-value next step is a written dense-feature gap inventory against D99/non-market PIT inputs, followed by one predeclared dense-family test on Stage011.
- 2025-2026 remain sealed.


# Grok Independent Review — Stages 023–036 gate (2026-10-09)

VERDICT: Stage011 conservative champion; Stage016 retained historical challenger, Stage035 not promoted. Stage018C/019 not reinstated. Stage023 LOGIT/RF fail. No predictive fit until identity authority is certified.

CRITICAL CORRECTION: Stage034 zero-match is a guard short-circuit, not an identity result. The script filters the prototype bridge to automatic_merge_allowed TRUE with canonical_horse_id, but all 473 flags are false. The reported 457 single-code and 16 ambiguous counts are classifications on the prototype, not actual matches to the 63,236 performance-rating rows. Do not treat zero as an identity failure.

Stage036 only searches keywords in EPI builders; does not establish formula, as-of training, market independence, earlier-date exclusion or canonical identity. EPI remains quarantined.

NEXT STEP (Stage037, no model): exact normalized-name and (name,race_date) join of public/data/edgeiq_historical_performance_rating_v1.csv against public/data/edgeiq_official_runs_master_v1.csv; prototype bridge is negative control, LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv existence check. Restrict reported rates to rating rows year <=2024. Count excluded sealed rows only. Report row counts, exact name hit, exact name/date hit, matched-name canonical-ID collision fraction. Normalizer uppercase, strip non-alphanumerics, exact equality only. PASS >=90% exact name/date and zero collisions; STOP <50% or any collisions; otherwise INDETERMINATE. No fuzzy match, no forced merge, no feature fit. If STOP, read Stage036 original builder formulas at source level, not another grep.

Additional risk: Stage031 first_starter_flag is derived from trainer_prior_first_starters.notna(), hence is a coverage indicator rather than genuine debutant status; Stage031/035 cannot be interpreted as tests of first-starter skill. Repeated reuse of 2022–24 creates multiplicity; 2025–26 remain sealed. No market/SP, no threshold mining, no learner search.

Independent review was provided by user as Grok's response. Grok could not access Actions logs directly; numeric run results were taken from CURRENT_STATE. ChatGPT independently fetched and verified Stage023, 031, 034, 035, 036 logs. Full Grok text is in the user's pasted review, dated 2026-10-09.


# Grok Independent Review — Stages 037–042 gate (2026-10-09)

Independent review provided by user. Grok read scripts Stage037–042 but could not read Actions log bodies or push to branch. Its conclusions are independent recommendations, not independently verified run logs.

## VERDICT
Park historical performance rating as V2 feature family; do not fit. Stage037B/038 certify rating-to-official-master name/date joins only, not V2 warehouse identities. Stage039 formula replay uses rating-file finish_position and margin_x, not official master finish/margin, so does not independently verify official outcome inputs. Stage040 only proves strict-prior shift within rating population. Stage041 shows V2 warehouse has _horse hash but no horse name; Stage042 finds no certified mapping and canonical master/alias absent.

## NEXT EXPERIMENT: Stage043 source-level horse mint audit (no model)
Locate the first script/artifact assigning EIQ_HORSE_ identifiers and print exact mint expression. Recompute only if it is a pure function of an on-runner field of edgeiq_official_runs_master_v1.csv. Exact string join only, pre-2025 only. Report warehouse runner exact-match rate, horse-key collisions, strict-prior rating coverage. PASS if >=80% exact match, zero collisions, >=50% prior rating coverage. STOP if mint absent/impure, match <50%, any collision, prior coverage <20%. Otherwise INDETERMINATE, park. No fuzzy join, name inference, bridge repair, model fit, SP/market, 2025–26 outcomes, or EPI activation.

## STRATEGIC JUDGMENT
Historical rating is a redundant nonlinear encoding of finish position, beaten margin and field size; Stage011 already has prior finish and margin. Even if identity passes, do not fit without a separate predeclared ablation and coverage rationale. One bounded mint audit is justified because it may unblock other official-master families, not because this rating is promising. Stage011 champion unchanged.

## REVIEW HANDOFF NOTE
Full Grok review text was pasted by user in conversation on 2026-10-09; this repository section preserves its decision, objections, quantitative gates and experiment contract. Grok could not push directly.
