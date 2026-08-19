# SPEC-004
# EDGEIQ MEETING DETAIL
## PRODUCT ENGINEERING SPECIFICATION
### VERSION 1.0
### STATUS LOCKED

---

# 1. PURPOSE

The Meeting Detail workspace is the operational command centre for an individual race meeting.

Once a meeting has been selected from the Meetings workspace, the analyst remains inside the Meeting Detail workspace while navigating all meeting-level information.

The Meeting Detail workspace is a persistent shell.

Only the content beneath the navigation changes.

The shell itself never reloads.

---

# 2. PRODUCT PHILOSOPHY

The Meeting Detail workspace is designed to answer every operational question relating to a meeting before the analyst begins race analysis.

It should provide complete confidence that the meeting information is current, governed and operationally accurate.

It is not designed to replace the Race workspace.

It prepares the analyst for entering it.

---

# 3. USER GOALS

The analyst should immediately know

• Meeting status

• Weather

• Track

• Rail

• Scratchings

• Gear Changes

• Results

• Operational changes

without leaving the workspace.

---

# 4. WORKSPACE LAYOUT

--------------------------------------------------------

HEADER

--------------------------------------------------------

MEETING INFORMATION STRIP

--------------------------------------------------------

WORKSPACE TABS

--------------------------------------------------------

ACTIVE TAB CONTENT

--------------------------------------------------------

RIGHT OPERATIONAL PANEL

--------------------------------------------------------

The shell remains constant.

Only ACTIVE TAB CONTENT changes.

---

# 5. HEADER

Displays

Track

Meeting Name

Meeting Date

Meeting Status

Current Time

Last Updated

Total Races

First Race

Last Race

Background

FFFFFF

Height

72px

Border Bottom

1px solid #E5E8EE

---

# 6. MEETING INFORMATION STRIP

Displays

Track Rating

Rail Position

Weather

Temperature

Wind

Rainfall

Irrigation

Data Freshness

This strip remains visible regardless of the selected tab.

No intelligence is shown here.

Official operational data only.

---

# 7. WORKSPACE TABS

Locked Order

RACES

SCRATCHINGS

GEAR CHANGES

TRACK

WEATHER

RESULTS

No additional tabs may be inserted without updating this specification.

---

# 8. TAB DESIGN

Inactive

White background

Grey text

Subtle border

Active

EDGEIQ Blue underline

Dark text

No filled backgrounds.

No pill buttons.

No gradients.

---

END OF PART 1


---

# 9. ACTIVE TAB WORKSPACE

## Purpose

The Active Tab Workspace displays the selected operational workspace while preserving the Meeting Detail shell.

Changing tabs must never reload the meeting.

Changing tabs must never lose operational context.

The Meeting Detail shell remains persistent.

Only the content area updates.

---

## Active Workspace Height

Minimum

720px

Preferred

Auto

Maximum

Unlimited

The workspace expands naturally with content.

---

## Workspace Width

100%

No fixed-width content.

All workspaces utilise the available desktop width.

---

# 10. RIGHT OPERATIONAL PANEL

## Purpose

Provides contextual operational information for the currently selected meeting.

This panel complements—not duplicates—the active tab.

---

## Fixed Width

360px

Background

FFFFFF

Border Left

1px solid #E5E8EE

Independent scrolling.

---

## Card Order

Meeting Summary

↓

Current Conditions

↓

Operational Alerts

↓

Feed Status

↓

Data Quality

This order is fixed.

---

# 11. MEETING SUMMARY CARD

Displays

Meeting

Track

State

Meeting Type

First Race

Last Race

Total Races

Current Status

Official information only.

---

# 12. CURRENT CONDITIONS CARD

Displays

Track Rating

Rail Position

Temperature

Wind

Weather

Rainfall

Humidity

Irrigation

Surface Notes (future)

No forecasts.

No estimations.

Only governed data.

---

# 13. OPERATIONAL ALERTS

Purpose

Highlight important operational events.

Examples

Meeting Delayed

Track Downgrade

Rail Movement

Abandoned

Late Scratchings

Stewards Notice

No marketing.

No betting commentary.

No intelligence.

---

# 14. FEED STATUS

Displays

Canonical Builder Version

Feed Timestamp

Coverage

Data Source

Last Successful Refresh

Audit Status

This provides transparency into operational readiness.

---

# 15. TAB NAVIGATION

Selecting another tab

Must

Preserve

Meeting

Selected Day

Scroll Position (where practical)

Filter State

Operational Context

Only the Active Workspace changes.

The shell remains unchanged.

---

# 16. OPENING A RACE

Selecting a race from any meeting tab opens

Race Workspace

Returning from the Race Workspace restores

Meeting

Tab

Scroll Position

Selected Race (where practical)

No reset to Meetings.

---

# 17. DATA GOVERNANCE

React Responsibilities

Display

Navigate

Highlight

Switch Tabs

React MUST NEVER

Generate meeting intelligence

Calculate weather

Estimate track conditions

Modify governed data

Builders are responsible for

Meeting information

Operational state

Track

Weather

Results

Scratchings

Gear Changes

Coverage

Audits

---

# 18. DESIGN SYSTEM COMPLIANCE

Background

FFFFFF

Primary Surface

FFFFFF

Secondary Surface

FAFBFC

Primary Border

E5E8EE

Primary Accent

EDGEIQ Blue

Typography

Master Design System only.

No deviations permitted.

---

END OF PART 2


---

# 19. RESPONSIVE BEHAVIOUR

## Desktop

Primary design target.

Minimum Supported Width

1600px

Preferred Width

1920px

All meeting information remains visible.

No horizontal scrolling.

---

## Laptop

Reduce

Padding

Margins

Card spacing

Typography remains unchanged.

Meeting Information Strip remains visible.

---

## Tablet

Operational Panel moves beneath the Active Workspace.

Meeting shell remains unchanged.

---

## Mobile

Not supported during Beta.

---

# 20. PERFORMANCE TARGETS

Workspace Load

Target

<300ms

Tab Change

<75ms

Meeting Change

<100ms

Open Race

<100ms

Return From Race

<100ms

Hover

Immediate

Search

Instant

Filter

Instant

No unnecessary React re-rendering.

---

# 21. STATE MANAGEMENT

Meeting Detail owns

Selected Meeting

Selected Tab

Operational Context

The Race Workspace owns

Selected Race

Selected Runner

Returning from Race restores

Meeting

Tab

Scroll Position

Meeting Context

No information is lost.

---

# 22. ERROR HANDLING

If data is unavailable

Display

Unavailable

Do NOT

Estimate

Guess

Average

Carry Forward

Invent

Operational integrity always overrides appearance.

---

# 23. DATA QUALITY

Every meeting exposes

Coverage

Builder Version

Timestamp

Audit Status

Canonical Source

Feed Health

Internally available through governed services.

---

# 24. FUTURE EXPANSION

Reserved Workspaces

Stewards

Broadcast

Late Changes

Track Evolution

Operational Timeline

Meeting Health

Veterinary Notices

These additions extend the Meeting Detail workspace.

They never redesign the shell.

---

# 25. ACCESSIBILITY

Keyboard Navigation

Supported

Tab Order

Logical

Focus States

Visible

Contrast

WCAG AA

Information must never rely solely on colour.

---

# 26. ACCEPTANCE CRITERIA

Meeting Detail is complete when

✓ Persistent shell implemented

✓ Meeting Information Strip remains visible

✓ Locked tab order preserved

✓ Active workspace swaps without reloading shell

✓ Right Operational Panel implemented

✓ Meeting context preserved

✓ Race return restores context

✓ White EDGEIQ Design System implemented

✓ npm build passes

✓ All audits pass

---

# 27. CODEX IMPLEMENTATION CHECKLIST

Codex MUST

Implement persistent meeting shell

Implement fixed Meeting Information Strip

Implement locked tab order

Preserve navigation state

Preserve meeting state

Preserve selected tab

Never calculate operational intelligence in React

Consume canonical builders only

Follow MASTER Design System

Run npm build

Run engineering audits

Capture verification screenshots

Provide implementation summary

---

# 28. ENGINEERING GOVERNANCE

This specification is the canonical authority for the Meeting Detail workspace.

Any layout, interaction, navigation or behavioural change requires:

• Specification update

• Version increment

• Engineering review

• Audit update

Implementation must follow this specification exactly.

---

# END OF SPECIFICATION

Specification

SPEC-004

Workspace

MEETING DETAIL

Status

LOCKED

Authority

EDGEIQ Product Engineering Specification

Revision

1.0

