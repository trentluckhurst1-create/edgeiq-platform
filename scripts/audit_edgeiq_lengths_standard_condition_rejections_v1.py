from __future__ import annotations
import csv, json, re, sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
csv.field_size_limit(sys.maxsize)
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'; DOCS=ROOT/'docs'/'performance-intelligence'/'restart-v1'
REJECTIONS=DATA/'edgeiq_lengths_versus_standard_fact_v1_rejections.csv'
OUT_CSV=DATA/'edgeiq_lengths_standard_condition_rejection_audit_v1.csv'
OUT_SUMMARY=DATA/'edgeiq_lengths_standard_condition_rejection_audit_v1_summary.json'
OUT_MD=DOCS/'EDGEIQ_LENGTHS_STANDARD_CONDITION_REJECTION_AUDIT_V1.md'
CANDIDATE_FILES=[DATA/'edgeiq_historical_results_warehouse_v2_graphql.csv',DATA/'edgeiq_vic_three_day_race_list_v1.csv',DATA/'edgeiq_vic_three_day_race_fields.csv',DATA/'edgeiq_live_track_intelligence_v2_1.csv',DATA/'edgeiq_track_intelligence_card_v1.csv',DATA/'edgeiq_racingcom_race_speed_summary_v1.csv']
CONDITION_FIELDS=['track_condition','track_rating','condition','going','surface_condition','condition_group']
RACE_NO_FIELDS=['race_no','race_number','raceNumber']; TRACK_FIELDS=['track','track_name','venue_name','normalised_track']; DATE_FIELDS=['race_date','meeting_date','date']
def text(v): return str(v if v is not None else '').strip()
def clean(v): return re.sub(r'[^A-Z0-9]','',text(v).upper())
def int_text(v):
    m=re.search(r'\d+',text(v)); return str(int(m.group(0))) if m else ''
def first(row,fields):
    lower={k.lower():k for k in row}
    for f in fields:
        k=lower.get(f.lower())
        if k and text(row.get(k)): return text(row.get(k))
    return ''
def read_rows(path):
    if not path.exists(): return []
    with path.open('r',encoding='utf-8-sig',newline='') as h: return list(csv.DictReader(h))
def race_no_from_key(v):
    m=re.search(r'R(\d+)',text(v),flags=re.I); return str(int(m.group(1))) if m else ''
def key_variants(date,track,race_no):
    base=(date,track,race_no); out=[base]
    if race_no: out.append((date,track,''))
    return out
def build_index():
    idx=defaultdict(list); files=[]
    for path in CANDIDATE_FILES:
        rows=read_rows(path); files.append(str(path.relative_to(ROOT)))
        for row in rows:
            d=first(row,DATE_FIELDS); tr=clean(first(row,TRACK_FIELDS)); rn=int_text(first(row,RACE_NO_FIELDS))
            if not d or not tr: continue
            cond={f:text(row.get(f)) for f in CONDITION_FIELDS if text(row.get(f))}
            entry={'file':str(path.relative_to(ROOT)),'condition_values':cond}
            idx[(d,tr,rn)].append(entry); idx[(d,tr,'')].append(entry)
    return idx,files
def main():
    DOCS.mkdir(parents=True,exist_ok=True); rejs=read_rows(REJECTIONS); idx,files=build_index(); audit=[]
    for rej in rejs:
        d=text(rej.get('race_date')); tr=clean(rej.get('track_name')); rn=race_no_from_key(rej.get('race_key')) or int_text(rej.get('race_no'))
        matches=[]
        for k in key_variants(d,tr,rn): matches.extend(idx.get(k,[]))
        # if branded track names differ, do one bounded same-date scan over indexed keys only
        if not matches:
            for (kd,kt,krn),vals in idx.items():
                if kd==d and (tr in kt or kt in tr) and (not rn or not krn or rn==krn): matches.extend(vals)
        source_matches=sorted({m['file'] for m in matches}); cond_matches=[m for m in matches if m['condition_values']]
        if cond_matches:
            status='AUTHORITATIVE_CONDITION_CANDIDATE_FOUND_REVIEW_REQUIRED'; finding=json.dumps(cond_matches[:5],sort_keys=True)
        elif source_matches:
            status='SOURCE_MATCH_WITHOUT_CONDITION'; finding='|'.join(source_matches[:10])
        else:
            status='NO_AUTHORITATIVE_CONDITION_SOURCE_FOUND'; finding=''
        audit.append({'race_time_delta_id':text(rej.get('race_time_delta_id')),'race_key':text(rej.get('race_key')),'race_date':d,'track_name':text(rej.get('track_name')),'race_no':rn,'distance':text(rej.get('official_distance_metres')),'original_rejection_reason':text(rej.get('rejection_reason')),'condition_audit_status':status,'matched_source_count':len(source_matches),'condition_match_count':len(cond_matches),'finding':finding})
    fields=['race_time_delta_id','race_key','race_date','track_name','race_no','distance','original_rejection_reason','condition_audit_status','matched_source_count','condition_match_count','finding']
    with OUT_CSV.open('w',encoding='utf-8',newline='') as h:
        w=csv.DictWriter(h,fieldnames=fields,lineterminator='\n'); w.writeheader(); w.writerows(audit)
    counts=Counter(r['condition_audit_status'] for r in audit); summary={'audit_name':'edgeiq_lengths_standard_condition_rejection_audit_v1','audit_method':'INDEXED_BY_DATE_TRACK_RACE_NO','audited_at_utc':datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z'),'rejection_rows':len(audit),'status_counts':dict(counts),'candidate_files':files,'decision':'RETAIN_EXPLICIT_REJECTIONS' if not any(r['condition_match_count'] for r in audit) else 'CONDITION_CANDIDATE_REVIEW_REQUIRED','no_inference_declaration':'YES'}
    OUT_SUMMARY.write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    OUT_MD.write_text('\n'.join(['# EDGEiQ Lengths v Standard Condition Rejection Audit V1','',f'Rejection rows audited: {len(audit)}',f'Decision: {summary["decision"]}','','No condition was inferred from race descriptions. Only explicit condition fields in candidate authoritative files were accepted.','','Status counts:',*[f'- {k}: {v}' for k,v in sorted(counts.items())],'']),encoding='utf-8')
    print('EDGEIQ_LENGTHS_STANDARD_CONDITION_REJECTION_AUDIT_V1_PASS'); print(f'rejection_rows={len(audit)}'); print(f'decision={summary["decision"]}'); print(f'output={OUT_CSV}')
if __name__=='__main__': main()
