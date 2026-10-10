# EDGEiQ — Prospective validation protocol amendment (DESIGN ONLY)

Date: 2026-10-11
Status: DRAFT — NOT ACTIVATABLE. No fit, scoring, unsealing, publication, or evaluation is authorised.
Research decision: Stage011 champion retained; Candidate B unpromoted; A–G closed. 2025–2026 sealed. All 2022–2024 comparisons are reused development evidence.

## Scientific questions
1. **Primary, predeclared:** On genuinely future races, what are the separately measured race-level log losses for Stage011 and Candidate B?
2. **Secondary, winner identification:** On that same paired population, what proportion of races is won by each model's highest-probability runner? Report only after primary log loss is computed and published. Resolve exact-probability ties by a fixed, predeclared canonical runner-ID order. Report the number of ties.
3. **Secondary, calibration:** Evaluate only after the primary result, under a separately specified fixed binning/reporting plan.
4. **Not in scope:** betting returns, market comparison, profitability, or promotion by a secondary metric.

Winner strike rate and log loss measure different things. A higher strike rate is not automatically better calibrated probability, and neither establishes profitability.

## Prospective population and stopping
- Start date/time: **UNSET**, must be later than signed freeze and every race used for model selection.
- Stop: the **earlier** of an approved fixed end date or the first 1,000 eligible races; exact end date **UNSET**. Never choose an end based on model performance.
- Evaluation uses future races only; no retrospective year is relabelled a holdout.
- Publish the candidate race universe and deterministic inclusion/exclusion policy before the first evaluation outcome read.
- Exactly one certified winner, >=2 scored starters, and each model's race probabilities summing to 1 within absolute 1e-12. All failures must be logged with timestamp and reason. No result-driven deletion, backfill, or substitution.
- For primary head-to-head comparison, use the **same races scored by both models**. Publish Stage011-only, B-only, neither-scored, and paired counts. Any one-sided missing score is an audit failure, never silently omitted. Coverage below 100% of the eligible window blocks promotion regardless of paired LL.
- Race failures that become known only after result ingestion are reported in the full audit and handled solely by predeclared mechanical eligibility rules, not discretionary removal.

## Models, training and freeze
- Stage011 ordered 35-feature historical manifest hash: f35dd342d570b35831043c75cf756f7cac4e28ebdd564988393db3383c82454f.
- Candidate B ordered 44-feature historical manifest hash: 0c8becc834d09b619832c46d748f705c183ab4a391e319ae9f6971ee05e9321e.
- Both fixed HGB parameters: max_iter=200; learning_rate=0.05; max_leaf_nodes=5; l2_regularization=1; random_state=42.
- Historical feature hashes are not signed prospective freeze evidence.
- Before any authorised fit, record training cutoff strictly earlier than start, source manifests, and proof of >=1,000 certified earlier races without reading sealed outcomes.
- Only a separate explicit authorisation can permit **one fit per model**. No refits.
- Freeze serialized fitted model bytes and SHA256 for each, ordered feature manifest and SHA256, source lineage, training cutoff, approved code version, and signed independent no-evaluation-outcome/no-metric-read attestation.
- Existing retrospective reproduction scripts and commit hashes are not frozen fitted model objects.

## Identity, pre-off publication and outcome append
- Canonical identity: race key `_race`; runner key `_horse`; require unique (`_race`,`_horse`) per model; no fuzzy matching or post-result remapping.
- Specify and approve the authoritative source of scheduled off times and timestamped scratchings **before activation**.
- For every scored race, write separate Stage011 and B artifacts with model-object hash, ordered feature hash, source hashes, training cutoff, race/runner keys, scheduled off time, scratch-as-of source/timestamp, scoring timestamp, raw score, normalized probability, and protocol version.
- Only scratchings recorded before scoring timestamp can remove runners. Renormalise race probabilities before publication. A late scratching never rewrites a published score.
- Write, timestamp, SHA256-hash and publish the immutable score file **before scheduled off time**. Record independent, auditable publication timestamp, path and artifact hash. Publication failure/missing timestamp/duplicate identity/mass failure: fail closed before off and record reason.
- Never overwrite published scores. Append outcomes later in a separate file referencing the exact published artifact hash.
- Define postponed/abandoned race handling and publication failure paths before activation. No race may be dropped after its result is seen.

## Metrics and decision discipline
- Primary metric: for each eligible paired race, `-ln(clip(p_w, 1e-15, 1-1e-15))`; unweighted arithmetic mean across races, Stage011 and B reported separately. Publish primary result first.
- Secondary top-1 strike rate: on the identical paired race set, count winner = argmax pre-off probability per model; divide by paired eligible race count. Publish only **after** primary LL. Include counts, denominator and tied-selection count; do not use for mid-window tuning.
- A lower B LL or higher B top-1 strike rate is evidence, not automatic promotion. Any promotion requires independent review and separate authorisation.
- No price/SP/BSP, betting, profitability, or market calculations.

## Readiness and decision register
| Item | Status |
| --- | --- |
| Stage011 and B historical feature definitions | IDENTIFIED, not signed freeze |
| HGB parameters/seed | IDENTIFIED |
| Future start date/time | UNSET |
| Fixed end date | UNSET |
| Training cutoff | UNSET |
| >=1,000 certified earlier races | UNVERIFIED |
| Fitted model objects + SHA256 | MISSING |
| One-fit authorisation | NOT GRANTED |
| Signed no-outcome/no-metric attestation | MISSING |
| Scheduled off-time authority | UNAPPROVED |
| Scratchings timestamp authority | UNAPPROVED |
| Immutable pre-off publisher and independent timestamp evidence | NOT IMPLEMENTED |
| Outcome append-only audit trail | NOT IMPLEMENTED |
| Race/runner identity and failure handling | DESIGN ONLY |
| Prospective activation | NOT AUTHORISED |

This amendment defines evaluation questions and failure controls only. It does not authorise fitting, scoring, unsealing, activation, or metric computation.
