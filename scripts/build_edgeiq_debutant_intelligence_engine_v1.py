from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import re

DATA = Path("./public/data")

LIVE = DATA / "edgeiq_live_runner_board_governed_v1.csv"
OUT = DATA / "edgeiq_debutant_intelligence_engine_v1.csv"
SUMMARY = DATA / "edgeiq_debutant_intelligence_engine_v1_summary.csv"
AUDIT = DATA / "edgeiq_debutant_intelligence_engine_v1_audit.csv"
REPORT = DATA / "edgeiq_debutant_intelligence_engine_v1_report.txt"

candidates = [
    DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv",
    DATA / "edgeiq_results_warehouse_full_v1.csv",
    DATA / "edgeiq_historical_results_warehouse_full_v1.csv",
    DATA / "edgeiq_results_warehouse_v1.csv",
]

RESULTS = next((p for p in candidates if p.exists()), None)
if RESULTS is None:
    found = sorted(DATA.glob("*warehouse*.csv"), key=lambda p: p.stat().st_size, reverse=True)
    RESULTS = found[0] if found else None

if RESULTS is None or not RESULTS.exists():
    raise FileNotFoundError("No historical warehouse CSV found")

hist = pd.read_csv(RESULTS, dtype=str, keep_default_na=False, low_memory=False)
live = pd.read_csv(LIVE, dtype=str, keep_default_na=False, low_memory=False)

def norm_name(x):
    return re.sub(r"[^A-Z0-9]+", "", str(x).upper())

def pick_col(df, options):
    lower = {c.lower(): c for c in df.columns}
    for o in options:
        if o.lower() in lower:
            return lower[o.lower()]
    for c in df.columns:
        cl = c.lower()
        if any(o.lower() in cl for o in options):
            return c
    return None

horse_col = pick_col(hist, ["horse", "runner", "horse_name"])
trainer_col = pick_col(hist, ["trainer"])
jockey_col = pick_col(hist, ["jockey"])
finish_col = pick_col(hist, ["finish", "finish_position", "placing", "position"])
race_date_col = pick_col(hist, ["race_date", "date"])

if not all([horse_col, trainer_col, jockey_col, finish_col]):
    raise RuntimeError(f"Required cols missing. horse={horse_col}, trainer={trainer_col}, jockey={jockey_col}, finish={finish_col}")

hist["_horse_key"] = hist[horse_col].map(norm_name)
hist["_trainer_key"] = hist[trainer_col].map(norm_name)
hist["_jockey_key"] = hist[jockey_col].map(norm_name)
hist["_finish_num"] = pd.to_numeric(hist[finish_col], errors="coerce")

if race_date_col:
    hist["_race_date_dt"] = pd.to_datetime(hist[race_date_col], errors="coerce")
    hist = hist.sort_values(["_horse_key", "_race_date_dt"])
else:
    hist = hist.sort_values(["_horse_key"])

hist["_career_start_no"] = hist.groupby("_horse_key").cumcount() + 1
debs = hist[(hist["_career_start_no"] == 1) & hist["_horse_key"].ne("")].copy()

def stats(group_col, prefix):
    s = (
        debs.groupby(group_col)
        .agg(
            **{
                f"{prefix}_first_starter_starts": ("_horse_key", "size"),
                f"{prefix}_first_starter_wins": ("_finish_num", lambda x: int((x == 1).sum())),
                f"{prefix}_first_starter_places": ("_finish_num", lambda x: int((x <= 3).sum())),
            }
        )
        .reset_index()
    )
    starts = s[f"{prefix}_first_starter_starts"].replace(0, np.nan)
    s[f"{prefix}_first_starter_win_pct"] = (s[f"{prefix}_first_starter_wins"] / starts * 100).round(2)
    s[f"{prefix}_first_starter_place_pct"] = (s[f"{prefix}_first_starter_places"] / starts * 100).round(2)
    return s

trainer_stats = stats("_trainer_key", "trainer")
jockey_stats = stats("_jockey_key", "jockey")

combo = debs.copy()
combo["_combo_key"] = combo["_trainer_key"] + "__" + combo["_jockey_key"]
combo_stats = (
    combo.groupby("_combo_key")
    .agg(
        combo_first_starter_starts=("_horse_key", "size"),
        combo_first_starter_wins=("_finish_num", lambda x: int((x == 1).sum())),
        combo_first_starter_places=("_finish_num", lambda x: int((x <= 3).sum())),
    )
    .reset_index()
)
combo_starts = combo_stats["combo_first_starter_starts"].replace(0, np.nan)
combo_stats["combo_first_starter_win_pct"] = (combo_stats["combo_first_starter_wins"] / combo_starts * 100).round(2)
combo_stats["combo_first_starter_place_pct"] = (combo_stats["combo_first_starter_places"] / combo_starts * 100).round(2)

live["_trainer_key"] = live["trainer"].map(norm_name) if "trainer" in live.columns else ""
live["_jockey_key"] = live["jockey"].map(norm_name) if "jockey" in live.columns else ""
live["_combo_key"] = live["_trainer_key"] + "__" + live["_jockey_key"]

out = live.merge(trainer_stats, on="_trainer_key", how="left")
out = out.merge(jockey_stats, on="_jockey_key", how="left")
out = out.merge(combo_stats, on="_combo_key", how="left")

for c in [
    "trainer_first_starter_starts","trainer_first_starter_wins","trainer_first_starter_places",
    "trainer_first_starter_win_pct","trainer_first_starter_place_pct",
    "jockey_first_starter_starts","jockey_first_starter_wins","jockey_first_starter_places",
    "jockey_first_starter_win_pct","jockey_first_starter_place_pct",
    "combo_first_starter_starts","combo_first_starter_wins","combo_first_starter_places",
    "combo_first_starter_win_pct","combo_first_starter_place_pct",
]:
    if c in out.columns:
        out[c] = out[c].fillna(0)

out["debutant_intelligence_score"] = (
    np.minimum(out["trainer_first_starter_starts"].astype(float), 50) / 50 * 20 +
    out["trainer_first_starter_win_pct"].astype(float).clip(0, 30) / 30 * 35 +
    out["trainer_first_starter_place_pct"].astype(float).clip(0, 60) / 60 * 20 +
    np.minimum(out["combo_first_starter_starts"].astype(float), 20) / 20 * 10 +
    out["combo_first_starter_win_pct"].astype(float).clip(0, 30) / 30 * 15
).round(1)

out["debutant_intelligence_band"] = pd.cut(
    out["debutant_intelligence_score"],
    bins=[-1, 25, 45, 65, 80, 101],
    labels=["LOW", "WATCH", "POSITIVE", "STRONG", "ELITE"]
).astype(str)

out["debutant_intelligence_summary"] = (
    "Trainer debut: " + out["trainer_first_starter_starts"].astype(int).astype(str) +
    " starts, " + out["trainer_first_starter_win_pct"].round(1).astype(str) +
    "% win | Combo debut: " + out["combo_first_starter_starts"].astype(int).astype(str) +
    " starts, " + out["combo_first_starter_win_pct"].round(1).astype(str) + "% win"
)

out.to_csv(OUT, index=False)

pd.DataFrame([{
    "status": "EDGEIQ_DEBUTANT_INTELLIGENCE_ENGINE_V1_BUILT",
    "historical_source": RESULTS.name,
    "historical_rows": len(hist),
    "debutant_rows": len(debs),
    "live_rows": len(out),
    "trainer_profiles": len(trainer_stats),
    "jockey_profiles": len(jockey_stats),
    "combo_profiles": len(combo_stats),
    "production_changed": "NO",
    "pricing_changed": "NO",
    "ui_changed": "NO",
    "built_at": datetime.now(timezone.utc).isoformat()
}]).to_csv(SUMMARY, index=False)

pd.DataFrame([{
    "historical_source": RESULTS.name,
    "horse_col": horse_col,
    "trainer_col": trainer_col,
    "jockey_col": jockey_col,
    "finish_col": finish_col,
    "race_date_col": race_date_col,
}]).to_csv(AUDIT, index=False)

REPORT.write_text("EDGEIQ_DEBUTANT_INTELLIGENCE_ENGINE_V1 BUILT\n", encoding="utf-8")

print("[EDGEIQ_DEBUTANT_INTELLIGENCE_ENGINE_V1] COMPLETE")
print(f"source={RESULTS}")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(f"audit={AUDIT}")
