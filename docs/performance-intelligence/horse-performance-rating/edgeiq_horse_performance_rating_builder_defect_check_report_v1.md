# EDGEiQ Horse Performance Rating Builder Defect Check V1

Deterministic code defect found: `NO`
Repair applied: `NO`

## Missing Governed Sources
- `config\performance-intelligence\edgeiq_performance_normalisation_parameter_source_v1.csv`: exists=`NO`, rows=`0`
- `config\performance-intelligence\edgeiq_horse_performance_aggregation_parameter_source_v1.csv`: exists=`NO`, rows=`0`
- `config\performance-intelligence\edgeiq_horse_performance_identity_map_v1.csv`: exists=`NO`, rows=`0`

## Finding
The zero-row outcome is reproducible through missing governed source dependencies, not through a deterministic builder defect. The parameter builders intentionally write header-only fact files when their governed source CSVs are absent. The horse observation builder would fail once rating-base rows exist unless a governed identity map is restored.
No formula, threshold, rating scale, temporal rule, identity rule or source provenance change was made.
