# SPEC-017
# EDGEIQ RACE SHAPE ENGINE
## PRODUCT ENGINEERING SPECIFICATION
### VERSION 1.0
### STATUS LOCKED

---

# 1. PURPOSE

The Race Shape Engine is the canonical tactical intelligence engine of EDGEIQ.

Its responsibility is to model the likely early positioning, tempo, pressure and tactical structure of a race before it is run.

The Race Shape Engine does not predict the winner.

It predicts the likely structure of the race.

Every workspace that references tactical positioning consumes this engine.

---

# 2. PRODUCT PHILOSOPHY

Race Shape is evidence.

Not prediction.

The engine answers

"What is the race likely to look like after the barriers open?"

It provides governed tactical evidence for analysts.

---

# 3. ENGINE RESPONSIBILITIES

The Race Shape Engine produces

Effective Barrier

↓

Early Speed Ranking

↓

Projected Position

↓

Tempo Classification

↓

Pressure Classification

↓

Leader Count

↓

Midfield Structure

↓

Backmarker Structure

↓

Race Shape Summary

↓

Coverage

↓

Builder Version

↓

Audit Output

Every downstream workspace consumes these outputs.

---

# 4. ENGINE INPUTS

Canonical Inputs

Official Field

↓

Official Scratchings

↓

Effective Barriers

↓

Early Speed Ratings

↓

Running Styles

↓

Historical Position Data

↓

Track Configuration

↓

Distance

↓

Field Size

↓

Barrier Positions

↓

Race Conditions

The engine never consumes React state.

Only governed builders.

---

# 5. ENGINE OUTPUTS

Canonical Outputs

Race Shape

↓

Projected Positions

↓

Tempo

↓

Pressure

↓

Field Compression

↓

Leader Map

↓

Coverage

↓

Audit

These outputs become canonical.

React never modifies them.

---

# 6. ENGINE PRINCIPLES

Race Shape is

Deterministic

Repeatable

Auditable

Explainable

Every output must be reproducible from governed inputs.

No random behaviour.

No opaque AI outputs.

---

# 7. TEMPO CLASSIFICATION

Canonical Tempo Values

Very Slow

↓

Slow

↓

Even

↓

Genuine

↓

Fast

↓

Very Fast

Only these values are permitted.

No free-text tempo descriptions.

---

# 8. PRESSURE CLASSIFICATION

Canonical Pressure Values

Very Low

↓

Low

↓

Moderate

↓

High

↓

Extreme

Only these values are permitted.

Pressure reflects tactical pressure only.

Not race quality.

---

END OF PART 1

