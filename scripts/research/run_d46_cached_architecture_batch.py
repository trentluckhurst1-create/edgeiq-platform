from pathlib import Path
import pandas as pd,numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier,ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
P=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\d45\D45_FROZEN_PIT_FEATURE_MATRIX.csv")
d=pd.read_csv(P);d["date"]=pd.to_datetime(d["race_date"]);d["year"]=d["date"].dt.year
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone"}
num=[c for c in d.columns if c not in meta and pd.api.types.is_numeric_dtype(d[c])]
tb=[c for c in num if c.startswith("tb_mech_")];db=[c for c in num if c.startswith("db_mech_")];tdb=[c for c in num if c.startswith("tdb_mech_")]
context=set(tb+db+tdb+["distance_band_200"])
base=[c for c in num if c not in context]
families={"PBC":base,"PBC_TB":base+tb,"PBC_TDB":base+tdb,"PBC_TB_TDB":base+tb+tdb}
models={
"HGB15":lambda:make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=15,l2_regularization=1,random_state=42)),
"HGB31R5":lambda:make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=250,learning_rate=.04,max_leaf_nodes=31,l2_regularization=5,random_state=42)),
"HGB7R2":lambda:make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=250,learning_rate=.04,max_leaf_nodes=7,l2_regularization=2,random_state=42)),
"LOGIT":lambda:make_pipeline(SimpleImputer(strategy="median"),LogisticRegression(C=.2,max_iter=1000)),
"ET":lambda:make_pipeline(SimpleImputer(strategy="median"),ExtraTreesClassifier(n_estimators=300,min_samples_leaf=20,max_features=.7,n_jobs=-1,random_state=42))
}
print("D46_BATCH_START","ROWS",len(d),"RACES",d["_race"].nunique(),"NUMERIC",len(num))
for yr in [2022,2023,2024]:
 tr=d.year<yr;te=d.year.eq(yr)
 for fam,feats in families.items():
  for mn,mk in models.items():
   m=mk();m.fit(d.loc[tr,feats],d.loc[tr,"y"]);p=m.predict_proba(d.loc[te,feats])[:,1]
   q=d.loc[te,["_race","y"]].copy();q["p"]=p;q["rp"]=q.p/q.groupby("_race").p.transform("sum");q["rank"]=q.groupby("_race").p.rank(ascending=False,method="first")
   w=q[q.y.eq(1)];print("RESULT",yr,fam,mn,"RACES",len(w),"TOP1",float((w["rank"]<=1).mean()),"TOP2",float((w["rank"]<=2).mean()),"TOP3",float((w["rank"]<=3).mean()),"MRR",float((1/w["rank"]).mean()),"LL",float(-np.log(w["rp"].clip(1e-12,1)).mean()))
print("D46_BATCH_COMPLETE")
