import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

versions = [
    ("V1",   "edgeiq_probability_engine_v6_2_factor_overlay_research_summary.csv"),
    ("V2",   "edgeiq_probability_engine_v6_2_factor_overlay_research_v2_summary.csv"),
    ("V2_1", "edgeiq_probability_engine_v6_2_factor_overlay_research_v2_1_summary.csv"),
    ("V2_2", "edgeiq_probability_engine_v6_2_factor_overlay_research_v2_2_summary.csv"),
]

rows = []

for version, file in versions:

    path = DATA / file

    if not path.exists():
        continue

    s = pd.read_csv(path)

    lookup = dict(zip(s.metric.astype(str), s.value.astype(str)))

    rows.append({
        "version": version,
        "top_changed_races": lookup.get("top_changed_races",""),
        "avg_overlay_score": lookup.get("avg_overlay_score",""),
        "avg_adjustment_pct": lookup.get("avg_adjustment_pct",""),
        "avg_abs_fair_delta_pct": lookup.get("avg_abs_fair_delta_pct",""),
        "max_abs_fair_delta_pct": lookup.get("max_abs_fair_delta_pct",""),
        "positive_factor_total": lookup.get("positive_factor_total",""),
        "negative_factor_total": lookup.get("negative_factor_total","")
    })

out = pd.DataFrame(rows)

OUT = DATA / "edgeiq_probability_engine_v6_2_factor_overlay_version_comparison.csv"

out.to_csv(OUT,index=False)

print("[V6_2_FACTOR_OVERLAY_VERSION_COMPARISON] COMPLETE")
print(out.to_string(index=False))
