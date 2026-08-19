from __future__ import annotations
import csv,json,re,hashlib
from collections import Counter,defaultdict
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'; CONFIG=ROOT/'config'/'performance-intelligence'; DOC=ROOT/'docs'/'victoria-live-recovery-v4'
CROSS=CONFIG/'edgeiq_racing_australia_horse_identity_crosswalk_v1.csv'; MAP=CONFIG/'edgeiq_horse_performance_identity_map_v1.csv'; RATING=DATA/'edgeiq_performance_rating_base_fact_v1.csv'; OBS=DATA/'edgeiq_horse_performance_observation_fact_v1.csv'; REJ=DATA/'edgeiq_horse_performance_observation_fact_v1_rejections.csv'; HPR=DATA/'edgeiq_performance_normalisation_parameter_fact_v1.csv'
def text(v): return str(v if v is not None else '').strip()
def read(p):
    if not p.exists(): return []
    with p.open('r',encoding='utf-8-sig',newline='') as h: return list(csv.DictReader(h))
def write_csv(p,rows,fields):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8',newline='') as h:
        w=csv.DictWriter(h,fieldnames=fields,lineterminator='\n'); w.writeheader(); [w.writerow({f:text(r.get(f,'')) for f in fields}) for r in rows]
def write_json(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def sha_file(p): return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ''
def main():
    cross=read(CROSS); imap=read(MAP); ratings=[r for r in read(RATING) if text(r.get('race_date'))>='2026-07-20']; obs=[r for r in read(OBS) if text(r.get('race_date'))>='2026-07-20']; rej=[r for r in read(REJ) if text(r.get('race_date'))>='2026-07-20']
    methods={text(r.get('match_method')) for r in cross}; forbidden={'FUZZY_AUTO','TRAINER_ONLY','NAME_PREFIX','NAME_SUBSTRING','PHONETIC_AUTO','MANUAL_UNEVIDENCED'}
    source_ids=[text(r.get('source_horse_id')) for r in cross]
    checks=[]
    def add(name,ok,detail): checks.append({'check':name,'status':'PASS' if ok else 'FAIL','detail':json.dumps(detail,sort_keys=True)[:2000]})
    add('crosswalk_exists', bool(cross), {'rows':len(cross)})
    add('source_horse_ids_retained', all(source_ids), {'rows':len(cross),'nonblank':sum(1 for x in source_ids if x)})
    add('no_fuzzy_auto_promotion', not methods.intersection(forbidden), {'methods':sorted(methods)})
    add('source_id_unique_canonical', all(c==1 for c in Counter((r.get('source_system'),r.get('source_horse_id'),r.get('canonical_horse_id')) for r in cross).values()), {'duplicate_triples':[]})
    multi=defaultdict(set)
    for r in cross: multi[(r.get('source_system'),r.get('source_horse_id'))].add(r.get('canonical_horse_id'))
    add('no_source_id_to_multiple_canonical', all(len(v)==1 for v in multi.values()), {'conflicts':{str(k):list(v) for k,v in multi.items() if len(v)>1}})
    approved_names={text(r.get('source_horse_name')).upper() for r in imap if text(r.get('identity_status'))=='APPROVED'}
    rating_names={text(r.get('winner_horse_name')).upper() for r in ratings}
    add('current_rating_winners_approved', rating_names.issubset(approved_names), {'missing':sorted(rating_names-approved_names)})
    add('partial_safe_observation_processing', len(ratings)==len(obs)+len(rej), {'rating_rows':len(ratings),'observations':len(obs),'rejections':len(rej)})
    add('identity_rejection_evidence_retained', REJ.exists(), {'path':str(REJ.relative_to(ROOT)),'rows':len(rej)})
    add('post_cutoff_observations', len(obs)>0, {'post_cutoff_observations':len(obs)})
    ch=[r for r in cross if text(r.get('source_horse_name')).upper()=='CHIGURH']
    add('chigurh_resolved', len(ch)==1 and text(ch[0].get('source_horse_id'))=='34054013730', ch)
    status='PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL'
    fields=['check','status','detail']; write_csv(DOC/'EDGEIQ_CURRENT_HORSE_IDENTITY_GOVERNANCE_AUDIT.csv',checks,fields); write_json(DOC/'EDGEIQ_CURRENT_HORSE_IDENTITY_GOVERNANCE_AUDIT.json',{'status':status,'checks':checks,'counts':{'crosswalk_rows':len(cross),'identity_map_rows':len(imap),'post_cutoff_ratings':len(ratings),'post_cutoff_observations':len(obs),'identity_rejections':len(rej)},'hpr_norm_a_v1_sha256':sha_file(HPR)})
    print(json.dumps({'status':status,'crosswalk_rows':len(cross),'post_cutoff_observations':len(obs),'identity_rejections':len(rej)},indent=2)); return 0 if status=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
