"""Experimental Stage011 win probabilities from observed pre-race form.

Not certified or actionable. Uses frozen champion, never odds/outcomes from target race.
Missing feature families remain NaN and use the artifact's native preprocessing.
"""
from pathlib import Path
import argparse,hashlib,json
import joblib,numpy as np,pandas as pd
from run_issue23_dual_live_scorer_v2 import FEATURES,sha
LIVE=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1")
ART=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\issue23_prospective_artifacts")
def num(s):return pd.to_numeric(s,errors="coerce")
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--date",default="2026-10-14")
 p.add_argument("--venue",default="Caulfield")
 p.add_argument("--output",default="outputs/research/selection_gate_v2/CAULFIELD_EXPERIMENTAL_STAGE011_PREDICTIONS.csv")
 a=p.parse_args()
 manifest=json.loads((ART/"ISSUE23_MODEL_ARTIFACT_MANIFEST.json").read_text(encoding="utf-8"))
 modelpath=ART/"ISSUE23_STAGE011_TRAIN_THROUGH_2024.joblib"
 if manifest["features"]!=FEATURES or manifest["training_year_max"]!=2024 or sha(modelpath)!=manifest["stage011_sha256"]:raise RuntimeError("STOP model drift")
 d=pd.read_csv(LIVE/"october_graphql_field_identities.csv",dtype="string")
 d=d[d.race_date.eq(a.date)&d.venue.str.casefold().eq(a.venue.casefold())].copy()
 if d.empty or d.race_entry_id.isna().any() or d.race_entry_id.duplicated().any():raise RuntimeError("STOP identities")
 h=pd.read_csv(LIVE/"caulfield_browser_form.csv",dtype="string")
 required={"horse_code","race_date","distance","margin","finish","field_size"}
 if not required.issubset(h):raise RuntimeError("STOP form schema")
 h["prior_date"]=pd.to_datetime(h.race_date,errors="coerce")
 target=pd.Timestamp(a.date)
 h=h[h.prior_date.lt(target)].copy()
 h["margin_num"]=num(h.margin)
 h["finish_num"]=num(h.finish)
 h["distance_num"]=num(h.distance)
 h["field_num"]=num(h.field_size)
 h=h.sort_values(["horse_code","prior_date","race_code"],ascending=[True,False,False],kind="stable")
 by={str(k):v for k,v in h.groupby("horse_code",sort=False)}
 records=[]
 for r in d.itertuples(index=False):
  x={k:np.nan for k in FEATURES}
  hist=by.get(str(r.horse_code))
  if hist is not None and not hist.empty:
   # This is a deliberately incomplete feature bridge; no LVS or governed connection stats.
   recent=hist.head(5)
   margins=recent.margin_num.dropna()
   x["hist_runs"]=float(len(hist))
   x["margin_mean5"]=float(margins.mean()) if len(margins) else np.nan
   x["margin_std5"]=float(margins.std(ddof=0)) if len(margins) else np.nan
   x["margin_worst5"]=float(margins.max()) if len(margins) else np.nan
   x["margin_last1"]=float(hist.iloc[0].margin_num) if pd.notna(hist.iloc[0].margin_num) else np.nan
   x["margin_last2"]=float(hist.iloc[1].margin_num) if len(hist)>1 and pd.notna(hist.iloc[1].margin_num) else np.nan
   x["last_distance"]=float(hist.iloc[0].distance_num) if pd.notna(hist.iloc[0].distance_num) else np.nan
   x["days_since_last"]=float((target-hist.iloc[0].prior_date).days)
   if pd.notna(x["margin_last1"]) and pd.notna(x["margin_last2"]):x["margin_change_l1_l2"]=x["margin_last1"]-x["margin_last2"]
   for i,col in enumerate(("margin_per_runner_last1","margin_per_runner_last2")):
    if len(hist)>i:
     q=hist.iloc[i]
     if pd.notna(q.margin_num) and pd.notna(q.field_num) and q.field_num>0:x[col]=float(q.margin_num/q.field_num)
   finishes=hist.finish_num.dropna().head(5)
   if len(finishes):
    x["clean_finish_mean5"]=float(finishes.mean())
    x["clean_last_finish"]=float(finishes.iloc[0])
    x["clean_last_won"]=float(finishes.iloc[0]==1)
    x["clean_last_top3"]=float(finishes.iloc[0]<=3)
    x["clean_finish_hist_n"]=float(len(finishes))
  records.append({"race_id":str(r.race_id),"runner_id":str(r.race_entry_id),"race_no":str(r.race_no),"horse_name":str(r.horse_name),"historical_form_runs":0 if hist is None else len(hist),**x})
 f=pd.DataFrame(records)
 # Do not infer current distance, scratches, field-size denominator, LVS or connection rates.
 X=f[FEATURES].apply(pd.to_numeric,errors="coerce")
 if not X.notna().any().any():raise RuntimeError("STOP no observed features")
 champ=joblib.load(modelpath)
 scores=np.asarray(champ.decision_function(X),dtype=float)
 if len(scores)!=len(f) or not np.isfinite(scores).all():raise RuntimeError("STOP scorer cannot handle incomplete features")
 f["stage011_raw_score"]=scores
 f["experimental_win_probability"]=f.groupby("race_id").stage011_raw_score.transform(lambda s:np.exp(s-s.max())/np.exp(s-s.max()).sum())
 f["experimental_fair_odds"]=1/f.experimental_win_probability
 f["race_rank"]=f.groupby("race_id").experimental_win_probability.rank(method="first",ascending=False).astype(int)
 f["populated_features"]=X.notna().sum(axis=1)
 f["required_features"]=len(FEATURES)
 f["evidence_class"]="EXPERIMENTAL_INCOMPLETE_FEATURES_NOT_CERTIFIED"
 f["model_sha256"]=sha(modelpath)
 out=Path(a.output)
 if out.exists():raise RuntimeError("STOP immutable output exists; specify new --output")
 out.parent.mkdir(parents=True,exist_ok=True)
 f.sort_values(["race_no","race_rank"]).to_csv(out,index=False)
 print("EXPERIMENTAL_STAGE011_SCORED",len(f),"RUNNERS",f.race_id.nunique(),"RACES")
 print("FEATURE_COUNTS",f.populated_features.value_counts().sort_index().to_dict())
 print("OUTPUT",out)
 for race,g in f.groupby("race_no",sort=True):
  print("RACE",race)
  for row in g.nsmallest(3,"race_rank").itertuples():print(" ",row.race_rank,row.horse_name,round(row.experimental_win_probability*100,2),"%", "features",row.populated_features)
 print("WARNING NOT VALIDATED; incomplete input feature distribution; not suitable for betting or profitability claims")
if __name__=="__main__":main()
