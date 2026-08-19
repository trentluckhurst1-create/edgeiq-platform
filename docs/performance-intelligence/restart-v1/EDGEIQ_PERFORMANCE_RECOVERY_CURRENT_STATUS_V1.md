# EDGEiQ Performance Recovery Current Status V1

Status: `LENGTH_CONVERSION_RESOLVED_DOWNSTREAM_TEMPORAL_NORMALISATION_BLOCKED`

Selected conversion model: `EDGEIQ_SURFACE_AWARE_LENGTHS_PER_SECOND_V2`

Canonical race-time delta rows: `17`

Lengths versus standard rows: `13`

LVS rejections: `4`

Performance base rows: `13`

Normalisation rows: `0`

Normalisation rejections: `13`

Remaining blocker: HPR-NORM-A-v1 normalisation parameter effective_from_date is 2026-07-20; converted canonical race-time deltas are 2026-05-30 and 2026-05-31, so all 13 base rows are rejected rather than normalised.

Build: `PASS`
