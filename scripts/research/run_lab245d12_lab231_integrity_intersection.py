from pathlib import Path
import pandas as pd,numpy as np,json,re
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH");O=R/"outputs/research/profitability_program/lab245b"
P231=R/"outputs/research/model_price_diagnostics/lab231/LAB231_HISTORICAL_PERFORMANCE_FEATURES.csv";PB=O/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
d=pd.read_csv(P231,low_memory=False);b=pd.read_csv(PB,low_memory=False)
features=[c for c in d.columns if c.startswith("h231_")]
susp=[c for c in features if re.search(r"(target|outcome|result|winner|win_|finish_current|sp|odds|price|market|bsp|future|post)",c,re.I)]
keys=["_race","_horse"];x=d.merge(b[keys+["_year","target_finish_position"]],on=keys,how="inner",suffixes=("_231","_b"))
x["y231"]=pd.to_numeric(x["_y"],errors="coerce").fillna(0).astype(int);x["yb"]=(pd.to_numeric(x["target_finish_position"],errors="coerce")==1).astype(int)
race231=set(d.loc[d._year.between(2022,2024),"_race"]);raceb=set(b.loc[b._year.between(2022,2024),"_race"])
audit={"contract":"LAB245D12_LAB231_INTEGRITY_INTERSECTION_V1","lab231_rows":len(d),"bridge_rows":len(b),"joined_runner_rows":len(x),"joined_races":int(x._race.nunique()),"outcome_disagreements":int((x.y231!=x.yb).sum()),"suspicious_feature_names":susp,"features":features,"race_counts":{},"2025_2026_opened":False}
for yr in [2022,2023,2024]:
 a=set(d.loc[d._year==yr,"_race"]);bb=set(b.loc[b._year==yr,"_race"]);audit["race_counts"][str(yr)]={"lab231":len(a),"bridge":len(bb),"intersection":len(a&bb),"lab231_share_of_bridge":len(a&bb)/len(bb) if bb else None}
print(json.dumps(audit,indent=2));(O/"LAB245D12_LAB231_INTEGRITY_INTERSECTION.json").write_text(json.dumps(audit,indent=2))
