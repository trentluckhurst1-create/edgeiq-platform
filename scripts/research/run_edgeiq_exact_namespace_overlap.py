"""Research-only exact-ID identity namespace check; NEVER certifies Stage006 mapping.

Grok's suggested join between Racing.com and Racing Australia canonical IDs cannot
establish an EIQ_HORSE to LAB245B crosswalk. Report disjoint namespaces honestly.
No name-based joins, scores, changes to config, or model promotion.
"""
import argparse
from pathlib import Path
import pandas as pd


def read_checked(path, required):
    df = pd.read_csv(path, dtype="string")
    missing = set(required).difference(df.columns)
    if missing:
        raise RuntimeError(f"STOP MISSING_COLUMNS {path}: {sorted(missing)}")
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rcom", default="config/performance-intelligence/edgeiq_horse_performance_identity_map_v1.csv")
    parser.add_argument("--ra", default="config/performance-intelligence/edgeiq_racing_australia_horse_identity_crosswalk_v1.csv")
    parser.add_argument("--pit", default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage006\V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv")
    parser.add_argument("--warehouse", default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245B_WAREHOUSE_RUNNER_LVS.csv")
    args = parser.parse_args()
    rcom = read_checked(Path(args.rcom), ["source_horse_name", "canonical_horse_id", "identity_status", "evidence_sha256"])
    ra = read_checked(Path(args.ra), ["source_horse_id", "canonical_horse_id", "approval_status", "identity_evidence_sha256", "match_method"])
    rcom = rcom[rcom.identity_status.eq("APPROVED")].copy()
    ra = ra[ra.approval_status.eq("APPROVED")].copy()
    for name, frame, key in (("RCOM_SOURCE", rcom, "source_horse_name"), ("RA_SOURCE", ra, "source_horse_id")):
        if frame[key].isna().any() or frame[key].duplicated().any():
            raise RuntimeError(f"STOP {name}_MISSING_OR_DUPLICATE_SOURCE")
    if rcom.evidence_sha256.isna().any() or ra.identity_evidence_sha256.isna().any():
        raise RuntimeError("STOP MISSING_EVIDENCE_HASH")
    overlap = set(rcom.canonical_horse_id.dropna()) & set(ra.canonical_horse_id.dropna())
    print("APPROVED_RCOM_ROWS", len(rcom), "APPROVED_RA_ROWS", len(ra), "EXACT_SHARED_CANONICAL_IDS", len(overlap))
    pit = read_checked(Path(args.pit), ["_horse", "_race"])
    warehouse = read_checked(Path(args.warehouse), ["canonical_horse_id", "canonical_race_id"])
    pit_horse = set(pit._horse.dropna())
    wh_horse = set(warehouse.canonical_horse_id.dropna())
    pit_race = set(pit._race.dropna())
    wh_race = set(warehouse.canonical_race_id.dropna())
    print("PIT_UNIQUE_HORSES", len(pit_horse), "WAREHOUSE_UNIQUE_HORSES", len(wh_horse),
          "EXACT_HORSE_ID_OVERLAP", len(pit_horse & wh_horse))
    print("PIT_UNIQUE_RACES", len(pit_race), "WAREHOUSE_UNIQUE_RACES", len(wh_race),
          "EXACT_RACE_ID_OVERLAP", len(pit_race & wh_race))
    print("RCOM_MAP_IS_NOT_EIQ_STAGE006_CROSSWALK")
    print("OVERLAP_IS_DIAGNOSTIC_ONLY_NOT_IDENTITY_CERTIFICATION")
    print("NO_SCORING_NO_MODEL_PROMOTION")


if __name__ == "__main__":
    main()
