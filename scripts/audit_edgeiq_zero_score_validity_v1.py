import csv
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'
feed=DATA/'edgeiq_command_enrichment_feed_v2.csv'; out=DATA/'edgeiq_zero_score_validity_v1.csv'; sumout=DATA/'edgeiq_zero_score_validity_v1_summary.csv'; report=DATA/'edgeiq_zero_score_validity_v1_report.txt'
fields={'distance':'edgeiq_score_distance_v2','condition':'edgeiq_score_condition_v2','class':'edgeiq_score_class_v2','campaign':'edgeiq_score_campaign_v2','pace':'edgeiq_score_pace_v2','connections':'edgeiq_score_connections_v2','market':'edgeiq_score_market_v2','confidence':'edgeiq_score_confidence_v2'}
def read(path):
    with path.open('r',newline='',encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return list(r)
def parse(v):
    s=str(v or '').strip()
    if s=='': return None
    try: return float(s)
    except Exception: return None
rows=read(feed); outrows=[]
for label,col in fields.items():
    vals=[parse(r.get(col)) for r in rows]
    zero=sum(1 for v in vals if v==0)
    blank=sum(1 for r in rows if str(r.get(col,'')).strip()=='')
    null=blank
    src_missing=sum(1 for r in rows if f'{label.upper()}:MISSING' in str(r.get('edgeiq_score_source_v2','')).upper())
    # In V2, blank with source MISSING means not loaded. Zero is only real if nonblank and source not MISSING.
    zero_real=sum(1 for r in rows if parse(r.get(col))==0 and f'{label.upper()}:MISSING' not in str(r.get('edgeiq_score_source_v2','')).upper())
    meaning='REAL_SCORE' if zero and zero_real==zero else ('MISSING_ENCODED_OR_NOT_LOADED' if zero or blank else 'NO_ZERO_VALUES')
    outrows.append({'factor':label,'field':col,'zero_count':zero,'blank_count':blank,'null_count':null,'source_missing_count':src_missing,'zero_real_score_count':zero_real,'zero_meaning':meaning})
status='ZERO_SCORE_VALIDITY_AUDIT_COMPLETE'
summary=[{'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'rows':len(rows),'zero_real_factors':'|'.join([r['factor'] for r in outrows if int(r['zero_real_score_count'])>0]),'missing_or_not_loaded_factors':'|'.join([r['factor'] for r in outrows if r['zero_meaning']=='MISSING_ENCODED_OR_NOT_LOADED']),'recommendation':'DISPLAY_NOT_LOADED_FOR_BLANK_OR_SOURCE_MISSING; SHOW_ZERO_ONLY_WHEN_ZERO_REAL_SCORE_COUNT_GT_0'}]
for p,data in [(out,outrows),(sumout,summary)]:
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0].keys())); w.writeheader(); w.writerows(data)
report.write_text('\n'.join(['EDGEiQ Zero Score Validity Audit V1','='*42,f'Status: {status}',f'Rows: {len(rows)}']+[f"- {r['factor']}: zero={r['zero_count']} blank={r['blank_count']} source_missing={r['source_missing_count']} zero_real={r['zero_real_score_count']} meaning={r['zero_meaning']}" for r in outrows]+[f'Recommendation: {summary[0]["recommendation"]}'])+'\n',encoding='utf-8')
print(status); [print(r) for r in outrows]
