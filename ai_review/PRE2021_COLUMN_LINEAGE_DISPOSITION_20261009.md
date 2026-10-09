# EDGEiQ — Gate 2 column-lineage audit disposition (2026-10-09)

Source: user's local output from scripts/research/audit_pre2021_column_lineage_gate.py (commit 3d3dbf4b).

## Observed results
- Pre-2021 rows inspected under approved column restrictions: 644,364.
- Provisional flat races: 50,671.
- Exactly-one-winner and unique runner-key provisional flat races: 50,209 (99.088236%).
- Remaining 462 races fail the eligibility rule; script reports zero-winner and multiple-winner by year.
- Missing 2011 and 2017 remain gaps; 2016 only 399 races.
- Jumps and picnic labels were excluded by string pattern; nonblank remaining class labels were called FLAT_PROVISIONAL, not independently verified flat.
- No pre-race candidate builder was inspected or certified. Script status STOP, reason NO_CERTIFIED_PRE_RACE_CANDIDATE_BUILDER.

## Interpretation
Outcome-integrity numerical thresholds pass (>=95%, >=1000), but overall gate does not pass because no PRE_RACE_CANDIDATE lineage is established. This is not a model-fitting approval or a frozen modelling population. Header-only status guesses are not PIT evidence; in particular race_time_utc and track_rating require explicit interpretation.

## Requested next independent-review decision
APPROVE / AMEND / REJECT a **read-only, named-source feature-builder lineage inspection** only. Restrict to selected committed research scripts that create declared pre-jump fields (e.g. barrier, declared weight, distance, race class, prior historical form). No warehouse reread, no other archive read, no joining, no scoring/fitting, no 2025–2026 outcomes. Require exact file allowlist, pre-jump temporal contract, exclusion of current-race finish/margin/time/rating, market/SP/odds, EPI, and 90% historical coverage measurement to be separately authorised before a fit. Return one named feature proposal, not a feature search.
