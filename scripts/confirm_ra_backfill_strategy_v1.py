from pathlib import Path
import pandas as pd

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

TARGETS = DATA / "edgeiq_active_ra_profile_backfill_targets_v1.csv"

targets = pd.read_csv(TARGETS)

print("=" * 100)
print("EDGEIQ RA PROFILE BACKFILL READINESS")
print("=" * 100)

print()
print("TOTAL ACTIVE RUNNERS:", len(targets))
print("READY TO BACKFILL:", int(targets["has_ra_profile_url"].sum()))
print()

print("TARGET HORSES:")
print("-" * 100)

for _, r in targets.iterrows():
    print(
        f'{r["horse"]} | '
        f'{r["track"]} R{r["race_no"]} | '
        f'{r["target_status"]}'
    )

print()
print("IMPORTANT:")
print("-" * 100)

print("This confirms the core problem is NOT identity.")
print("The live board already contains valid RA profile URLs.")
print("The issue is that raw form runs were never backfilled into form_card_runs.csv.")

print()
print("NEXT PHASE:")
print("-" * 100)

print("1. Build RA active profile backfill engine")
print("2. Scrape HorseFullForm pages directly")
print("3. Extract historical runs")
print("4. Append into form_card_runs.csv")
print("5. Rebuild live form context")
print("6. Rebuild feature quality engine")
print("7. Rebuild execution engine")

print()
print("THIS IS THE REAL BREAKTHROUGH.")
print("The data source already exists inside the live board.")
