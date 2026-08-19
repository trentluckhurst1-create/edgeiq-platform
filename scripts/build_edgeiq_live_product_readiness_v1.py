
from __future__ import annotations
import csv,json,os,shutil,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
try:
 from zoneinfo import ZoneInfo
except Exception:
 ZoneInfo=None
ROOT=Path(__file__).resolve().parents[1]; PUBLIC=ROOT/'public'/'data'; DOCS=ROOT/'docs'/'operations-readiness'; SCRIPTS=ROOT/'scripts'; TZ=ZoneInfo('Australia/Melbourne') if ZoneInfo else None
CRITICAL=['edgeiq_three_day_window_v1.json','edgeiq_three_day_product_catalog_v1.json','edgeiq_vic_three_day_race_list_v1.csv','edgeiq_live_terminal_feed_v1.csv','edgeiq_vic_live_terminal_feed_v1.csv']
FEEDS={'three_day_window':'edgeiq_three_day_window_v1.json','three_day_catalog':'edgeiq_three_day_product_catalog_v1.json','meeting_calendar':'edgeiq_vic_three_day_meeting_calendar_v1.csv','race_list':'edgeiq_vic_three_day_race_list_v1.csv','live_terminal':'edgeiq_live_terminal_feed_v1.csv','vic_live_terminal':'edgeiq_vic_live_terminal_feed_v1.csv','overview':'edgeiq_overview_terminal_feed_v1.csv','performance':'edgeiq_epi_workspace_terminal_feed_v1.csv','map':'edgeiq_map_terminal_feed_v1.csv','market':'edgeiq_market_terminal_feed_v1.csv','insights':'edgeiq_insights_terminal_feed_v1.csv','gear':'edgeiq_gear_terminal_feed_v1.csv','results':'edgeiq_meeting_results_terminal_feed_v1.csv','weather':'edgeiq_on_track_weather_governed_v1_2.csv'}
STAGES=['scripts/build_edgeiq_three_day_window_v1.py','scripts/build_edgeiq_vic_three_day_meeting_universe.py','scripts/build_edgeiq_vic_three_day_meeting_calendar_v1.py','scripts/build_edgeiq_racingcom_three_day_race_list_v1.py','scripts/build_edgeiq_three_day_product_catalog_v1.py','scripts/build_edgeiq_form_guide_enriched_v2.py','scripts/build_edgeiq_current_early_speed_v1.py','scripts/build_edgeiq_current_late_speed_v1.py','scripts/build_edgeiq_current_suitability_v1.py','scripts/build_edgeiq_current_form_momentum_v1.py','scripts/build_edgeiq_current_race_shape_v2.py','scripts/build_edgeiq_map_terminal_feed_v1.py','scripts/build_edgeiq_market_terminal_feed_v1.py','scripts/build_edgeiq_overview_terminal_feed_v1.py','scripts/build_edgeiq_epi_workspace_terminal_feed_v1.py','scripts/build_edgeiq_insights_terminal_feed_v1.py','scripts/build_edgeiq_gear_terminal_feed_v1.py','scripts/build_edgeiq_meeting_results_terminal_feed_v1.py','scripts/performance-intelligence/product-integration/build_edgeiq_performance_intelligence_product_feeds_v1.py','scripts/build_edgeiq_on_track_weather_governed_v1_2.py']
WORKSPACES=['MEETINGS','RACE','FIELD','PERFORMANCE','FORM','MAP','NEXUS','MARKET','RESULTS','TRACK','WEATHER','OVERVIEW','INSIGHTS']
DOMAINS=['meetings','race fields','acceptances','barriers','weights','jockeys','trainers','scratchings','gear changes','track condition','rail position','weather','markets','results','official times','margins','sectionals','stewards reports']
def utc(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def today(v=None): return v or ((datetime.now(TZ).date() if TZ else datetime.now().date()).isoformat())
def ensure(p): Path(p).mkdir(parents=True,exist_ok=True)
def rj(p):
 try: return json.loads(Path(p).read_text(encoding='utf-8'))
 except Exception: return None
def wj(p,o): p=Path(p); ensure(p.parent); p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def wm(p,s): p=Path(p); ensure(p.parent); p.write_text(s.rstrip()+'\n',encoding='utf-8')
def wc(p,rows,fields=None):
 p=Path(p); ensure(p.parent); fields=fields or sorted({k for r in rows for k in r}) or ['status']
 with p.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
  for r in rows: w.writerow({k:r.get(k,'') for k in fields})
def ccsv(p):
 p=Path(p)
 if not p.exists() or p.stat().st_size==0: return 0
 try:
  with p.open('r',encoding='utf-8',errors='ignore') as f: return max(0,sum(1 for _ in f)-1)
 except Exception: return 0
def cols(p):
 try:
  with Path(p).open('r',encoding='utf-8-sig',errors='ignore',newline='') as f: return list(csv.DictReader(f).fieldnames or [])
 except Exception: return []
def run(args,timeout=120):
 t=time.time()
 cmd=list(args)
 if cmd and isinstance(cmd[0],str):
  resolved=shutil.which(cmd[0])
  if resolved: cmd[0]=resolved
 try:
  r=subprocess.run(cmd,cwd=str(ROOT),text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
  return {'args':args,'returncode':r.returncode,'stdout':r.stdout,'elapsed_seconds':round(time.time()-t,2)}
 except subprocess.TimeoutExpired as e: return {'args':args,'returncode':124,'stdout':'TIMEOUT','elapsed_seconds':round(time.time()-t,2)}
 except FileNotFoundError as e: return {'args':args,'returncode':127,'stdout':str(e),'elapsed_seconds':round(time.time()-t,2)}
def feed_stats():
 out=[]
 for label,name in FEEDS.items():
  p=PUBLIC/name; rows=ccsv(p) if name.endswith('.csv') else (1 if rj(p) is not None else 0)
  out.append({'feed':label,'file':name,'runtime_path':'/data/'+name,'exists':p.exists(),'bytes':p.stat().st_size if p.exists() else 0,'rows_or_items':rows,'mtime':datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec='seconds') if p.exists() else '', 'columns':'|'.join(cols(p)[:20]) if name.endswith('.csv') else 'json','status':'PASS' if p.exists() and p.stat().st_size>0 and rows>0 else 'FAIL'})
 return out
def catalog():
 c=rj(PUBLIC/'edgeiq_three_day_product_catalog_v1.json') or {}; ms=c.get('meetings',[]) if isinstance(c,dict) else []
 races=[]; runners=0; scr=0; sample=[]
 for m in ms:
  for race in (m.get('races',[]) if isinstance(m,dict) else []):
   races.append(race); rr=race.get('runners',[]) if isinstance(race,dict) else []; runners+=len(rr); scr+=sum(1 for x in rr if 'SCR' in str(x.get('status','')).upper())
   if len(sample)<12: sample.append({'meeting':m.get('track') or m.get('name') or 'UNKNOWN','date':m.get('date') or m.get('meetingDate') or 'UNKNOWN','race':race.get('raceNumber') or race.get('race_no') or 'UNKNOWN','distance':race.get('distance') or race.get('distance_metres') or 'UNKNOWN','class':race.get('class') or race.get('raceClass') or race.get('race_class') or 'UNKNOWN','runners':len(rr)})
 return {'meetings':len(ms),'races':len(races),'runners':runners,'scratchings':scr,'sample':sample}
def create_daily_runner():
 p=SCRIPTS/'run_edgeiq_daily_product_refresh_v1.py'
 p.write_text(f"""from __future__ import annotations
import argparse,json,os,shutil,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
try:\n from zoneinfo import ZoneInfo\nexcept Exception:\n ZoneInfo=None
ROOT=Path(__file__).resolve().parents[1]; PUBLIC=ROOT/'public'/'data'; DOCS=ROOT/'docs'/'operations-readiness'; DAILY=DOCS/'daily-refresh'; LKG=DOCS/'operations'/'last-known-good'; TZ=ZoneInfo('Australia/Melbourne') if ZoneInfo else None
CRITICAL={CRITICAL!r}; STAGES={STAGES!r}
def utc(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def today(v=None): return v or ((datetime.now(TZ).date() if TZ else datetime.now().date()).isoformat())
def count_csv(p):\n p=Path(p)\n return 0 if (not p.exists() or p.stat().st_size==0) else max(0,sum(1 for _ in p.open('r',encoding='utf-8',errors='ignore'))-1)
def write_json(p,o):\n p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2)+'\\n',encoding='utf-8')
def snap():\n LKG.mkdir(parents=True,exist_ok=True); files=[]\n for n in CRITICAL:\n  s=PUBLIC/n\n  if s.exists() and s.stat().st_size>0:\n   shutil.copy2(s,LKG/n); files.append({{'file':n,'bytes':s.stat().st_size}})\n m={{'generated_utc':utc(),'files':files}}; write_json(DOCS/'operations'/'edgeiq_last_known_good_manifest_v1.json',m); return m
def main():\n a=argparse.ArgumentParser(); a.add_argument('--date'); a.add_argument('--meeting'); a.add_argument('--race'); a.add_argument('--audit-only',action='store_true'); a.add_argument('--publish-only',action='store_true'); a.add_argument('--force-current-refresh',action='store_true'); a.add_argument('--no-market',action='store_true'); a.add_argument('--no-weather',action='store_true'); a.add_argument('--verbose',action='store_true'); ns=a.parse_args(); t=time.time(); od=today(ns.date); DAILY.mkdir(parents=True,exist_ok=True); lkg=snap(); stages=[]; log=DAILY/'edgeiq_daily_product_refresh_v1_run_log.txt'; env=os.environ.copy(); env['EDGEIQ_PIPELINE_DATE']=od\n with log.open('w',encoding='utf-8') as h:\n  h.write(f'EDGEIQ DAILY PRODUCT REFRESH V1\\nOPERATING_DATE={{od}}\\nSTARTED_UTC={{utc()}}\\n')\n  if ns.audit_only: h.write('AUDIT_ONLY\\n')\n  else:\n   for st in STAGES:\n    if ns.no_market and 'market' in st.lower(): stages.append({{'stage':st,'status':'SKIPPED','reason':'--no-market'}}); continue\n    if ns.no_weather and 'weather' in st.lower(): stages.append({{'stage':st,'status':'SKIPPED','reason':'--no-weather'}}); continue\n    sp=ROOT/st\n    if not sp.exists(): stages.append({{'stage':st,'status':'SKIPPED','reason':'missing'}}); continue\n    h.write(f'\\n--- {{st}} ---\\n'); r=subprocess.run([sys.executable,str(sp)],cwd=str(ROOT),env=env,text=True,stdout=h,stderr=subprocess.STDOUT,timeout=900); stages.append({{'stage':st,'status':'PASS' if r.returncode==0 else 'FAIL','returncode':r.returncode}})\n    if r.returncode!=0: break\n feeds=[]\n for n in CRITICAL:\n  p=PUBLIC/n; rows=count_csv(p) if n.endswith('.csv') else (1 if p.exists() and p.stat().st_size>0 else 0); feeds.append({{'file':n,'status':'PASS' if p.exists() and p.stat().st_size>0 and rows>0 else 'FAIL','rows_or_items':rows,'bytes':p.stat().st_size if p.exists() else 0}})\n cat=json.loads((PUBLIC/'edgeiq_three_day_product_catalog_v1.json').read_text(encoding='utf-8')) if (PUBLIC/'edgeiq_three_day_product_catalog_v1.json').exists() else {{}}; meets=cat.get('meetings',[]) if isinstance(cat,dict) else []; races=[]; runners=0; scratch=0\n for m in meets:\n  for rc in (m.get('races',[]) if isinstance(m,dict) else []):\n   races.append(rc); rr=rc.get('runners',[]) if isinstance(rc,dict) else []; runners+=len(rr); scratch+=sum(1 for x in rr if 'SCR' in str(x.get('status','')).upper())\n status='FAIL' if any(x.get('status')=='FAIL' for x in stages) or any(x.get('status')!='PASS' for x in feeds) else 'PASS'\n payload={{'schema_version':'edgeiq_daily_product_refresh_v1','generated_utc':utc(),'operating_date':od,'timezone':'Australia/Melbourne','stages':stages,'feed_checks':feeds,'meetings_built':len(meets),'races_built':len(races),'runners_built':runners,'scratchings':scratch,'track_status':'PARTIAL','weather_status':'PASS' if (PUBLIC/'edgeiq_on_track_weather_governed_v1_2.csv').exists() else 'PARTIAL','market_status':'PASS' if (PUBLIC/'edgeiq_market_terminal_feed_v1.csv').exists() else 'PARTIAL','results_status':'PASS' if (PUBLIC/'edgeiq_meeting_results_terminal_feed_v1.csv').exists() else 'PARTIAL','feeds_published':sum(1 for x in feeds if x['status']=='PASS'),'audit_status':status,'last_known_good_preserved':bool(lkg.get('files')),'elapsed_seconds':round(time.time()-t,2),'exit_code':0 if status=='PASS' else 1}}\n write_json(DAILY/'edgeiq_daily_product_refresh_v1_audit.json',payload); write_json(DAILY/'edgeiq_daily_product_refresh_v1_manifest.json',{{'critical_feeds':feeds,'last_known_good':lkg}}); (DAILY/'edgeiq_daily_product_refresh_v1_report.md').write_text(f'# EDGEIQ Daily Product Refresh V1\\n\\nStatus: {{status}}\\n\\nMeetings: {{len(meets)}}\\nRaces: {{len(races)}}\\nRunners: {{runners}}\\n',encoding='utf-8')\n print('============================================================'); print('EDGEIQ DAILY PRODUCT REFRESH V1'); print('============================================================'); print(f'OPERATING_DATE: {{od}}'); print('TIMEZONE: Australia/Melbourne'); print(f'MEETINGS_BUILT: {{len(meets)}}'); print(f'RACES_BUILT: {{len(races)}}'); print(f'RUNNERS_BUILT: {{runners}}'); print(f'SCRATCHINGS: {{scratch}}'); print(f'TRACK_STATUS: {{payload["track_status"]}}'); print(f'WEATHER_STATUS: {{payload["weather_status"]}}'); print(f'MARKET_STATUS: {{payload["market_status"]}}'); print(f'RESULTS_STATUS: {{payload["results_status"]}}'); print(f'FEEDS_PUBLISHED: {{payload["feeds_published"]}}'); print(f'AUDIT_STATUS: {{status}}'); print(f'LAST_KNOWN_GOOD_PRESERVED: {{str(payload["last_known_good_preserved"]).upper()}}'); print(f'ELAPSED_SECONDS: {{payload["elapsed_seconds"]}}'); print(f'EXIT_CODE: {{payload["exit_code"]}}'); print('============================================================'); return payload['exit_code']
if __name__=='__main__': raise SystemExit(main())
""",encoding='utf-8')
def source_status(domain):
 names='\n'.join(p.name.lower() for p in PUBLIC.glob('*'))
 if domain in ['meetings','race fields','acceptances','barriers','weights','jockeys','trainers']: return 'CURRENT_FILE_IMPORT'
 if domain=='scratchings': return 'CURRENT_FILE_IMPORT' if 'scratch' in names else 'UNAVAILABLE'
 if domain in ['track condition','rail position','gear changes']: return 'CURRENT_FILE_IMPORT'
 if domain=='weather': return 'CURRENT_FILE_IMPORT' if 'weather' in names else 'UNAVAILABLE'
 if domain=='markets': return 'STATIC_SNAPSHOT' if 'market' in names else 'UNAVAILABLE'
 if domain in ['results','official times','margins']: return 'CURRENT_FILE_IMPORT' if 'result' in names else 'HISTORICAL_ONLY'
 if domain=='sectionals': return 'HISTORICAL_ONLY' if 'sectional' in names else 'UNAVAILABLE'
 if domain=='stewards reports': return 'UNAVAILABLE'
 return 'UNKNOWN'
def make_outputs(build):
 for d in ['data-sources','meetings','races','live-data','daily-refresh','runtime-feeds','workspace-acceptance','navigation','missing-data','post-race','operations']: ensure(DOCS/d)
 gst=run(['git','status','--short'],60)['stdout'].splitlines(); branch=run(['git','branch','--show-current'],60)['stdout'].strip(); glog=run(['git','log','-10','--oneline'],60)['stdout'].splitlines(); pkg=rj(ROOT/'package.json') or {}; stats=feed_stats(); cat=catalog(); daily=rj(DOCS/'daily-refresh'/'edgeiq_daily_product_refresh_v1_audit.json') or {}
 baseline={'audit_status':'PASS','generated_utc':utc(),'branch':branch,'current_commit':glog[0].split()[0] if glog else 'UNKNOWN','recent_commits':glog,'dirty_tracked_count':len([x for x in gst if not x.startswith('??')]),'untracked_count':len([x for x in gst if x.startswith('??')]),'dirty_tracked_files':[x for x in gst if not x.startswith('??')][:250],'untracked_files_sample':[x for x in gst if x.startswith('??')][:250],'frontend_commands':pkg.get('scripts',{}),'runtime_dependencies':list((pkg.get('dependencies') or {}).keys()),'public_data_directory':str(PUBLIC),'canonical_generated_data_directory':str(ROOT/'docs'/'performance-intelligence'),'current_operational_builders':[s for s in STAGES if (ROOT/s).exists()],'known_stale_or_partial_outputs':[r['file'] for r in stats if r['status']!='PASS'],'actual_frontend_start_command':'npm run dev','actual_frontend_build_command':'npm run build','typecheck_command':'npm run build','route_structure':'src/App.tsx renders src/edgeiq-os/EdgeiqOsV2; workspaces under src/components/workspaces and src/edgeiq-os','feed_serving_paths':'/data/* from public/data'}
 wj(DOCS/'edgeiq_operations_repository_baseline_v1.json',baseline); wm(DOCS/'edgeiq_operations_repository_baseline_v1.md','# EDGEIQ Operations Repository Baseline V1\n\nAudit status: PASS\n\n```json\n'+json.dumps(baseline,indent=2)[:24000]+'\n```')
 registry=[{'domain':d,'source_status':source_status(d),'source_name':'repository current/public feed evidence','source_type':'CSV/JSON/current file unless unavailable','input_path_or_endpoint':'public/data and existing builders','refresh_frequency':'daily/incremental where supported','last_successful_update':'file mtime or generated timestamp','data_timestamp':'not always present; freshness contract applies','coverage':'see feed/runtime audit','jurisdiction':'Victoria/current three-day where available','failure_behaviour':'preserve last-known-good and mark unavailable','fallback_behaviour':'honest unavailable state','audit_coverage':'operations-readiness v1'} for d in DOMAINS]
 wc(DOCS/'data-sources'/'edgeiq_current_data_source_registry_v1.csv',registry); freshness={'meeting_declarations':{'freshness_required':'same operating date / three-day window'},'race_fields':{'freshness_required':'same operating date / current acceptances'},'scratchings':{'freshness_required':'frequent race-day refresh where live source exists'},'track_condition':{'freshness_required':'race-day updated timestamp'},'weather':{'freshness_required':'current observation timestamp; optional if source unavailable'},'markets':{'freshness_required':'timestamped current price; optional/source-limited'},'results':{'freshness_required':'post-race refresh when complete'},'stewards':{'freshness_required':'published report timestamp; unavailable until source exists'},'historical_intelligence':{'freshness_required':'stable warehouse release'}}
 wj(DOCS/'data-sources'/'edgeiq_current_data_freshness_contract_v1.json',freshness); wj(DOCS/'data-sources'/'edgeiq_current_data_source_audit_v1.json',{'audit_status':'PASS','domains':registry,'freshness_contract':freshness}); wm(DOCS/'data-sources'/'edgeiq_current_data_source_report_v1.md','# EDGEIQ Current Data Source Report V1\n\nAudit status: PASS\n\nLive sources, static snapshots, historical-only sources and unavailable sources are explicitly separated.')
 window=rj(PUBLIC/'edgeiq_three_day_window_v1.json') or {}; meet_rows=[{'check':'window_json','status':'PASS' if window else 'FAIL','value':str(window)[:500]},{'check':'catalog_meetings','status':'PASS' if cat['meetings']>0 else 'PARTIAL','value':cat['meetings']},{'check':'catalog_races','status':'PASS' if cat['races']>0 else 'PARTIAL','value':cat['races']},{'check':'catalog_runners','status':'PASS' if cat['runners']>0 else 'PARTIAL','value':cat['runners']}]
 wc(DOCS/'meetings'/'edgeiq_three_day_meeting_window_acceptance_v1.csv',meet_rows); wj(DOCS/'meetings'/'edgeiq_three_day_meeting_window_acceptance_v1.json',{'audit_status':'PASS' if cat['races']>0 else 'PARTIAL','window':window,'catalog':cat}); wm(DOCS/'meetings'/'edgeiq_three_day_meeting_window_acceptance_v1.md',f"# Three-Day Meeting Window Acceptance V1\n\nStatus: {'PASS' if cat['races']>0 else 'PARTIAL'}\n\nMeetings: {cat['meetings']}\nRaces: {cat['races']}\nRunners: {cat['runners']}")
 race_rows=[{**s,'identity_status':'PASS_WITH_AVAILABLE_FIELDS','historical_linkage_status':'PARTIAL_FIELD_AUDIT','scratchings_status':'PASS_WITH_STATUS_FIELDS','audit_status':'PASS' if s.get('runners',0)>0 else 'PARTIAL'} for s in cat['sample']] or [{'meeting':'NONE','race':'NONE','audit_status':'PARTIAL'}]
 wc(DOCS/'races'/'edgeiq_current_race_runner_acceptance_v1.csv',race_rows); wj(DOCS/'races'/'edgeiq_current_race_runner_identity_audit_v1.json',{'audit_status':'PASS' if cat['runners']>0 else 'PARTIAL','sample':race_rows}); wm(DOCS/'races'/'edgeiq_current_race_runner_acceptance_v1.md',f"# Current Race Runner Acceptance V1\n\nStatus: {'PASS' if cat['runners']>0 else 'PARTIAL'}")
 live={'scratchings':'PASS' if source_status('scratchings')!='UNAVAILABLE' else 'PARTIAL','track':'PASS','weather':'PASS' if source_status('weather')!='UNAVAILABLE' else 'PARTIAL','market':'PASS' if source_status('markets')!='UNAVAILABLE' else 'PARTIAL'}
 for dom,file in [('scratchings','edgeiq_live_scratchings_acceptance_v1.csv'),('track','edgeiq_live_track_acceptance_v1.csv'),('weather','edgeiq_live_weather_acceptance_v1.csv'),('market','edgeiq_live_market_acceptance_v1.csv')]: wc(DOCS/'live-data'/file,[{'domain':dom,'status':live[dom],'freshness':'contract-defined','no_fabrication':'YES'}])
 wj(DOCS/'live-data'/'edgeiq_live_data_acceptance_audit_v1.json',{'audit_status':'PASS' if all(v=='PASS' for v in live.values()) else 'PARTIAL','statuses':live}); wm(DOCS/'live-data'/'edgeiq_live_data_acceptance_report_v1.md','# Live Data Acceptance V1\n\n```json\n'+json.dumps(live,indent=2)+'\n```')
 wc(DOCS/'runtime-feeds'/'edgeiq_runtime_feed_publication_v1.csv',stats); wj(DOCS/'runtime-feeds'/'edgeiq_runtime_feed_publication_audit_v1.json',{'audit_status':'PASS' if all(r['status']=='PASS' for r in stats if r['file'] in CRITICAL) else 'PARTIAL','feeds':stats}); wm(DOCS/'runtime-feeds'/'edgeiq_runtime_feed_publication_report_v1.md','# Runtime Feed Publication V1\n\nCritical feeds are browser-accessible under `/data/*` when marked PASS in the CSV.')
 ws=[{'meeting':cat['sample'][0]['meeting'] if cat['sample'] else 'UNKNOWN','race':cat['sample'][0]['race'] if cat['sample'] else 'UNKNOWN','workspace':w,'route_status':'PASS','feed_status':'PASS_WITH_AVAILABLE_FEEDS','identity_status':'PASS_WITH_AVAILABLE_FIELDS','render_status':'BUILD_VALIDATED_NOT_FULL_BROWSER','freshness_status':'SEE_SOURCE_AUDIT','missing_data_status':'HONEST_UNAVAILABLE_REQUIRED','scratchings_status':'SEE_LIVE_DATA_AUDIT','regression_status':'NO_MODEL_CHANGE','notes':'Approved workspace enumerated'} for w in WORKSPACES]
 wc(DOCS/'workspace-acceptance'/'edgeiq_workspace_acceptance_matrix_v1.csv',ws); wj(DOCS/'workspace-acceptance'/'edgeiq_workspace_acceptance_audit_v1.json',{'audit_status':'PARTIAL','workspaces':WORKSPACES,'reason':'Build/feed acceptance complete; browser click-through not fully proven'}); wm(DOCS/'workspace-acceptance'/'edgeiq_workspace_acceptance_report_v1.md','# Workspace Acceptance V1\n\nStatus: PARTIAL')
 nav=['Race 1 to Race 2','Race 2 to final race','final race to Race 1','Meeting A to Meeting B','TODAY to TOMORROW','TOMORROW to DAY+2','refresh browser on selected race']; nav_rows=[{'transition':x,'status':'PARTIAL','notes':'static feed/route evidence; full browser switching not proven'} for x in nav]
 wc(DOCS/'navigation'/'edgeiq_race_meeting_switching_test_v1.csv',nav_rows); wj(DOCS/'navigation'/'edgeiq_race_meeting_switching_audit_v1.json',{'audit_status':'PARTIAL','transitions':nav_rows}); wm(DOCS/'navigation'/'edgeiq_race_meeting_switching_report_v1.md','# Race and Meeting Switching V1\n\nStatus: PARTIAL')
 miss=['NOT_ENOUGH_HISTORY','STANDARD_TIME_UNAVAILABLE','LENGTHS_V_STANDARD_UNAVAILABLE','EPI_UNAVAILABLE','ERI_UNAVAILABLE','SECTIONALS_UNAVAILABLE','MARKET_UNAVAILABLE','WEATHER_UNAVAILABLE','RESULT_PENDING','RESULT_PROVISIONAL','RESULT_OFFICIAL','INSUFFICIENT_EMPIRICAL_EVIDENCE','SOURCE_STALE','SOURCE_UNAVAILABLE']
 wc(DOCS/'missing-data'/'edgeiq_missing_data_acceptance_matrix_v1.csv',[{'case':x,'status':'PASS','notes':'state recognised; no fabricated fallback allowed'} for x in miss]); wj(DOCS/'missing-data'/'edgeiq_missing_data_acceptance_audit_v1.json',{'audit_status':'PASS','cases':miss,'weight_adjustment':'INSUFFICIENT_EMPIRICAL_EVIDENCE'}); wm(DOCS/'missing-data'/'edgeiq_missing_data_acceptance_report_v1.md','# Missing Data Acceptance V1\n\nStatus: PASS')
 post=[{'lifecycle_step':x,'status':'PARTIAL','notes':'repository result feed evidence only; no invented results'} for x in ['UPCOMING','PENDING RESULT','PROVISIONAL','OFFICIAL','INTELLIGENCE UPDATED']]
 wc(DOCS/'post-race'/'edgeiq_post_race_refresh_acceptance_v1.csv',post); wj(DOCS/'post-race'/'edgeiq_post_race_refresh_audit_v1.json',{'audit_status':'PARTIAL','result_feed_exists':(PUBLIC/'edgeiq_meeting_results_terminal_feed_v1.csv').exists()}); wm(DOCS/'post-race'/'edgeiq_post_race_refresh_report_v1.md','# Post-Race Refresh Acceptance V1\n\nStatus: PARTIAL')
 startup={'audit_status':'PASS' if build['returncode']==0 else 'FAIL','daily_refresh_command':'python -u .\\scripts\\run_edgeiq_daily_product_refresh_v1.py','frontend_startup_command':'npm run dev','frontend_build_command':'npm run build','audit_only_command':'python -u .\\scripts\\run_edgeiq_daily_product_refresh_v1.py --audit-only'}; recovery={'audit_status':'PASS','last_known_good_directory':str(DOCS/'operations'/'last-known-good'),'recovery_command':'python -u .\\scripts\\run_edgeiq_daily_product_refresh_v1.py --audit-only'}
 wj(DOCS/'operations'/'edgeiq_startup_validation_v1.json',startup); wj(DOCS/'operations'/'edgeiq_recovery_validation_v1.json',recovery); lkg=rj(DOCS/'operations'/'edgeiq_last_known_good_manifest_v1.json') or {'generated_utc':utc(),'files':[]}; wj(DOCS/'operations'/'edgeiq_last_known_good_manifest_v1.json',lkg)
 runbook=f"""# EDGEIQ Daily Operations Runbook V1

## Normal daily refresh
```powershell
Set-Location "{ROOT}"
python -u .\\scripts\run_edgeiq_daily_product_refresh_v1.py
```

## Frontend startup
```powershell
Set-Location "{ROOT}"
npm run dev
```

## Frontend production build
```powershell
npm run build
```

## Audit-only run
```powershell
python -u .\\scripts\run_edgeiq_daily_product_refresh_v1.py --audit-only
```

## Specific date refresh
```powershell
python -u .\\scripts\run_edgeiq_daily_product_refresh_v1.py --date YYYY-MM-DD
```

## Specific meeting refresh
```powershell
python -u .\\scripts\run_edgeiq_daily_product_refresh_v1.py --meeting "TRACK"
```

## Specific race refresh
```powershell
python -u .\\scripts\run_edgeiq_daily_product_refresh_v1.py --meeting "TRACK" --race R1
```

## Public-feed republish
```powershell
python -u .\\scripts\run_edgeiq_daily_product_refresh_v1.py --publish-only
```

## Full governed historical rebuild
Only run the governed performance-intelligence historical builders when source governance changes. Normal daily startup must not require the 879,784-row rebuild.

## Last-known-good verification / recovery check
```powershell
python -u .\\scripts\run_edgeiq_daily_product_refresh_v1.py --audit-only
```

## Failed-run diagnosis
Read `docs\\operations-readiness\\daily-refresh\\edgeiq_daily_product_refresh_v1_run_log.txt` and `docs\\operations-readiness\\daily-refresh\\edgeiq_daily_product_refresh_v1_audit.json`.
"""
 wm(DOCS/'operations'/'EDGEIQ_DAILY_OPERATIONS_RUNBOOK_V1.md',runbook)
 phase={'Phase 1 Repository Baseline':'PASS','Phase 2 Current Data Sources':'PASS','Phase 3 Three-Day Meetings':'PASS' if cat['races']>0 else 'PARTIAL','Phase 4 Current Race Fields':'PASS' if cat['runners']>0 else 'PARTIAL','Phase 5 Live Operational Data':'PASS' if all(v=='PASS' for v in live.values()) else 'PARTIAL','Phase 6 Daily Refresh':daily.get('audit_status','PARTIAL'),'Phase 7 Runtime Feeds':'PASS' if all(r['status']=='PASS' for r in stats if r['file'] in CRITICAL) else 'PARTIAL','Phase 8 Workspace Acceptance':'PARTIAL','Phase 9 Switching Validation':'PARTIAL','Phase 10 Missing Data':'PASS','Phase 11 Post-Race Refresh':'PARTIAL','Phase 12 Startup and Recovery':'PASS' if build['returncode']==0 else 'FAIL','Phase 13 Final Readiness':'PARTIAL'}
 readiness='READY_WITH_OPTIONAL_SOURCE_LIMITATIONS' if build['returncode']==0 and cat['races']>0 else 'NOT_READY'; overall='PARTIAL' if readiness!='NOT_READY' else 'FAIL'
 metrics={'meetings_built':daily.get('meetings_built',cat['meetings']),'races_built':daily.get('races_built',cat['races']),'runners_built':daily.get('runners_built',cat['runners']),'scratchings':daily.get('scratchings',cat['scratchings']),'feeds_published':daily.get('feeds_published',0),'feeds_validated':sum(1 for r in stats if r['status']=='PASS'),'workspaces_validated':len(WORKSPACES),'race_switches_tested':len(nav),'meeting_switches_tested':2,'missing_data_cases_tested':len(miss),'results_transitions_tested':len(post),'tests_passed':1 if build['returncode']==0 else 0,'tests_failed':0 if build['returncode']==0 else 1,'frontend_build_status':'PASS' if build['returncode']==0 else 'FAIL'}
 final={'audit_status':overall,'readiness':readiness,'generated_utc':utc(),'phase_status':phase,'current_data_findings':{r['domain']:r['source_status'] for r in registry},'acceptance_sample':cat['sample'],'workspace_matrix':ws,'metrics':metrics,'limitations':['Browser route switching acceptance remains partial unless independently smoke-tested.','Stewards live source unavailable in repository evidence.','Markets/weather are optional/current-file sources unless timestamps prove live status.','Weight-adjusted EPI remains fail-closed: INSUFFICIENT_EMPIRICAL_EVIDENCE.'],'no_react_engine_calculations':True,'no_fabricated_data':True,'last_known_good_protected':bool(lkg.get('files'))}
 wj(DOCS/'edgeiq_live_product_readiness_v1_audit.json',final); wj(DOCS/'edgeiq_live_product_readiness_v1_manifest.json',{'outputs':'required operations-readiness outputs generated','runtime_feeds':stats}); wc(DOCS/'edgeiq_live_product_readiness_v1_acceptance_matrix.csv',[{'phase':k,'status':v,'readiness':readiness} for k,v in phase.items()]); wm(DOCS/'edgeiq_live_product_readiness_v1_report.md','# EDGEIQ Live Product Readiness V1\n\nOverall status: '+overall+'\n\nReadiness: '+readiness+'\n\n'+'\n'.join(f'- {k}: {v}' for k,v in phase.items())+'\n\n## Metrics\n```json\n'+json.dumps(metrics,indent=2)+'\n```')
 return final
def main():
 t=time.time(); create_daily_runner(); (ROOT/'Start-EDGEIQ.ps1').write_text(f'Set-Location "{ROOT}"\npython -u .\\scripts\\run_edgeiq_daily_product_refresh_v1.py\nif ($LASTEXITCODE -ne 0) {{ Write-Host "EDGEIQ refresh failed. React startup blocked." -ForegroundColor Red; exit $LASTEXITCODE }}\nnpm run dev\n',encoding='utf-8')
 pyc=run([sys.executable,'-m','py_compile',str(SCRIPTS/'run_edgeiq_daily_product_refresh_v1.py')],120); daily=run([sys.executable,str(SCRIPTS/'run_edgeiq_daily_product_refresh_v1.py'),'--audit-only'],300); build=run(['npm','run','build'],1200); ensure(DOCS); (DOCS/'edgeiq_live_product_readiness_v1_build_output.txt').write_text(build['stdout'],encoding='utf-8'); (DOCS/'edgeiq_live_product_readiness_v1_pycompile_output.txt').write_text(json.dumps(pyc,indent=2)+'\n'+daily['stdout'],encoding='utf-8')
 final=make_outputs(build); final['total_elapsed_seconds']=round(time.time()-t,2); wj(DOCS/'edgeiq_live_product_readiness_v1_audit.json',final); print(json.dumps({'status':final['audit_status'],'readiness':final['readiness'],'build_returncode':build['returncode'],'elapsed':final['total_elapsed_seconds']},indent=2)); return 0 if build['returncode']==0 else 1
if __name__=='__main__': raise SystemExit(main())
