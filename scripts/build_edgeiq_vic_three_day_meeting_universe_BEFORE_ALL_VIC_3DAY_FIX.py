from __future__ import annotations

import csv
import re
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


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

try:
    LOCAL_TZ = ZoneInfo("Australia/Sydney")
except Exception:
    LOCAL_TZ = timezone(timedelta(hours=10), name="Australia/Sydney")

VIC_TRACKS = {
    "ARARAT", "AVOCA", "BAIRNSDALE", "BALLARAT", "BALNARRING", "BENDIGO", "BENALLA",
    "BET365 STAWELL", "CAULFIELD", "COLAC", "CRANBOURNE", "DONALD", "DUNKELD", "ECHUCA",
    "FLEMINGTON", "GEELONG", "HAMILTON", "HANGING ROCK", "HORSHAM", "KILMORE", "KYNETON",
    "MILDURA", "MOE", "MOONEE VALLEY", "MORNINGTON", "MORTLAKE", "MURTOA", "PAKENHAM",
    "PENSHURST", "SALE", "SANDOWN", "SEYMOUR", "ST ARNAUD", "STAWELL", "TERANG",
    "THE VALLEY", "TOWONG", "TRARALGON", "WANGARATTA", "WARRACKNABEAL", "WARRNAMBOOL",
    "WERRIBEE", "WODONGA", "YARRA VALLEY",
}

FIELDS = [
    "built_at", "meeting_key", "race_key", "runner_key", "source", "race_date", "day_bucket", "track", "race_no", "race_time", "minutes_to_jump",
    "race_state", "distance", "race_class", "track_condition", "horse_no", "saddlecloth", "horse",
    "horse_key", "barrier", "jockey", "trainer", "silkUrl", "silk_url", "local_silk_path",
    "is_scratched", "scratch_status", "runner_status", "ui_price", "sportsbet_price", "live_price",
    "market_price", "fixed_win", "rated_price", "ui_fair_price", "edge_pct", "ui_edge_pct",
    "truth_grade", "market_confidence", "liquidity_grade", "fake_overlay_flag", "late_drift_risk",
    "execution_trust_score", "suppression_action", "suppression_reason", "clv_expectation",
    "open_price", "mid_price", "close_price", "flucs", "last10", "last_10", "speed_map_bucket",
    "map_position", "run_style", "pace_profile", "settling_band", "map_x_pct", "map_y_px",
]

DIAG_FIELDS = ["built_at", "metric", "race_date", "track", "race_no", "value", "message"]


def now_local() -> datetime:
    return datetime.now(LOCAL_TZ)


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null"} else text


def clean_track_key(value: object) -> str:
    return " ".join(clean(value).upper().replace("|", " ").replace("_", " ").split())


def meeting_key_value(race_date: object, track: object) -> str:
    return f"{clean(race_date)}_{clean_track_key(track)}"


def canonical_race_key(race_date: object, track: object, race_no_value: object) -> str:
    digits = "".join(ch for ch in clean(race_no_value) if ch.isdigit()) or "0"
    return f"{meeting_key_value(race_date, track)}_R{int(digits)}"


def canonical_runner_key(race_date: object, track: object, race_no_value: object, horse_key_value: object, horse: object) -> str:
    runner = clean(horse_key_value) or "".join(ch for ch in clean(horse).upper() if ch.isalnum())
    return f"{canonical_race_key(race_date, track, race_no_value)}_{runner}"


def norm_track(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"\b(SPORTSBET|BET365|LADBROKES|TAB|RACING\.COM|RACING|PARK|MRC|VRC)\b", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_vic(row: dict[str, str]) -> bool:
    state = clean(row.get("state") or row.get("state_rated")).upper()
    track = norm_track(row.get("track") or row.get("meeting") or row.get("track_name"))
    if state and state != "VIC":
        return False
    return track in VIC_TRACKS or any(track.startswith(v) or v in track for v in VIC_TRACKS)


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


def parse_date(value: object) -> datetime.date | None:
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


def race_datetime(row: dict[str, str], race_date: datetime.date) -> tuple[str, float | None]:
    raw = clean(row.get("race_time") or row.get("race_time_rated") or row.get("jump_time") or row.get("start_time") or row.get("time"))
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
    date = race_date or first(row, ["race_date", "date", "meeting_date"])
    track = norm_track(first(row, ["track", "meeting", "track_name"]))
    rn = race_no(first(row, ["race_no", "race_number", "race"]))
    hk = horse_key(first(row, ["horse_key", "_horse_key", "horse", "runner", "horse_name", "runner_name"]))
    return date, track, rn, hk


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


def build_base_rows() -> tuple[list[dict[str, str]], list[dict[str, object]]]:
    today = now_local().date()
    max_date = today + timedelta(days=2)
    seen: dict[tuple[str, str, int, str], dict[str, str]] = {}
    diagnostics: list[dict[str, object]] = []
    stale_removed = 0
    future_removed = 0
    undated_removed = 0

    for path in FIELD_SOURCES:
        for row in read_csv(path):
            if not is_vic(row):
                continue

            date_value = parse_date(first(row, ["race_date", "date", "meeting_date", "race_date_rated", "date_rated"]))
            if date_value is None:
                undated_removed += 1
                continue
            if date_value < today:
                stale_removed += 1
                continue
            if date_value > max_date:
                future_removed += 1
                continue
            horse = first(row, ["horse", "runner", "horse_name", "runner_name", "horse_rated"])
            track = norm_track(first(row, ["track", "meeting", "track_name"]))
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

    diagnostics.extend([
        diag("stale_rows_removed", "", "", "", stale_removed, "Rows older than today removed from universe"),
        diag("future_rows_removed", "", "", "", future_removed, "Rows beyond next day removed from universe"),
        diag("undated_field_rows_removed", "", "", "", undated_removed, "Undated rows cannot create meetings"),
    ])
    return list(seen.values()), diagnostics


def diag(metric: str, race_date: object, track: object, race_no_value: object, value: object, message: str) -> dict[str, object]:
    return {
        "built_at": now_local().isoformat(timespec="seconds"),
        "metric": metric,
        "race_date": race_date,
        "track": track,
        "race_no": race_no_value,
        "value": value,
        "message": message,
    }


def build_lookup(paths: list[Path]) -> tuple[dict[tuple[str, str, int, str], dict[str, str]], dict[tuple[str, int, str], dict[str, str]]]:
    exact: dict[tuple[str, str, int, str], dict[str, str]] = {}
    loose: dict[tuple[str, int, str], dict[str, str]] = {}

    def enrich(target: dict[str, str], source: dict[str, str]) -> None:
        for field, value in source.items():
            if not clean(value):
                continue

            # Price / market / map fields are allowed to be refreshed by later,
            # more specific sources. This prevents older weak rows blocking
            # speed-map, suppression, race-state, and market-truth fields.
            if field in {
                "ui_price", "sportsbet_price", "live_price", "market_price", "fixed_win",
                "rated_price", "ui_fair_price", "edge_pct", "ui_edge_pct",
                "truth_grade", "market_confidence", "liquidity_grade", "fake_overlay_flag",
                "late_drift_risk", "execution_trust_score", "suppression_action",
                "suppression_reason", "clv_expectation", "open_price", "mid_price",
                "close_price", "flucs", "last10", "last_10",
                "speed_map_bucket", "map_position", "run_style", "pace_profile",
                "settling_band", "map_x_pct", "map_y_px",
            }:
                target[field] = value
                continue

            # Identity and field-card data should not be overwritten once set.
            if not clean(target.get(field)):
                target[field] = value

    for path in paths:
        for row in read_csv(path):
            key = key_for(row)
            loose_key = loose_key_for(row)

            if key[0] and key[1] and key[2] and key[3]:
                if key not in exact:
                    exact[key] = {}
                enrich(exact[key], row)

            if loose_key[0] and loose_key[1] and loose_key[2]:
                if loose_key not in loose:
                    loose[loose_key] = {}
                enrich(loose[loose_key], row)

    return exact, loose


def merge_row(base: dict[str, str], exact: dict[tuple[str, str, int, str], dict[str, str]], loose: dict[tuple[str, int, str], dict[str, str]]) -> dict[str, object]:
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
                "ui_price", "sportsbet_price", "live_price", "market_price", "fixed_win", "rated_price",
                "ui_fair_price", "edge_pct", "ui_edge_pct", "truth_grade", "market_confidence",
                "liquidity_grade", "fake_overlay_flag", "late_drift_risk", "execution_trust_score",
                "suppression_action", "suppression_reason", "clv_expectation", "open_price", "mid_price",
                "close_price", "flucs", "settling_band", "map_x_pct", "map_y_px",
            } and clean(value):
                merged[key] = value

    race_time, minutes = race_datetime(merged, parse_date(race_date) or now_local().date())
    track = norm_track(first(merged, ["track", "meeting", "track_name"]))
    rn = race_no(first(merged, ["race_no", "race_number", "race"]))
    horse = first(merged, ["horse", "runner", "horse_name", "runner_name", "horse_rated"])
    scratch = boolish(first(merged, ["is_scratched", "scratched", "scratch_status", "runner_status", "status"]))
    live_price = number_text(first(merged, ["ui_price", "sportsbet_price", "live_price", "market_price", "fixed_win"])) or "-"
    fair_price = number_text(first(merged, ["ui_fair_price", "rated_price", "fair_price"])) or "-"
    edge = number_text(first(merged, ["ui_edge_pct", "edge_pct", "overlay_pct"])) or "-"
    hk = horse_key(first(merged, ["horse_key", "_horse_key", "horse", "runner", "horse_name", "horse_rated"]))

    return {
        "built_at": now_local().isoformat(timespec="seconds"),
        "meeting_key": meeting_key_value(race_date, track),
        "race_key": canonical_race_key(race_date, track, rn),
        "runner_key": canonical_runner_key(race_date, track, rn, hk, horse),
        "source": first(merged, ["_source_name", "source"]) or "three_day_universe",
        "race_date": race_date,
        "day_bucket": day_bucket(parse_date(race_date) or now_local().date()),
        "track": track,
        "race_no": rn,
        "race_time": race_time,
        "minutes_to_jump": "" if minutes is None else minutes,
        "race_state": first(merged, ["race_state"]) or state_from_minutes(minutes),
        "distance": first(merged, ["distance", "distance_rated"]),
        "race_class": first(merged, ["race_class", "race_class_clean", "race_class_rated"]),
        "track_condition": first(merged, ["track_condition", "track_condition_rated"]),
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


def day_bucket(date_value: datetime.date) -> str:
    delta = (date_value - now_local().date()).days
    if delta == 0:
        return "TODAY"
    if delta == 1:
        return "TOMORROW"
    if delta == 2:
        return "NEXT_DAY"
    return "OUTSIDE_WINDOW"


def state_from_minutes(minutes: float | None) -> str:
    if minutes is None:
        return "TIME_TBC"
    if minutes > 90:
        return "PREOPEN"
    if minutes > 25:
        return "STANDBY"
    if minutes > 3:
        return "NEXT_UP"
    if minutes > -5:
        return "ACTIVE"
    if minutes > -25:
        return "CLOSED"
    return "RESULTED"


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    base_rows, diagnostics = build_base_rows()
    price_exact, price_loose = build_lookup(PRICE_SOURCES + MERGE_SOURCES)
    rows = [merge_row(row, price_exact, price_loose) for row in base_rows]
    rows.sort(key=lambda row: (
        {"TODAY": 0, "TOMORROW": 1, "NEXT_DAY": 2}.get(str(row["day_bucket"]), 9),
        str(row["race_date"]),
        str(row["track"]),
        int(row["race_no"] or 0),
        int(float(str(row["horse_no"] or row["saddlecloth"] or 999))),
    ))

    missing_prices = sum(1 for row in rows if row["ui_price"] == "-" and not row["is_scratched"])
    race_keys = {(row["race_date"], row["track"], row["race_no"]) for row in rows}
    meeting_keys = {(row["race_date"], row["track"]) for row in rows}
    for race_date, track in sorted(meeting_keys):
        diagnostics.append(diag("meeting", race_date, track, "", sum(1 for row in rows if row["race_date"] == race_date and row["track"] == track), "meeting_rows"))
    for race_date, track, rn in sorted(race_keys):
        diagnostics.append(diag("race", race_date, track, rn, sum(1 for row in rows if row["race_date"] == race_date and row["track"] == track and row["race_no"] == rn), "race_field_size"))
    for bucket in ("TODAY", "TOMORROW", "NEXT_DAY"):
        diagnostics.append(diag("day_bucket_count", "", "", "", sum(1 for row in rows if row["day_bucket"] == bucket), bucket))
    diagnostics.append(diag("missing_price_count", "", "", "", missing_prices, "Runners retained with no live price"))
    diagnostics.append(diag("universe_rows", "", "", "", len(rows), "Total field-driven rows"))
    diagnostics.append(diag("universe_races", "", "", "", len(race_keys), "Total races in three-day VIC universe"))

    write_csv(UNIVERSE_OUT, rows, FIELDS)
    write_csv(FIELDS_OUT, rows, FIELDS)
    write_csv(DIAG_OUT, diagnostics, DIAG_FIELDS)
    print("=" * 100)
    print("EDGEIQ VIC THREE DAY MEETING UNIVERSE")
    print("=" * 100)
    print("ROWS:", len(rows))
    print("RACES:", len(race_keys))
    print("MISSING_PRICES:", missing_prices)
    print("OUT:", UNIVERSE_OUT)
    print("FIELDS:", FIELDS_OUT)
    print("DIAG:", DIAG_OUT)


if __name__ == "__main__":
    main()



