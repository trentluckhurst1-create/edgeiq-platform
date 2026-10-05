from pathlib import Path
import pandas as pd, numpy as np, json
ROOT=Path(__file__).resolve().parents[2]
D=ROOT/"outputs/research/profitability_program/lab245b"
P=D/"LAB245C5_DEPTH_RANK_RECALIBRATION.csv"
OUT=D/"LAB245C6_RACE_DISCRIMINATION.csv"; AUD=D/"LAB245C6_RACE_DISCRIMINATION.json"

def evaluate(d,pcol):
 rows=[]
 for race,g in d.groupby("_race",sort=False):
  g=g.sort_values(pcol,ascending=False).copy()
  winners=np.flatnonzero(g.y.to_numpy(int)==1)
  if len(winners)!=1: continue
  wr=int(winners[0])+1
  wp=float(g.iloc[wr-1][pcol])
  rows.append((race,wr,wp,-np.log(max(wp,1e-12))))
 z=pd.DataFrame(rows,columns=["_race","winner_rank","winner_p","race_log_loss"])
 return {
  "races":int(len(z)),
  "top1":float((z.winner_rank<=1).mean()),
  "top2":float((z.winner_rank<=2).mean()),
  "top3":float((z.winner_rank<=3).mean()),
  "mrr":float((1/z.winner_rank).mean()),
  "mean_winner_p":float(z.winner_p.mean()),
  "race_log_loss":float(z.race_log_loss.mean())
 }

def main():
 x=pd.read_csv(P,low_memory=False)
 results=[]
 for yr in [2023,2024]:
  d=x[x._year.eq(yr)].copy()
  for col in ["p_model","p_recal"]:
   m=evaluate(d,col); m.update({"year":yr,"model":col}); results.append(m)
 r=pd.DataFrame(results)
 gains=[]
 for yr in [2023,2024]:
  a=r[(r.year==yr)&(r.model=="p_model")].iloc[0]; b=r[(r.year==yr)&(r.model=="p_recal")].iloc[0]
  gains.append({"year":yr,
   "top1_gain":float(b.top1-a.top1),"top2_gain":float(b.top2-a.top2),"top3_gain":float(b.top3-a.top3),
   "mrr_gain":float(b.mrr-a.mrr),"winner_p_gain":float(b.mean_winner_p-a.mean_winner_p),
   "race_log_loss_gain":float(a.race_log_loss-b.race_log_loss)})
 r.to_csv(OUT,index=False)
 audit={"contract":"LAB245C6_RACE_DISCRIMINATION_V1",
  "purpose":"Compare retained C5 recalibration with frozen C2 probability at race decision layer",
  "chronology":"C5 predictions are forward: fit 2022 score 2023; fit 2022-23 score 2024",
  "2024_role":"OBSERVED_DIAGNOSTIC_NOT_PRISTINE_FOR_NEW_ARCHITECTURE",
  "2025_2026_opened":False,"results":results,"gains":gains}
 AUD.write_text(json.dumps(audit,indent=2))
 print(json.dumps(audit,indent=2))
 print("\nRACE DISCRIMINATION"); print(r.to_string(index=False))
 print("\nGAINS C5 MINUS C2"); print(pd.DataFrame(gains).to_string(index=False))
if __name__=="__main__": main()
