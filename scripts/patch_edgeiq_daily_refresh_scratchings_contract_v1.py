
from __future__ import annotations
import shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'scripts'/'run_edgeiq_daily_product_refresh_v1.py'
CP=ROOT/'scripts'/'run_edgeiq_daily_product_refresh_v1_CHECKPOINT_PRE_SCRATCHINGS_CONTRACT_V1.py'
if not CP.exists(): shutil.copy2(P,CP)
text=P.read_text(encoding='utf-8')
old="""cat=json.loads((PUBLIC/'edgeiq_three_day_product_catalog_v1.json').read_text(encoding='utf-8')) if (PUBLIC/'edgeiq_three_day_product_catalog_v1.json').exists() else {}; meets=cat.get('meetings',[]) if isinstance(cat,dict) else []; races=[]; runners=0; scratch=0
 for m in meets:
  for rc in (m.get('races',[]) if isinstance(m,dict) else []):
   races.append(rc); rr=rc.get('runners',[]) if isinstance(rc,dict) else []; runners+=len(rr); scratch+=sum(1 for x in rr if 'SCR' in str(x.get('status','')).upper())
"""
new="""cat=json.loads((PUBLIC/'edgeiq_three_day_product_catalog_v1.json').read_text(encoding='utf-8')) if (PUBLIC/'edgeiq_three_day_product_catalog_v1.json').exists() else {}; meets=cat.get('meetings',[]) if isinstance(cat,dict) else []; races=[]; runners=0; total_current_scratchings=0; active_runners=0
 def _runner_scratched(x):
  off=x.get('official') if isinstance(x,dict) and isinstance(x.get('official'),dict) else {}
  src=x.get('source') if isinstance(x,dict) and isinstance(x.get('source'),dict) else {}
  vals=[off.get('scratched'),src.get('scratched'),src.get('is_scratched'),off.get('status'),src.get('status')]
  return any(str(v).strip().lower() in {'true','scr','scratched','lscr','late scratching'} for v in vals)
 for m in meets:
  for rc in (m.get('races',[]) if isinstance(m,dict) else []):
   races.append(rc); rr=rc.get('runners',[]) if isinstance(rc,dict) else []; runners+=len(rr); race_scratch=sum(1 for x in rr if _runner_scratched(x)); total_current_scratchings+=race_scratch; active_runners+=max(0,len(rr)-race_scratch)
 scratch=total_current_scratchings
"""
if old not in text:
    if 'total_current_scratchings' in text:
        print('daily refresh already patched')
    else:
        raise SystemExit('daily refresh scratchings block not found')
else:
    text=text.replace(old,new)
    text=text.replace("'runners_built':runners,'scratchings':scratch,'track_status'", "'runners_built':runners,'declared_runners':runners,'active_runners':active_runners,'total_current_scratchings':total_current_scratchings,'new_scratchings_this_run':None,'scratching_changes_this_run':None,'reinstated_runners_this_run':None,'scratchings_metric_deprecated':scratch,'track_status'")
    text=text.replace("print(f'SCRATCHINGS: {scratch}')", "print(f'DECLARED_RUNNERS: {runners}'); print(f'ACTIVE_RUNNERS: {active_runners}'); print(f'TOTAL_CURRENT_SCRATCHINGS: {total_current_scratchings}'); print('NEW_SCRATCHINGS_THIS_RUN: NOT_CALCULATED'); print('SCRATCHING_CHANGES_THIS_RUN: NOT_CALCULATED'); print('REINSTATED_RUNNERS_THIS_RUN: NOT_CALCULATED')")
    P.write_text(text,encoding='utf-8')
    print('patched daily refresh scratchings contract')
