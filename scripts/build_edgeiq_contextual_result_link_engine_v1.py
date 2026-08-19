from pathlib import Path
import pandas as pd
import numpy as np
import re
import unicodedata

ROOT = Path.cwd()
DATA = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"

CONTEXT = DATA / "edgeiq_contextual_probability_engine_v5.csv"
RESULTS = DATA / "edgeiq_results_master.csv"

OUT = DATA / "edgeiq_contextual_result_link_v1.csv"
DIAG = DATA / "edgeiq_contextual_result_link_v1_diagnostics.csv"

COUNTRY_SUFFIXES = [
    "NZ","GB","IRE","FR","USA","SAF","GER","JPN","JAP",
    "CAN","AUS","ARG","CHI","BRZ","ITY"
]

TRACK_ALIASES = {
    "BET365 STAWELL": "STAWELL",
    "SPORTSBET GAWLER": "GAWLER",
    "PICKLEBET PARK WERRIBEE": "WERRIBEE",
}

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

def canon(v):
    s = safe(v).upper()

    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")

    s = re.sub(r"\([^)]*\)", "", s)

    for suffix in COUNTRY_SUFFIXES:
        s = re.sub(rf"\b{suffix}\b$", "", s).strip()

    s = s.replace("&", "AND")
    s = re.sub(r"[^A-Z0-9]", "", s)

    return s

def norm_track(v):
    s = safe(v).upper()
    return TRACK_ALIASES.get(s, s)

def norm_race(v):
    s = safe(v)
    if s.endswith(".0"):
        s = s[:-2]
    return s

def build_key(track, race_no, horse):

    track_key = norm_track(track)
    race_key = norm_race(race_no)
    horse_key = canon(horse)

    race_id = f"{track_key}_R{race_key}"

    return f"{race_id}_{horse_key}"

print("=" * 100)
print("EDGEIQ CONTEXTUAL RESULT LINK ENGINE V1")
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
# BUILD UNIVERSAL KEYS
# =============================================================================

ctx["universal_runner_key"] = ctx.apply(
    lambda r: build_key(
        r.get("track"),
        r.get("race_no"),
        r.get("horse")
    ),
    axis=1
)

if not res.empty:

    res["universal_runner_key"] = res.apply(
        lambda r: build_key(
            r.get("track"),
            r.get("race_no"),
            r.get("horse")
        ),
        axis=1
    )

# =============================================================================
# RESULT CLEANING
# =============================================================================

if not res.empty:

    if "finish_position" not in res.columns:

        if "placing" in res.columns:
            res["finish_position"] = res["placing"]

        elif "position" in res.columns:
            res["finish_position"] = res["position"]

        else:
            res["finish_position"] = np.nan

    res["finish_position"] = pd.to_numeric(
        res["finish_position"],
        errors="coerce"
    )

    res["won_flag"] = np.where(
        res["finish_position"] == 1,
        1,
        0
    )

    res["placed_flag"] = np.where(
        (res["finish_position"] >= 1)
        & (res["finish_position"] <= 3),
        1,
        0
    )

# =============================================================================
# MERGE
# =============================================================================

if not res.empty:

    keep_cols = [
        c for c in [
            "universal_runner_key",
            "finish_position",
            "won_flag",
            "placed_flag",
            "official_sp",
            "sp",
            "closing_price",
            "profit",
            "result",
            "track",
            "race_no",
            "horse"
        ]
        if c in res.columns
    ]

    res_small = (
        res[keep_cols]
        .sort_values(
            ["won_flag"],
            ascending=False
        )
        .drop_duplicates(
            ["universal_runner_key"],
            keep="first"
        )
    )

    out = ctx.merge(
        res_small,
        how="left",
        on="universal_runner_key",
        suffixes=("", "_result")
    )

else:
    out = ctx.copy()

# =============================================================================
# MATCH DIAGNOSTICS
# =============================================================================

out["result_linked"] = np.where(
    out["finish_position"].notna(),
    1,
    0
)

out["won_flag"] = pd.to_numeric(
    out.get("won_flag"),
    errors="coerce"
).fillna(0)

out["placed_flag"] = pd.to_numeric(
    out.get("placed_flag"),
    errors="coerce"
).fillna(0)

# =============================================================================
# LEARNING METRICS
# =============================================================================

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

# =============================================================================
# PROFIT MODEL
# =============================================================================

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

    out["sim_return"] = np.where(
        out["won_flag"] == 1,
        pd.to_numeric(out[price_col], errors="coerce"),
        0
    )

else:
    out["sim_return"] = 0

out["sim_stake"] = 1.0

out["sim_profit"] = (
    out["sim_return"]
    - out["sim_stake"]
)

# =============================================================================
# SAVE
# =============================================================================

out.to_csv(OUT, index=False)

diag = pd.DataFrame([{
    "rows": len(out),
    "results_rows": len(res) if not res.empty else 0,
    "linked_results": int(out["result_linked"].sum()),
    "link_rate_pct": round(
        (out["result_linked"].mean() * 100),
        2
    ),
    "winners": int(out["won_flag"].sum()),
    "placers": int(out["placed_flag"].sum()),
    "overlay_runners": int(out["overlay_flag"].sum()),
    "elite_overlay_runners": int(out["elite_overlay_flag"].sum()),
    "sim_profit": round(
        pd.to_numeric(out["sim_profit"], errors="coerce").sum(),
        2
    )
}])

diag.to_csv(DIAG, index=False)

# =============================================================================
# PRINT
# =============================================================================

print()
print("=" * 100)
print("RESULT LINK SUMMARY")
print("=" * 100)

print(diag.to_string(index=False))

print()
print("=" * 100)
print("TOP LINKED CONTEXTUAL RUNNERS")
print("=" * 100)

cols = [
    "track",
    "race_no",
    "horse",
    "v5_contextual_overlay_pct",
    "projected_race_shape",
    "proxy_energy_archetype",
    "tempo_fit_v2",
    "finish_position",
    "won_flag",
    "placed_flag",
    "sim_profit"
]

cols = [c for c in cols if c in out.columns]

linked = out[out["result_linked"] == 1]

if not linked.empty:

    print(
        linked.sort_values(
            ["won_flag","sim_profit"],
            ascending=False
        )[cols]
        .head(40)
        .to_string(index=False)
    )

else:
    print("NO RESULT LINKS YET")

print()
print("SAVED:")
print(OUT)
print(DIAG)

