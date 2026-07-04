from pathlib import Path
import pandas as pd
import math

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HIST = DATA / "edgeiq_historical_performance_rating_v6_1_research.csv"
LIVE = DATA / "edgeiq_current_field_projection_V6_1_RESEARCH_replay.csv"
BOARD = DATA / "edgeiq_live_runner_board_governed_v1.csv"

OUT = DATA / "edgeiq_v6_1_backfilled_live_risk_v1.csv"
SUMMARY = DATA / "edgeiq_v6_1_backfilled_live_risk_summary_v1.csv"

def num(x, default=math.nan):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return default
        return float(str(x).strip())
    except Exception:
        return default

def canon(x):
    return str(x or "").strip().upper()

hist = pd.read_csv(HIST, dtype=str, keep_default_na=False, low_memory=False)
live = pd.read_csv(LIVE, dtype=str, keep_default_na=False, low_memory=False)
board = pd.read_csv(BOARD, dtype=str, keep_default_na=False, low_memory=False)

hist["horse_key"] = hist["horse"].map(canon)
live["horse_key"] = live["horse"].map(canon)
board["horse_key"] = board["horse"].map(canon)

backfilled = hist[hist["rating_v5_1_status"].eq("BACKFILLED_POWER_RATING")].copy()

agg = backfilled.groupby("horse_key").agg(
    backfilled_rows=("horse_key", "size"),
    backfilled_82_4_rows=("performance_rating_v6_1_research", lambda s: (pd.to_numeric(s, errors="coerce").round(2).eq(82.40)).sum()),
    backfilled_base82_rows=("performance_rating_v6_1_research_reason", lambda s: s.astype(str).str.contains("v6_1_base=82.00", regex=False).sum()),
    backfilled_unknown_class_rows=("race_class_clean", lambda s: s.astype(str).str.upper().eq("UNKNOWN").sum()),
    backfilled_blank_distance_rows=("distance", lambda s: s.astype(str).str.strip().eq("").sum()),
    backfilled_blank_condition_rows=("condition_recovered", lambda s: s.astype(str).str.strip().eq("").sum()),
).reset_index()

cols = [
    "race_no",
    "horse",
    "horse_key",
    "starts_found_research",
    "projected_rating_v5_2",
    "projection_gap_v5_2",
    "projection_band_v5_2",
    "projected_rating_V6_1_RESEARCH",
    "projection_gap_V6_1_RESEARCH",
    "projection_band_V6_1_RESEARCH",
    "projection_gap_delta_research_minus_v5_2",
]
live_small = live[[c for c in cols if c in live.columns]].copy()

out = live_small.merge(agg, on="horse_key", how="left")
out = out[out["backfilled_rows"].notna()].copy()

board_cols = [
    "horse_key",
    "live_price",
    "fair_price",
    "win_pct",
    "edge_pct",
    "V6_1_RESEARCH_price_rank",
    "execution_action_governed",
]
board_small = board[[c for c in board_cols if c in board.columns]].copy()
out = out.merge(board_small, on="horse_key", how="left")

def risk(row):
    starts = num(row.get("starts_found_research"))
    gap_delta = num(row.get("projection_gap_delta_research_minus_v5_2"))
    v6_band = str(row.get("projection_band_V6_1_RESEARCH", "")).upper()
    v5_band = str(row.get("projection_band_v5_2", "")).upper()
    base82 = num(row.get("backfilled_base82_rows"), 0)
    exact824 = num(row.get("backfilled_82_4_rows"), 0)

    if (
        starts <= 2
        and v6_band in {"ELITE", "STRONG"}
        and v5_band in {"NEUTRAL", "NEGATIVE", "POOR"}
        and gap_delta >= 5
        and (base82 > 0 or exact824 > 0)
    ):
        return "CRITICAL"

    if (
        starts <= 2
        and v6_band in {"ELITE", "STRONG", "POSITIVE"}
        and gap_delta >= 3
        and (base82 > 0 or exact824 > 0)
    ):
        return "HIGH"

    if starts <= 2 and (base82 > 0 or exact824 > 0):
        return "MEDIUM"

    return "LOW"

out["v6_1_backfilled_live_risk"] = out.apply(risk, axis=1)

out = out.sort_values(
    by=["v6_1_backfilled_live_risk", "race_no", "horse"],
    ascending=[True, True, True],
)

out.to_csv(OUT, index=False)

summary_rows = []
summary_rows.append({"metric": "status", "value": "AUDIT_ONLY_COMPLETE"})
summary_rows.append({"metric": "live_backfilled_exposed_runners", "value": len(out)})
for label, count in out["v6_1_backfilled_live_risk"].value_counts().items():
    summary_rows.append({"metric": f"risk_{label}", "value": int(count)})

summary_rows.append({"metric": "critical_horses", "value": ", ".join(out[out["v6_1_backfilled_live_risk"].eq("CRITICAL")]["horse"].astype(str).tolist())})

summary = pd.DataFrame(summary_rows)
summary.to_csv(SUMMARY, index=False)

print("[V6_1_BACKFILLED_LIVE_RISK_AUDIT] COMPLETE")
print(summary.to_string(index=False))
print(f"out={OUT}")
print(f"summary={SUMMARY}")
