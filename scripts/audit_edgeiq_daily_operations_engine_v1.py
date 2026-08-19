from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path
from edgeiq_daily_operations_common_v1 import *
FIELDS=['check','status','detail']
def main():
    checks=[]
    def check(name, passed, detail=''):
        checks.append({'check':name,'status':'PASS' if passed else 'FAIL','detail':clean(detail)})
    cfg=load_config(); check('configuration_exists', bool(cfg), CONFIG_PATH)
    for key in ['timezone','default_lookback_days','lock_path','source_authority_order','allowed_source_adapters']:
        check('config_key_'+key, key in cfg, key)
    required_scripts=['build_edgeiq_daily_race_discovery_v1.py','build_edgeiq_daily_official_results_ingestion_v1.py','build_edgeiq_daily_official_timing_ingestion_v1.py','build_edgeiq_daily_condition_evidence_v1.py','build_edgeiq_delayed_speed_data_ingestion_v1.py','build_edgeiq_race_data_lifecycle_fact_v1.py','update_edgeiq_canonical_historical_timing_warehouse_v1.py','run_edgeiq_daily_operations_engine_v1.py']
    for s in required_scripts: check('script_exists_'+s,(ROOT/'scripts'/s).exists(),s)
    outputs=['edgeiq_daily_race_discovery_v1.csv','edgeiq_daily_official_results_fact_v1.csv','edgeiq_daily_official_timing_candidate_v1.csv','edgeiq_daily_condition_evidence_v1.csv','edgeiq_delayed_speed_data_ingestion_v1.csv','edgeiq_race_data_lifecycle_fact_v1.csv','edgeiq_daily_operations_manifest_v1.json','edgeiq_daily_operations_alert_fact_v1.csv']
    for o in outputs: check('output_exists_'+o,(DATA/o).exists(),o)
    lifecycle=read_csv(DATA/'edgeiq_race_data_lifecycle_fact_v1.csv')
    ids=[r.get('canonical_race_id','') for r in lifecycle if r.get('canonical_race_id')]
    check('lifecycle_unique_current_rows', len(ids)==len(set(ids)), f'{len(ids)} rows')
    lock=ROOT/clean(cfg.get('lock_path','')) if cfg.get('lock_path') else None
    check('lock_released', not lock or not lock.exists(), lock or '')
    for ps in ['install_edgeiq_daily_operations_tasks_v1.ps1','uninstall_edgeiq_daily_operations_tasks_v1.ps1','show_edgeiq_daily_operations_tasks_v1.ps1','run_edgeiq_daily_operations_now_v1.ps1']:
        check('scheduler_script_exists_'+ps,(ROOT/'scripts'/ps).exists(),ps)
    forbidden_changed=[]
    r=subprocess.run(['git','diff','--cached','--name-only','--','src','public/data/*pricing*','public/data/*probability*'],cwd=ROOT,text=True,capture_output=True)
    if r.stdout.strip(): forbidden_changed=r.stdout.strip().splitlines()
    check('protected_system_changes_absent', not forbidden_changed, ';'.join(forbidden_changed))
    failed=[c for c in checks if c['status']!='PASS']
    write_csv_atomic(DATA/'edgeiq_daily_operations_engine_v1_audit.csv',checks,FIELDS)
    payload={'status':'PASS' if not failed else 'FAIL','checks':len(checks),'failed_checks':failed}; write_json_atomic(DATA/'edgeiq_daily_operations_engine_v1_audit_summary.json',payload); print(json.dumps(payload,indent=2)); return 0 if not failed else 1
if __name__=='__main__': raise SystemExit(main())
