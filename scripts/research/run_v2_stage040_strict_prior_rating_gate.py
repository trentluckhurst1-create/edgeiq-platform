from pathlib import Path
import pandas as pd
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
print("V2_STAGE040_CONTRACT HISTORICAL_RATING_STRICT_PRIOR_DATE_GATE NO_MODEL NO_MARKET 2025_2026_SEALED")
r=pd.read_csv(P/"public"/"data"/"edgeiq_historical_performance_rating_v1.csv",low_memory=False,usecols=["horse","race_date","performance_rating_v1"])
r["date"]=pd.to_datetime(r["race_date"],errors="coerce").dt.normalize()
r=r[r["date"].dt.year.le(2024)].copy()
r["name"]=r["horse"].fillna("").astype(str).str.upper().str.replace(r"[^A-Z0-9]","",regex=True)
r=r[r["date"].notna()&r["name"].ne("")].copy()
r["rating"]=pd.to_numeric(r["performance_rating_v1"],errors="coerce")
r=r.sort_values(["name","date"],kind="stable")
# Strictly earlier race date: shift the per-date aggregate, not the row. This also excludes same-day races.
d=r.groupby(["name","date"],sort=True).agg(n=("rating","size"),sum_rating=("rating","sum"),last_rating=("rating","last")).reset_index()
g=d.groupby("name",sort=False)
d["prior_n"]=g["n"].cumsum()-d["n"]
d["prior_sum"]=g["sum_rating"].cumsum()-d["sum_rating"]
d["prior_mean"]=d["prior_sum"]/d["prior_n"].where(d["prior_n"].gt(0))
d["prior_last"]=g["last_rating"].shift(1)
first=d[d["prior_n"].eq(0)]
later=d[d["prior_n"].gt(0)]
print("V2_STAGE040_COUNTS ELIGIBLE_RATING_ROWS",len(r),"HORSE_DATE_GROUPS",len(d),"HORSES",d.name.nunique(),"FIRST_DATE_GROUPS",len(first),"WITH_PRIOR_GROUPS",len(later))
print("V2_STAGE040_SAME_DATE_MULTI_GROUPS",int(d.n.gt(1).sum()),"SAME_DATE_MULTI_ROWS",int(d.loc[d.n.gt(1),"n"].sum()))
print("V2_STAGE040_PRIOR_LAST_MISSING_WHEN_PRIOR",int(later.prior_last.isna().sum()),"PRIOR_MEAN_MISSING_WHEN_PRIOR",int(later.prior_mean.isna().sum()))
print("V2_STAGE040_FIRST_DATE_LEAK",int(first.prior_last.notna().sum()+first.prior_mean.notna().sum()))
print("V2_STAGE040_RATING_DATE_MAX",str(d.date.max().date()) if len(d) else "NONE")
good=(len(d)>0 and not r.rating.isna().any() and not later.prior_last.isna().any() and not later.prior_mean.isna().any() and not first.prior_last.notna().any() and not first.prior_mean.notna().any())
print("V2_STAGE040_DECISION","PASS_STRICT_PRIOR_DATE_CONSTRUCTION_ONLY" if good else "STOP_PRIOR_DATE_INTEGRITY")
print("V2_STAGE040_COMPLETE")
