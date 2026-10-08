from pathlib import Path
# Build Stage018C champion, then add clean LAB037 shrinkage connection family only.
exec_path=Path(__file__).parent/"run_v2_stage018c_weight_structure.py"
code=exec_path.read_text(encoding="utf-8")
prefix=code.split('print("V2_STAGE018C_CONTRACT')[0]
exec(prefix,globals())
# At this point x includes weight family and 'family' names the Stage018C weight block.
weight_family=family.copy()
A=P/"outputs"/"research"/"model_lab_037"/"prior_jockey_trainer_intelligence_037.csv"
a=pd.read_csv(A);a["race_date"]=pd.to_datetime(a.race_date,errors="coerce");a=a.rename(columns={"canonical_race_id":"_race","canonical_horse_id":"_horse"})
conn=["jockey_prior_win_rate_raw_037","jockey_prior_win_rate_shrunk_037","trainer_prior_win_rate_raw_037","trainer_prior_win_rate_shrunk_037"]
a=a[["_race","_horse","race_date"]+conn].drop_duplicates(["_race","_horse","race_date"])
x=x.merge(a,on=["_race","_horse","race_date"],how="left",validate="one_to_one")
allf=features+weight_family+conn
print("V2_STAGE019_CONTRACT STAGE018C_PLUS_CLEAN_SHRUNK_CONNECTION_QUALITY FIXED_HGB NO_EPI NO_RESIDUAL NO_SEARCH NO_MARKET 2025_2026_SEALED")
print("V2_STAGE019_FEATURES","|".join(conn))
def sm(v):
 v=np.asarray(v,float);e=np.exp(v-np.max(v));return e/e.sum()
for yr in [2022,2023,2024]:
 tr=x[x.year<yr];te=x[x.year==yr].copy()
 m=HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42)
 m.fit(tr[allf].replace([np.inf,-np.inf],np.nan),tr.y.astype(int))
 te["raw"]=m.decision_function(te[allf].replace([np.inf,-np.inf],np.nan));te["p"]=te.groupby("_race").raw.transform(lambda s:sm(s.values))
 rr=[];ll=[]
 for _,g in te.groupby("_race"):
  g=g.sort_values("p",ascending=False).reset_index(drop=True);ii=np.flatnonzero(g.y.values==1)
  if len(ii)!=1:continue
  i=int(ii[0]);rr.append(i+1);ll.append(-np.log(max(float(g.loc[i,"p"]),1e-15)))
 q=np.array(rr);print("V2_STAGE019_YEAR",yr,"RACES",len(q),"LL",repr(float(np.mean(ll))),"TOP1",repr(float(np.mean(q<=1))),"TOP2",repr(float(np.mean(q<=2))),"TOP3",repr(float(np.mean(q<=3))),"MRR",repr(float(np.mean(1/q))))
print("V2_STAGE019_COMPLETE")
