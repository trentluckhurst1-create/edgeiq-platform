from pathlib import Path
# Diagnostic only: deterministically reproduce frozen Stage011/Stage016 scores, then inspect them.
exec_path=Path(__file__).parent/"run_v2_stage011_clean_placing.py"
code=exec_path.read_text(encoding="utf-8");prefix=code.split('print("V2_STAGE011_CONTRACT')[0];exec(prefix,globals())
C=P/"outputs"/"research"/"model_lab_031"/"certified_current_race_context_031.csv"
c=pd.read_csv(C);c["race_date"]=pd.to_datetime(c.race_date,errors="coerce")
c=c.rename(columns={"canonical_race_id":"_race","canonical_horse_id":"_horse"})
ctx=["current_weight_kg","weight_change_kg","distance_change_metres","abs_distance_change_metres","prior_same_class_starts","prior_exact_distance_starts_031"]
c=c[["_race","_horse","race_date"]+ctx].drop_duplicates(["_race","_horse","race_date"])
x=x.merge(c,on=["_race","_horse","race_date"],how="left",validate="one_to_one")
x["context_authority_missing"]=x["current_weight_kg"].isna().astype(float)
x["weight_change_missing"]=x["weight_change_kg"].isna().astype(float)
x["distance_change_missing"]=x["distance_change_metres"].isna().astype(float)
f16=ctx+["context_authority_missing","weight_change_missing","distance_change_missing"]
def sm(v):
 v=np.asarray(v,float);e=np.exp(v-np.max(v));return e/e.sum()
def predict(train,test,fs):
 m=HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42)
 m.fit(train[fs].replace([np.inf,-np.inf],np.nan),train.y.astype(int))
 t=test[["_race","_horse","y"]].copy()
 t["raw"]=m.decision_function(test[fs].replace([np.inf,-np.inf],np.nan))
 t["p"]=t.groupby("_race").raw.transform(lambda s:sm(s.values))
 t["rank"]=t.groupby("_race").p.rank(method="first",ascending=False)
 return t
print("V2_STAGE021_CONTRACT FROZEN_SCORE_REPRODUCTION_DIAGNOSTIC STAGE011_VS_STAGE016 RELIABILITY_DECILES WINNER_RANK NO_FEATURE_SEARCH NO_CALIBRATION_FIT NO_MARKET 2025_2026_SEALED")
for yr in [2022,2023,2024]:
 tr=x[x.year<yr];te=x[x.year==yr]
 for name,fs in [("S011",features),("S016",features+f16)]:
  t=predict(tr,te,fs)
  # deterministic equal-count probability deciles, diagnostic only
  t["decile"]=pd.qcut(t["p"].rank(method="first"),10,labels=False)+1
  print("V2_STAGE021_YEAR",yr,name,"N",len(t),"RACES",t["_race"].nunique())
  for d,g in t.groupby("decile"):
   print("V2_STAGE021_DECILE",yr,name,int(d),"N",len(g),"MEAN_P",repr(float(g.p.mean())),"OBS_WIN",repr(float(g.y.mean())),"GAP",repr(float(g.y.mean()-g.p.mean())))
  w=t[t.y==1]
  print("V2_STAGE021_WINRANK",yr,name,"MEAN",repr(float(w["rank"].mean())),"MEDIAN",repr(float(w["rank"].median())),"TOP1",repr(float((w["rank"]<=1).mean())),"TOP2",repr(float((w["rank"]<=2).mean())),"TOP3",repr(float((w["rank"]<=3).mean())))
print("V2_STAGE021_COMPLETE")
