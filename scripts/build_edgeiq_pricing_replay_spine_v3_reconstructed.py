from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

SPINE = DATA / "edgeiq_pricing_replay_spine_v2.csv"
RECON = DATA / "edgeiq_pricing_replay_model_state_reconstruction_v1_2.csv"

OUT = DATA / "edgeiq_pricing_replay_spine_v3_reconstructed.csv"
SUMMARY = DATA / "edgeiq_pricing_replay_spine_v3_reconstructed_summary.csv"

print("[PRICING_REPLAY_SPINE_V3_RECONSTRUCTED] START")

spine = pd.read_csv(SPINE, low_memory=False)
recon = pd.read_csv(RECON, low_memory=False)

def find_col(df, names):
    lower = {c.lower(): c for c in df.columns}
    for n in names:
        if n.lower() in lower:
            return lower[n.lower()]
    return None

spine_runner_key = find_col(spine, ["runner_key", "join_key"])
recon_runner_key = find_col(recon, ["runner_key"])

if not spine_runner_key:
    raise RuntimeError("No runner_key/join_key found in replay spine")

if not recon_runner_key:
    raise RuntimeError("No runner_key found in reconstruction file")

keep = [
    recon_runner_key,
    "replay_probability_final",
    "replay_fair_price_final",
    "replay_probability_source",
    "probability_sum_after_v1_2",
    "normalisation_status_v1_2",
    "final_rating"
]

keep = [c for c in keep if c in recon.columns]

r = recon[keep].copy()

rename = {
    recon_runner_key: spine_runner_key,
    "replay_probability_final": "reconstructed_replay_probability_v3",
    "replay_fair_price_final": "reconstructed_replay_fair_price_v3",
    "replay_probability_source": "reconstructed_replay_probability_source_v3",
    "probability_sum_after_v1_2": "reconstructed_probability_sum_v3",
    "normalisation_status_v1_2": "reconstructed_normalisation_status_v3",
    "final_rating": "reconstructed_rating_v3"
}

r = r.rename(columns=rename)

merged = spine.merge(
    r,
    on=spine_runner_key,
    how="left"
)

merged["has_reconstructed_probability_v3"] = (
    pd.to_numeric(
        merged["reconstructed_replay_probability_v3"],
        errors="coerce"
    ).notna()
)

merged["pricing_replay_history_status_v3"] = merged["has_reconstructed_probability_v3"].map(
    {
        True: "REPLAY_READY_RECONSTRUCTED",
        False: "NO_RECONSTRUCTED_HISTORY"
    }
)

merged["built_at_v3"] = datetime.now(timezone.utc).isoformat()

merged.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "built_at": datetime.now(timezone.utc).isoformat(),
    "rows": len(merged),
    "races": merged["race_key"].nunique() if "race_key" in merged.columns else "",
    "reconstructed_probability_rows": int(merged["has_reconstructed_probability_v3"].sum()),
    "reconstructed_probability_coverage_pct": round(float(merged["has_reconstructed_probability_v3"].mean() * 100), 2),
    "status": "PRICING_REPLAY_SPINE_V3_RECONSTRUCTED_BUILT_RESEARCH_ONLY"
}])

summary.to_csv(SUMMARY, index=False)

print("[PRICING_REPLAY_SPINE_V3_RECONSTRUCTED] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(summary.to_string(index=False))
