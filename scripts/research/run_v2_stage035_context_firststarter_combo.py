from pathlib import Path
# Predeclared combination: retained Stage016 context + certified Stage031 first-starter family.
exec_path=Path(__file__).parent/"run_v2_stage016_context_family.py"
code=exec_path.read_text(encoding="utf-8")
prefix=code.split('def sm(v):')[0]
exec(prefix,globals())
A=P/"outputs"/"research"/"model_lab_075f2"/"canonical_strict_date_first_starter_universe_075f2.csv"
a=pd.read_csv(A,low_memory=False);a["race_date"]=pd.to_datetime(a.race_date,errors="coerce")
a=a[a["canonical_horse_id_075f2"].notna() & a["lab026_canonical_race_id"].notna()].copy()
a["_horse"]=a["canonical_horse_id_075f2"].astype(str).str.strip();a["_race"]=a["lab026_canonical_race_id"].astype(str).str.strip()
x["_horse"]=x["_horse"].astype(str).str.strip();x["_race"]=x["_race"].astype(str).str.strip()
raw=["trainer_prior_first_starters","trainer_prior_first_starter_wins","trainer_prior_first_starter_places","jockey_prior_first_starters","jockey_prior_first_starter_wins","jockey_prior_first_starter_places","combo_prior_first_starters","combo_prior_first_starter_wins","combo_prior_first_starter_places"]
a=a[["_race","_horse","race_date"]+raw].drop_duplicates(["_race","_horse","race_date"])
x=x.merge(a,on=["_race","_horse","race_date"],how="left",validate="one_to_one")
x["first_starter_flag"]=x[raw[0]].notna().astype(float)
for c in raw:x[c]=x[c].fillna(0.0)
for who in ["trainer","jockey","combo"]:
 n=x[f"{who}_prior_first_starters"]
 x[f"{who}_prior_fs_win_rate"]=np.where(n>0,x[f"{who}_prior_first_starter_wins"]/n,0.0)
 x[f"{who}_prior_fs_place_rate"]=np.where(n>0,x[f"{who}_prior_first_starter_places"]/n,0.0)
fs=["first_starter_flag","trainer_prior_first_starters","jockey_prior_first_starters","combo_prior_first_starters","trainer_prior_fs_win_rate","trainer_prior_fs_place_rate","jockey_prior_fs_win_rate","jockey_prior_fs_place_rate","combo_prior_fs_win_rate","combo_prior_fs_place_rate"]
def sm(v):
 v=np.asarray(v,float);e=np.exp(v-np.max(v));return e/e.sum()
def score(tr,te,cols):
 m=HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42)
 m.fit(tr[cols].replace([np.inf,-np.inf],np.nan),tr.y.astype(int))
 t=te.copy();t["raw"]=m.decision_function(t[cols].replace([np.inf,-np.inf],np.nan));t["p"]=t.groupby("_race").raw.transform(lambda s:sm(s.values))
 rr=[];ll=[]
 for _,g in t.groupby("_race"):
  g=g.sort_values("p",ascending=False).reset_index(drop=True);ii=np.flatnonzero(g.y.values==1)
  if len(ii)!=1:continue
  i=int(ii[0]);rr.append(i+1);ll.append(-np.log(max(float(g.loc[i,"p"]),1e-15)))
 q=np.array(rr);return len(q),float(np.mean(ll)),float(np.mean(q<=1)),float(np.mean(q<=2)),float(np.mean(q<=3)),float(np.mean(1/q))
print("V2_STAGE035_CONTRACT STAGE016_PLUS_CERTIFIED_FIRST_STARTER FIXED_HGB NO_SEARCH NO_MARKET 2025_2026_SEALED")
for yr in [2022,2023,2024]:
 tr=x[x.year<yr];te=x[x.year==yr]
 b=score(tr,te,features);c=score(tr,te,features+fs)
 print("V2_STAGE035_YEAR",yr,"STAGE016","|".join(map(repr,b)),"COMBINED","|".join(map(repr,c)))
print("V2_STAGE035_COMPLETE")
