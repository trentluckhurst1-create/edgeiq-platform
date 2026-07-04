from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

DATA = Path("public/data")

SRC = DATA / "edgeiq_probability_research_v7_tab_candidate_t6.csv"
SUMMARY_SRC = DATA / "edgeiq_probability_research_v7_tab_candidate_t6_summary.csv"

OUT = DATA / "edgeiq_probability_engine_v7.csv"
SUMMARY = DATA / "edgeiq_probability_engine_v7_summary.csv"
REPORT = DATA / "edgeiq_probability_engine_v7_promotion_report.txt"

print("[PROBABILITY_ENGINE_V7_PROMOTION_ARTIFACT] START")

df = pd.read_csv(SRC, low_memory=False)
s = pd.read_csv(SUMMARY_SRC).iloc[0]

out = df.copy()

out["probability_engine_version"] = "V7_TEMPERATURE6_TAB_QUALITY"
out["probability_engine_status"] = "PROMOTION_ARTIFACT_NOT_LIVE_WIRED"
out["edgeiq_probability_v7"] = out["v7_tab_probability_t6"]
out["edgeiq_fair_price_v7"] = out["v7_tab_fair_price_t6"]
out["production_changed"] = "NO"
out["built_at_probability_engine_v7"] = datetime.now(timezone.utc).isoformat()

out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "built_at": datetime.now(timezone.utc).isoformat(),
    "rows": int(s["rows"]),
    "races": int(s["races"]),
    "temperature": float(s["temperature"]),
    "avg_log_loss": float(s["avg_log_loss"]),
    "avg_brier": float(s["avg_brier"]),
    "top_pick_win_pct": float(s["top_pick_win_pct"]),
    "avg_fav_prob": float(s["avg_fav_prob"]),
    "avg_fav_fair": float(s["avg_fav_fair"]),
    "probability_engine_version": "V7_TEMPERATURE6_TAB_QUALITY",
    "promotion_status": "PROMOTION_ARTIFACT_CREATED_NOT_LIVE_WIRED",
    "market_benchmark_status": "BLOCKED",
    "production_changed": "NO"
}])

summary.to_csv(SUMMARY, index=False)

lines = []
lines.append("EDGEiQ PROBABILITY ENGINE V7 PROMOTION ARTIFACT")
lines.append("=" * 58)
lines.append(f"built_at={datetime.now(timezone.utc).isoformat()}")
lines.append("")
lines.append("STATUS")
lines.append("- artifact_created=YES")
lines.append("- live_wired=NO")
lines.append("- production_changed=NO")
lines.append("")
lines.append("MODEL")
lines.append("- version=V7_TEMPERATURE6_TAB_QUALITY")
lines.append(f"- rows={int(s['rows'])}")
lines.append(f"- races={int(s['races'])}")
lines.append(f"- temperature={float(s['temperature'])}")
lines.append("")
lines.append("REPLAY METRICS")
lines.append(f"- avg_log_loss={float(s['avg_log_loss']):.6f}")
lines.append(f"- avg_brier={float(s['avg_brier']):.6f}")
lines.append(f"- top_pick_win_pct={float(s['top_pick_win_pct']):.2f}")
lines.append(f"- avg_fav_prob={float(s['avg_fav_prob']):.6f}")
lines.append(f"- avg_fav_fair={float(s['avg_fav_fair']):.6f}")
lines.append("")
lines.append("MARKET BENCHMARK")
lines.append("- status=BLOCKED")
lines.append("- reason=no trustworthy historical pre-race market archive exists")
lines.append("")
lines.append("NEXT")
lines.append("- audit fair price upgrade using edgeiq_probability_engine_v7.csv")
lines.append("- do not wire live production until fair price audit passes")

REPORT.write_text("\n".join(lines), encoding="utf-8")

print("[PROBABILITY_ENGINE_V7_PROMOTION_ARTIFACT] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(f"report={REPORT}")
print(summary.to_string(index=False))
