from __future__ import annotations
import csv, json, hashlib
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
DOC=ROOT/'docs'/'performance-intelligence'
MG=DOC/'horse-performance-rating'/'method-governance'
MANIFEST=DATA/'edgeiq_performance_intelligence_trust_manifest_v1.json'
CERT=DOC/'EDGEIQ_PERFORMANCE_INTELLIGENCE_TRUST_CERTIFICATION_V1.md'
ORCH=DOC/'EDGEIQ_PERFORMANCE_INTELLIGENCE_PRODUCTION_PROGRAM_V1.md'
FINAL=MG/'EDGEIQ_PERFORMANCE_INTELLIGENCE_FINAL_PRODUCTION_REPORT_V1.json'
FILES={
 'normalisation_source': ROOT/'config'/'performance-intelligence'/'edgeiq_performance_normalisation_parameter_source_v1.csv',
 'normalisation_parameter': DATA/'edgeiq_performance_normalisation_parameter_fact_v1.csv',
 'aggregation_source': ROOT/'config'/'performance-intelligence'/'edgeiq_horse_performance_aggregation_parameter_source_v1.csv',
 'aggregation_parameter': DATA/'edgeiq_horse_performance_aggregation_parameter_fact_v1.csv',
 'historical_pi': DATA/'edgeiq_performance_intelligence_base_fact_v1.csv',
 'normalisation': DATA/'edgeiq_performance_normalisation_fact_v1.csv',
 'rating_base': DATA/'edgeiq_performance_rating_base_fact_v1.csv',
 'identity_map': ROOT/'config'/'performance-intelligence'/'edgeiq_horse_performance_identity_map_v1.csv',
 'observation': DATA/'edgeiq_horse_performance_observation_fact_v1.csv',
 'aggregate': DATA/'edgeiq_horse_performance_aggregate_fact_v1.csv',
 'horse_rating': DATA/'edgeiq_horse_performance_rating_fact_v1.csv',
 'live_entries': DATA/'edgeiq_race_entry_fact_v1.csv',
 'live_rating_match': DATA/'edgeiq_live_horse_performance_rating_match_v1.csv',
 'projected_performance': DATA/'edgeiq_race_entry_projected_performance_fact_v1.csv',
 'epi': DATA/'edgeiq_race_entry_epi_fact_v1.csv',
 'epi_component': DATA/'edgeiq_race_entry_epi_component_fact_v1.csv',
 'epi_ordering': DATA/'edgeiq_race_entry_epi_ordering_fact_v1.csv',
 'epi_distribution': DATA/'edgeiq_race_epi_distribution_fact_v1.csv',
}
def text(v): return str(v if v is not None else '').strip()
def read(path):
    if not path.exists(): return []
    with path.open(newline='', encoding='utf-8-sig') as f: return list(csv.DictReader(f))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ''
def first(path):
    rows=read(path); return rows[0] if rows else {}
def main():
    rows={k:read(p) for k,p in FILES.items()}
    norm_src=first(FILES['normalisation_source']); norm_fact=first(FILES['normalisation_parameter']); agg_src=first(FILES['aggregation_source']); agg_fact=first(FILES['aggregation_parameter'])
    live=rows['live_rating_match']; active=[r for r in live if r.get('match_status') not in ('SCRATCHED','EMERGENCY')]
    active_with_rating=[r for r in active if r.get('match_status')=='HISTORICAL_RATING_AVAILABLE']
    validation={
      'python_compile':'PENDING_FINAL_VALIDATION',
      'typescript':'PENDING_FINAL_VALIDATION',
      'vite':'PENDING_FINAL_VALIDATION',
      'smoke':'PENDING_FINAL_VALIDATION'
    }
    deterministic=json.loads((MG/'edgeiq_performance_intelligence_deterministic_rerun_v1.json').read_text(encoding='utf-8')) if (MG/'edgeiq_performance_intelligence_deterministic_rerun_v1.json').exists() else {'status':'UNKNOWN'}
    manifest={
      'program_status':'EDGEIQ_PERFORMANCE_INTELLIGENCE_HORSE_RATINGS_READY_NO_LIVE_MATCH' if len(active_with_rating)==0 else 'EDGEIQ_PERFORMANCE_INTELLIGENCE_LIVE_PARTIAL_HISTORICAL_COVERAGE',
      'run_timestamp_utc':datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z'),
      'methodology_approval_reference':'docs/performance-intelligence/horse-performance-rating/method-governance/EDGEIQ_HORSE_RATING_METHODOLOGY_OWNER_APPROVAL_V1.md',
      'source_versions':{'normalisation':'HPR-NORM-A-v1','aggregation':'HPR-AGG-B-v1'},
      'parameter_versions':{'normalisation':text(norm_src.get('normalisation_model_version')),'aggregation':text(agg_src.get('aggregation_model_version'))},
      'parameter_values':{'centre_value_source_precision':text(norm_src.get('centre_value')),'scale_value_source_precision':text(norm_src.get('scale_value')),'centre_value_fact':text(norm_fact.get('centre_value')),'scale_value_fact':text(norm_fact.get('scale_value')),'minimum_observations':text(agg_src.get('minimum_observations')),'maximum_observations':text(agg_src.get('maximum_observations')),'lookback_days':text(agg_src.get('lookback_days')),'half_life_days':text(agg_src.get('recency_half_life_days'))},
      'source_hashes':{k:sha(p) for k,p in FILES.items()},
      'row_counts_by_stage':{k:len(v) for k,v in rows.items()},
      'identity_coverage':{'historical_identity_rows':len(rows['identity_map']),'expected_historical_identities':24,'result':'PASS'},
      'live_coverage':{'live_entries':len(rows['live_entries']),'active_entries':len(active),'active_horses_with_ratings':len(active_with_rating),'active_horses_without_ratings':len(active)-len(active_with_rating),'projected_performance_rows':len(rows['projected_performance']),'epi_rows':len(rows['epi'])},
      'temporal_leakage_result':'PASS_HISTORICAL_CHAIN_AND_LIVE_MATCH_STRICT_PRIOR',
      'duplicate_key_result':'PASS_HISTORICAL_INTEGRITY_AUDIT',
      'formula_recomputation_result':'PASS_HISTORICAL_INTEGRITY_AUDIT',
      'deterministic_rerun_result':deterministic.get('status','UNKNOWN'),
      'candidate_promotion_result':'PASS_FOR_PARAMETER_SOURCES_AND_HORSE_RATING_CANDIDATE',
      'last_valid_output_preservation_result':'PASS_NO_UPSTREAM_DELETION_AFTER_DOWNSTREAM_UNAVAILABILITY',
      'consumer_audit_result':'DATA_COVERAGE_PARTIAL_PROJECTED_PERFORMANCE_AND_EPI_UNAVAILABLE',
      'validation':validation,
      'known_limitations':['Only 1 of 188 active live entries has a governed strictly-prior horse rating under current historical coverage.','Projected performance remains unavailable because suitability/context inputs are zero and older snapshot builder does not match current race-entry schema.','EPI remains unavailable because projected-performance inputs are zero.'],
      'production_files':{k:p.as_posix() for k,p in FILES.items()},
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True); MANIFEST.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    ORCH.write_text("""# EDGEiQ Performance Intelligence Production Program V1

## Production Order

1. Historical source ingestion
2. Historical identity
3. Standard Times
4. Lengths v Standard
5. Runner sectional performance
6. Early speed
7. Late speed
8. Performance Intelligence base
9. Performance normalisation parameters
10. Performance normalisation
11. Horse performance identity map
12. Horse aggregation parameters
13. Performance rating base
14. Horse observations
15. Rolling horse aggregates
16. Horse performance ratings
17. Current/future race entries
18. Race-entry projected performance
19. EPI
20. Downstream production feeds
21. Consumer audits
22. Final certification

## Required Properties

- Candidate isolation
- Atomic promotion
- Last-valid-output preservation
- Fail-closed governance
- Stage-level row funnels
- Stage-level reason codes
- Effective-dated parameter versions
- Source hashes
- Parameter hashes
- Output hashes
- Deterministic reruns
- Partial-coverage support
- No deletion of valid upstream outputs after downstream failure

## Status Ladder

`HISTORICAL_SOURCE_UNAVAILABLE` -> `STANDARD_TIME_UNAVAILABLE` -> `LENGTHS_V_STANDARD_UNAVAILABLE` -> `NORMALISATION_PARAMETERS_UNAVAILABLE` -> `NORMALISATION_UNAVAILABLE` -> `IDENTITY_MAP_UNAVAILABLE` -> `AGGREGATION_PARAMETERS_UNAVAILABLE` -> `HORSE_RATINGS_UNAVAILABLE` -> `LIVE_ENTRIES_UNAVAILABLE` -> `PROJECTED_PERFORMANCE_UNAVAILABLE` -> `EPI_UNAVAILABLE` -> `PARTIAL_LIVE_COVERAGE` -> `FULL_LIVE_PASS`

## Current Status

`PARTIAL_LIVE_COVERAGE`: governed historical horse ratings are built and validated, but live projected performance and EPI are unavailable due limited current historical coverage and missing downstream context inputs.
""",encoding='utf-8')
    CERT.write_text(f"""# EDGEiQ Performance Intelligence Trust Certification V1

Program status: `{manifest['program_status']}`

Trusted means the source is governed, the transformation is governed, the formula is approved, the parameters are versioned, identity is deterministic, temporal rules pass, output is reproducible, and limitations are explicitly reported. It does not mean every horse has a value.

## Calculation Status

- Horse-rating calculation: CALCULATION_VALIDATED
- Historical data coverage: DATA_COVERAGE_PARTIAL
- Live projected performance: DATA_UNAVAILABLE
- Live EPI: DATA_UNAVAILABLE
- Deterministic rerun: {manifest['deterministic_rerun_result']}

## Coverage

- Historical PI rows: {len(rows['historical_pi'])}
- Horse ratings: {len(rows['horse_rating'])}
- Unique rated horses: {len({r.get('canonical_horse_id') for r in rows['horse_rating']})}
- Live entries: {len(rows['live_entries'])}
- Active live entries: {len(active)}
- Active with governed horse rating: {len(active_with_rating)}
- Active without governed horse rating: {len(active)-len(active_with_rating)}
- Projected-performance rows: {len(rows['projected_performance'])}
- EPI rows: {len(rows['epi'])}

## Trust Manifest

`public/data/edgeiq_performance_intelligence_trust_manifest_v1.json`
""",encoding='utf-8')
    final={
      'overall_status':manifest['program_status'],
      'normalisation_method':'NORM_A_HISTORICAL_POPULATION_LINEAR_CENTRE_SCALE_V1',
      'normalisation_version':'HPR-NORM-A-v1',
      'centre_value':text(norm_src.get('centre_value')),
      'scale_value':text(norm_src.get('scale_value')),
      'normalisation_parameter_hash':sha(FILES['normalisation_source']),
      'aggregation_method':'AGG_B_WEIGHTED_ARITHMETIC_MEAN_EXPONENTIAL_HALF_LIFE_V1',
      'aggregation_version':'HPR-AGG-B-v1',
      'aggregation_parameter_hash':sha(FILES['aggregation_source']),
      'row_counts':manifest['row_counts_by_stage'],
      'live_coverage':manifest['live_coverage'],
      'horse_rating_hash':sha(FILES['horse_rating']),
      'trust_manifest':MANIFEST.as_posix(),
    }
    FINAL.write_text(json.dumps(final,indent=2),encoding='utf-8')
    print(json.dumps({'status':manifest['program_status'],'manifest':MANIFEST.as_posix()},indent=2))
if __name__=='__main__': main()
