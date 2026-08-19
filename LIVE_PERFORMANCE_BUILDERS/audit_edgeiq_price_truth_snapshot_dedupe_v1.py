from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT = DATA / "edgeiq_price_truth_history_v1.csv"
OUTPUT = DATA / "edgeiq_price_truth_snapshot_dedupe_v1.csv"
SUMMARY = DATA / "edgeiq_price_truth_snapshot_dedupe_v1_summary.csv"

EXPECTED_RACES_PER_SNAPSHOT = 8
EXPECTED_RUNNERS_PER_SNAPSHOT = 87

REQUIRED_COLUMNS = {
    "snapshot_timestamp",
    "race_date",
    "track",
    "race_no",
    "horse",
    "horse_key",
    "edgeiq_price",
    "sportsbet_price",
}


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


def key_text(value: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", norm(value))


def clean_race_no(value: object) -> str:
    if not has_text(value):
        return ""
    text = str(value).strip()
    text = text[:-2] if text.endswith(".0") else text
    match = re.search(r"\d+", text)
    return str(int(match.group(0))) if match else ""


def bool_text(value: object) -> str:
    return "TRUE" if bool(value) else "FALSE"


def load_history() -> pd.DataFrame:
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing price truth history: {INPUT}")

    df = pd.read_csv(INPUT, dtype=str, keep_default_na=False, low_memory=False)
    missing = sorted(REQUIRED_COLUMNS.difference(df.columns))
    if missing:
        raise ValueError(f"Price truth history missing required columns: {missing}")
    return df


def valid_timestamp_mask(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    return parsed.notna()


def full_row_signature(row: pd.Series, columns: list[str]) -> str:
    joined = "\u241f".join(str(row.get(column, "")) for column in columns)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def add_count_column(df: pd.DataFrame, key_column: str, count_column: str) -> pd.DataFrame:
    counts = df.groupby(key_column, dropna=False).size().rename(count_column).reset_index()
    return df.merge(counts, on=key_column, how="left")


def build_detail(df: pd.DataFrame) -> pd.DataFrame:
    detail = df.copy()
    detail["snapshot_timestamp_clean"] = detail["snapshot_timestamp"].astype(str).str.strip()
    detail["track_key_v1"] = detail["track"].map(key_text)
    detail["race_no_key_v1"] = detail["race_no"].map(clean_race_no)
    detail["horse_key_clean_v1"] = detail["horse_key"].map(key_text)
    detail["horse_name_key_v1"] = detail["horse"].map(key_text)

    detail["exact_snapshot_runner_key_v1"] = (
        detail["snapshot_timestamp_clean"]
        + "|"
        + detail["track_key_v1"]
        + "|"
        + detail["race_no_key_v1"]
        + "|"
        + detail["horse_key_clean_v1"]
    )
    detail["same_horse_race_timestamp_key_v1"] = (
        detail["snapshot_timestamp_clean"]
        + "|"
        + detail["track_key_v1"]
        + "|"
        + detail["race_no_key_v1"]
        + "|"
        + detail["horse_name_key_v1"]
    )
    detail["race_context_key_v1"] = (
        detail["snapshot_timestamp_clean"]
        + "|"
        + detail["race_date"].map(norm)
        + "|"
        + detail["track_key_v1"]
        + "|"
        + detail["race_no_key_v1"]
    )

    source_columns = list(df.columns)
    detail["full_row_signature_v1"] = detail.apply(
        lambda row: full_row_signature(row, source_columns),
        axis=1,
    )
    detail["snapshot_full_row_signature_v1"] = (
        detail["snapshot_timestamp_clean"] + "|" + detail["full_row_signature_v1"]
    )

    detail = add_count_column(
        detail,
        "exact_snapshot_runner_key_v1",
        "duplicate_exact_key_count_v1",
    )
    detail = add_count_column(
        detail,
        "same_horse_race_timestamp_key_v1",
        "duplicate_same_horse_race_timestamp_count_v1",
    )
    detail = add_count_column(
        detail,
        "snapshot_full_row_signature_v1",
        "duplicated_full_row_same_timestamp_count_v1",
    )

    snapshot_rows = (
        detail.groupby("snapshot_timestamp_clean", dropna=False)
        .size()
        .rename("rows_in_snapshot_v1")
        .reset_index()
    )
    snapshot_races = (
        detail.groupby("snapshot_timestamp_clean", dropna=False)["race_context_key_v1"]
        .nunique()
        .rename("races_in_snapshot_v1")
        .reset_index()
    )
    snapshot_runners = (
        detail.groupby("snapshot_timestamp_clean", dropna=False)["exact_snapshot_runner_key_v1"]
        .nunique()
        .rename("runners_in_snapshot_v1")
        .reset_index()
    )
    snapshot_missing_edgeiq = (
        detail.assign(missing_edgeiq_price_flag_v1=~detail["edgeiq_price"].map(has_text))
        .groupby("snapshot_timestamp_clean", dropna=False)["missing_edgeiq_price_flag_v1"]
        .sum()
        .rename("missing_edgeiq_price_in_snapshot_v1")
        .reset_index()
    )
    snapshot_missing_sportsbet = (
        detail.assign(missing_sportsbet_price_flag_v1=~detail["sportsbet_price"].map(has_text))
        .groupby("snapshot_timestamp_clean", dropna=False)["missing_sportsbet_price_flag_v1"]
        .sum()
        .rename("missing_sportsbet_price_in_snapshot_v1")
        .reset_index()
    )

    for frame in [
        snapshot_rows,
        snapshot_races,
        snapshot_runners,
        snapshot_missing_edgeiq,
        snapshot_missing_sportsbet,
    ]:
        detail = detail.merge(frame, on="snapshot_timestamp_clean", how="left")

    blank_timestamp = ~detail["snapshot_timestamp_clean"].map(has_text)
    valid_timestamp = valid_timestamp_mask(detail["snapshot_timestamp_clean"])
    detail["blank_timestamp_flag_v1"] = blank_timestamp
    detail["malformed_timestamp_flag_v1"] = (~blank_timestamp) & (~valid_timestamp)
    detail["duplicate_exact_key_flag_v1"] = detail["duplicate_exact_key_count_v1"] > 1
    detail["duplicate_same_horse_same_race_timestamp_flag_v1"] = (
        detail["duplicate_same_horse_race_timestamp_count_v1"] > 1
    )
    detail["duplicated_full_row_same_timestamp_flag_v1"] = (
        detail["duplicated_full_row_same_timestamp_count_v1"] > 1
    )
    detail["snapshot_fewer_than_8_races_flag_v1"] = (
        detail["races_in_snapshot_v1"] < EXPECTED_RACES_PER_SNAPSHOT
    )
    detail["snapshot_fewer_than_87_runners_flag_v1"] = (
        detail["runners_in_snapshot_v1"] < EXPECTED_RUNNERS_PER_SNAPSHOT
    )
    detail["missing_edgeiq_price_flag_v1"] = ~detail["edgeiq_price"].map(has_text)
    detail["missing_sportsbet_price_flag_v1"] = ~detail["sportsbet_price"].map(has_text)

    fail_flags = [
        "blank_timestamp_flag_v1",
        "malformed_timestamp_flag_v1",
        "duplicate_exact_key_flag_v1",
        "duplicate_same_horse_same_race_timestamp_flag_v1",
        "duplicated_full_row_same_timestamp_flag_v1",
    ]
    warn_flags = [
        "snapshot_fewer_than_8_races_flag_v1",
        "snapshot_fewer_than_87_runners_flag_v1",
        "missing_edgeiq_price_flag_v1",
        "missing_sportsbet_price_flag_v1",
    ]

    detail["dedupe_fail_flag_v1"] = detail[fail_flags].any(axis=1)
    detail["dedupe_warn_flag_v1"] = (~detail["dedupe_fail_flag_v1"]) & detail[warn_flags].any(
        axis=1
    )
    detail["dedupe_status_v1"] = "DEDUPE_PASS"
    detail.loc[detail["dedupe_warn_flag_v1"], "dedupe_status_v1"] = "DEDUPE_WARN"
    detail.loc[detail["dedupe_fail_flag_v1"], "dedupe_status_v1"] = "DEDUPE_FAIL"
    detail["built_at_dedupe_audit_v1"] = now_utc()

    bool_columns = [
        "blank_timestamp_flag_v1",
        "malformed_timestamp_flag_v1",
        "duplicate_exact_key_flag_v1",
        "duplicate_same_horse_same_race_timestamp_flag_v1",
        "duplicated_full_row_same_timestamp_flag_v1",
        "snapshot_fewer_than_8_races_flag_v1",
        "snapshot_fewer_than_87_runners_flag_v1",
        "missing_edgeiq_price_flag_v1",
        "missing_sportsbet_price_flag_v1",
        "dedupe_fail_flag_v1",
        "dedupe_warn_flag_v1",
    ]
    for column in bool_columns:
        detail[column] = detail[column].map(bool_text)

    return detail


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


def count_true(detail: pd.DataFrame, column: str) -> int:
    return int(detail[column].eq("TRUE").sum())


def duplicate_group_count(detail: pd.DataFrame, key_column: str, count_column: str) -> int:
    grouped = detail[[key_column, count_column]].drop_duplicates()
    return int((pd.to_numeric(grouped[count_column], errors="coerce") > 1).sum())


def build_summary(detail: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    total_rows = len(detail)
    unique_snapshots = int(detail["snapshot_timestamp_clean"].nunique(dropna=False))
    duplicate_exact_rows = count_true(detail, "duplicate_exact_key_flag_v1")
    duplicate_same_horse_rows = count_true(
        detail,
        "duplicate_same_horse_same_race_timestamp_flag_v1",
    )
    duplicate_full_rows = count_true(detail, "duplicated_full_row_same_timestamp_flag_v1")
    blank_timestamp_rows = count_true(detail, "blank_timestamp_flag_v1")
    malformed_timestamp_rows = count_true(detail, "malformed_timestamp_flag_v1")
    low_race_snapshot_rows = count_true(detail, "snapshot_fewer_than_8_races_flag_v1")
    low_runner_snapshot_rows = count_true(detail, "snapshot_fewer_than_87_runners_flag_v1")
    missing_edgeiq_rows = count_true(detail, "missing_edgeiq_price_flag_v1")
    missing_sportsbet_rows = count_true(detail, "missing_sportsbet_price_flag_v1")

    status = "DEDUPE_PASS"
    if (
        duplicate_exact_rows
        or duplicate_same_horse_rows
        or duplicate_full_rows
        or blank_timestamp_rows
        or malformed_timestamp_rows
    ):
        status = "DEDUPE_FAIL"
    elif (
        low_race_snapshot_rows
        or low_runner_snapshot_rows
        or missing_edgeiq_rows
        or missing_sportsbet_rows
    ):
        status = "DEDUPE_WARN"

    rows.extend(
        [
            summary_row("overall", "total_rows", total_rows),
            summary_row("overall", "unique_snapshots", unique_snapshots),
            summary_row("overall", "duplicate_exact_key_rows", duplicate_exact_rows),
            summary_row(
                "overall",
                "duplicate_exact_key_groups",
                duplicate_group_count(
                    detail,
                    "exact_snapshot_runner_key_v1",
                    "duplicate_exact_key_count_v1",
                ),
            ),
            summary_row(
                "overall",
                "duplicate_same_horse_same_race_timestamp_rows",
                duplicate_same_horse_rows,
            ),
            summary_row(
                "overall",
                "duplicate_same_horse_same_race_timestamp_groups",
                duplicate_group_count(
                    detail,
                    "same_horse_race_timestamp_key_v1",
                    "duplicate_same_horse_race_timestamp_count_v1",
                ),
            ),
            summary_row(
                "overall",
                "duplicated_full_row_same_timestamp_rows",
                duplicate_full_rows,
            ),
            summary_row(
                "overall",
                "duplicated_full_row_same_timestamp_groups",
                duplicate_group_count(
                    detail,
                    "snapshot_full_row_signature_v1",
                    "duplicated_full_row_same_timestamp_count_v1",
                ),
            ),
            summary_row("overall", "blank_timestamp_rows", blank_timestamp_rows),
            summary_row("overall", "malformed_timestamp_rows", malformed_timestamp_rows),
            summary_row(
                "overall",
                "snapshots_with_fewer_than_8_races",
                int(
                    detail.loc[
                        detail["snapshot_fewer_than_8_races_flag_v1"].eq("TRUE"),
                        "snapshot_timestamp_clean",
                    ].nunique(dropna=False)
                ),
            ),
            summary_row(
                "overall",
                "snapshots_with_fewer_than_87_runners",
                int(
                    detail.loc[
                        detail["snapshot_fewer_than_87_runners_flag_v1"].eq("TRUE"),
                        "snapshot_timestamp_clean",
                    ].nunique(dropna=False)
                ),
            ),
            summary_row("overall", "missing_edgeiq_price_rows", missing_edgeiq_rows),
            summary_row("overall", "missing_sportsbet_price_rows", missing_sportsbet_rows),
            summary_row("status", "dedupe_status", status),
        ]
    )

    snapshot_summary = (
        detail.groupby("snapshot_timestamp_clean", dropna=False)
        .agg(
            rows_per_snapshot=("snapshot_timestamp_clean", "size"),
            races_per_snapshot=("race_context_key_v1", "nunique"),
            runners_per_snapshot=("exact_snapshot_runner_key_v1", "nunique"),
            duplicate_exact_key_rows=("duplicate_exact_key_flag_v1", lambda s: int(s.eq("TRUE").sum())),
            duplicate_same_horse_same_race_timestamp_rows=(
                "duplicate_same_horse_same_race_timestamp_flag_v1",
                lambda s: int(s.eq("TRUE").sum()),
            ),
            duplicated_full_row_same_timestamp_rows=(
                "duplicated_full_row_same_timestamp_flag_v1",
                lambda s: int(s.eq("TRUE").sum()),
            ),
            blank_timestamp_rows=("blank_timestamp_flag_v1", lambda s: int(s.eq("TRUE").sum())),
            malformed_timestamp_rows=(
                "malformed_timestamp_flag_v1",
                lambda s: int(s.eq("TRUE").sum()),
            ),
            missing_edgeiq_price_rows=("missing_edgeiq_price_flag_v1", lambda s: int(s.eq("TRUE").sum())),
            missing_sportsbet_price_rows=(
                "missing_sportsbet_price_flag_v1",
                lambda s: int(s.eq("TRUE").sum()),
            ),
        )
        .reset_index()
        .sort_values("snapshot_timestamp_clean")
    )

    for _, row in snapshot_summary.iterrows():
        snapshot = str(row["snapshot_timestamp_clean"])
        for metric in [
            "rows_per_snapshot",
            "races_per_snapshot",
            "runners_per_snapshot",
            "duplicate_exact_key_rows",
            "duplicate_same_horse_same_race_timestamp_rows",
            "duplicated_full_row_same_timestamp_rows",
            "blank_timestamp_rows",
            "malformed_timestamp_rows",
            "missing_edgeiq_price_rows",
            "missing_sportsbet_price_rows",
        ]:
            rows.append(
                summary_row(
                    "snapshot",
                    metric,
                    int(row[metric]),
                    snapshot,
                )
            )

    status_counts = detail["dedupe_status_v1"].value_counts(dropna=False).sort_index()
    for status_name, count in status_counts.items():
        rows.append(summary_row("dedupe_status_counts", str(status_name), int(count)))

    return pd.DataFrame(rows)


def main() -> None:
    history = load_history()
    detail = build_detail(history)
    summary = build_summary(detail)

    detail.to_csv(OUTPUT, index=False)
    summary.to_csv(SUMMARY, index=False)

    status = summary.loc[
        (summary["section"] == "status") & (summary["metric"] == "dedupe_status"),
        "value",
    ].iloc[0]

    print("=" * 88)
    print("EDGEIQ PRICE TRUTH SNAPSHOT DEDUPE AUDIT V1 - READ ONLY")
    print("=" * 88)
    print(f"input: {INPUT}")
    print(f"wrote: {OUTPUT}")
    print(f"wrote: {SUMMARY}")
    print("")
    print(summary[summary["section"].isin(["overall", "status", "dedupe_status_counts"])].to_string(index=False))
    print("")
    print(summary[summary["section"].eq("snapshot")].to_string(index=False))
    print("")
    print(f"status: {status}")
    print("=" * 88)


if __name__ == "__main__":
    main()
