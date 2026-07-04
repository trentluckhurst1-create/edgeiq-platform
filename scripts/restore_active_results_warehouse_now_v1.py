from pathlib import Path
import shutil
import pandas as pd
import time

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

ts = time.strftime("%Y%m%d_%H%M%S")

active = DATA / "edgeiq_racingcom_results_warehouse_v1.csv"
allv1 = DATA / "edgeiq_racingcom_results_warehouse_all_v1.csv"
fullv1 = DATA / "edgeiq_racingcom_results_warehouse_full_v1.csv"

print("=== RESTORE ACTIVE RESULTS WAREHOUSE ===")

for p in [active, allv1, fullv1]:
    if p.exists():
        try:
            n = len(pd.read_csv(p, low_memory=False))
        except Exception as e:
            n = f"ERROR {e}"
        print(p.name, p.stat().st_size, n)
    else:
        print(p.name, "MISSING")

active_backup = DATA / f"edgeiq_racingcom_results_warehouse_v1_BROKEN_458_BACKUP_{ts}.csv"
shutil.copy2(active, active_backup)
print("backup:", active_backup.name)

# choose biggest valid warehouse
candidates = []
for p in [allv1, fullv1]:
    if p.exists():
        df_head = pd.read_csv(p, nrows=5, low_memory=False)
        cols = set(df_head.columns)
        required = {"meeting_date","track","race_no","horseName","horseKey","barrier","distance"}
        ok = required.issubset(cols)
        rows = len(pd.read_csv(p, usecols=["track"], low_memory=False))
        candidates.append((rows, ok, p))

candidates = [x for x in candidates if x[1]]
if not candidates:
    raise SystemExit("NO VALID FULL WAREHOUSE FOUND")

source = sorted(candidates, reverse=True)[0][2]
print("using source:", source.name)

shutil.copy2(source, active)

check = pd.read_csv(active, low_memory=False)
print("RESTORED active rows:", len(check))
print("RESTORED tracks:", check["track"].nunique())
print(check["track"].value_counts().head(20).to_string())
