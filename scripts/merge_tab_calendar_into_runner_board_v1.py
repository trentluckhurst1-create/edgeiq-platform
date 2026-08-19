from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import math
import pandas as pd
import re


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
TAB = DATA / "edgeiq_tab_calendar_racecards_vic_v1.csv"
OUT = DATA / "edgeiq_live_runner_board_v1.csv"
AUDIT = DATA / "edgeiq_runner_board_tab_calendar_merge_audit_v1.csv"

LOCAL_TZ = ZoneInfo("Australia/Sydney")
TODAY = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")


def clean(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null", "undefined"} else text


def num(value: object) -> float | None:
    text = clean(value)
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
    return f"{float(value):.{places}f}".rstrip("0").rstrip(".")


def norm_track(value: object) -> str:
    return re.sub(r"\s+", " ", clean(value).upper()).strip()


def horse_key(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"\([^)]*\)", " ", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def race_no(value: object) -> str:
    digits = re.sub(r"[^0-9]", "", clean(value))
    return str(int(digits)) if digits else ""


def first_nonblank(row: pd.Series, names: list[str]) -> str:
    for name in names:
        value = clean(row.get(name, ""))
        if value:
            return value
    return ""


def is_scratched(row: pd.Series) -> bool:
    values = [
        clean(row.get("tab_fixed_betting_status", "")),
        clean(row.get("tab_tote_betting_status", "")),
        clean(row.get("scratched_time", "")),
        clean(row.get("scratch_status", "")),
        clean(row.get("runner_status", "")),
        clean(row.get("is_scratched", "")),
    ]
    text = " ".join(values).upper()
    return any(flag in text for flag in ["SCRATCH", "LATESCRATCH", "LATE SCRATCH", "SCR"])


def display_source(row: pd.Series) -> str:
    if row.get("is_scratched") == "True":
        return "SCRATCHED"
    if clean(row.get("display_live_price")):
        return clean(row.get("live_price_source")) or clean(row.get("tab_live_price_source")) or "TAB_FIXED_WIN"
    if clean(row.get("display_fair_price")):
        return "MODEL"
    return "MARKET_PENDING" if clean(row.get("race_date")) > TODAY else "MODEL"


def edge_calc(row: pd.Series) -> str:
    live = num(row.get("display_live_price"))
    fair = num(row.get("display_fair_price"))
    if live is None or fair is None or live <= 0 or fair <= 0:
        return ""
    return fmt(((live / fair) - 1.0) * 100.0, 1)


def decision_from(row: pd.Series) -> str:
    if row.get("is_scratched") == "True":
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


def should_replace_execution_action(current_action: object) -> bool:
    return clean(current_action).upper() in {"", "NO MARKET", "NO_MODEL", "NO MODEL", "NO EDGE"}


def main() -> None:
    board = pd.read_csv(BOARD, dtype=str, keep_default_na=False, low_memory=False).fillna("")
    tab = pd.read_csv(TAB, dtype=str, keep_default_na=False, low_memory=False).fillna("")

    for frame in [board, tab]:
        frame["_date"] = frame.get("race_date", frame.get("meeting_date", "")).astype(str).str[:10]
        frame["_track"] = frame.get("track", frame.get("meeting_name", "")).astype(str).map(norm_track)
        frame["_race"] = frame["race_no"].map(race_no)
        if "horse_key" not in frame.columns:
            frame["horse_key"] = ""
        frame["_horse"] = frame["horse_key"].map(clean)
        missing = frame["_horse"].eq("")
        frame.loc[missing, "_horse"] = frame.loc[missing, "horse"].map(horse_key)

    tab_keep = [
        "_date",
        "_track",
        "_race",
        "_horse",
        "tab_fixed_win",
        "tab_fixed_place",
        "tab_fixed_open_win",
        "tab_fixed_betting_status",
        "tab_tote_win",
        "tab_tote_place",
        "tab_tote_betting_status",
        "scratched_time",
        "early_speed_rating",
        "early_speed_band",
        "dfs_form_rating",
        "tech_form_rating",
        "total_rating_points",
        "silk_url",
    ]
    tab_keep = [column for column in tab_keep if column in tab.columns]

    rename_map = {}
    for column in [
        "tab_fixed_win",
        "tab_fixed_place",
        "tab_fixed_open_win",
        "tab_fixed_betting_status",
        "tab_tote_win",
        "tab_tote_place",
        "tab_tote_betting_status",
        "scratched_time",
    ]:
        if column in tab.columns:
            rename_map[column] = f"{column}_from_tab"

    tab_join = tab[tab_keep].rename(columns=rename_map).drop_duplicates(["_date", "_track", "_race", "_horse"])
    merged = board.merge(tab_join, on=["_date", "_track", "_race", "_horse"], how="left", suffixes=("", "_tab"))

    price_columns = [
        "tab_fixed_win",
        "tab_fixed_place",
        "tab_fixed_open_win",
        "tab_tote_win",
        "tab_tote_place",
    ]
    meta_columns = [
        "tab_fixed_betting_status",
        "tab_tote_betting_status",
        "scratched_time",
    ]

    today_mask = merged["_date"].eq(TODAY)

    for column in meta_columns:
        source_column = f"{column}_from_tab"
        if column not in merged.columns:
            merged[column] = ""
        if source_column in merged.columns:
            merged[column] = merged[source_column].where(
                merged[source_column].astype(str).str.strip().ne(""),
                merged[column],
            )

    for column in price_columns:
        source_column = f"{column}_from_tab"
        if column not in merged.columns:
            merged[column] = ""
        if source_column in merged.columns:
            merge_values = merged[source_column].where(
                merged[source_column].astype(str).str.strip().ne(""),
                merged[column],
            )
            merged.loc[today_mask, column] = merge_values.loc[today_mask]

    merged["tab_live_price_source"] = merged.apply(
        lambda row: "TAB_FIXED_WIN" if clean(row.get("tab_fixed_win")) and row.get("_date") == TODAY else clean(row.get("tab_live_price_source")),
        axis=1,
    )

    merged["is_scratched"] = merged.apply(lambda row: "True" if is_scratched(row) else "False", axis=1)
    merged["scratch_status"] = merged.apply(
        lambda row: "SCRATCHED" if row["is_scratched"] == "True" else clean(row.get("scratch_status", "")),
        axis=1,
    )
    merged["runner_status"] = merged.apply(
        lambda row: "SCRATCHED" if row["is_scratched"] == "True" else (clean(row.get("runner_status")) or "ACTIVE"),
        axis=1,
    )

    def live_price_value(row: pd.Series) -> str:
        if row["is_scratched"] == "True":
            return ""
        if row.get("_date") != TODAY:
            return clean(row.get("live_price")) or clean(row.get("display_live_price"))
        return first_nonblank(row, ["tab_fixed_win", "live_price", "display_live_price"])

    merged["live_price"] = merged.apply(live_price_value, axis=1)
    merged["display_live_price"] = merged["live_price"]
    merged["live_price_source"] = merged.apply(
        lambda row: (
            "TAB_FIXED_WIN"
            if clean(row.get("tab_fixed_win")) and row["is_scratched"] != "True" and row.get("_date") == TODAY
            else clean(row.get("live_price_source", ""))
        ),
        axis=1,
    )
    merged["ui_status"] = merged.apply(
        lambda row: "SCRATCHED"
        if row["is_scratched"] == "True"
        else (
            "LIVE"
            if clean(row.get("live_price", ""))
            else ("MARKET_PENDING" if clean(row.get("race_date")) > TODAY else clean(row.get("ui_status", "")) or "NO_LIVE_PRICE")
        ),
        axis=1,
    )
    merged["market_state"] = merged.apply(
        lambda row: "SCRATCHED"
        if row["is_scratched"] == "True"
        else (
            clean(row.get("market_state"))
            or ("MARKET_PENDING" if clean(row.get("race_date")) > TODAY and clean(row.get("live_price")) == "" else "")
        ),
        axis=1,
    )

    def fair_display_value(row: pd.Series) -> str:
        if row["is_scratched"] == "True":
            return ""
        return first_nonblank(
            row,
            [
                "display_fair_price",
                "fair_price",
                "ui_fair_price",
                "rated_price",
                "V6_1_RESEARCH_fair_price",
            ],
        )

    merged["display_fair_price"] = merged.apply(fair_display_value, axis=1)
    merged["fair_price"] = merged["display_fair_price"]
    merged["rated_price"] = merged["display_fair_price"]
    merged["ui_fair_price"] = merged["display_fair_price"]

    merged["win_pct"] = merged.apply(
        lambda row: "" if row["is_scratched"] == "True" else clean(row.get("win_pct", "")),
        axis=1,
    )

    merged["display_edge_pct"] = merged.apply(edge_calc, axis=1)
    merged["edge_pct"] = merged["display_edge_pct"]
    merged["ui_edge_pct"] = merged["display_edge_pct"]
    merged["display_source"] = merged.apply(display_source, axis=1)
    merged["display_decision"] = merged.apply(decision_from, axis=1)

    current_actions = merged.get("execution_action", pd.Series([""] * len(merged), index=merged.index)).map(clean)
    replace_mask = current_actions.map(should_replace_execution_action)
    merged.loc[replace_mask, "execution_action"] = merged.loc[replace_mask, "display_decision"]

    current_display = merged.get("execution_action_final", pd.Series([""] * len(merged), index=merged.index)).map(clean)
    display_replace_mask = current_display.eq("")
    merged.loc[display_replace_mask, "execution_action_final"] = merged.loc[display_replace_mask, "display_decision"]

    merged = merged.sort_values(
        ["_date", "_track", "_race", "horse_no", "saddlecloth", "horse"],
        ascending=[True, True, True, True, True, True],
    )

    merged.drop(columns=[column for column in merged.columns if column.endswith("_from_tab")], inplace=True, errors="ignore")
    merged.to_csv(OUT, index=False, encoding="utf-8")

    audit_rows = [
        ["status", "COMPLETE"],
        ["run_timestamp", datetime.now(LOCAL_TZ).isoformat(timespec="seconds")],
        ["board_rows", len(board)],
        ["tab_rows", len(tab)],
        ["merged_rows", len(merged)],
        ["today_live_price_rows", int(((merged["_date"] == TODAY) & merged["live_price"].map(clean).ne("")).sum())],
        ["future_market_pending_rows", int(((merged["_date"] > TODAY) & merged["live_price"].map(clean).eq("")).sum())],
        ["scratched_rows", int(merged["is_scratched"].eq("True").sum())],
    ]
    pd.DataFrame(audit_rows, columns=["metric", "value"]).to_csv(AUDIT, index=False, encoding="utf-8")

    print("[MERGE_TAB_CALENDAR_INTO_RUNNER_BOARD_V1] COMPLETE")
    print(f"board_rows={len(board)}")
    print(f"tab_rows={len(tab)}")
    print(f"merged_rows={len(merged)}")
    print(f"future_market_pending_rows={int(((merged['_date'] > TODAY) & merged['live_price'].map(clean).eq('')).sum())}")
    print(f"wrote={OUT}")
    print(f"audit={AUDIT}")


if __name__ == "__main__":
    main()
