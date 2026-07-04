import pandas as pd
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_live_runner_board_v1.csv"
WAREHOUSE = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"

OUT = DATA / "edgeiq_live_graphql_entity_resolution_bridge_v3.csv"
SUMMARY = DATA / "edgeiq_live_graphql_entity_resolution_bridge_v3_summary.csv"

def norm(x):
    if pd.isna(x):
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(x).upper())

def surname_key(name):
    s = str(name).upper().strip()
    s = s.replace(",", " ")
    parts = re.split(r"\s+|&", s)
    parts = [p for p in parts if p and p not in ["AND", "THE"]]
    if not parts:
        return ""
    return norm(parts[-1])

def initials_surname_key(name):
    s = str(name).upper().strip()
    s = s.replace(",", " ")
    parts = re.split(r"\s+|&", s)
    parts = [p for p in parts if p and p not in ["AND", "THE"]]
    if not parts:
        return ""

    surname = parts[-1]
    initials = "".join([p[0] for p in parts[:-1] if p])
    return norm(initials + surname)

def graphql_key(name):
    s = str(name).upper().strip()
    if not s:
        return ""
    return norm(s)

def graphql_surname_key(name):
    s = str(name).upper().strip()
    s = s.replace(".", " ")
    s = s.replace("&", " ")
    parts = [p for p in re.split(r"\s+", s) if p]
    if not parts:
        return ""
    return norm(parts[-1])

print("[ENTITY_RESOLUTION_V3] loading...")
live = pd.read_csv(LIVE, low_memory=False)
wh = pd.read_csv(WAREHOUSE, low_memory=False, usecols=["trainer","jockey"])

rows = []

for entity_type, live_col, wh_col in [
    ("TRAINER", "trainer", "trainer"),
    ("JOCKEY", "jockey", "jockey"),
]:
    live_entities = (
        live[live_col].fillna("").astype(str).str.strip()
        .replace("", pd.NA).dropna().drop_duplicates().tolist()
    )

    gql_counts = (
        wh[wh_col].fillna("").astype(str).str.strip()
        .replace("", pd.NA).dropna()
        .value_counts()
        .reset_index()
    )
    gql_counts.columns = ["graphql_name", "rows_seen"]

    gql_counts["graphql_key"] = gql_counts["graphql_name"].apply(graphql_key)
    gql_counts["graphql_surname_key"] = gql_counts["graphql_name"].apply(graphql_surname_key)

    gql_by_key = gql_counts.sort_values("rows_seen", ascending=False).drop_duplicates("graphql_key")
    gql_by_surname = gql_counts.sort_values("rows_seen", ascending=False).drop_duplicates("graphql_surname_key")

    key_map = dict(zip(gql_by_key["graphql_key"], gql_by_key["graphql_name"]))
    key_rows = dict(zip(gql_by_key["graphql_key"], gql_by_key["rows_seen"]))
    surname_map = dict(zip(gql_by_surname["graphql_surname_key"], gql_by_surname["graphql_name"]))
    surname_rows = dict(zip(gql_by_surname["graphql_surname_key"], gql_by_surname["rows_seen"]))

    for name in live_entities:
        k_direct = graphql_key(name)
        k_initial = initials_surname_key(name)
        k_surname = surname_key(name)

        matched = ""
        method = "NO_MATCH"
        rows_seen = 0

        if k_direct in key_map:
            matched = key_map[k_direct]
            rows_seen = key_rows[k_direct]
            method = "DIRECT_KEY"
        elif k_initial in key_map:
            matched = key_map[k_initial]
            rows_seen = key_rows[k_initial]
            method = "INITIAL_SURNAME_KEY"
        elif k_surname in surname_map and k_surname:
            matched = surname_map[k_surname]
            rows_seen = surname_rows[k_surname]
            method = "SURNAME_FALLBACK"

        rows.append({
            "entity_type": entity_type,
            "live_name": name,
            "live_key": k_direct,
            "live_initial_surname_key": k_initial,
            "live_surname_key": k_surname,
            "graphql_name": matched,
            "graphql_key": graphql_key(matched),
            "match_status": "MATCHED" if matched else "NO_MATCH",
            "method": method,
            "rows_seen": rows_seen,
            "built_at": datetime.now(timezone.utc).isoformat(),
        })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "LIVE_GRAPHQL_ENTITY_RESOLUTION_BRIDGE_V3_BUILT",
    "rows": len(out),
    "matched": int((out["match_status"] == "MATCHED").sum()),
    "no_match": int((out["match_status"] == "NO_MATCH").sum()),
    "trainer_matched": int(((out["entity_type"] == "TRAINER") & (out["match_status"] == "MATCHED")).sum()),
    "trainer_no_match": int(((out["entity_type"] == "TRAINER") & (out["match_status"] == "NO_MATCH")).sum()),
    "jockey_matched": int(((out["entity_type"] == "JOCKEY") & (out["match_status"] == "MATCHED")).sum()),
    "jockey_no_match": int(((out["entity_type"] == "JOCKEY") & (out["match_status"] == "NO_MATCH")).sum()),
    "built_at": datetime.now(timezone.utc).isoformat(),
}])

summary.to_csv(SUMMARY, index=False)

print("[ENTITY_RESOLUTION_V3] COMPLETE")
print(summary.to_string(index=False))
