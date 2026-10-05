from pathlib import Path
import os,json,re
import pandas as pd, numpy as np
ROOT=Path(__file__).resolve().parents[2]; DATA=Path(os.environ.get("EDGEIQ_DATA_ROOT",str(ROOT))).resolve()
D=ROOT/"outputs/research/profitability_program/lab245b"; D.mkdir(parents=True,exist_ok=True)
P=D/"LAB245C2_FULL_FIELD_OOF_PROBABILITIES.csv"
I1=DATA/"outputs/research/model_lab_080/LAB081D2_TARGETED_MARKET_ARCHIVE_INVENTORY.csv"
I2=DATA/"outputs/research/model_lab_080/historical_market_candidate_assets_080b.csv"
OUT=D/"LAB245C3F_MARKET_ARCHIVE_CANDIDATE_RANK.csv"; AUD=D/"LAB245C3F_MARKET_ARCHIVE_CANDIDATE_RANK.json"
TOK=("sp","price","odds","market","starting","bsp","dividend","tote")
def splitcols(v):
 if pd.isna(v): return []
 s=str(v)
 return [x.strip(" []'\"") for x in re.split(r"[,|;]",s) if x.strip(" []'\"")]
def resolve(v):
 if not isinstance(v,str) or not v.strip(): return None
 p=Path(v)
 if p.exists(): return p
 q=DATA/v
 return q if q.exists() else None
def main():
 p=pd.read_csv(P,usecols=["_race","_horse","_year"],low_memory=False)
 model_races=set(p._race.astype(str)); model_horses=set(zip(p._race.astype(str),p._horse.astype(str)))
 rows=[]
 for inv,kind in [(I1,"TARGETED6287"),(I2,"CANDIDATE102")]:
  if not inv.exists(): continue
  df=pd.read_csv(inv,low_memory=False)
  for _,r in df.iterrows():
   raw=r.get("file",r.get("path","")); f=resolve(raw)
   if f is None or not f.is_file() or f.suffix.lower() not in {".csv",".parquet"}: continue
   price=splitcols(r.get("price_cols",r.get("price_columns","")))
   if not price: continue
   ident=[]
   for c in ("race_cols","horse_cols","identity_columns"):
    ident+=splitcols(r.get(c,""))
   # prioritize files that inventory says contain race/horse identities
   score=sum(any(t in x.lower() for x in ident) for t in ("race","horse","runner"))
   rows.append({"inventory":kind,"path":str(f),"inventory_rows":r.get("rows",None),"price_columns":"|".join(price),"identity_columns":"|".join(ident),"identity_hint_score":score,"bytes":f.stat().st_size})
 cand=pd.DataFrame(rows).drop_duplicates("path")
 if cand.empty: raise RuntimeError("No readable inventoried market candidates")
 # Rank without loading every huge asset: identity hints, row count, size, explicit SP/price semantics.
 cand["inventory_rows_num"]=pd.to_numeric(cand.inventory_rows,errors="coerce").fillna(0)
 cand["semantic_score"]=cand.price_columns.str.lower().apply(lambda s:sum(t in s for t in ("starting","_sp","closing","bsp","decimal_price","odds")))
 cand["priority_score"]=cand.identity_hint_score*100+cand.semantic_score*10+np.log1p(cand.inventory_rows_num)
 cand=cand.sort_values(["priority_score","inventory_rows_num","bytes"],ascending=False)
 cand.to_csv(OUT,index=False)
 audit={"contract_version":"LAB245C3F_MARKET_ARCHIVE_CANDIDATE_RANK_V1","inventory_6287_rows":int(len(pd.read_csv(I1))) if I1.exists() else 0,"inventory_102_rows":int(len(pd.read_csv(I2))) if I2.exists() else 0,"resolved_price_candidates":int(len(cand)),"top_candidates":cand.head(30).to_dict("records"),"holdout_2025_2026_opened":False}
 AUD.write_text(json.dumps(audit,indent=2,default=str))
 print(f"RESOLVED_PRICE_CANDIDATES={len(cand)}")
 print("\nTOP 30")
 print(cand[["inventory","inventory_rows_num","bytes","price_columns","identity_columns","path"]].head(30).to_string(index=False))
 print(f"\nOUTPUT={OUT}")
if __name__=="__main__":main()
