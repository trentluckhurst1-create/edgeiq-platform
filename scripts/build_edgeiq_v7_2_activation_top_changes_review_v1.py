from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'public'/'data'
INP=DATA/'edgeiq_v7_2_activation_side_by_side_v1.csv'
RACE=DATA/'edgeiq_v7_2_activation_race_level_changes_v1.csv'
OUT=DATA/'edgeiq_v7_2_activation_top_changes_review_v1.csv'
SUM=DATA/'edgeiq_v7_2_activation_top_changes_review_v1_summary.csv'
REP=DATA/'edgeiq_v7_2_activation_top_changes_review_v1_report.txt'

df=pd.read_csv(INP,dtype=str,keep_default_na=False,low_memory=False) if INP.exists() else pd.DataFrame()
races=pd.read_csv(RACE,dtype=str,keep_default_na=False,low_memory=False) if RACE.exists() else pd.DataFrame()
if not df.empty:
    for c in ['production_display_price_used','v7_2_display_price_used','absolute_display_price_delta','pct_display_price_delta','production_rank_in_race','v7_2_rank_in_race','rank_delta']:
        df[c]=pd.to_numeric(df[c], errors='coerce')
    top_changed_keys=set()
    if not races.empty:
        for r in races[races['top_pick_changed'].eq('YES')].itertuples(index=False):
            top_changed_keys.add(f'{r.race_date}|{r.track}|{r.race_no}')
    def flag(row):
        key=f"{row['race_date']}|{row['track']}|{row['race_no']}"
        if key in top_changed_keys and (row['production_rank_in_race']==1 or row['v7_2_rank_in_race']==1): return 'REVIEW_TOP_PICK_CHANGE'
        if abs(row['rank_delta'])>=2: return 'REVIEW_MAJOR_RANK_MOVE'
        if row['pct_display_price_delta']>=30: return 'REVIEW_MAJOR_PRICE_MOVE'
        return 'REVIEW_NORMAL'
    df['review_flag']=df.apply(flag, axis=1)
    df['_sort_score']=df['absolute_display_price_delta'].fillna(0)+df['pct_display_price_delta'].fillna(0)/10+df['rank_delta'].abs().fillna(0)*5
    cols=['race_date','track','race_no','horse','production_display_price_used','v7_2_display_price_used','absolute_display_price_delta','pct_display_price_delta','production_rank_in_race','v7_2_rank_in_race','rank_delta','v7_2_probability_source','review_flag']
    out=df.sort_values('_sort_score', ascending=False).head(100)[cols]
else:
    out=pd.DataFrame()
out.to_csv(OUT,index=False)
if out.empty:
    metrics={'built_at':datetime.now(timezone.utc).isoformat(),'rows':0,'status':'TOP_CHANGES_BLOCKED_NO_INPUT'}
else:
    suspicious=int((pd.to_numeric(out['v7_2_display_price_used'], errors='coerce')>=100).sum() + (pd.to_numeric(out['v7_2_display_price_used'], errors='coerce')<1.01).sum())
    metrics={'built_at':datetime.now(timezone.utc).isoformat(),'rows':len(out),'review_top_pick_change_rows':int(out['review_flag'].eq('REVIEW_TOP_PICK_CHANGE').sum()),'review_major_rank_move_rows':int(out['review_flag'].eq('REVIEW_MAJOR_RANK_MOVE').sum()),'review_major_price_move_rows':int(out['review_flag'].eq('REVIEW_MAJOR_PRICE_MOVE').sum()),'review_normal_rows':int(out['review_flag'].eq('REVIEW_NORMAL').sum()),'suspicious_price_rows':suspicious,'status':'TOP_CHANGES_REVIEW_BUILT_REVIEW_REQUIRED'}
pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_csv(SUM,index=False)
big=out.head(20) if not out.empty else pd.DataFrame()
lines='\n'.join([f"- {r.track} R{r.race_no} {r.horse}: prod {r.production_display_price_used}, V7.2 {r.v7_2_display_price_used}, pct {r.pct_display_price_delta}, rank {r.production_rank_in_race}->{r.v7_2_rank_in_race}, {r.review_flag}" for r in big.itertuples(index=False)]) or '- None.'
susp=out[pd.to_numeric(out['v7_2_display_price_used'], errors='coerce')>=100] if not out.empty else pd.DataFrame()
susp_lines='\n'.join([f"- {r.track} R{r.race_no} {r.horse}: V7.2 display {r.v7_2_display_price_used}" for r in susp.head(20).itertuples(index=False)]) or '- None.'
report=f'''EDGEiQ V7.2 ACTIVATION TOP CHANGES REVIEW V1

- Status: {metrics.get('status')}
- No activation occurred.
- Rows: {metrics.get('rows')}
- Top-pick change rows: {metrics.get('review_top_pick_change_rows','')}
- Major rank move rows: {metrics.get('review_major_rank_move_rows','')}
- Major price move rows: {metrics.get('review_major_price_move_rows','')}
- Suspicious price rows: {metrics.get('suspicious_price_rows','')}

Biggest 20 changes:
{lines}

Suspicious prices:
{susp_lines}
'''
REP.write_text(report,encoding='utf-8')
print(pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_string(index=False))
print(report)
