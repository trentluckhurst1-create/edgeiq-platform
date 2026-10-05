from pathlib import Path
import json
import os
import hashlib
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
DATA_ROOT=Path(os.environ.get("EDGEIQ_DATA_ROOT",str(ROOT))).resolve()
OUT=ROOT/"outputs/research/profitability_program/lab245b"
PY=sys.executable
EXPECTED_WAREHOUSE_SHA="bcdcef1c7cb9144feae5783ca2fa83b1dc2b8dc07a42ac31c31fd7bd12b53107"
EXPECTED_TARGET_CONTRACT="LAB245B_STRICT_PIT_LVS_V12_QUARANTINE_LINEAGE_COMPLETE_V1_LENGTH_CONVERSION_TRACK_DISTANCE_CONDITION_MIN20"
EXPECTED_AUTHORITY_SHA="b08bb7a334ddba2f6a76942452dd964cd59db05001dc5710ff19aa7fc6e12926"
EXPECTED_AUTHORITY_BYTES=80343742
AUTHORITY=DATA_ROOT/"docs/performance-intelligence/lengths-v-standard/edgeiq_runner_lengths_v_standard_fact_v1.csv"
WAREHOUSE=DATA_ROOT/"docs/performance-intelligence/warehouse/edgeiq_performance_fact_warehouse_v1.csv"

def run(script):
    print(f"\\n=== RUN {script} ===",flush=True)
    env=os.environ.copy()
    subprocess.run([PY,str(ROOT/script)],cwd=ROOT,env=env,check=True)

def authority_valid():
    if not AUTHORITY.exists() or AUTHORITY.stat().st_size!=EXPECTED_AUTHORITY_BYTES:
        return False
    h=hashlib.sha256()
    with AUTHORITY.open("rb") as fh:
        for b in iter(lambda:fh.read(16*1024*1024),b""): h.update(b)
    return h.hexdigest()==EXPECTED_AUTHORITY_SHA

def target_checkpoint_valid():
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

def write_status(stage,status,detail=None):
    p=OUT/"LAB245B_CHAIN_STATUS.json"
    payload={"stage":stage,"status":status,"holdout_2025_2026_opened":False}
    if detail is not None: payload["detail"]=detail
    p.write_text(json.dumps(payload,indent=2),encoding="utf-8")

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    write_status("PREFLIGHT","STARTED")
    print("LAB245B PREHOLDOUT GOVERNED CHAIN")
    print(f"EDGEIQ_DATA_ROOT={os.environ.get('EDGEIQ_DATA_ROOT',str(ROOT))}")
    print("HOLDOUT_POLICY=2025_2026_CANNOT_BE_OPENED_BY_THIS_LAUNCHER")
    run("scripts/research/run_lab245b_preflight.py")
    write_status("PREFLIGHT","PASS")

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
    compact=OUT/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
    compact_meta=OUT/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.manifest.json"
    compact_ok=False
    if compact.exists() and compact_meta.exists():
        try:
            cm=json.loads(compact_meta.read_text(encoding="utf-8"))
            tm=json.loads((OUT/"LAB245B_WAREHOUSE_RUNNER_LVS.manifest.json").read_text(encoding="utf-8"))
            compact_ok=(cm.get("source_contract_version")==EXPECTED_TARGET_CONTRACT and cm.get("source_sha256")==tm.get("output_sha256") and cm.get("pit_policy")=="HORSE_HISTORY_DATE_LT_TARGET_DATE")
            if compact_ok:
                ch=hashlib.sha256()
                with compact.open("rb") as fh:
                    for b in iter(lambda:fh.read(8*1024*1024),b""): ch.update(b)
                compact_ok=(cm.get("output_sha256")==ch.hexdigest() and cm.get("output_bytes")==compact.stat().st_size)
        except Exception:
            compact_ok=False
    write_status("TARGET_AND_PARITY","PASS")
    if compact_ok:
        print("RESUME_CHECKPOINT=LAB245B_COMPACT_PIT_HISTORY_VALID; SKIP_REBUILD=YES")
    else:
        run("scripts/research/build_lab245b_compact_performance_bridge.py")

    a1p=OUT/"LAB245B1_AUDIT.json"
    if a1p.exists():
        a1=audit("LAB245B1_AUDIT.json")
        tm=audit("LAB245B_WAREHOUSE_RUNNER_LVS.manifest.json")
        stale=not (a1.get("target_contract_version")==EXPECTED_TARGET_CONTRACT and a1.get("target_output_sha256")==tm.get("output_sha256"))
        if stale:
            print("RESUME_CHECKPOINT=B1_STALE_LINEAGE; RERUN=YES")
            run("scripts/research/run_lab245b1_next_performance_forecast.py")
            a1=audit("LAB245B1_AUDIT.json")
        else:
            print(f"RESUME_CHECKPOINT=B1_VALID_LINEAGE AUDIT_STATUS={a1.get('status')}")
    else:
        run("scripts/research/run_lab245b1_next_performance_forecast.py")
        a1=audit("LAB245B1_AUDIT.json")
    write_status("B1",a1.get("status"))
    if a1.get("status")!="SURVIVE_TO_LAB245B2":
        print(f"CHAIN_STOP=B1 SCIENTIFIC_STATUS={a1.get('status')}")
        return

    a2p=OUT/"LAB245B2_AUDIT.json"
    a2=None
    if a2p.exists():
        old=audit("LAB245B2_AUDIT.json")
        if old.get("b1_oof_predictions_sha256")==a1.get("oof_predictions_sha256"):
            a2=old
            print(f"RESUME_CHECKPOINT=B2_VALID_LINEAGE AUDIT_STATUS={a2.get('status')}")
        else:
            print("RESUME_CHECKPOINT=B2_STALE_LINEAGE; RERUN=YES")
    if a2 is None:
        run("scripts/research/run_lab245b2_probability_challenger.py")
        a2=audit("LAB245B2_AUDIT.json")
    write_status("B2",a2.get("status"))
    if a2.get("status")!="SURVIVE_TO_LAB245B3":
        print(f"CHAIN_STOP=B2 SCIENTIFIC_STATUS={a2.get('status')}")
        return

    a3p=OUT/"LAB245B3_AUDIT.json"
    a3=None
    if a3p.exists():
        old=audit("LAB245B3_AUDIT.json")
        if old.get("b2_oof_probabilities_sha256")==a2.get("oof_probabilities_sha256"):
            a3=old
            print(f"RESUME_CHECKPOINT=B3_VALID_LINEAGE AUDIT_STATUS={a3.get('status')}")
        else:
            print("RESUME_CHECKPOINT=B3_STALE_LINEAGE; RERUN=YES")
    if a3 is None:
        run("scripts/research/run_lab245b3_selective_betting_forensics.py")
        a3=audit("LAB245B3_AUDIT.json")
    write_status("B3_PREHOLDOUT_COMPLETE",a3.get("status"))
    print(f"CHAIN_STOP=PREHOLDOUT_COMPLETE B3_STATUS={a3.get('status')}")
    print("2025_2026_HOLDOUT_REMAINS_SEALED=YES")

if __name__=="__main__":
    main()
