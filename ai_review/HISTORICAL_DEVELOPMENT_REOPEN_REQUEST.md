# EDGEiQ — Historical Betting Model Development Reopening Request

Date: 2026-10-09
Status: USER-AUTHORISED REQUEST TO REOPEN DEVELOPMENT; PENDING INDEPENDENT REVIEW. NO MODEL FIT AUTHORISED.

## User decision
User explicitly wishes to resume building a betting model from historical racing data. The objective is a probability model that may support positive-expectation wagers, not a commercial software product.

## Research distinction
- 2022–2024 were repeatedly used for model selection. They may serve as **development / exploratory diagnostics only**, never as untouched confirmation or a basis for a validated profitability claim.
- 2021 is the earliest established certified V2 year and does not provide >=1,000 earlier certified races for an untouched evaluation.
- 2025–2026 outcome data remain sealed. No market/SP/EPI as predictive features; no fuzzy identity joins.
- Stage011 remains the fixed reference model, Stage016 unpromoted. Stage044 original scored artifacts missing; Stage045 synthetic validator 18/18 does not establish model performance.
- The previous Grok verdict A and no-outcome inventory STOP are explicitly acknowledged; this request seeks **amended permission**, not an assertion they were overturned.

## Proposed controlled development lane
1. Freeze a named single development hypothesis, the Stage011 feature manifest and HGB configuration (max_iter=200, learning_rate=.05, max_leaf_nodes=5, l2_regularization=1, random_state=42), training eligibility, exact identity and PIT rules before any run.
2. Restrict development outcomes to 2024 and earlier, with strictly earlier-year training in any historical fold. Label all 2022–2024 performance **reused development evidence**.
3. Persist exact runner-level probability outputs and hashes per ai_review/SCORING_ARTIFACT_PROTOCOL.md. The existing protocol's comparator/eligibility gates may need a separately reviewed development-only amendment; do not silently reinterpret it.
4. One predeclared run only after Grok approves exact scope. No open-ended feature/threshold/learner search; no unapproved refit of Stage011/D99.
5. Separately certify timestamped, pre-off available betting prices and executable cost assumptions before any ROI test. SP/BSP are retrospective diagnostics, not evidence of achievable execution.
6. No model promotion, profitable-model claim, or unsealing on development metrics. Later independent evaluation must use a truly unexposed population under a fresh, separately authorised protocol.

## Questions to Grok
Return APPROVE, AMEND, or REJECT, independently:
- Can an explicitly exploratory, non-confirmatory historical development lane be authorised without misrepresenting 2022–2024?
- Specify exactly one first permitted run (or STOP), frozen inputs, expected artifacts, and hard leakage/multiplicity gates.
- Clarify any amendments needed to the frozen scored-artifact protocol for development-only outputs.
- Identify the evidence that would justify a separate historical-price feasibility audit, without computing ROI or opening sealed years.

## Hard boundary
This document is a decision request only. No code execution, model fitting, new metrics, 2025–2026 outcome access, production change or market-derived predictive feature is authorised. Require Grok review and explicit implementation approval before a run.
