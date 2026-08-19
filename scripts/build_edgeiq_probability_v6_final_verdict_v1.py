from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_v6_vs_temperature6_replay_v1_summary.csv"

OUT = DATA / "edgeiq_probability_v6_final_verdict_v1.csv"
REPORT = DATA / "edgeiq_probability_v6_final_verdict_v1_report.txt"

print("[V6_FINAL_VERDICT_V1] START")

s = pd.read_csv(SRC)

row = s.iloc[0].to_dict()

baseline_log_loss = float(row["baseline_log_loss"])
v6_log_loss = float(row["v6_log_loss"])
baseline_brier = float(row["baseline_brier"])
v6_brier = float(row["v6_brier"])
baseline_top = float(row["baseline_top_pick_win_pct"])
v6_top = float(row["v6_top_pick_win_pct"])

log_loss_delta = v6_log_loss - baseline_log_loss
brier_delta = v6_brier - baseline_brier
top_delta = v6_top - baseline_top

if log_loss_delta < 0 and brier_delta < 0 and top_delta >= 0:
    verdict = "PROMOTION_CANDIDATE"
    promotion = "ALLOW_REVIEW"
else:
    verdict = "RESEARCH_ONLY"
    promotion = "BLOCKED"

out = pd.DataFrame([{
    "built_at": datetime.now(timezone.utc).isoformat(),
    "model": "PROBABILITY_ENGINE_V6",
    "benchmark": "TEMPERATURE6_HISTORICAL_RECONSTRUCTION",
    "rows": row["rows"],
    "races": row["races"],
    "baseline_log_loss": baseline_log_loss,
    "v6_log_loss": v6_log_loss,
    "log_loss_delta_v6_minus_baseline": log_loss_delta,
    "baseline_brier": baseline_brier,
    "v6_brier": v6_brier,
    "brier_delta_v6_minus_baseline": brier_delta,
    "baseline_top_pick_win_pct": baseline_top,
    "v6_top_pick_win_pct": v6_top,
    "top_pick_win_pct_delta_v6_minus_baseline": top_delta,
    "verdict": verdict,
    "promotion_status": promotion,
    "production_changed": "NO",
    "reason": "V6 underperforms calibrated historical reconstruction baseline on log loss, Brier and top-pick strike rate."
}])

out.to_csv(OUT, index=False)

lines = []
lines.append("EDGEiQ PROBABILITY ENGINE V6 FINAL VERDICT V1")
lines.append("=" * 52)
lines.append(f"built_at={datetime.now(timezone.utc).isoformat()}")
lines.append("")
lines.append("PRODUCTION STATUS")
lines.append("- production_changed=NO")
lines.append("- live_fair_prices_changed=NO")
lines.append("- production_pricing_changed=NO")
lines.append("")
lines.append("BENCHMARK")
lines.append("- benchmark=TEMPERATURE6_HISTORICAL_RECONSTRUCTION")
lines.append(f"- rows={row['rows']}")
lines.append(f"- races={row['races']}")
lines.append("")
lines.append("RESULT")
lines.append(f"- baseline_log_loss={baseline_log_loss:.6f}")
lines.append(f"- v6_log_loss={v6_log_loss:.6f}")
lines.append(f"- log_loss_delta_v6_minus_baseline={log_loss_delta:.6f}")
lines.append(f"- baseline_brier={baseline_brier:.6f}")
lines.append(f"- v6_brier={v6_brier:.6f}")
lines.append(f"- brier_delta_v6_minus_baseline={brier_delta:.6f}")
lines.append(f"- baseline_top_pick_win_pct={baseline_top:.2f}")
lines.append(f"- v6_top_pick_win_pct={v6_top:.2f}")
lines.append(f"- top_pick_win_pct_delta_v6_minus_baseline={top_delta:.2f}")
lines.append("")
lines.append("FINAL VERDICT")
lines.append(f"- verdict={verdict}")
lines.append(f"- promotion_status={promotion}")
lines.append("")
lines.append("REASON")
lines.append("- V6 performs worse than the calibrated historical reconstruction baseline.")
lines.append("- It loses on log loss, Brier score, and top-pick strike rate.")
lines.append("- It must remain research-only.")
lines.append("")
lines.append("NEXT DIRECTION")
lines.append("- Do not rescue/promote V6.")
lines.append("- Use the calibrated replay benchmark as the new Probability Lab baseline.")
lines.append("- Build future V7 candidates only if they beat T=6 on replay metrics.")

REPORT.write_text("\n".join(lines), encoding="utf-8")

print("[V6_FINAL_VERDICT_V1] COMPLETE")
print(f"out={OUT}")
print(f"report={REPORT}")
print(out.to_string(index=False))
