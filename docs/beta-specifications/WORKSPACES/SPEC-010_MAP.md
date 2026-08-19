# SPEC-010
# EDGEIQ MAP
## PRODUCT ENGINEERING SPECIFICATION
### VERSION 1.0
### STATUS LOCKED

---

# 1. PURPOSE

The MAP Workspace is the tactical visualisation engine for EDGEIQ.

Its purpose is to display the projected early race positioning of every runner before the race begins.

The MAP is not a track diagram.

The MAP is not a replay.

The MAP is not a pace chart.

The MAP visualises where every horse is expected to position during the early stages of the race.

---

# 2. PRODUCT PHILOSOPHY

The MAP must answer

"What will this race look like after the barriers open?"

It provides

Barrier

↓

Early Speed

↓

Projected Position

↓

Field Compression

↓

Race Shape

The analyst interprets the picture.

EDGEIQ does not make the decision.

---

# 3. USER GOALS

Immediately understand

• Expected Leaders

• Midfield

• Backmarkers

• Barrier Influence

• Speed Advantage

• Field Compression

• Effective Barriers

within seconds.

---

# 4. WORKSPACE LAYOUT

----------------------------------------------------

HEADER

----------------------------------------------------

MAP SUMMARY

----------------------------------------------------

SPEED MAP

----------------------------------------------------

RUNNER TABLE

----------------------------------------------------

MAP NOTES

----------------------------------------------------

---

# 5. MAP SUMMARY

Displays

Expected Tempo

↓

Pressure

↓

Leaders

↓

Backmarkers

↓

Data Quality

↓

Last Updated

Card Height

110px

Background

FFFFFF

Border

1px solid #E5E8EE

---

# 6. SPEED MAP

Purpose

Display the projected early race positioning.

The MAP represents Victorian racing.

All races travel

RIGHT

↓

LEFT

The map orientation is fixed.

It must never rotate.

---

# 7. BARRIER AXIS

Barrier Axis Position

RIGHT

Highest Barrier

TOP

Barrier One

BOTTOM

Equal spacing between barriers.

Barrier numbers remain visible at all times.

No barrier group labels.

No Rail.

No Inner.

No Mid.

No Wide.

Barrier numbers only.

---

# 8. PROJECTION LINES

Every runner begins

at its

Effective Barrier.

Projection lines extend

from

Effective Barrier

↓

Projected Speed Position

Projection lines never begin in open space.

They always begin at the barrier.

---

END OF PART 1


---

# 9. EFFECTIVE BARRIER LOGIC

## Purpose

The MAP always displays the runner's

Effective Barrier

NOT

Original Barrier.

Effective Barrier reflects every official scratching that has occurred inside the runner.

The Effective Barrier is the canonical barrier used throughout EDGEIQ.

Original Barrier is retained for historical reference only.

---

## Effective Barrier Algorithm

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

Scratchings

1

3

Horse originally drawn

Barrier 6

Displays

Effective Barrier 4

Every downstream workspace uses the Effective Barrier.

This includes

MAP

↓

Overview

↓

Insights

↓

Race Shape

↓

Future Intelligence

React performs no calculations.

Builders calculate Effective Barrier.

---

# 10. PROJECTION LINES

Projection Lines begin

Exactly at

Effective Barrier.

They terminate

At

Projected Early Position.

Projection lines are continuous.

No gaps.

No floating labels.

No disconnected graphics.

---

## Line Style

Colour

EDGEIQ Blue

Thickness

2px

Style

Solid

Opacity

100%

All runners use identical styling.

No colour coding.

No gradients.

No heat map.

---

# 11. HORSE LABELS

Each projection line displays

Saddlecloth Number

↓

Horse Name

↓

Projected Speed Value

Position

Immediately beside the projected speed value.

Horse names are never displayed only at the end of the lane.

Labels remain attached to the projected position.

---

## Saddlecloth Numbers

Displayed

To the LEFT

of the Horse Name.

Displayed

Plain Text.

No coloured circles.

No coloured boxes.

No backgrounds.

---

## Speed Values

Displayed

Immediately beside

Horse Name.

Single decimal place.

No arrows.

No icons.

---

# 12. RUNNER TABLE

Purpose

Provide numerical reference for the visual map.

---

LOCKED COLUMN ORDER

NO

HORSE

BARRIER

EFFECTIVE BARRIER

RUN STYLE

EARLY SPEED

PROJECTED POSITION

---

## Table Rules

Runner Number

Plain Text.

Horse

Bold.

Barrier

Centre.

Effective Barrier

Centre.

Run Style

Plain Text.

No coloured dots.

No icons.

Early Speed

One decimal place.

Projected Position

Text only.

---

# 13. REMOVED COMPONENTS

The following are permanently excluded.

Heat Map

↓

Speed Advantage Heat Map

↓

Racing Direction Arrow

↓

Barrier Group Labels

Rail

Inner

Mid

Wide

↓

Coloured Run Style Dots

↓

Coloured Barrier Numbers

These are not part of the EDGEIQ MAP specification.

---

END OF PART 2


---

# 14. DATA GOVERNANCE

## React Responsibilities

React is responsible for

Display

Layout

Hover

Filtering

Search

Navigation

Responsive Rendering

React MUST NEVER

Calculate Early Speed

Calculate Effective Barriers

Calculate Projected Position

Calculate Tempo

Calculate Race Shape

Estimate Runner Positions

Modify MAP Intelligence

Everything displayed within the MAP originates from governed builders.

---

## Builder Responsibilities

Canonical MAP Builders produce

Effective Barrier

↓

Early Speed

↓

Projected Position

↓

Run Style

↓

Tempo

↓

Pressure

↓

Coverage

↓

Builder Version

↓

Audit Reports

Builder output is the single source of truth.

---

# 15. DATA QUALITY

Every MAP record exposes

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

Projection Lines

EDGEIQ Blue

Thickness

2px

No gradients.

No glow.

No shadows.

No coloured lanes.

Professional software presentation only.

---

# 17. RESPONSIVE BEHAVIOUR

Desktop

Primary target.

Speed Map occupies maximum available width.

Laptop

Reduce margins only.

Tablet

Runner Table moves beneath Speed Map.

Mobile

Not supported during Beta.

---

# 18. PERFORMANCE TARGETS

Workspace Load

<300ms

Runner Selection

<100ms

MAP Refresh

<100ms

Hover

Immediate

Search

Instant

No unnecessary React re-rendering.

---

# 19. ACCESSIBILITY

Keyboard Navigation

Supported

Focus Indicators

Visible

Contrast

WCAG AA

Projection Lines

Always supported by textual data in the Runner Table.

Information must never rely solely on graphics.

---

# 20. FUTURE EXPANSION

Reserved

Animated Race Playback

↓

Stride Length Overlay

↓

Acceleration Curves

↓

Historical MAP Comparison

↓

GPS Position Replay

↓

Sectional Synchronisation

↓

Pressure Evolution

↓

Live Running Updates

These additions extend the workspace.

They never redesign it.

---

# 21. ACCEPTANCE CRITERIA

MAP Workspace is complete when

✓ Victorian orientation implemented

✓ Right-to-left race flow

✓ Barrier 1 displayed at bottom

✓ Highest barrier displayed at top

✓ Effective Barrier implemented

✓ Projection lines originate at Effective Barrier

✓ Horse names displayed beside projected speed values

✓ Saddlecloth number displayed left of horse name

✓ Uniform EDGEIQ blue lanes

✓ Runner Table follows locked column order

✓ Heat Map removed

✓ Racing Direction Arrow removed

✓ Barrier Group Labels removed

✓ Coloured Run Style Dots removed

✓ Canonical builders only

✓ White EDGEIQ Design System implemented

✓ npm build passes

✓ Engineering audits pass

---

# 22. CODEX IMPLEMENTATION CHECKLIST

Codex MUST

Use canonical MAP builders

Never calculate MAP intelligence in React

Implement Effective Barrier logic

Implement Projection Lines

Implement Horse Labels beside speed values

Implement Runner Table

Implement uniform EDGEIQ blue lanes

Remove Heat Map

Remove Racing Direction Arrow

Remove Barrier Group Labels

Remove Coloured Run Style Dots

Follow MASTER Design System

Run npm build

Run engineering audits

Capture verification screenshots

Produce implementation report

---

# 23. ENGINEERING GOVERNANCE

This specification is the canonical authority for the MAP Workspace.

Any modification to

Effective Barrier

Projection Logic

Horse Labels

Runner Table

Builder ownership

Workspace layout

or

MAP behaviour

requires

Specification revision

Version increment

Engineering review

Audit update

Implementation must follow this specification exactly.

---

# END OF SPECIFICATION

Specification

SPEC-010

Workspace

MAP

Status

LOCKED

Authority

EDGEIQ Product Engineering Specification

Revision

1.0

