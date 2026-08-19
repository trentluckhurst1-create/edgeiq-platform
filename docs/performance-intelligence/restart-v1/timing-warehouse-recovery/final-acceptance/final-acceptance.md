# EDGEiQ Timing Warehouse Recovery V1 Final Acceptance

Overall status: PARTIAL

The reason for the 39-row canonical timing population is established: the active benchmark observation producer reads the Racing.com V2.1 current-window speed warehouse, whose audit reports 39 canonical races. A separate governed historical performance timing warehouse exists with 70308 timed race-level observations.

Side-by-side recovered outputs were built and audited. Current public canonical outputs were not overwritten in this unit. Normalisation remains governed by HPR-NORM-A-v1 effective from 2026-07-20; recovered pre-cutoff performance base rows are explicitly rejected.

Protected systems changed: NO. Pricing/probability/V6.1/V7.2G2/UI changed: NO.
