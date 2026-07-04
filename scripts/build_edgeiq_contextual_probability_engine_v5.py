from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path.cwd()
DATA = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"

SRC = DATA / "edgeiq_horse_energy_proxy_v1.csv"

OUT = DATA / "edgeiq_contextual_probability_engine_v5.csv"
DIAG = DATA / "edgeiq_contextual_probability_engine_v5_diagnostics.csv"

def num(v, default=np.nan):
    try:
        if pd.isna(v):
            return default
        return float(str(v).replace("$","").replace(",","").strip())
    except Exception:
        return default

def safe(v):
    if pd.isna(v):
        return ""
    return str(v).strip()

def contextual_v5(row):
    base_prob = num(row.get("contextual_probability"))
    if pd.isna(base_prob):
        base_prob = num(row.get("v3_probability"))

    market_prob = num(row.get("market_probability"))
    price = num(row.get("market_price"))

    if pd.isna(base_prob):
        return {
            "v5_energy_source": "NONE",
            "v5_energy_bonus": 0,
            "v5_energy_penalty": 0,
            "v5_contextual_probability": np.nan,
            "v5_contextual_fair_price": np.nan,
            "v5_contextual_overlay_pct": np.nan,
            "v5_contextual_action": "NO_PROBABILITY",
            "v5_contextual_reason": "missing probability"
        }

    real_source = safe(row.get("energy_source_type")).upper()
    proxy_tier = safe(row.get("proxy_energy_tier")).upper()
    proxy_fit = safe(row.get("proxy_tempo_fit")).upper()
    proxy_score = num(row.get("proxy_energy_score"), 50)
    proxy_conf = num(row.get("proxy_confidence_score"), 0)

    real_tier = safe(row.get("energy_edge_tier")).upper()
    real_conf = safe(row.get("energy_confidence_band")).upper()
    tempo_fit = safe(row.get("tempo_fit_v2")).upper()

    bonus = 0.0
    penalty = 0.0
    source = "PROXY"

    # =========================================================================
    # REAL SECTIONAL ENERGY HAS PRIORITY
    # =========================================================================

    if real_source == "REAL_SECTIONAL_PRIMARY" and real_tier:
        source = "REAL_SECTIONAL"

        if real_tier == "ELITE_ENERGY_EDGE":
            bonus += 0.006
        elif real_tier == "STRONG_ENERGY_EDGE":
            bonus += 0.004
        elif real_tier == "USABLE_ENERGY_EDGE":
            bonus += 0.002

        if real_conf == "MEDIUM":
            bonus *= 0.75
        elif real_conf in ["LOW", "VERY_LOW", ""]:
            bonus *= 0.40

    # =========================================================================
    # PROXY ENERGY FILLS THE NATIONAL COVERAGE GAP
    # =========================================================================

    else:
        source = "PROXY"

        if proxy_fit == "PROXY_ADVANTAGED":
            bonus += 0.0025
        elif proxy_fit in ["PROXY_PRESSURE_RISK", "PROXY_DISADVANTAGED"]:
            penalty += 0.0035

        if proxy_tier == "USABLE_PROXY_EDGE":
            bonus += 0.002
        elif proxy_tier == "WEAK_PROXY":
            penalty += 0.0015

        if proxy_score >= 64:
            bonus += 0.001
        elif proxy_score <= 50:
            penalty += 0.001

        # proxy confidence must heavily dampen the effect
        proxy_weight = max(0.15, min(0.65, proxy_conf / 100.0))
        bonus *= proxy_weight
        penalty *= proxy_weight

    # =========================================================================
    # TEMPO FIT CROSS-CHECK
    # =========================================================================

    if tempo_fit == "ADVANTAGED":
        bonus += 0.002
    elif tempo_fit == "DISADVANTAGED":
        penalty += 0.003

    # =========================================================================
    # LONGSHOT PROTECTION
    # =========================================================================

    max_bonus = 0.006

    if not pd.isna(price):
        if price >= 80:
            max_bonus = 0.0008
        elif price >= 40:
            max_bonus = 0.0012
        elif price >= 20:
            max_bonus = 0.002
        elif price >= 10:
            max_bonus = 0.0035

    bonus = min(bonus, max_bonus)
    penalty = min(penalty, 0.010)

    adjusted = base_prob + bonus - penalty

    if not pd.isna(market_prob):
        floor = max(0.001, market_prob * 0.65)
        ceiling = min(0.70, market_prob * 1.45 + 0.02)
        adjusted = max(floor, min(ceiling, adjusted))

    fair = 1.0 / adjusted if adjusted > 0 else np.nan

    overlay = np.nan
    if not pd.isna(price) and not pd.isna(fair):
        overlay = ((price / fair) - 1.0) * 100.0

    action = "PASS"

    if not pd.isna(overlay):
        if overlay >= 18 and source == "REAL_SECTIONAL":
            action = "REAL_ENERGY_EDGE"
        elif overlay >= 15 and source == "PROXY" and proxy_conf >= 55:
            action = "PROXY_CONTEXTUAL_WATCH"
        elif overlay >= 10:
            action = "WATCH"
        elif overlay <= -15:
            action = "UNDERLAY"

    reason = (
        f"source={source} | bonus={bonus:.4f} | penalty={penalty:.4f} | "
        f"proxy={proxy_tier}/{proxy_fit}/{proxy_conf} | real={real_tier}/{real_conf}"
    )

    return {
        "v5_energy_source": source,
        "v5_energy_bonus": round(bonus, 6),
        "v5_energy_penalty": round(penalty, 6),
        "v5_contextual_probability": round(adjusted, 6),
        "v5_contextual_fair_price": round(fair, 4) if not pd.isna(fair) else np.nan,
        "v5_contextual_overlay_pct": round(overlay, 2) if not pd.isna(overlay) else np.nan,
        "v5_contextual_action": action,
        "v5_contextual_reason": reason
    }

df = pd.read_csv(SRC, low_memory=False)
df.columns = [c.strip() for c in df.columns]

rows = []
for _, row in df.iterrows():
    rows.append(contextual_v5(row))

calc = pd.DataFrame(rows)
out = pd.concat([df, calc], axis=1)

out.to_csv(OUT, index=False)

diag = pd.DataFrame([{
    "rows": len(out),
    "real_energy_rows": int((out["v5_energy_source"] == "REAL_SECTIONAL").sum()),
    "proxy_energy_rows": int((out["v5_energy_source"] == "PROXY").sum()),
    "real_energy_edges": int((out["v5_contextual_action"] == "REAL_ENERGY_EDGE").sum()),
    "proxy_contextual_watch": int((out["v5_contextual_action"] == "PROXY_CONTEXTUAL_WATCH").sum()),
    "watch": int((out["v5_contextual_action"] == "WATCH").sum()),
    "underlay": int((out["v5_contextual_action"] == "UNDERLAY").sum()),
    "avg_bonus": round(pd.to_numeric(out["v5_energy_bonus"], errors="coerce").mean(), 6),
    "avg_penalty": round(pd.to_numeric(out["v5_energy_penalty"], errors="coerce").mean(), 6),
    "avg_overlay": round(pd.to_numeric(out["v5_contextual_overlay_pct"], errors="coerce").mean(), 2),
}])

diag.to_csv(DIAG, index=False)

print("=" * 100)
print("EDGEIQ CONTEXTUAL PROBABILITY ENGINE V5")
print("=" * 100)
print(diag.to_string(index=False))

print()
print("=" * 100)
print("TOP V5 CONTEXTUAL EDGES")
print("=" * 100)

cols = [
    "track","race_no","horse","market_price",
    "v5_contextual_fair_price","v5_contextual_overlay_pct",
    "v5_energy_source","proxy_energy_archetype","proxy_tempo_fit",
    "proxy_energy_score","proxy_confidence_score",
    "energy_source_type","v5_contextual_action","v5_contextual_reason"
]

cols = [c for c in cols if c in out.columns]

print(
    out.sort_values("v5_contextual_overlay_pct", ascending=False)
    [cols]
    .head(40)
    .to_string(index=False)
)

print()
print("SAVED:")
print(OUT)
print(DIAG)
