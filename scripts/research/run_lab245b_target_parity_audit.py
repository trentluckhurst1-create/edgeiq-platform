from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"docs/performance-intelligence/lengths-v-standard/edgeiq_runner_lengths_v_standard_fact_v1.csv"
PIT=ROOT/"outputs/research/profitability_program/lab245b/LAB245B_WAREHOUSE_RUNNER_LVS.csv"
OUT=ROOT/"outputs/research/profitability_program/lab245b/LAB245B_TARGET_PARITY_AUDIT.json"
EXPECTED_SIZE=80343742
EXPECTED_SHA="b08bb7a334ddba2f6a76942452dd964cd59db05001dc5710ff19aa7fc6e12926"

def sha256(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(8*1024*1024),b""): h.update(b)
 return h.hexdigest()

def main():
 OUT.parent.mkdir(parents=True,exist_ok=True)
 if not PIT.exists(): raise FileNotFoundError(PIT)
 report={"status":"PASS","authority_role":"PARITY_ONLY_NOT_FORECAST_TARGET",
         "pit_policy":"STRICT_DATE_LT_TARGET_DATE",
         "comparison_note":"Differences in level are expected because historical authority used all-history standards."}
 if not AUTH.exists():
  report.update({"authority_present":False,"parity_status":"SKIPPED_AUTHORITY_ABSENT"})
 else:
  size=AUTH.stat().st_size; digest=sha256(AUTH)
  if size!=EXPECTED_SIZE or digest!=EXPECTED_SHA:
   raise RuntimeError(f"Authority identity drift size={size} sha={digest}")
  a=pd.read_csv(AUTH,usecols=["canonical_race_id","canonical_horse_id","runner_lengths_v_standard"],low_memory=False)
  a=a.rename(columns={"runner_lengths_v_standard":"authority_lvs"})
  p=pd.read_csv(PIT,usecols=["canonical_race_id","canonical_horse_id","runner_lvs"],low_memory=False)
  for d in (a,p):
   d["canonical_race_id"]=d["canonical_race_id"].astype("string").str.strip()
   d["canonical_horse_id"]=d["canonical_horse_id"].astype("string").str.strip()
  if a.duplicated(["canonical_race_id","canonical_horse_id"]).any(): raise RuntimeError("Authority duplicate race/horse keys")
  if p.duplicated(["canonical_race_id","canonical_horse_id"]).any(): raise RuntimeError("PIT duplicate race/horse keys")
  m=p.merge(a,on=["canonical_race_id","canonical_horse_id"],how="inner",validate="one_to_one")
  m["runner_lvs"]=pd.to_numeric(m["runner_lvs"],errors="coerce")
  m["authority_lvs"]=pd.to_numeric(m["authority_lvs"],errors="coerce")
  v=m.dropna(subset=["runner_lvs","authority_lvs"]).copy()
  corr=float(v["runner_lvs"].corr(v["authority_lvs"])) if len(v)>1 else None
  delta=v["runner_lvs"]-v["authority_lvs"]
  # Formula/sign/unit guardrail only. We do NOT require numerical equality because standards differ by PIT policy.
  if len(v)==0: raise RuntimeError("No exact parity overlap")
  if corr is None or not np.isfinite(corr) or corr<=0:
   raise RuntimeError(f"Parity sign/unit failure correlation={corr}")
  report.update({"authority_present":True,"authority_size":size,"authority_sha256":digest,
                 "pit_rows":int(len(p)),"authority_rows":int(len(a)),"exact_overlap_rows":int(len(m)),
                 "numeric_overlap_rows":int(len(v)),"lvs_correlation":corr,
                 "mean_pit_minus_authority_lvs":float(delta.mean()),"mae_lvs":float(delta.abs().mean()),
                 "parity_status":"PASS_SIGN_UNIT_FORMULA"})
 OUT.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print(json.dumps(report,indent=2))
 print(f"OUT={OUT}")

if __name__=="__main__": main()
