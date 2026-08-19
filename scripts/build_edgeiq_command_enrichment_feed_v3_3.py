import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
GOV=DATA/'edgeiq_live_runner_board_governed_v1.csv'
BASE=DATA/'edgeiq_command_enrichment_feed_v3.csv'
CAMP=DATA/'edgeiq_campaign_feed_v1.csv'
OUT=DATA/'edgeiq_command_enrichment_feed_v3_3.csv'
SUMMARY=DATA/'edgeiq_command_enrichment_feed_v3_3_summary.csv'
AUDIT=DATA/'edgeiq_command_enrichment_feed_v3_3_audit.csv'
REPORT=DATA/'edgeiq_command_enrichment_feed_v3_3_report.txt'

def read_csv(p):
    if not p.exists(): return [],[]
    with p.open('r',newline='',encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return list(r), list(r.fieldnames or [])
def write_csv(p,rows,fields):
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def clean(v): return ' '.join(str(v or '').strip().upper().replace('\u00a0',' ').split())
def clean_horse(v): return ''.join(ch for ch in clean(v) if ch.isalnum())
def race_no(v):
    s=clean(v).replace('RACE ','').replace('R','')
    return s.lstrip('0') or s
def key(r): return (clean(r.get('race_date') or r.get('current_race_date')),clean(r.get('track')),race_no(r.get('race_no')),clean_horse(r.get('horse') or r.get('horse_key')))
def rkey(r): return key(r)[:3]
def yes(v): return clean(v) in {'YES','TRUE','1','Y','ON'}

gov,_=read_csv(GOV); base,bf=read_csv(BASE); camp,cf=read_csv(CAMP); camp_by={key(r):r for r in camp}
out=[]; audit=[]; matched=0
fields=list(bf)
new=['edgeiq_campaign_available_v3_3','edgeiq_campaign_truth_status_v3_3','edgeiq_campaign_score_v3_3','edgeiq_campaign_narrative_v3_3','edgeiq_campaign_source_v3_3','edgeiq_campaign_match_method_v3_3','race_campaign_available_count_v3_3','race_campaign_true_zero_count_v3_3','race_campaign_source_missing_count_v3_3','race_campaign_fallback_match_count_v3_3']
for f in new:
    if f not in fields: fields.append(f)
for r in base:
    nr=dict(r); c=camp_by.get(key(r))
    if c:
        matched+=1
        nr['edgeiq_campaign_available_v3_3']=c.get('edgeiq_campaign_available_v1','')
        nr['edgeiq_campaign_truth_status_v3_3']=c.get('edgeiq_campaign_truth_status_v1','')
        nr['edgeiq_campaign_score_v3_3']=c.get('edgeiq_campaign_score_v1','')
        nr['edgeiq_campaign_narrative_v3_3']=c.get('edgeiq_campaign_narrative_v1','')
        nr['edgeiq_campaign_source_v3_3']=c.get('edgeiq_campaign_source_v1','')
        nr['edgeiq_campaign_match_method_v3_3']=c.get('edgeiq_campaign_match_method_v1','')
        # Fill existing score slot when campaign has a valid score and existing was blank.
        if not str(nr.get('edgeiq_score_campaign_v3','')).strip() and str(c.get('edgeiq_campaign_score_v1','')).strip():
            nr['edgeiq_score_campaign_v3']=c.get('edgeiq_campaign_score_v1','')
            nr['edgeiq_score_source_v3']=(nr.get('edgeiq_score_source_v3','') or '').replace('CAMPAIGN:MISSING','CAMPAIGN:CAMPAIGN_FEED_V1')
    else:
        nr['edgeiq_campaign_available_v3_3']='NO'; nr['edgeiq_campaign_truth_status_v3_3']='CAMPAIGN_SOURCE_MISSING_OR_JOIN_FAILED'; nr['edgeiq_campaign_score_v3_3']=''; nr['edgeiq_campaign_narrative_v3_3']=''; nr['edgeiq_campaign_source_v3_3']='NO_MATCH_IN_CAMPAIGN_FEED_V1'; nr['edgeiq_campaign_match_method_v3_3']='NO_MATCH'
    out.append(nr)
    audit.append({'race_date':r.get('race_date',''),'track':r.get('track',''),'race_no':r.get('race_no',''),'horse':r.get('horse',''),'campaign_matched':'YES' if c else 'NO','campaign_available':nr['edgeiq_campaign_available_v3_3'],'campaign_truth_status':nr['edgeiq_campaign_truth_status_v3_3'],'match_method':nr['edgeiq_campaign_match_method_v3_3']})
byrace=defaultdict(list)
for r in out: byrace[rkey(r)].append(r)
for rk,members in byrace.items():
    counts={'race_campaign_available_count_v3_3':str(sum(1 for x in members if x['edgeiq_campaign_available_v3_3']=='YES')),'race_campaign_true_zero_count_v3_3':str(sum(1 for x in members if x['edgeiq_campaign_truth_status_v3_3']=='TRUE_ZERO_NO_CAMPAIGN_HISTORY')),'race_campaign_source_missing_count_v3_3':str(sum(1 for x in members if x['edgeiq_campaign_truth_status_v3_3'] in {'CAMPAIGN_SOURCE_MISSING','CAMPAIGN_SOURCE_MISSING_OR_JOIN_FAILED'})),'race_campaign_fallback_match_count_v3_3':str(sum(1 for x in members if x['edgeiq_campaign_match_method_v3_3']=='HORSE_KEY_FALLBACK'))}
    for x in members: x.update(counts)
rows=len(out); races=len(set(rkey(r) for r in out)); dup=rows-len(set(key(r) for r in out)); v7=sum(1 for r in gov if yes(r.get('edgeiq_v7_2g2_feature_flag')))
status='COMMAND_ENRICHMENT_FEED_V3_3_BUILT' if rows==383 and races==25 and matched==383 and dup==0 and v7==383 else 'COMMAND_ENRICHMENT_FEED_V3_3_BLOCKED'
summary={'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'rows':rows,'races':races,'campaign_matched_rows':matched,'campaign_available_rows':sum(1 for r in out if r['edgeiq_campaign_available_v3_3']=='YES'),'campaign_true_zero_rows':sum(1 for r in out if r['edgeiq_campaign_truth_status_v3_3']=='TRUE_ZERO_NO_CAMPAIGN_HISTORY'),'campaign_source_missing_rows':sum(1 for r in out if r['edgeiq_campaign_truth_status_v3_3'] in {'CAMPAIGN_SOURCE_MISSING','CAMPAIGN_SOURCE_MISSING_OR_JOIN_FAILED'}),'campaign_fallback_match_rows':sum(1 for r in out if r['edgeiq_campaign_match_method_v3_3']=='HORSE_KEY_FALLBACK'),'duplicate_runner_keys':dup,'v7_2g2_on_rows':v7,'pricing_math_changed':'NO','v6_1_changed':'NO','v7_2g2_changed':'NO'}
write_csv(OUT,out,fields); write_csv(SUMMARY,[summary],list(summary.keys())); write_csv(AUDIT,audit,list(audit[0].keys()))
REPORT.write_text('\n'.join(['EDGEiQ Command Enrichment Feed V3.3','='*44,f'Status: {status}',f'Rows/races: {rows}/{races}',f'Campaign matched/available/true-zero/source-missing/fallback: {matched}/{summary["campaign_available_rows"]}/{summary["campaign_true_zero_rows"]}/{summary["campaign_source_missing_rows"]}/{summary["campaign_fallback_match_rows"]}',f'Duplicates: {dup}',f'V7.2G2 ON: {v7}/383','Pricing maths changed: NO','V6.1 changed: NO','V7.2G2 changed: NO'])+'\n',encoding='utf-8')
print(status)
