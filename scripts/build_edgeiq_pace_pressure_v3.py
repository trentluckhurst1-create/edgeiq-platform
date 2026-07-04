from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

INPUT = ROOT / "public" / "data" / "edgeiq_tactical_dna_speed_map_race_summary_v2.csv"
OUTPUT = ROOT / "public" / "data" / "edgeiq_pace_pressure_v3.csv"
AUDIT = ROOT / "public" / "data" / "edgeiq_pace_pressure_v3_audit.csv"

ALIASES = {
    "race_date": ["race_date", "meeting_date", "date", "meetingDate"],
    "track": ["track", "venue", "meeting_name", "location"],
    "race_no": ["race_no", "race_number", "raceNo", "race"],
    "field_size": ["field_size", "runners", "runner_count", "active_runners", "total_runners"],
    "leader_count": ["leader_count", "leaders", "expected_leaders", "leader_runners"],
    "onpace_count": ["onpace_count", "on_pace_count", "onpace", "on_pace", "pace_runners"],
    "midfield_count": ["midfield_count", "midfield"],
    "backmarker_count": ["backmarker_count", "backmarkers", "backmarker"],
    "unknown_count": ["unknown_count", "unknown"],
    "expected_leaders": ["expected_leaders", "leader_count", "leaders"],
}

def find_col(df, key):
    cols = list(df.columns)
    lower = {c.lower(): c for c in cols}
    for a in ALIASES.get(key, []):
        if a in cols:
            return a
        if a.lower() in lower:
            return lower[a.lower()]
    return None

def num(v, default=0.0):
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default

def get(row, col, default=0.0):
    if col is None:
        return default
    return num(row.get(col), default)

def pace_band(row, cols):
    leaders = get(row, cols["leader_count"])
    onpace = get(row, cols["onpace_count"])
    midfield = get(row, cols["midfield_count"])
    backmarkers = get(row, cols["backmarker_count"])
    unknown = get(row, cols["unknown_count"])
    expected_leaders = get(row, cols["expected_leaders"], leaders)

    raw_field = get(row, cols["field_size"])
    inferred_field = leaders + onpace + midfield + backmarkers + unknown
    field_size = max(raw_field, inferred_field, 1)

    leader_rate = leaders / field_size
    pressure_rate = (leaders + onpace) / field_size

    score = (
        expected_leaders * 1.35
        + leaders * 1.15
        + onpace * 0.55
        + pressure_rate * 3.0
        + leader_rate * 2.0
    )

    if expected_leaders <= 0.25 and leaders <= 0 and onpace <= 1:
        band = "VERY_SLOW"
    elif score < 2.25:
        band = "SLOW"
    elif score < 4.25:
        band = "MODERATE"
    elif score < 6.25:
        band = "GENUINE"
    elif score < 8.25:
        band = "FAST"
    else:
        band = "EXTREME"

    return pd.Series({
        "field_size_v3": field_size,
        "leader_count_v3": leaders,
        "onpace_count_v3": onpace,
        "midfield_count_v3": midfield,
        "backmarker_count_v3": backmarkers,
        "unknown_count_v3": unknown,
        "expected_leaders_v3": expected_leaders,
        "pace_pressure_score_v3": round(score, 3),
        "pace_pressure_v3": band,
    })

def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing input: {INPUT}")

    df = pd.read_csv(INPUT)
    cols = {k: find_col(df, k) for k in ALIASES.keys()}

    print("[PACE_PRESSURE_V3] INPUT COLUMNS")
    print(", ".join(df.columns))
    print("[PACE_PRESSURE_V3] COLUMN MAP")
    for k, v in cols.items():
        print(f"{k}={v}")

    calc = df.apply(lambda r: pace_band(r, cols), axis=1)
    out = pd.concat([df.copy(), calc], axis=1)

    out["pace_pressure_confidence_v3"] = np.where(
        out["field_size_v3"] >= 8,
        "HIGH",
        np.where(out["field_size_v3"] >= 5, "MEDIUM", "LOW")
    )

    out["pace_pressure_engine"] = "PACE_PRESSURE_V3"
    out["pace_pressure_input"] = INPUT.name

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False)

    id_cols = [c for c in [cols["race_date"], cols["track"], cols["race_no"]] if c is not None]
    unique_races = out[id_cols].drop_duplicates().shape[0] if id_cols else len(out)

    audit = pd.DataFrame([{
        "input_rows": len(out),
        "unique_races": unique_races,
        "avg_field_size_v3": round(out["field_size_v3"].mean(), 2),
        "very_slow": int((out["pace_pressure_v3"] == "VERY_SLOW").sum()),
        "slow": int((out["pace_pressure_v3"] == "SLOW").sum()),
        "moderate": int((out["pace_pressure_v3"] == "MODERATE").sum()),
        "genuine": int((out["pace_pressure_v3"] == "GENUINE").sum()),
        "fast": int((out["pace_pressure_v3"] == "FAST").sum()),
        "extreme": int((out["pace_pressure_v3"] == "EXTREME").sum()),
        "mapped_race_date_col": cols["race_date"] or "",
        "mapped_track_col": cols["track"] or "",
        "mapped_race_no_col": cols["race_no"] or "",
        "mapped_field_size_col": cols["field_size"] or "",
        "mapped_leader_col": cols["leader_count"] or "",
        "mapped_onpace_col": cols["onpace_count"] or "",
        "output": str(OUTPUT),
    }])

    audit.to_csv(AUDIT, index=False)

    print("[PACE_PRESSURE_V3] COMPLETE")
    print(f"input_rows={len(out)}")
    print(f"wrote={OUTPUT}")
    print(f"audit={AUDIT}")
    print(out["pace_pressure_v3"].value_counts(dropna=False).to_string())

if __name__ == "__main__":
    main()
