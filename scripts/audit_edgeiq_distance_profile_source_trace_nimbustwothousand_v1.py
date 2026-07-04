import pandas as pd
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

target = "NIMBUSTWOTHOUSAND"

files = [
    DATA / "edgeiq_results_warehouse_full_v1.csv",
    DATA / "edgeiq_historical_results_warehouse_full_v1.csv",
    DATA / "edgeiq_historical_performance_rating_v6_1_research.csv",
    DATA / "edgeiq_runner_dna_drawer_feed_v2.csv",
    DATA / "edgeiq_runners_enrichment_feed_v1_1.csv",
    DATA / "edgeiq_live_runner_factor_scorecard_v2.csv",
]

rows = []

def clean(x):
    return str(x).strip().upper() if pd.notna(x) else ""

for path in files:
    if not path.exists():
        rows.append({"file": path.name, "status": "MISSING_FILE"})
        continue

    df = pd.read_csv(path, low_memory=False)
    horse_cols = [c for c in df.columns if "horse" in c.lower() or "runner" in c.lower()]
    dist_cols = [c for c in df.columns if "distance" in c.lower() or c.lower() in ["dist", "race_distance"]]
    pos_cols = [c for c in df.columns if "finish" in c.lower() or "position" in c.lower() or c.lower() in ["pos", "placing"]]

    mask = pd.Series(False, index=df.index)
    for c in horse_cols:
        mask = mask | df[c].astype(str).str.upper().str.contains(target, na=False)

    sub = df.loc[mask].copy()

    rows.append({
        "file": path.name,
        "status": "FOUND",
        "rows": len(df),
        "target_rows": len(sub),
        "horse_cols": " | ".join(horse_cols),
        "distance_cols": " | ".join(dist_cols),
        "position_cols": " | ".join(pos_cols),
    })

    if len(sub):
        out_cols = []
        for c in ["race_date","date","track","race_no","race_number","horse","runner","distance","race_distance","dist","finishing_position","finish_position","position","placing","beaten_margin","sp","rating","performance_rating_v6_1_research"]:
            if c in sub.columns:
                out_cols.append(c)
        sub[out_cols].to_csv(DATA / f"edgeiq_distance_profile_target_rows_{path.stem}_NIMBUSTWOTHOUSAND.csv", index=False)

summary = pd.DataFrame(rows)
summary.to_csv(DATA / "edgeiq_distance_profile_source_trace_nimbustwothousand_v1.csv", index=False)

with open(DATA / "edgeiq_distance_profile_source_trace_nimbustwothousand_v1_report.txt", "w", encoding="utf-8") as f:
    f.write("[EDGEIQ_DISTANCE_PROFILE_SOURCE_TRACE_NIMBUSTWOTHOUSAND_V1]\n")
    for _, r in summary.iterrows():
        f.write("\n---\n")
        for k, v in r.items():
            f.write(f"{k}: {v}\n")

print("[DISTANCE_PROFILE_TRACE] COMPLETE")
print(DATA / "edgeiq_distance_profile_source_trace_nimbustwothousand_v1.csv")
print(DATA / "edgeiq_distance_profile_source_trace_nimbustwothousand_v1_report.txt")
