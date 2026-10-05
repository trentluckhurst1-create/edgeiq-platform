from pathlib import Path
import os
import json
import hashlib
from collections import defaultdict
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
DATA_ROOT=Path(os.environ.get("EDGEIQ_DATA_ROOT",str(ROOT))).resolve()
SOURCE=ROOT/"outputs/research/profitability_program/lab245b/LAB245B_WAREHOUSE_RUNNER_LVS.csv"
OUTDIR=ROOT/"outputs/research/profitability_program/lab245b"
OUT=OUTDIR/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
SOURCE_MANIFEST=SOURCE.with_suffix(".manifest.json")
OUT_MANIFEST=OUT.with_suffix(".manifest.json")
EXPECTED_CONTRACT="LAB245B_STRICT_PIT_LVS_V12_QUARANTINE_LINEAGE_COMPLETE_V1_LENGTH_CONVERSION_TRACK_DISTANCE_CONDITION_MIN20"
NEED=["canonical_race_id","canonical_horse_id","race_date","distance_metres","finish_position","finish_margin","runner_lvs","field_size"]

def stats(a,n):
 x=np.asarray(a[-n:],dtype=float)
 x=x[np.isfinite(x)]
 if not len(x): return (np.nan,np.nan,np.nan)
 return (float(np.mean(x)),float(np.median(x)),float(np.std(x)))

def main():
 OUTDIR.mkdir(parents=True,exist_ok=True)
 if not SOURCE.exists(): raise FileNotFoundError(SOURCE)
 if not SOURCE_MANIFEST.exists(): raise FileNotFoundError(SOURCE_MANIFEST)
 sm=json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
 if sm.get("contract_version")!=EXPECTED_CONTRACT or sm.get("pit_policy")!="STRICT_DATE_LT_TARGET_DATE": raise RuntimeError("LAB245B compact bridge source lineage mismatch")
 h=hashlib.sha256()
 with SOURCE.open("rb") as fh:
  for b in iter(lambda:fh.read(16*1024*1024),b""): h.update(b)
 source_sha=h.hexdigest()
 if source_sha!=sm.get("output_sha256"): raise RuntimeError("LAB245B compact bridge source hash mismatch")
 d=pd.read_csv(SOURCE,usecols=NEED,low_memory=False)
 for c in ["canonical_race_id","canonical_horse_id"]: d[c]=d[c].astype("string").str.strip()
 d["race_date"]=pd.to_datetime(d["race_date"],errors="coerce")
 for c in ["distance_metres","finish_position","finish_margin","field_size","runner_lvs"]: d[c]=pd.to_numeric(d[c],errors="coerce")
 d=d.dropna(subset=["canonical_race_id","canonical_horse_id","race_date"])
 represented=d.groupby("canonical_race_id")["canonical_horse_id"].nunique().to_dict()
 d=d.sort_values(["canonical_horse_id","race_date","canonical_race_id"],kind="stable")
 rows=[]
 for horse,g in d.groupby("canonical_horse_id",sort=False):
  hist=[]
  for dt,day in g.groupby("race_date",sort=True):
   # Freeze history before scoring any same-date row.
   lvs=[x["lvs"] for x in hist if np.isfinite(x["lvs"])]
   margins=[x["margin"] for x in hist if np.isfinite(x["margin"])]
   poss=[x["pos"] for x in hist if np.isfinite(x["pos"])]
   dates=[x["date"] for x in hist]
   l3=stats(lvs,3); l5=stats(lvs,5)
   m5=stats(margins,5); p5=stats(poss,5)
   for r in day.itertuples(index=False):
    year=int(dt.year)
    if 2021<=year<=2024:
     rec={"_race":r.canonical_race_id,"_horse":horse,"_year":year,"race_date":dt.date().isoformat(),
          "target_lvs":r.runner_lvs,"target_finish_position":r.finish_position,"target_field_size":r.field_size,"represented_field_size":represented.get(r.canonical_race_id),"current_distance":r.distance_metres,"hist_runs":len(hist),
          "lvs_last1":lvs[-1] if lvs else np.nan,"lvs_mean3":l3[0],"lvs_mean5":l5[0],
          "lvs_median5":l5[1],"lvs_std5":l5[2],"lvs_peak":max(lvs) if lvs else np.nan,
          "lvs_worst5":min(lvs[-5:]) if lvs else np.nan,
          "margin_mean5":m5[0],"margin_std5":m5[2],"margin_worst5":max(margins[-5:]) if margins else np.nan,
          "finishpos_mean5":p5[0],"days_since_last":(dt-max(dates)).days if dates else np.nan}
     if pd.notna(r.distance_metres):
      near=[x for x in hist if np.isfinite(x["distance"]) and abs(x["distance"]-r.distance_metres)<=200]
      nl=[x["lvs"] for x in near if np.isfinite(x["lvs"])]
      rec.update({"dist200_runs":len(near),"dist200_lvs_mean":float(np.mean(nl)) if nl else np.nan,
                  "dist200_lvs_best":max(nl) if nl else np.nan})
     rows.append(rec)
   # Same-date exclusion: update only after all rows on date are scored.
   for r in day.itertuples(index=False):
    hist.append({"date":dt,"distance":float(r.distance_metres) if pd.notna(r.distance_metres) else np.nan,
                 "pos":float(r.finish_position) if pd.notna(r.finish_position) else np.nan,
                 "margin":float(r.finish_margin) if pd.notna(r.finish_margin) else np.nan,
                 "lvs":float(r.runner_lvs) if pd.notna(r.runner_lvs) else np.nan})
 out=pd.DataFrame(rows)
 if not out["_year"].between(2021,2024).all(): raise RuntimeError("Sealed-year breach.")
 if out.duplicated(["_race","_horse"]).any(): raise RuntimeError("Duplicate race/horse keys.")
 forbidden=[c for c in out if c.lower() in {"_sp","sp","final_sp","odds","p_model","market_probability"}]
 if forbidden: raise RuntimeError(f"Forbidden market columns: {forbidden}")
 out.to_csv(OUT,index=False)
 oh=hashlib.sha256()
 with OUT.open("rb") as fh:
  for b in iter(lambda:fh.read(8*1024*1024),b""): oh.update(b)
 OUT_MANIFEST.write_text(json.dumps({"contract_version":"LAB245B_COMPACT_PIT_HISTORY_V1","source_contract_version":EXPECTED_CONTRACT,"source_sha256":source_sha,"pit_policy":"HORSE_HISTORY_DATE_LT_TARGET_DATE","rows":int(len(out)),"races":int(out["_race"].nunique()),"output_sha256":oh.hexdigest(),"output_bytes":OUT.stat().st_size},indent=2),encoding="utf-8")
 print(f"ROWS={len(out):,} RACES={out._race.nunique():,} OBS_TARGET={out.target_lvs.notna().sum():,}")
 print(f"TARGET_COVERAGE={out.target_lvs.notna().mean():.6f} YEARS={sorted(out._year.unique())}")
 print("PIT_POLICY=HORSE_HISTORY_DATE_LT_TARGET_DATE")
 print(f"OUT={OUT}")
if __name__=="__main__": main()
