import csv, re, unicodedata
from pathlib import Path

DATA = Path("public/data")

BACKFILL = DATA / "edgeiq_official_results_backfill_v1.csv"
VALIDATION = DATA / "edgeiq_temporal_physics_validation_v1.csv"
TRUTH = DATA / "edgeiq_canonical_results_truth_v1.csv"

OUT = DATA / "edgeiq_backfill_to_temporal_key_audit_v1.csv"

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

def key(row):
    d = date(row.get("race_date") or row.get("date") or row.get("meeting_date"))
    t = track(row.get("track") or row.get("track_name") or row.get("meeting"))
    r = race(row.get("race_no") or row.get("race_number") or row.get("race"))
    h = norm(row.get("horse") or row.get("horse_name") or row.get("runner_name") or row.get("results_runner"))
    return f"{d}|{t}|{r}|{h}" if d and t and r and h else ""

def racekey_from_key(k):
    return "|".join(k.split("|")[:3])

def read(p):
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

backfill = read(BACKFILL)
validation = read(VALIDATION)
truth = read(TRUTH)

validation_keys = {key(r) for r in validation if key(r)}
validation_races = {racekey_from_key(k) for k in validation_keys}

truth_safe_keys = {
    key(r) for r in truth
    if key(r) and clean(r.get("safe_for_model_validation")).upper() == "YES" and clean(r.get("finish_position"))
}

rows = []
for r in backfill:
    k = key(r)
    rk = racekey_from_key(k)
    rows.append({
        "race_date": r.get("race_date", ""),
        "track": r.get("track", ""),
        "race_no": r.get("race_no", ""),
        "horse": r.get("horse", ""),
        "backfill_key": k,
        "backfill_race_in_temporal_validation": "YES" if rk in validation_races else "NO",
        "backfill_runner_in_temporal_validation": "YES" if k in validation_keys else "NO",
        "backfill_runner_safe_in_truth": "YES" if k in truth_safe_keys else "NO",
        "diagnosis": (
            "DIRECT_TEMPORAL_MATCH_SHOULD_VALIDATE" if k in validation_keys and k in truth_safe_keys else
            "RACE_EXISTS_HORSE_KEY_MISMATCH" if rk in validation_races else
            "BACKFILLED_RACE_NOT_IN_TEMPORAL_UNIVERSE"
        )
    })

with OUT.open("w", encoding="utf-8", newline="") as f:
    fields = ["race_date","track","race_no","horse","backfill_key","backfill_race_in_temporal_validation","backfill_runner_in_temporal_validation","backfill_runner_safe_in_truth","diagnosis"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

from collections import Counter
c = Counter(r["diagnosis"] for r in rows)
print("="*80)
print("BACKFILL TO TEMPORAL KEY AUDIT")
print("="*80)
print(f"backfill rows: {len(rows)}")
for k,v in c.most_common():
    print(f"{k}: {v}")
print(f"saved: {OUT}")
