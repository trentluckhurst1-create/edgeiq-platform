from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

files = [
    ("V1_AGGRESSIVE", DATA / "edgeiq_runner_dna_v6_2_weight_replay_v1_summary.csv"),
    ("V2_SAFE", DATA / "edgeiq_runner_dna_v6_2_weight_replay_v2_safe_summary.csv"),
]

rows = []

for version, path in files:
    if not path.exists():
        continue

    s = pd.read_csv(path, dtype=str).fillna("")
    m = dict(zip(s["metric"], s["value"]))

    rows.append({
        "version": version,
        "top_changed_races": m.get("top_changed_races", ""),
        "avg_abs_score_delta": m.get("avg_abs_score_delta", ""),
        "max_abs_score_delta": m.get("max_abs_score_delta", ""),
        "avg_abs_rank_delta": m.get("avg_abs_rank_delta", ""),
        "max_abs_rank_delta": m.get("max_abs_rank_delta", ""),
        "band_changed_rows": m.get("band_changed_rows", ""),
        "research_only": m.get("research_only", ""),
    })

out = pd.DataFrame(rows)
OUT = DATA / "edgeiq_runner_dna_v6_2_weight_replay_comparison_v1.csv"
out.to_csv(OUT, index=False)

print("[DNA_WEIGHT_REPLAY_COMPARISON_V1] COMPLETE")
print(out.to_string(index=False))
print(f"wrote={OUT}")
