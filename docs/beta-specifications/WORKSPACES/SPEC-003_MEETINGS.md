# SPEC-003
# EDGEIQ MEETINGS
## PRODUCT ENGINEERING SPECIFICATION
### VERSION 1.0
### STATUS LOCKED

---

# 1. PURPOSE

The Meetings Workspace is the operational home page of EDGEIQ.

It is the first workspace every user sees after entering the platform.

Its responsibility is not to analyse races.

Its responsibility is to answer

"What meetings deserve my attention today?"

The workspace must allow a professional analyst to understand the entire Australian racing day in less than thirty seconds.

---

# 2. PRODUCT PHILOSOPHY

The Meetings workspace is an operations console.

Not a racecard.

Not a website.

Not a dashboard.

The design language is that of professional analytical software.

Every meeting should be immediately comparable.

No meeting should dominate the interface.

Information density is preferred over oversized graphics.

---

# 3. USER GOALS

The analyst should immediately know

• Which meetings are available

• Which meetings are metropolitan

• Track conditions

• Rail positions

• Weather

• Number of races

• First race

• Last race

• Status

• Which meeting requires attention

within one screen.

---

# 4. WORKSPACE LAYOUT

----------------------------------------------------

HEADER

----------------------------------------------------

DAY SELECTOR

TODAY

TOMORROW

DAY +2

----------------------------------------------------

SEARCH / FILTER BAR

----------------------------------------------------

MEETING TABLE

----------------------------------------------------

RIGHT OPERATIONAL PANEL

----------------------------------------------------

---

# 5. HEADER

Displays

EDGEIQ

Meetings

Current Date

Australia/Melbourne Time

Last Refresh

Total Meetings

Total Races

Refresh Button

Header Height

72px

Background

FFFFFF

Border Bottom

E5E8EE

---

# 6. DAY SELECTOR

Three buttons only

TODAY

TOMORROW

DAY +2

These values come exclusively from

edgeiq_three_day_window_v1.json

No hard coded dates.

No local browser dates.

The canonical window controls everything.

---

# 7. SEARCH BAR

Searches

Meeting

Track

State

Supports

Partial Match

Case Insensitive

Instant Search

No submit button.

---

# 8. FILTERS

State

Metro

Country

Status

Track Condition

Weather

All filters operate client-side only.

No React intelligence.

---

# 9. MEETING TABLE

Purpose

Provide a complete operational summary of every meeting.

No scrolling required on standard desktop resolutions where practical.

---

LOCKED COLUMN ORDER

TRACK

STATE

FIRST

LAST

RACES

TRACK

RAIL

WEATHER

TEMP

WIND

STATUS

OPEN

This order is frozen.

---

END OF PART 1


---

# 10. MEETING TABLE

## Purpose

The Meeting Table is the operational heart of the Meetings workspace.

It provides a complete overview of every meeting within the current three-day rolling window.

The table is designed for rapid comparison rather than deep analysis.

Users should be able to identify the meeting they wish to investigate within seconds.

---

## Layout

Full Width

100%

No cards.

No tiles.

No oversized graphics.

Professional data table only.

---

## Table Dimensions

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

## Locked Column Specification

TRACK

Width

220px

Alignment

Left

Displays

Track Name

Meeting Type

Meeting Status

---

STATE

Width

70px

Centre

---

FIRST

Width

90px

Centre

Official first race time.

---

LAST

Width

90px

Centre

Official final race time.

---

RACES

Width

70px

Centre

Total races scheduled.

---

TRACK

Width

90px

Centre

Official track rating.

Examples

Good 4

Soft 6

Heavy 8

Synthetic

---

RAIL

Width

120px

Centre

Official rail position exactly as published.

---

WEATHER

Width

120px

Centre

Current weather summary.

Never estimated.

---

TEMP

Width

70px

Centre

Current temperature.

Display

18°

Not

18.3°C

---

WIND

Width

120px

Centre

Direction

+

Speed

Example

NW 18 km/h

---

STATUS

Width

110px

Centre

Scheduled

Abandoned

Completed

Delayed

Running

Official terminology only.

---

OPEN

Width

90px

Centre

Primary action.

Selecting OPEN enters the Meeting Detail workspace.

No secondary actions.

---

# 11. TABLE DESIGN RULES

No vertical column lines.

Horizontal separators only.

No alternating row colours.

Hover

Very Light EDGEIQ Blue

Selection

Blue border only.

No filled blue rows.

Typography never changes.

No icons unless operationally meaningful.

---

# 12. SORTING

Sortable

Track

State

First Race

Last Race

Race Count

Track Rating

Temperature

Status

Default Sort

First Race

Ascending

No hidden sorting.

Current sort always visible.

---

# 13. SEARCH

Search supports

Track

Meeting

State

Instant filtering.

No submit button.

Case insensitive.

Partial matching.

---

# 14. FILTERS

Today's Meetings

Tomorrow

Day +2

State

Metro

Country

Status

Track Rating

Weather

Filters never modify canonical data.

Only displayed rows change.

---

# 15. ROW INTERACTION

Hover

Blue highlight.

Click

Select meeting.

Double Click

Optional future shortcut to Meeting Detail.

OPEN

Loads Meeting Detail.

Current day selection remains preserved.

---

END OF PART 2


---

# 16. RIGHT OPERATIONAL PANEL

## Purpose

The Right Operational Panel provides a concise operational summary of the selected meeting without requiring the analyst to enter the Meeting Detail workspace.

It is designed to answer:

• Is this meeting worth analysing now?

• Has anything operationally changed?

• Are there any issues requiring attention?

The panel supplements the Meeting Table. It never replaces it.

---

## Layout

Fixed Width

360px

Full Height

Independent vertical scrolling.

Always visible on desktop.

Background

FFFFFF

Border Left

1px solid #E5E8EE

---

## Card Order

Meeting Summary

↓

Track Conditions

↓

Weather Summary

↓

Operational Alerts

↓

Data Status

This order is fixed.

---

# 17. MEETING SUMMARY

Displays

Track

State

Meeting Type

First Race

Last Race

Race Count

Meeting Status

Last Updated

No intelligence appears here.

Official operational information only.

---

# 18. TRACK CONDITIONS

Displays

Track Rating

Rail Position

Penetrometer (when available)

Irrigation

Rainfall 24 Hours

Rainfall 7 Days

Track Manager Notes (future)

Official values only.

---

# 19. WEATHER SUMMARY

Displays

Temperature

Wind

Humidity

Rainfall

Cloud Cover

Conditions

Sunrise

Sunset

No radar.

No forecast confidence.

No estimated values.

Unavailable remains unavailable.

---

# 20. OPERATIONAL ALERTS

Displays only factual operational notices.

Examples

Late Track Downgrade

Rail Change

Meeting Delay

Abandonment

Stewards Notice

No marketing messages.

No promotional content.

No betting commentary.

---

# 21. DATA STATUS

Purpose

Communicate data quality.

Displays

Current Feed Status

Last Successful Update

Canonical Builder Version

Coverage Status

Builder Timestamp

Audit Status

This allows analysts to understand the freshness and completeness of the operational data.

---

# 22. THREE-DAY WINDOW

The Meetings workspace MUST use

edgeiq_three_day_window_v1.json

as the single source of truth.

React MUST NEVER

Generate dates

Calculate offsets

Use browser dates

Use JavaScript Date()

The builder is the authority.

---

# 23. NAVIGATION

Workflow

MEETINGS

↓

Meeting Selected

↓

Meeting Detail

↓

Race

↓

Race Workspace

↓

Return

↓

Meeting Detail

↓

Return

↓

Meetings

Selected meeting

Selected day

Search

Filters

must all be preserved.

---

# 24. RESPONSIVE BEHAVIOUR

Desktop

Full layout.

Laptop

Reduce spacing only.

Tablet

Operational panel collapses beneath table.

Mobile

Not part of Beta.

---

# 25. PERFORMANCE TARGETS

Workspace Load

<300ms

Meeting Selection

<100ms

Filter

<50ms

Search

Instant

Hover

Immediate

No unnecessary re-rendering.

---

# 26. DATA GOVERNANCE

React Responsibilities

Display

Filter

Sort

Navigate

Highlight

React MUST NEVER

Calculate dates

Generate meetings

Estimate weather

Generate intelligence

Modify canonical data

Builders are responsible for

Meeting generation

Three-day window

Track

Weather

Operational status

Coverage

Audits

---

# 27. FUTURE EXPANSION

Reserved

Meeting Ratings

Operational Risk

Meeting Health

Track Evolution

Late Intelligence

Video Status

Broadcast Status

These additions extend the panel.

They never redesign the workspace.

---

# 28. ACCEPTANCE CRITERIA

The Meetings Workspace is complete when

✓ Canonical three-day window is used

✓ Meeting table follows locked column order

✓ Right operational panel implemented

✓ Search operates instantly

✓ Filters preserve state

✓ Meeting selection preserved

✓ Navigation preserved

✓ White EDGEIQ design system

✓ Build passes

✓ All audits pass

---

# 29. CODEX IMPLEMENTATION CHECKLIST

Codex MUST

Use canonical rolling window

Never calculate dates in React

Preserve selected meeting

Preserve selected day

Implement right operational panel

Maintain locked column order

Follow EDGEIQ Design System

Run npm build

Run audits

Capture screenshots

Produce completion report

---

# END OF SPECIFICATION

Specification

SPEC-003

Workspace

MEETINGS

Status

LOCKED

Authority

EDGEIQ Product Engineering Specification

Revision

Version changes require formal specification updates only.

