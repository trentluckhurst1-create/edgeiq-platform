from pathlib import Path
import os,json,hashlib
import pandas as pd, numpy as np
ROOT=Path(__file__).resolve().parents[2]; DATA=Path(os.environ.get("EDGEIQ_DATA_ROOT",str(ROOT))).resolve()
D=ROOT/"outputs/research/profitability_program/lab245b"
P=D/"LAB245C2_FULL_FIELD_OOF_PROBABILITIES.csv"
SRC=DATA/"outputs/research/model_price_diagnostics/forward_validation/LAB146_COMPLETE_HISTORICAL_E264_MATRIX.csv"
OUT=D/"LAB245C3C_LAB146_PRICE_BRIDGE_AUDIT.json"; SAMPLE=D/"LAB245C3C_LAB146_PRICE_BRIDGE.csv"
def main():
 if not SRC.exists(): raise FileNotFoundError(SRC)
 h=pd.read_csv(SRC,nrows=0).columns.tolist()
 req={"_race","_horse","starting_price_decimal"}
 if not req.issubset(h): raise RuntimeError(f"LAB146 missing {req-set(h)}")
 use=["_race","_horse","starting_price_decimal"]+[c for c in ["race_date","_year","year"] if c in h]
 s=pd.read_csv(SRC,usecols=use,low_memory=False)
 s["_race"]=s._race.astype("string").str.strip(); s["_horse"]=s._horse.astype("string").str.strip(); s["_sp"]=pd.to_numeric(s.starting_price_decimal,errors="coerce")
 raw=len(s); valid=s._sp.gt(1)&s._sp.notna(); s=s[valid].copy()
 dup=int(s.duplicated(["_race","_horse"],keep=False).sum())
 # identical duplicate SP rows are safe to collapse; conflicting prices are not.
 g=s.groupby(["_race","_horse"],sort=False)._sp.agg(["size","nunique"]).reset_index()
 conflict=int((g.nunique>1).sum()); duplicate_keys=int((g["size"]>1).sum())
 if conflict: raise RuntimeError(f"LAB146 conflicting SP identity keys={conflict}")
 s=s.drop_duplicates(["_race","_horse"],keep="first")
 p=pd.read_csv(P,low_memory=False); p["_race"]=p._race.astype("string").str.strip(); p["_horse"]=p._horse.astype("string").str.strip()
 m=p.merge(s[["_race","_horse","_sp"]],on=["_race","_horse"],how="left",validate="one_to_one")
 rc=m.groupby("_race").agg(rows=("_horse","size"),sp_rows=("_sp",lambda z:int(z.notna().sum())),year=("_year","first"))
 full=rc[rc.rows.eq(rc.sp_rows)].copy()
 audit={"contract_version":"LAB245C3C_LAB146_PRICE_BRIDGE_AUDIT_V1","source":str(SRC),"source_bytes":SRC.stat().st_size,"source_raw_rows":raw,"source_valid_sp_rows":len(s),"duplicate_identity_rows":dup,"duplicate_identity_keys":duplicate_keys,"conflicting_sp_identity_keys":conflict,"probability_runner_rows":len(p),"matched_runner_rows":int(m._sp.notna().sum()),"probability_races":int(p._race.nunique()),"any_sp_races":int(rc[rc.sp_rows.gt(0)].shape[0]),"complete_field_races":len(full),"complete_field_race_coverage_pct":100*len(full)/p._race.nunique(),"complete_by_year":{str(y):int((full.year==y).sum()) for y in [2022,2023,2024]},"market_role":"FORENSIC_ONLY_NOT_MODEL_FEATURE","holdout_2025_2026_opened":False}
 OUT.write_text(json.dumps(audit,indent=2)); 
 m[m._race.isin(full.index)][["_year","race_date","_race","_horse","p_model","target_finish_position","_sp"]].to_csv(SAMPLE,index=False)
 print(json.dumps(audit,indent=2))
if __name__=="__main__":main()
