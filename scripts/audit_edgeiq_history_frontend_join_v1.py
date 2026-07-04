from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re

import pandas as pd
from pandas.errors import EmptyDataError, ParserError


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_PATH = DATA / "edgeiq_live_runner_board_v1.csv"

OUT_AUDIT_PATH = DATA / "edgeiq_history_frontend_join_audit_v1.csv"
OUT_SUMMARY_PATH = DATA / "edgeiq_history_frontend_join_audit_v1_summary.csv"

FRONTEND_HISTORY_SOURCES = {"edgeiq_runner_history_detail_v1.csv", "runner_form_history.csv"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def text(value: object) -> str:
    if value is None:
        return ""
    result = str(value).strip()
    return "" if result.lower() == "nan" else result


def normalize_track(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", text(value).upper())


def normalize_horse(value: object) -> str:
    base = text(value).upper()
    base = re.sub(r"\([^)]*\)", "", base)
    base = re.sub(r"[^A-Z0-9]+", "", base)
    return re.sub(r"(NZ|GB|IRE|FR|USA|JPN|AUS)$", "", base)


def truthy_flag(value: object) -> bool:
    return text(value).upper() in {"1", "TRUE", "YES", "Y", "SCRATCHED", "LATE_SCRATCHED", "LATESCRATCHED"}


def detect_history_files() -> list[Path]:
    explicit = [
        "edgeiq_historical_run_ratings_master_v1.csv",
        "edgeiq_historical_performance_rating_v6_1_research.csv",
        "edgeiq_historical_performance_rating_v6_research.csv",
        "edgeiq_racingcom_results_warehouse_full_v1.csv",
        "historical_form_table.csv",
        "edgeiq_runner_history_detail_v1.csv",
        "runner_form_history.csv",
        "edgeiq_horse_career_intelligence_v1.csv",
    ]
    return [DATA / name for name in explicit]


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, dtype=str).fillna("")
    except (EmptyDataError, ParserError, UnicodeDecodeError):
        return pd.DataFrame()


def load_active_live() -> pd.DataFrame:
    live = load_csv(LIVE_PATH)
    if live.empty:
        raise FileNotFoundError(f"Missing or empty live runner board: {LIVE_PATH}")
    active_mask = ~live.apply(
        lambda row: (
            text(row.get("runner_status")).upper() == "SCRATCHED"
            or truthy_flag(row.get("is_scratched"))
            or "SCRATCH" in text(row.get("scratch_status")).upper()
        ),
        axis=1,
    )
    active = live.loc[active_mask].copy()
    active["race_date_value"] = active["race_date"].map(text)
    active["track_value"] = active["track"].map(text)
    active["race_no_value"] = active["race_no"].map(text)
    active["horse_value"] = active["horse"].map(text)
    active["horse_key_value"] = active["horse_key"].map(text)
    active["track_norm"] = active["track_value"].map(normalize_track)
    active["horse_norm"] = active["horse_value"].map(normalize_horse)
    active["horse_key_norm"] = active["horse_key_value"].map(normalize_horse)
    return active


def detect_columns(df: pd.DataFrame) -> tuple[str, str, str, str, str]:
    columns = list(df.columns)
    horse_col = next((col for col in ["horse_key", "horseKey", "horse", "horseName", "runner", "runner_name"] if col in columns), "")
    horse_name_col = next((col for col in ["horse", "horseName", "runner", "runner_name"] if col in columns), "")
    date_col = next((col for col in ["run_date_iso", "run_date", "race_date", "meeting_date", "date"] if col in columns), "")
    track_col = next((col for col in ["track", "meeting", "meeting_name"] if col in columns), "")
    race_col = next((col for col in ["race_no", "raceNo", "race_number", "race"] if col in columns), "")
    return horse_col, horse_name_col, date_col, track_col, race_col


def detect_rating_column(df: pd.DataFrame) -> str:
    columns = list(df.columns)
    for name in [
        "performance_rating",
        "performance_rating_v6_1_research",
        "performance_rating_v6_research",
        "run_rating_final",
        "run_rating",
        "rating",
        "latest_rating",
        "peak_rating",
    ]:
        if name in columns:
            return name
    return ""


def prepare_source(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    if df.empty:
        return df.copy(), {"horse_col": "", "horse_name_col": "", "date_col": "", "track_col": "", "race_col": "", "rating_col": ""}
    horse_col, horse_name_col, date_col, track_col, race_col = detect_columns(df)
    rating_col = detect_rating_column(df)
    prepared = df.copy()
    prepared["horse_key_norm"] = prepared[horse_col].map(normalize_horse) if horse_col else ""
    prepared["horse_norm"] = prepared[horse_name_col].map(normalize_horse) if horse_name_col else prepared["horse_key_norm"]
    prepared["date_value"] = prepared[date_col].map(text) if date_col else ""
    prepared["track_norm"] = prepared[track_col].map(normalize_track) if track_col else ""
    prepared["race_no_value"] = prepared[race_col].map(text) if race_col else ""
    prepared["rating_value"] = prepared[rating_col].map(text) if rating_col else ""
    return prepared, {
        "horse_col": horse_col,
        "horse_name_col": horse_name_col,
        "date_col": date_col,
        "track_col": track_col,
        "race_col": race_col,
        "rating_col": rating_col,
    }


def current_runner_coverage(active: pd.DataFrame, source: pd.DataFrame) -> dict[str, object]:
    if source.empty:
        return {
            "strict_match_count": 0,
            "cleaned_match_count": 0,
            "loose_match_count": 0,
            "contextual_match_count": 0,
            "dated_match_count": 0,
            "rated_match_count": 0,
            "three_plus_rated_match_count": 0,
            "sample_unmatched": "",
        }

    strict_total = source[source["horse_key_norm"] != ""].groupby("horse_key_norm").size().to_dict()
    cleaned_total = source[source["horse_norm"] != ""].groupby("horse_norm").size().to_dict()
    contextual_total = source[(source["horse_norm"] != "") & (source["track_norm"] != "") & (source["race_no_value"] != "")].groupby(["track_norm", "race_no_value", "horse_norm"]).size().to_dict()
    strict_dated = source[(source["horse_key_norm"] != "") & (source["date_value"] != "")].groupby("horse_key_norm").size().to_dict()
    cleaned_dated = source[(source["horse_norm"] != "") & (source["date_value"] != "")].groupby("horse_norm").size().to_dict()
    strict_rated = source[(source["horse_key_norm"] != "") & (source["date_value"] != "") & (source["rating_value"] != "")].groupby("horse_key_norm").size().to_dict()
    cleaned_rated = source[(source["horse_norm"] != "") & (source["date_value"] != "") & (source["rating_value"] != "")].groupby("horse_norm").size().to_dict()

    strict_matches = []
    cleaned_matches = []
    loose_matches = []
    contextual_matches = []
    dated_matches = []
    rated_matches = []
    three_plus_matches = []
    unmatched_examples: list[str] = []

    for _, live_row in active.iterrows():
        horse_key_norm = text(live_row["horse_key_norm"])
        horse_norm = text(live_row["horse_norm"])
        track_norm = text(live_row["track_norm"])
        race_no_value = text(live_row["race_no_value"])

        strict_count = strict_total.get(horse_key_norm, 0) if horse_key_norm else 0
        cleaned_count = max(strict_count, cleaned_total.get(horse_norm, 0))
        contextual_count = contextual_total.get((track_norm, race_no_value, horse_norm), 0)
        dated_count = max(strict_dated.get(horse_key_norm, 0) if horse_key_norm else 0, cleaned_dated.get(horse_norm, 0))
        rated_count = max(strict_rated.get(horse_key_norm, 0) if horse_key_norm else 0, cleaned_rated.get(horse_norm, 0))

        if strict_count > 0:
            strict_matches.append(live_row["horse_value"])
        if cleaned_count > 0:
            cleaned_matches.append(live_row["horse_value"])
        if cleaned_count > 0:
            loose_matches.append(live_row["horse_value"])
        if contextual_count > 0:
            contextual_matches.append(live_row["horse_value"])
        if dated_count > 0:
            dated_matches.append(live_row["horse_value"])
        if rated_count > 0:
            rated_matches.append(live_row["horse_value"])
        if rated_count >= 3:
            three_plus_matches.append(live_row["horse_value"])
        if cleaned_count == 0 and len(unmatched_examples) < 8:
            unmatched_examples.append(live_row["horse_value"])

    return {
        "strict_match_count": len(strict_matches),
        "cleaned_match_count": len(cleaned_matches),
        "loose_match_count": len(loose_matches),
        "contextual_match_count": len(contextual_matches),
        "dated_match_count": len(dated_matches),
        "rated_match_count": len(rated_matches),
        "three_plus_rated_match_count": len(three_plus_matches),
        "sample_unmatched": " | ".join(unmatched_examples),
    }


def main() -> None:
    built_at = now_iso()
    active = load_active_live()
    active_bendigo = active[
        (active["race_date_value"] == "2026-06-25")
        & (active["track_norm"] == normalize_track("BENDIGO"))
        & (active["race_no_value"] == "6")
    ].copy()

    audit_rows: list[dict[str, object]] = []

    for path in detect_history_files():
        raw = load_csv(path)
        source, meta = prepare_source(raw)
        unique_horses = int(source["horse_norm"].replace("", pd.NA).dropna().nunique()) if not source.empty else 0
        dated_rows = int((source["date_value"] != "").sum()) if not source.empty else 0
        rated_rows = int(((source["date_value"] != "") & (source["rating_value"] != "")).sum()) if not source.empty else 0
        live_coverage = current_runner_coverage(active, source)
        bendigo_coverage = current_runner_coverage(active_bendigo, source)

        if path.name in FRONTEND_HISTORY_SOURCES:
            if bendigo_coverage["rated_match_count"] == 0:
                root_cause = "CURRENT_FRONTEND_SOURCE_TOO_NARROW"
            else:
                root_cause = "FRONTEND_SOURCE_PARTIAL"
        elif source.empty:
            root_cause = "SOURCE_EMPTY" if path.exists() else "SOURCE_FILE_MISSING"
        elif bendigo_coverage["rated_match_count"] == 0 and live_coverage["rated_match_count"] > 0:
            root_cause = "NO_BENDIGO_R6_HISTORY_ROWS"
        elif bendigo_coverage["rated_match_count"] > 0:
            root_cause = "HEALTHY_HISTORY_SPINE"
        else:
            root_cause = "HORSE_MATCH_OR_DATE_RATING_GAP"

        audit_rows.append(
            {
                "source_file": path.name,
                "file_exists": "YES" if path.exists() else "NO",
                "rows": len(raw),
                "unique_horses": unique_horses,
                "dated_rows": dated_rows,
                "rating_rows": rated_rows,
                "horse_column": meta["horse_col"] or meta["horse_name_col"],
                "date_column": meta["date_col"],
                "track_column": meta["track_col"],
                "race_no_column": meta["race_col"],
                "rating_column": meta["rating_col"],
                "strict_horse_key_matches": live_coverage["strict_match_count"],
                "cleaned_horse_matches": live_coverage["cleaned_match_count"],
                "loose_horse_matches": live_coverage["loose_match_count"],
                "track_race_date_context_matches": live_coverage["contextual_match_count"],
                "matched_current_runners_with_dated_history": live_coverage["dated_match_count"],
                "matched_current_runners_with_rated_history": live_coverage["rated_match_count"],
                "matched_current_runners_with_3plus_dated_rated_rows": live_coverage["three_plus_rated_match_count"],
                "bendigo_r6_active_runners": len(active_bendigo),
                "bendigo_r6_runners_with_any_history": bendigo_coverage["cleaned_match_count"],
                "bendigo_r6_runners_with_dated_history": bendigo_coverage["dated_match_count"],
                "bendigo_r6_runners_with_dated_rated_history": bendigo_coverage["rated_match_count"],
                "bendigo_r6_runners_with_3plus_dated_rated_rows": bendigo_coverage["three_plus_rated_match_count"],
                "bendigo_r6_unmatched_examples": bendigo_coverage["sample_unmatched"],
                "likely_root_cause": root_cause,
                "recommended_fix": (
                    "Prefer this source as a history spine candidate."
                    if root_cause == "HEALTHY_HISTORY_SPINE"
                    else "Do not use this as the sole runner-history source for the frontend."
                ),
                "built_at": built_at,
            }
        )

    audit_df = pd.DataFrame(audit_rows).sort_values(
        ["bendigo_r6_runners_with_3plus_dated_rated_rows", "matched_current_runners_with_rated_history", "rating_rows", "rows"],
        ascending=[False, False, False, False],
    )
    audit_df.to_csv(OUT_AUDIT_PATH, index=False)

    best_source_row = audit_df.iloc[0] if not audit_df.empty else None
    frontend_rows = audit_df[audit_df["source_file"].isin(FRONTEND_HISTORY_SOURCES)].copy()
    frontend_best = frontend_rows["bendigo_r6_runners_with_dated_rated_history"].max() if not frontend_rows.empty else 0
    best_bendigo_rated = 0 if best_source_row is None else int(best_source_row["bendigo_r6_runners_with_dated_rated_history"])
    likely_root_cause = (
        "FRONTEND_HISTORY_SOURCE_TOO_NARROW"
        if best_bendigo_rated > frontend_best
        else "TRUE_LOW_COVERAGE"
    )
    recommended_fix = (
        "Use edgeiq_historical_run_ratings_master_v1.csv as the primary history spine for frontend evidence and historical drawer rows; keep edgeiq_runner_history_detail_v1.csv only as a richer-detail fallback."
        if likely_root_cause == "FRONTEND_HISTORY_SOURCE_TOO_NARROW"
        else "Historical coverage is genuinely limited for the current runners."
    )
    readiness = "READY_TO_SWITCH_SOURCE" if likely_root_cause == "FRONTEND_HISTORY_SOURCE_TOO_NARROW" else "TRUE_LOW_COVERAGE"

    summary_df = pd.DataFrame(
        [
            {
                "audit_status": "PASS",
                "active_runners": len(active),
                "best_source": "" if best_source_row is None else best_source_row["source_file"],
                "best_source_rows": 0 if best_source_row is None else best_source_row["rows"],
                "best_source_join_success": 0 if best_source_row is None else best_source_row["matched_current_runners_with_rated_history"],
                "bendigo_r6_join_success": 0 if best_source_row is None else best_source_row["bendigo_r6_runners_with_dated_rated_history"],
                "likely_root_cause": likely_root_cause,
                "recommended_fix": recommended_fix,
                "best_source_for_history_footer": "" if best_source_row is None else best_source_row["source_file"],
                "best_source_for_runner_dossier_history": "" if best_source_row is None else best_source_row["source_file"],
                "recommended_frontend_join_strategy": "Horse-key / clean-horse history spine, with run rows sourced primarily from edgeiq_historical_run_ratings_master_v1.csv and enriched from edgeiq_runner_history_detail_v1.csv when available.",
                "ui_wire_readiness": readiness,
                "built_at": built_at,
            }
        ]
    )
    summary_df.to_csv(OUT_SUMMARY_PATH, index=False)

    print("[EDGEIQ_HISTORY_FRONTEND_JOIN_AUDIT_V1] COMPLETE")
    print(f"active_runners={len(active)}")
    print(f"best_source={summary_df.loc[0, 'best_source']}")
    print(f"best_source_join_success={summary_df.loc[0, 'best_source_join_success']}")
    print(f"bendigo_r6_join_success={summary_df.loc[0, 'bendigo_r6_join_success']}")
    print(f"likely_root_cause={summary_df.loc[0, 'likely_root_cause']}")
    print(f"recommended_fix={summary_df.loc[0, 'recommended_fix']}")
    print(f"wrote={OUT_AUDIT_PATH}")
    print(f"summary={OUT_SUMMARY_PATH}")


if __name__ == "__main__":
    main()
