from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT = DATA / "edgeiq_class_recovery_engine_v3.csv"
OUTPUT = DATA / "edgeiq_historical_class_clean_v3.csv"
AUDIT = DATA / "edgeiq_historical_class_clean_v3_audit.csv"


USABLE_STATUS = {"RECOVERED", "KEPT_EXISTING"}
EXCLUDE_STATUS = {"EXCLUDE_TRIAL_JUMPOUT"}
JUMPS_OR_HIGHWEIGHT = {"JUMPS_RATING_BAND", "BM120", "HURDLE", "STEEPLECHASE"}
BLACKTYPE = {"GROUP 1", "GROUP 2", "GROUP 3", "LISTED"}
OPEN_SET_WEIGHTS = {"OPEN", "SET WEIGHTS", "SET WEIGHTS PENALTIES"}
REGIONAL_RESTRICTED = {"HIGHWAY", "MIDWAY", "COUNTRY", "PROVINCIAL"}
RESTRICTED_SERIES = {"WESTSPEED"}


def normalise_class(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).upper().strip().split())


def main() -> None:
    print("=" * 90)
    print("EDGEIQ HISTORICAL CLASS CLEAN V3")
    print("=" * 90)

    if not INPUT.exists():
        raise FileNotFoundError(f"Missing input: {INPUT}")

    df = pd.read_csv(INPUT, dtype=str, keep_default_na=False, low_memory=False)

    required = {"race_class_recovered", "class_recovery_status"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing required input columns: {missing}")

    status = df["class_recovery_status"].astype(str).str.upper().str.strip()
    df["race_class_model_v3"] = df["race_class_recovered"].map(normalise_class)

    df["is_class_usable_v3"] = status.isin(USABLE_STATUS)
    df["is_excluded_from_class_model_v3"] = status.isin(EXCLUDE_STATUS) | df["race_class_model_v3"].eq("TRIAL_OR_JUMPOUT")

    df["class_model_family_v3"] = "UNRESOLVED"
    df.loc[df["race_class_model_v3"].str.match(r"^BM[0-9]{2,3}$", na=False), "class_model_family_v3"] = "BENCHMARK"
    df.loc[df["race_class_model_v3"].str.match(r"^CLASS [1-6]$", na=False), "class_model_family_v3"] = "CLASS"
    df.loc[df["race_class_model_v3"].eq("MAIDEN"), "class_model_family_v3"] = "MAIDEN"
    df.loc[df["race_class_model_v3"].isin(BLACKTYPE), "class_model_family_v3"] = "BLACKTYPE"
    df.loc[df["race_class_model_v3"].isin(OPEN_SET_WEIGHTS), "class_model_family_v3"] = "OPEN_SET_WEIGHTS"
    df.loc[df["race_class_model_v3"].isin(REGIONAL_RESTRICTED), "class_model_family_v3"] = "REGIONAL_RESTRICTED"
    df.loc[df["race_class_model_v3"].isin(RESTRICTED_SERIES), "class_model_family_v3"] = "RESTRICTED_SERIES"
    df.loc[df["race_class_model_v3"].isin(JUMPS_OR_HIGHWEIGHT), "class_model_family_v3"] = "JUMPS_OR_HIGHWEIGHT"
    df.loc[df["is_excluded_from_class_model_v3"], "class_model_family_v3"] = "EXCLUDED_TRIAL_JUMPOUT"

    df["class_model_confidence_v3"] = "LOW"
    df.loc[status.eq("KEPT_EXISTING"), "class_model_confidence_v3"] = "HIGH"
    df.loc[status.eq("RECOVERED"), "class_model_confidence_v3"] = "MEDIUM"
    df.loc[df["class_model_family_v3"].eq("UNRESOLVED"), "class_model_confidence_v3"] = "UNRESOLVED"
    df.loc[df["class_model_family_v3"].eq("EXCLUDED_TRIAL_JUMPOUT"), "class_model_confidence_v3"] = "EXCLUDED"

    df["class_clean_engine_version"] = "V3"
    df["built_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    df.to_csv(OUTPUT, index=False)

    audit_rows = [
        {"metric": "rows_loaded", "value": len(df)},
        {"metric": "rows_written", "value": len(df)},
        {"metric": "rows_usable_class", "value": int(df["is_class_usable_v3"].sum())},
        {"metric": "rows_excluded_trial_jumpout", "value": int(df["is_excluded_from_class_model_v3"].sum())},
        {"metric": "rows_unresolved_family", "value": int(df["class_model_family_v3"].eq("UNRESOLVED").sum())},
        {"metric": "benchmark_rows", "value": int(df["class_model_family_v3"].eq("BENCHMARK").sum())},
        {"metric": "class_rows", "value": int(df["class_model_family_v3"].eq("CLASS").sum())},
        {"metric": "maiden_rows", "value": int(df["class_model_family_v3"].eq("MAIDEN").sum())},
        {"metric": "blacktype_rows", "value": int(df["class_model_family_v3"].eq("BLACKTYPE").sum())},
        {"metric": "open_set_weights_rows", "value": int(df["class_model_family_v3"].eq("OPEN_SET_WEIGHTS").sum())},
        {"metric": "regional_restricted_rows", "value": int(df["class_model_family_v3"].eq("REGIONAL_RESTRICTED").sum())},
        {"metric": "restricted_series_rows", "value": int(df["class_model_family_v3"].eq("RESTRICTED_SERIES").sum())},
        {"metric": "jumps_or_highweight_rows", "value": int(df["class_model_family_v3"].eq("JUMPS_OR_HIGHWEIGHT").sum())},
    ]

    for family, count in df["class_model_family_v3"].value_counts().sort_index().items():
        audit_rows.append({"metric": f"family_count_{family}", "value": int(count)})

    for confidence, count in df["class_model_confidence_v3"].value_counts().sort_index().items():
        audit_rows.append({"metric": f"confidence_count_{confidence}", "value": int(count)})

    audit = pd.DataFrame(audit_rows)
    audit.to_csv(AUDIT, index=False)

    print(f"wrote: {OUTPUT}")
    print(f"wrote: {AUDIT}")
    print(audit.to_string(index=False))
    print("=" * 90)


if __name__ == "__main__":
    main()
