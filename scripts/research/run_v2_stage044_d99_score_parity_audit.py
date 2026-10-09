from pathlib import Path
import pandas as pd
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
print("V2_STAGE044_CONTRACT FROZEN_SCORE_ARTIFACT_INVENTORY NO_MODEL NO_MARKET_VALUES SEALED")
for label,base in [("RESEARCH",R/"outputs"/"research"),("PRODUCTION_READONLY",P/"outputs"/"research")]:
 print("V2_STAGE044_ROOT",label,"EXISTS",base.exists())
 if not base.exists():continue
 candidates=[]
 for p in base.rglob("*"):
  if not p.is_file() or p.suffix.lower() not in (".csv",".parquet",".json"):continue
  s=p.name.lower()
  if any(t in s for t in ("stage011","d99","score","prediction","probabilit")):
   candidates.append(p)
 print("V2_STAGE044_CANDIDATE_COUNT",label,len(candidates))
 for p in candidates[:100]:
  try:
   if p.suffix.lower()==".csv":cols=list(pd.read_csv(p,nrows=0).columns)
   elif p.suffix.lower()==".parquet":
    import pyarrow.parquet as pq
    cols=pq.ParquetFile(p).schema.names
   else:cols=[]
   keys=[c for c in cols if c.lower() in ("_race","canonical_race_id","_horse","canonical_horse_id","y","p","probability","p_model","race_date","year")]
   print("V2_STAGE044_CANDIDATE",label,str(p.relative_to(base)),"BYTES",p.stat().st_size,"KEYS","|".join(keys),"COLS",len(cols))
  except Exception as e:print("V2_STAGE044_HEADER_ERROR",p.name,type(e).__name__)
print("V2_STAGE044_SOURCE_CONTRACT Stage011 and D99 scripts print annual LL but do not write row-level predictions")
print("V2_STAGE044_DECISION STOP_PENDING_ORIGINAL_SCORED_ARTIFACTS_NO_REFIT")
print("V2_STAGE044_COMPLETE")
