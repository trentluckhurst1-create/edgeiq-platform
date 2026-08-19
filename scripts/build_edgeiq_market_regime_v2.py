from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_execution_board_live.csv"
TERMINAL = DATA / "edgeiq_execution_board_terminal.csv"
TAPE = DATA / "edgeiq_market_tape.csv"
OUT = DATA / "edgeiq_market_regime_v2.csv"

def read(p):
    if not p.exists():
        print(f"MISSING: {p}")
        return pd.DataFrame()
    df = pd.read_csv(p)
    print(f"READ {p.name}: {len(df)} rows")
    return df

def n(x):
    return pd.to_numeric(x, errors="coerce")

def classify(row):
    price = row.get("sportsbet_price", row.get("market_price", row.get("current_price", np.nan)))
    overlay = row.get("overlay_pct", np.nan)
    mover = str(row.get("market_mover", row.get("movement_signal", ""))).upper()
    regime_old = str(row.get("market_regime", "")).upper()
    clabel = str(row.get("calibrated_confidence_label", "")).upper()
    risk = str(row.get("suppression_risk_grade", "")).upper()

    try: price = float(price)
    except: price = np.nan
    try: overlay = float(overlay)
    except: overlay = np.nan

    tags = []

    if risk in ["KILL", "SUPPRESS"]:
        tags.append("TOXIC_SIGNAL")
    if clabel in ["VERY_LOW", "LOW"]:
        tags.append("LOW_TRUST")
    if pd.notna(price) and price >= 26:
        tags.append("ROUGHIE_EXPANSION")
    elif pd.notna(price) and price <= 3:
        tags.append("FAVOURITE_ZONE")
    if pd.notna(overlay) and overlay >= 100:
        tags.append("EXTREME_OVERLAY")
    elif pd.notna(overlay) and overlay < 0:
        tags.append("NEGATIVE_OVERLAY")
    if "STEAM" in mover or "FIRM" in mover or "FIRM" in regime_old:
        tags.append("STEAM_PRESSURE")
    if "DRIFT" in mover:
        tags.append("DRIFT_PRESSURE")
    if "CHAOTIC" in regime_old or "VOLATILE" in regime_old:
        tags.append("VOLATILE")

    if "TOXIC_SIGNAL" in tags and "EXTREME_OVERLAY" in tags:
        regime = "TOXIC_EXTREME_OVERLAY"
    elif "TOXIC_SIGNAL" in tags:
        regime = "TOXIC_SUPPRESSION"
    elif "ROUGHIE_EXPANSION" in tags and "EXTREME_OVERLAY" in tags:
        regime = "DANGEROUS_ROUGHIE_OVERLAY"
    elif "STEAM_PRESSURE" in tags and "LOW_TRUST" in tags:
        regime = "LOW_TRUST_STEAM"
    elif "DRIFT_PRESSURE" in tags:
        regime = "DRIFTING"
    elif "VOLATILE" in tags:
        regime = "VOLATILE"
    elif "NEGATIVE_OVERLAY" in tags:
        regime = "NEGATIVE_VALUE"
    elif "FAVOURITE_ZONE" in tags:
        regime = "FAVOURITE_ZONE"
    else:
        regime = "STABLE"

    if regime in ["TOXIC_EXTREME_OVERLAY", "TOXIC_SUPPRESSION", "DANGEROUS_ROUGHIE_OVERLAY"]:
        action = "HARD_SUPPRESS"
        risk_grade = "RED"
    elif regime in ["LOW_TRUST_STEAM", "VOLATILE", "DRIFTING"]:
        action = "THROTTLE"
        risk_grade = "ORANGE"
    elif regime in ["NEGATIVE_VALUE"]:
        action = "PASS"
        risk_grade = "ORANGE"
    else:
        action = "ALLOW_WITH_EXISTING_RULES"
        risk_grade = "GREEN"

    return pd.Series({
        "market_regime_v2": regime,
        "market_regime_v2_tags": ",".join(tags),
        "market_regime_v2_action": action,
        "market_regime_v2_risk": risk_grade,
    })

def main():
    print("="*100)
    print("EDGEIQ MARKET REGIME ENGINE V2")
    print("="*100)

    live = read(LIVE)
    if live.empty:
        pd.DataFrame().to_csv(OUT, index=False)
        print("No live rows.")
        return

    regime_cols = live.apply(classify, axis=1)
    live = pd.concat([live, regime_cols], axis=1)

    live["execution_action_before_regime_v2"] = live.get("execution_action", "")
    live["final_execution_state_before_regime_v2"] = live.get("final_execution_state", live.get("execution_action", ""))

    def apply(row):
        current = str(row.get("execution_action", "")).upper()
        reg_action = str(row.get("market_regime_v2_action", "")).upper()
        regime = str(row.get("market_regime_v2", "")).upper()

        if reg_action == "HARD_SUPPRESS":
            return "SUPPRESS"
        if reg_action == "THROTTLE" and current in ["MAX_BET", "PRIORITY_EXECUTE", "EXECUTE"]:
            return "WATCH"
        if reg_action == "PASS" and current in ["MAX_BET", "PRIORITY_EXECUTE", "EXECUTE", "WATCH", "MONITOR"]:
            return "PASS"
        return current

    live["execution_action"] = live.apply(apply, axis=1)
    live["final_execution_state"] = live["execution_action"]
    live["market_regime_v2_applied"] = (
        live["execution_action"].astype(str).str.upper()
        != live["execution_action_before_regime_v2"].astype(str).str.upper()
    ).astype(str).str.upper()

    out_cols = [
        "horse","track","race_no","sportsbet_price","rated_price","overlay_pct",
        "execution_action_before_regime_v2","execution_action",
        "calibrated_confidence_score","calibrated_confidence_label",
        "suppression_risk_grade","market_regime_v2","market_regime_v2_tags",
        "market_regime_v2_action","market_regime_v2_risk","market_regime_v2_applied"
    ]
    out_cols = [c for c in out_cols if c in live.columns]
    audit = live[out_cols].copy()

    live.to_csv(LIVE, index=False)
    live.to_csv(TERMINAL, index=False)
    audit.to_csv(OUT, index=False)

    print("REGIME COUNTS")
    print(live["market_regime_v2"].value_counts(dropna=False).to_string())
    print()
    print("REGIME ACTION COUNTS")
    print(live["market_regime_v2_action"].value_counts(dropna=False).to_string())
    print()
    print(audit.to_string(index=False))
    print("="*100)
    print("MARKET REGIME V2 COMPLETE")
    print("="*100)

if __name__ == "__main__":
    main()

