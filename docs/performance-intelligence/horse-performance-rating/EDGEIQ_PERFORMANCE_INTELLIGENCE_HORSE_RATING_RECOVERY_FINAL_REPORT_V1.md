# EDGEiQ Performance Intelligence Horse Rating Recovery Final Report V1

## Overall Status
OVERALL STATUS: `EDGEIQ_PERFORMANCE_INTELLIGENCE_BLOCKED_BY_HORSE_RATING_METHOD`
FINAL DECISION: Do not build or promote historical horse-performance ratings until governed normalisation parameters, horse aggregation parameters, and a deterministic horse identity map are restored.

## Active Horse Rating Builder
- Active builder: `scripts/build_edgeiq_horse_performance_rating_fact_v1.py`
- Classification: `ACTIVE_BUILDER_INPUT_EMPTY`
- Entry function: `main`
- Production path: `public/data/edgeiq_horse_performance_rating_fact_v1.csv`
- Candidate path in active builder: `NOT_DEFINED`

## Rating Method
- Rating method: `DIRECT_HISTORICAL_AGGREGATE_VALUE`
- Rating version: `edgeiq_horse_performance_rating_fact_v1.0.0`
- Rating fact grain: `ROLLING_HORSE_AS_OF_DATE_RATING_FACT`

## Historical Input Sources
- `public\data\edgeiq_lengths_versus_standard_fact_v1.csv`: rows=168, sha256=`5e59508c162c316586781abad4531b3f55dd3fe8d68128690db93daf65f295ef`
- `public\data\edgeiq_results_lengths_v_standard_v2.csv`: rows=168, sha256=`89407374ba388fee0d24696146c896410899b3d498fa3d8eb00f8f9bac68f93b`
- `public\data\edgeiq_runner_sectional_performance_v2.csv`: rows=24, sha256=`d4202c74c294e870b0586802be2bbc477ce15fe3fc54959e0a23a3eaffb392c9`
- `public\data\edgeiq_results_early_speed_v2.csv`: rows=24, sha256=`cbd13707b2bee705b6b252dc62f5889193ab7831b0fd8950f48469db2657b2a6`
- `public\data\edgeiq_results_late_speed_v2.csv`: rows=24, sha256=`8e1b1f6dd1aec11b765d0fa0edb44a6ae03a79e5c17ff00ebd5bfbcc0eb5b261`
- `public\data\edgeiq_performance_intelligence_base_fact_v1.csv`: rows=168, sha256=`537c3fbb54c0579d78499d1bda49f0c552865f108070a1b49bafd2c61c72648f`
- `public\data\edgeiq_performance_normalisation_parameter_fact_v1.csv`: rows=0, sha256=`2a26cddb3146a45a9bf89bd466880859225684e0e22ade459a186adaeee6c97c`
- `public\data\edgeiq_performance_normalisation_fact_v1.csv`: rows=0, sha256=`9a0ce873e01937b6644a3a6cbb4b67696886a7f57e9374be490d049616a438df`
- `public\data\edgeiq_performance_rating_base_fact_v1.csv`: rows=0, sha256=`5a98979645907125b0b7f9003368005584ab66df50e55bd495c4ccd2ec82eb14`
- `public\data\edgeiq_horse_performance_observation_fact_v1.csv`: rows=0, sha256=`d68b0e1c93c76375bcf8934bc6264487d8dc92ab6ac0df3b1d67478f9325cf34`
- `public\data\edgeiq_horse_performance_aggregation_parameter_fact_v1.csv`: rows=0, sha256=`a3eaaac9b5d67b3c437132fc4f371aa658eef19cd15dab3eea2d04002292113b`
- `public\data\edgeiq_horse_performance_aggregate_fact_v1.csv`: rows=0, sha256=`33d2ec9fd25246be9daa0f6043e85d9302f1dd81d05653524019db865bfe5a26`
- `public\data\edgeiq_horse_performance_rating_fact_v1.csv`: rows=0, sha256=`7b01a0669adbf44a5e46ca1206cf549f5390f62135ba72321106e6de37585312`
- `public\data\edgeiq_race_entry_fact_v1.csv`: rows=204, sha256=`812478a08e5f6014611109ead277d4c263b4916c2863f0dd2c3b8b88f5d3983b`
- `public\data\edgeiq_race_entry_projected_performance_fact_v1.csv`: rows=0, sha256=`2d7996a050856e252e6639bdb6569f9cff9b49442cf8ee5cbc676c92fc92fc54`
- `public\data\edgeiq_live_entry_historical_rating_coverage_v1.csv`: rows=204, sha256=`9f1e9f12f0e173de6d1b9f257ad1a576e43a02e1e8e964260a5ca6b437adcc0c`

## Join Coverage And Identity
- Historical runner performances: `24`
- Racing.com runner IDs available in V2 performance rows: `24`
- Exact historical identity matches: `0`
- Identity misses: `24`
- Identity collisions: `0`
- Missing source: `config/performance-intelligence/edgeiq_horse_performance_identity_map_v1.csv`

## Row Funnel
- FIRST ZERO-ROW STAGE: `required formula fields validated`
- Root rejection reason: `MISSING_FORMULA_INPUT`
- Rejected at first zero stage: `168`
- Performance base rows present before zero stage: `168`
- Normalisation parameter rows: `0`
- Normalisation rows: `0`
- Rating-base rows: `0`
- Horse observation rows: `0`
- Horse aggregate rows: `0`
- Horse rating rows: `0`

## Eligibility Gates
- History depth distribution: `24 runners with 5+ eligible segments`
- Depth blocker: `NO`
- Failed gates: `normalisation parameter available`, `horse identity map available`, `horse aggregation parameter available`

## Candidate And Production Rows
- Horse performance rating candidate rows: `0`
- Horse performance rating production rows: `0`
- Horse performance rating hash: `7b01a0669adbf44a5e46ca1206cf549f5390f62135ba72321106e6de37585312`

## Live Race Entries
- Live race-entry rows: `204`
- Active live entries: `188`
- Live horses with historical ratings: `0`
- Live horses without historical ratings: `188`
- Scratched: `6`
- Emergency: `10`

## Projected Performance And EPI
- Projected performance input rows: `0`
- Projected performance output rows: `0`
- Projected blocked reason: `NO_HISTORICAL_RATINGS`
- EPI input rows: `0 projected performance rows`
- EPI output rows: `0 rebuilt in this pass`
- Active runners with EPI: `0 from this pass`
- Active runners without EPI: `188`
- Historical EPI retained: `YES; no production EPI overwrite was performed`

## Orchestration Status
- Orchestration status: `NO_HISTORICAL_RATINGS`
- Deterministic rerun: `NOT_RUN_BLOCKED_BY_GOVERNED_SOURCE_GAPS`
- Consumer audit: `EPI_INPUTS_PARTIAL_PROJECTED_PERFORMANCE_MISSING`
- TypeScript compile: `PASS` (`npx.cmd tsc -b`)
- Vite build: `BUILD_CODE_VALIDATION_PASS_RESOURCE_EXECUTION_BLOCKED` (`npm run build` timed out after TypeScript had passed)
- Program smoke: `RESOURCE_TIMEOUT`

## Files Created
- `scripts/audit_edgeiq_horse_performance_rating_builder_trace_v1.py`
- `scripts/audit_edgeiq_horse_performance_rating_row_funnel_v1.py`
- `scripts/audit_edgeiq_horse_performance_rating_grain_v1.py`
- `scripts/audit_edgeiq_horse_performance_rating_input_compatibility_v1.py`
- `scripts/audit_edgeiq_historical_performance_identity_v1.py`
- `scripts/audit_edgeiq_horse_performance_rating_eligibility_v1.py`
- `scripts/audit_edgeiq_horse_performance_rating_builder_defects_v1.py`
- `scripts/audit_edgeiq_live_entry_historical_rating_coverage_v1.py`
- `docs/performance-intelligence/horse-performance-rating/*`
- `public/data/edgeiq_live_entry_historical_rating_coverage_v1.csv`

## Files Modified Or Preserved
- Pricing/probability/V6.1/V7.2G2/UI files changed: `NO`
- Production horse rating fact overwritten with fabricated rows: `NO`
- Projected-performance formula changed: `NO`
- EPI formula changed: `NO`

## Commits
- `4c86633 audit: trace horse performance rating builder`
- `082180f audit: recover governed horse performance rating method`
- `9cf25ef audit: expose horse performance rating row funnel`
- `5c51958 audit: prove horse performance rating fact grain`
- `a1c2fa8 audit: verify horse performance rating input compatibility`
- `5d0fe21 audit: verify historical performance horse identities`
- `789c6e8 audit: verify horse performance rating eligibility gates`
- `7792241 audit: check horse performance rating builder defects`
- `c600e62 audit: report live entry historical rating coverage`

## Defects Found
- No deterministic builder defect found in the active horse rating builder.
- Governed source dependency gaps found: missing normalisation parameter source, missing horse aggregation parameter source, missing horse identity map.

## Genuine Data Gaps
- `config/performance-intelligence/edgeiq_performance_normalisation_parameter_source_v1.csv` missing.
- `config/performance-intelligence/edgeiq_horse_performance_aggregation_parameter_source_v1.csv` missing.
- `config/performance-intelligence/edgeiq_horse_performance_identity_map_v1.csv` missing.

## Exact Next Action
Recover or approve the governed parameter source CSVs and deterministic historical horse identity map. Then rerun the unchanged governed chain from performance normalisation parameters through horse ratings, projected performance, and EPI.
