# EDGEIQ Performance Intelligence Restart Baseline V1

## Verdict

**PASS**

This unit is forensic only. It changed no engine logic,
governed thresholds, source data, runtime data or React.

## Repository Position

- Branch: `feature/component-refactor`
- Starting HEAD: `633c784`
- Performance Intelligence artefacts inventoried: 3450
- Builder or audit scripts identified: 661
- CSV artefacts: 659
- Populated CSV artefacts: 616
- Header-only CSV artefacts: 32
- Empty CSV artefacts: 9
- CSV parse errors: 2

## Expected Canonical Outputs

| Output | Present | CSV status | Data rows |
|---|---:|---|---:|
| `docs/performance-intelligence/canonical-identities/edgeiq_canonical_performance_identity_v1.csv` | YES | POPULATED | 879784 |
| `docs/performance-intelligence/canonical-identities/edgeiq_canonical_horse_identity_v1.csv` | YES | POPULATED | 97112 |
| `docs/performance-intelligence/canonical-identities/edgeiq_canonical_race_identity_v1.csv` | YES | POPULATED | 71019 |
| `docs/performance-intelligence/canonical-identities/edgeiq_canonical_meeting_identity_v1.csv` | YES | POPULATED | 8600 |
| `docs/performance-intelligence/canonical-identities/edgeiq_canonical_track_identity_v1.csv` | YES | POPULATED | 100 |
| `docs/performance-intelligence/epi/edgeiq_epi_performance_fact_v1.csv` | YES | POPULATED | 533387 |
| `docs/performance-intelligence/lengths-v-standard/edgeiq_runner_lengths_v_standard_fact_v1.csv` | YES | POPULATED | 533387 |
| `public/data/edgeiq_standard_time_fact_v1.csv` | YES | HEADER_ONLY | 0 |
| `public/data/edgeiq_performance_intelligence_base_fact_v1.csv` | YES | POPULATED | 168 |
| `public/data/edgeiq_performance_normalisation_fact_v1.csv` | YES | POPULATED | 168 |
| `public/data/edgeiq_performance_rating_base_fact_v1.csv` | YES | N/A | N/A |
| `public/data/edgeiq_horse_performance_observation_fact_v1.csv` | YES | POPULATED | 168 |
| `public/data/edgeiq_horse_performance_rating_fact_v1.csv` | YES | POPULATED | 24 |
| `public/data/edgeiq_horse_performance_aggregate_fact_v1.csv` | YES | POPULATED | 24 |
| `public/data/edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv` | YES | HEADER_ONLY | 0 |

## Governed Next Action

**FORENSICALLY_TRACE_FIRST_ZERO_ROW_CANONICAL_OUTPUT**

At least one expected canonical Performance Intelligence CSV exists but contains zero data rows.

No repair is authorised by this baseline.
The next unit must inspect lineage and the first
provable loss point before changing any builder.

## Outputs

- `edgeiq_performance_intelligence_restart_inventory_v1.csv`
- `edgeiq_performance_intelligence_restart_baseline_v1.json`
- `EDGEIQ_PERFORMANCE_INTELLIGENCE_RESTART_BASELINE_V1.md`
- `edgeiq_performance_intelligence_restart_git_history_v1.txt`
