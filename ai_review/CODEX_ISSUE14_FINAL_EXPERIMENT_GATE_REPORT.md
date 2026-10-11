# CODEX Issue #14 Final Experiment Gate Report

Date: 2026-10-11  
Branch: `codex/issue-14-final-experiment-gate`  
Scope: final protocol corrections and execution gate only. No model fitting, scoring, market access, sealed-year access, Stage011 change, production change, or model promotion.

## Decision

**RUN-READY BUT STOPPED.**

The logit-softmax probability rule is now frozen in implementation and tests. The experiment remains fail-closed until a legitimate research-use attestation is supplied.

## Exact Probability Rule

For each race `r`, the model must use `HistGradientBoostingClassifier.decision_function(X_i)`:

```text
z_i = decision_function(X_i)
p_i = exp(z_i - max_r(z)) / sum_j exp(z_j - max_r(z))
```

Probability mass gate:

```text
abs(sum_i p_i - 1) <= 1e-12 for every race
```

Direct normalization of `predict_proba` is forbidden.

## Frozen Experiment

- Train years: `2000-2010`, `2012-2015`, `2018`
- History-only sparse year: `2016`
- Excluded missing years: `2011`, `2017`
- Evaluation years: `2019`, `2020`, reported separately
- Reused, not independent: `2021`
- Learner: `HistGradientBoostingClassifier(loss="log_loss", learning_rate=0.05, max_leaf_nodes=5, l2_regularization=1.0, max_iter=200, random_state=42)`
- Features: fixed Issue #12 non-market feature set
- Missing handling: HGB native missing handling plus explicit identity missing flags

## Research-Use Attestation Gate

Default state: **UNAPPROVED**.

The preflight requires an external JSON attestation containing:

- `decision`
- `authorising_rights_holder_or_owner_role`
- `basis_or_terms`
- `source_scope`
- `approval_date`
- `permitted_purpose`
- `approval_evidence_reference`
- `approval_evidence_sha256`

The script validates that:

- `decision` is `APPROVED`
- source scope explicitly covers pre-2022/pre2022 data
- permitted purpose states research
- approval date is valid ISO date and not in the future
- evidence hash is a 64-character SHA256 value

Possession of source data is not treated as permission.

## Commands

Preflight without attestation, expected to stop:

```powershell
cd C:\EDGEIQ_PROFITABILITY_RESEARCH
.\scripts\research\run_issue14_frozen_historical_experiment.ps1
```

Preflight with attestation:

```powershell
cd C:\EDGEIQ_PROFITABILITY_RESEARCH
.\scripts\research\run_issue14_frozen_historical_experiment.ps1 -Attestation "path\to\research_use_attestation.json"
```

Compile and tests:

```powershell
cd C:\EDGEIQ_PROFITABILITY_RESEARCH
python -m py_compile .\scripts\research\run_issue14_frozen_historical_experiment.py .\tests\test_issue14_frozen_historical_experiment.py
python -m unittest .\tests\test_issue14_frozen_historical_experiment.py
```

## Verification

Tests cover:

- race probability mass sums to 1
- monotonic ranking by logits
- numerical stability for extreme logits
- one-starter races
- fail-closed missing attestation
- valid complete approved attestation

## Current Preflight Status

The committed preflight artifact was generated without an attestation and therefore stops with:

- `ATTESTATION_NO_ATTESTATION_PATH_SUPPLIED`

This is expected and correct.

## Remaining Gate

A legitimately authorised person or rights holder must supply the research-use attestation. After that, the same preflight can pass and the one frozen experiment can be separately authorised.
