from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'public'/'data'
INP=DATA/'edgeiq_live_runner_board_v7_2g2_staging_candidate.csv'
OUT=DATA/'edgeiq_v7_2g2_staging_candidate_audit_v1.csv'
SUM=DATA/'edgeiq_v7_2g2_staging_candidate_audit_v1_summary.csv'
REP=DATA/'edgeiq_v7_2g2_staging_candidate_audit_v1_report.txt'

def vals(df,c): return ','.join(sorted(df[c].fillna('').astype(str).unique())) if c in df.columns and len(df) else ''
def num(df,c): return pd.to_numeric(df[c].replace('',pd.NA),errors='coerce') if c in df.columns else pd.Series([pd.NA]*len(df))

df=pd.read_csv(INP,dtype=str,keep_default_na=False,low_memory=False) if INP.exists() else pd.DataFrame()
if df.empty:
    metrics={'built_at':datetime.now(timezone.utc).isoformat(),'rows':0,'status':'V7_2G2_STAGING_CANDIDATE_AUDIT_BLOCKED'}; detail=pd.DataFrame()
else:
    prices=num(df,'edgeiq_v7_2g2_on_preview_display_fair_price')
    df['race_key']=df['race_date'].astype(str)+'|'+df['track'].astype(str)+'|'+df['race_no'].astype(str)
    rb=tls=0
    for rk,g in df.groupby('race_key'):
        p=num(g,'edgeiq_v7_2g2_on_preview_display_fair_price')
        vals_sorted=p.sort_values(kind='mergesort').tolist()
        if any(vals_sorted[i]>vals_sorted[i+1]+1e-9 for i in range(len(vals_sorted)-1)): rb+=1
        if len(vals_sorted)>=2 and vals_sorted[0]>vals_sorted[1]+1e-9: tls+=1
    fallback=df.get('edgeiq_v7_2g2_active_price_source_shadow',pd.Series(dtype=str)).eq('PRODUCTION_FALLBACK_FEATURE_FLAG_OFF').sum()
    old=all(c in df.columns for c in ['fair_price','ui_fair_price','live_price','win_pct'])
    checks={'rows_378':len(df)==378,'feature_flag_off':vals(df,'edgeiq_v7_2g2_feature_flag')=='OFF','live_wired_no':vals(df,'edgeiq_v7_2g2_live_wired_flag')=='NO','production_changed_no':vals(df,'edgeiq_v7_2g2_production_changed')=='NO','active_shadow_fallback':fallback==len(df),'on_preview_populated':prices.notna().sum()==len(df),'old_price_fields_present':old,'no_null_guarded':prices.notna().sum()==len(df),'min_gte_1_01':float(prices.min())>=1.01,'max_lte_50':float(prices.max())<=50,'rank_order_breaks_zero':rb==0,'top_pick_longer_than_second_zero':tls==0}
    status='V7_2G2_STAGING_CANDIDATE_AUDIT_PASS' if all(checks.values()) else 'V7_2G2_STAGING_CANDIDATE_AUDIT_BLOCKED'
    detail=pd.DataFrame([{'check':k,'pass':'YES' if v else 'NO'} for k,v in checks.items()])
    metrics={'built_at':datetime.now(timezone.utc).isoformat(),'rows':len(df),'feature_flag_values':vals(df,'edgeiq_v7_2g2_feature_flag'),'live_wired_values':vals(df,'edgeiq_v7_2g2_live_wired_flag'),'production_changed_values':vals(df,'edgeiq_v7_2g2_production_changed'),'active_shadow_fallback_rows':int(fallback),'on_preview_rows':int(prices.notna().sum()),'min_preview_price':float(prices.min()),'max_preview_price':float(prices.max()),'rank_order_breaks':rb,'top_pick_longer_than_second':tls,'status':status}
detail.to_csv(OUT,index=False)
pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_csv(SUM,index=False)
report=f'''EDGEiQ V7.2G2 STAGING CANDIDATE AUDIT V1

- Status: {metrics.get('status')}
- Rows: {metrics.get('rows')}
- Feature flag values: {metrics.get('feature_flag_values','')}
- Live wired values: {metrics.get('live_wired_values','')}
- Production changed values: {metrics.get('production_changed_values','')}
- Active shadow fallback rows: {metrics.get('active_shadow_fallback_rows','')}
- ON-preview rows: {metrics.get('on_preview_rows','')}
- Preview price range: {metrics.get('min_preview_price','')} to {metrics.get('max_preview_price','')}
- Rank order breaks: {metrics.get('rank_order_breaks','')}
- Top pick longer than second: {metrics.get('top_pick_longer_than_second','')}
'''
REP.write_text(report,encoding='utf-8')
print(pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_string(index=False)); print(report)
