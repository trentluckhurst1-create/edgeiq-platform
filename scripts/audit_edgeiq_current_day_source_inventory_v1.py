from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
import re
from zoneinfo import ZoneInfo

import pandas as pd

from build_edgeiq_vic_three_day_meeting_calendar_v1 import (
    CALENDAR_OUT,
    build_calendar_rows,
    normalise_track as calendar_normalise_track,
)
from build_edgeiq_vic_three_day_meeting_universe import DIAG_OUT as MEETING_DIAGNOSTICS_OUT


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

AUDIT_OUT = DATA / "edgeiq_current_day_source_inventory_audit_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_current_day_source_inventory_summary_v1.csv"
TAB_MEETINGS_OUT = DATA / "edgeiq_tab_vic_thoroughbred_meetings_v1.csv"

LOCAL_TZ = ZoneInfo("Australia/Sydney")
TODAY = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
TOMORROW = (datetime.now(LOCAL_TZ) + timedelta(days=1)).strftime("%Y-%m-%d")
DAY2 = (datetime.now(LOCAL_TZ) + timedelta(days=2)).strftime("%Y-%m-%d")

TRACK_CONFIGS = {
    "PAKENHAM SYNTHETIC": {
        "aliases": {
            "PAKENHAM",
            "PAKENHAM SYNTHETIC",
            "SOUTHSIDE PAKENHAM SYNTHETIC",
        },
        "tab_slug": "pakenham-synthetic",
        "tab_venue": "PAK",
        "tab_race_type": "R",
    },
    "BALLARAT SYNTHETIC": {
        "aliases": {
            "BALLARAT SYNTHETIC",
            "SPORTSBET BALLARAT SYNTHETIC",
            "SPORTSBET-BALLARAT SYNTHETIC",
            "BALLARAT SYN",
        },
        "tab_slug": "ballarat-synthetic",
        "tab_venue": "",
        "tab_race_type": "R",
    },
    "CAULFIELD HEATH": {
        "aliases": {
            "CAULFIELD HEATH",
        },
        "tab_slug": "caulfield-heath",
        "tab_venue": "",
        "tab_race_type": "R",
    },
    "MOE": {
        "aliases": {
            "MOE",
        },
        "tab_slug": "moe",
        "tab_venue": "",
        "tab_race_type": "R",
    },
    "GEELONG": {
        "aliases": {
            "GEELONG",
        },
        "tab_slug": "geelong",
        "tab_venue": "",
        "tab_race_type": "R",
    },
}

DATE_COLUMN_CANDIDATES = ["race_date", "meeting_date", "date"]
TRACK_COLUMN_CANDIDATES = ["track", "meeting_name", "meeting", "location", "track_name"]
RACE_NO_COLUMN_CANDIDATES = ["race_no", "race_number", "race"]
HORSE_COLUMN_CANDIDATES = ["horse", "runner", "runner_name", "horse_name"]

SUGGESTED_UPSTREAM_SCRIPTS = [
    r"python .\scripts\build_edgeiq_vic_three_day_meeting_calendar_v1.py",
    r"python .\scripts\build_edgeiq_vic_three_day_meeting_universe.py",
    r"powershell -ExecutionPolicy Bypass -File .\scripts\run_edgeiq_midnight_promotion_chain_v1.ps1",
    r"powershell -ExecutionPolicy Bypass -File .\scripts\run_edgeiq_today_tab_only_dashboard_refresh_v1.ps1",
]


@dataclass(frozen=True)
class SourceSpec:
    path: Path
    source_kind: str
    scrape_priority: int
    terminal_priority: int


SOURCE_SPECS = [
    SourceSpec(DATA / "edgeiq_vic_three_day_meeting_universe.csv", "MEETING_UNIVERSE", 100, 100),
    SourceSpec(DATA / "edgeiq_live_terminal_feed_v1_TAB_ONLY_TODAY.csv", "TODAY_TERMINAL_FEED", 90, 70),
    SourceSpec(DATA / "edgeiq_live_runner_board_v1.csv", "RUNNER_BOARD", 85, 90),
    SourceSpec(DATA / "edgeiq_vic_live_fields_synced.csv", "LIVE_FIELD_SYNC", 80, 85),
    SourceSpec(DATA / "edgeiq_vic_live_terminal_feed_v1.csv", "LEGACY_VIC_TERMINAL_FEED", 70, 60),
    SourceSpec(DATA / "edgeiq_live_terminal_feed_v1.csv", "LEGACY_TERMINAL_FEED", 65, 55),
    SourceSpec(DATA / "race_card_report.csv", "RACE_CARD_REPORT", 50, 80),
    SourceSpec(DATA / "race_fields.csv", "RACE_FIELDS", 40, 50),
]


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null"} else text


def norm_track(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"\s+", " ", text)
    return calendar_normalise_track(text).strip()


def date_key(value: object) -> str:
    return clean(value)[:10]


def race_no_key(value: object) -> str:
    return re.sub(r"[^0-9]", "", clean(value))


def default_tab_slug(track: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", track.lower()).strip("-")


def default_track_config(track: str) -> dict[str, object]:
    return {
        "aliases": {track} if track else set(),
        "tab_slug": default_tab_slug(track) if track else "",
        "tab_venue": "",
        "tab_race_type": "R",
    }


def read_source_frame(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)


def first_matching_column(columns: list[str], candidates: list[str]) -> str:
    lowered = {column.lower(): column for column in columns}
    for candidate in candidates:
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]
    return ""


@lru_cache(maxsize=1)
def read_calendar_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if CALENDAR_OUT.exists():
        try:
            calendar_frame = read_source_frame(CALENDAR_OUT).fillna("")
            for row in calendar_frame.to_dict("records"):
                rows.append(
                    {
                        "race_date": clean(row.get("race_date")),
                        "track": norm_track(row.get("track")),
                        "meeting_type": clean(row.get("meeting_type")) or "UNKNOWN",
                        "day_bucket": clean(row.get("day_bucket")),
                    }
                )
        except Exception:
            rows = []

    if rows:
        return rows

    built_rows = build_calendar_rows()
    return [
        {
            "race_date": clean(row.get("race_date")),
            "track": norm_track(row.get("track")),
            "meeting_type": clean(row.get("meeting_type")) or "UNKNOWN",
            "day_bucket": clean(row.get("day_bucket")),
        }
        for row in built_rows
    ]


def calendar_row_for_day_bucket(day_bucket: str) -> dict[str, object]:
    target = clean(day_bucket).upper()
    for row in read_calendar_rows():
        if clean(row.get("day_bucket")).upper() == target:
            return row
    return {}


def calendar_track_for_day_bucket(day_bucket: str) -> str:
    return norm_track(calendar_row_for_day_bucket(day_bucket).get("track"))


@lru_cache(maxsize=1)
def read_meeting_diagnostics_frame() -> pd.DataFrame:
    if not MEETING_DIAGNOSTICS_OUT.exists():
        return pd.DataFrame()
    try:
        return read_source_frame(MEETING_DIAGNOSTICS_OUT).fillna("")
    except Exception:
        return pd.DataFrame()


def diagnostics_today_track() -> str:
    frame = read_meeting_diagnostics_frame()
    if frame.empty or not {"record_type", "day_bucket", "track"}.issubset(frame.columns):
        return ""

    today_rows = frame[
        frame["record_type"].map(clean).str.upper().eq("MEETING")
        & frame["day_bucket"].map(clean).str.upper().eq("TODAY")
    ].copy()
    if today_rows.empty:
        return ""

    tracks = today_rows["track"].map(norm_track)
    tracks = tracks[tracks != ""]
    if tracks.empty:
        return ""
    return str(tracks.iloc[0])


def fallback_selected_track_from_sources() -> str:
    for spec in SOURCE_SPECS:
        if not spec.path.exists():
            continue
        try:
            frame = read_source_frame(spec.path).fillna("")
        except Exception:
            continue
        if frame.empty:
            continue

        columns = list(frame.columns)
        date_col = first_matching_column(columns, DATE_COLUMN_CANDIDATES)
        track_col = first_matching_column(columns, TRACK_COLUMN_CANDIDATES)
        if not date_col or not track_col:
            continue

        today_rows = frame[frame[date_col].map(date_key) == TODAY].copy()
        if today_rows.empty:
            continue

        tracks = today_rows[track_col].map(norm_track)
        tracks = tracks[tracks != ""]
        if not tracks.empty:
            return str(tracks.mode().iloc[0])

    return ""


def detect_display_track() -> str:
    for candidate in (
        calendar_track_for_day_bucket("TODAY"),
        diagnostics_today_track(),
        fallback_selected_track_from_sources(),
    ):
        track = norm_track(candidate)
        if track:
            return track
    return ""


@lru_cache(maxsize=1)
def get_display_track() -> str:
    return detect_display_track()


@lru_cache(maxsize=None)
def tab_meeting_override_for_track(track: str) -> dict[str, object]:
    if not track or not TAB_MEETINGS_OUT.exists():
        return {}

    try:
        frame = read_source_frame(TAB_MEETINGS_OUT).fillna("")
    except Exception:
        return {}

    if frame.empty or "track" not in frame.columns:
        return {}

    frame["track_key"] = frame["track"].map(norm_track)
    frame["meeting_date_key"] = frame["meeting_date"].map(date_key)
    candidates = frame[
        (frame["track_key"] == track)
        & frame["meeting_date_key"].isin({TODAY, TOMORROW, DAY2})
    ].copy()
    if candidates.empty:
        return {}

    candidates.sort_values(["meeting_date_key"], inplace=True)
    first_row = candidates.iloc[0].to_dict()
    return {
        "aliases": {track},
        "tab_slug": default_tab_slug(track),
        "tab_venue": clean(first_row.get("venue_code")),
        "tab_race_type": clean(first_row.get("race_type")) or "R",
    }


def get_track_config(selected_track: str | None = None) -> dict[str, object]:
    track = norm_track(selected_track or get_display_track())
    configured = TRACK_CONFIGS.get(track, {})
    override = tab_meeting_override_for_track(track)
    base = default_track_config(track)

    aliases: set[str] = set()
    for source in (configured, override):
        for alias in source.get("aliases", set()):
            alias_key = norm_track(alias)
            if alias_key:
                aliases.add(alias_key)
    if track:
        aliases.add(track)

    base["aliases"] = aliases

    for source in (configured, override):
        for key, value in source.items():
            if key == "aliases":
                continue
            if clean(value):
                base[key] = value

    return base


def get_selected_track_aliases(selected_track: str | None = None) -> set[str]:
    config = get_track_config(selected_track)
    aliases = config.get("aliases", set())
    return {norm_track(value) for value in aliases if norm_track(value)}


def canonical_track_for_selected_meeting(value: object, selected_track: str, aliases: set[str]) -> str:
    track = norm_track(value)
    if not track:
        return ""
    if selected_track and track in aliases:
        return selected_track
    return track


def canonical_track(value: object) -> str:
    selected_track = get_display_track()
    aliases = get_selected_track_aliases(selected_track)
    return canonical_track_for_selected_meeting(value, selected_track, aliases)


def track_matches_selected_meeting(value: object) -> bool:
    selected_track = get_display_track()
    if not selected_track:
        return False
    return canonical_track(value) == selected_track


def source_specs() -> list[SourceSpec]:
    return SOURCE_SPECS[:]


def build_audit_row(spec: SourceSpec) -> dict[str, object]:
    selected_track = get_display_track()
    selected_aliases = get_selected_track_aliases(selected_track)
    exists = spec.path.exists()

    base_row = {
        "file_name": spec.path.name,
        "file_path": str(spec.path),
        "source_kind": spec.source_kind,
        "selected_meeting": selected_track,
        "file_exists": "YES" if exists else "NO",
        "read_status": "MISSING" if not exists else "PENDING",
        "rows": 0,
        "columns_count": 0,
        "date_column_used": "",
        "track_column_used": "",
        "race_no_column_used": "",
        "horse_column_used": "",
        "has_required_date_role": "NO",
        "has_required_track_role": "NO",
        "has_required_race_no_role": "NO",
        "has_required_horse_role": "NO",
        "schema_has_scrape_required_columns": "NO",
        "schema_has_terminal_required_columns": "NO",
        "schema_missing_scrape_roles": "date|track|race_no",
        "schema_missing_terminal_roles": "date|track|race_no|horse",
        "min_race_date": "",
        "max_race_date": "",
        "today_row_count": 0,
        "tomorrow_row_count": 0,
        "selected_meeting_row_count": 0,
        "selected_meeting_race_count": 0,
        "selected_track_total_row_count": 0,
        "is_stale": "YES" if exists else "UNKNOWN",
        "freshness_status": "MISSING" if not exists else "PENDING",
        "scrape_priority": spec.scrape_priority,
        "terminal_priority": spec.terminal_priority,
        "usable_for_scrape_inventory": "NO",
        "usable_for_terminal_inventory": "NO",
    }

    if not exists:
        return base_row

    try:
        frame = read_source_frame(spec.path)
    except Exception as exc:
        base_row["read_status"] = f"ERROR: {exc}"
        base_row["freshness_status"] = "READ_ERROR"
        return base_row

    base_row["read_status"] = "OK"
    base_row["rows"] = int(len(frame))
    base_row["columns_count"] = int(len(frame.columns))

    columns = list(frame.columns)
    date_col = first_matching_column(columns, DATE_COLUMN_CANDIDATES)
    track_col = first_matching_column(columns, TRACK_COLUMN_CANDIDATES)
    race_col = first_matching_column(columns, RACE_NO_COLUMN_CANDIDATES)
    horse_col = first_matching_column(columns, HORSE_COLUMN_CANDIDATES)

    base_row["date_column_used"] = date_col
    base_row["track_column_used"] = track_col
    base_row["race_no_column_used"] = race_col
    base_row["horse_column_used"] = horse_col
    base_row["has_required_date_role"] = "YES" if date_col else "NO"
    base_row["has_required_track_role"] = "YES" if track_col else "NO"
    base_row["has_required_race_no_role"] = "YES" if race_col else "NO"
    base_row["has_required_horse_role"] = "YES" if horse_col else "NO"

    missing_scrape_roles = [
        role
        for role, ok in {
            "date": bool(date_col),
            "track": bool(track_col),
            "race_no": bool(race_col),
        }.items()
        if not ok
    ]
    missing_terminal_roles = [
        role
        for role, ok in {
            "date": bool(date_col),
            "track": bool(track_col),
            "race_no": bool(race_col),
            "horse": bool(horse_col),
        }.items()
        if not ok
    ]

    base_row["schema_missing_scrape_roles"] = "|".join(missing_scrape_roles)
    base_row["schema_missing_terminal_roles"] = "|".join(missing_terminal_roles)
    base_row["schema_has_scrape_required_columns"] = "YES" if not missing_scrape_roles else "NO"
    base_row["schema_has_terminal_required_columns"] = "YES" if not missing_terminal_roles else "NO"

    if frame.empty:
        base_row["freshness_status"] = "EMPTY"
        base_row["is_stale"] = "UNKNOWN"
        return base_row

    if date_col:
        frame["_audit_date_key"] = frame[date_col].map(date_key)
        date_values = frame["_audit_date_key"][frame["_audit_date_key"] != ""]
        if not date_values.empty:
            base_row["min_race_date"] = str(date_values.min())
            base_row["max_race_date"] = str(date_values.max())
            base_row["today_row_count"] = int((frame["_audit_date_key"] == TODAY).sum())
            base_row["tomorrow_row_count"] = int((frame["_audit_date_key"] == TOMORROW).sum())
    else:
        frame["_audit_date_key"] = ""

    if track_col:
        frame["_audit_track_key"] = frame[track_col].map(
            lambda value: canonical_track_for_selected_meeting(value, selected_track, selected_aliases)
        )
        if selected_track:
            base_row["selected_track_total_row_count"] = int((frame["_audit_track_key"] == selected_track).sum())
    else:
        frame["_audit_track_key"] = ""

    if date_col and track_col and selected_track:
        selected_mask = (frame["_audit_date_key"] == TODAY) & (frame["_audit_track_key"] == selected_track)
        base_row["selected_meeting_row_count"] = int(selected_mask.sum())
        if race_col:
            selected_races = frame.loc[selected_mask, race_col].map(race_no_key)
            selected_races = selected_races[selected_races != ""]
            base_row["selected_meeting_race_count"] = int(selected_races.nunique())

    max_date = clean(base_row["max_race_date"])
    today_rows = int(base_row["today_row_count"])
    selected_rows = int(base_row["selected_meeting_row_count"])

    if not date_col:
        base_row["freshness_status"] = "NO_DATE_COLUMN"
        base_row["is_stale"] = "UNKNOWN"
    elif selected_track and today_rows > 0 and selected_rows > 0:
        base_row["freshness_status"] = "CURRENT_SELECTED_MEETING"
        base_row["is_stale"] = "NO"
    elif today_rows > 0:
        base_row["freshness_status"] = "CURRENT_OTHER_MEETING"
        base_row["is_stale"] = "NO"
    elif max_date and max_date < TODAY:
        base_row["freshness_status"] = "STALE"
        base_row["is_stale"] = "YES"
    elif int(base_row["tomorrow_row_count"]) > 0:
        base_row["freshness_status"] = "TOMORROW_ONLY"
        base_row["is_stale"] = "NO"
    else:
        base_row["freshness_status"] = "NO_SELECTED_MEETING_ROWS"
        base_row["is_stale"] = "UNKNOWN"

    base_row["usable_for_scrape_inventory"] = (
        "YES"
        if base_row["schema_has_scrape_required_columns"] == "YES" and selected_rows > 0
        else "NO"
    )
    base_row["usable_for_terminal_inventory"] = (
        "YES"
        if base_row["schema_has_terminal_required_columns"] == "YES" and selected_rows > 0
        else "NO"
    )
    return base_row


def select_best_source(audit_df: pd.DataFrame, purpose: str) -> dict[str, object] | None:
    if audit_df.empty:
        return None

    if purpose == "scrape":
        usable_col = "usable_for_scrape_inventory"
        priority_col = "scrape_priority"
    else:
        usable_col = "usable_for_terminal_inventory"
        priority_col = "terminal_priority"

    candidates = audit_df[audit_df[usable_col] == "YES"].copy()
    if candidates.empty:
        return None

    candidates["max_race_date_sort"] = candidates["max_race_date"].fillna("")
    candidates = candidates.sort_values(
        [
            priority_col,
            "selected_meeting_race_count",
            "selected_meeting_row_count",
            "today_row_count",
            "max_race_date_sort",
            "file_name",
        ],
        ascending=[False, False, False, False, False, True],
    )
    return candidates.iloc[0].to_dict()


def build_inventory_audit(write_outputs: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    selected_track = get_display_track()
    today_calendar = calendar_row_for_day_bucket("TODAY")
    tomorrow_calendar = calendar_row_for_day_bucket("TOMORROW")
    day2_calendar = calendar_row_for_day_bucket("DAY+2")

    rows = [build_audit_row(spec) for spec in source_specs()]
    audit_df = pd.DataFrame(rows)

    scrape_choice = select_best_source(audit_df, purpose="scrape")
    terminal_choice = select_best_source(audit_df, purpose="terminal")

    meeting_diag = read_meeting_diagnostics_frame()
    meeting_status = ""
    dashboard_ready = ""
    if not meeting_diag.empty and {"record_type", "day_bucket", "meeting_status", "dashboard_ready"}.issubset(meeting_diag.columns):
        today_diag = meeting_diag[
            meeting_diag["record_type"].map(clean).str.upper().eq("MEETING")
            & meeting_diag["day_bucket"].map(clean).str.upper().eq("TODAY")
        ].head(1)
        if not today_diag.empty:
            meeting_status = clean(today_diag.iloc[0].get("meeting_status"))
            dashboard_ready = clean(today_diag.iloc[0].get("dashboard_ready"))

    summary_row = {
        "run_timestamp": datetime.now(LOCAL_TZ).isoformat(timespec="seconds"),
        "local_today": TODAY,
        "local_tomorrow": TOMORROW,
        "local_day2": DAY2,
        "selected_meeting": selected_track,
        "selected_meeting_status": meeting_status,
        "selected_meeting_dashboard_ready": dashboard_ready,
        "calendar_today_meeting": clean(today_calendar.get("track")),
        "calendar_tomorrow_meeting": clean(tomorrow_calendar.get("track")),
        "calendar_day2_meeting": clean(day2_calendar.get("track")),
        "calendar_rows": len(read_calendar_rows()),
        "files_audited": int(len(audit_df)),
        "files_existing": int((audit_df["file_exists"] == "YES").sum()) if not audit_df.empty else 0,
        "files_with_today_rows": int((audit_df["today_row_count"] > 0).sum()) if not audit_df.empty else 0,
        "files_with_selected_meeting_rows": int((audit_df["selected_meeting_row_count"] > 0).sum()) if not audit_df.empty else 0,
        "best_scrape_inventory_source": scrape_choice["file_name"] if scrape_choice else "",
        "best_scrape_inventory_rows": int(scrape_choice["selected_meeting_row_count"]) if scrape_choice else 0,
        "best_terminal_inventory_source": terminal_choice["file_name"] if terminal_choice else "",
        "best_terminal_inventory_rows": int(terminal_choice["selected_meeting_row_count"]) if terminal_choice else 0,
        "stale_files": "|".join(audit_df.loc[audit_df["freshness_status"] == "STALE", "file_name"].astype(str)) if not audit_df.empty else "",
        "status": (
            "CURRENT_DAY_SOURCE_READY"
            if selected_track and scrape_choice and terminal_choice
            else "NO_CURRENT_DAY_SOURCE_FOUND"
        ),
        "suggested_upstream_scripts": " | ".join(SUGGESTED_UPSTREAM_SCRIPTS),
    }
    summary_df = pd.DataFrame([summary_row])

    if write_outputs:
        AUDIT_OUT.parent.mkdir(parents=True, exist_ok=True)
        audit_df.to_csv(AUDIT_OUT, index=False)
        summary_df.to_csv(SUMMARY_OUT, index=False)

    return audit_df, summary_df


def filter_frame_to_selected_meeting(frame: pd.DataFrame, date_col: str, track_col: str) -> pd.DataFrame:
    selected_track = get_display_track()
    selected_aliases = get_selected_track_aliases(selected_track)
    if not date_col or not track_col or not selected_track:
        return frame.iloc[0:0].copy()

    filtered = frame.copy()
    filtered["_audit_date_key"] = filtered[date_col].map(date_key)
    filtered["_audit_track_key"] = filtered[track_col].map(
        lambda value: canonical_track_for_selected_meeting(value, selected_track, selected_aliases)
    )
    filtered = filtered[
        (filtered["_audit_date_key"] == TODAY)
        & (filtered["_audit_track_key"] == selected_track)
    ].copy()
    filtered.drop(columns=["_audit_date_key", "_audit_track_key"], inplace=True, errors="ignore")
    return filtered


def load_selected_source_rows(
    purpose: str,
    write_outputs: bool = True,
) -> tuple[Path, pd.DataFrame, dict[str, object], pd.DataFrame]:
    audit_df, summary_df = build_inventory_audit(write_outputs=write_outputs)
    choice = select_best_source(audit_df, purpose=purpose)
    if not choice:
        print(build_missing_source_diagnostic(audit_df, purpose))
        raise SystemExit(1)

    source_path = Path(str(choice["file_path"]))
    frame = read_source_frame(source_path)
    filtered = filter_frame_to_selected_meeting(
        frame,
        str(choice.get("date_column_used", "")),
        str(choice.get("track_column_used", "")),
    )
    return source_path, filtered, choice, audit_df


def build_missing_source_diagnostic(audit_df: pd.DataFrame, purpose: str) -> str:
    selected_track = get_display_track()
    today_calendar = calendar_row_for_day_bucket("TODAY")
    tomorrow_calendar = calendar_row_for_day_bucket("TOMORROW")
    day2_calendar = calendar_row_for_day_bucket("DAY+2")
    purpose_label = "TAB_ACTIVE_RACE_SCRAPE" if purpose == "scrape" else "TODAY_TERMINAL_FEED_BUILD"

    lines = [
        f"No current-day source inventory found for {TODAY} {selected_track or '<UNRESOLVED_TODAY_MEETING>'}.",
        f"purpose={purpose_label}",
        f"calendar_today_meeting={clean(today_calendar.get('track'))}",
        f"calendar_tomorrow_meeting={clean(tomorrow_calendar.get('track'))}",
        f"calendar_day2_meeting={clean(day2_calendar.get('track'))}",
        f"calendar_file={CALENDAR_OUT}",
        f"meeting_diagnostics_file={MEETING_DIAGNOSTICS_OUT}",
        "sources_checked=",
    ]

    if audit_df.empty:
        lines.append(" - none")
    else:
        for row in audit_df.to_dict("records"):
            lines.append(
                " - {file_name} | exists={file_exists} | freshness={freshness_status} | "
                "max_date={max_race_date} | today_rows={today_row_count} | "
                "selected_meeting_rows={selected_meeting_row_count} | scrape_schema={schema_has_scrape_required_columns} | "
                "terminal_schema={schema_has_terminal_required_columns}".format(**row)
            )

    lines.extend(
        [
            "suggested_upstream_scripts=",
            *[f" - {script}" for script in SUGGESTED_UPSTREAM_SCRIPTS],
            f"audit_csv={AUDIT_OUT}",
            f"summary_csv={SUMMARY_OUT}",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    selected_track = get_display_track()
    audit_df, summary_df = build_inventory_audit(write_outputs=True)
    summary = summary_df.iloc[0].to_dict() if not summary_df.empty else {}

    print("[CURRENT_DAY_SOURCE_INVENTORY_AUDIT_V1] COMPLETE")
    print(f"today={TODAY}")
    print(f"selected_meeting={selected_track}")
    print(f"calendar_today_meeting={summary.get('calendar_today_meeting', '')}")
    print(f"calendar_tomorrow_meeting={summary.get('calendar_tomorrow_meeting', '')}")
    print(f"calendar_day2_meeting={summary.get('calendar_day2_meeting', '')}")
    print(f"files_audited={int(summary.get('files_audited', 0))}")
    print(f"files_existing={int(summary.get('files_existing', 0))}")
    print(f"files_with_today_rows={int(summary.get('files_with_today_rows', 0))}")
    print(f"files_with_selected_meeting_rows={int(summary.get('files_with_selected_meeting_rows', 0))}")
    print(f"best_scrape_inventory_source={summary.get('best_scrape_inventory_source', '')}")
    print(f"best_terminal_inventory_source={summary.get('best_terminal_inventory_source', '')}")
    print(f"status={summary.get('status', '')}")
    print(f"wrote={AUDIT_OUT}")
    print(f"wrote={SUMMARY_OUT}")

    if not audit_df.empty:
        print("[CURRENT_DAY_SOURCE_INVENTORY_AUDIT_V1] SOURCE_ROWS")
        print(
            audit_df[
                [
                    "file_name",
                    "freshness_status",
                    "max_race_date",
                    "today_row_count",
                    "selected_meeting_row_count",
                    "usable_for_scrape_inventory",
                    "usable_for_terminal_inventory",
                ]
            ].to_string(index=False)
        )


if __name__ == "__main__":
    main()
