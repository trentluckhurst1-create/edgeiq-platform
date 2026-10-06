from pathlib import Path
import pandas as pd,numpy as np
from scipy.optimize import minimize
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
P=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\d45\D45_FROZEN_PIT_FEATURE_MATRIX.csv")
d=pd.read_csv(P);d["date"]=pd.to_datetime(d.race_date);d["year"]=d.date.dt.year
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone"}
num=[c for c in d if c not in meta and pd.api.types.is_numeric_dtype(d[c])]
context={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"}
F=[c for c in num if c not in context]
# compact choice model: remove obvious count/scale duplicates, retain race-relative performance/barrier/JT rates
F=[c for c in F if ("rank" not in c.lower()) and not c.endswith("_starts")]
print("D51_CHOICE_START FEATURES",len(F),F)
def fit_eval(yr,l2):
 tr=d.year<yr;te=d.year.eq(yr)
 imp=SimpleImputer(strategy="median");sc=StandardScaler()
 Xtr=sc.fit_transform(imp.fit_transform(d.loc[tr,F]));Xte=sc.transform(imp.transform(d.loc[te,F]))
 y=d.loc[tr,"y"].to_numpy(float); races=d.loc[tr,"_race"].astype("category").cat.codes.to_numpy()
 # contiguous race groups after current dataframe order not guaranteed; use index lists
 groups={}
 for k,ix in enumerate(races):groups.setdefault(ix,[]).append(k)
 def fg(b):
  z=Xtr@b;loss=0.;g=np.zeros_like(b)
  for inds in groups.values():
   a=np.asarray(inds);zz=z[a];m=zz.max();e=np.exp(zz-m);p=e/e.sum();yy=y[a];loss-=float((yy*np.log(np.clip(p,1e-15,1))).sum());g+=Xtr[a].T@(p-yy)
  loss+=.5*l2*np.dot(b,b);g+=l2*b;return loss,g
 res=minimize(lambda b:fg(b),np.zeros(Xtr.shape[1]),jac=True,method="L-BFGS-B",options={"maxiter":150,"ftol":1e-9})
 q=d.loc[te,["_race","y"]].copy();q["s"]=Xte@res.x;q["p"]=q.groupby("_race")["s"].transform(lambda x:np.exp(x-x.max())/np.exp(x-x.max()).sum());q["rank"]=q.groupby("_race").s.rank(ascending=False,method="first");w=q[q.y.eq(1)]
 print("RESULT",yr,"L2",l2,"CONV",res.success,"TOP1",float((w["rank"]<=1).mean()),"TOP2",float((w["rank"]<=2).mean()),"TOP3",float((w["rank"]<=3).mean()),"MRR",float((1/w["rank"]).mean()),"LL",float(-np.log(w.p.clip(1e-12,1)).mean()))
for yr in [2022,2023,2024]:
 for l2 in [.1,1.,10.]:fit_eval(yr,l2)
print("D51_CHOICE_COMPLETE")
