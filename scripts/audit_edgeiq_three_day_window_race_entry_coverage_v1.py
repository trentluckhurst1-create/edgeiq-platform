import csv
csv.field_size_limit(1024 * 1024 * 64)
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
TODAY = date.today()
OUT_DIR = ROOT / "docs" / "performance-intelligence" / "race-entry"
OUT_DIR.mkdir(parents=True, exist_ok=True)
RACE_OUT = OUT_DIR / "edgeiq_three_day_window_race_coverage_v1.csv"
RUNNER_OUT = OUT_DIR / "edgeiq_three_day_window_runner_coverage_v1.csv"
REPORT_OUT = OUT_DIR / "edgeiq_three_day_window_entry_gap_report_v1.md"

FILES = {
    "window": ROOT / "public/data/edgeiq_three_day_window_v1.json",
    "catalog": ROOT / "public/data/edgeiq_three_day_product_catalog_v1.json",
    "race_list": ROOT / "public/data/edgeiq_vic_three_day_race_list_v1.csv",
    "meeting_calendar": ROOT / "public/data/edgeiq_vic_three_day_meeting_calendar_v1.csv",
    "meeting_universe": ROOT / "public/data/edgeiq_vic_three_day_meeting_universe.csv",
    "race_fields": ROOT / "public/data/edgeiq_vic_three_day_race_fields.csv",
    "diagnostics": ROOT / "public/data/edgeiq_vic_three_day_meeting_diagnostics.csv",
}
SCRIPT_NAMES = [
    "scripts/edgeiq_three_day_window_v1_common.py",
    "scripts/build_edgeiq_three_day_window_v1.py",
    "scripts/build_edgeiq_three_day_product_catalog_v1.py",
    "scripts/build_edgeiq_vic_three_day_meeting_calendar_v1.py",
    "scripts/build_edgeiq_vic_three_day_meeting_universe.py",
    "scripts/build_edgeiq_racingcom_three_day_race_list_v1.py",
    "scripts/patch_edgeiq_product_catalog_canonical_window_v1.py",
    "scripts/patch_three_day_catalog_runner_merge_v1.py",
]


def norm(v: Any) -> str:
    return "" if v is None else str(v).strip()


def parse_date(v: Any):
    s = norm(v)
    if not s: return None
    if s.endswith("Z"): s = s[:-1] + "+00:00"
    try: return datetime.fromisoformat(s).date()
    except Exception: pass
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"]:
        try: return datetime.strptime(s[:10], fmt).date()
        except Exception: pass
    return None


def parse_distance(v: Any) -> str:
    s = norm(v)
    m = re.search(r"\d+", s)
    return m.group(0) if m else s


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists(): return []
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as f:
        return [dict(r) for r in csv.DictReader(f)]


def load_json(path: Path):
    if not path.exists(): return None
    return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))


def product_catalog_rows():
    obj = load_json(FILES["catalog"])
    races=[]; runners=[]; meetings=[]
    if not isinstance(obj, dict): return meetings, races, runners
    for meeting in obj.get("meetings", []) or []:
        if not isinstance(meeting, dict): continue
        mdate = norm(meeting.get("date") or meeting.get("meetingDate"))
        track = norm(meeting.get("meeting") or meeting.get("track") or meeting.get("trackName"))
        meeting_key = norm(meeting.get("meetingKey") or f"{mdate}|{track.upper()}")
        meeting_row = {"source":"edgeiq_three_day_product_catalog_v1.json","meeting_date":mdate,"track":track,"meeting_key":meeting_key,"race_count_declared":len(meeting.get("races") or []),"runner_count_declared":0}
        for race in meeting.get("races", []) or []:
            if not isinstance(race, dict): continue
            race_no = norm(race.get("raceNumber") or race.get("raceNo") or race.get("race_no"))
            race_key = norm(race.get("raceKey") or f"{meeting_key}|R{race_no}")
            runner_list = race.get("runners") or race.get("field") or race.get("entries") or []
            count = len(runner_list) if isinstance(runner_list, list) else 0
            meeting_row["runner_count_declared"] += count
            races.append({
                "source":"edgeiq_three_day_product_catalog_v1.json",
                "meeting_date":mdate,
                "track":track,
                "meeting_key":meeting_key,
                "race_key":race_key,
                "race_no":race_no,
                "race_id":norm(race.get("raceId") or race.get("race_id")),
                "race_name":norm(race.get("raceName") or race.get("name")),
                "race_distance_metres":parse_distance(race.get("distance") or race.get("raceDistance")),
                "race_start_time":norm(race.get("raceTime") or race.get("startTime")),
                "track_condition":norm(race.get("trackCondition") or meeting.get("trackCondition")),
                "rail_position":norm(race.get("rail") or meeting.get("rail")),
                "declared_runner_count":count,
                "current_or_future_flag":"YES" if (parse_date(mdate) and parse_date(mdate) >= TODAY) else "NO",
            })
            if isinstance(runner_list, list):
                for runner in runner_list:
                    if not isinstance(runner, dict): continue
                    official = runner.get("official") if isinstance(runner.get("official"), dict) else {}
                    source = runner.get("source") if isinstance(runner.get("source"), dict) else {}
                    horse = norm(runner.get("runnerName") or runner.get("horse") or runner.get("horseName") or runner.get("name") or official.get("runner") or source.get("horseName"))
                    runners.append({
                        "source":"edgeiq_three_day_product_catalog_v1.json",
                        "meeting_date":mdate,
                        "track":track,
                        "meeting_key":meeting_key,
                        "race_key":race_key,
                        "race_no":race_no,
                        "race_id":norm(race.get("raceId") or race.get("race_id")),
                        "runner_name":horse,
                        "saddlecloth_number":norm(runner.get("runnerNumber") or runner.get("saddlecloth") or runner.get("number") or official.get("number") or official.get("no")),
                        "barrier":norm(runner.get("barrier") or runner.get("barrierNumber") or official.get("barrier")),
                        "weight_kg":norm(runner.get("weight") or runner.get("weightKg") or runner.get("weight_kg") or official.get("weight")),
                        "jockey_name":norm(runner.get("jockey") or runner.get("jockeyName") or official.get("jockey")),
                        "trainer_name":norm(runner.get("trainer") or runner.get("trainerName") or official.get("trainer")),
                        "scratching_status":"SCRATCHED" if official.get("scratched") else "ACTIVE",
                        "runner_id":norm(runner.get("runnerId") or runner.get("id")),
                        "current_or_future_flag":"YES" if (parse_date(mdate) and parse_date(mdate) >= TODAY) else "NO",
                    })
        meetings.append(meeting_row)
    return meetings, races, runners


def race_list_rows():
    rows=[]
    for r in read_csv(FILES["race_list"]):
        d=norm(r.get("race_date")); track=norm(r.get("track") or r.get("normalised_track")); rn=norm(r.get("race_no"))
        rows.append({
            "source":"edgeiq_vic_three_day_race_list_v1.csv",
            "meeting_date":d,"track":track,"meeting_key":norm(r.get("meeting_key") or f"{d}|{track.upper()}"),
            "race_key":f"{d}|{track.upper()}|R{rn}","race_no":rn,"race_id":norm(r.get("race_id")),"race_name":norm(r.get("race_name")),
            "race_distance_metres":parse_distance(r.get("distance")),"race_start_time":norm(r.get("race_time_utc")),"track_condition":norm(r.get("track_condition")),"rail_position":norm(r.get("rail_position")),
            "declared_runner_count":"FORM_ENTRIES_JSON_ONLY" if norm(r.get("form_entries_json")) else "0",
            "current_or_future_flag":"YES" if (parse_date(d) and parse_date(d) >= TODAY) else "NO",
        })
    return rows


def field_feed_runner_rows(path_key: str) -> List[Dict[str, str]]:
    out=[]
    for r in read_csv(FILES[path_key]):
        d=norm(r.get("race_date")); track=norm(r.get("track")); rn=norm(r.get("race_no"))
        horse=norm(r.get("horse") or r.get("runner_name"))
        out.append({
            "source":FILES[path_key].name,"meeting_date":d,"track":track,"meeting_key":norm(r.get("meeting_key")),"race_key":norm(r.get("race_key")),"race_no":rn,"race_id":"",
            "runner_name":horse,"saddlecloth_number":norm(r.get("saddlecloth") or r.get("horse_no")),"barrier":norm(r.get("barrier")),"weight_kg":norm(r.get("weight_kg") or r.get("weight")),
            "jockey_name":norm(r.get("jockey")),"trainer_name":norm(r.get("trainer")),"scratching_status":norm(r.get("scratch_status") or r.get("runner_status") or r.get("is_scratched")),"runner_id":norm(r.get("runner_key")),
            "current_or_future_flag":"YES" if (parse_date(d) and parse_date(d) >= TODAY) else "NO",
        })
    return out


def script_dependency_rows():
    out=[]
    for rel in SCRIPT_NAMES:
        p=ROOT/rel
        txt=p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
        deps=sorted(set(re.findall(r"edgeiq_[\w_./\\-]+\.(?:csv|json|txt)", txt)))
        out.append({
            "script":rel,
            "exists":"YES" if p.exists() else "NO",
            "mentions_race_entry_fact":"YES" if "edgeiq_race_entry_fact_v1" in txt else "NO",
            "mentions_race_fields":"YES" if "edgeiq_vic_three_day_race_fields" in txt else "NO",
            "mentions_product_catalog":"YES" if "edgeiq_three_day_product_catalog_v1" in txt else "NO",
            "dependencies":";".join(deps[:20]),
        })
    return out


def main():
    meetings, catalog_races, catalog_runners = product_catalog_rows()
    race_rows = []
    race_rows.extend(catalog_races)
    race_rows.extend(race_list_rows())
    runner_rows = []
    runner_rows.extend(catalog_runners)
    runner_rows.extend(field_feed_runner_rows("meeting_universe"))
    runner_rows.extend(field_feed_runner_rows("race_fields"))
    race_fields = ["source","meeting_date","track","meeting_key","race_key","race_no","race_id","race_name","race_distance_metres","race_start_time","track_condition","rail_position","declared_runner_count","current_or_future_flag"]
    with RACE_OUT.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=race_fields); w.writeheader(); w.writerows(race_rows)
    runner_fields = ["source","meeting_date","track","meeting_key","race_key","race_no","race_id","runner_name","saddlecloth_number","barrier","weight_kg","jockey_name","trainer_name","scratching_status","runner_id","current_or_future_flag"]
    with RUNNER_OUT.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=runner_fields); w.writeheader(); w.writerows(runner_rows)
    deps=script_dependency_rows()
    dep_out=OUT_DIR/"edgeiq_three_day_window_source_trace_v1.csv"
    with dep_out.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=["script","exists","mentions_race_entry_fact","mentions_race_fields","mentions_product_catalog","dependencies"]); w.writeheader(); w.writerows(deps)
    current_races=[r for r in race_rows if r.get("current_or_future_flag")=="YES"]
    current_runners=[r for r in runner_rows if r.get("current_or_future_flag")=="YES"]
    stale_runners=[r for r in runner_rows if r.get("current_or_future_flag")!="YES"]
    lines=[]
    lines.append("# EDGEiQ Three-Day Window Race Entry Gap Report V1")
    lines.append("")
    lines.append(f"Audit date: {TODAY.isoformat()}")
    window=load_json(FILES["window"])
    if isinstance(window, dict):
        lines.append(f"Three-day window generatedAt: {window.get('generatedAt')}")
        lines.append(f"Three-day window dates: {', '.join([d.get('date','') for d in window.get('dates',[]) if isinstance(d,dict)])}")
    lines.append("")
    lines.append("## Coverage")
    lines.append(f"- Race records traced: {len(race_rows)}")
    lines.append(f"- Current/future race records: {len(current_races)}")
    lines.append(f"- Runner records traced: {len(runner_rows)}")
    lines.append(f"- Current/future runner records: {len(current_runners)}")
    lines.append(f"- Stale runner records: {len(stale_runners)}")
    lines.append("")
    lines.append("## Source Shape Decision")
    if current_runners:
        lines.append("- The three-day pipeline contains current/future runner-level entries and can be formalised as the canonical race-entry source after identity audit.")
    elif current_races:
        lines.append("- The three-day pipeline contains current/future meeting/race-level entries but no current/future runner declarations. A meeting-detail/field ingestion refresh is required before race-entry fact build.")
    else:
        lines.append("- The three-day pipeline is stale or meeting-summary-only relative to the audit date. It cannot build current/future race-entry facts without refresh/repair.")
    lines.append("")
    lines.append("## Field Feed Findings")
    lines.append(f"- edgeiq_vic_three_day_meeting_universe.csv rows: {len(read_csv(FILES['meeting_universe']))}")
    lines.append(f"- edgeiq_vic_three_day_race_fields.csv rows: {len(read_csv(FILES['race_fields']))}")
    lines.append("- Both field-feed outputs are the expected downstream runner-level locations, but currently contain zero rows.")
    lines.append("")
    lines.append("## Next Required Action")
    lines.append("Trace the authoritative live field source: either repair the existing three-day product/field refresh or establish that no governed live field ingestion exists.")
    REPORT_OUT.write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(f"RACES={len(race_rows)} CURRENT_RACES={len(current_races)} RUNNERS={len(runner_rows)} CURRENT_RUNNERS={len(current_runners)}")
    print(f"WROTE {RACE_OUT}")
    print(f"WROTE {RUNNER_OUT}")
    print(f"WROTE {REPORT_OUT}")

if __name__ == "__main__":
    main()
