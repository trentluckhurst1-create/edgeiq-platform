from pathlib import Path
import pandas as pd
import numpy as np
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

CARD = DATA / "edgeiq_current_field_projection_v5_2.csv"
INTEL = DATA / "edgeiq_runner_intelligence_v1.csv"
LIVE = DATA / "sportsbet_live_market_v1.csv"
PROB_V3 = DATA / "edgeiq_probability_engine_v3.csv"

OUT = DATA / "edgeiq_live_runner_board_v1.csv"
DIAG = DATA / "edgeiq_live_runner_board_v1_diagnostics.csv"
MISS = DATA / "edgeiq_live_runner_board_v1_unmatched.csv"

COUNTRY_SUFFIXES = [
    "NZ", "GB", "IRE", "FR", "USA", "SAF", "GER", "JPN", "JAP",
    "CAN", "AUS", "ARG", "CHI", "BRZ", "ITY"
]

TRACK_ALIASES = {
    "BET365 STAWELL": "STAWELL",
    "SPORTSBET GAWLER": "GAWLER",
    "PICKLEBET PARK WERRIBEE": "WERRIBEE",
}

def normalize_track(v):
    if pd.isna(v):
        return ""
    t = str(v).upper().strip()
    return TRACK_ALIASES.get(t, t)


def canon(v):
    s = str(v or "").strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"\([^)]*\)", "", s)
    for suffix in COUNTRY_SUFFIXES:
        s = re.sub(rf"\b{suffix}\b$", "", s).strip()
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s

def num(v):
    try:
        if pd.isna(v):
            return np.nan
        return float(str(v).replace("$", "").replace(",", "").strip())
    except Exception:
        return np.nan

def safe(v):
    if pd.isna(v):
        return ""
    return str(v).strip()

print("=" * 100)
print("EDGEIQ LIVE MARKET MERGE ENGINE V2 - HARD CANONICAL MATCHING")
print("=" * 100)

card = pd.read_csv(CARD, low_memory=False)
intel = pd.read_csv(INTEL, low_memory=False)
live = pd.read_csv(LIVE, low_memory=False)

if PROB_V3.exists():
    prob_v3 = pd.read_csv(PROB_V3, low_memory=False)
else:
    prob_v3 = pd.DataFrame()

for df in [card, intel, live]:
    df.columns = [c.strip() for c in df.columns]


card["horse_canon"] = card["horse"].apply(canon)

# ====================================================================================
# HARD DEDUPE ACTIVE CARD
# ====================================================================================

card["race_key"] = (
    card["track"].astype(str).str.upper().str.strip()
    + "_R"
    + card["race_no"].astype(str).str.strip()
)

before = len(card)

card = (
    card
    .sort_values(
        ["race_date"],
        ascending=False,
        na_position="last"
    )
    .drop_duplicates(
        ["race_key", "horse_canon"],
        keep="first"
    )
)

after = len(card)

print("=" * 100)
print("CARD DEDUPE")
print("=" * 100)
print("BEFORE:", before)
print("AFTER :", after)
print("REMOVED:", before - after)


intel["horse_canon"] = intel["horse"].apply(canon)

# ====================================================================================
# HARD DEDUPE INTELLIGENCE LAYER
# ====================================================================================

intel_before = len(intel)

sort_cols = []

for c in [
    "confidence_score",
    "model_confidence_score",
    "race_date",
    "timestamp",
    "edge_pct"
]:
    if c in intel.columns:
        sort_cols.append(c)

if sort_cols:

    intel = (
        intel
        .sort_values(
            sort_cols,
            ascending=False,
            na_position="last"
        )
        .drop_duplicates(
            ["horse_canon"],
            keep="first"
        )
    )

intel_after = len(intel)

print("=" * 100)
print("INTEL DEDUPE")
print("=" * 100)
print("BEFORE:", intel_before)
print("AFTER :", intel_after)
print("REMOVED:", intel_before - intel_after)

live["horse_canon"] = live["horse"].apply(canon)

live["sportsbet_price_num"] = live["sportsbet_price"].apply(num)

for optional_col in [
    "market_mover",
    "recent_odds_fluctuations",
    "bookmaker",
    "mobile_silk_image",
    "event_id",
    "market_id",
    "timestamp",
]:
    if optional_col not in live.columns:
        live[optional_col] = ""

live_small = live[
    [
        "horse_canon",
        "horse",
        "sportsbet_price_num",
        "track",
        "race_no",
        "market_mover",
        "recent_odds_fluctuations",
        "bookmaker",
        "mobile_silk_image",
        "event_id",
        "market_id",
        "timestamp",
    ]
].copy()

live_small = (
    live_small
    .sort_values(["track", "race_no", "horse_canon", "sportsbet_price_num"], na_position="last")
    .drop_duplicates(["track", "race_no", "horse_canon"], keep="first")
)

intel_small = intel.copy()

merged = card.merge(
    intel_small,
    on=["horse_canon"],
    how="left",
    suffixes=("", "_intel")
)

# IMPORTANT:
# Sportsbet racecard pages may not expose track cleanly, but they DO expose event_id.
# We first map live prices by horse only, then HARD FILTER to the captured Sportsbet event race_no.
# This prevents cross-meeting contamination like FLYING NIC appearing at HORSHAM.
merged["track"] = merged["track"].astype(str).str.upper().str.strip()
live_small["track"] = live_small["track"].astype(str).str.upper().str.strip()
merged["race_no"] = merged["race_no"].astype(str).str.replace(".0", "", regex=False).str.strip()
live_small["race_no"] = live_small["race_no"].astype(str).str.replace(".0", "", regex=False).str.strip()

print("=" * 100)
print("LIVE MERGE KEYS")
print("=" * 100)
print(["track", "race_no", "horse_canon"])

merged = merged.merge(
    live_small,
    on=["track", "race_no", "horse_canon"],
    how="left",
    suffixes=("", "_live")
)


# ====================================================================================
# MERGE V3 PROBABILITY ENGINE
# ====================================================================================

if not prob_v3.empty:

    prob_v3["horse_canon"] = prob_v3["horse"].apply(canon)

    prob_v3["track"] = prob_v3["track"].apply(normalize_track)

    prob_v3["race_no"] = (
        prob_v3["race_no"]
        .astype(str)
        .str.replace(".0", "", regex=False)
        .str.strip()
    )

    prob_small = prob_v3[[
        "track",
        "race_no",
        "horse_canon",
        "v3_probability",
        "v3_fair_price",
        "v3_overlay_pct",
        "v3_realism_grade",
        "v3_pricing_action",
        "post_v3_execution_action",
        "v3_reason"
    ]].copy()

    prob_small["v3_fair_price_num"] = pd.to_numeric(prob_small["v3_fair_price"], errors="coerce")
    prob_small["v3_overlay_pct_num"] = pd.to_numeric(prob_small["v3_overlay_pct"], errors="coerce")

    prob_small = (
        prob_small
        .sort_values(
            ["track", "race_no", "horse_canon", "v3_fair_price_num", "v3_overlay_pct_num"],
            na_position="last"
        )
        .drop_duplicates(["track", "race_no", "horse_canon"], keep="first")
        .drop(columns=["v3_fair_price_num", "v3_overlay_pct_num"], errors="ignore")
    )

    merged = merged.merge(
        prob_small,
        on=["track", "race_no", "horse_canon"],
        how="left"
    )


# Old horse-only race_no filter removed.
# Live merge is now strict on track + race_no + horse_canon, so no blanking block is required.


# Merge V5.2 projection/fair-price context directly into the live board before execution logic.
# This prevents V3 market-anchored prices from creating WATCH rows without model support.
fair_review_path = DATA / "edgeiq_current_fair_prices_review_v5_2.csv"
if fair_review_path.exists():
    fair_ctx = pd.read_csv(fair_review_path, dtype=str, keep_default_na=False, low_memory=False)
    if "horse" in fair_ctx.columns:
        fair_ctx["horse_canon"] = fair_ctx["horse"].apply(canon)

        fair_cols = [
            "race_date",
            "track",
            "race_no",
            "horse_canon",
            "projected_rating_v5_2",
            "race_target_rating_v5_2",
            "projection_gap_v5_2",
            "projection_band_v5_2",
            "projection_confidence_v5_2",
            "rated_price_status_v5_2_review",
        ]

        for col in fair_cols:
            if col not in fair_ctx.columns:
                fair_ctx[col] = ""

        fair_small = (
            fair_ctx[fair_cols]
            .drop_duplicates(["race_date", "track", "race_no", "horse_canon"], keep="first")
        )

        for col in [
            "projected_rating_v5_2",
            "race_target_rating_v5_2",
            "projection_gap_v5_2",
            "projection_band_v5_2",
            "projection_confidence_v5_2",
            "rated_price_status_v5_2_review",
        ]:
            if col in merged.columns:
                merged = merged.drop(columns=[col])

        merged = merged.merge(
            fair_small,
            on=["race_date", "track", "race_no", "horse_canon"],
            how="left",
        )

rows = []

for _, r in merged.iterrows():
    horse = safe(r.get("horse"))
    live_price = num(r.get("sportsbet_price_num"))
    # V3 is now the ONLY authoritative live fair price source.
    # No fallback to legacy fair_price/rated_price, because that reintroduces fake overlays.
    fair_price = num(r.get("v3_fair_price"))

    edge_pct = np.nan
    if not pd.isna(live_price) and not pd.isna(fair_price) and fair_price > 0:
        edge_pct = round(((live_price / fair_price) - 1) * 100, 1)

    confidence = num(r.get("confidence_score"))
    if pd.isna(confidence):
        confidence = 35

    realism = safe(r.get("v3_realism_grade"))
    v3_action = safe(r.get("post_v3_execution_action"))

    # Hard safety gate: only suppress rows that V3 itself currently marks as no-live.
    # Do not use stale post_v3_execution_action here; it can carry old NO_LIVE values.
    pricing_action = safe(r.get("v3_pricing_action"))
    stale_v3 = realism == "NO_LIVE_MARKET" or pricing_action == "NO_LIVE_PRICE"

    if pd.isna(live_price):
        execution = "NO LIVE"

    elif stale_v3:
        fair_price = np.nan
        edge_pct = np.nan
        execution = "SUPPRESS_STALE_V3"

    elif realism in ["EXTREME_FAKE_OVERLAY", "LOW_CONFIDENCE_FAKE_OVERLAY"]:
        execution = "SUPPRESS"

    elif edge_pct >= 18 and confidence >= 70:
        execution = "EXECUTE"

    elif edge_pct >= 10 and confidence >= 55:
        execution = "STRONG_WATCH"

    elif edge_pct >= 6:
        execution = "WATCH"

    elif edge_pct <= -18:
        execution = "UNDERLAY"

    else:
        execution = "PASS"

    projection_band = safe(r.get("projection_band_v5_2"))
    projection_confidence = safe(r.get("projection_confidence_v5_2"))
    weak_projection = projection_band in ["POOR", "NO_PROJECTION", ""] or projection_confidence in ["LOW", "VERY_LOW", ""]

    if pd.isna(live_price):
        execution = "NO LIVE"
    elif pricing_action in ["PASS", "NO_EDGE"]:
        execution = "PASS"
    elif pricing_action in ["SUPPRESS", "SUPPRESS_FAKE_OVERLAY"]:
        execution = "SUPPRESS"
    elif pricing_action in ["WATCH", "ALLOW_REALISTIC"] and weak_projection:
        execution = "PASS"
    elif pricing_action in ["WATCH", "ALLOW_REALISTIC"]:
        execution = "WATCH"
    elif pricing_action == "UNDERLAY":
        execution = "UNDERLAY"
    elif v3_action and v3_action not in ["NO LIVE", "NO_LIVE", "NO_LIVE_PRICE"]:
        execution = v3_action

    mover_raw = safe(r.get("market_mover")).upper()
    flucs = safe(r.get("recent_odds_fluctuations"))

    market_state = "STABLE"
    if mover_raw in ["TRUE", "STEAMING", "STEAM"]:
        market_state = "STEAM"
    elif mover_raw in ["DRIFTING", "DRIFT"]:
        market_state = "DRIFT"

    rows.append({
        "race_date": safe(r.get("race_date")),
        "track": safe(r.get("track")),
        "race_no": r.get("race_no"),
        "horse_no": r.get("horse_no"),
        "horse": horse,
        "horse_canon": r.get("horse_canon"),
        "projected_rating_v5_2": safe(r.get("projected_rating_v5_2")),
        "distance": r.get("distance"),
        "track_condition": r.get("track_condition"),
        "rail_position": r.get("rail_position"),
        "barrier": r.get("barrier"),
        "jockey": safe(r.get("jockey")),
        "trainer": safe(r.get("trainer")),

        "live_price": live_price,
        "fair_price": fair_price,
        "edge_pct": edge_pct,
        "execution_action": execution,
        "v3_probability": r.get("v3_probability"),
        "v3_realism_grade": safe(r.get("v3_realism_grade")),
        "v3_pricing_action": safe(r.get("v3_pricing_action")),

        "confidence_score": confidence,
        "run_style": safe(r.get("run_style")),
        "projected_spd": r.get("projected_spd"),
        "settling_band": safe(r.get("settling_band")),
        "dna_confidence": safe(r.get("dna_confidence")),
        "archetype": safe(r.get("archetype")),

        "late_power_index": r.get("late_power_index"),
        "fatigue_risk_index": r.get("fatigue_risk_index"),
        "sectional_weapon_score": r.get("sectional_weapon_score"),

        "market_state": market_state,
        "market_mover": mover_raw,
        "movement_velocity": flucs,
        "bookmaker": safe(r.get("bookmaker")),
        "sportsbet_event_id": safe(r.get("event_id")),
        "sportsbet_market_id": safe(r.get("market_id")),
        "sportsbet_timestamp": safe(r.get("timestamp")),
        "mobile_silk_image": safe(r.get("mobile_silk_image")),

        "intelligence_note": safe(r.get("intelligence_note")),
    })

out = pd.DataFrame(rows)

out["live_rank"] = out.groupby(["track", "race_no"])["live_price"].rank(method="dense")
out["fair_rank"] = out.groupby(["track", "race_no"])["fair_price"].rank(method="dense")
out["edge_rank"] = out.groupby(["track", "race_no"])["edge_pct"].rank(ascending=False, method="dense")


# EDGEIQ SAFETY FIX:
# BASELINE_NO_HISTORY runners are unrated/unraced in the fair-price review.
# They must never create overlay/watch/execute decisions.
fair_review_path = Path(__file__).resolve().parents[1] / "public" / "data" / "edgeiq_current_fair_prices_review_v5_2.csv"

if fair_review_path.exists():
    fair_review = pd.read_csv(fair_review_path, dtype=str, keep_default_na=False, low_memory=False)
    if {"race_date", "track", "race_no", "horse", "rated_price_status_v5_2_review"}.issubset(fair_review.columns):
        fair_review["horse_canon"] = fair_review["horse"].apply(canon)
        projection_keep_cols = [
            "race_date",
            "track",
            "race_no",
            "horse_canon",
            "projected_rating_v5_2",
            "race_target_rating_v5_2",
            "projection_gap_v5_2",
            "projection_band_v5_2",
            "projection_confidence_v5_2",
            "rated_price_status_v5_2_review",
        ]

        for col in projection_keep_cols:
            if col not in fair_review.columns:
                fair_review[col] = ""

        status_keep = fair_review[
            projection_keep_cols
        ].drop_duplicates(["race_date", "track", "race_no", "horse_canon"], keep="first")

        for col in [
            "projected_rating_v5_2",
            "race_target_rating_v5_2",
            "projection_gap_v5_2",
            "projection_band_v5_2",
            "projection_confidence_v5_2",
            "rated_price_status_v5_2_review",
        ]:
            if col in out.columns:
                out = out.drop(columns=[col])

        out = out.merge(
            status_keep,
            on=["race_date", "track", "race_no", "horse_canon"],
            how="left",
        )

        no_hist_mask = out["rated_price_status_v5_2_review"].astype(str).eq("BASELINE_NO_HISTORY")

        out.loc[no_hist_mask, "fair_price"] = np.nan
        out.loc[no_hist_mask, "edge_pct"] = np.nan
        out.loc[no_hist_mask, "execution_action"] = "NO_HISTORY"
        out.loc[no_hist_mask, "market_state"] = "NO_HISTORY"
        out.loc[no_hist_mask, "confidence_score"] = 0

out.to_csv(OUT, index=False)

unmatched = out[out["live_price"].isna()][
    ["race_date", "track", "race_no", "horse", "horse_canon", "fair_price", "projected_spd", "settling_band"]
].copy()

unmatched.to_csv(MISS, index=False)

diag = pd.DataFrame([{
    "rows": len(out),
    "live_market_rows": len(live),
    "live_unique_canon": live["horse_canon"].nunique(),
    "card_unique_canon": card["horse_canon"].nunique(),
    "with_live_price": int(out["live_price"].notna().sum()),
    "with_edge": int(out["edge_pct"].notna().sum()),
    "execute": int((out["execution_action"] == "EXECUTE").sum()),
    "watch": int((out["execution_action"] == "WATCH").sum()),
    "pass": int((out["execution_action"] == "PASS").sum()),
    "underlay": int((out["execution_action"] == "UNDERLAY").sum()),
    "no_live": int((out["execution_action"] == "NO LIVE").sum()),
}])

diag.to_csv(DIAG, index=False)

print()
print("=" * 100)
print("LIVE RUNNER BOARD V2 COMPLETE")
print("=" * 100)
print(diag.to_string(index=False))

print()
print("=" * 100)
print("MATCHED LIVE PRICE PREVIEW")
print("=" * 100)
matched = out[out["live_price"].notna()]
if matched.empty:
    print("NO LIVE MATCHES - CHECK unmatched file")
else:
    print(matched[[
        "track", "race_no", "horse", "live_price", "fair_price", "edge_pct",
        "execution_action", "market_state", "projected_spd", "settling_band", "confidence_score"
    ]].head(50).to_string(index=False))

print()
print("=" * 100)
print("FILES WRITTEN")
print("=" * 100)
print(OUT)
print(DIAG)
print(MISS)












