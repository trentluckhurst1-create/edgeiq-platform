from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RATING = DATA / "edgeiq_historical_performance_rating_v3.csv"
CLEAN = DATA / "edgeiq_historical_class_clean_v3.csv"
V3_1 = DATA / "edgeiq_historical_performance_rating_v3_1.csv"

OUTPUT = DATA / "edgeiq_historical_performance_rating_v3_3.csv"
AUDIT = DATA / "edgeiq_historical_performance_rating_v3_3_audit.csv"

EXACT_KEYS = ["_horse_key", "_track_key", "_race_date_key", "_distance_key"]
FALLBACK_KEYS = ["_horse_key", "_track_key", "_distance_key"]

CLASS_FIELDS = [
    "race_class_model_v3",
    "class_model_family_v3",
    "class_model_confidence_v3",
    "is_class_usable_v3",
    "is_excluded_from_class_model_v3",
    "class_recovery_status",
    "class_recovery_reason",
    "race_type_recovered",
    "age_restriction_recovered",
    "sex_restriction_recovered",
    "condition_token_recovered",
    "race_name",
    "race_class_raw",
    "race_class_recovered",
    "cup_name_detected_v3",
    "race_name_recovery_applied_v3",
    "race_name_recovery_reason_v3",
]


def norm_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).upper().strip()
    return re.sub(r"\s+", " ", text)


def date_key(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()[:10]


def distance_key(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return ""
    return str(int(round(float(number))))


def boolish(value: object) -> bool:
    return str(value).strip().upper() in {"TRUE", "1", "YES", "Y"}


def valid_class(value: object) -> bool:
    cls = norm_text(value)
    return cls not in {"", "UNKNOWN", "TRIAL_OR_JUMPOUT", "HANDICAP_UNRESOLVED"}


def add_join_keys(df: pd.DataFrame) -> pd.DataFrame:
    keyed = df.copy()
    keyed["_horse_key"] = keyed["horse"].map(norm_text)
    keyed["_track_key"] = keyed["track"].map(norm_text)
    keyed["_race_date_key"] = keyed["race_date"].map(date_key)
    keyed["_distance_key"] = keyed["distance"].map(distance_key)
    return keyed


def best_clean_frame(clean: pd.DataFrame, keys: list[str], suffix: str) -> pd.DataFrame:
    stats = (
        clean.groupby(keys, dropna=False)
        .agg(
            clean_class_match_count=("race_class_model_v3", "size"),
            clean_class_distinct_class_count=("race_class_model_v3", lambda s: int(s.map(norm_text).nunique())),
        )
        .reset_index()
    )

    ranked = clean.copy()
    ranked["_class_valid_rank"] = ranked["race_class_model_v3"].map(valid_class).astype(int)
    ranked["_usable_rank"] = ranked["is_class_usable_v3"].map(boolish).astype(int)
    ranked["_confidence_rank"] = ranked["class_model_confidence_v3"].map(
        {
            "HIGH": 0,
            "MEDIUM": 1,
            "LOW": 2,
            "UNRESOLVED": 3,
            "EXCLUDED": 4,
        }
    ).fillna(9)
    ranked["_class_sort"] = ranked["race_class_model_v3"].map(norm_text)

    ranked = ranked.sort_values(
        keys + ["_class_valid_rank", "_usable_rank", "_confidence_rank", "_class_sort"],
        ascending=[True] * len(keys) + [False, False, True, True],
    )

    keep = ranked.drop_duplicates(keys, keep="first")[keys + CLASS_FIELDS].copy()
    keep = keep.merge(stats, on=keys, how="left")

    renamed = {}
    for column in CLASS_FIELDS + ["clean_class_match_count", "clean_class_distinct_class_count"]:
        renamed[column] = f"{column}_{suffix}"
    return keep.rename(columns=renamed)


def first_available(merged: pd.DataFrame, column: str) -> pd.Series:
    exact = merged[f"{column}_exact"]
    fallback = merged[f"{column}_fallback"]
    return exact.where(exact.notna() & exact.astype(str).str.strip().ne(""), fallback)


def metric_row(
    section: str,
    metric: str,
    value: object = "",
    v3_1_value: object = "",
    v3_3_value: object = "",
    delta: object = "",
    source_file: str = "",
    rows: object = "",
    joined: object = "",
    not_joined: object = "",
    join_rate_pct: object = "",
    notes: str = "",
) -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "source_file": source_file,
        "value": value,
        "v3_1_value": v3_1_value,
        "v3_3_value": v3_3_value,
        "delta": delta,
        "rows": rows,
        "joined": joined,
        "not_joined": not_joined,
        "join_rate_pct": join_rate_pct,
        "notes": notes,
    }


def joined_mask(df: pd.DataFrame, status_column: str) -> pd.Series:
    return df[status_column].astype(str).str.upper().ne("NOT_JOINED")


def pct(part: int, total: int) -> str:
    if not total:
        return ""
    return f"{(part / total) * 100:.2f}"


def source_stats_v3_1(v3_1: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if v3_1.empty or "source_file" not in v3_1.columns or "clean_class_join_status" not in v3_1.columns:
        return pd.DataFrame(columns=["source_file", "rows", "joined", "not_joined", "join_rate_pct"])

    for source_file, group in v3_1.groupby("source_file", dropna=False):
        total = len(group)
        joined = int(group["clean_class_join_status"].astype(str).str.upper().eq("JOINED").sum())
        rows.append(
            {
                "source_file": source_file,
                "rows": total,
                "joined": joined,
                "not_joined": total - joined,
                "join_rate_pct": pct(joined, total),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    print("=" * 90)
    print("EDGEIQ HISTORICAL PERFORMANCE RATING V3.3 - CLEAN CLASS V3 JOIN")
    print("=" * 90)

    if not RATING.exists():
        raise FileNotFoundError(f"Missing input: {RATING}")
    if not CLEAN.exists():
        raise FileNotFoundError(f"Missing input: {CLEAN}")

    rating = pd.read_csv(RATING, dtype=str, keep_default_na=False, low_memory=False)
    clean = pd.read_csv(CLEAN, dtype=str, keep_default_na=False, low_memory=False)

    required_rating = {"horse", "race_date", "track", "distance", "source_file"}
    required_clean = {"horse", "race_date", "track", "distance", *CLASS_FIELDS}
    missing_rating = sorted(required_rating.difference(rating.columns))
    missing_clean = sorted(required_clean.difference(clean.columns))
    if missing_rating:
        raise ValueError(f"Missing rating columns: {missing_rating}")
    if missing_clean:
        raise ValueError(f"Missing class-clean columns: {missing_clean}")

    rating_keyed = add_join_keys(rating)
    clean_keyed = add_join_keys(clean)

    exact = best_clean_frame(clean_keyed, EXACT_KEYS, "exact")
    fallback = best_clean_frame(clean_keyed, FALLBACK_KEYS, "fallback")

    merged = rating_keyed.merge(exact, on=EXACT_KEYS, how="left")
    merged = merged.merge(fallback, on=FALLBACK_KEYS, how="left")

    has_exact = merged["race_class_model_v3_exact"].notna() & merged["race_class_model_v3_exact"].astype(str).str.strip().ne("")
    has_fallback = merged["race_class_model_v3_fallback"].notna() & merged["race_class_model_v3_fallback"].astype(str).str.strip().ne("")

    merged["clean_class_join_status_v3_3"] = np.select(
        [has_exact, has_fallback],
        ["JOINED_EXACT_HORSE_DATE_TRACK_DISTANCE", "JOINED_FALLBACK_HORSE_TRACK_DISTANCE"],
        default="NOT_JOINED",
    )
    merged["clean_class_join_key_v3_3"] = np.select(
        [has_exact, has_fallback],
        ["horse|race_date|track|distance", "horse|track|distance"],
        default="",
    )

    for column in CLASS_FIELDS:
        merged[column] = first_available(merged, column)

    merged["clean_class_match_count_v3_3"] = merged["clean_class_match_count_exact"].where(
        has_exact, merged["clean_class_match_count_fallback"]
    )
    merged["clean_class_distinct_class_count_v3_3"] = merged["clean_class_distinct_class_count_exact"].where(
        has_exact, merged["clean_class_distinct_class_count_fallback"]
    )
    merged["clean_class_ambiguous_match_v3_3"] = np.where(
        pd.to_numeric(merged["clean_class_distinct_class_count_v3_3"], errors="coerce").fillna(0) > 1,
        "TRUE",
        "FALSE",
    )

    merged["race_class_clean_v3_3"] = merged["race_class_model_v3"]
    merged["race_class_family_v3_3"] = merged["class_model_family_v3"]
    merged["race_class_confidence_v3_3"] = merged["class_model_confidence_v3"]
    merged["built_at_v3_3"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    drop_columns = [
        column
        for column in merged.columns
        if column.startswith("_")
        or column.endswith("_exact")
        or column.endswith("_fallback")
    ]
    merged = merged.drop(columns=drop_columns)
    merged.to_csv(OUTPUT, index=False)

    joined_v3_3 = int(joined_mask(merged, "clean_class_join_status_v3_3").sum())
    not_joined_v3_3 = len(merged) - joined_v3_3
    usable_v3_3 = int(merged["race_class_confidence_v3_3"].isin(["HIGH", "MEDIUM"]).sum())
    unresolved_v3_3 = int(merged["race_class_family_v3_3"].eq("UNRESOLVED").sum())
    excluded_v3_3 = int(merged["race_class_family_v3_3"].eq("EXCLUDED_TRIAL_JUMPOUT").sum())

    v3_1 = pd.read_csv(V3_1, dtype=str, keep_default_na=False, low_memory=False) if V3_1.exists() else pd.DataFrame()
    if not v3_1.empty:
        joined_v3_1 = int(v3_1["clean_class_join_status"].astype(str).str.upper().eq("JOINED").sum())
        not_joined_v3_1 = len(v3_1) - joined_v3_1
        usable_v3_1 = int(v3_1["race_class_confidence_v3_1"].isin(["HIGH", "MEDIUM"]).sum())
        unresolved_v3_1 = int(v3_1["race_class_family_v3_1"].eq("UNRESOLVED").sum())
        source_v3_1 = source_stats_v3_1(v3_1)
    else:
        joined_v3_1 = ""
        not_joined_v3_1 = ""
        usable_v3_1 = ""
        unresolved_v3_1 = ""
        source_v3_1 = pd.DataFrame(columns=["source_file", "rows", "joined", "not_joined", "join_rate_pct"])

    audit_rows: list[dict[str, object]] = [
        metric_row("overall", "rating_rows_loaded", value=len(rating), v3_3_value=len(rating)),
        metric_row("overall", "class_clean_v3_rows_loaded", value=len(clean), v3_3_value=len(clean)),
        metric_row("overall", "rows_written", value=len(merged), v3_3_value=len(merged)),
        metric_row("overall_compare_v3_1_v3_3", "clean_class_joined", v3_1_value=joined_v3_1, v3_3_value=joined_v3_3, delta=(joined_v3_3 - joined_v3_1) if isinstance(joined_v3_1, int) else ""),
        metric_row("overall_compare_v3_1_v3_3", "clean_class_not_joined", v3_1_value=not_joined_v3_1, v3_3_value=not_joined_v3_3, delta=(not_joined_v3_3 - not_joined_v3_1) if isinstance(not_joined_v3_1, int) else ""),
        metric_row("overall_compare_v3_1_v3_3", "usable_clean_class_rows", v3_1_value=usable_v3_1, v3_3_value=usable_v3_3, delta=(usable_v3_3 - usable_v3_1) if isinstance(usable_v3_1, int) else ""),
        metric_row("overall_compare_v3_1_v3_3", "unresolved_clean_class_rows", v3_1_value=unresolved_v3_1, v3_3_value=unresolved_v3_3, delta=(unresolved_v3_3 - unresolved_v3_1) if isinstance(unresolved_v3_1, int) else ""),
        metric_row("overall", "excluded_trial_jumpout_rows", value=excluded_v3_3, v3_3_value=excluded_v3_3),
        metric_row("overall", "joined_exact_horse_date_track_distance", value=int(merged["clean_class_join_status_v3_3"].eq("JOINED_EXACT_HORSE_DATE_TRACK_DISTANCE").sum())),
        metric_row("overall", "joined_fallback_horse_track_distance", value=int(merged["clean_class_join_status_v3_3"].eq("JOINED_FALLBACK_HORSE_TRACK_DISTANCE").sum())),
        metric_row("overall", "ambiguous_clean_class_matches", value=int(merged["clean_class_ambiguous_match_v3_3"].eq("TRUE").sum())),
        metric_row("input_clean_key_audit", "exact_join_key_groups", value=int(clean_keyed.groupby(EXACT_KEYS, dropna=False).ngroups)),
        metric_row("input_clean_key_audit", "exact_join_key_groups_with_multiple_classes", value=int((clean_keyed.groupby(EXACT_KEYS, dropna=False)["race_class_model_v3"].nunique() > 1).sum())),
        metric_row("input_clean_key_audit", "fallback_join_key_groups", value=int(clean_keyed.groupby(FALLBACK_KEYS, dropna=False).ngroups)),
        metric_row("input_clean_key_audit", "fallback_join_key_groups_with_multiple_classes", value=int((clean_keyed.groupby(FALLBACK_KEYS, dropna=False)["race_class_model_v3"].nunique() > 1).sum())),
    ]

    for status, count in merged["clean_class_join_status_v3_3"].value_counts().sort_index().items():
        audit_rows.append(metric_row("v3_3_join_status_counts", status, value=int(count)))

    for source_file, group in merged.groupby("source_file", dropna=False):
        total = len(group)
        joined = int(joined_mask(group, "clean_class_join_status_v3_3").sum())
        not_joined = total - joined
        usable = int(group["race_class_confidence_v3_3"].isin(["HIGH", "MEDIUM"]).sum())
        unresolved = int(group["race_class_family_v3_3"].eq("UNRESOLVED").sum())
        audit_rows.append(
            metric_row(
                "v3_3_source_file_join_rate",
                "source_file_join_rate",
                source_file=source_file,
                rows=total,
                joined=joined,
                not_joined=not_joined,
                join_rate_pct=pct(joined, total),
                notes=f"usable={usable}; unresolved={unresolved}",
            )
        )

    source_v3_3 = (
        pd.DataFrame(
            [
                {
                    "source_file": source_file,
                    "rows": len(group),
                    "joined": int(joined_mask(group, "clean_class_join_status_v3_3").sum()),
                }
                for source_file, group in merged.groupby("source_file", dropna=False)
            ]
        )
        if "source_file" in merged.columns
        else pd.DataFrame(columns=["source_file", "rows", "joined"])
    )
    if not source_v3_3.empty:
        source_v3_3["not_joined"] = source_v3_3["rows"] - source_v3_3["joined"]
        source_v3_3["join_rate_pct"] = [
            pct(int(row.joined), int(row.rows)) for row in source_v3_3.itertuples(index=False)
        ]

    compare_sources = source_v3_3.merge(
        source_v3_1,
        on="source_file",
        how="outer",
        suffixes=("_v3_3", "_v3_1"),
    ).fillna("")

    for row in compare_sources.to_dict("records"):
        v31_joined = row.get("joined_v3_1", "")
        v33_joined = row.get("joined_v3_3", "")
        delta = ""
        if str(v31_joined).strip() and str(v33_joined).strip():
            delta = int(v33_joined) - int(v31_joined)
        audit_rows.append(
            metric_row(
                "v3_1_vs_v3_3_source_file_compare",
                "source_file_join_compare",
                source_file=row.get("source_file", ""),
                rows=row.get("rows_v3_3", ""),
                joined=row.get("joined_v3_3", ""),
                not_joined=row.get("not_joined_v3_3", ""),
                join_rate_pct=row.get("join_rate_pct_v3_3", ""),
                v3_1_value=v31_joined,
                v3_3_value=v33_joined,
                delta=delta,
                notes=f"v3_1_rate={row.get('join_rate_pct_v3_1', '')}; v3_3_rate={row.get('join_rate_pct_v3_3', '')}",
            )
        )

    audit = pd.DataFrame(audit_rows)
    audit.to_csv(AUDIT, index=False)

    print(f"wrote: {OUTPUT}")
    print(f"wrote: {AUDIT}")
    print()
    print(audit[audit["section"].isin(["overall", "overall_compare_v3_1_v3_3", "v3_3_join_status_counts"])].to_string(index=False))
    print()
    print("Source-file join rates:")
    print(audit[audit["section"].eq("v3_3_source_file_join_rate")].to_string(index=False))
    print("=" * 90)


if __name__ == "__main__":
    main()
