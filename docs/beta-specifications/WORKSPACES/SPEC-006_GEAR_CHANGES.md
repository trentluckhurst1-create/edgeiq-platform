# SPEC-006
# EDGEIQ GEAR CHANGES
## PRODUCT ENGINEERING SPECIFICATION
### VERSION 1.0
### STATUS LOCKED

---

# 1. PURPOSE

The Gear Changes Workspace provides the official operational record of all approved gear changes for the selected meeting.

Its purpose is to present factual equipment changes in a structured, searchable and comparable format.

The workspace is intentionally evidence-driven.

EDGEIQ never assumes a gear change is positive or negative.

Gear changes become one piece of evidence within the overall intelligence model.

---

# 2. PRODUCT PHILOSOPHY

Gear changes are operational facts.

Not opinions.

Not selections.

Not predictions.

The workspace allows the analyst to immediately identify

• Which runners have changed gear

• What equipment changed

• Whether it is first time

• Previous equipment configuration

• Historical gear usage

The analyst determines significance.

---

# 3. USER GOALS

Immediately identify

• First-time gear

• Gear removed

• Gear added

• Multiple gear changes

• Horses with no changes

without opening every runner individually.

---

# 4. WORKSPACE LAYOUT

----------------------------------------------------

HEADER

----------------------------------------------------

SUMMARY CARDS

----------------------------------------------------

GEAR CHANGE TABLE

----------------------------------------------------

HISTORICAL GEAR PANEL

----------------------------------------------------

NOTES

----------------------------------------------------

---

# 5. SUMMARY CARDS

Displays

Total Gear Changes

↓

First Time Gear

↓

Gear Removed

↓

Multiple Changes

Card Height

110px

Background

FFFFFF

Border

1px solid #E5E8EE

---

# 6. GEAR CHANGE TABLE

Purpose

Display every official gear change.

One row

One runner.

No grouped rows.

---

LOCKED COLUMN ORDER

RACE

NO

HORSE

TRAINER

GEAR CHANGE

CHANGE TYPE

FIRST TIME

PREVIOUS GEAR

NOTES

This order is frozen.

---

END OF PART 1


---

# 7. TABLE DESIGN

## Layout

Full Width

100%

Minimum Height

620px

Preferred Height

720px

Row Height

48px

Header Height

46px

Border Radius

8px

Border

1px solid #E5E8EE

Background

FFFFFF

---

## Column Specifications

RACE

Width

70px

Centre

---

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

TRAINER

Width

180px

Left

---

GEAR CHANGE

Width

220px

Left

Official Racing Australia terminology only.

Examples

Blinkers On

Blinkers Off

Tongue Tie On

Visors On

Cross-over Noseband

Ear Muffs Pre-Race

Synthetic Hoof Filler

No abbreviations unless official.

---

CHANGE TYPE

Width

120px

Centre

Values

Added

Removed

Modified

Multiple

---

FIRST TIME

Width

100px

Centre

Displays

YES

NO

Future

Historical Count

---

PREVIOUS GEAR

Width

220px

Left

Displays the previous official gear configuration.

No calculated values.

---

NOTES

Width

260px

Left

Official steward or authority notes only.

No generated commentary.

---

# 8. FIRST-TIME GEAR

Purpose

Immediately identify equipment being used for the first time.

Display

YES

No coloured icons.

No flashing indicators.

No prediction.

Evidence only.

---

# 9. HISTORICAL GEAR PANEL

Selecting a runner opens

Historical Gear Summary

Displays

Current Gear

↓

Previous Starts

↓

Historical Changes

↓

Dates Introduced

↓

Dates Removed

↓

Current Configuration

This panel is informational only.

---

# 10. GEAR HISTORY

Display

Date

↓

Meeting

↓

Gear

↓

Status

↓

Official Notes

One row per historical gear change.

No grouping.

---

# 11. INTERACTION

Selecting a runner

↓

Updates Historical Gear Panel

↓

Does not leave the workspace

Hovering Gear

Displays

Official description

First-use date

Last-use date

Current status

No intelligence.

---

# 12. SEARCH

Search

Horse

Trainer

Gear

Partial match

Case insensitive

Instant

No submit button.

---

END OF PART 2


---

# 13. DATA GOVERNANCE

## React Responsibilities

React is responsible for

Display

Sort

Filter

Search

Navigation

Highlight

Expand

Collapse

React MUST NEVER

Generate gear history

Interpret gear effectiveness

Calculate strike rates

Estimate improvement

Predict performance

Generate intelligence

Every displayed value originates from governed builders.

---

## Builder Responsibilities

Canonical builders produce

Official Gear Changes

Historical Gear Records

First-Time Gear Flags

Current Gear Configuration

Coverage Reports

Builder Versions

Audit Reports

Builder output is the single source of truth.

---

# 14. DATA QUALITY

Every gear record exposes

Official Source

Builder Version

Coverage

Timestamp

Audit Status

Feed Status

Unavailable data displays

Unavailable

Never estimated.

Never inferred.

---

# 15. DESIGN SYSTEM COMPLIANCE

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

No gradients.

No shadows beyond subtle elevation.

No coloured gear icons.

No decorative graphics.

---

# 16. RESPONSIVE BEHAVIOUR

Desktop

Primary design target.

Laptop

Reduce spacing only.

Tablet

Historical Gear Panel moves beneath table.

Mobile

Not supported during Beta.

---

# 17. PERFORMANCE TARGETS

Workspace Load

<300ms

Runner Selection

<100ms

Historical Gear Update

<100ms

Search

Instant

Sort

<50ms

Hover

Immediate

No unnecessary re-rendering.

---

# 18. ACCESSIBILITY

Keyboard Navigation

Supported

Focus Indicators

Visible

Contrast

WCAG AA

Gear changes must never rely solely on colour.

---

# 19. FUTURE EXPANSION

Reserved

Historical Gear Strike Rates

Trainer Gear Statistics

Gear Success Profiles

Stable Equipment Trends

Equipment Timeline

Runner Equipment Evolution

Veterinary Equipment Notes

These additions extend the workspace.

They never redesign it.

---

# 20. ACCEPTANCE CRITERIA

Gear Changes Workspace is complete when

✓ Locked column order implemented

✓ Official terminology displayed

✓ First-Time Gear correctly identified

✓ Historical Gear Panel implemented

✓ Search operational

✓ React remains display-only

✓ Canonical builders used

✓ White EDGEIQ Design System implemented

✓ npm build passes

✓ Engineering audits pass

---

# 21. CODEX IMPLEMENTATION CHECKLIST

Codex MUST

Use canonical gear builders

Never interpret gear changes

Never calculate intelligence in React

Implement Historical Gear Panel

Implement First-Time Gear indicators

Preserve Meeting Detail context

Follow MASTER Design System

Run npm build

Run engineering audits

Capture verification screenshots

Produce implementation report

---

# 22. ENGINEERING GOVERNANCE

This specification is the canonical authority for the Gear Changes workspace.

Any modification to

Gear terminology

Historical presentation

First-Time Gear logic

Builder ownership

or

Operational workflow

requires

Specification revision

Version increment

Engineering review

Audit update

Implementation must follow this specification exactly.

---

# END OF SPECIFICATION

Specification

SPEC-006

Workspace

GEAR CHANGES

Status

LOCKED

Authority

EDGEIQ Product Engineering Specification

Revision

1.0

