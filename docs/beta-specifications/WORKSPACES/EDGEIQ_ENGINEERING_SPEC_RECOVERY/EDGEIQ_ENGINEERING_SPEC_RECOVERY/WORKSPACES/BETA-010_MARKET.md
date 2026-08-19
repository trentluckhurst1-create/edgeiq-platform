# BETA-010 — Market Workspace
Status: LOCKED
Version: 1.0

## Purpose
Answers: **What does the market believe, how has it moved, and where does governed EDGEiQ pricing differ?**

## Governing rules
Inherits MASTER-001. Do not reinterpret approved hierarchy, columns, alignment, colour semantics or data ownership.


## Exclusion
No Back/Lay columns or exchange ladder/order-book styling.

## Summary
Market status, favourite, largest firmer/drifter, market percentage, last update.

## Table
`NO | HORSE | EPI | MARKET | OPEN | HIGH | LOW | MOVE | EDGEiQ PRICE | EDGE | STATUS`
Plain saddlecloth numbers. Horse left aligned; compact values centred.

## Movement/edge
Governed opening/current/high/low timeline. No interpolation in React.
Builder compares current market and EDGEiQ Price. Never compare EPI directly to price.

## Acceptance
No Back/Lay; clear market vs EDGEiQ Price; racing-market analysis, not trading UI.
