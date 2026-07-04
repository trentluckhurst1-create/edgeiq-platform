from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_trainer_name_crosswalk_v1.csv"

OUT = DATA / "edgeiq_trainer_crosswalk_master_v1.csv"
SUMMARY = DATA / "edgeiq_trainer_crosswalk_master_v1_summary.csv"

df = pd.read_csv(SRC, low_memory=False)

df["match_status"] = df["match_status"].astype(str).str.strip().str.upper()
df["match_score"] = pd.to_numeric(df["match_score"], errors="coerce").fillna(0)

safe = df[
    (df["match_status"].isin(["EXACT_MATCH", "ALIAS_MATCH"])) |
    ((df["match_status"] == "FUZZY_ALIAS_MATCH") & (df["match_score"] >= 90))
].copy()

safe = safe[[
    "live_trainer",
    "matched_warehouse_trainer",
    "match_status",
    "match_method",
    "match_score",
]]

safe = safe.rename(columns={
    "matched_warehouse_trainer": "warehouse_trainer"
})

safe = safe.sort_values(
    ["match_score", "live_trainer"],
    ascending=[False, True]
)

safe["built_at"] = datetime.now(timezone.utc).isoformat()

safe.to_csv(OUT, index=False)

summary = pd.DataFrame([
    ["status", "EDGEIQ_TRAINER_CROSSWALK_MASTER_V1_BUILT"],
    ["source", str(SRC)],
    ["rows", len(safe)],
    ["exact_match", int((safe["match_status"] == "EXACT_MATCH").sum())],
    ["alias_match", int((safe["match_status"] == "ALIAS_MATCH").sum())],
    ["safe_fuzzy_alias_match", int((safe["match_status"] == "FUZZY_ALIAS_MATCH").sum())],
    ["excluded", int(len(df) - len(safe))],
    ["output", str(OUT)],
    ["built_at", datetime.now(timezone.utc).isoformat()],
], columns=["metric", "value"])

summary.to_csv(SUMMARY, index=False)

print("[TRAINER_CROSSWALK_MASTER_V1] COMPLETE")
print(f"rows={len(safe)}")
print(f"output={OUT}")
