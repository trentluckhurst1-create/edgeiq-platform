import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INP = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
OUT = DATA / "edgeiq_context_warehouse_v2_graphql.csv"
SUMMARY = DATA / "edgeiq_context_warehouse_v2_graphql_summary.csv"

MIN_STARTS = 20

def pct(a,b):
    return round((a / b * 100), 4) if b else 0

def signal(starts, win_pct, place_pct, base_win, base_place):
    if starts < MIN_STARTS:
        return "LOW_SAMPLE"
    win_lift = win_pct - base_win
    place_lift = place_pct - base_place
    if win_lift >= 8 and place_lift >= 10:
        return "STRONG_POSITIVE"
    if win_lift >= 4 or place_lift >= 6:
        return "POSITIVE"
    if win_lift <= -6 and place_lift <= -8:
        return "NEGATIVE"
    return "NEUTRAL"

def build_context(df, entity_col, entity_type, context_col, context_type, base):
    g = (
        df.groupby([entity_col, context_col], dropna=False)
        .agg(starts=("horse","count"), wins=("won","sum"), places=("placed","sum"))
        .reset_index()
    )
    g = g[(g[entity_col] != "") & (g[context_col] != "")]
    g["win_pct"] = g.apply(lambda r: pct(r["wins"], r["starts"]), axis=1)
    g["place_pct"] = g.apply(lambda r: pct(r["places"], r["starts"]), axis=1)
    g = g.merge(base, on=entity_col, how="left")
    g["win_lift_pct"] = (g["win_pct"] - g["base_win_pct"]).round(4)
    g["place_lift_pct"] = (g["place_pct"] - g["base_place_pct"]).round(4)
    g["entity_type"] = entity_type
    g["entity_name"] = g[entity_col]
    g["context_type"] = context_type
    g["context_value"] = g[context_col]
    g["signal"] = g.apply(lambda r: signal(r["starts"], r["win_pct"], r["place_pct"], r["base_win_pct"], r["base_place_pct"]), axis=1)
    g["insight"] = g.apply(lambda r: f"{r['entity_name']} {context_type.lower()} {r['context_value']}: {r['signal']} from {r['starts']} starts.", axis=1)
    return g[["entity_type","entity_name","context_type","context_value","signal","starts","wins","places","win_pct","place_pct","win_lift_pct","place_lift_pct","insight"]]

print("[CONTEXT_WAREHOUSE_V2_GRAPHQL] loading warehouse...")
df = pd.read_csv(INP, low_memory=False)

df["finish_num"] = pd.to_numeric(df["finish_num"], errors="coerce")
df["won"] = (df["finish_num"] == 1).astype(int)
df["placed"] = df["finish_num"].isin([1,2,3]).astype(int)
df["scratched_bool"] = df["scratched"].astype(str).str.lower().eq("true")

df = df[(~df["scratched_bool"]) & (df["finish_num"].notna())].copy()

df["distance_bucket"] = pd.to_numeric(df["distance"].astype(str).str.extract(r"(\d+)")[0], errors="coerce")
df["distance_bucket"] = pd.cut(
    df["distance_bucket"],
    bins=[0,1200,1400,1600,2000,10000],
    labels=["SPRINT","SHORT","MILE","MIDDLE","STAYING"]
).astype(str).replace("nan","")

df["condition_bucket"] = df["track_condition"].fillna("").astype(str).str.upper().str.extract(r"(GOOD|SOFT|HEAVY|FAST|SYNTHETIC)")[0].fillna("")
df["track"] = df["track"].fillna("").astype(str).str.upper().str.strip()
df["trainer"] = df["trainer"].fillna("").astype(str).str.upper().str.strip()
df["jockey"] = df["jockey"].fillna("").astype(str).str.upper().str.strip()
df["horse"] = df["horse"].fillna("").astype(str).str.upper().str.strip()
df["connection"] = df["trainer"] + " + " + df["jockey"]

bases = {}
for col in ["horse","trainer","jockey","connection"]:
    b = df.groupby(col).agg(base_starts=("horse","count"), base_wins=("won","sum"), base_places=("placed","sum")).reset_index()
    b["base_win_pct"] = b.apply(lambda r: pct(r["base_wins"], r["base_starts"]), axis=1)
    b["base_place_pct"] = b.apply(lambda r: pct(r["base_places"], r["base_starts"]), axis=1)
    bases[col] = b[[col,"base_starts","base_win_pct","base_place_pct"]]

parts = []
for entity_col, entity_type in [
    ("horse","HORSE"),
    ("trainer","TRAINER"),
    ("jockey","JOCKEY"),
    ("connection","CONNECTION"),
]:
    base = bases[entity_col]
    for context_col, context_type in [
        ("track","TRACK"),
        ("distance_bucket","DISTANCE"),
        ("condition_bucket","CONDITION"),
    ]:
        parts.append(build_context(df, entity_col, entity_type, context_col, context_type, base))

out = pd.concat(parts, ignore_index=True)
out["built_at"] = datetime.now(timezone.utc).isoformat()
out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "CONTEXT_WAREHOUSE_V2_GRAPHQL_BUILT",
    "rows": len(out),
    "horse_rows": int((out["entity_type"] == "HORSE").sum()),
    "trainer_rows": int((out["entity_type"] == "TRAINER").sum()),
    "jockey_rows": int((out["entity_type"] == "JOCKEY").sum()),
    "connection_rows": int((out["entity_type"] == "CONNECTION").sum()),
    "strong_positive": int((out["signal"] == "STRONG_POSITIVE").sum()),
    "positive": int((out["signal"] == "POSITIVE").sum()),
    "negative": int((out["signal"] == "NEGATIVE").sum()),
    "low_sample": int((out["signal"] == "LOW_SAMPLE").sum()),
    "built_at": datetime.now(timezone.utc).isoformat(),
}])

summary.to_csv(SUMMARY, index=False)

print("[CONTEXT_WAREHOUSE_V2_GRAPHQL] COMPLETE")
print(summary.to_string(index=False))
