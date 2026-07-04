from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LADDER = DATA / "edgeiq_runner_dna_weight_ladder_v1_summary.csv"
GAIN = DATA / "edgeiq_runner_dna_v6_3_safe_factor_flip_analysis_v1_summary.csv"
LOSS = DATA / "edgeiq_runner_dna_v6_3_safe_loss_analysis_v1_summary.csv"
SPCOV = DATA / "edgeiq_runner_dna_v6_3_top_selection_sp_coverage_audit_v1_summary.csv"

OUT = DATA / "edgeiq_runner_dna_v6_3_final_promotion_gate_v1.csv"

built_at = datetime.now(timezone.utc).isoformat()

ladder = pd.read_csv(LADDER, dtype=str).fillna("")
spcov = pd.read_csv(SPCOV, dtype=str).fillna("")

def n(x):
    try:
        return float(str(x).replace("%","").strip())
    except Exception:
        return np.nan

base = ladder[ladder["version"] == "BASE"].iloc[0]
medium = ladder[ladder["version"] == "MEDIUM"].iloc[0]

base_win = n(base["rank1_win_pct"])
medium_win = n(medium["rank1_win_pct"])
base_place = n(base["rank1_place_pct"])
medium_place = n(medium["rank1_place_pct"])

win_lift = medium_win - base_win
place_lift = medium_place - base_place
flip_pct = n(medium["top_changed_pct"])
top_changed = int(float(medium["top_changed_races"]))

sp_valid_row = spcov[(spcov["version"] == "MEDIUM") & (spcov["segment"] == "SP_VALID_ONLY")]
sp_place = n(sp_valid_row.iloc[0]["place_pct"]) if len(sp_valid_row) else np.nan
sp_warning = "YES" if sp_place > 90 else "NO"

checks = []

def add(check, result, detail):
    checks.append({
        "check": check,
        "result": result,
        "detail": detail,
        "built_at": built_at,
    })

add("win_lift_positive", "PASS" if win_lift > 0 else "FAIL", round(win_lift, 3))
add("win_lift_material", "PASS" if win_lift >= 0.30 else "WARN", round(win_lift, 3))
add("place_lift_positive", "PASS" if place_lift > 0 else "FAIL", round(place_lift, 3))
add("place_lift_material", "PASS" if place_lift >= 0.75 else "WARN", round(place_lift, 3))
add("flip_rate_controlled", "PASS" if flip_pct <= 5.0 else "FAIL", round(flip_pct, 3))
add("top_changed_controlled", "PASS" if top_changed <= 700 else "FAIL", top_changed)
add("sp_roi_valid_for_promotion", "FAIL" if sp_warning == "YES" else "PASS", f"SP_VALID_ONLY place_pct={sp_place}")
add("research_only", "PASS", "YES")

pass_count = sum(1 for c in checks if c["result"] == "PASS")
fail_count = sum(1 for c in checks if c["result"] == "FAIL")
warn_count = sum(1 for c in checks if c["result"] == "WARN")

if fail_count == 0 and warn_count <= 1:
    verdict = "PROMOTION_READY"
elif fail_count == 1 and sp_warning == "YES":
    verdict = "PROMOTION_CANDIDATE_WITH_SP_ROI_BLOCKED"
else:
    verdict = "HOLD"

summary = pd.DataFrame([{
    "status": "RUNNER_DNA_V6_3_FINAL_PROMOTION_GATE_V1_BUILT",
    "candidate": "MEDIUM",
    "verdict": verdict,
    "base_win_pct": round(base_win, 3),
    "medium_win_pct": round(medium_win, 3),
    "win_lift_pct": round(win_lift, 3),
    "base_place_pct": round(base_place, 3),
    "medium_place_pct": round(medium_place, 3),
    "place_lift_pct": round(place_lift, 3),
    "top_changed_races": top_changed,
    "top_changed_pct": round(flip_pct, 3),
    "sp_roi_blocked": sp_warning,
    "pass_count": pass_count,
    "warn_count": warn_count,
    "fail_count": fail_count,
    "research_only": "YES",
    "built_at": built_at,
}])

detail = pd.DataFrame(checks)

out = pd.concat([summary.assign(row_type="SUMMARY"), detail.assign(row_type="CHECK")], ignore_index=True, sort=False)
out.to_csv(OUT, index=False)

print("[RUNNER_DNA_V6_3_FINAL_PROMOTION_GATE_V1] COMPLETE")
print(summary.to_string(index=False))
print("")
print(detail.to_string(index=False))
print(f"wrote={OUT}")
