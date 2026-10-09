# EDGEiQ V2 — Independent Grok Review Gate (2026-10-09)

## Request to Grok
Review independently. Challenge ChatGPT's conclusions and choose exactly one next non-model experiment or a justified STOP. Do not merely agree. Provide verdict, risks, required test, pass/stop criteria, and whether historical performance rating should be parked. Please write your review to `ai_review/GROK_REVIEW.md` on branch `research/profitability-program-20261004` if you have GitHub write access; otherwise provide the full review for the user to paste back to ChatGPT.

## Governance
2025–2026 sealed; no reading outcomes from those years. No market/SP features or SP-based selection. No fuzzy horse joins. No production writes. Stage011 remains champion. Stage016 unpromoted. No model training until identity and point-in-time integrity established. Note the official runs master contains an `sp` column, but audit scripts do not consume it.

## Completed GitHub runs
- Stage037B: https://github.com/trentluckhurst1-create/edgeiq-platform/actions/runs/37876595085 — 14,640 pre-2025 rating rows, 100% exact normalized name+race_date hit in official runs master; zero name-to-horse_key collisions among 1,168 names. `horse_key` is NOT `canonical_horse_id`.
- Stage038: https://github.com/trentluckhurst1-create/edgeiq-platform/actions/runs/37876742222 — all 14,640 rating rows match exactly one master row; zero duplicate keys or ambiguous join rows.
- Stage039: https://github.com/trentluckhurst1-create/edgeiq-platform/actions/runs/37877288467 — zero formula replay mismatches, 14,640 official runs, zero trials/jumpouts. Builder `scripts/build_edgeiq_historical_performance_rating_v1.py` calculates a class-independent rating from finish position, beaten margin, and field size. This is a POST-RACE observation; must only be used strictly earlier than prediction date.
- Stage040: https://github.com/trentluckhurst1-create/edgeiq-platform/actions/runs/37877361727 — strictly earlier-date rating features construct correctly within rating population: 14,640 rows, 1,168 horses, 13,472 with prior history, no same-day duplicates, zero detected first-observation leak. NOT YET validated against model runners.
- Stage041: https://github.com/trentluckhurst1-create/edgeiq-platform/actions/runs/37877494081 — V2 Stage006 warehouse has 91,434 pre-2025 rows and fields `_race`, `_horse`, `race_date` but NO horse name; no exact join to rating source.
- Stage042: https://github.com/trentluckhurst1-create/edgeiq-platform/actions/runs/37877640708 — V2 warehouse `_horse` sample `EIQ_HORSE_000D1DE904D9A5DB`, official master `horse_key` sample `ABATEDBREATH`; cannot assume equivalent. Canonical master and alias files absent on runner. Historical bridge 204 rows (current/historical canonical names/IDs); current crosswalk 114; RA↔RCom bridge 114. NO certified mapping from `_horse` to official `horse_key` established.

## Core question
Is there an authoritative, exact, collision-free mapping from Stage006 warehouse `_horse` (EIQ_HORSE hash IDs) to official master `horse_key` / historical rating horse names? If not, park this rating family rather than introduce name-only inference or hand-built identity assumptions.

## Potential methodological risk
The recovered historical rating is a deterministic nonlinear summary of finish position, beaten margin and field size, while Stage011 already has margin and clean placing features. Even a perfect bridge might offer little new signal. Stage040 proves a local date-shift construction, not a full end-to-end PIT join. Coverage may be sparse and selected (1,168 horses in ratings versus broad V2 universe).

## Ask for your judgement
1. Should we stop this rating family now because the V2 warehouse has no name and canonical master/alias are absent, or run ONE bounded source-level `_horse` derivation and exact crosswalk audit?
2. What are quantitative PASS/STOP criteria, including coverage and collision threshold, for that audit?
3. Is the performance rating worth a predeclared challenger once identity is certified, given feature redundancy?
4. Is there a more promising scientific next step than spending time on this sparse family? Provide one concrete experiment, not a search.
