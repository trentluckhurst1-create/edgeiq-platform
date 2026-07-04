from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_jockey_name_crosswalk_v1.csv"

OUT = DATA / "edgeiq_jockey_crosswalk_master_v1.csv"
SUMMARY = DATA / "edgeiq_jockey_crosswalk_master_v1_summary.csv"

df = pd.read_csv(SRC, low_memory=False)

df["match_status"] = df["match_status"].astype(str).str.strip().str.upper()

master = df[
    df["match_status"].isin([
        "INITIALS_MATCH",
        "FUZZY_MATCH",
        "EXACT_MATCH"
    ])
].copy()

master = master[[
    "live_jockey",
    "matched_warehouse_jockey",
    "match_status",
    "match_method",
    "match_score"
]]

master = master.rename(columns={
    "matched_warehouse_jockey":"warehouse_jockey"
})

master = master.sort_values(
    ["match_score","live_jockey"],
    ascending=[False,True]
)

master["built_at"] = datetime.now(
    timezone.utc
).isoformat()

master.to_csv(
    OUT,
    index=False
)

summary = pd.DataFrame([
    ["status","EDGEIQ_JOCKEY_CROSSWALK_MASTER_V1_BUILT"],
    ["rows",len(master)],
    ["exact_match",(master["match_status"]=="EXACT_MATCH").sum()],
    ["initials_match",(master["match_status"]=="INITIALS_MATCH").sum()],
    ["fuzzy_match",(master["match_status"]=="FUZZY_MATCH").sum()],
    ["output",str(OUT)],
])

summary.columns=["metric","value"]

summary.to_csv(
    SUMMARY,
    index=False
)

print("[JOCKEY_CROSSWALK_MASTER_V1] COMPLETE")
print(f"rows={len(master)}")
print(f"output={OUT}")
