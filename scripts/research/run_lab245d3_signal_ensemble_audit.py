from pathlib import Path
import pandas as pd, numpy as np, json, math
ROOT=Path(__file__).resolve().parents[2]; D=ROOT/"outputs/research/profitability_program/lab245b"
P=D/"LAB245D2_DIRECT_WIN_OOF.csv"; B=D/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
OUT=D/"LAB245D3_SIGNAL_ENSEMBLE_AUDIT.csv"; SEG=D/"LAB245D3_SEGMENTS.csv"; AUD=D/"LAB245D3_SIGNAL_ENSEMBLE_AUDIT.json"

def met(z,score):
 rr=[]
 for _,g in z.groupby("_race",sort=False):
  w=np.flatnonzero(g.y.to_numpy()==1)
  if len(w)!=1: continue
  raw=g[score].to_numpy(float); p=np.clip(raw,1e-12,None); p=p/p.sum()
  order=pd.Series(raw,index=g.index).rank(method="first",ascending=False); rank=int(order.iloc[w[0]])
  rr.append((rank,float(p[w[0]]),-math.log(max(float(p[w[0]]),1e-12))))
 a=np.array(rr,float)
 return {"races":len(a),"top1":np.mean(a[:,0]<=1),"top2":np.mean(a[:,0]<=2),"top3":np.mean(a[:,0]<=3),"mrr":np.mean(1/a[:,0]),"race_log_loss":np.mean(a[:,2])}

def main():
 o=pd.read_csv(P,low_memory=False)
 # D2 OOF contains one row/model. Wide scores for exact runner identity.
 w=o.pivot_table(index=["_race","_horse","_year","y"],columns="model",values="raw",aggfunc="first").reset_index()
 h="HGB_WIN"; l="LOGIT_L2_C03"
 rows=[]
 for yr in [2022,2023,2024]:
  d=w[w._year.eq(yr)].copy()
  for a in [0,.25,.5,.75,1]:
   c=f"blend_{a:.2f}"; d[c]=a*d[h]+(1-a)*d[l]
   rows.append({"year":yr,"model":c,**met(d,c)})
 pd.DataFrame(rows).to_csv(OUT,index=False)
 # Segment HGB vs logistic by winner history depth and field size using bridge metadata.
 b=pd.read_csv(B,usecols=["_race","_horse","hist_runs"],low_memory=False)
 q=w.merge(b,on=["_race","_horse"],how="left"); q["hist_bucket"]=pd.cut(q.hist_runs,[-1,0,1,2,4,9,np.inf],labels=["0","1","2","3-4","5-9","10+"])
 fs=q.groupby("_race")["_horse"].transform("size"); q["field_bucket"]=pd.cut(fs,[0,8,12,16,np.inf],labels=["<=8","9-12","13-16","17+"])
 seg=[]
 for yr in [2022,2023,2024]:
  d=q[q._year.eq(yr)]
  for kind,col in [("winner_hist","hist_bucket"),("field_size","field_bucket")]:
   for val in d[col].dropna().unique():
    races=[]
    for race,g in d.groupby("_race"):
     wi=g.index[g.y.eq(1)]
     if len(wi)==1 and str(g.loc[wi[0],col])==str(val): races.append(race)
    s=d[d._race.isin(races)]
    if len(races)>=20:
     for m in [h,l]:
      z=met(s,m); seg.append({"year":yr,"segment_type":kind,"segment":str(val),"model":m,**z})
 pd.DataFrame(seg).to_csv(SEG,index=False)
 r=pd.DataFrame(rows); dev=r[r.year.isin([2022,2023])].groupby("model").agg(top1=("top1","mean"),mrr=("mrr","mean"),top3=("top3","mean"),race_log_loss=("race_log_loss","mean")).reset_index().sort_values(["top1","mrr"],ascending=False)
 audit={"contract":"LAB245D3_SIGNAL_ENSEMBLE_AUDIT_V1","purpose":"Test HGB/logit complementarity and locate winner-signal segments","blend_weight_definition":"weight_on_HGB_WIN","selection_years":[2022,2023],"2024_role":"OBSERVED_DIAGNOSTIC_ONLY","2025_2026_opened":False,"market_used":False,"dev_blend_leaderboard":dev.to_dict("records")}
 AUD.write_text(json.dumps(audit,indent=2)); print(r.to_string(index=False)); print("\nDEV BLENDS"); print(dev.to_string(index=False)); print("\nSEGMENTS"); print(pd.DataFrame(seg).to_string(index=False)); print("\n"+json.dumps(audit,indent=2))
if __name__=="__main__": main()
