from __future__ import annotations

import math
import re
import unicodedata
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "public" / "data"

TRACKING_PATH = DATA_DIR / "edgeiq_execution_tracking_v2.csv"
RESULTS_PATH = DATA_DIR / "edgeiq_racingcom_results_warehouse_v1.csv"

OUTPUT_PATH = DATA_DIR / "edgeiq_execution_tracking_v2_settled.csv"
SUMMARY_PATH = DATA_DIR / "edgeiq_execution_tracking_v2_settlement_summary.csv"
BY_ACTION_PATH = DATA_DIR / "edgeiq_execution_tracking_v2_by_action_settlement.csv"

ACTION_ORDER = {
    "ELITE_EXECUTE": 1,
    "EXECUTE": 2,
    "STRONG_WATCH": 3,
    "WATCH": 4,
    "NO_BET": 5,
}

SETTLEMENT_COLUMNS = [
    "result_status",
    "settlement_source",
    "finish_position",
    "won",
    "placed",
    "profit_1u_win",
]


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def fix_mojibake(text: str) -> str:
    if text == "":
        return ""
    if any(ord(ch) > 127 for ch in text):
        try:
            repaired = text.encode("latin1").decode("utf-8")
            return repaired
        except Exception:
            return text
    return text


def normalize_track(value: object) -> str:
    text = fix_mojibake(clean_text(value))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.upper()
    return re.sub(r"[^A-Z0-9]+", "", text)


def canonical_horse(value: object) -> str:
    text = fix_mojibake(clean_text(value))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.upper().strip()
    text = re.sub(r"\([^)]*\)", "", text)
    text = text.replace("&", " AND ")
    return re.sub(r"[^A-Z0-9]+", "", text)


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def parse_finish(value: object) -> float:
    text = clean_text(value).upper()
    if text in {"", "NAN", "NONE", "SCR", "SCRATCHED"}:
        return math.nan
    match = re.search(r"\d+", text)
    if not match:
        return math.nan
    try:
        return float(match.group(0))
    except Exception:
        return math.nan


def build_race_key(df: pd.DataFrame, date_col: str, track_col: str, race_col: str) -> pd.Series:
    race_no = to_num(df[race_col]).fillna(-1).astype(int).astype(str)
    return df[date_col].astype(str).str[:10] + "|" + df[track_col].map(normalize_track) + "|" + race_no


def build_runner_key(df: pd.DataFrame, date_col: str, track_col: str, race_col: str, horse_series: pd.Series) -> pd.Series:
    return build_race_key(df, date_col, track_col, race_col) + "|" + horse_series.map(canonical_horse)


def action_priority(action: str) -> int:
    return ACTION_ORDER.get(clean_text(action).upper(), 99)


def settle_row(row: pd.Series, race_keys: set[str], results_lookup: pd.DataFrame) -> pd.Series:
    race_key = clean_text(row.get("_race_key_v2", ""))
    runner_key = clean_text(row.get("_runner_key_v2", ""))
    market_price = pd.to_numeric(row.get("market_price_v1"), errors="coerce")

    status = "PENDING"
    source = ""
    finish = ""
    won = ""
    placed = ""
    profit = ""

    if runner_key in results_lookup.index:
        result_row = results_lookup.loc[runner_key]
        finish_num = pd.to_numeric(result_row.get("finish_position_result_v2"), errors="coerce")
        if pd.notna(finish_num):
            status = "SETTLED"
            source = "RACING_COM"
            finish_int = int(finish_num)
            finish = str(finish_int)
            won_value = 1 if finish_int == 1 else 0
            placed_value = 1 if finish_int <= 3 else 0
            won = str(won_value)
            placed = str(placed_value)
            if pd.notna(market_price):
                profit = round(float(market_price) - 1.0, 2) if won_value == 1 else -1.0
        else:
            status = "PENDING"
    elif race_key in race_keys:
        status = "RESULT_NOT_FOUND"
        source = "RACING_COM"
    else:
        status = "PENDING"

    row["result_status"] = status
    row["settlement_source"] = source
    row["finish_position"] = finish
    row["won"] = won
    row["placed"] = placed
    row["profit_1u_win"] = profit
    return row


def metric_summary(out_df: pd.DataFrame) -> pd.DataFrame:
    settled_mask = out_df["result_status"].astype(str).str.upper().eq("SETTLED")
    pending_mask = out_df["result_status"].astype(str).str.upper().eq("PENDING")
    not_found_mask = out_df["result_status"].astype(str).str.upper().eq("RESULT_NOT_FOUND")

    won_num = to_num(out_df["won"]).fillna(0)
    placed_num = to_num(out_df["placed"]).fillna(0)
    profit_num = to_num(out_df["profit_1u_win"])

    settled_profit = profit_num[settled_mask & profit_num.notna()]
    total_profit = round(float(settled_profit.sum()), 2) if not settled_profit.empty else 0.0
    profit_bet_count = int(settled_profit.shape[0])
    roi = round(total_profit / profit_bet_count, 4) if profit_bet_count else 0.0

    summary_rows = [
        {"metric": "tracking_rows", "value": int(len(out_df))},
        {"metric": "settled_rows", "value": int(settled_mask.sum())},
        {"metric": "pending_rows", "value": int(pending_mask.sum())},
        {"metric": "result_not_found_rows", "value": int(not_found_mask.sum())},
        {"metric": "wins", "value": int(won_num[settled_mask].sum())},
        {"metric": "places", "value": int(placed_num[settled_mask].sum())},
        {"metric": "profit_1u_win", "value": total_profit},
        {"metric": "roi_1u_win", "value": roi},
    ]
    return pd.DataFrame(summary_rows)


def by_action_metrics(out_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    actions = sorted(out_df["execution_action_v2"].fillna("").astype(str).unique(), key=action_priority)
    for action in actions:
        action_df = out_df[out_df["execution_action_v2"].astype(str) == action].copy()
        settled_mask = action_df["result_status"].astype(str).str.upper().eq("SETTLED")
        settled_df = action_df[settled_mask].copy()
        profit_num = to_num(settled_df["profit_1u_win"])
        priced_profit = profit_num[profit_num.notna()]
        settled_count = int(len(settled_df))
        wins = int(to_num(settled_df["won"]).fillna(0).sum()) if settled_count else 0
        places = int(to_num(settled_df["placed"]).fillna(0).sum()) if settled_count else 0
        profit = round(float(priced_profit.sum()), 2) if not priced_profit.empty else 0.0
        roi = round(profit / int(priced_profit.shape[0]), 4) if int(priced_profit.shape[0]) else 0.0
        rows.append(
            {
                "execution_action_v2": action,
                "runners": int(len(action_df)),
                "settled": settled_count,
                "wins": wins,
                "places": places,
                "win_rate": round(wins / settled_count, 4) if settled_count else 0.0,
                "place_rate": round(places / settled_count, 4) if settled_count else 0.0,
                "profit_1u_win": profit,
                "roi_1u_win": roi,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    tracking_df = pd.read_csv(TRACKING_PATH, dtype=str, keep_default_na=False)
    results_df = pd.read_csv(RESULTS_PATH, dtype=str, keep_default_na=False, low_memory=False)

    tracking_df = tracking_df.copy()
    tracking_df["meeting_date"] = tracking_df["meeting_date"].astype(str).str[:10]
    tracking_df["race_no"] = to_num(tracking_df["race_no"]).astype("Int64")
    tracking_df["_race_key_v2"] = build_race_key(tracking_df, "meeting_date", "track", "race_no")
    tracking_df["_runner_key_v2"] = build_runner_key(tracking_df, "meeting_date", "track", "race_no", tracking_df["horse"])

    for column in SETTLEMENT_COLUMNS:
        if column not in tracking_df.columns:
            tracking_df[column] = ""
        tracking_df[column] = tracking_df[column].astype(object)

    date_col = "meeting_date" if "meeting_date" in results_df.columns else "race_date"
    track_col = "track"
    race_col = "race_no"
    horse_key_col = "horseKey" if "horseKey" in results_df.columns else None
    horse_name_col = "horseName" if "horseName" in results_df.columns else ("horse" if "horse" in results_df.columns else None)
    finish_col = "finishPosition" if "finishPosition" in results_df.columns else "finish_position"

    results_df = results_df.copy()
    results_df[date_col] = results_df[date_col].astype(str).str[:10]
    results_df[race_col] = to_num(results_df[race_col]).astype("Int64")
    results_df["_race_key_v2"] = build_race_key(results_df, date_col, track_col, race_col)

    if horse_key_col is not None and horse_key_col in results_df.columns:
        horse_join_source = results_df[horse_key_col].where(
            results_df[horse_key_col].fillna("").astype(str).str.strip().ne(""),
            results_df[horse_name_col],
        )
    else:
        horse_join_source = results_df[horse_name_col]

    results_df["_runner_key_v2"] = build_runner_key(results_df, date_col, track_col, race_col, horse_join_source)
    results_df["finish_position_result_v2"] = results_df[finish_col].map(parse_finish)

    results_lookup = (
        results_df[["_runner_key_v2", "finish_position_result_v2"]]
        .drop_duplicates("_runner_key_v2", keep="last")
        .set_index("_runner_key_v2")
    )
    race_keys = set(results_df["_race_key_v2"].dropna().astype(str).tolist())

    settled_df = tracking_df.apply(lambda row: settle_row(row, race_keys, results_lookup), axis=1)
    settled_df = settled_df.drop(columns=["_race_key_v2", "_runner_key_v2"], errors="ignore")
    settled_df.to_csv(OUTPUT_PATH, index=False)

    summary_df = metric_summary(settled_df)
    summary_df.to_csv(SUMMARY_PATH, index=False)

    by_action_df = by_action_metrics(settled_df)
    by_action_df.to_csv(BY_ACTION_PATH, index=False)

    settled_preview = settled_df[
        [
            "meeting_date",
            "track",
            "race_no",
            "horse",
            "execution_action_v2",
            "market_price_v1",
            "result_status",
            "finish_position",
            "won",
            "placed",
            "profit_1u_win",
        ]
    ].copy()
    settled_preview = settled_preview[settled_preview["result_status"].astype(str).str.upper().ne("PENDING")]

    print("[EDGEIQ_EXECUTION_TRACKING_SETTLEMENT_V2] COMPLETE")
    print(summary_df.to_string(index=False))
    print("\nBy Action")
    print(by_action_df.to_string(index=False))
    print("\nSettled Rows")
    if settled_preview.empty:
        print("No settled or result-not-found rows yet.")
    else:
        print(settled_preview.to_string(index=False))


if __name__ == "__main__":
    main()
