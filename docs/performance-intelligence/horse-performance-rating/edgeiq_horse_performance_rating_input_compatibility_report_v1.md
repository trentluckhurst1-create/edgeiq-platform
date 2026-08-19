# EDGEiQ Horse Performance Rating Input Compatibility V1

Schema failures: `0`
Governed parameter population gaps: `2`

## Finding
The current governed V2 performance outputs contain the expected race, runner, surface, distance, lengths-versus-standard, sectional, early-speed and late-speed columns.
The active V1 horse-rating chain is not blocked by a stale V1/V2 filename or column mismatch at this audit point.
The compatibility blocker is that both governed parameter facts required after the base PI stage are header-only: normalisation parameters and horse aggregation parameters.
No builder patch is justified by this audit because the schema aligns; the missing evidence is governed parameter population, not a deterministic code defect.

## Inputs
- `canonical race identity` from `edgeiq_results_lengths_v_standard_v2.csv`: availability=`AVAILABLE`, rows=168, schema=`PASS`, migration=`NO`
- `canonical runner identity` from `edgeiq_results_lengths_v_standard_v2.csv`: availability=`AVAILABLE`, rows=168, schema=`PASS`, migration=`NO`
- `canonical track` from `edgeiq_results_lengths_v_standard_v2.csv`: availability=`AVAILABLE`, rows=168, schema=`PASS`, migration=`NO`
- `surface group` from `edgeiq_results_lengths_v_standard_v2.csv`: availability=`AVAILABLE`, rows=168, schema=`PASS`, migration=`NO`
- `distance metres` from `edgeiq_results_lengths_v_standard_v2.csv`: availability=`AVAILABLE`, rows=168, schema=`PASS`, migration=`NO`
- `seconds per length` from `edgeiq_results_lengths_v_standard_v2.csv`: availability=`AVAILABLE`, rows=168, schema=`PASS`, migration=`NO`
- `lengths versus standard` from `edgeiq_results_lengths_v_standard_v2.csv`: availability=`AVAILABLE`, rows=168, schema=`PASS`, migration=`NO`
- `sectional early/mid/late` from `edgeiq_runner_sectional_performance_v2.csv`: availability=`AVAILABLE`, rows=24, schema=`PASS`, migration=`NO`
- `early speed phase` from `edgeiq_results_early_speed_v2.csv`: availability=`AVAILABLE`, rows=24, schema=`PASS`, migration=`NO`
- `late speed phase` from `edgeiq_results_late_speed_v2.csv`: availability=`AVAILABLE`, rows=24, schema=`PASS`, migration=`NO`
- `canonical V1 performance base bridge` from `edgeiq_lengths_versus_standard_fact_v1.csv`: availability=`AVAILABLE`, rows=168, schema=`PASS`, migration=`NO`
- `normalisation parameters` from `edgeiq_performance_normalisation_parameter_fact_v1.csv`: availability=`HEADER_ONLY`, rows=0, schema=`PASS`, migration=`GOVERNED_PARAMETER_POPULATION_REQUIRED`
- `horse aggregation parameters` from `edgeiq_horse_performance_aggregation_parameter_fact_v1.csv`: availability=`HEADER_ONLY`, rows=0, schema=`PASS`, migration=`GOVERNED_PARAMETER_POPULATION_REQUIRED`
