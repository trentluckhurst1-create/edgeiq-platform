# SPEC-012
# EDGEIQ OVERVIEW
## PRODUCT ENGINEERING SPECIFICATION
### VERSION 1.0
### STATUS LOCKED

---

# 1. PURPOSE

The Overview Workspace is the executive summary of the selected race.

It provides a concise, evidence-based briefing before the analyst enters the deeper workspaces.

Its purpose is to answer one question:

"What does this race look like right now?"

The Overview never replaces detailed analysis.

It directs the analyst towards it.

---

# 2. PRODUCT PHILOSOPHY

The Overview Workspace is the race briefing.

It combines

Race Conditions

↓

Field Strength

↓

Tempo

↓

Market

↓

Key Intelligence

↓

Operational Information

into one workspace.

The Overview is intentionally concise.

Every deeper detail is available in the dedicated workspaces.

---

# 3. USER GOALS

Immediately understand

• Race Conditions

• Field Strength

• Tempo

• Early Speed

• Key Runners

• Market Position

• Track Conditions

• Weather

• Intelligence Summary

within thirty seconds.

---

# 4. WORKSPACE LAYOUT

----------------------------------------------------

HEADER

----------------------------------------------------

RACE SUMMARY

----------------------------------------------------

KEY INTELLIGENCE

----------------------------------------------------

RACE CONDITIONS

----------------------------------------------------

KEY RUNNERS

----------------------------------------------------

MARKET SUMMARY

----------------------------------------------------

TRACK & WEATHER

----------------------------------------------------

OPERATIONAL STATUS

----------------------------------------------------

---

# 5. RACE SUMMARY

Displays

Meeting

↓

Race Number

↓

Distance

↓

Class

↓

Track Rating

↓

Rail Position

↓

Field Size

↓

Prize Money

↓

Start Time

Card Height

110px

Background

FFFFFF

Border

1px solid #E5E8EE

---

# 6. KEY INTELLIGENCE

Purpose

Provide the highest-value intelligence for the race.

Displays

Expected Tempo

↓

Race Shape Summary

↓

Highest Rated Runner (EPI)

↓

Best Suitability

↓

Strongest Form Momentum

↓

Most Significant Market Position

↓

Key Operational Notes

No selections.

No betting advice.

Evidence only.

---

# 7. RACE CONDITIONS

Displays

Track

↓

Distance

↓

Class

↓

Track Rating

↓

Rail Position

↓

Weather

↓

Temperature

↓

Wind

↓

Humidity

↓

Field Size

Official information only.

---

# 8. KEY RUNNERS

Displays

Top EPI Runners

↓

Top Early Speed

↓

Top Late Speed

↓

Top Suitability

↓

Top Form Momentum

Each category displays the leading runners only.

No rankings beyond the required list.

---

END OF PART 1


---

# 9. MARKET SUMMARY

## Purpose

The Market Summary provides a concise operational snapshot of today's betting market.

It is not intended to replace the Market Workspace.

It exists to identify significant market characteristics before deeper analysis.

---

## Displays

Current Favourite

↓

Second Favourite

↓

Largest Firmer

↓

Largest Drifter

↓

Average Market Percentage

↓

EDGEIQ Market Status

↓

Last Updated

No betting advice.

No selections.

Evidence only.

---

# 10. TRACK & WEATHER SUMMARY

Purpose

Present the most important environmental information affecting today's race.

Displays

Track Rating

↓

Rail Position

↓

Temperature

↓

Wind

↓

Weather

↓

Rainfall

↓

Humidity

↓

Operational Notes

This section summarises.

The dedicated Track and Weather workspaces contain full detail.

---

# 11. OPERATIONAL STATUS

Purpose

Display the current operational state of the race.

Displays

Scratchings

↓

Gear Changes

↓

Stewards Notices

↓

Late Rider Changes

↓

Data Coverage

↓

Builder Status

↓

Last Refresh

No warnings are manufactured.

Only official operational information is displayed.

---

# 12. USER INTERACTION

Hover

Displays

Source

↓

Builder Version

↓

Timestamp

↓

Definition

Click

Navigates directly to the detailed workspace responsible for that information.

Examples

Tempo

→ MAP

Track Rating

→ TRACK

Weather

→ WEATHER

Market

→ MARKET

EPI

→ FORM GUIDE

The Overview acts as the navigation hub.

---

# 13. DATA GOVERNANCE

React Responsibilities

Display

Navigate

Highlight

Responsive Layout

React MUST NEVER

Calculate Tempo

Calculate EPI

Calculate Suitability

Calculate Market Intelligence

Generate Race Commentary

Generate Recommendations

All intelligence originates from canonical builders.

---

# 14. BUILDER RESPONSIBILITIES

Canonical builders provide

Race Summary

↓

Race Conditions

↓

Tempo

↓

EPI

↓

Suitability

↓

Form Momentum

↓

Market Summary

↓

Track Summary

↓

Weather Summary

↓

Operational Status

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

Every value displayed within the Overview Workspace must originate from a governed canonical builder.

The Overview never owns data.

It consumes governed services only.

---

## Data Quality Fields

Each information block exposes

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

Unavailable information displays

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

Primary Border

E5E8EE

Primary Accent

EDGEIQ Blue

Primary Text

1A1A1A

Secondary Text

5C6675

No gradients.

No glossy cards.

No oversized hero banners.

No decorative graphics.

Professional software presentation only.

---

# 17. RESPONSIVE BEHAVIOUR

Desktop

Primary target.

Overview occupies full workspace width.

Laptop

Reduce spacing only.

Tablet

Cards stack vertically.

Navigation behaviour remains unchanged.

Mobile

Not supported during Beta.

---

# 18. PERFORMANCE TARGETS

Workspace Load

Target

<300ms

Navigation

<100ms

Hover

Immediate

Card Rendering

<50ms

No unnecessary React re-rendering.

No duplicate builder requests.

---

# 19. ACCESSIBILITY

Keyboard Navigation

Supported

Focus Indicators

Visible

Contrast

WCAG AA

Every card requires

Accessible Label

Accessible Description

Data Source

Timestamp

Information must never rely solely on colour.

---

# 20. FUTURE EXPANSION

Reserved

Race Confidence Summary

↓

Field Strength Timeline

↓

Historical Race Comparison

↓

Class Progression

↓

AI Evidence Explorer

↓

Operational Timeline

↓

Probability Distribution

↓

Interactive Intelligence Drill-down

These additions extend the workspace.

They never redesign it.

---

# 21. ACCEPTANCE CRITERIA

Overview Workspace is complete when

✓ Race Summary implemented

✓ Key Intelligence implemented

✓ Race Conditions implemented

✓ Key Runners implemented

✓ Market Summary implemented

✓ Track & Weather Summary implemented

✓ Operational Status implemented

✓ Navigation links to detailed workspaces implemented

✓ Canonical builders only

✓ White EDGEIQ Design System implemented

✓ npm build passes

✓ Engineering audits pass

---

# 22. CODEX IMPLEMENTATION CHECKLIST

Codex MUST

Use canonical builders only

Never calculate intelligence in React

Implement Race Summary

Implement Key Intelligence

Implement Race Conditions

Implement Key Runners

Implement Market Summary

Implement Track & Weather Summary

Implement Operational Status

Implement navigation into detailed workspaces

Follow MASTER Design System

Run npm build

Run engineering audits

Capture verification screenshots

Produce implementation report

---

# 23. ENGINEERING GOVERNANCE

This specification is the canonical authority for the Overview Workspace.

Any modification to

Race Summary

Key Intelligence

Navigation

Builder ownership

Workspace layout

or

Operational behaviour

requires

Specification revision

Version increment

Engineering review

Audit update

Implementation must follow this specification exactly.

---

# END OF SPECIFICATION

Specification

SPEC-012

Workspace

OVERVIEW

Status

LOCKED

Authority

EDGEIQ Product Engineering Specification

Revision

1.0

