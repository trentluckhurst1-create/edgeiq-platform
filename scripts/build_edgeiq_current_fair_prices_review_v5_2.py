from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PROJECTION = DATA / "edgeiq_current_field_projection_v5_2.csv"
PRICE_AUDIT = DATA / "edgeiq_current_field_rated_price_audit_v5_2.csv"

OUT = DATA / "edgeiq_current_fair_prices_review_v5_2.csv"
AUDIT = DATA / "edgeiq_current_fair_prices_review_v5_2_audit.csv"

MODEL = "MODEL_B_EXCLUDE_NO_HISTORY"


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


def review_status(row: pd.Series) -> str:
    if pd.isna(row.get("model_b_probability")) or pd.isna(row.get("model_b_rated_price_research")):
        return "NO_PRICE"

    treatment = norm(row.get("no_history_treatment_v5_2", ""))
    if "BASELINE" in treatment:
        return "BASELINE_NO_HISTORY"
    if treatment == "REAL_PROJECTION_GAP":
        return "RATED_HISTORY"
    return "NO_PRICE"


def audit_row(
    section: str,
    metric: str,
    value: object = "",
    count: object = "",
    race_key: str = "",
    race_no: object = "",
    race_time: str = "",
    race_class_corrected: str = "",
    horse: str = "",
    rank: object = "",
    probability: object = "",
    rated_price: object = "",
    status: str = "",
    notes: str = "",
) -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "count": count,
        "race_key": race_key,
        "race_no": race_no,
        "race_time": race_time,
        "race_class_corrected": race_class_corrected,
        "horse": horse,
        "rank": rank,
        "probability": probability,
        "rated_price": rated_price,
        "rated_price_status_v5_2_review": status,
        "notes": notes,
    }


def race_sort_key(value: object) -> int:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return 999
    return int(parsed)


def main() -> None:
    print("=" * 90)
    print("EDGEIQ CURRENT FAIR PRICES REVIEW V5.2 - REVIEW ONLY")
    print("=" * 90)

    for path in [PROJECTION, PRICE_AUDIT]:
        if not path.exists():
            raise FileNotFoundError(f"Missing input: {path}")

    projection = pd.read_csv(PROJECTION, dtype=str, keep_default_na=False, low_memory=False)
    price_audit = pd.read_csv(PRICE_AUDIT, dtype=str, keep_default_na=False, low_memory=False)

    projection_required = {
        "race_date",
        "track",
        "race_no",
        "race_time",
        "distance",
        "corrected_race_class_v5_1",
        "horse",
        "horse_key",
        "saddlecloth",
        "barrier",
        "jockey",
        "trainer",
        "projected_rating_v5_2",
        "race_target_rating_v5_2",
        "projection_gap_v5_2",
        "projection_band_v5_2",
        "projection_confidence_v5_2",
        "current_field_size_v5_2",
    }
    price_required = {
        "model",
        "race_context_key_v5_2",
        "race_date",
        "track",
        "race_no",
        "horse",
        "saddlecloth",
        "priced_runner_count",
        "no_history_count",
        "no_history_treatment_v5_2",
        "model_b_probability",
        "model_b_rated_price_research",
        "model_b_rank_within_race",
    }

    missing = {
        "projection": sorted(projection_required.difference(projection.columns)),
        "price_audit": sorted(price_required.difference(price_audit.columns)),
    }
    missing = {name: columns for name, columns in missing.items() if columns}
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    projection["race_no"] = projection["race_no"].map(clean_race_no)
    price_audit["race_no"] = price_audit["race_no"].map(clean_race_no)

    prices = price_audit[price_audit["model"].eq(MODEL)].copy()

    join_keys = ["race_date", "track", "race_no", "saddlecloth", "horse"]
    duplicate_prices = int(prices.duplicated(join_keys).sum())
    if duplicate_prices:
        raise ValueError(f"Duplicate MODEL_B_INCLUDE_BASELINE price rows on join keys: {duplicate_prices}")

    price_keep = prices[
        [
            *join_keys,
            "race_context_key_v5_2",
            "priced_runner_count",
            "no_history_count",
            "no_history_treatment_v5_2",
            "model_b_probability",
            "model_b_rated_price_research",
            "model_b_rank_within_race",
        ]
    ].copy()

    review = projection.merge(price_keep, on=join_keys, how="left", validate="one_to_one")

    review["model_b_probability"] = pd.to_numeric(review["model_b_probability"], errors="coerce")
    review["model_b_rated_price_research"] = pd.to_numeric(review["model_b_rated_price_research"], errors="coerce")
    review["model_b_rank_within_race"] = pd.to_numeric(review["model_b_rank_within_race"], errors="coerce")
    review["current_field_size_v5_2"] = pd.to_numeric(review["current_field_size_v5_2"], errors="coerce")

    review["rated_price_status_v5_2_review"] = review.apply(review_status, axis=1)
    review["is_scratched"] = "FALSE"
    review["field_size"] = review["current_field_size_v5_2"]
    review["race_class_corrected"] = review["corrected_race_class_v5_1"]
    review["rated_probability_v5_2_review"] = review["model_b_probability"].round(6)
    review["rated_price_v5_2_review"] = review["model_b_rated_price_research"].round(2)
    review["price_rank_in_race_v5_2"] = review["model_b_rank_within_race"].astype("Int64")

    numeric_projection_cols = [
        "projected_rating_v5_2",
        "race_target_rating_v5_2",
        "projection_gap_v5_2",
    ]
    for column in numeric_projection_cols:
        review[column] = pd.to_numeric(review[column], errors="coerce").round(2)

    review["built_at_fair_price_review_v5_2"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    output_cols = [
        "race_date",
        "track",
        "race_no",
        "race_time",
        "distance",
        "race_class_corrected",
        "horse",
        "horse_key",
        "saddlecloth",
        "barrier",
        "jockey",
        "trainer",
        "is_scratched",
        "projected_rating_v5_2",
        "race_target_rating_v5_2",
        "projection_gap_v5_2",
        "projection_band_v5_2",
        "projection_confidence_v5_2",
        "rated_probability_v5_2_review",
        "rated_price_v5_2_review",
        "rated_price_status_v5_2_review",
        "price_rank_in_race_v5_2",
        "field_size",
        "priced_runner_count",
        "no_history_count",
    ]
    review.to_csv(OUT, index=False, columns=output_cols)

    audit_rows: list[dict[str, object]] = [
        audit_row("overall", "projection_rows_loaded", len(projection)),
        audit_row("overall", "model_b_exclude_no_history_rows_loaded", len(prices)),
        audit_row("overall", "rows_written", len(review)),
        audit_row("overall", "races", review[["race_date", "track", "race_no"]].drop_duplicates().shape[0]),
        audit_row("overall", "runners", len(review)),
        audit_row("overall", "missing_price_rows", int(review["rated_price_status_v5_2_review"].eq("NO_PRICE").sum())),
        audit_row(
            "overall",
            "is_scratched_source_note",
            notes="is_scratched is FALSE for every row because current_field_projection_v5_2 excluded scratched runners before this review file",
        ),
    ]

    probability_sums = review.groupby(["race_date", "track", "race_no"], dropna=False)["rated_probability_v5_2_review"].sum(min_count=1)
    audit_rows.extend(
        [
            audit_row("probability_integrity", "probability_sum_min", fmt(probability_sums.min())),
            audit_row("probability_integrity", "probability_sum_max", fmt(probability_sums.max())),
            audit_row("probability_integrity", "probability_sum_avg", fmt(probability_sums.mean())),
        ]
    )

    race_table = (
        review.sort_values(["race_date", "track", "race_no", "rated_probability_v5_2_review"], ascending=[True, True, True, False])
        .groupby(["race_date", "track", "race_no"], dropna=False)
        .first()
        .reset_index()
    )
    race_table["race_sort"] = race_table["race_no"].map(race_sort_key)
    for _, row in race_table.sort_values(["race_date", "track", "race_sort"]).iterrows():
        audit_rows.append(
            audit_row(
                "favourite_per_race",
                "favourite",
                race_key=row.get("race_context_key_v5_2", ""),
                race_no=row["race_no"],
                race_time=row["race_time"],
                race_class_corrected=row["race_class_corrected"],
                horse=row["horse"],
                rank=row["price_rank_in_race_v5_2"],
                probability=fmt(row["rated_probability_v5_2_review"]),
                rated_price=fmt2(row["rated_price_v5_2_review"]),
                status=row["rated_price_status_v5_2_review"],
                notes=f"field_size={row['field_size']}; priced_runner_count={row['priced_runner_count']}; no_history_count={row['no_history_count']}",
            )
        )

    for status, count in review["rated_price_status_v5_2_review"].value_counts().sort_index().items():
        audit_rows.append(audit_row("rated_price_status_counts", status, count=int(count), status=status))

    audit_rows.extend(
        [
            audit_row("price_sanity", "rated_price_lt_1_50", count=int((review["rated_price_v5_2_review"] < 1.50).sum())),
            audit_row("price_sanity", "rated_price_gt_100", count=int((review["rated_price_v5_2_review"] > 100).sum())),
        ]
    )

    top30 = review.sort_values("rated_probability_v5_2_review", ascending=False, na_position="last").head(30)
    for rank, (_, row) in enumerate(top30.iterrows(), start=1):
        audit_rows.append(
            audit_row(
                "top_30_rated_runners",
                "top_rated_runner",
                count=rank,
                race_no=row["race_no"],
                race_time=row["race_time"],
                race_class_corrected=row["race_class_corrected"],
                horse=row["horse"],
                rank=row["price_rank_in_race_v5_2"],
                probability=fmt(row["rated_probability_v5_2_review"]),
                rated_price=fmt2(row["rated_price_v5_2_review"]),
                status=row["rated_price_status_v5_2_review"],
                notes=f"gap={fmt2(row['projection_gap_v5_2'])}; band={row['projection_band_v5_2']}; confidence={row['projection_confidence_v5_2']}",
            )
        )

    audit = pd.DataFrame(audit_rows)
    audit["built_at"] = review["built_at_fair_price_review_v5_2"].iloc[0]
    audit.to_csv(AUDIT, index=False)

    print(f"wrote: {OUT}")
    print(f"wrote: {AUDIT}")
    print()
    print(audit[audit["section"].isin(["overall", "probability_integrity", "rated_price_status_counts", "price_sanity"])].to_string(index=False))
    print()
    print(audit[audit["section"].eq("favourite_per_race")].to_string(index=False))
    print()
    print(audit[audit["section"].eq("top_30_rated_runners")].head(30).to_string(index=False))
    print("=" * 90)


if __name__ == "__main__":
    main()

