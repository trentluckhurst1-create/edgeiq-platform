from pathlib import Path
import os,re,json,csv
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]; DATA=Path(os.environ.get("EDGEIQ_DATA_ROOT",str(ROOT))).resolve()
D=ROOT/"outputs/research/profitability_program/lab245b"; OUT=D/"LAB245C3E_MARKET_LINEAGE_FORENSICS.txt"
NEED=("LAB146_COMPLETE_HISTORICAL_E264_MATRIX","LAB145_FULL_HISTORICAL_E264_MATRIX","starting_price_decimal","graphql_starting_price","CERTIFIED_FROZEN_MARKET_UNIVERSE","historical_market_candidate","market_archive")
SKIP={".git","node_modules",".venv","venv","__pycache__"}
def scan_text(root):
 hits=[]
 exts={".py",".ps1",".md",".txt",".json",".yaml",".yml",".toml"}
 for f in root.rglob("*"):
  if not f.is_file() or f.suffix.lower() not in exts or any(x in SKIP for x in f.parts): continue
  try:
   if f.stat().st_size>5_000_000: continue
   t=f.read_text(errors="ignore")
  except Exception: continue
  low=t.lower()
  ks=[k for k in NEED if k.lower() in low]
  if ks:
   lines=t.splitlines()
   excerpts=[]
   for i,line in enumerate(lines):
    if any(k.lower() in line.lower() for k in NEED):
     excerpts.append(f"{i+1}: {line[:500]}")
     if len(excerpts)>=12: break
   hits.append((str(f),ks,excerpts))
 return hits
def inventory():
 paths=[
 DATA/"outputs/research/model_lab_080/LAB081D2_TARGETED_MARKET_ARCHIVE_INVENTORY.csv",
 DATA/"outputs/research/model_lab_080/historical_market_candidate_assets_080b.csv",
 DATA/"outputs/research/model_lab_054/live_source_inventory_054.csv"]
 out=[]
 for p in paths:
  if p.exists():
   try:
    df=pd.read_csv(p,low_memory=False); out.append((str(p),len(df),df.columns.tolist(),df.head(30).to_dict("records")))
   except Exception as e: out.append((str(p),"ERROR",[],[str(e)]))
 return out
def main():
 roots=[DATA/"scripts",DATA/"docs",DATA/"outputs/research"]
 hits=[]
 for r in roots:
  if r.exists(): hits+=scan_text(r)
 inv=inventory()
 lines=["LAB245C3E MARKET LINEAGE FORENSICS","="*100,f"TEXT_HIT_FILES={len(hits)}"]
 for f,ks,ex in hits:
  lines+=["",f,"KEYS="+", ".join(ks)]+ex
 lines+=["","="*100,"EXISTING MARKET INVENTORIES"]
 for p,n,cols,rows in inv:
  lines+=["",p,f"ROWS={n}","COLUMNS="+repr(cols)]
  for row in rows: lines.append(json.dumps(row,default=str)[:4000])
 OUT.write_text("\n".join(lines),errors="ignore")
 print(f"TEXT_HIT_FILES={len(hits)}")
 print(f"OUTPUT={OUT}")
 print("\nTOP LINEAGE FILES")
 for f,ks,_ in hits[:80]: print(f"{f} :: {', '.join(ks)}")
 print("\nINVENTORIES")
 for p,n,cols,_ in inv: print(f"{p} ROWS={n} COLS={cols}")
if __name__=="__main__":main()
