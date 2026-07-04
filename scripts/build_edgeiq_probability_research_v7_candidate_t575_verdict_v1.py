from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

V6 = DATA / "edgeiq_probability_v6_final_verdict_v1.csv"
T6 = DATA / "edgeiq_pricing_replay_spine_v3_3_temperature6_summary.csv"
V7 = DATA / "edgeiq_probability_research_v7_candidate_t575_summary.csv"

OUT = DATA / "edgeiq_probability_research_v7_candidate_t575_verdict_v1.csv"
REPORT = DATA / "edgeiq_probability_research_v7_candidate_t575_verdict_v1_report.txt"

print("[V7_T575_VERDICT_V1] START")

v6 = pd.read_csv(V6).iloc[0]
t6 = pd.read_csv(T6).iloc[0]
v7 = pd.read_csv(V7).iloc[0]

t6_log = float(t6["avg_log_loss"])
t6_brier = float(t6["avg_brier"])
v7_log = float(v7["avg_log_loss"])
v7_brier = float(v7["avg_brier"])

log_delta = v7_log - t6_log
brier_delta = v7_brier - t6_brier

if log_delta < 0 and brier_delta <= 0:
    verdict = "V7_RESEARCH_LEAD_CANDIDATE"
    promotion = "RESEARCH_REVIEW_ONLY"
else:
    verdict = "MARGINAL_RESEARCH_ONLY"
    promotion = "BLOCKED_PENDING_MORE_TESTS"

out = pd.DataFrame([{
    "built_at": datetime.now(timezone.utc).isoformat(),
    "candidate": "PROBABILITY_RESEARCH_V7_T575",
    "benchmark": "TEMPERATURE6_HISTORICAL_RECONSTRUCTION",
    "rows": int(v7["rows"]),
    "races": int(v7["races"]),
    "v7_temperature": float(v7["temperature"]),
    "t6_log_loss": t6_log,
    "v7_log_loss": v7_log,
    "log_loss_delta_v7_minus_t6": log_delta,
    "t6_brier": t6_brier,
    "v7_brier": v7_brier,
    "brier_delta_v7_minus_t6": brier_delta,
    "v7_top_pick_win_pct": float(v7["top_pick_win_pct"]),
    "v7_avg_fav_prob": float(v7["avg_fav_prob"]),
    "v7_avg_fav_fair": float(v7["avg_fav_fair"]),
    "v6_verdict": str(v6["verdict"]),
    "verdict": verdict,
    "promotion_status": promotion,
    "production_changed": "NO"
}])

out.to_csv(OUT, index=False)

lines = []
lines.append("EDGEiQ PROBABILITY RESEARCH V7 T5.75 VERDICT V1")
lines.append("=" * 58)
lines.append(f"built_at={datetime.now(timezone.utc).isoformat()}")
lines.append("")
lines.append("PRODUCTION STATUS")
lines.append("- production_changed=NO")
lines.append("- live_fair_prices_changed=NO")
lines.append("- production_pricing_changed=NO")
lines.append("")
lines.append("BENCHMARK")
lines.append("- benchmark=T6 calibrated historical reconstruction")
lines.append(f"- rows={int(v7['rows'])}")
lines.append(f"- races={int(v7['races'])}")
lines.append("")
lines.append("RESULT")
lines.append(f"- T6 log_loss={t6_log:.9f}")
lines.append(f"- V7 T5.75 log_loss={v7_log:.9f}")
lines.append(f"- delta={log_delta:.9f}")
lines.append(f"- T6 brier={t6_brier:.9f}")
lines.append(f"- V7 T5.75 brier={v7_brier:.9f}")
lines.append(f"- delta={brier_delta:.9f}")
lines.append(f"- V7 top_pick_win_pct={float(v7['top_pick_win_pct']):.2f}")
lines.append(f"- V7 avg_fav_prob={float(v7['avg_fav_prob']):.6f}")
lines.append(f"- V7 avg_fav_fair={float(v7['avg_fav_fair']):.6f}")
lines.append("")
lines.append("VERDICT")
lines.append(f"- verdict={verdict}")
lines.append(f"- promotion_status={promotion}")
lines.append("")
lines.append("NOTE")
lines.append("- V7 T5.75 improves log loss slightly over T6 but Brier is effectively flat/slightly worse.")
lines.append("- This is not enough for production promotion.")
lines.append("- It is the current research lead only.")

REPORT.write_text("\n".join(lines), encoding="utf-8")

print("[V7_T575_VERDICT_V1] COMPLETE")
print(f"out={OUT}")
print(f"report={REPORT}")
print(out.to_string(index=False))
