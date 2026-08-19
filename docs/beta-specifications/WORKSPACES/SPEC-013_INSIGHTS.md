# SPEC-013
# EDGEIQ INSIGHTS
## PRODUCT ENGINEERING SPECIFICATION
### VERSION 1.0
### STATUS LOCKED

---

# 1. PURPOSE

The Insights Workspace is the intelligence workspace of EDGEIQ.

Its purpose is to transform governed racing evidence into concise, explainable intelligence while preserving complete transparency.

Insights are evidence.

They are not predictions.

They are not selections.

They are not betting advice.

Every insight must be traceable back to governed evidence.

---

# 2. PRODUCT PHILOSOPHY

EDGEIQ never asks the user to trust a black box.

Every displayed insight must be explainable.

Every displayed conclusion must be supported.

Every displayed statement must have evidence.

The analyst remains responsible for the final judgement.

---

# 3. USER GOALS

Immediately understand

• Suitability

↓

• Form Momentum

↓

• Speed Profile

↓

• Race Shape Position

↓

• Market Position

↓

• Track Suitability

↓

• Distance Suitability

↓

• Hidden Positives

↓

• Hidden Negatives

without manually searching every dataset.

---

# 4. WORKSPACE LAYOUT

----------------------------------------------------

HEADER

----------------------------------------------------

INTELLIGENCE SUMMARY

----------------------------------------------------

EVIDENCE PANELS

----------------------------------------------------

DETAILED INSIGHTS

----------------------------------------------------

SUPPORTING EVIDENCE

----------------------------------------------------

DATA QUALITY

----------------------------------------------------

---

# 5. INTELLIGENCE SUMMARY

Displays

Overall Intelligence Summary

↓

Best Positive

↓

Largest Risk

↓

Strongest Evidence

↓

Weakest Evidence

↓

Coverage

↓

Last Updated

Purpose

Provide a concise race briefing before deeper investigation.

No selections.

No betting advice.

---

# 6. EVIDENCE PANELS

Displays

Suitability

↓

Form Momentum

↓

Early Speed

↓

Late Speed

↓

Market Position

↓

Track Profile

↓

Distance Profile

↓

Barrier Profile

Each panel displays

Headline

↓

Evidence Summary

↓

Confidence (Evidence Quality)

↓

Expand

Confidence represents

Evidence Quality

NOT

Winning Chance.

---

# 7. DETAILED INSIGHTS

Purpose

Provide explainable intelligence.

Every insight contains

Headline

↓

Evidence

↓

Supporting Factors

↓

Data Source

↓

Builder Version

↓

Timestamp

Every statement must be explainable.

No unsupported commentary.

---

# 8. SUPPORTING EVIDENCE

Expandable.

Displays

Historical Runs

↓

Benchmark Figures

↓

Suitability Components

↓

Momentum Components

↓

Speed Components

↓

Market Components

↓

Track Components

↓

Distance Components

This section explains

WHY

the insight exists.

---

END OF PART 1


---

# 9. EXPLAINABILITY

## Purpose

Every insight displayed within EDGEIQ must be fully explainable.

Users must always be able to understand

What

Why

Where

When

How

an insight was produced.

No black-box intelligence is permitted.

---

## Explainability Hierarchy

Insight

↓

Evidence Groups

↓

Supporting Metrics

↓

Historical Evidence

↓

Canonical Builder

↓

Source Data

Every insight must trace completely through this hierarchy.

---

# 10. EVIDENCE QUALITY

Purpose

Communicate the strength of available evidence.

Evidence Quality is NOT

Winning Chance

Probability

Confidence of Success

Instead it represents

Completeness

Consistency

Reliability

Coverage

Freshness

of the supporting evidence.

---

## Evidence Quality Scale

Very High

High

Moderate

Limited

Unavailable

This scale reflects data quality only.

---

## Colour Rules

Very High

EDGEIQ Green

High

Blue

Moderate

Amber

Limited

Grey

Unavailable

Light Grey

Colour is supplementary.

The wording always remains visible.

---

# 11. SUPPORTING EVIDENCE

Selecting an insight expands

Historical Runs

↓

Benchmark Sectionals

↓

Track Profile

↓

Distance Profile

↓

Barrier Profile

↓

Suitability Components

↓

Momentum Components

↓

Speed Components

↓

Market Components

↓

Official Source

↓

Builder Version

↓

Timestamp

Every insight is backed by governed evidence.

---

# 12. INTELLIGENCE RULES

Insights must never

Recommend Bets

Recommend Horses

Recommend Markets

Generate Tips

Use subjective language.

Preferred wording

Strong historical suitability.

Track profile remains favourable.

Limited evidence under today's conditions.

Momentum improving.

Late speed profile strengthening.

Avoid wording such as

Best Bet

Good Thing

Should Win

Back This Horse

Confidence remains evidence quality only.

---

# 13. USER INTERACTION

Hover

Displays

Definition

↓

Builder

↓

Timestamp

↓

Coverage

↓

Source

Expand

Displays

Full evidence hierarchy.

Collapse

Returns to summary.

No hidden calculations occur within React.

---

# 14. DATA GOVERNANCE

React Responsibilities

Display

Expand

Collapse

Navigate

Highlight

Responsive Layout

React MUST NEVER

Generate Insights

Interpret Evidence

Calculate Suitability

Calculate Momentum

Calculate Speed

Generate Commentary

Everything originates from governed builders.

---

# 15. BUILDER RESPONSIBILITIES

Canonical builders provide

Insights

↓

Suitability

↓

Momentum

↓

Speed

↓

Track Intelligence

↓

Distance Intelligence

↓

Market Intelligence

↓

Evidence Quality

↓

Coverage

↓

Audit Reports

Builder output is the single source of truth.

---

END OF PART 2


---

# 16. DATA QUALITY

## Canonical Source

Every insight displayed within the Insights Workspace originates from governed canonical builders.

Insights never own data.

They consume governed intelligence only.

---

## Data Quality Fields

Each insight exposes

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

Unavailable evidence displays

Unavailable

Never estimated.

Never inferred.

Never fabricated.

---

# 17. DESIGN SYSTEM COMPLIANCE

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

Evidence Quality

Very High

EDGEIQ Green

High

EDGEIQ Blue

Moderate

Amber

Limited

Grey

Unavailable

Light Grey

No gradients.

No glowing cards.

No oversized banners.

Professional analytical software only.

---

# 18. RESPONSIVE BEHAVIOUR

Desktop

Primary target.

Evidence Panels displayed in responsive grid.

Detailed Insights occupy full workspace width.

Laptop

Reduce spacing only.

Tablet

Evidence Panels stack vertically.

Supporting Evidence remains expandable.

Mobile

Not supported during Beta.

---

# 19. PERFORMANCE TARGETS

Workspace Load

Target

<300ms

Expand Insight

<100ms

Collapse Insight

<100ms

Hover

Immediate

Navigation

<100ms

No unnecessary React re-rendering.

No duplicated builder requests.

---

# 20. ACCESSIBILITY

Keyboard Navigation

Supported

Focus Indicators

Visible

Contrast

WCAG AA

Every Evidence Panel requires

Accessible Label

Accessible Description

Builder Version

Timestamp

Evidence Quality

Information must never rely solely on colour.

---

# 21. FUTURE EXPANSION

Reserved

AI Evidence Explorer

↓

Historical Intelligence Timeline

↓

Evidence Relationships

↓

Runner Comparison

↓

Intelligence Evolution

↓

Stable Intelligence

↓

Interactive Evidence Graph

↓

Cross-Race Intelligence

These additions extend the workspace.

They never redesign it.

---

# 22. ACCEPTANCE CRITERIA

Insights Workspace is complete when

✓ Intelligence Summary implemented

✓ Evidence Panels implemented

✓ Detailed Insights implemented

✓ Supporting Evidence implemented

✓ Explainability hierarchy implemented

✓ Evidence Quality implemented

✓ Expand / Collapse implemented

✓ Canonical builders only

✓ White EDGEIQ Design System implemented

✓ React remains display only

✓ npm build passes

✓ Engineering audits pass

---

# 23. CODEX IMPLEMENTATION CHECKLIST

Codex MUST

Use canonical intelligence builders

Never calculate intelligence in React

Implement Intelligence Summary

Implement Evidence Panels

Implement Detailed Insights

Implement Supporting Evidence

Implement Explainability hierarchy

Implement Evidence Quality

Implement Expand / Collapse

Follow MASTER Design System

Run npm build

Run engineering audits

Capture verification screenshots

Produce implementation report

---

# 24. ENGINEERING GOVERNANCE

This specification is the canonical authority for the Insights Workspace.

Any modification to

Insight generation

Evidence hierarchy

Evidence Quality

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

SPEC-013

Workspace

INSIGHTS

Status

LOCKED

Authority

EDGEIQ Product Engineering Specification

Revision

1.0

