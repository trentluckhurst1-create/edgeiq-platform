from pathlib import Path
import pandas as pd, numpy as np, json, math
ROOT=Path(__file__).resolve().parents[2]; D=ROOT/"outputs/research/profitability_program/lab245b"
P=D/"LAB245D2_DIRECT_WIN_OOF.csv"; B=D/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
OUT=D/"LAB245D4_DEPTH_EXPERT_ROUTER.csv"; AUD=D/"LAB245D4_DEPTH_EXPERT_ROUTER.json"

def metrics(z,c):
 rr=[]
 for _,g in z.groupby("_race",sort=False):
  w=np.flatnonzero(g.y.to_numpy()==1)
  if len(w)!=1: continue
  s=g[c].to_numpy(float); p=np.clip(s,1e-12,None); p/=p.sum()
  rank=int(pd.Series(s).rank(method="first",ascending=False).iloc[w[0]])
  rr.append((rank,p[w[0]],-math.log(max(p[w[0]],1e-12))))
 a=np.array(rr,float)
 return {"races":len(a),"top1":np.mean(a[:,0]<=1),"top2":np.mean(a[:,0]<=2),"top3":np.mean(a[:,0]<=3),"mrr":np.mean(1/a[:,0]),"race_log_loss":np.mean(a[:,2])}

def main():
 o=pd.read_csv(P,low_memory=False)
 w=o.pivot_table(index=["_race","_horse","_year","y"],columns="model",values="raw",aggfunc="first").reset_index()
 b=pd.read_csv(B,usecols=["_race","_horse","hist_runs"],low_memory=False)
 x=w.merge(b,on=["_race","_horse"],how="left")
 H="HGB_WIN"; L="LOGIT_L2_C03"
 # Predeclared from D3 dev structure only: logistic for lightly raced 1-2; HGB otherwise.
 # Also test conservative 1-only and 2-only routers as sensitivity, not post-hoc 2024 selection.
 x["HGB_ONLY"]=x[H]
 x["LOGIT_ONLY"]=x[L]
 x["ROUTER_1_2"]=np.where(x.hist_runs.isin([1,2]),x[L],x[H])
 x["ROUTER_1"]=np.where(x.hist_runs.eq(1),x[L],x[H])
 x["ROUTER_2"]=np.where(x.hist_runs.eq(2),x[L],x[H])
 rows=[]
 for yr in [2022,2023,2024]:
  d=x[x._year.eq(yr)]
  for c in ["HGB_ONLY","LOGIT_ONLY","ROUTER_1_2","ROUTER_1","ROUTER_2"]:
   rows.append({"year":yr,"model":c,**metrics(d,c)})
 r=pd.DataFrame(rows); r.to_csv(OUT,index=False)
 dev=r[r.year.isin([2022,2023])].groupby("model").agg(top1=("top1","mean"),mrr=("mrr","mean"),top3=("top3","mean"),race_log_loss=("race_log_loss","mean")).reset_index().sort_values(["top1","mrr"],ascending=False)
 audit={"contract":"LAB245D4_DEPTH_EXPERT_ROUTER_V1","hypothesis":"History depth determines which direct-win expert is strongest","router_policy":"LOGIT_FOR_HIST1_2_HGB_OTHERWISE","sensitivity":["LOGIT_HIST1_ONLY","LOGIT_HIST2_ONLY"],"selection_years":[2022,2023],"2024_role":"OBSERVED_DIAGNOSTIC_ONLY","2025_2026_opened":False,"market_used":False,"dev_leaderboard":dev.to_dict("records")}
 AUD.write_text(json.dumps(audit,indent=2)); print(r.to_string(index=False)); print("\nDEV ROUTERS"); print(dev.to_string(index=False)); print("\n"+json.dumps(audit,indent=2))
if __name__=="__main__":main()
