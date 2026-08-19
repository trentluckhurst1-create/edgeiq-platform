import os
import re
import pandas as pd
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

LIVE_SRC = os.path.join(DATA, "edgeiq_live_runner_board_v1.csv")
DNA_SRC = os.path.join(DATA, "edgeiq_tactical_dna_v1.csv")

OUT = os.path.join(DATA, "edgeiq_dna_match_audit_v2.csv")
SUMMARY_OUT = os.path.join(DATA, "edgeiq_dna_match_audit_v2_summary.csv")

print("=" * 100)
print("EDGEIQ DNA MATCH AUDIT V2")
print("=" * 100)
print(f"LIVE_SRC: {LIVE_SRC}")
print(f"DNA_SRC:  {DNA_SRC}")

if not os.path.exists(LIVE_SRC):
    raise FileNotFoundError(f"Missing live runner board: {LIVE_SRC}")

if not os.path.exists(DNA_SRC):
    raise FileNotFoundError(f"Missing tactical DNA file: {DNA_SRC}")

live = pd.read_csv(LIVE_SRC, dtype=str).fillna("")
dna = pd.read_csv(DNA_SRC, dtype=str).fillna("")

def clean_key(x):
    x = str(x).upper().strip()
    x = re.sub(r"\([^)]*\)", "", x)
    x = x.replace("'", "")
    x = re.sub(r"\bTHE\b", "THE", x)
    x = re.sub(r"[^A-Z0-9]+", "", x)
    return x

def clean_name_soft(x):
    x = str(x).upper().strip()
    x = re.sub(r"\([^)]*\)", "", x)
    x = x.replace("'", "")
    x = re.sub(r"[^A-Z0-9 ]+", " ", x)
    x = re.sub(r"\s+", " ", x).strip()
    return x

def find_col(cols, options):
    lower = {c.lower(): c for c in cols}
    for opt in options:
        if opt.lower() in lower:
            return lower[opt.lower()]
    return None

live_horse_col = find_col(live.columns, ["horse", "horseName", "runner", "runner_name", "name"])
live_key_col = find_col(live.columns, ["horse_key", "horseKey", "runner_key"])
track_col = find_col(live.columns, ["track", "meeting_name", "location"])
race_col = find_col(live.columns, ["race_no", "raceNo", "race_number"])
date_col = find_col(live.columns, ["meeting_date", "race_date", "date"])

dna_key_col = find_col(dna.columns, ["horse_key", "horseKey"])
dna_name_col = find_col(dna.columns, ["horse", "horseName", "runner", "name"])

if live_horse_col is None and live_key_col is None:
    raise ValueError("Live file has no horse or horse_key column.")

if dna_key_col is None:
    raise ValueError("DNA file has no horse_key column.")

if dna_name_col is None:
    dna_name_col = dna_key_col

live["live_horse"] = live[live_horse_col] if live_horse_col else live[live_key_col]
live["live_key_existing"] = live[live_key_col] if live_key_col else ""
live["live_key_clean_from_name"] = live["live_horse"].apply(clean_key)
live["live_key_clean_from_existing"] = live["live_key_existing"].apply(clean_key)
live["live_join_key"] = np.where(
    live["live_key_clean_from_existing"] != "",
    live["live_key_clean_from_existing"],
    live["live_key_clean_from_name"]
)
live["live_soft_name"] = live["live_horse"].apply(clean_name_soft)

live["track"] = live[track_col] if track_col else ""
live["race_no"] = live[race_col] if race_col else ""
live["meeting_date"] = live[date_col] if date_col else ""

dna["dna_horse"] = dna[dna_name_col]
dna["dna_key_existing"] = dna[dna_key_col]
dna["dna_key_clean"] = dna[dna_key_col].apply(clean_key)
dna["dna_soft_name"] = dna["dna_horse"].apply(clean_name_soft)

dna_keys = set(dna["dna_key_clean"].dropna().astype(str))
dna_soft = set(dna["dna_soft_name"].dropna().astype(str))

direct = live["live_join_key"].isin(dna_keys)
name_direct = live["live_key_clean_from_name"].isin(dna_keys)
soft_direct = live["live_soft_name"].isin(dna_soft)

status = []
for i, r in live.iterrows():
    if r["live_join_key"] in dna_keys:
        status.append("MATCH_EXISTING_KEY")
    elif r["live_key_clean_from_name"] in dna_keys:
        status.append("MATCH_NAME_KEY")
    elif r["live_soft_name"] in dna_soft:
        status.append("MATCH_SOFT_NAME")
    else:
        status.append("NO_MATCH")

live["dna_match_status"] = status
live["matched_key_used"] = np.where(
    live["live_join_key"].isin(dna_keys),
    live["live_join_key"],
    np.where(
        live["live_key_clean_from_name"].isin(dna_keys),
        live["live_key_clean_from_name"],
        ""
    )
)

live["possible_issue"] = np.where(
    live["dna_match_status"] != "NO_MATCH",
    "",
    np.where(
        live["live_key_existing"].astype(str).str.strip() == "",
        "NO_LIVE_HORSE_KEY_OR_DNA_HISTORY",
        "LIVE_KEY_DOES_NOT_EXIST_IN_DNA"
    )
)

out_cols = [
    "meeting_date",
    "track",
    "race_no",
    "live_horse",
    "live_key_existing",
    "live_key_clean_from_existing",
    "live_key_clean_from_name",
    "live_soft_name",
    "dna_match_status",
    "matched_key_used",
    "possible_issue",
]

audit = live[out_cols].copy()

summary = pd.DataFrame([{
    "live_rows": len(live),
    "dna_rows": len(dna),
    "match_existing_key": int((audit["dna_match_status"] == "MATCH_EXISTING_KEY").sum()),
    "match_name_key": int((audit["dna_match_status"] == "MATCH_NAME_KEY").sum()),
    "match_soft_name": int((audit["dna_match_status"] == "MATCH_SOFT_NAME").sum()),
    "no_match": int((audit["dna_match_status"] == "NO_MATCH").sum()),
    "match_rate_pct": round((audit["dna_match_status"] != "NO_MATCH").mean() * 100, 2),
}])

audit.to_csv(OUT, index=False)
summary.to_csv(SUMMARY_OUT, index=False)

print("")
print("DONE")
print(f"WROTE: {OUT}")
print(f"WROTE: {SUMMARY_OUT}")
print("")
print(summary.to_string(index=False))
print("")
print("MATCH STATUS")
print(audit["dna_match_status"].value_counts(dropna=False).to_string())
print("")
print("FIRST 80 UNMATCHED")
print(audit[audit["dna_match_status"] == "NO_MATCH"].head(80)[[
    "meeting_date",
    "track",
    "race_no",
    "live_horse",
    "live_key_existing",
    "live_key_clean_from_name",
    "possible_issue",
]].to_string(index=False))
