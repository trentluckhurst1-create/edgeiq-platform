# SPEC-009
# EDGEIQ RESULTS
## PRODUCT ENGINEERING SPECIFICATION
### VERSION 1.0
### STATUS LOCKED

---

# 1. PURPOSE

The Results Workspace is the official post-race intelligence workspace for EDGEIQ.

It combines the official race result with EDGEIQ performance intelligence after the race has been completed.

This workspace is not a replay page.

It is the permanent historical record of every race.

Official information always remains unchanged.

EDGEIQ intelligence is layered on top.

---

# 2. PRODUCT PHILOSOPHY

Results are evidence.

Not selections.

Not betting advice.

The Results Workspace allows analysts to understand

• What happened

• Why it happened

• How strong the race was

• How every runner performed

• How the race compares historically

Everything is evidence driven.

---

# 3. USER GOALS

Immediately understand

• Official finishing order

• Margins

• Starting Prices

• Runner Performance

• Benchmark Sectionals

• EPI

• ERI

• Stewards Comments

without leaving EDGEIQ.

---

# 4. WORKSPACE LAYOUT

----------------------------------------------------

HEADER

----------------------------------------------------

MEETING RESULTS

----------------------------------------------------

EXPANDABLE RACE RESULTS

----------------------------------------------------

RUNNER PERFORMANCE

----------------------------------------------------

STEWARDS COMMENTS

----------------------------------------------------

---

# 5. HEADER

Displays

Meeting

↓

Track

↓

Date

↓

Completed Races

↓

Meeting Status

↓

Last Updated

Background

FFFFFF

Border Bottom

1px solid #E5E8EE

Height

72px

---

# 6. MEETING RESULTS TABLE

Purpose

Provide a complete summary of every race in the meeting.

One row

One race.

Rows expand into the Individual Race Results workspace.

---

LOCKED COLUMN ORDER

RACE

TIME

WINNER

SECOND

THIRD

MARGIN

STATUS

OPEN

This order is frozen.

---

# 7. INDIVIDUAL RACE RESULTS

Selecting OPEN expands the race.

Displays

Official Finishing Order

↓

Horse

↓

Barrier

↓

Weight

↓

Jockey

↓

Trainer

↓

Official Margin

↓

Official Starting Price

↓

Stewards Comments (when available)

↓

Runner Performance

Race Replay is intentionally excluded.

Race Tempo is intentionally excluded.

EPI v SP is intentionally excluded.

---

END OF PART 1


---

# 8. RUNNER PERFORMANCE

## Purpose

Runner Performance is the hero component of the Results Workspace.

Its purpose is to explain how every horse performed relative to today's race.

This section occupies the largest amount of space within the expanded race.

It is the primary analytical component after the official result.

---

## Layout

Full Width

100%

Minimum Height

520px

Preferred Height

620px

Background

FFFFFF

Border

1px solid #E5E8EE

Border Radius

8px

---

## Locked Column Order

POS

NO

HORSE

BARRIER

WT

JOCKEY

TRAINER

MARGIN

EPI

ERI

8-6

6-4

4-2

2-F

This order is frozen.

---

# 9. BENCHMARK SECTIONALS

Sectionals are displayed in

Lengths

NOT

Seconds

Examples

-3.2

Inside benchmark

+1.8

Outside benchmark

0.0

On benchmark

---

## Colour Rules

Negative

Green

Positive

Red

Zero

Neutral Grey

Raw seconds remain available only through future drill-down functionality.

---

# 10. EDGEIQ PERFORMANCE INDEX (EPI)

Purpose

Display each runner's post-race EDGEIQ Performance Index.

EPI is calculated automatically once official sectional data becomes available.

Display

Single decimal place

No sparklines

No arrows

No prediction

No React calculations.

---

# 11. EDGEIQ RACE INDEX (ERI)

Purpose

Display the historical strength of the completed race.

ERI is calculated automatically.

One value per race.

Displayed for every runner in that race.

Single decimal place.

---

# 12. AUTOMATIC ENRICHMENT

The Results Workspace begins with official racing information.

As additional governed data becomes available, the workspace enriches automatically.

Sequence

Official Result

↓

Official Margins

↓

Official Starting Prices

↓

Official Stewards Comments

↓

Official Sectionals

↓

EPI Calculation

↓

ERI Calculation

↓

Benchmark Lengths

No manual refresh required.

React responds only to updated governed data.

---

# 13. STEWARDS COMMENTS

Purpose

Display the official stewards report for each runner.

Stewards comments are automatically loaded when officially published.

Expected timing

Typically within 90 minutes of the final race.

Display

Runner

↓

Official Comment

↓

Publication Time

↓

Source

No generated commentary.

No summaries.

Official text only.

---

# 14. REMOVED COMPONENTS

The following components are permanently excluded.

Race Replay

Race Tempo

EPI v SP

Betting Recommendations

Selections

These do not form part of the EDGEIQ Results specification.

---

END OF PART 2


---

# 15. DATA GOVERNANCE

## React Responsibilities

React is responsible for

Display

Sort

Filter

Search

Expand

Collapse

Navigate

Highlight

Responsive Layout

React MUST NEVER

Calculate EPI

Calculate ERI

Calculate Benchmark Sectionals

Calculate Margins

Interpret Stewards Comments

Generate Intelligence

Modify Official Results

Official information is immutable.

EDGEIQ intelligence is layered on top.

---

## Builder Responsibilities

Canonical builders produce

Official Results

Official Margins

Official Starting Prices

Official Scratchings

Official Stewards Comments

Official Sectionals

EPI

ERI

Benchmark Lengths

Coverage Reports

Builder Versions

Audit Reports

Builder output is the single source of truth.

---

# 16. DATA QUALITY

Every result record exposes

Official Source

↓

Builder Version

↓

Coverage

↓

Timestamp

↓

Audit Status

↓

Feed Health

Unavailable values display

Unavailable

Never estimated.

Never inferred.

---

# 17. DESIGN SYSTEM COMPLIANCE

Background

FFFFFF

Surface

FFFFFF

Secondary Surface

FAFBFC

Border

E5E8EE

Primary Accent

EDGEIQ Blue

Primary Text

1A1A1A

Secondary Text

5C6675

Positive Benchmark

Green

Negative Benchmark

Red

Neutral Benchmark

Grey

No gradients.

No decorative winner colours.

No oversized graphics.

Professional software presentation only.

---

# 18. RESPONSIVE BEHAVIOUR

Desktop

Primary target.

Runner Performance occupies full width.

Laptop

Reduce spacing only.

Tablet

Runner Performance stacks beneath Official Results.

Mobile

Not supported during Beta.

---

# 19. PERFORMANCE TARGETS

Workspace Load

<300ms

Expand Race

<100ms

Runner Performance Refresh

<100ms

Official Enrichment Refresh

Automatic

Hover

Immediate

Search

Instant

No unnecessary React re-rendering.

---

# 20. ACCESSIBILITY

Keyboard Navigation

Supported

Focus Indicators

Visible

Contrast

WCAG AA

Benchmark colours must never be the only indicator.

All performance values remain readable without colour.

---

# 21. FUTURE EXPANSION

Reserved

Replay Synchronisation

↓

Stride Metrics

↓

Sectional Graphs

↓

Video Timeline

↓

GPS Tracking

↓

Running Line Analysis

↓

Veterinary Reports

↓

Official Objections

↓

Protests

↓

Photo Finish Images

These modules extend the workspace.

They never redesign it.

---

# 22. ACCEPTANCE CRITERIA

Results Workspace is complete when

✓ Meeting Results table implemented

✓ Expandable Race Results implemented

✓ Runner Performance is the hero section

✓ Locked column order preserved

✓ Benchmark sectionals displayed in lengths

✓ Automatic EPI calculation supported

✓ Automatic ERI calculation supported

✓ Automatic steward report loading supported

✓ Race Replay excluded

✓ Race Tempo excluded

✓ EPI v SP excluded

✓ White EDGEIQ Design System implemented

✓ Canonical builders only

✓ npm build passes

✓ Engineering audits pass

---

# 23. CODEX IMPLEMENTATION CHECKLIST

Codex MUST

Use canonical results builders

Never calculate EPI in React

Never calculate ERI in React

Never calculate benchmark lengths in React

Implement expandable race results

Implement Runner Performance as hero

Implement benchmark-length sectionals

Implement automatic steward loading

Exclude Race Replay

Exclude Race Tempo

Exclude EPI v SP

Follow MASTER Design System

Run npm build

Run engineering audits

Capture verification screenshots

Produce implementation report

---

# 24. ENGINEERING GOVERNANCE

This specification is the canonical authority for the Results Workspace.

Any modification to

Runner Performance

Benchmark Sectionals

EPI

ERI

Official Results

Stewards Comments

Builder ownership

or

Workspace layout

requires

Specification revision

Version increment

Engineering review

Audit update

Implementation must follow this specification exactly.

---

# END OF SPECIFICATION

Specification

SPEC-009

Workspace

RESULTS

Status

LOCKED

Authority

EDGEIQ Product Engineering Specification

Revision

1.0

