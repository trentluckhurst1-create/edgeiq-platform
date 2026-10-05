from pathlib import Path
import os,re,json
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]; DATA=Path(os.environ.get("EDGEIQ_DATA_ROOT",str(ROOT))).resolve()
OUT=ROOT/"outputs/research/profitability_program/lab245b/LAB245C3B_MARKET_SCHEMA_INVENTORY.csv"
TOKENS=re.compile(r"(odds|price|starting|start_price|sp$|_sp|bsp|betfair|tote|dividend|fixed|market|win_price|winprice)",re.I)
IDTOK=re.compile(r"(^_?race$|race_id|raceid|race_key|^_?horse$|horse_id|horseid|runner|runner_name|horse_name)",re.I)
def main():
 rows=[]; roots=[DATA/"outputs",DATA/"data",DATA/"docs"]
 for root in roots:
  if not root.exists(): continue
  for f in root.rglob("*"):
   if not f.is_file() or f.suffix.lower() not in {".csv",".parquet",".json",".jsonl"}: continue
   try:
    if f.suffix.lower()==".csv": cols=list(pd.read_csv(f,nrows=0).columns)
    elif f.suffix.lower()==".parquet": cols=list(pd.read_parquet(f).columns)
    else:
     # lightweight JSON schema sample only
     x=pd.read_json(f,lines=f.suffix.lower()==".jsonl",nrows=5 if f.suffix.lower()==".jsonl" else None); cols=list(x.columns)
   except Exception: continue
   market=[str(c) for c in cols if TOKENS.search(str(c))]
   ids=[str(c) for c in cols if IDTOK.search(str(c))]
   if market:
    rows.append({"path":str(f),"bytes":f.stat().st_size,"market_columns":" | ".join(market),"identity_columns":" | ".join(ids),"column_count":len(cols)})
 r=pd.DataFrame(rows)
 if len(r): r=r.sort_values(["bytes","path"],ascending=[False,True])
 r.to_csv(OUT,index=False)
 print(f"MARKET_SCHEMA_FILES={len(r):,}")
 print(r.head(100).to_string(index=False) if len(r) else "NONE")
if __name__=="__main__":main()
