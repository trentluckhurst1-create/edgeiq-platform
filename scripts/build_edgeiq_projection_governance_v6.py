import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PROJECTION_FILE = DATA / "edgeiq_current_field_projection_v5_2.csv"
STRENGTH_FILE = DATA / "edgeiq_strength_adjusted_ratings_v2.csv"

OUT_FILE = DATA / "edgeiq_projection_governance_v6.csv"
AUDIT_FILE = DATA / "edgeiq_projection_governance_v6_audit.csv"


def num(v, default=np.nan):
    try:
        if pd.isna(v):
            return default
        if str(v).strip() == "":
            return default
        return float(v)
    except Exception:
        return default


def clean_key(v):
    if pd.isna(v):
        return ""
    return "".join(ch for ch in str(v).upper().strip() if ch.isalnum())


def projection_status(row):
    starts = num(row.get("starts_found_v5_2"), 0)
    proj = num(row.get("projected_rating_v5_2"), np.nan)
    method = str(row.get("projection_method_v5_2", "")).upper()
    hist = str(row.get("history_match_status_v5_2", "")).upper()
    horse = str(row.get("horse", "")).upper()

    if starts <= 0 or pd.isna(proj):
        if "IMPORT" in method or "(GB)" in horse or "(IRE)" in horse or "(FR)" in horse or "(USA)" in horse or "(JPN)" in horse:
            return "IMPORT_UNKNOWN"
        return "FIRST_STARTER_OR_UNKNOWN"

    if starts == 1:
        return "LIMITED_DATA_1_START"

    if starts == 2:
        return "LIMITED_DATA_2_STARTS"

    if starts < 5:
        return "LIMITED_DATA_3_4_STARTS"

    if "MATCHED" in hist:
        return "PROVEN"

    return "PROVEN_UNCLEAR_HISTORY"


def governance_score(row):
    status = str(row.get("projection_status_v6", ""))

    if status == "PROVEN":
        return 100
    if status == "PROVEN_UNCLEAR_HISTORY":
        return 90
    if status == "LIMITED_DATA_3_4_STARTS":
        return 72
    if status == "LIMITED_DATA_2_STARTS":
        return 58
    if status == "LIMITED_DATA_1_START":
        return 45
    if status == "IMPORT_UNKNOWN":
        return 38
    if status == "FIRST_STARTER_OR_UNKNOWN":
        return 25

    return 40


def projection_floor(row):
    status = str(row.get("projection_status_v6", ""))

    if status == "PROVEN":
        return 50
    if status == "PROVEN_UNCLEAR_HISTORY":
        return 45
    if status == "LIMITED_DATA_3_4_STARTS":
        return 38
    if status == "LIMITED_DATA_2_STARTS":
        return 32
    if status == "LIMITED_DATA_1_START":
        return 28
    if status == "IMPORT_UNKNOWN":
        return 26
    if status == "FIRST_STARTER_OR_UNKNOWN":
        return 22

    return 30


def confidence_band(v):
    v = num(v, 0)

    if v >= 85:
        return "HIGH"
    if v >= 70:
        return "MEDIUM"
    if v >= 50:
        return "LOW"
    return "VERY_LOW"


def reason(row):
    status = str(row.get("projection_status_v6", ""))

    if status == "PROVEN":
        return "proven runner with sufficient matched history"
    if status == "PROVEN_UNCLEAR_HISTORY":
        return "usable projection but history match is not fully clear"
    if status == "LIMITED_DATA_3_4_STARTS":
        return "limited exposed form; moderate uncertainty penalty"
    if status == "LIMITED_DATA_2_STARTS":
        return "two-start profile; strong uncertainty penalty"
    if status == "LIMITED_DATA_1_START":
        return "one-start profile; high uncertainty penalty"
    if status == "IMPORT_UNKNOWN":
        return "import or overseas profile without enough local evidence"
    if status == "FIRST_STARTER_OR_UNKNOWN":
        return "no race-history projection; unknown runner governance penalty"

    return "projection governance fallback"


def main():
    if not PROJECTION_FILE.exists():
        raise FileNotFoundError(f"Missing {PROJECTION_FILE}")

    proj = pd.read_csv(PROJECTION_FILE)

    out = proj.copy()

    if "horse_key" not in out.columns:
        if "horse_match_key_v5_2" in out.columns:
            out["horse_key"] = out["horse_match_key_v5_2"]
        else:
            out["horse_key"] = out["horse"].map(clean_key)

    out["horse_key_join"] = out["horse_key"].map(clean_key)

    out["projection_status_v6"] = out.apply(projection_status, axis=1)
    out["projection_governance_score_v6"] = out.apply(governance_score, axis=1)
    out["projection_floor_v6"] = out.apply(projection_floor, axis=1)
    out["projection_governance_confidence_v6"] = out["projection_governance_score_v6"].map(confidence_band)
    out["projection_governance_reason_v6"] = out.apply(reason, axis=1)

    raw_proj = pd.to_numeric(out.get("projected_rating_v5_2"), errors="coerce")
    floor = pd.to_numeric(out["projection_floor_v6"], errors="coerce").fillna(30)

    out["governed_projection_rating_v6"] = raw_proj.fillna(floor)
    out["governed_projection_rating_v6"] = np.where(
        out["projection_status_v6"].isin(["FIRST_STARTER_OR_UNKNOWN", "IMPORT_UNKNOWN"]),
        np.minimum(out["governed_projection_rating_v6"], floor),
        out["governed_projection_rating_v6"],
    )

    out["governed_projection_rating_v6"] = pd.to_numeric(out["governed_projection_rating_v6"], errors="coerce").fillna(floor).round(3)

    if STRENGTH_FILE.exists():
        strength = pd.read_csv(STRENGTH_FILE)

        if "horse_key" not in strength.columns:
            if "horse_match_key_v5_2" in strength.columns:
                strength["horse_key"] = strength["horse_match_key_v5_2"]
            else:
                strength["horse_key"] = strength["horse"].map(clean_key)

        strength["horse_key_join"] = strength["horse_key"].map(clean_key)

        join_cols = [
            "race_context_key_v5_2",
            "horse_key_join",
            "strength_adjusted_rating_v2",
            "strength_adjusted_band_v2",
        ]

        join_cols = [c for c in join_cols if c in strength.columns]

        if "race_context_key_v5_2" in out.columns and "race_context_key_v5_2" in strength.columns:
            out = out.merge(
                strength[join_cols].drop_duplicates(["race_context_key_v5_2", "horse_key_join"]),
                on=["race_context_key_v5_2", "horse_key_join"],
                how="left",
            )

    audit = pd.DataFrame([{
        "rows": len(out),
        "unique_races": out["race_context_key_v5_2"].nunique() if "race_context_key_v5_2" in out.columns else 0,
        "unique_horses": out["horse_key_join"].nunique(),
        "proven": int((out["projection_status_v6"] == "PROVEN").sum()),
        "proven_unclear_history": int((out["projection_status_v6"] == "PROVEN_UNCLEAR_HISTORY").sum()),
        "limited_3_4_starts": int((out["projection_status_v6"] == "LIMITED_DATA_3_4_STARTS").sum()),
        "limited_2_starts": int((out["projection_status_v6"] == "LIMITED_DATA_2_STARTS").sum()),
        "limited_1_start": int((out["projection_status_v6"] == "LIMITED_DATA_1_START").sum()),
        "import_unknown": int((out["projection_status_v6"] == "IMPORT_UNKNOWN").sum()),
        "first_starter_or_unknown": int((out["projection_status_v6"] == "FIRST_STARTER_OR_UNKNOWN").sum()),
        "avg_governance_score": round(float(out["projection_governance_score_v6"].mean()), 3),
        "avg_governed_projection": round(float(out["governed_projection_rating_v6"].mean()), 3),
        "output": str(OUT_FILE),
    }])

    out.to_csv(OUT_FILE, index=False)
    audit.to_csv(AUDIT_FILE, index=False)

    print("[PROJECTION_GOVERNANCE_V6] COMPLETE")
    print(f"rows={len(out)}")
    print(f"wrote={OUT_FILE}")
    print(f"audit={AUDIT_FILE}")
    print(out["projection_status_v6"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
