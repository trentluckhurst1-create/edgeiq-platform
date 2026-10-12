"""Issue23: full-feature chronological pairwise challenger. No market; sealed 2025-26."""
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier

R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
SOURCE=R/"scripts/research/run_v2_stage011_reproduction_artifact.py"
OUT=R/"outputs/research/model_v2/issue23_full_pairwise"
EXPECTED={2022:(22578,7459,612,138),2023:(30037,30163,2396,495),2024:(60200,31234,2402,552)}
FEATURES=["current_distance","hist_runs","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_std5","margin_worst5","margin_last1","margin_last2","last_distance","margin_change_l1_l2","margin_per_runner_last1","margin_per_runner_last2","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best","represented_field_size","barrier_position_pct","jockey_prior_starts","jockey_prior_win_rate","jockey_prior_top3_rate","trainer_prior_starts","trainer_prior_win_rate","trainer_prior_top3_rate","clean_finish_mean5","clean_last_finish","clean_last_won","clean_last_top3","clean_finish_hist_n"]

def compare(year,te,raw):
 z=te[["_race","_horse","y","p"]].copy()
 z["score"]=raw
 hits=base=corrected=lost=changed=0
 for _,g in z.groupby("_race",sort=False):
  a=g.sort_values(["p","_horse"],ascending=[False,True],kind="stable").iloc[0]
  b=g.sort_values(["score","_horse"],ascending=[False,True],kind="stable").iloc[0]
  base+=int(a.y);hits+=int(b.y)
  changed+=int(a._horse!=b._horse) if False else int(a["_horse"]!=b["_horse"])
  corrected+=int(a.y==0 and b.y==1)
  lost+=int(a.y==1 and b.y==0)
 print(f"YEAR={year} RACES={z._race.nunique()} BASE={base} CHALLENGER={hits} DELTA={hits-base:+d} DELTA_PP={100*(hits-base)/z._race.nunique():+.4f} CORRECTED={corrected} LOST={lost} CHANGED={changed}",flush=True)
 if base!=EXPECTED[year][3]:raise RuntimeError("STOP baseline winner drift")
 return hits

def run(x,features):
 if features!=FEATURES:raise RuntimeError("STOP exact Stage011 feature manifest mismatch")
 if x.year.min()!=2021 or x.year.max()!=2024:raise RuntimeError("STOP historical years drift")
 if x.duplicated(["_race","_horse"]).any():raise RuntimeError("STOP duplicate keys")
 OUT.mkdir(parents=True,exist_ok=True)
 print("ISSUE23 FULL 35-FEATURE CHRONOLOGICAL PAIRWISE RANKER",flush=True)
 print("NO MARKET; 2025-26 SEALED; 2022-24 REUSED DEVELOPMENT",flush=True)
 for year in (2022,2023,2024):
  tr=x[x.year<year].copy();te=x[x.year==year].copy()
  nt,nv,nr,_=EXPECTED[year]
  if (len(tr),len(te),te._race.nunique())!=(nt,nv,nr):raise RuntimeError("STOP population mismatch")
  # Compare original Stage011 p to existing reproduction. Never refit or modify champion.
  old=pd.read_csv(R/f"outputs/research/model_v2/stage011_reproduction/STAGE011_RUNNER_PROBABILITIES_{year}.csv",usecols=["_race","_horse","p","y"])
  te=te.merge(old.rename(columns={"p":"champ_p","y":"champ_y"}),on=["_race","_horse"],how="left",validate="one_to_one")
  if te.champ_p.isna().any() or not (te.y==te.champ_y).all():raise RuntimeError("STOP champion join drift")
  te["p"]=te.champ_p
  # Preprocessing fit only on the earlier training years.
  a=tr[features].replace([np.inf,-np.inf],np.nan).to_numpy(dtype=float)
  b=te[features].replace([np.inf,-np.inf],np.nan).to_numpy(dtype=float)
  imp=SimpleImputer(strategy="median",keep_empty_features=True)
  a=imp.fit_transform(a);b=imp.transform(b)
  scale=StandardScaler()
  a=scale.fit_transform(a);b=scale.transform(b)
  pairs=[]
  tr2=tr[["_race","y"]].reset_index(drop=True)
  for _,g in tr2.groupby("_race",sort=False):
   ids=g.index.to_numpy();winner=ids[g.y.to_numpy()==1]
   if len(winner)!=1:raise RuntimeError("STOP training race outcome contract")
   other=ids[g.y.to_numpy()==0]
   if len(other):pairs.append(a[winner[0]]-a[other])
  if not pairs:raise RuntimeError("STOP no training pairs")
  d=np.vstack(pairs)
  # Mirrored pairs make the learned score comparable within each race.
  xx=np.vstack([d,-d]);yy=np.r_[np.ones(len(d),dtype=int),np.zeros(len(d),dtype=int)]
  model=LogisticRegression(C=0.1,fit_intercept=False,solver="lbfgs",max_iter=500)
  model.fit(xx,yy)
  scores=b@model.coef_[0]
  print(f"YEAR={year} TRAIN_ROWS={len(tr)} TRAIN_RACES={tr._race.nunique()} PAIRS={len(d)} FEATURES={len(features)}",flush=True)
  compare(year,te,scores)
  out=te[["_race","_horse","race_date","y","p"]].copy()
  out["challenger_score"]=scores
  out.to_csv(OUT/f"ISSUE23_FULL_PAIRWISE_{year}.csv",index=False)
 print("NO_PROMOTION; 2022-24 ARE REUSED DEVELOPMENT; INDEPENDENT VALIDATION STILL REQUIRED",flush=True)

def main():
 if not SOURCE.is_file():raise FileNotFoundError(SOURCE)
 src=SOURCE.read_text(encoding="utf-8-sig")
 marker='    print("STAGE011_REPRODUCTION_ONLY SEED=42 EVIDENCE_CLASS=REUSED_DEVELOPMENT")'
 if src.count(marker)!=1:raise RuntimeError("STOP upstream source changed")
 # Execute the exact upstream feature construction, replacing only its model-fit/output tail.
 prefix=src.split(marker)[0]
 injected=prefix+"    __issue23_run(x,features)\n"
 ns={"__name__":"issue23_upstream","__issue23_run":run}
 print("UPSTREAM_SOURCE_SHA256="+hashlib.sha256(src.encode()).hexdigest(),flush=True)
 exec(compile(injected,str(SOURCE),"exec"),ns)
 ns["main"]()
if __name__=="__main__":main()
