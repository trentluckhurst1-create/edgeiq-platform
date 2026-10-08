from pathlib import Path
# Stage011 plus predeclared categorical current-class representation.
exec_path=Path(__file__).parent/"run_v2_stage011_clean_placing.py"
code=exec_path.read_text(encoding="utf-8");prefix=code.split('print("V2_STAGE011_CONTRACT')[0];exec(prefix,globals())
A=P/"outputs"/"research"/"model_lab_031"/"certified_current_race_context_031.csv"
a=pd.read_csv(A,usecols=["canonical_race_id","canonical_horse_id","race_date","current_class_group"])
a["race_date"]=pd.to_datetime(a.race_date,errors="coerce");a=a.rename(columns={"canonical_race_id":"_race","canonical_horse_id":"_horse"})
x=x.merge(a,on=["_race","_horse","race_date"],how="left",validate="one_to_one")
labels=["MAIDEN","BENCHMARK","OPEN","BLACKTYPE","QUALITY"]
cls=x.current_class_group.fillna("").astype(str).str.strip().str.upper()
cf=[]
for lab in labels:
 c="class_"+lab.lower();x[c]=(cls==lab).astype(float);cf.append(c)
x["class_known"]=cls.isin(labels).astype(float);cf.append("class_known")
features=features+cf
print("V2_STAGE018B_CONTRACT STAGE011_PLUS_CATEGORICAL_CLASS FIXED_HGB NO_SEARCH NO_MARKET 2025_2026_SEALED")
print("V2_STAGE018B_FEATURES","|".join(cf))
def sm(v):
 v=np.asarray(v,float);e=np.exp(v-np.max(v));return e/e.sum()
for yr in [2022,2023,2024]:
 tr=x[x.year<yr];te=x[x.year==yr].copy()
 m=HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42)
 m.fit(tr[features].replace([np.inf,-np.inf],np.nan),tr.y.astype(int))
 te["raw"]=m.decision_function(te[features].replace([np.inf,-np.inf],np.nan));te["p"]=te.groupby("_race").raw.transform(lambda s:sm(s.values))
 rr=[];ll=[]
 for _,g in te.groupby("_race"):
  g=g.sort_values("p",ascending=False).reset_index(drop=True);ii=np.flatnonzero(g.y.values==1)
  if len(ii)!=1:continue
  i=int(ii[0]);rr.append(i+1);ll.append(-np.log(max(float(g.loc[i,"p"]),1e-15)))
 q=np.array(rr);print("V2_STAGE018B_YEAR",yr,"RACES",len(q),"LL",repr(float(np.mean(ll))),"TOP1",repr(float(np.mean(q<=1))),"TOP2",repr(float(np.mean(q<=2))),"TOP3",repr(float(np.mean(q<=3))),"MRR",repr(float(np.mean(1/q))))
print("V2_STAGE018B_COMPLETE")
