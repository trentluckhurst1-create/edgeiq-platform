from pathlib import Path
# Stage012 deliberately reuses Stage011 construction, then tests only race-relative transforms.
p=Path(__file__).parent/"run_v2_stage011_clean_placing.py"
s=p.read_text(encoding="utf-8")
# intercept immediately before features definition by augmenting x with within-race relative fields
old='features=base+list(clean.columns)'
new='''rel_src=[c for c in ["trainer_prior_win_rate","trainer_prior_top3_rate","jockey_prior_win_rate","jockey_prior_top3_rate","barrier_position_pct","clean_finish_mean5","clean_last_finish"] if c in x.columns]
rel=[]
for c in rel_src:
    rc=c+"_field_rel"
    x[rc]=x[c]-x.groupby("_race")[c].transform("median")
    rel.append(rc)
features=base+list(clean.columns)+rel
print("V2_STAGE012_REL_FEATURES",len(rel),"|".join(rel))'''
s=s.replace(old,new).replace("V2_STAGE011_CONTRACT","V2_STAGE012_CONTRACT").replace("V2_STAGE011_CLEAN_COVERAGE","V2_STAGE012_CLEAN_COVERAGE").replace("V2_STAGE011_YEAR","V2_STAGE012_YEAR").replace("V2_STAGE011_COMPLETE","V2_STAGE012_COMPLETE").replace("REBUILD_CLEAN_STRICT_PRIOR_PLACING_FROM_PERF026 STAGE008_PLUS_CLEAN_PLACE","STAGE011_PLUS_RACE_RELATIVE_PROVEN_CORE")
exec(compile(s,str(p),"exec"))
