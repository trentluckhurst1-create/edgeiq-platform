"""Synthetic contract tests for EDGEiQ selection gate V2; no real bets or results."""
import csv
import subprocess
import sys
import tempfile
from pathlib import Path

ENGINE=Path(__file__).with_name("run_edgeiq_selection_gate_v2.py")
COLUMNS=["race_id","runner_id","snapshot_time","scheduled_start_time","model_id","model_version","model_probability","probability_certified","data_certified","commission_rate","back_odds","lay_odds","back_available","lay_available"]
BASE=dict(race_id="R1",snapshot_time="2026-10-14T01:00:00Z",scheduled_start_time="2026-10-14T02:00:00Z",model_id="synthetic",model_version="test",probability_certified="true",data_certified="true",commission_rate=".05",back_odds="4",lay_odds="4.2",back_available="100",lay_available="100")
def case(name,**kw):return {**BASE,"runner_id":name,**kw}
CASES=[
 case("BACK_VALUE",model_probability=".4",lay_odds="4.2"),
 case("LAY_VALUE",model_probability=".2",back_odds="3",lay_odds="3.5"),
 case("NO_VALUE",model_probability=".3",back_odds="2",lay_odds="4"),
 case("UNCERTIFIED",model_probability=".4",probability_certified="false"),
 case("NO_LIQUIDITY",model_probability=".4",back_available="0",lay_available="0"),
 case("LAY_LIABILITY_FAIL",model_probability=".2",back_odds="5.5",lay_odds="6"),
]
EXPECTED={
 "BACK_VALUE":("RESEARCH_CANDIDATE","NO_VALUE"),
 "LAY_VALUE":("NO_VALUE","RESEARCH_CANDIDATE"),
 "NO_VALUE":("NO_VALUE","NO_VALUE"),
 "UNCERTIFIED":("MODEL_UNCERTIFIED","MODEL_UNCERTIFIED"),
 "NO_LIQUIDITY":("MARKET_OR_LIQUIDITY_FAIL","MARKET_OR_LIABILITY_FAIL"),
 "LAY_LIABILITY_FAIL":("NO_VALUE","MARKET_OR_LIABILITY_FAIL"),
}
def main():
 with tempfile.TemporaryDirectory() as td:
  inp=Path(td)/"synthetic.csv";out=Path(td)/"classified.csv"
  with inp.open("w",newline="",encoding="utf-8") as f:
   w=csv.DictWriter(f,fieldnames=COLUMNS);w.writeheader();w.writerows(CASES)
  run=subprocess.run([sys.executable,str(ENGINE),"--input",str(inp),"--output",str(out),"--min-depth","30"],capture_output=True,text=True)
  if run.returncode:raise AssertionError(run.stdout+"\n"+run.stderr)
  with out.open(newline="",encoding="utf-8") as f:rows={r["runner_id"]:r for r in csv.DictReader(f)}
  for name,(back,lay) in EXPECTED.items():
   r=rows[name]
   assert (r["back_status"],r["lay_status"])==(back,lay),(name,r)
   assert r["execution_authorized"]=="False",name
  assert abs(float(rows["BACK_VALUE"]["back_ev_per_stake"])-0.54)<1e-10
  assert abs(float(rows["LAY_VALUE"]["lay_ev_per_liability"])-0.104)<1e-10
  print("EDGEIQ SELECTION GATE V2: PASS")
  print("SYNTHETIC_CASES",len(rows),"STATUS_ASSERTIONS",2*len(rows))
  print("BACK_EV",rows["BACK_VALUE"]["back_ev_per_stake"])
  print("LAY_EV",rows["LAY_VALUE"]["lay_ev_per_liability"])
  print("NO_REAL_ODDS; NO_OUTCOMES; NO_EXECUTION")
if __name__=="__main__":main()
