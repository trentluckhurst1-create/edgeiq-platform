from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT = DATA / "edgeiq_current_fair_prices_sportsbet_comparison_v5_2.csv"
OUT = DATA / "edgeiq_overlay_quality_audit_v5_2.csv"
SUMMARY = DATA / "edgeiq_overlay_quality_audit_v5_2_summary.csv"

LONGSHOT_PRICE_THRESHOLD = 100.0
EXTREME_PRICE_THRESHOLD = 200.0


def norm(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).upper().strip().split())


def to_number(value: object) -> float:
    return pd.to_numeric(value, errors="coerce")


def fmt(value: object, decimals: int = 6) -> str:
    parsed = to_number(value)
    if pd.isna(parsed):
        return ""
    return f"{float(parsed):.{decimals}f}"


def has_flag(flags: object, flag: str) -> bool:
    return flag in str(flags).split("|")


def price_band(price: object) -> str:
    value = to_number(price)
    if pd.isna(value):
        return "NO_PRICE"
    if value < 2:
        return "LT_2"
    if value < 4:
        return "2_TO_4"
    if value < 8:
        return "4_TO_8"
    if value < 15:
        return "8_TO_15"
    if value < 30:
        return "15_TO_30"
    if value < 50:
        return "30_TO_50"
    if value <= 100:
        return "50_TO_100"
    if value <= 200:
        return "100_TO_200"
    return "GT_200"


def price_role(price: object) -> str:
    value = to_number(price)
    if pd.isna(value):
        return "NO_PRICE"
    if value < 2:
        return "FAVOURITE"
    if value < 10:
        return "MIDPRICE"
    return "LONGSHOT"


def overlay_percentage_band(overlay: object) -> str:
    value = to_number(overlay)
    if pd.isna(value):
        return "NO_COMPARISON"
    pct = value * 100.0
    if pct <= -50:
        return "UNDERLAY_LE_-50"
    if pct <= -20:
        return "UNDERLAY_-50_TO_-20"
    if pct < -2:
        return "UNDERLAY_-20_TO_-2"
    if pct <= 2:
        return "NEUTRAL_-2_TO_2"
    if pct < 20:
        return "OVERLAY_2_TO_20"
    if pct < 50:
        return "OVERLAY_20_TO_50"
    if pct < 100:
        return "OVERLAY_50_TO_100"
    if pct < 200:
        return "OVERLAY_100_TO_200"
    return "OVERLAY_GT_200"


def overlay_percent(overlay: object) -> float:
    value = to_number(overlay)
    if pd.isna(value):
        return pd.NA
    return float(value) * 100.0


def overlay_quality_class(row: pd.Series) -> str:
    status = norm(row.get("overlay_status_v5_2_review", ""))
    if status == "UNDERLAY":
        return "UNDERLAY"
    if status == "NEUTRAL":
        return "NEUTRAL"
    if status != "OVERLAY":
        return "NEUTRAL"

    if bool(row.get("no_history_flag_v5_2", False)):
        return "NO_HISTORY_BLOCK"
    if bool(row.get("possible_fake_overlay_flag_v5_2", False)):
        return "POSSIBLE_FAKE_OVERLAY"
    if bool(row.get("extreme_price_flag_v5_2", False)):
        return "EXTREME_PRICE_BLOCK"
    if bool(row.get("longshot_flag_v5_2", False)):
        return "LONGSHOT_REVIEW"
    return "CLEAN_RESEARCH_OVERLAY"


def quality_reason(row: pd.Series) -> str:
    quality = row["overlay_quality_class_v5_2"]
    status = norm(row.get("overlay_status_v5_2_review", ""))
    if quality == "UNDERLAY":
        return "Sportsbet price is below review fair price by more than the neutral band."
    if quality == "NEUTRAL":
        return "Sportsbet price is within the neutral overlay band."
    if quality == "NO_HISTORY_BLOCK":
        return "Overlay is blocked because the runner uses baseline no-history pricing."
    if quality == "POSSIBLE_FAKE_OVERLAY":
        return "Overlay is flagged as possible fake value by conservative comparison flags."
    if quality == "EXTREME_PRICE_BLOCK":
        return "Overlay is blocked because Sportsbet or review fair price is above the extreme price threshold."
    if quality == "LONGSHOT_REVIEW":
        return "Overlay is longshot-priced and requires separate research review."
    if quality == "CLEAN_RESEARCH_OVERLAY":
        return "Overlay has rated history and no conservative longshot, no-history, fake-overlay, or extreme-price block."
    return f"Unclassified comparison status: {status}"


def load_input() -> pd.DataFrame:
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing comparison input: {INPUT}")

    df = pd.read_csv(INPUT, dtype=str, keep_default_na=False, low_memory=False)
    required = {
        "race_date",
        "track",
        "race_no",
        "race_time",
        "race_class_corrected",
        "horse",
        "horse_key",
        "rated_probability_v5_2_review",
        "rated_price_v5_2_review",
        "rated_price_status_v5_2_review",
        "sportsbet_price",
        "overlay_v5_2_review",
        "overlay_status_v5_2_review",
        "conservative_flags_v5_2",
        "projection_gap_v5_2",
        "projection_band_v5_2",
        "projection_confidence_v5_2",
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing required columns from comparison file: {missing}")
    return df


def build_runner_audit(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["race_no"] = out["race_no"].astype(str).str.replace(r"\.0$", "", regex=True)
    out["rated_probability_v5_2_review"] = pd.to_numeric(
        out["rated_probability_v5_2_review"], errors="coerce"
    )
    out["rated_price_v5_2_review"] = pd.to_numeric(
        out["rated_price_v5_2_review"], errors="coerce"
    )
    out["sportsbet_price"] = pd.to_numeric(out["sportsbet_price"], errors="coerce")
    out["overlay_v5_2_review"] = pd.to_numeric(out["overlay_v5_2_review"], errors="coerce")
    out["projection_gap_v5_2"] = pd.to_numeric(out["projection_gap_v5_2"], errors="coerce")

    out["race_key_v5_2"] = (
        out["race_date"].astype(str)
        + "_"
        + out["track"].astype(str)
        + "_R"
        + out["race_no"].astype(str)
    )
    out["history_bucket_v5_2"] = out["rated_price_status_v5_2_review"].map(norm).map(
        lambda value: "NO_HISTORY" if value == "BASELINE_NO_HISTORY" else "RATED_HISTORY"
    )
    out["sportsbet_price_band_v5_2"] = out["sportsbet_price"].apply(price_band)
    out["rated_price_band_v5_2"] = out["rated_price_v5_2_review"].apply(price_band)
    out["price_role_v5_2"] = out["sportsbet_price"].apply(price_role)
    out["overlay_percentage_v5_2"] = out["overlay_v5_2_review"].apply(overlay_percent)
    out["overlay_percentage_band_v5_2"] = out["overlay_v5_2_review"].apply(
        overlay_percentage_band
    )

    out["no_history_flag_v5_2"] = out["conservative_flags_v5_2"].apply(
        lambda flags: has_flag(flags, "NO_HISTORY")
    )
    out["longshot_flag_v5_2"] = out["conservative_flags_v5_2"].apply(
        lambda flags: has_flag(flags, "LONGSHOT_GT_100")
    )
    out["possible_fake_overlay_flag_v5_2"] = out["conservative_flags_v5_2"].apply(
        lambda flags: has_flag(flags, "POSSIBLE_FAKE_OVERLAY")
    )
    out["extreme_price_flag_v5_2"] = (
        (out["sportsbet_price"] > EXTREME_PRICE_THRESHOLD).fillna(False)
        | (out["rated_price_v5_2_review"] > EXTREME_PRICE_THRESHOLD).fillna(False)
    )

    out["overlay_quality_class_v5_2"] = out.apply(overlay_quality_class, axis=1)
    out["overlay_quality_reason_v5_2"] = out.apply(quality_reason, axis=1)
    out["built_at_overlay_quality_audit_v5_2"] = datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )

    output_cols = [
        "race_date",
        "track",
        "race_no",
        "race_time",
        "race_key_v5_2",
        "race_class_corrected",
        "horse",
        "horse_key",
        "saddlecloth",
        "barrier",
        "jockey",
        "trainer",
        "rated_probability_v5_2_review",
        "rated_price_v5_2_review",
        "rated_price_status_v5_2_review",
        "history_bucket_v5_2",
        "sportsbet_price",
        "sportsbet_price_band_v5_2",
        "rated_price_band_v5_2",
        "price_role_v5_2",
        "overlay_v5_2_review",
        "overlay_percentage_v5_2",
        "overlay_status_v5_2_review",
        "overlay_percentage_band_v5_2",
        "overlay_quality_class_v5_2",
        "overlay_quality_reason_v5_2",
        "no_history_flag_v5_2",
        "longshot_flag_v5_2",
        "possible_fake_overlay_flag_v5_2",
        "extreme_price_flag_v5_2",
        "conservative_flags_v5_2",
        "projection_gap_v5_2",
        "projection_band_v5_2",
        "projection_confidence_v5_2",
        "field_size",
        "priced_runner_count",
        "no_history_count",
        "event_id",
        "selection_id",
        "match_confidence",
        "market_source",
        "market_captured_at",
        "sportsbet_source_file_v5_2",
        "built_at_overlay_quality_audit_v5_2",
    ]
    return out[[col for col in output_cols if col in out.columns]].copy()


def summary_row(
    section: str,
    group: str,
    runner_count: int,
    overlay_count: int,
    underlay_count: int,
    neutral_count: int,
    clean_overlay_count: int,
    fake_overlay_count: int,
    no_history_block_count: int,
    longshot_review_count: int,
    extreme_price_block_count: int,
    avg_overlay_pct: object,
    max_overlay_pct: object,
    min_overlay_pct: object,
    notes: str = "",
) -> dict[str, object]:
    return {
        "section": section,
        "group": group,
        "runner_count": runner_count,
        "overlay_count": overlay_count,
        "underlay_count": underlay_count,
        "neutral_count": neutral_count,
        "clean_research_overlay_count": clean_overlay_count,
        "possible_fake_overlay_count": fake_overlay_count,
        "no_history_block_count": no_history_block_count,
        "longshot_review_count": longshot_review_count,
        "extreme_price_block_count": extreme_price_block_count,
        "avg_overlay_pct": fmt(avg_overlay_pct, decimals=2),
        "max_overlay_pct": fmt(max_overlay_pct, decimals=2),
        "min_overlay_pct": fmt(min_overlay_pct, decimals=2),
        "notes": notes,
    }


def aggregate_section(audit: pd.DataFrame, section: str, column: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for group, frame in audit.groupby(column, dropna=False):
        rows.append(
            summary_row(
                section=section,
                group=str(group),
                runner_count=len(frame),
                overlay_count=int(frame["overlay_status_v5_2_review"].eq("OVERLAY").sum()),
                underlay_count=int(frame["overlay_status_v5_2_review"].eq("UNDERLAY").sum()),
                neutral_count=int(frame["overlay_status_v5_2_review"].eq("NEUTRAL").sum()),
                clean_overlay_count=int(
                    frame["overlay_quality_class_v5_2"].eq("CLEAN_RESEARCH_OVERLAY").sum()
                ),
                fake_overlay_count=int(
                    frame["overlay_quality_class_v5_2"].eq("POSSIBLE_FAKE_OVERLAY").sum()
                ),
                no_history_block_count=int(
                    frame["overlay_quality_class_v5_2"].eq("NO_HISTORY_BLOCK").sum()
                ),
                longshot_review_count=int(
                    frame["overlay_quality_class_v5_2"].eq("LONGSHOT_REVIEW").sum()
                ),
                extreme_price_block_count=int(
                    frame["overlay_quality_class_v5_2"].eq("EXTREME_PRICE_BLOCK").sum()
                ),
                avg_overlay_pct=frame["overlay_percentage_v5_2"].mean(),
                max_overlay_pct=frame["overlay_percentage_v5_2"].max(),
                min_overlay_pct=frame["overlay_percentage_v5_2"].min(),
            )
        )
    return rows


def top_rows(audit: pd.DataFrame, section: str, ascending: bool) -> list[dict[str, object]]:
    frame = audit.sort_values("overlay_percentage_v5_2", ascending=ascending).head(20)
    rows: list[dict[str, object]] = []
    for _, row in frame.iterrows():
        rows.append(
            {
                "section": section,
                "group": row["horse"],
                "runner_count": 1,
                "overlay_count": 1 if row["overlay_status_v5_2_review"] == "OVERLAY" else 0,
                "underlay_count": 1 if row["overlay_status_v5_2_review"] == "UNDERLAY" else 0,
                "neutral_count": 1 if row["overlay_status_v5_2_review"] == "NEUTRAL" else 0,
                "clean_research_overlay_count": 1
                if row["overlay_quality_class_v5_2"] == "CLEAN_RESEARCH_OVERLAY"
                else 0,
                "possible_fake_overlay_count": 1
                if row["overlay_quality_class_v5_2"] == "POSSIBLE_FAKE_OVERLAY"
                else 0,
                "no_history_block_count": 1
                if row["overlay_quality_class_v5_2"] == "NO_HISTORY_BLOCK"
                else 0,
                "longshot_review_count": 1
                if row["overlay_quality_class_v5_2"] == "LONGSHOT_REVIEW"
                else 0,
                "extreme_price_block_count": 1
                if row["overlay_quality_class_v5_2"] == "EXTREME_PRICE_BLOCK"
                else 0,
                "avg_overlay_pct": fmt(row["overlay_percentage_v5_2"], decimals=2),
                "max_overlay_pct": fmt(row["overlay_percentage_v5_2"], decimals=2),
                "min_overlay_pct": fmt(row["overlay_percentage_v5_2"], decimals=2),
                "notes": (
                    f"R{row['race_no']} {row['race_time']} {row['race_class_corrected']}; "
                    f"class={row['overlay_quality_class_v5_2']}; "
                    f"sportsbet={fmt(row['sportsbet_price'], decimals=2)}; "
                    f"rated={fmt(row['rated_price_v5_2_review'], decimals=2)}"
                ),
            }
        )
    return rows


def build_summary(audit: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    rows.append(
        summary_row(
            section="overall",
            group="ALL",
            runner_count=len(audit),
            overlay_count=int(audit["overlay_status_v5_2_review"].eq("OVERLAY").sum()),
            underlay_count=int(audit["overlay_status_v5_2_review"].eq("UNDERLAY").sum()),
            neutral_count=int(audit["overlay_status_v5_2_review"].eq("NEUTRAL").sum()),
            clean_overlay_count=int(
                audit["overlay_quality_class_v5_2"].eq("CLEAN_RESEARCH_OVERLAY").sum()
            ),
            fake_overlay_count=int(
                audit["overlay_quality_class_v5_2"].eq("POSSIBLE_FAKE_OVERLAY").sum()
            ),
            no_history_block_count=int(
                audit["overlay_quality_class_v5_2"].eq("NO_HISTORY_BLOCK").sum()
            ),
            longshot_review_count=int(
                audit["overlay_quality_class_v5_2"].eq("LONGSHOT_REVIEW").sum()
            ),
            extreme_price_block_count=int(
                audit["overlay_quality_class_v5_2"].eq("EXTREME_PRICE_BLOCK").sum()
            ),
            avg_overlay_pct=audit["overlay_percentage_v5_2"].mean(),
            max_overlay_pct=audit["overlay_percentage_v5_2"].max(),
            min_overlay_pct=audit["overlay_percentage_v5_2"].min(),
            notes=(
                "Review-only overlay quality audit. Classes are diagnostics, not betting recommendations."
            ),
        )
    )

    rows.extend(aggregate_section(audit, "by_race", "race_key_v5_2"))
    rows.extend(aggregate_section(audit, "by_sportsbet_price_band", "sportsbet_price_band_v5_2"))
    rows.extend(aggregate_section(audit, "by_history_bucket", "history_bucket_v5_2"))
    rows.extend(aggregate_section(audit, "by_longshot_flag", "longshot_flag_v5_2"))
    rows.extend(aggregate_section(audit, "by_fake_overlay_flag", "possible_fake_overlay_flag_v5_2"))
    rows.extend(aggregate_section(audit, "by_extreme_price_flag", "extreme_price_flag_v5_2"))
    rows.extend(aggregate_section(audit, "by_price_role", "price_role_v5_2"))
    rows.extend(aggregate_section(audit, "by_overlay_percentage_band", "overlay_percentage_band_v5_2"))
    rows.extend(aggregate_section(audit, "by_quality_class", "overlay_quality_class_v5_2"))
    rows.extend(top_rows(audit[audit["overlay_status_v5_2_review"].eq("OVERLAY")], "top_20_overlays", False))
    rows.extend(top_rows(audit[audit["overlay_status_v5_2_review"].eq("UNDERLAY")], "top_20_underlays", True))

    summary = pd.DataFrame(rows)
    summary["built_at_overlay_quality_audit_v5_2"] = datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )
    return summary


def main() -> None:
    print("=" * 90)
    print("EDGEIQ OVERLAY QUALITY AUDIT V5.2 - REVIEW ONLY")
    print("=" * 90)

    comparison = load_input()
    audit = build_runner_audit(comparison)
    summary = build_summary(audit)

    audit.to_csv(OUT, index=False)
    summary.to_csv(SUMMARY, index=False)

    print(f"input: {INPUT}")
    print(f"wrote: {OUT}")
    print(f"wrote: {SUMMARY}")
    print()
    print(summary[summary["section"].eq("overall")].to_string(index=False))
    print()
    print(summary[summary["section"].eq("by_quality_class")].to_string(index=False))
    print()
    print(summary[summary["section"].eq("by_race")].to_string(index=False))
    print()
    print(summary[summary["section"].eq("by_overlay_percentage_band")].to_string(index=False))
    print("=" * 90)


if __name__ == "__main__":
    main()
