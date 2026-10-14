# EDGEiQ Issue #25 Stage011 Runner Certification Report

Status: RESEARCH-ONLY VALIDATION, NO SCORING OR RETRAINING

## Branch Scope

This branch was created from `origin/main` and contains only the Stage011 live-completion recovery paths extracted from commit `c4819156`. It excludes the unrelated Issue #23 Top-1 winner-selection and BACK/LAY research changes that remain on PR #24.

## Source Admission

| Source | Status | SHA-256 |
|---|---|---|
| `october_graphql_field_identities.csv` | `PASS` | `7f0332cd3cf98e3c753a8951e276daa84d0c652ac1c1f57b498bfde4e19026e4` |
| `caulfield_browser_form.csv` | `PASS` | `042e0a36600fa1bac179b41973a0a074e53929a92e023f90610f23d12f7167bf` |
| `public_race_snapshot_20261012T051330Z.json` | `PASS` | `579afa96ef24e3dae641177ca4c13a01980bbe82d7a2e96b426eab0eed061aad` |
| `LAB245B_WAREHOUSE_RUNNER_LVS.csv` | `PASS` | `169652f38b830a4d2337975d65d9cead16fe306373ac4802bc57b7b33793a8fb` |
| `edgeiq_certified_flat_walk_forward_epi_026.csv` | `PASS` | `97d2fbca0ed1a613df2fb6a826b50ec2a8a68c3c456b136afafd8a964c55f132` |
| `ISSUE23_LIVE_HISTORY_FEATURE_CANDIDATES_V3.csv` | `MISSING_OPTIONAL_SOURCE` | not used |

The LAB245B warehouse matched the expected fixed SHA-256 exactly. The optional candidate file was absent and was not substituted.

## Runner Certification Summary

- Declared runners: 104
- Races: 8
- Feature/provenance-eligible active runners: 78
- Withheld scratched runners: 2
- Withheld active runners: 24
- Certified LAB245B identities: 81
- Live EIQ horse ID hash provenance: 104 / 104 pass
- Ambiguous prior race matches: 0
- Duplicate LAB245B prior race records: 0

Identity bridge statuses:

- `CERTIFIED_EXACT_ID_MULTI_PRIOR_MATCH`: 81
- `NO_STRICT_PRIOR_LAB245B_HISTORY`: 18
- `ONE_PRIOR_MATCH_INSUFFICIENT`: 5

## Two Scratched Certified Identities

These runners have certified identities but are withheld because they are scratched:

- Race 3, `Miss Castelvecchio`
- Race 5, `Yam`

## Zourain

`Zourain` is identity-certified but not score-eligible:

- Race: 3
- Runner ID: `15842114`
- Canonical horse ID: `EIQ_HORSE_BE3BDAC12250DD33`
- Matched distinct prior races: 11
- LAB245B prior records: 20
- Direct LVS status: `DIRECT_LVS_AVAILABLE`
- Distance-near LVS status: `DISTANCE_NEAR_LVS_AVAILABLE`
- Personnel priors: jockey and trainer both `D45_FULL_HISTORY_PRIOR`
- Blocking feature: `margin_per_runner_last1`
- Blocking reason: `SOURCE_FIELD_UNAVAILABLE`

This is a genuine feature-value blocker, not an identity or timing blocker.

## Twenty-Three Unresolved Timing Identities

The 23 runners without certified historical timing split as:

- 18 with `NO_STRICT_PRIOR_LAB245B_HISTORY`.
- 5 with `ONE_PRIOR_MATCH_INSUFFICIENT`.

The five one-record cases are:

- Race 2, `Cliff Runner`
- Race 3, `Space Age`
- Race 5, `Grecian Destiny`
- Race 6, `Best Time`
- Race 6, `Freedom Flame`

The full runner-level certification table is saved to:

`outputs\research\stage011_live_completion\EDGEIQ_STAGE011_RUNNER_CERTIFICATION_REPORT.csv`

## Personnel and Timing Coverage

- Jockey prior available: 100 / 104
- Trainer prior available: 101 / 104
- Personnel feature cells populated: 603 / 624
- Direct LVS timing available: 81 / 104
- Distance-near LVS available: 74 / 104
- Certified missing distance-near LVS: 7

## Validation Commands

```powershell
Set-Location "C:\EDGEIQ_ISSUE25_STAGE011"
python -m py_compile scripts\research\run_edgeiq_stage011_live_feature_pipeline.py scripts\research\test_edgeiq_stage011_live_feature_pipeline.py
python scripts\research\test_edgeiq_stage011_live_feature_pipeline.py
python scripts\research\run_edgeiq_stage011_live_feature_pipeline.py
```

All commands passed. No market data, target outcomes, model fitting, Stage011 scoring, production changes, or betting logic were used.
