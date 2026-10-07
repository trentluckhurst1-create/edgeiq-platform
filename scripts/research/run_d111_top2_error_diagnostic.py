from pathlib import Path
base=(Path(__file__).parent/'run_d107_d99_family_ablation.py').read_text(encoding='utf-8');setup=base[:base.index('print("D107_CONTRACT')]
extra=r'''
print("D111_CONTRACT D99_TOP2_ERROR_FEATURE_DIAGNOSTIC NO_NEW_MODEL NO_SEARCH")
for yr in [2022,2023,2024]:
 tr=z.year_eval<yr;te=z.year_eval.eq(yr);m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42));m.fit(z.loc[tr,F99],z.loc[tr,"y"]);q=z.loc[te,["_race","_horse","y"]+F99].copy();q["s"]=m.decision_function(z.loc[te,F99]);q["rank"]=q.groupby("_race").s.rank(ascending=False,method="first")
 w=q[q.y.eq(1)][["_race","rank"]];races=set(w.loc[w["rank"].le(2),"_race"]);top=q[q._race.isin(races)&q["rank"].le(2)].copy()
 rows=[]
 for race,g in top.groupby("_race"):
  if len(g)!=2:continue
  g=g.sort_values("rank");win=g[g.y.eq(1)]
  if len(win)!=1:continue
  correct=int(win.iloc[0]["rank"]==1)
  a=g.iloc[0];b=g.iloc[1]
  for c in F99:
   av=pd.to_numeric(pd.Series([a[c]]),errors="coerce").iloc[0];bv=pd.to_numeric(pd.Series([b[c]]),errors="coerce").iloc[0]
   if pd.notna(av) and pd.notna(bv):rows.append((c,correct,float(av-bv)))
 x=pd.DataFrame(rows,columns=["feature","correct","gap"])
 print("D111_YEAR",yr,"TOP2_RACES",len(races),"CORRECT",int(w[w["rank"].le(2)]["rank"].eq(1).sum()),"WRONG",int(w[w["rank"].le(2)]["rank"].eq(2).sum()))
 out=[]
 for c,g in x.groupby("feature"):
  a=g[g.correct.eq(1)].gap;b=g[g.correct.eq(0)].gap
  if len(a)>=20 and len(b)>=20:
   scale=float(g.gap.std())
   effect=(float(a.mean())-float(b.mean()))/scale if scale>0 else 0
   out.append((abs(effect),effect,c,len(a),len(b),float(a.mean()),float(b.mean())))
 for row in sorted(out,reverse=True)[:15]:print("D111_FEATURE",yr,"ABS_EFFECT",row[0],"EFFECT",row[1],"FEATURE",row[2],"N_CORRECT",row[3],"N_WRONG",row[4],"GAP_CORRECT",row[5],"GAP_WRONG",row[6])
print("D111_COMPLETE 2025_2026_SEALED")
'''
exec(compile(setup+extra,'D111','exec'))
