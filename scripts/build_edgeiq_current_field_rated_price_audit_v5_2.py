from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_current_field_projection_v5_2.csv"
OUT = DATA / "edgeiq_current_field_rated_price_audit_v5_2.csv"
SUMMARY = DATA / "edgeiq_current_field_rated_price_audit_v5_2_summary.csv"

MODEL_B_POWER = 1.35
BASELINE_GAP_PENALTY = 2.0

MODELS = [
    "MODEL_B_EXCLUDE_NO_HISTORY",
    "MODEL_B_INCLUDE_BASELINE",
]

PRICE_BUCKETS = [
    ("<2", 0, 2),
    ("2-4", 2, 4),
    ("4-8", 4, 8),
    ("8-15", 8, 15),
    ("15-30", 15, 30),
    ("30-50", 30, 50),
    ("50+", 50, np.inf),
]


def norm(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).upper().strip().split())


def clean_race_no(value: object) -> str:
    text = str(value).strip()
    return text[:-2] if text.endswith(".0") else text


def fmt(value: object) -> str:
    if pd.isna(value):
        return ""
    return f"{float(value):.6f}"


def fmt2(value: object) -> str:
    if pd.isna(value):
        return ""
    return f"{float(value):.2f}"


def safe_mean(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return float("nan")
    return float(values.mean())


def price_bucket(price: object) -> str:
    value = pd.to_numeric(price, errors="coerce")
    if pd.isna(value):
        return "MISSING"
    for label, lower, upper in PRICE_BUCKETS:
        if value >= lower and value < upper:
            return label
    return "MISSING"


def build_race_key(df: pd.DataFrame) -> pd.Series:
    return (
        df["race_date"].astype(str)
        + "|"
        + df["track"].astype(str)
        + "|R"
        + df["race_no"].astype(str).map(clean_race_no)
    )


def add_model_b_for_race(group: pd.DataFrame, model: str) -> pd.DataFrame:
    out = group.copy()
    known = ~out["is_no_history_for_pricing_v5_2"] & out["projection_gap_v5_2"].notna()
    known_count = int(known.sum())
    no_history_count = int(out["is_no_history_for_pricing_v5_2"].sum())

    out["model"] = model
    out["model_b_gap_used"] = np.nan
    out["model_b_score"] = np.nan
    out["model_b_probability"] = np.nan
    out["model_b_rated_price_research"] = np.nan
    out["model_b_rank_within_race"] = pd.NA
    out["model_b_price_bucket"] = "MISSING"
    out["no_history_treatment_v5_2"] = ""
    out["priced_runner_count"] = 0
    out["no_history_count"] = no_history_count

    if model == "MODEL_B_EXCLUDE_NO_HISTORY":
        out.loc[~known, "no_history_treatment_v5_2"] = "EXCLUDED_NO_HISTORY"
        out.loc[known, "no_history_treatment_v5_2"] = "REAL_PROJECTION_GAP"

        if known_count == 0:
            out["model_notes"] = "no runners with historical projection gap"
            return out

        race_min = out.loc[known, "projection_gap_v5_2"].min()
        out.loc[known, "model_b_gap_used"] = out.loc[known, "projection_gap_v5_2"]
        out.loc[known, "model_b_score"] = (out.loc[known, "model_b_gap_used"] - race_min + 1.0).clip(lower=0.000001).pow(MODEL_B_POWER)
        score_sum = out.loc[known, "model_b_score"].sum()
        out.loc[known, "model_b_probability"] = out.loc[known, "model_b_score"] / score_sum
        out.loc[known, "model_b_rated_price_research"] = 1.0 / out.loc[known, "model_b_probability"]
        out.loc[known, "priced_runner_count"] = known_count
        out.loc[~known, "priced_runner_count"] = known_count
        out["model_notes"] = "no-history runners excluded from probability normalization"
    else:
        if known_count == 0:
            baseline_gap = 0.0
            out["model_b_gap_used"] = baseline_gap
            out["no_history_treatment_v5_2"] = "ALL_RUNNERS_EQUAL_BASELINE_NO_HISTORY"
            out["model_b_score"] = 1.0
            out["model_notes"] = "all runners no-history; equal baseline probability"
        else:
            race_min_known = out.loc[known, "projection_gap_v5_2"].min()
            baseline_gap = race_min_known - BASELINE_GAP_PENALTY
            out.loc[known, "model_b_gap_used"] = out.loc[known, "projection_gap_v5_2"]
            out.loc[~known, "model_b_gap_used"] = baseline_gap
            out.loc[known, "no_history_treatment_v5_2"] = "REAL_PROJECTION_GAP"
            out.loc[~known, "no_history_treatment_v5_2"] = f"BASELINE_GAP_{BASELINE_GAP_PENALTY:.1f}_BELOW_RACE_WORST"
            race_min = out["model_b_gap_used"].min()
            out["model_b_score"] = (out["model_b_gap_used"] - race_min + 1.0).clip(lower=0.000001).pow(MODEL_B_POWER)
            out["model_notes"] = "no-history runners included with conservative race-baseline gap"

        score_sum = out["model_b_score"].sum()
        out["model_b_probability"] = out["model_b_score"] / score_sum
        out["model_b_rated_price_research"] = 1.0 / out["model_b_probability"]
        out["priced_runner_count"] = len(out)

    ranked = out["model_b_probability"].rank(method="first", ascending=False)
    out["model_b_rank_within_race"] = ranked.where(out["model_b_probability"].notna(), pd.NA)
    out["model_b_price_bucket"] = out["model_b_rated_price_research"].apply(price_bucket)
    return out


def summary_row(
    section: str,
    metric: str,
    model: str = "",
    race_key: str = "",
    race_no: object = "",
    race_time: str = "",
    race_class_corrected: str = "",
    value: object = "",
    count: object = "",
    runner_count: object = "",
    priced_runner_count: object = "",
    no_history_count: object = "",
    favourite: str = "",
    favourite_probability: object = "",
    favourite_rated_price: object = "",
    second_probability: object = "",
    third_probability: object = "",
    horse: str = "",
    rank: object = "",
    probability: object = "",
    rated_price: object = "",
    projection_gap: object = "",
    notes: str = "",
) -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "model": model,
        "race_key": race_key,
        "race_no": race_no,
        "race_time": race_time,
        "race_class_corrected": race_class_corrected,
        "value": value,
        "count": count,
        "runner_count": runner_count,
        "priced_runner_count": priced_runner_count,
        "no_history_count": no_history_count,
        "favourite": favourite,
        "favourite_probability": favourite_probability,
        "favourite_rated_price": favourite_rated_price,
        "second_probability": second_probability,
        "third_probability": third_probability,
        "horse": horse,
        "rank": rank,
        "probability": probability,
        "rated_price": rated_price,
        "projection_gap": projection_gap,
        "notes": notes,
    }


def model_recommendation(audit: pd.DataFrame) -> tuple[str, str]:
    include = audit[audit["model"].eq("MODEL_B_INCLUDE_BASELINE")]
    exclude = audit[audit["model"].eq("MODEL_B_EXCLUDE_NO_HISTORY")]

    baseline_rows = include[include["is_no_history_for_pricing_v5_2"]]
    no_history_count = len(baseline_rows)
    baseline_avg_probability = safe_mean(baseline_rows["model_b_probability"])
    baseline_avg_price = safe_mean(baseline_rows["model_b_rated_price_research"])
    exclude_unpriced_count = int(exclude["model_b_probability"].isna().sum())

    if no_history_count == 0:
        return "MODEL_B_EXCLUDE_NO_HISTORY", "no no-history runners in current fields; exclusion and baseline are equivalent"

    if baseline_avg_probability <= 0.08 and baseline_avg_price >= 12.0:
        return (
            "MODEL_B_INCLUDE_BASELINE",
            (
                f"recommended for field completeness: {no_history_count} no-history runners get conservative "
                f"baseline probability avg={baseline_avg_probability:.4f}, price avg={baseline_avg_price:.2f}; "
                f"exclude model leaves {exclude_unpriced_count} live runners unpriced"
            ),
        )

    return (
        "MODEL_B_EXCLUDE_NO_HISTORY",
        (
            f"baseline too influential for a conservative placeholder: no-history avg probability="
            f"{baseline_avg_probability:.4f}, avg price={baseline_avg_price:.2f}; keep unpriced until projection history exists"
        ),
    )


def main() -> None:
    print("=" * 90)
    print("EDGEIQ CURRENT FIELD RATED PRICE AUDIT V5.2 - RESEARCH ONLY")
    print("=" * 90)

    if not SRC.exists():
        raise FileNotFoundError(f"Missing input: {SRC}")

    df = pd.read_csv(SRC, dtype=str, keep_default_na=False, low_memory=False)

    required = {
        "race_date",
        "track",
        "race_no",
        "race_time",
        "current_field_size_v5_2",
        "horse",
        "corrected_race_class_v5_1",
        "history_match_status_v5_2",
        "starts_found_v5_2",
        "projected_rating_v5_2",
        "race_target_rating_v5_2",
        "target_status_v5_2",
        "projection_gap_v5_2",
        "projection_confidence_v5_2",
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing required projection V5.2 columns: {missing}")

    rows_loaded = len(df)
    df["race_no"] = df["race_no"].map(clean_race_no)
    df["race_context_key_v5_2"] = build_race_key(df)
    df["current_field_size_v5_2"] = pd.to_numeric(df["current_field_size_v5_2"], errors="coerce")
    df["starts_found_v5_2"] = pd.to_numeric(df["starts_found_v5_2"], errors="coerce").fillna(0).astype(int)
    for column in ["projection_gap_v5_2", "projected_rating_v5_2", "race_target_rating_v5_2"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["runner_count"] = df.groupby("race_context_key_v5_2")["horse"].transform("size")
    df["is_no_history_for_pricing_v5_2"] = (
        df["history_match_status_v5_2"].eq("NO_HISTORY")
        | df["starts_found_v5_2"].eq(0)
        | df["projection_gap_v5_2"].isna()
    )

    model_frames: list[pd.DataFrame] = []
    for model in MODELS:
        model_frames.append(
            pd.concat(
                [
                    add_model_b_for_race(group, model)
                    for _, group in df.groupby("race_context_key_v5_2", dropna=False)
                ],
                ignore_index=True,
            )
        )

    audit = pd.concat(model_frames, ignore_index=True)
    audit["model_b_probability_sum_by_race"] = audit.groupby(["model", "race_context_key_v5_2"])["model_b_probability"].transform("sum")
    audit["built_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for column in ["model_b_gap_used", "model_b_score", "model_b_probability", "model_b_rated_price_research"]:
        audit[column] = pd.to_numeric(audit[column], errors="coerce")

    output_cols = [
        "model",
        "race_context_key_v5_2",
        "race_date",
        "track",
        "race_no",
        "race_time",
        "corrected_race_class_v5_1",
        "current_field_size_v5_2",
        "runner_count",
        "priced_runner_count",
        "no_history_count",
        "horse_no",
        "saddlecloth",
        "horse",
        "history_match_status_v5_2",
        "starts_found_v5_2",
        "is_no_history_for_pricing_v5_2",
        "projection_gap_v5_2",
        "model_b_gap_used",
        "no_history_treatment_v5_2",
        "model_b_score",
        "model_b_probability",
        "model_b_probability_sum_by_race",
        "model_b_rated_price_research",
        "model_b_rank_within_race",
        "model_b_price_bucket",
        "projected_rating_v5_2",
        "race_target_rating_v5_2",
        "target_status_v5_2",
        "projection_confidence_v5_2",
        "model_notes",
        "built_at",
    ]
    output_cols = [column for column in output_cols if column in audit.columns]
    audit.to_csv(OUT, index=False, columns=output_cols)

    summary_rows: list[dict[str, object]] = [
        summary_row("overall", "rows_loaded", value=rows_loaded),
        summary_row("overall", "race_count", value=df["race_context_key_v5_2"].nunique()),
        summary_row("overall", "runner_count", value=len(df)),
        summary_row("overall", "no_history_runner_count", value=int(df["is_no_history_for_pricing_v5_2"].sum())),
        summary_row("overall", "model_b_power", value=MODEL_B_POWER),
        summary_row("overall", "baseline_gap_penalty", value=BASELINE_GAP_PENALTY),
    ]

    for model, model_df in audit.groupby("model", dropna=False):
        probability_sums = model_df.groupby("race_context_key_v5_2", dropna=False)["model_b_probability"].sum(min_count=1)
        summary_rows.extend(
            [
                summary_row("probability_integrity", "probability_sum_min", model=model, value=fmt(probability_sums.min())),
                summary_row("probability_integrity", "probability_sum_max", model=model, value=fmt(probability_sums.max())),
                summary_row("probability_integrity", "probability_sum_avg", model=model, value=fmt(probability_sums.mean())),
            ]
        )

        for race_key, race in model_df.groupby("race_context_key_v5_2", dropna=False):
            probability_sum = pd.to_numeric(race["model_b_probability"], errors="coerce").sum()
            race_sorted = race.sort_values(["model_b_probability", "saddlecloth"], ascending=[False, True], na_position="last")
            priced = race_sorted[race_sorted["model_b_probability"].notna()]
            favorite = priced.iloc[0] if len(priced) >= 1 else None
            second = priced.iloc[1] if len(priced) >= 2 else None
            third = priced.iloc[2] if len(priced) >= 3 else None

            summary_rows.append(
                summary_row(
                    "probability_sum_per_race",
                    "probability_sum",
                    model=model,
                    race_key=race_key,
                    race_no=race["race_no"].iloc[0],
                    race_time=race["race_time"].iloc[0],
                    race_class_corrected=race["corrected_race_class_v5_1"].iloc[0],
                    value=fmt(probability_sum),
                    runner_count=int(race["runner_count"].iloc[0]),
                    priced_runner_count=int(race["priced_runner_count"].iloc[0]),
                    no_history_count=int(race["no_history_count"].iloc[0]),
                )
            )

            summary_rows.append(
                summary_row(
                    "race_level_output",
                    "race_pricing_snapshot",
                    model=model,
                    race_key=race_key,
                    race_no=race["race_no"].iloc[0],
                    race_time=race["race_time"].iloc[0],
                    race_class_corrected=race["corrected_race_class_v5_1"].iloc[0],
                    runner_count=int(race["runner_count"].iloc[0]),
                    priced_runner_count=int(race["priced_runner_count"].iloc[0]),
                    no_history_count=int(race["no_history_count"].iloc[0]),
                    favourite="" if favorite is None else favorite["horse"],
                    favourite_probability="" if favorite is None else fmt(favorite["model_b_probability"]),
                    favourite_rated_price="" if favorite is None else fmt2(favorite["model_b_rated_price_research"]),
                    second_probability="" if second is None else fmt(second["model_b_probability"]),
                    third_probability="" if third is None else fmt(third["model_b_probability"]),
                    notes="MODEL_B power curve; research only, not production price",
                )
            )

            for _, row in priced.head(3).iterrows():
                summary_rows.append(
                    summary_row(
                        "top_rated_runners_by_race",
                        "top_rated_runner",
                        model=model,
                        race_key=race_key,
                        race_no=row["race_no"],
                        race_time=row["race_time"],
                        race_class_corrected=row["corrected_race_class_v5_1"],
                        horse=row["horse"],
                        rank=int(row["model_b_rank_within_race"]),
                        probability=fmt(row["model_b_probability"]),
                        rated_price=fmt2(row["model_b_rated_price_research"]),
                        projection_gap=fmt2(row["projection_gap_v5_2"]),
                        notes=row["no_history_treatment_v5_2"],
                    )
                )

        priced_all = model_df[model_df["model_b_rated_price_research"].notna()].copy()
        summary_rows.extend(
            [
                summary_row("price_sanity", "rated_price_lt_1_20", model=model, count=int((priced_all["model_b_rated_price_research"] < 1.20).sum())),
                summary_row("price_sanity", "rated_price_lt_1_50", model=model, count=int((priced_all["model_b_rated_price_research"] < 1.50).sum())),
                summary_row("price_sanity", "rated_price_gt_50", model=model, count=int((priced_all["model_b_rated_price_research"] > 50).sum())),
                summary_row("price_sanity", "rated_price_gt_100", model=model, count=int((priced_all["model_b_rated_price_research"] > 100).sum())),
            ]
        )

        if model == "MODEL_B_INCLUDE_BASELINE":
            baseline = model_df[model_df["is_no_history_for_pricing_v5_2"]].copy()
            summary_rows.extend(
                [
                    summary_row("no_history_treatment", "baseline_runner_count", model=model, count=len(baseline)),
                    summary_row("no_history_treatment", "baseline_avg_probability", model=model, value=fmt(safe_mean(baseline["model_b_probability"]))),
                    summary_row("no_history_treatment", "baseline_avg_price", model=model, value=fmt2(safe_mean(baseline["model_b_rated_price_research"]))),
                ]
            )
        else:
            excluded = model_df[model_df["is_no_history_for_pricing_v5_2"]]
            summary_rows.append(summary_row("no_history_treatment", "excluded_no_history_runner_count", model=model, count=len(excluded)))

    recommended_model, recommendation_notes = model_recommendation(audit)
    summary_rows.append(
        summary_row(
            "recommendation",
            "preferred_research_treatment",
            model=recommended_model,
            value=recommended_model,
            notes=recommendation_notes,
        )
    )

    summary = pd.DataFrame(summary_rows)
    summary["built_at"] = audit["built_at"].iloc[0]
    summary.to_csv(SUMMARY, index=False)

    print(f"wrote: {OUT}")
    print(f"wrote: {SUMMARY}")
    print()
    print(summary[summary["section"].isin(["overall", "probability_integrity", "price_sanity", "no_history_treatment", "recommendation"])].to_string(index=False))
    print()
    print(summary[summary["section"].eq("race_level_output")].to_string(index=False))
    print()
    print(summary[summary["section"].eq("top_rated_runners_by_race")].head(24).to_string(index=False))
    print("=" * 90)


if __name__ == "__main__":
    main()
