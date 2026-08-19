# EDGEiQ Missing Horse Rating Governance Source Consumer Trace V1

## Classification
- `edgeiq_performance_normalisation_parameter_source_v1.csv`: `SCHEMA_PROVEN`; source_exists=NO; source_rows=0
- `edgeiq_horse_performance_aggregation_parameter_source_v1.csv`: `SCHEMA_PROVEN`; source_exists=NO; source_rows=0
- `edgeiq_horse_performance_identity_map_v1.csv`: `SCHEMA_PROVEN`; source_exists=NO; source_rows=0

## Findings
- `edgeiq_performance_normalisation_parameter_source_v1.csv` schema is proven by active builder `SOURCE_FIELDS` and the parameter fact contract. It supplies `centre_value` and `scale_value` for `LINEAR_CENTRE_AND_SCALE`.
- `edgeiq_horse_performance_aggregation_parameter_source_v1.csv` schema is proven by active builder `SOURCE_FIELDS` and the parameter fact contract. It supplies aggregation method, lookback, min/max observations and recency treatment.
- `edgeiq_horse_performance_identity_map_v1.csv` schema is proven by active observation builder `IDENTITY_FIELDS`, while the observation fact contract proves its consumer output semantics. It is identity governance, not a formula parameter source.
- Active parameter builders intentionally return an empty source list when the source CSV is absent; that publishes header-only parameter facts. The identity map source is not optional once rating-base rows exist.
