from __future__ import annotations
import csv, json, math, hashlib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
WH=ROOT/"docs/performance-intelligence/warehouse/edgeiq_performance_fact_warehouse_v1.csv"
STD_CANDIDATES=[
    ROOT/"docs/performance-intelligence/standard-times/edgeiq_standard_time_fact_v1.csv",
    ROOT/"public/data/edgeiq_standard_time_fact_v1.csv",
]
STD=next((p for p in STD_CANDIDATES if p.exists()),STD_CANDIDATES[0])
OUT=ROOT/"work/all-runner-epi-restore-v1"
RUNNER=OUT/"edgeiq_runner_lengths_v_standard_fact_v1.csv"
EPI=OUT/"edgeiq_epi_performance_fact_v1.csv"
RACE=OUT/"edgeiq_race_lengths_v_standard_fact_v1.csv"
ERI=OUT/"edgeiq_epi_race_strength_fact_v1.csv"
AUDIT=OUT/"edgeiq_all_runner_epi_restore_v1_audit.json"

EXPECTED={"warehouse_rows":879784,"standard_rows":586,"runner_rows":533387,"race_rows":51769,
          "epi_rows":533387,"eri_rows":51769,"unmatched_benchmark":232783,"invalid_calculation":113614}
ALIASES={"PICKLEBETPARKWERRIBEE":"WERRIBEE","WERRIBEE":"WERRIBEE","SPORTSBETPAKENHAMSYNTHETIC":"PAKENHAMSYNTHETIC","SOUTHSIDEPAKENHAMSYNTHETIC":"PAKENHAMSYNTHETIC","PAKENHAMSYNTHETIC":"PAKENHAMSYNTHETIC","SOUTHSIDEPAKENHAM":"PAKENHAM","TYNONG":"PAKENHAM","PAKENHAM":"PAKENHAM","TYNONGSYNTHETIC":"PAKENHAMSYNTHETIC","SOUTHSIDECRANBOURNE":"CRANBOURNE","CRANBOURNE":"CRANBOURNE","SPORTSBETSANDOWNLAKESIDE":"SANDOWNLAKESIDE","SANDOWNLAKESIDE":"SANDOWNLAKESIDE","SPORTSBETSANDOWNHILLSIDE":"SANDOWNHILLSIDE","SANDOWNHILLSIDE":"SANDOWNHILLSIDE","LADBROKESGEELONG":"GEELONG","GEELONG":"GEELONG","SPORTSBETBALLARAT":"BALLARAT","BALLARAT":"BALLARAT","SPORTSBETBALLARATSYNTHETIC":"BALLARATSYNTHETIC","BALLARATSYNTHETIC":"BALLARATSYNTHETIC","BET365PARKKYNETON":"KYNETON","BET365ECHUCA":"ECHUCA","BET365SEYMOUR":"SEYMOUR","BET365TERANG":"TERANG","BET365COLAC":"COLAC"}

def t(v):
    s="" if v is None else str(v).strip()
    return "" if s.lower() in {"","none","null","nan","n/a","na","-","missing","unknown"} else s
def num(v):
    try:
        x=float(t(v).replace(",","").replace("kg","").replace("KG",""))
        return x if math.isfinite(x) else None
    except Exception:return None
def it(v):
    x=num(v)
    return str(int(x)) if x is not None and x.is_integer() else (str(x) if x is not None else "")
def cond(v):
    s=t(v).upper()
    if "HEAVY" in s:return "HEAVY"
    if "SOFT" in s or "SLOW" in s:return "SOFT"
    if "GOOD" in s or "FIRM" in s or "FAST" in s:return "GOOD"
    if "SYN" in s or "POLY" in s or "TAPETA" in s:return "SYNTHETIC"
    return "UNKNOWN"
def surf(track,condition):
    s=(t(track)+" "+t(condition)).upper()
    return "SYNTHETIC" if any(x in s for x in ("SYNTH","POLY","TAPETA")) else "TURF_OR_UNKNOWN"
def lps(condition,surface):return 6.0 if surface=="SYNTHETIC" or cond(condition) not in {"SOFT","HEAVY"} else 5.0
def fmt(x,p=4):return "" if x is None else f"{x:.{p}f}"
def band(x):return "ELITE" if x>=70 else "POSITIVE" if x>=55 else "NEUTRAL" if x>=45 else "RISK"
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):h.update(b)
    return h.hexdigest()

def main():
    if not WH.exists():
        raise SystemExit("FAIL_CLOSED_MISSING_WAREHOUSE")
    if not STD.exists():
        raise SystemExit("FAIL_CLOSED_MISSING_STANDARD_TIME")
    OUT.mkdir(parents=True,exist_ok=True)
    standards={}
    with STD.open("r",encoding="utf-8-sig",newline="") as f:
        sr=list(csv.DictReader(f))
    if len(sr)!=EXPECTED["standard_rows"]:raise SystemExit(f"FAIL_CLOSED_STANDARD_ROWS={len(sr)}")
    for r in sr:
        k=(t(r.get("canonical_track_id")),it(r.get("distance_metres")),cond(r.get("track_condition_group")),t(r.get("jurisdiction")) or "VIC",t(r.get("surface")) or "TURF_OR_UNKNOWN")
        if k in standards:raise SystemExit("FAIL_CLOSED_DUPLICATE_STANDARD_KEY")
        standards[k]=r

    rf="canonical_race_id standard_time_id official_race_time_seconds standard_time_seconds time_difference_seconds race_lengths_v_standard benchmark_observation_count calculation_status".split()
    lf="canonical_performance_id canonical_race_id canonical_horse_id finish_position finish_margin_lengths runner_time_equivalent_seconds runner_lengths_v_standard early_section_lengths_v_standard mid_section_lengths_v_standard late_section_lengths_v_standard calculation_status".split()
    ef=lf+"epi_value epi_band epi_methodology raw_lengths_v_standard weight_carried_kg reference_weight_kg weight_delta_kg weight_adjustment_lengths weight_adjusted_lengths_v_standard race_strength_adjustment circumstance_adjustment epi_performance_rating weight_adjustment_status weight_adjustment_methodology weight_adjustment_coefficient_provenance".split()
    erf="canonical_race_id standard_time_id eri_value race_strength_method".split()
    counts=Counter(); seen_races=set(); seen_pid=set()
    with WH.open("r",encoding="utf-8-sig",errors="replace",newline="") as src, RUNNER.open("w",encoding="utf-8",newline="") as lo, EPI.open("w",encoding="utf-8",newline="") as eo, RACE.open("w",encoding="utf-8",newline="") as ro, ERI.open("w",encoding="utf-8",newline="") as ero:
        lw=csv.DictWriter(lo,fieldnames=lf); ew=csv.DictWriter(eo,fieldnames=ef); rw=csv.DictWriter(ro,fieldnames=rf); erw=csv.DictWriter(ero,fieldnames=erf)
        for w in (lw,ew,rw,erw):w.writeheader()
        for row in csv.DictReader(src):
            counts["warehouse_rows"]+=1
            pid=t(row.get("canonical_performance_id")); rid=t(row.get("canonical_race_id"))
            sf=surf(row.get("track"),row.get("track_condition"))
            key=(t(row.get("canonical_track_id")),it(row.get("distance_metres")),cond(row.get("track_condition_group") or row.get("track_condition")),t(row.get("jurisdiction")) or "VIC",sf)
            st=standards.get(key)
            if not st:counts["unmatched_benchmark"]+=1;continue
            sec=num(row.get("official_race_time_seconds")); margin=num(row.get("finish_margin")); std=num(st.get("standard_time_seconds"))
            if sec is None or margin is None or std is None or not rid or not pid:
                counts["invalid_calculation"]+=1;continue
            if pid in seen_pid:raise SystemExit(f"FAIL_CLOSED_DUPLICATE_PERFORMANCE_ID={pid}")
            seen_pid.add(pid)
            lp=lps(row.get("track_condition"),sf); runner_time=sec+margin/lp; runner_lvs=(std-runner_time)*lp; race_lvs=(std-sec)*lp
            if rid not in seen_races:
                seen_races.add(rid); counts["race_rows"]+=1; counts["eri_rows"]+=1
                rw.writerow({"canonical_race_id":rid,"standard_time_id":st["standard_time_id"],"official_race_time_seconds":fmt(sec),"standard_time_seconds":fmt(std),"time_difference_seconds":fmt(sec-std),"race_lengths_v_standard":fmt(race_lvs),"benchmark_observation_count":st.get("observation_count",""),"calculation_status":"CALCULATED"})
                eri=max(0,min(100,50+race_lvs*2.0)); erw.writerow({"canonical_race_id":rid,"standard_time_id":st["standard_time_id"],"eri_value":fmt(eri),"race_strength_method":"RACE_LENGTHS_V_STANDARD_SCALED_V1_CENTISECONDS_REPAIRED"})
            base={"canonical_performance_id":pid,"canonical_race_id":rid,"canonical_horse_id":t(row.get("canonical_horse_id")),"finish_position":t(row.get("finish_position")),"finish_margin_lengths":fmt(margin),"runner_time_equivalent_seconds":fmt(runner_time),"runner_lengths_v_standard":fmt(runner_lvs),"early_section_lengths_v_standard":"","mid_section_lengths_v_standard":"","late_section_lengths_v_standard":"","calculation_status":"CALCULATED_NO_OFFICIAL_SECTIONAL"}
            lw.writerow(base)
            ev=max(0,min(100,50+runner_lvs*2.5)); ep=dict(base); ep.update({"epi_value":fmt(ev),"epi_band":band(ev),"epi_methodology":"LENGTHS_V_STANDARD_SCALED_V1_CENTISECONDS_REPAIRED","raw_lengths_v_standard":fmt(runner_lvs),"weight_carried_kg":fmt(num(row.get("weight_carried")),3),"reference_weight_kg":"","weight_delta_kg":"","weight_adjustment_lengths":"","weight_adjusted_lengths_v_standard":"","race_strength_adjustment":"","circumstance_adjustment":"","epi_performance_rating":fmt(ev),"weight_adjustment_status":"INSUFFICIENT_EMPIRICAL_EVIDENCE","weight_adjustment_methodology":"FAIL_CLOSED_NO_EMPIRICALLY_DERIVED_COEFFICIENT","weight_adjustment_coefficient_provenance":"NONE"})
            ew.writerow(ep); counts["runner_rows"]+=1; counts["epi_rows"]+=1

    got={k:counts[k] for k in EXPECTED}
    failures={k:{"expected":v,"actual":got[k]} for k,v in EXPECTED.items() if got[k]!=v}
    audit={"generated_at":datetime.now(timezone.utc).isoformat(),"status":"PASS" if not failures else "FAIL","mode":"SIDE_BY_SIDE_READ_SOURCE_ONLY_NO_PRODUCTION_PROMOTION","source":str(WH.relative_to(ROOT)),"standard_source":str(STD.relative_to(ROOT)),"expected":EXPECTED,"actual":got,"failures":failures,"outputs":{"runner_lvs":{"path":str(RUNNER.relative_to(ROOT)),"sha256":sha(RUNNER)},"epi":{"path":str(EPI.relative_to(ROOT)),"sha256":sha(EPI)},"race_lvs":{"path":str(RACE.relative_to(ROOT)),"sha256":sha(RACE)},"eri":{"path":str(ERI.relative_to(ROOT)),"sha256":sha(ERI)}},"production_changed":False,"hpr_chain_changed":False}
    AUDIT.write_text(json.dumps(audit,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(audit,indent=2))
    if failures:raise SystemExit(2)
    print("EDGEIQ_ALL_RUNNER_EPI_RESTORE_V1_PASS")

if __name__=="__main__":main()
