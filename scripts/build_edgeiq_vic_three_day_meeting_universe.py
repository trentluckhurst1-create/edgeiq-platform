from __future__ import annotations

import csv
import re
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from edgeiq_three_day_window_v1_common import (
    TIMEZONE,
    build_three_day_window,
)

from build_edgeiq_vic_three_day_meeting_calendar_v1 import (
    CALENDAR_OUT,
    build_calendar_rows,
    day_bucket_for_date,
    meeting_key_value as calendar_meeting_key,
    normalise_track,
    write_calendar_output,
)


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
UNIVERSE_OUT = DATA / "edgeiq_vic_three_day_meeting_universe.csv"
FIELDS_OUT = DATA / "edgeiq_vic_three_day_race_fields.csv"
DIAG_OUT = DATA / "edgeiq_vic_three_day_meeting_diagnostics.csv"

FIELD_SOURCES = [
    DATA / "race_card_report.csv",
    DATA / "race_fields.csv",
    DATA / "edgeiq_vic_live_fields_synced.csv",
    DATA / "edgeiq_live_runner_board_v1.csv",
]

PRICE_SOURCES = [
    DATA / "edgeiq_vic_live_terminal_feed_v1.csv",
    DATA / "edgeiq_live_runner_board_v1.csv",
    DATA / "edgeiq_live_terminal_feed_v1.csv",
]

MERGE_SOURCES = [
    DATA / "edgeiq_market_truth_engine_v3.csv",
    DATA / "edgeiq_execution_suppression_v2.csv",
    DATA / "edgeiq_clv_memory.csv",
    DATA / "edgeiq_race_state_engine.csv",
    DATA / "edgeiq_real_speed_map_positions.csv",
]

LOCAL_TZ = TIMEZONE

VIC_TRACKS = {
    "ARARAT",
    "AVOCA",
    "BAIRNSDALE",
    "BALLARAT",
    "BALLARAT SYNTHETIC",
    "BALNARRING",
    "BENDIGO",
    "BENALLA",
    "BET365 STAWELL",
    "CAULFIELD",
    "CAULFIELD HEATH",
    "CASTERTON",
    "COLAC",
    "CRANBOURNE",
    "DONALD",
    "DUNKELD",
    "ECHUCA",
    "FLEMINGTON",
    "GEELONG",
    "HAMILTON",
    "HANGING ROCK",
    "HORSHAM",
    "KILMORE",
    "KYNETON",
    "MILDURA",
    "MOE",
    "MOONEE VALLEY",
    "MORNINGTON",
    "MORTLAKE",
    "MURTOA",
    "PAKENHAM",
    "PAKENHAM SYNTHETIC",
    "PENSHURST",
    "SALE",
    "SANDOWN",
    "SEYMOUR",
    "ST ARNAUD",
    "STAWELL",
    "SWAN HILL",
    "TERANG",
    "THE VALLEY",
    "TOWONG",
    "TRARALGON",
    "WANGARATTA",
    "WARRACKNABEAL",
    "WARRNAMBOOL",
    "WERRIBEE",
    "WODONGA",
    "YARRA VALLEY",
}

FIELDS = [
    "built_at",
    "meeting_key",
    "race_key",
    "runner_key",
    "source",
    "race_date",
    "day_bucket",
    "meeting_type",
    "meeting_status",
    "dashboard_ready",
    "track",
    "race_no",
    "race_time",
    "minutes_to_jump",
    "race_state",
    "distance",
    "race_class",
    "track_condition",
    "rail_position",
    "horse_no",
    "saddlecloth",
    "horse",
    "horse_key",
    "barrier",
    "jockey",
    "trainer",
    "silkUrl",
    "silk_url",
    "local_silk_path",
    "is_scratched",
    "scratch_status",
    "runner_status",
    "ui_price",
    "sportsbet_price",
    "live_price",
    "market_price",
    "fixed_win",
    "rated_price",
    "ui_fair_price",
    "edge_pct",
    "ui_edge_pct",
    "truth_grade",
    "market_confidence",
    "liquidity_grade",
    "fake_overlay_flag",
    "late_drift_risk",
    "execution_trust_score",
    "suppression_action",
    "suppression_reason",
    "clv_expectation",
    "open_price",
    "mid_price",
    "close_price",
    "flucs",
    "last10",
    "last_10",
    "speed_map_bucket",
    "map_position",
    "run_style",
    "pace_profile",
    "settling_band",
    "map_x_pct",
    "map_y_px",
]

DIAG_FIELDS = [
    "built_at",
    "record_type",
    "race_date",
    "track",
    "day_bucket",
    "meeting_type",
    "meeting_status",
    "dashboard_ready",
    "field_rows",
    "field_races",
    "priced_rows",
    "value",
    "message",
]


def now_local() -> datetime:
    return datetime.now(LOCAL_TZ)


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null", "undefined"} else text


def meeting_key_value(race_date: object, track: object) -> str:
    return calendar_meeting_key(race_date, track)


def canonical_race_key(race_date: object, track: object, race_no_value: object) -> str:
    digits = "".join(ch for ch in clean(race_no_value) if ch.isdigit()) or "0"
    return f"{meeting_key_value(race_date, track)}_R{int(digits)}"


def canonical_runner_key(
    race_date: object,
    track: object,
    race_no_value: object,
    horse_key_value: object,
    horse: object,
) -> str:
    runner = clean(horse_key_value) or "".join(ch for ch in clean(horse).upper() if ch.isalnum())
    return f"{canonical_race_key(race_date, track, race_no_value)}_{runner}"


def norm_track(value: object) -> str:
    return normalise_track(value)


def is_vic(row: dict[str, str]) -> bool:
    state = clean(row.get("state") or row.get("state_rated")).upper()
    track = norm_track(row.get("track") or row.get("meeting") or row.get("track_name"))
    if state and state != "VIC":
        return False
    return track in VIC_TRACKS


def horse_key(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = text.replace("â€™", "").replace("'", "")
    return re.sub(r"[^A-Z0-9]", "", text)


def race_no(value: object) -> int:
    text = clean(value).upper().replace("RACE", "").replace("R", "")
    digits = re.sub(r"[^0-9]", "", text)
    return int(digits) if digits else 0


def number_text(value: object) -> str:
    text = clean(value).replace("$", "").replace(",", "")
    if text == "-":
        return ""
    try:
        value_float = float(text)
        if value_float <= 0:
            return ""
        return f"{value_float:.4f}".rstrip("0").rstrip(".")
    except ValueError:
        return text


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    except Exception:
        return []


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{int(datetime.now().timestamp() * 1000)}.tmp")
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def parse_date(value: object) -> date | None:
    text = clean(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=LOCAL_TZ)
        return parsed.astimezone(LOCAL_TZ).date()
    except ValueError:
        return None


def parse_time(value: object) -> time | None:
    text = clean(value).upper().replace(".", ":")
    if not text:
        return None
    if "T" in text:
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=LOCAL_TZ)
            return parsed.astimezone(LOCAL_TZ).time().replace(second=0, microsecond=0)
        except ValueError:
            pass
    for fmt in ("%H:%M:%S", "%H:%M", "%I:%M%p", "%I:%M %p"):
        try:
            return datetime.strptime(text, fmt).time().replace(second=0, microsecond=0)
        except ValueError:
            pass
    match = re.search(r"(\d{1,2}):(\d{2})", text)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2))
    if "PM" in text and hour < 12:
        hour += 12
    if "AM" in text and hour == 12:
        hour = 0
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return time(hour, minute)
    return None


def race_datetime(row: dict[str, str], race_date: date) -> tuple[str, float | None]:
    raw = clean(
        row.get("race_time")
        or row.get("race_time_rated")
        or row.get("jump_time")
        or row.get("start_time")
        or row.get("time")
    )
    parsed_time = parse_time(raw)
    if parsed_time is None:
        return raw, None
    dt = datetime.combine(race_date, parsed_time, tzinfo=LOCAL_TZ)
    minutes = round((dt - now_local()).total_seconds() / 60, 1)
    return dt.strftime("%H:%M"), minutes


def boolish(value: object) -> bool:
    return clean(value).upper() in {"1", "Y", "YES", "TRUE", "SCR", "SCRATCHED", "LATE SCR", "WITHDRAWN"}


def first(row: dict[str, str], names: list[str]) -> str:
    for name in names:
        value = clean(row.get(name))
        if value:
            return value
    return ""


def key_for(row: dict[str, str], race_date: str | None = None) -> tuple[str, str, int, str]:
    date_value = race_date or first(row, ["race_date", "date", "meeting_date"])
    track = norm_track(first(row, ["track", "meeting", "track_name"]))
    rn = race_no(first(row, ["race_no", "race_number", "race"]))
    hk = horse_key(first(row, ["horse_key", "_horse_key", "horse", "runner", "horse_name", "runner_name"]))
    return date_value, track, rn, hk


def loose_key_for(row: dict[str, str]) -> tuple[str, int, str]:
    _, track, rn, hk = key_for(row)
    return track, rn, hk


def source_priority(path: Path) -> int:
    if path.name == "race_card_report.csv":
        return 1
    if path.name == "race_fields.csv":
        return 2
    if path.name == "edgeiq_vic_live_fields_synced.csv":
        return 3
    return 4


def meeting_status(day_bucket: str, field_rows: int) -> str:
    if field_rows > 0:
        return "FIELDS_READY"
    if day_bucket == "TODAY":
        return "FIELDS_UNAVAILABLE"
    return "FIELDS_PENDING"


def dashboard_ready_value(status: str) -> str:
    return "YES" if status == "FIELDS_READY" else "NO"


def build_calendar_map() -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    calendar_rows = build_calendar_rows()
    write_calendar_output(calendar_rows, CALENDAR_OUT)
    mapping = {meeting_key_value(row["race_date"], row["track"]): row for row in calendar_rows}
    return calendar_rows, mapping


def build_base_rows(
    calendar_map: dict[str, dict[str, object]],
) -> tuple[list[dict[str, str]], dict[str, int], dict[str, set[int]], list[dict[str, object]]]:
    seen: dict[tuple[str, str, int, str], dict[str, str]] = {}
    field_rows_by_meeting: dict[str, int] = {key: 0 for key in calendar_map}
    race_nos_by_meeting: dict[str, set[int]] = {key: set() for key in calendar_map}
    diagnostics: list[dict[str, object]] = []
    stale_removed = 0
    outside_window_removed = 0
    undated_removed = 0
    off_calendar_removed = 0

    for path in FIELD_SOURCES:
        for row in read_csv(path):
            if not is_vic(row):
                continue

            date_value = parse_date(
                first(row, ["race_date", "date", "meeting_date", "race_date_rated", "date_rated"])
            )
            if date_value is None:
                undated_removed += 1
                continue

            track = norm_track(first(row, ["track", "meeting", "track_name"]))
            meeting_key = meeting_key_value(date_value.isoformat(), track)
            calendar_row = calendar_map.get(meeting_key)
            if calendar_row is None:
                if date_value < now_local().date():
                    stale_removed += 1
                else:
                    off_calendar_removed += 1
                continue

            if str(calendar_row.get("day_bucket")) not in {"TODAY", "TOMORROW", "DAY+2"}:
                outside_window_removed += 1
                continue

            horse = first(row, ["horse", "runner", "horse_name", "runner_name", "horse_rated"])
            rn = race_no(first(row, ["race_no", "race_number", "race", "race_number_rated"]))
            if not horse or not track or not rn:
                continue

            key = key_for(row, date_value.isoformat())
            current = seen.get(key)
            enriched = dict(row)
            enriched["_source_priority"] = str(source_priority(path))
            enriched["_source_name"] = path.name
            enriched["_race_date_normalised"] = date_value.isoformat()
            if current is None or int(enriched["_source_priority"]) < int(current.get("_source_priority", "99")):
                seen[key] = enriched

            field_rows_by_meeting[meeting_key] = field_rows_by_meeting.get(meeting_key, 0) + 1
            race_nos_by_meeting.setdefault(meeting_key, set()).add(rn)

    diagnostics.extend(
        [
            diag("SUMMARY", "", "", "", "", "", "", "", stale_removed, "rows_older_than_calendar_window_removed"),
            diag("SUMMARY", "", "", "", "", "", "", "", outside_window_removed, "rows_outside_three_day_calendar_removed"),
            diag("SUMMARY", "", "", "", "", "", "", "", undated_removed, "undated_field_rows_removed"),
            diag("SUMMARY", "", "", "", "", "", "", "", off_calendar_removed, "rows_not_present_in_calendar_removed"),
        ]
    )
    return list(seen.values()), field_rows_by_meeting, race_nos_by_meeting, diagnostics


def diag(
    record_type: str,
    race_date: object,
    track: object,
    day_bucket: object,
    meeting_type: object,
    status: object,
    dashboard_ready: object,
    field_rows: object,
    value: object,
    message: str,
    field_races: object = "",
    priced_rows: object = "",
) -> dict[str, object]:
    return {
        "built_at": now_local().isoformat(timespec="seconds"),
        "record_type": record_type,
        "race_date": race_date,
        "track": track,
        "day_bucket": day_bucket,
        "meeting_type": meeting_type,
        "meeting_status": status,
        "dashboard_ready": dashboard_ready,
        "field_rows": field_rows,
        "field_races": field_races,
        "priced_rows": priced_rows,
        "value": value,
        "message": message,
    }


def build_lookup(
    paths: list[Path],
) -> tuple[dict[tuple[str, str, int, str], dict[str, str]], dict[tuple[str, int, str], dict[str, str]]]:
    exact: dict[tuple[str, str, int, str], dict[str, str]] = {}
    loose: dict[tuple[str, int, str], dict[str, str]] = {}

    def enrich(target: dict[str, str], source: dict[str, str]) -> None:
        for field, value in source.items():
            if not clean(value):
                continue
            if field in {
                "ui_price",
                "sportsbet_price",
                "live_price",
                "market_price",
                "fixed_win",
                "rated_price",
                "ui_fair_price",
                "edge_pct",
                "ui_edge_pct",
                "truth_grade",
                "market_confidence",
                "liquidity_grade",
                "fake_overlay_flag",
                "late_drift_risk",
                "execution_trust_score",
                "suppression_action",
                "suppression_reason",
                "clv_expectation",
                "open_price",
                "mid_price",
                "close_price",
                "flucs",
                "last10",
                "last_10",
                "speed_map_bucket",
                "map_position",
                "run_style",
                "pace_profile",
                "settling_band",
                "map_x_pct",
                "map_y_px",
            }:
                target[field] = value
                continue
            if not clean(target.get(field)):
                target[field] = value

    for path in paths:
        for row in read_csv(path):
            key = key_for(row)
            loose_key = loose_key_for(row)
            if key[0] and key[1] and key[2] and key[3]:
                exact.setdefault(key, {})
                enrich(exact[key], row)
            if loose_key[0] and loose_key[1] and loose_key[2]:
                loose.setdefault(loose_key, {})
                enrich(loose[loose_key], row)

    return exact, loose


def merge_row(
    base: dict[str, str],
    exact: dict[tuple[str, str, int, str], dict[str, str]],
    loose: dict[tuple[str, int, str], dict[str, str]],
    calendar_map: dict[str, dict[str, object]],
    field_rows_by_meeting: dict[str, int],
) -> dict[str, object]:
    race_date = base["_race_date_normalised"]
    exact_key = key_for(base, race_date)
    loose_key = loose_key_for(base)
    merged = dict(base)
    for row in [exact.get(exact_key), loose.get(loose_key)]:
        if not row:
            continue
        for key, value in row.items():
            if clean(value) and not clean(merged.get(key)):
                merged[key] = value
            if key in {
                "ui_price",
                "sportsbet_price",
                "live_price",
                "market_price",
                "fixed_win",
                "rated_price",
                "ui_fair_price",
                "edge_pct",
                "ui_edge_pct",
                "truth_grade",
                "market_confidence",
                "liquidity_grade",
                "fake_overlay_flag",
                "late_drift_risk",
                "execution_trust_score",
                "suppression_action",
                "suppression_reason",
                "clv_expectation",
                "open_price",
                "mid_price",
                "close_price",
                "flucs",
                "settling_band",
                "map_x_pct",
                "map_y_px",
            } and clean(value):
                merged[key] = value

    track = norm_track(first(merged, ["track", "meeting", "track_name"]))
    rn = race_no(first(merged, ["race_no", "race_number", "race"]))
    meeting_key = meeting_key_value(race_date, track)
    calendar_row = calendar_map.get(meeting_key, {})
    status = meeting_status(str(calendar_row.get("day_bucket", "")), field_rows_by_meeting.get(meeting_key, 0))
    dashboard_ready = dashboard_ready_value(status)

    race_time, minutes = race_datetime(merged, parse_date(race_date) or now_local().date())
    horse = first(merged, ["horse", "runner", "horse_name", "runner_name", "horse_rated"])
    scratch = boolish(first(merged, ["is_scratched", "scratched", "scratch_status", "runner_status", "status"]))
    live_price = number_text(first(merged, ["ui_price", "sportsbet_price", "live_price", "market_price", "fixed_win"])) or "-"
    fair_price = number_text(first(merged, ["ui_fair_price", "rated_price", "fair_price"])) or "-"
    edge = number_text(first(merged, ["ui_edge_pct", "edge_pct", "overlay_pct"])) or "-"
    hk = horse_key(first(merged, ["horse_key", "_horse_key", "horse", "runner", "horse_name", "horse_rated"]))

    return {
        "built_at": now_local().isoformat(timespec="seconds"),
        "meeting_key": meeting_key,
        "race_key": canonical_race_key(race_date, track, rn),
        "runner_key": canonical_runner_key(race_date, track, rn, hk, horse),
        "source": first(merged, ["_source_name", "source"]) or "three_day_universe",
        "race_date": race_date,
        "day_bucket": str(calendar_row.get("day_bucket") or day_bucket_for_date(parse_date(race_date) or now_local().date())),
        "meeting_type": str(calendar_row.get("meeting_type") or "UNKNOWN"),
        "meeting_status": status,
        "dashboard_ready": dashboard_ready,
        "track": track,
        "race_no": rn,
        "race_time": race_time,
        "minutes_to_jump": "" if minutes is None else minutes,
        "race_state": first(merged, ["race_state"]) or state_from_minutes(minutes),
        "distance": first(merged, ["distance", "distance_rated"]),
        "race_class": first(merged, ["race_class", "race_class_clean", "race_class_rated"]),
        "track_condition": first(merged, ["track_condition", "track_condition_rated"]),
        "rail_position": first(merged, ["rail_position", "rail_position_rated", "rail", "railPosition"]),
        "horse_no": first(merged, ["horse_no", "saddlecloth", "number", "runner_number", "tab_no", "horse_no_rated"]),
        "saddlecloth": first(merged, ["saddlecloth", "horse_no", "number", "runner_number", "tab_no", "horse_no_rated"]),
        "horse": horse,
        "horse_key": hk,
        "barrier": first(merged, ["barrier", "barrier_rated", "gate", "bar"]),
        "jockey": first(merged, ["jockey", "jockey_rated"]),
        "trainer": first(merged, ["trainer", "trainer_rated"]),
        "silkUrl": first(merged, ["silkUrl", "silk_url", "local_silk_path", "mobile_silk_image", "silk", "silks"]),
        "silk_url": first(merged, ["silk_url", "silkUrl", "local_silk_path", "mobile_silk_image", "silk", "silks"]),
        "local_silk_path": first(merged, ["local_silk_path", "silk_url", "silkUrl"]),
        "is_scratched": "1" if scratch else "",
        "scratch_status": "SCRATCHED" if scratch else first(merged, ["scratch_status"]),
        "runner_status": "SCRATCHED" if scratch else first(merged, ["runner_status"]),
        "ui_price": "-" if scratch else live_price,
        "sportsbet_price": "-" if scratch else number_text(first(merged, ["sportsbet_price"])) or "-",
        "live_price": "-" if scratch else number_text(first(merged, ["live_price"])) or live_price,
        "market_price": "-" if scratch else number_text(first(merged, ["market_price"])) or live_price,
        "fixed_win": "-" if scratch else number_text(first(merged, ["fixed_win"])) or live_price,
        "rated_price": "-" if scratch else fair_price,
        "ui_fair_price": "-" if scratch else fair_price,
        "edge_pct": "-" if scratch else edge,
        "ui_edge_pct": "-" if scratch else edge,
        "truth_grade": "-" if scratch else first(merged, ["truth_grade"]) or "-",
        "market_confidence": "-" if scratch else first(merged, ["market_confidence"]) or "-",
        "liquidity_grade": "-" if scratch else first(merged, ["liquidity_grade"]) or "-",
        "fake_overlay_flag": "-" if scratch else first(merged, ["fake_overlay_flag"]) or "-",
        "late_drift_risk": "-" if scratch else first(merged, ["late_drift_risk"]) or "-",
        "execution_trust_score": "-" if scratch else first(merged, ["execution_trust_score"]) or "-",
        "suppression_action": "SCRATCHED" if scratch else first(merged, ["suppression_action", "ui_action", "execution_action"]) or "-",
        "suppression_reason": "SCRATCHED" if scratch else first(merged, ["suppression_reason"]) or "-",
        "clv_expectation": "-" if scratch else first(merged, ["clv_expectation", "clv_expected"]) or "-",
        "open_price": "-" if scratch else first(merged, ["open_price"]) or "-",
        "mid_price": "-" if scratch else first(merged, ["mid_price"]) or "-",
        "close_price": "-" if scratch else first(merged, ["close_price"]) or "-",
        "flucs": "-" if scratch else first(merged, ["flucs", "market_fluctuations", "price_fluctuations", "fixed_odds_flucs", "odds_flucs"]) or "-",
        "last10": first(merged, ["last10", "last_10"]),
        "last_10": first(merged, ["last_10", "last10"]),
        "speed_map_bucket": first(merged, ["speed_map_bucket"]),
        "map_position": first(merged, ["map_position", "settling_position"]),
        "run_style": first(merged, ["run_style", "run_style_cluster", "proxy_energy_archetype"]),
        "pace_profile": first(merged, ["pace_profile", "tempo_role"]),
        "settling_band": first(merged, ["settling_band"]),
        "map_x_pct": first(merged, ["map_x_pct"]),
        "map_y_px": first(merged, ["map_y_px"]),
    }


def state_from_minutes(minutes: float | None) -> str:
    if minutes is None:
        return "TIME_TBC"
    if minutes > 90:
        return "PREOPEN"
    if minutes > 25:
        return "STANDBY"
    if minutes > 3:
        return "ACTIVE"
    if minutes > -5:
        return "CLOSED"
    if minutes > -25:
        return "RESULTED"
    return "RESULTED"


def build_meeting_diagnostics(
    calendar_rows: list[dict[str, object]],
    field_rows_by_meeting: dict[str, int],
    race_nos_by_meeting: dict[str, set[int]],
    universe_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    diagnostics: list[dict[str, object]] = []
    priced_rows_by_meeting: dict[str, int] = {}
    for row in universe_rows:
        meeting_key = meeting_key_value(row.get("race_date"), row.get("track"))
        has_price = clean(row.get("ui_price")) not in {"", "-"}
        if has_price and clean(row.get("is_scratched")) != "1":
            priced_rows_by_meeting[meeting_key] = priced_rows_by_meeting.get(meeting_key, 0) + 1

    for meeting in calendar_rows:
        meeting_key = meeting_key_value(meeting["race_date"], meeting["track"])
        field_rows = field_rows_by_meeting.get(meeting_key, 0)
        field_races = len(race_nos_by_meeting.get(meeting_key, set()))
        status = meeting_status(str(meeting["day_bucket"]), field_rows)
        dashboard_ready = dashboard_ready_value(status)
        if status == "FIELDS_READY":
            message = "calendar_meeting_discovered_and_field_rows_loaded"
        elif status == "FIELDS_PENDING":
            message = "calendar_meeting_discovered_waiting_for_future_field_rows"
        else:
            message = "calendar_meeting_discovered_but_no_current_field_source_rows"
        diagnostics.append(
            diag(
                "MEETING",
                meeting["race_date"],
                meeting["track"],
                meeting["day_bucket"],
                meeting["meeting_type"],
                status,
                dashboard_ready,
                field_rows,
                field_rows,
                message,
                field_races=field_races,
                priced_rows=priced_rows_by_meeting.get(meeting_key, 0),
            )
        )

    ready_count = sum(
        1
        for row in calendar_rows
        if meeting_status(str(row["day_bucket"]), field_rows_by_meeting.get(meeting_key_value(row["race_date"], row["track"]), 0))
        == "FIELDS_READY"
    )
    pending_count = sum(
        1
        for row in calendar_rows
        if meeting_status(str(row["day_bucket"]), field_rows_by_meeting.get(meeting_key_value(row["race_date"], row["track"]), 0))
        == "FIELDS_PENDING"
    )
    unavailable_count = sum(
        1
        for row in calendar_rows
        if meeting_status(str(row["day_bucket"]), field_rows_by_meeting.get(meeting_key_value(row["race_date"], row["track"]), 0))
        == "FIELDS_UNAVAILABLE"
    )

    diagnostics.extend(
        [
            diag("SUMMARY", "", "", "", "", "", "", "", len(calendar_rows), "calendar_meetings_total"),
            diag("SUMMARY", "", "", "", "", "FIELDS_READY", "YES", "", ready_count, "calendar_meetings_fields_ready"),
            diag("SUMMARY", "", "", "", "", "FIELDS_PENDING", "NO", "", pending_count, "calendar_meetings_fields_pending"),
            diag("SUMMARY", "", "", "", "", "FIELDS_UNAVAILABLE", "NO", "", unavailable_count, "calendar_meetings_fields_unavailable"),
            diag("SUMMARY", "", "", "", "", "", "", "", len(universe_rows), "runner_rows_written_to_universe"),
            diag(
                "SUMMARY",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                sum(1 for row in universe_rows if clean(row.get("ui_price")) not in {"", "-"} and clean(row.get("is_scratched")) != "1"),
                "runner_rows_with_market_price",
            ),
        ]
    )
    return diagnostics


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    calendar_rows, calendar_map = build_calendar_map()
    base_rows, field_rows_by_meeting, race_nos_by_meeting, base_diagnostics = build_base_rows(calendar_map)
    price_exact, price_loose = build_lookup(PRICE_SOURCES + MERGE_SOURCES)
    rows = [merge_row(row, price_exact, price_loose, calendar_map, field_rows_by_meeting) for row in base_rows]
    rows.sort(
        key=lambda row: (
            {"TODAY": 0, "TOMORROW": 1, "DAY+2": 2}.get(str(row["day_bucket"]), 9),
            str(row["race_date"]),
            str(row["track"]),
            int(row["race_no"] or 0),
            int(float(str(row["horse_no"] or row["saddlecloth"] or 999))),
        )
    )

    diagnostics = base_diagnostics + build_meeting_diagnostics(
        calendar_rows,
        field_rows_by_meeting,
        race_nos_by_meeting,
        rows,
    )
    race_keys = {(row["race_date"], row["track"], row["race_no"]) for row in rows}
    missing_prices = sum(1 for row in rows if row["ui_price"] == "-" and not row["is_scratched"])

    write_csv(UNIVERSE_OUT, rows, FIELDS)
    write_csv(FIELDS_OUT, rows, FIELDS)
    write_csv(DIAG_OUT, diagnostics, DIAG_FIELDS)

    ready_meetings = sum(
        1
        for row in calendar_rows
        if meeting_status(str(row["day_bucket"]), field_rows_by_meeting.get(meeting_key_value(row["race_date"], row["track"]), 0))
        == "FIELDS_READY"
    )
    pending_meetings = sum(
        1
        for row in calendar_rows
        if meeting_status(str(row["day_bucket"]), field_rows_by_meeting.get(meeting_key_value(row["race_date"], row["track"]), 0))
        == "FIELDS_PENDING"
    )
    unavailable_meetings = sum(
        1
        for row in calendar_rows
        if meeting_status(str(row["day_bucket"]), field_rows_by_meeting.get(meeting_key_value(row["race_date"], row["track"]), 0))
        == "FIELDS_UNAVAILABLE"
    )

    print("=" * 100)
    print("EDGEIQ VIC THREE DAY MEETING UNIVERSE")
    print("=" * 100)
    print(f"calendar_meetings={len(calendar_rows)}")
    print(f"fields_ready_meetings={ready_meetings}")
    print(f"fields_pending_meetings={pending_meetings}")
    print(f"fields_unavailable_meetings={unavailable_meetings}")
    print(f"runner_rows={len(rows)}")
    print(f"races={len(race_keys)}")
    print(f"missing_prices={missing_prices}")
    print(f"calendar={CALENDAR_OUT}")
    print(f"universe={UNIVERSE_OUT}")
    print(f"fields={FIELDS_OUT}")
    print(f"diag={DIAG_OUT}")


if __name__ == "__main__":
    main()
