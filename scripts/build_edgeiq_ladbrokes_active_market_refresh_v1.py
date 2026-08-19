from __future__ import annotations
import json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'public'/'data'
SUMMARY=PUBLIC/'edgeiq_ladbrokes_active_market_refresh_v1_summary.csv'
RUNTIME=PUBLIC/'edgeiq_ladbrokes_affiliate_market_runtime_v1.csv'
def write_summary(rows):
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    SUMMARY.write_text('metric,value\n'+'\n'.join(f'{k},{v}' for k,v in rows)+'\n',encoding='utf-8')
def main():
    from_header=os.environ.get('EDGEIQ_LADBROKES_FROM','').strip() or os.environ.get('EDGEIQ_LADBROKES_EMAIL','').strip()
    partner=os.environ.get('EDGEIQ_LADBROKES_X_PARTNER','').strip() or os.environ.get('EDGEIQ_LADBROKES_PARTNER_NAME','').strip()
    if not (from_header and partner):
        status='SKIPPED_NO_AUTH_PRESERVED_EXISTING_RUNTIME' if RUNTIME.exists() else 'AUTH_REQUIRED_NO_EXISTING_RUNTIME'
        write_summary([('status',status),('generated_at',datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')),('runtime_preserved','YES' if RUNTIME.exists() else 'NO'),('production_pricing_changed','NO')])
        print(json.dumps({'status':status,'runtime_preserved':RUNTIME.exists()},indent=2)); return
    result=subprocess.run([sys.executable,str(ROOT/'scripts'/'build_edgeiq_ladbrokes_affiliate_market_adapter_v1.py'),'--mode','ACTIVE_MARKET_REFRESH'],cwd=ROOT)
    write_summary([('status','PASS' if result.returncode==0 else 'FAIL'),('return_code',str(result.returncode)),('runtime_preserved','YES' if RUNTIME.exists() else 'NO'),('production_pricing_changed','NO')])
    raise SystemExit(result.returncode)
if __name__=='__main__': main()
