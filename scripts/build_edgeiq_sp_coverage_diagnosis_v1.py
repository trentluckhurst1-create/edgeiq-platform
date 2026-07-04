from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_rank1_sp_history_v1.csv"

OUT = DATA / "edgeiq_sp_coverage_diagnosis_v1.csv"
SUMMARY = DATA / "edgeiq_sp_coverage_diagnosis_v1_summary.csv"
BY_YEAR = DATA / "edgeiq_sp_coverage_diagnosis_v1_by_year.csv"
BY_TRACK = DATA / "edgeiq_sp_coverage_diagnosis_v1_by_track.csv"
BY_ENVIRONMENT = DATA / "edgeiq_sp_coverage_diagnosis_v1_by_environment.csv"
BY_TRUST = DATA / "edgeiq_sp_coverage_diagnosis_v1_by_trust.csv"
BY_FIELD_SIZE = DATA / "edgeiq_sp_coverage_diagnosis_v1_by_field_size.csv"
BY_RESULT = DATA / "edgeiq_sp_coverage_diagnosis_v1_by_result.csv"
BY_CLASS = DATA / "edgeiq_sp_coverage_diagnosis_v1_by_class.csv"

FIELD_BUCKET_ORDER = ["FIELD_LE_7", "FIELD_8_10", "FIELD_11_13", "FIELD_14_PLUS", "UNKNOWN"]
RESULT_BUCKET_ORDER = ["WIN", "LOSS", "UNKNOWN"]
STATUS_ORDER = ["VALID_SP", "MISSING_SP", "INVALID_SP"]


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def parse_numeric(value: object) -> float | None:
    text = clean_text(value)
    if not text:
        return None
    text = text.replace("$", "").replace(",", "").replace("â€“", "").replace("–", "")
    text = text.strip()
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        return None


def derive_sp_status(row: pd.Series) -> str:
    sp_raw = clean_text(row.get("sp"))
    sp_num = parse_numeric(row.get("sp_num_v1"))
    sp_valid = bool(row.get("sp_valid_v1")) and sp_num is not None and sp_num > 1
    if sp_valid:
        return "VALID_SP"
    if not sp_raw and not (sp_num is not None and sp_num > 1):
        return "MISSING_SP"
    return "INVALID_SP"


def derive_field_size_bucket(value: object) -> str:
    field_size = parse_numeric(value)
    if field_size is None:
        return "UNKNOWN"
    if field_size <= 7:
        return "FIELD_LE_7"
    if field_size <= 10:
        return "FIELD_8_10"
    if field_size <= 13:
        return "FIELD_11_13"
    return "FIELD_14_PLUS"


def derive_result_bucket(value: object) -> str:
    won = parse_numeric(value)
    if won is None:
        return "UNKNOWN"
    return "WIN" if int(won) == 1 else "LOSS"


def pick_race_class_column(frame: pd.DataFrame) -> str | None:
    for col in ["race_class", "raceClass", "race_class_diag_v1"]:
        if col in frame.columns:
            return col
    return None


def group_summary(frame: pd.DataFrame, group_col: str, sort_order: list[str] | None = None) -> pd.DataFrame:
    overall_win_pct_series = pd.to_numeric(frame["rank1_won"], errors="coerce").fillna(0)
    grouped_rows: list[dict[str, object]] = []

    for group_value, group_df in frame.groupby(group_col, dropna=False):
        group_label = clean_text(group_value) or "UNKNOWN"

        rows = len(group_df)
        valid_mask = group_df["has_valid_sp_v1"] == 1
        missing_mask = group_df["missing_sp_flag_v1"] == 1
        invalid_mask = group_df["invalid_sp_flag_v1"] == 1
        wins_mask = pd.to_numeric(group_df["rank1_won"], errors="coerce").fillna(0) == 1

        valid_sp_rows = int(valid_mask.sum())
        missing_sp_rows = int(missing_mask.sum())
        invalid_sp_rows = int(invalid_mask.sum())
        rank1_wins = int(wins_mask.sum())

        overall_rank1_win_pct = (rank1_wins / rows * 100) if rows else 0.0
        valid_sp_rank1_wins = int((valid_mask & wins_mask).sum())
        valid_sp_rank1_win_pct = (valid_sp_rank1_wins / valid_sp_rows * 100) if valid_sp_rows else 0.0
        coverage_bias_delta = valid_sp_rank1_win_pct - overall_rank1_win_pct if valid_sp_rows else 0.0

        grouped_rows.append(
            {
                group_col: group_label,
                "rows": int(rows),
                "valid_sp_rows": valid_sp_rows,
                "missing_sp_rows": missing_sp_rows,
                "invalid_sp_rows": invalid_sp_rows,
                "sp_coverage_pct": round((valid_sp_rows / rows * 100) if rows else 0.0, 2),
                "rank1_wins": rank1_wins,
                "rank1_win_pct": round(overall_rank1_win_pct, 2),
                "valid_sp_rank1_wins": valid_sp_rank1_wins,
                "valid_sp_rank1_win_pct": round(valid_sp_rank1_win_pct, 2),
                "coverage_bias_win_pct_delta": round(coverage_bias_delta, 2),
            }
        )

    out = pd.DataFrame(grouped_rows)

    if sort_order is not None and not out.empty:
        out["_sort_v1"] = out[group_col].map({value: idx for idx, value in enumerate(sort_order)})
        out["_sort_v1"] = out["_sort_v1"].fillna(len(sort_order) + 1)
        out = out.sort_values(["_sort_v1", group_col]).drop(columns="_sort_v1")
    else:
        out = out.sort_values(group_col)

    return out.reset_index(drop=True)


def main() -> None:
    if not SRC.exists():
        raise SystemExit("Missing edgeiq_rank1_sp_history_v1.csv")

    df = pd.read_csv(SRC, low_memory=False)

    required = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "rank1_horse",
        "rank1_horse_key",
        "rank1_won",
        "rank1_finish_position",
        "environment_score_v1",
        "environment_band_v1",
        "sp",
        "sp_num_v1",
        "sp_valid_v1",
        "sp_join_status_v1",
        "trust_profile_v1",
        "field_size",
        "score_share_band",
        "rank1_score_share_of_race",
        "rank1_dominance_band_v1",
        "rank1_dominance_score_v1",
    ]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise SystemExit("Source missing required columns: " + ", ".join(missing))

    df = df.copy()
    df["sp_status_v1"] = df.apply(derive_sp_status, axis=1)
    df["has_valid_sp_v1"] = (df["sp_status_v1"] == "VALID_SP").astype(int)
    df["missing_sp_flag_v1"] = (df["sp_status_v1"] == "MISSING_SP").astype(int)
    df["invalid_sp_flag_v1"] = (df["sp_status_v1"] == "INVALID_SP").astype(int)
    df["year_v1"] = pd.to_datetime(df["meeting_date"], errors="coerce").dt.year.astype("Int64").astype(str).replace("<NA>", "UNKNOWN")
    df["field_size_bucket_diag_v1"] = df["field_size"].map(derive_field_size_bucket)
    df["result_bucket_v1"] = df["rank1_won"].map(derive_result_bucket)

    race_class_col = pick_race_class_column(df)
    if race_class_col is not None:
        df["race_class_diag_v1"] = df[race_class_col].map(lambda x: clean_text(x) or "UNKNOWN")
    else:
        df["race_class_diag_v1"] = "UNKNOWN"

    df["environment_band_v1"] = df["environment_band_v1"].map(lambda x: clean_text(x).upper() or "UNKNOWN")
    df["trust_profile_v1"] = df["trust_profile_v1"].map(lambda x: clean_text(x).upper() or "UNKNOWN")

    df.to_csv(OUT, index=False)

    by_year_df = group_summary(df, "year_v1")
    by_track_df = group_summary(df, "track")
    by_environment_df = group_summary(df, "environment_band_v1", ["POOR", "NEGATIVE", "NEUTRAL", "POSITIVE", "ELITE", "UNKNOWN"])
    by_trust_df = group_summary(df, "trust_profile_v1", ["ELITE", "STRONG", "STANDARD", "CHAOTIC", "UNKNOWN"])
    by_field_size_df = group_summary(df, "field_size_bucket_diag_v1", FIELD_BUCKET_ORDER)
    by_result_df = group_summary(df, "result_bucket_v1", RESULT_BUCKET_ORDER)
    by_class_df = group_summary(df, "race_class_diag_v1")

    by_year_df.to_csv(BY_YEAR, index=False)
    by_track_df.to_csv(BY_TRACK, index=False)
    by_environment_df.to_csv(BY_ENVIRONMENT, index=False)
    by_trust_df.to_csv(BY_TRUST, index=False)
    by_field_size_df.to_csv(BY_FIELD_SIZE, index=False)
    by_result_df.to_csv(BY_RESULT, index=False)
    by_class_df.to_csv(BY_CLASS, index=False)

    total_rows = len(df)
    valid_sp_rows = int(df["has_valid_sp_v1"].sum())
    missing_sp_rows = int(df["missing_sp_flag_v1"].sum())
    invalid_sp_rows = int(df["invalid_sp_flag_v1"].sum())

    rank1_wins = int(pd.to_numeric(df["rank1_won"], errors="coerce").fillna(0).sum())
    overall_rank1_win_pct = (rank1_wins / total_rows * 100) if total_rows else 0.0
    valid_sp_rank1_wins = int(((pd.to_numeric(df["rank1_won"], errors="coerce").fillna(0) == 1) & (df["has_valid_sp_v1"] == 1)).sum())
    valid_sp_rank1_win_pct = (valid_sp_rank1_wins / valid_sp_rows * 100) if valid_sp_rows else 0.0
    coverage_bias_delta = valid_sp_rank1_win_pct - overall_rank1_win_pct if valid_sp_rows else 0.0
    sp_coverage_pct = (valid_sp_rows / total_rows * 100) if total_rows else 0.0

    eligible_years = by_year_df[by_year_df["rows"] > 0].copy()
    eligible_tracks = by_track_df[by_track_df["rows"] > 0].copy()

    worst_year_coverage_pct = float(eligible_years["sp_coverage_pct"].min()) if not eligible_years.empty else 0.0
    best_year_coverage_pct = float(eligible_years["sp_coverage_pct"].max()) if not eligible_years.empty else 0.0
    lowest_track_coverage_pct = float(eligible_tracks["sp_coverage_pct"].min()) if not eligible_tracks.empty else 0.0
    highest_track_coverage_pct = float(eligible_tracks["sp_coverage_pct"].max()) if not eligible_tracks.empty else 0.0

    if sp_coverage_pct >= 70.0:
        verdict = "SP_COVERAGE_ACCEPTABLE"
    elif abs(coverage_bias_delta) >= 5.0:
        verdict = "SP_COVERAGE_BIASED_DANGEROUS"
    else:
        verdict = "SP_COVERAGE_LOW_BUT_NOT_OBVIOUSLY_RESULT_BIASED"

    summary_df = pd.DataFrame(
        [
            {"metric": "status", "value": "COMPLETE"},
            {"metric": "total_rows", "value": total_rows},
            {"metric": "valid_sp_rows", "value": valid_sp_rows},
            {"metric": "missing_sp_rows", "value": missing_sp_rows},
            {"metric": "invalid_sp_rows", "value": invalid_sp_rows},
            {"metric": "sp_coverage_pct", "value": round(sp_coverage_pct, 2)},
            {"metric": "overall_rank1_win_pct", "value": round(overall_rank1_win_pct, 2)},
            {"metric": "valid_sp_rank1_win_pct", "value": round(valid_sp_rank1_win_pct, 2)},
            {"metric": "overall_coverage_bias_win_pct_delta", "value": round(coverage_bias_delta, 2)},
            {"metric": "worst_year_coverage_pct", "value": round(worst_year_coverage_pct, 2)},
            {"metric": "best_year_coverage_pct", "value": round(best_year_coverage_pct, 2)},
            {"metric": "lowest_track_coverage_pct", "value": round(lowest_track_coverage_pct, 2)},
            {"metric": "highest_track_coverage_pct", "value": round(highest_track_coverage_pct, 2)},
            {"metric": "verdict", "value": verdict},
        ]
    )
    summary_df.to_csv(SUMMARY, index=False)

    print("[EDGEIQ_SP_COVERAGE_DIAGNOSIS_V1] COMPLETE")
    print("status=COMPLETE")
    print(f"total_rows={total_rows}")
    print(f"valid_sp_rows={valid_sp_rows}")
    print(f"missing_sp_rows={missing_sp_rows}")
    print(f"invalid_sp_rows={invalid_sp_rows}")
    print(f"sp_coverage_pct={round(sp_coverage_pct, 2)}")
    print(f"overall_rank1_win_pct={round(overall_rank1_win_pct, 2)}")
    print(f"valid_sp_rank1_win_pct={round(valid_sp_rank1_win_pct, 2)}")
    print(f"coverage_bias_delta={round(coverage_bias_delta, 2)}")
    print(f"verdict={verdict}")
    print(f"wrote={OUT}")
    print(f"wrote={SUMMARY}")
    print(f"wrote={BY_YEAR}")
    print(f"wrote={BY_TRACK}")
    print(f"wrote={BY_ENVIRONMENT}")
    print(f"wrote={BY_TRUST}")
    print(f"wrote={BY_FIELD_SIZE}")
    print(f"wrote={BY_RESULT}")
    print(f"wrote={BY_CLASS}")


if __name__ == "__main__":
    main()
