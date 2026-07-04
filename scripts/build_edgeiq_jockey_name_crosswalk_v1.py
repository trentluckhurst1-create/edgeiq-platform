from pathlib import Path
import pandas as pd
from datetime import datetime, timezone
import difflib

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

WAREHOUSE = DATA / "edgeiq_composite_dna_v2_1.csv"
LIVE_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"

OUT = DATA / "edgeiq_jockey_name_crosswalk_v1.csv"
SUMMARY = DATA / "edgeiq_jockey_name_crosswalk_v1_summary.csv"

def clean(v):
    return "" if pd.isna(v) else str(v).strip()

def nkey(v):
    return clean(v).upper().replace(".", "").replace(" ", "").replace("-", "").replace("'", "").replace("(", "").replace(")", "")

def initials_key(name):
    parts = clean(name).replace(".", " ").split()
    if not parts:
        return ""
    if len(parts) == 1:
        return nkey(parts[0])
    return "".join(p[0].upper() for p in parts[:-1] if p) + parts[-1].upper()

warehouse = pd.read_csv(WAREHOUSE, low_memory=False)
live = pd.read_csv(LIVE_BOARD, low_memory=False)

warehouse_j = (
    warehouse[warehouse["entity_type"].astype(str).str.upper() == "JOCKEY"]
    [["entity_name"]]
    .drop_duplicates()
    .rename(columns={"entity_name": "warehouse_jockey"})
)

live_j = (
    live[["jockey"]]
    .drop_duplicates()
    .rename(columns={"jockey": "live_jockey"})
)

warehouse_j["warehouse_key"] = warehouse_j["warehouse_jockey"].apply(nkey)
warehouse_j["warehouse_initials_key"] = warehouse_j["warehouse_jockey"].apply(initials_key)

live_j["live_key"] = live_j["live_jockey"].apply(nkey)
live_j["live_initials_key"] = live_j["live_jockey"].apply(initials_key)

warehouse_keys = set(warehouse_j["warehouse_key"])
warehouse_initials = set(warehouse_j["warehouse_initials_key"])

rows = []
warehouse_lookup_key = {r["warehouse_key"]: r["warehouse_jockey"] for _, r in warehouse_j.iterrows()}
warehouse_lookup_initials = {r["warehouse_initials_key"]: r["warehouse_jockey"] for _, r in warehouse_j.iterrows()}

warehouse_key_list = list(warehouse_lookup_key.keys())

for _, r in live_j.iterrows():
    live_name = clean(r["live_jockey"])
    live_key = r["live_key"]
    live_init = r["live_initials_key"]

    if not live_name or live_name.upper() == "NOT NOTIFIED":
        status = "NO_RIDER"
        matched = ""
        method = ""
        score = 0
    elif live_key in warehouse_lookup_key:
        status = "EXACT_MATCH"
        matched = warehouse_lookup_key[live_key]
        method = "FULL_KEY"
        score = 100
    elif live_init in warehouse_lookup_initials:
        status = "INITIALS_MATCH"
        matched = warehouse_lookup_initials[live_init]
        method = "INITIALS_SURNAME"
        score = 95
    else:
        close = difflib.get_close_matches(live_key, warehouse_key_list, n=1, cutoff=0.74)
        if close:
            status = "FUZZY_MATCH"
            matched = warehouse_lookup_key[close[0]]
            method = "DIFFLIB"
            score = round(difflib.SequenceMatcher(None, live_key, close[0]).ratio() * 100, 1)
        else:
            status = "UNMATCHED"
            matched = ""
            method = ""
            score = 0

    rows.append({
        "built_at": datetime.now(timezone.utc).isoformat(),
        "live_jockey": live_name,
        "live_key": live_key,
        "live_initials_key": live_init,
        "matched_warehouse_jockey": matched,
        "match_status": status,
        "match_method": method,
        "match_score": score,
    })

out = pd.DataFrame(rows).sort_values(["match_status","live_jockey"])

out.to_csv(OUT, index=False)

summary = pd.DataFrame([
    ["status","EDGEIQ_JOCKEY_NAME_CROSSWALK_V1_BUILT"],
    ["live_jockeys",len(out)],
    ["exact_match",int((out["match_status"]=="EXACT_MATCH").sum())],
    ["initials_match",int((out["match_status"]=="INITIALS_MATCH").sum())],
    ["fuzzy_match",int((out["match_status"]=="FUZZY_MATCH").sum())],
    ["unmatched",int((out["match_status"]=="UNMATCHED").sum())],
    ["no_rider",int((out["match_status"]=="NO_RIDER").sum())],
    ["warehouse_jockeys",len(warehouse_j)],
    ["output",str(OUT)],
    ["built_at",datetime.now(timezone.utc).isoformat()],
], columns=["metric","value"])

summary.to_csv(SUMMARY,index=False)

print("[JOCKEY_NAME_CROSSWALK_V1] COMPLETE")
print(f"live_jockeys={len(out)}")
print(f"output={OUT}")
