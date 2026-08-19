import csv,math,re
from pathlib import Path
from datetime import datetime
D=Path('public/data'); LIVE=D/'edgeiq_live_runner_board_v1.csv'; OUT=D/'edgeiq_live_runner_board_governed_v7_2g2_FRESH_CURRENT_CANDIDATE.csv'; AUD=D/'edgeiq_governed_v7_2g2_fresh_current_candidate_v1.csv'; SUM=D/'edgeiq_governed_v7_2g2_fresh_current_candidate_v1_summary.csv'; REP=D/'edgeiq_governed_v7_2g2_fresh_current_candidate_v1_report.txt'
def read(p):
 with p.open('r',newline='',encoding='utf-8-sig') as f: r=csv.DictReader(f); return r.fieldnames or [], list(r)
def write(p,rows,fields=None):
 if fields is None: fields=list(rows[0].keys())
 with p.open('w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',lineterminator='\n'); w.writeheader(); w.writerows(rows)
def num(r,keys):
 for k in keys:
  try:
   s=str(r.get(k,'')).replace('$','').replace('%','').replace(',','').strip()
   if s!='': return float(s)
  except Exception: pass
 return None
def rn(v):
 m=re.search(r'\d+',str(v or '')); return m.group(0) if m else str(v or '').strip()
def rk(r): return (str(r.get('race_date') or '').strip(),str(r.get('track','')).strip().upper(),rn(r.get('race_no')))
cols,rows=read(LIVE); fields=list(cols)
add=['edgeiq_v7_2g2_feature_flag','edgeiq_v7_2g2_live_wired_flag','edgeiq_v7_2g2_production_changed','edgeiq_v7_2g2_probability','edgeiq_v7_2g2_guarded_display_fair_price','edgeiq_v7_2g2_strategy','edgeiq_v7_2g2_guardrail_reason','edgeiq_v7_2g2_active_display_fair_price_shadow','edgeiq_v7_2g2_active_price_source_shadow','edgeiq_v7_2g2_on_preview_display_fair_price','edgeiq_active_display_fair_price_shadow','edgeiq_active_price_source_shadow']
for c in add:
 if c not in fields: fields.append(c)
out=[]; audit=[]
for r in rows:
 rr=dict(r); prob=num(rr,['win_pct','V6_1_RESEARCH_probability','probability_normalised_v1']); fair=num(rr,['ui_fair_price','fair_price','rated_price','V6_1_RESEARCH_fair_price'])
 if prob is not None and prob>1: p=prob/100
 else: p=prob
 if fair is None and p and p>0: fair=1/p
 fallback = fair is None
 rr['edgeiq_v7_2g2_feature_flag']='ON'; rr['edgeiq_v7_2g2_live_wired_flag']='YES_CONTROLLED_ON'; rr['edgeiq_v7_2g2_production_changed']='NO'
 rr['edgeiq_v7_2g2_probability']='' if p is None else round(p*100,6)
 rr['edgeiq_v7_2g2_guarded_display_fair_price']='' if fair is None else round(fair,4)
 rr['edgeiq_v7_2g2_strategy']='FRESH_CURRENT_PRODUCTION_DISPLAY_PRESERVED'
 rr['edgeiq_v7_2g2_guardrail_reason']='FRESH_REBUILD_PRODUCTION_FALLBACK_MISSING_INPUT' if fallback else 'FRESH_REBUILD_CURRENT_LIVE_INPUT'
 rr['edgeiq_v7_2g2_active_display_fair_price_shadow']='' if fair is None else round(fair,4)
 rr['edgeiq_v7_2g2_active_price_source_shadow']='V7_2G2_FRESH_CURRENT_CONTROLLED_ON'
 rr['edgeiq_v7_2g2_on_preview_display_fair_price']='' if fair is None else round(fair,4)
 rr['edgeiq_active_display_fair_price_shadow']='' if fair is None else round(fair,4)
 rr['edgeiq_active_price_source_shadow']='V7_2G2_FRESH_CURRENT_CONTROLLED_ON'
 out.append(rr); audit.append({'race_date':rr.get('race_date',''),'track':rr.get('track',''),'race_no':rr.get('race_no',''),'horse':rr.get('horse',''),'active_display':rr['edgeiq_v7_2g2_active_display_fair_price_shadow'],'guardrail_reason':rr['edgeiq_v7_2g2_guardrail_reason']})
write(OUT,out,fields); write(AUD,audit)
races={rk(r) for r in out}; caul=sum(1 for r in out if rk(r)==('2026-06-27','CAULFIELD','7')); active=sum(1 for r in out if str(r.get('edgeiq_v7_2g2_active_display_fair_price_shadow','')).strip()); vals=[float(r['edgeiq_v7_2g2_active_display_fair_price_shadow']) for r in out if str(r.get('edgeiq_v7_2g2_active_display_fair_price_shadow','')).strip()]
fallbacks=sum(1 for r in out if r['edgeiq_v7_2g2_guardrail_reason']=='FRESH_REBUILD_PRODUCTION_FALLBACK_MISSING_INPUT')
status='FRESH_CURRENT_V7_2G2_CANDIDATE_BUILT_WITH_FALLBACKS' if fallbacks else 'FRESH_CURRENT_V7_2G2_CANDIDATE_BUILT'
s=[{'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'rows':len(out),'races':len(races),'caulfield_r7_rows':caul,'active_display_rows':active,'active_display_min':min(vals) if vals else '','active_display_max':max(vals) if vals else '','fallback_rows':fallbacks,'feature_flag_values':'ON','live_wired_values':'YES_CONTROLLED_ON','production_changed_values':'NO'}]
write(SUM,s)
REP.write_text('\n'.join(['EDGEiQ Governed V7.2G2 Fresh Current Candidate V1','='*60,f"Status: {status}",f"Rows/races: {len(out)} / {len(races)}",f"CAULFIELD R7 rows: {caul}",f"Active display rows: {active}",f"Active display min/max: {s[0]['active_display_min']} / {s[0]['active_display_max']}",f"Fallback rows: {fallbacks}"])+'\n',encoding='utf-8')
print(status, s[0])
