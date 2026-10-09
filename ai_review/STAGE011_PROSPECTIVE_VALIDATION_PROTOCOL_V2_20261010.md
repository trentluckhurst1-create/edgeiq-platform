# EDGEiQ Stage011 — Prospective Validation Protocol v2 (AMENDED DESIGN; INACTIVE)
Date: 2026-10-10
Supersedes draft at commit f092e46c for protocol design only.
Independent reviewer decision: AMEND, 2026-10-10.

## Status
**DESIGN ONLY / NOT ACTIVATABLE / NO EXECUTION AUTHORITY.** No fit, score, feature search, calibration, market/SP input, 2025–2026 access or retrospective evaluation-window designation. Stage011 remains the unvalidated champion; Stage016 remains unpromoted.

## Unset activation prerequisites
- Prospective start date: **UNSET**.
- Prospective end date or fixed stopping rule: **UNSET**.
- Independent pre-outcome-read sign-off and timestamp: **UNSET**.
- Frozen ordered feature manifest and SHA-256: **UNSET**.
- Training cutoff and >=1,000 strictly earlier certified races: **UNVERIFIED**.
- Frozen point-in-time features and race/runner identity controls: **UNVERIFIED**.
- Outcome-blind evaluation and no-prior-metrics evidence: **UNVERIFIED**.
- Fitted model object and its SHA-256: **NOT CREATED**.

## One fit, frozen before scoring
The start date and frozen feature-manifest hash must be written before fitting. Then fit Stage011 **once**, using only certified races strictly earlier than the prospective start date; no evaluation race can enter training. Require at least 1,000 strictly earlier certified training races. Freeze the fitted object and compute the **model-artifact SHA-256 of its serialized bytes**; a source-code commit hash does not substitute. Freeze the fixed HGB settings and seed 42: max_iter=200, learning_rate=0.05, max_leaf_nodes=5, l2_regularization=1, random_state=42. Use the exact certified Stage011 feature construction and race-level softmax; no tuning or substitutions.

## Predeclared primary metric (one only)
**Unweighted race-normalised win log loss** over eligible evaluation races:
For each eligible race, obtain the race-softmax winning runner probability p_w; clip p_w to [1e-15, 1-1e-15] and compute -ln(clipped p_w). The reported primary metric is the arithmetic mean of these per-race losses, with each eligible race weighted equally.

### Eligibility and exclusion, fixed in advance
- Exactly one certified winner.
- At least two scored starters.
- Race-softmax probabilities sum to 1 with absolute error <=1e-12.
- Exclude any runner scratched **before the scoring timestamp** from the scoring field, prior to probability normalisation.
- No race may be dropped or reclassified after its result is observed. Any predeclared eligibility failure must be documented with a reason and auditable timing; a post-outcome failure must be reported, not silently removed.

## Prospective scoring artifact contract
One immutable, outcome-blind row per scored starter: evaluation window ID, race ID, runner ID, race date, scoring timestamp (before off), scratch-status-as-of-scoring timestamp, raw decision score, race-softmax probability, frozen feature-manifest hash, fitted model-object hash, training cutoff and provenance, protocol version, and evidence of score publication before outcomes. Validate unique race/runner keys, [0,1] probabilities, race mass <=1e-12 and >=2 scored starters. Append certified winner outcomes only in a separate later controlled evaluation phase; never overwrite pre-outcome scoring artifacts. Retain integrity hashes and audit trail.

## Reporting order
Report the **single primary race-normalised win log loss first**. Before it is reported, **do not compute any secondary metric, calibration table, or price comparison**. Any later secondary analyses require separate approval. No betting or profitability inference from this protocol. A future profitability study requires a collision-free, timestamped pre-off price source; SP and BSP do not qualify.

## Independence declaration
Before first evaluation outcome read, a dated signed statement must name the prospective start date, frozen fitted model-object hash, and single primary metric. It must establish no outcome read and no previous model metric for the evaluation window, and confirm that the evaluation races have not entered fitting, selection or calibration. A retrospective year cannot fill the prospective window fields; 2025–2026 remain sealed without separate explicit unsealing authority.

## Activation decision
This amendment **does not authorise execution**. A separately approved, fully specified prospective start/end rule, signed freeze declaration, verified certified training universe, model/manifest freeze and outcome-access controls are mandatory. Otherwise STOP.
