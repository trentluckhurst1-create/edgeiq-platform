from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import re

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'public'/'data'
TERM_PREF=[DATA/'edgeiq_live_terminal_feed_v1.csv', DATA/'edgeiq_vic_live_terminal_feed_v1.csv']
CAND=DATA/'edgeiq_current_day_v7_1_candidate_from_live_board_v1.csv'
OUT=DATA/'edgeiq_live_terminal_feed_v7_1_current_day_candidate.csv'
AUD=DATA/'edgeiq_live_terminal_feed_v7_1_current_day_candidate_join_audit_v1.csv'
SUM=DATA/'edgeiq_live_terminal_feed_v7_1_current_day_candidate_join_summary_v1.csv'
REP=DATA/'edgeiq_live_terminal_feed_v7_1_current_day_candidate_join_report_v1.txt'
FIELDS=['edgeiq_probability_v7_current_day_candidate','edgeiq_fair_price_v7_calibrated_current_day_candidate','edgeiq_display_fair_price_v7_1_current_day_candidate','edgeiq_current_day_v7_1_probability_source','edgeiq_price_engine_version_candidate','edgeiq_display_price_engine_version_candidate','edgeiq_v7_1_current_day_feature_flag','edgeiq_v7_1_current_day_live_wired_flag','edgeiq_v7_1_current_day_production_changed','edgeiq_v7_1_current_day_join_key','edgeiq_v7_1_current_day_built_at']

def read(p): return pd.read_csv(p,dtype=str,keep_default_na=False,low_memory=False) if p.exists() else pd.DataFrame()
def pick():
    for p in TERM_PREF:
        if p.exists(): return p
    return None
def rel(p): return str(p.relative_to(BASE)) if p else 'MISSING'
def norm_date(v):
    raw='' if pd.isna(v) else str(v).strip(); dt=pd.to_datetime(raw, errors='coerce')
    return raw.upper() if pd.isna(dt) else dt.strftime('%Y-%m-%d')
def norm_track(v): return re.sub(r'\s+',' ',('' if pd.isna(v) else str(v)).upper().strip())
def norm_race(v):
    raw='' if pd.isna(v) else str(v).upper().strip(); m=re.search(r'\d+',raw); return str(int(m.group(0))) if m else raw
def norm_horse(v):
    raw=('' if pd.isna(v) else str(v)).upper().strip(); raw=re.sub(r'[^A-Z0-9\s]','',raw); return re.sub(r'\s+',' ',raw).strip()
def date_col(df):
    for c in ['race_date','meeting_date','date']:
        if c in df.columns: return c
    return None
def key(df):
    dc=date_col(df); d=df[dc].map(norm_date) if dc else pd.Series(['']*len(df), index=df.index)
    return d+'|'+df['track'].map(norm_track)+'|'+df['race_no'].map(norm_race)+'|'+df['horse'].map(norm_horse)
def metric_df(m): return pd.DataFrame([{'metric':k,'value':v} for k,v in m.items()])

term_path=pick(); term=read(term_path) if term_path else pd.DataFrame(); cand=read(CAND)
built_at=datetime.now(timezone.utc).isoformat(); blocked=False; reason=[]
for need in ['track','race_no','horse']:
    if need not in term.columns: blocked=True; reason.append('terminal missing '+need)
if date_col(term) is None: blocked=True; reason.append('terminal missing race_date/meeting_date')
if 'edgeiq_v7_1_current_day_join_key' not in cand.columns: blocked=True; reason.append('candidate missing edgeiq_v7_1_current_day_join_key')
if blocked:
    out=term.copy()
    for f in FIELDS:
        if f not in out.columns: out[f]=''
        else: out[f]=out[f].fillna('')
    out['edgeiq_v7_1_current_day_join_status']='BLOCKED_SCHEMA_MISSING'
    status='BLOCKED_SCHEMA_MISSING'
else:
    out=term.copy(); out['_join_key']=key(out)
    ccols=['edgeiq_v7_1_current_day_join_key']+[f for f in FIELDS if f in cand.columns and f!='edgeiq_v7_1_current_day_join_key']
    cmap=cand[ccols].drop_duplicates('edgeiq_v7_1_current_day_join_key', keep='first')
    out=out.merge(cmap, left_on='_join_key', right_on='edgeiq_v7_1_current_day_join_key', how='left', suffixes=('','_cand'))
    for f in FIELDS:
        if f not in out.columns: out[f]=''
        else: out[f]=out[f].fillna('')
    matched=out['edgeiq_probability_v7_current_day_candidate'].fillna('').astype(str).str.strip().ne('') | out['edgeiq_display_fair_price_v7_1_current_day_candidate'].fillna('').astype(str).str.strip().ne('')
    out['edgeiq_v7_1_current_day_join_status']=matched.map(lambda x:'MATCHED' if x else 'UNMATCHED')
    out['edgeiq_v7_1_current_day_feature_flag']=out['edgeiq_v7_1_current_day_feature_flag'].fillna('').replace('', 'OFF')
    out['edgeiq_v7_1_current_day_live_wired_flag']=out['edgeiq_v7_1_current_day_live_wired_flag'].fillna('').replace('', 'NO')
    out['edgeiq_v7_1_current_day_production_changed']=out['edgeiq_v7_1_current_day_production_changed'].fillna('').replace('', 'NO')
    out['edgeiq_v7_1_current_day_join_key']=out['_join_key']
    out=out.drop(columns=['_join_key'], errors='ignore')
    match_rate=round(int(matched.sum())/len(out)*100,4) if len(out) else 0
    if len(out)!=len(term): status='BLOCKED_ROW_COUNT_CHANGED'
    elif match_rate>=95: status='CURRENT_DAY_TERMINAL_JOIN_READY_FOR_REVIEW'
    else: status='CURRENT_DAY_TERMINAL_JOIN_BUILT_WITH_UNMATCHED_REVIEW_REQUIRED'

out.to_csv(OUT,index=False)
matched_rows=int((out.get('edgeiq_v7_1_current_day_join_status',pd.Series(dtype=str))=='MATCHED').sum()) if len(out) else 0
unmatched=len(out)-matched_rows
match_rate=round(matched_rows/len(out)*100,4) if len(out) else 0
feature=','.join(sorted(out.get('edgeiq_v7_1_current_day_feature_flag',pd.Series([''])).astype(str).unique())) if len(out) else ''
livewired=','.join(sorted(out.get('edgeiq_v7_1_current_day_live_wired_flag',pd.Series([''])).astype(str).unique())) if len(out) else ''
prod=','.join(sorted(out.get('edgeiq_v7_1_current_day_production_changed',pd.Series([''])).astype(str).unique())) if len(out) else ''
metrics={'built_at':built_at,'terminal_source_file_used':rel(term_path),'candidate_source_file_used':rel(CAND),'terminal_rows':len(term),'candidate_rows':len(cand),'output_rows':len(out),'matched_rows':matched_rows,'unmatched_rows':unmatched,'match_rate_pct':match_rate,'feature_flag_values':feature,'live_wired_values':livewired,'production_changed_values':prod,'duplicate_terminal_keys':int(key(term).duplicated(keep=False).sum()) if not blocked and len(term) else 0,'duplicate_candidate_keys':int(cand['edgeiq_v7_1_current_day_join_key'].duplicated(keep=False).sum()) if 'edgeiq_v7_1_current_day_join_key' in cand.columns else 0,'status':status}
metric_df(metrics).to_csv(SUM,index=False)
audit=pd.DataFrame({'join_key':out.get('edgeiq_v7_1_current_day_join_key',pd.Series(['']*len(out))),'track':out['track'] if 'track' in out.columns else '','race_no':out['race_no'] if 'race_no' in out.columns else '','horse':out['horse'] if 'horse' in out.columns else '','join_status':out.get('edgeiq_v7_1_current_day_join_status',pd.Series(['']*len(out))),'reason':out.get('edgeiq_v7_1_current_day_join_status',pd.Series(['']*len(out))).map(lambda x:'JOINED_ON_CURRENT_DAY_KEY' if x=='MATCHED' else 'NO_CURRENT_DAY_CANDIDATE_MATCH')})
audit.to_csv(AUD,index=False)
report=f'''EDGEiQ LIVE TERMINAL FEED V7.1 CURRENT-DAY CANDIDATE JOIN V1

- Candidate only.
- No live wiring.
- No production change.
- Feature flag OFF.
- Existing terminal columns preserved.
- Candidate columns appended only.
- Terminal source: {rel(term_path)}
- Candidate source: {rel(CAND)}
- Terminal rows: {len(term)}
- Output rows: {len(out)}
- Matched rows: {matched_rows}
- Unmatched rows: {unmatched}
- Match rate pct: {match_rate}
- Status: {status}

Review required before any wiring.
'''
REP.write_text(report,encoding='utf-8')
print(metric_df(metrics).to_string(index=False)); print(report)


