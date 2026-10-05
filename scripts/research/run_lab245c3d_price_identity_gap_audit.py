from pathlib import Path
import os,json,re
import pandas as pd, numpy as np
ROOT=Path(__file__).resolve().parents[2]; DATA=Path(os.environ.get("EDGEIQ_DATA_ROOT",str(ROOT))).resolve()
D=ROOT/"outputs/research/profitability_program/lab245b"
P=D/"LAB245C2_FULL_FIELD_OOF_PROBABILITIES.csv"
S=DATA/"outputs/research/model_price_diagnostics/forward_validation/LAB146_COMPLETE_HISTORICAL_E264_MATRIX.csv"
OUT=D/"LAB245C3D_PRICE_IDENTITY_GAP_AUDIT.json"; RACES=D/"LAB245C3D_PRICE_IDENTITY_GAP_RACES.csv"
def norm(x):
 return x.astype("string").str.upper().str.replace(r"[^A-Z0-9]","",regex=True)
def main():
 p=pd.read_csv(P,low_memory=False); s=pd.read_csv(S,usecols=["_race","_horse","starting_price_decimal"],low_memory=False)
 for x in [p,s]:
  x["_race"]=x._race.astype("string").str.strip(); x["_horse"]=x._horse.astype("string").str.strip()
 s["_sp"]=pd.to_numeric(s.starting_price_decimal,errors="coerce"); s=s[s._sp.gt(1)].drop_duplicates(["_race","_horse"])
 exact=p.merge(s[["_race","_horse","_sp"]],on=["_race","_horse"],how="left",validate="one_to_one")
 rc=exact.groupby("_race").agg(year=("_year","first"),model_rows=("_horse","size"),exact_sp_rows=("_sp",lambda z:int(z.notna().sum())))
 rc["missing"]=rc.model_rows-rc.exact_sp_rows
 # Race identity coverage independent of horse identity
 sr=set(s._race); rc["source_race_present"]=rc.index.to_series().isin(sr).values
 # Within same exact race, test normalized horse-name recovery only; diagnostics, not promoted prices.
 p2=p[["_race","_horse"]].copy(); p2["_hn"]=norm(p2._horse)
 s2=s[["_race","_horse"]].copy(); s2["_hn"]=norm(s2._horse)
 # only unique normalized horse identities within race on each side
 pc=p2.groupby(["_race","_hn"]).size(); sc=s2.groupby(["_race","_hn"]).size()
 goodp=set(pc[pc.eq(1)].index); goods=set(sc[sc.eq(1)].index); recover=goodp & goods
 exkeys=set(zip(s._race,s._horse))
 unmatched=p2[[ (r,h) not in exkeys for r,h in zip(p2._race,p2._horse) ]].copy()
 unmatched["norm_same_race_recoverable"]=[(r,n) in recover for r,n in zip(unmatched._race,unmatched._hn)]
 rec=unmatched.groupby("_race").norm_same_race_recoverable.sum()
 rc["norm_name_recoverable"]=rc.index.to_series().map(rec).fillna(0).astype(int).values
 rc["potential_rows_after_norm"]=rc.exact_sp_rows+rc.norm_name_recoverable
 rc["potential_complete_after_norm"]=rc.potential_rows_after_norm.eq(rc.model_rows)
 rc.to_csv(RACES)
 audit={
 "contract_version":"LAB245C3D_PRICE_IDENTITY_GAP_AUDIT_V1",
 "probability_races":int(len(rc)),
 "source_race_present":int(rc.source_race_present.sum()),
 "exact_any_sp_races":int((rc.exact_sp_rows>0).sum()),
 "exact_complete_races":int(rc.exact_sp_rows.eq(rc.model_rows).sum()),
 "partial_races":int(((rc.exact_sp_rows>0)&(rc.exact_sp_rows<rc.model_rows)).sum()),
 "zero_exact_match_races":int(rc.exact_sp_rows.eq(0).sum()),
 "missing_model_runner_rows":int(rc.missing.sum()),
 "normalized_same_race_unique_name_recoverable_rows":int(unmatched.norm_same_race_recoverable.sum()),
 "potential_complete_races_after_normalized_name":int(rc.potential_complete_after_norm.sum()),
 "potential_complete_by_year_after_normalized_name":{str(y):int(((rc.year==y)&rc.potential_complete_after_norm).sum()) for y in [2022,2023,2024]},
 "note":"normalized-name matches are diagnostic only; no prices promoted by this audit",
 "holdout_2025_2026_opened":False}
 OUT.write_text(json.dumps(audit,indent=2)); print(json.dumps(audit,indent=2))
 print("\nMISSING_RUNNERS_DISTRIBUTION"); print(rc["missing"].value_counts().sort_index().head(25).to_string())
if __name__=="__main__":main()
