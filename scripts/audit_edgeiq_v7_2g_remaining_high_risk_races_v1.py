from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'public'/'data'
G=DATA/'edgeiq_v7_2g_side_by_side_review_v1.csv'
RAW_RACE=DATA/'edgeiq_v7_2_activation_race_level_changes_v1.csv'
OUT=DATA/'edgeiq_v7_2g_remaining_high_risk_races_v1.csv'
SUM=DATA/'edgeiq_v7_2g_remaining_high_risk_races_v1_summary.csv'
REP=DATA/'edgeiq_v7_2g_remaining_high_risk_races_v1_report.txt'

def band_risk(top_changed, large_rows, dec_ratio):
    if top_changed=='YES': return 'HIGH','TOP_PICK_CHANGED'
    if large_rows>3: return 'HIGH','LARGE_EXTREME_ROWS_GT_3'
    if dec_ratio>0.35: return 'HIGH','DECISION_CHANGE_RATIO_GT_35'
    if large_rows>1 or dec_ratio>0.2: return 'MEDIUM','MODERATE_CHANGE_LOAD'
    return 'LOW','LOW_CHANGE_LOAD'

df=pd.read_csv(G,dtype=str,keep_default_na=False,low_memory=False) if G.exists() else pd.DataFrame()
if df.empty:
    out=pd.DataFrame(); metrics={'built_at':datetime.now(timezone.utc).isoformat(),'races':0,'status':'REMAINING_HIGH_RISK_BLOCKED_NO_INPUT'}
else:
    for c in ['production_display','raw_v7_2_display','guarded_v7_2g_display','production_rank','raw_v7_2_rank','v7_2g_rank']:
        df[c]=pd.to_numeric(df[c], errors='coerce')
    rows=[]
    for (date,track,race),g in df.groupby(['race_date','track','race_no'], dropna=False):
        prod_top=g.sort_values('production_display', ascending=True, kind='mergesort').iloc[0]
        raw_top=g.sort_values('raw_v7_2_display', ascending=True, kind='mergesort').iloc[0]
        g_top=g.sort_values('guarded_v7_2g_display', ascending=True, kind='mergesort').iloc[0]
        raw_large=int(g['raw_movement_band'].isin(['LARGE','EXTREME']).sum())
        g_large=int(g['guarded_movement_band'].isin(['LARGE','EXTREME']).sum())
        raw_dec=int(g['raw_decision_change_flag'].eq('YES').sum())
        g_dec=int(g['guarded_decision_change_flag'].eq('YES').sum())
        top_raw='YES' if prod_top['horse']!=raw_top['horse'] else 'NO'
        top_g='YES' if prod_top['horse']!=g_top['horse'] else 'NO'
        risk,reason=band_risk(top_g,g_large,g_dec/len(g) if len(g) else 0)
        rows.append({'race_date':date,'track':track,'race_no':race,'runners':len(g),'production_top_pick':prod_top['horse'],'raw_v7_2_top_pick':raw_top['horse'],'v7_2g_top_pick':g_top['horse'],'production_top_price':prod_top['production_display'],'raw_v7_2_top_price':raw_top['raw_v7_2_display'],'v7_2g_top_price':g_top['guarded_v7_2g_display'],'top_pick_changed_raw':top_raw,'top_pick_changed_v7_2g':top_g,'raw_large_extreme_rows':raw_large,'v7_2g_large_extreme_rows':g_large,'raw_decision_change_rows':raw_dec,'v7_2g_decision_change_rows':g_dec,'avg_abs_delta_v7_2g':round(float((g['guarded_v7_2g_display']-g['production_display']).abs().mean()),4),'max_abs_delta_v7_2g':round(float((g['guarded_v7_2g_display']-g['production_display']).abs().max()),4),'current_risk_band':risk,'high_risk_reason':reason})
    out=pd.DataFrame(rows).sort_values(['current_risk_band','v7_2g_large_extreme_rows','v7_2g_decision_change_rows'], ascending=[False,False,False])
    high=int(out['current_risk_band'].eq('HIGH').sum())
    top=int(out['top_pick_changed_v7_2g'].eq('YES').sum())
    allowed=int(len(out)*0.2)
    metrics={'built_at':datetime.now(timezone.utc).isoformat(),'races':len(out),'high_risk_races':high,'top_pick_changed_races':top,'high_risk_threshold_allowed':allowed,'status':'REMAINING_HIGH_RISK_RACES_BUILT_REVIEW_REQUIRED'}
out.to_csv(OUT,index=False)
pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_csv(SUM,index=False)
high_lines='\n'.join([f"- {r.track} R{r.race_no}: {r.current_risk_band}, {r.high_risk_reason}, top {r.production_top_pick}->{r.v7_2g_top_pick}, large/extreme {r.v7_2g_large_extreme_rows}, decision {r.v7_2g_decision_change_rows}/{r.runners}" for r in out[out.get('current_risk_band',pd.Series(dtype=str)).eq('HIGH')].itertuples(index=False)]) if not out.empty else '- None.'
report=f'''EDGEiQ V7.2G REMAINING HIGH-RISK RACES V1

- Status: {metrics.get('status')}
- Races: {metrics.get('races')}
- High-risk races: {metrics.get('high_risk_races')}
- Top-pick changed races: {metrics.get('top_pick_changed_races')}
- High-risk threshold allowed: {metrics.get('high_risk_threshold_allowed')}

High-risk races:
{high_lines}
'''
REP.write_text(report,encoding='utf-8')
print(pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_string(index=False))
print(report)
