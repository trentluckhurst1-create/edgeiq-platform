from pathlib import Path
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
WAREHOUSE=ROOT/"docs/performance-intelligence/warehouse/edgeiq_performance_fact_warehouse_v1.csv"
LCP=ROOT/"public/data/edgeiq_length_conversion_parameter_fact_v2.csv"
OUT=ROOT/"outputs/research/profitability_program/lab245b/LAB245B_WAREHOUSE_RUNNER_LVS.csv"
MIN_SAMPLE=20

def cond(x):
 s=str(x or "").upper()
 if "FIRM" in s or s=="FAST": return "FIRM"
 if "GOOD" in s:return "GOOD"
 if any(z in s for z in ["SOFT","DEAD","SLOW"]):return "SOFT"
 if "HEAVY" in s or "HVY" in s:return "HEAVY"
 if any(z in s for z in ["SYNTH","POLY","TAPETA"]):return "STANDARD_SYNTHETIC"
 return s

def main():
 if not WAREHOUSE.exists():raise FileNotFoundError(WAREHOUSE)
 use=["canonical_race_id","canonical_horse_id","race_date","track","track_layout","distance_metres","track_condition","track_condition_group","finish_position","finish_margin","official_race_time_seconds"]
 d=pd.read_csv(WAREHOUSE,usecols=use,low_memory=False)
 d["race_date"]=pd.to_datetime(d["race_date"],errors="coerce")
 for x in ["distance_metres","finish_position","finish_margin","official_race_time_seconds"]:d[x]=pd.to_numeric(d[x],errors="coerce")
 d["condition"]=d["track_condition_group"].fillna(d["track_condition"]).map(cond)
 d["track_key"]=d["track"].fillna("").astype(str).str.strip().str.upper()
 txt=(d["track"].fillna("")+" "+d["track_layout"].fillna("")+" "+d["track_condition"].fillna("")+" "+d["track_condition_group"].fillna("")).str.upper()
 d["surface"]=np.where(txt.str.contains("SYNTHETIC|POLY|TAPETA|FIBRE|FIBER",regex=True),"AUSTRALIAN_SYNTHETIC","TURF")
 d["_valid_time"]=d["official_race_time_seconds"].gt(0)
 d["_winner"]=d["finish_position"].eq(1)
 r=d.sort_values(["canonical_race_id","_winner","_valid_time"],ascending=[True,False,False],kind="stable").drop_duplicates("canonical_race_id")
 r=r[r["_valid_time"]].copy()
 timed_races=len(r)

 # Strict date-PIT benchmark. All races on date D are scored from dates < D only.
 r=r.dropna(subset=["track_key","distance_metres","condition","official_race_time_seconds","race_date"]).sort_values(["race_date","canonical_race_id"],kind="stable")
 history={}
 scored=[]
 for race_date,day in r.groupby("race_date",sort=True):
  day=day.copy()
  std=[]; counts=[]
  for _,row in day.iterrows():
   k=(row["track_key"],row["distance_metres"],row["surface"],row["condition"])
   vals=history.get(k,[])
   counts.append(len(vals))
   std.append(float(np.median(vals)) if len(vals)>=MIN_SAMPLE else np.nan)
  day["benchmark_n"]=counts
  day["standard_time_seconds"]=std
  scored.append(day)
  # Add the whole date only after every race on the date has been scored.
  for _,row in day.iterrows():
   k=(row["track_key"],row["distance_metres"],row["surface"],row["condition"])
   history.setdefault(k,[]).append(float(row["official_race_time_seconds"]))
 r=pd.concat(scored,ignore_index=True)
 r=r[r["standard_time_seconds"].notna()].copy()

 p=pd.read_csv(LCP,usecols=["surface_group","track_condition_group","seconds_per_length"])
 p=p.rename(columns={"surface_group":"surface","track_condition_group":"condition"})
 r=r.merge(p,on=["surface","condition"],how="inner",validate="many_to_one")
 r["race_lvs"]=-(r["official_race_time_seconds"]-r["standard_time_seconds"])/r["seconds_per_length"]
 race_lvs=r[["canonical_race_id","race_lvs","standard_time_seconds","seconds_per_length","benchmark_n"]]
 out=d.merge(race_lvs,on="canonical_race_id",how="inner",validate="many_to_one")
 # Declared LAB245B reconstruction: race LVS and finish margin are both in lengths.
 out["runner_lvs"]=out["race_lvs"]-out["finish_margin"]
 keep=["canonical_race_id","canonical_horse_id","race_date","distance_metres","finish_position","finish_margin","runner_lvs","race_lvs","standard_time_seconds","seconds_per_length","benchmark_n"]
 out[keep].to_csv(OUT,index=False)
 lvs_races=r["canonical_race_id"].nunique()
 print(f"SOURCE_ROWS={len(d):,}")
 print(f"TIMED_RACES={timed_races:,}")
 print(f"LVS_RACES={lvs_races:,}")
 print(f"RUNNER_ROWS={len(out):,}")
 print("PIT_POLICY=STRICT_DATE_LT_TARGET_DATE")
 print("RUNNER_LVS_POLICY=DECLARED_LAB245B_RACE_LVS_MINUS_FINISH_MARGIN")
 print("KNOWN_RECOVERY_TIMED_RACES=70,308 DELTA_RACES=54,978 LVS_RACES=52,414")
 if abs(timed_races-70308)>10:raise RuntimeError("Timed-race recovery count materially disagrees with certified audit.")
 if lvs_races<=0 or lvs_races>=timed_races:raise RuntimeError("Invalid PIT LVS recovery funnel.")
 print(f"OUT={OUT}")
if __name__=="__main__":main()
