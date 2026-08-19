
import csv
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
AUDIT = DATA / "edgeiq_form_rating_outliers_v1.csv"
TARGETS = [DATA / "edgeiq_form_enrichment_feed_v4.csv", DATA / "edgeiq_live_runner_board_v1.csv", DATA / "edgeiq_live_runner_board_governed_v1.csv"]
OUT = DATA / "edgeiq_form_rating_outlier_fix_v1.csv"
SUM = DATA / "edgeiq_form_rating_outlier_fix_v1_summary.csv"
REP = DATA / "edgeiq_form_rating_outlier_fix_v1_report.txt"
STAMP = "20260629"
DASH = chr(8212)

ALT_SOURCES = [
    ("HISTORICAL_FORM_TABLE", DATA / "historical_form_table.csv", {"horse":["horse"],"date":["race_date"],"track":["track"],"distance":["distance"],"rating":["run_rating","race_rating"],"finish":["finish_pos"]}),
    ("HISTORY_MASTER", DATA / "edgeiq_historical_run_ratings_master_v1.csv", {"horse":["horse","horse_key"],"date":["race_date"],"track":["track"],"distance":["distance"],"rating":["performance_rating"],"finish":["finish_pos"]}),
    ("V6_1_RESEARCH_ARCHIVE", DATA / "edgeiq_historical_performance_rating_v6_1_research.csv", {"horse":["horse"],"date":["race_date"],"track":["track"],"distance":["distance"],"rating":["performance_rating_v6_1_research","performance_rating_v5_1","performance_rating_v3"],"finish":["finish_position","finish_pos_raw"]}),
    ("V6_1_REPLAY_ARCHIVE", DATA / "edgeiq_v6_1_settled_gap_replay_v2_expanded.csv", {"horse":["horse","horse_key"],"date":["race_date","meeting_date"],"track":["track"],"distance":[],"rating":["projected_rating_V6_1_RESEARCH","race_target_rating_V6_1_RESEARCH"],"finish":["finish_position"]}),
    ("RUNNER_BOARD_SNAPSHOT", DATA / "edgeiq_archived_probability_rating_candidates_v1.csv", {"horse":["horse","horse_key"],"date":["race_date","meeting_date"],"track":["track"],"distance":["distance"],"rating":["rating","production_rating","total_rating_points","governed_projection_rating_v6"],"finish":["finish_position","finish_pos"]}),
]

def clean(v): return str(v or "").strip()
def norm_horse(v):
    s = re.sub(r"\([^)]*\)", " ", clean(v).upper())
    return re.sub(r"[^A-Z0-9]+", "", s)
def clean_date(v):
    s = clean(v)[:10]
    try: return datetime.fromisoformat(s).date().isoformat()
    except Exception: return ""
def clean_track(v): return re.sub(r"\s+", " ", clean(v).upper())
def number(v):
    s=clean(v)
    if not s or s in {DASH,"--"}: return None
    m=re.search(r"-?\d+(?:\.\d+)?", s)
    if not m: return None
    try: return float(m.group(0))
    except Exception: return None
def first(row, cols):
    for c in cols:
        v=clean(row.get(c))
        if v and v.upper() not in {"UNKNOWN","NULL","NAN","NONE","N/A","NA","0","0.0"}: return v
    return ""
def fmt(x): return f"{float(x):.1f}"
def valid_rating(v, finish=None):
    x=number(v); f=number(finish)
    if x is None or x < 15 or x > 110: return False
    if f == 1 and x < 30: return False
    if f is not None and 1 <= f <= 3 and x < 25: return False
    return True
def rating_value(row,p):
    for c in [p+"rating",p+"rating_display_v2",p+"rating_display"]:
        x=number(row.get(c))
        if x is not None: return x
    return None
def finish_value(row,p):
    for c in [p+"position_display_v2",p+"position_display",p+"finish",p+"finishing_position",p+"position"]:
        x=number(row.get(c))
        if x is not None: return x
    return None

# Latest audit targets are authoritative.
audit_targets=set()
if AUDIT.exists():
    with AUDIT.open("r",encoding="utf-8-sig",newline="") as f:
        for ar in csv.DictReader(f):
            audit_targets.add((clean(ar.get("source_file")), norm_horse(ar.get("horse")), clean(ar.get("race_date")), clean(ar.get("track")), clean(ar.get("race_no")), str(clean(ar.get("last_start_n"))), clean_date(ar.get("run_date")), clean(ar.get("rating"))))

lookup=defaultdict(list)
for src,path,mapc in ALT_SOURCES:
    if not path.exists(): continue
    with path.open("r",encoding="utf-8-sig",errors="replace",newline="") as f:
        for row in csv.DictReader(f):
            h=norm_horse(first(row,mapc["horse"])); d=clean_date(first(row,mapc["date"]))
            if not h or not d: continue
            finish=first(row,mapc.get("finish",[]))
            for rc in mapc.get("rating",[]):
                rv=row.get(rc)
                if valid_rating(rv, finish):
                    lookup[(h,d)].append({"source":src,"rating":number(rv),"track":clean_track(first(row,mapc.get("track",[]))),"distance":number(first(row,mapc.get("distance",[]))),"finish":finish,"rating_col":rc})

def best_alt(h,d,track,dist,finish,original):
    best=None; best_score=-1
    for c in lookup.get((h,d),[]):
        if original is not None and abs(c["rating"]-original) < 0.01: continue
        score={"HISTORICAL_FORM_TABLE":80,"HISTORY_MASTER":70,"V6_1_RESEARCH_ARCHIVE":65,"V6_1_REPLAY_ARCHIVE":45,"RUNNER_BOARD_SNAPSHOT":35}.get(c["source"],0)
        if track and c["track"] and track==c["track"]: score+=10
        if dist is not None and c["distance"] is not None and abs(dist-c["distance"])<=25: score+=10
        cf=number(c.get("finish"))
        if finish is not None and cf is not None and abs(finish-cf)<0.01: score+=5
        if score>best_score: best=c; best_score=score
    return best

fix_rows=[]; counts=Counter()
for target in TARGETS:
    with target.open("r",encoding="utf-8-sig",errors="replace",newline="") as f:
        reader=csv.DictReader(f); fields=list(reader.fieldnames or []); rows=list(reader)
    backup=target.with_name(target.stem+f"_RATING_OUTLIER_FIX_V1_BACKUP_{STAMP}"+target.suffix)
    if not backup.exists(): shutil.copyfile(target,backup)
    for n in range(1,6):
        for extra in [f"last_start_{n}_rating_outlier_status",f"last_start_{n}_rating_outlier_original",f"last_start_{n}_rating_outlier_action",f"last_start_{n}_rating_outlier_replacement_source"]:
            if extra not in fields: fields.append(extra)
    for row in rows:
        h=norm_horse(row.get("horse_key") or row.get("horse")); horse=clean(row.get("horse"))
        for n in range(1,6):
            p=f"last_start_{n}_"; original=rating_value(row,p); run_date=clean_date(row.get(p+"date"))
            key=(target.name,h,clean(row.get("race_date") or row.get("current_race_date")),clean(row.get("track")),clean(row.get("race_no")),str(n),run_date,"" if original is None else f"{original:.3f}".rstrip("0").rstrip("."))
            simple=False
            if original is not None:
                fval=finish_value(row,p)
                simple = original < 15 or original > 110 or (fval == 1 and original < 30) or (fval is not None and 1 <= fval <= 3 and original < 25) or ("RECOVERED RATING" in (clean(row.get(p+"comment_display_v2"))+" "+clean(row.get(p+"comment_display"))).upper() and original < 30)
            if key not in audit_targets and not simple: continue
            alt=best_alt(h,run_date,clean_track(row.get(p+"track")),number(row.get(p+"distance")),finish_value(row,p),original)
            if alt:
                new=fmt(alt["rating"]); action="RECOVERED"; counts["recovered"]+=1
                row[p+"rating"]=new; row[p+"rating_display"]=new; row[p+"rating_display_v2"]=new
                row[p+"comment_display"]="Recovered Rating + "+alt["source"].replace("_"," ").title()
                row[p+"comment_display_v2"]="Recovered Rating + "+alt["source"].replace("_"," ").title()
                row[p+"rating_outlier_status"]="OUTLIER_RECOVERED"
                row[p+"rating_outlier_action"]="REPLACED_WITH_VALID_ALTERNATE"
                row[p+"rating_outlier_replacement_source"]=alt["source"]
            else:
                action="HIDDEN_UNRELIABLE"; counts["hidden_unreliable"]+=1
                row[p+"rating"]=""; row[p+"rating_display"]=DASH; row[p+"rating_display_v2"]=DASH
                row[p+"comment_display"]="Rating not reliable"; row[p+"comment_display_v2"]="Rating not reliable"
                row[p+"rating_outlier_status"]="UNRELIABLE_RATING_HIDDEN"
                row[p+"rating_outlier_action"]="HIDDEN_NO_VALID_ALTERNATE"
                row[p+"rating_outlier_replacement_source"]=""
            row[p+"rating_outlier_original"]="" if original is None else fmt(original)
            counts["flagged"]+=1
            fix_rows.append({"target_file":target.name,"horse":horse,"race_date":clean(row.get("race_date") or row.get("current_race_date")),"track":clean(row.get("track")),"race_no":clean(row.get("race_no")),"last_start_n":n,"run_date":run_date,"run_track":clean(row.get(p+"track")),"finish":clean(row.get(p+"position_display_v2") or row.get(p+"finish") or row.get(p+"finishing_position")),"original_rating":"" if original is None else fmt(original),"new_rating":clean(row.get(p+"rating_display_v2")),"action":action,"replacement_source":clean(row.get(p+"rating_outlier_replacement_source"))})
    with target.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore"); w.writeheader(); w.writerows(rows)

bankers=[r for r in fix_rows if norm_horse(r["horse"])=="BANKERSCHOICE"]
with OUT.open("w",encoding="utf-8",newline="") as f:
    fieldnames=["target_file","horse","race_date","track","race_no","last_start_n","run_date","run_track","finish","original_rating","new_rating","action","replacement_source"]
    w=csv.DictWriter(f,fieldnames=fieldnames); w.writeheader(); w.writerows(fix_rows)
summary=[("target_files",len(TARGETS)),("flagged_outlier_file_rows",counts["flagged"]),("recovered_file_rows",counts["recovered"]),("hidden_unreliable_file_rows",counts["hidden_unreliable"]),("bankers_choice_file_rows_fixed",len(bankers)),("bankers_choice_action",";".join(sorted(set(r["action"] for r in bankers))) if bankers else "NOT_FLAGGED"),("pricing_maths_changed","NO"),("v6_1_changed","NO"),("v7_2g2_changed","NO"),("status","FORM_RATING_OUTLIER_FIX_APPLIED")]
with SUM.open("w",encoding="utf-8",newline="") as f:
    w=csv.DictWriter(f,fieldnames=["metric","value"]); w.writeheader(); w.writerows({"metric":k,"value":v} for k,v in summary)
lines=["EDGEiQ FORM RATING OUTLIER FIX V1"]+[f"{k}={v}" for k,v in summary]
REP.write_text("\n".join(lines)+"\n",encoding="utf-8")
print("\n".join(lines))
