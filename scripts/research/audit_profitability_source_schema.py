from pathlib import Path
import pandas as pd, json, sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/research/profitability_program/schema_audit"
OUT.mkdir(parents=True,exist_ok=True)

sources=[
 ROOT/"outputs/research/model_price_diagnostics/lab231/LAB231_OOF_PREDICTIONS.csv",
 ROOT/"outputs/research/model_price_diagnostics/lab229/LAB229_OOF_PREDICTIONS_CORRECTED.csv",
 ROOT/"outputs/research/model_price_diagnostics/lab231/LAB231_HISTORICAL_PERFORMANCE_FEATURES.csv",
]
report=[]
for p in sources:
    item={"path":str(p.relative_to(ROOT)),"exists":p.exists()}
    if p.exists():
        item["bytes"]=p.stat().st_size
        try:
            df=pd.read_csv(p,nrows=5)
            item["columns"]=list(df.columns)
        except Exception as e:
            item["read_error"]=repr(e)
    report.append(item)

(OUT/"schema_audit.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
if not any(x["exists"] for x in report):
    print("RUNNER_EXTRACT_BLOCKED=LOCAL_LARGE_SOURCES_NOT_PRESENT_ON_GITHUB")
    sys.exit(2)
