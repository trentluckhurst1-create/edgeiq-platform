# BETA-001
# EDGEIQ FORM GUIDE
## PRODUCT ENGINEERING SPECIFICATION
### VERSION BETA V1
### STATUS: LOCKED

---

# 1. PURPOSE

The Form Guide is the primary analytical workspace of EDGEIQ.

This workspace exists to allow analysts to completely understand every runner in today's race.

It is designed for professional racing analysts, serious punters, syndicators and racing professionals.

EDGEIQ never replaces analysis.

EDGEIQ enhances analysis.

---

# 2. PRODUCT PHILOSOPHY

The Form Guide follows six core principles.

1. Form comes before prediction.

2. Historical evidence always precedes intelligence.

3. The analyst remains in control.

4. Every displayed value must come from governed evidence.

5. Unknown values remain unavailable.

6. The interface must resemble professional software rather than a betting website.

---

# 3. USER GOALS

The analyst should be able to answer:

• Is today's race suitable?

• Has the horse been racing well?

• Is today's market fair?

• Is the horse improving?

• Does today's class suit?

• Does today's track suit?

• Does today's distance suit?

• Does today's going suit?

without leaving the Form Guide.

---

# 4. USER JOURNEY

Meeting

↓

Race

↓

Form Guide

↓

Runner Table

↓

Select Runner

↓

Horse Profile

↓

Recent Form

↓

Historical Intelligence

↓

Next Runner

---

# 5. WORKSPACE HIERARCHY

The Form Guide contains five permanent regions.

HEADER

↓

FIELD TABLE

↓

HORSE PROFILE

↓

RECENT FORM

↓

EDGEIQ INSIGHTS

The hierarchy is fixed.

Recent Form is the hero component.

---

# 6. HEADER

Displays

Meeting

Race

Distance

Class

Track Rating

Rail

Weather

Time

Selected Runner

No intelligence appears here.

---

# 7. FIELD TABLE

LOCKED COLUMN ORDER

NO

SILKS

LAST 5

HORSE

TRAINER

JOCKEY

WT

BAR

DAYS

EPI

EARLY SPEED

LATE SPEED

SUITABILITY

FORM MOMENTUM

MARKET

EDGEIQ PRICE

This order is frozen.

---

# 8. TABLE RULES

No vertical column lines.

Subtle horizontal separators only.

White background.

No alternating row colours.

Hover

Very light EDGEIQ blue.

Selected Runner

Blue outline only.

No filled backgrounds.

Numeric values

Centre aligned.

Horse

Left aligned.

Trainer

Left aligned.

Jockey

Left aligned.

Typography

Single font family.

Uniform font size.

Uniform row height.

---

END OF PART 1

---

# 9. HORSE PROFILE

## Purpose

The Horse Profile provides a complete overview of the selected runner under today's conditions.

It must immediately answer:

• Has this horse performed under today's conditions?

• Does today's race suit?

• What profile does today's race match?

The Horse Profile is NOT intended to duplicate the Recent Form section.

It provides permanent career context.

---

## Layout

The Horse Profile spans the full workspace width.

It sits immediately beneath the Runner Field Table.

The layout consists of two horizontal regions.

LEFT

Career statistics

RIGHT

Today's Profile

No cards are stacked vertically.

The layout is fixed.

---

## Career Statistics

Display

Career

Track

Distance

Track/Distance

Class

Going

Clockwise

Anti-Clockwise

Jockey

Trainer

First Up

Second Up

Third Up

Barrier

Prize Money

Average Prize

Average Finish

Career EPI

Peak EPI

Average ERI

Every statistic is displayed using

Starts

Wins

Seconds

Thirds

Example

8:3-2-1

---

## Today's Match Highlighting

Today's conditions are automatically highlighted.

Highlight colour

EDGEIQ Blue

Background

Blue

Text

White

Border

None

The following fields participate

Track

Distance

Going

Barrier

Class

Jockey

Trainer

Track/Distance

Only matching conditions receive highlighting.

Nothing else.

---

## Highlight Priority

Highest

Track

Distance

Going

Second

Barrier

Class

Third

Trainer

Jockey

No flashing.

No animation.

---

## Profile Behaviour

Changing runner

Immediately refreshes

Horse Profile

Recent Form

EDGEIQ Insights

without refreshing the page.

Selection is instantaneous.

---

# 10. RECENT FORM

## Philosophy

Recent Form is the single most important component within the Form Guide.

It occupies the greatest amount of screen space.

Professional punters study form.

EDGEIQ respects this workflow.

---

## Header

RECENT FORM

This title is fixed.

LATEST RUN has been permanently removed.

---

## Layout

Recent Form spans

100%

of the available workspace.

No side cards.

No Today's Match panel.

No secondary widgets.

Recent Form is the hero.

---

## Locked Column Order

DATE

TRACK

DIST

POS

CLASS

MARGIN

WT

BAR

JOCKEY

TRACK

SP

8-6

6-4

4-2

2-F

ERI

---

## Column Rules

DATE

Centre

TRACK

Centre

DIST

Centre

POS

Bold

Centre

CLASS

Centre

MARGIN

Centre

WT

Centre

BAR

Centre

JOCKEY

Left

TRACK

Centre

SP

Centre

8-6

Benchmark Length

6-4

Benchmark Length

4-2

Benchmark Length

2-F

Benchmark Length

ERI

Centre

Bold

---

## Benchmark Length Rules

Sectionals are never displayed in seconds.

Display

-3.2

means

3.2 lengths inside benchmark.

Display

+2.8

means

2.8 lengths outside benchmark.

Colour Rules

Negative

Green

Positive

Red

Zero

Neutral Grey

Raw seconds remain available only through drill-down.

---

## ERI

ERI

EDGEIQ Race Index

Represents

Historical race strength.

It is NOT today's EPI.

It is NOT a speed figure.

It is the strength rating of the race.

Displayed as

Single integer.

---

END OF PART 2


---

# 11. EDGEIQ PERFORMANCE INDEX (EPI)

## Purpose

EPI is the current performance rating assigned to the runner.

It represents the horse's current ability according to the EDGEIQ intelligence engine.

EPI is the primary runner rating displayed throughout EDGEIQ.

It is not a speed figure.

It is not a market rating.

It is the canonical current performance rating.

---

## Display Rules

Display as

Single numeric value

Example

72.4

One decimal place.

No arrows.

No sparklines.

No trend icons.

No coloured backgrounds.

---

## Colour Rules

Normal

Dark Grey

Selected Runner

EDGEIQ Blue

Unavailable

Light Grey

Only exceptional values use colour.

---

## Hover

Hovering EPI displays

Current EPI

Peak Career EPI

Average Career EPI

Last Start EPI

Difference From Last Start

Last Updated

Model Version

No calculations occur in React.

---

# 12. EDGEIQ INSIGHTS

## Purpose

This component summarises the intelligence gathered for the selected runner.

It supports analysis.

It never replaces analysis.

---

## Position

Immediately beneath Recent Form.

Full width.

No side panels.

---

## Layout

Four equal insight columns.

Each contains

Heading

Evidence

Confidence

No recommendation language.

---

## Insight Categories

Current Profile

Suitability

Form Momentum

Market Position

Each insight references governed intelligence only.

---

## Language Rules

Examples

Excellent track profile.

Distance remains a query.

Returning to preferred conditions.

Market shorter than assessed price.

Late speed profile improving.

Avoid words such as

Back

Bet

Lay

Should Win

Good Thing

Best Bet

Confidence is evidence confidence only.

---

# 13. DATA CONTRACTS

React is display only.

React must never

Calculate

Average

Predict

Estimate

Infer

All values originate from canonical builders.

---

## Canonical Sources

Runner Identity

Race Fields

EPI

Early Speed

Late Speed

Suitability

Form Momentum

EDGEIQ Price

Market

Historical Form

Benchmark Sectionals

ERI

Official Results

Each source has one owner.

No duplicated intelligence.

---

# 14. BUILDER RESPONSIBILITIES

Builders produce

Validated JSON

Complete datasets

Governed calculations

Coverage reports

Audit outputs

React never changes these values.

---

# 15. REACT RESPONSIBILITIES

React

Displays

Filters

Sorts

Highlights

Expands

Collapses

Navigates

React must never

Calculate ratings

Calculate suitability

Generate insights

Predict prices

Estimate speed

Generate commentary

---

# 16. RESPONSIVE BEHAVIOUR

Desktop

Primary target.

No horizontal scrolling on standard desktop.

Laptop

Maintain full table.

Reduce spacing only.

Tablet

Allow controlled horizontal scrolling.

Mobile

Not a Beta priority.

---

# 17. PERFORMANCE

Runner switching

Target

<100ms

Expand Recent Form

<100ms

Sort table

<50ms

Hover

Immediate

No visible loading where cached.

---

# 18. ACCESSIBILITY

Minimum contrast

WCAG AA

Keyboard navigation

Supported

Hover information

Also available by keyboard focus.

Do not rely on colour alone.

---

END OF PART 3


---

# 19. USER INTERACTION SPECIFICATION

## Runner Selection

Selecting a runner updates

• Horse Profile

• Recent Form

• EDGEIQ Insights

• Highlighted Today's Profile

• Intelligence Panels

No full page refresh.

No scroll reset.

No loading spinner unless data genuinely requires retrieval.

---

## Row Hover

Hover colour

Very Light EDGEIQ Blue

Border

None

Shadow

None

Hover never changes typography.

Hover never changes row height.

---

## Sorting

Sortable Columns

Horse

Trainer

Jockey

Barrier

Weight

Days

EPI

Early Speed

Late Speed

Suitability

Form Momentum

Market

EDGEIQ Price

Default Sort

Barrier Number

Ascending

---

## Searching

Search

Horse

Trainer

Jockey

Search is instant.

Case insensitive.

Partial matching.

---

## Filtering

Future Expansion

Stable

Trainer

Jockey

Barrier

Market

Suitability

Momentum

No filtering removes canonical data.

Only display changes.

---

# 20. COMPONENT DIMENSIONS

HEADER

Height

72px

---

FIELD TABLE

Minimum Height

340px

Preferred Height

420px

Maximum Height

560px

---

HORSE PROFILE

Minimum Height

220px

Preferred

260px

---

RECENT FORM

Minimum Height

480px

Preferred

560px

This is intentionally the largest component in the workspace.

---

EDGEIQ INSIGHTS

Minimum Height

180px

Preferred

220px

---

# 21. DESIGN SYSTEM COMPLIANCE

Background

FFFFFF

Primary Surface

FFFFFF

Secondary Surface

FAFBFC

Primary Border

E5E8EE

Primary Text

1A1A1A

Secondary Text

5C6675

Primary Accent

EDGEIQ Blue

Success

Green

Failure

Red

No gradients.

No shadows beyond subtle elevation.

No glossy effects.

No coloured panels.

No black backgrounds.

---

# 22. INTELLIGENCE GOVERNANCE

React never calculates

EPI

ERI

Suitability

Form Momentum

EDGEIQ Price

Market Intelligence

Benchmark Sectionals

Race Shape

Speed

Suitability

Everything originates from governed builders.

---

# 23. ERROR HANDLING

If intelligence is unavailable

Display

Unavailable

Do NOT

Guess

Estimate

Average

Carry forward

Invent

Unknown remains Unknown.

---

# 24. DATA QUALITY

Every intelligence field must expose

Coverage

Timestamp

Version

Source

Builder

Audit

Internally available through governed services.

---

# 25. PERFORMANCE TARGETS

Workspace Load

Target

<300ms

Runner Change

<100ms

Hover

Instant

Expand Recent Form

<100ms

Search

<50ms

Sort

<50ms

No unnecessary re-rendering.

---

# 26. FUTURE EXPANSION

Reserved Areas

Historical Video

Stride Metrics

Biomechanics

Bloodlines

Sectional Charts

AI Replay

Video Synchronisation

Stewards Vision

Official Comments

Veterinary Notes

These additions must never change the existing layout hierarchy.

Only extend.

Never redesign.

---

# 27. ACCEPTANCE CRITERIA

The workspace is complete when

✓ Column order matches specification

✓ Horse Profile highlighting operates correctly

✓ Recent Form occupies full width

✓ Recent Form remains the hero component

✓ Benchmark sectionals display in lengths

✓ ERI displayed correctly

✓ EPI displayed correctly

✓ No vertical grid lines

✓ Typography consistent

✓ White EDGEIQ Beta theme

✓ Canonical builders only

✓ npm build passes

✓ All audits pass

---

# 28. CODEX IMPLEMENTATION CHECKLIST

Codex MUST

Preserve canonical services

Never calculate intelligence inside React

Follow exact column order

Maintain layout hierarchy

Use EDGEIQ Design System colours

Keep Recent Form as hero

Implement Today's Match highlighting

Display benchmark lengths

Maintain governed architecture

Never fabricate unavailable intelligence

Run build

Run audits

Capture screenshots

Produce completion report

---

# END OF SPECIFICATION

Specification

BETA-001

Workspace

FORM GUIDE

Status

LOCKED

Authority

Canonical EDGEIQ Beta Engineering Specification

Revision

Changes require explicit version increment.

