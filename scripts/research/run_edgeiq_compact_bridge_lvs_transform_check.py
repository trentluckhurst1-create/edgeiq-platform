"""Compare Stage011 LVS features to the previous run's target LVS within each horse.

This checks original training transforms directly, without assuming _horse equals
canonical_horse_id. Only rows strictly before 2025 are used.
"""
import argparse
import numpy as np
import pandas as pd
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--bridge",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv")
 a=p.parse_args()
 d=pd.read_csv(a.bridge,dtype="string")
 required=["_horse","_race","race_date","target_lvs","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5"]
 if not set(required).issubset(d):raise RuntimeError("STOP bridge schema missing")
 d["dt"]=pd.to_datetime(d.race_date,errors="coerce")
 d=d[d.dt.lt(pd.Timestamp("2025-01-01"))].copy()
 if d.duplicated(["_race","_horse"]).any():raise RuntimeError("STOP duplicate race horse")
 d["v"]=pd.to_numeric(d.target_lvs,errors="coerce")
 d=d.sort_values(["_horse","dt","_race"],kind="stable")
 errs={k:[] for k in required[4:]}
 rows=0
 ambiguous=0
 for horse,g in d.groupby("_horse",sort=False):
  history=[]
  for _,r in g.iterrows():
   if history and history[-1][0]==r.dt:
    ambiguous+=1
    history=[]
   if history:
    v=np.asarray([x[1] for x in history],dtype=float)
    last=v[-5:]
    calc={"lvs_last1":v[-1],"lvs_mean3":np.mean(v[-3:]),"lvs_mean5":np.mean(last),
          "lvs_median5":np.median(last),"lvs_std5":np.std(last,ddof=0),
          "lvs_peak":np.max(v),"lvs_worst5":np.min(last)}
    rows+=1
    for k,pred in calc.items():
     actual=pd.to_numeric(pd.Series([r[k]]),errors="coerce").iloc[0]
     if pd.notna(actual):errs[k].append(abs(float(actual)-float(pred)))
   if pd.notna(r.v):history.append((r.dt,float(r.v)))
 print("ROWS_COMPARED",rows,"SAME_DATE_AMBIGUITIES",ambiguous)
 for k,e in errs.items():
  print(k,"N",len(e),"EXACT",sum(x<1e-8 for x in e),"MAX_ABS",max(e) if e else None,
        "MATCH_RATE",round(sum(x<1e-8 for x in e)/len(e),6) if e else None)
 print("CAUTION: compact bridge contains a selected subset of historical runs; gaps may prevent exact reconstruction")
 print("NO_MODEL_SCORING_OR_PROMOTION")
if __name__=="__main__":main()
