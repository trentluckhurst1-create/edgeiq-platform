from __future__ import annotations

import csv, hashlib, json, math, os, tempfile
from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "victoria-live-recovery-v6"
ROLLBACK = DOCS / "rollback"
TS = "2026-07-30T00:00:00Z"
POLICY = "HPR-NORM-A-v2"
BUILDER = "edgeiq_victoria_live_recovery_v6_historical_backfill.1.0.0"
CONTRACT = "1.0.0"
METHOD = "LINEAR_CENTRE_AND_SCALE"
STATUS_NORM = "NORMALISED_GOVERNED"
STATUS_RATING_BASE = "OBSERVED_NORMALISED_GOVERNED"
STATUS_OBS = "IDENTIFIED_GOVERNED"
STATUS_AGG = "HISTORICAL_AGGREGATE_GOVERNED"
STATUS_RATING = "HISTORICAL_HORSE_RATING_GOVERNED"
STATUS_SNAPSHOT = "POINT_IN_TIME_HISTORICAL_RATING_AVAILABLE"

BASE = DATA / "edgeiq_performance_intelligence_base_fact_v1.csv"
RESULTS = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
NORM_PARAM = DATA / "edgeiq_performance_normalisation_parameter_fact_v1.csv"
AGG_PARAM = DATA / "edgeiq_horse_performance_aggregation_parameter_fact_v1.csv"
RA_XWALK = ROOT / "docs" / "victoria-live-recovery-v4" / "EDGEIQ_CURRENT_HORSE_IDENTITY_CROSSWALK_REPORT.csv"
RACE_ENTRY = DATA / "edgeiq_race_entry_fact_v1.csv"
COMPONENT = DATA / "edgeiq_race_entry_epi_component_fact_v1.csv"
EPI = DATA / "edgeiq_race_entry_epi_fact_v1.csv"

OUT_NORM = DATA / "edgeiq_performance_normalisation_fact_v1.csv"
OUT_NORM_REJ = DATA / "edgeiq_performance_normalisation_fact_v1_rejections.csv"
OUT_RATING_BASE = DATA / "edgeiq_performance_rating_base_fact_v1.csv"
OUT_OBS = DATA / "edgeiq_horse_performance_observation_fact_v1.csv"
OUT_OBS_REJ = DATA / "edgeiq_horse_performance_observation_fact_v1_rejections.csv"
OUT_AGG = DATA / "edgeiq_horse_performance_aggregate_fact_v1.csv"
OUT_RATING = DATA / "edgeiq_horse_performance_rating_fact_v1.csv"
OUT_SNAPSHOT = DATA / "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv"

FIELDS_NORM = ["performance_normalisation_id","performance_intelligence_base_id","normalisation_parameter_id","lengths_versus_standard_id","benchmark_observation_id","race_key","race_date","track_name","official_distance_metres","winner_horse_name","raw_performance_lengths","centre_value","scale_value","normalised_performance_value","normalisation_method","normalisation_status","normalisation_model_version","source_performance_base_evidence_sha256","source_normalisation_parameter_evidence_sha256","performance_normalisation_evidence_sha256","builder_version","contract_version","built_at_utc"]
FIELDS_NORM_REJ = ["performance_intelligence_base_id","lengths_versus_standard_id","race_key","race_date","track_name","official_distance_metres","winner_horse_name","rejection_reason"]
FIELDS_RB = ["performance_rating_base_id","performance_normalisation_id","performance_intelligence_base_id","normalisation_parameter_id","lengths_versus_standard_id","benchmark_observation_id","race_key","race_date","track_name","official_distance_metres","winner_horse_name","raw_performance_lengths","normalised_performance_value","rating_base_value","rating_method","rating_status","normalisation_model_version","source_performance_normalisation_evidence_sha256","performance_rating_base_evidence_sha256","source_builder_version","builder_version","contract_version","built_at_utc"]
FIELDS_OBS = ["horse_performance_observation_id","canonical_horse_id","canonical_horse_name","source_horse_name","performance_rating_base_id","performance_normalisation_id","performance_intelligence_base_id","benchmark_observation_id","race_key","race_date","track_name","official_distance_metres","raw_performance_lengths","normalised_performance_value","rating_base_value","rating_status","identity_method","identity_status","identity_evidence_reference","source_identity_evidence_sha256","source_performance_rating_base_evidence_sha256","horse_performance_observation_evidence_sha256","builder_version","contract_version","built_at_utc"]
FIELDS_OBS_REJ = ["performance_rating_base_id","performance_normalisation_id","performance_intelligence_base_id","benchmark_observation_id","race_key","race_date","track_name","official_distance_metres","source_horse_name","rejection_reason","policy_version","built_at_utc"]
FIELDS_AGG = ["horse_performance_aggregate_id","canonical_horse_id","canonical_horse_name","aggregate_as_of_date","horse_performance_aggregation_parameter_id","aggregation_method","maximum_observations","lookback_days","minimum_observations","recency_weighting_method","recency_half_life_days","eligible_observation_count","included_observation_count","oldest_included_race_date","newest_included_race_date","total_weight","aggregate_rating_value","aggregate_status","aggregation_model_version","included_observation_ids_sha256","source_parameter_evidence_sha256","source_observation_evidence_sha256","horse_performance_aggregate_evidence_sha256","builder_version","contract_version","built_at_utc"]
FIELDS_RATING = ["horse_performance_rating_id","horse_performance_aggregate_id","canonical_horse_id","canonical_horse_name","rating_as_of_date","horse_performance_aggregation_parameter_id","aggregation_method","included_observation_count","aggregate_rating_value","horse_performance_rating_value","horse_performance_rating_method","horse_performance_rating_status","aggregation_model_version","source_horse_performance_aggregate_evidence_sha256","horse_performance_rating_evidence_sha256","source_builder_version","builder_version","contract_version","built_at_utc"]
FIELDS_SNAP = ["race_entry_horse_performance_snapshot_id","race_entry_id","race_id","race_date","runner_id","canonical_horse_id","canonical_horse_name","selected_horse_performance_rating_id","selected_rating_as_of_date","rating_age_days","eligible_historical_rating_count","first_eligible_rating_date","latest_eligible_rating_date","selected_horse_performance_rating_value","highest_eligible_historical_rating_value","lowest_eligible_historical_rating_value","average_eligible_historical_rating_value","selected_included_observation_count","horse_performance_rating_method","race_entry_horse_performance_snapshot_status","source_race_entry_evidence_sha256","source_selected_rating_evidence_sha256","source_eligible_rating_ids_sha256","source_eligible_rating_evidence_sha256","race_entry_horse_performance_snapshot_evidence_sha256","source_race_entry_builder_version","source_rating_builder_version","builder_version","contract_version","built_at_utc"]

def t(v): return str(v if v is not None else "").strip()
def ct(v): return "".join(ch for ch in t(v).upper() if ch.isalnum())
def nn(v): return " ".join(t(v).upper().split())
def num(v):
    x=t(v)
    if x.endswith(".0") and x[:-2].isdigit(): return x[:-2]
    return x
def sh(parts: Iterable[object]) -> str: return hashlib.sha256("\x1f".join(t(x) for x in parts).encode("utf-8")).hexdigest()
def fsha(p: Path) -> str:
    if not p.exists(): return "MISSING"
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for b in iter(lambda: fh.read(1024*1024), b""): h.update(b)
    return h.hexdigest()
def rd(p: Path):
    with p.open("r", encoding="utf-8-sig", newline="") as fh:
        r = csv.DictReader(fh); return list(r.fieldnames or []), list(r)
def stream(p: Path):
    with p.open("r", encoding="utf-8-sig", newline="") as fh:
        yield from csv.DictReader(fh)
def d(v, name="decimal", pos=False):
    raw = t(v)
    try: x = Decimal(raw)
    except InvalidOperation as e: raise RuntimeError(f"Invalid {name}: {raw!r}") from e
    if not x.is_finite(): raise RuntimeError(f"Non-finite {name}: {raw!r}")
    if pos and x <= 0: raise RuntimeError(f"Non-positive {name}: {raw!r}")
    return x
def fd(x: Decimal): return f"{x.quantize(Decimal('0.000001')):.6f}"
def dt(s): return date.fromisoformat(t(s))
def aw_csv(p: Path, rows, fields):
    p.parent.mkdir(parents=True, exist_ok=True)
    fd0, tmpn = tempfile.mkstemp(prefix=f".{p.name}.", suffix=".tmp", dir=p.parent); os.close(fd0); tmp=Path(tmpn)
    try:
        with tmp.open("w", encoding="utf-8", newline="") as fh:
            w=csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore", lineterminator="\n"); w.writeheader(); w.writerows(rows)
        os.replace(tmp, p)
    finally:
        if tmp.exists(): tmp.unlink()
def aw_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    fd0, tmpn = tempfile.mkstemp(prefix=f".{p.name}.", suffix=".tmp", dir=p.parent); os.close(fd0); tmp=Path(tmpn)
    try:
        tmp.write_text(json.dumps(obj, indent=2, sort_keys=True)+"\n", encoding="utf-8"); os.replace(tmp, p)
    finally:
        if tmp.exists(): tmp.unlink()
def aw_text(p: Path, s: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    fd0, tmpn = tempfile.mkstemp(prefix=f".{p.name}.", suffix=".tmp", dir=p.parent); os.close(fd0); tmp=Path(tmpn)
    try:
        tmp.write_text(s, encoding="utf-8"); os.replace(tmp, p)
    finally:
        if tmp.exists(): tmp.unlink()

def backup(paths):
    ROLLBACK.mkdir(parents=True, exist_ok=True); m={}
    for p in paths:
        k=str(p.relative_to(ROOT)).replace("\\","/"); m[k]={"exists":p.exists(),"sha256":fsha(p)}
        if p.exists():
            b=ROLLBACK/(p.name+".pre_v6")
            if not b.exists(): b.write_bytes(p.read_bytes())
            m[k]["backup"]=str(b.relative_to(ROOT)).replace("\\","/")
    aw_json(ROLLBACK/"rollback_manifest.json", m); return m

def policy_doc():
    _, rows = rd(NORM_PARAM)
    v1=[r for r in rows if t(r.get("normalisation_model_version"))=="HPR-NORM-A-v1"]
    if len(v1)!=1: raise RuntimeError("Expected exactly one HPR-NORM-A-v1 parameter row")
    r=v1[0]
    if t(r.get("normalisation_method")) != METHOD: raise RuntimeError("BLOCKED_FORMULA_CHANGE_REQUIRES_APPROVAL")
    centre, scale = fd(d(r["centre_value"])), fd(d(r["scale_value"], pos=True))
    ev=sh([POLICY, METHOD, centre, scale, r.get("parameter_evidence_sha256"), "HISTORICAL_BACKFILL_AUTHORISED"])
    return {"policy_id":POLICY,"policy_version":POLICY,"supersedes_policy_id":"HPR-NORM-A-v1","approved_from_date":"2026-07-30","historical_eligibility_from_date":"2001-01-01","historical_backfill_authorised":True,"backfill_execution_timestamp":TS,"formula_version":"HPR-NORM-A","normalisation_method":METHOD,"centre_value":centre,"scale_value":scale,"formula_status":"FORMULA_UNCHANGED","minimum_observations_changed":False,"source_hpr_norm_a_v1_parameter_id":t(r.get("normalisation_parameter_id")),"source_hpr_norm_a_v1_parameter_evidence_sha256":t(r.get("parameter_evidence_sha256")),"policy_evidence_sha256":ev}

def race_no_from_key(race_key):
    x=t(race_key).upper()
    if "|R" in x:
        raw=x.split("|R")[-1][:2]
        return str(int(raw)) if raw.isdigit() else raw
    return ""

def winner_maps():
    by_key={}; dup=set(); counts=Counter()
    for r in stream(RESULTS):
        if t(r.get("won")).upper() not in {"1","TRUE","Y","YES"} and t(r.get("finish_num"))!="1": continue
        rn=num(r.get("race_no") or r.get("race_number"));
        if not t(r.get("race_date")) or not ct(r.get("track")) or not rn: continue
        rk=f"{t(r.get('race_date'))}|{ct(r.get('track'))}|{int(rn):02d}" if rn.isdigit() else f"{t(r.get('race_date'))}|{ct(r.get('track'))}|{rn}"
        sid=num(r.get("horse_code") or r.get("runner_id"))
        if not sid: continue
        payload={"source_system":"RACINGCOM","source_horse_id":sid,"canonical_horse_id":f"RCOM_HORSE_{sid}","canonical_horse_name":nn(r.get("horse")),"source_horse_name":nn(r.get("horse")),"runner_id":num(r.get("runner_id")),"race_id":num(r.get("race_id")),"identity_method":"EXACT_RACINGCOM_WINNER_SOURCE_ID","identity_evidence_reference":f"{RESULTS.name}#race_id={num(r.get('race_id'))};runner_id={num(r.get('runner_id'))};horse_code={sid}","source_identity_evidence_sha256":sh(["RACINGCOM",r.get("race_id"),r.get("runner_id"),sid,r.get("horse")])}
        counts[rk]+=1
        if rk not in by_key: by_key[rk]=payload
    for k,c in counts.items():
        if c>1: dup.add(k); by_key.pop(k,None)
    ra={}
    if RA_XWALK.exists():
        _, rows=rd(RA_XWALK)
        for r in rows:
            if t(r.get("approval_status"))!="APPROVED": continue
            rdte=t(r.get("source_meeting_date")); tr=ct(r.get("track")); rn=t(r.get("race_number")); name=nn(r.get("source_horse_name"))
            if not (rdte and tr and rn and name): continue
            k=f"{rdte}|{tr}|{int(rn):02d}|{name}" if rn.isdigit() else f"{rdte}|{tr}|{rn}|{name}"
            ra[k]={"source_system":"RACING_AUSTRALIA","source_horse_id":t(r.get("source_horse_id")),"canonical_horse_id":t(r.get("canonical_horse_id")),"canonical_horse_name":nn(r.get("canonical_horse_name") or r.get("source_horse_name")),"source_horse_name":name,"runner_id":t(r.get("source_race_entry_id")),"race_id":f"RA|{rdte}|{tr}|R{rn}","identity_method":"EXACT_RACING_AUSTRALIA_CURRENT_CROSSWALK","identity_evidence_reference":t(r.get("evidence_reference")),"source_identity_evidence_sha256":t(r.get("identity_evidence_sha256")) or sh(r.values())}
    return by_key, dup, ra

def build_core(pol):
    wb, dup, ra = winner_maps(); _, base = rd(BASE)
    centre, scale = Decimal(pol["centre_value"]), Decimal(pol["scale_value"])
    par_id = "PNP2-" + sh([POLICY, centre, scale])[:24].upper(); pe=pol["policy_evidence_sha256"]
    norms=[]; nrej=[]; rbs=[]; obs=[]; orej=[]; idrej=[]; seen=set()
    for b in base:
        pib=t(b.get("performance_intelligence_base_id")); rdate=t(b.get("race_date")); tr=ct(b.get("track_name")); rn=race_no_from_key(b.get("race_key")); key=f"{rdate}|{tr}|{int(rn):02d}" if rn.isdigit() else f"{rdate}|{tr}|{rn}"; name=nn(b.get("winner_horse_name"))
        ident=wb.get(key); idstatus="APPROVED_RACINGCOM" if ident else ""
        if not ident and name:
            ident=ra.get(f"{key}|{name}"); idstatus="APPROVED_CURRENT_RA" if ident else ""
        reason=""
        try:
            if not pib: reason="INVALID_RUNNER_ID"
            elif not rdate: reason="INVALID_PERFORMANCE_DATE"
            else: dt(rdate)
            if not reason and (not t(b.get("race_key")) or not t(b.get("lengths_versus_standard_id"))): reason="INVALID_RACE_ID"
            if not reason and (not t(b.get("raw_performance_lengths")) or not t(b.get("performance_intelligence_base_evidence_sha256"))): reason="MISSING_REQUIRED_INPUT"
            raw=d(b.get("raw_performance_lengths")) if not reason else Decimal(0)
            if not reason and key in dup: reason="IDENTITY_AMBIGUOUS"
            if not reason and not ident: reason="IDENTITY_UNRESOLVED"
            if not reason:
                nat=(ident["canonical_horse_id"],t(b.get("race_key")),rdate)
                if nat in seen: reason="DUPLICATE_RACE_RUNNER"
                else: seen.add(nat)
        except Exception:
            reason=reason or "NORMALISATION_INPUT_INVALID"; raw=Decimal(0)
        if reason:
            nrej.append({"performance_intelligence_base_id":pib,"lengths_versus_standard_id":t(b.get("lengths_versus_standard_id")),"race_key":t(b.get("race_key")),"race_date":rdate,"track_name":t(b.get("track_name")),"official_distance_metres":t(b.get("official_distance_metres")),"winner_horse_name":t(b.get("winner_horse_name")),"rejection_reason":reason})
            orej.append({"performance_rating_base_id":"","performance_normalisation_id":"","performance_intelligence_base_id":pib,"benchmark_observation_id":t(b.get("benchmark_observation_id")),"race_key":t(b.get("race_key")),"race_date":rdate,"track_name":t(b.get("track_name")),"official_distance_metres":t(b.get("official_distance_metres")),"source_horse_name":t(b.get("winner_horse_name")),"rejection_reason":reason,"policy_version":POLICY,"built_at_utc":TS})
            if reason in {"IDENTITY_UNRESOLVED","IDENTITY_AMBIGUOUS","DUPLICATE_RACE_RUNNER"}: idrej.append({"race_key":t(b.get("race_key")),"race_date":rdate,"track_name":t(b.get("track_name")),"winner_horse_name":t(b.get("winner_horse_name")),"rejection_reason":reason})
            continue
        nv=(raw-centre)/scale; nid="PNR2-"+sh([CONTRACT,POLICY,pib,b.get("lengths_versus_standard_id"),b.get("race_key"),rdate,fd(raw),fd(centre),fd(scale)])[:24].upper(); nev=sh([nid,pib,b.get("performance_intelligence_base_evidence_sha256"),pe,fd(nv)]); winner=ident["canonical_horse_name"] or name
        norms.append({"performance_normalisation_id":nid,"performance_intelligence_base_id":pib,"normalisation_parameter_id":par_id,"lengths_versus_standard_id":t(b.get("lengths_versus_standard_id")),"benchmark_observation_id":t(b.get("benchmark_observation_id")),"race_key":t(b.get("race_key")),"race_date":rdate,"track_name":t(b.get("track_name")),"official_distance_metres":t(b.get("official_distance_metres")),"winner_horse_name":winner,"raw_performance_lengths":fd(raw),"centre_value":fd(centre),"scale_value":fd(scale),"normalised_performance_value":fd(nv),"normalisation_method":METHOD,"normalisation_status":STATUS_NORM,"normalisation_model_version":POLICY,"source_performance_base_evidence_sha256":t(b.get("performance_intelligence_base_evidence_sha256")),"source_normalisation_parameter_evidence_sha256":pe,"performance_normalisation_evidence_sha256":nev,"builder_version":BUILDER,"contract_version":CONTRACT,"built_at_utc":TS})
        rid="PRB2-"+sh([CONTRACT,nid,fd(nv),STATUS_RATING_BASE])[:24].upper(); rev=sh([rid,nev,fd(nv),STATUS_RATING_BASE])
        rbs.append({"performance_rating_base_id":rid,"performance_normalisation_id":nid,"performance_intelligence_base_id":pib,"normalisation_parameter_id":par_id,"lengths_versus_standard_id":t(b.get("lengths_versus_standard_id")),"benchmark_observation_id":t(b.get("benchmark_observation_id")),"race_key":t(b.get("race_key")),"race_date":rdate,"track_name":t(b.get("track_name")),"official_distance_metres":t(b.get("official_distance_metres")),"winner_horse_name":winner,"raw_performance_lengths":fd(raw),"normalised_performance_value":fd(nv),"rating_base_value":fd(nv),"rating_method":"DIRECT_NORMALISED_PERFORMANCE_VALUE","rating_status":STATUS_RATING_BASE,"normalisation_model_version":POLICY,"source_performance_normalisation_evidence_sha256":nev,"performance_rating_base_evidence_sha256":rev,"source_builder_version":BUILDER,"builder_version":BUILDER,"contract_version":CONTRACT,"built_at_utc":TS})
        oid="HPO2-"+sh([CONTRACT,ident["canonical_horse_id"],t(b.get("race_key")),rid,rdate,ident["identity_method"]])[:24].upper(); oev=sh([oid,rev,ident["source_identity_evidence_sha256"],STATUS_OBS])
        obs.append({"horse_performance_observation_id":oid,"canonical_horse_id":ident["canonical_horse_id"],"canonical_horse_name":ident["canonical_horse_name"],"source_horse_name":ident["source_horse_name"],"performance_rating_base_id":rid,"performance_normalisation_id":nid,"performance_intelligence_base_id":pib,"benchmark_observation_id":t(b.get("benchmark_observation_id")),"race_key":t(b.get("race_key")),"race_date":rdate,"track_name":t(b.get("track_name")),"official_distance_metres":t(b.get("official_distance_metres")),"raw_performance_lengths":fd(raw),"normalised_performance_value":fd(nv),"rating_base_value":fd(nv),"rating_status":STATUS_RATING_BASE,"identity_method":ident["identity_method"],"identity_status":STATUS_OBS,"identity_evidence_reference":ident["identity_evidence_reference"],"source_identity_evidence_sha256":ident["source_identity_evidence_sha256"],"source_performance_rating_base_evidence_sha256":rev,"horse_performance_observation_evidence_sha256":oev,"builder_version":BUILDER,"contract_version":CONTRACT,"built_at_utc":TS})
    norms.sort(key=lambda r:(r["race_date"],r["race_key"],r["performance_intelligence_base_id"])); rbs.sort(key=lambda r:(r["race_date"],r["race_key"],r["performance_rating_base_id"])); obs.sort(key=lambda r:(r["canonical_horse_id"],r["race_date"],r["race_key"])); nrej.sort(key=lambda r:(r["race_date"],r["race_key"])); orej.sort(key=lambda r:(r["race_date"],r["race_key"])); idrej.sort(key=lambda r:(r["race_date"],r["race_key"]))
    aw_csv(OUT_NORM,norms,FIELDS_NORM); aw_csv(OUT_NORM_REJ,nrej,FIELDS_NORM_REJ); aw_csv(OUT_RATING_BASE,rbs,FIELDS_RB); aw_csv(OUT_OBS,obs,FIELDS_OBS); aw_csv(OUT_OBS_REJ,orej,FIELDS_OBS_REJ); aw_csv(DOCS/"EDGEIQ_HISTORICAL_HORSE_IDENTITY_REJECTIONS_V1.csv",idrej,["race_key","race_date","track_name","winner_horse_name","rejection_reason"])
    return {"performance_base_rows":len(base),"eligible_rows":len(norms),"accepted_rows":len(norms),"rejected_rows":len(nrej),"normalisation_rows":len(norms),"performance_rating_base_rows":len(rbs),"horse_observation_rows":len(obs),"rejection_reasons":dict(Counter(x["rejection_reason"] for x in nrej)),"distinct_historical_horses":len({x["canonical_horse_id"] for x in obs if x["canonical_horse_id"].startswith("RCOM_HORSE_")}),"approved_identities":len(obs),"unresolved_identities":sum(1 for x in nrej if x["rejection_reason"]=="IDENTITY_UNRESOLVED"),"ambiguous_identities":sum(1 for x in nrej if x["rejection_reason"]=="IDENTITY_AMBIGUOUS"),"identity_rejection_rows":len(idrej),"earliest_performance_date":min((x["race_date"] for x in norms), default=""),"latest_performance_date":max((x["race_date"] for x in norms), default=""),"policy_id":POLICY,"formula_version":"HPR-NORM-A","formula_status":"FORMULA_UNCHANGED"}, obs, rbs

def build_aggs(obs):
    _, ps=rd(AGG_PARAM); p=ps[0]
    mino=int(t(p["minimum_observations"])); maxo=int(t(p["maximum_observations"])); look=int(t(p["lookback_days"])); half=d(p["recency_half_life_days"]) if t(p.get("recency_half_life_days")) else None
    if mino != 5: raise RuntimeError("minimum_observations changed")
    by=defaultdict(list)
    for o in obs:
        by[o["canonical_horse_id"]].append(o)
    aggs=[]; ratings=[]; depths=[]; bands=Counter(); pid=t(p["horse_performance_aggregation_parameter_id"]); pev=t(p["parameter_evidence_sha256"])
    for hid, rows in sorted(by.items()):
        rows.sort(key=lambda r:(r["race_date"],r["horse_performance_observation_id"])); dep=len(rows); depths.append(dep)
        bands["1 observation" if dep==1 else "2 observations" if dep==2 else "3 observations" if dep==3 else "4 observations" if dep==4 else "5-9 observations" if dep<10 else "10-19 observations" if dep<20 else "20-49 observations" if dep<50 else "50+ observations"] += 1
        if dep < mino: continue
        for asof in sorted({dt(r["race_date"]) for r in rows}):
            start=asof-timedelta(days=look); elig=[r for r in rows if start <= dt(r["race_date"]) <= asof]
            elig.sort(key=lambda r:(r["race_date"],r["horse_performance_observation_id"]), reverse=True)
            if len(elig) < mino: continue
            inc=elig[:maxo]; vals=[]
            for r in inc:
                age=(asof-dt(r["race_date"])).days
                w=Decimal(str(math.pow(0.5, age/float(half)))) if half else Decimal(1)
                vals.append((d(r["rating_base_value"]), w))
            with localcontext() as ctx:
                ctx.prec=40; tw=sum((w for _,w in vals), Decimal(0)); av=sum((v*w for v,w in vals), Decimal(0))/tw
            chrono=sorted(inc,key=lambda r:(r["race_date"],r["horse_performance_observation_id"])); ids=[r["horse_performance_observation_id"] for r in chrono]; evs=[r["horse_performance_observation_evidence_sha256"] for r in chrono]
            idsha=sh(ids); obsha=sh(evs); aid="HPA2-"+sh([CONTRACT,hid,asof.isoformat(),pid,*ids])[:24].upper(); aev=sh([aid,pev,obsha,fd(av),fd(tw),len(inc),STATUS_AGG]); name=rows[-1]["canonical_horse_name"]
            aggs.append({"horse_performance_aggregate_id":aid,"canonical_horse_id":hid,"canonical_horse_name":name,"aggregate_as_of_date":asof.isoformat(),"horse_performance_aggregation_parameter_id":pid,"aggregation_method":t(p["aggregation_method"]),"maximum_observations":str(maxo),"lookback_days":str(look),"minimum_observations":str(mino),"recency_weighting_method":t(p["recency_weighting_method"]),"recency_half_life_days":fd(half) if half else "","eligible_observation_count":str(len(elig)),"included_observation_count":str(len(inc)),"oldest_included_race_date":min(dt(r["race_date"]) for r in inc).isoformat(),"newest_included_race_date":max(dt(r["race_date"]) for r in inc).isoformat(),"total_weight":fd(tw),"aggregate_rating_value":fd(av),"aggregate_status":STATUS_AGG,"aggregation_model_version":t(p["aggregation_model_version"]),"included_observation_ids_sha256":idsha,"source_parameter_evidence_sha256":pev,"source_observation_evidence_sha256":obsha,"horse_performance_aggregate_evidence_sha256":aev,"builder_version":BUILDER,"contract_version":CONTRACT,"built_at_utc":TS})
            hrid="HPR2-"+sh([CONTRACT,aid,hid,asof.isoformat(),fd(av)])[:24].upper(); hev=sh([hrid,aev,fd(av),STATUS_RATING])
            ratings.append({"horse_performance_rating_id":hrid,"horse_performance_aggregate_id":aid,"canonical_horse_id":hid,"canonical_horse_name":name,"rating_as_of_date":asof.isoformat(),"horse_performance_aggregation_parameter_id":pid,"aggregation_method":t(p["aggregation_method"]),"included_observation_count":str(len(inc)),"aggregate_rating_value":fd(av),"horse_performance_rating_value":fd(av),"horse_performance_rating_method":"DIRECT_HISTORICAL_AGGREGATE_VALUE","horse_performance_rating_status":STATUS_RATING,"aggregation_model_version":t(p["aggregation_model_version"]),"source_horse_performance_aggregate_evidence_sha256":aev,"horse_performance_rating_evidence_sha256":hev,"source_builder_version":BUILDER,"builder_version":BUILDER,"contract_version":CONTRACT,"built_at_utc":TS})
    aggs.sort(key=lambda r:(r["canonical_horse_id"],r["aggregate_as_of_date"],r["horse_performance_aggregate_id"])); ratings.sort(key=lambda r:(r["canonical_horse_id"],r["rating_as_of_date"],r["horse_performance_rating_id"]))
    aw_csv(OUT_AGG,aggs,FIELDS_AGG); aw_csv(OUT_RATING,ratings,FIELDS_RATING)
    return {"input_observations":len(obs),"distinct_horses":len(by),"horses_meeting_threshold":sum(1 for x in depths if x>=mino),"horses_below_threshold":sum(1 for x in depths if x<mino),"output_aggregates":len(aggs),"output_ratings":len(ratings),"distinct_rated_horses":len({r["canonical_horse_id"] for r in ratings}),"latest_rating_date":max((r["rating_as_of_date"] for r in ratings), default=""),"maximum_observation_depth":max(depths, default=0),"median_observation_depth":sorted(depths)[len(depths)//2] if depths else 0,"depth_distribution":dict(bands),"minimum_observations":mino}, aggs, ratings

def entry_adapt(r):
    if "race_entry_id" in r:
        return {"race_entry_id":t(r.get("race_entry_id")),"race_id":t(r.get("race_id")),"runner_id":t(r.get("runner_id")),"horse_id":t(r.get("canonical_horse_id")),"name":nn(r.get("canonical_horse_name")),"date":t(r.get("race_date")),"ev":t(r.get("race_entry_evidence_sha256")),"builder":t(r.get("builder_version"))}
    race=t(r.get("canonical_race_id")); run=t(r.get("canonical_runner_id"))
    return {"race_entry_id":"REF1-"+sh([race,run,r.get("source_record_id")])[:24].upper(),"race_id":race,"runner_id":run,"horse_id":run,"name":nn(r.get("runner_name")),"date":t(r.get("race_date")),"ev":t(r.get("source_hash")) or sh(r.values()),"builder":"edgeiq_race_entry_fact_v1.current_schema_adapter"}

def build_snaps(ratings):
    by=defaultdict(list)
    for r in ratings: by[r["canonical_horse_id"]].append(r)
    for xs in by.values(): xs.sort(key=lambda r:(r["rating_as_of_date"],r["horse_performance_rating_id"]))
    _, entries=rd(RACE_ENTRY); snaps=[]; miss=Counter()
    for raw in entries:
        e=entry_adapt(raw); hist=[r for r in by.get(e["horse_id"],[]) if r["rating_as_of_date"] < e["date"]]
        if not hist: miss["NO_PRIOR_HORSE_RATING"] += 1; continue
        sel=hist[-1]; vals=[d(x["horse_performance_rating_value"]) for x in hist]; ids=sh([x["horse_performance_rating_id"] for x in hist]); evs=sh([x["horse_performance_rating_evidence_sha256"] for x in hist]); sid="REHPS2-"+sh([CONTRACT,e["race_entry_id"],sel["horse_performance_rating_id"],e["date"]])[:24].upper(); sev=sh([sid,e["ev"],sel["horse_performance_rating_evidence_sha256"],ids,STATUS_SNAPSHOT])
        snaps.append({"race_entry_horse_performance_snapshot_id":sid,"race_entry_id":e["race_entry_id"],"race_id":e["race_id"],"race_date":e["date"],"runner_id":e["runner_id"],"canonical_horse_id":e["horse_id"],"canonical_horse_name":e["name"] or sel["canonical_horse_name"],"selected_horse_performance_rating_id":sel["horse_performance_rating_id"],"selected_rating_as_of_date":sel["rating_as_of_date"],"rating_age_days":str((dt(e["date"])-dt(sel["rating_as_of_date"])).days),"eligible_historical_rating_count":str(len(hist)),"first_eligible_rating_date":hist[0]["rating_as_of_date"],"latest_eligible_rating_date":hist[-1]["rating_as_of_date"],"selected_horse_performance_rating_value":sel["horse_performance_rating_value"],"highest_eligible_historical_rating_value":fd(max(vals)),"lowest_eligible_historical_rating_value":fd(min(vals)),"average_eligible_historical_rating_value":fd(sum(vals,Decimal(0))/Decimal(len(vals))),"selected_included_observation_count":sel["included_observation_count"],"horse_performance_rating_method":sel["horse_performance_rating_method"],"race_entry_horse_performance_snapshot_status":STATUS_SNAPSHOT,"source_race_entry_evidence_sha256":e["ev"],"source_selected_rating_evidence_sha256":sel["horse_performance_rating_evidence_sha256"],"source_eligible_rating_ids_sha256":ids,"source_eligible_rating_evidence_sha256":evs,"race_entry_horse_performance_snapshot_evidence_sha256":sev,"source_race_entry_builder_version":e["builder"],"source_rating_builder_version":sel["builder_version"],"builder_version":BUILDER,"contract_version":CONTRACT,"built_at_utc":TS})
    snaps.sort(key=lambda r:(r["race_date"],r["race_id"],r["race_entry_id"])); aw_csv(OUT_SNAPSHOT,snaps,FIELDS_SNAP)
    return {"race_entry_rows":len(entries),"input_ratings":len(ratings),"output_snapshots":len(snaps),"distinct_snapshot_horses":len({r["canonical_horse_id"] for r in snaps}),"latest_snapshot_date":max((r["race_date"] for r in snaps), default=""),"missing_snapshot_reasons":dict(miss)}, snaps

def epi_summary(snaps):
    comps=[]; epis=[]
    if COMPONENT.exists(): _, comps=rd(COMPONENT)
    if EPI.exists(): _, epis=rd(EPI)
    by=defaultdict(set)
    for c in comps: by[t(c.get("race_entry_id"))].add(t(c.get("epi_component_code")))
    need={"HISTORICAL_PERFORMANCE","SUITABILITY","RACE_CONTEXT"}; miss=Counter()
    for s in snaps:
        if need - by.get(s["race_entry_id"], set()): miss["MISSING_REQUIRED_EPI_COMPONENT"] += 1
        else: miss["READY_COMPONENTS"] += 1
    return {"input_component_rows":len(comps),"output_epi_rows":len(epis),"distinct_current_runners_with_epi":len({e.get("race_entry_id") for e in epis}),"current_runners_missing_epi":miss.get("MISSING_REQUIRED_EPI_COMPONENT",0),"missing_reasons":dict(miss),"epi_status":"BLOCKED_EPI_COMPONENT_CONTRACT" if snaps and not epis else ("EPI_POPULATED" if epis else "NO_SNAPSHOTS_FOR_EPI")}

def sale(obs, aggs, ratings, snaps):
    rows=[]
    if RA_XWALK.exists(): _, rows=rd(RA_XWALK)
    cur=[r for r in rows if t(r.get("source_meeting_date"))=="2026-07-26" and ct(r.get("track"))=="SALE"]
    obsby=defaultdict(list)
    for o in obs: obsby[o["canonical_horse_id"]].append(o)
    ah={r["canonical_horse_id"] for r in aggs}; rh={r["canonical_horse_id"] for r in ratings}; shs={r["canonical_horse_id"] for r in snaps}
    out=[]
    for r in sorted(cur,key=lambda x:(t(x.get("race_number")),t(x.get("saddlecloth")),t(x.get("source_horse_name")))):
        hid=t(r.get("canonical_horse_id")); co=[o for o in obsby.get(hid,[]) if o["race_date"]>="2026-07-20"]; ho=[o for o in obsby.get(hid,[]) if o["race_date"]<"2026-07-20"]; total=len(co)+len(ho)
        block="INSUFFICIENT_OBSERVATIONS" if total<5 else "NO_HORSE_AGGREGATE" if hid not in ah else "NO_PERFORMANCE_RATING" if hid not in rh else "NO_SNAPSHOT" if hid not in shs else "MISSING_REQUIRED_EPI_COMPONENT"
        out.append({"runner_name":t(r.get("source_horse_name")),"canonical_horse_id":hid,"race_number":t(r.get("race_number")),"current_observations":str(len(co)),"historical_observations":str(len(ho)),"total_governed_observations":str(total),"aggregate_available":"YES" if hid in ah else "NO","rating_available":"YES" if hid in rh else "NO","snapshot_available":"YES" if hid in shs else "NO","epi_available":"NO","blocking_reason":block})
    fields=["runner_name","canonical_horse_id","race_number","current_observations","historical_observations","total_governed_observations","aggregate_available","rating_available","snapshot_available","epi_available","blocking_reason"]
    aw_csv(DOCS/"EDGEIQ_VICTORIA_CURRENT_RATINGS_EPI_ACCEPTANCE_V3.csv",out,fields)
    ch=next((x for x in out if x["runner_name"]=="CHIGURH" or x["canonical_horse_id"]=="RA_HORSE_34054013730"),{})
    return {"current_sale_runners":len(out),"governed_identities":len({x["canonical_horse_id"] for x in out}),"runners_with_historical_observations":sum(int(x["historical_observations"])>0 for x in out),"runners_with_5_plus_observations":sum(int(x["total_governed_observations"])>=5 for x in out),"runners_with_aggregates":sum(x["aggregate_available"]=="YES" for x in out),"runners_with_ratings":sum(x["rating_available"]=="YES" for x in out),"runners_with_snapshots":sum(x["snapshot_available"]=="YES" for x in out),"runners_with_epi":0,"chigurh":ch}

def reports(pol, rb, ns, ag, ss, es, sal):
    aw_json(DOCS/"EDGEIQ_HPR_NORM_A_V2_POLICY.json", pol)
    aw_text(DOCS/"EDGEIQ_HPR_NORM_A_V2_POLICY.md", f"# EDGEIQ HPR-NORM-A-v2 Policy\n\nPolicy ID: {POLICY}\n\nHPR-NORM-A-v1 remains unchanged. HPR-NORM-A-v2 authorises historical backfill for governed Performance Base rows using the unchanged formula.\n\nFormula status: FORMULA_UNCHANGED\n\nMinimum observations changed: NO\n\nBackfill timestamp: {TS}\n")
    inv={"policy":pol,"rollback":rb,"historical_normalisation":ns,"horse_aggregates":ag,"snapshots":ss,"epi":es,"sale":sal}
    aw_json(DOCS/"EDGEIQ_VICTORIA_LIVE_RECOVERY_V6_INVESTIGATION.json", inv); aw_text(DOCS/"EDGEIQ_VICTORIA_LIVE_RECOVERY_V6_INVESTIGATION.md", "# EDGEIQ Victoria Live Recovery V6 Investigation\n\n"+json.dumps(inv,indent=2,sort_keys=True)+"\n")
    aw_json(DOCS/"EDGEIQ_HISTORICAL_NORMALISATION_BACKFILL_V1.json", ns); aw_text(DOCS/"EDGEIQ_HISTORICAL_NORMALISATION_BACKFILL_V1.md", "# Historical Normalisation Backfill V1\n\n"+json.dumps(ns,indent=2,sort_keys=True)+"\n"); aw_csv(DOCS/"EDGEIQ_HISTORICAL_NORMALISATION_BACKFILL_V1.csv",[{"metric":k,"value":json.dumps(v,sort_keys=True) if isinstance(v,(dict,list)) else v} for k,v in ns.items()],["metric","value"])
    ids={k:ns.get(k) for k in ["distinct_historical_horses","approved_identities","unresolved_identities","ambiguous_identities","identity_rejection_rows"]}; aw_json(DOCS/"EDGEIQ_HISTORICAL_HORSE_IDENTITY_BACKFILL_V1.json",ids); aw_text(DOCS/"EDGEIQ_HISTORICAL_HORSE_IDENTITY_BACKFILL_V1.md","# Historical Horse Identity Backfill V1\n\n"+json.dumps(ids,indent=2,sort_keys=True)+"\n")
    aw_csv(DOCS/"EDGEIQ_HORSE_OBSERVATION_DEPTH_V2.csv",[{"depth_band":k,"horse_count":v} for k,v in sorted(ag.get("depth_distribution",{}).items())],["depth_band","horse_count"]); aw_json(DOCS/"EDGEIQ_HORSE_OBSERVATION_DEPTH_V2.json",ag); aw_text(DOCS/"EDGEIQ_HORSE_OBSERVATION_DEPTH_V2.md","# Horse Observation Depth V2\n\n"+json.dumps(ag,indent=2,sort_keys=True)+"\n")
    aw_json(DOCS/"EDGEIQ_VICTORIA_CURRENT_RATINGS_EPI_ACCEPTANCE_V3.json",{"sale":sal,"epi":es,"snapshots":ss}); aw_text(DOCS/"EDGEIQ_VICTORIA_CURRENT_RATINGS_EPI_ACCEPTANCE_V3.md","# Victoria Current Ratings EPI Acceptance V3\n\n"+json.dumps({"sale":sal,"epi":es,"snapshots":ss},indent=2,sort_keys=True)+"\n")
    aw_text(DOCS/"EDGEIQ_VICTORIA_LIVE_RECOVERY_V6_VALIDATION.md", "# V6 Validation\n\nValidation is produced after compile/build commands. Core deterministic rebuild completed.\n")

def run():
    DOCS.mkdir(parents=True, exist_ok=True)
    rb=backup([OUT_NORM,OUT_NORM_REJ,OUT_RATING_BASE,OUT_OBS,OUT_OBS_REJ,OUT_AGG,OUT_RATING,OUT_SNAPSHOT,COMPONENT,EPI])
    pol=policy_doc(); ns, obs, _ = build_core(pol); ag, agrows, ratings = build_aggs(obs); ss, snaps = build_snaps(ratings); es = epi_summary(snaps); sal = sale(obs, agrows, ratings, snaps); reports(pol, rb, ns, ag, ss, es, sal)
    result={"policy":pol,"normalisation":ns,"aggregate":ag,"snapshot":ss,"epi":es,"sale":sal,"output_hashes":{str(p.relative_to(ROOT)).replace("\\","/"):fsha(p) for p in [OUT_NORM,OUT_NORM_REJ,OUT_RATING_BASE,OUT_OBS,OUT_OBS_REJ,OUT_AGG,OUT_RATING,OUT_SNAPSHOT]}}
    aw_json(DOCS/"EDGEIQ_VICTORIA_LIVE_RECOVERY_V6_IDEMPOTENCY.json",result)
    print("EDGEIQ_VICTORIA_LIVE_RECOVERY_V6_BUILD_COMPLETE")
    print(json.dumps({"normalisation_rows":ns["normalisation_rows"],"observations":ns["horse_observation_rows"],"aggregates":ag["output_aggregates"],"ratings":ag["output_ratings"],"snapshots":ss["output_snapshots"],"epi_status":es["epi_status"]},indent=2,sort_keys=True))
    return result

if __name__ == "__main__": run()
