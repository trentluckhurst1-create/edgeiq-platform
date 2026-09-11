# EDGEiQ Dashboard — APPROVED / LOCKED

Locked: 11 September 2026

This document is the visual and information-architecture authority for the EDGEiQ Dashboard.

## Locked visual direction

- Light application throughout: sidebar and page use the same white/light visual family.
- No dark sidebar on the Dashboard design.
- Primary accent: EDGEiQ blue.
- Main text: deep navy.
- Secondary text: muted blue-grey.
- Panels: white with subtle cool-grey borders, small radius, minimal shadow.
- Dense professional racing-software presentation; not a marketing website.
- Green is reserved for positive/live/ready states; red for failures/scratchings/negative alerts; amber for warnings.

## Locked Dashboard structure

1. Dashboard title and concise race-day command-centre subtitle.
2. Three-day selector at upper right.
3. Today's Meetings / selected-day Meetings table.
4. Race Activity.
5. Alerts.
6. Featured Race.
7. Track & Weather.
8. Market Summary entry point.
9. Intelligence entry points.
10. Race timeline.

## Explicit removals

The former KPI/value tile strip is removed. Do not restore the large Live Meetings / Races Today / Declared Runners / Scratchings tile row.

The former Welcome to EDGEiQ marketing hero, Evidence First, Built For Professionals and Complete Intelligence promotional cards are not part of the approved Dashboard.

## Three-day naming rule

Never show DAY +2 to the user.

The selector must use:

- first day: `Today`, with actual short date below it;
- second day: `Tomorrow`, with actual short date below it;
- third day: the actual weekday name derived from that date, e.g. `Sunday`, with actual short date below it.

Example for Friday 11 September 2026:

- Today — Fri 11 Sep
- Tomorrow — Sat 12 Sep
- Sunday — Sun 13 Sep

This rule is dynamic and must not hard-code Sunday.

## Data rule

The approved mockup defines layout and hierarchy only. Production components must continue to use governed EDGEiQ feeds. Do not invent mock market prices, runners, alerts, weather, ratings or race data merely to match a mockup.

## Change control

This Dashboard is locked. Future changes should preserve this design unless Trent explicitly approves a new Dashboard direction.
