"""EDGEiQ independent BACK/LAY qualification engine, research-only.

Uses point-in-time probability and market quote observations. No outcome access,
no historical return claim and no execution. Designed for prospective logging.
"""
import argparse
import json
from pathlib import Path
import pandas as pd

REQUIRED=["race_id","runner_id","snapshot_time","scheduled_start_time","model_id","model_version","model_probability","probability_certified","data_certified","commission_rate","back_odds","lay_odds","back_available","lay_available"]
def truth(x):return str(x).strip().lower() in ("true","1","yes")
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--input",required=True,type=Path)
 p.add_argument("--output",required=True,type=Path)
 p.add_argument("--min-edge",type=float,default=0.03)
 p.add_argument("--min-depth",type=float,default=50)
 p.add_argument("--max-lay-liability",type=float,default=100)
 a=p.parse_args()
 if a.output.exists():raise ValueError("STOP: output already exists")
 if not (0<a.min_edge<1 and a.min_depth>0 and a.max_lay_liability>0):raise ValueError("STOP: invalid policy")
 h=pd.read_csv(a.input,nrows=0).columns.tolist()
 forbidden=[c for c in h if c.lower() in ("outcome","won","winner","sp","bsp","result","finish_position")]
 if forbidden:raise ValueError("STOP: outcomes or closing prices in input: "+str(forbidden))
 missing=set(REQUIRED)-set(h)
 if missing:raise ValueError("STOP: missing columns "+str(sorted(missing)))
 d=pd.read_csv(a.input,dtype="string")
 for c in ["model_probability","commission_rate","back_odds","lay_odds","back_available","lay_available"]:
  d[c]=pd.to_numeric(d[c],errors="coerce")
 t=pd.to_datetime(d.snapshot_time,utc=True,errors="coerce")
 s=pd.to_datetime(d.scheduled_start_time,utc=True,errors="coerce")
 if (t.isna()|s.isna()|(t>=s)).any():raise ValueError("STOP: invalid or non-prejump timestamps")
 if d[["race_id","runner_id","snapshot_time","model_id","model_version"]].duplicated().any():raise ValueError("STOP: duplicate runner snapshot")
 if (d.model_probability.le(0)|d.model_probability.ge(1)|d.model_probability.isna()|d.commission_rate.lt(0)|d.commission_rate.ge(1)|d.commission_rate.isna()).any():raise ValueError("STOP: invalid probability or commission")
 if (d[["back_available","lay_available"]].lt(0).any().any()):raise ValueError("STOP: negative depth")
 certified=d.probability_certified.map(truth)&d.data_certified.map(truth)
 back_ok=d.back_odds.gt(1)&d.back_available.ge(a.min_depth)
 lay_ok=d.lay_odds.gt(1)&d.lay_available.ge(a.min_depth)&((a.min_depth*(d.lay_odds-1)).le(a.max_lay_liability))
 back_ev=d.model_probability*(d.back_odds-1)*(1-d.commission_rate)-(1-d.model_probability)
 lay_ev=(1-d.model_probability)*(1-d.commission_rate)/(d.lay_odds-1)-d.model_probability
 result=pd.DataFrame({"race_id":d.race_id,"runner_id":d.runner_id,"snapshot_time":d.snapshot_time,"model_id":d.model_id,"model_version":d.model_version,"model_probability":d.model_probability,"back_odds":d.back_odds,"lay_odds":d.lay_odds,"back_ev_per_stake":back_ev,"lay_ev_per_liability":lay_ev})
 result["back_status"]="NO_VALUE"
 result.loc[~back_ok,"back_status"]="MARKET_OR_LIQUIDITY_FAIL"
 result.loc[back_ok&back_ev.ge(a.min_edge),"back_status"]="RESEARCH_CANDIDATE"
 result.loc[~certified,"back_status"]="MODEL_UNCERTIFIED"
 result["lay_status"]="NO_VALUE"
 result.loc[~lay_ok,"lay_status"]="MARKET_OR_LIABILITY_FAIL"
 result.loc[lay_ok&lay_ev.ge(a.min_edge),"lay_status"]="RESEARCH_CANDIDATE"
 result.loc[~certified,"lay_status"]="MODEL_UNCERTIFIED"
 result["execution_authorized"]=False
 a.output.parent.mkdir(parents=True,exist_ok=True)
 result.to_csv(a.output,index=False)
 print("EDGEIQ QUALIFICATION GATE V2")
 print("ROWS",len(result),"BACK",result.back_status.value_counts().to_dict(),"LAY",result.lay_status.value_counts().to_dict())
 print("OUTPUT",a.output)
 print("RESEARCH_ONLY; NO_EXECUTION; NO_PROFITABILITY_CLAIM")
if __name__=="__main__":main()
