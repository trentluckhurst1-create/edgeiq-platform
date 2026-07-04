from __future__ import annotations

import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_environment_v2_trust_field_core.csv"

OUT = DATA / "edgeiq_environment_v2_replay_audit.csv"
SUMMARY = DATA / "edgeiq_environment_v2_replay_audit_summary.csv"
BY_BAND = DATA / "edgeiq_environment_v2_replay_audit_by_band.csv"
BY_YEAR = DATA / "edgeiq_environment_v2_replay_audit_by_year.csv"
VERDICT = DATA / "edgeiq_environment_v2_replay_audit_verdict.csv"

BAND_ORDER = ["POOR", "NEGATIVE", "NEUTRAL", "POSITIVE", "ELITE"]
COMBINED_ORDER = ["WEAK_POOR_NEGATIVE", "NEUTRAL_ONLY", "STRONG_POSITIVE_ELITE"]

TRUE_VALUES = {"1", "TRUE", "YES", "Y", "WIN", "WON"}
FALSE_VALUES = {"0", "FALSE", "NO", "N", "LOSE", "LOST"}

WIN_COLS = [
    "won",
    "is_winner",
    "winner",
    "result_winner",
    "rank1_won",
    "rank_1_won",
    "top_rank_won",
    "model_rank1_won",
    "rank1_win",
    "rank_1_win",
    "environment_win_v1",
]


def clean_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def clean_col(value: object) -> str:
    return clean_text(value).lower()


def find_col(df: pd.DataFrame, names: list[str]) -> str | None:
    lookup = {clean_col(column): column for column in df.columns}
    for name in names:
        if clean_col(name) in lookup:
            return lookup[clean_col(name)]
    return None


def truthy_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.upper().isin(TRUE_VALUES)


def infer_win(df: pd.DataFrame) -> tuple[pd.Series, str]:
    column = find_col(df, WIN_COLS)
    if column:
        return truthy_series(df[column]).astype(int), f"win_col:{column}"
    raise SystemExit("No supported win column found in V2 core file.")


def summarise_subset(group_df: pd.DataFrame, model_version: str, group_name: str, group_type: str) -> dict[str, object]:
    runners = int(len(group_df))
    wins = int(group_df["environment_v2_replay_win"].sum()) if runners else 0
    win_pct = round((wins / runners) * 100, 2) if runners else 0.0
    return {
        "model_version_v1": model_version,
        "group_type_v1": group_type,
        "band_or_group_v1": group_name,
        "runners": runners,
        "wins": wins,
        "win_pct": win_pct,
    }


def yearly_summary(group_df: pd.DataFrame, band_col: str) -> dict[str, object]:
    weak = group_df[group_df[band_col].isin(["POOR", "NEGATIVE"])]
    neutral = group_df[group_df[band_col] == "NEUTRAL"]
    strong = group_df[group_df[band_col].isin(["POSITIVE", "ELITE"])]

    weak_runners = int(len(weak))
    neutral_runners = int(len(neutral))
    strong_runners = int(len(strong))

    weak_win_pct = round(weak["environment_v2_replay_win"].mean() * 100, 2) if weak_runners else 0.0
    neutral_win_pct = round(neutral["environment_v2_replay_win"].mean() * 100, 2) if neutral_runners else 0.0
    strong_win_pct = round(strong["environment_v2_replay_win"].mean() * 100, 2) if strong_runners else 0.0
    lift_pts = round(strong_win_pct - weak_win_pct, 2) if weak_runners and strong_runners else 0.0

    return {
        "weak_runners": weak_runners,
        "weak_win_pct": weak_win_pct,
        "neutral_runners": neutral_runners,
        "neutral_win_pct": neutral_win_pct,
        "strong_runners": strong_runners,
        "strong_win_pct": strong_win_pct,
        "lift_pts": lift_pts,
        "passes": "YES" if weak_runners and strong_runners and strong_win_pct > weak_win_pct else "NO",
    }


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"Missing source file: {SRC}")

    df = pd.read_csv(SRC, low_memory=False)

    if "environment_band_v2" not in df.columns:
        raise SystemExit("environment_band_v2 missing from source file.")
    if "environment_band_v1" not in df.columns:
        raise SystemExit("environment_band_v1 missing from source file for comparison.")
    if "meeting_date" not in df.columns:
        raise SystemExit("meeting_date missing from source file.")

    wins, win_source = infer_win(df)
    df["environment_v2_replay_win"] = wins.astype(int)
    df["audit_year_v1"] = pd.to_datetime(df["meeting_date"], errors="coerce").dt.year
    df["v2_band_order_v1"] = df["environment_band_v2"].map({name: idx for idx, name in enumerate(BAND_ORDER)})
    df["v1_band_order_v1"] = df["environment_band_v1"].map({name: idx for idx, name in enumerate(BAND_ORDER)})
    df["v2_minus_v1_band_rank_v1"] = df["v2_band_order_v1"] - df["v1_band_order_v1"]
    df.to_csv(OUT, index=False)

    band_rows: list[dict[str, object]] = []
    for model_version, band_col in [("V2", "environment_band_v2"), ("V1", "environment_band_v1")]:
        for band in BAND_ORDER:
            band_rows.append(
                summarise_subset(
                    df[df[band_col] == band],
                    model_version,
                    band,
                    "BAND",
                )
            )

        band_rows.append(
            summarise_subset(
                df[df[band_col].isin(["POOR", "NEGATIVE"])],
                model_version,
                "WEAK_POOR_NEGATIVE",
                "COMBINED",
            )
        )
        band_rows.append(
            summarise_subset(
                df[df[band_col] == "NEUTRAL"],
                model_version,
                "NEUTRAL_ONLY",
                "COMBINED",
            )
        )
        band_rows.append(
            summarise_subset(
                df[df[band_col].isin(["POSITIVE", "ELITE"])],
                model_version,
                "STRONG_POSITIVE_ELITE",
                "COMBINED",
            )
        )

    by_band = pd.DataFrame(band_rows)
    group_sort = {name: idx for idx, name in enumerate(BAND_ORDER + COMBINED_ORDER)}
    by_band["model_sort_v1"] = by_band["model_version_v1"].map({"V2": 0, "V1": 1})
    by_band["group_sort_v1"] = by_band["band_or_group_v1"].map(group_sort)
    by_band = by_band.sort_values(["group_sort_v1", "model_sort_v1"]).drop(columns=["model_sort_v1", "group_sort_v1"])
    by_band.to_csv(BY_BAND, index=False)

    year_rows: list[dict[str, object]] = []
    year_df = df[df["audit_year_v1"].notna()].copy()
    year_df["audit_year_v1"] = year_df["audit_year_v1"].astype(int)
    for year in sorted(year_df["audit_year_v1"].unique()):
        subset = year_df[year_df["audit_year_v1"] == year].copy()
        v2 = yearly_summary(subset, "environment_band_v2")
        v1 = yearly_summary(subset, "environment_band_v1")
        year_rows.append(
            {
                "audit_year_v1": int(year),
                "rows": int(len(subset)),
                "wins": int(subset["environment_v2_replay_win"].sum()),
                "overall_win_pct": round(subset["environment_v2_replay_win"].mean() * 100, 2) if len(subset) else 0.0,
                "v2_weak_runners": v2["weak_runners"],
                "v2_weak_win_pct": v2["weak_win_pct"],
                "v2_neutral_runners": v2["neutral_runners"],
                "v2_neutral_win_pct": v2["neutral_win_pct"],
                "v2_strong_runners": v2["strong_runners"],
                "v2_strong_win_pct": v2["strong_win_pct"],
                "v2_lift_pts": v2["lift_pts"],
                "v2_passes": v2["passes"],
                "v1_weak_runners": v1["weak_runners"],
                "v1_weak_win_pct": v1["weak_win_pct"],
                "v1_neutral_runners": v1["neutral_runners"],
                "v1_neutral_win_pct": v1["neutral_win_pct"],
                "v1_strong_runners": v1["strong_runners"],
                "v1_strong_win_pct": v1["strong_win_pct"],
                "v1_lift_pts": v1["lift_pts"],
                "v1_passes": v1["passes"],
                "lift_delta_v2_minus_v1_pts": round(v2["lift_pts"] - v1["lift_pts"], 2),
            }
        )

    by_year = pd.DataFrame(year_rows)
    by_year.to_csv(BY_YEAR, index=False)

    v2_weak = by_band[(by_band["model_version_v1"] == "V2") & (by_band["band_or_group_v1"] == "WEAK_POOR_NEGATIVE")].iloc[0]
    v2_neutral = by_band[(by_band["model_version_v1"] == "V2") & (by_band["band_or_group_v1"] == "NEUTRAL_ONLY")].iloc[0]
    v2_strong = by_band[(by_band["model_version_v1"] == "V2") & (by_band["band_or_group_v1"] == "STRONG_POSITIVE_ELITE")].iloc[0]
    v1_weak = by_band[(by_band["model_version_v1"] == "V1") & (by_band["band_or_group_v1"] == "WEAK_POOR_NEGATIVE")].iloc[0]
    v1_strong = by_band[(by_band["model_version_v1"] == "V1") & (by_band["band_or_group_v1"] == "STRONG_POSITIVE_ELITE")].iloc[0]

    v2_lift = round(float(v2_strong["win_pct"]) - float(v2_weak["win_pct"]), 2)
    v1_lift = round(float(v1_strong["win_pct"]) - float(v1_weak["win_pct"]), 2)
    lift_delta = round(v2_lift - v1_lift, 2)

    years_tested = int(len(by_year))
    v2_years_passed = int((by_year["v2_passes"] == "YES").sum()) if years_tested else 0
    v1_years_passed = int((by_year["v1_passes"] == "YES").sum()) if years_tested else 0

    if years_tested and v2_years_passed == years_tested and v2_lift >= 10.0 and abs(lift_delta) <= 1.5:
        verdict = "V2_PRODUCTION_CANDIDATE_CONFIRMED"
    elif years_tested and v2_years_passed == years_tested and v2_lift >= 8.0:
        verdict = "V2_DIRECTIONALLY_VALIDATED"
    else:
        verdict = "V2_NOT_YET_PROVEN"

    summary_rows = [
        {"metric": "rows", "value": int(len(df))},
        {"metric": "wins", "value": int(df["environment_v2_replay_win"].sum())},
        {"metric": "overall_win_pct", "value": round(df["environment_v2_replay_win"].mean() * 100, 2)},
        {"metric": "win_source", "value": win_source},
        {"metric": "v2_weak_runners", "value": int(v2_weak["runners"])},
        {"metric": "v2_weak_win_pct", "value": float(v2_weak["win_pct"])},
        {"metric": "v2_neutral_runners", "value": int(v2_neutral["runners"])},
        {"metric": "v2_neutral_win_pct", "value": float(v2_neutral["win_pct"])},
        {"metric": "v2_strong_runners", "value": int(v2_strong["runners"])},
        {"metric": "v2_strong_win_pct", "value": float(v2_strong["win_pct"])},
        {"metric": "v2_strong_vs_weak_lift_pts", "value": v2_lift},
        {"metric": "v1_weak_win_pct", "value": float(v1_weak["win_pct"])},
        {"metric": "v1_strong_win_pct", "value": float(v1_strong["win_pct"])},
        {"metric": "v1_strong_vs_weak_lift_pts", "value": v1_lift},
        {"metric": "lift_delta_v2_minus_v1_pts", "value": lift_delta},
        {"metric": "years_tested", "value": years_tested},
        {"metric": "v2_years_passed", "value": v2_years_passed},
        {"metric": "v1_years_passed", "value": v1_years_passed},
        {"metric": "v2_min_year_lift_pts", "value": round(by_year["v2_lift_pts"].min(), 2) if years_tested else ""},
        {"metric": "v2_max_year_lift_pts", "value": round(by_year["v2_lift_pts"].max(), 2) if years_tested else ""},
        {"metric": "v1_min_year_lift_pts", "value": round(by_year["v1_lift_pts"].min(), 2) if years_tested else ""},
        {"metric": "v1_max_year_lift_pts", "value": round(by_year["v1_lift_pts"].max(), 2) if years_tested else ""},
        {"metric": "verdict", "value": verdict},
    ]
    pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)

    verdict_rows = [
        {"metric": "verdict", "value": verdict},
        {"metric": "v2_strong_vs_weak_lift_pts", "value": v2_lift},
        {"metric": "v1_strong_vs_weak_lift_pts", "value": v1_lift},
        {"metric": "lift_delta_v2_minus_v1_pts", "value": lift_delta},
        {"metric": "v2_years_passed", "value": f"{v2_years_passed}/{years_tested}"},
        {"metric": "meaning", "value": "Confirmed means V2 reproduces V1-like lift and passes by-year separation."},
    ]
    pd.DataFrame(verdict_rows).to_csv(VERDICT, index=False)

    print("[ENVIRONMENT_V2_REPLAY_AUDIT] COMPLETE")
    print(f"rows={len(df)}")
    print(f"overall_win_pct={round(df['environment_v2_replay_win'].mean() * 100, 2)}")
    print(f"v2_weak_win_pct={float(v2_weak['win_pct'])}")
    print(f"v2_neutral_win_pct={float(v2_neutral['win_pct'])}")
    print(f"v2_strong_win_pct={float(v2_strong['win_pct'])}")
    print(f"v2_strong_vs_weak_lift_pts={v2_lift}")
    print(f"v1_strong_vs_weak_lift_pts={v1_lift}")
    print(f"lift_delta_v2_minus_v1_pts={lift_delta}")
    print(f"v2_years_passed={v2_years_passed}/{years_tested}")
    print(f"verdict={verdict}")
    print(f"wrote={OUT}")
    print(f"wrote={SUMMARY}")
    print(f"wrote={BY_BAND}")
    print(f"wrote={BY_YEAR}")
    print(f"wrote={VERDICT}")


if __name__ == "__main__":
    main()
