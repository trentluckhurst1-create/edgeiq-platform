from pathlib import Path
import json
import os
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/research/profitability_program/lab245b"
PY=sys.executable

def run(script):
    print(f"\n=== RUN {script} ===",flush=True)
    env=os.environ.copy()
    subprocess.run([PY,str(ROOT/script)],cwd=ROOT,env=env,check=True)

def audit(name):
    p=OUT/name
    if not p.exists():
        raise FileNotFoundError(p)
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    print("LAB245B PREHOLDOUT GOVERNED CHAIN")
    print(f"EDGEIQ_DATA_ROOT={os.environ.get('EDGEIQ_DATA_ROOT',str(ROOT))}")
    print("HOLDOUT_POLICY=2025_2026_CANNOT_BE_OPENED_BY_THIS_LAUNCHER")
    run("scripts/research/run_lab245b_preflight.py")
    run("scripts/research/build_lab245b_warehouse_runner_lvs.py")
    run("scripts/research/run_lab245b_target_parity_audit.py")
    run("scripts/research/build_lab245b_compact_performance_bridge.py")
    run("scripts/research/run_lab245b1_next_performance_forecast.py")
    a1=audit("LAB245B1_AUDIT.json")
    if a1.get("status")!="SURVIVE_TO_LAB245B2":
        print(f"CHAIN_STOP=B1 SCIENTIFIC_STATUS={a1.get('status')}")
        return
    run("scripts/research/run_lab245b2_probability_challenger.py")
    a2=audit("LAB245B2_AUDIT.json")
    if a2.get("status")!="SURVIVE_TO_LAB245B3":
        print(f"CHAIN_STOP=B2 SCIENTIFIC_STATUS={a2.get('status')}")
        return
    run("scripts/research/run_lab245b3_selective_betting_forensics.py")
    a3=audit("LAB245B3_AUDIT.json")
    print(f"CHAIN_STOP=PREHOLDOUT_COMPLETE B3_STATUS={a3.get('status')}")
    print("2025_2026_HOLDOUT_REMAINS_SEALED=YES")

if __name__=="__main__":
    main()
