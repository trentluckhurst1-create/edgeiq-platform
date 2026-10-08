from pathlib import Path
import pandas as pd
import numpy as np

R=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
U=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage004\V2_CERTIFIED_SINGLE_WINNER_UNIVERSE.csv")
src=R/"public"/"data"/"edgeiq_historical_performance_rating_v1.csv"
print("V2_STAGE027_CONTRACT HISTORICAL_PERFORMANCE_RATING_PIT_CERT NO_MODEL NO_MARKET NO_FUZZY 2025_2026_SEALED")
print("V2_STAGE027_SOURCE",src,"EXISTS",src.exists())
if not src.exists(): raise SystemExit("Builder-defined historical performance rating authority missing")
a=pd.read_csv(src,low_memory=False)
u=pd.read_csv(U,low_memory=False)
print("V2_STAGE027_AUTH_ROWS",len(a))
print("V2_STAGE027_AUTH_COLS","|".join(a.columns))
# Required historical semantics.
date_col=next((c for c in ["race_date","date"] if c in a.columns),None)
horse_col=next((c for c in ["canonical_horse_id","horse_id"] if c in a.columns),None)
rating_col=next((c for c in ["performance_rating_v1","performance_rating"] if c in a.columns),None)
race_col=next((c for c in ["canonical_race_id","race_id"] if c in a.columns),None)
print("V2_STAGE027_KEYS",date_col,horse_col,rating_col,race_col)
if not date_col or not horse_col or not rating_col: raise SystemExit("Required rating authority keys missing")
a[date_col]=pd.to_datetime(a[date_col],errors="coerce")
u["race_date"]=pd.to_datetime(u["race_date"],errors="coerce")
if "canonical_horse_id" not in u.columns and "_horse" in u.columns:u["canonical_horse_id"]=u["_horse"]
for d,c in [(a,horse_col),(u,"canonical_horse_id")]:d[c]=d[c].astype(str).str.strip()
# Authority duplicate event identity.
dupk=[horse_col,date_col]+([race_col] if race_col else [])
print("V2_STAGE027_AUTH_DUP_EVENT_KEYS",int(a.duplicated(dupk).sum()))
print("V2_STAGE027_RATING_NONNULL",int(a[rating_col].notna().sum()),"RATE",float(a[rating_col].notna().mean()))
# Strict-prior availability: latest authority date for same horse must be < target date. No same-date allowed.
hist=a[[horse_col,date_col,rating_col]].dropna(subset=[date_col]).sort_values([horse_col,date_col])
targets=u[["canonical_horse_id","race_date"]].copy().sort_values(["canonical_horse_id","race_date"])
# Rename to common key for merge_asof.
hist=hist.rename(columns={horse_col:"horse_key",date_col:"hist_date",rating_col:"hist_rating"})
targets=targets.rename(columns={"canonical_horse_id":"horse_key","race_date":"target_date"})
# Per-horse strict prior via searchsorted to avoid any same-date ambiguity.
groups={k:(g["hist_date"].values,g["hist_rating"].values) for k,g in hist.groupby("horse_key",sort=False)}
prior=0;samedate_candidates=0
year_stats={}
for row in targets.itertuples(index=False):
 dates_vals=groups.get(row.horse_key)
 y=int(row.target_date.year) if pd.notna(row.target_date) else -1
 if dates_vals is None or pd.isna(row.target_date):
  year_stats.setdefault(y,[0,0,0]);year_stats[y][0]+=1;continue
 dates,ratings=dates_vals
 t=np.datetime64(row.target_date.to_datetime64())
 same=int(np.searchsorted(dates,t,side="right")-np.searchsorted(dates,t,side="left"))
 idx=int(np.searchsorted(dates,t,side="left")-1)
 ok=idx>=0 and pd.notna(ratings[idx])
 prior+=int(ok);samedate_candidates+=int(same>0)
 year_stats.setdefault(y,[0,0,0]);year_stats[y][0]+=1;year_stats[y][1]+=int(ok);year_stats[y][2]+=int(same>0)
print("V2_STAGE027_STRICT_PRIOR_NONNULL",prior,"N",len(targets),"RATE",prior/len(targets))
print("V2_STAGE027_TARGETS_WITH_SAMEDATE_AUTH_ROW",samedate_candidates,"RATE",samedate_candidates/len(targets))
for y,v in sorted(year_stats.items()):
 if y in [2021,2022,2023,2024]:print("V2_STAGE027_YEAR",y,"N",v[0],"STRICT_PRIOR",v[1],"RATE",v[1]/v[0],"SAMEDATE_PRESENT",v[2])
print("V2_STAGE027_RULE HISTORY_DATE_STRICTLY_LESS_THAN_TARGET_DATE")
print("V2_STAGE027_COMPLETE")
