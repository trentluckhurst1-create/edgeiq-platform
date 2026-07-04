import csv, re
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public/data'
BOARD=DATA/'edgeiq_live_runner_board_governed_v1.csv'; LEGACY=DATA/'edgeiq_live_runner_board_v1.csv'; FEED=DATA/'edgeiq_command_enrichment_feed_v2.csv'
OUT=DATA/'edgeiq_current_zero_evidence_race_v1.csv'; SUM=DATA/'edgeiq_current_zero_evidence_race_v1_summary.csv'; REPORT=DATA/'edgeiq_current_zero_evidence_race_v1_report.txt'
def read(path):
    with path.open('r',newline='',encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return r.fieldnames or [], list(r)
def yes(v): return str(v).strip().upper() in {'YES','TRUE','1','Y'}
def meaningful(v):
    s=str(v or '').strip().upper(); return bool(s) and s not in {'NO','NONE','N/A','NA','NO_SOURCE_MATCH','NO_CONNECTION','NO_EVIDENCE','FALSE','0','--'}
def rno(s):
    m=re.search(r'\d+',str(s or '')); return m.group(0) if m else str(s or '').strip()
def rk(r): return (str(r.get('race_date') or r.get('meeting_date') or '').strip(),str(r.get('track','')).strip(),rno(r.get('race_no')))
def num(v):
    try:
        s=str(v).replace('$','').replace(',','').strip(); return float(s) if s!='' else None
    except Exception: return None
def grouped(rows):
    g={}
    for r in rows: g.setdefault(rk(r),[]).append(r)
    return g
gcols,grows=read(BOARD); lcols,lrows=read(LEGACY); fcols,frows=read(FEED)
fg=grouped(frows); gg=grouped(grows); lg=grouped(lrows)
out=[]
allkeys=sorted(set(gg)|set(lg)|set(fg))
for key in allkeys:
    feed=fg.get(key,[]); gov=gg.get(key,[]); leg=lg.get(key,[])
    field=len(feed) or len(gov) or len(leg)
    market=sum(1 for r in feed if yes(r.get('edgeiq_market_evidence_available_v2')) or meaningful(r.get('edgeiq_market_signal_summary_v2')))
    conn=sum(1 for r in feed if yes(r.get('edgeiq_connection_evidence_available_v2')) or meaningful(r.get('edgeiq_connection_angle_summary_v2')))
    hidden=sum(1 for r in feed if yes(r.get('edgeiq_hidden_gem_evidence_available_v2')) or meaningful(r.get('edgeiq_hidden_gem_summary_v2')))
    price=sum(1 for r in gov if num(r.get('edgeiq_v7_2g2_active_display_fair_price_shadow')) or num(r.get('fair_price')) or num(r.get('ui_fair_price')))
    if not gov and leg: price_legacy=sum(1 for r in leg if num(r.get('fair_price')) or num(r.get('ui_fair_price')) or num(r.get('live_price')))
    else: price_legacy=0
    def verdict(count, source_rows):
        if count>0: return 'NOT_ZERO'
        if not source_rows: return 'FEED_FAILURE'
        return 'TRUE_ZERO'
    market_v=verdict(market,feed); conn_v=verdict(conn,feed); hidden_v=verdict(hidden,feed); price_v='NOT_ZERO' if price>0 else ('FEED_FAILURE' if not gov else 'TRUE_ZERO')
    overall='FEED_FAILURE' if any(v=='FEED_FAILURE' for v in [market_v,conn_v,hidden_v,price_v]) else ('TRUE_ZERO' if all(v=='TRUE_ZERO' for v in [market_v,conn_v,hidden_v,price_v]) else 'PARTIAL_FAILURE' if any(v=='TRUE_ZERO' for v in [market_v,conn_v,hidden_v,price_v]) else 'NOT_ZERO')
    out.append({'race_date':key[0],'track':key[1],'race_no':key[2],'field_size':field,'governed_rows':len(gov),'legacy_rows':len(leg),'feed_rows':len(feed),'market_count':market,'connection_count':conn,'hidden_gem_count':hidden,'edgeiq_price_count':price,'legacy_price_count':price_legacy,'market_status':market_v,'connection_status':conn_v,'hidden_gem_status':hidden_v,'edgeiq_price_status':price_v,'overall_status':overall})
# focus field 19 if any, else zero-symptom races
focus=next((r for r in out if int(r['field_size'])==19),None) or next((r for r in out if r['market_count']==0 and r['connection_count']==0 and r['edgeiq_price_count']==0),None) or out[0]
status=focus['overall_status'] if focus else 'FEED_FAILURE'
summary=[{'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'focus_race':'|'.join([focus['race_date'],focus['track'],focus['race_no']]),'field_size':focus['field_size'],'market':f"{focus['market_count']}:{focus['market_status']}",'connections':f"{focus['connection_count']}:{focus['connection_status']}",'hidden_gem':f"{focus['hidden_gem_count']}:{focus['hidden_gem_status']}",'edgeiq_price':f"{focus['edgeiq_price_count']}:{focus['edgeiq_price_status']}",'field_19_races':sum(1 for r in out if int(r['field_size'])==19)}]
for p,data in [(OUT,out),(SUM,summary)]:
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0].keys())); w.writeheader(); w.writerows(data)
report=['EDGEiQ Current Zero Evidence Race Audit V1','='*48,f"Status: {status}",f"Focus race: {summary[0]['focus_race']}",f"Field size: {summary[0]['field_size']}",f"Market: {summary[0]['market']}",f"Connections: {summary[0]['connections']}",f"Hidden Gem: {summary[0]['hidden_gem']}",f"EDGEiQ Price: {summary[0]['edgeiq_price']}",f"Field-19 races found: {summary[0]['field_19_races']}",'','Races with any zero/feed status:']
for r in out:
    if int(r['field_size'])==19 or r['market_status']!='NOT_ZERO' or r['connection_status']!='NOT_ZERO' or r['edgeiq_price_status']!='NOT_ZERO':
        report.append(f"- {r['race_date']} {r['track']} R{r['race_no']} field={r['field_size']} gov/feed/legacy={r['governed_rows']}/{r['feed_rows']}/{r['legacy_rows']} market={r['market_count']}:{r['market_status']} conn={r['connection_count']}:{r['connection_status']} hidden={r['hidden_gem_count']}:{r['hidden_gem_status']} price={r['edgeiq_price_count']}:{r['edgeiq_price_status']}")
REPORT.write_text('\n'.join(report)+'\n',encoding='utf-8')
print(status); print(summary[0])
