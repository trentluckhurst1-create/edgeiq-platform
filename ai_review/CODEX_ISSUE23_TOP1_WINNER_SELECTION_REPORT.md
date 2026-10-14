# Issue 23 Top-1 Winner Selection Report

Status: COMPLETED.

The experiment used existing admitted Issue5 runner scores for 2022-2024 and Stage006 race-state diagnostics. It did not use pricing, betting, market, SP/BSP, odds, profitability data, production code, or sealed 2025-2026 records.

## Primary Question

Can an existing non-market challenger improve race-level Top-1 winner selection enough to replace Stage011?

Primary metric: one highest-probability runner per race, with deterministic tie handling by probability descending then horse id ascending.

Guardrails: race log loss, runner Brier, calibration, winner-in-field coverage, and paired bootstrap uncertainty.

## Controlled Challenger

`ISSUE23_TOP1_ROUTER_2022_LOCKED`

The router was predeclared as:

- Learn from 2022 development slices only.
- Slice by field-size band, distance band, and prior-history band.
- Use Stage016 only where the 2022 slice has at least 50 races, Stage016 Top-1 beats Stage011 by at least 0.03, and Stage016 LL is no worse than Stage011 by more than 0.03.
- Otherwise use Stage011.

The rule selected Stage016 for 1 of 27 race-state slices.

## Core Results

Stage011:

- 2022 Top-1: 0.236928
- 2023 Top-1: 0.201586
- 2024 Top-1: 0.228976

Stage016:

- 2022 Top-1: 0.228758
- 2023 Top-1: 0.212020
- 2024 Top-1: 0.222731

Router:

- 2022 Top-1: 0.240196
- 2023 Top-1: 0.202003
- 2024 Top-1: 0.230641

The 2023 router paired Top-1 gain versus Stage011 was only 0.000417, with 95% bootstrap interval [-0.002922, 0.003756]. That is not a robust improvement.

Candidate G had the highest weighted Top-1 across 2022-2024 at 0.223475, but it failed the log-loss guardrail: weighted LL 2.198334 versus Stage011 2.120390.

## Verdict

NO-GO. Stage011 remains champion.

Stage016 has useful signal, especially in 2023 log loss, but its Top-1 effect is not stable across years. The controlled router did not generalize enough to justify promotion.

## Reproduction

```powershell
cd C:\EDGEIQ_ISSUE23
python scripts\research\run_issue23_top1_winner_selection.py
```
