from pathlib import Path
import pandas as pd,numpy as np
from sklearn.impute import SimpleImputer
from sklearn.ensemble import HistGradientBoostingClassifier
D=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\d45\D45_FROZEN_PIT_FEATURE_MATRIX.csv");B=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv")
d=pd.read_csv(D);b=pd.read_csv(B);z=d.merge(b[["_race","_horse","last_distance","last_finish","last_won","last_top3"]],on=["_race","_horse"],how="left",validate="one_to_one");z["distance_change"]=z.current_distance-z.last_distance;z["abs_distance_change"]=z.distance_change.abs();prep=["days_since_last","distance_change","abs_distance_change","last_finish","last_won","last_top3"];z["date"]=pd.to_datetime(z.race_date);z["year_eval"]=z.date.dt.year
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone","year","year_eval"};num=[c for c in d.columns if c not in meta and pd.api.types.is_numeric_dtype(d[c])];context={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"};F=list(dict.fromkeys([c for c in num if c not in context]+prep))
print("D95_CONTRACT PREP47_TOP2_PAIRWISE_MASS_REALLOCATION STRICT_PREYEAR NO_SEARCH SAME_HGB T1")
for yr in [2022,2023,2024]:
 tr=z[z.year_eval<yr].copy();te=z[z.year_eval.eq(yr)].copy();imp=SimpleImputer(strategy="median");X=imp.fit_transform(tr[F]);Xt=imp.transform(te[F]);base=HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42);base.fit(X,tr.y);sc=base.decision_function(Xt);te["s"]=sc;te["p"]=te.groupby("_race").s.transform(lambda a:np.exp(a-a.max())/np.exp(a-a.max()).sum());te["rank"]=te.groupby("_race").s.rank(ascending=False,method="first")
 # winner-loser difference pairs from historical races only
 pairs=[];labels=[]
 Xdf=pd.DataFrame(X,index=tr.index)
 for rid,g in tr.groupby("_race",sort=False):
  wi=g.index[g.y.eq(1)].tolist()
  if len(wi)!=1:continue
  wv=Xdf.loc[wi[0]].to_numpy()
  for li in g.index[g.y.eq(0)]:
   diff=wv-Xdf.loc[li].to_numpy();pairs.append(diff);labels.append(1);pairs.append(-diff);labels.append(0)
 pm=HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=43);pm.fit(np.asarray(pairs),np.asarray(labels))
 te["p2"]=te.p
 for rid,g in te.groupby("_race",sort=False):
  top=g.nsmallest(2,"rank")
  if len(top)<2:continue
  i,j=top.index[0],top.index[1];qi=float(pm.predict_proba((Xt[te.index.get_loc(i)]-Xt[te.index.get_loc(j)]).reshape(1,-1))[0,1]);mass=float(te.loc[i,"p"]+te.loc[j,"p"]);te.loc[i,"p2"]=mass*qi;te.loc[j,"p2"]=mass*(1-qi)
 for name,pc in [("PREP47","p"),("TOP2_PAIRWISE","p2")]:
  q=te.copy();q["rank2"]=q.groupby("_race")[pc].rank(ascending=False,method="first");w=q[q.y.eq(1)]
  print("D95_RESULT",yr,name,"RACES",len(w),"TOP1",float((w.rank2==1).mean()),"TOP2",float((w.rank2<=2).mean()),"TOP3",float((w.rank2<=3).mean()),"MRR",float((1/w.rank2).mean()),"LL",float(-np.log(w[pc].clip(1e-12,1)).mean()))
print("D95_COMPLETE 2025_2026_SEALED")
