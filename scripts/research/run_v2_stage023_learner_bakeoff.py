from pathlib import Path
# Reconstruct Stage011 matrix exactly; do not execute its model/reporting loop.
src=(Path(__file__).parent/"run_v2_stage011_clean_placing.py").read_text(encoding="utf-8")
prefix=src.split('print("V2_STAGE011_CONTRACT')[0]
exec(prefix,globals())

from sklearn.ensemble import HistGradientBoostingClassifier,RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

print("V2_STAGE023_CONTRACT STAGE011_MATRIX_ONLY HGB_VS_LOGIT_VS_RF PREDECLARED NO_TUNING NO_MARKET 2025_2026_SEALED")
print("V2_STAGE023_PROMOTION BEAT_HGB_LL_AT_LEAST_2_OF_3 YEARS_2024_NOT_WORSE ONE_YEAR_GAIN_GE_0.005")
print("V2_STAGE023_LOGIT L2_C_1_STANDARDIZED_TRAIN_MEDIAN_IMPUTE")
print("V2_STAGE023_RF N500_MINLEAF20_MAXFEATURES_SQRT_TRAIN_MEDIAN_IMPUTE_RANDOM42")
def sm(v):
 v=np.asarray(v,float);e=np.exp(v-np.max(v));return e/e.sum()
def evaluate(name,model,tr,te,native_missing=False):
 Xtr=tr[features].replace([np.inf,-np.inf],np.nan);Xte=te[features].replace([np.inf,-np.inf],np.nan)
 model.fit(Xtr,tr.y.astype(int))
 if hasattr(model,"decision_function"):raw=model.decision_function(Xte)
 else:
  p=model.predict_proba(Xte)[:,1];raw=np.log(np.clip(p,1e-12,1-1e-12)/np.clip(1-p,1e-12,1))
 t=te.copy();t["raw"]=raw;t["p"]=t.groupby("_race").raw.transform(lambda s:sm(s.values))
 rr=[];ll=[]
 for _,g in t.groupby("_race"):
  g=g.sort_values("p",ascending=False).reset_index(drop=True);ii=np.flatnonzero(g.y.values==1)
  if len(ii)!=1:continue
  i=int(ii[0]);rr.append(i+1);ll.append(-np.log(max(float(g.loc[i,"p"]),1e-15)))
 a=np.asarray(rr)
 return dict(races=len(a),ll=float(np.mean(ll)),top1=float(np.mean(a<=1)),top2=float(np.mean(a<=2)),top3=float(np.mean(a<=3)),mrr=float(np.mean(1/a)))
allres={}
for yr in [2022,2023,2024]:
 tr=x[x.year<yr];te=x[x.year==yr].copy()
 models={
 "HGB":HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42),
 "LOGIT":Pipeline([("imp",SimpleImputer(strategy="median")),("scale",StandardScaler()),("m",LogisticRegression(C=1.0,penalty="l2",solver="lbfgs",max_iter=2000,random_state=42))]),
 "RF":Pipeline([("imp",SimpleImputer(strategy="median")),("m",RandomForestClassifier(n_estimators=500,min_samples_leaf=20,max_features="sqrt",random_state=42,n_jobs=-1))])
 }
 allres[yr]={}
 for name,m in models.items():
  q=evaluate(name,m,tr,te);allres[yr][name]=q
  print("V2_STAGE023_YEAR",yr,name,"RACES",q["races"],"LL",repr(q["ll"]),"TOP1",repr(q["top1"]),"TOP2",repr(q["top2"]),"TOP3",repr(q["top3"]),"MRR",repr(q["mrr"]))
for name in ["LOGIT","RF"]:
 gains={y:allres[y]["HGB"]["ll"]-allres[y][name]["ll"] for y in [2022,2023,2024]}
 beats=sum(v>0 for v in gains.values());notworse=gains[2024]>=0;material=max(gains.values())>=0.005
 promote=(beats>=2 and notworse and material)
 print("V2_STAGE023_DECISION",name,"GAINS",repr(gains),"BEATS",beats,"2024_NOT_WORSE",notworse,"MATERIAL",material,"PROMOTE",promote)
print("V2_STAGE023_COMPLETE")
