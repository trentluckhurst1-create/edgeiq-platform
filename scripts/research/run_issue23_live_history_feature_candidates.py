"""Build strictly prior historical candidate features for linked live runners.
Research only: no scoring, no model promotion, no sealed evaluation.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--warehouse",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245B_WAREHOUSE_RUNNER_LVS.csv")
 p.add_argument("--linkage",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\issue23_live_features\ISSUE23_LAB245B_HISTORY_LINKAGE.csv")
 p.add_argument("--date",default="2026-10-14")
 p.add_argument("--venue",default="Caulfield")
 p.add_argument("--out",default=r"C:\EDGEIQ_ISSUE23\outputs\research\ISSUE23_LIVE_HISTORY_FEATURE_CANDIDATES_V1.csv")
 a=p.parse_args()
 l=pd.read_csv(a.linkage,dtype="string")
 l=l[l.race_date.eq(a.date)&l.venue.str.casefold().eq(a.venue.casefold())].copy()
 if l.empty or l.canonical_horse_id.isna().any() or l.duplicated(["race_date","race_no","canonical_horse_id"]).any():
  raise RuntimeError("STOP invalid live linkage")
 cols=["canonical_race_id","canonical_horse_id","race_date","runner_lvs","distance_metres","field_size","finish_position","finish_margin"]
 w=pd.read_csv(a.warehouse,usecols=cols,dtype="string")
 w["dt"]=pd.to_datetime(w.race_date,errors="coerce")
 cutoff=pd.Timestamp(a.date)
 w=w[w.dt.notna()&w.dt.lt(cutoff)&w.canonical_horse_id.isin(l.canonical_horse_id)].copy()
 if w.duplicated(["canonical_race_id","canonical_horse_id"]).any():raise RuntimeError("STOP duplicate warehouse observations")
 w=w.sort_values(["canonical_horse_id","dt","canonical_race_id"],kind="stable")
 groups=dict(tuple(w.groupby("canonical_horse_id",sort=False)))
 rows=[]
 for row in l.itertuples(index=False):
  h=groups.get(row.canonical_horse_id)
  result={"race_date":row.race_date,"race_no":row.race_no,"horse_name":row.horse_name,
          "canonical_horse_id":row.canonical_horse_id,"history_rows":0,"latest_history_date":pd.NA}
  for name in ["lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5",
               "margin_mean5","margin_std5","margin_worst5","margin_last1","margin_last2",
               "last_distance","margin_change_l1_l2","margin_per_runner_last1","margin_per_runner_last2",
               "days_since_last","clean_finish_mean5","clean_last_finish","clean_last_won","clean_last_top3","clean_finish_hist_n"]:
   result[name]=np.nan
  if h is not None and not h.empty:
   if h.dt.duplicated().any():raise RuntimeError("STOP ambiguous same-day history for "+str(row.canonical_horse_id))
   result["history_rows"]=len(h)
   result["latest_history_date"]=str(h.dt.max().date())
   v=pd.to_numeric(h.runner_lvs,errors="coerce").dropna().to_numpy(float)
   if len(v):
    t=v[-5:]
    result.update(lvs_last1=v[-1],lvs_mean3=float(v[-3:].mean()),lvs_mean5=float(t.mean()),
      lvs_median5=float(np.median(t)),lvs_std5=float(np.std(t,ddof=0)),
      lvs_peak=float(v.max()),lvs_worst5=float(t.min()))
   m=pd.to_numeric(h.finish_margin,errors="coerce").dropna().to_numpy(float)
   if len(m):
    t=m[-5:]
    result.update(margin_mean5=float(t.mean()),margin_std5=float(np.std(t,ddof=0)),
      margin_worst5=float(t.max()),margin_last1=float(m[-1]))
    if len(m)>1:result.update(margin_last2=float(m[-2]),margin_change_l1_l2=float(m[-1]-m[-2]))
   # Exact original LAB245B bridge denominator: max(prior race field_size - 1, 1).\n   # Missing prior-race field sizes remain NaN; never substitute current field size.
   valid=h.copy()
   valid["margin_num"]=pd.to_numeric(valid.finish_margin,errors="coerce")
   valid["field_num"]=pd.to_numeric(valid.field_size,errors="coerce")
   valid=valid[valid.margin_num.notna()&valid.field_num.gt(0)]
   if len(valid):
    result["margin_per_runner_last1"]=float(valid.iloc[-1].margin_num/max(valid.iloc[-1].field_num-1,1))
    if len(valid)>1:result["margin_per_runner_last2"]=float(valid.iloc[-2].margin_num/max(valid.iloc[-2].field_num-1,1))
   dist=pd.to_numeric(h.distance_metres,errors="coerce").dropna()
   if len(dist):result["last_distance"]=float(dist.iloc[-1])
   result["days_since_last"]=int((cutoff-h.dt.max()).days)
   finish=pd.to_numeric(h.finish_position,errors="coerce").dropna().to_numpy(float)
   if len(finish):
    t=finish[-5:]
    result.update(clean_finish_mean5=float(t.mean()),clean_last_finish=float(t[-1]),
      clean_last_won=float(t[-1]==1),clean_last_top3=float(t[-1]<=3),clean_finish_hist_n=float(len(t)))
  result["feature_status"]="RESEARCH_ONLY_UNVERIFIED_NON_LVS_TRANSFORMS_DO_NOT_SCORE"
  rows.append(result)
 out=pd.DataFrame(rows)
 target=Path(a.out)
 if target.exists():raise RuntimeError("STOP immutable output exists; specify --out")
 target.parent.mkdir(parents=True,exist_ok=True)
 out.to_csv(target,index=False)
 print("LINKED_RUNNERS",len(l),"CANDIDATE_ROWS",len(out))
 print("HISTORY_ROWS_AVAILABLE",int(out.history_rows.gt(0).sum()))
 print("FIELD_SIZE_SOURCE_NON_NULL",int(w.field_size.notna().sum()))
 print("FIELD_SIZE_SOURCE_NUMERIC_POSITIVE",int(pd.to_numeric(w.field_size,errors="coerce").gt(0).sum()))
 print("MARGIN_SOURCE_NUMERIC",int(pd.to_numeric(w.finish_margin,errors="coerce").notna().sum()))
 print("MARGIN_AND_FIELD_SIZE_USABLE",int((pd.to_numeric(w.field_size,errors="coerce").gt(0)&pd.to_numeric(w.finish_margin,errors="coerce").notna()).sum()))
 print("WAREHOUSE_LATEST",str(w.dt.max().date()) if len(w) else "NONE")
 for c in ["margin_per_runner_last1","margin_per_runner_last2","margin_mean5","clean_finish_mean5"]:
  print("FEATURE",c,"POPULATED",int(out[c].notna().sum()))
 print("OUTPUT",target)
 print("STOP FOR SCORING: margin, clean finish and denominator semantics require original-builder parity; recent timing incomplete")
if __name__=="__main__":main()
