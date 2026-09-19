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
    wh=eligible=0
    with WH.open(encoding="utf-8-sig",errors="replace",newline="") as f:
        for r in csv.DictReader(f):
            wh+=1
            pid=clean(r.get("canonical_performance_id"))
            if pid not in epi: continue
            eligible+=1
            sk=clean(r.get("source_record_key")).split("|")
            h=horse(sk[-1] if sk else "")
            dt=date(r.get("race_date")); tr=track(r.get("track")); d=dist(r.get("distance_metres"))
            if not h: continue
            rec=(pid,epi[pid],dt,tr,d,clean(r.get("track")),clean(r.get("distance_metres")))
            if dt and tr and d: idx[(h,dt,tr,d)].append(rec)
            if dt and d: by_hdd[(h,dt,d)].append(rec)
            if dt and tr: by_hdt[(h,dt,tr)].append(rec)
            if tr and d: by_htd[(h,tr,d)].append(rec)
            if dt: by_hd[(h,dt)].append(rec)
            by_h[h].append(rec)

    payload=json.loads(FORM.read_text(encoding="utf-8",errors="replace"))
    c=Counter(); unmatched=[]; conflicts=[]
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
                        reason="HORSE_NOT_PRESENT_CERTIFIED_EPI"
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

    DETAIL.parent.mkdir(parents=True,exist_ok=True)
    fields=["reason","runner","run_index","form_date","form_track","form_track_key","form_distance","candidate_count","candidate_sample"]
    with DETAIL.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(unmatched)

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
            "HORSE_NOT_PRESENT_CERTIFIED_EPI":c["HORSE_NOT_PRESENT_CERTIFIED_EPI"],
        },
        "unmatched_detail":str(DETAIL.relative_to(ROOT)),
        "conflict_examples":conflicts[:25],
        "production_changed":False,
    }
    OUT.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))
    print("EDGEIQ_ALL_RUNNER_EPI_PRODUCT_BRIDGE_AUDIT_V1_PASS")

if __name__=="__main__": main()
