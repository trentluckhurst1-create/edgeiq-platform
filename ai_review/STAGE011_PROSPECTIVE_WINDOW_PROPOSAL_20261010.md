# EDGEiQ Stage011 — Prospective Window Proposal (PLANNING ONLY)
Prepared: 2026-10-10
Status: **PROPOSAL / NOT APPROVED / NOT ACTIVE**.
Governing design: ai_review/STAGE011_PROSPECTIVE_VALIDATION_PROTOCOL_V2_20261010.md

## Proposed dates (not activated)
- Candidate window start: **2026-11-01** (Australia/Melbourne).
- Candidate window end: **2026-12-31** (Australia/Melbourne); fixed calendar end, not an outcome-dependent stopping rule.
- Both dates are **proposed only**. The candidate window falls within **sealed 2026**. No access to any 2026 data, including outcomes, is authorised by this proposal. A separate explicit sealed-year access decision and activation approval would be needed; without both, STOP.

## Pre-activation work still unverified
1. Independently approved evaluation window and outcome-access rules; confirm no evaluation outcomes have been read or metrics computed and no race in the window entered training or selection.
2. Named, frozen Stage011 ordered feature manifest and SHA-256, certified point-in-time builders, runner/race keys and scratch status as-of scoring.
3. At least 1,000 certified races strictly before the start, with source lineage and training cutoff recorded. Do not assume the pre-2021 archive or closed LAB245B identity line qualifies.
4. Start date and manifest hash written **before the one authorised fit**; freeze exact HGB settings and seed 42. Compute SHA-256 of the fitted model object's bytes, not of a source commit.
5. Immutable pre-off outcome-blind runner scoring artifacts, unique race/runner keys, >=2 scored starters, probability range [0,1], race mass <=1e-12 and scoring timestamps.
6. Dated independent pre-outcome-read declaration naming start date, model-object hash, and the sole primary metric; sign-off remains **UNSET**.

## Frozen metric design
Primary metric: unweighted mean of -ln(clip(p_winner,1e-15,1-1e-15)) across eligible races. Exactly one certified winner; >=2 scored starters; pre-scoring scratchings excluded; race mass error <=1e-12. No result-informed race exclusions. Report primary metric before computing any secondary metric.

## Requested independent review (planning only)
Decide whether to **APPROVE / AMEND / REJECT the proposed dates and fixed stopping rule as a candidate**. If rejected due to 2026 seal, recommend an alternative strictly future window such as 2027, without granting access or execution. No fit, score, feature search, price analysis, SP/BSP input, 2025–2026 unsealing, or retrospective testing requested.

## State
**STOP before execution.** This proposal is not an activation record, not an unsealing request, and not evidence of independent validation.
