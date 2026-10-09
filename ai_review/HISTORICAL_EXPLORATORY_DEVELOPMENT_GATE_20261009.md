# EDGEiQ — historical exploratory development authorisation request (2026-10-09)

STATUS: PROPOSAL ONLY. No dataset reads, joins, fitting, scoring, or sealed outcomes authorised by this document.

## Rationale
Single-file identity/date-only audit of edgeiq_historical_results_warehouse_v2_graphql.csv found 52,109 distinct pre-2021 year/race pairs, with populated race_id and runner_id. Missing calendar years 2011 and 2017. This is archive discovery, not race-level certification or a validated holdout. Existing V2 Stage011 is unvalidated champion, Stage016 unpromoted; D99/Stage007/Stage011 evaluate 2022–24, with strictly earlier-year training. Their input matrices' pre-2021 coverage is not established. Local V1 exposure unknown.

## Request: MODIFY governance to permit exploratory historical development, NOT confirmation
Gate 1 — read-only source certification, separately authorised: inspect only one named pre-2021 warehouse candidate and relevant point-in-time feature-builder source code; determine row/race key uniqueness, dates, jurisdiction/race-type scope, target validity, provenance, prior-only availability, and missing-year discontinuities. No 2025–26 outcomes, SP/odds/market predictors, or EPI/post-race features at prediction time. Predeclare exact files, columns, checks, and output before any read. Stop on duplicate race-runner identities, unresolvable dates, missing historical source lineage, or target leakage. This is not permission to read the warehouse now.

Gate 2 — separately approved exploratory modelling only after Gate 1 passes: predeclare frozen eligible race population and feature list, training windows, walk-forward chronological folds, model family/hyperparameters, primary race-normalised win-probability log loss and calibration diagnostics, and baseline Stage011 comparability conditions. Missing 2011 and 2017 are explicit gaps; no imputation of seasons. 2021–24 reused development evidence cannot be called independent; pre-2021 exposure remains UNPROVEN. No threshold mining, multiple learner search, or profitability claims. Record full prediction artifacts and hashes to prevent Stage044 recurrence. No sealed 2025–26 access.

Gate 3 — separate validation/profitability authorisation: no claim of independently validated performance without genuinely unexposed prospective or separately approved sealed data; no claim of executable betting profitability without collision-free timestamped executable pre-off prices. SP/BSP not substitutes.

## Requested Grok decision
APPROVE / AMEND / REJECT **Gate 1 only** as a bounded source-certification exercise. State precise approved source(s), allowed columns, checks, pass/fail thresholds, and stop conditions. Explicitly decide whether prior prohibition on reopening the historical warehouse is modified. Do not interpret this proposal as permission to fit, score, join, unseal, or run research.
