from pathlib import Path
import pandas as pd
D=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\public\data")
print("D87_CONTRACT HISTORICAL_PACE_REPLAY_SOURCE_GATE NO_MODEL")
for fn in ["edgeiq_historical_replay_v1.csv","edgeiq_racingcom_results_warehouse_v1.csv","edgeiq_historical_pace_advantage_replay_v1.csv"]:
 p=D/fn
 print("D87_FILE",fn,"EXISTS",p.exists())
 if not p.exists():continue
 h=pd.read_csv(p,nrows=0);print("D87_COLS",fn,list(h.columns))
 date=next((c for c in ["meeting_date","race_date","date"] if c in h.columns),None)
 use=[date] if date else []
 for c in ["inRun","in_run","tactical_style_pre_race_v1","style_starts_before_v1","pace_advantage_score_v1","pace_pressure_score_v1"]: 
  if c in h.columns:use.append(c)
 x=pd.read_csv(p,usecols=use,low_memory=False);dt=pd.to_datetime(x[date],errors="coerce") if date else pd.Series(pd.NaT,index=x.index)
 print("D87_RANGE",fn,str(dt.min()),str(dt.max()),"ROWS",len(x))
 for y in [2020,2021,2022,2023,2024]:print("D87_YEAR",fn,y,int(dt.dt.year.eq(y).sum()))
 for c in use[1:]:print("D87_COVERAGE",fn,c,float(x[c].notna().mean()),"N",int(x[c].notna().sum()))
print("D87_COMPLETE")
