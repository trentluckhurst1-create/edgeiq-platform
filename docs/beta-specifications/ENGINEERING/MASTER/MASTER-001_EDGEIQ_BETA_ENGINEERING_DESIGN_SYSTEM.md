# MASTER-001 EDGEiQ Beta Engineering Design System

## Document Control
- Specification ID: MASTER-001
- Version: V1
- Status: Canonical design-system and engineering-governance authority
- Last Updated: 2026-07-12
- Audit: scripts/audit_edgeiq_engineering_specification_library_v1.py

## Product Identity
EDGEiQ is professional racing intelligence software for racing people. It is not a tipping product, bookmaker interface, stock-market dashboard, exchange-trading terminal, generic admin template, card collection or widget dashboard. It augments the analyst. Evidence comes before synthesis.

## Source Of Truth Order
1. Explicit locked requirements in active task instructions.
2. Current mounted application architecture and imports.
3. Current canonical builders, services and data contracts.
4. Existing passing audits.
5. Current rendered screenshots and visual-audit captures.
6. Earlier product specification documents as supporting context only.

## Current Repository Trace
Active shell, race, meeting, form, MAP, results, weather, service and style paths inspected for this recovery:
- `src/edgeiq-os/shell/EdgeiqOsShell.tsx`
- `src/components/shell/edgeiqOsShell.css`
- `src/edgeiq-os/race/RaceFileV3.tsx`
- `src/edgeiq-os/race/components/AppNavigation.tsx`
- `src/edgeiq-os/race/components/MeetingsWorkspace.tsx`
- `src/edgeiq-os/race/components/MeetingWorkspace.tsx`
- `src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx`
- `src/edgeiq-os/race/components/MapWorkspace.tsx`
- `src/edgeiq-os/race/components/ResultsWorkspace.tsx`
- `src/edgeiq-os/race/services/threeDayCatalog.ts`
- `src/edgeiq-os/race/services/formGuideNormaliser.ts`
- `src/edgeiq-os/race/services/formGuideEnrichedFeed.ts`
- `src/edgeiq-os/services/race-file-v2.ts`
- `src/edgeiq-os/services/live-race-data-snapshot.ts`
- `src/edgeiq-os/services/weather/EdgeiqWeatherService.ts`
- `src/edgeiq-os/styles/edgeiqOsV2.css`
- `src/edgeiq-os/design-system/edgeiqDesignSystem.css`

## Global Colours
Canvas #F4F6F9. Primary surface #FFFFFF. Secondary surface #FAFBFC. Optional subtle surface #F7F9FC. Primary blue #1F5FD6. Blue hover #184FB5. Blue active #1546A5. Primary text #1A1A1A. Secondary text #5C6675. Muted text #7C8798. Border #E5E8EE. Stronger subtle border #D7DCE5. Green is objective positive or faster-than-benchmark only. Amber is caution or moderate evidence only. Red is objective negative, slower-than-benchmark or operational risk only. No gradients. No glow. No dark terminal panels. No excessive shadows. No decorative winner colours. No stars. No medals. No marketing hero text.

## Typography
Use one canonical application font family inherited from active app CSS. Page title 26-28px 600. Workspace title 20-22px 600. Section title 14-16px 600. Table header 11-12px 600. Table body 13-14px 400-500. Supporting text 12-13px. Normal table values share font family, base size, colour and line height unless an explicit exception exists.

## Table Standard
No visible vertical dividers. Subtle horizontal separators. Horse, trainer and jockey may be left aligned. Numeric, compact and status columns centred. Header alignment matches cell alignment. No ordinary numeric values in blocks, circles or pills. No alternating zebra striping except an approved extremely subtle treatment. Controlled horizontal scrolling on narrow screens. Do not convert desktop analytical tables into oversized cards.

## Benchmark Sectional Standard
Primary sectional display uses lengths versus governed EDGEiQ benchmark standard times. Negative means inside standard, better, faster and green. Positive means outside standard, slower and red. Zero or governed tolerance is neutral. Raw seconds may be shown only through tooltip, drill-down or audit data. Never reverse the sign convention.

## Common Missing-Data Rule
Missing evidence remains null, blank, unavailable or pending trusted feed. Never convert missing evidence to zero, average, neutral, unknown placement, default narrative or fabricated figure.

## React Intelligence Prohibition
React is display-only for racing intelligence. Builders own EPI, ERI, ESI, suitability, form momentum, speed, map positions, sectionals, market edge, insight confidence and narrative evidence. Services and normalisers own parsing and view-model shaping. Components own selection, hover, focus, local expansion, sort/filter/search UI state and navigation events only.

## Component Contract Standard
Every active or proposed component must document component name, expected file path, parent component, child components, responsibility, props, TypeScript types, owned state, unowned state, events emitted, data consumed, null/loading/error behaviour, keyboard behaviour, accessibility labels, responsive behaviour and test requirements.

## Canonical Data Lineage Standard
Every canonical value must document source builder, generated output, service/normaliser, view-model property, React rendering location and audit ownership. Data-lineage tables are mandatory in every workspace spec.

## Accessibility Standard
Use semantic HTML tables for tabular data unless an ARIA grid is required by interaction. Icon-only controls require labels. Colour coding must be paired with text, sign or accessible status. Keyboard focus must be visible. Hover cards require keyboard/focus equivalents.

## Performance Standard
React must load terminal feeds only, never warehouse-scale CSV. Any frontend parser seeing more than 10,000 rows must warn and reject setting React state. The system favours dense scan-first screens over decorative panels.

## Prohibited UI and Language
No tips, selections, bets, watch/avoid recommendations, exchange ladder, order-book styling, stock-market metaphors, stars, medals, decorative winner colours, raw sectional times as primary display, unsupported AI filler, fabricated unknown placement or model-internal jargon.

## Workspace Governance Matrix
| ID | Workspace | Canonical Spec | Primary Question |
| --- | --- | --- | --- |
| BETA-001 | FORM GUIDE | `docs/beta-specifications/ENGINEERING/WORKSPACES/BETA-001_FORM_GUIDE_ENGINEERING.md` | What has each horse actually done, and how relevant is that evidence to today's race? |
| BETA-002 | MEETINGS | `docs/beta-specifications/ENGINEERING/WORKSPACES/BETA-002_MEETINGS_ENGINEERING.md` | Where should the analyst be looking today? |
| BETA-003 | MEETING DETAIL | `docs/beta-specifications/ENGINEERING/WORKSPACES/BETA-003_MEETING_DETAIL_ENGINEERING.md` | Keep selected meeting context stable across races, scratchings, gear, track, weather and results. |
| BETA-004 | SCRATCHINGS | `docs/beta-specifications/ENGINEERING/WORKSPACES/BETA-004_SCRATCHINGS_ENGINEERING.md` | Show official scratchings and governed field impact without calculating barriers in React. |
| BETA-005 | GEAR CHANGES | `docs/beta-specifications/ENGINEERING/WORKSPACES/BETA-005_GEAR_CHANGES_ENGINEERING.md` | Show official gear changes in racing language while preserving official distinctions. |
| BETA-006 | TRACK | `docs/beta-specifications/ENGINEERING/WORKSPACES/BETA-006_TRACK_ENGINEERING.md` | Explain official track, rail, physical profile and governed track-pattern analysis. |
| BETA-007 | WEATHER | `docs/beta-specifications/ENGINEERING/WORKSPACES/BETA-007_WEATHER_ENGINEERING.md` | Show meeting weather facts and builder-owned race-day impact without radar or confidence scoring. |
| BETA-008 | RESULTS | `docs/beta-specifications/ENGINEERING/WORKSPACES/BETA-008_RESULTS_ENGINEERING.md` | Show official results, governed performance ratings and benchmark sectionals after completion. |
| BETA-009 | MAP | `docs/beta-specifications/ENGINEERING/WORKSPACES/BETA-009_MAP_ENGINEERING.md` | Project early positioning from barriers and governed early-speed evidence; it is not a track diagram. |
| BETA-010 | MARKET | `docs/beta-specifications/ENGINEERING/WORKSPACES/BETA-010_MARKET_ENGINEERING.md` | Show governed market movement and EDGEiQ price context without exchange ladder or betting action language. |
| BETA-011 | OVERVIEW | `docs/beta-specifications/ENGINEERING/WORKSPACES/BETA-011_OVERVIEW_ENGINEERING.md` | Provide the complete supported race picture without tips, guarantees or unsupported populated fields. |
| BETA-012 | INSIGHTS | `docs/beta-specifications/ENGINEERING/WORKSPACES/BETA-012_INSIGHTS_ENGINEERING.md` | Surface governed insights with source, timestamp, coverage and evidence-quality confidence. |
| BETA-013 | EPI WORKSPACE | `docs/beta-specifications/ENGINEERING/WORKSPACES/BETA-013_EPI_WORKSPACE_ENGINEERING.md` | Show each runner previous EPI ratings across up to 10 official starts in historical race-strength context. |

## BETA-001 FORM GUIDE Locked Summary
Purpose: What has each horse actually done, and how relevant is that evidence to today's race?

Primary columns/structure: `NO|SILKS|LAST 5|HORSE|TRAINER|JOCKEY|WT|BAR|DAYS|EPI|EARLY SPEED|LATE SPEED|SUITABILITY|FORM MOMENTUM|MARKET|EDGEiQ PRICE`

Locked notes: Race Shape must not appear in the field table. Late Speed must immediately follow Early Speed. Recent Form columns are DATE, TRACK, DIST, COND, POS, CLASS, MARGIN, WT, JOCKEY, BAR, SP, ERI, EPI, 8-6, 6-4, 4-2, 2-F. Current-race match highlights include Track, Distance, Track/Distance, Going, Class and Preparation. Scratched runners remain visible with reduced opacity and horse-name strike-through.

## BETA-002 MEETINGS Locked Summary
Purpose: Where should the analyst be looking today?

Primary columns/structure: `SELECT|MEETING|STATE|RAIL|TRACK|WEATHER|WIND|TEMP|RACES|DECLARED|SCRATCHINGS|FIRST|LAST|STATUS|EDGEiQ READ|OPEN`

Locked notes: TODAY, TOMORROW and DAY +2 come from public/data/edgeiq_three_day_window_v1.json. React must not calculate dates. EDGEiQ READ is maximum three short governed evidence phrases. Desktop split is approximately 82 percent main and 18 percent rail with a 16px gap.

## BETA-003 MEETING DETAIL Locked Summary
Purpose: Keep selected meeting context stable across races, scratchings, gear, track, weather and results.

Primary columns/structure: `RACE|TIME|DISTANCE|CLASS|RACE NAME|RESTRICTION|FIELD SIZE|STATUS|OPEN`

Locked notes: Persistent header fields are Meeting title, Date, Status, Race count, First race, Last race and Last update. Persistent condition strip fields are Track, Rail, Weather, Wind, Temperature, Rain 24h, Irrigation 24h and Official Update. Exact tab order is RACES, SCRATCHINGS, GEAR CHANGES, TRACK, WEATHER, RESULTS.

## BETA-004 SCRATCHINGS Locked Summary
Purpose: Show official scratchings and governed field impact without calculating barriers in React.

Primary columns/structure: `RACE|NO|SILK|HORSE|TRAINER|JOCKEY|SCRATCHED AT|REASON|SOURCE|STATUS`

Locked notes: Summary shows Total Scratchings, Races Affected, New Since time, Fields Materially Changed, Emergencies Promoted and Latest Update. Original barrier is immutable. Effective barrier after inside scratchings is builder-owned.

## BETA-005 GEAR CHANGES Locked Summary
Purpose: Show official gear changes in racing language while preserving official distinctions.

Primary columns/structure: `RACE|NO|SILK|HORSE|CHANGE|PREVIOUS|TODAY|FIRST TIME|COMMENT|SOURCE`

Locked notes: Filters are All races, All changes, All status and Search horse/change. Preserve first time, again, on, off, reapplied, removed, pre-race only and gelded. Do not flatten terminology.

## BETA-006 TRACK Locked Summary
Purpose: Explain official track, rail, physical profile and governed track-pattern analysis.

Primary columns/structure: `METRIC|TODAY|LAST 3 MEETINGS|LAST 10 MEETINGS`

Locked notes: Official fields include Official Rating, Inspection Time, Going Stick, Penetrometer Average, Moisture, Rain 24h, Rain 7d, Irrigation 24h, Irrigation 7d and Track Manager. Remove Track Record and Class Record. Use Track Pattern Analysis, not Track Bias as primary heading.

## BETA-007 WEATHER Locked Summary
Purpose: Show meeting weather facts and builder-owned race-day impact without radar or confidence scoring.

Primary columns/structure: `TIME|WEATHER|TEMP (C)|WIND (km/h)|GUSTS (km/h)|RAIN PROB.|RAIN (mm)`

Locked notes: Remove Radar, radar image, radar snapshot, radar link, Forecast Confidence, confidence bars and confidence scoring. Unavailable state is: Official weather data is not currently available for this meeting.

## BETA-008 RESULTS Locked Summary
Purpose: Show official results, governed performance ratings and benchmark sectionals after completion.

Primary columns/structure: `RACE|TIME|WINNER|JOCKEY|TRAINER|SP (TAB)|MARGIN|TIME|TRACK|STATUS|OPEN`

Locked notes: Runner Performance identity columns are NO, HORSE, JOCKEY, BAR, WT, SP, FINISH, MARGIN, then benchmark sectional columns, then EPI and ERI. Remove Race Replay, EPI versus SP and Race Tempo visual. Benchmark sectionals are lengths: negative green, positive red, zero neutral.

## BETA-009 MAP Locked Summary
Purpose: Project early positioning from barriers and governed early-speed evidence; it is not a track diagram.

Primary columns/structure: `NO|HORSE|BARRIER|EFFECTIVE BARRIER|RUN STYLE|EARLY SPEED|PROJECTED POSITION`

Locked notes: Victorian right-to-left. Barriers on the right. Barrier 1 bottom. Highest effective barrier top. No racing-direction arrow. No barrier-group names. Every runner line begins exactly at effective barrier. All lines use EDGEiQ blue.

## BETA-010 MARKET Locked Summary
Purpose: Show governed market movement and EDGEiQ price context without exchange ladder or betting action language.

Primary columns/structure: `NO|HORSE|EPI|MARKET|OPEN|HIGH|LOW|MOVE|EDGEiQ PRICE|EDGE|STATUS`

Locked notes: Remove Back, Lay, exchange ladder and order-book styling. EDGE compares governed market price with governed EDGEiQ Price. No EPI-to-price comparison calculation.

## BETA-011 OVERVIEW Locked Summary
Purpose: Provide the complete supported race picture without tips, guarantees or unsupported populated fields.

Primary columns/structure: `SECTION|EVIDENCE|SOURCE|STATUS|OPEN`

Locked notes: Full-width structure is Race Environment, MAP / Race Shape, Field Intelligence, EDGEiQ Race Read, Key Race Questions and Operational / Data State. Links preserve race context.

## BETA-012 INSIGHTS Locked Summary
Purpose: Surface governed insights with source, timestamp, coverage and evidence-quality confidence.

Primary columns/structure: `NO|HORSE|KEY INSIGHT|EDGE|CONFIDENCE`

Locked notes: Top cards are Key Insight, Best Rated Runner, Value Insight, Market Riser and Race Setup. Confidence means evidence quality, not winning chance. No betting recommendations or generic AI filler.

## BETA-013 EPI WORKSPACE Locked Summary
Purpose: Show each runner previous EPI ratings across up to 10 official starts in historical race-strength context.

Primary columns/structure: `NO|HORSE|CURRENT EPI|RANK|FIELD AVG|DIFF|START 10|START 9|START 8|START 7|START 6|START 5|START 4|START 3|START 2|START 1`

Locked notes: Hover card fields include Date, Track, Meeting / Race, Distance, Class, Condition, Barrier, Weight, Jockey, Trainer, Finish, Margin, SP, EPI, ERI, 8-6, 6-4, 4-2, 2-F, Source and Version. Missing starts are blank neutral cells, never zero. React must not calculate averages, peak, trend or tile class.

## Master Governance Detail 1
This detail binds the design-system rules to every future implementation. The implementer must verify source-of-truth order, active file paths, light design tokens, benchmark sectional sign convention, missing-data handling, React display-only boundary, table alignment, accessibility, visual regression captures and audit output before claiming completion. This is not an optional style preference; it is the system contract for EDGEiQ Beta engineering.

## Master Governance Detail 2
This detail binds the design-system rules to every future implementation. The implementer must verify source-of-truth order, active file paths, light design tokens, benchmark sectional sign convention, missing-data handling, React display-only boundary, table alignment, accessibility, visual regression captures and audit output before claiming completion. This is not an optional style preference; it is the system contract for EDGEiQ Beta engineering.

## Master Governance Detail 3
This detail binds the design-system rules to every future implementation. The implementer must verify source-of-truth order, active file paths, light design tokens, benchmark sectional sign convention, missing-data handling, React display-only boundary, table alignment, accessibility, visual regression captures and audit output before claiming completion. This is not an optional style preference; it is the system contract for EDGEiQ Beta engineering.

## Master Governance Detail 4
This detail binds the design-system rules to every future implementation. The implementer must verify source-of-truth order, active file paths, light design tokens, benchmark sectional sign convention, missing-data handling, React display-only boundary, table alignment, accessibility, visual regression captures and audit output before claiming completion. This is not an optional style preference; it is the system contract for EDGEiQ Beta engineering.

## Master Governance Detail 5
This detail binds the design-system rules to every future implementation. The implementer must verify source-of-truth order, active file paths, light design tokens, benchmark sectional sign convention, missing-data handling, React display-only boundary, table alignment, accessibility, visual regression captures and audit output before claiming completion. This is not an optional style preference; it is the system contract for EDGEiQ Beta engineering.

## Master Governance Detail 6
This detail binds the design-system rules to every future implementation. The implementer must verify source-of-truth order, active file paths, light design tokens, benchmark sectional sign convention, missing-data handling, React display-only boundary, table alignment, accessibility, visual regression captures and audit output before claiming completion. This is not an optional style preference; it is the system contract for EDGEiQ Beta engineering.

## Master Governance Detail 7
This detail binds the design-system rules to every future implementation. The implementer must verify source-of-truth order, active file paths, light design tokens, benchmark sectional sign convention, missing-data handling, React display-only boundary, table alignment, accessibility, visual regression captures and audit output before claiming completion. This is not an optional style preference; it is the system contract for EDGEiQ Beta engineering.

## Master Governance Detail 8
This detail binds the design-system rules to every future implementation. The implementer must verify source-of-truth order, active file paths, light design tokens, benchmark sectional sign convention, missing-data handling, React display-only boundary, table alignment, accessibility, visual regression captures and audit output before claiming completion. This is not an optional style preference; it is the system contract for EDGEiQ Beta engineering.

## Master Governance Detail 9
This detail binds the design-system rules to every future implementation. The implementer must verify source-of-truth order, active file paths, light design tokens, benchmark sectional sign convention, missing-data handling, React display-only boundary, table alignment, accessibility, visual regression captures and audit output before claiming completion. This is not an optional style preference; it is the system contract for EDGEiQ Beta engineering.

## Master Governance Detail 10
This detail binds the design-system rules to every future implementation. The implementer must verify source-of-truth order, active file paths, light design tokens, benchmark sectional sign convention, missing-data handling, React display-only boundary, table alignment, accessibility, visual regression captures and audit output before claiming completion. This is not an optional style preference; it is the system contract for EDGEiQ Beta engineering.

## Master Governance Detail 11
This detail binds the design-system rules to every future implementation. The implementer must verify source-of-truth order, active file paths, light design tokens, benchmark sectional sign convention, missing-data handling, React display-only boundary, table alignment, accessibility, visual regression captures and audit output before claiming completion. This is not an optional style preference; it is the system contract for EDGEiQ Beta engineering.

## Master Governance Detail 12
This detail binds the design-system rules to every future implementation. The implementer must verify source-of-truth order, active file paths, light design tokens, benchmark sectional sign convention, missing-data handling, React display-only boundary, table alignment, accessibility, visual regression captures and audit output before claiming completion. This is not an optional style preference; it is the system contract for EDGEiQ Beta engineering.

## Master Governance Detail 13
This detail binds the design-system rules to every future implementation. The implementer must verify source-of-truth order, active file paths, light design tokens, benchmark sectional sign convention, missing-data handling, React display-only boundary, table alignment, accessibility, visual regression captures and audit output before claiming completion. This is not an optional style preference; it is the system contract for EDGEiQ Beta engineering.

## Master Governance Detail 14
This detail binds the design-system rules to every future implementation. The implementer must verify source-of-truth order, active file paths, light design tokens, benchmark sectional sign convention, missing-data handling, React display-only boundary, table alignment, accessibility, visual regression captures and audit output before claiming completion. This is not an optional style preference; it is the system contract for EDGEiQ Beta engineering.

## Master Governance Detail 15
This detail binds the design-system rules to every future implementation. The implementer must verify source-of-truth order, active file paths, light design tokens, benchmark sectional sign convention, missing-data handling, React display-only boundary, table alignment, accessibility, visual regression captures and audit output before claiming completion. This is not an optional style preference; it is the system contract for EDGEiQ Beta engineering.

## Master Governance Detail 16
This detail binds the design-system rules to every future implementation. The implementer must verify source-of-truth order, active file paths, light design tokens, benchmark sectional sign convention, missing-data handling, React display-only boundary, table alignment, accessibility, visual regression captures and audit output before claiming completion. This is not an optional style preference; it is the system contract for EDGEiQ Beta engineering.

## Master Governance Detail 17
This detail binds the design-system rules to every future implementation. The implementer must verify source-of-truth order, active file paths, light design tokens, benchmark sectional sign convention, missing-data handling, React display-only boundary, table alignment, accessibility, visual regression captures and audit output before claiming completion. This is not an optional style preference; it is the system contract for EDGEiQ Beta engineering.

## Master Governance Detail 18
This detail binds the design-system rules to every future implementation. The implementer must verify source-of-truth order, active file paths, light design tokens, benchmark sectional sign convention, missing-data handling, React display-only boundary, table alignment, accessibility, visual regression captures and audit output before claiming completion. This is not an optional style preference; it is the system contract for EDGEiQ Beta engineering.

## Master Governance Detail 19
This detail binds the design-system rules to every future implementation. The implementer must verify source-of-truth order, active file paths, light design tokens, benchmark sectional sign convention, missing-data handling, React display-only boundary, table alignment, accessibility, visual regression captures and audit output before claiming completion. This is not an optional style preference; it is the system contract for EDGEiQ Beta engineering.

## Master Governance Detail 20
This detail binds the design-system rules to every future implementation. The implementer must verify source-of-truth order, active file paths, light design tokens, benchmark sectional sign convention, missing-data handling, React display-only boundary, table alignment, accessibility, visual regression captures and audit output before claiming completion. This is not an optional style preference; it is the system contract for EDGEiQ Beta engineering.

## Master Governance Detail 21
This detail binds the design-system rules to every future implementation. The implementer must verify source-of-truth order, active file paths, light design tokens, benchmark sectional sign convention, missing-data handling, React display-only boundary, table alignment, accessibility, visual regression captures and audit output before claiming completion. This is not an optional style preference; it is the system contract for EDGEiQ Beta engineering.

## Master Governance Detail 22
This detail binds the design-system rules to every future implementation. The implementer must verify source-of-truth order, active file paths, light design tokens, benchmark sectional sign convention, missing-data handling, React display-only boundary, table alignment, accessibility, visual regression captures and audit output before claiming completion. This is not an optional style preference; it is the system contract for EDGEiQ Beta engineering.

## Master Governance Detail 23
This detail binds the design-system rules to every future implementation. The implementer must verify source-of-truth order, active file paths, light design tokens, benchmark sectional sign convention, missing-data handling, React display-only boundary, table alignment, accessibility, visual regression captures and audit output before claiming completion. This is not an optional style preference; it is the system contract for EDGEiQ Beta engineering.
