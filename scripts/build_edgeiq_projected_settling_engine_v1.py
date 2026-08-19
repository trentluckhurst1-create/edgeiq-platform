from pathlib import Path
import pandas as pd
import re

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"

INFILE = PUBLIC / "live_speed_map_v3.csv"
OUT = PUBLIC / "edgeiq_projected_settling_engine_v1.csv"
DIAG = PUBLIC / "edgeiq_projected_settling_engine_v1_diagnostics.csv"

VIC_TRACKS = {
    "FLEMINGTON","CAULFIELD","SANDOWN","SANDOWN LAKESIDE","SANDOWN HILLSIDE",
    "MOONEE VALLEY","MORNINGTON","PAKENHAM","PAKENHAM SYNTHETIC","BENDIGO",
    "BALLARAT","BALLARAT SYNTHETIC","GEELONG","WARRNAMBOOL","CRANBOURNE",
    "SALE","TERANG","KILMORE","SEYMOUR","ECHUCA","HAMILTON","COLAC",
    "ARARAT","WANGARATTA","BENALLA","SWAN HILL","MILDURA","KYNETON",
    "CASTERTON","WODONGA","STAWELL","WERRIBEE","YARRA VALLEY","BAIRNSDALE"
}

def clean(x):
    return re.sub(r"\s+", " ", str(x or "").upper().strip())

def num(x, default=0.0):
    try:
        s = str(x).strip()
        if not s:
            return default
        return float(s)
    except Exception:
        return default

def read_csv(path):
    if not path.exists():
        raise SystemExit(f"MISSING INPUT: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False)

def style(row):
    raw = clean(row.get("speed_map_bucket") or row.get("map_style") or row.get("run_style_cluster") or row.get("sectional_profile"))
    if "LEAD" in raw:
        return "LEADER"
    if "PACE" in raw:
        return "ON PACE"
    if "BACK" in raw or "CLOS" in raw or "LATE" in raw:
        return "BACKMARKER"
    return "MIDFIELD"

def clamp(x, lo=1, hi=100):
    return max(lo, min(hi, x))

df = read_csv(INFILE)

df["track_clean"] = df["track"].map(clean)
df = df[df["track_clean"].isin(VIC_TRACKS)].copy()

rows = []

for (race_date, track, race_no), g in df.groupby(["race_date", "track", "race_no"], dropna=False):
    field = g.copy()
    field_size = len(field)

    for _, r in field.iterrows():
        barrier = num(r.get("barrier"))
        distance = num(r.get("distance"))
        weapon = num(r.get("sectional_weapon_score"))
        late = num(r.get("late_power_index"))
        fatigue = num(r.get("fatigue_risk_index"))
        run_style = style(r)

        if run_style == "LEADER":
            base = 18
        elif run_style == "ON PACE":
            base = 34
        elif run_style == "MIDFIELD":
            base = 58
        else:
            base = 82

        barrier_adj = 0
        if barrier:
            barrier_rank = barrier / max(field_size, 1)
            if run_style in {"LEADER", "ON PACE"}:
                barrier_adj = barrier_rank * 10
            elif run_style == "MIDFIELD":
                barrier_adj = barrier_rank * 6
            else:
                barrier_adj = barrier_rank * 3

        distance_adj = 0
        if distance <= 1100:
            distance_adj = -4
        elif distance >= 2000:
            distance_adj = 5

        late_adj = 0
        if late >= 80:
            late_adj += 7
        elif late >= 65:
            late_adj += 4

        weapon_adj = 0
        if weapon >= 80 and run_style in {"LEADER", "ON PACE"}:
            weapon_adj -= 4
        elif weapon >= 80:
            weapon_adj += 3

        fatigue_adj = 4 if fatigue >= 75 else 0

        projected_spd = clamp(round(base + barrier_adj + distance_adj + late_adj + weapon_adj + fatigue_adj, 1))

        if projected_spd <= 30:
            settling_band = "LEADER"
        elif projected_spd <= 48:
            settling_band = "ON PACE"
        elif projected_spd <= 72:
            settling_band = "MIDFIELD"
        else:
            settling_band = "BACKMARKER"

        confidence = "LOW"
        if weapon or late or r.get("memory_coverage_grade"):
            confidence = "MEDIUM"
        if (weapon >= 70 or late >= 70) and r.get("memory_coverage_grade") in {"HIGH", "MEDIUM"}:
            confidence = "HIGH"

        rows.append({
            "race_date": race_date,
            "track": track,
            "race_no": race_no,
            "horse": r.get("horse", ""),
            "horse_key": r.get("horse_key", ""),
            "saddlecloth": r.get("horse_no", ""),
            "barrier": r.get("barrier", ""),
            "jockey": r.get("jockey", ""),
            "projected_spd": projected_spd,
            "settling_band": settling_band,
            "source_run_style": run_style,
            "sectional_weapon_score": weapon,
            "late_power_index": late,
            "fatigue_risk_index": fatigue,
            "settling_confidence": confidence,
            "settling_note": f"{settling_band} | SPD {projected_spd} | {confidence}",
        })

out = pd.DataFrame(rows)

out.to_csv(OUT, index=False)

diag = pd.DataFrame([{
    "rows": len(out),
    "races": out[["race_date","track","race_no"]].drop_duplicates().shape[0] if len(out) else 0,
    "leaders": int((out["settling_band"] == "LEADER").sum()) if len(out) else 0,
    "onpace": int((out["settling_band"] == "ON PACE").sum()) if len(out) else 0,
    "midfield": int((out["settling_band"] == "MIDFIELD").sum()) if len(out) else 0,
    "backmarkers": int((out["settling_band"] == "BACKMARKER").sum()) if len(out) else 0,
    "high_confidence": int((out["settling_confidence"] == "HIGH").sum()) if len(out) else 0,
    "output": str(OUT),
}])

diag.to_csv(DIAG, index=False)

print("=" * 100)
print("EDGEIQ PROJECTED SETTLING ENGINE V1 BUILT")
print("=" * 100)
print(diag.to_string(index=False))
print()
print(out.head(30).to_string(index=False))
