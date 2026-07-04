from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'public'/'data'
INP=DATA/'edgeiq_v7_2_activation_side_by_side_v1.csv'
OUT=DATA/'edgeiq_v7_2_activation_race_level_changes_v1.csv'
SUM=DATA/'edgeiq_v7_2_activation_race_level_changes_v1_summary.csv'
REP=DATA/'edgeiq_v7_2_activation_race_level_changes_v1_report.txt'

df=pd.read_csv(INP,dtype=str,keep_default_na=False,low_memory=False) if INP.exists() else pd.DataFrame()
rows=[]
if not df.empty:
    for c in ['production_display_price_used','v7_2_display_price_used','absolute_display_price_delta','pct_display_price_delta']:
        df[c]=pd.to_numeric(df[c], errors='coerce')
    df['decision_change_bool']=df['decision_change_flag'].eq('YES')
    df['large_extreme_bool']=df['price_movement_band'].isin(['LARGE','EXTREME'])
    for (race_date,track,race_no), g in df.groupby(['race_date','track','race_no'], dropna=False):
        prod_top=g.sort_values('production_display_price_used', ascending=True, kind='mergesort').iloc[0]
        v72_top=g.sort_values('v7_2_display_price_used', ascending=True, kind='mergesort').iloc[0]
        large=int(g['large_extreme_bool'].sum())
        top_changed='YES' if str(prod_top['horse']) != str(v72_top['horse']) else 'NO'
        if top_changed=='NO' and large<=1: risk='LOW'
        elif top_changed=='NO' and large<=3: risk='MEDIUM'
        else: risk='HIGH'
        rows.append({'race_date':race_date,'track':track,'race_no':race_no,'runners':len(g),'production_top_pick':prod_top['horse'],'production_top_price':prod_top['production_display_price_used'],'v7_2_top_pick':v72_top['horse'],'v7_2_top_price':v72_top['v7_2_display_price_used'],'top_pick_changed':top_changed,'avg_abs_price_delta':round(float(g['absolute_display_price_delta'].mean()),4),'max_abs_price_delta':round(float(g['absolute_display_price_delta'].max()),4),'decision_change_rows':int(g['decision_change_bool'].sum()),'large_or_extreme_rows':large,'risk_band':risk})
out=pd.DataFrame(rows)
out.to_csv(OUT,index=False)
if out.empty:
    metrics={'built_at':datetime.now(timezone.utc).isoformat(),'races':0,'status':'RACE_LEVEL_CHANGES_BLOCKED_NO_INPUT'}
else:
    metrics={'built_at':datetime.now(timezone.utc).isoformat(),'races':len(out),'top_pick_changed_races':int(out['top_pick_changed'].eq('YES').sum()),'top_pick_changed_pct':round(float(out['top_pick_changed'].eq('YES').mean()*100),4),'high_risk_races':int(out['risk_band'].eq('HIGH').sum()),'high_risk_pct':round(float(out['risk_band'].eq('HIGH').mean()*100),4),'medium_risk_races':int(out['risk_band'].eq('MEDIUM').sum()),'low_risk_races':int(out['risk_band'].eq('LOW').sum()),'avg_race_delta':round(float(out['avg_abs_price_delta'].mean()),4),'max_race_delta':round(float(out['max_abs_price_delta'].max()),4),'status':'RACE_LEVEL_CHANGES_BUILT_REVIEW_REQUIRED'}
pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_csv(SUM,index=False)
high=out[out.get('risk_band',pd.Series(dtype=str)).eq('HIGH')].sort_values(['large_or_extreme_rows','max_abs_price_delta'], ascending=[False,False]).head(15) if not out.empty else pd.DataFrame()
changed=out[out.get('top_pick_changed',pd.Series(dtype=str)).eq('YES')].head(15) if not out.empty else pd.DataFrame()
high_lines='\n'.join([f"- {r.track} R{r.race_no}: risk {r.risk_band}, top {r.production_top_pick} -> {r.v7_2_top_pick}, large/extreme {r.large_or_extreme_rows}, max delta {r.max_abs_price_delta}" for r in high.itertuples(index=False)]) or '- None.'
changed_lines='\n'.join([f"- {r.track} R{r.race_no}: {r.production_top_pick} -> {r.v7_2_top_pick}" for r in changed.itertuples(index=False)]) or '- None.'
report=f'''EDGEiQ V7.2 ACTIVATION RACE LEVEL CHANGES V1

- Status: {metrics.get('status')}
- No activation occurred.
- Races: {metrics.get('races')}
- Top-pick changed races: {metrics.get('top_pick_changed_races','')}
- High-risk races: {metrics.get('high_risk_races','')}
- Medium-risk races: {metrics.get('medium_risk_races','')}
- Low-risk races: {metrics.get('low_risk_races','')}
- Avg race delta: {metrics.get('avg_race_delta','')}
- Max race delta: {metrics.get('max_race_delta','')}

Highest risk races:
{high_lines}

Top-pick changes:
{changed_lines}
'''
REP.write_text(report,encoding='utf-8')
print(pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_string(index=False))
print(report)
