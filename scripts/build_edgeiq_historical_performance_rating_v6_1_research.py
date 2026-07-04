from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import math

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_historical_performance_rating_v5_1.csv"

OUT = DATA / "edgeiq_historical_performance_rating_v6_1_research.csv"
AUDIT = DATA / "edgeiq_historical_performance_rating_v6_1_research_audit.csv"

def num(x, default=math.nan):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return default
        return float(str(x).strip())
    except Exception:
        return default

def v6_1_rating(row):
    finish = num(row.get("finish_position", ""), math.nan)
    field = num(row.get("real_field_size", ""), 10.0)
    margin = num(row.get("margin", ""), 0.0)
    distance = num(row.get("distance", ""), 1400.0)

    class_adj_v5 = num(row.get("class_quality_adjustment_v5_1", ""), 0.0)
    old_rating = num(row.get("performance_rating_v5_1", ""), math.nan)

    if math.isnan(finish):
        return math.nan, "NO_FINISH"

    # V6.1 research: keep sane V6 ladder, but restore controlled top-end winner separation.
    if finish == 1:
        base = 82.0

        # Controlled class restoration.
        # V6 used 35%; V6.1 adds extra top-end without allowing V5-style blowouts.
        class_adj = class_adj_v5 * 0.50

        # Controlled dominance restoration from old V5 rating only for genuine high-end winners.
        # Starts after 88, capped at +7, so max cannot explode back toward 107.
        if not math.isnan(old_rating):
            dominance_boost = max(0.0, min(7.0, (old_rating - 88.0) * 0.35))
        else:
            dominance_boost = 0.0

    elif finish == 2:
        base = 75.0
        class_adj = class_adj_v5 * 0.40
        dominance_boost = 0.0
    elif finish == 3:
        base = 70.0
        class_adj = class_adj_v5 * 0.35
        dominance_boost = 0.0
    elif finish <= 5:
        base = 64.0
        class_adj = class_adj_v5 * 0.30
        dominance_boost = 0.0
    elif finish <= 8:
        base = 57.0
        class_adj = class_adj_v5 * 0.25
        dominance_boost = 0.0
    else:
        base = 50.0
        class_adj = class_adj_v5 * 0.20
        dominance_boost = 0.0

    if field >= 16:
        field_adj = 1.5
    elif field >= 13:
        field_adj = 1.0
    elif field >= 10:
        field_adj = 0.4
    elif field >= 7:
        field_adj = 0.0
    else:
        field_adj = -0.8

    if finish == 1:
        margin_penalty = 0.0
    else:
        if distance <= 1200:
            scale = 1.05
        elif distance <= 1600:
            scale = 0.90
        elif distance <= 2200:
            scale = 0.75
        else:
            scale = 0.60
        margin_penalty = min(14.0, margin * scale)

    rating = base + field_adj + class_adj + dominance_boost - margin_penalty
    rating = max(25.0, min(95.0, rating))

    reason = (
        f"v6_1_base={base:.2f} | field_adj={field_adj:.2f} | "
        f"class_adj={class_adj:.2f} | dominance_boost={dominance_boost:.2f} | "
        f"margin={margin:.2f} | margin_penalty={margin_penalty:.2f}"
    )

    return round(rating, 2), reason

def main():
    if not SRC.exists():
        raise FileNotFoundError(f"Missing input: {SRC}")

    df = pd.read_csv(SRC, dtype=str, keep_default_na=False, low_memory=False)

    ratings = df.apply(v6_1_rating, axis=1, result_type="expand")
    df["performance_rating_v6_1_research"] = ratings[0]
    df["performance_rating_v6_1_research_reason"] = ratings[1]
    df["research_delta_v6_1_minus_v5_1"] = (
        pd.to_numeric(df["performance_rating_v6_1_research"], errors="coerce")
        - pd.to_numeric(df["performance_rating_v5_1"], errors="coerce")
    ).round(2)

    df["built_at_v6_1_research"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    df.to_csv(OUT, index=False)

    old = pd.to_numeric(df["performance_rating_v5_1"], errors="coerce")
    new = pd.to_numeric(df["performance_rating_v6_1_research"], errors="coerce")
    winners = df["finish_position"].astype(str).eq("1")

    rows = [
        {"section":"overall","metric":"rows","value":len(df)},
        {"section":"overall","metric":"old_avg","value":round(float(old.mean()),4)},
        {"section":"overall","metric":"v6_1_avg","value":round(float(new.mean()),4)},
        {"section":"overall","metric":"old_max","value":round(float(old.max()),4)},
        {"section":"overall","metric":"v6_1_max","value":round(float(new.max()),4)},
        {"section":"overall","metric":"old_90_plus","value":int((old >= 90).sum())},
        {"section":"overall","metric":"v6_1_90_plus","value":int((new >= 90).sum())},
        {"section":"overall","metric":"old_95_plus","value":int((old >= 95).sum())},
        {"section":"overall","metric":"v6_1_95_plus","value":int((new >= 95).sum())},
        {"section":"winners","metric":"old_winner_avg","value":round(float(old[winners].mean()),4)},
        {"section":"winners","metric":"v6_1_winner_avg","value":round(float(new[winners].mean()),4)},
        {"section":"winners","metric":"old_winner_max","value":round(float(old[winners].max()),4)},
        {"section":"winners","metric":"v6_1_winner_max","value":round(float(new[winners].max()),4)},
        {"section":"winners","metric":"old_winner_min","value":round(float(old[winners].min()),4)},
        {"section":"winners","metric":"v6_1_winner_min","value":round(float(new[winners].min()),4)},
    ]

    audit = pd.DataFrame(rows)
    audit.to_csv(AUDIT, index=False)

    print("[HISTORICAL_PERFORMANCE_RATING_V6_1_RESEARCH] COMPLETE")
    print(audit.to_string(index=False))
    print(f"out={OUT}")
    print(f"audit={AUDIT}")

if __name__ == "__main__":
    main()
