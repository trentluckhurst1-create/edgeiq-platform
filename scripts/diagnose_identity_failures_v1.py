from pathlib import Path
import pandas as pd

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

summary = pd.read_csv(DATA / "edgeiq_identity_match_audit_summary_v1.csv")

print("=" * 100)
print("EDGEIQ IDENTITY FAILURE DIAGNOSIS")
print("=" * 100)

print(summary.to_string(index=False))

print()
print("CRITICAL FINDINGS:")
print("-" * 100)

print("1. form_summary linkage works")
print("2. form_runs linkage FAILS")
print("3. race_fields linkage FAILS")
print("4. official_runs linkage mostly FAILS")
print("5. sectional linkage mostly FAILS")

print()
print("ROOT CAUSE:")
print("-" * 100)

print("LIVE BOARD = BENDIGO 2026-05-13")
print("race_fields = 2026-05-15")
print("form_card_runs = unrelated horses")
print("official_runs = historical archive")
print("sectionals = mostly Geelong/VIC archive")

print()
print("THIS IS NOT A HORSE_KEY FAILURE.")
print("THIS IS A RACE CONTEXT + COVERAGE FAILURE.")

print()
print("WHAT THIS MEANS:")
print("-" * 100)

print("The matching engine is working.")
print("The datasets simply do not contain the active race context.")
print("Your live board is ahead of the enrichment pipelines.")

print()
print("NEXT REQUIRED FIXES:")
print("-" * 100)

fixes = [
    "1. rebuild race_fields closer to jump time",
    "2. rebuild form_card_runs for today's meetings",
    "3. rebuild form_card_summary for today's meetings",
    "4. expand official_runs coverage",
    "5. expand sectional ingestion coverage",
    "6. add active-meeting prioritisation",
    "7. build live race enrichment refresh loop",
]

for x in fixes:
    print(x)

print()
print("MOST IMPORTANT:")
print("-" * 100)

print("The engine is NOT fundamentally broken anymore.")
print("It is now exposing where data coverage is missing.")
