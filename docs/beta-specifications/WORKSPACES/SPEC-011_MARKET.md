# SPEC-011
# EDGEIQ MARKET
## PRODUCT ENGINEERING SPECIFICATION
### VERSION 1.0
### STATUS LOCKED

---

# 1. PURPOSE

The Market Workspace is the official market intelligence workspace within EDGEIQ.

Its purpose is to present factual market behaviour alongside EDGEIQ intelligence, allowing analysts to compare public market opinion with internally generated pricing.

The Market Workspace is not a betting interface.

It is an analytical comparison workspace.

---

# 2. PRODUCT PHILOSOPHY

The market is one source of evidence.

It is never treated as truth.

EDGEIQ allows the analyst to compare

Public Market

↓

EDGEIQ Price

↓

Market Movement

↓

Value Position

↓

Market Intelligence

The analyst decides whether the market is correct.

---

# 3. USER GOALS

Immediately identify

• Current Market

• Market Movement

• EDGEIQ Price

• Overlay

• Underlay

• Firmers

• Drifters

• Market Status

without leaving EDGEIQ.

---

# 4. WORKSPACE LAYOUT

----------------------------------------------------

HEADER

----------------------------------------------------

MARKET SUMMARY

----------------------------------------------------

MARKET TABLE

----------------------------------------------------

MARKET MOVEMENT

----------------------------------------------------

MARKET NOTES

----------------------------------------------------

---

# 5. MARKET SUMMARY

Displays

Market Status

↓

Current Favourite

↓

Largest Firmer

↓

Largest Drifter

↓

Average Market Percentage

↓

Last Updated

Card Height

110px

Background

FFFFFF

Border

1px solid #E5E8EE

---

# 6. MARKET TABLE

Purpose

Provide a complete comparison between the public market and EDGEIQ.

One row

One runner.

---

LOCKED COLUMN ORDER

NO

HORSE

MARKET

EDGEIQ PRICE

DIFFERENCE

MOVEMENT

STATUS

This order is frozen.

---

# 7. COLUMN SPECIFICATIONS

NO

Width

60px

Centre

Plain saddlecloth number.

No coloured backgrounds.

---

HORSE

Width

240px

Left

Bold

Primary identifier.

---

MARKET

Width

110px

Centre

Current official market price.

Display

$3.80

No percentages.

---

EDGEIQ PRICE

Width

110px

Centre

Canonical EDGEIQ assessed price.

Single decimal place.

---

DIFFERENCE

Width

100px

Centre

Difference between

Market

and

EDGEIQ Price.

Positive and negative values only.

No recommendation.

---

MOVEMENT

Width

120px

Centre

Displays

Firming

Drifting

Stable

Official market movement only.

---

STATUS

Width

140px

Centre

Displays

Overlay

Underlay

Fair

This is an analytical classification only.

Not betting advice.

---

END OF PART 1


---

# 8. MARKET MOVEMENT

## Purpose

The Market Movement panel provides a chronological view of how each runner's market has evolved from the opening market to the current price.

Its purpose is to show market behaviour.

It does not explain market behaviour.

---

## Layout

Full Width

100%

Background

FFFFFF

Border

1px solid #E5E8EE

Border Radius

8px

---

## Displays

Opening Price

↓

Current Price

↓

Lowest Price

↓

Highest Price

↓

Net Movement

↓

Movement Direction

↓

Last Update

---

## Movement Rules

Opening

↓

Current

↓

Lowest

↓

Highest

↓

Net Change

No smoothing.

No interpolation.

Official prices only.

---

# 9. MARKET HISTORY

Purpose

Display historical price evolution.

Timeline

Opening

↓

5 Minutes

↓

10 Minutes

↓

30 Minutes

↓

60 Minutes

↓

Current

Future versions may increase sampling frequency.

Historical prices are immutable once captured.

---

# 10. OVERLAY ANALYSIS

Purpose

Compare the public market against the canonical EDGEIQ Price.

Formula

Difference

=

Market Price

-

EDGEIQ Price

This calculation is performed by the canonical builder.

React displays only.

---

## STATUS CLASSIFICATION

Display

Overlay

↓

Fair

↓

Underlay

No recommendation.

No betting advice.

No confidence wording.

---

## Colour Rules

Overlay

EDGEIQ Green

Fair

Neutral Grey

Underlay

EDGEIQ Red

Colour is supplementary only.

Text remains visible without colour.

---

# 11. MARKET NOTES

Purpose

Provide factual observations about market behaviour.

Examples

Largest Firmer

Largest Drifter

Stable Market

Late Market Activity

Late Scratching Impact

Market Suspended

Official operational observations only.

No generated commentary.

---

# 12. REMOVED COMPONENTS

The following are permanently excluded.

Back

Lay

Exchange Ladder

Matched Volume

Order Book

Trading Interface

Market Depth Visualisation (until officially supported)

These are not part of the EDGEIQ Market specification.

---

# 13. USER INTERACTION

Hover

Displays

Opening Price

↓

Current Price

↓

Lowest Price

↓

Highest Price

↓

Last Updated

Click

No action.

Double Click

None.

The Market workspace is informational.

---

END OF PART 2


---

# 14. DATA GOVERNANCE

## React Responsibilities

React is responsible for

Display

Sort

Filter

Search

Hover

Responsive Layout

Navigation

Highlight

React MUST NEVER

Calculate EDGEIQ Price

Calculate Overlay

Calculate Underlay

Calculate Market Difference

Calculate Market Movement

Generate Market Commentary

Modify Official Prices

All market intelligence originates from governed builders.

---

## Builder Responsibilities

Canonical Market Builders produce

Official Market

↓

Opening Market

↓

Current Market

↓

Lowest Market

↓

Highest Market

↓

EDGEIQ Price

↓

Difference

↓

Overlay Status

↓

Movement Status

↓

Coverage

↓

Builder Version

↓

Audit Reports

Builder output is the single source of truth.

---

# 15. DATA QUALITY

Every market record exposes

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

# 16. DESIGN SYSTEM COMPLIANCE

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

Overlay

EDGEIQ Green

Fair

Neutral Grey

Underlay

EDGEIQ Red

No gradients.

No exchange styling.

No trading interface.

Professional analytical software only.

---

# 17. RESPONSIVE BEHAVIOUR

Desktop

Primary target.

Market Table occupies full width.

Laptop

Reduce margins only.

Tablet

Market Movement stacks beneath Market Table.

Mobile

Not supported during Beta.

---

# 18. PERFORMANCE TARGETS

Workspace Load

<300ms

Market Refresh

Automatic

Hover

Immediate

Search

Instant

Sort

<50ms

No unnecessary React re-rendering.

No duplicate market requests.

---

# 19. ACCESSIBILITY

Keyboard Navigation

Supported

Focus Indicators

Visible

Contrast

WCAG AA

Overlay, Fair and Underlay must never rely solely on colour.

Text must always remain readable.

---

# 20. FUTURE EXPANSION

Reserved

Market Probability Curve

↓

Late Money Detection

↓

Market Efficiency

↓

Bookmaker Comparison

↓

Corporate Comparison

↓

SP Analysis

↓

Market Replay

↓

Price Distribution

These modules extend the workspace.

They never redesign it.

---

# 21. ACCEPTANCE CRITERIA

Market Workspace is complete when

✓ Market Summary implemented

✓ Market Table implemented

✓ Market Movement implemented

✓ Overlay analysis implemented

✓ Locked column order preserved

✓ EDGEIQ Price displayed

✓ Difference displayed

✓ Overlay / Fair / Underlay displayed

✓ Back removed

✓ Lay removed

✓ Exchange interface removed

✓ Canonical builders only

✓ White EDGEIQ Design System implemented

✓ npm build passes

✓ Engineering audits pass

---

# 22. CODEX IMPLEMENTATION CHECKLIST

Codex MUST

Use canonical market builders

Never calculate market intelligence in React

Implement Market Summary

Implement Market Table

Implement Market Movement

Implement Overlay Analysis

Remove Back

Remove Lay

Remove Exchange Interface

Follow MASTER Design System

Run npm build

Run engineering audits

Capture verification screenshots

Produce implementation report

---

# 23. ENGINEERING GOVERNANCE

This specification is the canonical authority for the Market Workspace.

Any modification to

EDGEIQ Price

Overlay Logic

Market Movement

Builder Ownership

Workspace Layout

or

Market Behaviour

requires

Specification revision

Version increment

Engineering review

Audit update

Implementation must follow this specification exactly.

---

# END OF SPECIFICATION

Specification

SPEC-011

Workspace

MARKET

Status

LOCKED

Authority

EDGEIQ Product Engineering Specification

Revision

1.0

