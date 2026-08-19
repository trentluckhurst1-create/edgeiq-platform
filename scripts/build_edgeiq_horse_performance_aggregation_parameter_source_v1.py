from __future__ import annotations
import csv, hashlib, json, shutil
from pathlib import Path
from datetime import datetime, timezone, date
from decimal import Decimal
ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'config'/'performance-intelligence'
DOC=ROOT/'docs'/'performance-intelligence'/'horse-performance-rating'/'method-governance'
BASE=ROOT/'public'/'data'/'edgeiq_performance_intelligence_base_fact_v1.csv'
APPROVAL=DOC/'EDGEIQ_HORSE_RATING_METHODOLOGY_OWNER_APPROVAL_V1.md'
CANDIDATE=CONFIG/'edgeiq_horse_performance_aggregation_parameter_source_v1_CANDIDATE.csv'
MANIFEST=DOC/'edgeiq_horse_performance_aggregation_parameter_source_v1_candidate_manifest.json'
FIELDS=['aggregation_method','maximum_observations','lookback_days','minimum_observations','recency_weighting_method','recency_half_life_days','aggregation_model_version','parameter_status','effective_from_date','effective_to_date','evidence_reference','evidence_sha256']

def text(v): return str(v if v is not None else '').strip()
def sha(parts): return hashlib.sha256('\x1f'.join(text(p) for p in parts).encode('utf-8')).hexdigest()
def min_base_date():
    with BASE.open(newline='', encoding='utf-8-sig') as f:
        rows=list(csv.DictReader(f))
    dates=sorted({text(r.get('race_date')) for r in rows if text(r.get('performance_status'))=='OBSERVED_GOVERNED' and text(r.get('race_date'))})
    if not dates: raise RuntimeError('No governed base dates found')
    return dates[0]

def main():
    if not APPROVAL.exists(): raise RuntimeError(f'Missing approval document: {APPROVAL}')
    eff=min_base_date()
    semantic='AGG_B_WEIGHTED_ARITHMETIC_MEAN_EXPONENTIAL_HALF_LIFE_V1'
    row={
        'aggregation_method':'WEIGHTED_ARITHMETIC_MEAN',
        'maximum_observations':'20',
        'lookback_days':'730',
        'minimum_observations':'5',
        'recency_weighting_method':'EXPONENTIAL_HALF_LIFE',
        'recency_half_life_days':'120',
        'aggregation_model_version':'HPR-AGG-B-v1',
        'parameter_status':'APPROVED',
        'effective_from_date':eff,
        'effective_to_date':'',
        'evidence_reference':APPROVAL.as_posix(),
        'evidence_sha256':'',
    }
    row['evidence_sha256']=sha([semantic]+[row[f] for f in FIELDS if f!='evidence_sha256']+[APPROVAL.read_text(encoding='utf-8')])
    CONFIG.mkdir(parents=True, exist_ok=True)
    with CANDIDATE.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=FIELDS, lineterminator='\n'); w.writeheader(); w.writerow(row)
    manifest={
        'status':'AGGREGATION_PARAMETER_CANDIDATE_BUILT',
        'semantic_method':semantic,
        'executable_method':'WEIGHTED_ARITHMETIC_MEAN',
        'recency_weighting_method':'EXPONENTIAL_HALF_LIFE',
        'aggregation_model_version':'HPR-AGG-B-v1',
        'minimum_observations':5,
        'maximum_observations':20,
        'lookback_days':730,
        'recency_half_life_days':120,
        'observation_order':'MOST_RECENT_FIRST',
        'best_run_treatment':'NONE',
        'poor_run_treatment':'INCLUDE_IF_ELIGIBLE',
        'outlier_method':'NONE_IN_HPR_AGG_B_V1',
        'surface_treatment':'NO_ADDITIONAL_AGGREGATION_WEIGHT',
        'distance_treatment':'NO_ADDITIONAL_AGGREGATION_WEIGHT',
        'predictive_temporal_rule':'STRICTLY_PRIOR_TO_TARGET_RACE',
        'missing_parameter_rule':'FAIL_CLOSED_NO_FALLBACK_UNLESS_APPROVED',
        'effective_from_date':eff,
        'effective_to_date':'',
        'source_evidence_sha256':row['evidence_sha256'],
        'candidate_hash':hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(),
        'built_at_utc':datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z'),
    }
    DOC.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('status=AGGREGATION_PARAMETER_CANDIDATE_BUILT')
    print(f"candidate={CANDIDATE}")
    print(f"candidate_hash={manifest['candidate_hash']}")
if __name__=='__main__': main()
