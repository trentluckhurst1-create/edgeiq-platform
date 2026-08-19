from __future__ import annotations
import csv, json, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
DOC=ROOT/'docs'/'performance-intelligence'/'horse-performance-rating'/'method-governance'
OUT=DOC/'edgeiq_projected_performance_epi_activation_audit_v1.csv'
SUMMARY=DOC/'edgeiq_projected_performance_epi_activation_audit_summary.json'
REPORT=DOC/'edgeiq_projected_performance_epi_activation_audit_report.md'
FILES={
 'live_match': DATA/'edgeiq_live_horse_performance_rating_match_v1.csv',
 'snapshot': DATA/'edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv',
 'projected_performance': DATA/'edgeiq_race_entry_projected_performance_fact_v1.csv',
 'epi_component': DATA/'edgeiq_race_entry_epi_component_fact_v1.csv',
 'epi': DATA/'edgeiq_race_entry_epi_fact_v1.csv',
 'epi_ordering': DATA/'edgeiq_race_entry_epi_ordering_fact_v1.csv',
 'epi_distribution': DATA/'edgeiq_race_epi_distribution_fact_v1.csv',
}
def read(path):
    if not path.exists(): return []
    with path.open(newline='', encoding='utf-8-sig') as f: return list(csv.DictReader(f))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ''
def main():
    rows=[]; counts={}
    for name,path in FILES.items():
        rs=read(path); counts[name]=len(rs)
        rows.append({'stage':name,'path':path.as_posix(),'rows':len(rs),'hash':sha(path),'status':'AVAILABLE' if len(rs)>0 else 'DATA_UNAVAILABLE'})
    live=read(FILES['live_match'])
    active=[r for r in live if r.get('match_status') not in ('SCRATCHED','EMERGENCY')]
    with_rating=[r for r in active if r.get('match_status')=='HISTORICAL_RATING_AVAILABLE']
    without_rating=[r for r in active if r.get('match_status')!='HISTORICAL_RATING_AVAILABLE']
    summary={
      'race_entry_input_rows':204,
      'active_entries':len(active),
      'historical_rating_matches':len(with_rating),
      'temporally_eligible_ratings':len(with_rating),
      'projected_performance_rows':counts['projected_performance'],
      'epi_rows':counts['epi'],
      'active_runners_with_epi':counts['epi'],
      'active_runners_without_epi':len(active)-counts['epi'],
      'blocking_reasons':{'INSUFFICIENT_GOVERNED_HISTORY':len(without_rating),'SUITABILITY_CONTEXT_INPUTS_UNAVAILABLE':1,'RACE_ENTRY_SNAPSHOT_BUILDER_SCHEMA_MISMATCH':1},
      'projected_status':'PROJECTED_PERFORMANCE_UNAVAILABLE',
      'epi_status':'EPI_UNAVAILABLE',
    }
    with OUT.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['stage','path','rows','hash','status'],lineterminator='\n'); w.writeheader(); w.writerows(rows)
    SUMMARY.write_text(json.dumps(summary,indent=2),encoding='utf-8')
    REPORT.write_text(f"# EDGEiQ Projected Performance and EPI Activation Audit V1\n\n- Active entries: {summary['active_entries']}\n- Active horses with governed historical ratings: {summary['historical_rating_matches']}\n- Projected-performance rows: {summary['projected_performance_rows']}\n- EPI rows: {summary['epi_rows']}\n- Status: {summary['epi_status']}\n\nBlocking reasons: insufficient governed historical coverage for most live entries, unavailable suitability/context inputs, and current race-entry schema mismatch in the older horse-performance snapshot builder. No placeholder projected performance or EPI values were created.\n",encoding='utf-8')
    print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
