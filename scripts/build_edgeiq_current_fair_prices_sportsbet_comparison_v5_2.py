from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

FAIR_PRICES = DATA / "edgeiq_current_fair_prices_review_v5_2.csv"
SPORTSBET_SOURCE = DATA / "sportsbet_live_market_full_day_v5_2.csv"

OUT = DATA / "edgeiq_current_fair_prices_sportsbet_comparison_v5_2.csv"
AUDIT = DATA / "edgeiq_current_fair_prices_sportsbet_comparison_v5_2_audit.csv"

NEUTRAL_OVERLAY_BAND = 0.02
POSSIBLE_FAKE_OVERLAY_THRESHOLD = 0.50


def norm(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).upper().strip().split())


def horse_key(value: object) -> str:
    text = norm(value)
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def clean_race_no(value: object) -> str:
    text = str(value).strip()
    return text[:-2] if text.endswith(".0") else text


def number(value: object) -> float:
    return pd.to_numeric(value, errors="coerce")


def fmt(value: object, decimals: int = 6) -> str:
    parsed = number(value)
    if pd.isna(parsed):
        return ""
    return f"{float(parsed):.{decimals}f}"


def overlay_status(value: object) -> str:
    overlay = number(value)
    if pd.isna(overlay):
        return "NO_COMPARISON"
    if overlay > NEUTRAL_OVERLAY_BAND:
        return "OVERLAY"
    if overlay < -NEUTRAL_OVERLAY_BAND:
        return "UNDERLAY"
    return "NEUTRAL"


def has_flag(flags: str, flag: str) -> bool:
    return flag in str(flags).split("|")


def conservative_flags(row: pd.Series) -> str:
    flags = ["REVIEW_ONLY"]

    rated_status = norm(row.get("rated_price_status_v5_2_review", ""))
    if rated_status == "BASELINE_NO_HISTORY":
        flags.append("NO_HISTORY")

    sportsbet_price = number(row.get("sportsbet_price"))
    rated_price = number(row.get("rated_price_v5_2_review"))
    if pd.isna(sportsbet_price):
        flags.append("SPORTSBET_MISSING")
    if pd.isna(rated_price):
        flags.append("RATED_PRICE_MISSING")

    if (pd.notna(sportsbet_price) and sportsbet_price > 100) or (
        pd.notna(rated_price) and rated_price > 100
    ):
        flags.append("LONGSHOT_GT_100")

    if (pd.notna(sportsbet_price) and sportsbet_price < 2) or (
        pd.notna(rated_price) and rated_price < 2
    ):
        flags.append("FAVOURITE_UNDER_2")

    overlay = number(row.get("overlay_v5_2_review"))
    confidence = norm(row.get("projection_confidence_v5_2", ""))
    if (
        pd.notna(overlay)
        and overlay >= POSSIBLE_FAKE_OVERLAY_THRESHOLD
        and (
            "NO_HISTORY" in flags
            or "LONGSHOT_GT_100" in flags
            or confidence == "LOW"
        )
    ):
        flags.append("POSSIBLE_FAKE_OVERLAY")

    return "|".join(flags)


def audit_row(
    section: str,
    metric: str,
    value: object = "",
    count: object = "",
    race_no: object = "",
    race_time: object = "",
    race_class_corrected: object = "",
    horse: object = "",
    overlay: object = "",
    sportsbet_price: object = "",
    rated_price: object = "",
    probability_sum: object = "",
    flags: object = "",
    notes: object = "",
) -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "count": count,
        "race_no": race_no,
        "race_time": race_time,
        "race_class_corrected": race_class_corrected,
        "horse": horse,
        "overlay_v5_2_review": overlay,
        "sportsbet_price": sportsbet_price,
        "rated_price_v5_2_review": rated_price,
        "probability_sum": probability_sum,
        "conservative_flags_v5_2": flags,
        "notes": notes,
    }


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not FAIR_PRICES.exists():
        raise FileNotFoundError(f"Missing fair-price input: {FAIR_PRICES}")
    if not SPORTSBET_SOURCE.exists():
        raise FileNotFoundError(f"Missing Sportsbet full-day input: {SPORTSBET_SOURCE}")

    fair = pd.read_csv(FAIR_PRICES, dtype=str, keep_default_na=False, low_memory=False)
    sportsbet = pd.read_csv(SPORTSBET_SOURCE, dtype=str, keep_default_na=False, low_memory=False)

    fair_required = {
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
        "rated_probability_v5_2_review",
        "rated_price_v5_2_review",
        "rated_price_status_v5_2_review",
        "price_rank_in_race_v5_2",
        "projection_gap_v5_2",
        "projection_band_v5_2",
        "projection_confidence_v5_2",
        "field_size",
        "priced_runner_count",
        "no_history_count",
    }
    sportsbet_required = {
        "race_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "sportsbet_price",
    }

    missing = {
        "fair_prices": sorted(fair_required.difference(fair.columns)),
        "sportsbet_full_day": sorted(sportsbet_required.difference(sportsbet.columns)),
    }
    missing = {name: cols for name, cols in missing.items() if cols}
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    return fair, sportsbet


def prepare_fair(fair: pd.DataFrame) -> pd.DataFrame:
    out = fair.copy()
    out["race_no"] = out["race_no"].map(clean_race_no)
    out["track_match"] = out["track"].map(norm)
    out["fair_horse_key_match"] = out.apply(
        lambda row: horse_key(row.get("horse_key", "")) or horse_key(row.get("horse", "")),
        axis=1,
    )
    out["rated_probability_v5_2_review"] = pd.to_numeric(
        out["rated_probability_v5_2_review"], errors="coerce"
    )
    out["rated_price_v5_2_review"] = pd.to_numeric(
        out["rated_price_v5_2_review"], errors="coerce"
    )
    out["price_rank_in_race_v5_2"] = pd.to_numeric(
        out["price_rank_in_race_v5_2"], errors="coerce"
    )
    return out


def prepare_sportsbet(sportsbet: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    out = sportsbet.copy()
    out["race_no"] = out["race_no"].map(clean_race_no)
    out["track_match"] = out["track"].map(norm)
    out["sportsbet_price"] = pd.to_numeric(out["sportsbet_price"], errors="coerce")
    out["sportsbet_horse_key_match"] = out.apply(
        lambda row: horse_key(row.get("horse_key", "")) or horse_key(row.get("horse", "")),
        axis=1,
    )

    if "price_win" in out.columns:
        out["price_win"] = pd.to_numeric(out["price_win"], errors="coerce")

    out = out[out["sportsbet_horse_key_match"].ne("")].copy()
    out = out.sort_values(
        [
            "race_date",
            "track_match",
            "race_no",
            "sportsbet_horse_key_match",
            "match_confidence" if "match_confidence" in out.columns else "horse",
        ]
    )
    deduped = out.drop_duplicates(
        ["race_date", "track_match", "race_no", "sportsbet_horse_key_match"],
        keep="first",
    ).copy()
    duplicate_count = len(out) - len(deduped)
    return deduped, duplicate_count


def build_comparison(
    fair: pd.DataFrame, sportsbet: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    sportsbet_optional_cols = [
        "price_win",
        "market_source",
        "market_captured_at",
        "capture_timestamp_utc",
        "event_id",
        "selection_id",
        "match_confidence",
        "is_scratched",
        "runner_status",
        "selection_status",
        "source_status",
        "source_url",
        "event_name",
        "market_type",
        "market_name",
        "market_id",
        "bookmaker",
        "notes",
    ]
    sportsbet_cols = [
        "race_date",
        "track_match",
        "race_no",
        "sportsbet_horse_key_match",
        "horse",
        "sportsbet_price",
        *[col for col in sportsbet_optional_cols if col in sportsbet.columns],
    ]

    comparison = fair.merge(
        sportsbet[sportsbet_cols],
        left_on=["race_date", "track_match", "race_no", "fair_horse_key_match"],
        right_on=["race_date", "track_match", "race_no", "sportsbet_horse_key_match"],
        how="left",
        suffixes=("", "_sportsbet"),
    )

    comparison["sportsbet_match_status_v5_2"] = comparison["sportsbet_price"].notna().map(
        {True: "MATCHED_SPORTSBET", False: "MISSING_SPORTSBET"}
    )
    comparison["overlay_v5_2_review"] = (
        comparison["sportsbet_price"] / comparison["rated_price_v5_2_review"] - 1.0
    )
    comparison["overlay_status_v5_2_review"] = comparison["overlay_v5_2_review"].apply(
        overlay_status
    )
    comparison["conservative_flags_v5_2"] = comparison.apply(conservative_flags, axis=1)
    comparison["sportsbet_source_file_v5_2"] = SPORTSBET_SOURCE.name
    comparison["built_at_sportsbet_comparison_v5_2"] = datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")

    unmatched_sportsbet = sportsbet.merge(
        fair[["race_date", "track_match", "race_no", "fair_horse_key_match"]],
        left_on=["race_date", "track_match", "race_no", "sportsbet_horse_key_match"],
        right_on=["race_date", "track_match", "race_no", "fair_horse_key_match"],
        how="left",
        indicator=True,
    )
    unmatched_sportsbet = unmatched_sportsbet[unmatched_sportsbet["_merge"].eq("left_only")].copy()

    return comparison, unmatched_sportsbet


def write_comparison(comparison: pd.DataFrame) -> None:
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
        "rated_probability_v5_2_review",
        "rated_price_v5_2_review",
        "rated_price_status_v5_2_review",
        "price_rank_in_race_v5_2",
        "sportsbet_price",
        "overlay_v5_2_review",
        "overlay_status_v5_2_review",
        "sportsbet_match_status_v5_2",
        "conservative_flags_v5_2",
        "projection_gap_v5_2",
        "projection_band_v5_2",
        "projection_confidence_v5_2",
        "field_size",
        "priced_runner_count",
        "no_history_count",
        "sportsbet_source_file_v5_2",
        "market_source",
        "market_captured_at",
        "capture_timestamp_utc",
        "event_id",
        "selection_id",
        "match_confidence",
        "event_name",
        "market_type",
        "market_name",
        "market_id",
        "is_scratched",
        "runner_status",
        "selection_status",
        "source_status",
        "source_url",
        "built_at_sportsbet_comparison_v5_2",
    ]
    existing_cols = [col for col in output_cols if col in comparison.columns]
    comparison.to_csv(OUT, index=False, columns=existing_cols)


def add_race_coverage_rows(rows: list[dict[str, object]], comparison: pd.DataFrame) -> None:
    grouped = comparison.groupby(["race_date", "track", "race_no"], dropna=False)
    for (race_date, track, race_no), group in grouped:
        matched = group["sportsbet_match_status_v5_2"].eq("MATCHED_SPORTSBET")
        probability_sum = group["rated_probability_v5_2_review"].sum(min_count=1)
        event_ids = ""
        if "event_id" in group.columns:
            event_ids = ",".join(
                sorted(
                    {
                        str(value)
                        for value in group["event_id"].dropna().tolist()
                        if str(value).strip()
                    }
                )
            )
        rows.append(
            audit_row(
                "race_coverage",
                "race",
                count=len(group),
                race_no=race_no,
                race_time=group["race_time"].iloc[0],
                race_class_corrected=group["race_class_corrected"].iloc[0],
                probability_sum=fmt(probability_sum),
                notes=(
                    f"{race_date} {track}; fair_rows={len(group)}; "
                    f"matched={int(matched.sum())}; missing={int((~matched).sum())}; "
                    f"sportsbet_prices={int(group['sportsbet_price'].notna().sum())}; "
                    f"event_ids={event_ids}"
                ),
            )
        )


def add_top_rows(
    rows: list[dict[str, object]],
    matched: pd.DataFrame,
    section: str,
    ascending: bool,
) -> None:
    status = "UNDERLAY" if ascending else "OVERLAY"
    candidates = matched[matched["overlay_status_v5_2_review"].eq(status)].copy()
    candidates = candidates.sort_values("overlay_v5_2_review", ascending=ascending).head(20)
    for _, row in candidates.iterrows():
        rows.append(
            audit_row(
                section,
                "overlay",
                race_no=row["race_no"],
                race_time=row["race_time"],
                race_class_corrected=row["race_class_corrected"],
                horse=row["horse"],
                overlay=fmt(row["overlay_v5_2_review"]),
                sportsbet_price=fmt(row["sportsbet_price"], decimals=2),
                rated_price=fmt(row["rated_price_v5_2_review"], decimals=2),
                flags=row["conservative_flags_v5_2"],
                notes=(
                    f"status={row['rated_price_status_v5_2_review']}; "
                    f"projection_confidence={row['projection_confidence_v5_2']}; "
                    f"projection_band={row['projection_band_v5_2']}"
                ),
            )
        )


def add_probability_sum_rows(rows: list[dict[str, object]], comparison: pd.DataFrame) -> None:
    probability_sums = comparison.groupby(
        ["race_date", "track", "race_no"], dropna=False
    )["rated_probability_v5_2_review"].sum(min_count=1)
    for (race_date, track, race_no), probability_sum in probability_sums.items():
        rows.append(
            audit_row(
                "probability_sums",
                "rated_probability_sum",
                value=fmt(probability_sum),
                race_no=race_no,
                probability_sum=fmt(probability_sum),
                notes=f"{race_date} {track} R{race_no}",
            )
        )


def build_audit(
    fair: pd.DataFrame,
    sportsbet_raw: pd.DataFrame,
    sportsbet: pd.DataFrame,
    sportsbet_duplicate_count: int,
    comparison: pd.DataFrame,
    unmatched_sportsbet: pd.DataFrame,
) -> pd.DataFrame:
    matched = comparison[comparison["sportsbet_match_status_v5_2"].eq("MATCHED_SPORTSBET")].copy()

    fair_races = fair[["race_date", "track", "race_no"]].drop_duplicates().shape[0]
    sportsbet_races = sportsbet[["race_date", "track_match", "race_no"]].drop_duplicates().shape[0]
    matched_races = matched[["race_date", "track", "race_no"]].drop_duplicates().shape[0]

    sportsbet_price_missing_count = int(comparison["sportsbet_price"].isna().sum())
    rated_price_missing_count = int(comparison["rated_price_v5_2_review"].isna().sum())
    overlay_count = int(comparison["overlay_status_v5_2_review"].eq("OVERLAY").sum())
    underlay_count = int(comparison["overlay_status_v5_2_review"].eq("UNDERLAY").sum())
    neutral_count = int(comparison["overlay_status_v5_2_review"].eq("NEUTRAL").sum())
    no_history_overlay_count = int(
        (
            comparison["rated_price_status_v5_2_review"].eq("BASELINE_NO_HISTORY")
            & comparison["overlay_status_v5_2_review"].eq("OVERLAY")
        ).sum()
    )
    longshot_flag_count = int(
        comparison["conservative_flags_v5_2"].apply(lambda flags: has_flag(flags, "LONGSHOT_GT_100")).sum()
    )
    possible_fake_overlay_count = int(
        comparison["conservative_flags_v5_2"].apply(
            lambda flags: has_flag(flags, "POSSIBLE_FAKE_OVERLAY")
        ).sum()
    )
    no_history_flag_count = int(
        comparison["conservative_flags_v5_2"].apply(lambda flags: has_flag(flags, "NO_HISTORY")).sum()
    )

    rows: list[dict[str, object]] = [
        audit_row("overall", "fair_price_rows_loaded", len(fair)),
        audit_row(
            "overall",
            "sportsbet_rows_loaded",
            len(sportsbet_raw),
            notes=f"source={SPORTSBET_SOURCE.name}",
        ),
        audit_row("overall", "sportsbet_rows_after_dedup", len(sportsbet)),
        audit_row("overall", "sportsbet_duplicate_rows_removed", sportsbet_duplicate_count),
        audit_row("overall", "fair_price_races", fair_races),
        audit_row("overall", "sportsbet_races", sportsbet_races),
        audit_row("overall", "races_matched", matched_races),
        audit_row("overall", "matched_runners", len(matched)),
        audit_row("overall", "unmatched_fair_price_runners", sportsbet_price_missing_count),
        audit_row("overall", "unmatched_sportsbet_runners", len(unmatched_sportsbet)),
        audit_row("overall", "sportsbet_price_missing_count", sportsbet_price_missing_count),
        audit_row("overall", "rated_price_missing_count", rated_price_missing_count),
        audit_row("overall", "overlay_count", overlay_count, notes=f"overlay > {NEUTRAL_OVERLAY_BAND:.2%}"),
        audit_row("overall", "underlay_count", underlay_count, notes=f"underlay < -{NEUTRAL_OVERLAY_BAND:.2%}"),
        audit_row("overall", "neutral_count", neutral_count, notes=f"neutral within +/-{NEUTRAL_OVERLAY_BAND:.2%}"),
        audit_row("overall", "max_overlay", fmt(matched["overlay_v5_2_review"].max()) if len(matched) else ""),
        audit_row("overall", "min_overlay", fmt(matched["overlay_v5_2_review"].min()) if len(matched) else ""),
        audit_row("overall", "no_history_runner_overlay_count", no_history_overlay_count),
        audit_row("overall", "no_history_flag_count", no_history_flag_count),
        audit_row("overall", "longshot_flag_count", longshot_flag_count),
        audit_row("overall", "possible_fake_overlay_count", possible_fake_overlay_count),
    ]

    add_race_coverage_rows(rows, comparison)
    add_probability_sum_rows(rows, comparison)
    add_top_rows(rows, matched, "top_20_overlays", ascending=False)
    add_top_rows(rows, matched, "top_20_underlays", ascending=True)

    warnings: list[str] = []
    if len(fair) != 87:
        warnings.append(f"expected 87 fair-price rows, found {len(fair)}")
    if len(sportsbet_raw) != 87:
        warnings.append(f"expected 87 Sportsbet rows, found {len(sportsbet_raw)}")
    if len(matched) != len(fair):
        warnings.append(f"matched {len(matched)} of {len(fair)} fair-price runners")
    if sportsbet_price_missing_count:
        warnings.append(f"{sportsbet_price_missing_count} fair-price runners missing Sportsbet price")
    if matched_races != fair_races:
        warnings.append(f"matched {matched_races} of {fair_races} fair-price races")
    if rated_price_missing_count:
        warnings.append(f"{rated_price_missing_count} fair-price rows missing rated price")
    if longshot_flag_count:
        warnings.append(f"{longshot_flag_count} longshot flag rows present")
    if possible_fake_overlay_count:
        warnings.append(f"{possible_fake_overlay_count} possible fake overlay flags present")
    if not warnings:
        warnings.append("no sanity warnings")

    for warning in warnings:
        rows.append(audit_row("sanity_warnings", "warning", notes=warning))

    audit = pd.DataFrame(rows)
    audit["built_at"] = comparison["built_at_sportsbet_comparison_v5_2"].iloc[0]
    return audit


def main() -> None:
    print("=" * 90)
    print("EDGEIQ CURRENT FAIR PRICES SPORTSBET COMPARISON V5.2 - FULL-DAY REVIEW ONLY")
    print("=" * 90)

    fair_raw, sportsbet_raw = load_inputs()
    fair = prepare_fair(fair_raw)
    sportsbet, sportsbet_duplicate_count = prepare_sportsbet(sportsbet_raw)
    comparison, unmatched_sportsbet = build_comparison(fair, sportsbet)

    write_comparison(comparison)
    audit = build_audit(
        fair,
        sportsbet_raw,
        sportsbet,
        sportsbet_duplicate_count,
        comparison,
        unmatched_sportsbet,
    )
    audit.to_csv(AUDIT, index=False)

    print(f"Sportsbet source: {SPORTSBET_SOURCE}")
    print(f"wrote: {OUT}")
    print(f"wrote: {AUDIT}")
    print()
    print(audit[audit["section"].isin(["overall", "sanity_warnings"])].to_string(index=False))
    print()
    print(audit[audit["section"].eq("race_coverage")].to_string(index=False))
    print()
    print(audit[audit["section"].eq("probability_sums")].to_string(index=False))
    print()
    print(audit[audit["section"].eq("top_20_overlays")].head(20).to_string(index=False))
    print()
    print(audit[audit["section"].eq("top_20_underlays")].head(20).to_string(index=False))
    print("=" * 90)


if __name__ == "__main__":
    main()
