from pathlib import Path
import pandas as pd
import numpy as np
import re

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "dashboard" / "racing-dashboard"
PUBLIC = DASH / "public" / "data"

OUT = PUBLIC / "edgeiq_positional_dna_engine_v1.csv"
DIAG = PUBLIC / "edgeiq_positional_dna_engine_v1_diagnostics.csv"

SOURCE_CANDIDATES = [
    ROOT / "all_horse_runs_rated.csv",
    ROOT / "outputs" / "all_horse_runs_rated.csv",
    PUBLIC / "all_horse_runs_rated.csv",
    ROOT / "all_horse_runs_excluded.csv",
    ROOT / "outputs" / "all_horse_runs_excluded.csv",
    PUBLIC / "all_horse_runs_excluded.csv",
]

def clean(x):
    return re.sub(r"\s+", " ", str(x or "").upper().strip())

def num(x, default=np.nan):
    try:
        s = str(x).strip()
        if not s:
            return default
        return float(re.sub(r"[^\d\.\-]", "", s))
    except Exception:
        return default

def pick(row, cols):
    for c in cols:
        if c in row and str(row.get(c, "")).strip():
            return row.get(c)
    return ""

def parse_in_run(raw):
    s = str(raw or "").strip()
    if not s:
        return []

    nums = re.findall(r"\d+", s)
    return [float(x) for x in nums if x.isdigit()]

def positional_bucket(avg_pos):
    if pd.isna(avg_pos):
        return "UNKNOWN"
    if avg_pos <= 3:
        return "LEADER"
    if avg_pos <= 6:
        return "ON PACE"
    if avg_pos <= 10:
        return "MIDFIELD"
    return "BACKMARKER"

frames = []
sources_used = []

print("=" * 100)
print("EDGEIQ POSITIONAL DNA ENGINE V1")
print("=" * 100)

for path in SOURCE_CANDIDATES:
    if not path.exists():
        continue

    try:
        df = pd.read_csv(path, dtype=str, low_memory=False)

        if "horse" not in df.columns:
            continue

        print(f"READING: {path}")
        sources_used.append(str(path))
        df["_source_file"] = path.name
        frames.append(df)

    except Exception as e:
        print(f"FAILED: {path} -> {e}")

if not frames:
    raise SystemExit("NO POSITIONAL SOURCE FILES FOUND")

raw = pd.concat(frames, ignore_index=True)

rows = []

for _, r in raw.iterrows():
    horse = clean(r.get("horse"))
    if not horse:
        continue

    in_run_raw = pick(r, ["in_run_positions_raw", "in_run", "inrun", "positions_in_run"])
    in_run_nums = parse_in_run(in_run_raw)

    pos_800 = num(pick(r, ["pos_800", "position_800", "position_800m"]))
    pos_600 = num(pick(r, ["pos_600", "position_600", "position_600m"]))
    pos_400 = num(pick(r, ["pos_400", "position_400", "position_400m"]))
    pos_200 = num(pick(r, ["pos_200", "position_200", "position_200m"]))

    if len(in_run_nums) >= 1 and pd.isna(pos_800):
        pos_800 = in_run_nums[0]

    if len(in_run_nums) >= 2 and pd.isna(pos_600):
        pos_600 = in_run_nums[1]

    if len(in_run_nums) >= 3 and pd.isna(pos_400):
        pos_400 = in_run_nums[2]

    if len(in_run_nums) >= 4 and pd.isna(pos_200):
        pos_200 = in_run_nums[3]

    early_positions = [x for x in [pos_800, pos_600] if not pd.isna(x)]
    turn_positions = [x for x in [pos_600, pos_400] if not pd.isna(x)]
    late_positions = [x for x in [pos_400, pos_200] if not pd.isna(x)]

    avg_early = np.nan if not early_positions else float(np.mean(early_positions))
    avg_turn = np.nan if not turn_positions else float(np.mean(turn_positions))
    avg_late_pos = np.nan if not late_positions else float(np.mean(late_positions))

    finish_pos = num(pick(r, ["finish_pos_num", "finish_pos", "finish_pos_raw"]))
    margin = num(pick(r, ["margin_num", "margin", "margin_l", "comp_margin"]))
    last600 = num(pick(r, ["sectional_600_seconds", "sectional_600", "last_600m", "last_600m_sec"]))

    if not pd.isna(avg_early):
        if avg_early <= 3:
            style = "LEADER"
        elif avg_early <= 6:
            style = "ON PACE"
        elif avg_early <= 10:
            style = "MIDFIELD"
        else:
            style = "BACKMARKER"
    else:
        style = "UNKNOWN"

    gained_late = np.nan
    if not pd.isna(avg_early) and not pd.isna(avg_late_pos):
        gained_late = avg_early - avg_late_pos

    rows.append({
        "horse": horse,
        "source_file": r.get("_source_file", ""),
        "pos_800": pos_800,
        "pos_600": pos_600,
        "pos_400": pos_400,
        "pos_200": pos_200,
        "avg_early_position": avg_early,
        "avg_turn_position": avg_turn,
        "avg_late_position": avg_late_pos,
        "run_style_observed": style,
        "finish_pos": finish_pos,
        "margin": margin,
        "last600": last600,
        "gained_late_positions": gained_late,
    })

obs = pd.DataFrame(rows)

valid = obs[obs["run_style_observed"] != "UNKNOWN"].copy()

if valid.empty:
    raise SystemExit("NO VALID POSITIONAL OBSERVATIONS FOUND")

summary_rows = []

for horse, g in obs.groupby("horse"):
    gv = g[g["run_style_observed"] != "UNKNOWN"]

    total = len(g)
    valid_samples = len(gv)

    leader_pct = round((gv["run_style_observed"] == "LEADER").mean() * 100, 1) if valid_samples else 0.0
    onpace_pct = round((gv["run_style_observed"] == "ON PACE").mean() * 100, 1) if valid_samples else 0.0
    midfield_pct = round((gv["run_style_observed"] == "MIDFIELD").mean() * 100, 1) if valid_samples else 0.0
    backmarker_pct = round((gv["run_style_observed"] == "BACKMARKER").mean() * 100, 1) if valid_samples else 0.0

    avg_early = round(gv["avg_early_position"].mean(), 2) if valid_samples else np.nan
    avg_turn = round(gv["avg_turn_position"].mean(), 2) if valid_samples else np.nan
    avg_late = round(gv["avg_late_position"].mean(), 2) if valid_samples else np.nan
    avg_gain = round(gv["gained_late_positions"].mean(), 2) if valid_samples and gv["gained_late_positions"].notna().any() else np.nan

    early_speed_rating = 50
    if not pd.isna(avg_early):
      early_speed_rating = round(max(1, min(100, 105 - (avg_early * 7))), 1)

    if leader_pct >= 45:
        archetype = "NATURAL LEADER"
    elif leader_pct + onpace_pct >= 60:
        archetype = "FORWARD / ON PACE"
    elif backmarker_pct >= 45:
        archetype = "BACKMARKER / CLOSER"
    elif midfield_pct >= 60:
        archetype = "MIDFIELD STALKER"
    else:
        archetype = "TACTICALLY FLEXIBLE"

    closing_profile = "UNKNOWN"
    if not pd.isna(avg_gain):
        if avg_gain >= 3:
            closing_profile = "STRONG CLOSER"
        elif avg_gain >= 1:
            closing_profile = "MILD CLOSER"
        elif avg_gain <= -2:
            closing_profile = "FADES / PRESSURE RISK"
        else:
            closing_profile = "HOLDS POSITION"

    confidence = "LOW"
    if valid_samples >= 8:
        confidence = "HIGH"
    elif valid_samples >= 3:
        confidence = "MEDIUM"

    summary_rows.append({
        "horse": horse,
        "total_rows": total,
        "valid_position_samples": valid_samples,
        "leader_pct": leader_pct,
        "onpace_pct": onpace_pct,
        "midfield_pct": midfield_pct,
        "backmarker_pct": backmarker_pct,
        "avg_early_position": avg_early,
        "avg_turn_position": avg_turn,
        "avg_late_position": avg_late,
        "avg_late_gain_positions": avg_gain,
        "early_speed_rating": early_speed_rating,
        "run_style_archetype": archetype,
        "closing_profile": closing_profile,
        "positional_confidence": confidence,
    })

summary = pd.DataFrame(summary_rows)

summary = summary.sort_values(
    ["positional_confidence", "early_speed_rating", "valid_position_samples"],
    ascending=[True, False, False]
)

summary.to_csv(OUT, index=False)

diag = pd.DataFrame([{
    "horses": len(summary),
    "raw_rows": len(obs),
    "valid_position_rows": len(valid),
    "high_confidence": int((summary["positional_confidence"] == "HIGH").sum()),
    "medium_confidence": int((summary["positional_confidence"] == "MEDIUM").sum()),
    "low_confidence": int((summary["positional_confidence"] == "LOW").sum()),
    "sources_used": " | ".join(sources_used),
    "output": str(OUT),
}])

diag.to_csv(DIAG, index=False)

print("=" * 100)
print("POSITIONAL DNA BUILT")
print("=" * 100)
print(diag.to_string(index=False))
print()
print(summary.head(40).to_string(index=False))
