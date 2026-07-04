from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import re

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'public'/'data'
LIVE=DATA/'edgeiq_live_runner_board_governed_v1.csv'
CAND=DATA/'edgeiq_live_runner_board_v7_2g2_activation_candidate.csv'
GATE=DATA/'edgeiq_v7_2g2_activation_safety_gate_v1_summary.csv'
OUTBOARD=DATA/'edgeiq_live_runner_board_v7_2g2_staging_candidate.csv'
OUT=DATA/'edgeiq_v7_2g2_staging_candidate_v1.csv'
SUM=DATA/'edgeiq_v7_2g2_staging_candidate_v1_summary.csv'
REP=DATA/'edgeiq_v7_2g2_staging_candidate_v1_report.txt'

def m(path):
    if not path.exists(): return {}
    df=pd.read_csv(path,dtype=str,keep_default_na=False)
    return dict(zip(df['metric'],df['value'])) if {'metric','value'}.issubset(df.columns) else {}
def norm_horse(s): return str(s).upper().strip()
def key(df): return df['race_date'].astype(str)+'|'+df['track'].astype(str).str.upper().str.strip()+'|'+df['race_no'].astype(str)+'|'+df['horse'].astype(str).str.upper().str.replace(r'[^A-Z0-9\s]','',regex=True).str.replace(r'\s+',' ',regex=True).str.strip()
def first_series(df,cols):
    out=pd.Series(['']*len(df),index=df.index,dtype=object)
    for c in cols:
        if c in df.columns:
            vals=df[c].fillna('').astype(str)
            out=out.where(out.astype(str).str.strip().ne(''),vals)
    return out.fillna('').astype(str)

live=pd.read_csv(LIVE,dtype=str,keep_default_na=False,low_memory=False) if LIVE.exists() else pd.DataFrame()
cand=pd.read_csv(CAND,dtype=str,keep_default_na=False,low_memory=False) if CAND.exists() else pd.DataFrame()
gate=m(GATE)
if gate.get('status')!='V7_2G2_ACTIVATION_SAFETY_GATE_PASS_HUMAN_APPROVAL_REQUIRED' or live.empty or cand.empty:
    out=live.copy(); status='V7_2G2_STAGING_CANDIDATE_BLOCKED'
else:
    live=live.copy(); cand=cand.copy(); live['join_key_g2']=key(live); cand['join_key_g2']=key(cand)
    ccols=['join_key_g2','edgeiq_v7_2g2_probability','edgeiq_v7_2g2_guarded_display_fair_price','edgeiq_v7_2g2_strategy','edgeiq_v7_2g2_guardrail_reason']
    out=live.merge(cand[ccols].drop_duplicates('join_key_g2'),on='join_key_g2',how='left')
    out['edgeiq_v7_2g2_feature_flag']='OFF'
    out['edgeiq_v7_2g2_live_wired_flag']='NO'
    out['edgeiq_v7_2g2_production_changed']='NO'
    fallback=first_series(out,['ui_fair_price','display_fair_price','fair_price','rated_price','live_price'])
    out['edgeiq_v7_2g2_active_display_fair_price_shadow']=fallback
    out['edgeiq_v7_2g2_active_price_source_shadow']='PRODUCTION_FALLBACK_FEATURE_FLAG_OFF'
    out['edgeiq_v7_2g2_on_preview_display_fair_price']=out['edgeiq_v7_2g2_guarded_display_fair_price']
    out['edgeiq_v7_2g2_on_preview_price_source']='V7_2G2_ON_PREVIEW_CANDIDATE'
    out=out.drop(columns=['join_key_g2'],errors='ignore')
    status='V7_2G2_STAGING_CANDIDATE_BUILT_FLAG_OFF' if len(out)==len(live) else 'V7_2G2_STAGING_CANDIDATE_BLOCKED_ROW_MISMATCH'
out.to_csv(OUTBOARD,index=False)
out.to_csv(OUT,index=False)
preview=int(out.get('edgeiq_v7_2g2_on_preview_display_fair_price',pd.Series(dtype=str)).astype(str).str.strip().ne('').sum()) if len(out) else 0
metrics={'built_at':datetime.now(timezone.utc).isoformat(),'rows':len(out),'source_live_rows':len(live),'on_preview_rows':preview,'feature_flag_values':'OFF' if len(out) else '','live_wired_values':'NO' if len(out) else '','production_changed_values':'NO' if len(out) else '','status':status}
pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_csv(SUM,index=False)
report=f'''EDGEiQ V7.2G2 STAGING CANDIDATE V1

- Status: {status}
- Rows: {len(out)}
- ON-preview rows: {preview}
- Feature flag: OFF
- Live wired: NO
- Production changed: NO
- Active shadow remains production fallback.
- Do not overwrite live board from this script.
'''
REP.write_text(report,encoding='utf-8')
print(pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_string(index=False)); print(report)
