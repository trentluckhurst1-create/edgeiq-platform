from pathlib import Path
base=(Path(__file__).parent/'run_d107_d99_family_ablation.py').read_text(encoding='utf-8');setup=base[:base.index('print("D107_CONTRACT')]
extra=r'''
for c in ["trainer_prior_win_rate","trainer_prior_top3_rate"]:
 z[c+"_field_rel"]=z[c]-z.groupby("_race")[c].transform("median")
F112=F99+["trainer_prior_win_rate_field_rel","trainer_prior_top3_rate_field_rel"]
print("D112_CONTRACT D99_PLUS_TRAINER_QUALITY_FIELD_REL SAME_L5_T1 NO_SEARCH PASS_BOTH_SELECTION_YEARS_TOP1_FLOOR_MINUS_0.005")
def sc(yr,name,ff):
 tr=z.year_eval<yr;te=z.year_eval.eq(yr);m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42));m.fit(z.loc[tr,ff],z.loc[tr,"y"]);q=z.loc[te,["_race","y"]].copy();q["s"]=m.decision_function(z.loc[te,ff]);q["p"]=q.groupby("_race").s.transform(lambda a:np.exp(a-a.max())/np.exp(a-a.max()).sum());q["rank"]=q.groupby("_race").s.rank(ascending=False,method="first");w=q[q.y.eq(1)];print("D112_RESULT",yr,name,"NFEATURES",len(ff),"TOP1",float((w["rank"]==1).mean()),"TOP2",float((w["rank"]<=2).mean()),"TOP3",float((w["rank"]<=3).mean()),"MRR",float((1/w["rank"]).mean()),"LL",float(-np.log(w.p.clip(1e-12,1)).mean()))
for yr in [2022,2023,2024]:
 sc(yr,"D99",F99);sc(yr,"D112_TRAINER_REL",F112)
print("D112_COMPLETE 2025_2026_SEALED")
'''
exec(compile(setup+extra,'D112','exec'))
