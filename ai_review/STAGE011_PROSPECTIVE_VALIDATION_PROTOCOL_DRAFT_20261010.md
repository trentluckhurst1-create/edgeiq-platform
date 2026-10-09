# EDGEiQ Stage011 — Prospective Validation Protocol (DRAFT; NOT ACTIVE)
Date drafted: 2026-10-10
Governance: Grok independent review 2026-10-10 — AMEND, planning only.

## Status and prohibitions
**DRAFT / NOT FROZEN / NO EXECUTION AUTHORITY.** No fitting, scoring, feature search, market or SP input, historical identity investigation, or 2025–2026 access. No evaluation window is activated by this document. Stage011 remains an unvalidated champion; Stage016 remains unpromoted.

## Pre-activation fields (must be completed and approved before first outcome read)
- Prospective evaluation start date (local race timezone): **UNSET**.
- End date / fixed stopping rule: **UNSET**.
- Frozen model artifact SHA-256: **UNSET** (a source-code commit hash is not a trained-model hash).
- Frozen feature manifest and ordered column list SHA-256: **UNSET**.
- Frozen training population, cutoff and evidence of >=1,000 strictly earlier *certified* races: **UNVERIFIED**.
- Frozen input schema, canonical runner/race identity and point-in-time feature availability: **UNVERIFIED**.
- Pre-scoring sign-off timestamp and independent approval: **NOT GIVEN**.
- Outcome-access controls and evidence of no previous outcome reads or metrics for evaluation races: **UNVERIFIED**.

## Fixed Stage011 settings (from reproduced Stage011 source)
HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_leaf_nodes=5, l2_regularization=1, random_state=42). Scoring uses race-level softmax of decision_function scores. Feature construction, order, missingness handling, identity and historical sources must match a separately certified frozen manifest; no substitutions or tuning.

## Primary metric — only one
**Race-normalised win log loss**: for each eligible race with exactly one certified winner, compute -ln(p_winner) using the race-softmax probability, then average equally over eligible races. Predeclare numeric clipping, missing/invalid race policy, and eligibility rules before activation; no post hoc exclusions. The exact computation must be frozen with the scoring protocol.

## Scoring artifact contract (to freeze before activation)
One row per race/runner, with: race identifier, runner identifier, race date, scoring timestamp (before scheduled off), raw score, race-normalised win probability, model artifact SHA-256, feature manifest SHA-256, training cutoff, training population provenance, protocol version, evaluation window ID, and outcome-blind scoring evidence. Outcomes must be appended in a separate, later controlled evaluation phase, never during prospective scoring. Include checks for unique race/runner keys, probability range [0,1], race mass error <=1e-12, and no race from or after the evaluation start date in training. The final schema and file hashes require separate approval.

## Independence and timing
A signed/dated declaration must exist **before any evaluation outcome is read**. It must name the prospective window start date, frozen model hash, and single primary metric. Confirm no evaluation outcome has been inspected and no metric computed on that window, with audit trail. Evaluation races must occur after the freeze and be absent from training, selection, calibration and prior outcome-based analyses. The minimum training prerequisite is >=1,000 certified races strictly earlier than the evaluation window.

## Financial evaluation
Not authorised. Any future profitability claim requires a collision-free, timestamped pre-off price source. SP/BSP do not qualify.

## Activation gate
Independent reviewer must approve the fully populated protocol, freeze evidence, point-in-time controls, training eligibility and access boundary in a **separate execution decision**. Without that, STOP. The 2025–2026 years remain sealed unless explicitly and separately unsealed.

## Current decision
Record this draft only. Do not run, fit, score, inspect sealed outcomes, or designate a retrospective year as an independent window.
