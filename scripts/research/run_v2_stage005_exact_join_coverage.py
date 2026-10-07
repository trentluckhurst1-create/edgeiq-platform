from pathlib import Path
import pandas as pd,numpy as np
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH");P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
U=R/"outputs"/"research"/"model_v2"/"stage004"/"V2_CERTIFIED_SINGLE_WINNER_UNIVERSE.csv"
u=pd.read_csv(U);u["year"]=pd.to_datetime(u.race_date).dt.year
print("V2_STAGE005_CONTRACT EXACT_JOIN_COVERAGE_AUDIT NO_MODEL NO_FUZZY_IDENTITY 2025_2026_SEALED")
# exact canonical authorities
specs=[
("PERFORMANCE",R/"outputs"/"research"/"profitability_program"/"lab245b"/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv",["_race","_horse"],["_race","_horse"],["hist_runs","lvs_mean5"]),
("TIMING",P/"outputs"/"research"/"model_lab_090"/"LAB090F5B_STRICT_PRIOR_TIMING_H4B_MATRIX.csv",["_race","_horse"],["canonical_race_id","canonical_horse_id"],["has_prior_timing_signal","timing_epi_prior_obs"]),
("PACE",P/"outputs"/"research"/"model_lab_087"/"LAB087G_PACE_H4B_IDENTITY_BRIDGE.csv",["_race","_horse"],["canonical_race_id","canonical_horse_id"],["tactical_prior_starts","style_usable"]),
]
for name,p,uk,ak,sig in specs:
 a=pd.read_csv(p,usecols=list(dict.fromkeys(ak+sig)))
 a=a.drop_duplicates(ak)
 m=u[["_race","_horse","year"]].merge(a,left_on=uk,right_on=ak,how="left")
 matched=m[ak[0]].notna() if ak[0] not in uk else m[sig].notna().any(axis=1)
 print("V2_STAGE005_AUTH",name,"AUTH_ROWS",len(a),"MATCHED",int(matched.sum()),"RATE",float(matched.mean()))
 for yr,g in m.groupby("year"):
  mm=(g[ak[0]].notna() if ak[0] not in uk else g[sig].notna().any(axis=1))
  usable=g[sig].notna().any(axis=1)
  print("V2_STAGE005_YEAR",name,int(yr),"ROWS",len(g),"MATCH",int(mm.sum()),"USABLE",int(usable.sum()),"USABLE_RATE",float(usable.mean()))
# form-line key semantics: test horse_id against canonical _horse exactly, no coercion/fuzzy
p=P/"outputs"/"research"/"model_lab_120"/"LAB120E_DYNAMIC_FORM_LINE_FEATURES.csv"
a=pd.read_csv(p);a=a.drop_duplicates(["canonical_race_id","horse_id"])
m=u[["_race","_horse","year"]].merge(a,left_on=["_race","_horse"],right_on=["canonical_race_id","horse_id"],how="left")
feat=[c for c in a.columns if c not in {"canonical_race_id","horse_id","race_id_int","runner_id_int"}]
usable=m[feat].notna().any(axis=1)
print("V2_STAGE005_AUTH FORM_LINE AUTH_ROWS",len(a),"EXACT_MATCH",int(usable.sum()),"RATE",float(usable.mean()))
for yr,g in m.groupby("year"):print("V2_STAGE005_YEAR FORM_LINE",int(yr),"ROWS",len(g),"USABLE",int(g[feat].notna().any(axis=1).sum()),"RATE",float(g[feat].notna().any(axis=1).mean()))
# first starter authority overlap by canonical horse+date only, diagnostic exact chronology
p=P/"outputs"/"research"/"model_lab_075f2"/"canonical_strict_date_first_starter_universe_075f2.csv"
a=pd.read_csv(p,usecols=["race_date","canonical_horse_id","trainer_prior_first_starters","jockey_prior_first_starters","combo_prior_first_starters"]);a["race_date"]=pd.to_datetime(a.race_date).dt.strftime("%Y-%m-%d");a=a.drop_duplicates(["race_date","canonical_horse_id"])
uu=u[["_race","_horse","race_date","year"]].copy();uu["race_date"]=pd.to_datetime(uu.race_date).dt.strftime("%Y-%m-%d")
m=uu.merge(a,left_on=["race_date","_horse"],right_on=["race_date","canonical_horse_id"],how="left");matched=m.canonical_horse_id.notna()
print("V2_STAGE005_AUTH FIRST_STARTER EXACT_DATE_HORSE_MATCH",int(matched.sum()),"RATE",float(matched.mean()))
for yr,g in m.groupby("year"):print("V2_STAGE005_YEAR FIRST_STARTER",int(yr),"MATCH",int(g.canonical_horse_id.notna().sum()),"ROWS",len(g))
print("V2_STAGE005_COMPLETE")
