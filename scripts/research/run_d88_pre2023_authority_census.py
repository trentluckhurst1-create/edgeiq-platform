from pathlib import Path
import pandas as pd, os, re
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
roots=[ROOT/"public"/"data",ROOT/"outputs"/"research"]
date_names=["race_date","meeting_date","date","run_date","event_date"]
horse_names=["canonical_horse_id","horse_key","horse","horse_name","runner","runner_name","canonical_horse_name"]
print("D88_CONTRACT AUTHORITY_WIDE_PRE2023_RUNNER_CENSUS NO_MODEL NO_MARKET")
hits=[]
for base in roots:
 if not base.exists(): continue
 for p in base.rglob("*.csv"):
  try:
   size=p.stat().st_size
   if size<10000: continue
   h=pd.read_csv(p,nrows=0,low_memory=False); cols=list(h.columns); low={str(c).lower():c for c in cols}
   dc=next((low[n] for n in date_names if n in low),None); hc=next((low[n] for n in horse_names if n in low),None)
   if not dc or not hc: continue
   x=pd.read_csv(p,usecols=[dc,hc],nrows=350000,low_memory=False)
   dt=pd.to_datetime(x[dc],errors="coerce"); y20=int(dt.dt.year.eq(2020).sum());y21=int(dt.dt.year.eq(2021).sum());y22=int(dt.dt.year.eq(2022).sum())
   if y21+y22==0: continue
   nonmeta=[c for c in cols if str(c).lower() not in set(date_names+horse_names+["race_id","canonical_race_id","race_key","meeting_id","track","track_name","canonical_track_id","race_no","race_number"])]
   rec={"path":str(p.relative_to(ROOT)),"mb":round(size/1048576,2),"rows_sample":len(x),"min":str(dt.min()),"max":str(dt.max()),"y2020":y20,"y2021":y21,"y2022":y22,"ncols":len(cols),"candidate_cols":nonmeta[:80]}
   hits.append(rec)
  except Exception: pass
hits=sorted(hits,key=lambda r:(-(r["y2021"]+r["y2022"]),-r["mb"]))
print("D88_HITS",len(hits))
for r in hits[:100]: print("D88_AUTH",r)
print("D88_COMPLETE")
