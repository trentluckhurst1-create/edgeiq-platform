from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_historical_performance_rating_v5_1.csv"
V5_1_PARS = DATA / "edgeiq_class_pars_v5_1.csv"

OUT = DATA / "edgeiq_class_pars_v5_2.csv"
AUDIT = DATA / "edgeiq_class_pars_v5_2_audit.csv"

BLACKTYPE = {"GROUP 1", "GROUP 2", "GROUP 3", "LISTED"}

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

HIERARCHY_LOW_TO_HIGH = [
    ("MAIDEN", "CLASS 1", True),
    ("CLASS 1", "CLASS 2", True),
    ("CLASS 2", "CLASS 3", True),
    ("CLASS 3", "BM56", True),
    ("BM56", "BM58", False),
    ("BM58", "BM64", True),
    ("BM64", "BM70", True),
    ("BM70", "BM78", True),
    ("BM78", "BM84", True),
    ("BM84", "LISTED", True),
    ("LISTED", "GROUP 3", True),
    ("GROUP 3", "GROUP 2", True),
    ("GROUP 2", "GROUP 1", True),
]


def norm(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).upper().strip().split())


def fmt(value: object) -> str:
    if pd.isna(value):
        return ""
    return f"{float(value):.2f}"


def as_float(value: object) -> float | None:
    try:
        if value == "" or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def previous_pars() -> dict[str, str]:
    if not V5_1_PARS.exists():
        return {}
    old = pd.read_csv(V5_1_PARS, dtype=str, keep_default_na=False, low_memory=False)
    if {"race_class_clean_v5_1", "class_par_rating_v5_1"}.difference(old.columns):
        return {}
    return {
        norm(row["race_class_clean_v5_1"]): str(row["class_par_rating_v5_1"])
        for _, row in old.iterrows()
        if norm(row["race_class_clean_v5_1"])
    }


def choose_par(
    race_class: str,
    run_count: int,
    winner_count: int,
    top3_count: int,
    winner_median: float,
    top3_median: float,
    all_median: float,
) -> tuple[float, str, str, str]:
    if race_class in BLACKTYPE and winner_count >= 8 and top3_count >= 25:
        confidence = "HIGH" if winner_count >= 20 and top3_count >= 50 else "MEDIUM"
        return (
            (0.60 * winner_median) + (0.40 * top3_median),
            "WINNER_TOP3_BLEND",
            confidence,
            "BLACKTYPE_RELAXED_WINNER_TOP3_BLEND",
        )

    if winner_count >= 20 and top3_count >= 50 and run_count >= 100:
        return (0.70 * all_median) + (0.30 * top3_median), "RUNNER_TOP3_BLEND", "HIGH", "RUNNER_STANDARD_V5_2_FIX"
    if top3_count >= 30 and run_count >= 50:
        return (0.80 * all_median) + (0.20 * top3_median), "RUNNER_TOP3_LIGHT_BLEND", "MEDIUM", "RUNNER_STANDARD_V5_2_FIX"
    if run_count >= 50:
        return all_median, "ALL_MEDIAN_RUNNER_STANDARD", "LOW", "RUNNER_STANDARD_V5_2_FIX"
    return all_median, "LOW_SAMPLE_RESEARCH_ONLY", "VERY_LOW", "STANDARD_V5_1_THRESHOLDS"


def apply_hierarchy_guard(out: pd.DataFrame) -> pd.DataFrame:
    guarded = out.copy()
    guarded["class_par_rating_numeric_v5_2"] = pd.to_numeric(guarded["class_par_rating_raw_v5_2"], errors="coerce")
    guarded["class_par_rating_final_numeric_v5_2"] = guarded["class_par_rating_numeric_v5_2"]
    guarded["class_par_hierarchy_adjustment_v5_2"] = 0.0
    guarded["class_par_hierarchy_reason_v5_2"] = ""

    index_by_class = {
        str(race_class): idx
        for idx, race_class in guarded["race_class_clean_v5_2"].items()
    }

    for lower, higher, strict in HIERARCHY_LOW_TO_HIGH:
        if lower not in index_by_class or higher not in index_by_class:
            continue

        lower_idx = index_by_class[lower]
        higher_idx = index_by_class[higher]
        lower_value = guarded.at[lower_idx, "class_par_rating_final_numeric_v5_2"]
        higher_value = guarded.at[higher_idx, "class_par_rating_final_numeric_v5_2"]

        if pd.isna(lower_value) or pd.isna(higher_value):
            continue

        required_value = float(lower_value) + (0.01 if strict else 0.0)
        if float(higher_value) + 1e-9 < required_value:
            adjusted_value = round(required_value, 2)
            guarded.at[higher_idx, "class_par_rating_final_numeric_v5_2"] = adjusted_value
            guarded.at[higher_idx, "class_par_hierarchy_adjustment_v5_2"] = round(adjusted_value - float(higher_value), 2)
            comparator = ">" if strict else ">="
            guarded.at[higher_idx, "class_par_hierarchy_reason_v5_2"] = (
                f"hard_hierarchy_guard: {higher} must be {comparator} {lower}"
            )

    guarded["class_par_rating_v5_2"] = guarded["class_par_rating_final_numeric_v5_2"].map(fmt)
    guarded["class_par_hierarchy_adjustment_v5_2"] = guarded["class_par_hierarchy_adjustment_v5_2"].map(fmt)
    return guarded.drop(columns=["class_par_rating_numeric_v5_2", "class_par_rating_final_numeric_v5_2"])


def hierarchy_check(out: pd.DataFrame) -> tuple[bool, str]:
    lookup = {
        row.race_class_clean_v5_2: as_float(row.class_par_rating_v5_2)
        for row in out[["race_class_clean_v5_2", "class_par_rating_v5_2"]].itertuples(index=False)
    }

    failures: list[str] = []
    for lower, higher, strict in HIERARCHY_LOW_TO_HIGH:
        lower_value = lookup.get(lower)
        higher_value = lookup.get(higher)
        if lower_value is None or higher_value is None:
            failures.append(f"missing {higher} or {lower}")
            continue
        if strict and higher_value <= lower_value:
            failures.append(f"{higher} {higher_value:.2f} not > {lower} {lower_value:.2f}")
        if not strict and higher_value < lower_value:
            failures.append(f"{higher} {higher_value:.2f} not >= {lower} {lower_value:.2f}")

    return not failures, "; ".join(failures)


def audit_row(
    section: str,
    metric: str,
    race_class: str = "",
    value: object = "",
    count: object = "",
    v5_1_value: object = "",
    v5_2_raw_value: object = "",
    v5_2_value: object = "",
    delta: object = "",
    notes: str = "",
) -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "race_class": race_class,
        "value": value,
        "count": count,
        "v5_1_value": v5_1_value,
        "v5_2_raw_value": v5_2_raw_value,
        "v5_2_value": v5_2_value,
        "delta": delta,
        "notes": notes,
    }


def main() -> None:
    print("=" * 90)
    print("EDGEIQ CLASS PARS V5.2")
    print("=" * 90)

    if not SRC.exists():
        raise FileNotFoundError(f"Missing input: {SRC}")

    df = pd.read_csv(SRC, dtype=str, keep_default_na=False, low_memory=False)
    required = {
        "performance_rating_v5_1",
        "finish_position",
        "race_class_clean_v3_3",
        "race_class_confidence_v3_3",
        "race_class_family_v3_3",
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing required V5.1 columns: {missing}")

    df["performance_rating_v5_1"] = pd.to_numeric(df["performance_rating_v5_1"], errors="coerce")
    df["finish_position"] = pd.to_numeric(df["finish_position"], errors="coerce")
    df["_class_key"] = df["race_class_clean_v3_3"].map(norm)

    source_rows = len(df)
    df = df[
        df["performance_rating_v5_1"].notna()
        & df["finish_position"].notna()
        & df["race_class_confidence_v3_3"].isin(["HIGH", "MEDIUM"])
        & ~df["race_class_family_v3_3"].isin(["UNRESOLVED", "EXCLUDED_TRIAL_JUMPOUT"])
        & df["_class_key"].ne("")
    ].copy()

    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows: list[dict[str, object]] = []

    for race_class, group in df.groupby("_class_key", dropna=False):
        winners = group[group["finish_position"].eq(1)]
        top3 = group[group["finish_position"].le(3)]

        run_count = len(group)
        winner_count = len(winners)
        top3_count = len(top3)

        winner_median = winners["performance_rating_v5_1"].median() if winner_count else np.nan
        top3_median = top3["performance_rating_v5_1"].median() if top3_count else np.nan
        all_median = group["performance_rating_v5_1"].median() if run_count else np.nan

        par, method, confidence, threshold_rule = choose_par(
            race_class,
            run_count,
            winner_count,
            top3_count,
            winner_median,
            top3_median,
            all_median,
        )

        rows.append(
            {
                "race_class_clean_v5_2": race_class,
                "run_count": run_count,
                "winner_count": winner_count,
                "top3_count": top3_count,
                "winner_median_v5_2": fmt(winner_median),
                "top3_median_v5_2": fmt(top3_median),
                "all_runs_median_v5_2": fmt(all_median),
                "class_par_rating_raw_v5_2": fmt(par),
                "class_par_method_v5_2": method,
                "class_par_confidence_v5_2": confidence,
                "class_par_threshold_rule_v5_2": threshold_rule,
                "built_at": built_at,
            }
        )

    out = pd.DataFrame(rows)
    if not out.empty:
        out = apply_hierarchy_guard(out)
        out["_sort_rating"] = pd.to_numeric(out["class_par_rating_v5_2"], errors="coerce")
        out = out.sort_values("_sort_rating", ascending=False).drop(columns=["_sort_rating"])

    out.to_csv(OUT, index=False)

    pass_flag, pass_notes = hierarchy_check(out)
    v5_1 = previous_pars()

    audit_rows: list[dict[str, object]] = [
        audit_row("overall", "source_rows_loaded", value=source_rows),
        audit_row("overall", "rows_used", value=len(df)),
        audit_row("overall", "class_par_rows", value=len(out)),
        audit_row("overall", "hard_hierarchy_check_pass", value="TRUE" if pass_flag else "FALSE", notes=pass_notes),
        audit_row("overall", "blacktype_relaxed_threshold_rows", value=int(out["class_par_threshold_rule_v5_2"].eq("BLACKTYPE_RELAXED_WINNER_TOP3_BLEND").sum()) if not out.empty else 0),
        audit_row("overall", "hierarchy_guard_adjusted_rows", value=int(pd.to_numeric(out["class_par_hierarchy_adjustment_v5_2"], errors="coerce").fillna(0).ne(0).sum()) if not out.empty else 0),
    ]

    keyed = out.set_index("race_class_clean_v5_2") if not out.empty else pd.DataFrame()
    for race_class in KEY_CLASSES:
        if not keyed.empty and race_class in keyed.index:
            row = keyed.loc[race_class]
            previous_value = v5_1.get(race_class, "")
            current_value = row["class_par_rating_v5_2"]
            previous_number = as_float(previous_value)
            current_number = as_float(current_value)
            delta = f"{current_number - previous_number:.2f}" if previous_number is not None and current_number is not None else ""
            audit_rows.append(
                audit_row(
                    "key_class_pars",
                    "class_par_rating",
                    race_class=race_class,
                    count=row["run_count"],
                    v5_1_value=previous_value,
                    v5_2_raw_value=row["class_par_rating_raw_v5_2"],
                    v5_2_value=current_value,
                    delta=delta,
                    notes=(
                        f"winner_count={row['winner_count']}; top3_count={row['top3_count']}; "
                        f"method={row['class_par_method_v5_2']}; confidence={row['class_par_confidence_v5_2']}; "
                        f"rule={row['class_par_threshold_rule_v5_2']}; "
                        f"hierarchy_adjustment={row['class_par_hierarchy_adjustment_v5_2']}; "
                        f"hierarchy_reason={row['class_par_hierarchy_reason_v5_2']}"
                    ),
                )
            )
        else:
            audit_rows.append(audit_row("key_class_pars", "class_par_rating", race_class=race_class, notes="missing"))

    for confidence, count in out["class_par_confidence_v5_2"].value_counts().sort_index().items():
        audit_rows.append(audit_row("class_par_confidence_counts", confidence, value=int(count)))

    for method, count in out["class_par_method_v5_2"].value_counts().sort_index().items():
        audit_rows.append(audit_row("class_par_method_counts", method, value=int(count)))

    audit = pd.DataFrame(audit_rows)
    audit.to_csv(AUDIT, index=False)

    print(f"wrote: {OUT}")
    print(f"wrote: {AUDIT}")
    print()
    print(audit[audit["section"].isin(["overall", "key_class_pars"])].to_string(index=False))
    print("=" * 90)

    if not pass_flag:
        raise SystemExit("V5.2 hard hierarchy check failed")


if __name__ == "__main__":
    main()

