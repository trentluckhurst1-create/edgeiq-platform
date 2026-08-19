import csv
import hashlib
import json
import shutil
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public/data"
CANDIDATE = DATA / "edgeiq_race_entry_fact_v1_CANDIDATE.csv"
PRODUCTION = DATA / "edgeiq_race_entry_fact_v1.csv"
REJECTED = DATA / "edgeiq_race_entry_fact_v1_rejected_v1.csv"
AUDIT = DATA / "edgeiq_race_entry_fact_v1_audit.csv"
REPORT = DATA / "edgeiq_race_entry_fact_v1_audit_report.txt"
CONTRACT = ROOT / "contracts/performance-intelligence/edgeiq_race_entry_fact_v1_contract.json"
TODAY = date.today()
csv.field_size_limit(1024*1024*64)

def read_csv(path):
    if not path.exists(): return []
    with path.open(newline='',encoding='utf-8-sig',errors='replace') as f: return [dict(r) for r in csv.DictReader(f)]
def parse_date(v):
    try: return datetime.fromisoformat((v or '')[:10]).date()
    except Exception: return None
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()
def metric(rows,k,v): rows.append({'metric':k,'value':v})

def main():
    rows=read_csv(CANDIDATE)
    rejected=read_csv(REJECTED)
    contract=json.loads(CONTRACT.read_text(encoding='utf-8'))
    required=contract['requiredFields']
    cols=set(rows[0].keys()) if rows else set()
    missing_cols=[c for c in required if c not in cols]
    keys=set(); dup=0
    for r in rows:
        key=(r.get('canonical_race_id'),r.get('canonical_runner_id'))
        if key in keys: dup+=1
        keys.add(key)
    bad_dates=sum(1 for r in rows if not parse_date(r.get('race_date')) or parse_date(r.get('race_date'))<TODAY)
    id_miss=sum(1 for r in rows if not r.get('canonical_race_id') or not r.get('canonical_runner_id'))
    surface_bad=sum(1 for r in rows if r.get('surface_group') not in {'TURF','AUSTRALIAN_SYNTHETIC'})
    distance_bad=sum(1 for r in rows if not r.get('race_distance_metres'))
    source_miss=sum(1 for r in rows if not r.get('source_record_id') or not r.get('source_hash'))
    results_only=sum(1 for r in rejected if 'RESULTS' in (r.get('rejection_reason') or '').upper())
    by_decl={}
    for r in rows: by_decl[r.get('declaration_status','')]=by_decl.get(r.get('declaration_status',''),0)+1
    by_day={'today':0,'tomorrow':0,'day_plus_2':0,'later':0}
    for r in rows:
        d=parse_date(r.get('race_date'))
        if not d: continue
        delta=(d-TODAY).days
        if delta==0: by_day['today']+=1
        elif delta==1: by_day['tomorrow']+=1
        elif delta==2: by_day['day_plus_2']+=1
        else: by_day['later']+=1
    failures={
        'missing_required_columns':len(missing_cols),
        'duplicate_race_runner_keys':dup,
        'bad_or_stale_dates':bad_dates,
        'identity_misses':id_miss,
        'surface_identity_invalid':surface_bad,
        'race_distance_invalid':distance_bad,
        'source_provenance_missing':source_miss,
    }
    verdict='PASS' if rows and all(v==0 for v in failures.values()) else 'FAIL'
    audit=[]
    metric(audit,'candidate_rows',len(rows)); metric(audit,'active_rows',by_decl.get('ACTIVE_ENTRY',0)); metric(audit,'scratched_rows',by_decl.get('SCRATCHED_ENTRY',0)); metric(audit,'emergency_rows',by_decl.get('EMERGENCY_ENTRY',0)); metric(audit,'races',len(set(r.get('canonical_race_id') for r in rows))); metric(audit,'meetings',len(set((r.get('race_date'),r.get('canonical_track')) for r in rows))); metric(audit,'tracks',len(set(r.get('canonical_track') for r in rows))); metric(audit,'today_rows',by_day['today']); metric(audit,'tomorrow_rows',by_day['tomorrow']); metric(audit,'day_plus_2_rows',by_day['day_plus_2']); metric(audit,'earliest_date',min([r.get('race_date') for r in rows], default='')); metric(audit,'latest_date',max([r.get('race_date') for r in rows], default='')); metric(audit,'rejected_rows',len(rejected)); metric(audit,'results_or_non_final_blocked_rows',len(rejected));
    for k,v in failures.items(): metric(audit,k,v)
    metric(audit,'readiness_verdict',verdict)
    if verdict=='PASS': metric(audit,'race_entry_fact_hash',sha(CANDIDATE))
    with AUDIT.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows(audit)
    lines=['EDGEIQ_RACE_ENTRY_FACT_V1_AUDIT',f'verdict={verdict}',f'candidate_rows={len(rows)}',f'rejected_rows={len(rejected)}',f'races={len(set(r.get("canonical_race_id") for r in rows))}',f'active_rows={by_decl.get("ACTIVE_ENTRY",0)}',f'scratched_rows={by_decl.get("SCRATCHED_ENTRY",0)}',f'emergency_rows={by_decl.get("EMERGENCY_ENTRY",0)}',f'today_rows={by_day["today"]}',f'tomorrow_rows={by_day["tomorrow"]}',f'day_plus_2_rows={by_day["day_plus_2"]}',f'failures={json.dumps(failures, sort_keys=True)}']
    if verdict=='PASS':
        if PRODUCTION.exists():
            backup=DATA/f"edgeiq_race_entry_fact_v1_PRE_PROMOTION_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            shutil.copy2(PRODUCTION, backup)
            lines.append(f'previous_production_backup={backup}')
        shutil.copy2(CANDIDATE, PRODUCTION)
        lines.append(f'promoted={PRODUCTION}')
        lines.append(f'race_entry_fact_hash={sha(PRODUCTION)}')
    else:
        lines.append('promoted=NO')
    REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines))
if __name__=='__main__': main()
