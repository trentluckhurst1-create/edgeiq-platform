"""Read-only, schema-first eligibility audit. No outcomes, fits, prices, or sealed-year access."""
from pathlib import Path
import csv, re
ROOTS=[Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research"),Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research")]
UNIVERSE=ROOTS[0]/"model_v2"/"stage006"/"V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv"
KEYS={"_race","_horse","race_date","canonical_race_id","canonical_horse_id"}
TARGET=re.compile(r"(^|_)(age|sex|gender|going|track_condition|surface|horse_age|horse_sex)($|_)",re.I)
BLOCK=re.compile(r"market|odds|price|bsp|starting.price|result|outcome|epi|prediction|scored|holdout|2025|2026",re.I)
def headers(p):
    try:
        with p.open("r",encoding="utf-8-sig",newline="") as f:return next(csv.reader(f))
    except (OSError,UnicodeError,StopIteration,csv.Error):return []
print("AUDIT_CONTRACT SCHEMA_ONLY NO_OUTCOMES NO_TRAINING NO_PRICES SEALED_2025_2026")
if not UNIVERSE.is_file():raise SystemExit("STOP: certified V2 feature warehouse missing")
uc=headers(UNIVERSE)
print("V2_WAREHOUSE",UNIVERSE,"KEYS",",".join(c for c in uc if c in KEYS))
print("V2_DIRECT_CANDIDATES",",".join(c for c in uc if TARGET.search(c)) or "NONE")
if not {"_race","_horse","race_date"}.issubset(uc):raise SystemExit("STOP: expected V2 keys missing")
found=0
for root in ROOTS:
    if not root.is_dir():continue
    for p in root.rglob("*.csv"):
        rel=str(p).lower()
        if BLOCK.search(rel) or p==UNIVERSE:continue
        cols=headers(p)
        target=[c for c in cols if TARGET.search(c) and not BLOCK.search(c)]
        if not target:continue
        keys=[c for c in cols if c in KEYS]
        if not keys:continue
        found+=1
        print("CANDIDATE",p,"KEYS",",".join(keys),"FIELDS",",".join(target))
print("SCHEMA_CANDIDATE_COUNT",found)
print("STATUS UNVERIFIED: SCHEMA ONLY; PIT, EXACT JOIN, 90_PERCENT_COVERAGE AND NEVER_FITTED NOT CERTIFIED")
