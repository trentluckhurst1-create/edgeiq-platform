from __future__ import annotations
import csv,json
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'; DOC=ROOT/'docs'/'victoria-live-recovery-v4'
def text(v): return str(v if v is not None else '').strip()
def read(p):
    if not p.exists(): return []
    with p.open('r',encoding='utf-8-sig',newline='') as h: return list(csv.DictReader(h))
def write_csv(p,rows,fields):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8',newline='') as h:
        w=csv.DictWriter(h,fieldnames=fields,lineterminator='\n'); w.writeheader(); [w.writerow({f:text(r.get(f,'')) for f in fields}) for r in rows]
def write_json(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def write_text(p,s): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s if s.endswith('\n') else s+'\n',encoding='utf-8')
def post(rows,fields=('race_date','rating_as_of_date','aggregate_as_of_date')):
    out=[]
    for r in rows:
        d=''
        for f in fields:
            if text(r.get(f)): d=text(r.get(f)); break
        if d>='2026-07-20': out.append(r)
    return out
def latest(rows,fields=('race_date','rating_as_of_date','aggregate_as_of_date')):
    vals=[]
    for r in rows:
        for f in fields:
            if text(r.get(f)): vals.append(text(r.get(f))); break
    return max(vals) if vals else ''
def main():
    obs=read(DATA/'edgeiq_horse_performance_observation_fact_v1.csv'); ag=read(DATA/'edgeiq_horse_performance_aggregate_fact_v1.csv'); rt=read(DATA/'edgeiq_horse_performance_rating_fact_v1.csv'); snap=read(DATA/'edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv'); epi=read(DATA/'edgeiq_race_entry_epi_fact_v1.csv'); pbase=read(DATA/'edgeiq_performance_rating_base_fact_v1.csv'); params=read(DATA/'edgeiq_horse_performance_aggregation_parameter_fact_v1.csv')
    po,pa,pr,ps,pe,pp=[post(x) for x in [obs,ag,rt,snap,epi,pbase]]
    minobs=next((text(r.get('minimum_observations')) for r in params if text(r.get('parameter_status'))=='AVAILABLE'),'')
    obs_by_horse={}
    for r in po: obs_by_horse[text(r.get('canonical_horse_id'))]=obs_by_horse.get(text(r.get('canonical_horse_id')),0)+1
    below=bool(po) and not pa and minobs and all(v<int(minobs) for v in obs_by_horse.values())
    if pe: status='PASS_VICTORIA_LIVE'
    elif ps: status='BLOCKED_EPI'
    elif pr: status='BLOCKED_SNAPSHOTS'
    elif pa: status='BLOCKED_HORSE_RATINGS'
    elif below: status='BLOCKED_HORSE_AGGREGATES'
    elif po: status='BLOCKED_HORSE_AGGREGATES'
    else: status='BLOCKED_HORSE_IDENTITY_EVIDENCE'
    rows=[
      {'stage':'PERFORMANCE_RATING_BASE','post_cutoff_rows':len(pp),'latest_date':latest(pbase),'status':'PASS' if pp else 'FAIL','blocker':''},
      {'stage':'HORSE_OBSERVATIONS','post_cutoff_rows':len(po),'latest_date':latest(obs),'status':'PASS' if po else 'FAIL','blocker':'' if po else 'NO_APPROVED_IDENTITIES'},
      {'stage':'HORSE_AGGREGATES','post_cutoff_rows':len(pa),'latest_date':latest(ag),'status':'PASS' if pa else 'BLOCKED','blocker':'MINIMUM_OBSERVATIONS_NOT_MET' if below else ''},
      {'stage':'HORSE_RATINGS','post_cutoff_rows':len(pr),'latest_date':latest(rt,('rating_as_of_date',)),'status':'PASS' if pr else 'BLOCKED','blocker':'NO_AGGREGATES'},
      {'stage':'SNAPSHOTS','post_cutoff_rows':len(ps),'latest_date':latest(snap),'status':'PASS' if ps else 'BLOCKED','blocker':'NO_HORSE_RATINGS'},
      {'stage':'EPI','post_cutoff_rows':len(pe),'latest_date':latest(epi),'status':'PASS' if pe else 'BLOCKED','blocker':'NO_SNAPSHOTS_OR_COMPONENTS'},
    ]
    write_csv(DOC/'EDGEIQ_VICTORIA_RATINGS_EPI_COMPLETION.csv',rows,'stage post_cutoff_rows latest_date status blocker'.split())
    payload={'status':status,'post_cutoff':{'performance_rating_base':len(pp),'horse_observations':len(po),'horse_aggregates':len(pa),'horse_ratings':len(pr),'snapshots':len(ps),'epi':len(pe)},'minimum_observations_required':minobs,'observed_horse_counts':obs_by_horse,'latest':{'observation':latest(obs),'rating':latest(rt,('rating_as_of_date',)),'epi':latest(epi)}}
    write_json(DOC/'EDGEIQ_VICTORIA_RATINGS_EPI_COMPLETION.json',payload)
    write_text(DOC/'EDGEIQ_VICTORIA_RATINGS_EPI_COMPLETION.md','# EDGEiQ Victoria Ratings EPI Completion V4\n\n'+f"Status: `{status}`\n\n"+'\n'.join(f"- {r['stage']}: {r['post_cutoff_rows']} {r['status']} {r['blocker']}" for r in rows))
    print(json.dumps(payload,indent=2)); return 0 if status in {'PASS_VICTORIA_LIVE','BLOCKED_HORSE_AGGREGATES','BLOCKED_HORSE_RATINGS','BLOCKED_SNAPSHOTS','BLOCKED_EPI'} else 1
if __name__=='__main__': raise SystemExit(main())
