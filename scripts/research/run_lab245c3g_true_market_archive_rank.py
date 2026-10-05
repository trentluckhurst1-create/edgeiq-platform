from pathlib import Path
import os,re,json
import pandas as pd, numpy as np
ROOT=Path(__file__).resolve().parents[2]; DATA=Path(os.environ.get("EDGEIQ_DATA_ROOT",str(ROOT))).resolve()
D=ROOT/"outputs/research/profitability_program/lab245b"; D.mkdir(parents=True,exist_ok=True)
I1=DATA/"outputs/research/model_lab_080/LAB081D2_TARGETED_MARKET_ARCHIVE_INVENTORY.csv"
I2=DATA/"outputs/research/model_lab_080/historical_market_candidate_assets_080b.csv"
OUT=D/"LAB245C3G_TRUE_MARKET_ARCHIVE_RANK.csv"; AUD=D/"LAB245C3G_TRUE_MARKET_ARCHIVE_RANK.json"
PRICE_PAT=re.compile(r"(^|_)(starting_price(_decimal)?|sp|bsp|closing_(odds|price|sp)|decimal_price|win_(odds|price)|fixed_(odds|price)|tote_(odds|price)|market_(odds|price))($|_)",re.I)
RACE_PAT=re.compile(r"(^|_)(race|race_id|race_key|raceid|race_no|race_number)($|_)",re.I)
HORSE_PAT=re.compile(r"(^|_)(horse|horse_name|runner|runner_id|runner_name|horse_code|canonical_horse_id)($|_)",re.I)
def toks(v):
 if pd.isna(v): return []
 return [x.strip(" []'\"") for x in re.split(r"[,|;]",str(v)) if x.strip(" []'\"")]
def resolve(v):
 p=Path(str(v))
 if p.exists(): return p
 q=DATA/str(v)
 return q if q.exists() else None
def main():
 rec=[]
 for inv,kind in [(I1,"TARGETED6287"),(I2,"CANDIDATE102")]:
  if not inv.exists(): continue
  df=pd.read_csv(inv,low_memory=False)
  for _,r in df.iterrows():
   f=resolve(r.get("file",r.get("path","")))
   if f is None or not f.is_file() or f.suffix.lower() not in {".csv",".parquet"}: continue
   pc=toks(r.get("price_cols",r.get("price_columns","")))
   ic=[]
   for c in ("race_cols","horse_cols","identity_columns"): ic+=toks(r.get(c,""))
   truep=[x for x in pc if PRICE_PAT.search(x)]
   race=[x for x in ic if RACE_PAT.search(x)]
   horse=[x for x in ic if HORSE_PAT.search(x)]
   if not truep or not race or not horse: continue
   rec.append({"inventory":kind,"path":str(f),"inventory_rows":r.get("rows",None),"true_price_columns":"|".join(truep),"race_identity":"|".join(race),"horse_identity":"|".join(horse),"bytes":f.stat().st_size})
 c=pd.DataFrame(rec).drop_duplicates("path")
 if c.empty: raise RuntimeError("No true market candidates")
 c["rows_num"]=pd.to_numeric(c.inventory_rows,errors="coerce").fillna(0)
 def sem(s):
  z=s.lower(); return 100*("starting_price_decimal" in z)+90*("closing" in z)+80*("_sp" in z or z=="sp")+70*("bsp" in z)+50*("decimal_price" in z)+20*("odds" in z)
 c["semantic_score"]=c.true_price_columns.apply(sem)
 c=c.sort_values(["semantic_score","rows_num","bytes"],ascending=False)
 c.to_csv(OUT,index=False)
 audit={"contract_version":"LAB245C3G_TRUE_MARKET_ARCHIVE_RANK_V1","true_market_candidates":int(len(c)),"top50":c.head(50).to_dict("records"),"holdout_2025_2026_opened":False}
 AUD.write_text(json.dumps(audit,indent=2,default=str))
 print(f"TRUE_MARKET_CANDIDATES={len(c)}")
 print(c[["inventory","rows_num","bytes","true_price_columns","race_identity","horse_identity","path"]].head(50).to_string(index=False))
 print(f"\nOUTPUT={OUT}")
if __name__=="__main__":main()
