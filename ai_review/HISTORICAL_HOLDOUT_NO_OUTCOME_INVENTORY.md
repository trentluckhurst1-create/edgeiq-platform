# Historical holdout — no-outcome inventory (2026-10-09)

**Status: FAIL / STOP.** Prepared in response to Grok's AMEND. This is a read-only source/metadata inventory, not a model run. No outcome values, SP/market values, sealed-year records or performance metrics were read or computed.

## Established from certified V2 research record

| Year | Certified V2 role | Previous model metric exposure | Earlier certified race count | Untouched historical holdout eligible? |
| --- | --- | --- | --- | --- |
| 2021 | Earliest certified V2 year; historical training material | No independent holdout metric established | 0 certified races before earliest year | **NO**: fails >=1,000 earlier races |
| 2022 | Walk-forward evaluation year (Stage007/011 and subsequent model selection) | **YES** | Not freshly recounted; must not be treated as untouched | **NO** |
| 2023 | Walk-forward evaluation year (Stage007/011 and subsequent model selection) | **YES** | Not freshly recounted; must not be treated as untouched | **NO** |
| 2024 | Walk-forward evaluation year (Stage007/011 and subsequent model selection) | **YES** | Not freshly recounted; must not be treated as untouched | **NO** |
| 2025–2026 | Sealed by research governance | Not inspected | Not inspected | **NOT AVAILABLE** |

The Stage007 and Stage011 source scripts explicitly loop over test years 2022, 2023 and 2024 and train on earlier years. Stage006 reads the Stage004 certified universe but does not hardcode the year inventory; its yearly counts are emitted at runtime. The original certified Stage004 data is stored in the local Windows research workspace and is not included in the GitHub repository tree. Thus **an exhaustive per-year race count has not been independently recertified in this GitHub-only inspection**. Do not invent counts or imply that 2021's race count was verified here.

## Decision under Grok's stop rule

Grok independently reports that 2021 is the earliest certified V2 year; 2022–2024 have been used for model selection; 2025–2026 are sealed. On that established scope, there is **no eligible, untouched historical holdout**: the earliest year has zero earlier certified races, the three later unsealed years have metric exposure, and the later years cannot be opened. The candidate search therefore fails closed without examining outcome rows or computing model metrics.

**STOP.** Do not fit or refit, dispatch any research run, read 2025–2026 outcomes, relabel 2022–2024 as independent, or claim betting profitability. The exact per-year certified race inventory is still an unverified metadata detail; resolving it cannot by itself create an untouched holdout among the established years.

A future reopening requires a genuinely unexposed evaluation population plus a frozen hypothesis/features and provenance-compliant runner-level scored artifacts, with independent approval before training. Historical data remains useful for training and development, but cannot retroactively create an untouched confirmation window.
