"""Research-only BACK/LAY decision board from existing Stage011 predictions.

No prices, odds, quotes, or certified probability means NO BET, never a candidate.
"""
from pathlib import Path
import argparse,json
import pandas as pd

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--predictions",default="outputs/research/selection_gate_v2/CAULFIELD_EXPERIMENTAL_STAGE011_PREDICTIONS.csv")
 p.add_argument("--output",default="outputs/research/selection_gate_v2/CAULFIELD_BET_QUALIFICATION_BOARD.csv")
 a=p.parse_args()
 src=Path(a.predictions);out=Path(a.output)
 if out.exists():raise RuntimeError("STOP immutable output exists")
 d=pd.read_csv(src,dtype={"race_id":"string","runner_id":"string"})
 required={"race_id","runner_id","horse_name","experimental_win_probability","populated_features","required_features","evidence_class"}
 if not required.issubset(d):raise RuntimeError("STOP missing fields")
 if d.empty or d.duplicated(["race_id","runner_id"]).any():raise RuntimeError("STOP duplicate identities")
 # This output is intentionally conservative. Model rankings are not qualifying bets.
 board=d[["race_id","runner_id","race_no","horse_name","experimental_win_probability","populated_features","required_features","evidence_class"]].copy()
 board["model_status"]="UNCERTIFIED_INCOMPLETE_FEATURES"
 board["back_status"]="NO_BET"
 board["lay_status"]="NO_BET"
 board["back_blockers"]="MODEL_PROBABILITY_UNCERTIFIED|NO_TIMESTAMPED_EXECUTABLE_BACK_QUOTE|NO_CERTIFIED_DEPTH"
 board["lay_blockers"]="MODEL_PROBABILITY_UNCERTIFIED|NO_TIMESTAMPED_BETFAIR_LAY_QUOTE|NO_CERTIFIED_DEPTH"
 board["back_ev"]=float("nan")
 board["lay_ev"]=float("nan")
 board["execution_authorized"]=False
 board["research_only"]=True
 out.parent.mkdir(parents=True,exist_ok=True)
 board.to_csv(out,index=False)
 print("EDGEIQ BET QUALIFICATION BOARD — RESEARCH ONLY")
 print("RUNNERS",len(board),"RACES",board.race_id.nunique())
 print("BACK",board.back_status.value_counts().to_dict(),"LAY",board.lay_status.value_counts().to_dict())
 print("OUTPUT",out)
 print("NEXT ACTION: certify Stage011 inputs and capture executable timestamped BACK/LAY quotes; then run selection gate V2")
 print("NO BETS; NO PROFITABILITY CLAIMS")
if __name__=="__main__":main()
