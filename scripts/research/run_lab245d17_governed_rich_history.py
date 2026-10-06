from pathlib import Path
import pandas as pd
R=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM"); W=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
C=R/"outputs/research/model_lab_031/certified_current_race_context_031.csv"
B=W/"outputs/research/profitability_program/lab245b/LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
c=pd.read_csv(C,low_memory=False); b=pd.read_csv(B,low_memory=False)
print("BRIDGE_COLS",list(b.columns))
def norm(s): return s.astype(str).str.strip().str.lower()
br="canonical_race_id" if "canonical_race_id" in b else "_race"; bh="canonical_horse_id" if "canonical_horse_id" in b else "_horse"
b["_jr"]=norm(b[br]); b["_jh"]=norm(b[bh]); c["_jr"]=norm(c["canonical_race_id"]); c["_jh"]=norm(c["canonical_horse_id"])
ctx=c[["_jr","_jh","current_class_group","current_condition_group","current_distance_metres"]].drop_duplicates(["_jr","_jh"])
j=b.merge(ctx,on=["_jr","_jh"],how="left",indicator=True)
print("BRIDGE_ROWS",len(b),"JOINED",int((j["_merge"]=="both").sum()),"COVERAGE",round(float((j["_merge"]=="both").mean()),6))
print("BRIDGE_RACES",b["_jr"].nunique(),"JOINED_RACES",j.loc[j["_merge"]=="both","_jr"].nunique())
for col in ["current_class_group","current_condition_group"]:
 print(col,"NONNULL",int(j[col].notna().sum()),"UNIQUE",j[col].nunique(dropna=True))
for y in sorted(pd.to_numeric(b["_year"],errors="coerce").dropna().astype(int).unique()):
 z=j[pd.to_numeric(j["_year"],errors="coerce")==y]; print("YEAR",y,"ROWS",len(z),"JOIN",int((z["_merge"]=="both").sum()),"COV",round(float((z["_merge"]=="both").mean()),6),"RACES",z["_jr"].nunique())
