from pathlib import Path
# Build Stage011 identically, then compare on LAB089-covered races only.
exec_path=Path(__file__).parent/"run_v2_stage011_clean_placing.py"
code=exec_path.read_text(encoding="utf-8")
prefix=code.split('print("V2_STAGE011_CONTRACT')[0]
exec(prefix,globals())
A=P/"outputs"/"research"/"model_lab_089"/"LAB089D_E_F_CERTIFIED_TODAY_CONTEXT_FEATURE_MATRIX.csv"
a=pd.read_csv(A);a["race_date"]=pd.to_datetime(a.race_date,errors="coerce")
a=a.rename(columns={"canonical_race_id":"_race","horse_id":"_horse"})
prep=["lab089_prep_runs_this_preparation","lab089_prep_first_up_flag","lab089_prep_second_up_flag","lab089_prep_third_up_flag","lab089_prep_days_since_second_last_run","lab089_prep_spell_length","lab089_prep_short_backup_flag","lab089_prep_freshened_flag"]
a=a[["_race","_horse","race_date"]+prep].drop_duplicates(["_race","_horse","race_date"])
x=x.merge(a,on=["_race","_horse","race_date"],how="left",validate="one_to_one")
# Covered-race contract: every runner in a race must have LAB089 identity coverage.
x["_lab089_present"]=x[prep].notna().any(axis=1)
racecov=x.groupby("_race")["_lab089_present"].transform("all")
z=x[racecov].copy()
print("V2_STAGE017C_CONTRACT COVERED_RACES_STAGE011_VS_PREP_SPELL FIXED_HGB NO_SEARCH NO_MARKET 2025_2026_SEALED")
print("V2_STAGE017C_FEATURES","|".join(prep))
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
 tr=z[z.year<yr];te=z[z.year==yr]
 b=score(tr,te,features);c=score(tr,te,features+prep)
 print("V2_STAGE017C_YEAR",yr,"BASE","|".join(map(repr,b)),"CHALLENGER","|".join(map(repr,c)))
print("V2_STAGE017C_COMPLETE")
