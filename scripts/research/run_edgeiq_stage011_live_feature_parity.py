"""Read-only Stage011 feature parity diagnostic: never emits probabilities or bets.

Compares frozen model manifest against prospective feature input, and reports
coverage per feature and runner. Requires exact feature columns; never imputes
missing values or labels them certified.
"""
import argparse,json
from pathlib import Path
import pandas as pd
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--manifest",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\issue23_prospective_artifacts\ISSUE23_MODEL_ARTIFACT_MANIFEST.json")
 p.add_argument("--features",default="outputs/research/selection_gate_v2/CAULFIELD_EXPERIMENTAL_STAGE011_PREDICTIONS.csv")
 p.add_argument("--output",default="outputs/research/selection_gate_v2/STAGE011_LIVE_FEATURE_PARITY_REPORT.json")
 a=p.parse_args()
 m=json.loads(Path(a.manifest).read_text(encoding="utf-8"))
 required=m["features"]
 if len(required)!=len(set(required)) or not required:raise RuntimeError("STOP invalid feature manifest")
 d=pd.read_csv(a.features)
 if d.empty:raise RuntimeError("STOP empty live features")
 coverage={}
 for f in required:
  v=pd.to_numeric(d[f],errors="coerce") if f in d else pd.Series(float("nan"),index=d.index)
  coverage[f]={"populated":int(v.notna().sum()),"missing":int(v.isna().sum()),"coverage_pct":round(100*float(v.notna().mean()),2),"column_present":f in d.columns}
 observed=d[[f for f in required if f in d]].apply(pd.to_numeric,errors="coerce")
 row_count=observed.notna().sum(axis=1) if not observed.empty else pd.Series(0,index=d.index)
 complete=int(row_count.eq(len(required)).sum())
 result={"status":"FAIL" if complete!=len(d) else "COVERAGE_ONLY_NOT_SEMANTIC_CERTIFICATION",
 "rows":len(d),"required_feature_count":len(required),"complete_rows":complete,
 "incomplete_rows":len(d)-complete,"row_populated_feature_counts":{str(k):int(v) for k,v in row_count.value_counts().sort_index().items()},
 "feature_coverage":coverage,
 "critical_limitation":"Non-null feature coverage does not establish point-in-time provenance, training/live calculation parity, or prediction accuracy.",
 "model_probabilities_usable_for_betting":False}
 out=Path(a.output)
 if out.exists():raise RuntimeError("STOP immutable report already exists; supply new --output")
 out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(result,indent=2),encoding="utf-8")
 print("STAGE011 LIVE FEATURE PARITY",result["status"],"ROWS",len(d),"COMPLETE",complete)
 for k,v in coverage.items():print(f"{k:32s} {v['populated']:4d}/{len(d)}")
 print("REPORT",out)
 print("NO PROBABILITIES, NO BETS, NO MODEL PROMOTION")
if __name__=="__main__":main()
