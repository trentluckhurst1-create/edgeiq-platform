# EDGEIQ Weather Workspace Standard

## Purpose

The WEATHER workspace presents factual meeting weather information that may influence racing.

## Locked principle

EDGEIQ predicts horse performance.

EDGEIQ does not predict steward decisions.

## Display

Show available sourced information only:

- official track rating
- official rail position
- current temperature
- overnight rainfall
- rainfall since 9:00 am
- rainfall today
- forecast rainfall
- wind direction
- wind speed
- humidity
- official weather forecast
- factual weather alerts

## Forecast language

Weather-provider forecasts must be clearly labelled as forecasts.

Acceptable:

- 3–8 mm forecast this afternoon
- rain forecast later in the meeting
- strong winds forecast

Not acceptable:

- track will become Soft 5
- expected downgrade after Race 4
- projected official track rating
- expected upgrade

## Track information

The official published track rating and rail position remain authoritative.

EDGEIQ must not infer or replace either value.

## Weather alerts

Alerts must be factual and source-supported.

Examples:

- 14 mm overnight rainfall
- 6 mm forecast during the meeting
- strong wind forecast
- thunderstorm warning issued
- official track rating unchanged

Do not create an alert from missing data.

## Empty states

Do not show rows of dashes as connected data.

When weather fields are unavailable, show one concise meeting-level empty state.

## Status

LOCKED DESIGN STANDARD
Approved July 2026
