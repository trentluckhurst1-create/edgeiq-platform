import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PROJ = DATA / "edgeiq_runner_projection_v3.csv"
REPAIRED_MARKET = DATA / "edgeiq_vic_live_terminal_feed_v1_market_repaired.csv"

OUT = DATA / "edgeiq_rated_price_engine_v3_sandbox.csv"
AUDIT = DATA / "edgeiq_rated_price_engine_v3_sandbox_audit.csv"

print("=" * 90)
print("EDGEIQ RATED PRICE ENGINE V3 SANDBOX")
print("=" * 90)

if not PROJ.exists():
    raise FileNotFoundError(PROJ)

proj = pd.read_csv(PROJ, low_memory=False)
market = pd.read_csv(REPAIRED_MARKET, low_memory=False) if REPAIRED_MARKET.exists() else pd.DataFrame()

def norm(x):
    return str(x).upper().strip()

def to_num(s):
    return pd.to_numeric(s, errors="coerce")

def pick(df, names):
    for n in names:
        if n in df.columns:
            return n
    return None

horse_col = pick(proj, ["horse", "runner", "runner_name"])
track_col = pick(proj, ["track"])
race_no_col = pick(proj, ["race_no"])
gap_col = pick(proj, ["rating_gap_v3"])
proj_col = pick(proj, ["projected_rating_v3"])
target_col = pick(proj, ["target_rating_v3"])
gap_band_col = pick(proj, ["gap_band"])
proj_conf_col = pick(proj, ["projection_confidence"])
target_conf_col = pick(proj, ["target_confidence"])

required = {
    "horse": horse_col,
    "track": track_col,
    "race_no": race_no_col,
    "rating_gap_v3": gap_col,
    "projected_rating_v3": proj_col,
    "target_rating_v3": target_col,
    "gap_band": gap_band_col,
    "projection_confidence": proj_conf_col,
    "target_confidence": target_conf_col,
}
missing = [k for k, v in required.items() if v is None]
if missing:
    print("PROJECTION COLUMNS:", list(proj.columns))
    raise ValueError(f"Missing projection columns: {missing}")

df = proj.copy()

df["_horse_key"] = df[horse_col].map(norm)
df["_track_key"] = df[track_col].map(norm)
df["_race_key"] = df[race_no_col].astype(str).str.replace(".0", "", regex=False).str.strip()

df["projected_rating_v3"] = to_num(df[proj_col])
df["target_rating_v3"] = to_num(df[target_col])
df["rating_gap_v3"] = to_num(df[gap_col])

# Attach repaired live market prices if available.
df["sportsbet_price"] = np.nan
if not market.empty:
    mh = pick(market, ["horse", "runner", "runner_name"])
    mt = pick(market, ["track"])
    mr = pick(market, ["race_no"])
    mp = pick(market, ["sportsbet_price", "market_price", "current_price"])
    if mh and mt and mr and mp:
        m = market.copy()
        m["_horse_key"] = m[mh].map(norm)
        m["_track_key"] = m[mt].map(norm)
        m["_race_key"] = m[mr].astype(str).str.replace(".0", "", regex=False).str.strip()
        m["sportsbet_price_market"] = to_num(m[mp])
        m = m[["_horse_key", "_track_key", "_race_key", "sportsbet_price_market"]].dropna()
        m = m.drop_duplicates(["_horse_key", "_track_key", "_race_key"], keep="last")
        df = df.merge(m, on=["_horse_key", "_track_key", "_race_key"], how="left")
        df["sportsbet_price"] = df["sportsbet_price_market"]

# Convert rating gap to a raw probability score.
# This is intentionally conservative: ratings are not prices yet.
gap = df["rating_gap_v3"]

raw_prob = 1 / (1 + np.exp(-(gap.fillna(-99) / 5.5)))

# Base shrinkage by confidence.
proj_conf = df[proj_conf_col].astype(str).str.upper()
target_conf = df[target_conf_col].astype(str).str.upper()

confidence_multiplier = np.select(
    [
        proj_conf.eq("HIGH") & target_conf.eq("HIGH"),
        proj_conf.eq("HIGH") & target_conf.eq("MEDIUM"),
        proj_conf.eq("MEDIUM") & target_conf.isin(["HIGH", "MEDIUM"]),
        proj_conf.eq("LOW"),
        proj_conf.eq("NO_HISTORY"),
    ],
    [
        1.00,
        0.85,
        0.75,
        0.45,
        0.00,
    ],
    default=0.55,
)

# Blend toward a neutral long-run runner probability.
# This avoids fake overconfidence when target joins are LOW.
neutral_prob = 0.08
df["rated_probability_v3"] = (
    raw_prob * confidence_multiplier +
    neutral_prob * (1 - confidence_multiplier)
)

# Cap probabilities to sane pre-market sandbox bounds.
df["rated_probability_v3"] = df["rated_probability_v3"].clip(lower=0.005, upper=0.55)

df["rated_price_v3"] = np.where(
    df["rated_probability_v3"] > 0,
    1 / df["rated_probability_v3"],
    np.nan
)

df["rated_price_v3"] = np.round(df["rated_price_v3"], 2)

df["market_implied_probability"] = np.where(
    df["sportsbet_price"].notna() & (df["sportsbet_price"] > 0),
    1 / df["sportsbet_price"],
    np.nan
)

df["rated_overlay_pct_v3"] = np.where(
    df["sportsbet_price"].notna() & df["rated_price_v3"].notna() & (df["rated_price_v3"] > 0),
    ((df["sportsbet_price"] / df["rated_price_v3"]) - 1) * 100,
    np.nan
)

df["rated_overlay_pct_v3"] = np.round(df["rated_overlay_pct_v3"], 1)

df["price_action_v3"] = np.select(
    [
        proj_conf.eq("NO_HISTORY"),
        df["sportsbet_price"].isna(),
        df["rated_overlay_pct_v3"] >= 25,
        df["rated_overlay_pct_v3"] >= 10,
        df["rated_overlay_pct_v3"] <= -20,
    ],
    [
        "NO_HISTORY_NO_PRICE_TRUST",
        "NO_MARKET_PRICE",
        "POTENTIAL_VALUE_AUDIT",
        "WATCH_VALUE",
        "MARKET_SHORTER_THAN_MODEL",
    ],
    default="NO_EDGE",
)

df["price_audit_flag"] = np.select(
    [
        proj_conf.eq("NO_HISTORY") & df["rated_price_v3"].notna(),
        target_conf.eq("LOW") & (df["rated_overlay_pct_v3"].fillna(0) >= 10),
        df["sportsbet_price"].isna(),
        df["rated_price_v3"].isna(),
    ],
    [
        "NO_HISTORY_PRICE_SUPPRESSED",
        "LOW_TARGET_CONFIDENCE_OVERLAY_RISK",
        "MISSING_MARKET_PRICE",
        "MISSING_RATED_PRICE",
    ],
    default="OK",
)

out_cols = [
    horse_col,
    track_col,
    race_no_col,
    proj_col,
    target_col,
    gap_col,
    gap_band_col,
    proj_conf_col,
    target_conf_col,
    "sportsbet_price",
    "rated_probability_v3",
    "rated_price_v3",
    "rated_overlay_pct_v3",
    "price_action_v3",
    "price_audit_flag",
]

out = df[out_cols].copy()
out = out.rename(columns={
    horse_col: "horse",
    track_col: "track",
    race_no_col: "race_no",
    proj_col: "projected_rating_v3",
    target_col: "target_rating_v3",
    gap_col: "rating_gap_v3",
    gap_band_col: "gap_band",
    proj_conf_col: "projection_confidence",
    target_conf_col: "target_confidence",
})

out["built_at"] = datetime.now().isoformat(timespec="seconds")
out.to_csv(OUT, index=False)

audit = pd.DataFrame([
    {"metric": "rows_loaded", "value": len(df)},
    {"metric": "rows_written", "value": len(out)},
    {"metric": "market_prices_available", "value": int(out["sportsbet_price"].notna().sum())},
    {"metric": "market_prices_missing", "value": int(out["sportsbet_price"].isna().sum())},
    {"metric": "rated_prices_created", "value": int(out["rated_price_v3"].notna().sum())},
    {"metric": "no_history_count", "value": int(out["projection_confidence"].astype(str).str.upper().eq("NO_HISTORY").sum())},
    {"metric": "potential_value_audit_count", "value": int(out["price_action_v3"].eq("POTENTIAL_VALUE_AUDIT").sum())},
    {"metric": "watch_value_count", "value": int(out["price_action_v3"].eq("WATCH_VALUE").sum())},
    {"metric": "low_target_confidence_overlay_risk", "value": int(out["price_audit_flag"].eq("LOW_TARGET_CONFIDENCE_OVERLAY_RISK").sum())},
])
audit.to_csv(AUDIT, index=False)

print(f"wrote: {OUT}")
print(f"wrote: {AUDIT}")
print(audit.to_string(index=False))
print("=" * 90)
