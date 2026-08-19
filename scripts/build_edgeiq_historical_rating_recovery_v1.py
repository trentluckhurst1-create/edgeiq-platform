import csv, os, re, collections, math
from datetime import datetime
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
DATA=os.path.join(ROOT,'public','data')
FORM=os.path.join(DATA,'edgeiq_form_enrichment_feed_v4.csv')
INV=os.path.join(DATA,'edgeiq_historical_rating_recovery_inventory_v1.csv')
OUT=os.path.join(DATA,'edgeiq_historical_rating_recovery_v1.csv')
SUM=os.path.join(DATA,'edgeiq_historical_rating_recovery_v1_summary.csv')
REP=os.path.join(DATA,'edgeiq_historical_rating_recovery_v1_report.txt')

def read_csv(path):
    with open(path,newline='',encoding='utf-8-sig',errors='replace') as f:
        r=csv.DictReader(f); return list(r), r.fieldnames or []
def blank(v): return v is None or str(v).strip()=='' or str(v).strip().upper() in {'--','N/A','NA','NULL','NONE','UNKNOWN','NAN'}
def norm_horse(v):
    s=str(v or '').upper().replace('�','')
    s=re.sub(r'\([^)]*\)',' ',s)
    s=re.sub(r'\b\d+E\b',' ',s)
    return re.sub(r'[^A-Z0-9]+','',s)
def clean_track(v): return re.sub(r'\s+',' ',str(v or '').upper().strip())
def clean_dist(v):
    s=str(v or '').strip()
    m=re.search(r'\d+(?:\.\d+)?',s)
    if not m: return ''
    return str(int(round(float(m.group(0)))))
def clean_date(v):
    s=str(v or '').strip()[:10]
    try: return datetime.fromisoformat(s).date().isoformat()
    except Exception: return ''
def first(row, cols):
    for c in cols:
        v=row.get(c,'')
        if not blank(v): return str(v).strip()
    return ''
def rating_value(row, cols):
    for c in cols:
        v=row.get(c,'')
        if blank(v): continue
        try:
            x=float(str(v).replace('$','').replace(',',''))
            # Exclude probability-like, rank-like, and impossible rating values.
            if 0 < x <= 130:
                return x,c
        except Exception:
            continue
    return None,''
def split_cols(s): return [x for x in str(s or '').split('|') if x]
def source_bucket(name):
    l=name.lower()
    if 'historical_run_ratings_master' in l: return 'HISTORICAL_RATING_WAREHOUSE'
    if 'historical_performance_rating' in l: return 'HISTORICAL_PERFORMANCE_RATING'
    if 'v5_1' in l: return 'V5_1_ARCHIVE'
    if 'v6_1' in l: return 'V6_1_RESEARCH_ARCHIVE'
    if 'projection' in l or 'projected' in l: return 'HISTORICAL_PROJECTION'
    if 'replay' in l: return 'REPLAY_ARCHIVE'
    if 'runner_board' in l or 'snapshot' in l: return 'RUNNER_BOARD_SNAPSHOT'
    if 'intelligence' in l: return 'INTELLIGENCE_SNAPSHOT'
    return 'OTHER_RATING_SOURCE'

form, form_cols=read_csv(FORM)
targets=[]
for r in form:
    horse_norm=norm_horse(r.get('horse_key') or r.get('horse'))
    for i in range(1,6):
        date=clean_date(r.get(f'last_start_{i}_date',''))
        if not date: continue
        if blank(r.get(f'last_start_{i}_rating','')):
            targets.append({'runner_key':r.get('runner_key',''),'horse':r.get('horse',''),'horse_norm':horse_norm,'run_index':str(i),'run_date':date,'track_norm':clean_track(r.get(f'last_start_{i}_track','')),'distance_norm':clean_dist(r.get(f'last_start_{i}_distance','')),'current_source':r.get(f'last_start_{i}_source','')})
target_lookup=collections.defaultdict(list)
for t in targets: target_lookup[(t['horse_norm'],t['run_date'])].append(t)
active_horses={t['horse_norm'] for t in targets}
active_dates={t['run_date'] for t in targets}
inv,_=read_csv(INV)
# Skip audits/summaries and tiny summary rows. Keep real archives.
candidates=[]
for r in inv:
    name=r['file']
    l=name.lower()
    if l.endswith('_summary.csv') or '_summary' in l or '_audit' in l or 'diagnostic' in l:
        continue
    if r.get('usable_for_recovery')!='YES': continue
    try: rows=int(float(r.get('rows') or 0))
    except Exception: rows=0
    if rows <= 1: continue
    candidates.append(r)
candidates.sort(key=lambda r:(int(float(r.get('priority') or 99)), -int(float(r.get('rows') or 0))))
# limit duplicate/checkpoint clones after primary names to keep pass efficient but broad
seen_stems=set(); filtered=[]
for r in candidates:
    stem=re.sub(r'_CHECKPOINT.*|_BACKUP.*|_WORKING.*|_PRE_.*','',r['file'],flags=re.I)
    if stem in seen_stems and len(filtered)>80:
        continue
    seen_stems.add(stem); filtered.append(r)
# keep enough breadth for archives/replay/snapshots
candidates=filtered[:180]

best={}
scan_stats=[]
for meta in candidates:
    file=meta['file']; path=os.path.join(DATA,file)
    horse_cols=split_cols(meta['horse_columns']); date_cols=split_cols(meta['date_columns']); track_cols=split_cols(meta['track_columns']); dist_cols=split_cols(meta['distance_columns']); rating_cols=split_cols(meta['rating_columns'])
    if not os.path.exists(path): continue
    matches=0; recovered_candidates=0
    try:
        with open(path,newline='',encoding='utf-8-sig',errors='replace') as f:
            reader=csv.DictReader(f)
            for row in reader:
                h=norm_horse(first(row,horse_cols))
                if h not in active_horses: continue
                d=clean_date(first(row,date_cols))
                if d not in active_dates: continue
                linked=target_lookup.get((h,d),[])
                if not linked: continue
                rv,col=rating_value(row,rating_cols)
                if rv is None: continue
                tr=clean_track(first(row,track_cols)); ds=clean_dist(first(row,dist_cols))
                for t in linked:
                    score=1000 - int(float(meta.get('priority') or 99))*50
                    if tr and t['track_norm'] and tr==t['track_norm']: score+=30
                    if ds and t['distance_norm'] and ds==t['distance_norm']: score+=30
                    if tr and t['track_norm'] and tr!=t['track_norm']: score-=10
                    if ds and t['distance_norm'] and ds!=t['distance_norm']: score-=10
                    key=(t['runner_key'],t['run_index'])
                    rec={'runner_key':t['runner_key'],'horse':t['horse'],'run_index':t['run_index'],'run_date':t['run_date'],'target_track':t['track_norm'],'target_distance':t['distance_norm'],'recovered_rating':f'{rv:.1f}','rating_column':col,'recovery_source_file':file,'recovery_source_bucket':source_bucket(file),'recovery_match_score':score,'source_track':tr,'source_distance':ds,'recovery_confidence':'HIGH' if score>=950 else 'MEDIUM' if score>=850 else 'LOW'}
                    if key not in best or score>best[key]['recovery_match_score']:
                        best[key]=rec
                        recovered_candidates+=1
                matches+=1
    except Exception:
        continue
    scan_stats.append({'file':file,'matches_seen':matches,'best_candidate_updates':recovered_candidates})

recoveries=list(best.values())
recoveries.sort(key=lambda r:(r['horse'],int(r['run_index'])))
fields=['runner_key','horse','run_index','run_date','target_track','target_distance','recovered_rating','rating_column','recovery_source_file','recovery_source_bucket','recovery_match_score','source_track','source_distance','recovery_confidence']
with open(OUT,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(recoveries)
source_counts=collections.Counter(r['recovery_source_bucket'] for r in recoveries)
summary=[{'metric':'missing_rating_targets','value':len(targets)},{'metric':'recovered_ratings','value':len(recoveries)},{'metric':'recovered_pct','value':f'{(len(recoveries)/max(1,len(targets))*100):.2f}'},{'metric':'still_missing','value':len(targets)-len(recoveries)},{'metric':'candidate_sources_scanned','value':len(candidates)}]
for k,v in source_counts.items(): summary.append({'metric':f'source_{k}','value':v})
summary += [{'metric':'pricing_maths_changed','value':'NO'},{'metric':'v6_1_changed','value':'NO'},{'metric':'v7_2g2_changed','value':'NO'}]
with open(SUM,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows(summary)
rep=['EDGEiQ HISTORICAL RATING RECOVERY V1',f'missing_rating_targets={len(targets)}',f'recovered_ratings={len(recoveries)}',f'recovered_pct={(len(recoveries)/max(1,len(targets))*100):.2f}',f'still_missing={len(targets)-len(recoveries)}','source_counts:']
for k,v in source_counts.most_common(): rep.append(f'- {k}: {v}')
rep += ['pricing_maths_changed=NO','v6_1_changed=NO','v7_2g2_changed=NO','status=HISTORICAL_RATING_RECOVERY_BUILT']
with open(REP,'w',encoding='utf-8') as f: f.write('\n'.join(rep)+'\n')
print('\n'.join(rep))
