from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import math
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
V61 = DATA / "edgeiq_current_fair_prices_V6_1_RESEARCH_replay.csv"

OUT = DATA / "edgeiq_live_runner_board_v1.csv"
MISS = DATA / "edgeiq_live_runner_board_v1_unmatched.csv"
DIAG = DATA / "edgeiq_live_runner_board_v1_diagnostics.csv"

LOCAL_TZ = ZoneInfo("Australia/Sydney")
TODAY = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")


def clean(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null", "undefined"} else text


def num(value: object) -> float | None:
    text = clean(value).replace("$", "").replace(",", "")
    if text in {"", "-"}:
        return None
    try:
        parsed = float(text)
        if not math.isfinite(parsed):
            return None
        return parsed
    except ValueError:
        return None


def fmt(value: float | None, places: int = 2) -> str:
    if value is None:
        return ""
    if not math.isfinite(float(value)):
        return ""
    return f"{float(value):.{places}f}".rstrip("0").rstrip(".")


def norm_track(value: object) -> str:
    return re.sub(r"\s+", " ", clean(value).upper()).strip()


def horse_key(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def race_no_key(value: object) -> str:
    digits = re.sub(r"[^0-9]", "", clean(value))
    return str(int(digits)) if digits else ""


def ensure(frame: pd.DataFrame, column: str) -> None:
    if column not in frame.columns:
        frame[column] = ""


def is_scratched(row: pd.Series) -> bool:
    values = [
        row.get("is_scratched", ""),
        row.get("scratch_status", ""),
        row.get("runner_status", ""),
        row.get("tab_fixed_betting_status", ""),
        row.get("tab_tote_betting_status", ""),
        row.get("ui_status", ""),
    ]
    text = " ".join(clean(value).upper() for value in values)
    return "SCRATCH" in text or text in {"TRUE", "1", "YES"}


def is_future_row(race_date: object) -> bool:
    value = clean(race_date)[:10]
    return value > TODAY


def source_from(row: pd.Series) -> str:
    if is_scratched(row):
        return "SCRATCHED"
    if clean(row.get("live_price_source")):
        return clean(row.get("live_price_source"))
    if clean(row.get("tab_live_price_source")):
        return clean(row.get("tab_live_price_source"))
    if clean(row.get("display_live_price")):
        return "TAB_FIXED_WIN"
    if is_future_row(row.get("race_date")):
        return "MARKET_PENDING"
    return "MODEL"


def decision_from(row: pd.Series) -> str:
    if is_scratched(row):
        return "SCRATCHED"

    live = num(row.get("display_live_price"))
    fair = num(row.get("display_fair_price"))
    edge = num(row.get("display_edge_pct"))

    if live is None or live <= 0:
        return "NO MARKET"
    if fair is None or fair <= 0:
        return "NO MODEL"
    if edge is None:
        return "NO EDGE"
    if edge >= 18:
        return "WATCH"
    if edge >= 10:
        return "LEAN"
    if edge > 0:
        return "PASS"
    return "UNDERLAY"


def main() -> None:
    if not SRC.exists():
        raise FileNotFoundError(f"Missing terminal feed: {SRC}")
    if not V61.exists():
        raise FileNotFoundError(f"Missing V6.1 replay file: {V61}")

    df = pd.read_csv(SRC, dtype=str, keep_default_na=False, low_memory=False).fillna("")
    v6 = pd.read_csv(V61, dtype=str, keep_default_na=False, low_memory=False).fillna("")

    if df.empty:
        raise SystemExit(f"Terminal feed empty: {SRC}")
    if v6.empty:
        raise SystemExit(f"V6.1 replay empty: {V61}")

    base_cols = [
        "race_date",
        "day_bucket",
        "meeting_type",
        "meeting_status",
        "dashboard_ready",
        "track",
        "race_no",
        "race_key",
        "meeting_key",
        "runner_key",
        "horse",
        "horse_key",
        "horse_no",
        "saddlecloth",
        "barrier",
        "jockey",
        "trainer",
        "race_time",
        "distance",
        "race_class",
        "track_condition",
        "rail_position",
        "live_price",
        "tab_fixed_win",
        "tab_fixed_place",
        "tab_fixed_betting_status",
        "tab_tote_win",
        "tab_tote_place",
        "tab_tote_betting_status",
        "tab_live_price_source",
        "live_price_source",
        "is_scratched",
        "scratch_status",
        "runner_status",
        "run_style",
        "speed_map_bucket",
        "settling_band",
        "map_x_pct",
        "map_y_px",
        "ui_status",
        "market_state",
        "source",
        "terminal_scope",
        "intelligence_note",
        "market_source_status",
        "market_source_ready",
        "market_source_rows",
        "market_source_age_seconds",
        "market_source_file",
        "market_capture_timestamp",
        "execution_action",
        "rated_price",
        "fair_price",
        "ui_fair_price",
        "edge_pct",
        "ui_edge_pct",
    ]

    for column in base_cols:
        ensure(df, column)

    df["race_date_key"] = df["race_date"].map(clean).str[:10]
    df["track_key"] = df["track"].map(norm_track)
    df["race_no_key"] = df["race_no"].map(race_no_key)
    df["horse_key_join"] = df["horse_key"].map(clean)
    missing_horse_keys = df["horse_key_join"].eq("")
    df.loc[missing_horse_keys, "horse_key_join"] = df.loc[missing_horse_keys, "horse"].map(horse_key)

    df = df[
        df["race_date_key"].ne("")
        & df["track_key"].ne("")
        & df["race_no_key"].ne("")
        & df["horse"].map(clean).ne("")
    ].copy()

    if df.empty:
        raise SystemExit("No valid terminal rows found after multi-day filtering.")

    for column in ["race_date", "track", "race_no", "horse", "horse_key"]:
        ensure(v6, column)

    v6["race_date_key"] = v6["race_date"].map(clean).str[:10]
    v6["track_key"] = v6["track"].map(norm_track)
    v6["race_no_key"] = v6["race_no"].map(race_no_key)
    v6["horse_key_join"] = v6["horse_key"].map(clean)
    missing_v6_horse_keys = v6["horse_key_join"].eq("")
    v6.loc[missing_v6_horse_keys, "horse_key_join"] = v6.loc[missing_v6_horse_keys, "horse"].map(horse_key)

    v6_keep_cols = [
        "race_date_key",
        "track_key",
        "race_no_key",
        "horse_key_join",
        "projected_rating_v5_2",
        "projection_gap_v5_2",
        "projection_band_v5_2",
        "projection_confidence_v5_2",
        "projected_rating_V6_1_RESEARCH",
        "projection_gap_V6_1_RESEARCH",
        "projection_band_V6_1_RESEARCH",
        "V6_1_RESEARCH_probability",
        "V6_1_RESEARCH_fair_price",
        "V6_1_RESEARCH_price_status",
        "V6_1_RESEARCH_price_bucket",
        "V6_1_RESEARCH_price_rank",
    ]

    for column in v6_keep_cols:
        ensure(v6, column)

    v6s = v6[v6_keep_cols].drop_duplicates(
        ["race_date_key", "track_key", "race_no_key", "horse_key_join"],
        keep="first",
    )

    merged = df.merge(
        v6s,
        on=["race_date_key", "track_key", "race_no_key", "horse_key_join"],
        how="left",
        indicator=True,
    )

    merged["scratch_bool"] = merged.apply(is_scratched, axis=1)
    merged["v61_status_clean"] = merged["V6_1_RESEARCH_price_status"].map(clean)
    merged["is_v61_rated"] = merged["v61_status_clean"].eq("RESEARCH_RATED")

    merged["display_live_price"] = merged.apply(
        lambda row: "" if row["scratch_bool"] else (
            clean(row.get("live_price"))
            or clean(row.get("tab_fixed_win"))
            or clean(row.get("ui_price"))
            or clean(row.get("market_price"))
            or clean(row.get("fixed_win"))
        ),
        axis=1,
    )

    merged["display_fair_price"] = ""
    rated_mask = merged["is_v61_rated"] & ~merged["scratch_bool"]
    merged.loc[rated_mask, "display_fair_price"] = merged.loc[rated_mask, "V6_1_RESEARCH_fair_price"]

    merged["fair_price"] = merged["display_fair_price"]
    merged["rated_price"] = merged["display_fair_price"]
    merged["ui_fair_price"] = merged["display_fair_price"]

    probability_numeric = pd.to_numeric(merged["V6_1_RESEARCH_probability"], errors="coerce")
    merged["win_pct"] = ""
    merged.loc[rated_mask, "win_pct"] = (probability_numeric[rated_mask] * 100.0).round(2).map(
        lambda value: f"{value:.2f}".rstrip("0").rstrip(".")
    )

    def edge_calc(row: pd.Series) -> str:
        live = num(row.get("display_live_price"))
        fair = num(row.get("display_fair_price"))
        if live is None or fair is None or live <= 0 or fair <= 0:
            return ""
        return fmt(((live / fair) - 1.0) * 100.0, 1)

    merged["display_edge_pct"] = merged.apply(edge_calc, axis=1)
    merged["edge_pct"] = merged["display_edge_pct"]
    merged["ui_edge_pct"] = merged["display_edge_pct"]
    merged["display_source"] = merged.apply(source_from, axis=1)
    merged["display_decision"] = merged.apply(decision_from, axis=1)

    merged["execution_action_final"] = merged["execution_action"].map(clean)
    blank_execution = merged["execution_action_final"].eq("")
    merged.loc[blank_execution, "execution_action_final"] = merged.loc[blank_execution, "display_decision"]

    merged["horse_no_final"] = merged["horse_no"].where(merged["horse_no"].map(clean).ne(""), merged["saddlecloth"])
    merged["runner_key_final"] = merged["runner_key"]
    missing_runner_keys = merged["runner_key_final"].map(clean).eq("")
    merged.loc[missing_runner_keys, "runner_key_final"] = (
        merged["race_date_key"] + "_" + merged["track_key"] + "_R" + merged["race_no_key"] + "_" + merged["horse_key_join"]
    )

    future_mask = merged["race_date_key"].gt(TODAY) & ~merged["scratch_bool"] & merged["display_live_price"].map(clean).eq("")
    merged.loc[future_mask, "market_state"] = "MARKET_PENDING"
    merged.loc[future_mask, "ui_status"] = "MARKET_PENDING"

    keep = pd.DataFrame(
        {
            "race_date": merged["race_date_key"],
            "day_bucket": merged["day_bucket"],
            "meeting_type": merged["meeting_type"],
            "meeting_status": merged["meeting_status"],
            "dashboard_ready": merged["dashboard_ready"],
            "track": merged["track_key"],
            "race_no": merged["race_no_key"],
            "race_key": merged["race_key"],
            "meeting_key": merged["meeting_key"],
            "runner_key": merged["runner_key_final"],
            "source": merged["source"],
            "terminal_scope": merged["terminal_scope"],
            "horse": merged["horse"],
            "horse_key": merged["horse_key_join"],
            "horse_no": merged["horse_no_final"],
            "saddlecloth": merged["saddlecloth"],
            "barrier": merged["barrier"],
            "jockey": merged["jockey"],
            "trainer": merged["trainer"],
            "race_time": merged["race_time"],
            "distance": merged["distance"],
            "race_class": merged["race_class"],
            "track_condition": merged["track_condition"],
            "rail_position": merged["rail_position"],
            "live_price": merged["display_live_price"],
            "tab_fixed_win": merged["tab_fixed_win"],
            "tab_fixed_place": merged["tab_fixed_place"],
            "tab_fixed_betting_status": merged["tab_fixed_betting_status"],
            "tab_tote_win": merged["tab_tote_win"],
            "tab_tote_place": merged["tab_tote_place"],
            "tab_tote_betting_status": merged["tab_tote_betting_status"],
            "tab_live_price_source": merged["tab_live_price_source"],
            "live_price_source": merged["live_price_source"],
            "projected_rating_v5_2": merged["projected_rating_v5_2"],
            "projection_gap_v5_2": merged["projection_gap_v5_2"],
            "projection_band_v5_2": merged["projection_band_v5_2"],
            "projection_confidence_v5_2": merged["projection_confidence_v5_2"],
            "projected_rating_V6_1_RESEARCH": merged["projected_rating_V6_1_RESEARCH"],
            "projection_gap_V6_1_RESEARCH": merged["projection_gap_V6_1_RESEARCH"],
            "projection_band_V6_1_RESEARCH": merged["projection_band_V6_1_RESEARCH"],
            "V6_1_RESEARCH_probability": merged["V6_1_RESEARCH_probability"],
            "V6_1_RESEARCH_fair_price": merged["V6_1_RESEARCH_fair_price"],
            "V6_1_RESEARCH_price_status": merged["V6_1_RESEARCH_price_status"],
            "V6_1_RESEARCH_price_bucket": merged["V6_1_RESEARCH_price_bucket"],
            "V6_1_RESEARCH_price_rank": merged["V6_1_RESEARCH_price_rank"],
            "win_pct": merged["win_pct"],
            "fair_price": merged["fair_price"],
            "rated_price": merged["rated_price"],
            "ui_fair_price": merged["ui_fair_price"],
            "edge_pct": merged["edge_pct"],
            "ui_edge_pct": merged["ui_edge_pct"],
            "execution_action": merged["execution_action_final"],
            "display_source": merged["display_source"],
            "display_decision": merged["display_decision"],
            "display_edge_pct": merged["display_edge_pct"],
            "display_live_price": merged["display_live_price"],
            "display_fair_price": merged["display_fair_price"],
            "is_scratched": merged["is_scratched"],
            "scratch_status": merged["scratch_status"],
            "runner_status": merged["runner_status"],
            "run_style": merged["run_style"],
            "speed_map_bucket": merged["speed_map_bucket"],
            "settling_band": merged["settling_band"],
            "map_x_pct": merged["map_x_pct"],
            "map_y_px": merged["map_y_px"],
            "ui_status": merged["ui_status"],
            "market_state": merged["market_state"],
            "market_source_status": merged["market_source_status"],
            "market_source_ready": merged["market_source_ready"],
            "market_source_rows": merged["market_source_rows"],
            "market_source_age_seconds": merged["market_source_age_seconds"],
            "market_source_file": merged["market_source_file"],
            "market_capture_timestamp": merged["market_capture_timestamp"],
            "intelligence_note": merged["intelligence_note"],
        }
    )

    scratched_mask = keep["display_decision"].eq("SCRATCHED")
    keep.loc[
        scratched_mask,
        [
            "win_pct",
            "fair_price",
            "rated_price",
            "ui_fair_price",
            "edge_pct",
            "ui_edge_pct",
            "display_edge_pct",
            "display_fair_price",
        ],
    ] = ""

    keep["race_no_sort"] = pd.to_numeric(keep["race_no"], errors="coerce").fillna(9999)
    keep["horse_no_sort"] = pd.to_numeric(keep["horse_no"], errors="coerce").fillna(9999)
    keep = keep.sort_values(
        ["race_date", "track", "race_no_sort", "horse_no_sort", "horse"],
        ascending=[True, True, True, True, True],
    ).drop(columns=["race_no_sort", "horse_no_sort"])

    unmatched = keep[keep["V6_1_RESEARCH_price_status"].map(clean).eq("")]
    keep.to_csv(OUT, index=False, encoding="utf-8")
    unmatched.to_csv(MISS, index=False, encoding="utf-8")

    diag = pd.DataFrame(
        [
            ["status", "COMPLETE"],
            ["run_timestamp", datetime.now(LOCAL_TZ).isoformat(timespec="seconds")],
            ["source_file", SRC.name],
            ["source_rows", len(df)],
            ["date_range", "|".join(sorted(set(keep["race_date"].astype(str).tolist())))],
            ["track_count", int(keep["track"].nunique())],
            ["rows", len(keep)],
            ["future_rows", int((keep["race_date"].astype(str) > TODAY).sum())],
            ["v61_join_matched_rows", int((merged["_merge"] == "both").sum())],
            ["v61_research_rated_rows", int(keep["V6_1_RESEARCH_price_status"].eq("RESEARCH_RATED").sum())],
            ["with_win_pct", int(keep["win_pct"].map(clean).ne("").sum())],
            ["with_fair_price", int(keep["fair_price"].map(clean).ne("").sum())],
            ["with_live_price", int(keep["live_price"].map(clean).ne("").sum())],
            ["unmatched_rows", int(len(unmatched))],
        ],
        columns=["metric", "value"],
    )
    diag.to_csv(DIAG, index=False, encoding="utf-8")

    print("[LIVE_RUNNER_BOARD_FROM_TERMINAL_V1] COMPLETE")
    print(f"source_rows={len(df)}")
    print(f"rows={len(keep)}")
    print(f"future_rows={int((keep['race_date'].astype(str) > TODAY).sum())}")
    print(f"v61_join_matched_rows={int((merged['_merge'] == 'both').sum())}")
    print(f"v61_research_rated_rows={int(keep['V6_1_RESEARCH_price_status'].eq('RESEARCH_RATED').sum())}")
    print(f"wrote={OUT}")
    print(f"unmatched={MISS}")
    print(f"diag={DIAG}")


if __name__ == "__main__":
    main()
