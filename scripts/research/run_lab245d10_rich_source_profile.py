from pathlib import Path
import pandas as pd,json
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH"); O=R/"outputs/research/profitability_program/lab245b"
files=[R/"outputs/research/model_price_diagnostics/lab231/LAB231_HISTORICAL_PERFORMANCE_FEATURES.csv",R/"outputs/research/profitability_program/lab237/LAB237_FULL_INFORMATION_INVENTORY.csv"]
out=[]
for p in files:
 print("\n"+"="*120);print(p)
 d=pd.read_csv(p,nrows=8,low_memory=False);print("COLUMNS",len(d.columns));print(list(d.columns))
 full=pd.read_csv(p,usecols=lambda c:c.lower() in {"_race","race_id","race_date","date","meeting_date","_horse","horse","horse_code","year"},low_memory=False)
 print("ROWS",len(full))
 info={"path":str(p.relative_to(R)),"columns":list(d.columns),"column_count":len(d.columns),"rows":len(full)}
 for c in full.columns:
  s=full[c]; info[c]={"non_null":int(s.notna().sum()),"unique":int(s.nunique(dropna=True)),"min":str(s.min()) if len(s.dropna()) else None,"max":str(s.max()) if len(s.dropna()) else None}
 print(json.dumps(info,indent=2));out.append(info)
(O/"LAB245D10_RICH_SOURCE_PROFILE.json").write_text(json.dumps({"contract":"LAB245D10_RICH_SOURCE_PROFILE_V1","sources":out},indent=2),encoding="utf-8")
