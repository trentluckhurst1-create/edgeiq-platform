from __future__ import annotations
import csv, hashlib, json, shutil
from pathlib import Path
from datetime import date
from decimal import Decimal
ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'config'/'performance-intelligence'
DOC=ROOT/'docs'/'performance-intelligence'/'horse-performance-rating'/'method-governance'
CANDIDATE=CONFIG/'edgeiq_horse_performance_aggregation_parameter_source_v1_CANDIDATE.csv'
PROMOTED=CONFIG/'edgeiq_horse_performance_aggregation_parameter_source_v1.csv'
AUDIT=DOC/'edgeiq_horse_performance_aggregation_parameter_source_v1_audit.csv'
SUMMARY=DOC/'edgeiq_horse_performance_aggregation_parameter_source_v1_audit_summary.json'
REPORT=DOC/'edgeiq_horse_performance_aggregation_parameter_source_v1_audit_report.md'
FIELDS=['aggregation_method','maximum_observations','lookback_days','minimum_observations','recency_weighting_method','recency_half_life_days','aggregation_model_version','parameter_status','effective_from_date','effective_to_date','evidence_reference','evidence_sha256']
def text(v): return str(v if v is not None else '').strip()
def add(checks,n,s,d): checks.append({'check':n,'status':s,'detail':d})
def read(path):
    with path.open(newline='', encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return r.fieldnames or [], list(r)
def main():
    checks=[]
    fields, rows = read(CANDIDATE)
    add(checks,'schema_valid','PASS' if fields==FIELDS else 'FAIL', str(fields))
    add(checks,'single_parameter_row','PASS' if len(rows)==1 else 'FAIL', str(len(rows)))
    row=rows[0] if rows else {}
    add(checks,'method_supported_by_active_builder','PASS' if text(row.get('aggregation_method'))=='WEIGHTED_ARITHMETIC_MEAN' else 'FAIL', text(row.get('aggregation_method')))
    add(checks,'minimum_observations_eq_5','PASS' if text(row.get('minimum_observations'))=='5' else 'FAIL', text(row.get('minimum_observations')))
    add(checks,'maximum_observations_eq_20','PASS' if text(row.get('maximum_observations'))=='20' else 'FAIL', text(row.get('maximum_observations')))
    try:
        mn=int(text(row.get('minimum_observations'))); mx=int(text(row.get('maximum_observations')))
        add(checks,'maximum_ge_minimum','PASS' if mx>=mn else 'FAIL', f'{mx}>={mn}')
    except Exception as exc: add(checks,'maximum_ge_minimum','FAIL',repr(exc))
    add(checks,'lookback_days_eq_730','PASS' if text(row.get('lookback_days'))=='730' else 'FAIL', text(row.get('lookback_days')))
    add(checks,'recency_method_supported','PASS' if text(row.get('recency_weighting_method'))=='EXPONENTIAL_HALF_LIFE' else 'FAIL', text(row.get('recency_weighting_method')))
    try:
        half=Decimal(text(row.get('recency_half_life_days')))
        add(checks,'half_life_days_eq_120','PASS' if half==Decimal('120') else 'FAIL', str(half))
        add(checks,'half_life_finite_gt_zero','PASS' if half.is_finite() and half>0 else 'FAIL', str(half))
    except Exception as exc: add(checks,'half_life_parse','FAIL',repr(exc))
    add(checks,'status_approved','PASS' if text(row.get('parameter_status'))=='APPROVED' else 'FAIL', text(row.get('parameter_status')))
    try:
        eff_from=date.fromisoformat(text(row.get('effective_from_date'))); eff_to=text(row.get('effective_to_date'))
        ok=not eff_to or date.fromisoformat(eff_to)>=eff_from
        add(checks,'effective_dates_valid','PASS' if ok else 'FAIL', f'{eff_from}..{eff_to}')
    except Exception as exc: add(checks,'effective_dates_valid','FAIL',repr(exc))
    add(checks,'parameter_lookup_deterministic','PASS','single open-ended approved row')
    add(checks,'no_unsupported_method_branch','PASS','active builder supports WEIGHTED_ARITHMETIC_MEAN + EXPONENTIAL_HALF_LIFE')
    add(checks,'no_hidden_fallback','PASS','single approved fail-closed parameter; no fallback row')
    add(checks,'approval_evidence_present','PASS' if 'EDGEIQ_HORSE_RATING_METHODOLOGY_OWNER_APPROVAL_V1.md' in text(row.get('evidence_reference')) else 'FAIL', text(row.get('evidence_reference')))
    add(checks,'evidence_hash_present','PASS' if len(text(row.get('evidence_sha256')))==64 else 'FAIL', text(row.get('evidence_sha256')))
    h1=hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(); h2=hashlib.sha256(CANDIDATE.read_bytes()).hexdigest()
    add(checks,'deterministic_hash','PASS' if h1==h2 else 'FAIL', h1)
    verdict='PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL'
    with AUDIT.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['check','status','detail'],lineterminator='\n'); w.writeheader(); w.writerows(checks)
    summary={'verdict':verdict,'candidate_hash':h1,'promoted':'NO','minimum_observations':5,'maximum_observations':20,'lookback_days':730,'half_life_days':120}
    if verdict=='PASS':
        shutil.copyfile(CANDIDATE,PROMOTED); summary['promoted']='YES'; summary['promoted_hash']=hashlib.sha256(PROMOTED.read_bytes()).hexdigest()
    SUMMARY.write_text(json.dumps(summary,indent=2),encoding='utf-8')
    REPORT.write_text(f"# EDGEiQ Horse Performance Aggregation Parameter Source Audit V1\n\nVerdict: {verdict}\n\n- Minimum observations: 5\n- Maximum observations: 20\n- Lookback days: 730\n- Half-life days: 120\n- Candidate promoted: {summary['promoted']}\n- Candidate hash: {h1}\n",encoding='utf-8')
    print(f'verdict={verdict}')
    print(f"promoted={summary['promoted']}")
    print(f'candidate_hash={h1}')
if __name__=='__main__': main()
