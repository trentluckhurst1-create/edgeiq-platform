from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_projection_v5_1.csv"
AUDIT = DATA / "edgeiq_race_context_grouping_audit_v5_1.csv"
RUNNER_REVIEW = DATA / "edgeiq_race_context_grouping_runner_review_v5_1.csv"
SUMMARY = DATA / "edgeiq_race_context_grouping_summary_v5_1.csv"

SOURCE_FILES = [
    "run_context.csv",
    "run_context_FIXED.csv",
    "horse_runs_ra.csv",
    "ra_horse_runs.csv",
]

GROUPINGS = {
    "A_CURRENT_FULL_CONTEXT": [
        "race_date_key",
        "track_key",
        "distance_key",
        "race_class_key",
        "condition_key",
        "field_size_key",
        "source_file_key",
    ],
    "B_DATE_TRACK_DISTANCE_SOURCE": [
        "race_date_key",
        "track_key",
        "distance_key",
        "source_file_key",
    ],
    "C_DATE_TRACK_DISTANCE_ROUND_25_SOURCE": [
        "race_date_key",
        "track_key",
        "distance_round_25_key",
        "source_file_key",
    ],
    "D_DATE_TRACK_DISTANCE_ROUND_50_SOURCE": [
        "race_date_key",
        "track_key",
        "distance_round_50_key",
        "source_file_key",
    ],
    "F_DATE_TRACK_DISTANCE_BAND_SOURCE": [
        "race_date_key",
        "track_key",
        "distance_band_key",
        "source_file_key",
    ],
}


def raw_text_key(value: object) -> str:
    if pd.isna(value):
        return "[blank]"
    text = str(value).strip()
    return text if text else "[blank]"


def number_key(value: object) -> str:
    numeric = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric):
        return "[blank]"
    return str(round(float(numeric), 2))


def nearest_key(value: object, base: int) -> str:
    numeric = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric):
        return "[blank]"
    rounded = int(np.floor((float(numeric) + (base / 2.0)) / base) * base)
    return str(float(rounded))


def make_context_key(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    key = df[cols[0]].astype(str)
    for col in cols[1:]:
        key = key + "|" + df[col].astype(str)
    return key


def distribution_stats(counts: pd.Series) -> dict[str, object]:
    if counts.empty:
        return {
            "race_contexts": 0,
            "single_runner_contexts": 0,
            "multi_runner_contexts": 0,
            "average_runner_count": "",
            "median_runner_count": "",
            "max_runner_count": "",
            "contexts_2_4": 0,
            "contexts_5_8": 0,
            "contexts_9_16": 0,
            "contexts_17_plus": 0,
        }

    return {
        "race_contexts": int(len(counts)),
        "single_runner_contexts": int(counts.eq(1).sum()),
        "multi_runner_contexts": int(counts.gt(1).sum()),
        "average_runner_count": round(float(counts.mean()), 2),
        "median_runner_count": round(float(counts.median()), 2),
        "max_runner_count": int(counts.max()),
        "contexts_2_4": int(counts.between(2, 4).sum()),
        "contexts_5_8": int(counts.between(5, 8).sum()),
        "contexts_9_16": int(counts.between(9, 16).sum()),
        "contexts_17_plus": int(counts.ge(17).sum()),
    }


def append_metric(rows: list[dict[str, object]], section: str, metric: str, value: object, grouping: str = "", source_file: str = "", notes: str = "") -> None:
    rows.append(
        {
            "section": section,
            "grouping_candidate": grouping,
            "source_file": source_file,
            "metric": metric,
            "value": value,
            "notes": notes,
        }
    )


def context_summary(df: pd.DataFrame, grouping: str, key_col: str, key_fields: list[str]) -> pd.DataFrame:
    agg = (
        df.groupby(key_col, dropna=False)
        .agg(
            runner_count=("horse", "size"),
            race_date=("race_date", "first"),
            track=("track", "first"),
            distance_min=("distance_num", "min"),
            distance_max=("distance_num", "max"),
            distance_band=("distance_band_v5_1", "first"),
            race_class=("race_class_clean_v5_1", "first"),
            condition=("condition_group_v5_1", "first"),
            real_field_size=("real_field_size_num", "first"),
            source_file=("source_file", "first"),
            sample_horses=("horse", lambda s: " | ".join(s.astype(str).head(8))),
            winner_count=("finish_position_num", lambda s: int((s == 1).sum())),
        )
        .reset_index()
        .rename(columns={key_col: "context_key"})
    )
    agg["grouping_candidate"] = grouping
    agg["key_fields"] = " + ".join(key_fields)
    return agg


def runner_review_rows(df: pd.DataFrame, grouping: str, key_col: str, contexts: pd.DataFrame, review_type: str, limit: int) -> pd.DataFrame:
    selected = contexts.head(limit)[["context_key", "runner_count"]].copy()
    rows = df[df[key_col].isin(selected["context_key"])].copy()
    rows = rows.merge(selected, left_on=key_col, right_on="context_key", how="left", suffixes=("", "_context"))
    rows["grouping_candidate"] = grouping
    rows["review_type"] = review_type
    rows["context_key"] = rows[key_col]
    return rows


def main() -> None:
    print("=" * 90)
    print("EDGEIQ RACE CONTEXT GROUPING AUDIT V5.1")
    print("=" * 90)

    if not SRC.exists():
        raise FileNotFoundError(f"Missing input: {SRC}")

    df = pd.read_csv(SRC, dtype=str, keep_default_na=False, low_memory=False)
    required = {
        "horse",
        "race_date",
        "track",
        "distance",
        "distance_band_v5_1",
        "race_class_clean_v5_1",
        "condition_group_v5_1",
        "real_field_size",
        "source_file",
        "finish_position",
        "projection_status_v5_1",
        "projection_gap_v5_1",
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing required projection columns: {missing}")

    rows_loaded = len(df)
    projected = df[df["projection_status_v5_1"].eq("PROJECTED")].copy()
    projected["projection_gap_num"] = pd.to_numeric(projected["projection_gap_v5_1"], errors="coerce")
    projected = projected[projected["projection_gap_num"].notna()].copy()

    projected["distance_num"] = pd.to_numeric(projected["distance"], errors="coerce")
    projected["real_field_size_num"] = pd.to_numeric(projected["real_field_size"], errors="coerce")
    projected["finish_position_num"] = pd.to_numeric(projected["finish_position"], errors="coerce")

    projected["race_date_key"] = projected["race_date"].map(raw_text_key)
    projected["track_key"] = projected["track"].map(raw_text_key)
    projected["distance_key"] = projected["distance"].map(number_key)
    projected["distance_round_25_key"] = projected["distance"].map(lambda value: nearest_key(value, 25))
    projected["distance_round_50_key"] = projected["distance"].map(lambda value: nearest_key(value, 50))
    projected["distance_band_key"] = projected["distance_band_v5_1"].map(raw_text_key)
    projected["race_class_key"] = projected["race_class_clean_v5_1"].map(raw_text_key)
    projected["condition_key"] = projected["condition_group_v5_1"].map(raw_text_key)
    projected["field_size_key"] = projected["real_field_size"].map(number_key)
    projected["source_file_key"] = projected["source_file"].map(raw_text_key)

    has_race_name = "race_name" in projected.columns and projected["race_name"].astype(str).str.strip().ne("").any()
    if has_race_name:
        projected["race_name_key"] = projected["race_name"].map(raw_text_key)

    audit_rows: list[dict[str, object]] = []
    append_metric(audit_rows, "overall", "rows_loaded", rows_loaded)
    append_metric(audit_rows, "overall", "projected_rows_used", len(projected))
    append_metric(audit_rows, "overall", "no_target_rows_excluded", rows_loaded - len(projected))
    append_metric(audit_rows, "overall", "race_name_available_for_candidate_E", "TRUE" if has_race_name else "FALSE")

    summary_frames: list[pd.DataFrame] = []
    runner_review_frames: list[pd.DataFrame] = []

    grouping_specs = dict(GROUPINGS)
    if has_race_name:
        grouping_specs["E_DATE_TRACK_RACE_NAME_SOURCE"] = [
            "race_date_key",
            "track_key",
            "race_name_key",
            "source_file_key",
        ]
    else:
        append_metric(
            audit_rows,
            "grouping_unavailable",
            "candidate_E_unavailable",
            "UNAVAILABLE_MISSING_RACE_NAME",
            grouping="E_DATE_TRACK_RACE_NAME_SOURCE",
            notes="edgeiq_projection_v5_1.csv does not contain race_name",
        )

    for grouping, fields in grouping_specs.items():
        key_col = f"context_key_{grouping}"
        projected[key_col] = make_context_key(projected, fields)

        counts = projected.groupby(key_col, dropna=False).size()
        stats = distribution_stats(counts)
        for metric, value in stats.items():
            append_metric(audit_rows, "grouping_summary", metric, value, grouping=grouping, notes="all projected rows")

        contexts = context_summary(projected, grouping, key_col, fields)
        summary_frames.append(contexts)

        single_contexts = contexts[contexts["runner_count"].eq(1)].sort_values(
            ["race_date", "track", "distance_min", "race_class", "source_file", "context_key"]
        )
        largest_contexts = contexts.sort_values(
            ["runner_count", "race_date", "track", "distance_min"],
            ascending=[False, True, True, True],
        )

        if grouping == "A_CURRENT_FULL_CONTEXT":
            runner_review_frames.append(
                runner_review_rows(projected, grouping, key_col, single_contexts, "top_100_single_runner_contexts_current_grouping", 100)
            )

        runner_review_frames.append(
            runner_review_rows(projected, grouping, key_col, largest_contexts, "top_100_largest_contexts", 100)
        )

        for source_file in SOURCE_FILES:
            source_counts = projected[projected["source_file"].eq(source_file)].groupby(key_col, dropna=False).size()
            source_stats = distribution_stats(source_counts)
            for metric, value in source_stats.items():
                append_metric(
                    audit_rows,
                    "source_file_grouping_summary",
                    metric,
                    value,
                    grouping=grouping,
                    source_file=source_file,
                    notes="projected rows for source_file",
                )

    split_base = [
        "race_date_key",
        "track_key",
        "source_file_key",
    ]
    split = (
        projected.groupby(split_base, dropna=False)
        .agg(
            runner_rows=("horse", "size"),
            exact_distance_count=("distance_key", "nunique"),
            rounded_25_distance_count=("distance_round_25_key", "nunique"),
            rounded_50_distance_count=("distance_round_50_key", "nunique"),
            distance_band_count=("distance_band_key", "nunique"),
            single_runner_current_contexts=("context_key_A_CURRENT_FULL_CONTEXT", lambda s: int(s.value_counts().eq(1).sum())),
            total_current_contexts=("context_key_A_CURRENT_FULL_CONTEXT", "nunique"),
            min_distance=("distance_num", "min"),
            max_distance=("distance_num", "max"),
            sample_distances=("distance_key", lambda s: " | ".join(sorted(set(s.astype(str)))[:12])),
            sample_horses=("horse", lambda s: " | ".join(s.astype(str).head(12))),
        )
        .reset_index()
    )
    split["distance_span"] = split["max_distance"] - split["min_distance"]
    split_examples = split[
        (split["runner_rows"] >= 3)
        & (split["exact_distance_count"] >= 2)
        & (split["single_runner_current_contexts"] >= 2)
        & (split["distance_span"] <= 150)
    ].sort_values(
        ["single_runner_current_contexts", "exact_distance_count", "runner_rows"],
        ascending=[False, False, False],
    ).head(100)

    for _, row in split_examples.iterrows():
        append_metric(
            audit_rows,
            "potential_duplicate_split_examples",
            "nearby_distance_split",
            row["single_runner_current_contexts"],
            source_file=row["source_file_key"],
            notes=(
                f"date={row['race_date_key']}; track={row['track_key']}; rows={row['runner_rows']}; "
                f"current_contexts={row['total_current_contexts']}; distances={row['sample_distances']}; "
                f"span={row['distance_span']}; horses={row['sample_horses']}"
            ),
        )

    summary = pd.concat(summary_frames, ignore_index=True) if summary_frames else pd.DataFrame()
    review = pd.concat(runner_review_frames, ignore_index=True) if runner_review_frames else pd.DataFrame()

    review_cols = [
        "review_type",
        "grouping_candidate",
        "context_key",
        "runner_count",
        "horse",
        "race_date",
        "track",
        "distance",
        "distance_band_v5_1",
        "race_class_clean_v5_1",
        "condition_group_v5_1",
        "real_field_size",
        "source_file",
        "finish_position",
        "performance_rating_v5_1",
        "race_target_rating_v5_1",
        "projection_gap_v5_1",
        "projection_band_v5_1",
        "projection_confidence_v5_1",
    ]
    review_cols = [col for col in review_cols if col in review.columns]

    audit = pd.DataFrame(audit_rows)
    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    audit["built_at"] = built_at
    summary["built_at"] = built_at
    review["built_at"] = built_at

    audit.to_csv(AUDIT, index=False)
    summary.to_csv(SUMMARY, index=False)
    review.to_csv(RUNNER_REVIEW, index=False, columns=review_cols)

    print(f"wrote: {AUDIT}")
    print(f"wrote: {RUNNER_REVIEW}")
    print(f"wrote: {SUMMARY}")
    print()
    print(audit[audit["section"].isin(["overall", "grouping_unavailable", "grouping_summary"])].to_string(index=False))
    print("=" * 90)


if __name__ == "__main__":
    main()
