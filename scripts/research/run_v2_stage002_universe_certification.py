from pathlib import Path
import pandas as pd,numpy as np
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
D=R/"outputs"/"research"/"profitability_program"/"d45"/"D45_FROZEN_PIT_FEATURE_MATRIX.csv"
OUT=R/"outputs"/"research"/"model_v2"/"stage002";OUT.mkdir(parents=True,exist_ok=True)
use=["_race","_horse","race_date","y","target_finish_position","target_field_size"]
z=pd.read_csv(D,usecols=use)
z["date"]=pd.to_datetime(z.race_date,errors="coerce");z["year"]=z.date.dt.year
# V2 development/audit universe explicitly ends 2024. Do not inspect 2025-26 outcomes.
z=z[z.year.le(2024)].copy()
race=z.groupby("_race",dropna=False).agg(race_date=("date","min"),year=("year","min"),runners=("_horse","size"),unique_horses=("_horse","nunique"),wins=("y","sum"),field_min=("target_field_size","min"),field_max=("target_field_size","max"),finish_nonnull=("target_finish_position",lambda s:s.notna().sum())).reset_index()
race["valid_one_winner"]=race.wins.eq(1);race["unique_runner_ids"]=race.runners.eq(race.unique_horses);race["field_consistent"]=race.field_min.eq(race.field_max)
dup=z.duplicated(["_race","_horse"],keep=False)
print("V2_STAGE002_CONTRACT CERTIFY_EXISTING_PIT_UNIVERSE THROUGH_2024 ONLY NO_MODEL 2025_2026_SEALED")
print("V2_STAGE002_RUNNERS",len(z),"RACES",z._race.nunique(),"DUP_RACE_HORSE_ROWS",int(dup.sum()),"DATE_MIN",z.date.min(),"DATE_MAX",z.date.max())
for yr,g in z.groupby("year"):
 rg=race[race.year.eq(yr)]
 print("V2_STAGE002_YEAR",int(yr),"RUNNERS",len(g),"RACES",g._race.nunique(),"WINNERS",int(g.y.sum()),"ONE_WINNER_RACES",int(rg.valid_one_winner.sum()),"UNIQUE_ID_RACES",int(rg.unique_runner_ids.sum()),"FIELD_CONSISTENT_RACES",int(rg.field_consistent.sum()),"FINISH_NONNULL",int(g.target_finish_position.notna().sum()))
bad=race[~(race.valid_one_winner&race.unique_runner_ids&race.field_consistent)]
print("V2_STAGE002_BAD_RACES",len(bad))
race.to_csv(OUT/"V2_STAGE002_RACE_INTEGRITY.csv",index=False)
z[["_race","_horse","race_date","year","y","target_finish_position","target_field_size"]].to_csv(OUT/"V2_STAGE002_CERTIFIED_RUNNER_UNIVERSE.csv",index=False)
print("V2_STAGE002_COMPLETE",OUT)
