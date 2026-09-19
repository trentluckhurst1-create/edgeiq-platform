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
    DATA/"edgeiq_form_guide_enriched_v1.json",
]
FORM=next((p for p in FORM_CANDIDATES if p.exists()),FORM_CANDIDATES[0])
OUT=WORK/"edgeiq_all_runner_epi_product_bridge_v1_audit.json"
ALIASES={"FLEMINGTON":"FLEM","CAULFIELD":"CAUL","CAULFIELDHEATH":"CAUH","SANDOWN":"SANL","SPORTSBETSANDOWNLAKESIDE":"SANL","SANDOWNLAKESIDE":"SANL","SPORTSBETSANDOWNHILLSIDE":"SANH","SANDOWNHILLSIDE":"SANH","PAKENHAM":"PAKM","SOUTHSIDEPAKENHAM":"PAKM","PAKENHAMSYNTHETIC":"PAKS","SPORTSBETPAKENHAMSYNTHETIC":"PAKS","CRANBOURNE":"CRAN","SOUTHSIDECRANBOURNE":"CRAN","GEELONG":"GEEL","LADBROKESGEELONG":"GEEL","BALLARAT":"BRAT","SPORTSBETBALLARAT":"BRAT","BALLARATSYNTHETIC":"BALS","SPORTSBETBALLARATSYNTHETIC":"BALS","WARRNAMBOOL":"WNBL","WERRIBEE":"WERR","PICKLEBETPARKWERRIBEE":"WERR","MORNINGTON":"MORN","WANGARATTA":"WANG","SPORTSBETWANGARATTA":"WANG","KYNETON":"KYNE","BET365PARKKYNETON":"KYNE","ECHUCA":"ECHA","BET365ECHUCA":"ECHA","SEYMOUR":"SEYM","BET365SEYMOUR":"SEYM","HORSHAM":"HSHM","TERANG":"TER","BET365TERANG":"TER","COLAC":"CLAC","BET365COLAC":"CLAC","DONALD":"DON","TATURA":"TAT","ARARAT":"ARAT","BENDIGO":"BDGO","SALE":"SALE","MOE":"MOE","BENALLA":"BEN","HAMILTON":"HAM","SWANHILL":"SWAN","MILDURA":"MILD","STAWELL":"STAW","CASTERTON":"CAST"}
def clean(v): return "" if v is None else str(v).strip()
def norm(v): return re.sub(r"[^A-Z0-9]+","",clean(v).upper())
def track(v):
    k=norm(v)
    return ALIASES.get(k,k)
def dist(v):
    m=re.search(r"\d+",clean(v)); return m.group(0) if m else ""
def main():
    for p in (EPI,WH):
        if not p.exists(): raise SystemExit(f"FAIL_CLOSED_MISSING={p}")
    if not FORM.exists():
        available=[str(p.relative_to(ROOT)) for p in FORM_CANDIDATES if p.exists()]
        raise SystemExit("FAIL_CLOSED_MISSING_FORM_GUIDE candidates="+json.dumps([str(p.relative_to(ROOT)) for p in FORM_CANDIDATES])+" available="+json.dumps(available))
    epi={}
    with EPI.open(encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f): epi[clean(r["canonical_performance_id"])]=clean(r["epi_value"])
    idx=defaultdict(list); wh=0; eligible=0
    with WH.open(encoding="utf-8-sig",errors="replace",newline="") as f:
        for r in csv.DictReader(f):
            wh+=1; pid=clean(r.get("canonical_performance_id"))
            if pid not in epi: continue
            eligible+=1
            sk=clean(r.get("source_record_key")).split("|")
            horse=norm(sk[-1] if sk else "")
            date=clean(r.get("race_date")); tr=track(r.get("track")); d=dist(r.get("distance_metres"))
            if horse and date and tr and d: idx[(horse,date,tr,d)].append((pid,epi[pid]))
    payload=json.loads(FORM.read_text(encoding="utf-8",errors="replace"))
    c=Counter(); examples=[]
    for race in payload.get("races",[]) or []:
        for runner in race.get("runners",[]) or []:
            horse=norm(runner.get("runnerName"))
            for run in runner.get("fullForm",[]) or []:
                c["form_runs"]+=1
                k=(horse,clean(run.get("date")),track(run.get("track")),dist(run.get("distance")))
                hits=idx.get(k,[])
                if not hits: c["no_match"]+=1
                elif len(hits)==1: c["unique_match"]+=1
                else:
                    vals=sorted({x[1] for x in hits})
                    if len(vals)==1:c["same_epi_duplicates"]+=1
                    else:c["conflicting_epi"]+=1
                    if len(examples)<50:examples.append({"key":k,"hits":hits[:10]})
    result={"status":"PASS_READ_ONLY","warehouse_rows":wh,"certified_epi_rows":len(epi),"warehouse_epi_rows_indexed":eligible,"form_source":str(FORM.relative_to(ROOT)),"form_runs":c["form_runs"],"unique_match":c["unique_match"],"same_epi_duplicates":c["same_epi_duplicates"],"conflicting_epi":c["conflicting_epi"],"no_match":c["no_match"],"examples":examples,"production_changed":False}
    OUT.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))
    print("EDGEIQ_ALL_RUNNER_EPI_PRODUCT_BRIDGE_AUDIT_V1_PASS")
if __name__=="__main__":main()
