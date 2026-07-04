from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RATINGS = DATA / "edgeiq_historical_performance_rating_v5_1.csv"
CLASS_PARS = DATA / "edgeiq_class_pars_v5_2.csv"
DISTANCE_PARS = DATA / "edgeiq_distance_pars_v5_1.csv"
CONDITION_PARS = DATA / "edgeiq_condition_pars_v5_1.csv"
OLD_TARGETS = DATA / "edgeiq_race_rating_targets_v5.csv"

OUT = DATA / "edgeiq_race_rating_targets_v5_1.csv"
AUDIT = DATA / "edgeiq_race_rating_targets_v5_1_audit.csv"

TARGET_FORMULA = "0.70*class_par_rating_v5_2 + 0.15*distance_par_rating_v5_1 + 0.15*condition_par_rating_v5_1"

KEY_CLASSES = [
    "GROUP 1",
    "GROUP 2",
    "GROUP 3",
    "LISTED",
    "BM84",
    "BM78",
    "BM70",
    "BM64",
    "BM58",
    "BM56",
    "CLASS 1",
    "CLASS 2",
    "CLASS 3",
    "MAIDEN",
]


def norm(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).upper().strip().split())


def distance_band(distance: object) -> str:
    value = pd.to_numeric(distance, errors="coerce")
    if pd.isna(value):
        return ""
    if value < 800:
        return "UNDER_800"
    if value <= 999:
        return "800-999"
    if value <= 1199:
        return "1000-1199"
    if value <= 1399:
        return "1200-1399"
    if value <= 1599:
        return "1400-1599"
    if value <= 1799:
        return "1600-1799"
    if value <= 1999:
        return "1800-1999"
    if value <= 2199:
        return "2000-2199"
    if value <= 2399:
        return "2200-2399"
    if value <= 2799:
        return "2400-2799"
    return "2800+"


def condition_group(df: pd.DataFrame) -> pd.Series:
    condition = df.get("condition_recovered", pd.Series("", index=df.index)).astype(str).str.upper().str.strip()
    token = df.get("condition_token_recovered", pd.Series("", index=df.index)).astype(str).str.upper().str.strip()
    blob = condition + " " + token

    output = pd.Series("UNKNOWN", index=df.index)
    output = output.mask(blob.str.contains("FIRM", regex=False, na=False), "FIRM")
    output = output.mask(blob.str.contains("GOOD", regex=False, na=False), "GOOD")
    output = output.mask(blob.str.contains("SOFT", regex=False, na=False), "SOFT")
    output = output.mask(blob.str.contains("HEAVY", regex=False, na=False), "HEAVY")
    output = output.mask(blob.str.contains("SYNTH", regex=False, na=False) | blob.str.contains("POLY", regex=False, na=False), "SYNTHETIC")
    return output


def old_v5_target_built_rows() -> int | str:
    if not OLD_TARGETS.exists():
        return ""
    old = pd.read_csv(OLD_TARGETS, dtype=str, keep_default_na=False, low_memory=False, usecols=lambda c: c in {"target_status_v5"})
    if "target_status_v5" not in old.columns:
        return ""
    return int(old["target_status_v5"].eq("TARGET_BUILT").sum())


def audit_row(section: str, metric: str, value: object = "", race_class: str = "", count: object = "", notes: str = "") -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "race_class": race_class,
        "value": value,
        "count": count,
        "notes": notes,
    }


def confidence_series(df: pd.DataFrame) -> pd.Series:
    parts = df[["class_par_confidence_v5_2", "distance_par_confidence_v5_1", "condition_par_confidence_v5_1"]].fillna("MISSING")
    output = pd.Series("HIGH", index=df.index)
    output = output.mask(parts.eq("MEDIUM").any(axis=1), "MEDIUM")
    output = output.mask(parts.isin(["MISSING", "VERY_LOW", "LOW"]).any(axis=1), "LOW")
    output = output.mask(df["target_status_v5_1"].eq("NO_TARGET"), "NO_TARGET")
    return output


def missing_notes(df: pd.DataFrame) -> pd.Series:
    missing_class = df["class_par_rating_v5_2"].isna()
    missing_distance = df["distance_par_rating_v5_1"].isna()
    missing_condition = df["condition_par_rating_v5_1"].isna()

    notes = pd.Series("", index=df.index)
    notes = notes.mask(missing_class, notes + "class_par,")
    notes = notes.mask(missing_distance, notes + "distance_par,")
    notes = notes.mask(missing_condition, notes + "condition_par,")
    notes = notes.str.rstrip(",")
    return notes.mask(notes.eq(""), "").mask(notes.ne(""), "missing " + notes)


def main() -> None:
    print("=" * 90)
    print("EDGEIQ RACE RATING TARGETS V5.1")
    print("=" * 90)

    for path in [RATINGS, CLASS_PARS, DISTANCE_PARS, CONDITION_PARS]:
        if not path.exists():
            raise FileNotFoundError(f"Missing input: {path}")

    ratings = pd.read_csv(RATINGS, dtype=str, keep_default_na=False, low_memory=False)
    class_pars = pd.read_csv(CLASS_PARS, dtype=str, keep_default_na=False, low_memory=False)
    distance_pars = pd.read_csv(DISTANCE_PARS, dtype=str, keep_default_na=False, low_memory=False)
    condition_pars = pd.read_csv(CONDITION_PARS, dtype=str, keep_default_na=False, low_memory=False)

    required_rating = {
        "race_date",
        "track",
        "distance",
        "real_field_size",
        "source_file",
        "race_class_clean_v3_3",
        "condition_recovered",
    }
    required_class = {
        "race_class_clean_v5_2",
        "class_par_rating_v5_2",
        "class_par_confidence_v5_2",
        "class_par_method_v5_2",
        "class_par_hierarchy_adjustment_v5_2",
    }
    required_distance = {
        "distance_band_v5_1",
        "distance_par_rating_v5_1",
        "distance_par_confidence_v5_1",
        "distance_par_method_v5_1",
    }
    required_condition = {
        "condition_group_v5_1",
        "condition_par_rating_v5_1",
        "condition_par_confidence_v5_1",
        "condition_par_method_v5_1",
    }

    missing = {
        "ratings": sorted(required_rating.difference(ratings.columns)),
        "class_pars": sorted(required_class.difference(class_pars.columns)),
        "distance_pars": sorted(required_distance.difference(distance_pars.columns)),
        "condition_pars": sorted(required_condition.difference(condition_pars.columns)),
    }
    missing = {name: cols for name, cols in missing.items() if cols}
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    ratings["distance"] = pd.to_numeric(ratings["distance"], errors="coerce")
    ratings["real_field_size"] = pd.to_numeric(ratings["real_field_size"], errors="coerce")
    ratings["race_class_clean_v5_1"] = ratings["race_class_clean_v3_3"].map(norm)
    ratings["distance_band_v5_1"] = ratings["distance"].apply(distance_band)
    ratings["condition_group_v5_1"] = condition_group(ratings)

    class_keep = class_pars[
        [
            "race_class_clean_v5_2",
            "class_par_rating_v5_2",
            "class_par_confidence_v5_2",
            "class_par_method_v5_2",
            "class_par_hierarchy_adjustment_v5_2",
        ]
    ].copy()
    class_keep["race_class_clean_v5_1"] = class_keep["race_class_clean_v5_2"].map(norm)
    class_keep = class_keep.drop(columns=["race_class_clean_v5_2"]).drop_duplicates("race_class_clean_v5_1", keep="first")

    distance_keep = distance_pars[
        [
            "distance_band_v5_1",
            "distance_par_rating_v5_1",
            "distance_par_confidence_v5_1",
            "distance_par_method_v5_1",
        ]
    ].drop_duplicates("distance_band_v5_1", keep="first")

    condition_keep = condition_pars[
        [
            "condition_group_v5_1",
            "condition_par_rating_v5_1",
            "condition_par_confidence_v5_1",
            "condition_par_method_v5_1",
        ]
    ].drop_duplicates("condition_group_v5_1", keep="first")

    df = ratings.merge(class_keep, on="race_class_clean_v5_1", how="left")
    df = df.merge(distance_keep, on="distance_band_v5_1", how="left")
    df = df.merge(condition_keep, on="condition_group_v5_1", how="left")

    for column in ["class_par_rating_v5_2", "distance_par_rating_v5_1", "condition_par_rating_v5_1"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["race_target_rating_v5_1"] = (
        (0.70 * df["class_par_rating_v5_2"])
        + (0.15 * df["distance_par_rating_v5_1"])
        + (0.15 * df["condition_par_rating_v5_1"])
    )
    df["target_status_v5_1"] = np.where(df["race_target_rating_v5_1"].notna(), "TARGET_BUILT", "NO_TARGET")
    df["target_confidence_v5_1"] = confidence_series(df)
    df["target_notes_v5_1"] = missing_notes(df)
    df["target_formula_v5_1"] = TARGET_FORMULA

    group_cols = [
        "race_date",
        "track",
        "distance",
        "race_class_clean_v5_1",
        "condition_group_v5_1",
        "real_field_size",
        "source_file",
    ]

    agg_cols = {
        "distance_band_v5_1": "first",
        "class_par_rating_v5_2": "first",
        "distance_par_rating_v5_1": "first",
        "condition_par_rating_v5_1": "first",
        "race_target_rating_v5_1": "first",
        "target_status_v5_1": "first",
        "target_confidence_v5_1": "first",
        "class_par_confidence_v5_2": "first",
        "distance_par_confidence_v5_1": "first",
        "condition_par_confidence_v5_1": "first",
        "class_par_method_v5_2": "first",
        "distance_par_method_v5_1": "first",
        "condition_par_method_v5_1": "first",
        "class_par_hierarchy_adjustment_v5_2": "first",
        "target_formula_v5_1": "first",
        "target_notes_v5_1": "first",
    }

    out = df.groupby(group_cols, dropna=False).agg(agg_cols)
    out["runner_rows_in_context"] = df.groupby(group_cols, dropna=False).size()
    out = out.reset_index()

    for column in ["distance", "real_field_size", "class_par_rating_v5_2", "distance_par_rating_v5_1", "condition_par_rating_v5_1", "race_target_rating_v5_1"]:
        out[column] = pd.to_numeric(out[column], errors="coerce").round(2)

    out["built_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    out = out[
        [
            "race_date",
            "track",
            "distance",
            "distance_band_v5_1",
            "race_class_clean_v5_1",
            "condition_group_v5_1",
            "real_field_size",
            "source_file",
            "class_par_rating_v5_2",
            "distance_par_rating_v5_1",
            "condition_par_rating_v5_1",
            "race_target_rating_v5_1",
            "target_status_v5_1",
            "target_confidence_v5_1",
            "class_par_confidence_v5_2",
            "distance_par_confidence_v5_1",
            "condition_par_confidence_v5_1",
            "class_par_method_v5_2",
            "distance_par_method_v5_1",
            "condition_par_method_v5_1",
            "class_par_hierarchy_adjustment_v5_2",
            "target_formula_v5_1",
            "target_notes_v5_1",
            "runner_rows_in_context",
            "built_at",
        ]
    ]
    out.to_csv(OUT, index=False)

    target_built = int(out["target_status_v5_1"].eq("TARGET_BUILT").sum())
    no_target = int(out["target_status_v5_1"].eq("NO_TARGET").sum())
    old_target_built = old_v5_target_built_rows()
    delta_old = target_built - old_target_built if isinstance(old_target_built, int) else ""

    audit_rows: list[dict[str, object]] = [
        audit_row("overall", "rating_rows_loaded", len(ratings)),
        audit_row("overall", "race_target_rows", len(out)),
        audit_row("overall", "target_built_rows", target_built),
        audit_row("overall", "no_target_rows", no_target),
        audit_row("overall", "old_v5_target_built_rows", old_target_built),
        audit_row("overall", "target_built_delta_vs_old_v5", delta_old),
        audit_row("overall", "high_confidence_targets", int(out["target_confidence_v5_1"].eq("HIGH").sum())),
        audit_row("overall", "medium_confidence_targets", int(out["target_confidence_v5_1"].eq("MEDIUM").sum())),
        audit_row("overall", "low_confidence_targets", int(out["target_confidence_v5_1"].eq("LOW").sum())),
        audit_row("overall", "no_target_confidence_rows", int(out["target_confidence_v5_1"].eq("NO_TARGET").sum())),
    ]

    for status, count in out["target_status_v5_1"].value_counts().sort_index().items():
        audit_rows.append(audit_row("target_status_counts", status, count=count))

    for confidence, count in out["target_confidence_v5_1"].value_counts().sort_index().items():
        audit_rows.append(audit_row("target_confidence_counts", confidence, count=count))

    built_targets = out[out["target_status_v5_1"].eq("TARGET_BUILT")].copy()
    for race_class in KEY_CLASSES:
        samples = built_targets[built_targets["race_class_clean_v5_1"].map(norm).eq(race_class)].copy()
        if samples.empty:
            audit_rows.append(audit_row("target_samples", "sample_target", race_class=race_class, notes="no target sample"))
            continue

        samples = samples.sort_values("race_target_rating_v5_1", ascending=False)
        sample = samples.iloc[0]
        audit_rows.append(
            audit_row(
                "target_samples",
                "sample_target",
                value=sample["race_target_rating_v5_1"],
                race_class=race_class,
                count=len(samples),
                notes=(
                    f"track={sample['track']}; date={sample['race_date']}; dist={sample['distance']}; "
                    f"condition={sample['condition_group_v5_1']}; confidence={sample['target_confidence_v5_1']}; "
                    f"class={sample['class_par_rating_v5_2']}; distance={sample['distance_par_rating_v5_1']}; "
                    f"condition_par={sample['condition_par_rating_v5_1']}"
                ),
            )
        )

    audit = pd.DataFrame(audit_rows)
    audit.to_csv(AUDIT, index=False)

    print(f"wrote: {OUT}")
    print(f"wrote: {AUDIT}")
    print()
    print(audit[audit["section"].isin(["overall", "target_samples"])].to_string(index=False))
    print("=" * 90)


if __name__ == "__main__":
    main()
