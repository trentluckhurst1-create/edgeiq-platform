# EDGEIQ Suitability Engine V1

## Purpose

Suitability answers how well today's actual race setup suits a runner. It is a current-race runner-specific setup score, not a performance rating, not a probability and not a market view.

## Difference From EPI

EPI is a performance-index projection. Suitability may use current EPI as one evidence family, but EPI alone cannot create a Suitability score. Suitability also requires profile, setup, speed/map and race-condition evidence.

## Factor Families

Selected factor families are:

- Distance profile from dated historical runs.
- Track profile from dated historical runs.
- Track and distance profile from dated historical runs.
- Condition profile from dated historical runs.
- Class profile from dated historical runs.
- Days-since-run context from latest as-of run.
- Current EPI as one setup factor.
- Current Early Speed V1.
- Current Late Speed V1.
- Current Race Shape V2.
- Barrier context when field size is available.
- Gear context as an evidence note only unless supported by dated evidence.

## Missing Data Rules

Missing values are ignored. They are never treated as zero. A score is blank when the minimum independent evidence threshold is not met.

## Minimum Evidence

V1 requires at least four independent populated factor families and at least two dated historical runs unless a future approved first-starter profile feed is added. EPI and barrier by themselves are not sufficient.

## Score Scale

The public score is 0 to 100, higher means stronger suitability for today's setup.

Public bands:

- 85 to 100: STRONG FIT
- 70 to 84: POSITIVE
- 50 to 69: NEUTRAL
- 35 to 49: QUESTIONABLE
- 0 to 34: POOR FIT

## Confidence And Coverage

The feed exposes evidence factor count, available factor count, evidence coverage and historical evidence runs. It does not expose private production weights.

## As-Of Protections

Historical evidence must satisfy `historical race_date < selected race date`. Selected-race outcomes, future results and ambiguous joins are excluded.

## Exclusions

Suitability does not use market price as a scoring input. It does not copy EPI, Race Shape, Early Speed or Late Speed directly. It does not run calculations in React.

## Audit Expectations

Audits must verify no future rows, no selected-race rows, no cross-runner joins, no cross-race joins, no missing-as-zero treatment and no broad duplication with EPI.
