from pathlib import Path
exec_path=Path(__file__).parent/"run_v2_stage011_clean_placing.py"
code=exec_path.read_text(encoding="utf-8");prefix=code.split('print("V2_STAGE011_CONTRACT')[0];exec(prefix,globals())
A=P/"outputs"/"research"/"model_lab_045a"/"weight_features_045a.csv"
a=pd.read_csv(A);a["race_date"]=pd.to_datetime(a.race_date,errors="coerce")
a=a.rename(columns={"canonical_race_id":"_race","canonical_horse_id":"_horse"})
family=["weight_rank_in_full_field","weight_pct_in_full_field","full_field_weight_count"]
a=a[["_race","_horse","race_date"]+family].drop_duplicates(["_race","_horse","race_date"])
x=x.merge(a,on=["_race","_horse","race_date"],how="left",validate="one_to_one")
x["weight_field_context_missing"]=x["weight_rank_in_full_field"].isna().astype(float)
family=family+["weight_field_context_missing"]
print("V2_STAGE019E_CONTRACT STAGE011_PLUS_DENSE_FIELD_RELATIVE_WEIGHT FIXED_HGB NO_SEARCH NO_MARKET NO_EPI 2025_2026_SEALED")
print("V2_STAGE019E_FEATURES","|".join(family))
def sm(v):
 v=np.asarray(v,float);e=np.exp(v-np.max(v));return e/e.sum()
def score(train,test,fs):
 m=HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42)
 m.fit(train[fs].replace([np.inf,-np.inf],np.nan),train.y.astype(int))
 t=test.copy();t["raw"]=m.decision_function(t[fs].replace([np.inf,-np.inf],np.nan));t["p"]=t.groupby("_race").raw.transform(lambda s:sm(s.values))
 rr=[];ll=[]
 for _,g in t.groupby("_race"):
  g=g.sort_values("p",ascending=False).reset_index(drop=True);ii=np.flatnonzero(g.y.values==1)
  if len(ii)!=1:continue
  i=int(ii[0]);rr.append(i+1);ll.append(-np.log(max(float(g.loc[i,"p"]),1e-15)))
 q=np.array(rr);return len(q),float(np.mean(ll)),float(np.mean(q<=1)),float(np.mean(q<=2)),float(np.mean(q<=3)),float(np.mean(1/q))
for yr in [2022,2023,2024]:
 tr=x[x.year<yr];te=x[x.year==yr]
 b=score(tr,te,features);c=score(tr,te,features+family)
 print("V2_STAGE019E_YEAR",yr,"BASE","|".join(map(repr,b)),"CHALLENGER","|".join(map(repr,c)))
print("V2_STAGE019E_COMPLETE")
