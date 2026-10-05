from pathlib import Path
import pandas as pd, numpy as np, math, json
from collections import defaultdict
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier

R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
O=R/"outputs/research/profitability_program/lab245b"
B=O/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
S=O/"LAB245B_WAREHOUSE_RUNNER_LVS.csv"

base=["hist_runs","current_distance","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_std5","margin_worst5","finishpos_mean5","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best"]
b=pd.read_csv(B,low_memory=False)
b["_race"]=b["_race"].astype(str); b["_horse"]=b["_horse"].astype(str)
b["target_finish_position"]=pd.to_numeric(b["target_finish_position"],errors="coerce")
b=b[b["target_finish_position"].notna()].copy()
b["y"]=(b["target_finish_position"]==1).astype(int)

use=["canonical_race_id","canonical_horse_id","race_date","distance_metres","runner_lvs"]
d=pd.read_csv(S,usecols=use,low_memory=False)
d["race_date"]=pd.to_datetime(d["race_date"],errors="coerce")
d["distance_metres"]=pd.to_numeric(d["distance_metres"],errors="coerce")
d["runner_lvs"]=pd.to_numeric(d["runner_lvs"],errors="coerce")
d=d.dropna(subset=["canonical_race_id","canonical_horse_id","race_date"]).sort_values(["canonical_horse_id","race_date","canonical_race_id"],kind="stable")
targets=set(zip(b["_race"],b["_horse"]))
extra={}
for horse,g in d.groupby("canonical_horse_id",sort=False):
    horse=str(horse); vals=[]; dated=[]; dist_hist=[]
    for dt,day in g.groupby("race_date",sort=True):
        lv=np.asarray([v for _,v in vals],float)
        last5=lv[-5:]; last10=lv[-10:]
        peak_i=int(np.argmax(lv)) if len(lv) else -1
        peak=float(lv[peak_i]) if peak_i>=0 else np.nan
        med10=float(np.median(last10)) if len(last10) else np.nan
        recent=last5
        slope=float(np.polyfit(np.arange(len(last5)),last5,1)[0]) if len(last5)>=2 else np.nan
        for r in day.itertuples(index=False):
            key=(str(r.canonical_race_id),horse)
            if key not in targets: continue
            near=[v for dd,v in dist_hist if pd.notna(r.distance_metres) and abs(dd-float(r.distance_metres))<=200]
            extra[key]={
                "rich_best3":float(np.max(lv[-3:])) if len(lv) else np.nan,
                "rich_best5":float(np.max(last5)) if len(last5) else np.nan,
                "rich_second_best5":float(np.sort(last5)[-2]) if len(last5)>=2 else np.nan,
                "rich_median10":med10,
                "rich_best10":float(np.max(last10)) if len(last10) else np.nan,
                "rich_worst10":float(np.min(last10)) if len(last10) else np.nan,
                "rich_std10":float(np.std(last10)) if len(last10)>=2 else np.nan,
                "rich_peak_minus_median10":peak-med10 if np.isfinite(peak) and np.isfinite(med10) else np.nan,
                "rich_last1_minus_peak":float(lv[-1]-peak) if len(lv) else np.nan,
                "rich_last1_minus_median5":float(lv[-1]-np.median(last5)) if len(last5) else np.nan,
                "rich_slope5":slope,
                "rich_days_since_peak":(dt-dated[peak_i]).days if peak_i>=0 else np.nan,
                "rich_peak_age_runs":len(lv)-1-peak_i if peak_i>=0 else np.nan,
                "rich_dist200_best_minus_peak":float(max(near)-peak) if near and np.isfinite(peak) else np.nan,
                "rich_near_peak_share_last10":float(np.mean(last10>=peak-1.0)) if len(last10) and np.isfinite(peak) else np.nan,
                "rich_recent_above_last10_median_share":float(np.mean(recent>=med10)) if len(recent) and np.isfinite(med10) else np.nan,
            }
        for r in day.itertuples(index=False):
            if pd.notna(r.runner_lvs):
                v=float(r.runner_lvs); vals.append((dt,v)); dated.append(dt)
                if pd.notna(r.distance_metres): dist_hist.append((float(r.distance_metres),v))

e=pd.DataFrame.from_dict(extra,orient="index")
e.index=pd.MultiIndex.from_tuples(e.index,names=["_race","_horse"])
e=e.reset_index()
x=b.merge(e,on=["_race","_horse"],how="left",validate="one_to_one")
rich=[c for c in x.columns if c.startswith("rich_")]
rankable=[c for c in base+rich if c!="current_distance"]
for c in rankable:
    v=pd.to_numeric(x[c],errors="coerce")
    x[c+"_rank_pct"]=v.groupby(x["_race"]).rank(pct=True,method="average")
    mu=v.groupby(x["_race"]).transform("mean"); sd=v.groupby(x["_race"]).transform("std").replace(0,np.nan)
    x[c+"_z"]=(v-mu)/sd
families={
    "BASE17":base,
    "RICH_RAW":base+rich,
    "RICH_RANK":base+rich+[c+"_rank_pct" for c in rankable],
    "RICH_ALL":base+rich+[c+"_rank_pct" for c in rankable]+[c+"_z" for c in rankable],
}
def mk(seed):
    return make_pipeline(SimpleImputer(strategy="median",add_indicator=True),HistGradientBoostingClassifier(max_iter=350,learning_rate=.035,max_leaf_nodes=15,min_samples_leaf=30,l2_regularization=10,random_state=seed))
def met(q):
    a=[]
    for _,g in q.groupby("_race",sort=False):
        w=np.flatnonzero(g.y.to_numpy()==1)
        if len(w)!=1: continue
        s=g.s.to_numpy(); p=np.clip(s,1e-12,None); p/=p.sum()
        rk=int(pd.Series(s).rank(ascending=False,method="first").iloc[w[0]])
        a.append((rk,-math.log(max(p[w[0]],1e-12))))
    a=np.asarray(a,float)
    return len(a),np.mean(a[:,0]<=1),np.mean(a[:,0]<=2),np.mean(a[:,0]<=3),np.mean(1/a[:,0]),np.mean(a[:,1])
res=[]
for yr in [2022,2023,2024]:
    tr=x[x["_year"]<yr]; te=x[x["_year"]==yr]
    for i,(name,ff) in enumerate(families.items()):
        m=mk(3170+i); m.fit(tr[ff],tr.y)
        q=te[["_race","y"]].copy(); q["s"]=m.predict_proba(te[ff])[:,1]
        res.append([yr,name,len(ff),*met(q)])
o=pd.DataFrame(res,columns=["year","model","features","races","top1","top2","top3","mrr","race_log_loss"])
dev=o[o.year.isin([2022,2023])].groupby("model").mean(numeric_only=True).drop(columns=["year","features","races"]).sort_values("top1",ascending=False)
print(o.to_string(index=False)); print("\nDEV\n"+dev.to_string())
audit={"contract":"LAB245D17A_OPTIMIZED_RICH_HISTORY_V1","rows":len(x),"races":int(x._race.nunique()),"extra_features":rich,"pit_policy":"DATE_LT_TARGET_DATE_SAME_DATE_FROZEN","selection_years":[2022,2023],"2024_role":"OBSERVED_DIAGNOSTIC_ONLY","2025_2026_opened":False,"market_used":False,"dev":dev.reset_index().to_dict("records")}
o.to_csv(O/"LAB245D17A_OPTIMIZED_RICH_HISTORY.csv",index=False)
(O/"LAB245D17A_OPTIMIZED_RICH_HISTORY.json").write_text(json.dumps(audit,indent=2))
print(json.dumps(audit,indent=2))
