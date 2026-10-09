from pathlib import Path
import pandas as pd

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
RATING = DATA / "edgeiq_historical_performance_rating_v1.csv"
MASTER = DATA / "edgeiq_official_runs_master_v1.csv"
PROTOTYPE = ROOT / "docs" / "performance-intelligence" / "prototypes" / "phase1_4_1b" / "edgeiq_cross_provider_horse_identity_candidates_v0_1_20260716_063119.csv"
BRIDGE = DATA / "LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"

print("V2_STAGE037_CONTRACT EXACT_OFFICIAL_RUNS_MASTER_IDENTITY NO_MODEL NO_FUZZY NO_MARKET 2025_2026_SEALED")
print("V2_STAGE037_SOURCE_EXISTS RATING", RATING.exists(), "MASTER", MASTER.exists(), "PROTOTYPE", PROTOTYPE.exists(), "COMPACT_BRIDGE", BRIDGE.exists())
if not RATING.exists() or not MASTER.exists():
    raise SystemExit("V2_STAGE037_STOP REQUIRED_SOURCE_MISSING")
def normalise(s):
    return s.fillna("").astype(str).str.upper().str.replace(r"[^A-Z0-9]", "", regex=True)
def parse_date(s):
    return pd.to_datetime(s, errors="coerce", dayfirst=False).dt.normalize()
r = pd.read_csv(RATING, low_memory=False, usecols=["horse", "race_date"])
mhead = pd.read_csv(MASTER, nrows=0)
print("V2_STAGE037_MASTER_COLUMNS", "|".join(mhead.columns))
if "horse_key" not in mhead.columns or "horse" not in mhead.columns or "race_date" not in mhead.columns:
    raise SystemExit("V2_STAGE037_STOP MASTER_SCHEMA_MISMATCH")
m = pd.read_csv(MASTER, low_memory=False, usecols=["horse_key", "horse", "race_date"])
r["_date"] = parse_date(r["race_date"])
m["_date"] = parse_date(m["race_date"])
excluded = int((r["_date"].dt.year > 2024).sum())
invalid = int(r["_date"].isna().sum())
r = r[r["_date"].dt.year.le(2024)].copy()
m = m[m["_date"].dt.year.le(2024)].copy()
r["_name"] = normalise(r["horse"])
m["_name"] = normalise(m["horse"])
r = r[r["_name"].ne("") & r["_date"].notna()].copy()
m = m[m["_name"].ne("") & m["_date"].notna()].copy()
m["horse_key"] = m["horse_key"].fillna("").astype(str).str.strip()
m = m[m["horse_key"].ne("")].copy()
name_keys = set(m["_name"].unique())
date_keys = set(zip(m["_name"], m["_date"]))
name_hits = int(r["_name"].isin(name_keys).sum())
pair_hits = int(sum(pair in date_keys for pair in zip(r["_name"], r["_date"])))
ids = m.groupby("_name")["horse_key"].nunique()
matched_names = set(r.loc[r["_name"].isin(name_keys), "_name"])
colliding = sorted(name for name in matched_names if ids.get(name, 0) > 1)
name_hit_rate = name_hits / len(r) if len(r) else 0
pair_hit_rate = pair_hits / len(r) if len(r) else 0
collision_rate = len(colliding) / len(matched_names) if matched_names else 0
print("V2_STAGE037_COUNTS RATING_PRE2025", len(r), "MASTER_PRE2025", len(m), "EXCLUDED_SEALED_RATING_N", excluded, "INVALID_RATING_DATE_N", invalid)
print("V2_STAGE037_NAME_HITS", name_hits, "RATE", name_hit_rate)
print("V2_STAGE037_EXACT_NAME_DATE_HITS", pair_hits, "RATE", pair_hit_rate)
print("V2_STAGE037_MATCHED_UNIQUE_NAMES", len(matched_names), "COLLIDING_NAMES", len(colliding), "COLLISION_RATE", collision_rate)
print("V2_STAGE037_COLLISION_SAMPLE", "|".join(colliding[:30]) if colliding else "NONE")
for year, z in r.groupby(r["_date"].dt.year):
    h = sum(pair in date_keys for pair in zip(z["_name"], z["_date"]))
    print("V2_STAGE037_YEAR", int(year), "RATING", len(z), "EXACT_PAIR_HITS", h, "RATE", h / len(z))
if not len(r):
    decision = "STOP_NO_ELIGIBLE_ROWS"
elif colliding or pair_hit_rate < 0.50:
    decision = "STOP"
elif pair_hit_rate >= 0.90 and not colliding:
    decision = "PASS_EXACT_HORSE_KEY_CANDIDATE_NOT_CANONICAL"
else:
    decision = "INDETERMINATE"
print("V2_STAGE037_DECISION", decision)
print("V2_STAGE037_COMPLETE")
