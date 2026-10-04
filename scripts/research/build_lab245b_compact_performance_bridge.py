from pathlib import Path
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
LAB026=ROOT/"outputs/research/profitability_program/lab245b/LAB245B_WAREHOUSE_RUNNER_LVS.csv"
OUTDIR=ROOT/"outputs/research/profitability_program/lab245b"
OUT=OUTDIR/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"

NEED=["canonical_race_id","canonical_horse_id","race_date","distance_metres",
"finish_position","finish_margin","runner_lvs"]

def num(x): return pd.to_numeric(x,errors="coerce")

def main():
    OUTDIR.mkdir(parents=True,exist_ok=True)
    if not LAB026.exists(): raise FileNotFoundError(LAB026)
    d=pd.read_csv(LAB026,usecols=NEED,low_memory=False)
    d["canonical_race_id"]=d["canonical_race_id"].astype("string").str.strip()
    d["canonical_horse_id"]=d["canonical_horse_id"].astype("string").str.strip()
    d["race_date"]=pd.to_datetime(d["race_date"],errors="coerce")
    for c in ["distance_metres","finish_position","finish_margin","runner_lvs"]:
        d[c]=num(d[c])
    d=d.dropna(subset=["canonical_race_id","canonical_horse_id","race_date"])
    d=d.sort_values(["canonical_horse_id","race_date","canonical_race_id"],kind="stable")
    # Same-date history is deliberately excluded: all summaries shift by date, not row.
    rows=[]
    for horse,g in d.groupby("canonical_horse_id",sort=False):
        history=[]
        for dt,day in g.groupby("race_date",sort=True):
            prior=pd.DataFrame(history)
            for _,r in day.iterrows():
                year=int(dt.year)
                if 2021<=year<=2024:
                    rec={"_race":r.canonical_race_id,"_horse":horse,"_year":year,
                         "race_date":dt.date().isoformat(),"target_lvs":r.runner_lvs,
                         "current_distance":r.distance_metres,"hist_runs":len(prior)}
                    if len(prior):
                        e=prior["epi"].dropna(); l=prior["lvs"].dropna(); m=prior["margin"].dropna(); p=prior["pos"].dropna()
                        def tail(s,n): return s.tail(n)
                        rec.update({
                          "epi_last1":e.iloc[-1] if len(e) else np.nan,
                          "epi_mean3":tail(e,3).mean(),"epi_mean5":tail(e,5).mean(),
                          "epi_median5":tail(e,5).median(),"epi_peak":e.max(),"epi_worst5":tail(e,5).min(),
                          "epi_std5":tail(e,5).std(ddof=0),
                          "lvs_last1":l.iloc[-1] if len(l) else np.nan,
                          "lvs_mean3":tail(l,3).mean(),"lvs_mean5":tail(l,5).mean(),
                          "lvs_median5":tail(l,5).median(),"lvs_best":l.max(),"lvs_worst5":tail(l,5).min(),
                          "lvs_std5":tail(l,5).std(ddof=0),
                          "margin_mean5":tail(m,5).mean(),"margin_worst5":tail(m,5).max(),
                          "margin_std5":tail(m,5).std(ddof=0),"finishpos_mean5":tail(p,5).mean(),
                          "days_since_last":(dt-prior["date"].max()).days,
                        })
                        if pd.notna(r.distance_metres):
                            near=prior[(prior["distance"]-r.distance_metres).abs()<=200]
                            nl=near["lvs"].dropna(); ne=near["epi"].dropna()
                            rec.update({"dist200_runs":len(near),"dist200_lvs_mean":nl.mean(),
                              "dist200_lvs_best":nl.max(),"dist200_epi_mean":ne.mean(),"dist200_epi_best":ne.max()})
                    rows.append(rec)
            # Only after every runner on this date has been scored may this date enter history.
            for _,r in day.iterrows():
                history.append({"date":dt,"distance":r.distance_metres,"pos":r.finish_position,
                  "margin":r.finish_margin,"lvs":r.runner_lengths_v_standard_026,"epi":r.runner_lvs})
    out=pd.DataFrame(rows)
    if not out["_year"].between(2021,2024).all(): raise RuntimeError("Sealed-year breach.")
    if out.duplicated(["_race","_horse"]).any(): raise RuntimeError("Duplicate race/horse keys.")
    forbidden=[c for c in out if c.lower() in {"_sp","sp","final_sp","odds","p_model","market_probability"}]
    if forbidden: raise RuntimeError(f"Forbidden market columns: {forbidden}")
    out.to_csv(OUT,index=False)
    print(f"ROWS={len(out):,} RACES={out._race.nunique():,} OBS_TARGET={out.target_lvs.notna().sum():,}")
    print(f"TARGET_COVERAGE={out.target_lvs.notna().mean():.6f} YEARS={sorted(out._year.unique())}")
    print(f"OUT={OUT}")
if __name__=="__main__":main()