import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

files = {
    "historical_v6_1": DATA / "edgeiq_historical_performance_rating_v6_1_research.csv",
    "governed": DATA / "edgeiq_live_runner_board_governed_v1.csv",
    "trajectory": DATA / "edgeiq_runner_trajectory_feed_v1.csv",
    "runners": DATA / "edgeiq_runners_enrichment_feed_v1_1.csv",
    "command": DATA / "edgeiq_command_enrichment_feed_v3.csv",
    "dna": DATA / "edgeiq_runner_dna_drawer_feed_v2.csv",
}

rows = []

for name, path in files.items():
    if not path.exists():
        rows.append({"source": name, "file": str(path), "status": "MISSING_FILE"})
        continue

    df = pd.read_csv(path, low_memory=False)
    cols = list(df.columns)

    form_cols = [c for c in cols if any(k in c.lower() for k in [
        "rating", "finish", "position", "beaten", "margin", "sp",
        "distance", "class", "condition", "track", "date",
        "trend", "form", "last", "start", "history"
    ])]

    horse_cols = [c for c in cols if "horse" in c.lower() or "runner" in c.lower()]

    rows.append({
        "source": name,
        "file": str(path),
        "status": "FOUND",
        "rows": len(df),
        "cols": len(cols),
        "horse_cols": " | ".join(horse_cols[:60]),
        "form_like_cols": " | ".join(form_cols[:160]),
    })

out = DATA / "edgeiq_form_tab_source_trace_v1.csv"
pd.DataFrame(rows).to_csv(out, index=False)

report = DATA / "edgeiq_form_tab_source_trace_v1_report.txt"
with open(report, "w", encoding="utf-8") as f:
    f.write("[EDGEIQ_FORM_TAB_SOURCE_TRACE_V1]\n")
    f.write(f"built_at={datetime.now(timezone.utc).isoformat()}\n")
    f.write(f"rows={len(rows)}\n\n")
    for r in rows:
        f.write("---\n")
        for k, v in r.items():
            f.write(f"{k}: {v}\n")

print("[EDGEIQ_FORM_TAB_SOURCE_TRACE_V1] COMPLETE")
print(out)
print(report)
