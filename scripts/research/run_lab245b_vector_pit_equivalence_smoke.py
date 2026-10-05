import pandas as pd
import numpy as np
from bisect import insort

MIN_SAMPLE=3
GCOLS=["track_key","distance_metres","condition"]

def old_loop(r):
    history={}; out=[]
    for dt,day in r.groupby("race_date",sort=True):
        day=day.copy(); ns=[]; meds=[]
        for _,x in day.iterrows():
            k=(x.track_key,x.distance_metres,x.condition); vals=history.get(k,[])
            ns.append(len(vals)); meds.append(float(np.median(vals)) if len(vals)>=MIN_SAMPLE else np.nan)
        day["n_old"]=ns; day["m_old"]=meds; out.append(day)
        for _,x in day.iterrows():
            k=(x.track_key,x.distance_metres,x.condition)
            insort(history.setdefault(k,[]),float(x.official_race_time_seconds))
    return pd.concat(out).sort_values("canonical_race_id")

def vector(r):
    x=r.sort_values(GCOLS+["race_date","canonical_race_id"],kind="stable").reset_index(drop=True).copy()
    g=x.groupby(GCOLS,sort=False,dropna=False)
    x["_n"]=g.cumcount()
    em=(g["official_race_time_seconds"].expanding().median().reset_index(level=GCOLS,drop=True).sort_index())
    x["_em"]=em
    x["_pm"]=x.groupby(GCOLS,sort=False,dropna=False)["_em"].shift(1)
    dk=GCOLS+["race_date"]
    x["n_new"]=x.groupby(dk,sort=False,dropna=False)["_n"].transform("first")
    x["m_new"]=x.groupby(dk,sort=False,dropna=False)["_pm"].transform("first")
    x.loc[x["n_new"]<MIN_SAMPLE,"m_new"]=np.nan
    return x.sort_values("canonical_race_id")

def main():
    rows=[]; i=0
    spec=[
      ("2026-01-01","A",1200,"GOOD",[70,72]),
      ("2026-01-02","A",1200,"GOOD",[68]),
      ("2026-01-03","A",1200,"GOOD",[69,71]),
      ("2026-01-03","B",1400,"SOFT",[85,86]),
      ("2026-01-04","A",1200,"GOOD",[67]),
      ("2026-01-04","B",1400,"SOFT",[84]),
      ("2026-01-05","B",1400,"SOFT",[83,82]),
    ]
    for dt,t,d,c,ts in spec:
        for v in ts:
            i+=1; rows.append({"canonical_race_id":f"R{i:03d}","race_date":pd.Timestamp(dt),"track_key":t,"distance_metres":d,"condition":c,"official_race_time_seconds":v})
    r=pd.DataFrame(rows)
    a=old_loop(r); b=vector(r)
    z=a[["canonical_race_id","n_old","m_old"]].merge(b[["canonical_race_id","n_new","m_new"]],on="canonical_race_id",validate="one_to_one")
    if not (z.n_old.to_numpy()==z.n_new.to_numpy()).all(): raise RuntimeError("Prior-count equivalence failed")
    if not np.allclose(z.m_old,z.m_new,equal_nan=True): raise RuntimeError("Prior-median equivalence failed")
    same=b[(b.track_key=="A")&(b.race_date==pd.Timestamp("2026-01-03"))]
    if same.n_new.nunique()!=1 or same.m_new.nunique(dropna=False)!=1: raise RuntimeError("Same-date freeze failed")
    print("LAB245B_VECTOR_PIT_EQUIVALENCE=PASS")
    print(f"ROWS={len(z)} SAME_DATE_FREEZE=PASS")

if __name__=="__main__": main()
