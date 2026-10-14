"""Issue23: research-only model export from exact Stage011 feature construction."""
from pathlib import Path
import hashlib,json
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
SOURCE=R/"scripts/research/run_v2_stage011_reproduction_artifact.py"
OUT=R/"outputs/research/model_v2/issue23_prospective_artifacts"
FEATURES=["current_distance","hist_runs","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_std5","margin_worst5","margin_last1","margin_last2","last_distance","margin_change_l1_l2","margin_per_runner_last1","margin_per_runner_last2","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best","represented_field_size","barrier_position_pct","jockey_prior_starts","jockey_prior_win_rate","jockey_prior_top3_rate","trainer_prior_starts","trainer_prior_win_rate","trainer_prior_top3_rate","clean_finish_mean5","clean_last_finish","clean_last_won","clean_last_top3","clean_finish_hist_n"]
def digest(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(8*1024*1024),b""):h.update(b)
 return h.hexdigest()
def build(x,features):
 if features!=FEATURES:raise RuntimeError("STOP feature manifest drift")
 if x.year.min()!=2021 or x.year.max()!=2024:raise RuntimeError("STOP year scope")
 if x.duplicated(["_race","_horse"]).any():raise RuntimeError("STOP duplicate runner")
 # 2024 is historical research data, but the live prospective fit uses through 2024.
 tr=x[x.year.le(2024)].copy()
 if len(tr)!=91434:raise RuntimeError(f"STOP historical training rows unexpected: {len(tr)}")
 a=tr[features].replace([np.inf,-np.inf],np.nan).to_numpy(float)
 y=tr.y.to_numpy(int)
 champ=HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42)
 champ.fit(pd.DataFrame(a,columns=features),y)
 imp=SimpleImputer(strategy="median",keep_empty_features=True)
 z=imp.fit_transform(a)
 scaler=StandardScaler()
 z=scaler.fit_transform(z)
 pieces=[]
 keys=tr[["_race","y"]].reset_index(drop=True)
 for _,g in keys.groupby("_race",sort=False):
  ids=g.index.to_numpy();w=ids[g.y.to_numpy()==1];others=ids[g.y.to_numpy()==0]
  if len(w)!=1:raise RuntimeError("STOP winner contract")
  if len(others):pieces.append(z[w[0]]-z[others])
 delta=np.vstack(pieces)
 X=np.vstack([delta,-delta]);target=np.r_[np.ones(len(delta),dtype=int),np.zeros(len(delta),dtype=int)]
 pair=LogisticRegression(C=.1,fit_intercept=False,solver="lbfgs",max_iter=500)
 pair.fit(X,target)
 OUT.mkdir(parents=True,exist_ok=True)
 p1=OUT/"ISSUE23_STAGE011_TRAIN_THROUGH_2024.joblib"
 p2=OUT/"ISSUE23_PAIRWISE_TRAIN_THROUGH_2024.joblib"
 for path,obj in [(p1,champ),(p2,{"imputer":imp,"scaler":scaler,"model":pair,"features":features})]:
  if path.exists():raise RuntimeError(f"STOP artifact already exists, refusing overwrite: {path}")
  joblib.dump(obj,path)
 manifest={"status":"RESEARCH_ONLY_UNVALIDATED","training_year_max":2024,"training_rows":len(tr),"training_races":int(tr._race.nunique()),"features":features,"source_sha256":digest(SOURCE),"stage011_sha256":digest(p1),"pairwise_sha256":digest(p2),"no_market":True,"prospective_predictions_recorded":False,"no_production_promotion":True}
 mp=OUT/"ISSUE23_MODEL_ARTIFACT_MANIFEST.json"
 mp.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
 print("ARTIFACT_EXPORT=PASS",flush=True)
 print("TRAIN_ROWS="+str(len(tr))+" TRAIN_RACES="+str(tr._race.nunique()))
 print("STAGE011_MODEL="+str(p1)+" SHA256="+digest(p1))
 print("PAIRWISE_MODEL="+str(p2)+" SHA256="+digest(p2))
 print("MANIFEST="+str(mp))
 print("NO_LIVE_INPUTS_SCORED; NO_2025_2026_OUTCOMES")
def main():
 src=SOURCE.read_text(encoding="utf-8-sig")
 marker='    print("STAGE011_REPRODUCTION_ONLY SEED=42 EVIDENCE_CLASS=REUSED_DEVELOPMENT")'
 if src.count(marker)!=1:raise RuntimeError("STOP reproduction source drift")
 ns={"__name__":"issue23_source","__issue23_build":build}
 exec(compile(src.split(marker)[0]+"    __issue23_build(x,features)\n",str(SOURCE),"exec"),ns)
 ns["main"]()
if __name__=="__main__":main()
