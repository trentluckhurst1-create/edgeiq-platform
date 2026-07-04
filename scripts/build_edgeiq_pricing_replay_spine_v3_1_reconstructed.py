from pathlib import Path
import pandas as pd
import re
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

SPINE = DATA / "edgeiq_pricing_replay_spine_v2.csv"
RECON = DATA / "edgeiq_pricing_replay_model_state_reconstruction_v1_2.csv"

OUT = DATA / "edgeiq_pricing_replay_spine_v3_1_reconstructed.csv"
SUMMARY = DATA / "edgeiq_pricing_replay_spine_v3_1_reconstructed_summary.csv"
AUDIT = DATA / "edgeiq_pricing_replay_spine_v3_1_reconstructed_audit.csv"

def norm_text(x):
    if pd.isna(x):
        return ""
    return re.sub(r"\s+", " ", str(x).strip().upper())

def norm_horse(x):
    x = norm_text(x)
    x = re.sub(r"[^A-Z0-9 ]+", "", x)
    return re.sub(r"\s+", " ", x).strip()

def find_col(df, names):
    lower = {c.lower(): c for c in df.columns}
    for n in names:
        if n.lower() in lower:
            return lower[n.lower()]
    return None

def date_s(s):
    return pd.to_datetime(s, errors="coerce").dt.date.astype("string")

def num_s(s):
    return pd.to_numeric(s, errors="coerce").astype("Int64").astype("string")

print("[PRICING_REPLAY_SPINE_V3_1_RECONSTRUCTED] START")

spine = pd.read_csv(SPINE, low_memory=False)
recon = pd.read_csv(RECON, low_memory=False)

s_date = find_col(spine, ["race_date", "meeting_date", "date"])
s_track = find_col(spine, ["track", "venue"])
s_race = find_col(spine, ["race_no", "race_number", "race"])
s_horse = find_col(spine, ["horse", "runner", "runner_name"])

r_date = find_col(recon, ["race_date", "meeting_date", "date"])
r_track = find_col(recon, ["track", "venue"])
r_race = find_col(recon, ["race_no", "race_number", "race"])
r_horse = find_col(recon, ["horse", "runner", "runner_name"])

missing = []
for label, value in {
    "spine_date": s_date,
    "spine_track": s_track,
    "spine_race": s_race,
    "spine_horse": s_horse,
    "recon_date": r_date,
    "recon_track": r_track,
    "recon_race": r_race,
    "recon_horse": r_horse,
}.items():
    if not value:
        missing.append(label)

if missing:
    raise RuntimeError(f"Missing join fields: {missing}")

spine["_replay_join_key_v3_1"] = (
    date_s(spine[s_date]).fillna("").astype(str) + "|" +
    spine[s_track].map(norm_text).fillna("").astype(str) + "|" +
    num_s(spine[s_race]).fillna("").astype(str) + "|" +
    spine[s_horse].map(norm_horse).fillna("").astype(str)
)

recon["_replay_join_key_v3_1"] = (
    date_s(recon[r_date]).fillna("").astype(str) + "|" +
    recon[r_track].map(norm_text).fillna("").astype(str) + "|" +
    num_s(recon[r_race]).fillna("").astype(str) + "|" +
    recon[r_horse].map(norm_horse).fillna("").astype(str)
)

keep = [
    "_replay_join_key_v3_1",
    "replay_probability_final",
    "replay_fair_price_final",
    "replay_probability_source",
    "probability_sum_after_v1_2",
    "normalisation_status_v1_2",
    "final_rating"
]

keep = [c for c in keep if c in recon.columns]

r = recon[keep].copy()

r = r.rename(columns={
    "replay_probability_final": "reconstructed_replay_probability_v3_1",
    "replay_fair_price_final": "reconstructed_replay_fair_price_v3_1",
    "replay_probability_source": "reconstructed_replay_probability_source_v3_1",
    "probability_sum_after_v1_2": "reconstructed_probability_sum_v3_1",
    "normalisation_status_v1_2": "reconstructed_normalisation_status_v3_1",
    "final_rating": "reconstructed_rating_v3_1"
})

r = r.drop_duplicates("_replay_join_key_v3_1", keep="first")

merged = spine.merge(
    r,
    on="_replay_join_key_v3_1",
    how="left"
)

merged["has_reconstructed_probability_v3_1"] = (
    pd.to_numeric(
        merged["reconstructed_replay_probability_v3_1"],
        errors="coerce"
    ).notna()
)

merged["pricing_replay_history_status_v3_1"] = merged["has_reconstructed_probability_v3_1"].map(
    {
        True: "REPLAY_READY_RECONSTRUCTED",
        False: "NO_RECONSTRUCTED_HISTORY"
    }
)

merged["built_at_v3_1"] = datetime.now(timezone.utc).isoformat()

merged.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "built_at": datetime.now(timezone.utc).isoformat(),
    "rows": len(merged),
    "reconstructed_probability_rows": int(merged["has_reconstructed_probability_v3_1"].sum()),
    "reconstructed_probability_coverage_pct": round(float(merged["has_reconstructed_probability_v3_1"].mean() * 100), 2),
    "unmatched_rows": int((~merged["has_reconstructed_probability_v3_1"]).sum()),
    "status": "PRICING_REPLAY_SPINE_V3_1_RECONSTRUCTED_BUILT_RESEARCH_ONLY"
}])

summary.to_csv(SUMMARY, index=False)

audit = (
    merged
    .groupby("pricing_replay_history_status_v3_1")
    .size()
    .reset_index(name="rows")
)

audit.to_csv(AUDIT, index=False)

print("[PRICING_REPLAY_SPINE_V3_1_RECONSTRUCTED] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(f"audit={AUDIT}")
print(summary.to_string(index=False))
print("")
print(audit.to_string(index=False))
