"""Reconcile screenshot-transcribed Betfair Caulfield R5 runners against EDGEiQ identities.

No fuzzy automatic matches. Produces a reviewable exact-name join and a
fail-closed qualification state. Screenshot quotes are indicative, not certified.
"""
from pathlib import Path
import argparse,re,unicodedata
import pandas as pd
RUNNERS=[
 ("Battle Cry",30.0),("Buccleuch",4.0),("Grecian Destiny",1000.0),
 ("Space Rider",26.0),("Fiorenot",10.5),("Hell Rip",20.0),
 ("Jett Smash",5.6),("Markdel",26.0),("Chase Your Dreams",270.0),
 ("Villasaurus",110.0),("Real Class",75.0),("Test Of Love",210.0),
 ("Presser",32.0),("Fundamental Nature",6.4)]
# Screenshot shows Fervia as a non-runner; excluded.
def norm(s):
 s=unicodedata.normalize("NFKD",str(s)).casefold()
 return re.sub(r"[^a-z0-9]","",s)
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--predictions",default="outputs/research/selection_gate_v2/CAULFIELD_EXPERIMENTAL_STAGE011_PREDICTIONS.csv")
 p.add_argument("--output",default="outputs/research/selection_gate_v2/CAULFIELD_R5_BETFAIR_SCREENSHOT_RECONCILIATION.csv")
 a=p.parse_args()
 d=pd.read_csv(a.predictions,dtype={"race_id":"string","runner_id":"string","race_no":"string"})
 d=d[d.race_no.eq("5")].copy()
 if d.empty:raise RuntimeError("STOP no model R5")
 if d.horse_name.map(norm).duplicated().any():raise RuntimeError("STOP duplicate model names")
 index={norm(r.horse_name):r for r in d.itertuples(index=False)}
 rows=[]
 for name,odds in RUNNERS:
  r=index.get(norm(name))
  rows.append({"betfair_runner_name":name,"screenshot_lay_odds":odds,
   "model_runner_name":"" if r is None else r.horse_name,
   "race_id":"" if r is None else r.race_id,
   "runner_id":"" if r is None else r.runner_id,
   "model_probability_experimental":float("nan") if r is None else r.experimental_win_probability,
   "model_features_present":0 if r is None else int(r.populated_features),
   "name_match":"UNMATCHED" if r is None else "EXACT_NORMALIZED_NAME_ONLY",
   "lay_qualification":"NO_BET",
   "blockers":"UNCERTIFIED_MODEL|SCREENSHOT_NOT_EXECUTABLE_CERTIFIED_QUOTE|UNVERIFIED_MARKET_IDENTITY"+("|NO_NAME_MATCH" if r is None else "")})
 out=Path(a.output)
 if out.exists():raise RuntimeError("STOP output exists")
 out.parent.mkdir(parents=True,exist_ok=True)
 pd.DataFrame(rows).to_csv(out,index=False)
 print("CAULFIELD R5 SCREENSHOT RECONCILIATION")
 print("MODEL_R5_RUNNERS",len(d),"SCREENSHOT_ACTIVE_RUNNERS",len(rows))
 print("EXACT_NAME_MATCHES",sum(x["name_match"]!="UNMATCHED" for x in rows))
 for x in rows:
  print(x["betfair_runner_name"],"LAY",x["screenshot_lay_odds"],"MATCH",x["model_runner_name"] or "NONE")
 print("OUTPUT",out)
 print("ALL NO_BET: identity and quote provenance unverified; model incomplete")
if __name__=="__main__":main()
