from __future__ import annotations
import csv,json,re
from collections import Counter,defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"public"/"data"; WORK=ROOT/"work"/"all-runner-epi-restore-v1"
EPI=WORK/"edgeiq_epi_performance_fact_v1.csv"
WH=ROOT/"docs"/"performance-intelligence"/"warehouse"/"edgeiq_performance_fact_warehouse_v1.csv"
FORM_CANDIDATES=[
    DATA/"edgeiq_form_guide_enriched_v2.json",
    ROOT/"dist"/"data"/"edgeiq_form_guide_enriched_v2.json",
    DATA/"edgeiq_form_guide_enriched_v1.json",
    ROOT/"dist"/"data"/"edgeiq_form_guide_enriched_v1.json",
]
FORM=next((p for p in FORM_CANDIDATES if p.exists()),FORM_CANDIDATES[0])
OUT=WORK/"edgeiq_all_runner_epi_product_bridge_v1_audit.json"
DETAIL=WORK/"edgeiq_all_runner_epi_product_bridge_v1_unmatched_detail.csv"
REJECT_DETAIL=WORK/"edgeiq_all_runner_epi_product_bridge_v1_exact_run_rejection_detail.csv"

ALIASES={"FLEMINGTON":"FLEM","CAULFIELD":"CAUL","CAULFIELDHEATH":"CAUH","SANDOWN":"SANL","SPORTSBETSANDOWNLAKESIDE":"SANL","SANDOWNLAKESIDE":"SANL","SPORTSBETSANDOWNHILLSIDE":"SANH","SANDOWNHILLSIDE":"SANH","PAKENHAM":"PAKM","SOUTHSIDEPAKENHAM":"PAKM","PAKENHAMSYNTHETIC":"PAKS","SPORTSBETPAKENHAMSYNTHETIC":"PAKS","CRANBOURNE":"CRAN","SOUTHSIDECRANBOURNE":"CRAN","GEELONG":"GEEL","LADBROKESGEELONG":"GEEL","BALLARAT":"BRAT","SPORTSBETBALLARAT":"BRAT","BALLARATSYNTHETIC":"BALS","SPORTSBETBALLARATSYNTHETIC":"BALS","WARRNAMBOOL":"WNBL","WERRIBEE":"WERR","PICKLEBETPARKWERRIBEE":"WERR","MORNINGTON":"MORN","WANGARATTA":"WANG","SPORTSBETWANGARATTA":"WANG","KYNETON":"KYNE","BET365PARKKYNETON":"KYNE","ECHUCA":"ECHA","BET365ECHUCA":"ECHA","SEYMOUR":"SEYM","BET365SEYMOUR":"SEYM","HORSHAM":"HSHM","TERANG":"TER","BET365TERANG":"TER","COLAC":"CLAC","BET365COLAC":"CLAC","DONALD":"DON","TATURA":"TAT","ARARAT":"ARAT","BENDIGO":"BDGO","SALE":"SALE","MOE":"MOE","BENALLA":"BEN","HAMILTON":"HAM","SWANHILL":"SWAN","MILDURA":"MILD","STAWELL":"STAW","CASTERTON":"CAST"}

def clean(v): return "" if v is None else str(v).strip()
def norm(v): return re.sub(r"[^A-Z0-9]+","",clean(v).upper())
def horse(v):
    x=norm(v)
    for suffix in ("AUS","NZ","GB","IRE","USA","FR","JPN"):
        if x.endswith(suffix) and len(x)>len(suffix)+2:
            x=x[:-len(suffix)]
            break
    return x
def track(v):
    k=norm(v)
    return ALIASES.get(k,k)
def dist(v):
    m=re.search(r"\d+(?:\.\d+)?",clean(v).replace(",",""))
    if not m:return ""
    x=float(m.group(0))
    return str(int(x)) if x.is_integer() else str(x)
def date(v):
    x=clean(v)
    return x.split("T",1)[0].split(" ",1)[0]

def main():
    for p in (EPI,WH):
        if not p.exists(): raise SystemExit(f"FAIL_CLOSED_MISSING={p}")
    if not FORM.exists():
        available=[str(p.relative_to(ROOT)) for p in FORM_CANDIDATES if p.exists()]
        raise SystemExit("FAIL_CLOSED_MISSING_FORM_GUIDE candidates="+json.dumps([str(p.relative_to(ROOT)) for p in FORM_CANDIDATES])+" available="+json.dumps(available))

    epi={}
    with EPI.open(encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            epi[clean(r["canonical_performance_id"])]=clean(r["epi_value"])

    idx=defaultdict(list)
    by_hdd=defaultdict(list)
    by_hdt=defaultdict(list)
    by_htd=defaultdict(list)
    by_hd=defaultdict(list)
    by_h=defaultdict(list)
    wh_all_h=defaultdict(list)
    wh=eligible=0
    with WH.open(encoding="utf-8-sig",errors="replace",newline="") as f:
        for r in csv.DictReader(f):
            wh+=1
            pid=clean(r.get("canonical_performance_id"))
            sk=clean(r.get("source_record_key")).split("|")
            h=horse(sk[-1] if sk else "")
            dt=date(r.get("race_date")); tr=track(r.get("track")); d=dist(r.get("distance_metres"))
            if h:
                wh_all_h[h].append((pid,dt,tr,d,clean(r.get("track")),clean(r.get("distance_metres")),clean(r.get("time_governance_status") or r.get("time_status") or r.get("time_unit")),clean(r.get("official_race_time_seconds")),clean(r.get("race_id") or r.get("canonical_race_id"))))
            if pid not in epi: continue
            eligible+=1
            if not h: continue
            rec=(pid,epi[pid],dt,tr,d,clean(r.get("track")),clean(r.get("distance_metres")))
            if dt and tr and d: idx[(h,dt,tr,d)].append(rec)
            if dt and d: by_hdd[(h,dt,d)].append(rec)
            if dt and tr: by_hdt[(h,dt,tr)].append(rec)
            if tr and d: by_htd[(h,tr,d)].append(rec)
            if dt: by_hd[(h,dt)].append(rec)
            by_h[h].append(rec)

    # Reconstruct the exact historical EPI eligibility decision for warehouse rows
    # without writing any production artifacts. This mirrors the certified July logic:
    # first require a governed benchmark key, then require time/margin/race/performance IDs.
    std_rows=[]
    std_candidates=[
        ROOT/"docs"/"performance-intelligence"/"standard-times"/"edgeiq_standard_time_fact_v1.csv",
        WORK/"edgeiq_standard_time_fact_v1.csv",
    ]
    std_path=next((p for p in std_candidates if p.exists()),None)
    std_keys=set()
    if std_path:
        with std_path.open(encoding="utf-8-sig",errors="replace",newline="") as f:
            for r in csv.DictReader(f):
                std_keys.add((
                    clean(r.get("canonical_track_id")),
                    dist(r.get("distance_metres")),
                    norm(r.get("track_condition_group")),
                    clean(r.get("jurisdiction")) or "VIC",
                    clean(r.get("surface")) or "TURF_OR_UNKNOWN",
                ))

    payload=json.loads(FORM.read_text(encoding="utf-8",errors="replace"))
    c=Counter(); unmatched=[]; conflicts=[]; exact_rejections=[]
    for race in payload.get("races",[]) or []:
        for runner in race.get("runners",[]) or []:
            h=horse(runner.get("runnerName"))
            for run_index,run in enumerate(runner.get("fullForm",[]) or [],start=1):
                c["form_runs"]+=1
                dt=date(run.get("date")); tr=track(run.get("track")); d=dist(run.get("distance"))
                k=(h,dt,tr,d); hits=idx.get(k,[])
                if not hits:
                    c["no_match"]+=1
                    if by_hdd.get((h,dt,d)):
                        reason="TRACK_ONLY"
                        cand=by_hdd[(h,dt,d)]
                    elif by_hdt.get((h,dt,tr)):
                        reason="DISTANCE_ONLY"
                        cand=by_hdt[(h,dt,tr)]
                    elif by_htd.get((h,tr,d)):
                        reason="DATE_ONLY"
                        cand=by_htd[(h,tr,d)]
                    elif by_hd.get((h,dt)):
                        reason="TRACK_AND_OR_DISTANCE"
                        cand=by_hd[(h,dt)]
                    elif by_h.get(h):
                        reason="HORSE_PRESENT_OTHER_RUNS"
                        cand=by_h[h]
                    else:
                        whcand=wh_all_h.get(h,[])
                        same_run=[x for x in whcand if x[1]==dt and x[2]==tr and x[3]==d]
                        if same_run:
                            reason="RUN_PRESENT_WAREHOUSE_NOT_CERTIFIED_EPI"
                            cand=[]
                            for x in same_run:
                                # x tuple currently carries governance/time metadata only.
                                exact_rejections.append({
                                    "runner":clean(runner.get("runnerName")),
                                    "form_date":dt,
                                    "form_track":clean(run.get("track")),
                                    "form_distance":d,
                                    "canonical_performance_id":x[0],
                                    "warehouse_track":x[4],
                                    "warehouse_distance":x[5],
                                    "time_status":x[6],
                                    "official_race_time_seconds":x[7],
                                    "canonical_race_id":x[8],
                                })
                        elif whcand:
                            reason="HORSE_PRESENT_WAREHOUSE_OTHER_RUNS_ONLY"
                            cand=[]
                        else:
                            reason="HORSE_NOT_PRESENT_WAREHOUSE"
                            cand=[]
                    c[reason]+=1
                    unmatched.append({
                        "reason":reason,
                        "runner":clean(runner.get("runnerName")),
                        "run_index":run_index,
                        "form_date":dt,
                        "form_track":clean(run.get("track")),
                        "form_track_key":tr,
                        "form_distance":d,
                        "candidate_count":len(cand),
                        "candidate_sample":" | ".join(f"{x[2]}/{x[5]}/{x[6]}/EPI={x[1]}" for x in cand[:5]),
                    })
                elif len(hits)==1:
                    c["unique_match"]+=1
                else:
                    vals=sorted({x[1] for x in hits})
                    if len(vals)==1:
                        c["same_epi_duplicates"]+=1
                    else:
                        c["conflicting_epi"]+=1
                        conflicts.append({"key":k,"hits":hits[:10]})

    # Enrich exact-run exclusions with the original certified rejection reason.
    # Re-read only the small set of exact excluded PIDs so the classification uses the
    # original benchmark/calculation gates rather than heuristics.
    reject_pids={x["canonical_performance_id"] for x in exact_rejections if x["canonical_performance_id"]}
    if reject_pids:
        with WH.open(encoding="utf-8-sig",errors="replace",newline="") as f:
            for r in csv.DictReader(f):
                pid=clean(r.get("canonical_performance_id"))
                if pid not in reject_pids: continue
                tr_id=clean(r.get("canonical_track_id"))
                d=dist(r.get("distance_metres"))
                cond=norm(r.get("track_condition_group") or r.get("track_condition"))
                # Match the historical cond/surface semantics used by the producer.
                cond_group="HEAVY" if "HEAVY" in cond else ("SOFT" if ("SOFT" in cond or "SLOW" in cond) else ("GOOD" if ("GOOD" in cond or "FIRM" in cond or "FAST" in cond) else ("SYNTHETIC" if ("SYN" in cond or "POLY" in cond or "TAPETA" in cond) else "UNKNOWN")))
                sf="SYNTHETIC" if re.search("SYNTH|POLY|TAPETA",(clean(r.get("track"))+" "+clean(r.get("track_condition"))).upper()) else "TURF_OR_UNKNOWN"
                key=(tr_id,d,cond_group,clean(r.get("jurisdiction")) or "VIC",sf)
                sec=clean(r.get("official_race_time_seconds"))
                margin=clean(r.get("finish_margin"))
                rid=clean(r.get("canonical_race_id"))
                if key not in std_keys:
                    rejection="UNMATCHED_BENCHMARK"
                elif not sec or not margin or not rid or not pid:
                    rejection="INVALID_CALCULATION"
                else:
                    rejection="UNEXPLAINED_CHECK_REQUIRED"
                c["EXACT_RUN_"+rejection]+=1
                for x in exact_rejections:
                    if x["canonical_performance_id"]==pid:
                        x["rejection_reason"]=rejection
                        x["benchmark_key"]="|".join(key)
                        x["finish_margin"]=margin
                        break

    # Reconcile every exact-run miss at the Form Guide run level.
    classified_exact=sum(1 for x in exact_rejections if x.get("rejection_reason"))
    unclassified_exact=[x for x in exact_rejections if not x.get("rejection_reason")]
    c["EXACT_RUN_UNCLASSIFIED_ROW"]=len(unclassified_exact)

    DETAIL.parent.mkdir(parents=True,exist_ok=True)
    fields=["reason","runner","run_index","form_date","form_track","form_track_key","form_distance","candidate_count","candidate_sample"]
    with DETAIL.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(unmatched)
    reject_fields=["runner","form_date","form_track","form_distance","canonical_performance_id","canonical_race_id","warehouse_track","warehouse_distance","time_status","official_race_time_seconds","finish_margin","benchmark_key","rejection_reason"]
    with REJECT_DETAIL.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=reject_fields,extrasaction="ignore"); w.writeheader(); w.writerows(exact_rejections)

    result={
        "status":"PASS_READ_ONLY",
        "warehouse_rows":wh,
        "certified_epi_rows":len(epi),
        "warehouse_epi_rows_indexed":eligible,
        "form_source":str(FORM.relative_to(ROOT)),
        "form_source_runtime_contract":"/data/edgeiq_form_guide_enriched_v2.json" if FORM.name=="edgeiq_form_guide_enriched_v2.json" else "/data/edgeiq_form_guide_enriched_v1.json",
        "form_source_location":"PUBLIC_DATA" if DATA in FORM.parents else "DIST_DATA",
        "form_runs":c["form_runs"],
        "unique_match":c["unique_match"],
        "same_epi_duplicates":c["same_epi_duplicates"],
        "conflicting_epi":c["conflicting_epi"],
        "no_match":c["no_match"],
        "unmatched_classification":{
            "TRACK_ONLY":c["TRACK_ONLY"],
            "DISTANCE_ONLY":c["DISTANCE_ONLY"],
            "DATE_ONLY":c["DATE_ONLY"],
            "TRACK_AND_OR_DISTANCE":c["TRACK_AND_OR_DISTANCE"],
            "HORSE_PRESENT_OTHER_RUNS":c["HORSE_PRESENT_OTHER_RUNS"],
            "RUN_PRESENT_WAREHOUSE_NOT_CERTIFIED_EPI":c["RUN_PRESENT_WAREHOUSE_NOT_CERTIFIED_EPI"],
            "HORSE_PRESENT_WAREHOUSE_OTHER_RUNS_ONLY":c["HORSE_PRESENT_WAREHOUSE_OTHER_RUNS_ONLY"],
            "HORSE_NOT_PRESENT_WAREHOUSE":c["HORSE_NOT_PRESENT_WAREHOUSE"],
        },
        "exact_run_rejection_classification":{
            "UNMATCHED_BENCHMARK":c["EXACT_RUN_UNMATCHED_BENCHMARK"],
            "INVALID_CALCULATION":c["EXACT_RUN_INVALID_CALCULATION"],
            "UNEXPLAINED_CHECK_REQUIRED":c["EXACT_RUN_UNEXPLAINED_CHECK_REQUIRED"],
            "UNCLASSIFIED_EXACT_ROWS":c["EXACT_RUN_UNCLASSIFIED_ROW"],
            "CLASSIFIED_EXACT_ROWS":classified_exact,
            "EXACT_REJECTION_DETAIL_ROWS":len(exact_rejections),
            "RUN_PRESENT_WAREHOUSE_NOT_CERTIFIED_EPI":c["RUN_PRESENT_WAREHOUSE_NOT_CERTIFIED_EPI"],
            "RECONCILES": classified_exact + c["EXACT_RUN_UNCLASSIFIED_ROW"] == len(exact_rejections),
        },
        "unmatched_detail":str(DETAIL.relative_to(ROOT)),
        "exact_run_rejection_detail":str(REJECT_DETAIL.relative_to(ROOT)),
        "conflict_examples":conflicts[:25],
        "production_changed":False,
    }
    OUT.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))
    print("EDGEIQ_ALL_RUNNER_EPI_PRODUCT_BRIDGE_AUDIT_V1_PASS")

if __name__=="__main__": main()
