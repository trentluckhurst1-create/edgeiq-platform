from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'public'/'data'
PACK=DATA/'edgeiq_v7_2g2_human_review_pack_v1.csv'
LIVE=DATA/'edgeiq_live_runner_board_governed_v1.csv'
STAGE=DATA/'edgeiq_v7_2g2_staging_checkpoint_v1.csv'
OUT=DATA/'edgeiq_v7_2g2_final_visual_review_summary_v1.csv'
REP=DATA/'edgeiq_v7_2g2_final_visual_review_summary_v1_report.txt'

def read(p): return pd.read_csv(p,dtype=str,keep_default_na=False,low_memory=False) if p.exists() else pd.DataFrame()
def vals(df,c): return ','.join(sorted(df[c].fillna('').astype(str).unique())) if c in df.columns and len(df) else ''
def mrow(df): return df.iloc[0].to_dict() if len(df) else {}
pack=read(PACK); live=read(LIVE); stage=read(STAGE)
if pack.empty or live.empty or stage.empty:
    status='FINAL_VISUAL_REVIEW_PACK_BLOCKED_MISSING_INPUTS'
    metrics={'built_at':datetime.now(timezone.utc).isoformat(),'status':status,'review_rows':len(pack),'live_rows':len(live)}
else:
    for c in ['abs_delta','pct_delta']:
        pack[c]=pd.to_numeric(pack[c],errors='coerce')
    high=pack[pack['high_risk_flag'].eq('YES')]
    flag=vals(live,'edgeiq_v7_2g2_feature_flag')
    fallback=vals(live,'edgeiq_v7_2g2_active_price_source_shadow')
    preview_rows=int(live.get('edgeiq_v7_2g2_on_preview_display_fair_price',pd.Series(dtype=str)).astype(str).str.strip().ne('').sum())
    status='FINAL_VISUAL_REVIEW_PACK_READY' if flag=='OFF' and preview_rows==len(live) and fallback=='PRODUCTION_FALLBACK_FEATURE_FLAG_OFF' else 'FINAL_VISUAL_REVIEW_PACK_BLOCKED'
    metrics={'built_at':datetime.now(timezone.utc).isoformat(),'review_rows':len(pack),'high_risk_races':high[['race_date','track','race_no']].drop_duplicates().shape[0],'live_rows':len(live),'feature_flag_values':flag,'active_pricing_source_values':fallback,'on_preview_rows':preview_rows,'activation':'NO','status':status}
pd.DataFrame([metrics]).to_csv(OUT,index=False)
if not pack.empty:
    top_abs=pack.sort_values('abs_delta',ascending=False).head(30)
    top_pct=pack.sort_values('pct_delta',ascending=False).head(30)
    high_races=pack[pack['high_risk_flag'].eq('YES')][['race_date','track','race_no']].drop_duplicates()
    abs_lines='\n'.join([f"- {r.track} R{r.race_no} {r.horse}: prod {r.production_display_price}, G2 {r.v7_2g2_display_price}, abs {r.abs_delta}, pct {r.pct_delta}" for r in top_abs.itertuples(index=False)])
    pct_lines='\n'.join([f"- {r.track} R{r.race_no} {r.horse}: prod {r.production_display_price}, G2 {r.v7_2g2_display_price}, abs {r.abs_delta}, pct {r.pct_delta}" for r in top_pct.itertuples(index=False)])
    high_lines='\n'.join([f"- {r.track} R{r.race_no} ({r.race_date})" for r in high_races.itertuples(index=False)]) or '- None.'
else:
    abs_lines=pct_lines=high_lines='- None.'
report=f'''EDGEiQ V7.2G2 FINAL VISUAL REVIEW SUMMARY V1

- Status: {metrics.get('status')}
- Review rows: {metrics.get('review_rows')}
- High-risk races: {metrics.get('high_risk_races','')}
- Feature flag values: {metrics.get('feature_flag_values','')}
- Active pricing source: {metrics.get('active_pricing_source_values','')}
- ON-preview rows: {metrics.get('on_preview_rows','')}
- Activation: NO

High-risk races:
{high_lines}

Top 30 by absolute delta:
{abs_lines}

Top 30 by pct delta:
{pct_lines}
'''
REP.write_text(report,encoding='utf-8')
print(pd.DataFrame([metrics]).to_string(index=False)); print(report)
