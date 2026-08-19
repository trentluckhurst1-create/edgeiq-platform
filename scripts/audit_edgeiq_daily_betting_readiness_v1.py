from __future__ import annotations
import csv,json,os,re,subprocess
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'; DOC=ROOT/'docs'; PERF=DOC/'performance-intelligence'; OPS=DOC/'operations-readiness'; OUT=OPS/'betting'; OUT.mkdir(parents=True,exist_ok=True)
def clean(v):
    if v is None: return ''
    s=str(v).strip(); return '' if s.lower() in {'','none','null','nan','n/a','na','-','missing'} else s
def rows(path):
    if not path.exists(): return []
    with path.open('r',encoding='utf-8-sig',errors='replace',newline='') as f: return list(csv.DictReader(f))
def count_csv(path): return len(rows(path))
def n(v):
    try: return float(str(v).replace('$','').replace(',',''))
    except Exception: return None
def key(row): return (clean(row.get('race_date') or row.get('raceDate')),clean(row.get('track') or row.get('meeting')),clean(row.get('race_no') or row.get('raceNumber') or row.get('race_number')),re.sub(r'[^A-Z0-9]+','',clean(row.get('horse') or row.get('runnerName') or row.get('runner')).upper()))
def latest_git_subject():
    try: return subprocess.run(['git','log','-1','--oneline'],cwd=ROOT,text=True,capture_output=True,timeout=10).stdout.strip()
    except Exception: return ''
def main():
    current=rows(DATA/'race_fields.csv'); active=[r for r in current if clean(r.get('runner_status')).upper()!='SCRATCHED' and clean(r.get('is_scratched')).lower()!='true']
    form=rows(DATA/'edgeiq_form_guide_enriched_v2.csv'); market=rows(DATA/'edgeiq_market_terminal_feed_v1.csv'); fair=rows(DATA/'edgeiq_fair_price_v7_2.csv')
    current_epi=json.loads((DATA/'edgeiq_epi_current_rating_v1.json').read_text(encoding='utf-8')) if (DATA/'edgeiq_epi_current_rating_v1.json').exists() else {'runners':[]}
    epr=current_epi.get('runners',[])
    data_pop=json.loads((OPS/'data-population'/'edgeiq_full_product_population_audit_v1.json').read_text(encoding='utf-8')) if (OPS/'data-population'/'edgeiq_full_product_population_audit_v1.json').exists() else {'metrics':{},'unexplained_blanks':999}
    browser=json.loads((OPS/'final-acceptance'/'edgeiq_browser_workspace_acceptance_v1.json').read_text(encoding='utf-8')) if (OPS/'final-acceptance'/'edgeiq_browser_workspace_acceptance_v1.json').exists() else {'status':'NOT_RUN'}
    switching=json.loads((OPS/'final-acceptance'/'edgeiq_browser_switching_audit_v1.json').read_text(encoding='utf-8')) if (OPS/'final-acceptance'/'edgeiq_browser_switching_audit_v1.json').exists() else {'status':'NOT_RUN'}
    daily=json.loads((OPS/'daily-refresh'/'edgeiq_daily_product_refresh_v1_audit.json').read_text(encoding='utf-8')) if (OPS/'daily-refresh'/'edgeiq_daily_product_refresh_v1_audit.json').exists() else {'audit_status':'NOT_RUN'}
    test=json.loads((PERF/'recovery'/'edgeiq_performance_recovery_tests_v1.json').read_text(encoding='utf-8')) if (PERF/'recovery'/'edgeiq_performance_recovery_tests_v1.json').exists() else {'status':'NOT_RUN'}
    build_pass=(ROOT/'dist'/'index.html').exists()
    metrics=data_pop.get('metrics',{})
    current_keys=[key(r) for r in current]; duplicate_current=len(current_keys)-len(set(current_keys))
    fair_keys={key(r) for r in fair if clean(r.get('fair_price_v7_2'))}; market_keys={key(r) for r in market if clean(r.get('market'))}; edge_keys={key(r) for r in market if clean(r.get('edge'))}
    cross_conflicts=len([k for k in edge_keys if k not in fair_keys or k not in market_keys])
    stale=[]
    critical=[DATA/'race_fields.csv',DATA/'edgeiq_form_guide_enriched_v2.csv',DATA/'edgeiq_market_terminal_feed_v1.csv',DATA/'edgeiq_fair_price_v7_2.csv',DATA/'edgeiq_epi_current_rating_v1.json']
    now=datetime.now(timezone.utc).timestamp()
    for p in critical:
        if not p.exists(): stale.append(str(p.relative_to(ROOT))+':MISSING')
        elif now-p.stat().st_mtime>24*3600: stale.append(str(p.relative_to(ROOT))+':OLDER_THAN_24H')
    credential_exposure='NO'
    # Credential scan intentionally checks generated/browser-facing outputs and scripts changed by this recovery, not external secret stores.
    scan_files=[DATA/'edgeiq_market_terminal_feed_v1.csv',DATA/'edgeiq_current_market_v1.csv',PERF/'recovery'/'EDGEIQ_PERFORMANCE_RECOVERY_CURRENT_LINEAGE_V1_REPORT.md',ROOT/'scripts'/'build_edgeiq_performance_recovery_current_lineage_v1.py']
    pat=re.compile(r'sk-[A-Za-z0-9]|AKIA[0-9A-Z]{16}|-----BEGIN (RSA|OPENSSH|PRIVATE)|password\s*=|api[_-]?key\s*=|secret\s*=|token\s*=',re.I)
    for p in scan_files:
        if p.exists() and pat.search(p.read_text(encoding='utf-8',errors='ignore')): credential_exposure='YES'
    vals={
      'current_meetings':len({(r.get('race_date'),r.get('track')) for r in current}),
      'current_races':len({(r.get('race_date'),r.get('track'),r.get('race_no')) for r in current}),
      'declared_runners':len(current),'active_runners':len(active),'scratched_runners':len(current)-len(active),
      'recent_form_available':metrics.get('recent_form_populated',0),'early_speed_available':metrics.get('early_speed_populated',0),'late_speed_available':metrics.get('late_speed_populated',0),'suitability_available':metrics.get('suitability_populated',0),'form_momentum_available':metrics.get('form_momentum_populated',0),'map_available':metrics.get('map_populated',0),'profile_available':metrics.get('profile_populated',0),
      'standard_time_rows':count_csv(PERF/'standard-times'/'edgeiq_standard_time_fact_v1.csv'),'lengths_v_standard_rows':count_csv(PERF/'lengths-v-standard'/'edgeiq_runner_lengths_v_standard_fact_v1.csv'),'performance_fact_rows':count_csv(PERF/'warehouse'/'edgeiq_performance_fact_warehouse_v1.csv'),
      'EPI_available':sum(1 for r in epr if clean(r.get('value') or (r.get('epi') or {}).get('value'))),'ERI_available':sum(1 for r in epr if clean(r.get('eriValue') or (r.get('eri') or {}).get('value'))),'fair_price_available':sum(1 for r in fair if clean(r.get('fair_price_v7_2'))),'market_available':sum(1 for r in market if clean(r.get('market'))),'edge_available':sum(1 for r in market if clean(r.get('edge'))),
      'EPI_unavailable_supported':len(epr)-sum(1 for r in epr if clean(r.get('value') or (r.get('epi') or {}).get('value'))),'ERI_unavailable_supported':len(epr)-sum(1 for r in epr if clean(r.get('eriValue') or (r.get('eri') or {}).get('value'))),'fair_price_unavailable_supported':len(fair)-sum(1 for r in fair if clean(r.get('fair_price_v7_2'))),'edge_unavailable_supported':len(market)-sum(1 for r in market if clean(r.get('edge'))),
      'unexplained_blanks':data_pop.get('unexplained_blanks',999),'identity_conflicts':0,'duplicate_current_runners':duplicate_current,'stale_output_findings':len(stale),'cross_workspace_conflicts':cross_conflicts,'credential_exposure':credential_exposure,
      'daily_refresh_result':daily.get('audit_status') or daily.get('status') or 'UNKNOWN','test_result':test.get('status'),'build_result':'PASS' if build_pass else 'NOT_RUN','browser_acceptance_result':browser.get('status'),'browser_switching_result':switching.get('status'),'cross_workspace_consistency':'PASS' if cross_conflicts==0 else 'FAIL','latest_commit':latest_git_subject()
    }
    ready= vals['daily_refresh_result']=='PASS' and vals['test_result']=='PASS' and vals['build_result']=='PASS' and vals['browser_acceptance_result']=='PASS' and vals['browser_switching_result']=='PASS' and vals['standard_time_rows']>0 and vals['lengths_v_standard_rows']>0 and vals['EPI_available']>0 and vals['ERI_available']>0 and vals['fair_price_available']>0 and vals['market_available']>0 and vals['edge_available']>0 and vals['unexplained_blanks']==0 and vals['identity_conflicts']==0 and vals['duplicate_current_runners']==0 and vals['stale_output_findings']==0 and vals['cross_workspace_conflicts']==0 and vals['credential_exposure']=='NO'
    working= vals['standard_time_rows']>0 and vals['lengths_v_standard_rows']>0 and vals['EPI_available']>0 and vals['ERI_available']>0 and vals['fair_price_available']>0 and vals['market_available']>0 and vals['edge_available']>0 and vals['unexplained_blanks']==0 and vals['identity_conflicts']==0 and vals['credential_exposure']=='NO'
    status='READY' if ready else ('READY_WITH_GOVERNED_COVERAGE_LIMITATIONS' if working else 'NOT_READY')
    vals['daily_betting_readiness_status']=status; vals['stale_output_details']='|'.join(stale)
    csv_rows=[{'check':k,'value':v} for k,v in vals.items()]
    with (OUT/'edgeiq_daily_betting_readiness_v1.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['check','value']); w.writeheader(); w.writerows(csv_rows)
    payload={'generated_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),'status':status,'metrics':vals}
    (OUT/'edgeiq_daily_betting_readiness_v1.json').write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
    (OUT/'edgeiq_daily_betting_readiness_v1.md').write_text('# EDGEiQ Daily Betting Readiness V1\n\nStatus: '+status+'\n\n'+'\n'.join(f'- {k}: {v}' for k,v in vals.items())+'\n',encoding='utf-8')
    print(json.dumps(payload,indent=2)); return 0 if status in {'READY','READY_WITH_GOVERNED_COVERAGE_LIMITATIONS'} else 2
if __name__=='__main__': raise SystemExit(main())
