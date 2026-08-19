# EDGEiQ Victoria Live Architecture Investigation V1

Generated: 2026-07-30 Australia/Sydney

## Purpose

This document freezes the architecture decision that follows the data-acquisition investigation. It separates the engineering, commercial and legal questions before Victoria Live recovery resumes.

## Core Finding

EDGEiQ already has the engineering capability to calculate:

- Standard Times
- Race Time Delta
- Lengths v Standard
- Performance Base
- Normalisation
- Ratings
- EPI

The platform problem is not the calculation methodology. The missing piece is a sustainable and compliant acquisition path for the raw input data.

## Critical Distinction

Using raw racing data as an input to calculate independent EDGEiQ analytics is different from republishing another provider's database or proprietary analytics.

However, whether automated collection from a particular source is permitted depends on that source's terms, contracts and applicable law. The fact that EDGEiQ creates its own calculations does not automatically permit automation from any visible or protected source.

## Architecture Decision

Victoria Live should be restored around the core results-and-timing pipeline first.

Runner sectionals and detailed speed data are enrichment layers. They should not be a critical dependency for the core Performance Intelligence chain.

## Canonical Victoria Pipeline

The governed production target is:

1. Results Warehouse
2. Timed Races
3. Standard Times
4. Race Time Delta
5. Lengths v Standard
6. Performance Base
7. Normalisation
8. Ratings
9. Snapshots
10. EPI
11. Daily Operations
12. React Feeds

## Required vs Optional Inputs

### Required

- Results warehouse
- Official race times
- Margins
- Finish positions
- Track, distance, race class and condition facts
- Standard-time eligibility inputs

### Optional

- Runner sectionals
- Speed maps
- Weather enhancements
- Market enrichments
- Browser-rendered diagnostics

Missing optional data must never stop the core performance pipeline.

## PASS_VICTORIA_LIVE Acceptance

Victoria is complete only when the following all pass without manual intervention:

- Results Warehouse
- Timed Races
- Standard Times
- Race Time Delta
- Lengths v Standard
- Performance Base
- Normalisation
- Ratings
- Snapshots
- EPI
- Daily Operations
- React

The system must not fabricate data and must not depend on unavailable Racing.com sectionals.

## Expansion Principle

Do not expand to WA or other jurisdictions until Victoria reaches PASS_VICTORIA_LIVE. Once Victoria is deterministic and autonomous, each new jurisdiction becomes a governed data-adapter exercise rather than a platform redesign.
