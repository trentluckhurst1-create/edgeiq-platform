import csv, re, unicodedata
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path("public/data")

VALIDATION = DATA / "edgeiq_temporal_physics_validation_v1.csv"
TRUTH = DATA / "edgeiq_canonical_results_truth_v1.csv"

OUT = DATA / "edgeiq_temporal_direct_result_backfill_targets_v1.csv"
SUMMARY = DATA / "edgeiq_temporal_direct_result_backfill_summary_v1.csv"

def clean(v):
    s = str(v or "").strip()
    return "" if s.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"} else s

def norm(v):
    s = clean(v).upper()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"['`’‘]", "", s)
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def date(v):
    s = clean(v).replace("/", "-")
    m = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", s)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    return s[:10]

def race(v):
    m = re.search(r"\d+", clean(v))
    return str(int(m.group(0))) if m else ""

def track(v):
    t = norm(v)
    aliases = {
        "THE VALLEY": "MOONEE VALLEY",
        "SPORTSBET PAKENHAM": "PAKENHAM",
        "SOUTHSIDE PAKENHAM": "PAKENHAM",
        "PAKENHAM SYNTHETIC": "PAKENHAM",
        "BET365 YARRA VALLEY": "YARRA VALLEY",
        "SPORTSBET WANGARATTA": "WANGARATTA",
        "SANDOWN HILLSIDE": "SANDOWN",
        "SANDOWN LAKESIDE": "SANDOWN",
    }
    return aliases.get(t, t)

def race_key(row):
    d = date(row.get("race_date") or row.get("date") or row.get("meeting_date"))
    t = track(row.get("track") or row.get("track_name") or row.get("meeting"))
    r = race(row.get("race_no") or row.get("race_number") or row.get("race"))
    return f"{d}|{t}|{r}" if d and t and r else ""

def runner_key(row):
    rk = race_key(row)
    h = norm(row.get("horse") or row.get("horse_name") or row.get("runner_name") or row.get("results_runner"))
    return f"{rk}|{h}" if rk and h else ""

def read(p):
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

validation = read(VALIDATION)
truth = read(TRUTH)

safe_truth_keys = {
    runner_key(r) for r in truth
    if runner_key(r) and clean(r.get("safe_for_model_validation")).upper() == "YES" and clean(r.get("finish_position"))
}

by_race = defaultdict(lambda: {"rows": 0, "horses": set(), "matched": set(), "missing": set()})

for r in validation:
    rk = race_key(r)
    h = norm(r.get("horse"))
    k = runner_key(r)
    if not rk or not h:
        continue
    by_race[rk]["rows"] += 1
    by_race[rk]["horses"].add(h)
    if k in safe_truth_keys or clean(r.get("finish_position")):
        by_race[rk]["matched"].add(h)
    else:
        by_race[rk]["missing"].add(h)

rows = []
for rk, d in by_race.items():
    race_date, trk, rn = rk.split("|")
    horses = d["horses"]
    matched = d["matched"]
    missing = horses - matched
    coverage = len(matched) / len(horses) if horses else 0
    if not missing:
        continue
    priority = "HIGH" if d["rows"] >= 8 and coverage < 0.5 else "MEDIUM" if d["rows"] >= 3 else "LOW"
    rows.append({
        "priority": priority,
        "race_date": race_date,
        "track": trk,
        "race_no": rn,
        "temporal_rows": d["rows"],
        "temporal_horses": len(horses),
        "safe_result_horses": len(matched),
        "missing_horses": len(missing),
        "coverage_rate": round(coverage, 4),
        "missing_horse_list": ";".join(sorted(missing)[:30]),
        "required_source": "official settled result runner placings for exact temporal race",
        "recommended_action": "Backfill official result for this exact temporal validation race.",
    })

rows.sort(key=lambda r: ({"HIGH":0,"MEDIUM":1,"LOW":2}[r["priority"]], -int(r["temporal_rows"])))

with OUT.open("w", encoding="utf-8", newline="") as f:
    fields = ["priority","race_date","track","race_no","temporal_rows","temporal_horses","safe_result_horses","missing_horses","coverage_rate","missing_horse_list","required_source","recommended_action"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

summary = [
    {"metric": "temporal_races_total", "value": len(by_race)},
    {"metric": "target_races", "value": len(rows)},
    {"metric": "high_priority_targets", "value": sum(1 for r in rows if r["priority"] == "HIGH")},
    {"metric": "medium_priority_targets", "value": sum(1 for r in rows if r["priority"] == "MEDIUM")},
    {"metric": "low_priority_targets", "value": sum(1 for r in rows if r["priority"] == "LOW")},
    {"metric": "total_temporal_rows_in_targets", "value": sum(int(r["temporal_rows"]) for r in rows)},
    {"metric": "total_missing_horses", "value": sum(int(r["missing_horses"]) for r in rows)},
]

with SUMMARY.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["metric","value"])
    w.writeheader()
    w.writerows(summary)

print("="*80)
print("TEMPORAL DIRECT RESULT BACKFILL TARGETS V1")
print("="*80)
print(f"temporal races total: {len(by_race)}")
print(f"target races: {len(rows)}")
print(f"high priority: {sum(1 for r in rows if r['priority']=='HIGH')}")
print(f"total missing horses: {sum(int(r['missing_horses']) for r in rows)}")
print(f"saved: {OUT}")
print(f"saved: {SUMMARY}")
