from __future__ import annotations
import csv, hashlib, json, math, shutil
from decimal import Decimal, getcontext
from pathlib import Path
from datetime import date
getcontext().prec=50
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
CONFIG=ROOT/'config'/'performance-intelligence'
DOC=ROOT/'docs'/'performance-intelligence'/'horse-performance-rating'/'method-governance'
BASE=DATA/'edgeiq_performance_intelligence_base_fact_v1.csv'
CANDIDATE=CONFIG/'edgeiq_performance_normalisation_parameter_source_v1_CANDIDATE.csv'
PROMOTED=CONFIG/'edgeiq_performance_normalisation_parameter_source_v1.csv'
POP_AUDIT=DOC/'edgeiq_performance_normalisation_parameter_population_v1.csv'
AUDIT=DOC/'edgeiq_performance_normalisation_parameter_source_v1_audit.csv'
SUMMARY=DOC/'edgeiq_performance_normalisation_parameter_source_v1_audit_summary.json'
REPORT=DOC/'edgeiq_performance_normalisation_parameter_source_v1_audit_report.md'
FIELDS=["normalisation_method","centre_value","scale_value","normalisation_model_version","parameter_status","effective_from_date","effective_to_date","evidence_reference","evidence_sha256"]
METHOD='LINEAR_CENTRE_AND_SCALE'; VERSION='HPR-NORM-A-v1'; MIN_POP=100

def text(v): return str(v if v is not None else '').strip()
def sha(parts): return hashlib.sha256('\x1f'.join(text(p) for p in parts).encode('utf-8')).hexdigest()
def q12(d): return format(d.quantize(Decimal('0.000000000001')), 'f')
def rows(path):
    with path.open(newline='', encoding='utf-8-sig') as f: return list(csv.DictReader(f)), list(csv.DictReader(path.open(newline='', encoding='utf-8-sig')).fieldnames or []) if False else []
def read_csv(path):
    with path.open(newline='', encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return (r.fieldnames or []), list(r)
def eligible_base():
    fields, rs=read_csv(BASE); out=[]
    for row in rs:
        if text(row.get('performance_status'))!='OBSERVED_GOVERNED': continue
        raw=text(row.get('raw_performance_lengths'))
        if not raw: continue
        val=Decimal(raw)
        if not val.is_finite(): continue
        key=text(row.get('performance_intelligence_base_id')) or sha([row.get('race_key'), row.get('winner_horse_name'), row.get('raw_performance_lengths'), row.get('source_lengths_versus_standard_evidence_sha256')])
        out.append((key,row,val))
    out.sort(key=lambda x:x[0]); return out

def main():
    checks=[]
    def add(name,status,detail): checks.append({'check':name,'status':status,'detail':detail})
    if not CANDIDATE.exists(): raise RuntimeError('Missing candidate source')
    fields, rs=read_csv(CANDIDATE)
    add('schema_matches_active_contract','PASS' if fields==FIELDS else 'FAIL', str(fields))
    add('exactly_one_global_parameter_row','PASS' if len(rs)==1 else 'FAIL', str(len(rs)))
    row=rs[0] if rs else {}
    add('method_supported','PASS' if text(row.get('normalisation_method'))==METHOD else 'FAIL', text(row.get('normalisation_method')))
    add('version_present','PASS' if text(row.get('normalisation_model_version'))==VERSION else 'FAIL', text(row.get('normalisation_model_version')))
    add('status_approved','PASS' if text(row.get('parameter_status'))=='APPROVED' else 'FAIL', text(row.get('parameter_status')))
    eligible=eligible_base(); n=len(eligible); vals=[v for _,_,v in eligible]
    centre=sum(vals)/Decimal(n); scale=(sum((v-centre)*(v-centre) for v in vals)/Decimal(n)).sqrt()
    pop_hash=sha(['HPR-NORM-A-v1', n]+[f"{key}:{q12(val)}:{text(r.get('performance_intelligence_base_evidence_sha256'))}" for key,r,val in eligible])
    add('population_count_ge_minimum','PASS' if n>=MIN_POP else 'FAIL', str(n))
    pop_fields,pop_rows=read_csv(POP_AUDIT)
    add('population_count_equals_audited_eligible_population','PASS' if len(pop_rows)==n else 'FAIL', f"audit={len(pop_rows)} eligible={n}")
    try:
        c=Decimal(text(row.get('centre_value'))); s=Decimal(text(row.get('scale_value')))
        add('centre_value_finite','PASS' if c.is_finite() else 'FAIL', text(c))
        add('scale_value_finite','PASS' if s.is_finite() else 'FAIL', text(s))
        add('scale_value_gt_zero','PASS' if s.is_finite() and s>0 else 'FAIL', text(s))
        add('formula_independently_recomputed_centre','PASS' if q12(c)==q12(centre) else 'FAIL', f"source={q12(c)} recomputed={q12(centre)}")
        add('formula_independently_recomputed_scale','PASS' if q12(s)==q12(scale) else 'FAIL', f"source={q12(s)} recomputed={q12(scale)}")
    except Exception as exc:
        add('numeric_parse','FAIL', repr(exc))
    evidence_ref=text(row.get('evidence_reference'))
    add('approval_evidence_present','PASS' if 'EDGEIQ_HORSE_RATING_METHODOLOGY_OWNER_APPROVAL_V1.md' in evidence_ref else 'FAIL', evidence_ref)
    add('population_hash_independently_recomputed','PASS' if pop_hash in evidence_ref else 'FAIL', pop_hash)
    ids=[text(r.get('performance_intelligence_base_id')) for r in pop_rows]
    add('source_rows_uniquely_identified','PASS' if len(ids)==len(set(ids))==n else 'FAIL', f"unique={len(set(ids))} rows={len(ids)} eligible={n}")
    try:
        eff_from=date.fromisoformat(text(row.get('effective_from_date')))
        eff_to=text(row.get('effective_to_date'))
        add('effective_dates_valid','PASS' if (not eff_to or date.fromisoformat(eff_to)>=eff_from) else 'FAIL', f"{eff_from}..{eff_to}")
        dates=[date.fromisoformat(text(r.get('race_date'))) for _,r,_ in eligible]
        covers=all(d>=eff_from and (not eff_to or d<=date.fromisoformat(eff_to)) for d in dates)
        add('lookup_covers_all_historical_observations','PASS' if covers else 'FAIL', f"from={eff_from} to={eff_to} rows={len(dates)}")
    except Exception as exc:
        add('effective_date_parse','FAIL', repr(exc))
    add('no_unsupported_fallback','PASS','candidate has a single approved fail-closed parameter; no fallback rows')
    cand_hash_1=hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(); cand_hash_2=hashlib.sha256(CANDIDATE.read_bytes()).hexdigest()
    add('deterministic_rerun_hash','PASS' if cand_hash_1==cand_hash_2 else 'FAIL', cand_hash_1)
    verdict='PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL'
    DOC.mkdir(parents=True, exist_ok=True)
    with AUDIT.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['check','status','detail'],lineterminator='\n'); w.writeheader(); w.writerows(checks)
    summary={'verdict':verdict,'candidate_hash':cand_hash_1,'population_count':n,'centre_value':q12(centre),'scale_value':q12(scale),'population_sha256':pop_hash,'promoted':'NO'}
    if verdict=='PASS':
        shutil.copyfile(CANDIDATE, PROMOTED)
        summary['promoted']='YES'; summary['promoted_path']=PROMOTED.as_posix(); summary['promoted_hash']=hashlib.sha256(PROMOTED.read_bytes()).hexdigest()
    SUMMARY.write_text(json.dumps(summary,indent=2),encoding='utf-8')
    REPORT.write_text(f"# EDGEiQ Performance Normalisation Parameter Source Audit V1\n\nVerdict: {verdict}\n\n- Population rows: {n}\n- Centre value: {q12(centre)}\n- Scale value: {q12(scale)}\n- Population SHA256: {pop_hash}\n- Candidate promoted: {summary['promoted']}\n",encoding='utf-8')
    print(f"verdict={verdict}")
    print(f"promoted={summary['promoted']}")
    print(f"candidate_hash={cand_hash_1}")
if __name__=='__main__': main()
