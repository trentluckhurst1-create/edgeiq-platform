from pathlib import Path
import json
import os
import hashlib
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/research/profitability_program/lab245b"
PY=sys.executable
EXPECTED_WAREHOUSE_SHA="bcdcef1c7cb9144feae5783ca2fa83b1dc2b8dc07a42ac31c31fd7bd12b53107"
EXPECTED_TARGET_CONTRACT="LAB245B_STRICT_PIT_LVS_V5_GOVERNED_TRACK_DISTANCE_CONDITION_MIN20"\nEXPECTED_AUTHORITY_SHA="b08bb7a334ddba2f6a76942452dd964cd59db05001dc5710ff19aa7fc6e12926"\nEXPECTED_AUTHORITY_BYTES=80343742
AUTHORITY=ROOT/"docs/performance-intelligence/lengths-v-standard/edgeiq_runner_lengths_v_standard_fact_v1.csv"
WAREHOUSE=ROOT/"docs/performance-intelligence/warehouse/edgeiq_performance_fact_warehouse_v1.csv"

def run(script):
    print(f"\\n=== RUN {script} ===",flush=True)
    env=os.environ.copy()
    subprocess.run([PY,str(ROOT/script)],cwd=ROOT,env=env,check=True)

def authority_valid():\n    if not AUTHORITY.exists() or AUTHORITY.stat().st_size!=EXPECTED_AUTHORITY_BYTES:\n        return False\n    h=hashlib.sha256()\n    with AUTHORITY.open("rb") as fh:\n        for b in iter(lambda:fh.read(16*1024*1024),b""): h.update(b)\n    return h.hexdigest()==EXPECTED_AUTHORITY_SHA\n\ndef target_checkpoint_valid():
    p=OUT/"LAB245B_WAREHOUSE_RUNNER_LVS.csv"
    m=OUT/"LAB245B_WAREHOUSE_RUNNER_LVS.manifest.json"
    if not p.exists() or not m.exists():
        return False
    try:
        x=json.loads(m.read_text(encoding="utf-8"))
    except Exception:
        return False
    if not (x.get("warehouse_sha256")==EXPECTED_WAREHOUSE_SHA and x.get("contract_version")==EXPECTED_TARGET_CONTRACT and x.get("pit_policy")=="STRICT_DATE_LT_TARGET_DATE"):
        return False
    if x.get("output_bytes")!=p.stat().st_size or not x.get("output_sha256"):
        return False
    h=hashlib.sha256()
    with p.open("rb") as fh:
        for b in iter(lambda:fh.read(16*1024*1024),b""): h.update(b)
    return h.hexdigest()==x.get("output_sha256")

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

    # Forecasting target must be strict date-PIT. The historical 533,387-row
    # runner-LVS authority is formula/parity evidence only because its legacy
    # standard-time benchmark construction used all-history observations.
    print("TARGET_SOURCE=STRICT_PIT_WAREHOUSE_RECONSTRUCTION")
    if target_checkpoint_valid():
        print("RESUME_CHECKPOINT=LAB245B_STRICT_PIT_TARGET_VALID; SKIP_REBUILD=YES")
    else:
        run("scripts/research/build_lab245b_warehouse_runner_lvs.py")
    if AUTHORITY.exists():
        if not authority_valid():
            raise RuntimeError("Runner-LVS parity authority exists but fails immutable size/SHA verification.")
        print("PARITY_AUTHORITY=VERIFIED_IMMUTABLE; FORECAST_TARGET_USE=NO")
        run("scripts/research/run_lab245b_target_parity_audit.py")
    else:
        print("PARITY_AUTHORITY=ABSENT; PARITY_AUDIT=SKIPPED")
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
