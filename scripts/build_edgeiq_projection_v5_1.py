from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RATINGS = DATA / "edgeiq_historical_performance_rating_v5_1.csv"
TARGETS = DATA / "edgeiq_race_rating_targets_v5_1.csv"

OUT = DATA / "edgeiq_projection_v5_1.csv"
AUDIT = DATA / "edgeiq_projection_v5_1_audit.csv"

MATERIAL_WINNER_GAP_DELTA = 8.0

KEY_CLASSES = [
    "GROUP 1",
    "GROUP 2",
    "GROUP 3",
    "LISTED",
    "BM84",
    "BM70",
    "BM64",
    "BM58",
    "CLASS 1",
    "MAIDEN",
]

CLASS_FAMILIES = [
    "BLACKTYPE",
    "BENCHMARK",
    "CLASS",
    "MAIDEN",
    "OPEN_SET_WEIGHTS",
    "REGIONAL_RESTRICTED",
    "JUMPS_OR_HIGHWEIGHT",
]

JOIN_KEYS = [
    "race_date",
    "track",
    "distance",
    "race_class_clean_v5_1",
    "condition_group_v5_1",
    "real_field_size",
    "source_file",
]


def norm(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).upper().strip().split())


def fmt(value: object) -> str:
    if pd.isna(value):
        return ""
    return f"{float(value):.2f}"


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


def projection_band(gap: object) -> str:
    value = pd.to_numeric(gap, errors="coerce")
    if pd.isna(value):
        return "NO_TARGET"
    if value >= 8.0:
        return "ELITE"
    if value >= 4.0:
        return "STRONG"
    if value >= 1.0:
        return "POSITIVE"
    if value > -1.0:
        return "NEUTRAL"
    if value > -4.0:
        return "NEGATIVE"
    return "POOR"


def projection_confidence(row: pd.Series) -> str:
    stack = [
        norm(row.get("race_class_confidence_v3_3", "")),
        norm(row.get("class_par_confidence_v5_2", "")),
        norm(row.get("distance_par_confidence_v5_1", "")),
        norm(row.get("condition_par_confidence_v5_1", "")),
        norm(row.get("target_confidence_v5_1", "")),
    ]

    if norm(row.get("projection_status_v5_1", "")) != "PROJECTED":
        return "LOW"
    if any(value in {"", "MISSING", "NO_TARGET", "VERY_LOW", "LOW", "UNRESOLVED", "EXCLUDED"} for value in stack):
        return "LOW"
    if any(value == "MEDIUM" for value in stack):
        return "MEDIUM"
    return "HIGH"


def projection_confidence_reason(row: pd.Series) -> str:
    parts = {
        "race_class_confidence_v3_3": norm(row.get("race_class_confidence_v3_3", "")),
        "class_par_confidence_v5_2": norm(row.get("class_par_confidence_v5_2", "")),
        "distance_par_confidence_v5_1": norm(row.get("distance_par_confidence_v5_1", "")),
        "condition_par_confidence_v5_1": norm(row.get("condition_par_confidence_v5_1", "")),
        "target_confidence_v5_1": norm(row.get("target_confidence_v5_1", "")),
    }
    if norm(row.get("projection_status_v5_1", "")) != "PROJECTED":
        return "no race target joined"
    weak = [f"{key}={value or 'MISSING'}" for key, value in parts.items() if value in {"", "MISSING", "NO_TARGET", "VERY_LOW", "LOW", "UNRESOLVED", "EXCLUDED"}]
    medium = [f"{key}=MEDIUM" for key, value in parts.items() if value == "MEDIUM"]
    if weak:
        return "; ".join(weak)
    if medium:
        return "; ".join(medium)
    return "all confidence inputs HIGH"


def audit_row(
    section: str,
    metric: str,
    value: object = "",
    count: object = "",
    rank: object = "",
    horse: str = "",
    race_class: str = "",
    class_family: str = "",
    projection_band_value: str = "",
    projection_confidence_value: str = "",
    race_date: str = "",
    track: str = "",
    distance: object = "",
    finish_position: object = "",
    average_gap: object = "",
    median_gap: object = "",
    winner_average_gap: object = "",
    field_average_gap: object = "",
    winner_field_gap_delta: object = "",
    notes: str = "",
) -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "rank": rank,
        "horse": horse,
        "race_class": race_class,
        "class_family": class_family,
        "projection_band": projection_band_value,
        "projection_confidence": projection_confidence_value,
        "race_date": race_date,
        "track": track,
        "distance": distance,
        "finish_position": finish_position,
        "value": value,
        "count": count,
        "average_gap": average_gap,
        "median_gap": median_gap,
        "winner_average_gap": winner_average_gap,
        "field_average_gap": field_average_gap,
        "winner_field_gap_delta": winner_field_gap_delta,
        "notes": notes,
    }


def mean_value(series: pd.Series) -> str:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return ""
    return fmt(values.mean())


def median_value(series: pd.Series) -> str:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return ""
    return fmt(values.median())


def main() -> None:
    print("=" * 90)
    print("EDGEIQ PROJECTION V5.1")
    print("=" * 90)

    for path in [RATINGS, TARGETS]:
        if not path.exists():
            raise FileNotFoundError(f"Missing input: {path}")

    ratings = pd.read_csv(RATINGS, dtype=str, keep_default_na=False, low_memory=False)
    targets = pd.read_csv(TARGETS, dtype=str, keep_default_na=False, low_memory=False)

    required_rating = {
        "horse",
        "race_date",
        "track",
        "distance",
        "real_field_size",
        "source_file",
        "finish_position",
        "performance_rating_v5_1",
        "race_class_clean_v3_3",
        "race_class_family_v3_3",
        "race_class_confidence_v3_3",
        "condition_recovered",
    }
    required_target = {
        *JOIN_KEYS,
        "race_target_rating_v5_1",
        "target_status_v5_1",
        "target_confidence_v5_1",
        "class_par_confidence_v5_2",
        "distance_par_confidence_v5_1",
        "condition_par_confidence_v5_1",
    }

    missing_rating = sorted(required_rating.difference(ratings.columns))
    missing_target = sorted(required_target.difference(targets.columns))
    if missing_rating:
        raise ValueError(f"Missing rating columns: {missing_rating}")
    if missing_target:
        raise ValueError(f"Missing target columns: {missing_target}")

    ratings["distance"] = pd.to_numeric(ratings["distance"], errors="coerce").round(2)
    ratings["real_field_size"] = pd.to_numeric(ratings["real_field_size"], errors="coerce").round(2)
    ratings["finish_position"] = pd.to_numeric(ratings["finish_position"], errors="coerce")
    ratings["performance_rating_v5_1"] = pd.to_numeric(ratings["performance_rating_v5_1"], errors="coerce")
    ratings["race_class_clean_v5_1"] = ratings["race_class_clean_v3_3"].map(norm)
    ratings["distance_band_v5_1"] = ratings["distance"].apply(distance_band)
    ratings["condition_group_v5_1"] = condition_group(ratings)

    targets["distance"] = pd.to_numeric(targets["distance"], errors="coerce").round(2)
    targets["real_field_size"] = pd.to_numeric(targets["real_field_size"], errors="coerce").round(2)
    targets["race_class_clean_v5_1"] = targets["race_class_clean_v5_1"].map(norm)
    targets["race_target_rating_v5_1"] = pd.to_numeric(targets["race_target_rating_v5_1"], errors="coerce")

    target_keep = targets[
        [
            *JOIN_KEYS,
            "race_target_rating_v5_1",
            "target_status_v5_1",
            "target_confidence_v5_1",
            "class_par_rating_v5_2",
            "distance_par_rating_v5_1",
            "condition_par_rating_v5_1",
            "class_par_confidence_v5_2",
            "distance_par_confidence_v5_1",
            "condition_par_confidence_v5_1",
            "class_par_method_v5_2",
            "distance_par_method_v5_1",
            "condition_par_method_v5_1",
        ]
    ].drop_duplicates(JOIN_KEYS, keep="first")

    df = ratings.merge(target_keep, on=JOIN_KEYS, how="left")
    df["projection_status_v5_1"] = df["race_target_rating_v5_1"].apply(lambda value: "PROJECTED" if pd.notna(value) else "NO_TARGET")
    df["projection_gap_v5_1"] = df["performance_rating_v5_1"] - df["race_target_rating_v5_1"]
    df["projection_band_v5_1"] = df["projection_gap_v5_1"].apply(projection_band)
    df["projection_confidence_v5_1"] = df.apply(projection_confidence, axis=1)
    df["projection_confidence_reason_v5_1"] = df.apply(projection_confidence_reason, axis=1)
    df["built_at_v5_1"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    output_columns = [
        "horse",
        "race_date",
        "track",
        "distance",
        "distance_band_v5_1",
        "race_class_clean_v5_1",
        "race_class_family_v3_3",
        "race_class_confidence_v3_3",
        "condition_group_v5_1",
        "real_field_size",
        "source_file",
        "finish_position",
        "performance_rating_v5_1",
        "race_target_rating_v5_1",
        "projection_gap_v5_1",
        "projection_band_v5_1",
        "projection_confidence_v5_1",
        "projection_confidence_reason_v5_1",
        "projection_status_v5_1",
        "target_status_v5_1",
        "target_confidence_v5_1",
        "class_par_rating_v5_2",
        "distance_par_rating_v5_1",
        "condition_par_rating_v5_1",
        "class_par_confidence_v5_2",
        "distance_par_confidence_v5_1",
        "condition_par_confidence_v5_1",
        "class_par_method_v5_2",
        "distance_par_method_v5_1",
        "condition_par_method_v5_1",
        "rating_v5_1_status",
        "built_at_v5_1",
    ]
    output_columns = [column for column in output_columns if column in df.columns]

    projected = df[df["projection_status_v5_1"].eq("PROJECTED")].copy()
    projected["projection_gap_v5_1"] = pd.to_numeric(projected["projection_gap_v5_1"], errors="coerce")

    df.to_csv(OUT, index=False, columns=output_columns)

    audit_rows: list[dict[str, object]] = [
        audit_row("overall", "rows_loaded", len(ratings)),
        audit_row("overall", "rows_written", len(df)),
        audit_row("overall", "projected_rows", len(projected)),
        audit_row("overall", "no_target_rows", int(df["projection_status_v5_1"].eq("NO_TARGET").sum())),
        audit_row("gap_summary", "average_gap", average_gap=mean_value(projected["projection_gap_v5_1"])),
        audit_row("gap_summary", "median_gap", median_gap=median_value(projected["projection_gap_v5_1"])),
    ]

    for band, count in df["projection_band_v5_1"].value_counts().sort_index().items():
        audit_rows.append(audit_row("projection_band_counts", band, count=int(count), projection_band_value=band))

    for confidence, count in df["projection_confidence_v5_1"].value_counts().sort_index().items():
        audit_rows.append(audit_row("projection_confidence_counts", confidence, count=int(count), projection_confidence_value=confidence))

    for family in CLASS_FAMILIES:
        family_rows = projected[projected["race_class_family_v3_3"].map(norm).eq(family)]
        winners = family_rows[family_rows["finish_position"].eq(1)]
        audit_rows.append(
            audit_row(
                "projection_by_class_family",
                "family_gap_summary",
                class_family=family,
                count=len(family_rows),
                average_gap=mean_value(family_rows["projection_gap_v5_1"]),
                median_gap=median_value(family_rows["projection_gap_v5_1"]),
                winner_average_gap=mean_value(winners["projection_gap_v5_1"]),
                notes=f"winner_count={len(winners)}",
            )
        )

    top_positive = projected.sort_values("projection_gap_v5_1", ascending=False).head(50)
    for rank, row in enumerate(top_positive.itertuples(index=False), start=1):
        audit_rows.append(
            audit_row(
                "top_50_positive_projections",
                "projection_gap",
                rank=rank,
                horse=str(row.horse),
                race_class=str(row.race_class_clean_v5_1),
                class_family=str(row.race_class_family_v3_3),
                projection_band_value=str(row.projection_band_v5_1),
                projection_confidence_value=str(row.projection_confidence_v5_1),
                race_date=str(row.race_date),
                track=str(row.track),
                distance=row.distance,
                finish_position=row.finish_position,
                value=fmt(row.projection_gap_v5_1),
                notes=f"rating={fmt(row.performance_rating_v5_1)}; target={fmt(row.race_target_rating_v5_1)}",
            )
        )

    top_negative = projected.sort_values("projection_gap_v5_1", ascending=True).head(50)
    for rank, row in enumerate(top_negative.itertuples(index=False), start=1):
        audit_rows.append(
            audit_row(
                "top_50_negative_projections",
                "projection_gap",
                rank=rank,
                horse=str(row.horse),
                race_class=str(row.race_class_clean_v5_1),
                class_family=str(row.race_class_family_v3_3),
                projection_band_value=str(row.projection_band_v5_1),
                projection_confidence_value=str(row.projection_confidence_v5_1),
                race_date=str(row.race_date),
                track=str(row.track),
                distance=row.distance,
                finish_position=row.finish_position,
                value=fmt(row.projection_gap_v5_1),
                notes=f"rating={fmt(row.performance_rating_v5_1)}; target={fmt(row.race_target_rating_v5_1)}",
            )
        )

    validation_failures: list[str] = []
    for race_class in KEY_CLASSES:
        class_rows = projected[projected["race_class_clean_v5_1"].map(norm).eq(race_class)]
        winners = class_rows[class_rows["finish_position"].eq(1)]
        winner_avg = pd.to_numeric(winners["projection_gap_v5_1"], errors="coerce").mean()
        field_avg = pd.to_numeric(class_rows["projection_gap_v5_1"], errors="coerce").mean()
        delta = winner_avg - field_avg if pd.notna(winner_avg) and pd.notna(field_avg) else pd.NA
        status = "PASS" if pd.notna(delta) and float(delta) >= MATERIAL_WINNER_GAP_DELTA else "REVIEW"
        if status != "PASS":
            validation_failures.append(race_class)
        audit_rows.append(
            audit_row(
                "winner_vs_field_validation",
                status,
                race_class=race_class,
                count=len(class_rows),
                winner_average_gap=fmt(winner_avg),
                field_average_gap=fmt(field_avg),
                winner_field_gap_delta=fmt(delta),
                notes=f"winner_count={len(winners)}; material_delta_required={MATERIAL_WINNER_GAP_DELTA}",
            )
        )

    audit_rows.append(
        audit_row(
            "critical_validation",
            "winner_gaps_materially_higher_than_field",
            value="PASS" if not validation_failures else "REVIEW",
            notes="; ".join(validation_failures),
        )
    )

    audit = pd.DataFrame(audit_rows)
    audit.to_csv(AUDIT, index=False)

    print(f"wrote: {OUT}")
    print(f"wrote: {AUDIT}")
    print()
    print(audit[audit["section"].isin(["overall", "gap_summary", "projection_band_counts", "projection_confidence_counts", "winner_vs_field_validation", "critical_validation"])].to_string(index=False))
    print("=" * 90)


if __name__ == "__main__":
    main()
