from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_PATH = DATA / "edgeiq_trust_field_engine_v1.csv"
OUTPUT_MAIN = DATA / "edgeiq_trust_field_stability_audit_v1.csv"
OUTPUT_SUMMARY = DATA / "edgeiq_trust_field_stability_audit_v1_summary.csv"
OUTPUT_VERDICT = DATA / "edgeiq_trust_field_stability_audit_v1_verdict.csv"

BAND_ORDER = ["POOR", "NEGATIVE", "NEUTRAL", "POSITIVE", "ELITE"]
COMBINED_ORDER = ["WEAK_POOR_NEGATIVE", "NEUTRAL_ONLY", "STRONG_POSITIVE_ELITE"]


def parse_year(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.year


def summarise_group(year: int, group_name: str, group_type: str, group_df: pd.DataFrame) -> dict[str, object]:
    runners = int(len(group_df))
    wins = int(group_df["trust_field_win_v1"].sum()) if runners else 0
    win_pct = round((wins / runners) * 100, 2) if runners else 0.0
    avg_score = round(group_df["trust_field_score_v1"].mean(), 4) if runners else None
    avg_field_size = round(group_df["field_size_num_v1"].mean(), 4) if runners else None
    return {
        "audit_year_v1": int(year),
        "group_type_v1": group_type,
        "trust_field_band_v1": group_name,
        "runners": runners,
        "wins": wins,
        "win_pct": win_pct,
        "avg_trust_field_score_v1": avg_score,
        "avg_field_size": avg_field_size,
    }


def main() -> None:
    if not INPUT_PATH.exists():
        raise SystemExit(f"Missing input file: {INPUT_PATH}")

    df = pd.read_csv(INPUT_PATH, low_memory=False)

    if "meeting_date" not in df.columns:
        raise SystemExit("meeting_date column is required.")

    df["audit_year_v1"] = parse_year(df["meeting_date"])
    df = df[df["audit_year_v1"].notna()].copy()
    df["audit_year_v1"] = df["audit_year_v1"].astype(int)

    df["trust_field_score_v1"] = pd.to_numeric(df["trust_field_score_v1"], errors="coerce")
    df["field_size_num_v1"] = pd.to_numeric(df.get("field_size"), errors="coerce")
    df["trust_field_win_v1"] = pd.to_numeric(df["trust_field_win_v1"], errors="coerce").fillna(0).astype(int)

    detail_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    for year in sorted(df["audit_year_v1"].unique()):
        year_df = df[df["audit_year_v1"] == year].copy()

        for band in BAND_ORDER:
            band_df = year_df[year_df["trust_field_band_v1"] == band]
            detail_rows.append(summarise_group(year, band, "BAND", band_df))

        weak_df = year_df[year_df["trust_field_band_v1"].isin(["POOR", "NEGATIVE"])]
        neutral_df = year_df[year_df["trust_field_band_v1"] == "NEUTRAL"]
        strong_df = year_df[year_df["trust_field_band_v1"].isin(["POSITIVE", "ELITE"])]

        detail_rows.append(summarise_group(year, "WEAK_POOR_NEGATIVE", "COMBINED", weak_df))
        detail_rows.append(summarise_group(year, "NEUTRAL_ONLY", "COMBINED", neutral_df))
        detail_rows.append(summarise_group(year, "STRONG_POSITIVE_ELITE", "COMBINED", strong_df))

        weak_runners = int(len(weak_df))
        neutral_runners = int(len(neutral_df))
        strong_runners = int(len(strong_df))

        weak_win_pct = round(weak_df["trust_field_win_v1"].mean() * 100, 2) if weak_runners else 0.0
        neutral_win_pct = round(neutral_df["trust_field_win_v1"].mean() * 100, 2) if neutral_runners else 0.0
        strong_win_pct = round(strong_df["trust_field_win_v1"].mean() * 100, 2) if strong_runners else 0.0
        lift_pts = round(strong_win_pct - weak_win_pct, 2) if weak_runners and strong_runners else 0.0

        summary_rows.append(
            {
                "audit_year_v1": int(year),
                "rows": int(len(year_df)),
                "wins": int(year_df["trust_field_win_v1"].sum()),
                "overall_win_pct": round(year_df["trust_field_win_v1"].mean() * 100, 2) if len(year_df) else 0.0,
                "weak_runners": weak_runners,
                "weak_win_pct": weak_win_pct,
                "neutral_runners": neutral_runners,
                "neutral_win_pct": neutral_win_pct,
                "strong_runners": strong_runners,
                "strong_win_pct": strong_win_pct,
                "strong_vs_weak_lift_pts": lift_pts,
                "directional_pass_v1": "YES" if strong_runners and weak_runners and strong_win_pct > weak_win_pct else "NO",
                "approx_environment_pass_v1": "YES" if lift_pts >= 8.0 else "NO",
                "core_candidate_pass_v1": "YES" if lift_pts >= 10.0 else "NO",
            }
        )

    detail_df = pd.DataFrame(detail_rows)
    detail_sort = {name: idx for idx, name in enumerate(BAND_ORDER + COMBINED_ORDER)}
    detail_df["sort_order_v1"] = detail_df["trust_field_band_v1"].map(detail_sort)
    detail_df = detail_df.sort_values(["audit_year_v1", "sort_order_v1"]).drop(columns=["sort_order_v1"])
    detail_df.to_csv(OUTPUT_MAIN, index=False)

    summary_df = pd.DataFrame(summary_rows).sort_values("audit_year_v1")
    summary_df.to_csv(OUTPUT_SUMMARY, index=False)

    years_tested = int(len(summary_df))
    years_directional_passed = int((summary_df["directional_pass_v1"] == "YES").sum()) if years_tested else 0
    years_approx_passed = int((summary_df["approx_environment_pass_v1"] == "YES").sum()) if years_tested else 0
    years_core_candidate_passed = int((summary_df["core_candidate_pass_v1"] == "YES").sum()) if years_tested else 0

    if years_tested and years_directional_passed == years_tested and years_approx_passed == years_tested:
        verdict = "TRUST_FIELD_STABLE_BY_YEAR"
    elif years_tested and years_directional_passed == years_tested:
        verdict = "TRUST_FIELD_DIRECTIONALLY_STABLE"
    else:
        verdict = "TRUST_FIELD_YEAR_STABILITY_MIXED"

    verdict_rows = [
        {"metric": "verdict", "value": verdict},
        {"metric": "years_tested", "value": years_tested},
        {"metric": "years_directional_passed", "value": years_directional_passed},
        {"metric": "years_approx_environment_passed", "value": years_approx_passed},
        {"metric": "years_core_candidate_passed", "value": years_core_candidate_passed},
        {
            "metric": "min_strong_vs_weak_lift_pts",
            "value": round(summary_df["strong_vs_weak_lift_pts"].min(), 2) if years_tested else "",
        },
        {
            "metric": "avg_strong_vs_weak_lift_pts",
            "value": round(summary_df["strong_vs_weak_lift_pts"].mean(), 2) if years_tested else "",
        },
        {
            "metric": "max_strong_vs_weak_lift_pts",
            "value": round(summary_df["strong_vs_weak_lift_pts"].max(), 2) if years_tested else "",
        },
        {
            "metric": "meaning",
            "value": "Stable means STRONG_POSITIVE_ELITE beats WEAK_POOR_NEGATIVE in every tested year.",
        },
    ]
    pd.DataFrame(verdict_rows).to_csv(OUTPUT_VERDICT, index=False)

    print("[TRUST_FIELD_STABILITY_AUDIT_V1] COMPLETE")
    print(f"years_tested={years_tested}")
    print(f"years_directional_passed={years_directional_passed}")
    print(f"years_approx_environment_passed={years_approx_passed}")
    print(
        "min_strong_vs_weak_lift_pts="
        f"{round(summary_df['strong_vs_weak_lift_pts'].min(), 2) if years_tested else 'NA'}"
    )
    print(
        "max_strong_vs_weak_lift_pts="
        f"{round(summary_df['strong_vs_weak_lift_pts'].max(), 2) if years_tested else 'NA'}"
    )
    print(f"verdict={verdict}")
    print(f"wrote={OUTPUT_MAIN}")
    print(f"wrote={OUTPUT_SUMMARY}")
    print(f"wrote={OUTPUT_VERDICT}")


if __name__ == "__main__":
    main()
