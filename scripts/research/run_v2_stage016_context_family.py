from pathlib import Path
# Reuse certified Stage011 construction, then add one predeclared exact-ID context family.
exec_path=Path(__file__).parent/"run_v2_stage011_clean_placing.py"
code=exec_path.read_text(encoding="utf-8")
# execute only construction before Stage011 reporting/model loop
prefix=code.split('print("V2_STAGE011_CONTRACT')[0]
exec(prefix,globals())
C=P/"outputs"/"research"/"model_lab_031"/"certified_current_race_context_031.csv"
c=pd.read_csv(C);c["race_date"]=pd.to_datetime(c.race_date,errors="coerce")
c=c.rename(columns={"canonical_race_id":"_race","canonical_horse_id":"_horse"})
add=["current_weight_kg","weight_change_kg","distance_change_metres","abs_distance_change_metres","prior_same_class_starts","prior_exact_distance_starts_031"]
c=c[["_race","_horse","race_date"]+add].drop_duplicates(["_race","_horse","race_date"])
x=x.merge(c,on=["_race","_horse","race_date"],how="left",validate="one_to_one")
# Missingness is meaningful for no-prior/authority gaps; explicit flags, no imputation/search.
x["context_authority_missing"]=x["current_weight_kg"].isna().astype(float)
x["weight_change_missing"]=x["weight_change_kg"].isna().astype(float)
x["distance_change_missing"]=x["distance_change_metres"].isna().astype(float)
family=add+["context_authority_missing","weight_change_missing","distance_change_missing"]
features=features+family
print("V2_STAGE016_CONTRACT STAGE011_PLUS_EXACT_CONTEXT_FAMILY NO_SEARCH NO_MARKET FIXED_HGB 2025_2026_SEALED")
print("V2_STAGE016_FEATURES","|".join(family))
for yr in [2022,2023,2024]:
 tr=x[x.year<yr];te=x[x.year==yr].copy()
 m=HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42)
 m.fit(tr[features].replace([np.inf,-np.inf],np.nan),tr.y.astype(int))
 te["raw"]=m.decision_function(te[features].replace([np.inf,-np.inf],np.nan));te["p"]=te.groupby("_race").raw.transform(lambda s:sm(s.values))
 rr=[];ll=[]
 for _,g in te.groupby("_race"):
  g=g.sort_values("p",ascending=False).reset_index(drop=True);ii=np.flatnonzero(g.y.values==1)
  if len(ii)!=1: continue
  i=int(ii[0]);rr.append(i+1);ll.append(-np.log(max(float(g.loc[i,"p"]),1e-15)))
 a=np.array(rr);print("V2_STAGE016_YEAR",yr,"RACES",len(a),"LL",repr(float(np.mean(ll))),"TOP1",repr(float(np.mean(a<=1))),"TOP2",repr(float(np.mean(a<=2))),"TOP3",repr(float(np.mean(a<=3))),"MRR",repr(float(np.mean(1/a))))
print("V2_STAGE016_COMPLETE")
