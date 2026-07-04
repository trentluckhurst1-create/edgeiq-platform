from pathlib import Path
import pandas as pd
import numpy as np
import re

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"

INVENTORY = PUBLIC / "edgeiq_positional_expansion_source_inventory_v1.csv"
OBS_OUT = PUBLIC / "edgeiq_master_positional_observations_v1.csv"
DNA_OUT = PUBLIC / "edgeiq_master_positional_dna_v1.csv"
DIAG = PUBLIC / "edgeiq_master_positional_dna_v1_diagnostics.csv"

def clean(x):
    return re.sub(r"\s+", " ", str(x or "").upper().strip())

def strip_suffix(x):
    s = clean(x)
    s = re.sub(r"\s*\((NZ|GB|IRE|FR|USA|JPN|SAF|GER|ARG|BRZ|CAN|AUS)\)\s*$", "", s)
    return clean(s)

def compact(x):
    return re.sub(r"[^A-Z0-9]", "", strip_suffix(x))

def num(x, default=np.nan):
    try:
        s = str(x).strip()
        if not s:
            return default
        return float(re.sub(r"[^\d\.\-]", "", s))
    except Exception:
        return default

def find_col(cols, candidates):
    lower = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand.lower() in lower:
            return lower[cand.lower()]
    for c in cols:
        cl = c.lower()
        for cand in candidates:
            if cand.lower() in cl:
                return c
    return None

def parse_pos(raw, marker):
    s = str(raw or "")
    m = re.search(r"(\d+)(?:st|nd|rd|th)?\s*@" + str(marker) + r"m", s, re.I)
    return float(m.group(1)) if m else np.nan

def pct(mask):
    return round(float(mask.mean() * 100), 1) if len(mask) else 0.0

if not INVENTORY.exists():
    raise SystemExit("RUN INVENTORY SCRIPT FIRST")

inventory = pd.read_csv(INVENTORY, dtype=str).fillna("")
inventory["rows_estimate_num"] = pd.to_numeric(inventory["rows_estimate"], errors="coerce").fillna(0)

# Keep strong, useful files only.
sources = inventory[
    (inventory["score"].astype(float) >= 6) &
    (inventory["rows_estimate_num"] >= 50)
].copy()

rows = []
used = []

print("=" * 100)
print("EDGEIQ MASTER POSITIONAL DNA V1")
print("=" * 100)
print(f"SOURCES SELECTED: {len(sources)}")

for _, src in sources.iterrows():
    path = Path(src["file"])

    if not path.exists():
        continue

    try:
        df = pd.read_csv(path, dtype=str, low_memory=False).fillna("")
        cols = list(df.columns)

        horse_col = find_col(cols, ["horse_name", "horse", "runner", "runner_name"])
        raw_col = find_col(cols, ["in_run_positions_raw", "in_run"])
        finish_col = find_col(cols, ["finish_pos_num", "finish_pos", "finish_pos_raw"])
        field_col = find_col(cols, ["field_size_num", "field_size"])
        margin_col = find_col(cols, ["margin_num", "margin", "margin_l"])
        last600_col = find_col(cols, ["sectional_600_seconds", "sectional_600", "last_600m", "last_600m_sec"])
        speed_col = find_col(cols, ["speed_figure"])
        sectional_col = find_col(cols, ["sectional_figure"])
        date_col = find_col(cols, ["run_date", "date", "race_date"])
        track_col = find_col(cols, ["track"])
        distance_col = find_col(cols, ["distance"])
        barrier_col = find_col(cols, ["barrier_num", "barrier", "gate"])

        if not horse_col or not raw_col:
            continue

        used.append(str(path))
        print(f"READING: {path.name} ({len(df):,} rows)")

        for _, r in df.iterrows():
            horse = strip_suffix(r.get(horse_col, ""))
            if not horse:
                continue

            raw = r.get(raw_col, "")

            pos800 = parse_pos(raw, 800)
            pos400 = parse_pos(raw, 400)

            if pd.isna(pos800) and pd.isna(pos400):
                continue

            rows.append({
                "horse": horse,
                "canonical_key": compact(horse),
                "source_file": path.name,
                "run_date": r.get(date_col, "") if date_col else "",
                "track": r.get(track_col, "") if track_col else "",
                "distance": num(r.get(distance_col, "")) if distance_col else np.nan,
                "barrier": num(r.get(barrier_col, "")) if barrier_col else np.nan,
                "field_size": num(r.get(field_col, "")) if field_col else np.nan,
                "finish_pos": num(r.get(finish_col, "")) if finish_col else np.nan,
                "margin": num(r.get(margin_col, "")) if margin_col else np.nan,
                "last600": num(r.get(last600_col, "")) if last600_col else np.nan,
                "sectional_figure": num(r.get(sectional_col, "")) if sectional_col else np.nan,
                "speed_figure": num(r.get(speed_col, "")) if speed_col else np.nan,
                "raw_in_run": raw,
                "pos800": pos800,
                "pos400": pos400,
                "gain_800_400": pos800 - pos400 if not pd.isna(pos800) and not pd.isna(pos400) else np.nan,
            })

    except Exception as e:
        print(f"FAILED: {path.name} -> {e}")

obs = pd.DataFrame(rows)

if obs.empty:
    raise SystemExit("NO POSITIONAL OBSERVATIONS CREATED")

obs = obs.drop_duplicates(subset=["canonical_key", "run_date", "track", "distance", "raw_in_run", "finish_pos"])
obs.to_csv(OBS_OUT, index=False)

summary_rows = []

for key, g in obs.groupby("canonical_key"):
    if not key:
        continue

    horse = g["horse"].mode().iloc[0] if not g["horse"].mode().empty else g["horse"].iloc[0]
    samples = len(g)

    avg800 = round(g["pos800"].mean(), 2)
    avg400 = round(g["pos400"].mean(), 2)
    gain = round(g["gain_800_400"].mean(), 2)

    leader_pct = pct(g["pos800"] <= 3)
    onpace_pct = pct((g["pos800"] > 3) & (g["pos800"] <= 6))
    midfield_pct = pct((g["pos800"] > 6) & (g["pos800"] <= 10))
    backmarker_pct = pct(g["pos800"] > 10)

    early_speed = round(max(1, min(100, 108 - (avg800 * 7.5))), 1) if pd.notna(avg800) else 50

    if leader_pct >= 45:
        archetype = "NATURAL LEADER"
    elif leader_pct + onpace_pct >= 60:
        archetype = "FORWARD / ON PACE"
    elif backmarker_pct >= 45:
        archetype = "BACKMARKER / CLOSER"
    elif midfield_pct >= 55:
        archetype = "MIDFIELD STALKER"
    else:
        archetype = "TACTICALLY FLEXIBLE"

    if pd.isna(gain):
        movement = "UNKNOWN"
    elif gain >= 3:
        movement = "SURGES MIDRACE"
    elif gain >= 1:
        movement = "IMPROVES POSITION"
    elif gain <= -3:
        movement = "LOSES POSITION"
    elif gain <= -1:
        movement = "DRIFTS BACK"
    else:
        movement = "HOLDS POSITION"

    confidence = "LOW"
    if samples >= 8:
        confidence = "HIGH"
    elif samples >= 3:
        confidence = "MEDIUM"

    summary_rows.append({
        "horse": horse,
        "canonical_key": key,
        "samples": samples,
        "avg_800m_position": avg800,
        "avg_400m_position": avg400,
        "avg_800_to_400_gain": gain,
        "leader_pct": leader_pct,
        "onpace_pct": onpace_pct,
        "midfield_pct": midfield_pct,
        "backmarker_pct": backmarker_pct,
        "early_speed_rating": early_speed,
        "run_style_archetype": archetype,
        "positional_movement_profile": movement,
        "avg_last600": round(g["last600"].mean(), 2),
        "avg_sectional_figure": round(g["sectional_figure"].mean(), 2),
        "avg_speed_figure": round(g["speed_figure"].mean(), 2),
        "positional_confidence": confidence,
    })

dna = pd.DataFrame(summary_rows)
rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
dna["_rank"] = dna["positional_confidence"].map(rank).fillna(9)
dna = dna.sort_values(["_rank", "early_speed_rating", "samples"], ascending=[True, False, False]).drop(columns=["_rank"])
dna.to_csv(DNA_OUT, index=False)

diag = pd.DataFrame([{
    "sources_used": len(used),
    "observations": len(obs),
    "horses": len(dna),
    "high_confidence": int((dna["positional_confidence"] == "HIGH").sum()),
    "medium_confidence": int((dna["positional_confidence"] == "MEDIUM").sum()),
    "low_confidence": int((dna["positional_confidence"] == "LOW").sum()),
    "observations_output": str(OBS_OUT),
    "dna_output": str(DNA_OUT),
}])
diag.to_csv(DIAG, index=False)

print("=" * 100)
print("MASTER POSITIONAL DNA BUILT")
print("=" * 100)
print(diag.to_string(index=False))
print()
print(dna.head(40).to_string(index=False))
