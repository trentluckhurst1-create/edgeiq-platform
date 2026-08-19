# BETA-002 — Meetings Workspace
Status: LOCKED
Version: 1.0

## Purpose
Answers: **Where should the analyst be looking today?** Full-width operational entry point.

## Governing rules
Inherits MASTER-001. Do not reinterpret approved hierarchy, columns, alignment, colour semantics or data ownership.


## Layout
Header; canonical TODAY/TOMORROW/DAY+2 selector; day summary strip; meetings table; selected-meeting race strip; right selected-meeting rail. Desktop split about 82/18 with 16px gap.

## Canonical dates
Use `public\data\edgeiq_three_day_window_v1.json`. React never creates dates.

## Summary strip
`Meetings | Races | Declared | Scratchings | Heavy Tracks | Soft Tracks | Good Tracks | Weather Alerts`
One band, not separate cards.

## Table
Exact columns:
`SELECT | MEETING | STATE | RAIL | TRACK | WEATHER | WIND | TEMP | RACES | DECLARED | SCRATCHINGS | FIRST | LAST | STATUS | EDGEiQ READ | OPEN`
Meeting and EDGEiQ Read left aligned; others centred. Selected row = thin blue outline/pale tint. EDGEiQ Read max three governed phrases. OPEN = accessible arrow.

## Selected rail
Meeting/venue, track, rail, weather, wind, temp, rain 24h, irrigation 24h, official update, evidence-backed notes, `Open Meeting →`.

## Race strip
Compact horizontal cards: race, time, distance, class/name, restriction, field size, status, open.

## Acceptance
Full width; no stacked launcher cards; all three days; accurate totals; selected rail and race strip preserve route context.
