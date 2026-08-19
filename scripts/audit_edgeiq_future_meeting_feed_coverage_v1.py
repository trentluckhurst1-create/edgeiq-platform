from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

UNIVERSE = DATA / "edgeiq_vic_three_day_meeting_universe.csv"
DETAIL_OUT = DATA / "edgeiq_future_meeting_feed_coverage_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_future_meeting_feed_coverage_v1_summary.csv"

LOCAL_TZ = ZoneInfo("Australia/Sydney")
TODAY = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
TOMORROW = (datetime.now(LOCAL_TZ) + timedelta(days=1)).strftime("%Y-%m-%d")
DAY2 = (datetime.now(LOCAL_TZ) + timedelta(days=2)).strftime("%Y-%m-%d")

DATE_COLUMNS = ["race_date", "meeting_date", "date"]
TRACK_COLUMNS = ["track", "meeting", "meeting_name", "location", "track_name"]
RACE_COLUMNS = ["race_no", "raceNumber"]

FILE_SPECS = [
    {"label": "CLASS_CORRECTION", "aliases": ["edgeiq_current_race_class_correction_v5_1.csv"]},
    {"label": "PROJECTION_V5_2", "aliases": ["edgeiq_current_field_projection_v5_2.csv"]},
    {"label": "PROJECTION_V6_1_REPLAY", "aliases": ["edgeiq_current_field_projection_V6_1_RESEARCH_replay.csv"]},
    {"label": "FAIR_PRICE_V6_1_REPLAY", "aliases": ["edgeiq_current_fair_prices_V6_1_RESEARCH_replay.csv"]},
    {"label": "RUNNER_BOARD", "aliases": ["edgeiq_live_runner_board_v1.csv"]},
    {"label": "RUNNER_BOARD_GOVERNED", "aliases": ["edgeiq_live_runner_board_governed_v1.csv"]},
    {"label": "RUNNER_DNA_V6_2", "aliases": ["edgeiq_runner_dna_v6_2.csv", "edgeiq_live_runner_dna_v6_2.csv"]},
    {"label": "RUNNER_DNA_DRAWER_V2", "aliases": ["edgeiq_runner_dna_drawer_feed_v2.csv"]},
    {"label": "RACE_BRIEFING", "aliases": ["edgeiq_race_briefing_v1.csv"]},
    {"label": "MARKET_INTELLIGENCE", "aliases": ["edgeiq_market_intelligence_v1.csv"]},
    {"label": "RACE_VERDICT", "aliases": ["edgeiq_race_verdict_v1.csv"]},
    {"label": "TRACK_INTELLIGENCE", "aliases": ["edgeiq_track_intelligence_card_v1.csv", "edgeiq_live_track_intelligence_v1.csv"]},
]


def clean(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null", "undefined"} else text


def date_key(value: object) -> str:
    return clean(value)[:10]


def norm_track(value: object) -> str:
    return re.sub(r"\s+", " ", clean(value).upper()).strip()


def resolve_path(aliases: list[str]) -> Path | None:
    for alias in aliases:
        path = DATA / alias
        if path.exists():
            return path
    return None


def first_matching_column(columns: list[str], candidates: list[str]) -> str:
    lookup = {column.lower(): column for column in columns}
    for candidate in candidates:
        found = lookup.get(candidate.lower())
        if found:
            return found
    return ""


def read_frame(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)


def race_count(frame: pd.DataFrame, date_col: str, track_col: str, race_col: str) -> int:
    if not date_col or not track_col or not race_col or frame.empty:
        return 0
    temp = pd.DataFrame(
        {
            "race_date": frame[date_col].map(date_key),
            "track": frame[track_col].map(norm_track),
            "race_no": frame[race_col].map(clean),
        }
    )
    return int(len(temp.drop_duplicates()))


def summary_dates(frame: pd.DataFrame, date_col: str) -> str:
    if not date_col or frame.empty:
        return ""
    values = sorted({date_key(value) for value in frame[date_col].tolist() if date_key(value)})
    return "|".join(values)


def main() -> None:
    if not UNIVERSE.exists():
        raise FileNotFoundError(f"Missing universe input: {UNIVERSE}")

    built_at = datetime.now(LOCAL_TZ).isoformat(timespec="seconds")
    universe = read_frame(UNIVERSE)

    future_targets = universe.copy()
    future_targets["race_date_key"] = future_targets.get("race_date", "").astype(str).str[:10]
    future_targets["track_key"] = future_targets.get("track", "").astype(str).map(norm_track)
    future_targets["meeting_status_key"] = future_targets.get("meeting_status", "").astype(str).str.upper().str.strip()
    future_targets["dashboard_ready_key"] = future_targets.get("dashboard_ready", "").astype(str).str.upper().str.strip()
    future_targets = future_targets[
        future_targets["race_date_key"].isin([TOMORROW, DAY2])
        & future_targets["track_key"].ne("")
        & future_targets["meeting_status_key"].eq("FIELDS_READY")
    ].copy()

    target_summary = (
        future_targets.groupby(["race_date_key", "track_key"], dropna=False)
        .agg(universe_rows=("horse", "size"), universe_races=("race_no", "nunique"))
        .reset_index()
    )

    detail_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    for spec in FILE_SPECS:
        resolved_path = resolve_path(spec["aliases"])
        if resolved_path is None:
            for target in target_summary.itertuples(index=False):
                detail_rows.append(
                    {
                        "built_at": built_at,
                        "label": spec["label"],
                        "requested_file": spec["aliases"][0],
                        "resolved_file": "",
                        "exists": "NO",
                        "race_date": target.race_date_key,
                        "track": target.track_key,
                        "universe_rows": int(target.universe_rows),
                        "universe_races": int(target.universe_races),
                        "file_rows": 0,
                        "file_races": 0,
                        "rows_with_fair_price": 0,
                        "rows_with_live_price": 0,
                        "status": "FILE_MISSING",
                    }
                )
            summary_rows.append(
                {
                    "label": spec["label"],
                    "requested_file": spec["aliases"][0],
                    "resolved_file": "",
                    "exists": "NO",
                    "target_meetings": int(len(target_summary)),
                    "meetings_present": 0,
                    "meetings_missing": int(len(target_summary)),
                    "rows_present_total": 0,
                    "status": "FILE_MISSING",
                }
            )
            continue

        frame = read_frame(resolved_path)
        date_col = first_matching_column(list(frame.columns), DATE_COLUMNS)
        track_col = first_matching_column(list(frame.columns), TRACK_COLUMNS)
        race_col = first_matching_column(list(frame.columns), RACE_COLUMNS)
        fair_col = first_matching_column(list(frame.columns), ["fair_price", "ui_fair_price", "V6_1_RESEARCH_fair_price", "rated_price", "race_reliability_score_v1"])
        live_col = first_matching_column(list(frame.columns), ["live_price", "tab_fixed_win", "market_price"])

        if date_col:
            frame["_date"] = frame[date_col].map(date_key)
        else:
            frame["_date"] = ""
        if track_col:
            frame["_track"] = frame[track_col].map(norm_track)
        else:
            frame["_track"] = ""

        meetings_present = 0
        rows_present_total = 0

        for target in target_summary.itertuples(index=False):
            subset = frame[(frame["_date"] == target.race_date_key) & (frame["_track"] == target.track_key)].copy()
            file_rows = int(len(subset))
            file_races = race_count(subset, "_date", "_track", race_col) if race_col else 0
            rows_with_fair_price = 0
            rows_with_live_price = 0
            if fair_col:
                rows_with_fair_price = int(subset[fair_col].map(clean).ne("").sum())
            if live_col:
                rows_with_live_price = int(subset[live_col].map(clean).ne("").sum())

            status = "PRESENT" if file_rows > 0 else "MISSING_FUTURE_COVERAGE"
            if file_rows > 0:
                meetings_present += 1
                rows_present_total += file_rows

            detail_rows.append(
                {
                    "built_at": built_at,
                    "label": spec["label"],
                    "requested_file": spec["aliases"][0],
                    "resolved_file": resolved_path.name,
                    "exists": "YES",
                    "race_date": target.race_date_key,
                    "track": target.track_key,
                    "universe_rows": int(target.universe_rows),
                    "universe_races": int(target.universe_races),
                    "file_rows": file_rows,
                    "file_races": file_races,
                    "rows_with_fair_price": rows_with_fair_price,
                    "rows_with_live_price": rows_with_live_price,
                    "all_file_dates": summary_dates(frame, "_date"),
                    "status": status,
                }
            )

        summary_status = "PASS" if meetings_present == len(target_summary) else "PARTIAL" if meetings_present > 0 else "FAIL"
        summary_rows.append(
            {
                "label": spec["label"],
                "requested_file": spec["aliases"][0],
                "resolved_file": resolved_path.name,
                "exists": "YES",
                "target_meetings": int(len(target_summary)),
                "meetings_present": int(meetings_present),
                "meetings_missing": int(len(target_summary) - meetings_present),
                "rows_present_total": int(rows_present_total),
                "status": summary_status,
            }
        )

    detail = pd.DataFrame(detail_rows)
    summary = pd.DataFrame(summary_rows)

    detail.to_csv(DETAIL_OUT, index=False, encoding="utf-8")
    summary.to_csv(SUMMARY_OUT, index=False, encoding="utf-8")

    print("[EDGEIQ_FUTURE_MEETING_FEED_COVERAGE_V1] COMPLETE")
    print(f"today={TODAY}")
    print(f"tomorrow={TOMORROW}")
    print(f"day_plus_2={DAY2}")
    print(f"target_meetings={len(target_summary)}")
    print(f"wrote={DETAIL_OUT}")
    print(f"wrote={SUMMARY_OUT}")


if __name__ == "__main__":
    main()
