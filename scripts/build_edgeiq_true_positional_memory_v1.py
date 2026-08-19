from pathlib import Path
import pandas as pd
import numpy as np
import re

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "dashboard" / "racing-dashboard"
PUBLIC = DASH / "public" / "data"

OUTPUT = PUBLIC / "edgeiq_true_positional_memory_v1.csv"
DIAG = PUBLIC / "edgeiq_true_positional_memory_v1_diagnostics.csv"

SEARCH_FILES = [
    ROOT / "outputs" / "edgeiq_results_master.csv",
    ROOT / "outputs" / "edgeiq_results_review.csv",
    PUBLIC / "live_speed_map_v3.csv",
    PUBLIC / "race_fields.csv",
    PUBLIC / "full_career_form.csv",
    PUBLIC / "form_card_runs.csv",
]

def clean(x):
    return re.sub(r"\s+", " ", str(x or "").upper().strip())

def num(x, default=0):
    try:
        return float(str(x).replace("%","").strip())
    except:
        return default

def style_from_text(v):
    s = clean(v)

    if any(x in s for x in ["LEAD","LEADER","ROLLING"]):
        return "LEADER"

    if any(x in s for x in ["PACE","ONPACE","PRESS"]):
        return "ON_PACE"

    if any(x in s for x in ["BACK","CLOSER","LATE","TAIL"]):
        return "BACKMARKER"

    return "MIDFIELD"

all_rows = []

print("=" * 100)
print("EDGEIQ TRUE POSITIONAL MEMORY ENGINE V1")
print("=" * 100)

for file in SEARCH_FILES:

    if not file.exists():
        print(f"SKIP MISSING: {file.name}")
        continue

    try:
        df = pd.read_csv(file, dtype=str, low_memory=False)

        if "horse" not in df.columns:
            print(f"NO HORSE COLUMN: {file.name}")
            continue

        print(f"READING: {file.name} ({len(df):,} rows)")

        for _, row in df.iterrows():

            horse = clean(row.get("horse"))

            if not horse:
                continue

            barrier = num(
                row.get("barrier")
                or row.get("Barrier")
                or row.get("gate")
            )

            distance = num(row.get("distance"))

            settling_pos = num(
                row.get("settling_position")
                or row.get("settling_pos")
                or row.get("position_in_run")
                or row.get("in_run_position")
            )

            run_style = style_from_text(
                row.get("run_style_cluster")
                or row.get("speed_map_bucket")
                or row.get("map_style")
                or row.get("sectional_profile")
                or row.get("run_style")
            )

            sectional = num(row.get("sectional_weapon_score"))
            late = num(row.get("late_power_index"))
            fatigue = num(row.get("fatigue_risk_index"))

            if settling_pos > 0:
                if settling_pos <= 3:
                    run_style = "LEADER"
                elif settling_pos <= 6:
                    run_style = "ON_PACE"
                elif settling_pos <= 10:
                    run_style = "MIDFIELD"
                else:
                    run_style = "BACKMARKER"

            early_speed = 50

            if run_style == "LEADER":
                early_speed = 90
            elif run_style == "ON_PACE":
                early_speed = 74
            elif run_style == "MIDFIELD":
                early_speed = 52
            elif run_style == "BACKMARKER":
                early_speed = 28

            if barrier <= 4 and run_style in ["LEADER", "ON_PACE"]:
                early_speed += 4

            if barrier >= 12 and run_style == "BACKMARKER":
                early_speed += 3

            if late >= 80:
                early_speed -= 7

            if sectional >= 80 and run_style in ["LEADER", "ON_PACE"]:
                early_speed += 5

            early_speed = max(1, min(100, round(early_speed,1)))

            all_rows.append({
                "horse": horse,
                "run_style": run_style,
                "barrier": barrier,
                "distance": distance,
                "settling_position": settling_pos,
                "early_speed_rating": early_speed,
                "sectional_weapon_score": sectional,
                "late_power_index": late,
                "fatigue_risk_index": fatigue,
            })

    except Exception as e:
        print(f"FAILED: {file.name} -> {e}")

if not all_rows:
    raise SystemExit("NO POSITIONAL MEMORY BUILT")

df = pd.DataFrame(all_rows)

summary_rows = []

for horse, g in df.groupby("horse"):

    total = len(g)

    leader_pct = round((g["run_style"] == "LEADER").mean() * 100,1)
    onpace_pct = round((g["run_style"] == "ON_PACE").mean() * 100,1)
    midfield_pct = round((g["run_style"] == "MIDFIELD").mean() * 100,1)
    backmarker_pct = round((g["run_style"] == "BACKMARKER").mean() * 100,1)

    avg_speed = round(g["early_speed_rating"].mean(),1)

    avg_barrier = round(g["barrier"].replace(0,np.nan).mean(),1)
    avg_distance = round(g["distance"].replace(0,np.nan).mean(),0)

    avg_settling = round(g["settling_position"].replace(0,np.nan).mean(),1)

    adaptability = round(
        len(g["run_style"].unique()) / 4 * 100,
        1
    )

    if leader_pct >= 45:
        archetype = "NATURAL LEADER"

    elif leader_pct + onpace_pct >= 60:
        archetype = "FORWARD PRESSURE"

    elif backmarker_pct >= 45:
        archetype = "BACKMARKER CLOSER"

    elif midfield_pct >= 70:
        archetype = "MIDFIELD STALKER"

    else:
        archetype = "TACTICALLY FLEXIBLE"

    summary_rows.append({
        "horse": horse,
        "samples": total,
        "leader_pct": leader_pct,
        "onpace_pct": onpace_pct,
        "midfield_pct": midfield_pct,
        "backmarker_pct": backmarker_pct,
        "avg_early_speed_rating": avg_speed,
        "avg_settling_position": avg_settling,
        "avg_barrier": avg_barrier,
        "avg_distance": avg_distance,
        "pace_adaptability": adaptability,
        "run_style_archetype": archetype,
    })

summary = pd.DataFrame(summary_rows)

summary = summary.sort_values(
    ["avg_early_speed_rating","leader_pct"],
    ascending=[False,False]
)

summary.to_csv(OUTPUT,index=False)

diag = pd.DataFrame([{
    "horses": len(summary),
    "source_rows": len(df),
    "leaders": int((summary["leader_pct"] >= 40).sum()),
    "onpace": int((summary["onpace_pct"] >= 40).sum()),
    "backmarkers": int((summary["backmarker_pct"] >= 40).sum()),
    "output": str(OUTPUT)
}])

diag.to_csv(DIAG,index=False)

print()
print("=" * 100)
print("TRUE POSITIONAL MEMORY BUILT")
print("=" * 100)
print(diag.to_string(index=False))
print()
print(summary.head(40).to_string(index=False))
