from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PACE_PRESSURE = DATA / "edgeiq_pace_pressure_v1.csv"
PACE_ADVANTAGE = DATA / "edgeiq_pace_advantage_v1.csv"

OUT = DATA / "edgeiq_pace_trust_v1.csv"
AUDIT = DATA / "edgeiq_pace_trust_v1_audit.csv"

TRUST_SCORE_MAP = {
    "HIGH_TRUST": 100,
    "MEDIUM_TRUST": 50,
    "LOW_TRUST": 25,
    "IGNORE": 0,
}


def trust_decision(pace_band: str, leaders_count: int, on_pace_count: int) -> tuple[int, str, str]:
    forward_count = int(leaders_count) + int(on_pace_count)
    pace_band = str(pace_band).upper().strip()

    if pace_band == "SLOW":
        if forward_count >= 3:
            return 100, "HIGH_TRUST", "SLOW pace with at least 3 forward runners; trust leader/on-pace pace signal"
        if forward_count >= 2:
            return 50, "MEDIUM_TRUST", "SLOW pace with 2 forward runners; use pace signal cautiously"
        return 0, "IGNORE", "SLOW pace but not enough forward pressure clarity"

    if pace_band == "VERY_SLOW":
        if forward_count >= 3:
            return 25, "LOW_TRUST", "VERY_SLOW pace can matter with 3+ forward runners, but trust stays low"
        return 0, "IGNORE", "VERY_SLOW pace generally ignored without enough forward runners"

    if pace_band in {"FAST", "VERY_FAST"}:
        if forward_count >= 4:
            return 25, "LOW_TRUST", "FAST pace with 4+ forward runners; collapse risk exists but trust remains low"
        return 0, "IGNORE", "FAST pace lacks enough forward-runner density for trusted adjustment"

    if pace_band == "NEUTRAL":
        return 0, "IGNORE", "NEUTRAL pace is always ignored for selective trust"

    return 0, "IGNORE", "No selective pace trust condition met"


def main() -> None:
    if not PACE_PRESSURE.exists():
        raise FileNotFoundError(f"Missing pace pressure file: {PACE_PRESSURE}")
    if not PACE_ADVANTAGE.exists():
        raise FileNotFoundError(f"Missing pace advantage file: {PACE_ADVANTAGE}")

    pace_pressure = pd.read_csv(PACE_PRESSURE, low_memory=False)
    pace_advantage = pd.read_csv(PACE_ADVANTAGE, low_memory=False)

    pace_pressure["race_key"] = pace_pressure["race_key"].astype(str).str.strip()
    pace_advantage["race_key"] = pace_advantage["race_key"].astype(str).str.strip()

    decisions = [
        trust_decision(band, leaders, on_pace)
        for band, leaders, on_pace in zip(
            pace_pressure["pace_pressure_band_v1"],
            pace_pressure["leaders_count"],
            pace_pressure["on_pace_count"],
        )
    ]

    pace_pressure["pace_trust_score_v1"] = [item[0] for item in decisions]
    pace_pressure["pace_trust_band_v1"] = [item[1] for item in decisions]
    pace_pressure["pace_trust_reason_v1"] = [item[2] for item in decisions]

    out = pace_pressure[[
        "track",
        "race_no",
        "race_key",
        "field_size",
        "leaders_count",
        "on_pace_count",
        "midfield_count",
        "backmarker_count",
        "unknown_count",
        "pace_pressure_band_v1",
        "pace_trust_score_v1",
        "pace_trust_band_v1",
        "pace_trust_reason_v1",
    ]].copy()
    out = out.sort_values(["track", "race_no"]).reset_index(drop=True)
    out.to_csv(OUT, index=False)

    runner_trust = pace_advantage[["race_key"]].merge(
        out[["race_key", "pace_trust_band_v1"]],
        on="race_key",
        how="left",
    )

    audit_rows = [
        {"metric": "pace_pressure_races", "value": int(len(pace_pressure))},
        {"metric": "pace_advantage_rows", "value": int(len(pace_advantage))},
        {"metric": "pace_trust_rows", "value": int(len(out))},
        {"metric": "trusted_races", "value": int(out["pace_trust_band_v1"].ne("IGNORE").sum())},
        {"metric": "ignored_races", "value": int(out["pace_trust_band_v1"].eq("IGNORE").sum())},
        {"metric": "trusted_runner_rows", "value": int(runner_trust["pace_trust_band_v1"].ne("IGNORE").sum())},
        {"metric": "ignored_runner_rows", "value": int(runner_trust["pace_trust_band_v1"].eq("IGNORE").sum())},
        {"metric": "avg_forward_count", "value": round(float((out["leaders_count"] + out["on_pace_count"]).mean()), 3)},
        {"metric": "forward_count_ge_3_races", "value": int(((out["leaders_count"] + out["on_pace_count"]) >= 3).sum())},
        {"metric": "forward_count_ge_4_races", "value": int(((out["leaders_count"] + out["on_pace_count"]) >= 4).sum())},
    ]

    for band in ["HIGH_TRUST", "MEDIUM_TRUST", "LOW_TRUST", "IGNORE"]:
        audit_rows.append({"metric": f"trust_band::{band}", "value": int(out["pace_trust_band_v1"].eq(band).sum())})
        audit_rows.append({"metric": f"runner_rows::{band}", "value": int(runner_trust["pace_trust_band_v1"].eq(band).sum())})

    for band in ["VERY_FAST", "FAST", "NEUTRAL", "SLOW", "VERY_SLOW", "UNKNOWN"]:
        audit_rows.append({"metric": f"pace_band::{band}", "value": int(out["pace_pressure_band_v1"].astype(str).str.upper().eq(band).sum())})

    pd.DataFrame(audit_rows).to_csv(AUDIT, index=False)

    print("[EDGEIQ_PACE_TRUST_V1] COMPLETE")
    print(f"pace_trust_rows={len(out)}")
    print(f"trusted_races={int(out['pace_trust_band_v1'].ne('IGNORE').sum())}")
    print(f"trusted_runner_rows={int(runner_trust['pace_trust_band_v1'].ne('IGNORE').sum())}")
    print(f"wrote={OUT}")
    print(f"audit={AUDIT}")


if __name__ == "__main__":
    main()
