from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

AUDIT_OUT = DATA / "edgeiq_daily_freshness_audit_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_daily_freshness_audit_v1_summary.csv"

LOCAL_TZ = ZoneInfo("Australia/Sydney")
TODAY = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
TOMORROW = (datetime.now(LOCAL_TZ) + timedelta(days=1)).strftime("%Y-%m-%d")
DAY2 = (datetime.now(LOCAL_TZ) + timedelta(days=2)).strftime("%Y-%m-%d")

DATE_COLUMNS = ["race_date", "meeting_date", "date"]
TRACK_COLUMNS = ["track", "meeting", "meeting_name", "location", "track_name"]


FILE_SPECS = [
    {
        "file": "edgeiq_vic_three_day_meeting_universe.csv",
        "aliases": ["edgeiq_vic_three_day_meeting_universe.csv"],
        "kind": "THREE_DAY_UNIVERSE",
    },
    {
        "file": "edgeiq_live_runner_board_v1.csv",
        "aliases": ["edgeiq_live_runner_board_v1.csv"],
        "kind": "CURRENT_DAY",
    },
    {
        "file": "edgeiq_live_terminal_feed_v1.csv",
        "aliases": ["edgeiq_live_terminal_feed_v1.csv"],
        "kind": "CURRENT_DAY",
    },
    {
        "file": "edgeiq_runner_dna_drawer_feed_v2.csv",
        "aliases": ["edgeiq_runner_dna_drawer_feed_v2.csv"],
        "kind": "CURRENT_DAY",
    },
    {
        "file": "edgeiq_runner_dna_v6_2.csv",
        "aliases": ["edgeiq_runner_dna_v6_2.csv", "edgeiq_live_runner_dna_v6_2.csv"],
        "kind": "CURRENT_DAY_ALIAS_OK",
    },
    {
        "file": "edgeiq_race_briefing_v1.csv",
        "aliases": ["edgeiq_race_briefing_v1.csv"],
        "kind": "CURRENT_DAY",
    },
    {
        "file": "edgeiq_market_intelligence_v1.csv",
        "aliases": ["edgeiq_market_intelligence_v1.csv"],
        "kind": "CURRENT_DAY",
    },
    {
        "file": "edgeiq_race_verdict_v1.csv",
        "aliases": ["edgeiq_race_verdict_v1.csv"],
        "kind": "CURRENT_DAY",
    },
]


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null", "undefined"} else text


def upper(value: object) -> str:
    return clean(value).upper()


def date_key(value: object) -> str:
    return clean(value)[:10]


def norm_track(value: object) -> str:
    text = upper(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def summarise(values: list[str], max_items: int = 8) -> str:
    cleaned = [clean(value) for value in values if clean(value)]
    unique = sorted(set(cleaned))
    if not unique:
        return ""
    if len(unique) <= max_items:
        return "|".join(unique)
    return "|".join(unique[:max_items]) + f"|...(+{len(unique) - max_items})"


def resolve_existing_path(spec: dict[str, object]) -> Path | None:
    for name in spec["aliases"]:
        path = DATA / str(name)
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


def status_for_row(kind: str, rows: int, has_today: str, has_tomorrow: str, has_day2: str, alias_used: bool) -> str:
    if rows <= 0:
        return "FAIL_EMPTY"

    if kind == "THREE_DAY_UNIVERSE":
        if has_today != "YES" or has_tomorrow != "YES":
            return "FAIL_STALE_UNIVERSE"
        if has_day2 != "YES":
            return "WARN_DAY2_MISSING"
        return "PASS"

    if has_today != "YES":
        return "FAIL_STALE_CURRENT_DAY"

    if alias_used:
        return "PASS_ALIAS_RESOLVED"

    return "PASS"


def main() -> None:
    built_at = datetime.now(LOCAL_TZ).isoformat(timespec="seconds")
    audit_rows: list[dict[str, object]] = []

    for spec in FILE_SPECS:
        requested_name = str(spec["file"])
        kind = str(spec["kind"])
        resolved_path = resolve_existing_path(spec)
        alias_used = resolved_path is not None and resolved_path.name != requested_name

        if resolved_path is None:
            audit_rows.append(
                {
                    "built_at": built_at,
                    "file": requested_name,
                    "resolved_file": "",
                    "exists": "NO",
                    "last_write_time": "",
                    "rows": 0,
                    "race_dates": "",
                    "has_today": "NO",
                    "has_tomorrow": "NO",
                    "has_day_plus_2": "NO",
                    "status": "FAIL_MISSING",
                }
            )
            continue

        try:
            frame = read_frame(resolved_path)
        except Exception as exc:
            audit_rows.append(
                {
                    "built_at": built_at,
                    "file": requested_name,
                    "resolved_file": resolved_path.name,
                    "exists": "YES",
                    "last_write_time": datetime.fromtimestamp(resolved_path.stat().st_mtime, LOCAL_TZ).isoformat(timespec="seconds"),
                    "rows": 0,
                    "race_dates": "",
                    "has_today": "NO",
                    "has_tomorrow": "NO",
                    "has_day_plus_2": "NO",
                    "status": f"FAIL_READ_ERROR:{type(exc).__name__}",
                }
            )
            continue

        date_col = first_matching_column(list(frame.columns), DATE_COLUMNS)
        unique_dates: list[str] = []
        if date_col:
            unique_dates = sorted(set(date_key(value) for value in frame[date_col].tolist() if date_key(value)))

        has_today = "YES" if TODAY in unique_dates else "NO"
        has_tomorrow = "YES" if TOMORROW in unique_dates else "NO"
        has_day2 = "YES" if DAY2 in unique_dates else "NO"
        status = status_for_row(kind, len(frame), has_today, has_tomorrow, has_day2, alias_used)

        audit_rows.append(
            {
                "built_at": built_at,
                "file": requested_name,
                "resolved_file": resolved_path.name,
                "exists": "YES",
                "last_write_time": datetime.fromtimestamp(resolved_path.stat().st_mtime, LOCAL_TZ).isoformat(timespec="seconds"),
                "rows": int(len(frame)),
                "race_dates": summarise(unique_dates),
                "has_today": has_today,
                "has_tomorrow": has_tomorrow,
                "has_day_plus_2": has_day2,
                "status": status,
            }
        )

    audit = pd.DataFrame(audit_rows)
    audit.to_csv(AUDIT_OUT, index=False)

    fail_rows = audit[audit["status"].astype(str).str.startswith("FAIL")].copy()
    warn_rows = audit[audit["status"].astype(str).str.startswith("WARN")].copy()
    universe_row = audit[audit["file"] == "edgeiq_vic_three_day_meeting_universe.csv"].head(1)

    overall_status = "PASS"
    if not fail_rows.empty:
        overall_status = "FAIL"
    elif not warn_rows.empty:
        overall_status = "WARN"

    summary_row = {
        "built_at": built_at,
        "today_date": TODAY,
        "tomorrow_date": TOMORROW,
        "day_plus_2_date": DAY2,
        "files_checked": int(len(audit)),
        "pass_files": int((audit["status"] == "PASS").sum() + (audit["status"] == "PASS_ALIAS_RESOLVED").sum()),
        "warn_files": int(len(warn_rows)),
        "fail_files": int(len(fail_rows)),
        "overall_status": overall_status,
        "universe_race_dates": clean(universe_row.iloc[0]["race_dates"]) if not universe_row.empty else "",
        "universe_has_today": clean(universe_row.iloc[0]["has_today"]) if not universe_row.empty else "NO",
        "universe_has_tomorrow": clean(universe_row.iloc[0]["has_tomorrow"]) if not universe_row.empty else "NO",
        "universe_has_day_plus_2": clean(universe_row.iloc[0]["has_day_plus_2"]) if not universe_row.empty else "NO",
        "fail_files_list": summarise(fail_rows["file"].astype(str).tolist(), max_items=20),
        "warn_files_list": summarise(warn_rows["file"].astype(str).tolist(), max_items=20),
        "status_reason": (
            "FAIL_STALE_UNIVERSE"
            if not universe_row.empty and clean(universe_row.iloc[0]["status"]) == "FAIL_STALE_UNIVERSE"
            else "PASS"
            if overall_status == "PASS"
            else "SEE_AUDIT_ROWS"
        ),
    }

    pd.DataFrame([summary_row]).to_csv(SUMMARY_OUT, index=False)

    print("[EDGEIQ_DAILY_FRESHNESS_AUDIT_V1] COMPLETE")
    print(f"today_date={TODAY}")
    print(f"tomorrow_date={TOMORROW}")
    print(f"overall_status={overall_status}")
    print(f"wrote={AUDIT_OUT}")
    print(f"wrote={SUMMARY_OUT}")


if __name__ == "__main__":
    main()
