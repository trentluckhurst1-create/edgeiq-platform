# EDGEiQ — Historical Betting Model: Proposed Reopening Gate

Status: PROPOSAL FOR INDEPENDENT REVIEW ONLY. No model fitting, backtest, data unsealing, or research run authorised.

## Objective
Develop a historical-data-trained, point-in-time horse-racing win-probability model and determine whether its predictions identify a realistically executable positive expected-value betting strategy. A log-loss gain is not a profitability claim.

## Known evidence and constraints
- Stage011 is the last predeclared champion, not a preserved runner-level scored artifact. Stage016 is unpromoted.
- Stage044 could not establish Stage011/D99 runner-level parity because original scores were not persisted. Stage045 synthetic writer passed 18/18 contract tests; no real performance evidence.
- 2022–2024 have been repeatedly consulted in model selection, so their results are development evidence, not independent confirmation.
- 2025–2026 outcomes remain sealed. EPI and unverified identity bridges remain quarantined.
- Grok's final verdict A remains binding: no model research without a frozen hypothesis/features, a genuinely unused evaluation window, and compliant scored artifacts.

## Proposed historical-data design, conditional on independent approval
1. Inventory and identify a **genuinely untouched historical evaluation period** with documented prior exposure. Do not read outcomes or run a metric as part of the proposal. If no such period exists, STOP and propose a prospective holdout instead; do not re-label 2022–2024 as untouched.
2. Freeze a single primary hypothesis: the existing certified dense non-market Stage011 feature family can produce race-normalized probabilities with predictive value on an unused historical holdout. Freeze exact feature manifest, eligibility, label, identity authority, as-of cutoff, learner configuration, seed, and one training/evaluation split **before** reading holdout outcomes. Do not treat this as permission to refit Stage011.
3. Score once and persist exact runner-level records under ai_review/SCORING_ARTIFACT_PROTOCOL.md, including hashes and one winner per eligible race; prohibit target-race, future and same-day leakage.
4. Assess win log loss and calibration on the holdout with a predeclared comparator. Do not select features, hyperparameters, probability thresholds or bet filters using holdout outcomes.
5. Separately gate a betting profitability study on the provenance of **historically available, timestamped pre-off prices** and a predeclared execution/cost model. Final SP/BSP can be used only for appropriately labelled retrospective diagnostics, not as proof a price could have been taken before the jump. Price joins must be exact and collision-free.
6. If an eligible historical holdout or executable-price evidence cannot be certified, report NOT TESTABLE rather than invent ROI.

## Independent Grok review request
Independently challenge whether any historical period can still be certified untouched; whether the proposed frozen Stage011 hypothesis satisfies the prior stop; and whether the historical price sources support executable profitability testing. Choose APPROVE, AMEND or REJECT for a **single bounded pre-fit governance decision**, naming exact prerequisites and stop conditions. No scripts, model runs, metric computations or 2025–2026 outcome access authorised by this document.

## Decision required
Do not begin fitting until the independent review is returned, an unused holdout is documented, the protocol and hypothesis are frozen, and explicit approval is given.
