import csv,re
from pathlib import Path
from datetime import datetime
D=Path('public/data'); BASE=D/'edgeiq_live_runner_board_governed_v7_2g2_FRESH_CURRENT_CANDIDATE.csv'; OUT=D/'edgeiq_current_intelligence_evidence_fix_candidate_FRESH_v1.csv'; SUM=D/'edgeiq_current_evidence_fix_candidate_fresh_v1_summary.csv'; AUD=D/'edgeiq_current_evidence_fix_candidate_fresh_v1_audit.csv'; REP=D/'edgeiq_current_evidence_fix_candidate_fresh_v1_report.txt'
SOURCES=['edgeiq_current_intelligence_evidence_fix_candidate_v1.csv','edgeiq_connection_intelligence_v1.csv','edgeiq_explainability_terminal_feed_v1_2.csv','edgeiq_live_terminal_feed_v1.csv','edgeiq_tab_market_v1.csv','edgeiq_pre_result_market_history_warehouse_v1.csv','edgeiq_command_enrichment_feed_v2.csv']
def read(p):
 if not p.exists(): return [], []
 with p.open('r',newline='',encoding='utf-8-sig') as f: r=csv.DictReader(f); return r.fieldnames or [], list(r)
def write(p,rows,fields=None):
 if fields is None: fields=list(rows[0].keys())
 with p.open('w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',lineterminator='\n'); w.writeheader(); w.writerows(rows)
def norm(s): return re.sub(r'[^a-z0-9]+','',str(s or '').lower())
def rn(v):
 m=re.search(r'\d+',str(v or '')); return m.group(0) if m else str(v or '').strip()
def first(r,keys):
 for k in keys:
  if k in r and str(r.get(k,'')).strip(): return str(r.get(k)).strip()
 return ''
def key(r): return (first(r,['race_date','meeting_date','current_race_date','date']),first(r,['track']).upper(),rn(first(r,['race_no','race_number','race'])),norm(first(r,['horse','horse_name','runner_name','horse_key'])))
def meaningful(v):
 s=str(v or '').strip(); return bool(s) and s.upper() not in {'NO','NONE','N/A','NA','NO_SOURCE_MATCH','NO_CONNECTION','NO_EVIDENCE','FALSE','0','--'}
def yes(v): return str(v).strip().upper() in {'YES','TRUE','1','Y'}
def num(v):
 try:
  s=str(v).replace('$','').replace(',','').strip(); return float(s) if s!='' else None
 except Exception: return None
cols,base=read(BASE); source_indexes=[]
for name in SOURCES:
 sc,rs=read(D/name); idx={}
 for r in rs: idx.setdefault(key(r),[]).append(r)
 source_indexes.append((name,sc,idx))
out=[]; audit=[]
for r in base:
 k=key(r); conn=False; market=False; hidden=False; conn_sum=''; market_sum=''; hidden_sum=''; src=[]
 # market from current price context first
 fair=num(r.get('edgeiq_v7_2g2_active_display_fair_price_shadow')) or num(r.get('fair_price')) or num(r.get('ui_fair_price')); livep=num(r.get('live_price'))
 if fair or livep:
  market=True; market_sum='Market price context loaded.'; src.append('CURRENT_LIVE_PRICE_CONTEXT')
 for name,sc,idx in source_indexes:
  for row in idx.get(k,[])[:1]:
   cs=first(row,['edgeiq_connection_angle_summary','connection_narrative','connection_summary_for_decision_engine','connection_angle_1'])
   ms=first(row,['edgeiq_market_signal_summary','market_summary','market_expectation_label','edgeiq_market_signal_summary_v2'])
   hs=first(row,['edgeiq_hidden_gem_summary','hidden_gem_summary','performance_intelligence_narrative','edgeiq_hidden_gem_summary_v2'])
   if (yes(row.get('edgeiq_connection_evidence_available')) or yes(row.get('edgeiq_connection_evidence_available_v2')) or meaningful(cs)) and not conn:
    conn=True; conn_sum=cs or 'Connection evidence loaded.'; src.append('CONNECTION:'+name)
   if (yes(row.get('edgeiq_market_evidence_available')) or yes(row.get('edgeiq_market_evidence_available_v2')) or meaningful(ms)) and not market:
    market=True; market_sum=ms or 'Market evidence loaded.'; src.append('MARKET:'+name)
   if (yes(row.get('edgeiq_hidden_gem_evidence_available')) or yes(row.get('edgeiq_hidden_gem_evidence_available_v2')) or meaningful(hs)) and not hidden:
    hidden=True; hidden_sum=hs or 'Hidden gem evidence loaded.'; src.append('HIDDEN:'+name)
 outrow={'race_date':first(r,['race_date']),'track':first(r,['track']),'race_no':first(r,['race_no']),'horse':first(r,['horse']),'edgeiq_connection_evidence_available':'YES' if conn else 'NO','edgeiq_connection_angle_summary':conn_sum,'edgeiq_market_evidence_available':'YES' if market else 'NO','edgeiq_market_signal_summary':market_sum,'edgeiq_hidden_gem_evidence_available':'YES' if hidden else 'NO','edgeiq_hidden_gem_summary':hidden_sum,'edgeiq_evidence_fix_source':'|'.join(src) if src else 'NO_SOURCE_MATCH','edgeiq_evidence_fix_status':'EVIDENCE_AVAILABLE' if src else 'NO_SOURCE_MATCH'}
 out.append(outrow); audit.append({**outrow})
write(OUT,out); write(AUD,audit)
races={(r['race_date'],r['track'],r['race_no']) for r in out}; caul=[r for r in out if r['race_date']=='2026-06-27' and r['track'].upper()=='CAULFIELD' and r['race_no']=='7']
s=[{'status':'FRESH_EVIDENCE_FIX_CANDIDATE_BUILT','generated_at':datetime.now().isoformat(timespec='seconds'),'rows':len(out),'races':len(races),'market_available':sum(1 for r in out if r['edgeiq_market_evidence_available']=='YES'),'connections_available':sum(1 for r in out if r['edgeiq_connection_evidence_available']=='YES'),'hidden_gem_available':sum(1 for r in out if r['edgeiq_hidden_gem_evidence_available']=='YES'),'CAULFIELD_R7_market_available':sum(1 for r in caul if r['edgeiq_market_evidence_available']=='YES'),'CAULFIELD_R7_connections_available':sum(1 for r in caul if r['edgeiq_connection_evidence_available']=='YES'),'CAULFIELD_R7_hidden_gem_available':sum(1 for r in caul if r['edgeiq_hidden_gem_evidence_available']=='YES')}]
write(SUM,s)
REP.write_text('\n'.join(['EDGEiQ Fresh Evidence Fix Candidate V1', '='*42, f"Status: {s[0]['status']}", f"Rows/races: {len(out)} / {len(races)}", f"Market/connections/hidden: {s[0]['market_available']} / {s[0]['connections_available']} / {s[0]['hidden_gem_available']}", f"CAULFIELD R7 market/connections/hidden: {s[0]['CAULFIELD_R7_market_available']} / {s[0]['CAULFIELD_R7_connections_available']} / {s[0]['CAULFIELD_R7_hidden_gem_available']}"])+'\n',encoding='utf-8')
print(s[0])
