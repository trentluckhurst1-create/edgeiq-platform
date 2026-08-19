# BETA-001 — Form Guide Workspace
Status: LOCKED
Version: 1.0

## Purpose
Answers: **What has each horse actually done, and how relevant is that evidence to today’s race?** Recent Form is the hero.

## Governing rules
Inherits MASTER-001. Do not reinterpret approved hierarchy, columns, alignment, colour semantics or data ownership.


## Structure
1. Race header/selector
2. Field table
3. Runner identity/current metrics
4. Career/conditions profile
5. Recent Form — last 8 starts, full width
6. EDGEiQ Key Insights — full width

## Field table
Exact order:
`NO | SILKS | LAST 5 | HORSE | TRAINER | JOCKEY | WT | BAR | DAYS | EPI | EARLY SPEED | LATE SPEED | SUITABILITY | FORM MOMENTUM | MARKET | EDGEiQ PRICE`
Remove Race Shape. Late Speed immediately follows Early Speed. LAST 5 is compact. Horse/trainer/jockey left aligned; other compact fields centred. Plain values, no vertical dividers or blocks. Scratchings visible, faded, horse struck through, `SCRATCHED` clear. Horse click smooth-scrolls to dossier.

## Runner header/current metrics
Silks, horse, age/sex, breeding, trainer, jockey, barrier, weight.
Metrics: `EPI | Race Rank | Field Average | Difference | Suitability | Form Momentum`.
Scratchings excluded from active-field rank/average.

## Career/conditions profile
Panels: `Track | Distance | Track/Distance | Going | Class | Preparation`.
Every exact current-race match highlights using pale blue background, blue border and dark blue text. This means relevant, not positive.

## Recent Form
Header `RECENT FORM`; subtitle `Last 8 Starts`; largest full-width section.
Exact columns:
`DATE | TRACK | DIST | COND | POS | CLASS | MARGIN | WT | JOCKEY | BAR | SP | ERI | EPI | 8–6 | 6–4 | 4–2 | 2–F`
CLASS between POS and MARGIN. ERI = race strength. Sectionals in benchmark lengths; negative green, positive red, zero neutral.

## Insights
Full width below Recent Form. Supported groups only: Positive Evidence, Queries/Risks, Hidden Angles, Pattern Notes, Tempo & Map View, Value Assessment, Key Statistic. No filler or tips.

## Files to inspect
`RaceFormGuideWorkspace.tsx`, `formGuideNormaliser.ts`, `formGuideEnrichedFeed.ts`, `build_edgeiq_form_guide_enriched_v2.py`, `edgeiqOsV2.css`.

## Acceptance
Exact columns; recent form dominant; last eight starts; CLASS/ERI present; all current-condition matches highlighted; benchmark signs correct; coverage preserved.
