from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from audit_edgeiq_current_day_source_inventory_v1 import (
    TODAY,
    get_display_track,
    get_track_config,
    load_selected_source_rows,
)


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

TAB = DATA / "edgeiq_tab_live_prices_direct_v1.csv"
OUT = DATA / "edgeiq_live_terminal_feed_v1_TAB_ONLY_TODAY.csv"

LOCAL_TZ = ZoneInfo("Australia/Sydney")

FALLBACK_FIELDS = [
    "built_at", "meeting_key", "race_key", "runner_key", "source", "race_date", "day_bucket", "track", "race_no",
    "race_time", "minutes_to_jump", "race_state", "distance", "race_class", "track_condition", "rail_position",
    "horse_no", "saddlecloth", "horse", "horse_key", "barrier", "jockey", "trainer", "silkUrl", "silk_url",
    "local_silk_path", "mobile_silk_image", "is_scratched", "scratch_status", "runner_status", "ui_price",
    "sportsbet_price", "market_price", "fixed_win", "rated_price", "ui_fair_price", "edge_pct", "ui_edge_pct",
    "execution_action", "market_state", "market_mover", "movement_velocity", "bookmaker", "sportsbet_event_id",
    "sportsbet_market_id", "sportsbet_timestamp", "truth_grade", "market_confidence", "liquidity_grade",
    "fake_overlay_flag", "late_drift_risk", "execution_trust_score", "suppression_action", "suppression_reason",
    "clv_expectation", "open_price", "mid_price", "close_price", "flucs", "last10", "last_10", "speed_map_bucket",
    "map_position", "run_style", "pace_profile", "settling_band", "map_x_pct", "map_y_px", "ui_status",
    "market_source_status", "market_source_ready", "market_source_rows", "market_source_age_seconds",
    "market_source_file", "market_capture_timestamp", "terminal_scope", "intelligence_note", "live_rank", "fair_rank",
    "edge_rank", "tab_fixed_win", "tab_fixed_place", "tab_fixed_betting_status", "tab_live_price_source",
    "live_price", "live_price_source",
]


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null"} else text


def num(value: object) -> float | None:
    text = clean(value).replace("$", "").replace(",", "")
    if not text or text == "-":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def fmt_price(value: float | None) -> str:
    if value is None or value <= 0:
        return ""
    return f"{value:.2f}".rstrip("0").rstrip(".")


def fmt_pct(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.1f}".rstrip("0").rstrip(".")


def horse_key(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"\b(NZ|GB|IRE|USA|FR|JPN|SAF|GER|CAN)\b", " ", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def norm_track(value: object) -> str:
    return re.sub(r"\s+", " ", clean(value).upper()).strip()


def canonical_track(value: object) -> str:
    selected_track = get_display_track()
    aliases = {norm_track(alias) for alias in get_track_config(selected_track).get("aliases", set())}
    track = norm_track(value)
    if track in aliases:
        return selected_track
    return track


def race_no_int(value: object) -> int:
    digits = re.sub(r"[^0-9]", "", clean(value))
    return int(digits) if digits else 0


def parse_race_datetime(race_date: str, race_time: str) -> datetime | None:
    raw = clean(race_time).upper().replace(".", ":")
    if not raw:
        return None
    try:
        if "T" in raw:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=LOCAL_TZ)
            return parsed.astimezone(LOCAL_TZ)
    except ValueError:
        pass
    for fmt in ("%I:%M%p", "%I:%M %p", "%H:%M", "%H:%M:%S"):
        try:
            parsed = datetime.strptime(raw, fmt)
            return datetime(
                int(race_date[:4]),
                int(race_date[5:7]),
                int(race_date[8:10]),
                parsed.hour,
                parsed.minute,
                tzinfo=LOCAL_TZ,
            )
        except ValueError:
            continue
    return None


def state_from_minutes(minutes_to_jump: float | None, betting_status: str) -> str:
    status = clean(betting_status).upper()
    if status == "LATESCRATCHED":
        return "SCRATCHED"
    if status in {"OPEN", "PLACING", "WINNER", "LOSER"} and minutes_to_jump is None:
        return status
    if minutes_to_jump is None:
        return "TIME_TBC"
    if minutes_to_jump > 90:
        return "PREOPEN"
    if minutes_to_jump > 25:
        return "STANDBY"
    if minutes_to_jump > 3:
        return "NEXT_UP"
    if minutes_to_jump > -5:
        return "ACTIVE"
    if minutes_to_jump > -25:
        return "CLOSED"
    return "RESULTED"


def output_fields() -> list[str]:
    if OUT.exists():
        with OUT.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader, [])
            if header:
                for field in FALLBACK_FIELDS:
                    if field not in header:
                        header.append(field)
                return header
    return FALLBACK_FIELDS[:]


def build_tab_lookup() -> tuple[dict[tuple[str, int, str], dict[str, str]], int]:
    if not TAB.exists():
        return {}, 0
    if TAB.stat().st_size == 0:
        return {}, 0
    try:
        tab = pd.read_csv(TAB, dtype=str, keep_default_na=False, low_memory=False)
    except pd.errors.EmptyDataError:
        return {}, 0
    if tab.empty:
        return {}, 0
    tab["date_key"] = tab["meeting_date"].map(clean).str[:10]
    tab["race_no_key"] = tab["race_no"].map(race_no_int)
    tab["horse_key"] = tab["horse_key"].map(clean)
    lookup: dict[tuple[str, int, str], dict[str, str]] = {}
    for row in tab.to_dict("records"):
        lookup[(row["date_key"], row["race_no_key"], row["horse_key"])] = row
    return lookup, len(tab)


def live_edge_pct(live_price: float | None, fair_price: float | None) -> float | None:
    if live_price is None or live_price <= 0 or fair_price is None or fair_price <= 0:
        return None
    return round(((live_price / fair_price) - 1.0) * 100.0, 1)


def implied_probability(fair_price: float | None) -> float:
    if fair_price is None or fair_price <= 0:
        return 0.0
    return 1.0 / fair_price


def assign_ranks(frame: pd.DataFrame) -> pd.DataFrame:
    frame["live_rank"] = ""
    frame["fair_rank"] = ""
    frame["edge_rank"] = ""
    for _, index in frame.groupby("race_key", sort=False).groups.items():
        race = frame.loc[index].copy()
        active_mask = ~race["scratch_flag_bool"]

        live_rankable = race[active_mask & race["live_price_num"].notna() & race["live_price_num"].gt(0)].sort_values(
            ["live_price_num", "horse"]
        )
        for rank, idx in enumerate(live_rankable.index, start=1):
            frame.at[idx, "live_rank"] = str(rank)

        fair_rankable = race[active_mask & race["fair_price_num"].notna() & race["fair_price_num"].gt(0)].sort_values(
            ["fair_price_num", "horse"]
        )
        for rank, idx in enumerate(fair_rankable.index, start=1):
            frame.at[idx, "fair_rank"] = str(rank)

        edge_rankable = race[active_mask & race["edge_pct_num"].notna()].sort_values(
            ["edge_pct_num", "horse"],
            ascending=[False, True],
        )
        for rank, idx in enumerate(edge_rankable.index, start=1):
            frame.at[idx, "edge_rank"] = str(rank)

    return frame


def apply_scratch_normalisation(frame: pd.DataFrame) -> pd.DataFrame:
    frame["scratch_flag_bool"] = frame["is_scratched"].map(clean).str.upper().eq("YES")
    frame["fair_price_num"] = frame["rated_price"].map(num)
    frame["live_price_num"] = frame["live_price"].map(num)
    frame["edge_pct_num"] = frame["edge_pct"].map(num)

    for _, index in frame.groupby("race_key", sort=False).groups.items():
        race = frame.loc[index].copy()
        active_mask = (~race["scratch_flag_bool"]) & race["fair_price_num"].notna() & race["fair_price_num"].gt(0)
        active_prob_sum = float(race.loc[active_mask, "fair_price_num"].apply(implied_probability).sum())

        if active_prob_sum > 0:
            renorm_prob = race.loc[active_mask, "fair_price_num"].apply(implied_probability) / active_prob_sum
            renorm_fair = (1.0 / renorm_prob).round(4)
            frame.loc[renorm_fair.index, "fair_price_num"] = renorm_fair
            frame.loc[renorm_fair.index, "rated_price"] = renorm_fair.map(fmt_price)
            frame.loc[renorm_fair.index, "ui_fair_price"] = renorm_fair.map(fmt_price)

            recalculated_edge = [
                live_edge_pct(frame.at[idx, "live_price_num"], frame.at[idx, "fair_price_num"])
                for idx in renorm_fair.index
            ]
            frame.loc[renorm_fair.index, "edge_pct_num"] = recalculated_edge
            frame.loc[renorm_fair.index, "edge_pct"] = [fmt_pct(value) for value in recalculated_edge]
            frame.loc[renorm_fair.index, "ui_edge_pct"] = [fmt_pct(value) for value in recalculated_edge]

        scratched_index = race.index[race["scratch_flag_bool"]]
        if len(scratched_index) > 0:
            for column in ["rated_price", "ui_fair_price", "edge_pct", "ui_edge_pct", "live_rank", "fair_rank", "edge_rank"]:
                frame.loc[scratched_index, column] = ""
            for column in ["fair_price_num", "edge_pct_num"]:
                frame.loc[scratched_index, column] = pd.NA
            frame.loc[scratched_index, "execution_action"] = "SCRATCHED"
            frame.loc[scratched_index, "market_state"] = "SCRATCHED"
            frame.loc[scratched_index, "ui_status"] = "SCRATCHED"

    frame = assign_ranks(frame)
    return frame


def main() -> None:
    selected_track = get_display_track()
    source_path, card, choice, _ = load_selected_source_rows(purpose="terminal", write_outputs=True)
    date_col = str(choice.get("date_column_used", ""))
    track_col = str(choice.get("track_column_used", ""))
    race_col = str(choice.get("race_no_column_used", ""))
    horse_col = str(choice.get("horse_column_used", ""))

    if not horse_col or horse_col not in card.columns:
        raise SystemExit(f"Selected source missing horse column: {source_path}")

    if "horse" not in card.columns:
        card["horse"] = card[horse_col]
    else:
        card["horse"] = card["horse"].where(card["horse"].map(clean) != "", card[horse_col])

    for column in [
        "horse_no", "saddlecloth", "is_scratched", "runner_status", "scratch_status", "race_time",
        "distance", "race_class", "track_condition", "rail_position", "barrier", "jockey", "trainer",
        "market_price", "fixed_odds", "rated_price", "execution_action", "signal", "market_status",
        "market_mover", "movement_velocity", "flucs", "truth_grade", "market_confidence", "liquidity_grade",
        "fake_overlay_flag", "late_drift_risk", "execution_trust_score", "suppression_action",
        "suppression_reason", "clv_expectation", "open_price", "mid_price", "close_price", "last10", "last_10",
        "speed_map_bucket", "map_position", "run_style", "pace_profile", "settling_band", "map_x_pct", "map_y_px",
        "local_silk_path", "mobile_silk_image", "silkUrl", "silk_url", "market_note",
    ]:
        if column not in card.columns:
            card[column] = ""

    card["race_date_key"] = card[date_col].map(clean).str[:10]
    card["track_key"] = card[track_col].map(canonical_track)
    card["race_no_key"] = card[race_col].map(race_no_int)
    card["horse_key_norm"] = card[horse_col].map(horse_key)

    card = card[
        (card["race_date_key"] == TODAY)
        & (card["track_key"] == selected_track)
        & card["race_no_key"].gt(0)
        & card["horse"].map(clean).ne("")
    ].copy()

    if card.empty:
        raise SystemExit(f"No rows found in selected current-day source for {TODAY} {selected_track}: {source_path}")

    card.sort_values(["race_no_key", "horse_no", "saddlecloth", "horse"], inplace=True)
    tab_lookup, tab_rows = build_tab_lookup()
    fields = output_fields()
    built_at = datetime.now(LOCAL_TZ).isoformat(timespec="seconds")
    terminal_scope = "TODAY_ONLY_" + re.sub(r"[^A-Z0-9]+", "_", selected_track).strip("_")
    rows: list[dict[str, object]] = []

    for row in card.to_dict("records"):
        race_date = row["race_date_key"]
        track = canonical_track(row.get(track_col))
        rn = row["race_no_key"]
        hk = row["horse_key_norm"]
        horse = clean(row.get("horse"))
        meeting_key = f"{race_date}_{track}"
        race_key = f"{meeting_key}_R{rn}"
        runner_key = f"{race_key}_{hk}"

        tab_row = tab_lookup.get((race_date, rn, hk), {})
        tab_status = clean(tab_row.get("tab_fixed_betting_status"))
        scratch_flag = clean(row.get("is_scratched")).upper() in {"1", "TRUE", "YES"} or tab_status.upper() == "LATESCRATCHED"
        live_price_num = num(tab_row.get("tab_fixed_win")) or num(row.get("market_price")) or num(row.get("fixed_odds"))
        fair_price_num = num(row.get("rated_price"))
        edge_pct_num = live_edge_pct(live_price_num, fair_price_num)

        race_dt = parse_race_datetime(race_date, clean(row.get("race_time")))
        race_time_out = race_dt.isoformat() if race_dt else clean(row.get("race_time"))
        minutes_to_jump = None
        if race_dt is not None:
            minutes_to_jump = round((race_dt - datetime.now(LOCAL_TZ)).total_seconds() / 60.0, 1)
        race_state = state_from_minutes(minutes_to_jump, tab_status)

        out_row = {field: "" for field in fields}
        out_row.update(
            {
                "built_at": built_at,
                "meeting_key": meeting_key,
                "race_key": race_key,
                "runner_key": runner_key,
                "source": f"{source_path.name}+TAB_DIRECT_API",
                "race_date": race_date,
                "day_bucket": "TODAY",
                "track": track,
                "race_no": str(rn),
                "race_time": race_time_out,
                "minutes_to_jump": "" if minutes_to_jump is None else f"{minutes_to_jump:.1f}",
                "race_state": race_state,
                "distance": clean(row.get("distance")),
                "race_class": clean(row.get("race_class")),
                "track_condition": clean(row.get("track_condition")),
                "rail_position": clean(row.get("rail_position")),
                "horse_no": clean(row.get("horse_no")) or clean(row.get("saddlecloth")),
                "saddlecloth": clean(row.get("saddlecloth")) or clean(row.get("horse_no")),
                "horse": horse,
                "horse_key": hk,
                "barrier": clean(row.get("barrier")),
                "jockey": clean(row.get("jockey")),
                "trainer": clean(row.get("trainer")),
                "silkUrl": clean(row.get("silkUrl")) or clean(row.get("silk_url")),
                "silk_url": clean(row.get("silk_url")) or clean(row.get("silkUrl")),
                "local_silk_path": clean(row.get("local_silk_path")),
                "mobile_silk_image": clean(row.get("mobile_silk_image")),
                "is_scratched": "YES" if scratch_flag else "",
                "scratch_status": "LATE SCRATCHED" if scratch_flag else clean(row.get("scratch_status")),
                "runner_status": "SCRATCHED" if scratch_flag else clean(row.get("runner_status")) or clean(row.get("tab_fixed_betting_status")),
                "ui_price": fmt_price(live_price_num),
                "sportsbet_price": "",
                "market_price": fmt_price(live_price_num),
                "fixed_win": fmt_price(live_price_num),
                "rated_price": fmt_price(fair_price_num),
                "ui_fair_price": fmt_price(fair_price_num),
                "edge_pct": fmt_pct(edge_pct_num),
                "ui_edge_pct": fmt_pct(edge_pct_num),
                "execution_action": "SCRATCHED" if scratch_flag else clean(row.get("execution_action")) or clean(row.get("signal")),
                "market_state": "SCRATCHED" if scratch_flag else clean(tab_status) or clean(row.get("market_status")) or race_state,
                "market_mover": clean(row.get("market_mover")),
                "movement_velocity": clean(row.get("movement_velocity")) or clean(row.get("flucs")),
                "bookmaker": "TAB",
                "sportsbet_event_id": "",
                "sportsbet_market_id": "",
                "sportsbet_timestamp": "",
                "truth_grade": clean(row.get("truth_grade")),
                "market_confidence": clean(row.get("market_confidence")),
                "liquidity_grade": clean(row.get("liquidity_grade")),
                "fake_overlay_flag": clean(row.get("fake_overlay_flag")),
                "late_drift_risk": clean(row.get("late_drift_risk")),
                "execution_trust_score": clean(row.get("execution_trust_score")),
                "suppression_action": clean(row.get("suppression_action")),
                "suppression_reason": clean(row.get("suppression_reason")),
                "clv_expectation": clean(row.get("clv_expectation")),
                "open_price": clean(row.get("open_price")),
                "mid_price": clean(row.get("mid_price")),
                "close_price": clean(row.get("close_price")),
                "flucs": clean(row.get("flucs")),
                "last10": clean(row.get("last10")),
                "last_10": clean(row.get("last_10")),
                "speed_map_bucket": clean(row.get("speed_map_bucket")),
                "map_position": clean(row.get("map_position")),
                "run_style": clean(row.get("run_style")),
                "pace_profile": clean(row.get("pace_profile")),
                "settling_band": clean(row.get("settling_band")),
                "map_x_pct": clean(row.get("map_x_pct")),
                "map_y_px": clean(row.get("map_y_px")),
                "ui_status": "SCRATCHED" if scratch_flag else race_state,
                "market_source_status": "TAB_DIRECT_API_READY" if tab_row else "TAB_DIRECT_API_MISSING",
                "market_source_ready": "YES" if tab_row else "NO",
                "market_source_rows": str(tab_rows),
                "market_source_age_seconds": "",
                "market_source_file": TAB.name,
                "market_capture_timestamp": clean(tab_row.get("scraped_at")),
                "terminal_scope": terminal_scope,
                "intelligence_note": clean(row.get("market_note")) or f"source_inventory={source_path.name}",
                "live_rank": "",
                "fair_rank": "",
                "edge_rank": "",
                "tab_fixed_win": clean(tab_row.get("tab_fixed_win")),
                "tab_fixed_place": clean(tab_row.get("tab_fixed_place")),
                "tab_fixed_betting_status": tab_status,
                "tab_live_price_source": "TAB_SINGLE_RACE_API" if tab_row else "",
                "live_price": fmt_price(live_price_num),
                "live_price_source": "TAB_FIXED_WIN" if tab_row.get("tab_fixed_win") else ("SOURCE_MARKET_PRICE" if live_price_num else ""),
            }
        )
        rows.append(out_row)

    out = pd.DataFrame(rows)
    out["race_no_sort"] = out["race_no"].map(race_no_int)
    out["horse_no_sort"] = pd.to_numeric(out["horse_no"], errors="coerce").fillna(9999)
    out = out.sort_values(["race_no_sort", "horse_no_sort", "horse"]).drop(columns=["race_no_sort", "horse_no_sort"])

    out = apply_scratch_normalisation(out)
    out = out.drop(columns=["scratch_flag_bool", "fair_price_num", "live_price_num", "edge_pct_num"], errors="ignore")

    out.to_csv(OUT, index=False)

    print("[LIVE_TERMINAL_FEED_TAB_ONLY_TODAY] COMPLETE")
    print(f"today={TODAY}")
    print(f"selected_meeting={selected_track}")
    print(f"source_inventory={source_path.name}")
    print(f"rows={len(out)}")
    print("tracks=" + ", ".join(sorted(out["track"].dropna().astype(str).unique())))
    print(f"out={OUT}")


if __name__ == "__main__":
    main()
