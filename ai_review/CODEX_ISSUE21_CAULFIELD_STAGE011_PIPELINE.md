# Issue 21 Caulfield Stage011 Pipeline

Status: IMPLEMENTED AND EXECUTED LOCALLY AS RESEARCH-ONLY.

This branch adds an isolated Stage011 live-scoring bridge for the 2026-10-14 Caulfield field. It does not modify production code, does not alter frozen model artifacts, and does not use market, SP, BSP, odds, or price data.

## What Was Built

- `scripts/research/run_issue21_caulfield_stage011_pipeline.py`
  - Reads the Caulfield GraphQL field identity file from the local `EDGEIQ_PLATFORM` live-acquisition output.
  - Uses declared runner identity, scratching status, current barrier, jockey, trainer, race number, and source URL.
  - Recovers target race distances from the local public rendered-page snapshot.
  - Reads certified LAB245B strict-PIT LVS history where available.
  - Reads the Caulfield browser-form history for strict-prior finish, margin, field size, jockey, trainer, barrier, and clean-finish features.
  - Optionally captures Racing.com GraphQL responses with Playwright into a restartable checkpoint when `--capture-browser` is supplied.
  - Writes a 35-feature Stage011 matrix and audit artifacts.

- `scripts/research/edgeiq_stage011_live_scorer.py`
  - Loads the frozen Stage011 model only after checking the expected SHA-256.
  - Enforces the frozen 35-feature manifest SHA-256.
  - Rejects forbidden outcome/market columns.
  - Scores with the fitted model decision function.
  - Applies race-level softmax and verifies each race sums to 1.

- `tests/test_issue21_caulfield_stage011_pipeline.py`
  - Covers elapsed-time parsing, duplicate race payload handling, trial/jumpout exclusion, and race softmax mass.
  - Runs with plain Python assertions; `pytest` is not required.

## Local Execution Result

Command run:

```powershell
python scripts\research\run_issue21_caulfield_stage011_pipeline.py
```

Result:

- Status: `SCORED_RESEARCH_ONLY`
- Declared Caulfield entries: 104
- Active scored runners: 102
- Scratched excluded runners: 2
- Races scored: 8
- Stage011 features: 35
- All-missing features: 0
- Features with at least one missing value: 27
- Frozen model SHA-256: `f06c050e9febcd5b2588d29f90065b0a482872ab4be8c2cdb87ac22803ab9b91`
- Frozen feature manifest SHA-256: `f35dd342d570b35831043c75cf756f7cac4e28ebdd564988393db3383c82454f`
- Race probability mass max absolute error: `1.1102230246251565e-16`
- Market data used: NO
- Production modified: NO
- Frozen artifacts modified: NO
- Prospective publication attested: NO

## Outputs

Created under `outputs/research/issue21_caulfield_stage011_pipeline/`:

- `LAB21_CAULFIELD_STAGE011_FEATURE_MATRIX.csv`
- `LAB21_CAULFIELD_STAGE011_PROBABILITIES.csv`
- `LAB21_CAULFIELD_FEATURE_COVERAGE_BY_RUNNER.csv`
- `LAB21_TIMING_RACE_RECORDS.csv`
- `LAB21_CAULFIELD_STAGE011_PIPELINE_AUDIT.json`
- `LAB21_CAULFIELD_STAGE011_PIPELINE_REPORT.md`

## Important Caveat

The scorer output is a research-only Caulfield probability file, not a certified prospective publication.

Two feature groups are still marked as provisional in the audit:

- Jockey/trainer priors are reconstructed from the available Caulfield browser-form slice, not from a complete certified all-runner prior warehouse.
- Post-2026-06-21 recent LVS recovery is only used when elapsed race time is captured; the distance-only fallback is explicitly marked provisional and is not certified LAB245B.

The pipeline therefore delivers the requested end-to-end machinery and a scored Caulfield field, while preserving a clear audit trail of what remains unavailable for full live certification.

## Exact PowerShell Command

```powershell
cd C:\EDGEIQ_ISSUE21; .\scripts\research\run_issue21_caulfield_stage011_pipeline.ps1
```

To force a fresh browser/GraphQL capture before scoring:

```powershell
cd C:\EDGEIQ_ISSUE21; .\scripts\research\run_issue21_caulfield_stage011_pipeline.ps1 -CaptureBrowser
```
