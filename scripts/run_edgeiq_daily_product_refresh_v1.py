from __future__ import annotations
import argparse,json,os,shutil,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
try:
 from zoneinfo import ZoneInfo
except Exception:
 ZoneInfo=None
ROOT=Path(__file__).resolve().parents[1]; PUBLIC=ROOT/'public'/'data'; DOCS=ROOT/'docs'/'operations-readiness'; DAILY=DOCS/'daily-refresh'; LKG=DOCS/'operations'/'last-known-good'; TZ=ZoneInfo('Australia/Melbourne') if ZoneInfo else None
# EDGEIQ_STAGE6M_CURRENT_RUNNER_CHAIN_WIRING_V1
CRITICAL=['edgeiq_three_day_window_v1.json', 'edgeiq_three_day_product_catalog_v1.json', 'edgeiq_vic_three_day_race_list_v1.csv', 'edgeiq_live_terminal_feed_v1.csv', 'edgeiq_vic_live_terminal_feed_v1.csv']; STAGES=['scripts/build_edgeiq_three_day_window_v1.py', 'scripts/build_edgeiq_vic_three_day_meeting_universe.py', 'scripts/build_edgeiq_vic_three_day_meeting_calendar_v1.py', 'scripts/build_edgeiq_racingcom_three_day_race_list_v1.py', 'scripts/build_edgeiq_three_day_product_catalog_v1.py', 'scripts/build_edgeiq_current_race_fields_from_product_catalog_v1.py', 'scripts/build_edgeiq_ladbrokes_active_market_refresh_v1.py', 'scripts/build_edgeiq_current_market_v1.py', 'scripts/build_edgeiq_form_guide_current_base_v1.py', 'scripts/build_edgeiq_current_early_speed_v1.py', 'scripts/build_edgeiq_current_late_speed_v1.py', 'scripts/build_edgeiq_current_suitability_v1.py', 'scripts/build_edgeiq_current_form_momentum_v1.py', 'scripts/build_edgeiq_current_race_shape_v2.py', 'scripts/build_edgeiq_current_map_v1.py', 'scripts/build_edgeiq_form_guide_enriched_v2.py', 'scripts/build_edgeiq_performance_recovery_current_lineage_v1.py', 'scripts/build_edgeiq_form_guide_enriched_v2.py', 'scripts/build_edgeiq_map_terminal_feed_v1.py', 'scripts/build_edgeiq_market_terminal_feed_v1.py', 'scripts/build_edgeiq_overview_terminal_feed_v1.py', 'scripts/build_edgeiq_insights_terminal_feed_v1.py', 'scripts/build_edgeiq_gear_terminal_feed_v1.py', 'scripts/build_edgeiq_meeting_results_terminal_feed_v1.py', 'scripts/run_edgeiq_current_runner_scoped_performance_chain_v1.py', 'scripts/build_edgeiq_on_track_weather_governed_v1_2.py', 'scripts/build_edgeiq_victorian_track_weather_v1.py', 'scripts/audit_edgeiq_victorian_track_weather_v1.py']
CRITICAL=['edgeiq_three_day_window_v1.json', 'edgeiq_three_day_product_catalog_v1.json', 'edgeiq_vic_three_day_race_list_v1.csv', 'edgeiq_live_terminal_feed_v1.csv', 'edgeiq_vic_live_terminal_feed_v1.csv']; STAGES=['scripts/build_edgeiq_three_day_window_v1.py', 'scripts/build_edgeiq_vic_three_day_meeting_universe.py', 'scripts/build_edgeiq_vic_three_day_meeting_calendar_v1.py', 'scripts/build_edgeiq_racingcom_three_day_race_list_v1.py', 'scripts/build_edgeiq_three_day_product_catalog_v1.py', 'scripts/build_edgeiq_current_race_fields_from_product_catalog_v1.py', 'scripts/build_edgeiq_ladbrokes_active_market_refresh_v1.py', 'scripts/build_edgeiq_current_market_v1.py', 'scripts/build_edgeiq_form_guide_current_base_v1.py', 'scripts/build_edgeiq_current_early_speed_v1.py', 'scripts/build_edgeiq_current_late_speed_v1.py', 'scripts/build_edgeiq_current_suitability_v1.py', 'scripts/build_edgeiq_current_form_momentum_v1.py', 'scripts/build_edgeiq_current_race_shape_v2.py', 'scripts/build_edgeiq_current_map_v1.py', 'scripts/build_edgeiq_form_guide_enriched_v2.py', 'scripts/build_edgeiq_performance_recovery_current_lineage_v1.py', 'scripts/build_edgeiq_form_guide_enriched_v2.py', 'scripts/build_edgeiq_map_terminal_feed_v1.py', 'scripts/build_edgeiq_market_terminal_feed_v1.py', 'scripts/build_edgeiq_overview_terminal_feed_v1.py', 'scripts/build_edgeiq_insights_terminal_feed_v1.py', 'scripts/build_edgeiq_gear_terminal_feed_v1.py', 'scripts/build_edgeiq_meeting_results_terminal_feed_v1.py', 'scripts/performance-intelligence/product-integration/build_edgeiq_performance_intelligence_product_feeds_v1.py', 'scripts/build_edgeiq_on_track_weather_governed_v1_2.py', 'scripts/build_edgeiq_victorian_track_weather_v1.py', 'scripts/audit_edgeiq_victorian_track_weather_v1.py']
def utc(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def today(v=None): return v or ((datetime.now(TZ).date() if TZ else datetime.now().date()).isoformat())
def count_csv(p):
 p=Path(p)
 return 0 if (not p.exists() or p.stat().st_size==0) else max(0,sum(1 for _ in p.open('r',encoding='utf-8',errors='ignore'))-1)
def write_json(p,o):
 p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2)+'\n',encoding='utf-8')
def snap():
 LKG.mkdir(parents=True,exist_ok=True); files=[]
 for n in CRITICAL:
  s=PUBLIC/n
  if s.exists() and s.stat().st_size>0:
   shutil.copy2(s,LKG/n); files.append({'file':n,'bytes':s.stat().st_size})
 m={'generated_utc':utc(),'files':files}; write_json(DOCS/'operations'/'edgeiq_last_known_good_manifest_v1.json',m); return m
def main():
 a=argparse.ArgumentParser(); a.add_argument('--date'); a.add_argument('--meeting'); a.add_argument('--race'); a.add_argument('--audit-only',action='store_true'); a.add_argument('--publish-only',action='store_true'); a.add_argument('--force-current-refresh',action='store_true'); a.add_argument('--no-market',action='store_true'); a.add_argument('--no-weather',action='store_true'); a.add_argument('--verbose',action='store_true'); ns=a.parse_args(); t=time.time(); od=today(ns.date); DAILY.mkdir(parents=True,exist_ok=True); lkg=snap(); stages=[]; log=DAILY/'edgeiq_daily_product_refresh_v1_run_log.txt'; env=os.environ.copy(); env['EDGEIQ_PIPELINE_DATE']=od
 with log.open('w',encoding='utf-8') as h:
  h.write(f'EDGEIQ DAILY PRODUCT REFRESH V1\nOPERATING_DATE={od}\nSTARTED_UTC={utc()}\n')
  if ns.audit_only: h.write('AUDIT_ONLY\n')
  else:
   for st in STAGES:
    if ns.no_market and 'market' in st.lower(): stages.append({'stage':st,'status':'SKIPPED','reason':'--no-market'}); continue
    if ns.no_weather and 'weather' in st.lower(): stages.append({'stage':st,'status':'SKIPPED','reason':'--no-weather'}); continue
    sp=ROOT/st
    if not sp.exists(): stages.append({'stage':st,'status':'SKIPPED','reason':'missing'}); continue
    h.write(f'\n--- {st} ---\n'); r=subprocess.run([sys.executable,str(sp)],cwd=str(ROOT),env=env,text=True,stdout=h,stderr=subprocess.STDOUT,timeout=900); stages.append({'stage':st,'status':'PASS' if r.returncode==0 else 'FAIL','returncode':r.returncode})
    if r.returncode!=0: break
 feeds=[]
 for n in CRITICAL:
  p=PUBLIC/n; rows=count_csv(p) if n.endswith('.csv') else (1 if p.exists() and p.stat().st_size>0 else 0); feeds.append({'file':n,'status':'PASS' if p.exists() and p.stat().st_size>0 and rows>0 else 'FAIL','rows_or_items':rows,'bytes':p.stat().st_size if p.exists() else 0})
 cat=json.loads((PUBLIC/'edgeiq_three_day_product_catalog_v1.json').read_text(encoding='utf-8')) if (PUBLIC/'edgeiq_three_day_product_catalog_v1.json').exists() else {}; meets=cat.get('meetings',[]) if isinstance(cat,dict) else []; races=[]; runners=0; total_current_scratchings=0; active_runners=0
 def _runner_scratched(x):
  off=x.get('official') if isinstance(x,dict) and isinstance(x.get('official'),dict) else {}
  src=x.get('source') if isinstance(x,dict) and isinstance(x.get('source'),dict) else {}
  vals=[off.get('scratched'),src.get('scratched'),src.get('is_scratched'),off.get('status'),src.get('status')]
  return any(str(v).strip().lower() in {'true','scr','scratched','lscr','late scratching'} for v in vals)
 for m in meets:
  for rc in (m.get('races',[]) if isinstance(m,dict) else []):
   races.append(rc); rr=rc.get('runners',[]) if isinstance(rc,dict) else []; runners+=len(rr); race_scratch=sum(1 for x in rr if _runner_scratched(x)); total_current_scratchings+=race_scratch; active_runners+=max(0,len(rr)-race_scratch)
 scratch=total_current_scratchings
 status='FAIL' if any(x.get('status')=='FAIL' for x in stages) or any(x.get('status')!='PASS' for x in feeds) else 'PASS'
 payload={'schema_version':'edgeiq_daily_product_refresh_v1','generated_utc':utc(),'operating_date':od,'timezone':'Australia/Melbourne','stages':stages,'feed_checks':feeds,'meetings_built':len(meets),'races_built':len(races),'runners_built':runners,'declared_runners':runners,'active_runners':active_runners,'total_current_scratchings':total_current_scratchings,'new_scratchings_this_run':None,'scratching_changes_this_run':None,'reinstated_runners_this_run':None,'scratchings_metric_deprecated':scratch,'track_status':'PARTIAL','weather_status':'PASS' if (PUBLIC/'edgeiq_on_track_weather_governed_v1_2.csv').exists() else 'PARTIAL','market_status':'PASS' if (PUBLIC/'edgeiq_market_terminal_feed_v1.csv').exists() else 'PARTIAL','results_status':'PASS' if (PUBLIC/'edgeiq_meeting_results_terminal_feed_v1.csv').exists() else 'PARTIAL','feeds_published':sum(1 for x in feeds if x['status']=='PASS'),'audit_status':status,'last_known_good_preserved':bool(lkg.get('files')),'elapsed_seconds':round(time.time()-t,2),'exit_code':0 if status=='PASS' else 1}

 wv_path=DOCS.parent/'weather-intelligence'/'live'/'edgeiq_victorian_track_weather_v1_audit.json'
 wv={}
 try:
  wv=json.loads(wv_path.read_text(encoding='utf-8')) if wv_path.exists() else {}
 except Exception:
  wv={}
 payload.update({'weather_meetings_required':wv.get('meetings_required',0),'weather_direct_source_meetings':wv.get('direct_source_meetings',0),'weather_bom_meetings':wv.get('bom_meetings',0),'weather_current':wv.get('current',0),'weather_regional_proxy':wv.get('regional_proxy',0),'weather_stale':wv.get('stale',0),'weather_unavailable':wv.get('unavailable',0),'weather_licence_blocked':wv.get('licence_blocked',0),'weather_audit_status':wv.get('status','NOT_RUN')})
 write_json(DAILY/'edgeiq_daily_product_refresh_v1_audit.json',payload); write_json(DAILY/'edgeiq_daily_product_refresh_v1_manifest.json',{'critical_feeds':feeds,'last_known_good':lkg}); (DAILY/'edgeiq_daily_product_refresh_v1_report.md').write_text(f'# EDGEIQ Daily Product Refresh V1\n\nStatus: {status}\n\nMeetings: {len(meets)}\nRaces: {len(races)}\nRunners: {runners}\n',encoding='utf-8')
 print('============================================================'); print('EDGEIQ DAILY PRODUCT REFRESH V1'); print('============================================================'); print(f'OPERATING_DATE: {od}'); print('TIMEZONE: Australia/Melbourne'); print(f'MEETINGS_BUILT: {len(meets)}'); print(f'RACES_BUILT: {len(races)}'); print(f'RUNNERS_BUILT: {runners}'); print(f'DECLARED_RUNNERS: {runners}'); print(f'ACTIVE_RUNNERS: {active_runners}'); print(f'TOTAL_CURRENT_SCRATCHINGS: {total_current_scratchings}'); print('NEW_SCRATCHINGS_THIS_RUN: NOT_CALCULATED'); print('SCRATCHING_CHANGES_THIS_RUN: NOT_CALCULATED'); print('REINSTATED_RUNNERS_THIS_RUN: NOT_CALCULATED'); print(f'TRACK_STATUS: {payload["track_status"]}'); print(f'WEATHER_STATUS: {payload["weather_status"]}'); print(f'WEATHER_MEETINGS_REQUIRED: {payload.get("weather_meetings_required",0)}'); print(f'WEATHER_DIRECT_SOURCE_MEETINGS: {payload.get("weather_direct_source_meetings",0)}'); print(f'WEATHER_BOM_MEETINGS: {payload.get("weather_bom_meetings",0)}'); print(f'WEATHER_CURRENT: {payload.get("weather_current",0)}'); print(f'WEATHER_REGIONAL_PROXY: {payload.get("weather_regional_proxy",0)}'); print(f'WEATHER_STALE: {payload.get("weather_stale",0)}'); print(f'WEATHER_UNAVAILABLE: {payload.get("weather_unavailable",0)}'); print(f'WEATHER_LICENCE_BLOCKED: {payload.get("weather_licence_blocked",0)}'); print(f'WEATHER_AUDIT_STATUS: {payload.get("weather_audit_status","NOT_RUN")}'); print(f'MARKET_STATUS: {payload["market_status"]}'); print(f'RESULTS_STATUS: {payload["results_status"]}'); print(f'FEEDS_PUBLISHED: {payload["feeds_published"]}'); print(f'AUDIT_STATUS: {status}'); print(f'LAST_KNOWN_GOOD_PRESERVED: {str(payload["last_known_good_preserved"]).upper()}'); print(f'ELAPSED_SECONDS: {payload["elapsed_seconds"]}'); print(f'EXIT_CODE: {payload["exit_code"]}'); print('============================================================'); return payload['exit_code']
if __name__=='__main__': raise SystemExit(main())
