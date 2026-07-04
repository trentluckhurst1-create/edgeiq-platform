from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_probability_engine_v6_2_factor_overlay_research_v2_2.csv"
SUMMARY_SRC = DATA / "edgeiq_probability_engine_v6_2_factor_overlay_research_v2_2_summary.csv"
RACE_SRC = DATA / "edgeiq_probability_engine_v6_2_factor_overlay_research_v2_2_by_race.csv"

OUT = DATA / "edgeiq_probability_engine_v6_2_factor_overlay_research_v2_2_audit.csv"
SUMMARY_OUT = DATA / "edgeiq_probability_engine_v6_2_factor_overlay_research_v2_2_audit_summary.csv"

def num(x):
    try:
        s = str(x).replace("$", "").replace("%", "").strip()
        if s == "" or s.lower() == "nan":
            return np.nan
        return float(s)
    except Exception:
        return np.nan

df = pd.read_csv(SRC, dtype=str).fillna("")
summary = pd.read_csv(SUMMARY_SRC, dtype=str).fillna("")
races = pd.read_csv(RACE_SRC, dtype=str).fillna("")

summary_map = dict(zip(summary["metric"], summary["value"]))

df["fair_price_num"] = df["fair_price"].apply(num)
df["research_fair_price_num"] = df["research_fair_price_v6_2_v2_2"].apply(num)
df["fair_delta_pct"] = np.where(
    df["fair_price_num"] > 0,
    ((df["research_fair_price_num"] - df["fair_price_num"]) / df["fair_price_num"]) * 100,
    np.nan,
)
df["abs_fair_delta_pct"] = df["fair_delta_pct"].abs()
df["rank_delta"] = df["v6_2_v2_2_rank"].apply(num) - df["base_rank"].apply(num)

top_changed_races = int(str(summary_map.get("top_changed_races", "999")))
avg_abs_fair_delta_pct = float(summary_map.get("avg_abs_fair_delta_pct", 999))
max_abs_fair_delta_pct = float(summary_map.get("max_abs_fair_delta_pct", 999))

checks = [
    ("research_only", summary_map.get("research_only") == "YES"),
    ("production_prices_changed", summary_map.get("production_prices_changed") == "NO"),
    ("production_probability_changed", summary_map.get("production_probability_changed") == "NO"),
    ("top_changed_races_zero", top_changed_races == 0),
    ("avg_abs_fair_delta_pct_lte_2", avg_abs_fair_delta_pct <= 2.0),
    ("max_abs_fair_delta_pct_lte_5", max_abs_fair_delta_pct <= 5.0),
    ("pace_excluded", summary_map.get("pace_excluded") == "YES"),
    ("calibrated_thresholds", summary_map.get("calibrated_thresholds") == "YES"),
    ("zero_missing_fit_neutralised", summary_map.get("zero_missing_fit_neutralised") == "DISTANCE|CONDITION|CLASS"),
    ("compressed_meta_weights", summary_map.get("compressed_meta_weights") == "PROFILE|RATING|TRAINER|JOCKEY|COMBO"),
]

passed = all(v for _, v in checks)
verdict = "V6_2_FACTOR_OVERLAY_V2_2_PROMOTION_CANDIDATE" if passed else "V6_2_FACTOR_OVERLAY_V2_2_HOLD"

audit_rows = []
for name, ok in checks:
    audit_rows.append({
        "check": name,
        "result": "PASS" if ok else "FAIL",
        "built_at": datetime.now(timezone.utc).isoformat(),
    })

pd.DataFrame(audit_rows).to_csv(OUT, index=False)

audit_summary = pd.DataFrame([
    ["status", "V6_2_FACTOR_OVERLAY_V2_2_AUDIT_COMPLETE"],
    ["verdict", verdict],
    ["checks_passed", sum(1 for _, v in checks if v)],
    ["checks_total", len(checks)],
    ["rows", len(df)],
    ["priced_rows", int(df["fair_price_num"].notna().sum())],
    ["races", int(summary_map.get("races", 0))],
    ["top_changed_races", top_changed_races],
    ["avg_abs_fair_delta_pct", avg_abs_fair_delta_pct],
    ["max_abs_fair_delta_pct", max_abs_fair_delta_pct],
    ["avg_rank_delta_abs", round(df["rank_delta"].abs().mean(), 3)],
    ["research_only", summary_map.get("research_only")],
    ["production_prices_changed", summary_map.get("production_prices_changed")],
    ["production_probability_changed", summary_map.get("production_probability_changed")],
    ["built_at", datetime.now(timezone.utc).isoformat()],
], columns=["metric", "value"])

audit_summary.to_csv(SUMMARY_OUT, index=False)

print("[V6_2_FACTOR_OVERLAY_V2_2_AUDIT] COMPLETE")
print(audit_summary.to_string(index=False))
print(f"wrote={OUT}")
print(f"wrote={SUMMARY_OUT}")
