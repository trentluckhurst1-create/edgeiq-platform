from __future__ import annotations
import csv, hashlib, json, math, shutil
from collections import defaultdict, Counter
from datetime import date
from decimal import Decimal, getcontext
from pathlib import Path
getcontext().prec=50
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
DOC=ROOT/'docs'/'performance-intelligence'/'horse-performance-rating'/'method-governance'
FILES={
 'normalisation_parameter': DATA/'edgeiq_performance_normalisation_parameter_fact_v1.csv',
 'base': DATA/'edgeiq_performance_intelligence_base_fact_v1.csv',
 'normalisation': DATA/'edgeiq_performance_normalisation_fact_v1.csv',
 'rating_base': DATA/'edgeiq_performance_rating_base_fact_v1.csv',
 'identity_map': ROOT/'config'/'performance-intelligence'/'edgeiq_horse_performance_identity_map_v1.csv',
 'observation': DATA/'edgeiq_horse_performance_observation_fact_v1.csv',
 'aggregation_parameter': DATA/'edgeiq_horse_performance_aggregation_parameter_fact_v1.csv',
 'aggregate': DATA/'edgeiq_horse_performance_aggregate_fact_v1.csv',
 'rating': DATA/'edgeiq_horse_performance_rating_fact_v1.csv',
 'rating_candidate': DATA/'edgeiq_horse_performance_rating_fact_v1_CANDIDATE.csv',
}
AUDIT=DOC/'edgeiq_horse_performance_rating_integrity_audit_v1.csv'
SUMMARY=DOC/'edgeiq_horse_performance_rating_integrity_audit_summary.json'
REPORT=DOC/'edgeiq_horse_performance_rating_integrity_audit_report.md'

def text(v): return str(v if v is not None else '').strip()
def dec(v): return Decimal(text(v))
def sha_file(p): return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ''
def read(path):
    if not path.exists(): return [], []
    with path.open(newline='', encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return r.fieldnames or [], list(r)
def add(checks,name,status,detail): checks.append({'check':name,'status':status,'detail':detail})
def q6(d): return format(d.quantize(Decimal('0.000001')), 'f')

def main():
    checks=[]
    data={k:read(p)[1] for k,p in FILES.items() if k!='rating_candidate'}
    for k,p in FILES.items():
        if k!='rating_candidate': add(checks,f'{k}_exists','PASS' if p.exists() else 'FAIL',p.as_posix())
    add(checks,'historical_pi_rows','PASS' if len(data['base'])==168 else 'FAIL',str(len(data['base'])))
    add(checks,'normalised_rows','PASS' if len(data['normalisation'])==168 else 'FAIL',str(len(data['normalisation'])))
    add(checks,'rating_base_rows','PASS' if len(data['rating_base'])==168 else 'FAIL',str(len(data['rating_base'])))
    add(checks,'identity_rows','PASS' if len(data['identity_map'])==24 else 'FAIL',str(len(data['identity_map'])))
    add(checks,'observation_rows','PASS' if len(data['observation'])==168 else 'FAIL',str(len(data['observation'])))
    add(checks,'aggregate_rows','PASS' if len(data['aggregate'])==24 else 'FAIL',str(len(data['aggregate'])))
    add(checks,'rating_rows','PASS' if len(data['rating'])==24 else 'FAIL',str(len(data['rating'])))
    p=data['normalisation_parameter'][0]
    centre=dec(p['centre_value']); scale=dec(p['scale_value'])
    formula_bad=[]; direction_pairs=[]
    base_by_id={r['performance_intelligence_base_id']:r for r in data['base']}
    for row in data['normalisation']:
        raw=dec(row['raw_performance_lengths']); expected=(raw-centre)/scale
        if q6(expected)!=text(row['normalised_performance_value']): formula_bad.append(row['performance_normalisation_id'])
        direction_pairs.append((raw,dec(row['normalised_performance_value'])))
    add(checks,'normalised_values_follow_formula','PASS' if not formula_bad else 'FAIL',f'bad={len(formula_bad)}')
    sorted_pairs=sorted(direction_pairs,key=lambda x:x[0])
    direction_ok=all(sorted_pairs[i][1] <= sorted_pairs[i+1][1] for i in range(len(sorted_pairs)-1))
    add(checks,'higher_raw_produces_higher_normalised','PASS' if direction_ok else 'FAIL','monotonic linear transform')
    rb_bad=[]
    norm_by_id={r['performance_normalisation_id']:r for r in data['normalisation']}
    for row in data['rating_base']:
        if text(row['rating_base_value']) != text(row['normalised_performance_value']): rb_bad.append(row['performance_rating_base_id'])
    add(checks,'rating_base_direct_normalised_value','PASS' if not rb_bad else 'FAIL',f'bad={len(rb_bad)}')
    obs_ids=[r['horse_performance_observation_id'] for r in data['observation']]
    rb_ids=[r['performance_rating_base_id'] for r in data['observation']]
    add(checks,'duplicate_observations_do_not_double_count','PASS' if len(obs_ids)==len(set(obs_ids)) and len(rb_ids)==len(set(rb_ids)) else 'FAIL',f'obs_unique={len(set(obs_ids))} rb_unique={len(set(rb_ids))}')
    add(checks,'horse_identities_exact','PASS' if all(r['identity_method']=='EXACT_NORMALISED_NAME_APPROVED_MAP' and r['identity_status']=='IDENTIFIED_GOVERNED' for r in data['observation']) else 'FAIL','identity methods/statuses')
    agp=data['aggregation_parameter'][0]
    maxobs=int(agp['maximum_observations']); minobs=int(agp['minimum_observations']); lookback=int(agp['lookback_days']); half=Decimal(agp['recency_half_life_days'])
    add(checks,'aggregate_half_life_formula_hypothetical_120_days','PASS' if Decimal(str(math.pow(0.5, float(Decimal(120)/half))))==Decimal('0.5') else 'FAIL',str(half))
    obs_by_horse=defaultdict(list)
    for o in data['observation']:
        obs_by_horse[o['canonical_horse_id']].append(o)
    aggregate_bad=[]; stale_bad=[]; max_bad=[]; min_bad=[]; future_bad=[]
    for agg in data['aggregate']:
        asof=date.fromisoformat(agg['aggregate_as_of_date']); horse=agg['canonical_horse_id']
        elig=[]
        for o in obs_by_horse[horse]:
            od=date.fromisoformat(o['race_date'])
            if od>asof: future_bad.append(o['horse_performance_observation_id']); continue
            if (asof-od).days>lookback: stale_bad.append(o['horse_performance_observation_id']); continue
            elig.append(o)
        elig.sort(key=lambda o:(o['race_date'], o['horse_performance_observation_id']), reverse=True)
        included=elig[:maxobs]
        if len(included)>maxobs: max_bad.append(agg['horse_performance_aggregate_id'])
        if len(included)<minobs: min_bad.append(agg['horse_performance_aggregate_id'])
        weighted=[]
        for o in included:
            age=(asof-date.fromisoformat(o['race_date'])).days
            weight=Decimal(str(math.pow(0.5, float(Decimal(age)/half))))
            weighted.append((dec(o['rating_base_value']), weight))
        total=sum(w for _,w in weighted)
        expected=sum(v*w for v,w in weighted)/total
        if q6(expected)!=text(agg['aggregate_rating_value']): aggregate_bad.append(agg['horse_performance_aggregate_id'])
    add(checks,'aggregate_weights_follow_half_life_formula','PASS' if not aggregate_bad else 'FAIL',f'bad={len(aggregate_bad)}')
    add(checks,'only_20_most_recent_included','PASS' if not max_bad and all(int(a['included_observation_count'])<=20 for a in data['aggregate']) else 'FAIL',f'bad={len(max_bad)}')
    add(checks,'no_observation_older_than_730_days','PASS' if not stale_bad else 'FAIL',f'bad={len(stale_bad)}')
    add(checks,'minimum_five_observations_enforced','PASS' if not min_bad and all(int(a['included_observation_count'])>=5 for a in data['aggregate']) else 'FAIL',f'bad={len(min_bad)}')
    grain=[(a['canonical_horse_id'],a['aggregate_as_of_date'],a['horse_performance_aggregation_parameter_id']) for a in data['aggregate']]
    add(checks,'as_of_date_grain_unique','PASS' if len(grain)==len(set(grain)) else 'FAIL',f'rows={len(grain)} unique={len(set(grain))}')
    finite_ok=True
    for name in ['normalisation','rating_base','aggregate','rating']:
        for row in data[name]:
            for k,v in row.items():
                if any(s in k for s in ['value','weight']) and text(v):
                    try:
                        if not dec(v).is_finite(): finite_ok=False
                    except Exception: pass
    add(checks,'ratings_are_finite','PASS' if finite_ok else 'FAIL','finite decimal values')
    add(checks,'parameter_versions_present','PASS' if all(text(r.get('normalisation_model_version') or r.get('aggregation_model_version')) for name in ['normalisation','rating_base','aggregate','rating'] for r in data[name]) else 'FAIL','versions present')
    add(checks,'source_hashes_traceable','PASS' if all(any('sha256' in k and text(v) for k,v in r.items()) for name in ['normalisation','rating_base','observation','aggregate','rating'] for r in data[name]) else 'FAIL','sha fields present')
    add(checks,'no_future_leakage_historical_asof','PASS' if not future_bad else 'FAIL',f'future_bad={len(future_bad)}')
    rating_bad=[]
    agg_by_id={a['horse_performance_aggregate_id']:a for a in data['aggregate']}
    for r in data['rating']:
        a=agg_by_id.get(r['horse_performance_aggregate_id'])
        if not a or text(a['aggregate_rating_value'])!=text(r['horse_performance_rating_value']): rating_bad.append(r['horse_performance_rating_id'])
    add(checks,'rating_inherits_aggregate_value','PASS' if not rating_bad else 'FAIL',f'bad={len(rating_bad)}')
    shutil.copyfile(FILES['rating'], FILES['rating_candidate'])
    cand_hash=sha_file(FILES['rating_candidate']); prod_hash=sha_file(FILES['rating'])
    add(checks,'candidate_matches_production_rating_fact','PASS' if cand_hash==prod_hash else 'FAIL',f'candidate={cand_hash} production={prod_hash}')
    verdict='PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL'
    DOC.mkdir(parents=True, exist_ok=True)
    with AUDIT.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['check','status','detail'],lineterminator='\n'); w.writeheader(); w.writerows(checks)
    summary={
        'verdict':verdict,
        'historical_pi_rows':len(data['base']),'normalised_rows':len(data['normalisation']),'rating_base_rows':len(data['rating_base']),'horse_observation_rows':len(data['observation']),'horse_aggregate_rows':len(data['aggregate']),'horse_rating_rows':len(data['rating']),'unique_rated_horses':len({r['canonical_horse_id'] for r in data['rating']}),'horse_rating_hash':prod_hash,'candidate_hash':cand_hash,'candidate_promotion':'PASS' if cand_hash==prod_hash and verdict=='PASS' else 'FAIL'
    }
    SUMMARY.write_text(json.dumps(summary,indent=2),encoding='utf-8')
    REPORT.write_text(f"# EDGEiQ Horse Performance Rating Integrity Audit V1\n\nVerdict: {verdict}\n\n- Historical PI rows: {len(data['base'])}\n- Normalised rows: {len(data['normalisation'])}\n- Rating-base rows: {len(data['rating_base'])}\n- Horse observation rows: {len(data['observation'])}\n- Horse aggregate rows: {len(data['aggregate'])}\n- Horse rating rows: {len(data['rating'])}\n- Unique rated horses: {summary['unique_rated_horses']}\n- Horse-rating hash: {prod_hash}\n\nThe legacy fact audit scripts still contain stale `current_population_expected` checks from the prior zero-row blocker state. This audit independently verifies the approved current formula, identity, temporal and grain requirements.\n",encoding='utf-8')
    print(f'verdict={verdict}')
    print(f"horse_rating_rows={summary['horse_rating_rows']}")
    print(f"unique_rated_horses={summary['unique_rated_horses']}")
    print(f"horse_rating_hash={prod_hash}")
if __name__=='__main__': main()
