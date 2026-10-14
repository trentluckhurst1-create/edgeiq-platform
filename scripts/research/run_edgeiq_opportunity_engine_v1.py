"""EDGEiQ selection engine v1: deterministic BACK WIN / LAY WIN qualification.

Input is a NEW, explicitly authorized opportunity snapshot CSV; no Stage011
retraining, no sealed historical outcome access, no optimization. This engine
does not claim profitability. Market inputs are isolated from Issue23.
"""
from pathlib import Path
import argparse, json, hashlib
import numpy as np
import pandas as pd

REQUIRED=["race_id","runner_id","snapshot_time","scheduled_start_time","model_id","model_version","model_probability","probability_certified","data_certified","back_odds","lay_odds","back_available","lay_available","commission_rate"]
FORBIDDEN=("result","finish_position","winner","won","starting_price","bsp","sp_","payout","profit_realized")
def flag(s):
 v=s.astype("string").str.strip().str.lower()
 if not v.isin(["true","false"]).all():raise ValueError("STOP: invalid boolean")
 return v.eq("true")
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--input",required=True,help="Explicitly supplied pre-race opportunity snapshot CSV")
 p.add_argument("--output",required=True,help="New immutable output CSV")
 p.add_argument("--min-edge",type=float,default=.03,help="Provisional net EV per $1 of liability/stake; NOT validated")
 p.add_argument("--min-available",type=float,default=50.0)
 p.add_argument("--max-lay-liability",type=float,default=100.0)
 a=p.parse_args()
 if not (0<=a.min_edge<1 and a.min_available>=0 and a.max_lay_liability>0):raise ValueError("STOP invalid risk parameters")
 src=Path(a.input);out=Path(a.output)
 if out.exists():raise FileExistsError("STOP output already exists")
 if src.resolve()==out.resolve():raise ValueError("STOP source/output same")
 d=pd.read_csv(src)
 missing=set(REQUIRED)-set(d)
 if missing:raise ValueError("STOP missing columns: "+",".join(sorted(missing)))
 if any(any(token in c.lower() for token in FORBIDDEN) for c in d.columns):raise ValueError("STOP outcomes/SP columns forbidden")
 if d.empty or d.duplicated(["race_id","runner_id","snapshot_time","model_id","model_version"]).any():raise ValueError("STOP empty/duplicate input")
 d["snapshot_time"]=pd.to_datetime(d.snapshot_time,utc=True,errors="coerce")
 d["scheduled_start_time"]=pd.to_datetime(d.scheduled_start_time,utc=True,errors="coerce")
 if d[["snapshot_time","scheduled_start_time"]].isna().any().any() or not (d.snapshot_time<d.scheduled_start_time).all():raise ValueError("STOP snapshots not pre-race")
 for c in ("probability_certified","data_certified"):d[c]=flag(d[c])
 for c in ("model_probability","back_odds","lay_odds","back_available","lay_available","commission_rate"):
  d[c]=pd.to_numeric(d[c],errors="coerce")
 if not (d.model_probability.gt(0)&d.model_probability.lt(1)).all():raise ValueError("STOP probability outside (0,1)")
 if not d.commission_rate.between(0,1,inclusive="left").all():raise ValueError("STOP commission invalid")
 for c in ("back_available","lay_available"):
  if not d[c].ge(0).all():raise ValueError("STOP available size invalid")
 d["fair_odds"]=1/d.model_probability
 # Back: stake 1, win p*(odds-1)*(1-c), lose -(1-p)
 d["back_ev_per_stake"]=d.model_probability*(d.back_odds-1)*(1-d.commission_rate)-(1-d.model_probability)
 # Lay: liability 1; lay stake 1/(odds-1), win (1-p)*stake*(1-c), lose -p
 d["lay_ev_per_liability"]=(1-d.model_probability)*(1-d.commission_rate)/(d.lay_odds-1)-d.model_probability
 valid=d.probability_certified & d.data_certified
 back_market=d.back_odds.gt(1)&d.back_available.ge(a.min_available)
 lay_market=d.lay_odds.gt(1)&d.lay_available.ge(a.min_available)&((d.lay_odds-1)*a.min_available<=a.max_lay_liability)
 d["back_status"]=np.select([~valid,~back_market,d.back_ev_per_stake.lt(a.min_edge)],["MODEL_INCOMPLETE","MARKET_OR_LIQUIDITY_FAIL","NO_VALUE"],default="RESEARCH_CANDIDATE")
 d["lay_status"]=np.select([~valid,~lay_market,d.lay_ev_per_liability.lt(a.min_edge)],["MODEL_INCOMPLETE","MARKET_OR_LIABILITY_FAIL","NO_VALUE"],default="RESEARCH_CANDIDATE")
 d["back_reason"]=np.where(~valid,"UNCERTIFIED_INPUT",np.where(~back_market,"PRICE_OR_DEPTH",np.where(d.back_ev_per_stake.lt(a.min_edge),"EDGE_BELOW_THRESHOLD","PROVISIONAL_EDGE_PASS")))
 d["lay_reason"]=np.where(~valid,"UNCERTIFIED_INPUT",np.where(~lay_market,"PRICE_DEPTH_OR_LIABILITY",np.where(d.lay_ev_per_liability.lt(a.min_edge),"EDGE_BELOW_THRESHOLD","PROVISIONAL_EDGE_PASS")))
 d["qualification_version"]="ISSUE23_OPPORTUNITY_V1_PROVISIONAL"
 d["execution_authorized"]=False
 out.parent.mkdir(parents=True,exist_ok=True)
 d.to_csv(out,index=False)
 digest=hashlib.sha256(src.read_bytes()).hexdigest()
 print("EDGEIQ OPPORTUNITY ENGINE V1 — RESEARCH ONLY")
 print("INPUT_SHA256",digest,"ROWS",len(d),"RACES",d.race_id.nunique())
 print("BACK",d.back_status.value_counts().to_dict())
 print("LAY",d.lay_status.value_counts().to_dict())
 print("OUTPUT",out)
 print("NO_LIVE_BETTING; NO_HISTORICAL_OUTCOMES; NO_STRATEGY_VALIDATION; NO_PROMOTION")
if __name__=="__main__":main()
