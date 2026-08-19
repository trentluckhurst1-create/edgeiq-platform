from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

INPUT = ROOT / "public" / "data" / "edgeiq_pace_pressure_v3.csv"
OUTPUT = ROOT / "public" / "data" / "edgeiq_race_shape_engine_v1.csv"
AUDIT = ROOT / "public" / "data" / "edgeiq_race_shape_engine_v1_audit.csv"

def num(v, default=0.0):
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default

def race_shape(row):
    pace = str(row.get("pace_pressure_v3", "")).upper().strip()

    leaders = num(row.get("leader_count_v3"))
    onpace = num(row.get("onpace_count_v3"))
    midfield = num(row.get("midfield_count_v3"))
    backmarkers = num(row.get("backmarker_count_v3"))
    field_size = max(num(row.get("field_size_v3")), 1)
    expected_leaders = num(row.get("expected_leaders_v3"), leaders)

    leader_rate = leaders / field_size
    onpace_rate = onpace / field_size
    backmarker_rate = backmarkers / field_size

    reason = []

    if expected_leaders >= 3.5 or leaders >= 4 or pace == "EXTREME":
        shape = "CHAOTIC_SPEED"
        reason.append("multiple leaders / extreme tempo")
    elif expected_leaders >= 2.25 and leaders >= 2 and pace in ["FAST", "GENUINE"]:
        shape = "LEADER_BATTLE"
        reason.append("two or more likely leaders contesting control")
    elif leaders <= 1 and onpace <= 2 and pace in ["VERY_SLOW", "SLOW"]:
        shape = "SIT_AND_SPRINT"
        reason.append("limited speed and low pressure")
    elif leaders == 1 and onpace <= 3 and pace in ["SLOW", "MODERATE", "GENUINE"]:
        shape = "LONE_LEADER"
        reason.append("one main leader with manageable pressure")
    elif pace in ["MODERATE", "GENUINE"] and onpace_rate >= 0.18:
        shape = "CONTROLLED_TEMPO"
        reason.append("balanced on-pace group should control rhythm")
    elif pace in ["GENUINE", "FAST"]:
        shape = "GENUINE_PRESSURE"
        reason.append("race should be honestly run")
    else:
        shape = "CONTROLLED_TEMPO"
        reason.append("default balanced race shape")

    if backmarker_rate >= 0.45 and pace in ["FAST", "EXTREME"]:
        reason.append("high backmarker share may benefit late runners")
    if leader_rate >= 0.25:
        reason.append("high leader density")
    if onpace_rate >= 0.30:
        reason.append("strong on-pace presence")

    return pd.Series({
        "race_shape_v1": shape,
        "race_shape_reason_v1": "; ".join(reason),
        "leader_rate_v1": round(leader_rate, 3),
        "onpace_rate_v1": round(onpace_rate, 3),
        "backmarker_rate_v1": round(backmarker_rate, 3),
    })

def shape_confidence(row):
    cov = num(row.get("dna_coverage"))
    field = num(row.get("field_size_v3"))

    if cov >= 0.85 and field >= 8:
        return "HIGH"
    if cov >= 0.65 and field >= 6:
        return "MEDIUM"
    return "LOW"

def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing input: {INPUT}")

    df = pd.read_csv(INPUT)

    required = [
        "pace_pressure_v3",
        "field_size_v3",
        "leader_count_v3",
        "onpace_count_v3",
        "midfield_count_v3",
        "backmarker_count_v3",
        "expected_leaders_v3",
    ]

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    calc = df.apply(race_shape, axis=1)
    out = pd.concat([df.copy(), calc], axis=1)

    out["race_shape_confidence_v1"] = out.apply(shape_confidence, axis=1)
    out["race_shape_engine"] = "RACE_SHAPE_ENGINE_V1"
    out["race_shape_input"] = INPUT.name

    out.to_csv(OUTPUT, index=False)

    audit = pd.DataFrame([{
        "input_rows": len(out),
        "unique_races": out["race_key"].nunique() if "race_key" in out.columns else len(out),
        "lone_leader": int((out["race_shape_v1"] == "LONE_LEADER").sum()),
        "controlled_tempo": int((out["race_shape_v1"] == "CONTROLLED_TEMPO").sum()),
        "genuine_pressure": int((out["race_shape_v1"] == "GENUINE_PRESSURE").sum()),
        "leader_battle": int((out["race_shape_v1"] == "LEADER_BATTLE").sum()),
        "chaotic_speed": int((out["race_shape_v1"] == "CHAOTIC_SPEED").sum()),
        "sit_and_sprint": int((out["race_shape_v1"] == "SIT_AND_SPRINT").sum()),
        "high_confidence": int((out["race_shape_confidence_v1"] == "HIGH").sum()),
        "medium_confidence": int((out["race_shape_confidence_v1"] == "MEDIUM").sum()),
        "low_confidence": int((out["race_shape_confidence_v1"] == "LOW").sum()),
        "output": str(OUTPUT),
    }])

    audit.to_csv(AUDIT, index=False)

    print("[RACE_SHAPE_ENGINE_V1] COMPLETE")
    print(f"input_rows={len(out)}")
    print(f"wrote={OUTPUT}")
    print(f"audit={AUDIT}")
    print(out["race_shape_v1"].value_counts(dropna=False).to_string())

if __name__ == "__main__":
    main()
