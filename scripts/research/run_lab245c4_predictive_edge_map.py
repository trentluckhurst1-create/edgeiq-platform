from pathlib import Path
import pandas as pd, numpy as np, json
ROOT=Path(__file__).resolve().parents[2]; D=ROOT/"outputs/research/profitability_program/lab245b"; D.mkdir(parents=True,exist_ok=True)
P=D/"LAB245C2_FULL_FIELD_OOF_PROBABILITIES.csv"; B=D/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
OUT=D/"LAB245C4_PREDICTIVE_EDGE_MAP.csv"; AUD=D/"LAB245C4_PREDICTIVE_EDGE_MAP.json"
def metrics(g):
 p=np.clip(g.p_model.to_numpy(float),1e-12,1-1e-12); y=(g.target_finish_position.to_numpy(float)==1).astype(float)
 return pd.Series({"runners":len(g),"races":g._race.nunique(),"expected_wins":p.sum(),"actual_wins":y.sum(),"win_ratio":y.sum()/p.sum() if p.sum()>0 else np.nan,"brier":np.mean((p-y)**2),"mean_p":p.mean()})
def main():
 p=pd.read_csv(P,low_memory=False)
 if "hist_runs" in p.columns:
  x=p.copy()
  b=pd.read_csv(B,usecols=["_race","_horse","hist_runs"],low_memory=False).rename(columns={"hist_runs":"hist_runs_bridge"})
  x=x.merge(b,on=["_race","_horse"],how="left",validate="one_to_one")
  both=x["hist_runs"].notna() & x["hist_runs_bridge"].notna()
  if both.any() and not np.allclose(x.loc[both,"hist_runs"],x.loc[both,"hist_runs_bridge"]):
   raise RuntimeError("hist_runs lineage mismatch between probability OOF and compact bridge")
  x=x.drop(columns=["hist_runs_bridge"])
 else:
  b=pd.read_csv(B,usecols=["_race","_horse","hist_runs"],low_memory=False)
  x=p.merge(b,on=["_race","_horse"],how="left",validate="one_to_one")
 x["field_size"]=x.groupby("_race")["_horse"].transform("size")
 x["model_rank"]=x.groupby("_race")["p_model"].rank(method="first",ascending=False).astype(int)
 x["hist_bucket"]=pd.cut(x.hist_runs,[-1,0,1,2,4,9,10**9],labels=["0","1","2","3-4","5-9","10+"])
 x["field_bucket"]=pd.cut(x.field_size,[0,7,9,11,13,15,99],labels=["<=7","8-9","10-11","12-13","14-15","16+"])
 x["prob_bucket"]=pd.cut(x.p_model,[0,.03,.05,.075,.10,.15,.20,.30,1],right=False)
 x["rank_bucket"]=pd.cut(x.model_rank,[0,1,2,3,5,99],labels=["1","2","3","4-5","6+"])
 frames=[]
 for dim in ["hist_bucket","field_bucket","prob_bucket","rank_bucket"]:
  for year in [2022,2023,2024]:
   z=x[x._year.eq(year)].groupby(dim,observed=True).apply(metrics,include_groups=False).reset_index()
   z.insert(0,"year",year); z.insert(0,"dimension",dim); z=z.rename(columns={dim:"bucket"}); frames.append(z)
 allm=pd.concat(frames,ignore_index=True); allm.to_csv(OUT,index=False)
 # Top-pick race hit rate by field/history context
 top=x[x.model_rank.eq(1)].copy()
 top["won"]=(top.target_finish_position==1).astype(int)
 top_summary=top.groupby("_year").agg(races=("_race","nunique"),expected_wins=("p_model","sum"),actual_wins=("won","sum"))
 top_summary["win_ratio"]=top_summary.actual_wins/top_summary.expected_wins
 audit={"contract_version":"LAB245C4_PREDICTIVE_EDGE_MAP_V1","rows":int(len(x)),"races":int(x._race.nunique()),"years":{str(y):int(x[x._year.eq(y)]._race.nunique()) for y in [2022,2023,2024]},"top_pick_by_year":top_summary.reset_index().to_dict("records"),"selection_policy":"DIAGNOSTIC_ONLY_NO_BETTING_THRESHOLD_TUNING","architecture_note":"2024 is observed diagnostic, not pristine confirmation for future architectures","holdout_2025_2026_opened":False}
 AUD.write_text(json.dumps(audit,indent=2,default=str))
 print(json.dumps(audit,indent=2,default=str))
 print("\nEDGE MAP — WIN RATIO > 1 means more winners than model probability expected")
 print(allm.to_string(index=False))
if __name__=="__main__":main()
