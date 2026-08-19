from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT = DATA / "edgeiq_price_truth_history_v1.csv"
HEALTH = DATA / "edgeiq_price_truth_history_v1_health.csv"
SUMMARY = DATA / "edgeiq_price_truth_history_v1_health_summary.csv"

RESULT_COLUMNS = [
    "result_status",
    "finish_position",
    "won",
    "starting_price",
    "closing_price",
    "settlement_source",
]

REQUIRED_COLUMNS = {
    "snapshot_timestamp",
    "race_date",
    "track",
    "race_no",
    "horse",
    "horse_key",
    "barrier",
    "is_scratched",
    "edgeiq_price",
    "edgeiq_probability",
    "sportsbet_price",
    "sportsbet_implied_probability",
    "market_percentage_context",
    "overlay_pct",
    "projection_score",
    "race_target",
    "history_bucket",
    "price_role",
    "quality_class",
    "discipline_class",
    "warning_flags",
    *RESULT_COLUMNS,
}

EXPECTED_RACES_PER_SNAPSHOT = 8
EXPECTED_RUNNERS_PER_SNAPSHOT = 87


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def has_text(value: object) -> bool:
    if value is None or pd.isna(value):
        return False
    text = str(value).strip()
    return bool(text) and text.lower() != "nan"


def norm(value: object) -> str:
    if not has_text(value):
        return ""
    return " ".join(str(value).upper().strip().split())


def clean_race_no(value: object) -> str:
    text = str(value).strip()
    return text[:-2] if text.endswith(".0") else text


def to_number(value: object) -> float:
    return pd.to_numeric(value, errors="coerce")


def bool_text(value: bool) -> str:
    return "TRUE" if bool(value) else "FALSE"


def load_history() -> pd.DataFrame:
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing price truth history input: {INPUT}")

    df = pd.read_csv(INPUT, dtype=str, keep_default_na=False, low_memory=False)
    missing = sorted(REQUIRED_COLUMNS.difference(df.columns))
    if missing:
        raise ValueError(f"History file missing required columns: {missing}")
    return df


def duplicate_key_series(df: pd.DataFrame) -> pd.Series:
    return (
        df["snapshot_timestamp"].astype(str).str.strip()
        + "|"
        + df["track"].map(norm)
        + "|"
        + df["race_no"].map(clean_race_no)
        + "|"
        + df["horse_key"].map(norm)
    )


def build_health(df: pd.DataFrame) -> pd.DataFrame:
    health = df.copy()
    health["race_no"] = health["race_no"].map(clean_race_no)

    numeric_columns = [
        "edgeiq_price",
        "edgeiq_probability",
        "sportsbet_price",
        "sportsbet_implied_probability",
        "market_percentage_context",
        "overlay_pct",
        "projection_score",
        "race_target",
    ]
    for column in numeric_columns:
        health[f"{column}_numeric"] = pd.to_numeric(health[column], errors="coerce")

    health["truth_key_v1"] = duplicate_key_series(health)
    key_counts = health.groupby("truth_key_v1", dropna=False).size().rename("duplicate_key_count_v1")
    health = health.merge(key_counts, on="truth_key_v1", how="left")
    health["duplicate_key_flag_v1"] = health["duplicate_key_count_v1"] > 1

    health["missing_edgeiq_price_flag_v1"] = ~health["edgeiq_price"].map(has_text)
    health["missing_edgeiq_probability_flag_v1"] = ~health["edgeiq_probability"].map(has_text)
    health["missing_sportsbet_price_flag_v1"] = ~health["sportsbet_price"].map(has_text)
    health["missing_sportsbet_implied_probability_flag_v1"] = ~health[
        "sportsbet_implied_probability"
    ].map(has_text)
    health["missing_quality_class_flag_v1"] = ~health["quality_class"].map(has_text)
    health["missing_discipline_class_allowed_flag_v1"] = ~health["discipline_class"].map(
        has_text
    )
    health["overlay_pct_missing_flag_v1"] = ~health["overlay_pct"].map(has_text)

    health["invalid_edgeiq_probability_flag_v1"] = (
        health["edgeiq_probability_numeric"].notna()
        & (
            (health["edgeiq_probability_numeric"] <= 0)
            | (health["edgeiq_probability_numeric"] >= 1)
        )
    )
    health["invalid_sportsbet_implied_probability_flag_v1"] = (
        health["sportsbet_implied_probability_numeric"].notna()
        & (
            (health["sportsbet_implied_probability_numeric"] <= 0)
            | (health["sportsbet_implied_probability_numeric"] >= 1)
        )
    )
    health["invalid_probability_any_flag_v1"] = (
        health["invalid_edgeiq_probability_flag_v1"]
        | health["invalid_sportsbet_implied_probability_flag_v1"]
    )

    health["invalid_edgeiq_price_flag_v1"] = (
        health["edgeiq_price_numeric"].notna() & (health["edgeiq_price_numeric"] <= 1)
    )
    health["invalid_sportsbet_price_flag_v1"] = (
        health["sportsbet_price_numeric"].notna() & (health["sportsbet_price_numeric"] <= 1)
    )
    health["invalid_price_any_flag_v1"] = (
        health["invalid_edgeiq_price_flag_v1"] | health["invalid_sportsbet_price_flag_v1"]
    )

    result_blank = health[RESULT_COLUMNS].apply(lambda row: all(not has_text(v) for v in row), axis=1)
    result_populated = health[RESULT_COLUMNS].apply(lambda row: any(has_text(v) for v in row), axis=1)
    health["result_fields_blank_flag_v1"] = result_blank
    health["result_fields_populated_flag_v1"] = result_populated

    snapshot_races = (
        health.groupby("snapshot_timestamp", dropna=False)[["race_date", "track", "race_no"]]
        .apply(lambda frame: frame.drop_duplicates().shape[0])
        .rename("snapshot_race_count_v1")
        .reset_index()
    )
    snapshot_runners = (
        health.groupby("snapshot_timestamp", dropna=False).size().rename("snapshot_runner_count_v1").reset_index()
    )
    health = health.merge(snapshot_races, on="snapshot_timestamp", how="left")
    health = health.merge(snapshot_runners, on="snapshot_timestamp", how="left")
    health["snapshot_low_coverage_warning_v1"] = (
        (health["snapshot_race_count_v1"] < EXPECTED_RACES_PER_SNAPSHOT)
        | (health["snapshot_runner_count_v1"] < EXPECTED_RUNNERS_PER_SNAPSHOT)
    )

    fail_flags = [
        "duplicate_key_flag_v1",
        "missing_edgeiq_price_flag_v1",
        "missing_edgeiq_probability_flag_v1",
        "missing_sportsbet_price_flag_v1",
        "missing_sportsbet_implied_probability_flag_v1",
        "missing_quality_class_flag_v1",
        "overlay_pct_missing_flag_v1",
        "invalid_probability_any_flag_v1",
        "invalid_price_any_flag_v1",
        "snapshot_low_coverage_warning_v1",
    ]
    health["critical_issue_count_v1"] = health[fail_flags].sum(axis=1)
    health["health_status_v1"] = health["critical_issue_count_v1"].apply(
        lambda count: "PASS_PENDING_RESULTS" if int(count) == 0 else "FAIL_REVIEW_REQUIRED"
    )
    health["built_at_price_truth_health_v1"] = now_utc()

    bool_columns = [
        "duplicate_key_flag_v1",
        "missing_edgeiq_price_flag_v1",
        "missing_edgeiq_probability_flag_v1",
        "missing_sportsbet_price_flag_v1",
        "missing_sportsbet_implied_probability_flag_v1",
        "missing_quality_class_flag_v1",
        "missing_discipline_class_allowed_flag_v1",
        "overlay_pct_missing_flag_v1",
        "invalid_edgeiq_probability_flag_v1",
        "invalid_sportsbet_implied_probability_flag_v1",
        "invalid_probability_any_flag_v1",
        "invalid_edgeiq_price_flag_v1",
        "invalid_sportsbet_price_flag_v1",
        "invalid_price_any_flag_v1",
        "result_fields_blank_flag_v1",
        "result_fields_populated_flag_v1",
        "snapshot_low_coverage_warning_v1",
    ]
    for column in bool_columns:
        health[column] = health[column].map(bool_text)

    output_columns = [
        "snapshot_timestamp",
        "race_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "truth_key_v1",
        "edgeiq_price",
        "edgeiq_probability",
        "sportsbet_price",
        "sportsbet_implied_probability",
        "market_percentage_context",
        "overlay_pct",
        "quality_class",
        "discipline_class",
        "price_role",
        "result_status",
        "finish_position",
        "won",
        "starting_price",
        "closing_price",
        "settlement_source",
        "duplicate_key_count_v1",
        "duplicate_key_flag_v1",
        "missing_edgeiq_price_flag_v1",
        "missing_edgeiq_probability_flag_v1",
        "missing_sportsbet_price_flag_v1",
        "missing_sportsbet_implied_probability_flag_v1",
        "missing_quality_class_flag_v1",
        "missing_discipline_class_allowed_flag_v1",
        "overlay_pct_missing_flag_v1",
        "invalid_edgeiq_probability_flag_v1",
        "invalid_sportsbet_implied_probability_flag_v1",
        "invalid_probability_any_flag_v1",
        "invalid_edgeiq_price_flag_v1",
        "invalid_sportsbet_price_flag_v1",
        "invalid_price_any_flag_v1",
        "result_fields_blank_flag_v1",
        "result_fields_populated_flag_v1",
        "snapshot_race_count_v1",
        "snapshot_runner_count_v1",
        "snapshot_low_coverage_warning_v1",
        "critical_issue_count_v1",
        "health_status_v1",
        "built_at_price_truth_health_v1",
    ]
    return health[output_columns].copy()


def summary_row(
    section: str,
    metric: str,
    value: object,
    snapshot_timestamp: str = "",
    notes: str = "",
) -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "snapshot_timestamp": snapshot_timestamp,
        "notes": notes,
        "built_at": now_utc(),
    }


def count_true(health: pd.DataFrame, column: str) -> int:
    return int(health[column].eq("TRUE").sum())


def build_summary(history: pd.DataFrame, health: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    total_rows = len(history)
    unique_snapshots = history["snapshot_timestamp"].drop_duplicates().shape[0]

    rows.append(summary_row("overall", "total_rows", total_rows))
    rows.append(summary_row("overall", "unique_snapshot_timestamps", unique_snapshots))

    rows.append(
        summary_row(
            "duplicates",
            "duplicate_key_groups",
            int((health.groupby("truth_key_v1").size() > 1).sum()),
            notes="Key is snapshot_timestamp + track + race_no + horse_key.",
        )
    )
    rows.append(
        summary_row(
            "duplicates",
            "duplicate_key_rows",
            count_true(health, "duplicate_key_flag_v1"),
            notes="Rows belonging to duplicate truth keys.",
        )
    )

    rows.extend(
        [
            summary_row("missing", "missing_edgeiq_price_count", count_true(health, "missing_edgeiq_price_flag_v1")),
            summary_row(
                "missing",
                "missing_edgeiq_probability_count",
                count_true(health, "missing_edgeiq_probability_flag_v1"),
            ),
            summary_row("missing", "missing_sportsbet_price_count", count_true(health, "missing_sportsbet_price_flag_v1")),
            summary_row(
                "missing",
                "missing_sportsbet_implied_probability_count",
                count_true(health, "missing_sportsbet_implied_probability_flag_v1"),
            ),
            summary_row("missing", "missing_quality_class_count", count_true(health, "missing_quality_class_flag_v1")),
            summary_row(
                "missing",
                "missing_discipline_class_allowed_count",
                count_true(health, "missing_discipline_class_allowed_flag_v1"),
                notes="Allowed count only; discipline_class can be blank in future non-overlay research if explicitly accepted.",
            ),
            summary_row("missing", "overlay_pct_missing_count", count_true(health, "overlay_pct_missing_flag_v1")),
        ]
    )

    rows.extend(
        [
            summary_row("invalid", "invalid_edgeiq_probabilities_lte_0_or_gte_1", count_true(health, "invalid_edgeiq_probability_flag_v1")),
            summary_row(
                "invalid",
                "invalid_sportsbet_implied_probabilities_lte_0_or_gte_1",
                count_true(health, "invalid_sportsbet_implied_probability_flag_v1"),
            ),
            summary_row("invalid", "invalid_probability_any_count", count_true(health, "invalid_probability_any_flag_v1")),
            summary_row("invalid", "invalid_edgeiq_prices_lte_1", count_true(health, "invalid_edgeiq_price_flag_v1")),
            summary_row("invalid", "invalid_sportsbet_prices_lte_1", count_true(health, "invalid_sportsbet_price_flag_v1")),
            summary_row("invalid", "invalid_price_any_count", count_true(health, "invalid_price_any_flag_v1")),
        ]
    )

    rows.extend(
        [
            summary_row("results", "blank_result_fields_count", count_true(health, "result_fields_blank_flag_v1")),
            summary_row("results", "result_fields_populated_count", count_true(health, "result_fields_populated_flag_v1")),
        ]
    )

    for snapshot, frame in health.groupby("snapshot_timestamp", dropna=False):
        snapshot_text = str(snapshot)
        races = int(frame["snapshot_race_count_v1"].iloc[0]) if len(frame) else 0
        runners = int(frame["snapshot_runner_count_v1"].iloc[0]) if len(frame) else 0
        rows.append(summary_row("snapshot", "rows_by_snapshot_timestamp", len(frame), snapshot_text))
        rows.append(summary_row("snapshot", "races_per_snapshot", races, snapshot_text))
        rows.append(summary_row("snapshot", "runners_per_snapshot", runners, snapshot_text))
        if races < EXPECTED_RACES_PER_SNAPSHOT or runners < EXPECTED_RUNNERS_PER_SNAPSHOT:
            rows.append(
                summary_row(
                    "warning",
                    "snapshot_low_coverage",
                    "TRUE",
                    snapshot_text,
                    f"races={races}; runners={runners}; expected races>={EXPECTED_RACES_PER_SNAPSHOT}, runners>={EXPECTED_RUNNERS_PER_SNAPSHOT}",
                )
            )

    if not any(row["section"] == "warning" for row in rows):
        rows.append(summary_row("warning", "snapshot_low_coverage", "FALSE", notes="All snapshots meet minimum race and runner coverage."))

    for value, count in health["quality_class"].value_counts(dropna=False).sort_index().items():
        rows.append(summary_row("quality_class_counts", str(value), int(count)))

    for value, count in health["discipline_class"].value_counts(dropna=False).sort_index().items():
        rows.append(summary_row("discipline_class_counts", str(value), int(count)))

    for value, count in health["price_role"].value_counts(dropna=False).sort_index().items():
        rows.append(summary_row("price_role_counts", str(value), int(count)))

    for value, count in health["health_status_v1"].value_counts(dropna=False).sort_index().items():
        rows.append(summary_row("health_status_counts", str(value), int(count)))

    return pd.DataFrame(rows)


def main() -> None:
    print("=" * 90)
    print("EDGEIQ PRICE TRUTH HISTORY HEALTH AUDIT V1 - REVIEW ONLY")
    print("=" * 90)

    history = load_history()
    health = build_health(history)
    summary = build_summary(history, health)

    health.to_csv(HEALTH, index=False)
    summary.to_csv(SUMMARY, index=False)

    print(f"input: {INPUT}")
    print(f"wrote: {HEALTH}")
    print(f"wrote: {SUMMARY}")
    print()
    print(summary[summary["section"].isin(["overall", "duplicates", "missing", "invalid", "results", "warning"])].to_string(index=False))
    print()
    print(summary[summary["section"].eq("snapshot")].to_string(index=False))
    print()
    print(summary[summary["section"].isin(["quality_class_counts", "discipline_class_counts", "price_role_counts", "health_status_counts"])].to_string(index=False))
    print("=" * 90)


if __name__ == "__main__":
    main()
