from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_projection_v5_1.csv"
OUT = DATA / "edgeiq_rated_price_audit_v5_1.csv"
SUMMARY = DATA / "edgeiq_rated_price_audit_v5_1_summary.csv"

RACE_KEYS = [
    "race_date",
    "track",
    "distance",
    "race_class_clean_v5_1",
    "condition_group_v5_1",
    "real_field_size",
    "source_file",
]

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

MODELS = {
    "MODEL_A": {
        "description": "Soft exponential score = exp((gap - race_max_gap) / 8.0)",
        "probability_col": "model_a_probability",
        "price_col": "model_a_rated_price_research",
        "rank_col": "model_a_rank_within_race",
    },
    "MODEL_B": {
        "description": "Power score = (gap - race_min_gap + 1.0) ^ 1.35",
        "probability_col": "model_b_probability",
        "price_col": "model_b_rated_price_research",
        "rank_col": "model_b_rank_within_race",
    },
    "MODEL_C": {
        "description": "Logistic score = sigmoid((gap - race_mean_gap) / 4.0)",
        "probability_col": "model_c_probability",
        "price_col": "model_c_rated_price_research",
        "rank_col": "model_c_rank_within_race",
    },
}

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


def fmt(value: object) -> str:
    if pd.isna(value):
        return ""
    return f"{float(value):.6f}"


def fmt2(value: object) -> str:
    if pd.isna(value):
        return ""
    return f"{float(value):.2f}"


def summary_row(
    section: str,
    metric: str,
    model: str = "",
    race_class: str = "",
    price_bucket: str = "",
    rank: object = "",
    value: object = "",
    count: object = "",
    average_probability: object = "",
    average_price: object = "",
    win_rate: object = "",
    average_projection_gap: object = "",
    score: object = "",
    notes: str = "",
) -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "model": model,
        "race_class": race_class,
        "price_bucket": price_bucket,
        "rank": rank,
        "value": value,
        "count": count,
        "average_probability": average_probability,
        "average_price": average_price,
        "win_rate": win_rate,
        "average_projection_gap": average_projection_gap,
        "score": score,
        "notes": notes,
    }


def safe_mean(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return float("nan")
    return float(values.mean())


def sigmoid(values: pd.Series) -> pd.Series:
    clipped = values.clip(lower=-50, upper=50)
    return 1.0 / (1.0 + np.exp(-clipped))


def price_bucket(price: object) -> str:
    value = pd.to_numeric(price, errors="coerce")
    if pd.isna(value):
        return "MISSING"
    for label, lower, upper in PRICE_BUCKETS:
        if value >= lower and value < upper:
            return label
    return "MISSING"


def add_model_probabilities(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    grouped = out.groupby("race_context_key", dropna=False)

    race_min = grouped["projection_gap_v5_1"].transform("min")
    race_max = grouped["projection_gap_v5_1"].transform("max")
    race_mean = grouped["projection_gap_v5_1"].transform("mean")

    out["projection_positive_score"] = (out["projection_gap_v5_1"] - race_min + 1.0).clip(lower=0.000001)
    out["projection_share"] = out["projection_positive_score"] / out.groupby("race_context_key")["projection_positive_score"].transform("sum")

    out["model_a_score"] = np.exp(((out["projection_gap_v5_1"] - race_max) / 8.0).clip(lower=-50, upper=50))
    out["model_b_score"] = out["projection_positive_score"].pow(1.35)
    out["model_c_score"] = sigmoid((out["projection_gap_v5_1"] - race_mean) / 4.0)

    for model_key, config in MODELS.items():
        score_col = model_key.lower() + "_score"
        probability_col = config["probability_col"]
        price_col = config["price_col"]
        rank_col = config["rank_col"]

        score_sum = out.groupby("race_context_key")[score_col].transform("sum")
        out[probability_col] = out[score_col] / score_sum
        out[price_col] = 1.0 / out[probability_col]
        out[rank_col] = out.groupby("race_context_key")[probability_col].rank(method="first", ascending=False).astype(int)
        out[f"{model_key.lower()}_price_bucket"] = out[price_col].apply(price_bucket)

    return out


def model_probability_integrity(df: pd.DataFrame, probability_col: str) -> pd.DataFrame:
    return df.groupby("race_context_key", dropna=False)[probability_col].sum().reset_index(name="probability_sum")


def model_score(
    probability_min: float,
    probability_max: float,
    probability_average: float,
    under_101: int,
    under_120: int,
    over_100: int,
    over_200: int,
    favorite_prob_gap: float,
    favorite_gap_delta: float,
    row_count: int,
) -> tuple[float, str]:
    probability_error = (
        abs(probability_min - 1.0)
        + abs(probability_max - 1.0)
        + abs(probability_average - 1.0)
    )
    probability_integrity_score = max(0.0, 40.0 - (probability_error * 200.0))

    bad_price_load = (
        (under_101 * 1.00)
        + (under_120 * 0.50)
        + (over_100 * 0.35)
        + (over_200 * 0.55)
    ) / max(row_count, 1)
    price_stability_score = max(0.0, 35.0 * (1.0 - min(1.0, bad_price_load)))

    probability_separation_score = min(17.0, max(0.0, favorite_prob_gap * 60.0))
    gap_separation_score = min(8.0, max(0.0, favorite_gap_delta * 0.7))
    separation_score = probability_separation_score + gap_separation_score

    total = probability_integrity_score + price_stability_score + separation_score
    notes = (
        f"probability_integrity={probability_integrity_score:.2f}; "
        f"price_stability={price_stability_score:.2f}; "
        f"favorite_separation={separation_score:.2f}; "
        "research score only, no final model selected"
    )
    return round(total, 2), notes


def main() -> None:
    print("=" * 90)
    print("EDGEIQ RATED PRICE AUDIT V5.1 - RESEARCH ONLY")
    print("=" * 90)

    if not SRC.exists():
        raise FileNotFoundError(f"Missing input: {SRC}")

    df = pd.read_csv(SRC, dtype=str, keep_default_na=False, low_memory=False)

    required = {
        *RACE_KEYS,
        "horse",
        "finish_position",
        "projection_gap_v5_1",
        "projection_status_v5_1",
        "race_target_rating_v5_1",
        "performance_rating_v5_1",
        "race_class_family_v3_3",
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing required projection columns: {missing}")

    rows_loaded = len(df)
    projected = df[df["projection_status_v5_1"].eq("PROJECTED")].copy()
    no_target_rows = rows_loaded - len(projected)

    projected["projection_gap_v5_1"] = pd.to_numeric(projected["projection_gap_v5_1"], errors="coerce")
    projected["finish_position"] = pd.to_numeric(projected["finish_position"], errors="coerce")
    projected["performance_rating_v5_1"] = pd.to_numeric(projected["performance_rating_v5_1"], errors="coerce")
    projected["race_target_rating_v5_1"] = pd.to_numeric(projected["race_target_rating_v5_1"], errors="coerce")
    projected["distance"] = pd.to_numeric(projected["distance"], errors="coerce")
    projected["real_field_size"] = pd.to_numeric(projected["real_field_size"], errors="coerce")

    projected = projected[projected["projection_gap_v5_1"].notna()].copy()
    projected["race_class_clean_v5_1"] = projected["race_class_clean_v5_1"].map(norm)

    projected["race_context_key"] = (
        projected["race_date"].astype(str)
        + "|"
        + projected["track"].astype(str)
        + "|"
        + projected["distance"].round(2).astype(str)
        + "|"
        + projected["race_class_clean_v5_1"].astype(str)
        + "|"
        + projected["condition_group_v5_1"].astype(str)
        + "|"
        + projected["real_field_size"].round(2).astype(str)
        + "|"
        + projected["source_file"].astype(str)
    )

    projected["runner_count"] = projected.groupby("race_context_key")["horse"].transform("size")
    projected["gap_rank_within_race"] = projected.groupby("race_context_key")["projection_gap_v5_1"].rank(method="first", ascending=False).astype(int)
    projected["actual_win"] = projected["finish_position"].eq(1).astype(int)

    projected = add_model_probabilities(projected)
    projected["built_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    output_cols = [
        "race_context_key",
        "race_date",
        "track",
        "distance",
        "race_class_clean_v5_1",
        "race_class_family_v3_3",
        "condition_group_v5_1",
        "real_field_size",
        "source_file",
        "horse",
        "finish_position",
        "actual_win",
        "performance_rating_v5_1",
        "race_target_rating_v5_1",
        "projection_gap_v5_1",
        "gap_rank_within_race",
        "runner_count",
        "projection_positive_score",
        "projection_share",
        "model_a_probability",
        "model_a_rated_price_research",
        "model_a_rank_within_race",
        "model_a_price_bucket",
        "model_b_probability",
        "model_b_rated_price_research",
        "model_b_rank_within_race",
        "model_b_price_bucket",
        "model_c_probability",
        "model_c_rated_price_research",
        "model_c_rank_within_race",
        "model_c_price_bucket",
        "built_at",
    ]
    projected.to_csv(OUT, index=False, columns=output_cols)

    context_counts = projected.drop_duplicates("race_context_key")["runner_count"]
    summary_rows: list[dict[str, object]] = [
        summary_row("overall", "rows_loaded", value=rows_loaded),
        summary_row("overall", "projected_rows_used", value=len(projected)),
        summary_row("overall", "no_target_rows_excluded", value=no_target_rows),
        summary_row("overall", "race_contexts", value=projected["race_context_key"].nunique()),
        summary_row("overall", "single_runner_contexts", value=int(context_counts.eq(1).sum())),
        summary_row("overall", "multi_runner_contexts", value=int(context_counts.gt(1).sum())),
        summary_row("overall", "average_runner_count", value=fmt2(context_counts.mean())),
        summary_row("overall", "median_runner_count", value=fmt2(context_counts.median())),
    ]

    model_scores: dict[str, float] = {}

    for model_key, config in MODELS.items():
        probability_col = config["probability_col"]
        price_col = config["price_col"]
        rank_col = config["rank_col"]

        probability_sums = model_probability_integrity(projected, probability_col)
        probability_min = float(probability_sums["probability_sum"].min())
        probability_max = float(probability_sums["probability_sum"].max())
        probability_average = float(probability_sums["probability_sum"].mean())

        prices = pd.to_numeric(projected[price_col], errors="coerce")
        under_101 = int((prices < 1.01).sum())
        under_120 = int((prices < 1.20).sum())
        over_100 = int((prices > 100).sum())
        over_200 = int((prices > 200).sum())

        top_three = projected[projected[rank_col].isin([1, 2, 3])].copy()
        top_one = top_three[top_three[rank_col].eq(1)]
        top_two = top_three[top_three[rank_col].eq(2)]
        top_three_rank = top_three[top_three[rank_col].eq(3)]

        top_one_prob = safe_mean(top_one[probability_col])
        top_two_prob = safe_mean(top_two[probability_col])
        favorite_prob_gap = top_one_prob - top_two_prob if pd.notna(top_one_prob) and pd.notna(top_two_prob) else 0.0
        favorite_gap_delta = safe_mean(top_one["projection_gap_v5_1"]) - safe_mean(top_two["projection_gap_v5_1"])
        if pd.isna(favorite_gap_delta):
            favorite_gap_delta = 0.0

        score, score_notes = model_score(
            probability_min=probability_min,
            probability_max=probability_max,
            probability_average=probability_average,
            under_101=under_101,
            under_120=under_120,
            over_100=over_100,
            over_200=over_200,
            favorite_prob_gap=favorite_prob_gap,
            favorite_gap_delta=float(favorite_gap_delta),
            row_count=len(projected),
        )
        model_scores[model_key] = score

        summary_rows.extend(
            [
                summary_row("model_description", "curve", model=model_key, notes=config["description"]),
                summary_row("probability_integrity", "sum_probability_min", model=model_key, value=fmt(probability_min)),
                summary_row("probability_integrity", "sum_probability_max", model=model_key, value=fmt(probability_max)),
                summary_row("probability_integrity", "sum_probability_average", model=model_key, value=fmt(probability_average)),
                summary_row("price_sanity", "rated_price_lt_1_01", model=model_key, count=under_101),
                summary_row("price_sanity", "rated_price_lt_1_20", model=model_key, count=under_120),
                summary_row("price_sanity", "rated_price_gt_100", model=model_key, count=over_100),
                summary_row("price_sanity", "rated_price_gt_200", model=model_key, count=over_200),
                summary_row("research_recommendation", f"{model_key}_score", model=model_key, score=f"{score:.2f}", notes=score_notes),
            ]
        )

        for rank_value, rank_rows in [(1, top_one), (2, top_two), (3, top_three_rank)]:
            count = len(rank_rows)
            win_rate = safe_mean(rank_rows["actual_win"]) if count else float("nan")
            summary_rows.append(
                summary_row(
                    "favourite_performance",
                    "rated_rank_performance",
                    model=model_key,
                    rank=rank_value,
                    count=count,
                    win_rate=fmt(win_rate),
                    average_probability=fmt(safe_mean(rank_rows[probability_col])),
                    average_price=fmt2(safe_mean(rank_rows[price_col])),
                    average_projection_gap=fmt2(safe_mean(rank_rows["projection_gap_v5_1"])),
                    notes=f"rank {rank_value} by {model_key} probability",
                )
            )

        favourites = projected[projected[rank_col].eq(1)].copy()
        for race_class in KEY_CLASSES:
            class_favs = favourites[favourites["race_class_clean_v5_1"].eq(race_class)]
            summary_rows.append(
                summary_row(
                    "class_breakdown_favourites",
                    "average_favourite_probability_price",
                    model=model_key,
                    race_class=race_class,
                    count=len(class_favs),
                    average_probability=fmt(safe_mean(class_favs[probability_col])),
                    average_price=fmt2(safe_mean(class_favs[price_col])),
                )
            )

        for bucket_label, _, _ in PRICE_BUCKETS:
            bucket_count = int(projected[f"{model_key.lower()}_price_bucket"].eq(bucket_label).sum())
            summary_rows.append(
                summary_row(
                    "price_distribution",
                    "rated_price_bucket_count",
                    model=model_key,
                    price_bucket=bucket_label,
                    count=bucket_count,
                )
            )

    score_order = sorted(model_scores.items(), key=lambda item: item[1], reverse=True)
    summary_rows.append(
        summary_row(
            "research_recommendation",
            "score_order_research_only",
            value=" > ".join(f"{model} {score:.2f}" for model, score in score_order),
            notes="Do not select final model automatically; inspect probability and price behavior first.",
        )
    )

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(SUMMARY, index=False)

    print(f"wrote: {OUT}")
    print(f"wrote: {SUMMARY}")
    print()
    print(summary[summary["section"].isin(["overall", "probability_integrity", "price_sanity", "favourite_performance", "research_recommendation"])].to_string(index=False))
    print("=" * 90)


if __name__ == "__main__":
    main()
