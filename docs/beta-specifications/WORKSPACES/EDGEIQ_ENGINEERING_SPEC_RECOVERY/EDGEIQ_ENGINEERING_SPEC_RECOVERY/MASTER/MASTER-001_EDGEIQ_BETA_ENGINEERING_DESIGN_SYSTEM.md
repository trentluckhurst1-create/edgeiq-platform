# MASTER-001 — EDGEiQ Beta Engineering Design System
Status: LOCKED
Version: 1.0

## Product identity
EDGEiQ is professional racing intelligence software for racing people. It is not a bookmaker UI, tipping product, stock-market terminal, generic admin dashboard, or card collection. Evidence comes first; intelligence augments the analyst.

## Global layout and tokens
- Desktop-first, persistent left navigation, full available workspace width.
- Canvas `#F4F6F9`; primary surface `#FFFFFF`; secondary `#FAFBFC`; alternate `#F7F9FC`.
- Border `#E5E8EE`; stronger subtle border `#D7DCE5`.
- Blue `#1F5FD6`; hover `#184FB5`; active `#1546A5`.
- Text `#1A1A1A`; secondary `#5C6675`; muted `#7C8798`.
- Green/amber/red are semantic only.
- No gradients, glow, dark terminal panels, decorative winner colours, stars, medals, or oversized hero copy.

## Typography
- Page title 26–28px/600
- Workspace title 20–22px/600
- Section title 14–16px/600
- Table header 11–12px/600
- Table body 13–14px/400–500
- Supporting text 12–13px
Normal table values share one font family, size, colour and line height.

## Tables
- No visible vertical column dividers.
- Subtle horizontal separators.
- Numeric/compact fields centred.
- Horse/trainer/jockey may be left aligned; headers match.
- No ordinary value in a pill, circle, tile or coloured block.
- Controlled horizontal scrolling on narrower screens; do not convert desktop tables to cards.

## Intelligence boundary
React may render, sort, filter, select, expand, collapse and navigate.
React must not calculate EPI, ERI, price, edge, early/late speed, suitability, form momentum, race shape, benchmark sectionals, effective barriers, track profile, weather impact or insight narratives.
Missing evidence remains null/blank/unavailable. No fabricated fallback.

## Benchmark sectional standard
Primary display is lengths versus governed benchmark.
- Negative = inside/faster than standard; green.
- Positive = outside/slower than standard; red.
- Zero/within governed tolerance = neutral.
Raw seconds only in tooltip/drill-down/audit data.

## Verification
Every implementation requires task checkpoint, syntax validation, canonical data audit, UI structure audit, `npm run build`, browser screenshots, and no weakened audit thresholds.
