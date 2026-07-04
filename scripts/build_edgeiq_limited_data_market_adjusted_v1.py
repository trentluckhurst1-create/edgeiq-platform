from pathlib import Path
import pandas as pd
import math
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INP = DATA / "edgeiq_live_runner_board_governed_v1.csv"
OUT = DATA / "edgeiq_limited_data_market_adjusted_v1.csv"
SUMMARY = DATA / "edgeiq_limited_data_market_adjusted_v1_summary.csv"

def s(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def n(x):
    try:
        v = float(str(x).replace("$","").replace(",","").strip())
        if v <= 0:
            return math.nan
        return v
    except:
        return math.nan

def band_price(price):
    if math.isnan(price):
        return "NO_MARKET"
    if price <= 4:
        return "MARKET_STRONG"
    if price <= 8:
        return "MARKET_SOLID"
    if price <= 15:
        return "MARKET_OUTSIDER"
    return "MARKET_LONGSHOT"

def adjust(row):
    live = n(row.get("live_price",""))
    fair = n(row.get("fair_price_raw", row.get("fair_price","")))

    no_hist = s(row.get("no_history_flag","")).upper() == "TRUE"
    no_proj = s(row.get("no_projection_flag","")).upper() == "TRUE"

    if math.isnan(live):
        return pd.Series({
            "limited_data_market_anchor_price_v1": "",
            "limited_data_adjusted_price_v1": "",
            "limited_data_factor_score_v1": "",
            "limited_data_market_band_v1": "NO_MARKET",
            "limited_data_decision_v1": "NO_LIVE",
            "limited_data_reason_v1": "No live TAB market price."
        })

    score = 0
    reasons = []

    # MARKET RANK / PRICE SIGNAL
    if live <= 3.5:
        score += 18
        reasons.append("market respects runner strongly")
    elif live <= 6:
        score += 10
        reasons.append("market positive")
    elif live <= 10:
        score += 2
        reasons.append("market neutral")
    elif live >= 20:
        score -= 10
        reasons.append("market weak / long price")
    elif live >= 15:
        score -= 6
        reasons.append("market drifting outsider zone")

    # NO HISTORY / NO PROJECTION PENALTY
    if no_hist:
        score -= 4
        reasons.append("limited-history caution")
    if no_proj:
        score -= 4
        reasons.append("no-projection caution")

    # BARRIER SIMPLE RULE
    try:
        barrier = int(float(s(row.get("barrier",""))))
    except:
        barrier = None

    if barrier is not None:
        if barrier <= 3:
            score += 4
            reasons.append("inside barrier upgrade")
        elif barrier >= 8:
            score -= 4
            reasons.append("wide barrier penalty")

    # JOCKEY / TRAINER presence only for now
    if s(row.get("jockey","")):
        score += 2
    else:
        score -= 2
        reasons.append("missing jockey data")

    if s(row.get("trainer","")):
        score += 2

    # Existing EDGEiQ fair-price guard
    if not math.isnan(fair):
        if live > fair * 1.25:
            score += 8
            reasons.append("market price above model anchor")
        elif live < fair * 0.75:
            score -= 8
            reasons.append("market shorter than model anchor")

    # Convert score into adjusted price
    # positive score = shorter adjusted price
    multiplier = 1.0 - (score / 100.0)
    multiplier = max(0.65, min(1.45, multiplier))
    adj = round(live * multiplier, 2)

    if score >= 15:
        decision = "UPGRADE_WATCH"
    elif score >= 5:
        decision = "SLIGHT_UPGRADE"
    elif score <= -18:
        decision = "PENALISE_HARD"
    elif score <= -8:
        decision = "PENALISE"
    else:
        decision = "MARKET_NEUTRAL"

    return pd.Series({
        "limited_data_market_anchor_price_v1": live,
        "limited_data_adjusted_price_v1": adj,
        "limited_data_factor_score_v1": score,
        "limited_data_market_band_v1": band_price(live),
        "limited_data_decision_v1": decision,
        "limited_data_reason_v1": "; ".join(reasons)
    })

df = pd.read_csv(INP, dtype=str).fillna("")
extra = df.apply(adjust, axis=1)
out = pd.concat([df, extra], axis=1)

out.to_csv(OUT, index=False)

summary = []
summary.append(("status","COMPLETE"))
summary.append(("rows",len(out)))
summary.append(("limited_data_rows",int(((out.get("no_history_flag","").astype(str).str.upper()=="TRUE") | (out.get("no_projection_flag","").astype(str).str.upper()=="TRUE")).sum())))
for k,v in out["limited_data_decision_v1"].value_counts(dropna=False).to_dict().items():
    summary.append((f"decision_{k}",v))

pd.DataFrame(summary, columns=["metric","value"]).to_csv(SUMMARY,index=False)

print("[LIMITED_DATA_MARKET_ADJUSTED_V1] COMPLETE")
print(f"rows={len(out)}")
print(f"wrote={OUT}")
print(f"summary={SUMMARY}")

