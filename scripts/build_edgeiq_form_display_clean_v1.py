import csv, os, re, shutil, collections
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
DATA=os.path.join(ROOT,'public','data')
FORM=os.path.join(DATA,'edgeiq_form_enrichment_feed_v4.csv')
OUT=os.path.join(DATA,'edgeiq_form_display_clean_v1.csv')
SUM=os.path.join(DATA,'edgeiq_form_display_clean_v1_summary.csv')
REP=os.path.join(DATA,'edgeiq_form_display_clean_v1_report.txt')
BACKUP=os.path.join(DATA,'edgeiq_form_enrichment_feed_v4_DISPLAY_CLEAN_BACKUP_20260628.csv')
BAD={'','--','N/A','NA','NULL','NONE','UNKNOWN','NAN','NOT LOADED','NO_CLASS'}

def blank(v): return v is None or str(v).strip().upper() in BAD

def num(v):
    try:
        if blank(v): return None
        m=re.search(r'-?\d+(?:\.\d+)?',str(v))
        return float(m.group(0)) if m else None
    except Exception: return None

def fmt_num(x, digits=1):
    if x is None: return ''
    return f'{x:.{digits}f}'

def position_display(v):
    x=num(v)
    if x is None or x<=0 or x>30: return '--','BAD_POSITION_SANITISED'
    return str(int(x)),'OK'

def sp_display(v):
    x=num(v)
    if x is None or x<=1.0: return '--','BAD_SP_SANITISED'
    return f'{x:.2f}'.rstrip('0').rstrip('.'),'OK'

def margin_display(finish, margin):
    f=num(finish); m=num(margin)
    if m is None: return '--','BAD_MARGIN_SANITISED'
    if f==1:
        if m>0: return (f'Won by {m:.2f}L' if m < 0.1 else f'Won by {m:.1f}L'),'OK'
        return 'Won','ZERO_MARGIN_SANITISED'
    if m>0: return (f'Beaten {m:.2f}L' if m < 0.1 else f'Beaten {m:.1f}L'),'OK'
    return '--','ZERO_MARGIN_SANITISED'

def class_display(v):
    if blank(v): return 'UNKNOWN','CLASS_UNKNOWN_SANITISED'
    return str(v).strip(),'OK'

def condition_display(v):
    if blank(v) or str(v).strip() in {'0','0.0'}: return 'UNKNOWN','CONDITION_UNKNOWN_SANITISED'
    return str(v).strip().upper().replace('GOOD ', 'GOOD').replace('SOFT ', 'SOFT').replace('HEAVY ', 'HEAVY'),'OK'

def distance_display(v):
    x=num(v)
    if x is None or x<=0: return '--','DISTANCE_UNKNOWN_SANITISED'
    return f'{int(round(x))}m','OK'

def rating_display(v):
    x=num(v)
    if x is None: return '--','MISSING_RATING'
    return f'{x:.1f}','OK'

def customer_source(value):
    raw=str(value or '').upper()
    labels=[]
    def add(x):
        if x not in labels: labels.append(x)
    for part in re.split(r'[;|]',raw):
        p=part.strip()
        if not p: continue
        if 'OTHER_RATING_SOURCE' in p or 'RATING_DATE_MATCH' in p or 'RECOVERED' in p: add('Recovered Rating')
        elif 'RESULTS_WAREHOUSE' in p: add('Results Warehouse')
        elif 'RUNNER_BOARD_SNAPSHOT' in p: add('Board Snapshot')
        elif 'REPLAY_ARCHIVE' in p: add('Replay Archive')
        elif 'V6_1_RESEARCH_ARCHIVE' in p or 'V6.1 ARCHIVE' in p: add('V6.1 Archive')
        elif 'V6_1_RESEARCH_HISTORY' in p: add('V6.1 Rated History')
        elif 'INTELLIGENCE_SNAPSHOT' in p: add('Intelligence Snapshot')
        elif 'HISTORY_MASTER' in p or 'HISTORICAL_RATING_WAREHOUSE' in p: add('History Master')
        elif 'HISTORICAL_FORM_TABLE' in p: add('Historical Form')
        elif 'RATED_HISTORY' in p: add('Historical Rating')
        elif 'RESULT_HISTORY' in p: add('Results History')
        elif 'CONTEXT' in p: add('Context Only')
    return ' + '.join(labels[:2]) if labels else 'Not Enough Evidence'

def status_display(status):
    s=str(status or '').upper().replace('_',' ')
    if 'OK' in s: return 'OK HISTORY'
    if 'PARTIAL' in s: return 'PARTIAL HISTORY'
    if 'CONTEXT' in s: return 'CONTEXT ONLY'
    if 'GAP' in s: return 'SOURCE GAP'
    return 'UNKNOWN'

def trend_display(*vals):
    raw=' '.join(str(v or '').upper().replace('_',' ') for v in vals)
    if 'IMPROV' in raw or 'PEAK' in raw: return 'IMPROVING'
    if 'REGRESS' in raw or 'DECLIN' in raw: return 'REGRESSING'
    if 'LIMITED' in raw: return 'LIMITED'
    if 'CONTEXT' in raw: return 'CONTEXT ONLY'
    if 'RECENT FORM LOADED' in raw or 'HOLD' in raw or 'FULL HISTORY' in raw or 'OK' in raw: return 'HOLDING FORM'
    if 'PARTIAL' in raw: return 'PARTIAL EVIDENCE'
    return 'UNKNOWN'

def score_band(v):
    x=num(v)
    if x is None: return '--','LIMITED'
    if x>=85: return f'{x:.0f}','ELITE'
    if x>=75: return f'{x:.0f}','STRONG'
    if x>=60: return f'{x:.0f}','AVERAGE'
    if x>=45: return f'{x:.0f}','RISK'
    return f'{x:.0f}','POOR'

def evidence_display(status, rating_lines):
    st=status_display(status)
    n=num(rating_lines)
    if st=='OK HISTORY' and (n or 0)>=3: return 'HIGH'
    if st in {'OK HISTORY','PARTIAL HISTORY'}: return 'MEDIUM'
    return 'LOW'

def profile_score_display(row, prefix):
    keys=[f'{prefix}_fit_score',f'score_{prefix}',f'edgeiq_score_{prefix}_v3',f'{prefix}_score']
    val=None
    for k in keys:
        val=num(row.get(k,''))
        if val is not None: break
    if val is None or val<=0: return 'Not Enough Evidence'
    band='Strong' if val>=75 else 'Neutral' if val>=60 else 'Watch' if val>=45 else 'Risk'
    return f'score {val:.0f} | {band}'

rows=[]; counts=collections.Counter()
with open(FORM,newline='',encoding='utf-8-sig',errors='replace') as f:
    reader=csv.DictReader(f); cols=reader.fieldnames or []
    for r in reader:
        score_val=r.get('form_peak_rating_last5') or r.get('form_avg_rating_last5') or r.get('form_last_start_rating')
        score,band=score_band(score_val)
        r['form_status_display']=status_display(r.get('form_truth_status'))
        r['form_trend_display']=trend_display(r.get('form_trend'),r.get('rating_trend'),r.get('form_signal'),r.get('form_data_quality'))
        r['form_data_quality_display']=r.get('form_data_quality','').replace('_',' ').upper() or r['form_status_display']
        r['form_evidence_display']=evidence_display(r.get('form_truth_status'),r.get('form_v4_rating_line_count'))
        r['form_score_display']=score
        r['form_score_band_display']=band
        r['distance_profile_display']=profile_score_display(r,'distance')
        r['condition_profile_display']=profile_score_display(r,'condition')
        r['class_profile_display']=profile_score_display(r,'class')
        for i in range(1,6):
            p=f'last_start_{i}_'
            pos,posflag=position_display(r.get(p+'finish') or r.get(p+'finishing_position'))
            sp,spflag=sp_display(r.get(p+'sp') or r.get(p+'SP'))
            margin,marginflag=margin_display(pos, r.get(p+'margin') or r.get(p+'beaten_margin'))
            cls,clsflag=class_display(r.get(p+'class'))
            cond,condflag=condition_display(r.get(p+'condition'))
            dist,distflag=distance_display(r.get(p+'distance'))
            rating,ratingflag=rating_display(r.get(p+'rating'))
            comment=customer_source((r.get(p+'source','')+';'+r.get(p+'reason','')).strip(';'))
            r[p+'position_display']=pos; r[p+'sp_display']=sp; r[p+'margin_display']=margin; r[p+'class_display']=cls; r[p+'condition_display']=cond; r[p+'distance_display']=dist; r[p+'rating_display']=rating; r[p+'comment_display']=comment
            for flag in [posflag,spflag,marginflag,clsflag,condflag,distflag,ratingflag]:
                if flag!='OK': counts[flag]+=1
            if comment!='Not Enough Evidence': counts['SOURCE_LABEL_CLEANED']+=1
        rows.append(r)

if not os.path.exists(BACKUP): shutil.copyfile(FORM,BACKUP)
new_cols=list(cols)
for c in rows[0].keys():
    if c not in new_cols: new_cols.append(c)
with open(FORM,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=new_cols); w.writeheader(); w.writerows([{c:r.get(c,'') for c in new_cols} for r in rows])
with open(OUT,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=new_cols); w.writeheader(); w.writerows([{c:r.get(c,'') for c in new_cols} for r in rows])
summary=[{'metric':'rows','value':len(rows)}]+[{'metric':k,'value':v} for k,v in counts.most_common()]+[{'metric':'pricing_maths_changed','value':'NO'},{'metric':'v6_1_changed','value':'NO'},{'metric':'v7_2g2_changed','value':'NO'}]
with open(SUM,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows(summary)
rep=['EDGEiQ FORM DISPLAY CLEAN V1',f'rows={len(rows)}']+[f'{k}={v}' for k,v in counts.most_common()]+['pricing_maths_changed=NO','v6_1_changed=NO','v7_2g2_changed=NO','status=FORM_DISPLAY_CLEAN_FIELDS_BUILT']
with open(REP,'w',encoding='utf-8') as f: f.write('\n'.join(rep)+'\n')
print('\n'.join(rep))

