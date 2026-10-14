"""Caulfield R5 experimental LAY value: active-field normalization, commission, liability.

Research only; screenshot quotes and incomplete Stage011 features are not certified.
"""
from pathlib import Path
import argparse
import numpy as np,pandas as pd

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--reconciliation",default="outputs/research/selection_gate_v2/CAULFIELD_R5_BETFAIR_SCREENSHOT_RECONCILIATION.csv")
 p.add_argument("--commission",type=float,default=0.05)
 p.add_argument("--liability",type=float,default=100.0)
 p.add_argument("--min-edge",type=float,default=0.03)
 p.add_argument("--output",default="outputs/research/selection_gate_v2/CAULFIELD_R5_EXPERIMENTAL_LAY_VALUE.csv")
 a=p.parse_args()
 if not 0<=a.commission<1 or a.liability<=0 or not 0<=a.min_edge<1:raise ValueError("STOP invalid policy")
 d=pd.read_csv(a.reconciliation,dtype={"race_id":"string","runner_id":"string"})
 if len(d)!=14 or d.name_match.ne("EXACT_NORMALIZED_NAME_ONLY").any():raise RuntimeError("STOP R5 active runner identity mismatch")
 if d.duplicated("runner_id").any() or d.race_id.nunique()!=1:raise RuntimeError("STOP duplicate runner or mixed race")
 p0=pd.to_numeric(d.model_probability_experimental,errors="coerce")
 odds=pd.to_numeric(d.screenshot_lay_odds,errors="coerce")
 if p0.isna().any() or (p0<=0).any() or not np.isfinite(p0).all():raise RuntimeError("STOP model probability missing")
 if odds.isna().any() or (odds<=1).any() or not np.isfinite(odds).all():raise RuntimeError("STOP invalid odds")
 d["original_model_probability"]=p0
 d["active_field_probability"]=p0/p0.sum()
 d["lay_odds"]=odds
 d["lay_stake_for_fixed_liability"]=a.liability/(odds-1)
 d["max_profit_after_commission"]=d.lay_stake_for_fixed_liability*(1-a.commission)
 d["loss_if_runner_wins"]=a.liability
 d["lay_ev_per_liability"]=(1-d.active_field_probability)*(1-a.commission)/(odds-1)-d.active_field_probability
 d["lay_expected_profit_at_liability"]=d.lay_ev_per_liability*a.liability
 d["model_break_even_lay_odds"]=1+(1-d.active_field_probability)*(1-a.commission)/d.active_field_probability
 d["indicative_edge_pass"]=d.lay_ev_per_liability.ge(a.min_edge)
 d["back_status"]="NOT_EVALUATED"
 d["lay_status"]="NO_BET_UNCERTIFIED_MODEL_AND_SCREENSHOT_QUOTES"
 d["execution_authorized"]=False
 d["commission_assumption"]=a.commission
 d["liability_assumption"]=a.liability
 d["evidence_class"]="EXPERIMENTAL_ONLY_NOT_CERTIFIED"
 out=Path(a.output)
 if out.exists():raise RuntimeError("STOP output exists; specify --output new filename")
 out.parent.mkdir(parents=True,exist_ok=True)
 d.sort_values("lay_ev_per_liability",ascending=False).to_csv(out,index=False)
 print("CAULFIELD R5 EXPERIMENTAL LAY VALUE")
 print("ACTIVE",len(d),"MODEL_PROBABILITY_SUM_BEFORE",round(float(p0.sum()),8),"AFTER",round(float(d.active_field_probability.sum()),8))
 print("COMMISSION_ASSUMED",a.commission,"LIABILITY_ASSUMED",a.liability,"MIN_EDGE",a.min_edge)
 for r in d.sort_values("lay_ev_per_liability",ascending=False).itertuples(index=False):
  print(f"{r.betfair_runner_name:24s} LAY={r.lay_odds:7.2f} P={100*r.active_field_probability:6.2f}% EV_PER_LIABILITY={r.lay_ev_per_liability:+.4f} EXPECTED_AUD={r.lay_expected_profit_at_liability:+.2f} INDICATIVE_EDGE={r.indicative_edge_pass}")
 print("OUTPUT",out)
 print("NO QUALIFIED BETS; missing feature coverage and screenshot quote provenance")
if __name__=="__main__":main()
