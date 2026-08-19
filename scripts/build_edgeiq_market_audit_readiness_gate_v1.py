from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

WATCH_PATH = DATA / "edgeiq_pre_result_market_history_warehouse_v1_coverage_watch.csv"
JOIN_SUMMARY_PATH = DATA / "edgeiq_pre_result_market_rank1_join_audit_v1_summary.csv"

OUTPUT_MAIN = DATA / "edgeiq_market_audit_readiness_gate_v1.csv"
OUTPUT_SUMMARY = DATA / "edgeiq_market_audit_readiness_gate_v1_summary.csv"

EXPECTED_ENV_BANDS = ["POOR", "NEGATIVE", "NEUTRAL", "POSITIVE", "ELITE"]


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def parse_int(value: object) -> int:
    text = clean_text(value)
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def parse_float(value: object) -> float:
    text = clean_text(value)
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def as_flag(value: bool) -> str:
    return "YES" if value else "NO"


def load_watch_row() -> pd.Series:
    if not WATCH_PATH.exists():
        raise FileNotFoundError(f"Missing input file: {WATCH_PATH}")
    df = pd.read_csv(WATCH_PATH, dtype=str, keep_default_na=False)
    if df.empty:
        raise ValueError("Coverage watch file exists but has no rows")
    return df.iloc[-1]


def load_join_summary() -> dict[str, str]:
    if not JOIN_SUMMARY_PATH.exists():
        raise FileNotFoundError(f"Missing input file: {JOIN_SUMMARY_PATH}")
    df = pd.read_csv(JOIN_SUMMARY_PATH, dtype=str, keep_default_na=False)
    if df.empty:
        raise ValueError("Join audit summary file exists but has no rows")
    return {clean_text(row["metric"]): clean_text(row["value"]) for _, row in df.iterrows()}


def main() -> None:
    run_ts = datetime.now().astimezone().isoformat(timespec="seconds")
    watch = load_watch_row()
    join_summary = load_join_summary()

    warehouse_rows = parse_int(watch.get("warehouse_rows", "0"))
    warehouse_unique_dates = parse_int(watch.get("warehouse_unique_meeting_dates_v1", "0"))
    warehouse_unique_races = parse_int(watch.get("warehouse_unique_races_v1", "0"))
    warehouse_unique_horses = parse_int(watch.get("warehouse_unique_horses_v1", "0"))

    matched_rank1_rows_watch = parse_int(watch.get("rank1_matched_rows_v1", "0"))
    matched_rank1_rows_summary = parse_int(join_summary.get("matched_rank1_rows", "0"))
    matched_rank1_rows = matched_rank1_rows_summary or matched_rank1_rows_watch
    matched_dates = parse_int(watch.get("matched_dates_v1", "0"))
    matched_tracks = parse_int(watch.get("matched_tracks_v1", "0"))
    matched_environment_band_count = parse_int(watch.get("matched_environment_band_count_v1", "0"))
    matched_environment_bands_raw = clean_text(watch.get("matched_environment_bands_v1", ""))
    matched_environment_bands = [band for band in matched_environment_bands_raw.split("|") if band]
    matched_environment_band_set = set(matched_environment_bands)
    missing_environment_bands = [band for band in EXPECTED_ENV_BANDS if band not in matched_environment_band_set]

    rank1_rows = parse_int(join_summary.get("rank1_rows", watch.get("rank1_rows_v1", "0")))
    matched_market_rows = parse_int(join_summary.get("matched_market_rows", "0"))
    matched_rank1_rows_with_best_price = parse_int(join_summary.get("matched_rank1_rows_with_best_price", "0"))
    rank1_coverage_pct = parse_float(join_summary.get("rank1_coverage_pct", watch.get("rank1_coverage_pct_v1", "0")))
    tab_best_price_rows = parse_int(join_summary.get("tab_best_price_rows", watch.get("tab_best_price_rows_v1", "0")))
    sportsbet_best_price_rows = parse_int(join_summary.get("sportsbet_best_price_rows", watch.get("sportsbet_best_price_rows_v1", "0")))

    bookmakers_present_raw = clean_text(watch.get("bookmakers_present_v1", ""))
    bookmakers_present = [book for book in bookmakers_present_raw.split("|") if book]
    bookmaker_set = set(bookmakers_present)
    tab_present = "TAB" in bookmaker_set
    sportsbet_present = "SPORTSBET" in bookmaker_set
    both_bookmakers_present = tab_present and sportsbet_present

    minimum_ready_rows_flag = matched_rank1_rows >= 300
    minimum_ready_dates_flag = matched_dates >= 5
    minimum_ready_tracks_flag = matched_tracks >= 3
    minimum_ready_flag = minimum_ready_rows_flag and minimum_ready_dates_flag and minimum_ready_tracks_flag

    strong_ready_rows_flag = matched_rank1_rows >= 1000
    strong_ready_dates_flag = matched_dates >= 20
    strong_ready_tracks_flag = matched_tracks >= 8
    strong_ready_environment_flag = len(missing_environment_bands) == 0
    strong_ready_flag = (
        strong_ready_rows_flag
        and strong_ready_dates_flag
        and strong_ready_tracks_flag
        and strong_ready_environment_flag
    )

    if strong_ready_flag:
        verdict = "STRONG_READY_FOR_MARKET_AUDIT_V3"
    elif minimum_ready_flag:
        verdict = "MINIMUM_READY_FOR_DIRECTIONAL_AUDIT"
    else:
        verdict = "NOT_READY"

    rows_to_minimum = max(0, 300 - matched_rank1_rows)
    dates_to_minimum = max(0, 5 - matched_dates)
    tracks_to_minimum = max(0, 3 - matched_tracks)

    rows_to_strong = max(0, 1000 - matched_rank1_rows)
    dates_to_strong = max(0, 20 - matched_dates)
    tracks_to_strong = max(0, 8 - matched_tracks)

    consistency_flag = matched_rank1_rows_watch == matched_rank1_rows_summary

    if verdict == "STRONG_READY_FOR_MARKET_AUDIT_V3":
        reason = "strong thresholds met across rows, dates, tracks, and environment coverage"
    elif verdict == "MINIMUM_READY_FOR_DIRECTIONAL_AUDIT":
        bookmaker_note = "both bookmakers present" if both_bookmakers_present else "single-bookmaker bias still possible"
        reason = f"minimum thresholds met; {bookmaker_note}"
    else:
        gaps: list[str] = []
        if rows_to_minimum > 0:
            gaps.append(f"need {rows_to_minimum} more matched Rank1 rows")
        if dates_to_minimum > 0:
            gaps.append(f"need {dates_to_minimum} more matched dates")
        if tracks_to_minimum > 0:
            gaps.append(f"need {tracks_to_minimum} more matched tracks")
        reason = "; ".join(gaps) if gaps else "minimum readiness thresholds not met"

    output_row = {
        "run_timestamp_v1": run_ts,
        "watch_timestamp_v1": clean_text(watch.get("watch_timestamp_v1", "")),
        "warehouse_latest_capture_timestamp_v1": clean_text(watch.get("warehouse_latest_capture_timestamp_v1", "")),
        "warehouse_rows_v1": warehouse_rows,
        "warehouse_unique_meeting_dates_v1": warehouse_unique_dates,
        "warehouse_unique_races_v1": warehouse_unique_races,
        "warehouse_unique_horses_v1": warehouse_unique_horses,
        "warehouse_min_meeting_date_v1": clean_text(watch.get("warehouse_min_meeting_date_v1", "")),
        "warehouse_max_meeting_date_v1": clean_text(watch.get("warehouse_max_meeting_date_v1", "")),
        "rank1_rows_v1": rank1_rows,
        "matched_rank1_rows_watch_v1": matched_rank1_rows_watch,
        "matched_rank1_rows_summary_v1": matched_rank1_rows_summary,
        "matched_rank1_rows_v1": matched_rank1_rows,
        "matched_market_rows_v1": matched_market_rows,
        "matched_rank1_rows_with_best_price_v1": matched_rank1_rows_with_best_price,
        "rank1_coverage_pct_v1": round(rank1_coverage_pct, 4),
        "matched_dates_v1": matched_dates,
        "matched_tracks_v1": matched_tracks,
        "matched_environment_band_count_v1": matched_environment_band_count,
        "matched_environment_bands_v1": matched_environment_bands_raw,
        "all_environment_bands_present_v1": as_flag(strong_ready_environment_flag),
        "missing_environment_bands_v1": "|".join(missing_environment_bands),
        "bookmakers_present_v1": bookmakers_present_raw,
        "tab_present_v1": as_flag(tab_present),
        "sportsbet_present_v1": as_flag(sportsbet_present),
        "both_bookmakers_present_preferred_v1": as_flag(both_bookmakers_present),
        "tab_best_price_rows_v1": tab_best_price_rows,
        "sportsbet_best_price_rows_v1": sportsbet_best_price_rows,
        "minimum_ready_rows_flag_v1": as_flag(minimum_ready_rows_flag),
        "minimum_ready_dates_flag_v1": as_flag(minimum_ready_dates_flag),
        "minimum_ready_tracks_flag_v1": as_flag(minimum_ready_tracks_flag),
        "minimum_ready_flag_v1": as_flag(minimum_ready_flag),
        "strong_ready_rows_flag_v1": as_flag(strong_ready_rows_flag),
        "strong_ready_dates_flag_v1": as_flag(strong_ready_dates_flag),
        "strong_ready_tracks_flag_v1": as_flag(strong_ready_tracks_flag),
        "strong_ready_environment_flag_v1": as_flag(strong_ready_environment_flag),
        "strong_ready_flag_v1": as_flag(strong_ready_flag),
        "rows_to_minimum_ready_v1": rows_to_minimum,
        "dates_to_minimum_ready_v1": dates_to_minimum,
        "tracks_to_minimum_ready_v1": tracks_to_minimum,
        "rows_to_strong_ready_v1": rows_to_strong,
        "dates_to_strong_ready_v1": dates_to_strong,
        "tracks_to_strong_ready_v1": tracks_to_strong,
        "matched_rank1_consistency_flag_v1": as_flag(consistency_flag),
        "verdict_v1": verdict,
        "reason_v1": reason,
    }

    pd.DataFrame([output_row]).to_csv(OUTPUT_MAIN, index=False)

    summary_rows = [
        {"metric": "verdict_v1", "value": verdict},
        {"metric": "reason_v1", "value": reason},
        {"metric": "warehouse_rows_v1", "value": warehouse_rows},
        {"metric": "warehouse_unique_meeting_dates_v1", "value": warehouse_unique_dates},
        {"metric": "warehouse_unique_races_v1", "value": warehouse_unique_races},
        {"metric": "warehouse_unique_horses_v1", "value": warehouse_unique_horses},
        {"metric": "rank1_rows_v1", "value": rank1_rows},
        {"metric": "matched_rank1_rows_v1", "value": matched_rank1_rows},
        {"metric": "matched_market_rows_v1", "value": matched_market_rows},
        {"metric": "matched_rank1_rows_with_best_price_v1", "value": matched_rank1_rows_with_best_price},
        {"metric": "rank1_coverage_pct_v1", "value": round(rank1_coverage_pct, 4)},
        {"metric": "matched_dates_v1", "value": matched_dates},
        {"metric": "matched_tracks_v1", "value": matched_tracks},
        {"metric": "matched_environment_band_count_v1", "value": matched_environment_band_count},
        {"metric": "matched_environment_bands_v1", "value": matched_environment_bands_raw},
        {"metric": "all_environment_bands_present_v1", "value": as_flag(strong_ready_environment_flag)},
        {"metric": "bookmakers_present_v1", "value": bookmakers_present_raw},
        {"metric": "both_bookmakers_present_preferred_v1", "value": as_flag(both_bookmakers_present)},
        {"metric": "tab_best_price_rows_v1", "value": tab_best_price_rows},
        {"metric": "sportsbet_best_price_rows_v1", "value": sportsbet_best_price_rows},
        {"metric": "minimum_ready_flag_v1", "value": as_flag(minimum_ready_flag)},
        {"metric": "strong_ready_flag_v1", "value": as_flag(strong_ready_flag)},
        {"metric": "rows_to_minimum_ready_v1", "value": rows_to_minimum},
        {"metric": "dates_to_minimum_ready_v1", "value": dates_to_minimum},
        {"metric": "tracks_to_minimum_ready_v1", "value": tracks_to_minimum},
        {"metric": "rows_to_strong_ready_v1", "value": rows_to_strong},
        {"metric": "dates_to_strong_ready_v1", "value": dates_to_strong},
        {"metric": "tracks_to_strong_ready_v1", "value": tracks_to_strong},
        {"metric": "missing_environment_bands_v1", "value": "|".join(missing_environment_bands)},
        {"metric": "matched_rank1_consistency_flag_v1", "value": as_flag(consistency_flag)},
        {"metric": "output_main", "value": str(OUTPUT_MAIN)},
        {"metric": "output_summary", "value": str(OUTPUT_SUMMARY)},
    ]
    pd.DataFrame(summary_rows).to_csv(OUTPUT_SUMMARY, index=False)

    print("[MARKET_AUDIT_READINESS_GATE_V1] COMPLETE")
    print(f"matched_rank1_rows={matched_rank1_rows}")
    print(f"matched_dates={matched_dates}")
    print(f"matched_tracks={matched_tracks}")
    print(f"environment_band_count={matched_environment_band_count}")
    print(f"bookmakers_present={bookmakers_present_raw or 'NONE'}")
    print(f"minimum_ready={as_flag(minimum_ready_flag)}")
    print(f"strong_ready={as_flag(strong_ready_flag)}")
    print(f"verdict={verdict}")
    print(f"wrote={OUTPUT_MAIN}")
    print(f"wrote={OUTPUT_SUMMARY}")


if __name__ == "__main__":
    main()
