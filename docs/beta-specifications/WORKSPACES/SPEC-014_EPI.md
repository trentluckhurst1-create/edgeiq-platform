# SPEC-014
# EDGEIQ PERFORMANCE INDEX (EPI)
## PRODUCT ENGINEERING SPECIFICATION
### VERSION 1.0
### STATUS LOCKED

---

# 1. PURPOSE

The EPI Workspace is the historical performance intelligence centre of EDGEIQ.

Its purpose is to visualise the evolution of a runner's EDGEIQ Performance Index throughout its career.

Unlike the Form Guide, which presents historical race form, the EPI Workspace presents historical performance ratings.

It allows analysts to quickly identify

• Improvement

• Decline

• Consistency

• Peak Performance

• Suitability Trends

through objective historical ratings.

The EPI Workspace is evidence.

It never predicts future performance.

---

# 2. PRODUCT PHILOSOPHY

EPI measures performance.

It does not measure winning.

It allows analysts to compare

Today's Runner

↓

Past Runner

↓

Past Race Strength

↓

Historical Context

Every rating exists within the strength of the race it was achieved.

This is why ERI accompanies every historical EPI.

---

# 3. USER GOALS

Immediately understand

• Current EPI

↓

• Peak EPI

↓

• Average EPI

↓

• Last 10 EPIs

↓

• Historical Trend

↓

• Performance Consistency

↓

• Race Strength Context

↓

• Career Progression

without manually reviewing historical races.

---

# 4. WORKSPACE LAYOUT

----------------------------------------------------

HEADER

----------------------------------------------------

CAREER SUMMARY

----------------------------------------------------

EPI HEAT MAP

----------------------------------------------------

EPI HISTORY TABLE

----------------------------------------------------

TREND ANALYSIS

----------------------------------------------------

DATA QUALITY

----------------------------------------------------

---

# 5. CAREER SUMMARY

Displays

Current EPI

↓

Peak EPI

↓

Average EPI

↓

Median EPI

↓

Career Starts

↓

Last Updated

Card Height

110px

Background

FFFFFF

Border

1px solid #E5E8EE

---

# 6. EPI HEAT MAP

Purpose

Provide an immediate visual representation of historical performance.

Displays

Last 10 Official Starts

Each start occupies one heat-map tile.

Tiles are displayed

Left

(Oldest)

↓

Right

(Most Recent)

Every tile displays

EPI Rating

Only.

No race names inside tiles.

No icons.

No arrows.

---

# 7. HEAT MAP COLOUR SCALE

Highest Career EPI

EDGEIQ Green

↓

Above Average

Green

↓

Average

Neutral Grey

↓

Below Average

Amber

↓

Lowest Career EPI

EDGEIQ Red

Colour represents

Historical EPI only.

Nothing else.

---

# 8. TILE INTERACTION

Hovering any heat-map tile displays

Race Date

↓

Track

↓

Race Number

↓

Distance

↓

Class

↓

Track Rating

↓

Barrier

↓

Weight

↓

Jockey

↓

Trainer

↓

Finishing Position

↓

Margin

↓

Official SP

↓

EPI

↓

ERI

↓

Track Condition

↓

Weather

↓

Stewards Comments (when available)

This hover becomes the primary method of historical exploration.

No modal required.

---

END OF PART 1


---

# 9. HISTORICAL EPI TABLE

## Purpose

The Historical EPI Table provides the numerical history supporting the EPI Heat Map.

Every heat-map tile corresponds to exactly one row within this table.

The table is the authoritative historical record of the runner's EPI history.

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

Minimum Height

520px

Preferred Height

640px

---

## LOCKED COLUMN ORDER

DATE

TRACK

RACE

DIST

CLASS

POS

MARGIN

SP

EPI

ERI

DELTA

---

## Column Specifications

DATE

Centre

Official race date.

---

TRACK

Left

Official track name.

---

RACE

Centre

Official race number.

---

DIST

Centre

Official race distance.

---

CLASS

Centre

Official race class.

---

POS

Centre

Official finishing position.

---

MARGIN

Centre

Official beaten margin.

---

SP

Centre

Official Starting Price.

---

EPI

Centre

Single decimal place.

Canonical historical EPI.

---

ERI

Centre

Single decimal place.

Historical Race Strength.

---

DELTA

Centre

Difference from previous EPI.

Example

+3.6

-2.1

0.0

Calculated by canonical builder only.

React never calculates DELTA.

---

# 10. TREND ANALYSIS

Purpose

Provide objective historical performance trends.

Displays

Current Trend

↓

Average Trend

↓

Best Improvement

↓

Largest Decline

↓

Rolling Average

↓

Consistency Rating

No prediction.

No future projection.

Historical evidence only.

---

# 11. EPI PROGRESSION

Display

Career progression from

Oldest

↓

Most Recent

Every point represents one official race.

No interpolated values.

No smoothing.

No estimated races.

Missing races remain missing.

---

# 12. ERI CONTEXT

Every historical EPI must be interpreted within the strength of the race.

Each historical record therefore displays

Historical EPI

+

Historical ERI

Hovering ERI displays

Race Strength

↓

Field Strength

↓

Historical Context

↓

Builder Version

↓

Timestamp

ERI is never hidden.

It is fundamental to interpreting historical performance.

---

# 13. TILE HOVER BEHAVIOUR

Hover appears instantly.

Displays

Race Date

↓

Meeting

↓

Track

↓

Distance

↓

Class

↓

Barrier

↓

Weight

↓

Jockey

↓

Trainer

↓

Track Rating

↓

Finishing Position

↓

Margin

↓

Official SP

↓

Historical EPI

↓

Historical ERI

↓

Stewards Comment

↓

Builder Version

↓

Timestamp

Hover remains open while pointer remains inside.

No modal.

No page navigation.

---

# 14. USER INTERACTION

Selecting a heat-map tile

↓

Highlights corresponding table row.

Selecting a table row

↓

Highlights corresponding heat-map tile.

Selection remains synchronised.

Only one race may be selected at a time.

---

# 15. FILTERING

Future Capability

Career

↓

Track

↓

Distance

↓

Class

↓

Going

↓

Preparation Stage

↓

Trainer

↓

Jockey

Filtering never modifies canonical history.

Display only.

---

END OF PART 2


---

# 16. DATA GOVERNANCE

## React Responsibilities

React is responsible for

Display

Highlight

Hover

Expand

Collapse

Search

Filter

Responsive Layout

Synchronise Tile Selection

Synchronise Table Selection

React MUST NEVER

Calculate EPI

Calculate ERI

Calculate DELTA

Calculate Trends

Calculate Rolling Average

Calculate Consistency

Estimate Missing Ratings

Generate Commentary

Every value originates from governed canonical builders.

---

## Builder Responsibilities

Canonical EPI Builders produce

Current EPI

↓

Historical EPI

↓

Peak EPI

↓

Average EPI

↓

Median EPI

↓

Historical ERI

↓

EPI Delta

↓

Trend Analysis

↓

Consistency Rating

↓

Coverage

↓

Builder Version

↓

Audit Reports

Builder output is the single source of truth.

---

# 17. DATA QUALITY

Every historical EPI record exposes

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

Never interpolated.

---

# 18. DESIGN SYSTEM COMPLIANCE

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

Heat Map Colours

Highest Historical EPI

EDGEIQ Green

Above Average

Green

Average

Neutral Grey

Below Average

Amber

Lowest Historical EPI

EDGEIQ Red

Only historical EPI controls tile colouring.

No gradients.

No glow.

No animation.

Professional analytical software only.

---

# 19. RESPONSIVE BEHAVIOUR

Desktop

Primary target.

Career Summary

↓

Heat Map

↓

Historical Table

↓

Trend Analysis

display vertically in this order.

Laptop

Reduce spacing only.

Tablet

Historical Table stacks beneath Heat Map.

Trend Analysis stacks beneath Historical Table.

Mobile

Not supported during Beta.

---

# 20. PERFORMANCE TARGETS

Workspace Load

Target

<300ms

Heat Map Hover

Immediate

Tile Selection

<50ms

Table Synchronisation

<50ms

Historical Search

Instant

No unnecessary React re-rendering.

No duplicate builder requests.

---

# 21. ACCESSIBILITY

Keyboard Navigation

Supported

Focus Indicators

Visible

Contrast

WCAG AA

Every heat-map tile exposes

Accessible Label

↓

Race Date

↓

Historical EPI

↓

Historical ERI

↓

Finishing Position

↓

Builder Version

Information must never rely solely on colour.

---

# 22. FUTURE EXPANSION

Reserved

Career EPI Distribution

↓

Distance-specific EPI

↓

Track-specific EPI

↓

Preparation Stage EPI

↓

Trainer Change Timeline

↓

Jockey Change Timeline

↓

Interactive Career Graph

↓

Cross Runner EPI Comparison

↓

Historical Race Replay Synchronisation

These additions extend the workspace.

They never redesign it.

---

# 23. ACCEPTANCE CRITERIA

EPI Workspace is complete when

✓ Career Summary implemented

✓ Last 10 EPI Heat Map implemented

✓ Heat Map displays EPI values

✓ Heat Map colours follow specification

✓ Hover cards display full historical race information

✓ Historical EPI Table implemented

✓ Locked column order preserved

✓ ERI displayed for every historical run

✓ DELTA displayed

✓ Heat Map and Table remain synchronised

✓ Trend Analysis implemented

✓ Canonical builders only

✓ White EDGEIQ Design System implemented

✓ npm build passes

✓ Engineering audits pass

---

# 24. CODEX IMPLEMENTATION CHECKLIST

Codex MUST

Use canonical EPI builders

Never calculate EPI in React

Never calculate ERI in React

Never calculate DELTA in React

Implement Career Summary

Implement Last 10 Heat Map

Implement Tile Hover Cards

Implement Historical EPI Table

Implement Trend Analysis

Synchronise Heat Map and Table selection

Follow MASTER Design System

Run npm build

Run engineering audits

Capture verification screenshots

Produce implementation report

---

# 25. ENGINEERING GOVERNANCE

This specification is the canonical authority for the EPI Workspace.

Any modification to

Heat Map

Historical EPI

ERI

Trend Analysis

Hover Cards

Builder ownership

Workspace layout

or

Historical behaviour

requires

Specification revision

Version increment

Engineering review

Audit update

Implementation must follow this specification exactly.

---

# END OF SPECIFICATION

Specification

SPEC-014

Workspace

EPI

Status

LOCKED

Authority

EDGEIQ Product Engineering Specification

Revision

1.0

