import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
GOV=DATA/'edgeiq_live_runner_board_governed_v1.csv'
V3=DATA/'public_dummy_never.csv'
BASE=DATA/'checkpoints'
# Use the pre-V3.1 backup if available to avoid accumulating stale hidden classifications; otherwise current V3 is fine.
V3_SOURCE=DATA/'edgeiq_command_enrichment_feed_v3.csv'
HIDDEN=DATA/'edgeiq_current_hidden_gem_feed_v1_1.csv'
OUT=DATA/'edgeiq_command_enrichment_feed_v3_1.csv'
SUMMARY=DATA/'edgeiq_command_enrichment_feed_v3_1_summary.csv'
AUDIT=DATA/'edgeiq_command_enrichment_feed_v3_1_audit.csv'
REPORT=DATA/'edgeiq_command_enrichment_feed_v3_1_report.txt'

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
def populated(v): return str(v or '').strip() not in {'','-','--','N/A'}
def yes(v): return clean(v) in {'YES','TRUE','1','Y','ON'}
def first(row,cols):
    for c in cols:
        if populated(row.get(c,'')): return row.get(c,'')
    return ''

gov,gf=read_csv(GOV); v3,vf=read_csv(V3_SOURCE); hidden,hf=read_csv(HIDDEN)
gov_by={key(r):r for r in gov}; hidden_by={key(r):r for r in hidden}
# If current V3 already has V3.1 fields, keep all base fields but recalculate them.
out=[]
for r in v3:
    nr=dict(r); gr=gov_by.get(key(r),{}); hr=hidden_by.get(key(r),{})
    price=first(nr,['edgeiq_active_display_fair_price','edgeiq_v7_2g2_guarded_display_fair_price']) or first(gr,['edgeiq_active_display_fair_price_shadow','edgeiq_v7_2g2_guarded_display_fair_price','display_fair_price','ui_fair_price','fair_price'])
    if price: price_truth='PRICE_AVAILABLE'
    elif clean(gr.get('runner_status'))=='SCRATCHED' or clean(gr.get('scratch_status'))=='SCRATCHED' or clean(gr.get('is_scratched'))=='TRUE': price_truth='SCRATCHED_PRICE_SUPPRESSED'
    else: price_truth='EDGEIQ_PRICE_SOURCE_MISSING'
    nr['edgeiq_price_truth_status_v3_1']=price_truth
    nr['edgeiq_price_source_v3_1']='GOVERNED_V7_2G2_OR_PRODUCTION_PRICE_FIELD' if price_truth=='PRICE_AVAILABLE' else ('SCRATCHED_STATUS' if price_truth=='SCRATCHED_PRICE_SUPPRESSED' else 'NO_APPROVED_EDGEIQ_PRICE_FIELD_PRESENT')
    if hr:
        actionable=yes(hr.get('actionable_watch_flag')) or clean(hr.get('customer_display_band')) in {'HIGH','MEDIUM'}
        historical=yes(hr.get('historical_watch_flag')) or clean(hr.get('hidden_gem_recency_band')) in {'HISTORICAL','STALE','RECENT','CURRENT'}
        nr['edgeiq_hidden_gem_evidence_available_v3']='YES' if actionable else 'NO'
        nr['edgeiq_hidden_gem_summary_v3']=hr.get('hidden_gem_narrative','')
        if actionable: hidden_truth='ACTIONABLE_HIDDEN_GEM_SIGNAL'
        elif historical or populated(hr.get('hidden_gem_narrative')): hidden_truth='TRUE_ZERO_NO_ACTIONABLE_HIDDEN_GEM_SIGNAL'
        else: hidden_truth='TRUE_ZERO_NO_HIDDEN_GEM_SIGNAL'
        nr['edgeiq_hidden_gem_truth_status_v3']=hidden_truth
        nr['edgeiq_hidden_gem_source_v3_1']='edgeiq_current_hidden_gem_feed_v1_1.csv'
        nr['edgeiq_hidden_gem_customer_band_v3_1']=hr.get('customer_display_band','')
        nr['edgeiq_hidden_gem_score_v3_1']=hr.get('recency_adjusted_hidden_gem_score') or hr.get('last_hidden_gem_score','')
    else:
        nr['edgeiq_hidden_gem_evidence_available_v3']='NO'
        nr['edgeiq_hidden_gem_summary_v3']=''
        nr['edgeiq_hidden_gem_truth_status_v3']='HIDDEN_GEM_SOURCE_MISSING_OR_JOIN_FAILED'
        nr['edgeiq_hidden_gem_source_v3_1']='NO_MATCH_IN_EDGEIQ_CURRENT_HIDDEN_GEM_FEED_V1_1'
        nr['edgeiq_hidden_gem_customer_band_v3_1']=''
        nr['edgeiq_hidden_gem_score_v3_1']=''
    core_ok=yes(nr.get('edgeiq_market_evidence_available_v3')) and yes(nr.get('edgeiq_connection_evidence_available_v3')) and populated(nr.get('edgeiq_score_overall_v3'))
    if core_ok and price_truth=='PRICE_AVAILABLE': readiness='COMMAND_CARD_READY'
    elif core_ok and price_truth=='EDGEIQ_PRICE_SOURCE_MISSING': readiness='COMMAND_CARD_READY_PRICE_SOURCE_MISSING'
    elif core_ok and price_truth=='SCRATCHED_PRICE_SUPPRESSED': readiness='COMMAND_CARD_READY_SCRATCHED_PRICE_SUPPRESSED'
    else: readiness='COMMAND_CARD_PARTIAL'
    nr['command_card_readiness_v3_1']=readiness
    out.append(nr)
byrace=defaultdict(list)
for r in out: byrace[rkey(r)].append(r)
for rk, rows in byrace.items():
    counts={'race_edgeiq_price_available_count_v3_1':str(sum(1 for x in rows if x['edgeiq_price_truth_status_v3_1']=='PRICE_AVAILABLE')),'race_edgeiq_price_source_missing_count_v3_1':str(sum(1 for x in rows if x['edgeiq_price_truth_status_v3_1']=='EDGEIQ_PRICE_SOURCE_MISSING')),'race_scratched_price_suppressed_count_v3_1':str(sum(1 for x in rows if x['edgeiq_price_truth_status_v3_1']=='SCRATCHED_PRICE_SUPPRESSED')),'race_command_card_ready_count_v3_1':str(sum(1 for x in rows if x['command_card_readiness_v3_1'].startswith('COMMAND_CARD_READY'))),'race_hidden_gem_available_count_v3':str(sum(1 for x in rows if x['edgeiq_hidden_gem_evidence_available_v3']=='YES')),'race_hidden_gem_source_matched_count_v3_1':str(sum(1 for x in rows if x['edgeiq_hidden_gem_truth_status_v3']!='HIDDEN_GEM_SOURCE_MISSING_OR_JOIN_FAILED'))}
    for x in rows: x.update(counts)
fields=list(vf)
for f in ['edgeiq_price_truth_status_v3_1','edgeiq_price_source_v3_1','command_card_readiness_v3_1','race_edgeiq_price_available_count_v3_1','race_edgeiq_price_source_missing_count_v3_1','race_scratched_price_suppressed_count_v3_1','race_command_card_ready_count_v3_1','edgeiq_hidden_gem_source_v3_1','edgeiq_hidden_gem_customer_band_v3_1','edgeiq_hidden_gem_score_v3_1','race_hidden_gem_source_matched_count_v3_1']:
    if f not in fields: fields.append(f)
races=set(rkey(r) for r in out); caul=sum(1 for r in out if clean(r.get('track'))=='CAULFIELD' and race_no(r.get('race_no'))=='7')
status='COMMAND_ENRICHMENT_FEED_V3_1_BUILT' if len(out)==383 and len(races)==25 and caul==19 else 'COMMAND_ENRICHMENT_FEED_V3_1_BLOCKED'
audit=[]
for rk, rows in sorted(byrace.items()):
    audit.append({'race_date':rk[0],'track':rk[1],'race_no':rk[2],'field_size':len(rows),'price_available':sum(1 for x in rows if x['edgeiq_price_truth_status_v3_1']=='PRICE_AVAILABLE'),'price_source_missing':sum(1 for x in rows if x['edgeiq_price_truth_status_v3_1']=='EDGEIQ_PRICE_SOURCE_MISSING'),'scratched_price_suppressed':sum(1 for x in rows if x['edgeiq_price_truth_status_v3_1']=='SCRATCHED_PRICE_SUPPRESSED'),'hidden_gem_actionable':sum(1 for x in rows if x['edgeiq_hidden_gem_evidence_available_v3']=='YES'),'hidden_gem_source_matched':sum(1 for x in rows if x['edgeiq_hidden_gem_truth_status_v3']!='HIDDEN_GEM_SOURCE_MISSING_OR_JOIN_FAILED'),'command_card_ready':sum(1 for x in rows if x['command_card_readiness_v3_1'].startswith('COMMAND_CARD_READY'))})
summary={'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'rows':len(out),'races':len(races),'caulfield_r7_rows':caul,'price_available_rows':sum(1 for r in out if r['edgeiq_price_truth_status_v3_1']=='PRICE_AVAILABLE'),'price_source_missing_rows':sum(1 for r in out if r['edgeiq_price_truth_status_v3_1']=='EDGEIQ_PRICE_SOURCE_MISSING'),'scratched_price_suppressed_rows':sum(1 for r in out if r['edgeiq_price_truth_status_v3_1']=='SCRATCHED_PRICE_SUPPRESSED'),'hidden_gem_actionable_rows':sum(1 for r in out if r['edgeiq_hidden_gem_evidence_available_v3']=='YES'),'hidden_gem_source_matched_rows':sum(1 for r in out if r['edgeiq_hidden_gem_truth_status_v3']!='HIDDEN_GEM_SOURCE_MISSING_OR_JOIN_FAILED'),'hidden_gem_source_missing_rows':sum(1 for r in out if r['edgeiq_hidden_gem_truth_status_v3']=='HIDDEN_GEM_SOURCE_MISSING_OR_JOIN_FAILED'),'command_card_ready_rows':sum(1 for r in out if r['command_card_readiness_v3_1'].startswith('COMMAND_CARD_READY')),'pricing_math_changed':'NO','v7_2g2_math_changed':'NO'}
write_csv(OUT,out,fields); write_csv(SUMMARY,[summary],list(summary.keys())); write_csv(AUDIT,audit,list(audit[0].keys()))
REPORT.write_text('\n'.join(['EDGEiQ Command Enrichment Feed V3.1','='*42,f'Status: {status}',f'Rows/races: {len(out)}/{len(races)}',f'CAULFIELD R7 rows: {caul}',f'Price available/source missing/scratched suppressed: {summary["price_available_rows"]}/{summary["price_source_missing_rows"]}/{summary["scratched_price_suppressed_rows"]}',f'Hidden gem actionable/source matched/source missing: {summary["hidden_gem_actionable_rows"]}/{summary["hidden_gem_source_matched_rows"]}/{summary["hidden_gem_source_missing_rows"]}',f'Command card ready rows: {summary["command_card_ready_rows"]}','Pricing maths changed: NO','V7.2G2 maths changed: NO'])+'\n',encoding='utf-8')
print(status)
