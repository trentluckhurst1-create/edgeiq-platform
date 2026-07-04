from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timezone

DATA = Path("public/data")

SRC = DATA / "edgeiq_probability_engine_v7.csv"

OUT = DATA / "edgeiq_fair_price_engine_v7_probability_upgrade_audit_v1.csv"
SUMMARY = DATA / "edgeiq_fair_price_engine_v7_probability_upgrade_audit_v1_summary.csv"
REPORT = DATA / "edgeiq_fair_price_engine_v7_probability_upgrade_audit_v1_report.txt"

print("[FAIR_PRICE_ENGINE_V7_PROBABILITY_UPGRADE_AUDIT_V1] START")

df = pd.read_csv(SRC, low_memory=False)

df["_prob"] = pd.to_numeric(df["edgeiq_probability_v7"], errors="coerce")
df["_fair"] = pd.to_numeric(df["edgeiq_fair_price_v7"], errors="coerce")
df["_won"] = pd.to_numeric(df["won"], errors="coerce").fillna(0)
df["_race_group"] = df["_race_group_v4"].astype(str)

df["_fair_from_prob"] = np.where(
    df["_prob"] > 0,
    1 / df["_prob"],
    np.nan
)

df["_fair_delta"] = df["_fair"] - df["_fair_from_prob"]
df["_fair_abs_delta"] = df["_fair_delta"].abs()

df["_prob_sum"] = df.groupby("_race_group")["_prob"].transform("sum")
df["_prob_sum_ok"] = df["_prob_sum"].between(0.995, 1.005)

df["_price_bucket"] = pd.cut(
    df["_fair"],
    bins=[0, 2, 3, 5, 10, 20, 50, 1000],
    labels=["<$2", "$2-$3", "$3-$5", "$5-$10", "$10-$20", "$20-$50", "$50+"],
    include_lowest=True
)

bucket = (
    df.groupby("_price_bucket", observed=False)
    .agg(
        rows=("horse", "count"),
        winners=("_won", "sum"),
        avg_probability=("_prob", "mean"),
        avg_fair_price=("_fair", "mean"),
        actual_win_rate=("_won", "mean")
    )
    .reset_index()
)

bucket.to_csv(OUT, index=False)

race = (
    df.groupby("_race_group")
    .agg(
        runners=("horse", "count"),
        winners=("_won", "sum"),
        prob_sum=("_prob", "sum"),
        min_fair=("_fair", "min"),
        max_fair=("_fair", "max")
    )
    .reset_index()
)

summary = pd.DataFrame([{
    "built_at": datetime.now(timezone.utc).isoformat(),
    "rows": len(df),
    "races": df["_race_group"].nunique(),
    "probability_rows": int(df["_prob"].notna().sum()),
    "fair_price_rows": int(df["_fair"].notna().sum()),
    "probability_coverage_pct": round(float(df["_prob"].notna().mean() * 100), 2),
    "fair_price_coverage_pct": round(float(df["_fair"].notna().mean() * 100), 2),
    "races_prob_sum_ok": int(race["prob_sum"].between(0.995, 1.005).sum()),
    "races_prob_sum_bad": int((~race["prob_sum"].between(0.995, 1.005)).sum()),
    "max_fair_price_recalc_delta": float(df["_fair_abs_delta"].max()),
    "min_fair_price": float(df["_fair"].min()),
    "max_fair_price": float(df["_fair"].max()),
    "avg_fair_price": float(df["_fair"].mean()),
    "status": "FAIR_PRICE_ENGINE_V7_PROBABILITY_UPGRADE_AUDIT_COMPLETE_RESEARCH_ONLY",
    "production_changed": "NO"
}])

summary.to_csv(SUMMARY, index=False)

s = summary.iloc[0]

lines = []
lines.append("EDGEiQ FAIR PRICE ENGINE V7 PROBABILITY UPGRADE AUDIT V1")
lines.append("=" * 68)
lines.append(f"built_at={s['built_at']}")
lines.append("")
lines.append("STATUS")
lines.append("- production_changed=NO")
lines.append("- live_wired=NO")
lines.append("- audit_only=YES")
lines.append("")
lines.append("COVERAGE")
lines.append(f"- rows={int(s['rows'])}")
lines.append(f"- races={int(s['races'])}")
lines.append(f"- probability_coverage_pct={float(s['probability_coverage_pct']):.2f}")
lines.append(f"- fair_price_coverage_pct={float(s['fair_price_coverage_pct']):.2f}")
lines.append("")
lines.append("PROBABILITY SUM")
lines.append(f"- races_prob_sum_ok={int(s['races_prob_sum_ok'])}")
lines.append(f"- races_prob_sum_bad={int(s['races_prob_sum_bad'])}")
lines.append("")
lines.append("FAIR PRICE")
lines.append(f"- min_fair_price={float(s['min_fair_price']):.6f}")
lines.append(f"- max_fair_price={float(s['max_fair_price']):.6f}")
lines.append(f"- avg_fair_price={float(s['avg_fair_price']):.6f}")
lines.append(f"- max_fair_price_recalc_delta={float(s['max_fair_price_recalc_delta']):.12f}")
lines.append("")
lines.append("NEXT")
lines.append("- audit price bucket calibration")
lines.append("- audit race/field-size segments")
lines.append("- do not wire production until all audits pass")

REPORT.write_text("\n".join(lines), encoding="utf-8")

print("[FAIR_PRICE_ENGINE_V7_PROBABILITY_UPGRADE_AUDIT_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(f"report={REPORT}")
print(summary.to_string(index=False))
print("")
print(bucket.to_string(index=False))
