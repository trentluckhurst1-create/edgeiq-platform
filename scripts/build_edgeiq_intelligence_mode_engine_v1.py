from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

DATA = Path("./public/data")

BOARD = DATA / "edgeiq_live_runner_board_governed_v1.csv"
OUT = DATA / "edgeiq_intelligence_mode_engine_v1.csv"
SUMMARY = DATA / "edgeiq_intelligence_mode_engine_v1_summary.csv"
REPORT = DATA / "edgeiq_intelligence_mode_engine_v1_report.txt"

df = pd.read_csv(
    BOARD,
    dtype=str,
    keep_default_na=False,
    low_memory=False
)

for c in df.columns:
    df[c] = df[c].astype(str)

def pct(x):
    if len(x) == 0:
        return 0.0
    return round(100.0 * x.mean(), 2)

rows = []

for (track, race_no), g in df.groupby(["track", "race_no"], dropna=False):

    active = g[
        ~g["runner_status"].astype(str).str.upper().isin(
            ["SCR", "SCRATCHED"]
        )
    ].copy()

    n = len(active)

    if n == 0:
        continue

    projection_cov = pct(
        ~active["projection_band_V6_1_RESEARCH"]
        .isin(["", "NO_PROJECTION"])
    )

    no_projection_pct = pct(
        active["projection_band_V6_1_RESEARCH"]
        .isin(["", "NO_PROJECTION"])
    )

    price_cov = pct(
        active["V6_1_RESEARCH_price_status"]
        .eq("RESEARCH_RATED")
    )

    market_cov = pct(
        ~active["live_price"]
        .isin(["", "-", "nan", "NaN"])
    )

    connection_cols = [
        c for c in active.columns
        if "trainer" in c.lower()
        or "jockey" in c.lower()
    ]

    if connection_cols:
        connection_cov = pct(
            active[connection_cols]
            .replace("", np.nan)
            .notna()
            .any(axis=1)
        )
    else:
        connection_cov = 0.0

    pace_cols = [
        c for c in active.columns
        if "pace" in c.lower()
        or "run_style" in c.lower()
    ]

    if pace_cols:
        pace_cov = pct(
            active[pace_cols]
            .replace("", np.nan)
            .notna()
            .any(axis=1)
        )
    else:
        pace_cov = 0.0

    first_starter_pct = pct(
        active.apply(
            lambda r:
            str(r.astype(str).to_string()).upper().find("FIRST START") >= 0,
            axis=1
        )
    )

    data_quality = round(
        projection_cov * 0.35 +
        price_cov * 0.20 +
        connection_cov * 0.15 +
        pace_cov * 0.15 +
        market_cov * 0.15,
        2
    )

    if projection_cov >= 80 and no_projection_pct <= 20:
        mode = "RATINGS_DRIVEN"
        path = "Ratings + DNA + Sectionals"

    elif projection_cov >= 50:
        mode = "BALANCED"
        path = "Ratings + Connections + Market"

    elif first_starter_pct >= 35:
        mode = "DEBUTANT_DRIVEN"
        path = "Debut Intelligence + Connections + Market"

    elif market_cov >= 60:
        mode = "MARKET_DRIVEN"
        path = "Market + Connections"

    else:
        mode = "LOW_CONFIDENCE"
        path = "Exercise caution"

    if data_quality >= 80:
        confidence = "HIGH"
    elif data_quality >= 60:
        confidence = "MEDIUM"
    elif data_quality >= 40:
        confidence = "LOW"
    else:
        confidence = "VERY_LOW"

    rows.append({
        "track": track,
        "race_no": race_no,
        "runners": n,
        "projection_coverage_pct": projection_cov,
        "research_price_coverage_pct": price_cov,
        "market_coverage_pct": market_cov,
        "connection_coverage_pct": connection_cov,
        "pace_coverage_pct": pace_cov,
        "first_starter_pct": first_starter_pct,
        "no_projection_pct": no_projection_pct,
        "data_quality_score": data_quality,
        "intelligence_mode": mode,
        "intelligence_confidence": confidence,
        "recommended_analysis_path": path,
        "built_at": datetime.now(
            timezone.utc
        ).isoformat()
    })

out = pd.DataFrame(rows)

out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status":
        "EDGEIQ_INTELLIGENCE_MODE_ENGINE_V1_BUILT",
    "races": len(out),
    "avg_data_quality_score":
        round(out["data_quality_score"].mean(), 2),
    "mode_counts":
        out["intelligence_mode"]
        .value_counts()
        .to_dict(),
    "confidence_counts":
        out["intelligence_confidence"]
        .value_counts()
        .to_dict(),
    "built_at":
        datetime.now(timezone.utc).isoformat()
}])

summary.to_csv(SUMMARY, index=False)

REPORT.write_text(
    summary.to_string(index=False),
    encoding="utf-8"
)

print("[EDGEIQ_INTELLIGENCE_MODE_ENGINE_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(f"report={REPORT}")
