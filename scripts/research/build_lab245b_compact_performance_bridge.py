from pathlib import Path
import os
from collections import defaultdict
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
DATA_ROOT=Path(os.environ.get("EDGEIQ_DATA_ROOT",str(ROOT))).resolve()
AUTHORITY=DATA_ROOT/"docs/performance-intelligence/lengths-v-standard/edgeiq_runner_lengths_v_standard_fact_v1.csv"
FALLBACK=ROOT/"outputs/research/profitability_program/lab245b/LAB245B_WAREHOUSE_RUNNER_LVS.csv"
AUTHORITY_SIZE=80343742
AUTHORITY_SHA256="b08bb7a334ddba2f6a76942452dd964cd59db05001dc5710ff19aa7fc6e12926"
PARITY_AUTHORITY_ONLY=True  # LOCKED: historical 533,387-row authority used all-history benchmark construction. It is formula/parity evidence only; forecasting target must be strict date-PIT.
OUTDIR=ROOT/"outputs/research/profitability_program/lab245b"
OUT=OUTDIR/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
NEED=["canonical_race_id","canonical_horse_id","race_date","distance_metres","finish_position","finish_margin","runner_lvs"]

def load_source():
 import hashlib
 if AUTHORITY.exists() and not PARITY_AUTHORITY_ONLY:
  size=AUTHORITY.stat().st_size
  if size!=AUTHORITY_SIZE: raise RuntimeError(f"Runner-LVS authority size drift: {size} != {AUTHORITY_SIZE}")
  h=hashlib.sha256()
  with AUTHORITY.open("rb") as fh:
   for b in iter(lambda:fh.read(8*1024*1024),b""): h.update(b)
  digest=h.hexdigest()
  if digest!=AUTHORITY_SHA256: raise RuntimeError(f"Runner-LVS authority SHA drift: {digest}")
  a=pd.read_csv(AUTHORITY,usecols=["canonical_performance_id","canonical_race_id","canonical_horse_id","finish_position","finish_margin_lengths","runner_lengths_v_standard"],dtype={"canonical_performance_id":"string","canonical_race_id":"string","canonical_horse_id":"string"},low_memory=False)
  for k in ["canonical_performance_id","canonical_race_id","canonical_horse_id"]: a[k]=a[k].str.strip()
  if a["canonical_performance_id"].isna().any() or a["canonical_performance_id"].duplicated().any(): raise RuntimeError("Runner-LVS authority performance IDs are missing or non-unique.")
  # Authority lacks date/distance. Prefer compact one-row-per-race recovered timing identity map.
  timing=DATA_ROOT/"public/data/edgeiq_recovered_timing_warehouse_v1.csv"
  warehouse=DATA_ROOT/"docs/performance-intelligence/warehouse/edgeiq_performance_fact_warehouse_v1.csv"
  if timing.exists():
   w=pd.read_csv(timing,usecols=["canonical_race_id","race_date","distance_metres"],low_memory=False)
   w["canonical_race_id"]=w["canonical_race_id"].astype("string").str.strip()
   # Governance: race identity must be unique and internally consistent.
   chk=w.groupby("canonical_race_id",dropna=False).agg(race_date_n=("race_date","nunique"),distance_n=("distance_metres","nunique"))
   bad=chk[(chk.race_date_n>1)|(chk.distance_n>1)]
   if len(bad): raise RuntimeError(f"Conflicting recovered-timing race attributes: {len(bad)} races")
   w=w.drop_duplicates(["canonical_race_id"])
   d=a.merge(w,on="canonical_race_id",how="left",validate="many_to_one")
   cov=(d["race_date"].notna() & d["distance_metres"].notna()).mean()
   print(f"IDENTITY_ENRICHMENT=RECOVERED_TIMING_RACE_MAP RACES={len(w):,} COVERAGE={cov:.6f}")
   if cov<0.999:
    if not warehouse.exists(): raise RuntimeError(f"Recovered timing enrichment coverage too low: {cov:.6f}")
    # Fill only misses from the large warehouse; do not replace validated compact-map rows.
    need=set(d.loc[d["race_date"].isna()|d["distance_metres"].isna(),"canonical_race_id"].dropna().astype(str))
    fills=[]
    for ch in pd.read_csv(warehouse,usecols=["canonical_race_id","race_date","distance_metres"],chunksize=200000,low_memory=False):
     ch["canonical_race_id"]=ch["canonical_race_id"].astype("string").str.strip()
     x=ch[ch["canonical_race_id"].isin(need)].drop_duplicates(["canonical_race_id"])
     if len(x): fills.append(x)
    if fills:
     fill=pd.concat(fills,ignore_index=True).drop_duplicates(["canonical_race_id"]).set_index("canonical_race_id")
     miss=d["race_date"].isna()|d["distance_metres"].isna()
     d.loc[miss,"race_date"]=d.loc[miss,"canonical_race_id"].map(fill["race_date"])
     d.loc[miss,"distance_metres"]=d.loc[miss,"canonical_race_id"].map(fill["distance_metres"])
     print(f"IDENTITY_ENRICHMENT_FALLBACK=WAREHOUSE_MISSES RACES={len(fill):,}")
  else:
   if not warehouse.exists(): raise FileNotFoundError("Authority enrichment requires recovered timing map or warehouse.")
   race_parts=[]
   for ch in pd.read_csv(warehouse,usecols=["canonical_race_id","race_date","distance_metres"],chunksize=200000,low_memory=False):
    ch["canonical_race_id"]=ch["canonical_race_id"].astype("string").str.strip()
    race_parts.append(ch.drop_duplicates(["canonical_race_id"]))
   w=pd.concat(race_parts,ignore_index=True).drop_duplicates(["canonical_race_id"])
   d=a.merge(w,on="canonical_race_id",how="left",validate="many_to_one")
   print("IDENTITY_ENRICHMENT=WAREHOUSE_RACE_MAP")
  if d["race_date"].isna().any() or d["distance_metres"].isna().any(): raise RuntimeError(f"Authority rows missing race enrichment: date={int(d.race_date.isna().sum())} distance={int(d.distance_metres.isna().sum())}")
  d=d.rename(columns={"finish_margin_lengths":"finish_margin","runner_lengths_v_standard":"runner_lvs"})
  print(f"SOURCE=VERIFIED_RUNNER_LVS_AUTHORITY SIZE={size} SHA256={digest}")
  return d[NEED]
 if not FALLBACK.exists(): raise FileNotFoundError(f"Neither authority nor fallback exists: {AUTHORITY} | {FALLBACK}")
 print("SOURCE=STRICT_PIT_WAREHOUSE_RECONSTRUCTION")
 if AUTHORITY.exists(): print("PARITY_AUTHORITY_PRESENT_BUT_NOT_USED_AS_TARGET=YES")
 return pd.read_csv(FALLBACK,usecols=NEED,low_memory=False)

def stats(a,n):
 x=np.asarray(a[-n:],dtype=float)
 x=x[np.isfinite(x)]
 if not len(x): return (np.nan,np.nan,np.nan)
 return (float(np.mean(x)),float(np.median(x)),float(np.std(x)))

def main():
 OUTDIR.mkdir(parents=True,exist_ok=True)
 d=load_source()
 for c in ["canonical_race_id","canonical_horse_id"]: d[c]=d[c].astype("string").str.strip()
 d["race_date"]=pd.to_datetime(d["race_date"],errors="coerce")
 for c in ["distance_metres","finish_position","finish_margin","runner_lvs"]: d[c]=pd.to_numeric(d[c],errors="coerce")
 d=d.dropna(subset=["canonical_race_id","canonical_horse_id","race_date"])
 d["target_field_size"]=d.groupby("canonical_race_id")["canonical_horse_id"].transform("nunique")
 d=d.sort_values(["canonical_horse_id","race_date","canonical_race_id"],kind="stable")
 field_sizes=d.groupby("canonical_race_id")["canonical_horse_id"].nunique().to_dict()
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
   for _,r in day.iterrows():
    year=int(dt.year)
    if 2021<=year<=2024:
     rec={"_race":r.canonical_race_id,"_horse":horse,"_year":year,"race_date":dt.date().isoformat(),
          "target_lvs":r.runner_lvs,"target_finish_position":r.finish_position,"target_field_size":field_sizes.get(r.canonical_race_id,np.nan),"current_distance":r.distance_metres,"hist_runs":len(hist),
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
   for _,r in day.iterrows():
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
 print(f"ROWS={len(out):,} RACES={out._race.nunique():,} OBS_TARGET={out.target_lvs.notna().sum():,}")
 print(f"TARGET_COVERAGE={out.target_lvs.notna().mean():.6f} YEARS={sorted(out._year.unique())}")
 print("PIT_POLICY=HORSE_HISTORY_DATE_LT_TARGET_DATE")
 print(f"OUT={OUT}")
if __name__=="__main__": main()
