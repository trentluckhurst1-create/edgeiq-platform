# Issue #5 Stage011 Drift Audit Schema Fix

Status: SCHEMA FIX READY. AUDIT PASSED is not claimed because the real score-file audit was not run.

## Scope

This repair addresses the read-only Stage011 drift-audit failure where the score-file schema contained `y`, but the audit searched only for longer winner-column names and stopped with an ambiguous-winner error.

No Stage011 predictions were changed. No model fitting, scoring, A-G rerun, market/price work, or sealed-year access is authorised by this fix.

## Provenance for `y`

`y` is accepted as the Stage011 winner label because existing repository lineage defines and validates it before score-file creation:

- `ai_review/SCORING_ARTIFACT_PROTOCOL.md` defines `y` as the binary outcome with exactly one `1` per eligible race.
- `scripts/research/run_v2_stage004_certify_and_coverage.py` creates the certified single-winner universe by grouping races on `y` and retaining only races with one winner.
- `scripts/research/run_v2_stage011_reproduction_artifact.py` validates `x.y` as binary, validates exactly one winner per race, then writes `y` into `STAGE011_RUNNER_PROBABILITIES_{year}.csv`.

The new audit detector therefore recognises `y` only when the expected Stage011 score-file provenance schema is present. A bare `y` column without the Stage011 score provenance fails closed.

## Files Added

- `scripts/research/audit_v2_stage011_baseline_drift.py`
- `tests/test_stage011_drift_audit_schema.py`

## Stop Conditions

The audit stops on:

- missing `_race`, `_horse`, or `p`;
- missing winner label;
- `y` present without Stage011 score-file provenance fields;
- ambiguous winner labels;
- null or duplicate `(_race, _horse)` keys;
- null, non-numeric, or non-binary winner labels;
- any race with anything other than one winner;
- non-finite probabilities;
- probabilities outside `[0, 1]`;
- within-race probability mass error greater than `1e-12`;
- requested year file missing;
- `evaluation_year` mismatch when that column is present.

## Commands Run

```powershell
python -m py_compile scripts\research\audit_v2_stage011_baseline_drift.py tests\test_stage011_drift_audit_schema.py
python tests\test_stage011_drift_audit_schema.py
```

## Later Read-Only Audit Command

Run only after separate Grok approval for the real score-file audit:

```powershell
python scripts\research\audit_v2_stage011_baseline_drift.py --scores-dir outputs\research\model_v2\stage011_reproduction --years 2022 2023 2024 --report outputs\research\model_v2\stage011_reproduction\STAGE011_BASELINE_DRIFT_AUDIT.json
```

This command is read-only with respect to score files and writes only the requested audit report. It does not fit models, rescore rows, or modify Stage011 predictions.
