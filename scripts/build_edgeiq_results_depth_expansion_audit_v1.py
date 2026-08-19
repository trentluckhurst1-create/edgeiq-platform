from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUTS = {
    "match_diag": DATA / "edgeiq_temporal_match_diagnostics_v1.csv",
    "validation": DATA / "edgeiq_temporal_physics_validation_v1.csv",
    "results_truth": DATA / "edgeiq_canonical_results_truth_v1.csv",
    "physics": DATA / "edgeiq_real_sectional_physics_features_v1.csv",
    "fields": DATA / "edgeiq_vic_three_day_race_fields.csv",
    "master_events": DATA / "master_result_events.csv",
    "results_history": DATA / "results_history_clean.csv",
    "ra_results": DATA / "ra_calendar_official_results.csv",
    "results_master": DATA / "edgeiq_results_master.csv",
}

OUT = DATA / "edgeiq_results_depth_expansion_audit_v1.csv"
SUMMARY = DATA / "edgeiq_results_depth_expansion_summary_v1.csv"
TARGETS = DATA / "edgeiq_results_backfill_targets_v1.csv"

AUDIT_FIELDS = [
    "race_date","track","race_no","temporal_rows","sectional_horses",
    "safe_result_horses","missing_safe_result_horses","coverage_rate",
    "coverage_grade","result_depth_status","likely_blocker",
    "recommended_repair","repair_priority","notes"
]

TARGET_FIELDS = [
    "priority","race_date","track","race_no","missing_safe_result_horses",
    "temporal_rows","coverage_rate","required_source",
    "recommended_backfill_action","notes"
]

def clean(v):
    s = str(v or "").strip()
    return "" if s.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"} else s

def norm_text(v):
    s = clean(v).upper()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("&", " AND ")
    s = re.sub(r"\([^)]*\)", " ", s)
    s = re.sub(r"['`’‘]", "", s)
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

TRACK_ALIASES = {
    "BET365 YARRA VALLEY": "YARRA VALLEY",
    "SPORTSBET WANGARATTA": "WANGARATTA",
    "SOUTHSIDE PAKENHAM": "PAKENHAM",
    "SPORTSBET PAKENHAM": "PAKENHAM",
    "PAKENHAM SYNTHETIC": "PAKENHAM",
    "BALLARAT SYNTHETIC": "BALLARAT",
    "GEELONG SYNTHETIC": "GEELONG",
    "THE VALLEY": "MOONEE VALLEY",
    "SANDOWN HILLSIDE": "SANDOWN",
    "SANDOWN LAKESIDE": "SANDOWN",
}

def norm_track(v):
    t = norm_text(v)
    t = re.sub(r"\bRACING\b|\bCLUB\b", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return TRACK_ALIASES.get(t, t)

def norm_date(v):
    s = clean(v).replace("/", "-")
    m = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", s)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    return s[:10]

def norm_race_no(v):
    m = re.search(r"\d+", clean(v))
    return str(int(m.group(0))) if m else ""

def horse_key(v):
    return norm_text(v)

def race_key(row):
    d = norm_date(row.get("race_date") or row.get("date") or row.get("meeting_date"))
    t = norm_track(row.get("track") or row.get("track_name") or row.get("meeting"))
    r = norm_race_no(row.get("race_no") or row.get("race_number") or row.get("race"))
    return f"{d}|{t}|{r}" if d and t and r else ""

def runner_key(row):
    rk = race_key(row)
    h = horse_key(row.get("horse") or row.get("horse_name") or row.get("runner_name") or row.get("sectional_runner"))
    return f"{rk}|{h}" if rk and h else ""

def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)

def grade(rate):
    if rate >= 0.90: return "A"
    if rate >= 0.70: return "B"
    if rate >= 0.40: return "C"
    if rate >= 0.10: return "D"
    return "F"

def status(g):
    return {
        "A": "FULLY_COVERED",
        "B": "PARTIALLY_COVERED",
        "C": "PARTIALLY_COVERED",
        "D": "LOW_COVERAGE",
        "F": "NO_SAFE_RESULTS",
    }[g]

def priority(temporal_rows, rate):
    if temporal_rows >= 8 and rate < 0.40:
        return "HIGH"
    if temporal_rows >= 5 and rate == 0:
        return "HIGH"
    if temporal_rows >= 3 and rate < 0.70:
        return "MEDIUM"
    return "LOW"

def main():
    missing = [p.name for p in INPUTS.values() if not p.exists()]

    validation = read_csv(INPUTS["validation"])
    results_truth = read_csv(INPUTS["results_truth"])

    temporal_by_race = defaultdict(set)
    temporal_rows_by_race = Counter()

    for r in validation:
        rk = race_key(r)
        h = horse_key(r.get("horse"))
        if rk:
            temporal_rows_by_race[rk] += 1
            if h:
                temporal_by_race[rk].add(h)

    safe_results_by_race = defaultdict(set)
    all_result_rows_by_race = defaultdict(list)

    for r in results_truth:
        rk = race_key(r)
        h = horse_key(r.get("horse"))
        if rk:
            all_result_rows_by_race[rk].append(r)
            if clean(r.get("safe_for_model_validation")).upper() == "YES" and clean(r.get("finish_position")) and h:
                safe_results_by_race[rk].add(h)

    event_sources = {
        "master_events": read_csv(INPUTS["master_events"]),
        "results_history": read_csv(INPUTS["results_history"]),
        "ra_results": read_csv(INPUTS["ra_results"]),
        "results_master": read_csv(INPUTS["results_master"]),
    }

    event_races = defaultdict(set)
    for source, rows in event_sources.items():
        for r in rows:
            rk = race_key(r)
            if rk:
                event_races[rk].add(source)

    audit = []

    for rk, horses in sorted(temporal_by_race.items()):
        parts = rk.split("|")
        if len(parts) != 3:
            continue
        race_date, track, race_no = parts

        safe_horses = safe_results_by_race.get(rk, set())
        missing_horses = sorted(horses - safe_horses)

        temporal_rows = temporal_rows_by_race[rk]
        rate = len(safe_horses & horses) / len(horses) if horses else 0.0
        g = grade(rate)
        pr = priority(temporal_rows, rate)

        event_exists = rk in event_races
        result_rows_exist = len(all_result_rows_by_race.get(rk, [])) > 0

        if rate >= 0.90:
            blocker = "NONE"
            repair = "No immediate action required."
        elif result_rows_exist:
            blocker = "RESULT_SOURCE_EXISTS_BUT_NO_FINISH_POSITION"
            repair = "Inspect result source rows and extract settled finish positions into canonical results truth."
        elif event_exists:
            blocker = "RESULT_SOURCE_EXISTS_BUT_NO_FINISH_POSITION"
            repair = "Backfill runner-level official placings from existing race event source."
        else:
            blocker = "RESULT_RACE_EVENT_MISSING"
            repair = "Fetch/backfill official result event and runner placings for this race."

        audit.append({
            "race_date": race_date,
            "track": track,
            "race_no": race_no,
            "temporal_rows": temporal_rows,
            "sectional_horses": len(horses),
            "safe_result_horses": len(safe_horses & horses),
            "missing_safe_result_horses": len(missing_horses),
            "coverage_rate": round(rate, 4),
            "coverage_grade": g,
            "result_depth_status": status(g),
            "likely_blocker": blocker,
            "recommended_repair": repair,
            "repair_priority": pr,
            "notes": "Missing horses: " + ";".join(missing_horses[:20]),
        })

    targets = []
    for r in audit:
        if r["repair_priority"] == "LOW" and r["coverage_grade"] in {"A", "B"}:
            continue
        targets.append({
            "priority": r["repair_priority"],
            "race_date": r["race_date"],
            "track": r["track"],
            "race_no": r["race_no"],
            "missing_safe_result_horses": r["missing_safe_result_horses"],
            "temporal_rows": r["temporal_rows"],
            "coverage_rate": r["coverage_rate"],
            "required_source": "official settled race results / canonical results truth",
            "recommended_backfill_action": r["recommended_repair"],
            "notes": r["notes"],
        })

    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    targets.sort(key=lambda x: (order.get(x["priority"], 9), -int(x["temporal_rows"])))

    avg_rate = sum(float(r["coverage_rate"]) for r in audit) / len(audit) if audit else 0
    summary = [
        {"metric": "race_rows", "value": len(audit)},
        {"metric": "high_priority_targets", "value": sum(1 for r in targets if r["priority"] == "HIGH")},
        {"metric": "medium_priority_targets", "value": sum(1 for r in targets if r["priority"] == "MEDIUM")},
        {"metric": "low_priority_targets", "value": sum(1 for r in targets if r["priority"] == "LOW")},
        {"metric": "fully_covered_races", "value": sum(1 for r in audit if r["result_depth_status"] == "FULLY_COVERED")},
        {"metric": "no_safe_result_races", "value": sum(1 for r in audit if r["result_depth_status"] == "NO_SAFE_RESULTS")},
        {"metric": "partial_covered_races", "value": sum(1 for r in audit if r["result_depth_status"] == "PARTIALLY_COVERED")},
        {"metric": "average_coverage_rate", "value": round(avg_rate, 4)},
        {"metric": "total_temporal_rows", "value": sum(int(r["temporal_rows"]) for r in audit)},
        {"metric": "total_missing_safe_result_horses", "value": sum(int(r["missing_safe_result_horses"]) for r in audit)},
        {"metric": "research_pipeline_offline_only", "value": "YES"},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
    ]

    for m in missing:
        summary.append({"metric": f"missing_input::{m}", "value": "YES"})

    write_csv(OUT, audit, AUDIT_FIELDS)
    write_csv(TARGETS, targets, TARGET_FIELDS)
    write_csv(SUMMARY, summary, ["metric", "value"])

    print("=" * 88)
    print("EDGEIQ RESULTS DEPTH EXPANSION AUDIT V1")
    print("=" * 88)
    print(f"race rows: {len(audit)}")
    print(f"targets: {len(targets)}")
    print(f"high priority targets: {sum(1 for r in targets if r['priority'] == 'HIGH')}")
    print(f"average coverage rate: {avg_rate:.4f}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {TARGETS}")

if __name__ == "__main__":
    main()
