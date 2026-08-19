from pathlib import Path
import pandas as pd
import numpy as np
import math

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_historical_performance_rating_v5_1.csv"
OUT = DATA / "edgeiq_historical_performance_rating_v5_1_recalibration_research.csv"
AUDIT = DATA / "edgeiq_historical_performance_rating_v5_1_recalibration_research_audit.csv"

def num(x):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return np.nan
        return float(str(x).replace(",", "").strip())
    except Exception:
        return np.nan

def clamp(x, lo, hi):
    if pd.isna(x):
        return np.nan
    return max(lo, min(hi, x))

def main():
    df = pd.read_csv(SRC, dtype=str, keep_default_na=False, low_memory=False)

    for c in [
        "performance_rating_v5_1",
        "finish_position",
        "real_field_size",
        "margin",
        "class_ladder_score_v1",
    ]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Research-only ability rating:
    # Start from existing V5.1, but compress the winner/top3 finish-position effect.
    # Purpose: test whether projection gaps become more realistic without destroying ordering.
    finish = df["finish_position"]
    class_score = df["class_ladder_score_v1"].fillna(54.0)

    # Convert class ladder into a true base level.
    # Neutral class ~64, stronger classes lift, weaker classes drop.
    class_base = 64.0 + ((class_score - 54.0) * 0.35)

    # Finish contribution is deliberately much smaller than V3.
    finish_bonus = np.select(
        [
            finish.eq(1),
            finish.eq(2),
            finish.eq(3),
            finish.between(4, 5),
            finish.between(6, 8),
        ],
        [
            16.0,
            10.0,
            6.0,
            2.0,
            -3.0,
        ],
        default=-8.0,
    )

    margin = df["margin"].fillna(0.0)
    margin_penalty = np.where(finish.eq(1), 0.0, np.minimum(12.0, margin * 1.15))

    field_size = df["real_field_size"].fillna(10)
    field_adj = np.clip((field_size - 10) * 0.12, -1.0, 1.5)

    df["performance_rating_v5_1_research"] = (
        class_base + finish_bonus + field_adj - margin_penalty
    ).round(2)

    df["performance_rating_v5_1_research"] = df["performance_rating_v5_1_research"].clip(10, 110)

    df["research_delta_vs_v5_1"] = (
        df["performance_rating_v5_1_research"] - df["performance_rating_v5_1"]
    ).round(2)

    df.to_csv(OUT, index=False)

    audit_rows = []

    for label, col in [
        ("old_v5_1", "performance_rating_v5_1"),
        ("research", "performance_rating_v5_1_research"),
    ]:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        audit_rows.append({
            "section": "overall",
            "metric": label,
            "count": len(s),
            "avg": round(float(s.mean()), 4),
            "min": round(float(s.min()), 4),
            "max": round(float(s.max()), 4),
            "ge90": int((s >= 90).sum()),
            "ge95": int((s >= 95).sum()),
            "ge100": int((s >= 100).sum()),
        })

    for label, col in [
        ("old_v5_1", "performance_rating_v5_1"),
        ("research", "performance_rating_v5_1_research"),
    ]:
        winners = df[df["finish_position"].eq(1)].copy()
        s = pd.to_numeric(winners[col], errors="coerce").dropna()
        audit_rows.append({
            "section": "winners",
            "metric": label,
            "count": len(s),
            "avg": round(float(s.mean()), 4),
            "min": round(float(s.min()), 4),
            "max": round(float(s.max()), 4),
            "ge90": int((s >= 90).sum()),
            "ge95": int((s >= 95).sum()),
            "ge100": int((s >= 100).sum()),
        })

    for cls, g in df.groupby("race_class_clean_v3_3", dropna=False):
        winners = g[g["finish_position"].eq(1)].copy()
        if len(winners) < 10:
            continue
        old = pd.to_numeric(winners["performance_rating_v5_1"], errors="coerce").dropna()
        new = pd.to_numeric(winners["performance_rating_v5_1_research"], errors="coerce").dropna()
        audit_rows.append({
            "section": "winner_avg_by_class",
            "metric": cls,
            "count": len(winners),
            "old_avg": round(float(old.mean()), 4) if len(old) else "",
            "research_avg": round(float(new.mean()), 4) if len(new) else "",
            "delta": round(float(new.mean() - old.mean()), 4) if len(old) and len(new) else "",
        })

    audit = pd.DataFrame(audit_rows)
    audit.to_csv(AUDIT, index=False)

    print("[RECALIBRATION_RESEARCH] COMPLETE")
    print(f"rows={len(df)}")
    print(f"wrote={OUT}")
    print(f"audit={AUDIT}")
    print(audit[audit["section"].isin(["overall","winners"])].to_string(index=False))

if __name__ == "__main__":
    main()
