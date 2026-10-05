# LAB245B — Governed profitability research checkpoint

## Status
PREHOLDOUT CODE READY. Full-data execution requires the immutable local performance warehouse. 2025–2026 remains sealed.

## Scientific lineage
- LAB244 latent synthetic-performance engine: REJECTED.
- LAB245B target: actual race-T runner performance, reconstructed strict point-in-time.
- Historical runner-LVS authority is parity/formula evidence only because its legacy benchmark construction used all-history observations.

## Immutable data authorities
- Performance warehouse: `docs/performance-intelligence/warehouse/edgeiq_performance_fact_warehouse_v1.csv`
  - bytes: 416143437
  - SHA-256: `bcdcef1c7cb9144feae5783ca2fa83b1dc2b8dc07a42ac31c31fd7bd12b53107`
- Historical runner-LVS parity authority:
  `docs/performance-intelligence/lengths-v-standard/edgeiq_runner_lengths_v_standard_fact_v1.csv`
  - rows: 533387
  - bytes: 80343742
  - SHA-256: `b08bb7a334ddba2f6a76942452dd964cd59db05001dc5710ff19aa7fc6e12926`

## Recovered producer semantics
- seconds per length = 0.17
- race LVS = (standard_time_seconds - official_race_time_seconds) / 0.17
- runner LVS = race LVS - finish_margin
- runner time equivalent = race time + finish_margin * 0.17
- positive LVS = faster/better than standard

## Strict-PIT benchmark contract
- grouping: canonical track ID + distance + governed condition
- minimum prior races: 20
- statistic: median race time
- target race date D uses only benchmark races with date < D
- all races on the same date are scored before that date is added to benchmark history
- no threshold reduction
- centiseconds conversion invariant explicitly guards against the historical /1000 regression

## B1
Forecast next runner LVS using only prior horse history.
- development model selection: 2022–2023 only
- fixed confirmation: 2024
- 2025–2026 sealed
- ML candidates: Ridge and HGB
- simple comparators: last1, mean3, mean5, median5
- survival requires MAE, RMSE and within-race Spearman improvement in each development year, pooled development and 2024.

## B2
Convert fixed B1 predictions to race probabilities.
- temperature selected on 2022–2023 only
- fixed 2024 confirmation
- exact probability mass
- full represented field only
- primary: race-winner log loss; secondary: runner Brier
- minimum complete-field volume gate

## B3
Final-SP selective-betting forensics only.
- market is not a probability-model feature
- predeclared edge thresholds: 5%, 10%, 15%, 20%
- 2022 selects once; 2023 confirms; 2024 validates
- exact race+horse identity only; no fuzzy matching
- final-SP universe is complete-field exact-identity intersection and coverage is audited
- final SP cannot establish deployable POT; actual timestamped pre-race offered odds are required for deployment claims

## Holdout
LAB245B4 is not called by the preholdout launcher.
It may open 2025–2026 only after B3 returns SURVIVE_TO_FORENSIC_HOLDOUT and only via explicit manual holdout execution.

## Execution
GitHub Actions compiles the governed chain but cannot execute full data because the large immutable data authorities are intentionally not published to GitHub.

Local isolated launcher:
`scripts/research/run_lab245b_local.ps1`

Default roots:
- research: `C:\EDGEIQ_PROFITABILITY_RESEARCH`
- read-only data: `C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM`

No production reset, clean, checkout or data mutation is part of LAB245B execution.
