from pathlib import Path
import json, hashlib, sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/research/profitability_program/bootstrap"
OUT.mkdir(parents=True, exist_ok=True)

required=[
"outputs/research/model_price_diagnostics/lab229/LAB229_OOF_PREDICTIONS_CORRECTED.csv",
"outputs/research/model_price_diagnostics/lab230/LAB230_SUMMARY.csv",
"outputs/research/model_price_diagnostics/lab231/LAB231_SUMMARY.csv",
"outputs/research/model_price_diagnostics/lab231/LAB231_PRIMARY_RESULTS.csv",
"outputs/research/model_price_diagnostics/lab232/LAB232_SUMMARY.csv",
"outputs/research/model_price_diagnostics/lab232/LAB232_PRIMARY_RESULTS.csv",
]
optional=[
"outputs/research/model_price_diagnostics/lab231/run_lab231_performance_representation_search.py",
"outputs/research/model_price_diagnostics/lab232/run_lab232_evidence_supported_performance_combos.py",
"outputs/research/model_lab_026/edgeiq_certified_flat_walk_forward_epi_026.csv",
]
def meta(rel):
    p=ROOT/rel
    d={"path":rel,"exists":p.exists()}
    if p.exists() and p.is_file():
        d["bytes"]=p.stat().st_size
        if p.stat().st_size <= 100_000_000:
            h=hashlib.sha256()
            with p.open("rb") as f:
                for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
            d["sha256"]=h.hexdigest()
    return d
audit={"required":[meta(x) for x in required],"optional":[meta(x) for x in optional]}
audit["required_complete"]=all(x["exists"] for x in audit["required"])
(OUT/"bootstrap_audit.json").write_text(json.dumps(audit,indent=2),encoding="utf-8")
print(json.dumps(audit,indent=2))
print("PRODUCTION_MODIFIED=NO")
print("MARKET_AS_FEATURE=NO")
print("BOOTSTRAP_REQUIRED_COMPLETE="+("YES" if audit["required_complete"] else "NO"))
if not audit["required_complete"]:
    print("RESEARCH_EXECUTION_BLOCKED=MISSING_REMOTE_ARTIFACTS")
    sys.exit(2)
print("RESEARCH_EXECUTION_READY=YES")
