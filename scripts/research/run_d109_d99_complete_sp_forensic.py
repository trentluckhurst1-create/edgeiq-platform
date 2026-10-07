from pathlib import Path
base=(Path(__file__).parent/'run_d107_d99_family_ablation.py').read_text(encoding='utf-8')
cut=base.index('print("D107_CONTRACT')
setup=base[:cut]
extra=r'''
H=ROOT/"outputs"/"research"/"model_price_diagnostics"/"forward_validation"/"LAB146_COMPLETE_HISTORICAL_E264_MATRIX.csv"
hh=pd.read_csv(H,usecols=["_race","_horse","starting_price_decimal"]);hh["_race"]=hh["_race"].astype(str);hh["_horse"]=hh["_horse"].astype(str);hh["_sp"]=pd.to_numeric(hh.starting_price_decimal,errors="coerce");hh=hh[hh._sp.gt(1)].drop_duplicates(["_race","_horse"],keep=False)
z["_race"]=z["_race"].astype(str);z["_horse"]=z["_horse"].astype(str);z=z.merge(hh[["_race","_horse","_sp"]],on=["_race","_horse"],how="left",validate="one_to_one")
race_ok=z.groupby("_race").agg(n=("y","size"),priced=("_sp",lambda x:x.notna().sum()),wins=("y","sum"));complete=set(race_ok.index[(race_ok.n==race_ok.priced)&(race_ok.wins==1)])
print("D109_CONTRACT COMPLETE_FIELD_SP_FORENSIC PREP48_VS_D99 NO_PRICE_TRAINING NO_THRESHOLD_SEARCH")
for yr in [2022,2023,2024]:
 tr=z.year_eval<yr;te=z.year_eval.eq(yr)&z._race.isin(complete)
 for name,ff in [("PREP48",F0),("D99",F99)]:
  m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42));m.fit(z.loc[tr,ff],z.loc[tr,"y"]);q=z.loc[te,["_race","y","_sp"]].copy();q["s"]=m.decision_function(z.loc[te,ff]);q["p"]=q.groupby("_race").s.transform(lambda a:np.exp(a-a.max())/np.exp(a-a.max()).sum());q["rawq"]=1/q._sp;q["mq"]=q.rawq/q.groupby("_race").rawq.transform("sum");q["resid"]=q.p-q.mq;w=q[q.y.eq(1)]
  print("D109_RESULT",yr,name,"RUNNERS",len(q),"RACES",q._race.nunique(),"MODEL_LL",float(-np.log(w.p.clip(1e-12,1)).mean()),"MARKET_LL",float(-np.log(w.mq.clip(1e-12,1)).mean()),"ABS_RESID",float(q.resid.abs().mean()))
  q["band"]=pd.cut(q._sp,[1,2,4,8,16,np.inf],right=False,labels=["1-2","2-4","4-8","8-16","16+"])
  for band,g in q.groupby("band",observed=True):print("D109_BAND",yr,name,str(band),"N",len(g),"MEAN_P_MINUS_MARKET",float(g.resid.mean()))
print("D109_COMPLETE FINAL_SP_FORENSIC_ONLY 2025_2026_SEALED")
'''
Path('/tmp/noop') if False else None
exec(compile(setup+extra,'D109','exec'))
