from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import math
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

UNIVERSE = DATA / "edgeiq_vic_three_day_meeting_universe.csv"
TODAY_TERMINAL = DATA / "edgeiq_live_terminal_feed_v1_TAB_ONLY_TODAY.csv"
OUT_VIC = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
OUT_GENERIC = DATA / "edgeiq_live_terminal_feed_v1.csv"
SUMMARY = DATA / "edgeiq_vic_live_terminal_feed_v1_summary.csv"

LOCAL_TZ = ZoneInfo("Australia/Sydney")
TODAY = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
MAX_DATE = (datetime.now(LOCAL_TZ) + timedelta(days=2)).strftime("%Y-%m-%d")

PRICE_COLUMNS = [
    "ui_price",
    "sportsbet_price",
    "live_price",
    "market_price",
    "fixed_win",
    "tab_fixed_win",
    "tab_fixed_place",
    "tab_fixed_open_win",
    "tab_tote_win",
    "tab_tote_place",
]

MARKET_META_COLUMNS = [
    "tab_fixed_betting_status",
    "tab_tote_betting_status",
    "tab_live_price_source",
    "live_price_source",
    "market_capture_timestamp",
    "market_source_age_seconds",
]


def clean(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null", "undefined"} else text


def norm_track(value: object) -> str:
    return re.sub(r"\s+", " ", clean(value).upper()).strip()


def race_no_key(value: object) -> str:
    digits = re.sub(r"[^0-9]", "", clean(value))
    return str(int(digits)) if digits else ""


def horse_key(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"\([^)]*\)", " ", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def add_keys(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for column in ["race_date", "track", "race_no", "horse", "horse_key"]:
        if column not in out.columns:
            out[column] = ""
    out["_date"] = out["race_date"].map(clean).str[:10]
    out["_track"] = out["track"].map(norm_track)
    out["_race"] = out["race_no"].map(race_no_key)
    out["_horse"] = out["horse_key"].map(clean)
    missing = out["_horse"].eq("")
    out.loc[missing, "_horse"] = out.loc[missing, "horse"].map(horse_key)
    out["_join"] = out["_date"] + "|" + out["_track"] + "|" + out["_race"] + "|" + out["_horse"]
    return out


def nonblank(value: object) -> bool:
    return clean(value) != ""


def safe_read(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def order_columns(frame: pd.DataFrame) -> list[str]:
    preferred = [
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
        "mobile_silk_image",
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
        "execution_action",
        "market_state",
        "market_mover",
        "movement_velocity",
        "bookmaker",
        "sportsbet_event_id",
        "sportsbet_market_id",
        "sportsbet_timestamp",
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
        "ui_status",
        "market_source_status",
        "market_source_ready",
        "market_source_rows",
        "market_source_age_seconds",
        "market_source_file",
        "market_capture_timestamp",
        "terminal_scope",
        "intelligence_note",
        "live_rank",
        "fair_rank",
        "edge_rank",
        "tab_fixed_win",
        "tab_fixed_place",
        "tab_fixed_open_win",
        "tab_fixed_betting_status",
        "tab_tote_win",
        "tab_tote_place",
        "tab_tote_betting_status",
        "tab_live_price_source",
        "live_price_source",
    ]
    seen: set[str] = set()
    ordered: list[str] = []
    for column in preferred:
        if column in frame.columns and column not in seen:
            ordered.append(column)
            seen.add(column)
    for column in frame.columns:
        if column.startswith("_"):
            continue
        if column not in seen:
            ordered.append(column)
            seen.add(column)
    return ordered


def sort_frame(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["_race_sort"] = pd.to_numeric(out["race_no"], errors="coerce").fillna(9999)
    out["_horse_sort"] = pd.to_numeric(out.get("horse_no", ""), errors="coerce").fillna(
        pd.to_numeric(out.get("saddlecloth", ""), errors="coerce").fillna(9999)
    )
    return out.sort_values(
        ["race_date", "track", "_race_sort", "_horse_sort", "horse"],
        ascending=[True, True, True, True, True],
    ).drop(columns=["_race_sort", "_horse_sort"])


def main() -> None:
    if not UNIVERSE.exists():
        raise FileNotFoundError(f"Missing universe input: {UNIVERSE}")

    built_at = datetime.now(LOCAL_TZ).isoformat(timespec="seconds")

    universe = safe_read(UNIVERSE)
    today_terminal = safe_read(TODAY_TERMINAL)

    if universe.empty:
        raise SystemExit(f"Universe is empty: {UNIVERSE}")

    universe = add_keys(universe)
    universe = universe[
        universe["_date"].ge(TODAY) & universe["_date"].le(MAX_DATE) & universe["_race"].ne("") & universe["horse"].map(clean).ne("")
    ].copy()

    if universe.empty:
        raise SystemExit("No three-day universe rows available for terminal seed.")

    if today_terminal.empty:
        today_terminal = pd.DataFrame(columns=list(universe.columns))
    today_terminal = add_keys(today_terminal)
    today_terminal = today_terminal[
        today_terminal["_date"].eq(TODAY) & today_terminal["_race"].ne("") & today_terminal["horse"].map(clean).ne("")
    ].copy()

    today_lookup = (
        today_terminal.drop_duplicates("_join", keep="first").set_index("_join").to_dict("index")
        if not today_terminal.empty
        else {}
    )

    all_columns = list(universe.columns)
    for column in today_terminal.columns:
        if column not in all_columns:
            all_columns.append(column)

    overlay_matches = 0
    overlay_only_rows = 0
    merged_rows: list[dict[str, object]] = []
    seen_keys: set[str] = set()

    for row in universe.to_dict("records"):
        key = clean(row.get("_join"))
        seen_keys.add(key)
        today_row = today_lookup.get(key)
        merged = {column: clean(row.get(column, "")) for column in all_columns}

        if today_row:
            overlay_matches += 1
            for column in all_columns:
                overlay_value = clean(today_row.get(column, ""))
                if overlay_value != "":
                    merged[column] = overlay_value

        merged["built_at"] = built_at
        merged["source"] = clean(merged.get("source")) or "edgeiq_vic_three_day_meeting_universe.csv"
        merged["track"] = norm_track(merged.get("track"))
        merged["race_no"] = race_no_key(merged.get("race_no"))
        merged["horse_key"] = clean(merged.get("horse_key")) or horse_key(merged.get("horse"))

        is_future = clean(merged.get("race_date")) > TODAY
        if is_future and "SCRATCH" not in " ".join(
            clean(merged.get(column)).upper()
            for column in ["is_scratched", "scratch_status", "runner_status"]
        ):
            for column in PRICE_COLUMNS + MARKET_META_COLUMNS:
                if column in merged:
                    merged[column] = ""
            merged["market_state"] = "MARKET_PENDING"
            merged["ui_status"] = "MARKET_PENDING"
            merged["market_source_status"] = "FUTURE_MEETING_MARKET_PENDING"
            merged["market_source_ready"] = "NO"
            merged["market_source_rows"] = ""
            merged["bookmaker"] = clean(merged.get("bookmaker")) or "TAB"
        else:
            merged["market_source_status"] = clean(merged.get("market_source_status")) or (
                "LIVE_TAB_TERMINAL_OVERLAY" if today_row else "UNIVERSE_ONLY"
            )
            merged["market_source_ready"] = clean(merged.get("market_source_ready")) or (
                "YES" if nonblank(merged.get("live_price")) else "NO"
            )

        merged_rows.append(merged)

    for row in today_terminal.to_dict("records"):
        key = clean(row.get("_join"))
        if key in seen_keys:
            continue
        merged = {column: clean(row.get(column, "")) for column in all_columns}
        merged["built_at"] = built_at
        merged["track"] = norm_track(merged.get("track"))
        merged["race_no"] = race_no_key(merged.get("race_no"))
        merged["horse_key"] = clean(merged.get("horse_key")) or horse_key(merged.get("horse"))
        merged["source"] = clean(merged.get("source")) or "edgeiq_live_terminal_feed_v1_TAB_ONLY_TODAY.csv"
        merged["market_source_status"] = clean(merged.get("market_source_status")) or "LIVE_TAB_TERMINAL_OVERLAY_ONLY"
        merged["market_source_ready"] = clean(merged.get("market_source_ready")) or (
            "YES" if nonblank(merged.get("live_price")) else "NO"
        )
        merged_rows.append(merged)
        overlay_only_rows += 1

    out = pd.DataFrame(merged_rows)
    out = sort_frame(out)
    keep_columns = order_columns(out)
    out = out[keep_columns].copy()

    out.to_csv(OUT_VIC, index=False, encoding="utf-8")
    out.to_csv(OUT_GENERIC, index=False, encoding="utf-8")

    rows_with_live_price = int(out["live_price"].map(clean).ne("").sum()) if "live_price" in out.columns else 0
    future_rows = int((out["race_date"].map(clean) > TODAY).sum())
    future_market_pending = int(
        ((out["race_date"].map(clean) > TODAY) & out.get("market_state", pd.Series("", index=out.index)).map(clean).eq("MARKET_PENDING")).sum()
    )

    summary = pd.DataFrame(
        [
            {"metric": "status", "value": "THREE_DAY_TERMINAL_SEED_BUILT"},
            {"metric": "today", "value": TODAY},
            {"metric": "max_date", "value": MAX_DATE},
            {"metric": "universe_rows", "value": len(universe)},
            {"metric": "today_overlay_rows", "value": len(today_terminal)},
            {"metric": "today_overlay_matches", "value": overlay_matches},
            {"metric": "today_overlay_only_rows", "value": overlay_only_rows},
            {"metric": "output_rows", "value": len(out)},
            {"metric": "rows_with_live_price", "value": rows_with_live_price},
            {"metric": "future_rows", "value": future_rows},
            {"metric": "future_market_pending_rows", "value": future_market_pending},
            {"metric": "output_vic", "value": OUT_VIC.name},
            {"metric": "output_generic", "value": OUT_GENERIC.name},
        ]
    )
    summary.to_csv(SUMMARY, index=False, encoding="utf-8")

    print("[EDGEIQ_VIC_THREE_DAY_TERMINAL_SEED_V1] COMPLETE")
    print(f"today={TODAY}")
    print(f"universe_rows={len(universe)}")
    print(f"today_overlay_rows={len(today_terminal)}")
    print(f"output_rows={len(out)}")
    print(f"future_rows={future_rows}")
    print(f"future_market_pending_rows={future_market_pending}")
    print(f"wrote={OUT_VIC}")
    print(f"wrote={OUT_GENERIC}")
    print(f"summary={SUMMARY}")


if __name__ == "__main__":
    main()
