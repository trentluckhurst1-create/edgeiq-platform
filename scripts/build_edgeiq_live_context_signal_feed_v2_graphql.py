import pandas as pd
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_live_runner_board_v1.csv"
SIGNALS = DATA / "edgeiq_context_warehouse_v2_graphql_signal_view.csv"
RESOLVER = DATA / "edgeiq_live_graphql_entity_resolution_bridge_v3.csv"

OUT = DATA / "edgeiq_live_context_signal_feed_v2_graphql.csv"
SUMMARY = DATA / "edgeiq_live_context_signal_feed_v2_graphql_summary.csv"

def key(x):
    if pd.isna(x):
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(x).upper())

def dist_bucket(x):
    n = pd.to_numeric(pd.Series([str(x)]).str.extract(r"(\d+)")[0], errors="coerce").iloc[0]
    if pd.isna(n):
        return ""
    if n <= 1200:
        return "SPRINT"
    if n <= 1400:
        return "SHORT"
    if n <= 1600:
        return "MILE"
    if n <= 2000:
        return "MIDDLE"
    return "STAYING"

def cond_bucket(x):
    s = str(x).upper()
    for c in ["GOOD","SOFT","HEAVY","FAST","SYNTHETIC"]:
        if c in s:
            return c
    return ""

print("[LIVE_CONTEXT_SIGNAL_FEED_V2_GRAPHQL] loading...")
live = pd.read_csv(LIVE, low_memory=False)
signals = pd.read_csv(SIGNALS, low_memory=False)
resolver = pd.read_csv(RESOLVER, low_memory=False)

live["race_date"] = live["race_date"].astype(str).str[:10]
live["track"] = live["track"].astype(str).str.upper().str.strip()
live["race_no"] = live["race_no"].astype(str)
live["horse"] = live["horse"].astype(str).str.upper().str.strip()
live["trainer"] = live["trainer"].astype(str).str.upper().str.strip()
live["jockey"] = live["jockey"].astype(str).str.upper().str.strip()
live["distance_bucket"] = live["distance"].apply(dist_bucket)
live["condition_bucket"] = live["track_condition"].apply(cond_bucket)

resolver["entity_type"] = resolver["entity_type"].astype(str).str.upper()
resolver["live_key_norm"] = resolver["live_name"].apply(key)
resolver["graphql_name"] = resolver["graphql_name"].fillna("").astype(str).str.upper().str.strip()

trainer_map = dict(zip(
    resolver[(resolver["entity_type"] == "TRAINER") & (resolver["match_status"] == "MATCHED")]["live_key_norm"],
    resolver[(resolver["entity_type"] == "TRAINER") & (resolver["match_status"] == "MATCHED")]["graphql_name"]
))

jockey_map = dict(zip(
    resolver[(resolver["entity_type"] == "JOCKEY") & (resolver["match_status"] == "MATCHED")]["live_key_norm"],
    resolver[(resolver["entity_type"] == "JOCKEY") & (resolver["match_status"] == "MATCHED")]["graphql_name"]
))

live["trainer_graphql"] = live["trainer"].apply(lambda x: trainer_map.get(key(x), x))
live["jockey_graphql"] = live["jockey"].apply(lambda x: jockey_map.get(key(x), x))
live["connection_graphql"] = live["trainer_graphql"] + " + " + live["jockey_graphql"]

signals["entity_name"] = signals["entity_name"].astype(str).str.upper().str.strip()
signals["context_type"] = signals["context_type"].astype(str).str.upper().str.strip()
signals["context_value"] = signals["context_value"].astype(str).str.upper().str.strip()

rows = []

for _, r in live.iterrows():
    contexts = {
        "TRACK": r["track"],
        "DISTANCE": r["distance_bucket"],
        "CONDITION": r["condition_bucket"],
    }

    entities = {
        "HORSE": r["horse"],
        "TRAINER": r["trainer_graphql"],
        "JOCKEY": r["jockey_graphql"],
        "CONNECTION": r["connection_graphql"],
    }

    matches = []
    for etype, ename in entities.items():
        for ctype, cval in contexts.items():
            if not ename or not cval:
                continue
            m = signals[
                (signals["entity_type"] == etype) &
                (signals["entity_name"] == ename) &
                (signals["context_type"] == ctype) &
                (signals["context_value"] == cval)
            ]
            if len(m):
                matches.append(m)

    if matches:
        mdf = pd.concat(matches, ignore_index=True)
        mdf["importance_score"] = pd.to_numeric(mdf["importance_score"], errors="coerce").fillna(0)
        mdf = mdf.sort_values("importance_score", ascending=False)
        top = mdf.head(3).to_dict("records")
    else:
        top = []

    def val(i, col):
        return top[i].get(col, "") if len(top) > i else ""

    rows.append({
        "race_date": r["race_date"],
        "track": r["track"],
        "race_no": r["race_no"],
        "horse": r["horse"],
        "horse_key": r.get("horse_key", ""),
        "trainer": r["trainer"],
        "jockey": r["jockey"],
        "trainer_graphql": r["trainer_graphql"],
        "jockey_graphql": r["jockey_graphql"],
        "context_signal_count": len(top),
        "context_signal_1_entity_type": val(0,"entity_type"),
        "context_signal_1_context": f"{val(0,'context_type')}={val(0,'context_value')}" if val(0,"context_type") else "",
        "context_signal_1_signal": val(0,"signal"),
        "context_signal_1_starts": val(0,"starts"),
        "context_signal_1_importance": val(0,"importance_score"),
        "context_signal_1_insight": val(0,"insight"),
        "context_signal_2_entity_type": val(1,"entity_type"),
        "context_signal_2_context": f"{val(1,'context_type')}={val(1,'context_value')}" if val(1,"context_type") else "",
        "context_signal_2_signal": val(1,"signal"),
        "context_signal_2_insight": val(1,"insight"),
        "context_signal_3_entity_type": val(2,"entity_type"),
        "context_signal_3_context": f"{val(2,'context_type')}={val(2,'context_value')}" if val(2,"context_type") else "",
        "context_signal_3_signal": val(2,"signal"),
        "context_signal_3_insight": val(2,"insight"),
        "built_at": datetime.now(timezone.utc).isoformat(),
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "LIVE_CONTEXT_SIGNAL_FEED_V2_GRAPHQL_BUILT",
    "rows": len(out),
    "rows_with_context_signals": int((out["context_signal_count"] > 0).sum()),
    "total_top_context_signals": int(out["context_signal_count"].sum()),
    "built_at": datetime.now(timezone.utc).isoformat(),
}])
summary.to_csv(SUMMARY, index=False)

print("[LIVE_CONTEXT_SIGNAL_FEED_V2_GRAPHQL] COMPLETE")
print(summary.to_string(index=False))
