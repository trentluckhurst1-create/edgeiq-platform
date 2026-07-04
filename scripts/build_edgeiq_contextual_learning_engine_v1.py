from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path.cwd()
DATA = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"

CONTEXT = DATA / "edgeiq_contextual_probability_engine_v5.csv"
RESULTS = DATA / "edgeiq_results_master.csv"

OUT = DATA / "edgeiq_contextual_learning_engine_v1.csv"
SUMMARY = DATA / "edgeiq_contextual_learning_summary_v1.csv"

def safe(v):
    if pd.isna(v):
        return ""
    return str(v).strip()

def num(v, default=np.nan):
    try:
        if pd.isna(v):
            return default
        return float(str(v).replace("$","").replace(",","").strip())
    except Exception:
        return default

print("=" * 100)
print("EDGEIQ CONTEXTUAL LEARNING ENGINE V1")
print("=" * 100)

ctx = pd.read_csv(CONTEXT, low_memory=False)

if RESULTS.exists():
    res = pd.read_csv(RESULTS, low_memory=False)
else:
    res = pd.DataFrame()

for df in [ctx, res]:
    if not df.empty:
        df.columns = [c.strip() for c in df.columns]

# =============================================================================
# RESULT MERGE
# =============================================================================

if not res.empty:

    merge_cols = [
        c for c in [
            "race_date",
            "track",
            "race_no",
            "horse",
            "finish_position",
            "won",
            "placed",
            "sp",
            "official_sp",
            "closing_price",
            "profit",
            "result"
        ]
        if c in res.columns
    ]

    res_small = res[merge_cols].copy()

    out = ctx.merge(
        res_small,
        how="left",
        on=["race_date","track","race_no","horse"]
    )

else:
    out = ctx.copy()

# =============================================================================
# LEARNING FLAGS
# =============================================================================

out["won_flag"] = np.where(
    pd.to_numeric(out.get("finish_position"), errors="coerce") == 1,
    1,
    0
)

finish_pos = pd.to_numeric(
    out["finish_position"] if "finish_position" in out.columns else np.nan,
    errors="coerce"
)

out["placed_flag"] = np.where(
    (finish_pos >= 1) & (finish_pos <= 3),
    1,
    0
)

out["overlay_flag"] = np.where(
    pd.to_numeric(out.get("v5_contextual_overlay_pct"), errors="coerce") >= 10,
    1,
    0
)

out["elite_overlay_flag"] = np.where(
    pd.to_numeric(out.get("v5_contextual_overlay_pct"), errors="coerce") >= 18,
    1,
    0
)

out["positive_tempo_flag"] = np.where(
    out.get("tempo_fit_v2","").astype(str).str.upper() == "ADVANTAGED",
    1,
    0
)

out["negative_tempo_flag"] = np.where(
    out.get("tempo_fit_v2","").astype(str).str.upper() == "DISADVANTAGED",
    1,
    0
)

# =============================================================================
# CONTEXTUAL CLUSTERS
# =============================================================================

out["learning_cluster"] = (
    out.get("projected_race_shape","").astype(str)
    + " | "
    + out.get("proxy_energy_archetype","").astype(str)
    + " | "
    + out.get("tempo_fit_v2","").astype(str)
)

# =============================================================================
# ROI CALCULATION
# =============================================================================

out["assumed_stake"] = 1.0

price_col = None

for c in [
    "closing_price",
    "official_sp",
    "sp",
    "market_price"
]:
    if c in out.columns:
        price_col = c
        break

if price_col:
    out["return"] = np.where(
        out["won_flag"] == 1,
        pd.to_numeric(out[price_col], errors="coerce"),
        0
    )
else:
    out["return"] = 0

out["profit_loss"] = out["return"] - out["assumed_stake"]

# =============================================================================
# LEARNING SUMMARY
# =============================================================================

group_cols = [
    "projected_race_shape",
    "proxy_energy_archetype",
    "tempo_fit_v2",
]

summary = (
    out.groupby(group_cols, dropna=False)
    .agg(
        runners=("horse","count"),
        winners=("won_flag","sum"),
        placers=("placed_flag","sum"),
        overlays=("overlay_flag","sum"),
        elite_overlays=("elite_overlay_flag","sum"),
        total_profit=("profit_loss","sum"),
        avg_overlay=("v5_contextual_overlay_pct","mean"),
        avg_prob=("v5_contextual_probability","mean"),
    )
    .reset_index()
)

summary["win_rate"] = (
    summary["winners"] / summary["runners"]
).round(4)

summary["place_rate"] = (
    summary["placers"] / summary["runners"]
).round(4)

summary["roi"] = (
    summary["total_profit"] / summary["runners"]
).round(4)

summary["learning_signal"] = np.where(
    (summary["roi"] > 0.10)
    & (summary["runners"] >= 5),
    "POSITIVE_SIGNAL",

    np.where(
        (summary["roi"] < -0.10)
        & (summary["runners"] >= 5),
        "NEGATIVE_SIGNAL",
        "INSUFFICIENT_SAMPLE"
    )
)

summary = summary.sort_values(
    ["roi","win_rate"],
    ascending=False
)

# =============================================================================
# SAVE
# =============================================================================

out.to_csv(OUT, index=False)
summary.to_csv(SUMMARY, index=False)

# =============================================================================
# PRINT
# =============================================================================

print()
print("=" * 100)
print("LEARNING SUMMARY")
print("=" * 100)

diag = pd.DataFrame([{
    "rows": len(out),
    "learning_clusters": summary.shape[0],
    "winners": int(out["won_flag"].sum()),
    "placed": int(out["placed_flag"].sum()),
    "overlay_runners": int(out["overlay_flag"].sum()),
    "elite_overlays": int(out["elite_overlay_flag"].sum()),
    "avg_overlay": round(
        pd.to_numeric(out["v5_contextual_overlay_pct"], errors="coerce").mean(),
        2
    ),
}])

print(diag.to_string(index=False))

print()
print("=" * 100)
print("TOP LEARNING SIGNALS")
print("=" * 100)

cols = [
    "projected_race_shape",
    "proxy_energy_archetype",
    "tempo_fit_v2",
    "runners",
    "winners",
    "win_rate",
    "roi",
    "avg_overlay",
    "learning_signal",
]

print(
    summary[cols]
    .head(40)
    .to_string(index=False)
)

print()
print("SAVED:")
print(OUT)
print(SUMMARY)

