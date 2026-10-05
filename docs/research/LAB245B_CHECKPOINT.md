# LAB245B Research Checkpoint

Updated: 2026-10-05

## Objective
Test whether strict point-in-time historical runner performance (Lengths v Standard) can improve next-race performance forecasting, then probability quality, then selective historical betting economics without opening the 2025-2026 sealed holdout prematurely.

## Frozen scientific contract
- Historical warehouse authority: `edgeiq_performance_fact_warehouse_v1.csv`
- Frozen warehouse bytes: 416,143,437
- Historical runner-LVS parity authority (required for preflight/parity): `edgeiq_runner_lengths_v_standard_fact_v1.csv`
- Frozen parity authority bytes: 80,343,742
- Frozen parity SHA256: `b08bb7a334ddba2f6a76942452dd964cd59db05001dc5710ff19aa7fc6e12926`
- Runner formula recovered from original producer:
  - race LVS = (standard time - race time) / seconds per length
  - runner LVS = race LVS - finish margin
  - runner time equivalent = race time + finish margin * seconds per length
- Benchmark chronology: target date D uses races strictly before D.
- Minimum prior benchmark races: 20.
- Original implementation identity scope preserved as canonical track + distance + condition + jurisdiction (approved conceptual contract: track + distance + condition).
- Governed timing eligibility: race time 35-420 seconds; distance 800-3600m; canonical track present; known condition.
- Same-date horse history is excluded from predictors.
- Invalid finishing outcomes remain represented in the race field but receive null LVS targets.
- Probability evaluation requires the full represented race field.
- Market/final SP is excluded from performance and probability model fitting.
- Final SP may be used only for historical policy-selection/forensic economics and is explicitly non-deployable.
- 2025-2026 holdout remains sealed.

## Preholdout stages
1. Preflight authority/schema/hash checks.
2. Build strict-PIT runner LVS target.
3. Historical authority parity audit; declared correlation threshold >= 0.90.
4. Build prior-history compact feature bridge.
5. LAB245B1 next-performance challenger:
   - OOF 2022 and 2023 development.
   - fixed 2024 confirmation.
   - simple recency baselines vs Ridge/HGB.
6. LAB245B2 probability challenger:
   - temperature selected on 2022-2023 only.
   - fixed 2024 confirmation.
   - complete-field races only.
7. LAB245B3 selective betting forensics:
   - predeclared edge thresholds 1.05/1.10/1.15/1.20.
   - policy selected on 2022 only.
   - 2023 confirmation.
   - unchanged 2024 validation.
   - reports POT, drawdown, losing run, odds concentration and profit uncertainty diagnostics.
8. LAB245B4 cannot be opened by the preholdout launcher.

## Execution
`scripts/research/run_lab245b_preholdout_chain.py` runs the governed chain and stops automatically at the first scientific rejection.

GitHub-hosted Actions compile-checks the chain successfully but cannot execute the data stages because the large source authorities are intentionally ignored from Git publication.

The correct execution environment is the local EDGEiQ data authority (or a future self-hosted runner attached to it), not publication of proprietary warehouse data to the repository.

## Important recent commits
- `700f7b22` recovered original runner-LVS semantics.
- `911a85b` benchmark grouping alignment.
- `615d5e5` normalized strict-PIT builder.
- `e6e6820`, `8c2d4c5`, `102ab755` normalized preflight/B3/B1 source.
- `fe1851a` enforced parity correlation threshold.
- `01b38a8` added fail-closed preholdout launcher.
- `9709114` aligned preflight schema to builder.
- `2dae3b4` applied governed benchmark eligibility.
- `919742d`, `3454fde`, `c48cb92` preserved full race fields across target/B2/B4 completeness logic.
- `569a0b4` added profit uncertainty diagnostics.
- `e3c8f2e` matched strict-PIT benchmark identity scope to original jurisdiction-aware producer key.
- `71617c9` made the frozen runner-LVS parity authority mandatory for preholdout execution.
- `854dfde` aligned the workflow data gate with the mandatory parity authority.

## Next executable result required
Run the preholdout chain against the local ignored data authority. Do not open LAB245B4 unless B1, B2 and B3 survive their frozen gates.
