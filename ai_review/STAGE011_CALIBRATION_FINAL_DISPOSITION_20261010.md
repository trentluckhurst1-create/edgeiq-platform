# Stage011 calibration audit — final disposition (2026-10-10)

## Independent review decision
**REJECT further calibration experimentation; RECORD AND STOP.**

## Established execution results
- Stage011 reproduction PASS; reused development evidence only.
- 2022: 612 races, 7,459 runners, log loss 2.125060402398, top-1 winner share 0.225490, max ten-bin absolute gap 0.104727.
- 2023: 2,396 races, 30,163 runners, log loss 2.131427427909, top-1 winner share 0.206594, max ten-bin absolute gap 0.520011.
- 2024: 2,402 races, 31,234 runners, log loss 2.102222925037, top-1 winner share 0.229808, max ten-bin absolute gap 0.156418.
- All 5,410 races pass probability mass tolerance 1e-12 (observed max error 1.33e-15).
- Evidence class: REUSED_DEVELOPMENT.

## Calibration interpretation
- 2023 50–60% bin has one runner; its 0.520011 gap does not show systematic miscalibration.
- High-volume 0–20% bins are descriptively close; not validation.
- 20–40% results are mixed and higher-probability bins too sparse to estimate a slope.
- No probabilities above 60%; compression is not established without a predeclared baseline.

## Governance
Stage011 remains unvalidated champion; Stage016 unpromoted.
No calibrator fit, temperature or Platt correction, threshold search, feature change, market/SP input, 2025–2026 access, or profitability inference.
No further experiment until an unexposed evaluation window or named feature with certified point-in-time builder exists.
This document records the audit only; it does not promote a model or authorise execution.
