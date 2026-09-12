from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
BASE = DATA / "edgeiq_sectional_warehouse_v3.csv"
CERT = DATA / "edgeiq_sectional_raceid_to_raceno_v13.csv"
PAYLOAD = DATA / "edgeiq_sectional_payload_reconstruction_v1.csv"
OUT = DATA / "edgeiq_sectional_warehouse_v14.csv"
SUMMARY = DATA / "edgeiq_sectional_warehouse_v14_summary.csv"

MISSING={"","-","nan","none","null","undefined","n/a"}

def clean(v):
    s=str(v or "").strip()
    return "" if s.lower() in MISSING else s

def norm_name(v):
    import re
    return re.sub(r"[^A-Z0-9]","",clean(v).upper())

def main():
    if not BASE.exists(): raise SystemExit(f"Missing {BASE}")
    if not CERT.exists(): raise SystemExit(f"Missing {CERT}")
    if not PAYLOAD.exists(): raise SystemExit(f"Missing {PAYLOAD}")

    certified={}
    with CERT.open("r",newline="",encoding="utf-8-sig") as h:
        rd=csv.DictReader(h)
        for r in rd:
            if clean(r.get("status"))!="CERTIFIED_RACE_ID_TO_RACE_NO":
                continue
            key=(clean(r.get("source_file")), clean(r.get("row_no")))
            certified[key]=r

    rows=[]
    base_keys=set()
    with BASE.open("r",newline="",encoding="utf-8-sig") as h:
        rd=csv.DictReader(h)
        fields=list(rd.fieldnames or [])
        for r in rd:
            rows.append(dict(r))
            base_keys.add(clean(r.get("canonical_key")))

    added=0; skipped_missing_source=0; skipped_duplicate=0; skipped_no_splits=0
    with PAYLOAD.open("r",newline="",encoding="utf-8-sig") as h:
        rd=csv.DictReader(h)
        pfields=list(rd.fieldnames or [])
        def col(*names):
            low={x.lower():x for x in pfields}
            for n in names:
                if n.lower() in low:return low[n.lower()]
            return ""
        c_date=col("race_date","date")
        c_track=col("track","venue")
        c_horse=col("horse","horse_name","runner_name")
        c_horseid=col("horse_key","horse_id","runner_id")
        c_dist=col("distance","race_distance","race_distance_metres")
        c_200=col("last200","last_200","l200")
        c_400=col("last400","last_400","l400")
        c_600=col("last600","last_600","l600")
        c_conf=col("source_confidence","registry_confidence","confidence")
        for row_no,r in enumerate(rd,2):
            ck=(str(PAYLOAD.relative_to(ROOT)), str(row_no))
            cert=certified.get(ck)
            if not cert:
                continue
            race_date=clean(r.get(c_date))[:10] if c_date else clean(cert.get("race_date"))
            track=clean(r.get(c_track)).upper() if c_track else clean(cert.get("track"))
            horse=clean(r.get(c_horse)) if c_horse else ""
            horse_id=clean(r.get(c_horseid)) if c_horseid else ""
            horse_key=norm_name(horse or horse_id or cert.get("horse_key"))
            race_no=clean(cert.get("resolved_race_no"))
            race_id=clean(cert.get("recovered_race_id"))
            if not (race_date and track and horse_key and race_no):
                skipped_missing_source+=1; continue
            raw200=clean(r.get(c_200)) if c_200 else ""
            raw400=clean(r.get(c_400)) if c_400 else ""
            raw600=clean(r.get(c_600)) if c_600 else ""
            split_count=sum(bool(x) for x in (raw200,raw400,raw600))
            if split_count==0:
                skipped_no_splits+=1; continue
            canonical_key=f"{race_date}|{track}|{race_no}|{horse_key}"
            if canonical_key in base_keys:
                skipped_duplicate+=1; continue
            base_keys.add(canonical_key)
            template={k:"" for k in fields}
            template.update({
                "canonical_key":canonical_key,
                "race_date":race_date,
                "track":track,
                "race_no":race_no,
                "meeting_id":"",
                "race_id":race_id,
                "horse_id":horse_id,
                "horse_name":horse,
                "horse_key":horse_key,
                "distance":clean(r.get(c_dist)) if c_dist else "",
                "last200":raw200,
                "last400":raw400,
                "last600":raw600,
                "split_count":str(split_count),
                "source_rank":"100",
                "source_confidence":clean(r.get(c_conf)) if c_conf else "",
                "source_file":str(PAYLOAD.relative_to(ROOT)),
                "validation_status":"CERTIFIED_RACE_ID_TO_RACE_NO_V13",
                "ingested_at":"",
            })
            rows.append(template); added+=1

    rows.sort(key=lambda r:(clean(r.get("race_date")),clean(r.get("track")),int(clean(r.get("race_no")) or 0),clean(r.get("horse_name"))))
    with OUT.open("w",newline="",encoding="utf-8") as h:
        w=csv.DictWriter(h,fieldnames=fields);w.writeheader();w.writerows(rows)

    unique_races=len({f"{clean(r.get('race_date'))}|{clean(r.get('track'))}|{clean(r.get('race_no'))}" for r in rows if clean(r.get('race_date')) and clean(r.get('track')) and clean(r.get('race_no'))})
    unique_horses=len({clean(r.get("horse_key")) for r in rows if clean(r.get("horse_key"))})
    summary=[
        ("base_rows",len(rows)-added),
        ("certified_input_rows",len(certified)),
        ("certified_rows_added",added),
        ("skipped_missing_source",skipped_missing_source),
        ("skipped_duplicate",skipped_duplicate),
        ("skipped_no_splits",skipped_no_splits),
        ("warehouse_rows",len(rows)),
        ("unique_races",unique_races),
        ("unique_horses",unique_horses),
        ("production_status","CERTIFIED_INCREMENTAL_FOUNDATION"),
    ]
    with SUMMARY.open("w",newline="",encoding="utf-8") as h:
        w=csv.writer(h);w.writerow(["metric","value"]);w.writerows(summary)
    print("="*90);print("EDGEIQ SECTIONAL WAREHOUSE V14");print("="*90)
    for k,v in summary: print(f"{k}: {v}")
    print("OUT:",OUT);print("SUMMARY:",SUMMARY)

if __name__=="__main__":main()
