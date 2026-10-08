from pathlib import Path
# Stage011 exact construction, then one predeclared complete D99-relative information block.
exec_path=Path(__file__).parent/"run_v2_stage011_clean_placing.py"
code=exec_path.read_text(encoding="utf-8");prefix=code.split('print("V2_STAGE011_CONTRACT')[0];exec(prefix,globals())
pairs=[("hist_runs","hist_runs_rel"),("lvs_last1","lvs_last1_rel"),("lvs_mean3","lvs_mean3_rel"),("lvs_mean5","lvs_mean5_rel"),("lvs_median5","lvs_median5_rel"),("lvs_std5","lvs_std5_rel"),("lvs_peak","lvs_peak_rel"),("lvs_worst5","lvs_worst5_rel"),("margin_mean5","margin_mean5_rel"),("margin_std5","margin_std5_rel"),("margin_worst5","margin_worst5_rel"),("days_since_last","days_since_last_rel"),("dist200_runs","dist200_runs_rel"),("dist200_lvs_mean","dist200_lvs_mean_rel"),("dist200_lvs_best","dist200_lvs_best_rel")]
family=[]
for raw,rel in pairs:
 x[rel]=pd.to_numeric(x[raw],errors="coerce")-x.groupby("_race")[raw].transform("median")
 family.append(rel)
print("V2_STAGE020C_CONTRACT STAGE011_PLUS_COMPLETE_CERTIFIED_D99_RELATIVE_BLOCK FIXED_HGB NO_SEARCH NO_MARKET 2025_2026_SEALED")
print("V2_STAGE020C_FEATURES","|".join(family))
def sm2(v):
 v=np.asarray(v,float);e=np.exp(v-np.max(v));return e/e.sum()
def score(train,test,fs):
 m=HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42)
 m.fit(train[fs].replace([np.inf,-np.inf],np.nan),train.y.astype(int))
 t=test.copy();t["raw"]=m.decision_function(t[fs].replace([np.inf,-np.inf],np.nan));t["p"]=t.groupby("_race").raw.transform(lambda s:sm2(s.values))
 rr=[];ll=[]
 for _,g in t.groupby("_race"):
  g=g.sort_values("p",ascending=False).reset_index(drop=True);ii=np.flatnonzero(g.y.values==1)
  if len(ii)!=1:continue
  i=int(ii[0]);rr.append(i+1);ll.append(-np.log(max(float(g.loc[i,"p"]),1e-15)))
 q=np.array(rr);return len(q),float(np.mean(ll)),float(np.mean(q<=1)),float(np.mean(q<=2)),float(np.mean(q<=3)),float(np.mean(1/q))
for yr in [2022,2023,2024]:
 tr=x[x.year<yr];te=x[x.year==yr]
 b=score(tr,te,features);c=score(tr,te,features+family)
 print("V2_STAGE020C_YEAR",yr,"BASE","|".join(map(repr,b)),"CHALLENGER","|".join(map(repr,c)))
print("V2_STAGE020C_COMPLETE")
