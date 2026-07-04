import pandas as pd
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

files = {
    "command_v3": DATA / "edgeiq_command_enrichment_feed_v3.csv",
    "runners_v1_1": DATA / "edgeiq_runners_enrichment_feed_v1_1.csv",
    "factor_scorecard": DATA / "edgeiq_live_runner_factor_scorecard_v2.csv",
    "dna_drawer": DATA / "edgeiq_runner_dna_drawer_feed_v2.csv",
    "explainability": DATA / "edgeiq_explainability_terminal_feed_v1_2.csv",
    "governed": DATA / "edgeiq_live_runner_board_governed_v1.csv",
}

rows = []

def norm(x):
    return str(x).strip().upper() if pd.notna(x) else ""

for name, path in files.items():
    if not path.exists():
        rows.append({"source": name, "file": str(path), "status": "MISSING_FILE"})
        continue

    df = pd.read_csv(path, low_memory=False)
    cols = list(df.columns)

    score_like = [c for c in cols if any(k in c.lower() for k in [
        "overall", "distance", "condition", "class", "campaign", "pace",
        "connection", "market", "confidence", "score", "rating"
    ])]

    key_like = [c for c in cols if any(k in c.lower() for k in [
        "horse", "runner", "track", "race", "date", "saddle", "number", "no"
    ])]

    sample = df[
        df.astype(str).apply(
            lambda r: r.str.upper().str.contains("NIMBUSTWOTHOUSAND|NIMBUS").any(),
            axis=1
        )
    ].head(20)

    rows.append({
        "source": name,
        "file": str(path),
        "status": "FOUND",
        "rows": len(df),
        "cols": len(cols),
        "key_like_columns": " | ".join(key_like[:80]),
        "score_like_columns": " | ".join(score_like[:120]),
        "nimbus_rows_found": len(sample),
        "nimbus_columns_with_values": " | ".join(
            [c for c in score_like if len(sample) and sample[c].notna().any()]
        ) if len(sample) else ""
    })

out = DATA / "edgeiq_visible_score_breakdown_path_v1.csv"
pd.DataFrame(rows).to_csv(out, index=False)

report = DATA / "edgeiq_visible_score_breakdown_path_v1_report.txt"
with open(report, "w", encoding="utf-8") as f:
    f.write("[EDGEIQ_VISIBLE_SCORE_BREAKDOWN_PATH_AUDIT]\n")
    f.write(f"out={out}\n")
    f.write(f"rows={len(rows)}\n")
    for r in rows:
        f.write("\n---\n")
        for k,v in r.items():
            f.write(f"{k}: {v}\n")

print("[VISIBLE_SCORE_BREAKDOWN_PATH_AUDIT] COMPLETE")
print(out)
print(report)
