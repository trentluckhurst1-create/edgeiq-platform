# EDGEiQ Performance Intelligence Platform
## Canonical Architecture Specification V0.1

### Permanent pipeline

Raw source evidence  
↓  
Validation  
↓  
Normalisation  
↓  
Canonical identity resolution  
↓  
Immutable performance evidence  
↓  
Governed benchmarks  
↓  
Performance derivations  
↓  
Pattern and fingerprint engines  
↓  
Horse and campaign intelligence  
↓  
Query services  
↓  
EDGEiQ product services  
↓  
React display

### Permanent rules

1. React does not calculate racing intelligence.
2. Raw evidence is immutable.
3. Corrected evidence creates a new version.
4. Every horse in every race receives one permanent `performance_id`.
5. Raw sectional seconds and derived lengths are stored separately.
6. Negative deviation always means faster or better than benchmark.
7. Positive deviation always means slower or worse than benchmark.
8. Every benchmark records hierarchy level, sample count, exclusions, confidence and version.
9. Every derivation records source evidence, benchmark, engine version and derivation run.
10. Missing intelligence remains unavailable and is never fabricated.

### Initial canonical candidate direction

- Historical raw results foundation:
  `edgeiq_historical_results_warehouse_v2_graphql.csv`
- Broad consolidation and coverage reconciliation:
  `edgeiq_results_master_v1.csv`
- Runner sectional evidence:
  `racingcom_sectional_warehouse_v2.csv`
- Existing sectional identity evidence:
  `edgeiq_sectional_identity_engine_v3.csv`
- Existing horse entity graph:
  `edgeiq_runner_entity_graph_v1.csv`
- Benchmark seed definitions:
  `edgeiq_standard_times_v1.csv`
- Historical rating research:
  `edgeiq_historical_performance_rating_v5_1.csv`
- Existing integrated application view:
  `edgeiq_runner_history_detail_v1.csv`
- Legacy conversion baseline:
  fixed `0.17 seconds per length`, preserved only as
  `LEGACY_FIXED_0_17_V1`

No current asset is yet declared globally canonical.
