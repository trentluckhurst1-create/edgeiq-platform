# EDGEiQ Prospective Scoring Artifact Protocol

**Status:** FROZEN CONTRACT ONLY — NO IMPLEMENTATION AUTHORISED  
**Date:** 2026-10-09  
**Basis:** Grok independent review of Stage044 STOP, following commit `a92c4a1c`.

## Purpose and scope

Specify the minimum evidence that must be preserved **prospectively** for any future runner-level model-score comparison. This document does not reconstruct historical Stage011 or D99 predictions and does not authorise another fit, writer implementation, feature search, or production change.

Stage044 run `37879258536` succeeded as execution but stopped on missing certified original runner-level scored artifacts. Historical Stage011 and D99 annual log losses remain **NOT_COMPARABLE** on a certified common race set. Stage011 remains the last predeclared champion, **not** a reproducible runner-level score. Stage016 unpromoted; historical rating and EPI parked; identity mint unresolved.

## Required future scored-artifact schema

Exactly **one row per runner**, with these fields:

| Field | Contract |
| --- | --- |
| `_race` | Exact certified race key; no fuzzy join |
| `_horse` | Exact certified runner/horse key |
| `race_date` | Race date |
| `year` | Evaluation year, at most 2024 under current seal |
| `y` | Binary outcome: exactly one `1` per eligible race, others `0` |
| `p` | Post-within-race-softmax probability, not raw margin |
| `model_id` | Immutable model identifier |
| `git_sha` | Source commit identifier |
| `random_state` | Model random seed/state |
| `train_year_lt` | Strict training cutoff: train year less than this value |
| `feature_names_sha256` | Nonblank SHA-256 digest of the feature-name manifest |
| `input_file_sha256` | Nonblank SHA-256 digest of the scored input file |
| `n_train_rows` | Number of training rows |
| `n_test_rows` | Number of evaluation rows |

The contract's required fields must be present and populated. Do not include SP, odds, market rank, EPI, or any sealed-year outcome in the scored file. Do not read their values for this protocol. Sealed-year rows may be reported **only as an excluded count in the log**.

## Validation and comparability

- Require unique `(_race, _horse)` pairs, exactly one winner per eligible race, finite `p` values in `[0,1]`, and within-race `sum(p)` within `1e-12` of 1.
- Both original, provenance-certified scored artifacts must exist. Neither may be substituted with a neighbouring experiment's predictions.
- Compare only exact race-key intersections. For **each** test year, the intersection must include at least **95% of that year's races in each artifact**. Both input hashes must be recorded. If any condition fails, result is `NOT_COMPARABLE`.
- A comparability pass establishes eligibility for a later independently authorised score audit, **not** model superiority, feature value, or permission to fit.

## Separately authorised first implementation test (NOT NOW)

A future writer dry-run may use **one synthetic three-runner race only** and **must not fit a model**. It must fail if `sum(p)` differs from 1 by more than `1e-12`, any forbidden column is present, or either SHA-256 hash field is blank. This is a proposed test specification, **not authorisation to implement**.

## Stop and change control

**STOP after committing this contract.** Do not implement the writer, re-fit Stage011 or D99, reopen Stage016, rating, identity mint or EPI, examine 2025–2026 outcomes, add market/SP inputs, or begin another feature search. Any subsequent work requires a separately reviewed and explicitly authorised change.
