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


# Grok Independent Review — post-Stage043 direction (2026-10-09)

## VERDICT
Do not fit another feature to close D99. Stage011 champion, Stage016 unpromoted, rating parked, EPI quarantined, official-master line blocked. Stage043's 1,399 broad hits did not certify EIQ_HORSE_ mint; this does not prove mapping impossible. The single next experiment is row-aligned score parity, no model.

## CHALLENGE
D99 is a benchmark, not a V2 feature specification. Published Stage011 minus D99 LL gaps are approximately 0.0251 (2022), 0.0020 (2023), 0.0178 (2024). Stage016 narrows them but remains unpromoted. Stage020a compared column names on 5,000 D45 rows, not race-aligned scores. Differences may reflect race universe, winner definition, normalisation, market/SP, EPI, or leakage. Residual decomposition before row alignment is invalid; Stage023 learner search closed.

## NEXT EXPERIMENT
Script: scripts/research/run_v2_stage044_d99_score_parity_audit.py. Frozen inputs: original Stage011 scored output, original D99 scored output, certified V2 single-winner universe (2022/2023/2024: 612/2396/2402 races), D45_FROZEN_PIT_FEATURE_MATRIX.csv for feature names only. Exact race key, years <=2024, sealed rows excluded count only. Do not read SP/market/odds/EPI values. No fuzzy joins, fit, or threshold mining.

Report yearly exact race intersections; Stage011 and D99 log losses recomputed on identical races; differences from published figures; classify D99-only columns as MARKET_OR_SP, EPI_OR_DERIVED, ALREADY_IN_STAGE011, LEGAL_DENSE_ABSENT, and report legal dense nonnull coverage on intersection.

STOP feature work if either scored artifact absent, any year's intersection <95% of certified V2 races, or recomputed D99 LL differs from published by >0.005. PARITY PASS if intersection >=95% in every year and both scores reproduce published within 0.001. Even after pass, no fit. Later challenger only if LEGAL_DENSE_ABSENT feature coverage >=90%; if none, STOP. One audit, no exploratory fallback.

## PROVENANCE
Full independent Grok review supplied by user in conversation on 2026-10-09. Grok could not push; Stage043 log body was not independently reread by Grok.


# Grok Independent Review — Stage044 STOP and scoring protocol (2026-10-09)

## VERDICT
Stage044's stop is correct. Run 37879258536 was execution success only. Thirteen research and 98 production name-matched score files are other experiments' artifacts. run_v2_stage011_clean_placing.py and run_d99_full_clean_placing_features.py print annual log loss and do not persist runner-level probabilities, so published figures cannot be joined or reproduced. Not a parity pass, not a refutation of D99, not evidence of a missing feature. Do not re-fit to manufacture missing files; that is a new look at 2022–2024. Next step: one prospective scoring protocol, not a model or open-ended infrastructure program.

## PROTOCOL CONTRACT
Name ai_review/SCORING_ARTIFACT_PROTOCOL.md. No code in this step, no production write, no market/SP, no 2025–2026 outcomes, no EPI.

Future comparable scored artifact: exactly one row per runner; required fields _race, _horse, race_date, year, y (single winner), p (within-race softmax probability), model_id, git_sha, random_state, train_year_lt, feature_names_sha256, input_file_sha256, n_train_rows, n_test_rows. Forbidden: SP, odds, market rank, EPI, sealed-year outcomes. Sealed rows may be counted as excluded in log only.

Two artifacts comparable only if both exist, race-key intersection >=95% of each test year, and both input hashes recorded; otherwise NOT_COMPARABLE. No substitution of neighboring experiment scores.

First implementation test, only when separately authorised: synthetic three-runner writer dry-run, no model fit; fail if within-race sum(p) differs from 1 by more than 1e-12, any forbidden column appears, or hash fields blank.

## STOP
Do not implement writer in this step. Do not reopen Stage011, Stage016, rating family, identity mint, or EPI. Stage011 remains champion only as last predeclared model, not reproducible runner-level score. D99 gap uninterpreted.

## PROVENANCE
User-supplied Grok independent review dated 2026-10-09, referring to commit a92c4a1c. Grok could not push.


# Grok Independent Review — Stage045 synthetic writer gate (2026-10-09)

Reviewed ai_review/CURRENT_STATE.md at cfdcc627 against frozen ai_review/SCORING_ARTIFACT_PROTOCOL.md (basis commit 305bbf47). No implementation authorised by review.

## VERDICT: AMEND
One dry-run only after corrections. No real racing data, model fit, market/SP/EPI values, 2025–2026 outcomes, or production write. A pass does not make Stage011/D99 comparable or authorise a scoring run. Original negative cases insufficient: finite p in [0,1], year <=2024, nonblank SHA-256 digests, populated required fields, full forbidden-column set. n_train_rows must not be invented for no-model fixture.

## BOUNDED CONTRACT
Future script scripts/research/run_v2_stage045_synthetic_score_writer.py. Compliant fixture: one race, three synthetic runners, race_date 2020-01-01, year 2020, y=[1,0,0], p=[0.5,0.3,0.2]. Sentinels model_id=NO_MODEL_SYNTHETIC, git_sha=SYNTHETIC, random_state=NA, train_year_lt=2020, n_train_rows=0, n_test_rows=3; two distinct 64-character hex digests. Write only under temporary directory; assert three rows and one _race.

Each negative must fail closed with independent reason: (1) sum(p) >1e-12 deviation, use 1+2e-12; (2) forbidden set sp, odds, market_rank, epi; test sp and epi separately; (3) either hash blank OR not 64 hex; (4) duplicate (_race,_horse); (5) zero winners AND two winners separately; (6) p outside [0,1] AND nonfinite p separately; (7) year>=2025; (8) required field missing OR null.

Stop after machine-readable report. Do not retain artifact, refit Stage011/D99, or reopen Stage016, rating, identity mint, EPI.

## PROVENANCE
Full user-supplied Grok independent review on 2026-10-09; Grok could not push.


# Grok Independent Review — post-Stage045 research stop (2026-10-09)

Reviewed ai_review/CURRENT_STATE.md at ddb41e05. Stage045 run 37880357264 passed 18/18 synthetic writer tests, with model_fit=false and no real data. Stage044 remains STOP_PENDING_ORIGINAL_SCORED_ARTIFACTS_NO_REFIT. No implementation is authorised.

## VERDICT: A

Stop probability-model research until there is evaluation evidence that has not already been used to choose features, plus a prospective design frozen before any fit. Do not run another audit to keep the programme moving. Do not fit.

Stage011 remains the last predeclared champion, not a reproducible runner-level score. Stage016 stays unpromoted. The rating family, EPI, and the official-master identity line stay closed. The published D99 gap is not evidence of a missing feature.

## Evidence

The certified non-market path inside the V2 warehouse has already been used. Stage007 to Stage011 established the champion. Stage016's log-loss gains were small and its Top1 results mixed, so it was not promoted. Stage023 rejected logit and random forest. Sparse timing, form-line, and LAB089 were parked. The historical rating is a post-race function of finish, margin, and field size on 1,168 horses, and it does not join _horse. Stage043 did not certify a pure mint. EPI remains unproven. Stage044 found that neither Stage011 nor D99 persisted runner-level probabilities, so the annual figures cannot be joined.

Those same 612 / 2,396 / 2,402 races have been reused for every promotion and rejection. A further 2024 log-loss difference of 0.001 would not be interpretable. Stage045 only proves that a synthetic validator can fail closed. It does not make the historical scores comparable, and it does not show betting profitability. Lower log loss is not a demonstrated edge against a price.

## Falsification

Reopen only if all three exist before any metric is computed: a predeclared hypothesis and feature list, an evaluation window not used for this family selection, and scored artifacts under the frozen protocol. A certified exact _horse mint can reopen the identity line, not a model fit by itself. The D99 gap, a Stage045 pass, or a new transform of Stage011 fields does not falsify this stop.

## NEXT ACTION

Record the stop. Do not dispatch a run, write a scoring script, refit Stage011 or D99, or unseal 2025–2026.


# Grok Independent Review — development reopen `1d7dfbcf` (2026-10-09)

Reviewed `ai_review/HISTORICAL_DEVELOPMENT_REOPEN_REQUEST.md` and `ai_review/HISTORICAL_HOLDOUT_NO_OUTCOME_INVENTORY.md` at `1d7dfbcf`. Verdict A remains in force.

## VERDICT: AMEND

No training is authorised. The no-outcome inventory is a fail: 2021 has no earlier certified races, 2022–2024 were used for selection, and 2025–2026 stay sealed. Calling those years “development diagnostics” is an accurate label. It does not create an evaluation window or justify another fit.

A Stage011 refit would be a new look at the same races, not recovery of the missing Stage044 scores and not evidence of a better betting model. No hypothesis beyond “freeze Stage011” is named, so the proposed run is not yet a single experiment. A price audit is also premature: no timestamped pre-off source has been named, and SP or BSP still cannot prove a bet could have been struck.

## Protocol amendment, before any development file exists

Add `evidence_class`. Any 2022–2024 output must be `REUSED_DEVELOPMENT`. The confirmation rule returns `NOT_COMPARABLE` if either artifact has that class. Do not change the frozen confirmation thresholds to make a development file look eligible.

## First permitted run

None. Do not dispatch a fit, a refit, or a price join.

Training can start only under the conditions already stated: one window with no prior metric exposure, at least 1,000 strictly earlier certified races, the Stage011 manifest and fixed HGB seed frozen first, protocol-compliant runner-level scores, and one predeclared log-loss gate. A miss ends the fit. Profitability stays blocked until an exact, collision-free join to timestamped pre-off prices is established.

## Provenance

User-provided Grok review, 2026-10-09. The supplied text ended mid-sentence after “exact, collisi”; the final sentence above summarises previously stated price-provenance requirements rather than purporting to reproduce missing text verbatim.
