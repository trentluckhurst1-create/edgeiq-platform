from pathlib import Path
import pandas as pd,numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH");P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
W=R/"outputs"/"research"/"model_v2"/"stage006"/"V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv";D=R/"outputs"/"research"/"profitability_program"/"d45"/"D45_FROZEN_PIT_FEATURE_MATRIX.csv";A=P/"outputs"/"research"/"model_lab_026"/"edgeiq_certified_flat_walk_forward_epi_026.csv"
x=pd.read_csv(W);x["race_date"]=pd.to_datetime(x.race_date);x["year"]=x.race_date.dt.year;d=pd.read_csv(D)
ctx=[c for c in d.columns if any(k in c.lower() for k in ["barrier","jockey_prior","trainer_prior"]) and pd.api.types.is_numeric_dtype(d[c])]
x=x.merge(d[["_race","_horse"]+ctx].drop_duplicates(["_race","_horse"]),on=["_race","_horse"],how="left",validate="one_to_one")
base=["current_distance","hist_runs","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_std5","margin_worst5","margin_last1","margin_last2","last_distance","margin_change_l1_l2","margin_per_runner_last1","margin_per_runner_last2","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best","represented_field_size"]+ctx;base=[c for c in base if c in x.columns]
# rebuild clean strict-prior placing directly from PERF026; chunks for large authority.
need={"canonical_horse_id","race_date","finish_position"};parts=[]
for z in pd.read_csv(A,usecols=lambda c:c in need,chunksize=500000):
 z["race_date"]=pd.to_datetime(z.race_date,errors="coerce");z["finish_position"]=pd.to_numeric(z.finish_position,errors="coerce");z=z[z.finish_position.between(1,99)].dropna(subset=["canonical_horse_id","race_date"])
 parts.append(z)
h=pd.concat(parts,ignore_index=True).sort_values(["canonical_horse_id","race_date"])
# Collapse same horse/date to one observation only when unique valid placing; ambiguous same-date histories excluded.
h=h.groupby(["canonical_horse_id","race_date"],as_index=False).agg(finish_position=("finish_position",lambda s:s.iloc[0] if s.nunique()==1 else np.nan)).dropna()
by={k:g[["race_date","finish_position"]].sort_values("race_date") for k,g in h.groupby("canonical_horse_id")}
def feats(row):
 g=by.get(row["_horse"])
 if g is None:return pd.Series([np.nan]*5)
 q=g[g.race_date<row.race_date].tail(5).finish_position.to_numpy(float)
 if len(q)==0:return pd.Series([np.nan]*5)
 return pd.Series([q.mean(),q[-1],float(q[-1]==1),float(q[-1]<=3),float(len(q))])
clean=x[["_horse","race_date"]].apply(feats,axis=1);clean.columns=["clean_finish_mean5","clean_last_finish","clean_last_won","clean_last_top3","clean_finish_hist_n"];x=pd.concat([x.reset_index(drop=True),clean.reset_index(drop=True)],axis=1)
features=base+list(clean.columns)
print("V2_STAGE011_CONTRACT REBUILD_CLEAN_STRICT_PRIOR_PLACING_FROM_PERF026 STAGE008_PLUS_CLEAN_PLACE NO_MARKET 2025_2026_SEALED")
print("V2_STAGE011_CLEAN_COVERAGE",int(x.clean_finish_hist_n.notna().sum()),len(x))
def sm(v):
 v=np.asarray(v,float);e=np.exp(v-np.max(v));return e/e.sum()
for yr in [2022,2023,2024]:
 tr=x[x.year<yr];te=x[x.year==yr].copy();m=HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42);m.fit(tr[features].replace([np.inf,-np.inf],np.nan),tr.y.astype(int));te["raw"]=m.decision_function(te[features].replace([np.inf,-np.inf],np.nan));te["p"]=te.groupby("_race").raw.transform(lambda s:sm(s.values))
 rr=[];ll=[]
 for _,g in te.groupby("_race"):
  g=g.sort_values("p",ascending=False).reset_index(drop=True);i=int(np.flatnonzero(g.y.values==1)[0]);rr.append(i+1);ll.append(-np.log(max(float(g.loc[i,"p"]),1e-15)))
 a=np.array(rr);print("V2_STAGE011_YEAR",yr,"RACES",len(a),"LL",repr(float(np.mean(ll))),"TOP1",repr(float(np.mean(a<=1))),"TOP2",repr(float(np.mean(a<=2))),"TOP3",repr(float(np.mean(a<=3))),"MRR",repr(float(np.mean(1/a))))
print("V2_STAGE011_COMPLETE")
