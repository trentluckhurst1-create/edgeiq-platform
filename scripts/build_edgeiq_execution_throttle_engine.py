from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_execution_board_live.csv"
TERMINAL = DATA / "edgeiq_execution_board_terminal.csv"
OUT_AUDIT = DATA / "edgeiq_execution_throttle_audit.csv"

def read_csv(p):
    if not p.exists():
        print(f"MISSING: {p}")
        return pd.DataFrame()
    df = pd.read_csv(p)
    print(f"READ {p.name}: {len(df)} rows")
    return df

def score_to_throttle(score):
    try:
        s = float(score)
    except Exception:
        return "NO_CONFIDENCE_SCORE"

    if s < 25:
        return "HARD_SUPPRESS"
    if s < 40:
        return "WATCH_ONLY"
    if s < 55:
        return "REDUCED_EXECUTE"
    if s < 70:
        return "EXECUTE_ALLOWED"
    return "PRIORITY_ALLOWED"

def apply_throttle(row):
    original = str(row.get("execution_action", row.get("final_execution_state", row.get("execution_state", "")))).upper()
    score = row.get("calibrated_confidence_score", "")
    throttle = score_to_throttle(score)

    final = original
    reason = ""

    if throttle == "HARD_SUPPRESS":
        if original in ["MAX_BET", "PRIORITY_EXECUTE", "EXECUTE", "REDUCED_EXECUTE", "WATCH", "MONITOR"]:
            final = "SUPPRESS"
            reason = f"confidence throttle HARD_SUPPRESS score={score}"
    elif throttle == "WATCH_ONLY":
        if original in ["MAX_BET", "PRIORITY_EXECUTE", "EXECUTE", "REDUCED_EXECUTE"]:
            final = "WATCH"
            reason = f"confidence throttle WATCH_ONLY score={score}"
    elif throttle == "REDUCED_EXECUTE":
        if original in ["MAX_BET", "PRIORITY_EXECUTE"]:
            final = "EXECUTE"
            reason = f"confidence throttle reduced priority score={score}"
        elif original == "EXECUTE":
            final = "REDUCED_EXECUTE"
            reason = f"confidence throttle REDUCED_EXECUTE score={score}"
    elif throttle == "EXECUTE_ALLOWED":
        reason = f"confidence allows execution score={score}"
    elif throttle == "PRIORITY_ALLOWED":
        reason = f"confidence priority allowed score={score}"
    else:
        if original in ["MAX_BET", "PRIORITY_EXECUTE", "EXECUTE"]:
            final = "WATCH"
            reason = "missing confidence score; downgraded to WATCH"

    return pd.Series({
        "pre_throttle_execution_action": original,
        "confidence_throttle_state": throttle,
        "post_throttle_execution_action": final,
        "confidence_throttle_applied": str(final != original).upper(),
        "confidence_throttle_reason": reason,
    })

def reduce_stake(row):
    stake_cols = ["stake", "stake_units", "stake_units_v4_1", "original_stake"]
    val = None
    col_used = ""

    for c in stake_cols:
        if c in row.index:
            try:
                x = float(row.get(c))
                if pd.notna(x):
                    val = x
                    col_used = c
                    break
            except Exception:
                pass

    if val is None:
        return pd.Series({"throttled_stake": "", "throttled_stake_note": "no stake found"})

    state = str(row.get("confidence_throttle_state", "")).upper()
    post = str(row.get("post_throttle_execution_action", "")).upper()

    new = val
    note = f"unchanged from {col_used}"

    if state == "HARD_SUPPRESS" or post == "SUPPRESS":
        new = 0.0
        note = f"stake zeroed by throttle from {col_used}"
    elif state == "WATCH_ONLY" or post in ["WATCH", "MONITOR", "PASS"]:
        new = 0.0
        note = f"stake zeroed watch/pass from {col_used}"
    elif state == "REDUCED_EXECUTE" or post == "REDUCED_EXECUTE":
        new = round(val * 0.5, 4)
        note = f"stake halved by throttle from {col_used}"

    return pd.Series({"throttled_stake": new, "throttled_stake_note": note})

def main():
    print("=" * 100)
    print("EDGEIQ EXECUTION THROTTLE ENGINE V1")
    print("=" * 100)

    df = read_csv(LIVE)
    if df.empty:
        print("No live rows. Nothing to throttle.")
        return

    throttle_cols = df.apply(apply_throttle, axis=1)
    df = pd.concat([df, throttle_cols], axis=1)

    stake_cols = df.apply(reduce_stake, axis=1)
    df = pd.concat([df, stake_cols], axis=1)

    df["execution_action_before_confidence_throttle"] = df.get("execution_action", "")
    df["execution_action"] = df["post_throttle_execution_action"]
    df["final_execution_state"] = df["post_throttle_execution_action"]

    if "stake" in df.columns:
        df["stake_before_confidence_throttle"] = df["stake"]
        df["stake"] = df["throttled_stake"]
    elif "stake_units" in df.columns:
        df["stake_units_before_confidence_throttle"] = df["stake_units"]
        df["stake_units"] = df["throttled_stake"]

    df.to_csv(LIVE, index=False)
    df.to_csv(TERMINAL, index=False)

    audit = pd.DataFrame([{
        "rows": len(df),
        "hard_suppress": int((df["confidence_throttle_state"] == "HARD_SUPPRESS").sum()),
        "watch_only": int((df["confidence_throttle_state"] == "WATCH_ONLY").sum()),
        "reduced_execute": int((df["confidence_throttle_state"] == "REDUCED_EXECUTE").sum()),
        "execute_allowed": int((df["confidence_throttle_state"] == "EXECUTE_ALLOWED").sum()),
        "priority_allowed": int((df["confidence_throttle_state"] == "PRIORITY_ALLOWED").sum()),
        "throttle_applied": int(df["confidence_throttle_applied"].astype(str).str.upper().eq("TRUE").sum()),
        "final_suppress": int(df["execution_action"].astype(str).str.upper().eq("SUPPRESS").sum()),
        "final_watch": int(df["execution_action"].astype(str).str.upper().eq("WATCH").sum()),
        "final_execute": int(df["execution_action"].astype(str).str.upper().eq("EXECUTE").sum()),
        "final_reduced_execute": int(df["execution_action"].astype(str).str.upper().eq("REDUCED_EXECUTE").sum()),
    }])
    audit.to_csv(OUT_AUDIT, index=False)

    print("THROTTLE AUDIT")
    print(audit.to_string(index=False))
    print()
    show = ["horse", "calibrated_confidence_score", "calibrated_confidence_label", "pre_throttle_execution_action", "execution_action", "confidence_throttle_state", "confidence_throttle_reason"]
    show = [c for c in show if c in df.columns]
    print(df[show].to_string(index=False))
    print("=" * 100)
    print("EXECUTION THROTTLE COMPLETE")
    print("=" * 100)

if __name__ == "__main__":
    main()

