"""Stage045: synthetic-only scoring artifact writer contract test. No model or historical data."""
import csv
import hashlib
import json
import math
import re
import tempfile
from pathlib import Path

FIELDS = ["_race","_horse","race_date","year","y","p","model_id","git_sha","random_state","train_year_lt","feature_names_sha256","input_file_sha256","n_train_rows","n_test_rows"]
FORBIDDEN = {"sp","odds","market_rank","epi"}
TOL = 1e-12

def validate(rows):
    if not rows:
        raise ValueError("empty_artifact")
    for r in rows:
        if FORBIDDEN.intersection({str(k).lower() for k in r}):
            raise ValueError("forbidden_column")
        if any(k not in r for k in FIELDS):
            raise ValueError("missing_required_field")
        if any(r[k] is None or (isinstance(r[k],str) and not r[k].strip()) for k in FIELDS):
            raise ValueError("null_or_blank_required_field")
        for k in ("feature_names_sha256","input_file_sha256"):
            if not re.fullmatch(r"[0-9a-fA-F]{64}",str(r[k])):
                raise ValueError("invalid_sha256_"+k)
        if not math.isfinite(float(r["p"])):
            raise ValueError("nonfinite_probability")
        if not 0 <= float(r["p"]) <= 1:
            raise ValueError("probability_out_of_range")
        if int(r["year"]) >= 2025:
            raise ValueError("sealed_year")
        if int(r["y"]) not in (0,1):
            raise ValueError("invalid_outcome")
    keys=[(r["_race"],r["_horse"]) for r in rows]
    if len(set(keys))!=len(keys):
        raise ValueError("duplicate_runner_key")
    races={r["_race"] for r in rows}
    for race in races:
        group=[r for r in rows if r["_race"]==race]
        if sum(int(r["y"]) for r in group)!=1:
            raise ValueError("not_single_winner")
        if abs(sum(float(r["p"]) for r in group)-1)>TOL:
            raise ValueError("probability_mass")
    return True

def fixture():
    h1=hashlib.sha256(b"synthetic-feature-names").hexdigest()
    h2=hashlib.sha256(b"synthetic-input-file").hexdigest()
    return [dict(zip(FIELDS,["SYNTH_RACE_001",f"SYNTH_HORSE_{i}","2020-01-01",2020,int(i==0),[0.5,0.3,0.2][i],"NO_MODEL_SYNTHETIC","SYNTHETIC","NA",2020,h1,h2,0,3])) for i in range(3)]

def altered(mutator):
    rows=fixture()
    mutator(rows)
    return rows

def main():
    tests=[("compliant",fixture(),None)]
    cases=[
        ("mass_error",lambda r:r[0].update(p=0.5+2e-12),"probability_mass"),
        ("forbidden_sp",lambda r:r[0].update(sp="FORBIDDEN_SENTINEL"),"forbidden_column"),
        ("forbidden_epi",lambda r:r[0].update(epi="FORBIDDEN_SENTINEL"),"forbidden_column"),
        ("forbidden_odds",lambda r:r[0].update(odds="FORBIDDEN_SENTINEL"),"forbidden_column"),
        ("forbidden_market_rank",lambda r:r[0].update(market_rank="FORBIDDEN_SENTINEL"),"forbidden_column"),
        ("blank_feature_hash",lambda r:r[0].update(feature_names_sha256=""),"null_or_blank_required_field"),
        ("blank_input_hash",lambda r:r[0].update(input_file_sha256=""),"null_or_blank_required_field"),
        ("malformed_feature_hash",lambda r:r[0].update(feature_names_sha256="not-a-digest"),"invalid_sha256_feature_names_sha256"),
        ("malformed_input_hash",lambda r:r[0].update(input_file_sha256="0"*63),"invalid_sha256_input_file_sha256"),
        ("duplicate_key",lambda r:r[1].update(_horse=r[0]["_horse"]),"duplicate_runner_key"),
        ("zero_winners",lambda r:r[0].update(y=0),"not_single_winner"),
        ("two_winners",lambda r:r[1].update(y=1),"not_single_winner"),
        ("out_of_range_p",lambda r:r[0].update(p=1.1),"probability_out_of_range"),
        ("nonfinite_p",lambda r:r[0].update(p=float("nan")),"nonfinite_probability"),
        ("sealed_year",lambda r:r[0].update(year=2025),"sealed_year"),
        ("missing_field",lambda r:r[0].pop("model_id"),"missing_required_field"),
        ("null_field",lambda r:r[0].update(model_id=None),"null_or_blank_required_field"),
    ]
    tests.extend((name,altered(mutator),expected) for name,mutator,expected in cases)
    results=[]
    with tempfile.TemporaryDirectory(prefix="edgeiq_stage045_synthetic_") as td:
        good=fixture()
        assert len(good)==3 and len({r["_race"] for r in good})==1
        file=Path(td)/"synthetic_scored_artifact.csv"
        with file.open("w",newline="",encoding="utf-8") as fh:
            w=csv.DictWriter(fh,fieldnames=FIELDS)
            w.writeheader()
            w.writerows(good)
        with file.open(newline="",encoding="utf-8") as fh:
            saved=list(csv.DictReader(fh))
        assert validate(saved)
        for name,rows,expected in tests:
            observed=None
            try:validate(rows)
            except Exception as e:observed=str(e)
            ok=(observed is None) if expected is None else observed==expected
            results.append({"test":name,"pass":ok,"expected":expected or "ACCEPT","observed":observed or "ACCEPT"})
    report={"contract":"V2_STAGE045_SYNTHETIC_ONLY","model_fit":False,"real_data_access":False,"temporary_artifact_retained":False,"tests":results,"pass":all(t["pass"] for t in results)}
    print("V2_STAGE045_REPORT_JSON",json.dumps(report,sort_keys=True,allow_nan=False))
    print("V2_STAGE045_DECISION","PASS" if report["pass"] else "FAIL")
    if not report["pass"]:
        raise SystemExit(1)

if __name__=="__main__":
    main()
