from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
DASH = ROOT / "dashboard" / "racing-dashboard"
DATA = DASH / "public" / "data"

MASTER = DATA / "edgeiq_results_master.csv"
OUT = DATA / "edgeiq_confidence_calibration_v1.csv"
LIVE_IN = DATA / "edgeiq_execution_board_live.csv"
ALT_LIVE_IN = ROOT / "dashboard" / "racing-dashboard" / "public" / "data" / "edgeiq_execution_board_live.csv"
LIVE_OUT = DATA / "edgeiq_execution_board_live.csv"
TERMINAL_OUT = DATA / "edgeiq_execution_board_terminal.csv"

def num(s):
    return pd.to_numeric(s, errors="coerce")

def safe_read(p):
    if not p.exists():
        print(f"MISSING: {p}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(p)
        print(f"READ {p.name}: {len(df)} rows")
        return df
    except Exception as e:
        print(f"FAILED READ {p.name}: {e}")
        return pd.DataFrame()

def bucket_odds(x):
    try:
        x = float(x)
    except Exception:
        return "UNKNOWN"
    if x < 3:
        return "UNDER_3"
    if x < 6:
        return "3_TO_6"
    if x < 12:
        return "6_TO_12"
    if x < 26:
        return "12_TO_26"
    return "26_PLUS"

def bucket_overlay(x):
    try:
        x = float(x)
    except Exception:
        return "UNKNOWN"
    if x < 0:
        return "NEGATIVE_OVERLAY"
    if x < 10:
        return "0_TO_10"
    if x < 25:
        return "10_TO_25"
    if x < 50:
        return "25_TO_50"
    if x < 100:
        return "50_TO_100"
    return "100_PLUS"

def bucket_conf(x):
    s = str(x).strip().upper()
    if s in ["VERY_LOW", "LOW", "MEDIUM", "HIGH", "ELITE"]:
        return s
    try:
        v = float(s)
        if v < 35:
            return "VERY_LOW"
        if v < 50:
            return "LOW"
        if v < 65:
            return "MEDIUM"
        if v < 80:
            return "HIGH"
        return "ELITE"
    except Exception:
        return "UNKNOWN"

def grade_from_metrics(rows, roi, clv, beat_close):
    if rows < 20:
        return "PROVISIONAL"
    if roi >= 5 and beat_close >= 50 and clv >= 0:
        return "TRUST"
    if roi >= 0 and beat_close >= 45:
        return "ALLOW"
    if roi < -15 and beat_close < 35:
        return "DISTRUST"
    if roi < -8 or clv < -5:
        return "WEAK"
    return "CAUTION"

def segment_table(df, segment_type, col):
    if col not in df.columns:
        return pd.DataFrame()
    rows = []
    for val, g in df.groupby(col, dropna=False):
        settled = g[g["result"].astype(str).str.upper().isin(["WON","LOST"])] if "result" in g.columns else g.iloc[0:0]
        turnover = num(settled.get("stake", pd.Series(dtype=float))).fillna(0).sum()
        pl = num(settled.get("profit_loss", pd.Series(dtype=float))).fillna(0).sum()
        roi = (pl / turnover * 100) if turnover else 0
        clv_series = num(g.get("clv_pct", pd.Series(dtype=float))).dropna()
        avg_clv = clv_series.mean() if len(clv_series) else 0
        beat_close = (clv_series.gt(0).mean() * 100) if len(clv_series) else 0
        won = settled["result"].astype(str).str.upper().eq("WON").sum() if "result" in settled.columns else 0
        lost = settled["result"].astype(str).str.upper().eq("LOST").sum() if "result" in settled.columns else 0
        strike = (won / (won + lost) * 100) if (won + lost) else 0
        grade = grade_from_metrics(len(settled), roi, avg_clv, beat_close)
        rows.append({
            "segment_type": segment_type,
            "segment_value": str(val),
            "rows": len(g),
            "settled_rows": len(settled),
            "turnover": round(turnover, 4),
            "profit_loss": round(pl, 4),
            "roi_pct": round(roi, 4),
            "average_clv_pct": round(avg_clv, 4),
            "beat_close_pct": round(beat_close, 4),
            "strike_rate": round(strike, 4),
            "confidence_trust_grade": grade,
        })
    return pd.DataFrame(rows)

def score_row(grades):
    score = 50
    reasons = []
    for g in grades:
        if g == "TRUST":
            score += 15
            reasons.append("TRUST segment")
        elif g == "ALLOW":
            score += 7
            reasons.append("ALLOW segment")
        elif g == "CAUTION":
            score -= 5
            reasons.append("CAUTION segment")
        elif g == "WEAK":
            score -= 15
            reasons.append("WEAK segment")
        elif g == "DISTRUST":
            score -= 30
            reasons.append("DISTRUST segment")
        elif g == "PROVISIONAL":
            score -= 3
            reasons.append("PROVISIONAL sample")
    score = max(0, min(100, score))
    if score >= 75:
        label = "HIGH"
    elif score >= 60:
        label = "MEDIUM"
    elif score >= 40:
        label = "LOW"
    else:
        label = "VERY_LOW"
    return score, label, " | ".join(reasons[:6])

def main():
    print("="*100)
    print("EDGEIQ CONFIDENCE CALIBRATION ENGINE V1")
    print("="*100)

    df = safe_read(MASTER)
    if df.empty:
        pd.DataFrame(columns=[
            "segment_type","segment_value","rows","settled_rows","turnover","profit_loss",
            "roi_pct","average_clv_pct","beat_close_pct","strike_rate","confidence_trust_grade"
        ]).to_csv(OUT, index=False)
        print("No master rows. Empty calibration written.")
        return

    if "market_price" in df.columns:
        df["odds_bucket"] = df["market_price"].apply(bucket_odds)
    if "overlay_pct" in df.columns:
        df["overlay_bucket"] = df["overlay_pct"].apply(bucket_overlay)
    if "confidence" in df.columns:
        df["confidence_bucket_calibrated"] = df["confidence"].apply(bucket_conf)
    elif "confidence_bucket" in df.columns:
        df["confidence_bucket_calibrated"] = df["confidence_bucket"].apply(bucket_conf)

    parts = []
    for seg, col in [
        ("ODDS_BUCKET", "odds_bucket"),
        ("OVERLAY_BUCKET", "overlay_bucket"),
        ("CONFIDENCE_BUCKET", "confidence_bucket_calibrated"),
        ("REGIME", "regime"),
        ("EXECUTION_STATE", "final_execution_state"),
        ("RISK_GRADE", "suppression_risk_grade"),
    ]:
        t = segment_table(df, seg, col)
        if not t.empty:
            parts.append(t)

    cal = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    cal.to_csv(OUT, index=False)

    print(f"WROTE {OUT}: {len(cal)} rows")
    if len(cal):
        print(cal["confidence_trust_grade"].value_counts(dropna=False).to_string())

    live = safe_read(LIVE_IN)
    if live.empty:
        live = safe_read(ALT_LIVE_IN)
    if not live.empty and not cal.empty:
        lookup = {
            (str(r["segment_type"]).upper(), str(r["segment_value"]).upper()): str(r["confidence_trust_grade"]).upper()
            for _, r in cal.iterrows()
        }

        scores = []
        labels = []
        reasons = []

        for _, r in live.iterrows():
            segs = []

            price = r.get("sportsbet_price", r.get("market_price", r.get("price", "")))
            overlay = r.get("overlay_pct", "")
            conf = r.get("confidence", r.get("confidence_bucket", ""))
            state = r.get("final_execution_state", r.get("execution_action", r.get("execution_state", "")))
            risk = r.get("suppression_risk_grade", "")

            candidates = [
                ("ODDS_BUCKET", bucket_odds(price)),
                ("OVERLAY_BUCKET", bucket_overlay(overlay)),
                ("CONFIDENCE_BUCKET", bucket_conf(conf)),
                ("EXECUTION_STATE", str(state).upper()),
                ("RISK_GRADE", str(risk).upper()),
            ]

            for key in candidates:
                grade = lookup.get((key[0], key[1]))
                if grade:
                    segs.append(grade)

            score, label, reason = score_row(segs)
            scores.append(score)
            labels.append(label)
            reasons.append(reason)

        live["calibrated_confidence_score"] = scores
        live["calibrated_confidence_label"] = labels
        live["confidence_calibration_reason"] = reasons

        live.to_csv(LIVE_OUT, index=False)
        live.to_csv(TERMINAL_OUT, index=False)

        print(f"UPDATED LIVE CONFIDENCE: {len(live)} rows")
        print(live["calibrated_confidence_label"].value_counts(dropna=False).to_string())

    print("="*100)
    print("CONFIDENCE CALIBRATION COMPLETE")
    print("="*100)

if __name__ == "__main__":
    main()

