from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_historical_performance_rating_v3_3.csv"
LADDER = DATA / "edgeiq_class_ladder_v1.csv"
OLD_V5 = DATA / "edgeiq_historical_performance_rating_v5.csv"

OUT = DATA / "edgeiq_historical_performance_rating_v5_1.csv"
AUDIT = DATA / "edgeiq_historical_performance_rating_v5_1_audit.csv"

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

NEUTRAL_CLASS_SCORE = 54.0


def norm(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).upper().strip().split())


def safe_mean(series: pd.Series) -> str:
    cleaned = pd.to_numeric(series, errors="coerce").dropna()
    if cleaned.empty:
        return ""
    return f"{float(cleaned.mean()):.2f}"


def safe_first(series: pd.Series) -> str:
    cleaned = series.dropna()
    cleaned = cleaned[cleaned.astype(str).str.strip().ne("")]
    if cleaned.empty:
        return ""
    return str(cleaned.iloc[0])


def audit_row(
    section: str,
    metric: str,
    race_class: str = "",
    source_file: str = "",
    rating_status: str = "",
    value: object = "",
    count: object = "",
    old_v5_value: object = "",
    v5_1_value: object = "",
    delta: object = "",
    notes: str = "",
) -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "race_class": race_class,
        "source_file": source_file,
        "rating_status": rating_status,
        "value": value,
        "count": count,
        "old_v5_value": old_v5_value,
        "v5_1_value": v5_1_value,
        "delta": delta,
        "notes": notes,
    }


def class_summary(df: pd.DataFrame, class_col: str, rating_col: str) -> dict[str, dict[str, object]]:
    summaries: dict[str, dict[str, object]] = {}
    if class_col not in df.columns or rating_col not in df.columns:
        return summaries

    work = df.copy()
    work["_class_key"] = work[class_col].map(norm)
    work["finish_position"] = pd.to_numeric(work["finish_position"], errors="coerce")
    work[rating_col] = pd.to_numeric(work[rating_col], errors="coerce")
    if "performance_rating_v3" in work.columns:
        work["performance_rating_v3"] = pd.to_numeric(work["performance_rating_v3"], errors="coerce")

    for cls in KEY_CLASSES:
        group = work[work["_class_key"].eq(cls)]
        winners = group[group["finish_position"].eq(1)]
        summaries[cls] = {
            "runs": len(group),
            "winners": len(winners),
            "winner_avg": safe_mean(winners[rating_col]) if len(winners) else "",
            "all_avg": safe_mean(group[rating_col]) if len(group) else "",
            "v3_winner_avg": safe_mean(winners["performance_rating_v3"]) if len(winners) and "performance_rating_v3" in winners.columns else "",
            "ladder_score": safe_first(group["class_ladder_score_v1"]) if "class_ladder_score_v1" in group.columns and len(group) else "",
        }

    return summaries


def parse_float(value: object) -> float | None:
    try:
        if value == "" or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def hierarchy_pass(summaries: dict[str, dict[str, object]]) -> tuple[bool, str]:
    checks = [
        ("GROUP 1", "GROUP 2"),
        ("GROUP 2", "GROUP 3"),
        ("GROUP 3", "LISTED"),
        ("LISTED", "BM84"),
        ("BM84", "BM78"),
        ("BM78", "BM70"),
        ("BM70", "BM64"),
        ("BM64", "BM58"),
        ("BM58", "BM56"),
        ("CLASS 1", "MAIDEN"),
        ("CLASS 2", "CLASS 1"),
        ("CLASS 3", "CLASS 2"),
    ]

    failures: list[str] = []
    for higher, lower in checks:
        higher_value = parse_float(summaries.get(higher, {}).get("winner_avg"))
        lower_value = parse_float(summaries.get(lower, {}).get("winner_avg"))
        if higher_value is None or lower_value is None:
            continue
        if higher_value + 0.01 < lower_value:
            failures.append(f"{higher} {higher_value:.2f} below {lower} {lower_value:.2f}")

    return not failures, "; ".join(failures)


def main() -> None:
    print("=" * 90)
    print("EDGEIQ HISTORICAL PERFORMANCE RATING V5.1")
    print("=" * 90)

    if not SRC.exists():
        raise FileNotFoundError(f"Missing input: {SRC}")
    if not LADDER.exists():
        raise FileNotFoundError(f"Missing input: {LADDER}")

    df = pd.read_csv(SRC, dtype=str, keep_default_na=False, low_memory=False)
    ladder = pd.read_csv(LADDER, dtype=str, keep_default_na=False, low_memory=False)

    required = {
        "performance_rating_v3",
        "finish_position",
        "real_field_size",
        "race_class_clean_v3_3",
        "race_class_family_v3_3",
        "race_class_confidence_v3_3",
        "source_file",
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing required V3.3 input columns: {missing}")

    ladder_required = {
        "race_class",
        "class_ladder_score_v1",
        "class_ladder_norm_v1",
        "class_ladder_rank_v1",
        "class_ladder_reason_v1",
        "sample_confidence_v1",
    }
    ladder_missing = sorted(ladder_required.difference(ladder.columns))
    if ladder_missing:
        raise ValueError(f"Missing ladder columns: {ladder_missing}")

    df["performance_rating_v3"] = pd.to_numeric(df["performance_rating_v3"], errors="coerce")
    df["finish_position"] = pd.to_numeric(df["finish_position"], errors="coerce")
    df["real_field_size"] = pd.to_numeric(df["real_field_size"], errors="coerce")
    df["_class_key"] = df["race_class_clean_v3_3"].map(norm)

    ladder_keep = ladder[
        [
            "race_class",
            "class_ladder_score_v1",
            "class_ladder_norm_v1",
            "class_ladder_rank_v1",
            "class_ladder_reason_v1",
            "sample_confidence_v1",
        ]
    ].copy()
    ladder_keep["_class_key"] = ladder_keep["race_class"].map(norm)
    ladder_keep["class_ladder_score_v1"] = pd.to_numeric(ladder_keep["class_ladder_score_v1"], errors="coerce")
    ladder_keep = ladder_keep.drop_duplicates("_class_key", keep="first").drop(columns=["race_class"])

    df = df.merge(ladder_keep, on="_class_key", how="left")
    df["class_ladder_score_v1"] = pd.to_numeric(df["class_ladder_score_v1"], errors="coerce")

    df["class_quality_adjustment_v5_1"] = (
        (df["class_ladder_score_v1"] - NEUTRAL_CLASS_SCORE) / 10.0 * 2.5
    ).fillna(0)

    df["finish_quality_multiplier_v5_1"] = np.select(
        [
            df["finish_position"].eq(1),
            df["finish_position"].eq(2),
            df["finish_position"].eq(3),
            df["finish_position"].between(4, 5),
            df["finish_position"].between(6, 8),
        ],
        [
            1.00,
            0.85,
            0.70,
            0.50,
            0.30,
        ],
        default=0.15,
    )

    df["field_size_adjustment_v5_1"] = np.select(
        [
            df["real_field_size"] >= 16,
            df["real_field_size"].between(13, 15),
            df["real_field_size"].between(10, 12),
            df["real_field_size"].between(7, 9),
            df["real_field_size"].between(1, 6),
        ],
        [
            1.25,
            0.80,
            0.40,
            0.00,
            -0.50,
        ],
        default=0.00,
    )
    df["field_size_adjustment_v5_1"] = df["field_size_adjustment_v5_1"] * df["finish_quality_multiplier_v5_1"]

    df["performance_rating_base_v5_1"] = df["performance_rating_v3"]
    df["performance_rating_v5_1"] = (
        df["performance_rating_base_v5_1"]
        + (df["class_quality_adjustment_v5_1"] * df["finish_quality_multiplier_v5_1"])
        + df["field_size_adjustment_v5_1"]
    )
    df["performance_rating_v5_1"] = df["performance_rating_v5_1"].clip(lower=0, upper=120).round(2)

    confidence = df["race_class_confidence_v3_3"].astype(str).str.upper().str.strip()
    family = df["race_class_family_v3_3"].astype(str).str.upper().str.strip()

    df["rating_v5_1_status"] = np.select(
        [
            df["class_ladder_score_v1"].notna() & confidence.isin(["HIGH", "MEDIUM"]),
            family.eq("UNRESOLVED"),
            family.eq("EXCLUDED_TRIAL_JUMPOUT"),
        ],
        [
            "CLASS_LADDER_ADJUSTED",
            "UNRESOLVED_CLASS_BASE_ONLY",
            "EXCLUDED_TRIAL_JUMPOUT_BASE_ONLY",
        ],
        default="BASE_ONLY",
    )

    df["built_at_v5_1"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    df = df.drop(columns=["_class_key"])
    df.to_csv(OUT, index=False)

    old_summaries = {}
    if OLD_V5.exists():
        old_v5 = pd.read_csv(OLD_V5, dtype=str, keep_default_na=False, low_memory=False)
        old_summaries = class_summary(old_v5, "race_class_clean_v3_1", "performance_rating_v5")

    new_summaries = class_summary(df, "race_class_clean_v3_3", "performance_rating_v5_1")
    pass_flag, pass_notes = hierarchy_pass(new_summaries)

    audit_rows: list[dict[str, object]] = [
        audit_row("overall", "rows_loaded", value=len(df)),
        audit_row("overall", "rows_written", value=len(df)),
        audit_row("overall", "bm64_neutral_class_score", value=NEUTRAL_CLASS_SCORE),
        audit_row("overall", "ladder_scale_points_per_10", value=2.5),
        audit_row("overall", "v5_1_hierarchy_check_pass", value="TRUE" if pass_flag else "FALSE", notes=pass_notes),
        audit_row("overall", "class_ladder_missing_rows", value=int(df["class_ladder_score_v1"].isna().sum())),
        audit_row("overall", "class_ladder_adjusted_rows", value=int(df["rating_v5_1_status"].eq("CLASS_LADDER_ADJUSTED").sum())),
    ]

    for cls in KEY_CLASSES:
        new = new_summaries.get(cls, {})
        old = old_summaries.get(cls, {})
        old_winner_avg = old.get("winner_avg", "")
        new_winner_avg = new.get("winner_avg", "")
        old_value = parse_float(old_winner_avg)
        new_value = parse_float(new_winner_avg)
        delta = f"{new_value - old_value:.2f}" if old_value is not None and new_value is not None else ""
        audit_rows.append(
            audit_row(
                "key_class_winner_averages",
                "winner_average",
                race_class=cls,
                count=new.get("winners", ""),
                old_v5_value=old_winner_avg,
                v5_1_value=new_winner_avg,
                delta=delta,
                notes=(
                    f"runs={new.get('runs', '')}; v3_winner_avg={new.get('v3_winner_avg', '')}; "
                    f"ladder_score={new.get('ladder_score', '')}"
                ),
            )
        )

    for status, count in df["rating_v5_1_status"].value_counts().sort_index().items():
        audit_rows.append(audit_row("rating_v5_1_status_counts", status, rating_status=status, count=int(count)))

    for source_file, group in df.groupby("source_file", dropna=False):
        for status, count in group["rating_v5_1_status"].value_counts().sort_index().items():
            audit_rows.append(
                audit_row(
                    "source_file_rating_status_counts",
                    "source_file_status_count",
                    source_file=source_file,
                    rating_status=status,
                    count=int(count),
                )
            )

    audit = pd.DataFrame(audit_rows)
    audit.to_csv(AUDIT, index=False)

    print(f"wrote: {OUT}")
    print(f"wrote: {AUDIT}")
    print()
    print(audit[audit["section"].isin(["overall", "key_class_winner_averages", "rating_v5_1_status_counts"])].to_string(index=False))
    print("=" * 90)


if __name__ == "__main__":
    main()
