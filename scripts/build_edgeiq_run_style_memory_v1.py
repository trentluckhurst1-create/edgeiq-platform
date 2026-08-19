from pathlib import Path
import pandas as pd
import re
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "dashboard" / "racing-dashboard"
PUBLIC = DASH / "public" / "data"

OUTPUT = PUBLIC / "edgeiq_run_style_memory_v1.csv"
DIAG = PUBLIC / "edgeiq_run_style_memory_v1_diagnostics.csv"

SEARCH_PATHS = [
    ROOT / "outputs",
    PUBLIC
]

TARGET_FILES = [
    "edgeiq_results_master.csv",
    "edgeiq_results_review.csv",
    "edgeiq_execution_board_live.csv",
    "edgeiq_execution_board_terminal.csv",
    "race_fields.csv",
    "race_fields_v2.csv",
    "live_speed_map_v3.csv",
]

def clean(x):
    return re.sub(r"\s+", " ", str(x or "").upper().strip())

def num(x, default=0.0):
    try:
        return float(str(x).replace("%","").strip())
    except:
        return default

def find_files():
    found = []

    for root in SEARCH_PATHS:
        if not root.exists():
            continue

        for path in root.rglob("*.csv"):
            if path.name.lower() in [f.lower() for f in TARGET_FILES]:
                found.append(path)

    return list(dict.fromkeys(found))

def classify_run_style(row):
    raw = clean(
        row.get("run_style_cluster")
        or row.get("speed_map_bucket")
        or row.get("map_style")
        or row.get("sectional_profile")
        or row.get("run_style")
    )

    if "LEAD" in raw:
        return "LEADER"

    if "PACE" in raw:
        return "ON_PACE"

    if "BACK" in raw or "CLOSER" in raw or "LATE" in raw:
        return "BACKMARKER"

    return "MIDFIELD"

all_rows = []

files = find_files()

print("=" * 100)
print("EDGEIQ RUN STYLE MEMORY ENGINE V1")
print("=" * 100)
print(f"FILES FOUND: {len(files)}")
print()

for file in files:
    try:
        df = pd.read_csv(file, dtype=str, low_memory=False)

        if "horse" not in df.columns:
            continue

        print(f"READING: {file.name} ({len(df):,} rows)")

        for _, row in df.iterrows():
            horse = clean(row.get("horse"))

            if not horse:
                continue

            run_style = classify_run_style(row)

            barrier = num(row.get("barrier"))
            distance = num(row.get("distance"))

            sectional = num(row.get("sectional_weapon_score"))
            late = num(row.get("late_power_index"))
            fatigue = num(row.get("fatigue_risk_index"))

            early_speed = 0

            if run_style == "LEADER":
                early_speed = 90
            elif run_style == "ON_PACE":
                early_speed = 72
            elif run_style == "MIDFIELD":
                early_speed = 48
            else:
                early_speed = 20

            if barrier <= 4:
                early_speed += 5

            if late >= 80:
                early_speed -= 8

            if sectional >= 80 and run_style in {"LEADER", "ON_PACE"}:
                early_speed += 4

            early_speed = max(1, min(100, early_speed))

            all_rows.append({
                "horse": horse,
                "run_style": run_style,
                "barrier": barrier,
                "distance": distance,
                "sectional_weapon_score": sectional,
                "late_power_index": late,
                "fatigue_risk_index": fatigue,
                "early_speed_rating": early_speed,
            })

    except Exception as e:
        print(f"FAILED: {file.name} -> {e}")

if not all_rows:
    raise SystemExit("NO VALID ROWS FOUND")

df = pd.DataFrame(all_rows)

summary_rows = []

for horse, g in df.groupby("horse"):
    total = len(g)

    leader_pct = round((g["run_style"] == "LEADER").mean() * 100, 1)
    onpace_pct = round((g["run_style"] == "ON_PACE").mean() * 100, 1)
    midfield_pct = round((g["run_style"] == "MIDFIELD").mean() * 100, 1)
    backmarker_pct = round((g["run_style"] == "BACKMARKER").mean() * 100, 1)

    avg_early = round(g["early_speed_rating"].mean(), 1)

    avg_barrier = round(g["barrier"].replace(0, np.nan).mean(), 1)
    avg_distance = round(g["distance"].replace(0, np.nan).mean(), 0)

    if leader_pct >= 45:
        archetype = "NATURAL LEADER"
    elif leader_pct + onpace_pct >= 60:
        archetype = "FORWARD / ON PACE"
    elif backmarker_pct >= 40:
        archetype = "BACKMARKER / CLOSER"
    else:
        archetype = "MIDFIELD / BALANCED"

    pace_adaptability = round(
        len(g["run_style"].unique()) / 4 * 100,
        1
    )

    summary_rows.append({
        "horse": horse,
        "samples": total,
        "leader_pct": leader_pct,
        "onpace_pct": onpace_pct,
        "midfield_pct": midfield_pct,
        "backmarker_pct": backmarker_pct,
        "avg_early_speed_rating": avg_early,
        "avg_barrier": avg_barrier,
        "avg_distance": avg_distance,
        "pace_adaptability": pace_adaptability,
        "run_style_archetype": archetype,
    })

summary = pd.DataFrame(summary_rows)

summary = summary.sort_values(
    ["avg_early_speed_rating", "leader_pct"],
    ascending=[False, False]
)

summary.to_csv(OUTPUT, index=False)

diag = pd.DataFrame([{
    "horses": len(summary),
    "source_rows": len(df),
    "leaders": int((summary["leader_pct"] >= 40).sum()),
    "backmarkers": int((summary["backmarker_pct"] >= 40).sum()),
    "balanced": int((summary["run_style_archetype"] == "MIDFIELD / BALANCED").sum()),
    "output": str(OUTPUT)
}])

diag.to_csv(DIAG, index=False)

print()
print("=" * 100)
print("RUN STYLE MEMORY BUILT")
print("=" * 100)
print(diag.to_string(index=False))
print()
print(summary.head(30).to_string(index=False))
