from pathlib import Path
import pandas as pd,numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH");W=R/"outputs"/"research"/"model_v2"/"stage006"/"V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv";D=R/"outputs"/"research"/"profitability_program"/"d45"/"D45_FROZEN_PIT_FEATURE_MATRIX.csv"
x=pd.read_csv(W);x["race_date"]=pd.to_datetime(x.race_date);x["year"]=x.race_date.dt.year;d=pd.read_csv(D)
ctx=[c for c in d.columns if any(k in c.lower() for k in ["barrier","jockey_prior","trainer_prior"]) and pd.api.types.is_numeric_dtype(d[c])]
x=x.merge(d[["_race","_horse"]+ctx].drop_duplicates(["_race","_horse"]),on=["_race","_horse"],how="left",validate="one_to_one")
base=["current_distance","hist_runs","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_std5","margin_worst5","margin_last1","margin_last2","last_distance","margin_change_l1_l2","margin_per_runner_last1","margin_per_runner_last2","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best","represented_field_size"]+ctx;base=[c for c in base if c in x.columns]
# Form-line fields are those from LAB120, identified from warehouse schema by names.
ff=[c for c in x.columns if ("form" in c.lower() or "opponent" in c.lower() or "subsequent" in c.lower()) and c not in base]
ff=[c for c in ff if c not in ["formline_authority_present"]]+["formline_authority_present"]
features=base+ff
print("V2_STAGE010_CONTRACT STAGE008_PLUS_ISOLATED_DYNAMIC_FORMLINE SAME_LEARNER NO_MARKET NO_TIMING NO_PACE 2025_2026_SEALED")
print("V2_STAGE010_FORMLINE_FEATURES",len(ff),"|".join(ff))
def sm(v):
 v=np.asarray(v,float);e=np.exp(v-np.max(v));return e/e.sum()
for yr in [2022,2023,2024]:
 tr=x[x.year<yr];te=x[x.year==yr].copy();m=HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42)
 m.fit(tr[features].replace([np.inf,-np.inf],np.nan),tr.y.astype(int));te["raw"]=m.decision_function(te[features].replace([np.inf,-np.inf],np.nan));te["p"]=te.groupby("_race").raw.transform(lambda s:sm(s.values))
 rr=[];ll=[]
 for _,g in te.groupby("_race"):
  g=g.sort_values("p",ascending=False).reset_index(drop=True);i=int(np.flatnonzero(g.y.values==1)[0]);rr.append(i+1);ll.append(-np.log(max(float(g.loc[i,"p"]),1e-15)))
 a=np.array(rr);print("V2_STAGE010_YEAR",yr,"RACES",len(a),"LL",repr(float(np.mean(ll))),"TOP1",repr(float(np.mean(a<=1))),"TOP2",repr(float(np.mean(a<=2))),"TOP3",repr(float(np.mean(a<=3))),"MRR",repr(float(np.mean(1/a))))
print("V2_STAGE010_COMPLETE")
