from pathlib import Path
import pandas as pd,numpy as np
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH");P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
U=R/"outputs"/"research"/"model_v2"/"stage004"/"V2_CERTIFIED_SINGLE_WINNER_UNIVERSE.csv";OUT=R/"outputs"/"research"/"model_v2"/"stage006";OUT.mkdir(parents=True,exist_ok=True)
u=pd.read_csv(U);u["race_date"]=pd.to_datetime(u.race_date);u["year"]=u.race_date.dt.year
perf=pd.read_csv(R/"outputs"/"research"/"profitability_program"/"lab245b"/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv")
# Exclude target/outcome fields and known invalid blank field-size semantic.
drop={"_year","race_date","target_lvs","target_finish_position","target_field_size"}
pf=[c for c in perf.columns if c not in {"_race","_horse"}|drop]
x=u.merge(perf[["_race","_horse"]+pf],on=["_race","_horse"],how="left",validate="one_to_one")
tim=pd.read_csv(P/"outputs"/"research"/"model_lab_090"/"LAB090F5B_STRICT_PRIOR_TIMING_H4B_MATRIX.csv")
tk=["canonical_race_id","canonical_horse_id"];tf=[c for c in tim.columns if c not in tk+["race_date_model","year"]]
tim=tim[tk+tf].drop_duplicates(tk)
x=x.merge(tim,left_on=["_race","_horse"],right_on=tk,how="left",validate="one_to_one");x.drop(columns=tk,inplace=True)
x["timing_authority_present"]=x[tf].notna().any(axis=1).astype(int)
form=pd.read_csv(P/"outputs"/"research"/"model_lab_120"/"LAB120E_DYNAMIC_FORM_LINE_FEATURES.csv")
fk=["canonical_race_id","horse_id"];ff=[c for c in form.columns if c not in fk+["race_id_int","runner_id_int"]]
form=form[fk+ff].drop_duplicates(fk)
x=x.merge(form,left_on=["_race","_horse"],right_on=fk,how="left",validate="one_to_one");x.drop(columns=fk,inplace=True)
x["formline_authority_present"]=x[ff].notna().any(axis=1).astype(int)
# Audit suspicious footprint identity.
same=(x.timing_authority_present==x.formline_authority_present)
print("V2_STAGE006_CONTRACT BUILD_CLEAN_PIT_FEATURE_WAREHOUSE NO_MODEL CORE_PERFORMANCE SPARSE_TIMING_FORMLINE PACE_AND_FIRST_STARTER_QUARANTINED 2025_2026_SEALED")
print("V2_STAGE006_ROWS",len(x),"RACES",x._race.nunique(),"PERF_FEATURES",len(pf),"TIMING_FEATURES",len(tf),"FORMLINE_FEATURES",len(ff))
print("V2_STAGE006_TIMING_FORMLINE_PRESENCE_IDENTICAL_RATE",float(same.mean()),"DISAGREE",int((~same).sum()))
for yr,g in x.groupby("year"):
 print("V2_STAGE006_YEAR",int(yr),"ROWS",len(g),"RACES",g._race.nunique(),"TIMING_PRESENT",int(g.timing_authority_present.sum()),"FORMLINE_PRESENT",int(g.formline_authority_present.sum()))
# PIT safety schema gate: feature names that look target/outcome/market-like.
features=pf+tf+ff
bad=[c for c in features if any(t in c.lower() for t in ["target_","finish_position","starting_price","market_","won_","winner_"])]
print("V2_STAGE006_SCHEMA_LEAKAGE_NAME_FLAGS",len(bad),"|".join(bad))
x.to_csv(OUT/"V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv",index=False)
print("V2_STAGE006_COMPLETE",OUT/"V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv")
