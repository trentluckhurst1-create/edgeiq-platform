# SPEC-008
# EDGEIQ WEATHER
## PRODUCT ENGINEERING SPECIFICATION
### VERSION 1.0
### STATUS LOCKED

---

# 1. PURPOSE

The Weather Workspace is the canonical operational weather centre for the selected meeting.

Its purpose is to present trusted meteorological information that may influence racing conditions.

The Weather Workspace presents evidence.

It never predicts race outcomes.

It never estimates unavailable weather.

---

# 2. PRODUCT PHILOSOPHY

Weather affects

• Track evolution

• Running styles

• Wind resistance

• Irrigation effectiveness

• Surface drying

• Surface deterioration

EDGEIQ presents weather as factual operational intelligence.

The analyst determines significance.

---

# 3. USER GOALS

Immediately understand

• Current Conditions

• Temperature

• Wind

• Humidity

• Rainfall

• Cloud Cover

• Sunrise

• Sunset

• Racing Impact

without leaving EDGEIQ.

---

# 4. WORKSPACE LAYOUT

----------------------------------------------------

HEADER

----------------------------------------------------

CURRENT CONDITIONS

----------------------------------------------------

WEATHER SUMMARY

----------------------------------------------------

RACING IMPACT

----------------------------------------------------

DATA STATUS

----------------------------------------------------

---

# 5. CURRENT CONDITIONS

Displays

Current Conditions

↓

Temperature

↓

Apparent Temperature

↓

Wind

↓

Humidity

↓

Cloud Cover

↓

Rainfall

↓

Pressure

↓

Last Updated

Card Height

110px

Background

FFFFFF

Border

1px solid #E5E8EE

---

# 6. WEATHER SUMMARY

Displays

Temperature

↓

Wind Direction

↓

Wind Speed

↓

Humidity

↓

Rainfall 24 Hours

↓

Rainfall 7 Days

↓

Cloud Cover

↓

Sunrise

↓

Sunset

Official information only.

---

# 7. RACING IMPACT

Purpose

Summarise how today's weather may influence racing conditions.

Displays

Track Drying

↓

Track Wetting

↓

Wind Influence

↓

Surface Evolution

↓

Visibility

↓

Operational Notes

Evidence only.

No betting commentary.

No predictions.

---

# 8. REMOVED COMPONENTS

The following are permanently excluded.

Weather Radar

Forecast Confidence

Animated Weather Graphics

Estimated Conditions

These do not form part of the Beta specification.

---

END OF PART 1


---

# 9. WEATHER DATA GOVERNANCE

## Purpose

Weather data is operational information.

It is not predictive intelligence.

Every weather value displayed within EDGEIQ must originate from a governed canonical weather builder.

React is never permitted to calculate weather values.

---

## Canonical Weather Sources

The Weather Builder is responsible for supplying

Current Temperature

↓

Apparent Temperature

↓

Wind Direction

↓

Wind Speed

↓

Humidity

↓

Cloud Cover

↓

Rainfall (24 Hours)

↓

Rainfall (7 Days)

↓

Atmospheric Pressure

↓

Sunrise

↓

Sunset

↓

Weather Condition

No browser weather.

No JavaScript weather.

No third-party React APIs.

---

# 10. DATA QUALITY

Every weather record exposes

Official Source

↓

Builder Version

↓

Coverage

↓

Timestamp

↓

Audit Version

↓

Feed Status

Unavailable information is displayed as

Unavailable

Never estimated.

Never inferred.

Never carried forward.

---

# 11. PROFESSIONAL UNAVAILABLE STATE

If weather data cannot be obtained

Display

Unavailable

Display

Last Successful Update

Display

Reason (when available)

Examples

Weather Station Offline

Feed Unavailable

Awaiting Update

No placeholder temperatures.

No estimated rainfall.

No synthetic forecasts.

Operational honesty always overrides appearance.

---

# 12. USER INTERACTION

Hover

Displays

Definition

Source

Timestamp

Builder Version

No drill-down calculations.

No editing.

No interaction changes weather values.

---

# 13. DESIGN SYSTEM COMPLIANCE

Background

FFFFFF

Surface

FFFFFF

Secondary Surface

FAFBFC

Border

E5E8EE

Accent

EDGEIQ Blue

Primary Text

1A1A1A

Secondary Text

5C6675

No gradients.

No weather animations.

No decorative icons beyond simple condition indicators.

Professional software presentation only.

---

# 14. RESPONSIVE BEHAVIOUR

Desktop

Primary target.

No horizontal scrolling.

Laptop

Reduce spacing only.

Tablet

Cards stack vertically.

Mobile

Not supported during Beta.

---

# 15. PERFORMANCE TARGETS

Workspace Load

<300ms

Weather Refresh

<100ms

Hover

Immediate

No unnecessary React re-rendering.

---

END OF PART 2


---

# 16. ACCESSIBILITY

## Keyboard Navigation

Supported

All controls must be reachable using keyboard navigation.

Focus indicators must remain visible at all times.

---

## Colour Accessibility

Weather information must never rely solely on colour.

Icons must always be accompanied by text.

Status colours are supplementary only.

Minimum contrast

WCAG AA

---

## Screen Readers

Every weather card requires

Accessible Label

Accessible Description

Timestamp

Data Source

Unavailable State

---

# 17. FUTURE EXPANSION

Reserved Modules

Hourly Weather Timeline

↓

Wind Evolution

↓

Rain Radar Integration (Subject to Licensing)

↓

Historical Weather Comparison

↓

Track Moisture Correlation

↓

Track Drying Rate

↓

Weather Alerts

↓

Lightning Warnings

↓

Extreme Heat Notifications

These modules extend the workspace.

They never redesign it.

---

# 18. ENGINEERING RESPONSIBILITIES

## React Responsibilities

React is responsible for

Display

Layout

Filtering

Navigation

Highlighting

Accessibility

Responsive Layout

React MUST NEVER

Calculate weather

Estimate missing values

Generate forecasts

Modify weather history

Generate racing commentary

---

## Builder Responsibilities

Canonical Weather Builder owns

Temperature

Wind

Humidity

Cloud Cover

Rainfall

Pressure

Sunrise

Sunset

Weather Condition

Feed Status

Coverage

Audits

Builder output is the single source of truth.

---

# 19. ENGINEERING PERFORMANCE

Workspace Load

Target

<300ms

Weather Refresh

Target

<100ms

Hover

Immediate

Card Rendering

<50ms

No unnecessary React re-rendering.

No duplicated weather requests.

---

# 20. ACCEPTANCE CRITERIA

Weather Workspace is complete when

✓ Current Conditions implemented

✓ Weather Summary implemented

✓ Racing Impact implemented

✓ Data Status implemented

✓ Canonical weather builders used

✓ Honest Unavailable state implemented

✓ Weather Radar excluded

✓ Forecast Confidence excluded

✓ White EDGEIQ Design System implemented

✓ React remains display only

✓ npm build passes

✓ Engineering audits pass

---

# 21. CODEX IMPLEMENTATION CHECKLIST

Codex MUST

Use canonical weather builders

Never calculate weather in React

Implement Current Conditions

Implement Weather Summary

Implement Racing Impact

Implement Data Status

Implement professional Unavailable state

Exclude Radar

Exclude Forecast Confidence

Follow MASTER Design System

Run npm build

Run engineering audits

Capture verification screenshots

Produce implementation report

---

# 22. ENGINEERING GOVERNANCE

This specification is the canonical authority for the Weather Workspace.

Any modification to

Weather presentation

Weather builders

Unavailable behaviour

Data ownership

Workspace layout

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

SPEC-008

Workspace

WEATHER

Status

LOCKED

Authority

EDGEIQ Product Engineering Specification

Revision

1.0

