# SPEC-005
# EDGEIQ SCRATCHINGS
## PRODUCT ENGINEERING SPECIFICATION
### VERSION 1.0
### STATUS LOCKED

---

# 1. PURPOSE

The Scratchings Workspace is the operational authority for all withdrawn runners.

It exists to answer one question:

"What has changed since acceptances?"

Every scratching must automatically flow through the remainder of EDGEIQ.

No manual refresh.

No duplicated calculations.

No secondary maintenance.

---

# 2. PRODUCT PHILOSOPHY

Scratchings are operational events.

They are not merely removed horses.

A scratching changes

• Effective barriers

• Speed Map

• Race Shape

• Early Speed

• Pace Pressure

• Market

• Field Size

• Emergencies

The Scratchings workspace is therefore an operational control centre.

---

# 3. USER GOALS

Immediately identify

• Which horses are scratched

• When they were scratched

• Why they were scratched

• Which races are affected

• Which emergencies gained a start

• Which barriers changed

• Which maps changed

within seconds.

---

# 4. WORKSPACE LAYOUT

----------------------------------------------------

HEADER

----------------------------------------------------

SUMMARY CARDS

----------------------------------------------------

SCRATCHINGS TABLE

----------------------------------------------------

RACE IMPACT PANEL

----------------------------------------------------

OPERATIONAL LOG

----------------------------------------------------

---

# 5. SUMMARY CARDS

Displays

Total Scratchings

↓

Affected Races

↓

Emergency Promotions

↓

Last Updated

Card Height

110px

Background

FFFFFF

Border

1px solid #E5E8EE

---

# 6. SCRATCHINGS TABLE

Purpose

Display every official scratching.

One row

One scratching.

No grouped rows.

---

LOCKED COLUMN ORDER

RACE

NO

HORSE

TRAINER

ORIGINAL BARRIER

EFFECTIVE BARRIER

SCRATCHED

REASON

STATUS

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

No coloured background.

---

HORSE

Width

240px

Left

Primary identifier.

Bold.

---

TRAINER

Width

180px

Left

---

ORIGINAL BARRIER

Width

90px

Centre

Official barrier allocated at acceptance time.

Never changes.

---

EFFECTIVE BARRIER

Width

90px

Centre

Automatically recalculated.

Reflects the horse's barrier after all inside scratchings.

This value feeds every downstream workspace.

---

SCRATCHED

Width

150px

Centre

Official scratching timestamp.

---

REASON

Width

220px

Left

Official reason only.

Examples

Lame

Veterinary Advice

Trainer

Stewards

Transport

No interpretation.

---

STATUS

Width

120px

Centre

Official operational status.

---

# 8. EFFECTIVE BARRIER ALGORITHM

Purpose

Every scratching automatically compresses barriers inward.

Example

Original Field

1

2

3

4

5

6

7

8

Horse in Barrier

6

Scratchings

1

3

Effective Barrier

4

This effective barrier becomes the canonical value used by

MAP

Race Shape

Early Speed

Overview

Insights

Future analytics

The original barrier is never modified.

---

# 9. EMERGENCY PROMOTIONS

When an emergency gains a start

Display

Emergency Runner

Promotion Time

Replaced Runner

New Effective Barrier

Status

Promoted runners immediately become part of the canonical race field.

No manual refresh required.

---

# 10. MAP INTEGRATION

Every scratching automatically updates

Effective Barrier

↓

Speed Map

↓

Projected Position

↓

Race Shape

↓

Overview

↓

Insights

React never performs these calculations.

Builders update the canonical data.

---

# 11. RACE SHAPE INTEGRATION

Scratchings can materially alter

Expected Tempo

Pressure

On-speed runners

Backmarker opportunities

These changes originate from the Race Shape builder.

Scratchings Workspace only displays operational information.

---

# 12. NAVIGATION

Selecting a scratching

↓

Opens corresponding race

↓

Preserves Meeting

↓

Preserves selected tab

↓

Preserves scroll position

No unnecessary navigation resets.

---

END OF PART 2


---

# 13. OPERATIONAL TIMELINE

## Purpose

The Operational Timeline provides a complete chronological record of every scratching-related event for the meeting.

This is an audit trail.

It is not editable.

---

Displays

Time

↓

Race

↓

Horse

↓

Event

↓

Reason

↓

Source

↓

Processed

Every operational event is timestamped.

Newest events appear first.

---

# 14. DATA GOVERNANCE

React Responsibilities

Display

Filter

Sort

Navigate

Highlight

React MUST NEVER

Calculate Effective Barriers

Modify Barriers

Generate Scratchings

Generate Emergencies

Modify Race Shape

Modify MAP

Everything originates from canonical builders.

---

Builder Responsibilities

Official Scratchings

Emergency Promotions

Effective Barrier Calculation

Race Field Updates

MAP Refresh

Race Shape Refresh

Overview Refresh

Coverage Reports

Audit Reports

Builder output is the single source of truth.

---

# 15. DATA QUALITY

Each scratching record exposes

Official Timestamp

Builder Timestamp

Coverage Status

Canonical Source

Audit Version

Feed Status

Unavailable data is displayed as

Unavailable

Never estimated.

---

# 16. RESPONSIVE BEHAVIOUR

Desktop

Primary layout.

No horizontal scrolling.

Laptop

Reduce margins only.

Tablet

Race Impact Panel moves beneath table.

Mobile

Not supported during Beta.

---

# 17. PERFORMANCE TARGETS

Workspace Load

<300ms

Effective Barrier Update

<100ms

MAP Refresh

<100ms

Race Shape Refresh

<100ms

Search

Instant

Filter

Instant

Hover

Immediate

---

# 18. ACCESSIBILITY

Keyboard Navigation

Supported

Focus Indicators

Visible

Contrast

WCAG AA

Operational information must never rely solely on colour.

---

# 19. FUTURE EXPANSION

Reserved

Late Rider Changes

Emergency Acceptance Timeline

Veterinary Notifications

Stable Notifications

Stewards Operational Feed

Broadcast Status

Track Inspection Timeline

These additions extend the workspace.

They never redesign it.

---

# 20. ACCEPTANCE CRITERIA

Scratchings Workspace is complete when

✓ Official scratchings displayed

✓ Locked column order implemented

✓ Original Barrier preserved

✓ Effective Barrier calculated correctly

✓ Emergency promotions displayed

✓ MAP refreshes automatically

✓ Race Shape refreshes automatically

✓ Overview refreshes automatically

✓ Meeting context preserved

✓ White EDGEIQ Design System implemented

✓ npm build passes

✓ Engineering audits pass

---

# 21. CODEX IMPLEMENTATION CHECKLIST

Codex MUST

Use canonical scratching builder

Never calculate effective barriers in React

Implement automatic barrier compression

Refresh MAP automatically

Refresh Race Shape automatically

Refresh Overview automatically

Preserve Meeting Detail state

Preserve selected race

Follow EDGEIQ Design System

Run npm build

Run engineering audits

Capture verification screenshots

Produce implementation report

---

# 22. ENGINEERING GOVERNANCE

This specification is the canonical authority for the Scratchings workspace.

Any modification to

Barrier logic

Emergency logic

MAP integration

Race Shape integration

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

SPEC-005

Workspace

SCRATCHINGS

Status

LOCKED

Authority

EDGEIQ Product Engineering Specification

Revision

1.0

