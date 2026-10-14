"""Verify exact Stage006-to-LAB245B observation identity on pre-2025 rows.

Read-only; never uses sealed 2025-26 evaluation outcomes or scores a model.
"""
import argparse
import pandas as pd


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pit", default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage006\V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv")
    p.add_argument("--warehouse", default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245B_WAREHOUSE_RUNNER_LVS.csv")
    a = p.parse_args()
    h = pd.read_csv(a.pit, dtype="string")
    w = pd.read_csv(a.warehouse, dtype="string", usecols=["canonical_race_id", "canonical_horse_id", "race_date", "runner_lvs"])
    required = {"_race", "_horse", "race_date"}
    if not required.issubset(h):
        raise RuntimeError("STOP STAGE006_SCHEMA " + str(sorted(required - set(h))))
    h = h[h.race_date.lt("2025-01-01")].copy()
    w = w[w.race_date.lt("2025-01-01")].copy()
    keys = ["_race", "_horse"]
    if h[keys].isna().any().any() or w[["canonical_race_id", "canonical_horse_id"]].isna().any().any():
        raise RuntimeError("STOP NULL_OBSERVATION_KEYS")
    if h.duplicated(keys).any() or w.duplicated(["canonical_race_id", "canonical_horse_id"]).any():
        raise RuntimeError("STOP DUPLICATE_OBSERVATION_KEYS")
    joined = h.merge(
        w, left_on=keys, right_on=["canonical_race_id", "canonical_horse_id"],
        how="left", indicator=True, validate="one_to_one", suffixes=("_pit", "_warehouse"),
    )
    both = joined["_merge"].eq("both")
    same_date = joined["race_date_pit"].eq(joined["race_date_warehouse"]) & both
    print("PIT_PRE2025_ROWS", len(h))
    print("EXACT_RACE_HORSE_MATCHED", int(both.sum()))
    print("UNMATCHED", int((~both).sum()))
    print("MATCHED_SAME_DATE", int(same_date.sum()))
    print("MATCHED_DATE_CONFLICT", int((both & ~same_date).sum()))
    if "target_lvs" in joined.columns:
        x = pd.to_numeric(joined["target_lvs"], errors="coerce")
        y = pd.to_numeric(joined["runner_lvs"], errors="coerce")
        valid = same_date & x.notna() & y.notna()
        err = (x - y).abs()
        print("TARGET_LVS_NUMERIC_PAIRS", int(valid.sum()))
        print("TARGET_LVS_EXACT", int((valid & err.le(1e-8)).sum()))
        print("TARGET_LVS_MISMATCH", int((valid & err.gt(1e-8)).sum()))
    else:
        print("TARGET_LVS_COLUMN_ABSENT: row identity only; no value parity claim")
    if not both.all() or not same_date.all():
        print("STOP OBSERVATION_IDENTITY_NOT_CERTIFIED")
    else:
        print("OBSERVATION_KEYS_AND_DATES_EXACT: feature and lineage parity still required")
    print("READ_ONLY_NO_SCORING_NO_PROMOTION")


if __name__ == "__main__":
    main()
