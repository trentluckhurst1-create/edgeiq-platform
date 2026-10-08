from pathlib import Path
# Stage019 = Stage011 + successful Stage018E weight-history family + non-weight Stage016 context.
exec_path=Path(__file__).parent/"run_v2_stage011_clean_placing.py"
code=exec_path.read_text(encoding="utf-8");prefix=code.split('print("V2_STAGE011_CONTRACT')[0];exec(prefix,globals())
W=P/"outputs"/"research"/"model_lab_045a"/"weight_features_045a.csv"
w=pd.read_csv(W);w["race_date"]=pd.to_datetime(w.race_date,errors="coerce");w=w.rename(columns={"canonical_race_id":"_race","canonical_horse_id":"_horse"})
wf=["relative_to_race_mean","relative_to_race_min","relative_to_race_max","weight_rank_in_full_field","weight_pct_in_full_field","full_field_weight_count","previous_start_weight","change_from_previous_start","prior_recent_weight_average","change_from_recent_average"]
w=w[["_race","_horse","race_date"]+wf].drop_duplicates(["_race","_horse","race_date"]);x=x.merge(w,on=["_race","_horse","race_date"],how="left",validate="one_to_one");x["prior_weight_history_missing"]=x["previous_start_weight"].isna().astype(float)
C=P/"outputs"/"research"/"model_lab_031"/"certified_current_race_context_031.csv"
c=pd.read_csv(C);c["race_date"]=pd.to_datetime(c.race_date,errors="coerce");c=c.rename(columns={"canonical_race_id":"_race","canonical_horse_id":"_horse"})
cf=["distance_change_metres","abs_distance_change_metres","prior_same_class_starts","prior_exact_distance_starts_031"]
c=c[["_race","_horse","race_date"]+cf].drop_duplicates(["_race","_horse","race_date"]);x=x.merge(c,on=["_race","_horse","race_date"],how="left",validate="one_to_one");x["distance_change_missing"]=x["distance_change_metres"].isna().astype(float)
family=wf+["prior_weight_history_missing"]+cf+["distance_change_missing"];fs=features+family
print("V2_STAGE019_CONTRACT STAGE011_PLUS_018E_WEIGHT_PLUS_NONWEIGHT_016_CONTEXT FIXED_HGB NO_SEARCH NO_MARKET 2025_2026_SEALED")
print("V2_STAGE019_FEATURES","|".join(family))
def sm(v):
 v=np.asarray(v,float);e=np.exp(v-np.max(v));return e/e.sum()
for yr in [2022,2023,2024]:
 tr=x[x.year<yr];te=x[x.year==yr].copy();m=HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42);m.fit(tr[fs].replace([np.inf,-np.inf],np.nan),tr.y.astype(int));te["raw"]=m.decision_function(te[fs].replace([np.inf,-np.inf],np.nan));te["p"]=te.groupby("_race").raw.transform(lambda s:sm(s.values))
 rr=[];ll=[]
 for _,g in te.groupby("_race"):
  g=g.sort_values("p",ascending=False).reset_index(drop=True);ii=np.flatnonzero(g.y.values==1)
  if len(ii)!=1:continue
  i=int(ii[0]);rr.append(i+1);ll.append(-np.log(max(float(g.loc[i,"p"]),1e-15)))
 q=np.array(rr);print("V2_STAGE019_YEAR",yr,"RACES",len(q),"LL",repr(float(np.mean(ll))),"TOP1",repr(float(np.mean(q<=1))),"TOP2",repr(float(np.mean(q<=2))),"TOP3",repr(float(np.mean(q<=3))),"MRR",repr(float(np.mean(1/q))))
print("V2_STAGE019_COMPLETE")
