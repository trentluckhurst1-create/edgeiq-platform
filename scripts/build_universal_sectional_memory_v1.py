from pathlib import Path
import pandas as pd
import re

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"

FEATURES = PUBLIC / "edgeiq_sectional_feature_engine_v2.csv"
INTEL = PUBLIC / "edgeiq_sectional_intelligence_v2.csv"
MASTER = PUBLIC / "edgeiq_sectional_master_v1.csv"

OUT = PUBLIC / "edgeiq_universal_sectional_memory_v1.csv"
DIAG = PUBLIC / "edgeiq_universal_sectional_memory_v1_diagnostics.csv"

def read(path):
    if not path.exists():
        print(f"MISSING: {path}")
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False)

def clean_key(x):
    return re.sub(r"[^A-Z0-9]", "", str(x or "").upper())

def num(x, default=0.0):
    try:
        s = str(x).strip()
        if not s:
            return default
        return float(s)
    except Exception:
        return default

def pick(row, cols, default=""):
    for c in cols:
        if c in row and str(row.get(c, "")).strip():
            return str(row.get(c, "")).strip()
    return default

def avg(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 2) if vals else 0.0

features = read(FEATURES)
intel = read(INTEL)
master = read(MASTER)

if features.empty and intel.empty and master.empty:
    raise SystemExit("NO SECTIONAL SOURCE FILES FOUND")

horses = {}

def add_row(row, source):
    horse = pick(row, ["horse", "horse_sectional", "runner", "horse_name"])
    hk = clean_key(pick(row, ["horse_key"], horse))
    if not hk:
        return

    if hk not in horses:
        horses[hk] = {
            "horse": horse,
            "horse_key": hk,
            "sources": set(),
            "features": [],
            "intel": [],
            "master": [],
        }

    horses[hk]["sources"].add(source)
    horses[hk][source].append(row)

for _, r in features.iterrows():
    add_row(r, "features")

for _, r in intel.iterrows():
    add_row(r, "intel")

for _, r in master.iterrows():
    add_row(r, "master")

rows = []

for hk, h in horses.items():
    frows = h["features"]
    irows = h["intel"]
    mrows = h["master"]

    latest_f = frows[-1] if frows else {}
    latest_i = irows[-1] if irows else {}
    latest_m = mrows[-1] if mrows else {}

    late_power = avg([num(pick(r, ["late_power_index"])) for r in frows if pick(r, ["late_power_index"])])
    burst = avg([num(pick(r, ["burst_index"])) for r in frows if pick(r, ["burst_index"])])
    sustain = avg([num(pick(r, ["sustain_index"])) for r in frows if pick(r, ["sustain_index"])])
    fatigue = avg([num(pick(r, ["fatigue_risk_index"])) for r in frows if pick(r, ["fatigue_risk_index"])])
    weapon = avg([num(pick(r, ["sectional_weapon_score"])) for r in frows if pick(r, ["sectional_weapon_score"])])

    strength = avg([num(pick(r, ["sectional_strength_score"])) for r in irows if pick(r, ["sectional_strength_score"])])
    hidden = avg([num(pick(r, ["hidden_run_score"])) for r in irows if pick(r, ["hidden_run_score"])])

    if weapon == 0:
        weapon = strength

    run_style_cluster = pick(latest_f, ["run_style_cluster"])
    sectional_profile = pick(latest_i, ["sectional_profile"]) or run_style_cluster
    preferred_distance_bucket = pick(latest_i, ["preferred_distance_bucket"])
    preferred_track = pick(latest_i, ["preferred_track"])

    raw = f"{run_style_cluster} {sectional_profile}".upper()

    if "LEAD" in raw or "SPEED" in raw:
        projected_map_style = "LEADER"
    elif "BURST" in raw or "PEAK" in raw:
        projected_map_style = "ON PACE"
    elif "SUSTAIN" in raw or "CLOS" in raw or "LATE" in raw:
        projected_map_style = "BACKMARKER"
    elif raw.strip():
        projected_map_style = "MIDFIELD"
    else:
        projected_map_style = "UNKNOWN"

    if late_power >= 70 and sustain >= 60:
        best_tempo_setup = "HOT_TEMPO_COLLAPSE"
    elif burst >= 70:
        best_tempo_setup = "SHORT_BURST_SPRINT"
    elif sustain >= 70:
        best_tempo_setup = "SUSTAINED_PRESSURE"
    elif fatigue >= 70:
        best_tempo_setup = "AVOID_PRESSURE"
    else:
        best_tempo_setup = "NEUTRAL"

    coverage_score = min(len(frows) * 15, 45) + min(len(irows) * 15, 30) + min(len(mrows) * 5, 25)

    if coverage_score >= 70:
        coverage_grade = "HIGH"
    elif coverage_score >= 35:
        coverage_grade = "MEDIUM"
    elif coverage_score > 0:
        coverage_grade = "LOW"
    else:
        coverage_grade = "NONE"

    rows.append({
        "horse": h["horse"],
        "horse_key": hk,
        "sectional_sources": "|".join(sorted(h["sources"])),
        "master_rows": len(mrows),
        "feature_rows": len(frows),
        "intelligence_rows": len(irows),
        "coverage_score": coverage_score,
        "coverage_grade": coverage_grade,
        "projected_map_style": projected_map_style,
        "run_style_cluster": run_style_cluster,
        "sectional_profile": sectional_profile,
        "preferred_distance_bucket": preferred_distance_bucket,
        "preferred_track": preferred_track,
        "late_power_index": late_power,
        "burst_index": burst,
        "sustain_index": sustain,
        "fatigue_risk_index": fatigue,
        "sectional_weapon_score": weapon,
        "hidden_run_score": hidden,
        "best_tempo_setup": best_tempo_setup,
        "memory_note": f"{coverage_grade} sectional memory | {projected_map_style} | {best_tempo_setup}",
    })

out = pd.DataFrame(rows)

if out.empty:
    raise SystemExit("NO UNIVERSAL SECTIONAL MEMORY ROWS BUILT")

out = out.sort_values(
    ["coverage_score", "sectional_weapon_score", "late_power_index"],
    ascending=[False, False, False]
)

out.to_csv(OUT, index=False)

diag = pd.DataFrame([{
    "memory_rows": len(out),
    "high_coverage": int((out["coverage_grade"] == "HIGH").sum()),
    "medium_coverage": int((out["coverage_grade"] == "MEDIUM").sum()),
    "low_coverage": int((out["coverage_grade"] == "LOW").sum()),
    "with_weapon_score": int((out["sectional_weapon_score"] > 0).sum()),
    "with_projected_map_style": int((out["projected_map_style"] != "UNKNOWN").sum()),
    "output": str(OUT),
}])

diag.to_csv(DIAG, index=False)

print("=" * 100)
print("EDGEIQ UNIVERSAL SECTIONAL MEMORY V1 BUILT")
print("=" * 100)
print(diag.to_string(index=False))
print()
print(out.head(25).to_string(index=False))
