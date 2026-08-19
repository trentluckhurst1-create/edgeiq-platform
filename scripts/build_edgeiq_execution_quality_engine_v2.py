from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path.cwd()

EXECUTION = ROOT / "dashboard" / "racing-dashboard" / "public" / "data" / "edgeiq_execution_board_v3.csv"

OUT = ROOT / "dashboard" / "racing-dashboard" / "public" / "data" / "edgeiq_execution_quality_v2.csv"

def num(v):
    try:
        if pd.isna(v):
            return np.nan
        return float(str(v).replace("$","").replace(",","").strip())
    except:
        return np.nan

def safe(v):
    if pd.isna(v):
        return ""
    return str(v).strip()

def classify(row):

    edge = num(row.get("v3_edge_pct"))
    if pd.isna(edge):
        edge = num(row.get("edge_pct"))
    price = num(row.get("market_price"))
    if pd.isna(price):
        price = num(row.get("live_price"))
    conf = num(row.get("confidence_score"))
    market_state = safe(row.get("market_state")).upper()
    action = safe(row.get("v3_execution_action")).upper()
    if not action:
        action = safe(row.get("execution_action")).upper()
    realism = safe(row.get("v3_realism_grade")).upper()

    if pd.isna(edge):
        return (
            "NO_MARKET",
            0,
            "NO_MARKET",
            "NONE",
            "UNKNOWN",
            "NO_CONVICTION",
            0,
            "No live market"
        )

    stability = "UNSTABLE"

    if abs(edge) <= 6:
        stability = "EFFICIENT"
    elif abs(edge) <= 15:
        stability = "STABLE"
    elif abs(edge) <= 30:
        stability = "VOLATILE"
    else:
        stability = "EXTREME"

    steam = "NEUTRAL"

    if edge >= 18 and price <= 6:
        steam = "SHARP_STEAM"

    elif edge >= 18 and price > 15:
        steam = "ROUGHIE_STEAM"

    elif edge <= -15:
        steam = "PUBLIC_OVERBET"

    risk = "MEDIUM"

    if realism in ["EXTREME_FAKE_OVERLAY", "LOW_CONFIDENCE_FAKE_OVERLAY"]:
        risk = "EXTREME"

    elif market_state in ["CHAOTIC", "VOLATILE", "TOXIC_SUPPRESSION"]:
        risk = "HIGH"

    elif conf >= 70 and stability == "STABLE":
        risk = "LOW"

    quality = "NEUTRAL"

    if (
        action == "EXECUTE"
        and stability in ["STABLE", "EFFICIENT"]
        and risk == "LOW"
    ):
        quality = "ELITE_EXECUTION"

    elif (
        action in ["EXECUTE", "STRONG_WATCH"]
        and risk != "EXTREME"
    ):
        quality = "GOOD_EXECUTION"

    elif risk == "EXTREME":
        quality = "DO_NOT_TOUCH"

    elif stability == "EXTREME":
        quality = "UNSTABLE_EDGE"

    score = 50

    if quality == "ELITE_EXECUTION":
        score = 90

    elif quality == "GOOD_EXECUTION":
        score = 75

    elif quality == "UNSTABLE_EDGE":
        score = 35

    elif quality == "DO_NOT_TOUCH":
        score = 5

    conviction_score = 50

    if edge >= 18:
        conviction_score += 15
    elif edge >= 10:
        conviction_score += 8
    elif edge >= 6:
        conviction_score += 3

    if conf >= 70:
        conviction_score += 18
    elif conf >= 55:
        conviction_score += 10
    elif conf < 40:
        conviction_score -= 15

    if price >= 80:
        conviction_score -= 25
    elif price >= 40:
        conviction_score -= 18
    elif price >= 20:
        conviction_score -= 10
    elif price <= 6:
        conviction_score += 8

    if risk == "LOW":
        conviction_score += 10
    elif risk == "HIGH":
        conviction_score -= 15
    elif risk == "EXTREME":
        conviction_score -= 35

    if stability == "EXTREME":
        conviction_score -= 18
    elif stability == "VOLATILE":
        conviction_score -= 8
    elif stability == "STABLE":
        conviction_score += 8

    conviction_score = max(0, min(100, conviction_score))

    if conviction_score >= 85:
        conviction = "ELITE_CONVICTION"
    elif conviction_score >= 70:
        conviction = "HIGH_CONVICTION"
    elif conviction_score >= 50:
        conviction = "MEDIUM_CONVICTION"
    elif conviction_score >= 30:
        conviction = "LOW_CONVICTION"
    else:
        conviction = "NO_CONVICTION"

    commentary = (
        f"{quality} | "
        f"conviction={conviction}({conviction_score}) | "
        f"edge={edge:.1f}% | "
        f"stability={stability} | "
        f"steam={steam} | "
        f"risk={risk}"
    )

    return (
        quality,
        score,
        stability,
        steam,
        risk,
        conviction,
        conviction_score,
        commentary
    )

df = pd.read_csv(EXECUTION, low_memory=False)

qualities = []
scores = []
stabilities = []
steams = []
risks = []
convictions = []
conviction_scores = []
comments = []

for _, row in df.iterrows():

    q, s, st, sm, r, cv, cvs, c = classify(row)

    qualities.append(q)
    scores.append(s)
    stabilities.append(st)
    steams.append(sm)
    risks.append(r)
    convictions.append(cv)
    conviction_scores.append(cvs)
    comments.append(c)

df["execution_quality"] = qualities
df["execution_quality_score"] = scores
df["edge_stability"] = stabilities
df["steam_type"] = steams
df["execution_risk"] = risks
df["execution_conviction"] = convictions
df["execution_conviction_score"] = conviction_scores
df["execution_commentary"] = comments

df.to_csv(OUT, index=False)

print("=" * 100)
print("EDGEIQ EXECUTION QUALITY ENGINE V2")
print("=" * 100)

print(df["execution_quality"].value_counts().to_string())
print()
print("CONVICTION")
print(df["execution_conviction"].value_counts().to_string())

print()
print("=" * 100)
print("TOP EXECUTION OPPORTUNITIES")
print("=" * 100)

top = (
    df[
        df["execution_quality_score"] >= 70
    ]
    .sort_values(
        ["execution_quality_score", "edge_pct"],
        ascending=False
    )
)

cols = [
    "track",
    "race_no",
    "horse",
    "market_price",
    "v3_fair_price",
    "edge_pct",
    "execution_action",
    "execution_quality",
    "execution_quality_score",
    "execution_conviction",
    "execution_conviction_score",
    "steam_type",
    "execution_commentary"
]

cols = [c for c in cols if c in top.columns]

print(
    top[cols]
    .head(25)
    .to_string(index=False)
)

print()
print("SAVED:")
print(OUT)
