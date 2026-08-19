# SPEC-015
# EDGEIQ RUNNER PROFILE
## PRODUCT ENGINEERING SPECIFICATION
### VERSION 1.0
### STATUS LOCKED

---

# 1. PURPOSE

The Runner Profile Workspace is the complete intelligence dossier for an individual runner.

It consolidates every governed source of intelligence into a single location, allowing analysts to understand the horse's historical profile, current profile and today's suitability without navigating multiple workspaces.

The Runner Profile is evidence.

It is never a prediction engine.

---

# 2. PRODUCT PHILOSOPHY

The Runner Profile answers one question.

"What do we know about this horse?"

Everything displayed must originate from governed evidence.

Nothing is estimated.

Nothing is inferred inside React.

The Runner Profile becomes the permanent intelligence record for each runner.

---

# 3. USER GOALS

Immediately understand

• Career Profile

↓

• Current Preparation

↓

• Historical Performance

↓

• EPI Profile

↓

• Suitability

↓

• Speed Profile

↓

• Trainer

↓

• Jockey

↓

• Barrier

↓

• Weight

↓

• Market Position

↓

• Intelligence Summary

without opening multiple workspaces.

---

# 4. WORKSPACE LAYOUT

----------------------------------------------------

HEADER

----------------------------------------------------

RUNNER SUMMARY

----------------------------------------------------

CAREER PROFILE

----------------------------------------------------

CURRENT PREPARATION

----------------------------------------------------

PERFORMANCE PROFILE

----------------------------------------------------

TODAY'S PROFILE

----------------------------------------------------

INTELLIGENCE SUMMARY

----------------------------------------------------

DATA QUALITY

----------------------------------------------------

---

# 5. RUNNER SUMMARY

Displays

Horse Name

↓

Age

↓

Sex

↓

Colour

↓

Trainer

↓

Jockey

↓

Barrier

↓

Weight

↓

Current Market

↓

Current EPI

↓

Last Updated

Card Height

110px

Background

FFFFFF

Border

1px solid #E5E8EE

---

# 6. CAREER PROFILE

Displays

Career Starts

↓

Wins

↓

Seconds

↓

Thirds

↓

Win %

↓

Place %

↓

Peak EPI

↓

Average EPI

↓

Career Prize Money

↓

Average Prize

Official values only.

---

# 7. CURRENT PREPARATION

Displays

Preparation Stage

↓

Days Since Last Start

↓

First Up

↓

Second Up

↓

Third Up

↓

Current Campaign Starts

↓

Preparation EPI

↓

Preparation Trend

Evidence only.

No prediction.

---

# 8. PERFORMANCE PROFILE

Displays

Track Profile

↓

Distance Profile

↓

Track/Distance Profile

↓

Class Profile

↓

Going Profile

↓

Barrier Profile

↓

Jockey Profile

↓

Trainer Profile

↓

Historical Suitability

Every profile links to governed evidence.

---

END OF PART 1


---

# 9. TODAY'S PROFILE

## Purpose

Today's Profile presents every governed factor directly relevant to today's race.

It is the bridge between historical performance and today's conditions.

This section is race-specific.

It does not duplicate the Career Profile.

---

## Displays

Today's EPI

↓

Suitability

↓

Form Momentum

↓

Early Speed

↓

Late Speed

↓

Barrier

↓

Weight

↓

Track Suitability

↓

Distance Suitability

↓

Going Suitability

↓

Market Position

↓

Race Shape Position

All values originate from governed builders.

No React calculations.

---

# 10. INTELLIGENCE SUMMARY

Purpose

Provide a concise intelligence briefing for the selected runner.

Displays

Primary Strength

↓

Primary Risk

↓

Best Historical Match

↓

Current Preparation Summary

↓

Evidence Quality

↓

Coverage

↓

Last Updated

The summary provides direction only.

It never replaces detailed evidence.

---

# 11. CONNECTIONS

Displays

Trainer

↓

Trainer Strike Rate

↓

Trainer Place Rate

↓

Trainer/EPI History

↓

Jockey

↓

Jockey Strike Rate

↓

Jockey Place Rate

↓

Trainer/Jockey Combination

↓

Historical Combination Performance

Official statistics only.

No opinion.

---

# 12. SUITABILITY PROFILE

Displays

Track

↓

Distance

↓

Track & Distance

↓

Barrier

↓

Going

↓

Class

↓

Preparation Stage

↓

Field Size

Each suitability component is displayed independently.

No single suitability score replaces individual evidence.

---

# 13. SPEED PROFILE

Displays

Early Speed Rating

↓

Late Speed Rating

↓

Average Early Position

↓

Average Mid-Race Position

↓

Average Finish Position

↓

Historical Speed Trend

↓

Running Style

↓

Historical Pace Participation

Evidence only.

No predicted finishing position.

---

# 14. HISTORICAL PERFORMANCE

Displays

Last 5 Starts

↓

Last 10 Starts

↓

Peak Performance

↓

Average Performance

↓

Worst Performance

↓

Career Trend

↓

Historical EPI Distribution

Links directly to the EPI Workspace.

No duplicated calculations.

---

# 15. USER INTERACTION

Selecting

Track

↓

Distance

↓

Trainer

↓

Jockey

↓

Historical Run

↓

EPI

navigates directly to the corresponding EDGEIQ workspace where applicable.

Hover displays

Definition

↓

Builder Version

↓

Timestamp

↓

Coverage

↓

Source

No hidden calculations.

---

END OF PART 2


---

# 16. DATA GOVERNANCE

## React Responsibilities

React is responsible for

Display

Navigate

Search

Highlight

Expand

Collapse

Responsive Layout

Synchronise Components

React MUST NEVER

Calculate EPI

Calculate Suitability

Calculate Form Momentum

Calculate Early Speed

Calculate Late Speed

Calculate Historical Statistics

Calculate Connections

Generate Commentary

Generate Recommendations

Estimate Missing Values

All intelligence originates from governed canonical builders.

---

## Builder Responsibilities

Canonical builders provide

Runner Identity

↓

Career Statistics

↓

Current Preparation

↓

Historical Performance

↓

Historical EPI

↓

Current EPI

↓

Suitability

↓

Form Momentum

↓

Early Speed

↓

Late Speed

↓

Connections

↓

Market Intelligence

↓

Coverage

↓

Builder Version

↓

Audit Reports

Builder output is the single source of truth.

---

# 17. DATA QUALITY

Every runner record exposes

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

Never fabricated.

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

No gradients.

No glossy panels.

No decorative graphics.

Professional analytical software only.

---

# 19. RESPONSIVE BEHAVIOUR

Desktop

Primary target.

Runner Summary

↓

Career Profile

↓

Current Preparation

↓

Performance Profile

↓

Today's Profile

↓

Intelligence Summary

display vertically in this order.

Laptop

Reduce spacing only.

Tablet

Cards stack vertically.

Mobile

Not supported during Beta.

---

# 20. PERFORMANCE TARGETS

Workspace Load

Target

<300ms

Runner Change

<100ms

Expand Panel

<100ms

Hover

Immediate

Navigation

<100ms

Search

Instant

No unnecessary React re-rendering.

No duplicated builder requests.

---

# 21. ACCESSIBILITY

Keyboard Navigation

Supported

Focus Indicators

Visible

Contrast

WCAG AA

Every information panel exposes

Accessible Label

↓

Builder Version

↓

Timestamp

↓

Coverage

↓

Data Source

Information must never rely solely on colour.

---

# 22. FUTURE EXPANSION

Reserved

Bloodlines

↓

Ownership

↓

Veterinary Timeline

↓

Gear Timeline

↓

Training Reports

↓

Trial History

↓

Sectional History

↓

Biomechanics

↓

Video Synchronisation

↓

Career Milestones

These additions extend the workspace.

They never redesign it.

---

# 23. ACCEPTANCE CRITERIA

Runner Profile Workspace is complete when

✓ Runner Summary implemented

✓ Career Profile implemented

✓ Current Preparation implemented

✓ Performance Profile implemented

✓ Today's Profile implemented

✓ Intelligence Summary implemented

✓ Connections implemented

✓ Speed Profile implemented

✓ Historical Performance implemented

✓ Navigation to linked workspaces implemented

✓ Canonical builders only

✓ White EDGEIQ Design System implemented

✓ npm build passes

✓ Engineering audits pass

---

# 24. CODEX IMPLEMENTATION CHECKLIST

Codex MUST

Use canonical runner builders

Never calculate intelligence in React

Implement Runner Summary

Implement Career Profile

Implement Current Preparation

Implement Performance Profile

Implement Today's Profile

Implement Intelligence Summary

Implement Connections

Implement Speed Profile

Implement Historical Performance

Implement workspace navigation

Follow MASTER Design System

Run npm build

Run engineering audits

Capture verification screenshots

Produce implementation report

---

# 25. ENGINEERING GOVERNANCE

This specification is the canonical authority for the Runner Profile Workspace.

Any modification to

Career Profile

Today's Profile

Connections

Historical Performance

Builder ownership

Workspace layout

or

Runner intelligence

requires

Specification revision

Version increment

Engineering review

Audit update

Implementation must follow this specification exactly.

---

# END OF SPECIFICATION

Specification

SPEC-015

Workspace

RUNNER PROFILE

Status

LOCKED

Authority

EDGEIQ Product Engineering Specification

Revision

1.0

