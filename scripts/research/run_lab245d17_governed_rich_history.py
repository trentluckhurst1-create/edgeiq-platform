from pathlib import Path
import pandas as pd
R=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
W=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
C=R/"outputs/research/model_lab_031/certified_current_race_context_031.csv"
B=W/"outputs/research/profitability_program/lab245b/LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
print("CONTEXT_EXISTS",C.exists(),"SIZE",C.stat().st_size if C.exists() else None)
print("BRIDGE_EXISTS",B.exists(),"SIZE",B.stat().st_size if B.exists() else None)
if C.exists():
 c=pd.read_csv(C,low_memory=False); print("CONTEXT_ROWS",len(c)); print("CONTEXT_COLS",list(c.columns))
if B.exists() and C.exists():
 b=pd.read_csv(B,low_memory=False)
 def norm(x): return x.astype(str).str.strip().str.lower()
 for d in (b,c):
  d["_r"]=norm(d["canonical_race_id"]); d["_h"]=norm(d["canonical_horse_id"])
 j=b.merge(c.drop_duplicates(["_r","_h"]),on=["_r","_h"],how="left",suffixes=("","_ctx"),indicator=True)
 print("BRIDGE_ROWS",len(b),"JOINED",int((j["_merge"]=="both").sum()),"COVERAGE",float((j["_merge"]=="both").mean()))
 print("BRIDGE_RACES",b["_r"].nunique(),"JOINED_RACES",j.loc[j["_merge"]=="both","_r"].nunique())
 for col in ["class","condition","race_class_group","track_condition_group"]:
  if col in j: print(col,"NONNULL",int(j[col].notna().sum()),"UNIQUE",j[col].nunique(dropna=True))
