from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

TARGETS = DATA / "edgeiq_results_backfill_targets_v1.csv"
OUT = DATA / "edgeiq_official_results_backfill_v1.csv"
SUMMARY = DATA / "edgeiq_official_results_backfill_summary_v1.csv"
FAILURES = DATA / "edgeiq_official_results_backfill_failures_v1.csv"

SOURCES = [
    DATA / "ra_calendar_official_results.csv",
    DATA / "results_history_clean.csv",
    DATA / "master_result_events.csv",
    DATA / "edgeiq_results_master.csv",
    DATA / "race_results.csv",
    DATA / "model_result_review.csv",
    DATA / "edgeiq_results_truth_loop.csv",
    DATA / "edgeiq_results_auto_settlement.csv",
]

OUT_FIELDS = [
    "race_date","track","race_no","horse","finish_position","result_status",
    "result_source","backfill_confidence","canonical_runner_key",
    "safe_for_model_validation","notes"
]

FAIL_FIELDS = [
    "race_date","track","race_no","failure_reason","sources_checked",
    "recommended_next_step","notes"
]

def clean(v):
    s = str(v or "").strip()
    return "" if s.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"} else s

def norm(v):
    s = clean(v).upper()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("&", " AND ")
    s = re.sub(r"\([^)]*\)", " ", s)
    s = re.sub(r"['`’‘]", "", s)
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

TRACK_ALIASES = {
    "THE VALLEY": "MOONEE VALLEY",
    "SPORTSBET PAKENHAM": "PAKENHAM",
    "SOUTHSIDE PAKENHAM": "PAKENHAM",
    "PAKENHAM SYNTHETIC": "PAKENHAM",
    "BET365 YARRA VALLEY": "YARRA VALLEY",
    "SPORTSBET WANGARATTA": "WANGARATTA",
    "BALLARAT SYNTHETIC": "BALLARAT",
    "GEELONG SYNTHETIC": "GEELONG",
    "SANDOWN HILLSIDE": "SANDOWN",
    "SANDOWN LAKESIDE": "SANDOWN",
}

def norm_track(v):
    t = norm(v)
    t = re.sub(r"\bRACING\b|\bCLUB\b", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return TRACK_ALIASES.get(t, t)

def norm_date(v):
    s = clean(v).replace("/", "-")
    m = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", s)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    m = re.search(r"(\d{1,2})-(\d{1,2})-(20\d{2})", s)
    if m:
        d, mo, y = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    return s[:10]

def norm_race(v):
    m = re.search(r"\d+", clean(v))
    return str(int(m.group(0))) if m else ""

def horse_key(v):
    return norm(v)

def race_key(row):
    d = norm_date(row.get("race_date") or row.get("date") or row.get("meeting_date") or row.get("date_k"))
    t = norm_track(row.get("track") or row.get("track_name") or row.get("meeting") or row.get("track_k"))
    r = norm_race(row.get("race_no") or row.get("race_number") or row.get("race") or row.get("race_k"))
    return f"{d}|{t}|{r}" if d and t and r else ""

def runner_key(d, t, r, h):
    hk = horse_key(h)
    return f"{d}|{t}|{r}|{hk}" if d and t and r and hk else ""

def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path, rows, fields):
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)

def first(row, names):
    for n in names:
        v = clean(row.get(n))
        if v:
            return v
    return ""

def extract_finish(row):
    fields = [
        "finish_position","position","place","placing","result","finishing_position",
        "finish","rank","fin_pos","official_position","settled_position",
        "finish_pos","finish_pos_num"
    ]
    joined = " ".join(clean(row.get(x)) for x in ["result_status","status","result","finish","finish_pos"])
    j = norm(joined)
    if any(x in j.split() for x in ["SCR", "SCRATCHED", "SCRATCHING"]):
        return "", "SCRATCHED"
    for f in fields:
        raw = clean(row.get(f))
        if not raw:
            continue
        n = norm(raw)
        if n in {"WON", "WINNER", "WIN"}:
            return "1", "RESULTED"
        if any(x in n.split() for x in ["SCR", "SCRATCHED", "SCRATCHING"]):
            return "", "SCRATCHED"
        m = re.search(r"\d+", raw)
        if m:
            pos = int(m.group(0))
            if 0 < pos < 40:
                return str(pos), "RESULTED"
    return "", "PENDING_OR_NO_POSITION"

def canonical_source_row(row, source):
    d = norm_date(first(row, ["race_date","date","meeting_date","date_k"]))
    t = norm_track(first(row, ["track","track_name","meeting","track_k"]))
    r = norm_race(first(row, ["race_no","race_number","race","race_k"]))
    h = first(row, ["horse","horse_name","runner","runner_name","results_runner","market_runner","selection_name"])
    key = clean(row.get("canonical_runner_key"))
    if key and "|" in key and not all([d,t,r,h]):
        parts = key.split("|")
        if len(parts) >= 4:
            d = d or parts[0]
            t = t or parts[1]
            r = r or parts[2]
            h = h or parts[3]
    if not all([d,t,r,h]):
        return None
    finish, status = extract_finish(row)
    return {
        "race_date": d,
        "track": t,
        "race_no": r,
        "horse": h,
        "finish_position": finish,
        "result_status": status,
        "result_source": source,
        "canonical_runner_key": runner_key(d,t,r,h),
        "safe_for_model_validation": "YES" if finish else "NO",
    }

def main():
    targets = read_csv(TARGETS)
    target_races = set()
    for row in targets:
        d = norm_date(row.get("race_date"))
        t = norm_track(row.get("track"))
        r = norm_race(row.get("race_no"))
        if d and t and r:
            target_races.add(f"{d}|{t}|{r}")

    candidates = defaultdict(list)
    sources_checked = []

    for path in SOURCES:
        if not path.exists():
            continue
        sources_checked.append(path.name)
        for raw in read_csv(path):
            c = canonical_source_row(raw, path.name)
            if not c:
                continue
            rk = f"{c['race_date']}|{c['track']}|{c['race_no']}"
            if rk in target_races:
                candidates[c["canonical_runner_key"]].append(c)

    out = []
    for key, rows in candidates.items():
        rows = sorted(rows, key=lambda r: (1 if r["finish_position"] else 0, r["result_source"]), reverse=True)
        best = rows[0]
        if not best["finish_position"]:
            continue
        best["backfill_confidence"] = "HIGH" if best["result_source"] in {"ra_calendar_official_results.csv","results_history_clean.csv"} else "MEDIUM"
        best["notes"] = "Backfilled from local result source only. No inferred placings."
        out.append(best)

    covered_races = {f"{r['race_date']}|{r['track']}|{r['race_no']}" for r in out}
    failures = []
    for rk in sorted(target_races - covered_races):
        d,t,r = rk.split("|")
        failures.append({
            "race_date": d,
            "track": t,
            "race_no": r,
            "failure_reason": "NO_LOCAL_FINISH_POSITION_SOURCE_FOUND",
            "sources_checked": "|".join(sources_checked),
            "recommended_next_step": "Fetch official race result page/API for this race and extract runner placings.",
            "notes": "Local sweep found no settled runner finish positions for target race.",
        })

    summary = [
        {"metric": "target_races", "value": len(target_races)},
        {"metric": "races_backfilled", "value": len(covered_races)},
        {"metric": "runner_results_backfilled", "value": len(out)},
        {"metric": "safe_for_model_validation_yes", "value": sum(1 for r in out if r["safe_for_model_validation"] == "YES")},
        {"metric": "failed_races", "value": len(failures)},
        {"metric": "still_missing_finish_positions", "value": len(failures)},
        {"metric": "research_pipeline_offline_only", "value": "YES"},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
    ]

    write_csv(OUT, out, OUT_FIELDS)
    write_csv(FAILURES, failures, FAIL_FIELDS)
    write_csv(SUMMARY, summary, ["metric","value"])

    print("=" * 88)
    print("EDGEIQ OFFICIAL RESULTS BACKFILL V1")
    print("=" * 88)
    print(f"target races: {len(target_races)}")
    print(f"races backfilled: {len(covered_races)}")
    print(f"runner results backfilled: {len(out)}")
    print(f"failed races: {len(failures)}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {FAILURES}")

if __name__ == "__main__":
    main()
