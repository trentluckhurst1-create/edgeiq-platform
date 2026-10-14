"""Deterministic EDGEiQ opportunity engine smoke test.

Generates synthetic pre-race snapshots only, executes the engine, and checks
BACK/LAY classifications and EV arithmetic. No real markets or outcomes.
"""
from pathlib import Path
import subprocess, sys, tempfile
import pandas as pd
ENGINE=Path(__file__).with_name("run_edgeiq_opportunity_engine_v1.py")
def main():
 with tempfile.TemporaryDirectory(prefix="edgeiq_opportunity_test_") as temp:
  root=Path(temp);source=root/"synthetic.csv";output=root/"results.csv"
  base=dict(race_id="SYNTH_R1",snapshot_time="2026-10-10T00:00:00Z",scheduled_start_time="2026-10-10T03:00:00Z",model_id="SYNTHETIC",model_version="TEST",model_probability=.2,probability_certified=True,data_certified=True,back_odds=7.,lay_odds=3.5,back_available=100.,lay_available=100.,commission_rate=.05)
  rows=[]
  for name,overrides in [
   ("BACK_VALUE",dict(lay_odds=6.)),
   ("LAY_VALUE",dict(back_odds=3.)),
   ("NO_VALUE",dict(back_odds=3.,lay_odds=6.)),
   ("UNCERTIFIED",dict(probability_certified=False)),
   ("NO_LIQUIDITY",dict(back_available=0.,lay_available=0.)),
  ]:
   rows.append(dict(base,runner_id=name,**overrides))
  pd.DataFrame(rows).to_csv(source,index=False)
  cmd=[sys.executable,str(ENGINE),"--input",str(source),"--output",str(output),"--max-lay-liability","300"]
  result=subprocess.run(cmd,capture_output=True,text=True)
  if result.returncode:raise RuntimeError(result.stdout+"\n"+result.stderr)
  d=pd.read_csv(output).set_index("runner_id")
  checks={
   "BACK_VALUE":("RESEARCH_CANDIDATE","NO_VALUE"),
   "LAY_VALUE":("NO_VALUE","RESEARCH_CANDIDATE"),
   "NO_VALUE":("NO_VALUE","NO_VALUE"),
   "UNCERTIFIED":("MODEL_INCOMPLETE","MODEL_INCOMPLETE"),
   "NO_LIQUIDITY":("MARKET_OR_LIQUIDITY_FAIL","MARKET_OR_LIABILITY_FAIL"),
  }
  for key,(back,lay) in checks.items():
   actual=(d.loc[key,"back_status"],d.loc[key,"lay_status"])
   if actual!=(back,lay):raise AssertionError(f"{key}: expected {(back,lay)}, got {actual}")
  if abs(d.loc["BACK_VALUE","back_ev_per_stake"]-.34)>1e-10:raise AssertionError("BACK EV arithmetic incorrect")
  # lay odds 3.5: (1-.2)*.95/2.5-.2 = +.104 per $1 liability
  if abs(d.loc["LAY_VALUE","lay_ev_per_liability"]-.104)>1e-10:raise AssertionError("LAY EV arithmetic incorrect")
  if d.execution_authorized.astype("string").str.lower().ne("false").any():raise AssertionError("execution authorized unexpectedly")
  print("EDGEIQ OPPORTUNITY ENGINE SMOKE TEST: PASS")
  print("SYNTHETIC_CASES",len(d),"CLASSIFICATIONS_VERIFIED",len(checks)*2)
  print("BACK_EV_PER_STAKE",d.loc["BACK_VALUE","back_ev_per_stake"])
  print("LAY_EV_PER_LIABILITY",d.loc["LAY_VALUE","lay_ev_per_liability"])
  print("NO_REAL_MARKET_DATA; NO_OUTCOMES; NO_BETTING")
if __name__=="__main__":main()
