from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

CALENDAR = DATA / "edgeiq_vic_three_day_meeting_calendar_v1.csv"
OUT = DATA / "edgeiq_current_day_artifact_freshness_v1.csv"

ARTIFACTS = [
    DATA / "edgeiq_vic_three_day_meeting_calendar_v1.csv",
    DATA / "edgeiq_tab_calendar_racecards_vic_v1.csv",
    DATA / "edgeiq_vic_three_day_meeting_universe.csv",
    DATA / "edgeiq_vic_live_terminal_feed_v1.csv",
    DATA / "edgeiq_current_race_class_correction_v5_1.csv",
    DATA / "edgeiq_current_field_projection_v5_2.csv",
    DATA / "edgeiq_current_field_projection_V6_1_RESEARCH_replay.csv",
    DATA / "edgeiq_current_fair_prices_V6_1_RESEARCH_replay.csv",
    DATA / "edgeiq_live_runner_board_v1.csv",
    DATA / "edgeiq_live_runner_board_governed_v1.csv",
]

CURRENT_DAY_ONLY_FILES = {
    "edgeiq_tab_calendar_racecards_vic_v1.csv",
    "edgeiq_vic_live_terminal_feed_v1.csv",
    "edgeiq_current_race_class_correction_v5_1.csv",
    "edgeiq_current_field_projection_v5_2.csv",
    "edgeiq_current_field_projection_V6_1_RESEARCH_replay.csv",
    "edgeiq_current_fair_prices_V6_1_RESEARCH_replay.csv",
    "edgeiq_live_runner_board_v1.csv",
    "edgeiq_live_runner_board_governed_v1.csv",
}

DATE_COLUMNS = ["race_date", "meeting_date", "date"]
TRACK_COLUMNS = ["track", "meeting_name", "meeting"]
RACE_NO_COLUMNS = ["race_no", "race_number", "race"]
FAIR_PRICE_COLUMNS = ["fair_price", "V6_1_RESEARCH_fair_price", "ui_fair_price"]
LIVE_PRICE_COLUMNS = ["live_price", "display_live_price", "tab_fixed_win"]


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null", "undefined"} else text


def upper(value: object) -> str:
    return clean(value).upper()


def norm_track(value: object) -> str:
    text = upper(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def pick_column(columns: list[str], candidates: list[str]) -> str:
    column_lookup = {upper(column): column for column in columns}
    for candidate in candidates:
        found = column_lookup.get(upper(candidate))
        if found:
            return found
    return ""


def summarise_values(values: list[str], max_items: int = 6) -> str:
    cleaned = [clean(value) for value in values if clean(value)]
    unique = sorted(set(cleaned))
    if not unique:
        return ""
    if len(unique) <= max_items:
        return "|".join(unique)
    return "|".join(unique[:max_items]) + f"|...(+{len(unique) - max_items})"


def to_float(value: object) -> float | None:
    try:
        text = clean(value).replace(",", "").replace("$", "")
        if text == "":
            return None
        parsed = float(text)
        if pd.isna(parsed):
            return None
        return parsed
    except Exception:
        return None


def count_nonblank_numeric(frame: pd.DataFrame, column: str) -> int:
    if column == "" or column not in frame.columns:
        return 0
    count = 0
    for value in frame[column].tolist():
        parsed = to_float(value)
        if parsed is not None and parsed > 0:
            count += 1
    return count


def count_nonblank(frame: pd.DataFrame, column: str) -> int:
    if column == "" or column not in frame.columns:
        return 0
    return int(frame[column].map(clean).ne("").sum())


def scratched_row_count(frame: pd.DataFrame) -> int:
    scratch_columns = [
        column
        for column in ["runner_status", "scratch_status", "is_scratched", "tab_fixed_betting_status"]
        if column in frame.columns
    ]
    if not scratch_columns:
        return 0

    count = 0
    for _, row in frame[scratch_columns].iterrows():
        text = " ".join(upper(row.get(column, "")) for column in scratch_columns)
        if "SCRATCH" in text or "LATESCRATCHED" in text or text in {"TRUE", "YES", "1"}:
            count += 1
    return count


def race_no_range(frame: pd.DataFrame, column: str) -> tuple[str, str]:
    if column == "" or column not in frame.columns:
        return "", ""
    values = []
    for value in frame[column].tolist():
        digits = re.sub(r"[^0-9]", "", clean(value))
        if digits:
            values.append(int(digits))
    if not values:
        return "", ""
    return str(min(values)), str(max(values))


def calendar_today_context() -> tuple[str, str, bool]:
    if not CALENDAR.exists():
        return datetime.now(timezone.utc).date().isoformat(), "", False

    calendar = pd.read_csv(CALENDAR, dtype=str, keep_default_na=False, low_memory=False)
    if calendar.empty or "day_bucket" not in calendar.columns:
        return datetime.now(timezone.utc).date().isoformat(), "", False

    today_rows = calendar[calendar["day_bucket"].map(upper).eq("TODAY")].copy()
    if today_rows.empty:
        return datetime.now(timezone.utc).date().isoformat(), "", False

    today_date = clean(today_rows.iloc[0].get("race_date"))
    today_track = norm_track(today_rows.iloc[0].get("track"))
    return today_date, today_track, bool(today_date and today_track)


def status_for_artifact(
    file_name: str,
    file_exists: bool,
    rows: int,
    stale_vs_today: str,
    unique_dates: list[str],
    unique_tracks: list[str],
    today_date: str,
    today_track: str,
    today_ready: bool,
) -> str:
    if not file_exists or rows <= 0:
        return "FAIL"
    if stale_vs_today == "YES":
        return "FAIL"
    if not today_ready:
        return "WARN"

    if file_name in CURRENT_DAY_ONLY_FILES:
        only_today_dates = set(unique_dates).issubset({today_date})
        only_today_tracks = set(unique_tracks).issubset({today_track})
        if not only_today_dates or not only_today_tracks:
            return "WARN"

    return "PASS"


def main() -> None:
    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    today_date, today_track, today_ready = calendar_today_context()

    rows_out: list[dict[str, object]] = []

    for path in ARTIFACTS:
        file_exists = path.exists()
        file_name = path.name

        if not file_exists:
            rows_out.append(
                {
                    "built_at_utc": built_at,
                    "calendar_today_date": today_date,
                    "calendar_today_track": today_track,
                    "file_name": file_name,
                    "file_exists": "NO",
                    "rows": 0,
                    "race_dates": "",
                    "tracks": "",
                    "min_race_no": "",
                    "max_race_no": "",
                    "live_price_rows": "",
                    "fair_price_rows": "",
                    "scratched_rows": "",
                    "research_rated_rows": "",
                    "stale_vs_calendar_today": "YES",
                    "status": "FAIL",
                }
            )
            continue

        frame = pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)
        date_column = pick_column(frame.columns.tolist(), DATE_COLUMNS)
        track_column = pick_column(frame.columns.tolist(), TRACK_COLUMNS)
        race_no_column = pick_column(frame.columns.tolist(), RACE_NO_COLUMNS)
        fair_price_column = pick_column(frame.columns.tolist(), FAIR_PRICE_COLUMNS)
        live_price_column = pick_column(frame.columns.tolist(), LIVE_PRICE_COLUMNS)

        unique_dates = []
        unique_tracks = []
        if date_column:
            unique_dates = [clean(value)[:10] for value in frame[date_column].tolist() if clean(value)]
        if track_column:
            unique_tracks = [norm_track(value) for value in frame[track_column].tolist() if clean(value)]

        unique_dates = sorted(set(unique_dates))
        unique_tracks = sorted(set(unique_tracks))

        has_today_date = today_date in unique_dates if today_date else False
        has_today_track = today_track in unique_tracks if today_track else False
        stale_vs_today = "NO" if (today_ready and has_today_date and has_today_track) else "YES"
        if file_name == "edgeiq_vic_three_day_meeting_calendar_v1.csv" and today_ready:
            stale_vs_today = "NO"

        min_race_no, max_race_no = race_no_range(frame, race_no_column)
        live_price_rows = count_nonblank_numeric(frame, live_price_column) if live_price_column else ""
        fair_price_rows = count_nonblank_numeric(frame, fair_price_column) if fair_price_column else ""
        scratched_rows = scratched_row_count(frame) if rows_out is not None else 0

        research_rated_rows = ""
        if "V6_1_RESEARCH_price_status" in frame.columns:
            research_rated_rows = int(frame["V6_1_RESEARCH_price_status"].map(upper).eq("RESEARCH_RATED").sum())

        status = status_for_artifact(
            file_name=file_name,
            file_exists=file_exists,
            rows=len(frame),
            stale_vs_today=stale_vs_today,
            unique_dates=unique_dates,
            unique_tracks=unique_tracks,
            today_date=today_date,
            today_track=today_track,
            today_ready=today_ready,
        )

        rows_out.append(
            {
                "built_at_utc": built_at,
                "calendar_today_date": today_date,
                "calendar_today_track": today_track,
                "file_name": file_name,
                "file_exists": "YES",
                "rows": int(len(frame)),
                "race_dates": summarise_values(unique_dates),
                "tracks": summarise_values(unique_tracks),
                "min_race_no": min_race_no,
                "max_race_no": max_race_no,
                "live_price_rows": live_price_rows,
                "fair_price_rows": fair_price_rows,
                "scratched_rows": scratched_rows,
                "research_rated_rows": research_rated_rows,
                "stale_vs_calendar_today": stale_vs_today,
                "status": status,
            }
        )

    out = pd.DataFrame(rows_out)
    out.to_csv(OUT, index=False)

    print("[EDGEIQ_CURRENT_DAY_ARTIFACT_FRESHNESS_V1] COMPLETE")
    print(f"calendar_today_date={today_date}")
    print(f"calendar_today_track={today_track}")
    print(f"artifacts={len(rows_out)}")
    print(f"wrote={OUT}")


if __name__ == "__main__":
    main()
