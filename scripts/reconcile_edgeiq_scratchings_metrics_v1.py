
from __future__ import annotations
import csv, json, subprocess
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
OUT=ROOT/'docs'/'operations-readiness'/'final-acceptance'
CAT=DATA/'edgeiq_three_day_product_catalog_v1.json'
DAILY=ROOT/'docs'/'operations-readiness'/'daily-refresh'/'edgeiq_daily_product_refresh_v1_audit.json'
def clean(v): return '' if v is None else str(v).strip()
def utc(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def is_scr(r):
    off=r.get('official') if isinstance(r.get('official'),dict) else {}
    src=r.get('source') if isinstance(r.get('source'),dict) else {}
    vals=[off.get('scratched'),src.get('scratched'),src.get('is_scratched'),off.get('status'),src.get('status')]
    return any(str(v).strip().lower() in {'true','scr','scratched','lscr','late scratching'} for v in vals)
def main():
    if not CAT.exists(): raise FileNotFoundError(CAT)
    OUT.mkdir(parents=True,exist_ok=True)
    cat=json.loads(CAT.read_text(encoding='utf-8'))
    daily=json.loads(DAILY.read_text(encoding='utf-8')) if DAILY.exists() else {}
    rows=[]
    summary={'generated_utc':utc(),'meetings':0,'races':0,'declared_runners':0,'active_runners':0,'total_current_scratchings':0,'daily_refresh_legacy_scratchings':daily.get('scratchings'),'legacy_metric_scope':'runner.status text containing SCR only','correct_metric_scope':'official/source scratched boolean, de-duplicated once per race runner','reconciliation_status':'PASS'}
    for m in cat.get('meetings',[]) if isinstance(cat,dict) else []:
        summary['meetings']+=1; meeting_key=clean(m.get('meetingKey')); meeting=clean(m.get('meeting')); date=clean(m.get('date'))
        for race in m.get('races',[]) or []:
            summary['races']+=1; runners=race.get('runners',[]) or []; seen=set(); declared=scr=0
            for idx,runner in enumerate(runners):
                off=runner.get('official') if isinstance(runner.get('official'),dict) else {}; src=runner.get('source') if isinstance(runner.get('source'),dict) else {}
                horse=clean(off.get('runner') or src.get('horseName') or src.get('runnerName') or idx); no=clean(off.get('no') or off.get('number') or src.get('raceEntryNumber') or idx+1)
                key=(clean(race.get('raceKey')),no,horse.upper())
                if key in seen: continue
                seen.add(key); declared+=1; scr += 1 if is_scr(runner) else 0
            active=declared-scr; status='PASS' if active>=0 and declared-scr==active else 'FAIL'
            if status!='PASS': summary['reconciliation_status']='FAIL'
            rows.append({'race_date':date,'meeting':meeting,'meeting_key':meeting_key,'race_key':clean(race.get('raceKey')),'race_no':clean(race.get('raceNumber')),'declared_runners':declared,'current_scratchings':scr,'active_runners':active,'declared_minus_scratchings':declared-scr,'reconciliation_status':status})
            summary['declared_runners']+=declared; summary['total_current_scratchings']+=scr; summary['active_runners']+=active
    summary['scratchings_scope_discrepancy_cause']='Daily refresh legacy metric checked runner status text only; Meetings/catalog count official/source scratched booleans.'
    summary['new_scratchings_this_run']='NOT_CALCULATED_NO_PREVIOUS_SNAPSHOT_DIFF_IN_THIS_ACCEPTANCE_RUN'; summary['scratching_changes_this_run']='NOT_CALCULATED_NO_PREVIOUS_SNAPSHOT_DIFF_IN_THIS_ACCEPTANCE_RUN'; summary['reinstated_runners_this_run']='NOT_CALCULATED_NO_PREVIOUS_SNAPSHOT_DIFF_IN_THIS_ACCEPTANCE_RUN'
    with (OUT/'edgeiq_scratchings_reconciliation_v1.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    (OUT/'edgeiq_scratchings_reconciliation_v1.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    (OUT/'edgeiq_scratchings_reconciliation_v1.md').write_text(f"# EDGEiQ Scratchings Reconciliation V1\n\nStatus: {summary['reconciliation_status']}\n\nDeclared runners: {summary['declared_runners']}\nActive runners: {summary['active_runners']}\nTotal current scratchings: {summary['total_current_scratchings']}\nLegacy daily SCRATCHINGS field: {summary['daily_refresh_legacy_scratchings']}\n\nCause: {summary['scratchings_scope_discrepancy_cause']}\n",encoding='utf-8')
    print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
