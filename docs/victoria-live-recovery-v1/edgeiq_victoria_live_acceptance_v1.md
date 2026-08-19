# EDGEiQ Victoria Live Acceptance V1

Status: READY_TO_REBUILD_DOWNSTREAM
Blocker: Current-window Performance Base observations exist and should feed normalisation.

## Core Pipeline

Results through Performance Base pass: True
Performance Base rows: 52425
Performance Base min date: 2000-08-02
Performance Base max date: 2026-07-30

## Normalisation Gate

HPR-NORM-A-v1 effective from: 2026-07-20
Rows before effective date: 52414
Rows on/after effective date: 11
Rejection reasons: {'NORMALISATION_PARAMETER_NOT_EFFECTIVE_FOR_PERFORMANCE_DATE': 52414}

## Sectionals

Canonical runner sectional rows: 2854
Visible-page sectional rows: 0
Sectionals required for core Performance Intelligence: NO

## Acceptance

Victoria cannot yet reach PASS_VICTORIA_LIVE because there are no current-window Performance Base observations dated on or after 2026-07-20. This is a governed data-availability blocker, not a Racing.com sectional dependency and not a core timing architecture blocker.