from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import re

DATA = Path("./public/data")

HIST = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
LIVE = DATA / "edgeiq_live_runner_board_governed_v1.csv"

OUT = DATA / "edgeiq_gear_profile_engine_v1.csv"
SUMMARY = DATA / "edgeiq_gear_profile_engine_v1_summary.csv"
AUDIT = DATA / "edgeiq_gear_profile_engine_v1_audit.csv"
REPORT = DATA / "edgeiq_gear_profile_engine_v1_report.txt"

def norm_name(x):
    return re.sub(r"[^A-Z0-9]+", "", str(x).upper())

def pick_col(df, names):
    lower = {c.lower(): c for c in df.columns}
    for n in names:
        if n.lower() in lower:
            return lower[n.lower()]
    for c in df.columns:
        if any(n.lower() in c.lower() for n in names):
            return c
    return None

def split_gears(x):
    if pd.isna(x):
        return []
    s = str(x).strip()
    if not s:
        return []
    return [g.strip().upper() for g in re.split(r",|\|", s) if g.strip()]

hist = pd.read_csv(HIST, dtype=str, keep_default_na=False, low_memory=False)
live = pd.read_csv(LIVE, dtype=str, keep_default_na=False, low_memory=False)

horse_col = pick_col(hist, ["horse", "horse_name", "runner"])
trainer_col = pick_col(hist, ["trainer"])
jockey_col = pick_col(hist, ["jockey"])
finish_col = pick_col(hist, ["finish", "finish_position", "placing", "position"])
gear_col = pick_col(hist, ["gear_changes"])
sp_col = pick_col(hist, ["sp", "starting_price", "fixed_win", "price"])

if not all([horse_col, trainer_col, jockey_col, finish_col, gear_col]):
    raise RuntimeError(
        f"Missing required columns: horse={horse_col}, trainer={trainer_col}, jockey={jockey_col}, finish={finish_col}, gear={gear_col}"
    )

hist["_horse_key"] = hist[horse_col].map(norm_name)
hist["_trainer_key"] = hist[trainer_col].map(norm_name)
hist["_jockey_key"] = hist[jockey_col].map(norm_name)
hist["_finish_num"] = pd.to_numeric(hist[finish_col], errors="coerce")
hist["_sp_num"] = pd.to_numeric(hist[sp_col], errors="coerce") if sp_col else np.nan
hist["_gear_list"] = hist[gear_col].map(split_gears)

exploded = hist.explode("_gear_list").copy()
exploded = exploded[exploded["_gear_list"].astype(str).str.len() > 0].copy()
exploded = exploded.rename(columns={"_gear_list": "gear_change"})

exploded["won"] = exploded["_finish_num"].eq(1)
exploded["placed"] = exploded["_finish_num"].le(3)
exploded["profit_1u"] = np.where(
    exploded["won"] & exploded["_sp_num"].notna(),
    exploded["_sp_num"] - 1,
    np.where(exploded["_sp_num"].notna(), -1, np.nan)
)

def build_profile(group_cols, prefix):
    g = (
        exploded.groupby(group_cols)
        .agg(
            starts=("gear_change", "size"),
            wins=("won", "sum"),
            places=("placed", "sum"),
            avg_sp=("_sp_num", "mean"),
            roi=("profit_1u", "mean"),
        )
        .reset_index()
    )
    g["win_pct"] = (g["wins"] / g["starts"] * 100).round(2)
    g["place_pct"] = (g["places"] / g["starts"] * 100).round(2)
    g["avg_sp"] = g["avg_sp"].round(2)
    g["roi_pct"] = (g["roi"] * 100).round(2)
    g = g.drop(columns=["roi"])
    return g.rename(columns={
        "starts": f"{prefix}_gear_starts",
        "wins": f"{prefix}_gear_wins",
        "places": f"{prefix}_gear_places",
        "win_pct": f"{prefix}_gear_win_pct",
        "place_pct": f"{prefix}_gear_place_pct",
        "avg_sp": f"{prefix}_gear_avg_sp",
        "roi_pct": f"{prefix}_gear_roi_pct",
    })

gear_profile = build_profile(["gear_change"], "overall")
trainer_gear = build_profile(["_trainer_key", "gear_change"], "trainer")
jockey_gear = build_profile(["_jockey_key", "gear_change"], "jockey")
horse_gear = build_profile(["_horse_key", "gear_change"], "horse")

live["_horse_key"] = live["horse"].map(norm_name) if "horse" in live.columns else ""
live["_trainer_key"] = live["trainer"].map(norm_name) if "trainer" in live.columns else ""
live["_jockey_key"] = live["jockey"].map(norm_name) if "jockey" in live.columns else ""

if "gear_changes" in live.columns:
    live["_live_gear_list"] = live["gear_changes"].map(split_gears)
else:
    live["_live_gear_list"] = [[] for _ in range(len(live))]

out = live.explode("_live_gear_list").copy()
out = out.rename(columns={"_live_gear_list": "gear_change"})
out["gear_change"] = out["gear_change"].fillna("").astype(str)

out = out.merge(gear_profile, on="gear_change", how="left")
out = out.merge(trainer_gear, on=["_trainer_key", "gear_change"], how="left")
out = out.merge(jockey_gear, on=["_jockey_key", "gear_change"], how="left")
out = out.merge(horse_gear, on=["_horse_key", "gear_change"], how="left")

for c in out.columns:
    if c.endswith("_gear_starts") or c.endswith("_gear_wins") or c.endswith("_gear_places"):
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0).astype(int)
    elif "_gear_" in c:
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0)

out["gear_intelligence_score"] = (
    np.minimum(out.get("trainer_gear_starts", 0), 50) / 50 * 20 +
    out.get("trainer_gear_win_pct", 0).clip(0, 30) / 30 * 30 +
    out.get("trainer_gear_place_pct", 0).clip(0, 60) / 60 * 15 +
    np.minimum(out.get("jockey_gear_starts", 0), 50) / 50 * 10 +
    out.get("jockey_gear_win_pct", 0).clip(0, 30) / 30 * 10 +
    np.minimum(out.get("horse_gear_starts", 0), 20) / 20 * 5 +
    out.get("overall_gear_win_pct", 0).clip(0, 25) / 25 * 10
).round(1)

out["gear_intelligence_band"] = pd.cut(
    out["gear_intelligence_score"],
    bins=[-1, 24, 44, 64, 79, 101],
    labels=["RISK", "CAUTION", "NEUTRAL", "POSITIVE", "ELITE"]
).astype(str)

out["gear_intelligence_summary"] = np.where(
    out["gear_change"].astype(str).str.len() > 0,
    "Gear: " + out["gear_change"].astype(str) +
    " | Trainer: " + out["trainer_gear_starts"].astype(str) + " starts, " +
    out["trainer_gear_win_pct"].round(1).astype(str) + "% win | Overall: " +
    out["overall_gear_starts"].astype(str) + " starts, " +
    out["overall_gear_win_pct"].round(1).astype(str) + "% win",
    "No listed gear change"
)

out.to_csv(OUT, index=False)

pd.DataFrame([{
    "status": "EDGEIQ_GEAR_PROFILE_ENGINE_V1_BUILT",
    "historical_rows": len(hist),
    "historical_rows_with_gear": int(hist[gear_col].astype(str).str.strip().ne("").sum()),
    "gear_observation_rows": len(exploded),
    "unique_gear_changes": int(exploded["gear_change"].nunique()),
    "live_rows": len(live),
    "output_rows": len(out),
    "overall_profiles": len(gear_profile),
    "trainer_gear_profiles": len(trainer_gear),
    "jockey_gear_profiles": len(jockey_gear),
    "horse_gear_profiles": len(horse_gear),
    "production_changed": "NO",
    "pricing_changed": "NO",
    "ui_changed": "NO",
    "built_at": datetime.now(timezone.utc).isoformat()
}]).to_csv(SUMMARY, index=False)

pd.DataFrame([{
    "historical_source": HIST.name,
    "live_source": LIVE.name,
    "horse_col": horse_col,
    "trainer_col": trainer_col,
    "jockey_col": jockey_col,
    "finish_col": finish_col,
    "gear_col": gear_col,
    "sp_col": sp_col,
}]).to_csv(AUDIT, index=False)

REPORT.write_text(
    "EDGEIQ_GEAR_PROFILE_ENGINE_V1 BUILT\n"
    "Production changed: NO\n"
    "Pricing changed: NO\n"
    "UI changed: NO\n",
    encoding="utf-8"
)

print("[EDGEIQ_GEAR_PROFILE_ENGINE_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(f"audit={AUDIT}")
print(f"report={REPORT}")
