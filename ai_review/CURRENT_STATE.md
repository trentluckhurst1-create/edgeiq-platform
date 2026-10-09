# EDGEiQ V2 — Independent Grok Review Gate (2026-10-09)

## Request to Grok
Review independently. Challenge ChatGPT's conclusions and choose exactly one next non-model experiment or a justified STOP. Do not merely agree. Provide verdict, risks, required test, pass/stop criteria, and whether historical performance rating should be parked. Please write your review to `ai_review/GROK_REVIEW.md` on branch `research/profitability-program-20261004` if you have GitHub write access; otherwise provide the full review for the user to paste back to ChatGPT.

## Governance
2025–2026 sealed; no reading outcomes from those years. No market/SP features or SP-based selection. No fuzzy horse joins. No production writes. Stage011 remains champion. Stage016 unpromoted. No model training until identity and point-in-time integrity established. Note the official runs master contains an `sp` column, but audit scripts do not consume it.

## Completed GitHub runs
- Stage037B: https://github.com/trentluckhurst1-create/edgeiq-platform/actions/runs/37876595085 — 14,640 pre-2025 rating rows, 100% exact normalized name+race_date hit in official runs master; zero name-to-horse_key collisions among 1,168 names. `horse_key` is NOT `canonical_horse_id`.
- Stage038: https://github.com/trentluckhurst1-create/edgeiq-platform/actions/runs/37876742222 — all 14,640 rating rows match exactly one master row; zero duplicate keys or ambiguous join rows.
- Stage039: https://github.com/trentluckhurst1-create/edgeiq-platform/actions/runs/37877288467 — zero formula replay mismatches, 14,640 official runs, zero trials/jumpouts. Builder `scripts/build_edgeiq_historical_performance_rating_v1.py` calculates a class-independent rating from finish position, beaten margin, and field size. This is a POST-RACE observation; must only be used strictly earlier than prediction date.
- Stage040: https://github.com/trentluckhurst1-create/edgeiq-platform/actions/runs/37877361727 — strictly earlier-date rating features construct correctly within rating population: 14,640 rows, 1,168 horses, 13,472 with prior history, no same-day duplicates, zero detected first-observation leak. NOT YET validated against model runners.
- Stage041: https://github.com/trentluckhurst1-create/edgeiq-platform/actions/runs/37877494081 — V2 Stage006 warehouse has 91,434 pre-2025 rows and fields `_race`, `_horse`, `race_date` but NO horse name; no exact join to rating source.
- Stage042: https://github.com/trentluckhurst1-create/edgeiq-platform/actions/runs/37877640708 — V2 warehouse `_horse` sample `EIQ_HORSE_000D1DE904D9A5DB`, official master `horse_key` sample `ABATEDBREATH`; cannot assume equivalent. Canonical master and alias files absent on runner. Historical bridge 204 rows (current/historical canonical names/IDs); current crosswalk 114; RA↔RCom bridge 114. NO certified mapping from `_horse` to official `horse_key` established.

## Core question
Is there an authoritative, exact, collision-free mapping from Stage006 warehouse `_horse` (EIQ_HORSE hash IDs) to official master `horse_key` / historical rating horse names? If not, park this rating family rather than introduce name-only inference or hand-built identity assumptions.

## Potential methodological risk
The recovered historical rating is a deterministic nonlinear summary of finish position, beaten margin and field size, while Stage011 already has margin and clean placing features. Even a perfect bridge might offer little new signal. Stage040 proves a local date-shift construction, not a full end-to-end PIT join. Coverage may be sparse and selected (1,168 horses in ratings versus broad V2 universe).

## Ask for your judgement
1. Should we stop this rating family now because the V2 warehouse has no name and canonical master/alias are absent, or run ONE bounded source-level `_horse` derivation and exact crosswalk audit?
2. What are quantitative PASS/STOP criteria, including coverage and collision threshold, for that audit?
3. Is the performance rating worth a predeclared challenger once identity is certified, given feature redundancy?
4. Is there a more promising scientific next step than spending time on this sparse family? Provide one concrete experiment, not a search.


## Next research decision gate — post Stage043 (2026-10-09)

Stage043 GitHub Actions run 37878382128 completed successfully as a broad source search but did NOT certify an EIQ_HORSE_ mint. The search returned 1,399 broad hits, without identifying a reproducible, pure hash from official-master on-runner fields. Further source tracing confirms Stage006 inherits _horse from Stage004 / D45 / LAB245B; LAB245B_COMPACT_PERFORMANCE_BRIDGE copies canonical_horse_id from LAB245B_WAREHOUSE_RUNNER_LVS, which inherits it from the performance fact warehouse. An earlier phase1_6 builder computes a performance-record ID from race_id|runner_id, not the EIQ_HORSE_ canonical horse identifier. No match-rate, collision, or strict-prior coverage test was performed. Thus the source mint remains UNPROVEN; do not misrepresent this as a proven impossible mapping.

DECISION: Historical rating family parked for redundancy and sparse coverage. Official-master identity line blocked without certified pure mint. EPI quarantined. Stage011 champion unchanged; Stage016 unpromoted. No production changes, no market/SP, no 2025–26 outcomes, no fuzzy identity, no learner/threshold search.

## Question for Grok — independent next-stage experiment selection
We propose returning to the D99 benchmark performance gap using existing certified dense point-in-time non-market V2 features. Stage011 log losses (2022/2023/2024) = 2.1250604024 / 2.1314274279 / 2.1022229250. D99 benchmark = 2.099976855 / 2.129454621 / 2.084420614. Stage016 unpromoted challenger = 2.118552868 / 2.130118818 / 2.097479623. Stage023 learner bake-off failed; previous feature-family searches and repeated 2022–24 reuse limit interpretation. No betting profitability demonstrated.

Grok: Challenge whether returning to the D99 gap is scientifically justified, or whether the best next step is a strict input/parity audit, residual decomposition, or STOP. Propose exactly ONE bounded experiment with named script, precise frozen inputs, hypothesis, expected outputs, quantitative pass/fail gates, and leakage/multiplicity controls. Do not propose an exploratory search, market/SP, 2025–26 unsealing, EPI, or another model fit without a clear rationale. Record review in ai_review/GROK_REVIEW.md or provide complete text to user.


## Stage044 score-parity gate — final STOP (2026-10-09)

GitHub Actions run 37879258536 completed successfully (execution only). The Stage044 original-scored-artifact inventory inspected research and production read-only outputs. Research contained 13 name-matched prediction/score candidates and production 98; these are historical artifacts from other experiments, NOT established as the original Stage011 or D99 runner-level predictions. Original Stage011 script run_v2_stage011_clean_placing.py and original D99 script run_d99_full_clean_placing_features.py print yearly log losses but do not persist runner-level probability outputs. Consequently, Stage044 could not join scores on exact races or reproduce the two published annual LL figures. This is NOT a parity pass, not a refutation of D99, and not evidence of missing features. Explicit decision: STOP_PENDING_ORIGINAL_SCORED_ARTIFACTS_NO_REFIT. Do not substitute other experiments' scores, re-fit models, inspect market/SP/EPI values, or unseal 2025–26 to force progress. Stage011 remains champion; Stage016 remains unpromoted; historical rating and EPI parked; identity mint unresolved. No feature search authorised. To reopen, require a documented prospective scoring-artifact protocol and independent review of comparability and reproducibility before any run.


## Proposed next gate for Grok — Stage045 synthetic writer contract review (2026-10-09)

User authorised PREPARATION FOR GROK APPROVAL only; NOT implementation or execution. The frozen scoring contract is ai_review/SCORING_ARTIFACT_PROTOCOL.md (commit 305bbf47). Proposed single bounded test: a writer/validator dry-run on a wholly synthetic three-runner race with synthetic IDs and synthetic outcome, no historical source read and no model fit. Produce one compliant scored artifact with required exact columns (_race,_horse,race_date,year,y,p,model_id,git_sha,random_state,train_year_lt,feature_names_sha256,input_file_sha256,n_train_rows,n_test_rows). For test-only synthetic probabilities use e.g. [0.2,0.3,0.5], sum exactly 1 to 1e-12, exactly one y=1. Test negative cases independently: (1) p sum deviates by >1e-12, (2) forbidden column e.g. sp is present, (3) either hash blank, (4) duplicate (_race,_horse), (5) zero or multiple winners. Each must fail closed with an explicit reason; compliant case passes. Output only temporary synthetic test artifacts and a brief machine-readable PASS/FAIL report. No production write, no real runner data, no SP/market/EPI values, no 2025–26 outcomes, no changes to Stage011/D99 or model research. Do not write code until Grok has independently approved or amended this bounded test and user explicitly authorises implementation.

Grok: review the proposal as an approval gate. Check whether any missing negative cases or metadata constraints materially affect its validity. Respond APPROVE / AMEND / REJECT with one bounded contract. Do not broaden into a new research-infrastructure programme.
