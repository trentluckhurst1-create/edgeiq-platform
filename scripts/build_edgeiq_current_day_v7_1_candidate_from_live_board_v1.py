from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import re

BASE = Path(__file__).resolve().parents[1]
DATA = BASE/'public'/'data'
LIVE_PREF=[DATA/'edgeiq_live_runner_board_governed_v1.csv', DATA/'edgeiq_live_runner_board_v1.csv']
SOURCE_SUM=DATA/'edgeiq_current_day_v7_1_source_columns_v1_summary.csv'
OUT=DATA/'edgeiq_current_day_v7_1_candidate_from_live_board_v1.csv'
SUM=DATA/'edgeiq_current_day_v7_1_candidate_from_live_board_v1_summary.csv'
AUD=DATA/'edgeiq_current_day_v7_1_candidate_from_live_board_v1_audit.csv'
REP=DATA/'edgeiq_current_day_v7_1_candidate_from_live_board_v1_report.txt'
TEMP=6.0

def read(p): return pd.read_csv(p, dtype=str, keep_default_na=False, low_memory=False) if p.exists() else pd.DataFrame()
def pick_live():
    for p in LIVE_PREF:
        if p.exists(): return p
    return None
def rel(p): return str(p.relative_to(BASE)) if p else 'MISSING'
def norm_date(v):
    raw='' if pd.isna(v) else str(v).strip()
    if not raw: return ''
    dt=pd.to_datetime(raw, errors='coerce')
    if pd.isna(dt): return raw.upper()
    return dt.strftime('%Y-%m-%d')
def norm_track(v): return re.sub(r'\s+',' ',('' if pd.isna(v) else str(v)).upper().strip())
def norm_race(v):
    raw='' if pd.isna(v) else str(v).upper().strip(); m=re.search(r'\d+',raw)
    return str(int(m.group(0))) if m else raw
def norm_horse(v):
    raw=('' if pd.isna(v) else str(v)).upper().strip(); raw=re.sub(r'[^A-Z0-9\s]','',raw); return re.sub(r'\s+',' ',raw).strip()
def date_col(df):
    for c in ['race_date','meeting_date','date']:
        if c in df.columns: return c
    return None
def join_key(df):
    dc=date_col(df)
    d=df[dc].map(norm_date) if dc else pd.Series(['']*len(df), index=df.index)
    t=df['track'].map(norm_track) if 'track' in df.columns else pd.Series(['']*len(df), index=df.index)
    r=df['race_no'].map(norm_race) if 'race_no' in df.columns else pd.Series(['']*len(df), index=df.index)
    h=df['horse'].map(norm_horse) if 'horse' in df.columns else pd.Series(['']*len(df), index=df.index)
    return d+'|'+t+'|'+r+'|'+h
def race_key(df):
    dc=date_col(df)
    d=df[dc].map(norm_date) if dc else pd.Series(['']*len(df), index=df.index)
    t=df['track'].map(norm_track) if 'track' in df.columns else pd.Series(['']*len(df), index=df.index)
    r=df['race_no'].map(norm_race) if 'race_no' in df.columns else pd.Series(['']*len(df), index=df.index)
    return d+'|'+t+'|'+r
def get_summary_value(metric):
    s=read(SOURCE_SUM)
    if s.empty: return ''
    hit=s[s['metric']==metric]
    return '' if hit.empty else str(hit.iloc[0]['value'])
def classify_source(col, df):
    if not col or col not in df.columns: return 'NONE'
    lc=col.lower()
    vals=pd.to_numeric(df[col].replace('', pd.NA), errors='coerce')
    if vals.notna().sum()==0: return 'NONE'
    if 'rank' in lc: return 'RANK'
    if lc in ['win_pct','probability','edgeiq_probability'] or 'probability' in lc or 'win_pct' in lc: return 'PROBABILITY'
    return 'RATING'
def display_mult(rank):
    if rank==1: return 1.00
    if rank==2: return 1.05
    if rank==3: return 1.15
    if rank<=5: return 1.30
    if rank<=8: return 1.55
    return 1.85

live_path=pick_live(); live=read(live_path) if live_path else pd.DataFrame()
built_at=datetime.now(timezone.utc).isoformat()
source_col=get_summary_value('recommended_primary_input_column')
if not source_col or source_col not in live.columns:
    for c in ['total_rating_points','projected_rating_V6_1_RESEARCH','projected_rating_v5_2','dfs_form_rating','tech_form_rating','win_pct','V6_1_RESEARCH_price_rank']:
        if c in live.columns:
            source_col=c; break

out=live.copy()
out['edgeiq_v7_1_current_day_join_key']=join_key(out) if not out.empty else ''
out['_edgeiq_race_key_v7_1_current_day']=race_key(out) if not out.empty else ''
source_type=classify_source(source_col, out)
probs=pd.Series(np.nan, index=out.index, dtype=float)
source_status=pd.Series('', index=out.index, dtype=str)

for rk, idx in out.groupby('_edgeiq_race_key_v7_1_current_day', dropna=False).groups.items():
    ids=list(idx); n=len(ids)
    if n==0: continue
    if source_type=='RATING':
        vals=pd.to_numeric(out.loc[ids, source_col].replace('', pd.NA), errors='coerce')
        if vals.notna().sum()>=2 and float(vals.std(ddof=0))>0:
            filled=vals.fillna(float(vals.mean()))
            z=(filled-filled.mean())/filled.std(ddof=0)
            ez=np.exp(np.clip(z/TEMP, -50, 50))
            p=ez/ez.sum()
            probs.loc[ids]=p.values; source_status.loc[ids]=f'RATING_SOFTMAX_T6:{source_col}'
        else:
            probs.loc[ids]=1.0/n; source_status.loc[ids]='EQUAL_PROBABILITY_FALLBACK_SCHEMA_LIMITED'
    elif source_type=='PROBABILITY':
        vals=pd.to_numeric(out.loc[ids, source_col].replace('', pd.NA), errors='coerce').fillna(0.0)
        if vals.max()>1.0: vals=vals/100.0
        if vals.sum()>0:
            probs.loc[ids]=(vals/vals.sum()).values; source_status.loc[ids]=f'NORMALISED_EXISTING_PROBABILITY_INPUT:{source_col}'
        else:
            probs.loc[ids]=1.0/n; source_status.loc[ids]='EQUAL_PROBABILITY_FALLBACK_SCHEMA_LIMITED'
    elif source_type=='RANK':
        vals=pd.to_numeric(out.loc[ids, source_col].replace('', pd.NA), errors='coerce')
        vals=vals.where(vals>0)
        if vals.notna().sum()>0:
            weights=(1.0/vals.fillna(vals.max()+1)).replace([np.inf,-np.inf], np.nan).fillna(0.0)
            probs.loc[ids]=(weights/weights.sum()).values if weights.sum()>0 else 1.0/n
            source_status.loc[ids]=f'RANK_WEIGHTED_FALLBACK:{source_col}'
        else:
            probs.loc[ids]=1.0/n; source_status.loc[ids]='EQUAL_PROBABILITY_FALLBACK_SCHEMA_LIMITED'
    else:
        probs.loc[ids]=1.0/n; source_status.loc[ids]='EQUAL_PROBABILITY_FALLBACK_SCHEMA_LIMITED'

out['edgeiq_probability_v7_current_day_candidate']=probs.astype(float)
out['edgeiq_fair_price_v7_calibrated_current_day_candidate']=(1.0/out['edgeiq_probability_v7_current_day_candidate']).replace([np.inf,-np.inf], np.nan)
out['edgeiq_current_day_v7_1_probability_source']=source_status
out['edgeiq_price_engine_version_candidate']='V7_TEMPERATURE6_TAB_QUALITY_CURRENT_DAY'
out['edgeiq_display_price_engine_version_candidate']='V7_1_DISPLAY_FAIR_PRICE_LAYER_CURRENT_DAY'
out['edgeiq_v7_1_current_day_feature_flag']='OFF'
out['edgeiq_v7_1_current_day_live_wired_flag']='NO'
out['edgeiq_v7_1_current_day_production_changed']='NO'
out['edgeiq_v7_1_current_day_built_at']=built_at

# rank and display price with monotonic enforcement
out['__prob_rank']=out.groupby('_edgeiq_race_key_v7_1_current_day')['edgeiq_probability_v7_current_day_candidate'].rank(method='first', ascending=False).astype(int)
out['__base_display']=out['edgeiq_fair_price_v7_calibrated_current_day_candidate'] * out['__prob_rank'].map(display_mult)
out['__display']=out['__base_display'].clip(lower=1.01, upper=100.0)
for rk, idx in out.groupby('_edgeiq_race_key_v7_1_current_day').groups.items():
    order=out.loc[idx].sort_values('__prob_rank').index.tolist()
    last=1.01
    for i in order:
        val=float(out.at[i,'__display']) if pd.notna(out.at[i,'__display']) else last
        if val < last: val=last
        out.at[i,'__display']=min(max(val,1.01),100.0)
        last=out.at[i,'__display']
out['edgeiq_display_fair_price_v7_1_current_day_candidate']=out['__display']

# audits
race_sums=out.groupby('_edgeiq_race_key_v7_1_current_day')['edgeiq_probability_v7_current_day_candidate'].sum()
prob_ok=int(((race_sums-1.0).abs()<=0.0001).sum())
prob_bad=int(((race_sums-1.0).abs()>0.0001).sum())
rank_breaks=0; top_second=0
for rk, g in out.groupby('_edgeiq_race_key_v7_1_current_day'):
    gg=g.sort_values('__prob_rank')
    vals=gg['edgeiq_display_fair_price_v7_1_current_day_candidate'].astype(float).tolist()
    if any(vals[i] > vals[i+1] + 1e-9 for i in range(len(vals)-1)): rank_breaks += 1
    if len(vals)>=2 and vals[0] > vals[1] + 1e-9: top_second += 1
source_counts=out['edgeiq_current_day_v7_1_probability_source'].value_counts().to_dict()

if len(out)!=len(live): status='CURRENT_DAY_V7_1_CANDIDATE_BLOCKED_ROW_COUNT_CHANGED'
elif prob_bad>0: status='CURRENT_DAY_V7_1_CANDIDATE_BLOCKED_PROBABILITY_SUM_BAD'
elif rank_breaks>0: status='CURRENT_DAY_V7_1_CANDIDATE_BLOCKED_RANK_ORDER_BREAKS'
elif set(out['edgeiq_current_day_v7_1_probability_source'].unique())=={'EQUAL_PROBABILITY_FALLBACK_SCHEMA_LIMITED'}: status='CURRENT_DAY_V7_1_CANDIDATE_BUILT_EQUAL_PROB_FALLBACK_REVIEW_REQUIRED'
else: status='CURRENT_DAY_V7_1_CANDIDATE_BUILT_REVIEW_REQUIRED'

out.drop(columns=['_edgeiq_race_key_v7_1_current_day','__prob_rank','__base_display','__display'], errors='ignore').to_csv(OUT,index=False)
audit=pd.DataFrame([{
    'rows':len(out),'races':int(out['_edgeiq_race_key_v7_1_current_day'].nunique()),'probability_rows':int(out['edgeiq_probability_v7_current_day_candidate'].notna().sum()),'display_fair_rows':int(out['edgeiq_display_fair_price_v7_1_current_day_candidate'].notna().sum()),'probability_sum_ok_races':prob_ok,'probability_sum_bad_races':prob_bad,'min_probability':float(out['edgeiq_probability_v7_current_day_candidate'].min()),'max_probability':float(out['edgeiq_probability_v7_current_day_candidate'].max()),'min_calibrated_fair':float(out['edgeiq_fair_price_v7_calibrated_current_day_candidate'].min()),'max_calibrated_fair':float(out['edgeiq_fair_price_v7_calibrated_current_day_candidate'].max()),'min_display_fair':float(out['edgeiq_display_fair_price_v7_1_current_day_candidate'].min()),'max_display_fair':float(out['edgeiq_display_fair_price_v7_1_current_day_candidate'].max()),'rows_display_above_10':int((out['edgeiq_display_fair_price_v7_1_current_day_candidate']>10).sum()),'rows_display_above_20':int((out['edgeiq_display_fair_price_v7_1_current_day_candidate']>20).sum()),'rank_order_breaks':rank_breaks,'top_pick_longer_than_second':top_second,'null_display_rows':int(out['edgeiq_display_fair_price_v7_1_current_day_candidate'].isna().sum()),'source_path_counts':str(source_counts),'production_changed_values':','.join(sorted(out['edgeiq_v7_1_current_day_production_changed'].unique())),'live_wired_values':','.join(sorted(out['edgeiq_v7_1_current_day_live_wired_flag'].unique())),'feature_flag_values':','.join(sorted(out['edgeiq_v7_1_current_day_feature_flag'].unique())),'status':status
}])
audit.to_csv(AUD,index=False)
metrics={'built_at':built_at,'live_source_file_used':rel(live_path),'live_rows':len(live),'output_rows':len(out),'races':int(out['_edgeiq_race_key_v7_1_current_day'].nunique()),'source_column':source_col,'source_type':source_type,'probability_rows':int(out['edgeiq_probability_v7_current_day_candidate'].notna().sum()),'display_fair_rows':int(out['edgeiq_display_fair_price_v7_1_current_day_candidate'].notna().sum()),'probability_sum_ok_races':prob_ok,'probability_sum_bad_races':prob_bad,'rank_order_breaks':rank_breaks,'top_pick_longer_than_second':top_second,'min_display_fair':float(out['edgeiq_display_fair_price_v7_1_current_day_candidate'].min()),'max_display_fair':float(out['edgeiq_display_fair_price_v7_1_current_day_candidate'].max()),'source_path_counts':str(source_counts),'feature_flag_values':'OFF','live_wired_values':'NO','production_changed_values':'NO','status':status}
summary=pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]); summary.to_csv(SUM,index=False)
report=f'''EDGEiQ CURRENT-DAY V7.1 CANDIDATE FROM LIVE BOARD V1

- Candidate only.
- Source live board: {rel(live_path)}
- Rows: {len(out)}
- Races: {metrics['races']}
- Source column: {source_col}
- Source type: {source_type}
- Probability sum ok races: {prob_ok}
- Probability sum bad races: {prob_bad}
- Display fair range: {metrics['min_display_fair']} to {metrics['max_display_fair']}
- Rank order breaks: {rank_breaks}
- Top pick longer than second races: {top_second}
- Feature flag: OFF
- Live wired: NO
- Production changed: NO
- Status: {status}

This file proposes current-day V7 probability and V7.1 display fair-price fields only. It does not replace calibrated probability, existing fair_price, ui_fair_price, live_price, win_pct, or any production feed.
'''
REP.write_text(report,encoding='utf-8')
print(summary.to_string(index=False)); print(report)
