from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_historical_performance_rating_v5_1.csv"
OLD_PARS = DATA / "edgeiq_class_pars_v5.csv"

OUT = DATA / "edgeiq_class_pars_v5_1.csv"
AUDIT = DATA / "edgeiq_class_pars_v5_1_audit.csv"

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


def rounded(value: object) -> str:
    if pd.isna(value):
        return ""
    return f"{float(value):.2f}"


def parse_float(value: object) -> float | None:
    try:
        if value == "" or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def audit_row(
    section: str,
    metric: str,
    race_class: str = "",
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
        "value": value,
        "count": count,
        "old_v5_value": old_v5_value,
        "v5_1_value": v5_1_value,
        "delta": delta,
        "notes": notes,
    }


def old_par_lookup() -> dict[str, str]:
    if not OLD_PARS.exists():
        return {}
    old = pd.read_csv(OLD_PARS, dtype=str, keep_default_na=False, low_memory=False)
    if "race_class_clean_v5" not in old.columns or "class_par_rating_v5" not in old.columns:
        return {}
    return {
        norm(row["race_class_clean_v5"]): str(row["class_par_rating_v5"])
        for _, row in old.iterrows()
        if norm(row["race_class_clean_v5"])
    }


def main() -> None:
    print("=" * 90)
    print("EDGEIQ CLASS PARS V5.1")
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

    rows: list[dict[str, object]] = []
    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for cls, group in df.groupby("_class_key", dropna=False):
        winners = group[group["finish_position"].eq(1)]
        top3 = group[group["finish_position"].le(3)]

        run_count = len(group)
        winner_count = len(winners)
        top3_count = len(top3)

        winner_median = winners["performance_rating_v5_1"].median() if winner_count else np.nan
        top3_median = top3["performance_rating_v5_1"].median() if top3_count else np.nan
        all_median = group["performance_rating_v5_1"].median() if run_count else np.nan

        if winner_count >= 20 and top3_count >= 50:
            par = (0.60 * winner_median) + (0.40 * top3_median)
            method = "WINNER_TOP3_BLEND"
            confidence = "HIGH"
        elif top3_count >= 30:
            par = top3_median
            method = "TOP3_MEDIAN"
            confidence = "MEDIUM"
        elif run_count >= 50:
            par = all_median
            method = "ALL_MEDIAN_LOW_WIN_SAMPLE"
            confidence = "LOW"
        else:
            par = all_median
            method = "LOW_SAMPLE_RESEARCH_ONLY"
            confidence = "VERY_LOW"

        rows.append(
            {
                "race_class_clean_v5_1": cls,
                "run_count": run_count,
                "winner_count": winner_count,
                "top3_count": top3_count,
                "winner_median_v5_1": rounded(winner_median),
                "top3_median_v5_1": rounded(top3_median),
                "all_runs_median_v5_1": rounded(all_median),
                "class_par_rating_v5_1": rounded(par),
                "class_par_method_v5_1": method,
                "class_par_confidence_v5_1": confidence,
                "built_at": built_at,
            }
        )

    out = pd.DataFrame(rows)
    if not out.empty:
        out["_sort_rating"] = pd.to_numeric(out["class_par_rating_v5_1"], errors="coerce")
        out = out.sort_values("_sort_rating", ascending=False).drop(columns=["_sort_rating"])
    out.to_csv(OUT, index=False)

    old_lookup = old_par_lookup()
    audit_rows: list[dict[str, object]] = [
        audit_row("overall", "source_rows_loaded", value=source_rows),
        audit_row("overall", "rows_used", value=len(df)),
        audit_row("overall", "class_par_rows", value=len(out)),
        audit_row("overall", "high_confidence_pars", value=int(out["class_par_confidence_v5_1"].eq("HIGH").sum()) if not out.empty else 0),
        audit_row("overall", "medium_confidence_pars", value=int(out["class_par_confidence_v5_1"].eq("MEDIUM").sum()) if not out.empty else 0),
        audit_row("overall", "low_confidence_pars", value=int(out["class_par_confidence_v5_1"].eq("LOW").sum()) if not out.empty else 0),
        audit_row("overall", "very_low_confidence_pars", value=int(out["class_par_confidence_v5_1"].eq("VERY_LOW").sum()) if not out.empty else 0),
    ]

    keyed = out.set_index("race_class_clean_v5_1") if not out.empty else pd.DataFrame()
    for cls in KEY_CLASSES:
        if not keyed.empty and cls in keyed.index:
            row = keyed.loc[cls]
            new_value = row["class_par_rating_v5_1"]
            old_value = old_lookup.get(cls, "")
            old_num = parse_float(old_value)
            new_num = parse_float(new_value)
            delta = f"{new_num - old_num:.2f}" if old_num is not None and new_num is not None else ""
            audit_rows.append(
                audit_row(
                    "key_class_par_compare",
                    "class_par_rating",
                    race_class=cls,
                    count=row["run_count"],
                    old_v5_value=old_value,
                    v5_1_value=new_value,
                    delta=delta,
                    notes=(
                        f"winner_count={row['winner_count']}; top3_count={row['top3_count']}; "
                        f"method={row['class_par_method_v5_1']}; confidence={row['class_par_confidence_v5_1']}"
                    ),
                )
            )
        else:
            audit_rows.append(audit_row("key_class_par_compare", "class_par_rating", race_class=cls, notes="missing"))

    for confidence, count in out["class_par_confidence_v5_1"].value_counts().sort_index().items():
        audit_rows.append(audit_row("class_par_confidence_counts", confidence, value=int(count)))

    audit = pd.DataFrame(audit_rows)
    audit.to_csv(AUDIT, index=False)

    print(f"wrote: {OUT}")
    print(f"wrote: {AUDIT}")
    print()
    print(audit.to_string(index=False))
    print("=" * 90)


if __name__ == "__main__":
    main()
