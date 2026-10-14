"""Issue23 research-only dual scorer: immutable input, hash-checked artifacts, no outcomes."""
from pathlib import Path
import argparse,hashlib,json,datetime
import joblib,numpy as np,pandas as pd
FEATURES=["current_distance","hist_runs","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_std5","margin_worst5","margin_last1","margin_last2","last_distance","margin_change_l1_l2","margin_per_runner_last1","margin_per_runner_last2","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best","represented_field_size","barrier_position_pct","jockey_prior_starts","jockey_prior_win_rate","jockey_prior_top3_rate","trainer_prior_starts","trainer_prior_win_rate","trainer_prior_top3_rate","clean_finish_mean5","clean_last_finish","clean_last_won","clean_last_top3","clean_finish_hist_n"]
FORBIDDEN={"y","winner","won","result","result_position","finish_position","finishing_position","outcome","sp","bsp","market_price","starting_price","fixed_odds","betfair_price"}
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(8*1024*1024),b""):h.update(b)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--features",required=True)
 p.add_argument("--output",required=True)
 p.add_argument("--artifact-dir",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\issue23_prospective_artifacts")
 a=p.parse_args()
 root=Path(a.artifact_dir)
 manifest=root/"ISSUE23_MODEL_ARTIFACT_MANIFEST.json"
 m=json.loads(manifest.read_text(encoding="utf-8"))
 if m["status"]!="RESEARCH_ONLY_UNVALIDATED" or m["features"]!=FEATURES or m["training_year_max"]!=2024:raise RuntimeError("STOP artifact contract drift")
 cp=root/"ISSUE23_STAGE011_TRAIN_THROUGH_2024.joblib";pp=root/"ISSUE23_PAIRWISE_TRAIN_THROUGH_2024.joblib"
 if sha(cp)!=m["stage011_sha256"] or sha(pp)!=m["pairwise_sha256"]:raise RuntimeError("STOP model artifact hash mismatch")
 f=Path(a.features);o=Path(a.output)
 if o.exists():raise RuntimeError("STOP output exists; immutable prediction required")
 if f.resolve()==o.resolve():raise RuntimeError("STOP input/output same")
 d=pd.read_csv(f,dtype={"race_id":str,"runner_id":str})
 required={"race_id","runner_id","scoring_timestamp","scratch_status","scheduled_start_time"}|set(FEATURES)
 if not required.issubset(d.columns):raise RuntimeError("STOP missing fields "+str(sorted(required-set(d.columns))))
 bad=FORBIDDEN & {str(c).lower() for c in d.columns}
 if bad:raise RuntimeError("STOP outcome/market columns present "+str(sorted(bad)))
 if d.empty or d[["race_id","runner_id"]].isna().any().any() or d.duplicated(["race_id","runner_id"]).any():raise RuntimeError("STOP invalid identities")
 if not d.scratch_status.eq("ACTIVE").all():raise RuntimeError("STOP scratched/inactive rows")
 ts=pd.to_datetime(d.scoring_timestamp,utc=True,errors="raise")
 start=pd.to_datetime(d.scheduled_start_time,utc=True,errors="raise")
 if ts.isna().any() or start.isna().any() or not (ts<start).all():raise RuntimeError("STOP timestamps not strictly pre-race")
 now=pd.Timestamp.now(tz="UTC")
 if (ts>now+pd.Timedelta(minutes=2)).any():raise RuntimeError("STOP future scoring timestamp")
 if (now>=start).any():raise RuntimeError("STOP race has already started; not prospective")
 if (d.groupby("race_id").size()<2).any():raise RuntimeError("STOP race with fewer than two active runners")
 X=d[FEATURES].apply(pd.to_numeric,errors="raise").replace([np.inf,-np.inf],np.nan)
 if X.notna().sum().sum()==0:raise RuntimeError("STOP all feature values missing")
 # Trusted local artifacts only, after digest checks.
 champ=joblib.load(cp);bundle=joblib.load(pp)
 if bundle["features"]!=FEATURES:raise RuntimeError("STOP pairwise feature drift")
 prob=np.asarray(champ.predict_proba(X)[:,1],float)
 if not np.isfinite(prob).all():raise RuntimeError("STOP invalid champion probabilities")
 z=bundle["scaler"].transform(bundle["imputer"].transform(X.to_numpy(float)))
 score=np.asarray(bundle["model"].decision_function(z),float)
 if not np.isfinite(score).all():raise RuntimeError("STOP invalid pairwise scores")
 d=d[["race_id","runner_id","scoring_timestamp","scheduled_start_time"]].copy()
 d["stage011_raw_probability"]=prob;d["pairwise_score"]=score
 d["stage011_probability"]=d.groupby("race_id").stage011_raw_probability.transform(lambda x:x/x.sum())
 if not np.isfinite(d.stage011_probability).all():raise RuntimeError("STOP probability mass invalid")
 decisions=[]
 for race,g in d.groupby("race_id",sort=True):
  b=g.sort_values(["stage011_probability","runner_id"],ascending=[False,True],kind="stable")
  q=g.sort_values(["pairwise_score","runner_id"],ascending=[False,True],kind="stable")
  gap=float(b.iloc[0].stage011_probability-b.iloc[1].stage011_probability)
  switch=bool(q.iloc[0].runner_id==b.iloc[1].runner_id and gap<=.01)
  decisions.append({"race_id":race,"champion_runner_id":b.iloc[0].runner_id,"pairwise_runner_id":q.iloc[0].runner_id,"selected_runner_id":q.iloc[0].runner_id if switch else b.iloc[0].runner_id,"switch":switch,"stage011_top2_gap":gap})
 dec=pd.DataFrame(decisions)
 d=d.merge(dec,on="race_id",validate="many_to_one")
 d["source_sha256"]=sha(f);d["champion_model_sha256"]=sha(cp);d["pairwise_model_sha256"]=sha(pp)
 o.parent.mkdir(parents=True,exist_ok=True)
 with o.open("x",encoding="utf-8",newline="") as handle:d.to_csv(handle,index=False)
 print(f"ISSUE23_DUAL_SCORING_PASS RACES={len(dec)} RUNNERS={len(d)} SWITCHES={int(dec.switch.sum())}")
 print("OUTPUT="+str(o))
 print("STATUS=UNATTESTED_PRE_RACE_RESEARCH_PREDICTIONS")
 print("NO_OUTCOMES_READ; NO_PRODUCTION_PROMOTION")
if __name__=="__main__":main()
