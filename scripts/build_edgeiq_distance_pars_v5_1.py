from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_historical_performance_rating_v5_1.csv"
OUT = DATA / "edgeiq_distance_pars_v5_1.csv"
AUDIT = DATA / "edgeiq_distance_pars_v5_1_audit.csv"

DISTANCE_ORDER = [
    "UNDER_800",
    "800-999",
    "1000-1199",
    "1200-1399",
    "1400-1599",
    "1600-1799",
    "1800-1999",
    "2000-2199",
    "2200-2399",
    "2400-2799",
    "2800+",
]


def distance_band(distance: float) -> str:
    if distance < 800:
        return "UNDER_800"
    if distance <= 999:
        return "800-999"
    if distance <= 1199:
        return "1000-1199"
    if distance <= 1399:
        return "1200-1399"
    if distance <= 1599:
        return "1400-1599"
    if distance <= 1799:
        return "1600-1799"
    if distance <= 1999:
        return "1800-1999"
    if distance <= 2199:
        return "2000-2199"
    if distance <= 2399:
        return "2200-2399"
    if distance <= 2799:
        return "2400-2799"
    return "2800+"


def fmt(value: object) -> str:
    if pd.isna(value):
        return ""
    return f"{float(value):.2f}"


def audit_row(section: str, metric: str, value: object = "", distance_band_value: str = "", notes: str = "") -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "distance_band_v5_1": distance_band_value,
        "value": value,
        "notes": notes,
    }


def main() -> None:
    print("=" * 90)
    print("EDGEIQ DISTANCE PARS V5.1 - ADJUSTMENT MODE")
    print("=" * 90)

    if not SRC.exists():
        raise FileNotFoundError(f"Missing input: {SRC}")

    df = pd.read_csv(SRC, dtype=str, keep_default_na=False, low_memory=False)

    required = {
        "performance_rating_v5_1",
        "finish_position",
        "distance",
        "race_class_confidence_v3_3",
        "race_class_family_v3_3",
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing required V5.1 columns: {missing}")

    source_rows = len(df)

    df["performance_rating_v5_1"] = pd.to_numeric(df["performance_rating_v5_1"], errors="coerce")
    df["finish_position"] = pd.to_numeric(df["finish_position"], errors="coerce")
    df["distance"] = pd.to_numeric(df["distance"], errors="coerce")

    df = df[
        df["performance_rating_v5_1"].notna()
        & df["finish_position"].notna()
        & df["distance"].notna()
        & df["race_class_confidence_v3_3"].isin(["HIGH", "MEDIUM"])
        & ~df["race_class_family_v3_3"].isin(["UNRESOLVED", "EXCLUDED_TRIAL_JUMPOUT"])
    ].copy()

    df["distance_band_v5_1"] = df["distance"].apply(distance_band)

    winners_all = df[df["finish_position"].eq(1)]
    top3_all = df[df["finish_position"].le(3)]

    if len(winners_all) >= 20 and len(top3_all) >= 50:
        global_baseline = (0.60 * winners_all["performance_rating_v5_1"].median()) + (0.40 * top3_all["performance_rating_v5_1"].median())
        global_method = "GLOBAL_WINNER_TOP3_BLEND"
    elif len(top3_all) >= 30:
        global_baseline = top3_all["performance_rating_v5_1"].median()
        global_method = "GLOBAL_TOP3_MEDIAN"
    else:
        global_baseline = df["performance_rating_v5_1"].median()
        global_method = "GLOBAL_ALL_MEDIAN"

    rows: list[dict[str, object]] = []
    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for band, group in df.groupby("distance_band_v5_1", dropna=False):
        winners = group[group["finish_position"].eq(1)]
        top3 = group[group["finish_position"].le(3)]

        run_count = len(group)
        winner_count = len(winners)
        top3_count = len(top3)

        winner_median = winners["performance_rating_v5_1"].median() if winner_count else np.nan
        top3_median = top3["performance_rating_v5_1"].median() if top3_count else np.nan
        all_median = group["performance_rating_v5_1"].median() if run_count else np.nan

        if winner_count >= 20 and top3_count >= 50:
            absolute_par = (0.60 * winner_median) + (0.40 * top3_median)
            method = "ADJ_FROM_WINNER_TOP3_BLEND"
            confidence = "HIGH"
        elif top3_count >= 30:
            absolute_par = top3_median
            method = "ADJ_FROM_TOP3_MEDIAN"
            confidence = "MEDIUM"
        elif run_count >= 50:
            absolute_par = all_median
            method = "ADJ_FROM_ALL_MEDIAN_LOW_WIN_SAMPLE"
            confidence = "LOW"
        else:
            absolute_par = all_median
            method = "ADJ_FROM_LOW_SAMPLE_RESEARCH_ONLY"
            confidence = "VERY_LOW"

        adjustment = absolute_par - global_baseline if pd.notna(absolute_par) and pd.notna(global_baseline) else np.nan

        rows.append(
            {
                "distance_band_v5_1": band,
                "run_count": run_count,
                "winner_count": winner_count,
                "top3_count": top3_count,
                "winner_median_v5_1": fmt(winner_median),
                "top3_median_v5_1": fmt(top3_median),
                "all_runs_median_v5_1": fmt(all_median),
                "distance_absolute_par_rating_v5_1": fmt(absolute_par),
                "distance_global_baseline_v5_1": fmt(global_baseline),
                "distance_par_rating_v5_1": fmt(adjustment),
                "distance_par_method_v5_1": method,
                "distance_par_confidence_v5_1": confidence,
                "distance_par_mode_v5_1": "ADJUSTMENT_FROM_GLOBAL_BASELINE",
                "distance_global_method_v5_1": global_method,
                "built_at": built_at,
            }
        )

    out = pd.DataFrame(rows)
    out["sort_order"] = out["distance_band_v5_1"].apply(lambda value: DISTANCE_ORDER.index(value) if value in DISTANCE_ORDER else 999)
    out = out.sort_values("sort_order").drop(columns=["sort_order"])
    out.to_csv(OUT, index=False)

    audit_rows = [
        audit_row("overall", "source_rows_loaded", source_rows),
        audit_row("overall", "rows_used", len(df)),
        audit_row("overall", "global_baseline", fmt(global_baseline), notes=global_method),
        audit_row("overall", "distance_par_rows", len(out)),
        audit_row("overall", "adjustment_mode", "TRUE"),
    ]

    for row in out.to_dict("records"):
        audit_rows.append(
            audit_row(
                "distance_pars",
                "distance_adjustment_v5_1",
                row["distance_par_rating_v5_1"],
                distance_band_value=row["distance_band_v5_1"],
                notes=f"absolute={row['distance_absolute_par_rating_v5_1']}; baseline={row['distance_global_baseline_v5_1']}; method={row['distance_par_method_v5_1']}; confidence={row['distance_par_confidence_v5_1']}",
            )
        )

    audit = pd.DataFrame(audit_rows)
    audit.to_csv(AUDIT, index=False)

    print(f"wrote: {OUT}")
    print(f"wrote: {AUDIT}")
    print()
    print(out.to_string(index=False))
    print("=" * 90)


if __name__ == "__main__":
    main()
