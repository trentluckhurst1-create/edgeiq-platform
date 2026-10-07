from pathlib import Path
import pandas as pd,numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import log_loss
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH");W=R/"outputs"/"research"/"model_v2"/"stage006"/"V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv"
x=pd.read_csv(W);x["race_date"]=pd.to_datetime(x.race_date);x["year"]=x.race_date.dt.year
# V2 baseline uses only clean historical performance bridge fields. No sparse linked families.
perf_cols=["current_distance","hist_runs","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_std5","margin_worst5","margin_last1","margin_last2","last_distance","last_finish","last_won","last_top3","margin_change_l1_l2","margin_per_runner_last1","margin_per_runner_last2","finishpos_mean5","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best","represented_field_size"]
perf_cols=[c for c in perf_cols if c in x.columns]
# remove raw placing fields known contaminated from V1 evidence; baseline starts conservative.
contam={"last_finish","last_won","last_top3","finishpos_mean5"}
perf_cols=[c for c in perf_cols if c not in contam]
print("V2_STAGE007_CONTRACT FIRST_NEW_MODEL PERFORMANCE_ONLY CHRONOLOGICAL_WALK_FORWARD NO_MARKET NO_SPARSE_FAMILIES 2025_2026_SEALED")
print("V2_STAGE007_FEATURES",len(perf_cols),"|".join(perf_cols))
def race_softmax(s):
 s=np.asarray(s,float);e=np.exp(s-np.nanmax(s));return e/e.sum()
for testyr in [2022,2023,2024]:
 tr=x[x.year<testyr].copy();te=x[x.year.eq(testyr)].copy()
 # only races with one winner already certified
 Xtr=tr[perf_cols].replace([np.inf,-np.inf],np.nan);Xte=te[perf_cols].replace([np.inf,-np.inf],np.nan)
 m=HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42)
 m.fit(Xtr,tr.y.astype(int))
 raw=m.decision_function(Xte);te=te.copy();te["raw"]=raw
 te["p"]=te.groupby("_race")["raw"].transform(lambda s: race_softmax(s.values))
 ll=-np.mean([np.log(max(g.loc[g.y.eq(1),"p"].iloc[0],1e-15)) for _,g in te.groupby("_race")])
 ranks=[];top={1:0,2:0,3:0}
 for _,g in te.groupby("_race"):
  g=g.sort_values("p",ascending=False).reset_index(drop=True);r=int(np.flatnonzero(g.y.values==1)[0])+1;ranks.append(r)
  for k in top:top[k]+=r<=k
 n=te._race.nunique()
 print("V2_STAGE007_YEAR",testyr,"TRAIN_ROWS",len(tr),"TEST_ROWS",len(te),"RACES",n,"LL",repr(float(ll)),"TOP1",repr(top[1]/n),"TOP2",repr(top[2]/n),"TOP3",repr(top[3]/n),"MRR",repr(float(np.mean(1/np.array(ranks)))))
print("V2_STAGE007_COMPLETE")
