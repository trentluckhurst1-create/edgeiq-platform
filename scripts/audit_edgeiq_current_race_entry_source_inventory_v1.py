import csv
csv.field_size_limit(1024 * 1024 * 64)
import json
import re
import hashlib
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
TODAY = date.today()
OUT_DIR = ROOT / "docs" / "performance-intelligence" / "race-entry"
OUT_DIR.mkdir(parents=True, exist_ok=True)
INVENTORY_OUT = OUT_DIR / "edgeiq_current_race_entry_source_inventory_v1.csv"
CANDIDATE_OUT = OUT_DIR / "edgeiq_current_race_entry_candidate_sources_v1.csv"
DEPENDENCY_OUT = OUT_DIR / "edgeiq_current_race_entry_source_dependencies_v1.csv"
REPORT_OUT = OUT_DIR / "edgeiq_current_race_entry_source_inventory_report_v1.md"

SCAN_ROOTS = ["public/data", "data", "config", "contracts", "scripts", "outputs/performance-intelligence"]
KEYWORDS = re.compile(r"three[_ -]?day|meeting|race[_ -]?(entry|field|list|catalog|universe)|field|runner|form|accept|declaration|scratching|today|tomorrow|day", re.I)
LIVE_INCLUDE = re.compile(r"three_day|meeting_calendar|meeting_universe|race_fields|race_list|product_catalog|live_runner_board|form_guide_enriched|current_|scratch|racingcom_meeting_discovery|GetMeetsByMonth|race_entry", re.I)
LIVE_EXCLUDE = re.compile(r"historical|trainer|jockey|dna|sectional_profile|weight_ladder|predictive_value|calibration|backtest|checkpoint|backup|BEFORE|runner_history|entity_graph|metadata|trust_field|forecast|rank_validation|full_career|form_card_runs|standardised_sectionals", re.I)
DATE_RE = re.compile(r"(20\d{2})[-_/](\d{1,2})[-_/](\d{1,2})")
DATE_COLUMNS = ["race_date", "meeting_date", "date", "raceDate", "meetingDate", "run_date", "scheduled_date", "generatedAt", "built_at"]
TRACK_COLUMNS = ["track", "canonical_track", "track_name", "venue_name", "meeting", "meeting_name", "normalised_track"]
RACE_COLUMNS = ["race_no", "race_number", "raceNumber", "race", "race_id", "raceId", "raceKey", "race_key"]
RUNNER_COLUMNS = ["horse", "runner_name", "runnerName", "horse_name", "horseName", "runner", "runner_key", "runnerNumber"]
REQUIRED = {
    "meeting_date": ["meeting_date", "race_date", "date", "raceDate", "meetingDate"],
    "track": ["track", "canonical_track", "track_name", "venue_name", "meeting", "normalised_track"],
    "race_number": ["race_no", "race_number", "raceNumber"],
    "race_distance": ["distance", "race_distance", "race_distance_metres", "distance_metres"],
    "runner_name": ["horse", "runner_name", "runnerName", "horse_name", "horseName", "runner"],
    "barrier": ["barrier", "barrier_number"],
    "weight": ["weight", "weight_kg", "allocated_weight", "weight_carried"],
    "jockey": ["jockey", "jockey_name", "jockeyName"],
    "trainer": ["trainer", "trainer_name", "trainerName"],
    "status": ["runner_status", "scratch_status", "scratching_status", "is_scratched", "status", "declaration_status"],
}
IDENTITY = ["race_key", "raceKey", "runner_key", "runnerKey", "race_id", "raceId", "runner_id", "runnerId", "horse_code", "horseCode", "horse_key", "source_record_id", "meet_code", "track_code"]


def norm(v):
    return "" if v is None else str(v).strip()


def parse_date(v):
    s = norm(v)
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s).date()
    except Exception:
        pass
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except Exception:
            pass
    m = DATE_RE.search(s)
    if m:
        y, mo, d = map(int, m.groups())
        try:
            return date(y, mo, d)
        except Exception:
            return None
    return None


def first(row, aliases):
    lower = {str(k).lower(): k for k in row.keys()}
    for a in aliases:
        k = lower.get(a.lower())
        if k is not None and norm(row.get(k)):
            return norm(row.get(k))
    return ""


def init_stats(path, columns=None):
    cols = set(columns or [])
    return {
        "file": str(path.relative_to(ROOT)),
        "columns": cols,
        "row_count": 0,
        "dates": [],
        "races": set(),
        "runners": set(),
        "current_or_future_rows": 0,
    }


def add_row(stats, row):
    stats["row_count"] += 1
    stats["columns"].update(row.keys())
    d = parse_date(first(row, DATE_COLUMNS))
    if d:
        stats["dates"].append(d)
        if d >= TODAY:
            stats["current_or_future_rows"] += 1
    tr = first(row, TRACK_COLUMNS).upper()
    rn = first(row, RACE_COLUMNS)
    horse = first(row, RUNNER_COLUMNS).upper()
    if d or tr or rn:
        stats["races"].add((d.isoformat() if d else "", tr, rn))
    if horse:
        stats["runners"].add((d.isoformat() if d else "", tr, rn, horse))


def product_catalog_rows(obj):
    if not isinstance(obj, dict):
        return []
    out = []
    for meeting in obj.get("meetings", []) or []:
        if not isinstance(meeting, dict):
            continue
        mdate = meeting.get("date") or meeting.get("meetingDate") or ""
        track = meeting.get("meeting") or meeting.get("track") or meeting.get("trackName") or ""
        for race in meeting.get("races", []) or []:
            if not isinstance(race, dict):
                continue
            base = {
                "meeting_date": mdate,
                "race_date": race.get("raceDate") or mdate,
                "track": race.get("track") or track,
                "race_no": race.get("raceNumber") or race.get("raceNo") or race.get("race_no") or "",
                "race_name": race.get("raceName") or race.get("name") or "",
                "distance": race.get("distance") or race.get("raceDistance") or "",
                "race_time": race.get("raceTime") or race.get("startTime") or "",
                "race_key": race.get("raceKey") or "",
                "race_id": race.get("raceId") or race.get("race_id") or "",
                "track_condition": race.get("trackCondition") or meeting.get("trackCondition") or "",
                "rail_position": race.get("rail") or meeting.get("rail") or "",
            }
            runners = race.get("runners") or race.get("field") or race.get("entries") or []
            if isinstance(runners, list) and runners:
                for runner in runners:
                    if not isinstance(runner, dict): continue
                    official = runner.get("official") if isinstance(runner.get("official"), dict) else {}
                    source = runner.get("source") if isinstance(runner.get("source"), dict) else {}
                    row = dict(base)
                    row.update({
                        "runner_name": runner.get("runnerName") or runner.get("horse") or runner.get("horseName") or runner.get("name") or official.get("runner") or source.get("horseName") or "",
                        "horse": runner.get("horse") or runner.get("runnerName") or runner.get("horseName") or runner.get("name") or official.get("runner") or source.get("horseName") or "",
                        "runner_number": runner.get("runnerNumber") or runner.get("saddlecloth") or runner.get("number") or official.get("number") or official.get("no") or "",
                        "barrier": runner.get("barrier") or runner.get("barrierNumber") or official.get("barrier") or "",
                        "weight": runner.get("weight") or runner.get("weightKg") or runner.get("weight_kg") or official.get("weight") or "",
                        "jockey": runner.get("jockey") or runner.get("jockeyName") or official.get("jockey") or "",
                        "trainer": runner.get("trainer") or runner.get("trainerName") or official.get("trainer") or "",
                        "runner_status": runner.get("status") or runner.get("runnerStatus") or runner.get("scratchingStatus") or ("SCRATCHED" if official.get("scratched") else "ACTIVE") or "",
                        "runner_key": runner.get("runnerKey") or "",
                        "source_record_id": runner.get("runnerId") or runner.get("id") or "",
                    })
                    out.append(row)
            else:
                out.append(base)
    return out


def scan_csv(path):
    try:
        with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            stats = init_stats(path, reader.fieldnames or [])
            for row in reader:
                add_row(stats, row)
        return stats
    except Exception:
        return init_stats(path, [])


def scan_json(path):
    stats = init_stats(path, [])
    if path.stat().st_size > 15_000_000:
        return stats
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except Exception:
        return stats
    if path.name == "edgeiq_three_day_product_catalog_v1.json" or (isinstance(obj, dict) and "meetings" in obj):
        rows = product_catalog_rows(obj)
    elif isinstance(obj, list):
        rows = [r for r in obj if isinstance(r, dict)]
    elif isinstance(obj, dict) and "dates" in obj and isinstance(obj["dates"], list):
        rows = [r for r in obj["dates"] if isinstance(r, dict)]
        root_row = {k: v for k, v in obj.items() if not isinstance(v, (list, dict))}
        if root_row: rows.append(root_row)
    elif isinstance(obj, dict):
        rows = [{k: v for k, v in obj.items() if not isinstance(v, (list, dict))}]
    else:
        rows = []
    for row in rows:
        add_row(stats, row)
    return stats


def scan_text_dates(path):
    stats = init_stats(path, [])
    if path.stat().st_size > 3_000_000:
        return stats
    try:
        txt = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return stats
    for y, m, d in DATE_RE.findall(txt[:500000])[:2000]:
        add_row(stats, {"date": f"{y}-{int(m):02d}-{int(d):02d}"})
    return stats


def source_type(path, cols):
    name = path.name.lower(); joined = " ".join(cols).lower()
    if "results" in name or "historical_results" in name:
        return "RESULTS_ONLY_OR_HISTORICAL"
    if "three_day_product_catalog" in name:
        return "THREE_DAY_PRODUCT_CATALOG"
    if "three_day_race_list" in name:
        return "THREE_DAY_RACE_CATALOG"
    if "three_day_race_fields" in name or "meeting_universe" in name:
        return "THREE_DAY_FIELD_FEED"
    if "live_runner_board" in name:
        return "LIVE_RUNNER_BOARD"
    if "form_guide" in name:
        return "FORM_GUIDE_FEED"
    if "meeting" in name:
        return "MEETING_CATALOGUE"
    if "runner" in name or any(c.lower() in joined for c in RUNNER_COLUMNS):
        return "RUNNER_FIELD_CANDIDATE"
    if "race" in name:
        return "RACE_CATALOGUE"
    return "UNCLASSIFIED_CANDIDATE"


def classify(stype, current_rows, runner_count, req, path):
    lname = path.name.lower()
    if "result" in lname or stype == "RESULTS_ONLY_OR_HISTORICAL":
        return "RESULTS_ONLY"
    if current_rows <= 0:
        if "historical" in lname:
            return "HISTORICAL_ONLY"
        return "STALE_SOURCE"
    if runner_count > 0 and len(req) >= 8:
        return "ACTIVE_GOVERNED_SOURCE"
    if current_rows > 0 and (runner_count > 0 or len(req) >= 3):
        return "ACTIVE_BUT_INCOMPLETE"
    return "UNSUPPORTED_CANDIDATE"


def sha(path):
    if path.stat().st_size > 5_000_000: return "SKIPPED_LARGE_FILE"
    h=hashlib.sha256(); h.update(path.read_bytes()); return h.hexdigest()


def candidate_paths():
    paths=[]
    for sr in SCAN_ROOTS:
        base=ROOT/sr
        if not base.exists(): continue
        for p in base.rglob("*"):
            if not p.is_file(): continue
            if any(part.lower() in {"__pycache__", "checkpoints", "screenshots"} for part in p.relative_to(ROOT).parts): continue
            if p.suffix.lower() not in {".csv", ".json", ".txt", ".md", ".py"}: continue
            rel=str(p.relative_to(ROOT))
            name=p.name
            if p.suffix.lower() in {".csv", ".json"}:
                if LIVE_INCLUDE.search(rel) and not LIVE_EXCLUDE.search(name):
                    paths.append(p)
            else:
                if KEYWORDS.search(rel) and (LIVE_INCLUDE.search(rel) or str(p.relative_to(ROOT)).startswith("scripts")) and not LIVE_EXCLUDE.search(name):
                    paths.append(p)
    return sorted(set(paths), key=lambda p: str(p.relative_to(ROOT)).lower())


def final_row(path, stats):
    cols=stats["columns"]
    req=[name for name, aliases in REQUIRED.items() if any(a.lower() in {c.lower() for c in cols} for a in aliases)]
    identities=[c for c in cols if c.lower() in {a.lower() for a in IDENTITY}]
    st=source_type(path, cols)
    min_d=min(stats["dates"]).isoformat() if stats["dates"] else ""
    max_d=max(stats["dates"]).isoformat() if stats["dates"] else ""
    status=classify(st, stats["current_or_future_rows"], len(stats["runners"]), req, path)
    if stats["current_or_future_rows"]:
        freshness=f"CURRENT_OR_FUTURE_RELATIVE_TO_{TODAY.isoformat()}"
    elif max_d:
        freshness=f"STALE_MAX_{max_d}_RELATIVE_TO_{TODAY.isoformat()}"
    else:
        freshness="NO_DATE_EVIDENCE"
    # Consumer dependencies are emitted separately in edgeiq_current_race_entry_source_dependencies_v1.csv.
    consumers=[]
    return {
        "file": str(path.relative_to(ROOT)),
        "source_type": st,
        "row_count": stats["row_count"],
        "race_count": len(stats["races"]),
        "runner_count": len(stats["runners"]),
        "minimum_date": min_d,
        "maximum_date": max_d,
        "current_or_future_rows": stats["current_or_future_rows"],
        "required_fields_present": ";".join(req),
        "canonical_identity_coverage": f"{len(identities)} identity cols; {len(req)}/{len(REQUIRED)} required groups",
        "source_freshness": freshness,
        "governance_status": status,
        "consumer_status": ";".join(sorted(consumers)[:12]),
        "selected_candidate_reason": reason(status, stats["current_or_future_rows"], len(stats["runners"]), len(req)),
        "sha256": sha(path),
    }


def reason(status, cur, runners, reqn):
    if status == "ACTIVE_GOVERNED_SOURCE": return "Current/future runner-level rows with core field/declaration columns."
    if status == "ACTIVE_BUT_INCOMPLETE": return f"Current/future evidence but incomplete canonical coverage runners={runners} required_groups={reqn}."
    if status == "RESULTS_ONLY": return "Result-derived/historical source quarantined for target entry creation."
    if status == "STALE_SOURCE": return "No current/future rows relative to audit date."
    return "Unsupported as canonical live entry source."


def main():
    rows=[]; deps=[]
    for path in candidate_paths():
        suf=path.suffix.lower()
        if suf==".csv": stats=scan_csv(path)
        elif suf==".json": stats=scan_json(path)
        elif suf==".py":
            stats=scan_text_dates(path)
            try: txt=path.read_text(encoding="utf-8", errors="replace")
            except Exception: txt=""
            for dep in sorted(set(re.findall(r"[\w./\\-]*edgeiq_[\w./\\-]+\.(?:csv|json|txt)", txt))):
                deps.append({"script":str(path.relative_to(ROOT)),"dependency":dep.replace('\\','/'),"dependency_exists":str((ROOT/dep).exists() or (ROOT/dep.replace('/','\\')).exists()),"mentions_three_day":str(bool(re.search(r"three[_ -]?day|meeting|race|field|form", dep, re.I)))})
        else: stats=scan_text_dates(path)
        rows.append(final_row(path, stats))
    fields=["file","source_type","row_count","race_count","runner_count","minimum_date","maximum_date","current_or_future_rows","required_fields_present","canonical_identity_coverage","source_freshness","governance_status","consumer_status","selected_candidate_reason","sha256"]
    with INVENTORY_OUT.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    candidates=[r for r in rows if r['governance_status'] in {'ACTIVE_GOVERNED_SOURCE','ACTIVE_BUT_INCOMPLETE'} or int(r['current_or_future_rows'] or 0)>0]
    candidates.sort(key=lambda r:(r['governance_status']!='ACTIVE_GOVERNED_SOURCE', -int(r['runner_count'] or 0), -int(r['current_or_future_rows'] or 0)))
    with CANDIDATE_OUT.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(candidates)
    dep_fields=["script","dependency","dependency_exists","mentions_three_day"]
    with DEPENDENCY_OUT.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=dep_fields); w.writeheader(); w.writerows(deps)
    counts={}
    for r in rows: counts[r['governance_status']]=counts.get(r['governance_status'],0)+1
    best=candidates[0] if candidates else None
    lines=["# EDGEiQ Current Race-Entry Source Inventory V1", "", f"Audit date: {TODAY.isoformat()}", f"Files inventoried: {len(rows)}", "", "## Governance Classification Counts"]
    for k in sorted(counts): lines.append(f"- {k}: {counts[k]}")
    lines += ["", "## Best Current/Future Candidate"]
    if best:
        lines += [f"- File: `{best['file']}`", f"- Status: {best['governance_status']}", f"- Type: {best['source_type']}", f"- Rows: {best['row_count']}", f"- Races: {best['race_count']}", f"- Runners: {best['runner_count']}", f"- Date range: {best['minimum_date']} to {best['maximum_date']}", f"- Current/future rows: {best['current_or_future_rows']}", f"- Reason: {best['selected_candidate_reason']}"]
    else:
        lines.append("No current/future candidate source found.")
    lines += ["", "## Governance Notes", "- Results-only and historical sources are inventoried but blocked for target race-entry creation.", "- Stale race-entry-shaped files remain classified as stale and are not eligible for canonical live race-entry fact promotion.", "- Candidate selection requires current/future dates relative to the audit date and runner-level declaration fields."]
    REPORT_OUT.write_text("\n".join(lines)+"\n", encoding='utf-8')
    print(f"FILES={len(rows)} CANDIDATES={len(candidates)} BEST={(best or {}).get('file','NONE')}")

if __name__ == '__main__': main()
