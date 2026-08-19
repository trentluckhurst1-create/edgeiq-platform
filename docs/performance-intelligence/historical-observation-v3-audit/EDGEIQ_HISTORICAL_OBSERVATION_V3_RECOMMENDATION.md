# EDGEIQ Historical Observation V3 Recommendation

## Decision: REPLACE

The existing builder's source-admission architecture is broad and does not enforce the locked consolidated GraphQL authority. Because source authority defines the warehouse population, this is a foundational divergence rather than a cosmetic defect.

## Required next action

Create a new governed Phase 1A.6B builder that admits only the approved consolidated GraphQL authority, preserves the locked physical and identity populations, explicitly excludes prohibited source classes, and leaves the existing untracked V3 implementation untouched as forensic evidence.
