from pathlib import Path
import pandas as pd
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
print("V2_STAGE042_CONTRACT SOURCE_IDENTITY_BRIDGE_DIAGNOSTIC NO_MODEL NO_FUZZY NO_MARKET SEALED")
paths={
"warehouse":R/"outputs"/"research"/"model_v2"/"stage006"/"V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv",
"official":P/"public"/"data"/"edgeiq_official_runs_master_v1.csv",
"canonical_master":P/"public"/"data"/"edgeiq_canonical_horse_master_v2.csv",
"canonical_alias":P/"public"/"data"/"edgeiq_canonical_horse_alias_v2.csv",
"historical_bridge":P/"public"/"data"/"edgeiq_current_historical_horse_identity_bridge_v2.csv",
"current_crosswalk":P/"public"/"data"/"edgeiq_current_horse_identity_crosswalk_v1.csv",
"ra_rcom_bridge":P/"public"/"data"/"edgeiq_ra_to_rcom_horse_identity_bridge_v1.csv",
}
for label,p in paths.items():
 print("V2_STAGE042_SOURCE",label,"EXISTS",p.exists())
 if p.exists():
  h=pd.read_csv(p,nrows=0)
  print("V2_STAGE042_COLUMNS",label,"|".join(h.columns))
  ids=[c for c in h.columns if any(k in c.lower() for k in ("horse","identity","source_system","source_id","name"))]
  print("V2_STAGE042_IDENTITY_FIELDS",label,"|".join(ids))
  if label in ("warehouse","official","canonical_master","canonical_alias","historical_bridge","current_crosswalk","ra_rcom_bridge"):
   cols=[c for c in ids if c in h.columns][:8]
   if cols:
    t=pd.read_csv(p,usecols=cols,low_memory=False)
    if label=="warehouse":
     print("V2_STAGE042_WAREHOUSE_ROWS",len(t))
     print("V2_STAGE042_WAREHOUSE_HORSE_SAMPLES",t["_horse"].dropna().astype(str).head(6).tolist() if "_horse" in t else [])
    elif label=="official":
     print("V2_STAGE042_OFFICIAL_HORSE_KEY_SAMPLES",t["horse_key"].dropna().astype(str).head(6).tolist() if "horse_key" in t else [])
    else:print("V2_STAGE042_ROWS",label,len(t))
print("V2_STAGE042_DECISION SCHEMA_INSPECTION_ONLY_NO_BRIDGE_CERTIFIED")
print("V2_STAGE042_COMPLETE")
