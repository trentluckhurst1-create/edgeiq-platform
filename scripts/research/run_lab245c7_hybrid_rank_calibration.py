from pathlib import Path
import pandas as pd, numpy as np, json
ROOT=Path(__file__).resolve().parents[2]
D=ROOT/"outputs/research/profitability_program/lab245b"
P=D/"LAB245C5_DEPTH_RANK_RECALIBRATION.csv"
OUT=D/"LAB245C7_HYBRID_RANK_CALIBRATION.csv"; AUD=D/"LAB245C7_HYBRID_RANK_CALIBRATION.json"

def race_metrics(d,rank_col,prob_col):
 rows=[]
 for race,g in d.groupby("_race",sort=False):
  g=g.copy(); winners=g.index[g.y.eq(1)].tolist()
  if len(winners)!=1: continue
  w=winners[0]
  order=g[rank_col].rank(method="first",ascending=False)
  wr=int(order.loc[w]); wp=float(g.loc[w,prob_col])
  rows.append((race,wr,wp,-np.log(max(wp,1e-12))))
 z=pd.DataFrame(rows,columns=["_race","winner_rank","winner_p","race_log_loss"])
 return {"races":int(len(z)),"top1":float((z.winner_rank<=1).mean()),"top2":float((z.winner_rank<=2).mean()),"top3":float((z.winner_rank<=3).mean()),"mrr":float((1/z.winner_rank).mean()),"mean_winner_p":float(z.winner_p.mean()),"race_log_loss":float(z.race_log_loss.mean())}

def main():
 x=pd.read_csv(P,low_memory=False)
 results=[]
 # Predeclared hybrid: retain frozen C2 ordering, use C5 only for probability magnitude.
 # This is NOT a new fitted model and introduces no threshold search.
 for yr in [2023,2024]:
  d=x[x._year.eq(yr)].copy()
  specs=[("C2_BASE","p_model","p_model"),("C5_RECAL","p_recal","p_recal"),("HYBRID_C2_RANK_C5_PROB","p_model","p_recal")]
  for name,rcol,pcol in specs:
   m=race_metrics(d,rcol,pcol); m.update({"year":yr,"architecture":name}); results.append(m)
 r=pd.DataFrame(results); r.to_csv(OUT,index=False)
 audit={"contract":"LAB245C7_HYBRID_RANK_CALIBRATION_V1","policy":"PREDECLARED_C2_RANK_PLUS_C5_PROBABILITY_NO_THRESHOLD_SEARCH","purpose":"Preserve C2 ordering while retaining chronology-safe C5 calibration","2024_role":"OBSERVED_DIAGNOSTIC_NOT_PRISTINE","2025_2026_opened":False,"results":results}
 AUD.write_text(json.dumps(audit,indent=2)); print(json.dumps(audit,indent=2)); print("\nHYBRID AUDIT"); print(r.to_string(index=False))
if __name__=="__main__":main()
