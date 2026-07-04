from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT = DATA / "edgeiq_clean_overlay_review_board_v5_2.csv"
OUT = DATA / "edgeiq_overlay_discipline_filter_v5_2.csv"
SUMMARY = DATA / "edgeiq_overlay_discipline_filter_v5_2_summary.csv"

MARKET_SHAPE_REVIEW_THRESHOLD = 3
EXTREME_OVERLAY_THRESHOLD = 100.0


def norm(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).upper().strip().split())


def to_number(value: object) -> float:
    return pd.to_numeric(value, errors="coerce")


def fmt(value: object, decimals: int = 2) -> str:
    parsed = to_number(value)
    if pd.isna(parsed):
        return ""
    return f"{float(parsed):.{decimals}f}"


def load_input() -> pd.DataFrame:
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing clean overlay review board input: {INPUT}")

    df = pd.read_csv(INPUT, dtype=str, keep_default_na=False, low_memory=False)
    required = {
        "race",
        "horse",
        "sportsbet_price",
        "rated_price",
        "overlay_pct",
        "rated_probability",
        "sportsbet_implied_probability",
        "projection_score",
        "race_target",
        "history_bucket",
        "price_role",
        "overlay_band",
        "warning_flags",
        "review_note",
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing required clean board columns: {missing}")
    return df


def discipline_class(row: pd.Series) -> str:
    price_role = norm(row.get("price_role", ""))
    race_overlay_count = int(row.get("race_clean_overlay_count_v5_2", 0))

    if price_role == "LONGSHOT":
        return "LONGSHOT_RESEARCH_ONLY"
    if price_role == "MIDPRICE" and race_overlay_count >= MARKET_SHAPE_REVIEW_THRESHOLD:
        return "MARKET_SHAPE_REVIEW"
    if price_role == "MIDPRICE":
        return "PRIMARY_RESEARCH_CANDIDATE"
    if race_overlay_count >= MARKET_SHAPE_REVIEW_THRESHOLD:
        return "MARKET_SHAPE_REVIEW"
    return "REVIEW_ONLY"


def discipline_flags(row: pd.Series) -> str:
    flags = ["REVIEW_ONLY"]
    race_overlay_count = int(row.get("race_clean_overlay_count_v5_2", 0))
    overlay_pct = to_number(row.get("overlay_pct"))
    primary_class = row.get("discipline_class_v5_2", "")

    if primary_class:
        flags.append(str(primary_class))
    if race_overlay_count >= MARKET_SHAPE_REVIEW_THRESHOLD:
        flags.append("MARKET_SHAPE_REVIEW")
    if pd.notna(overlay_pct) and float(overlay_pct) > EXTREME_OVERLAY_THRESHOLD:
        flags.append("EXTREME_OVERLAY_REVIEW")

    deduped: list[str] = []
    for flag in flags:
        if flag and flag not in deduped:
            deduped.append(flag)
    return "|".join(deduped)


def discipline_note(row: pd.Series) -> str:
    primary_class = row["discipline_class_v5_2"]
    race_overlay_count = int(row["race_clean_overlay_count_v5_2"])
    overlay_pct = to_number(row["overlay_pct"])

    notes = ["Review-only discipline filter; not an execution recommendation."]
    if primary_class == "PRIMARY_RESEARCH_CANDIDATE":
        notes.append("Midprice clean overlay in a race with fewer than 3 clean overlays.")
    elif primary_class == "MARKET_SHAPE_REVIEW":
        notes.append("Midprice overlay sits in a race with 3+ clean overlays, so race shape/market shape needs review.")
    elif primary_class == "LONGSHOT_RESEARCH_ONLY":
        notes.append("Longshot-priced overlay is research-only noise until independently validated.")
    else:
        notes.append("Overlay requires manual review.")

    if race_overlay_count >= MARKET_SHAPE_REVIEW_THRESHOLD:
        notes.append(f"Race has {race_overlay_count} clean overlays.")
    if pd.notna(overlay_pct) and float(overlay_pct) > EXTREME_OVERLAY_THRESHOLD:
        notes.append(f"Overlay exceeds {EXTREME_OVERLAY_THRESHOLD:.0f}% and is extreme-review only.")
    return " ".join(notes)


def build_filter(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["sportsbet_price"] = pd.to_numeric(out["sportsbet_price"], errors="coerce")
    out["rated_price"] = pd.to_numeric(out["rated_price"], errors="coerce")
    out["overlay_pct"] = pd.to_numeric(out["overlay_pct"], errors="coerce")
    out["rated_probability"] = pd.to_numeric(out["rated_probability"], errors="coerce")
    out["sportsbet_implied_probability"] = pd.to_numeric(
        out["sportsbet_implied_probability"], errors="coerce"
    )
    out["projection_score"] = pd.to_numeric(out["projection_score"], errors="coerce")

    race_counts = out.groupby("race", dropna=False).size().rename("race_clean_overlay_count_v5_2")
    out = out.merge(race_counts, on="race", how="left")

    out["discipline_class_v5_2"] = out.apply(discipline_class, axis=1)
    out["market_shape_review_v5_2"] = (
        out["race_clean_overlay_count_v5_2"] >= MARKET_SHAPE_REVIEW_THRESHOLD
    )
    out["extreme_overlay_review_v5_2"] = out["overlay_pct"] > EXTREME_OVERLAY_THRESHOLD
    out["primary_research_candidate_v5_2"] = out["discipline_class_v5_2"].eq(
        "PRIMARY_RESEARCH_CANDIDATE"
    )
    out["longshot_research_only_v5_2"] = out["discipline_class_v5_2"].eq(
        "LONGSHOT_RESEARCH_ONLY"
    )
    out["discipline_flags_v5_2"] = out.apply(discipline_flags, axis=1)
    out["discipline_note_v5_2"] = out.apply(discipline_note, axis=1)
    out["built_at_overlay_discipline_filter_v5_2"] = datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )

    sort = out.copy()
    sort["_primary_sort"] = sort["primary_research_candidate_v5_2"].map({True: 0, False: 1})
    sort["_review_sort"] = sort["market_shape_review_v5_2"].map({True: 1, False: 0})
    sort = sort.sort_values(
        ["_primary_sort", "_review_sort", "race", "overlay_pct"],
        ascending=[True, True, True, False],
    )

    output_cols = [
        "race",
        "horse",
        "sportsbet_price",
        "rated_price",
        "overlay_pct",
        "rated_probability",
        "sportsbet_implied_probability",
        "projection_score",
        "race_target",
        "history_bucket",
        "price_role",
        "overlay_band",
        "race_clean_overlay_count_v5_2",
        "discipline_class_v5_2",
        "discipline_flags_v5_2",
        "primary_research_candidate_v5_2",
        "longshot_research_only_v5_2",
        "market_shape_review_v5_2",
        "extreme_overlay_review_v5_2",
        "warning_flags",
        "discipline_note_v5_2",
        "review_note",
        "built_at_overlay_discipline_filter_v5_2",
    ]
    return sort.drop(columns=["_primary_sort", "_review_sort"])[output_cols].reset_index(drop=True)


def summary_row(
    section: str,
    group: str,
    count: int,
    avg_overlay_pct: object = "",
    max_overlay_pct: object = "",
    min_overlay_pct: object = "",
    notes: str = "",
) -> dict[str, object]:
    return {
        "section": section,
        "group": group,
        "count": count,
        "avg_overlay_pct": fmt(avg_overlay_pct),
        "max_overlay_pct": fmt(max_overlay_pct),
        "min_overlay_pct": fmt(min_overlay_pct),
        "notes": notes,
    }


def aggregate_rows(df: pd.DataFrame, section: str, column: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for group, frame in df.groupby(column, dropna=False):
        rows.append(
            summary_row(
                section=section,
                group=str(group),
                count=len(frame),
                avg_overlay_pct=frame["overlay_pct"].mean(),
                max_overlay_pct=frame["overlay_pct"].max(),
                min_overlay_pct=frame["overlay_pct"].min(),
            )
        )
    return rows


def runner_rows(df: pd.DataFrame, section: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for _, row in df.iterrows():
        rows.append(
            summary_row(
                section=section,
                group=str(row["horse"]),
                count=1,
                avg_overlay_pct=row["overlay_pct"],
                max_overlay_pct=row["overlay_pct"],
                min_overlay_pct=row["overlay_pct"],
                notes=(
                    f"{row['race']}; class={row['discipline_class_v5_2']}; "
                    f"sportsbet={fmt(row['sportsbet_price'])}; rated={fmt(row['rated_price'])}; "
                    f"flags={row['discipline_flags_v5_2']}"
                ),
            )
        )
    return rows


def build_summary(filtered: pd.DataFrame) -> pd.DataFrame:
    primary = filtered[filtered["primary_research_candidate_v5_2"]].copy()
    review_only = filtered[~filtered["primary_research_candidate_v5_2"]].copy()

    rows: list[dict[str, object]] = [
        summary_row(
            "overall",
            "total_clean_overlays",
            len(filtered),
            filtered["overlay_pct"].mean(),
            filtered["overlay_pct"].max(),
            filtered["overlay_pct"].min(),
            "Review-only discipline filter. No execution recommendation is produced.",
        ),
        summary_row(
            "overall",
            "primary_research_candidates",
            int(filtered["primary_research_candidate_v5_2"].sum()),
            primary["overlay_pct"].mean(),
            primary["overlay_pct"].max(),
            primary["overlay_pct"].min(),
        ),
        summary_row(
            "overall",
            "longshot_research_only",
            int(filtered["longshot_research_only_v5_2"].sum()),
            filtered.loc[filtered["longshot_research_only_v5_2"], "overlay_pct"].mean(),
            filtered.loc[filtered["longshot_research_only_v5_2"], "overlay_pct"].max(),
            filtered.loc[filtered["longshot_research_only_v5_2"], "overlay_pct"].min(),
        ),
        summary_row(
            "overall",
            "market_shape_review",
            int(filtered["market_shape_review_v5_2"].sum()),
            filtered.loc[filtered["market_shape_review_v5_2"], "overlay_pct"].mean(),
            filtered.loc[filtered["market_shape_review_v5_2"], "overlay_pct"].max(),
            filtered.loc[filtered["market_shape_review_v5_2"], "overlay_pct"].min(),
        ),
        summary_row(
            "overall",
            "extreme_overlay_review",
            int(filtered["extreme_overlay_review_v5_2"].sum()),
            filtered.loc[filtered["extreme_overlay_review_v5_2"], "overlay_pct"].mean(),
            filtered.loc[filtered["extreme_overlay_review_v5_2"], "overlay_pct"].max(),
            filtered.loc[filtered["extreme_overlay_review_v5_2"], "overlay_pct"].min(),
        ),
    ]

    rows.extend(aggregate_rows(filtered, "candidates_by_race", "race"))
    rows.extend(aggregate_rows(filtered, "candidates_by_price_role", "price_role"))
    rows.extend(aggregate_rows(filtered, "discipline_class_counts", "discipline_class_v5_2"))

    top_primary = primary.sort_values("overlay_pct", ascending=False).head(20)
    if len(top_primary):
        rows.extend(runner_rows(top_primary, "top_primary_candidates"))
    else:
        rows.append(
            summary_row(
                "top_primary_candidates",
                "NONE",
                0,
                notes="No midprice clean overlays in races with fewer than 3 clean overlays.",
            )
        )

    blocked = review_only.sort_values("overlay_pct", ascending=False).head(20)
    rows.extend(runner_rows(blocked, "top_blocked_review_only_overlays"))

    summary = pd.DataFrame(rows)
    summary["built_at_overlay_discipline_filter_v5_2"] = datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )
    return summary


def main() -> None:
    print("=" * 90)
    print("EDGEIQ OVERLAY DISCIPLINE FILTER V5.2 - REVIEW ONLY")
    print("=" * 90)

    clean_board = load_input()
    filtered = build_filter(clean_board)
    summary = build_summary(filtered)

    filtered.to_csv(OUT, index=False)
    summary.to_csv(SUMMARY, index=False)

    print(f"input: {INPUT}")
    print(f"wrote: {OUT}")
    print(f"wrote: {SUMMARY}")
    print()
    print(summary[summary["section"].eq("overall")].to_string(index=False))
    print()
    print(summary[summary["section"].eq("candidates_by_race")].to_string(index=False))
    print()
    print(summary[summary["section"].eq("candidates_by_price_role")].to_string(index=False))
    print()
    print(summary[summary["section"].eq("discipline_class_counts")].to_string(index=False))
    print()
    print(summary[summary["section"].eq("top_primary_candidates")].to_string(index=False))
    print()
    print(summary[summary["section"].eq("top_blocked_review_only_overlays")].head(20).to_string(index=False))
    print("=" * 90)


if __name__ == "__main__":
    main()
