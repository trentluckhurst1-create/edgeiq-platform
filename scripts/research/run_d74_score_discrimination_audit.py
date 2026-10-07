from pathlib import Path
import pandas as pd,re,numpy as np
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH");ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM");D=R/"outputs"/"research"/"profitability_program"/"d45"/"D45_FROZEN_PIT_FEATURE_MATRIX.csv";DATA=ROOT/"public"/"data"
d=pd.read_csv(D,usecols=["_race","_horse","race_date"]);d["date"]=pd.to_datetime(d.race_date);sel=d[d.date.dt.year.isin([2022,2023])].copy()
def norm(s):return s.astype(str).str.upper().str.replace(r"[^A-Z0-9]","",regex=True)
sel["hk"]=norm(sel._horse)
print("D89_CONTRACT PRE2023_POSITIONAL_SECTIONAL_EXACT_OVERLAP NO_MODEL")
sources=[
("horse_runs_ra.csv","run_date",["horse_name","horse","horse_code"],["sectional_600","in_run_positions_raw"]),
("full_career_form_BEFORE_BULLETPROOF_SCRAPE.csv","race_date",["horse","horse_name"],["pos_800","pos_400","in_run_positions"]),
("edgeiq_positional_dna_observations_v2.csv","run_date",["horse","horse_name","horse_key"],["last600","sectional_figure","speed_figure","raw_in_run","pos800","pos400","gain_800_400"]),
("run_ratings_v1.csv","race_date",["horse","horse_name","horse_key"],["last_600m","last_600m_sec","official_time_sec"]),
("edgeiq_sectional_identity_engine_v1.csv","race_date",["matched_horse","normalized_horse","horse"],["raw_last_600","raw_last_400","raw_last_200","early_speed_raw","midrace_speed_raw","late_speed_raw","sectional_rating","match_confidence","validation_status"])
]
for fn,dcands,hcands,vals in sources:
 p=DATA/fn
 if not p.exists():print("D89_MISSING",fn);continue
 h=pd.read_csv(p,nrows=0);dc=dcands if dcands in h.columns else next((c for c in ["race_date","run_date","meeting_date","matched_race_date"] if c in h.columns),None);hc=next((c for c in hcands if c in h.columns),None);vv=[c for c in vals if c in h.columns]
 if not dc or not hc:print("D89_NO_KEYS",fn,dc,hc);continue
 x=pd.read_csv(p,usecols=[dc,hc]+vv,low_memory=False);x["date"]=pd.to_datetime(x[dc],errors="coerce");x["hk"]=norm(x[hc]);x=x[x.date.dt.year.le(2023)]
 m=sel.merge(x,on=["date","hk"],how="left",suffixes=("","_src"))
 print("D89_SOURCE",fn,"SRC_ROWS",len(x),"MATCH_ROWS",int(m[hc].notna().sum()) if hc in m else 0,"MATCH_RUNNERS",int(m.loc[m[hc].notna(),["_race","_horse"]].drop_duplicates().shape[0]) if hc in m else 0)
 for c in vv:
  print("D89_VALUE",fn,c,"MATCH_NON_NULL",int(m[c].notna().sum()),"SEL_COVERAGE",float(m.groupby(["_race","_horse"])[c].apply(lambda z:z.notna().any()).mean()))
print("D89_COMPLETE")
