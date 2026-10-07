from pathlib import Path
base=(Path(__file__).parent/'run_d107_d99_family_ablation.py').read_text(encoding='utf-8');setup=base[:base.index('print("D107_CONTRACT')]
extra=r'''
print("D110_CONTRACT PREP48_VS_D99_CONTENDER_DISCRIMINATION NO_NEW_MODEL NO_SEARCH")
for yr in [2022,2023,2024]:
 tr=z.year_eval<yr;te=z.year_eval.eq(yr)
 scores={}
 for name,ff in [("PREP48",F0),("D99",F99)]:
  m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42));m.fit(z.loc[tr,ff],z.loc[tr,"y"]);q=z.loc[te,["_race","y"]].copy();q["s"]=m.decision_function(z.loc[te,ff]);q["p"]=q.groupby("_race").s.transform(lambda a:np.exp(a-a.max())/np.exp(a-a.max()).sum());q["rank"]=q.groupby("_race").s.rank(ascending=False,method="first");q["topgap"]=q.groupby("_race").s.transform(lambda a:a.nlargest(2).iloc[0]-a.nlargest(2).iloc[1] if len(a)>1 else np.nan);scores[name]=q
  w=q[q.y.eq(1)]
  for k in [1,2,3]:
   print("D110_HIT",yr,name,"TOP",k,"RATE",float((w["rank"]<=k).mean()))
  # among races where winner is top2, how often winner is ranked first?
  w2=w[w["rank"]<=2];print("D110_TOP2_ORDER",yr,name,"N",len(w2),"WINNER_RANK1_GIVEN_TOP2",float((w2["rank"]==1).mean()),"MEAN_WINNER_P",float(w2.p.mean()),"MEAN_TOPGAP",float(w2.topgap.mean()))
  w3=w[w["rank"]<=3];print("D110_TOP3_ORDER",yr,name,"N",len(w3),"WINNER_RANK1_GIVEN_TOP3",float((w3["rank"]==1).mean()),"MRR_GIVEN_TOP3",float((1/w3["rank"]).mean()))
print("D110_COMPLETE 2025_2026_SEALED")
'''
exec(compile(setup+extra,'D110','exec'))
