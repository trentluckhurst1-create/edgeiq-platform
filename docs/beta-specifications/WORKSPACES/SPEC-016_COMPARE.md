# SPEC-016
# EDGEIQ COMPARE
## PRODUCT ENGINEERING SPECIFICATION
### VERSION 1.0
### STATUS LOCKED

---

# 1. PURPOSE

The Compare Workspace is the side-by-side analytical comparison engine of EDGEIQ.

Its purpose is to allow analysts to compare two or more runners using governed intelligence without manually switching between profiles.

The Compare Workspace is evidence.

It never recommends.

It never predicts.

It presents governed information in a directly comparable format.

---

# 2. PRODUCT PHILOSOPHY

Professional analysts constantly compare runners.

EDGEIQ should make comparison effortless.

Every comparison must use identical metrics.

Every comparison must use identical calculations.

Every comparison must originate from canonical builders.

---

# 3. USER GOALS

Immediately compare

• EPI

↓

• Suitability

↓

• Form Momentum

↓

• Early Speed

↓

• Late Speed

↓

• Historical Form

↓

• Track Profile

↓

• Distance Profile

↓

• Barrier

↓

• Weight

↓

• Trainer

↓

• Jockey

↓

• Market

↓

• Historical Statistics

without switching between runners.

---

# 4. WORKSPACE LAYOUT

----------------------------------------------------

HEADER

----------------------------------------------------

RUNNER SELECTION

----------------------------------------------------

COMPARISON GRID

----------------------------------------------------

CATEGORY TABS

----------------------------------------------------

DETAILED COMPARISON

----------------------------------------------------

DATA QUALITY

----------------------------------------------------

---

# 5. RUNNER SELECTION

Displays

Available Runners

↓

Selected Runner A

↓

Selected Runner B

↓

Optional Runner C

↓

Optional Runner D

Maximum Comparison

Four runners

No practical limit exists within canonical builders.

Beta interface supports four simultaneously.

---

# 6. COMPARISON GRID

Purpose

Provide immediate side-by-side comparison.

Rows

Comparison Metrics

Columns

Selected Runners

Every runner occupies an identical column.

Every metric occupies an identical row.

This layout never changes.

---

# 7. LOCKED COMPARISON ORDER

Current EPI

↓

Peak EPI

↓

Average EPI

↓

Suitability

↓

Form Momentum

↓

Early Speed

↓

Late Speed

↓

Track Profile

↓

Distance Profile

↓

Barrier

↓

Weight

↓

Trainer

↓

Jockey

↓

Current Market

↓

EDGEIQ Price

↓

Historical Strike Rate

↓

Career Statistics

↓

Current Preparation

This order is frozen.

---

# 8. CATEGORY TABS

Displays

OVERVIEW

↓

FORM

↓

EPI

↓

SPEED

↓

SUITABILITY

↓

MARKET

↓

CONNECTIONS

↓

CAREER

Changing tabs preserves selected runners.

Only comparison metrics change.

---

END OF PART 1


---

# 9. DETAILED COMPARISON

## Purpose

The Detailed Comparison section provides metric-by-metric analysis for every selected runner.

Each metric is presented in identical order for every runner.

The purpose is comparison.

Not recommendation.

---

## Layout

Rows

Comparison Metrics

Columns

Selected Runners

Every runner occupies identical width.

No runner receives visual priority.

---

# 10. COMPARISON METRICS

Every metric originates from canonical builders.

LOCKED ORDER

Current EPI

↓

Peak EPI

↓

Average EPI

↓

Current ERI Context

↓

Suitability

↓

Form Momentum

↓

Early Speed

↓

Late Speed

↓

Running Style

↓

Track Profile

↓

Distance Profile

↓

Track & Distance

↓

Barrier

↓

Weight

↓

Preparation Stage

↓

Trainer

↓

Jockey

↓

Market

↓

EDGEIQ Price

↓

Career Statistics

↓

Historical Strike Rate

This order is frozen.

---

# 11. HIGHLIGHTING

Purpose

Quickly identify meaningful differences.

Highest Value

EDGEIQ Green Border

Lowest Value

EDGEIQ Red Border

Equal Values

Neutral Border

No coloured backgrounds.

No flashing.

No animation.

Colour supports the comparison.

It never replaces the data.

---

# 12. USER INTERACTION

Selecting Runner

Immediately refreshes

Entire comparison.

Removing Runner

Automatically resizes columns.

Hover

Displays

Builder Version

↓

Timestamp

↓

Coverage

↓

Definition

No calculations occur in React.

---

# 13. DATA GOVERNANCE

React Responsibilities

Display

Highlight

Resize

Navigate

Filter

React MUST NEVER

Calculate comparisons

Calculate rankings

Generate commentary

Recommend runners

Everything originates from governed builders.

---

# 14. BUILDER RESPONSIBILITIES

Canonical builders provide

Comparison Metrics

↓

EPI

↓

ERI

↓

Suitability

↓

Momentum

↓

Speed

↓

Connections

↓

Market

↓

Coverage

↓

Audit Reports

Builder output is the single source of truth.

---

END OF PART 2


---

# 15. DATA QUALITY

## Canonical Source

Every comparison metric originates from governed canonical builders.

The Compare Workspace owns no intelligence.

It consumes governed services only.

---

## Data Quality Fields

Each comparison metric exposes

Builder Version

↓

Coverage

↓

Timestamp

↓

Audit Status

↓

Feed Health

↓

Canonical Source

Unavailable values display

Unavailable

Never estimated.

Never inferred.

Never fabricated.

---

# 16. DESIGN SYSTEM COMPLIANCE

Background

FFFFFF

Surface

FFFFFF

Secondary Surface

FAFBFC

Primary Border

E5E8EE

Primary Accent

EDGEIQ Blue

Primary Text

1A1A1A

Secondary Text

5C6675

Best Value

EDGEIQ Green Border

Lowest Value

EDGEIQ Red Border

Equal Values

Neutral Border

No gradients.

No glowing cards.

No animations.

No oversized hero graphics.

Professional analytical software only.

---

# 17. RESPONSIVE BEHAVIOUR

Desktop

Primary target.

Supports comparison of

2

3

or

4

runners simultaneously.

Columns resize evenly.

Laptop

Reduce spacing only.

Tablet

Horizontal scrolling permitted.

Mobile

Not supported during Beta.

---

# 18. PERFORMANCE TARGETS

Workspace Load

Target

<300ms

Runner Selection

<100ms

Comparison Refresh

<100ms

Hover

Immediate

Search

Instant

No unnecessary React re-rendering.

No duplicated builder requests.

---

# 19. ACCESSIBILITY

Keyboard Navigation

Supported

Focus Indicators

Visible

Contrast

WCAG AA

Every comparison cell exposes

Accessible Label

↓

Metric Name

↓

Runner Name

↓

Value

↓

Builder Version

↓

Timestamp

Information must never rely solely on colour.

---

# 20. FUTURE EXPANSION

Reserved

Unlimited Runner Comparison

↓

Cross Race Comparison

↓

Historical Comparison

↓

Career Comparison

↓

Trainer Comparison

↓

Jockey Comparison

↓

Stable Comparison

↓

Interactive Difference Charts

↓

Probability Comparison

These additions extend the workspace.

They never redesign it.

---

# 21. ACCEPTANCE CRITERIA

Compare Workspace is complete when

✓ Runner Selection implemented

✓ Comparison Grid implemented

✓ Locked comparison order preserved

✓ Category Tabs implemented

✓ Highlighting implemented

✓ Hover information implemented

✓ Supports two to four runners

✓ Canonical builders only

✓ White EDGEIQ Design System implemented

✓ npm build passes

✓ Engineering audits pass

---

# 22. CODEX IMPLEMENTATION CHECKLIST

Codex MUST

Use canonical comparison builders

Never calculate comparisons in React

Implement Runner Selection

Implement Comparison Grid

Implement Category Tabs

Implement Highlighting

Implement Hover Information

Support two to four runners

Follow MASTER Design System

Run npm build

Run engineering audits

Capture verification screenshots

Produce implementation report

---

# 23. ENGINEERING GOVERNANCE

This specification is the canonical authority for the Compare Workspace.

Any modification to

Comparison Metrics

Highlighting

Category Tabs

Builder ownership

Workspace layout

or

Comparison behaviour

requires

Specification revision

Version increment

Engineering review

Audit update

Implementation must follow this specification exactly.

---

# END OF SPECIFICATION

Specification

SPEC-016

Workspace

COMPARE

Status

LOCKED

Authority

EDGEIQ Product Engineering Specification

Revision

1.0

