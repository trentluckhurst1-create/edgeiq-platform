# SPEC-007
# EDGEIQ TRACK
## PRODUCT ENGINEERING SPECIFICATION
### VERSION 1.0
### STATUS LOCKED

---

# 1. PURPOSE

The Track Workspace is the authoritative source for all official track information, physical characteristics and historical context for the selected meeting.

It exists to answer:

"How will today's track influence today's racing?"

The Track Workspace presents evidence only.

It never predicts race outcomes.

---

# 2. PRODUCT PHILOSOPHY

Track conditions influence every race.

The Track Workspace allows the analyst to understand

• Surface

• Rail Position

• Track Rating

• Historical Bias

• Physical Layout

• Track Characteristics

without requiring external resources.

The workspace complements the Form Guide and MAP.

It never duplicates them.

---

# 3. USER GOALS

Immediately understand

• Track Rating

• Rail Position

• Course Configuration

• Track Dimensions

• Historical Bias

• Surface Characteristics

• Typical Racing Pattern

within one workspace.

---

# 4. WORKSPACE LAYOUT

----------------------------------------------------

HEADER

----------------------------------------------------

TRACK SUMMARY

----------------------------------------------------

TRACK MAP

----------------------------------------------------

TRACK PROFILE

----------------------------------------------------

HISTORICAL COMPARISON

----------------------------------------------------

TRACK CHARACTERISTICS

----------------------------------------------------

---

# 5. TRACK SUMMARY

Displays

Track

↓

Track Rating

↓

Rail Position

↓

Surface

↓

Weather

↓

Temperature

↓

Wind

↓

Rainfall

↓

Irrigation

Card Height

110px

Background

FFFFFF

Border

1px solid #E5E8EE

---

# 6. TRACK MAP

Purpose

Display the official course layout.

This is informational.

It is NOT a speed map.

Displays

Course

Start Positions

Winning Post

Rail Position

Distance Markers

Home Turn

Straight

No overlays.

No tactical information.

---

# 7. TRACK PROFILE

Displays

Surface

↓

Circumference

↓

Home Straight

↓

Track Width

↓

Camber

↓

Elevation

↓

Typical Racing Pattern

↓

Drainage Notes

↓

Surface Comments

Official information only.

---

END OF PART 1


---

# 8. HISTORICAL COMPARISON

## Purpose

Historical Comparison provides objective historical context for today's racing surface.

It allows analysts to compare today's official conditions against previous meetings without introducing prediction.

This component is evidence only.

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

Historical Track Rating Distribution

↓

Historical Rail Position Distribution

↓

Historical Winning Pattern

↓

Inside / Middle / Outside Lane Distribution

↓

On-Speed / Midfield / Backmarker Distribution

↓

Historical Weather Comparison

No race times.

No margins.

No track records.

No class records.

These have been intentionally removed.

---

# 9. TRACK CHARACTERISTICS

Purpose

Provide permanent physical information about the racecourse.

Displays

Track Shape

↓

Surface Type

↓

Circumference

↓

Home Straight Length

↓

Average Corner Radius

↓

Elevation

↓

Camber

↓

Typical Bias

↓

Typical Racing Pattern

These values rarely change.

---

# 10. BIAS INFORMATION

Bias information is descriptive.

Never predictive.

Displays

Inside Advantage

↓

Middle Advantage

↓

Outside Advantage

↓

Leader Advantage

↓

Backmarker Advantage

↓

Rail Movement History

No probability percentages.

No confidence scores.

No recommendations.

---

# 11. TRACK INFORMATION

Displays

Current Track Rating

Current Rail Position

Current Weather

Current Irrigation

Rainfall 24 Hours

Rainfall 7 Days

Penetrometer (where available)

Official Surface Notes

Only governed data.

---

# 12. REMOVED COMPONENTS

The following components are permanently excluded.

Track Record

Class Records

Historical Race Times

Historical Margins

These do not form part of the Beta specification.

---

# 13. USER INTERACTION

Hover

Displays definitions only.

Click

No action.

Double Click

None.

This workspace is informational.

It does not navigate elsewhere.

---

# 14. DATA GOVERNANCE

React Responsibilities

Display

Highlight

Navigate

React MUST NEVER

Predict bias

Estimate conditions

Generate commentary

Modify track information

Builders are responsible for

Track

Rail

Surface

Historical Comparison

Weather

Coverage

Audits

---

END OF PART 2


---

# 15. DATA QUALITY

## Canonical Source

All Track information originates from governed canonical builders.

No React calculations.

No browser calculations.

No derived estimates.

---

## Data Quality Fields

Each track record exposes

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

No gradients.

No glossy effects.

No heavy shadows.

No decorative graphics.

Professional software only.

---

# 17. RESPONSIVE BEHAVIOUR

Desktop

Primary target.

No horizontal scrolling.

Laptop

Reduce margins only.

Track Map scales proportionally.

Tablet

Historical Comparison stacks beneath Track Profile.

Mobile

Not supported during Beta.

---

# 18. PERFORMANCE TARGETS

Workspace Load

<300ms

Track Change

<100ms

Hover

Immediate

Scroll

60fps

No unnecessary React re-rendering.

---

# 19. ACCESSIBILITY

Keyboard Navigation

Supported

Focus States

Visible

Contrast

WCAG AA

Track information must never rely solely on colour.

All maps require text alternatives.

---

# 20. FUTURE EXPANSION

Reserved

Historical Bias Engine

Live Track Evolution

Lane Performance Analysis

Moisture Profile

Track Maintenance Timeline

Drone Course Imagery

Surface Wear Analysis

Sectional Overlay

These additions extend the workspace.

They never redesign it.

---

# 21. ACCEPTANCE CRITERIA

The Track Workspace is complete when

✓ Official Track Summary displayed

✓ Track Map implemented

✓ Track Profile implemented

✓ Historical Comparison implemented

✓ Bias Analysis implemented

✓ Track Records removed

✓ Class Records removed

✓ Historical Race Times removed

✓ Historical Margins removed

✓ White EDGEIQ Design System implemented

✓ Canonical builders only

✓ npm build passes

✓ Engineering audits pass

---

# 22. CODEX IMPLEMENTATION CHECKLIST

Codex MUST

Use canonical Track builders

Never calculate Track intelligence in React

Implement Track Summary

Implement Track Map

Implement Track Profile

Implement Historical Comparison

Implement Bias Analysis

Exclude removed components

Follow MASTER Design System

Run npm build

Run engineering audits

Capture verification screenshots

Produce implementation report

---

# 23. ENGINEERING GOVERNANCE

This specification is the canonical authority for the Track Workspace.

Any modification to

Track Profile

Historical Comparison

Bias

Track Map

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

SPEC-007

Workspace

TRACK

Status

LOCKED

Authority

EDGEIQ Product Engineering Specification

Revision

1.0

