from pathlib import Path
import pandas as pd,numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
W=R/"outputs"/"research"/"model_v2"/"stage006"/"V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv"
D=R/"outputs"/"research"/"profitability_program"/"d45"/"D45_FROZEN_PIT_FEATURE_MATRIX.csv"
x=pd.read_csv(W);x["race_date"]=pd.to_datetime(x.race_date);x["year"]=x.race_date.dt.year
d=pd.read_csv(D)
# exact keys, only pre-race context/connection columns; no outcomes/market.
wanted=[c for c in d.columns if any(k in c.lower() for k in ["barrier","jockey_prior","trainer_prior"]) and pd.api.types.is_numeric_dtype(d[c])]
ctx=d[["_race","_horse"]+wanted].drop_duplicates(["_race","_horse"])
x=x.merge(ctx,on=["_race","_horse"],how="left",validate="one_to_one")
base=["current_distance","hist_runs","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_std5","margin_worst5","margin_last1","margin_last2","last_distance","margin_change_l1_l2","margin_per_runner_last1","margin_per_runner_last2","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best","represented_field_size"]
base=[c for c in base if c in x.columns]
features=base+wanted
print("V2_STAGE008_CONTRACT ADD_UNIVERSAL_CONNECTION_CONTEXT_TO_STAGE007 SAME_LEARNER NO_MARKET NO_SPARSE_FAMILIES 2025_2026_SEALED")
print("V2_STAGE008_ADDED",len(wanted),"|".join(wanted))
def soft(v):
 v=np.asarray(v,float);e=np.exp(v-np.max(v));return e/e.sum()
for yr in [2022,2023,2024]:
 tr=x[x.year<yr];te=x[x.year==yr].copy()
 m=HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42)
 m.fit(tr[features].replace([np.inf,-np.inf],np.nan),tr.y.astype(int));te["raw"]=m.decision_function(te[features].replace([np.inf,-np.inf],np.nan));te["p"]=te.groupby("_race").raw.transform(lambda s:soft(s.values))
 ranks=[];loss=[]
 for _,g in te.groupby("_race"):
  g=g.sort_values("p",ascending=False).reset_index(drop=True);idx=int(np.flatnonzero(g.y.values==1)[0]);ranks.append(idx+1);loss.append(-np.log(max(float(g.loc[idx,"p"]),1e-15)))
 n=len(ranks);a=np.array(ranks)
 print("V2_STAGE008_YEAR",yr,"RACES",n,"LL",repr(float(np.mean(loss))),"TOP1",repr(float(np.mean(a<=1))),"TOP2",repr(float(np.mean(a<=2))),"TOP3",repr(float(np.mean(a<=3))),"MRR",repr(float(np.mean(1/a))))
print("V2_STAGE008_COMPLETE")
