from __future__ import annotations

import math
import re
import unicodedata
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "public" / "data"

TRACKING_PATH = DATA_DIR / "edgeiq_execution_tracking_v3.csv"
RESULTS_PATH = DATA_DIR / "edgeiq_racingcom_results_warehouse_v1.csv"
V2_SETTLED_PATH = DATA_DIR / "edgeiq_execution_tracking_v2_settled.csv"

OUTPUT_PATH = DATA_DIR / "edgeiq_execution_tracking_v3_settled.csv"
SUMMARY_PATH = DATA_DIR / "edgeiq_execution_tracking_v3_settlement_summary.csv"
BREAKDOWN_PATH = DATA_DIR / "edgeiq_execution_tracking_v3_by_action.csv"

ACTION_ORDER = {
    "ELITE_EXECUTE": 1,
    "EXECUTE": 2,
    "STRONG_WATCH": 3,
    "WATCH": 4,
    "NO_BET": 5,
}

TRACKING_COLUMNS = [
    "meeting_date",
    "track",
    "race_no",
    "horse",
    "execution_action_v3",
    "trust_profile_v1",
    "runner_rank_v6",
    "runner_score_v6",
    "market_price_v1",
    "edge_pct_v1",
    "execution_reason_v3",
    "captured_timestamp",
    "result_status",
    "settlement_source",
    "finish_position",
    "won",
    "placed",
    "profit_1u_win",
]

BREAKDOWN_COLUMNS = [
    "breakdown_type",
    "breakdown_value",
    "runners",
    "settled",
    "wins",
    "places",
    "win_rate",
    "place_rate",
    "profit_1u_win",
    "roi_1u_win",
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
            return text.encode("latin1").decode("utf-8")
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


def ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        if column not in df.columns:
            df[column] = ""
    return df[columns].copy()


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


def rank_bucket(rank_value: object) -> str:
    rank = pd.to_numeric(rank_value, errors="coerce")
    if pd.isna(rank):
        return "UNKNOWN"
    rank_int = int(rank)
    if rank_int == 1:
        return "RANK_1"
    if rank_int == 2:
        return "RANK_2"
    if rank_int == 3:
        return "RANK_3"
    if rank_int <= 5:
        return "RANK_4_5"
    if rank_int <= 10:
        return "RANK_6_10"
    return "RANK_11_PLUS"


def action_priority(action: str) -> int:
    return ACTION_ORDER.get(clean_text(action).upper(), 99)


def settle_row(row: pd.Series, race_keys: set[str], results_lookup: pd.DataFrame) -> pd.Series:
    race_key = clean_text(row.get("_race_key_v3", ""))
    runner_key = clean_text(row.get("_runner_key_v3", ""))
    market_price = pd.to_numeric(row.get("market_price_v1"), errors="coerce")

    if runner_key in results_lookup.index:
        result_row = results_lookup.loc[runner_key]
        finish_num = pd.to_numeric(result_row.get("finish_position_result_v3"), errors="coerce")
        if pd.notna(finish_num):
            finish_int = int(finish_num)
            row["result_status"] = "SETTLED"
            row["settlement_source"] = "RACING_COM"
            row["finish_position"] = str(finish_int)
            row["won"] = "1" if finish_int == 1 else "0"
            row["placed"] = "1" if finish_int <= 3 else "0"
            if pd.notna(market_price):
                row["profit_1u_win"] = round(float(market_price) - 1.0, 2) if finish_int == 1 else -1.0
            else:
                row["profit_1u_win"] = ""
            return row

    if race_key in race_keys:
        row["result_status"] = "RESULT_NOT_FOUND"
        row["settlement_source"] = "RACING_COM"
        row["finish_position"] = ""
        row["won"] = ""
        row["placed"] = ""
        row["profit_1u_win"] = ""
    else:
        row["result_status"] = "PENDING"
        row["settlement_source"] = ""
        row["finish_position"] = ""
        row["won"] = ""
        row["placed"] = ""
        row["profit_1u_win"] = ""
    return row


def summarize_settled(df: pd.DataFrame) -> dict[str, float]:
    settled_mask = df["result_status"].astype(str).str.upper().eq("SETTLED")
    wins = int(to_num(df.loc[settled_mask, "won"]).fillna(0).sum())
    places = int(to_num(df.loc[settled_mask, "placed"]).fillna(0).sum())
    settled_rows = int(settled_mask.sum())
    profit_num = to_num(df.loc[settled_mask, "profit_1u_win"])
    priced_profit = profit_num[profit_num.notna()]
    total_profit = round(float(priced_profit.sum()), 2) if not priced_profit.empty else 0.0
    roi = round(total_profit / int(priced_profit.shape[0]), 4) if int(priced_profit.shape[0]) else 0.0
    return {
        "settled_rows": settled_rows,
        "wins": wins,
        "places": places,
        "win_rate": round(wins / settled_rows, 4) if settled_rows else 0.0,
        "place_rate": round(places / settled_rows, 4) if settled_rows else 0.0,
        "profit_1u_win": total_profit,
        "roi_1u_win": roi,
    }


def breakdown_metrics(df: pd.DataFrame, group_col: str, breakdown_type: str, sort_order: list[str] | None = None) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    values = df[group_col].fillna("").astype(str).unique().tolist()
    if breakdown_type == "EXECUTION_ACTION_V3":
        values = sorted(values, key=action_priority)
    elif sort_order is not None:
        values = sorted(values, key=lambda value: sort_order.index(value) if value in sort_order else len(sort_order))
    else:
        values = sorted(values)

    for value in values:
        bucket_df = df[df[group_col].fillna("").astype(str) == value].copy()
        settled = bucket_df[bucket_df["result_status"].astype(str).str.upper().eq("SETTLED")].copy()
        settled_count = int(len(settled))
        wins = int(to_num(settled["won"]).fillna(0).sum()) if settled_count else 0
        places = int(to_num(settled["placed"]).fillna(0).sum()) if settled_count else 0
        profit_num = to_num(settled["profit_1u_win"])
        priced_profit = profit_num[profit_num.notna()]
        profit = round(float(priced_profit.sum()), 2) if not priced_profit.empty else 0.0
        roi = round(profit / int(priced_profit.shape[0]), 4) if int(priced_profit.shape[0]) else 0.0

        rows.append(
            {
                "breakdown_type": breakdown_type,
                "breakdown_value": value if value != "" else "UNKNOWN",
                "runners": int(len(bucket_df)),
                "settled": settled_count,
                "wins": wins,
                "places": places,
                "win_rate": round(wins / settled_count, 4) if settled_count else 0.0,
                "place_rate": round(places / settled_count, 4) if settled_count else 0.0,
                "profit_1u_win": profit,
                "roi_1u_win": roi,
            }
        )
    return pd.DataFrame(rows, columns=BREAKDOWN_COLUMNS)


def main() -> None:
    tracking_df = pd.read_csv(TRACKING_PATH, dtype=str, keep_default_na=False)
    results_df = pd.read_csv(RESULTS_PATH, dtype=str, keep_default_na=False, low_memory=False)

    tracking_df = ensure_columns(tracking_df, TRACKING_COLUMNS)
    tracking_df = tracking_df.copy()
    tracking_df["meeting_date"] = tracking_df["meeting_date"].astype(str).str[:10]
    tracking_df["race_no"] = to_num(tracking_df["race_no"]).astype("Int64")
    tracking_df["_race_key_v3"] = build_race_key(tracking_df, "meeting_date", "track", "race_no")
    tracking_df["_runner_key_v3"] = build_runner_key(tracking_df, "meeting_date", "track", "race_no", tracking_df["horse"])
    tracking_df["rank_bucket_v1"] = tracking_df["runner_rank_v6"].map(rank_bucket)

    date_col = "meeting_date" if "meeting_date" in results_df.columns else "race_date"
    track_col = "track"
    race_col = "race_no"
    horse_key_col = "horseKey" if "horseKey" in results_df.columns else None
    horse_name_col = "horseName" if "horseName" in results_df.columns else ("horse" if "horse" in results_df.columns else None)
    finish_col = "finishPosition" if "finishPosition" in results_df.columns else "finish_position"

    results_df = results_df.copy()
    results_df[date_col] = results_df[date_col].astype(str).str[:10]
    results_df[race_col] = to_num(results_df[race_col]).astype("Int64")
    results_df["_race_key_v3"] = build_race_key(results_df, date_col, track_col, race_col)

    if horse_key_col is not None and horse_key_col in results_df.columns:
        horse_join_source = results_df[horse_key_col].where(
            results_df[horse_key_col].fillna("").astype(str).str.strip().ne(""),
            results_df[horse_name_col],
        )
    else:
        horse_join_source = results_df[horse_name_col]

    results_df["_runner_key_v3"] = build_runner_key(results_df, date_col, track_col, race_col, horse_join_source)
    results_df["finish_position_result_v3"] = results_df[finish_col].map(parse_finish)
    results_lookup = (
        results_df[["_runner_key_v3", "finish_position_result_v3"]]
        .drop_duplicates("_runner_key_v3", keep="last")
        .set_index("_runner_key_v3")
    )
    race_keys = set(results_df["_race_key_v3"].dropna().astype(str).tolist())

    settled_df = tracking_df.apply(lambda row: settle_row(row, race_keys, results_lookup), axis=1)
    settled_df = settled_df.drop(columns=["_race_key_v3", "_runner_key_v3"], errors="ignore")
    settled_df.to_csv(OUTPUT_PATH, index=False)

    overall = summarize_settled(settled_df)
    pending_rows = int((settled_df["result_status"].astype(str).str.upper() == "PENDING").sum())
    result_not_found_rows = int((settled_df["result_status"].astype(str).str.upper() == "RESULT_NOT_FOUND").sum())

    action_breakdown_df = breakdown_metrics(settled_df, "execution_action_v3", "EXECUTION_ACTION_V3")
    trust_breakdown_df = breakdown_metrics(
        settled_df,
        "trust_profile_v1",
        "TRUST_PROFILE_V1",
        sort_order=["ELITE", "STRONG", "STANDARD", "CHAOTIC", "UNKNOWN"],
    )
    rank_breakdown_df = breakdown_metrics(
        settled_df,
        "rank_bucket_v1",
        "RANK_BUCKET_V1",
        sort_order=["RANK_1", "RANK_2", "RANK_3", "RANK_4_5", "RANK_6_10", "RANK_11_PLUS", "UNKNOWN"],
    )
    breakdown_df = pd.concat([action_breakdown_df, trust_breakdown_df, rank_breakdown_df], ignore_index=True)
    breakdown_df.to_csv(BREAKDOWN_PATH, index=False)

    action_lookup = action_breakdown_df.set_index("breakdown_value") if not action_breakdown_df.empty else pd.DataFrame().set_index(pd.Index([]))
    trust_lookup = trust_breakdown_df.set_index("breakdown_value") if not trust_breakdown_df.empty else pd.DataFrame().set_index(pd.Index([]))

    strong_watch_row = action_lookup.loc["STRONG_WATCH"] if "STRONG_WATCH" in action_lookup.index else None
    standard_row = trust_lookup.loc["STANDARD"] if "STANDARD" in trust_lookup.index else None
    chaotic_row = trust_lookup.loc["CHAOTIC"] if "CHAOTIC" in trust_lookup.index else None

    strongest_action = ""
    if not action_breakdown_df.empty:
        strongest_action = (
            action_breakdown_df[action_breakdown_df["settled"] > 0]
            .sort_values(["roi_1u_win", "win_rate", "settled"], ascending=[False, False, False], kind="mergesort")
            .head(1)["breakdown_value"]
            .astype(str)
            .tolist()
        )
        strongest_action = strongest_action[0] if strongest_action else ""

    strongest_profile = ""
    if not trust_breakdown_df.empty:
        strongest_profile = (
            trust_breakdown_df[trust_breakdown_df["settled"] > 0]
            .sort_values(["roi_1u_win", "win_rate", "settled"], ascending=[False, False, False], kind="mergesort")
            .head(1)["breakdown_value"]
            .astype(str)
            .tolist()
        )
        strongest_profile = strongest_profile[0] if strongest_profile else ""

    v2_comparison = "NOT_AVAILABLE"
    v2_roi = math.nan
    v2_win_rate = math.nan
    if V2_SETTLED_PATH.exists():
        v2_df = pd.read_csv(V2_SETTLED_PATH, dtype=str, keep_default_na=False)
        v2_summary = summarize_settled(v2_df)
        v2_roi = v2_summary["roi_1u_win"]
        v2_win_rate = v2_summary["win_rate"]
        v2_comparison = "YES" if overall["roi_1u_win"] > v2_roi else "NO"

    strong_watch_profitable = "NO_DATA"
    if strong_watch_row is not None and int(strong_watch_row["settled"]) > 0:
        strong_watch_profitable = "YES" if float(strong_watch_row["profit_1u_win"]) > 0 else "NO"

    standard_profitable = "NO_DATA"
    if standard_row is not None and int(standard_row["settled"]) > 0:
        standard_profitable = "YES" if float(standard_row["profit_1u_win"]) > 0 else "NO"

    chaotic_destroying = "NO_DATA"
    if chaotic_row is not None and int(chaotic_row["settled"]) > 0:
        chaotic_destroying = "YES" if float(chaotic_row["profit_1u_win"]) < 0 and float(chaotic_row["roi_1u_win"]) < overall["roi_1u_win"] else "NO"

    summary_rows = [
        {"metric": "tracking_rows", "value": int(len(settled_df))},
        {"metric": "settled_rows", "value": overall["settled_rows"]},
        {"metric": "pending_rows", "value": pending_rows},
        {"metric": "result_not_found_rows", "value": result_not_found_rows},
        {"metric": "wins", "value": overall["wins"]},
        {"metric": "places", "value": overall["places"]},
        {"metric": "win_rate", "value": overall["win_rate"]},
        {"metric": "place_rate", "value": overall["place_rate"]},
        {"metric": "profit_1u_win", "value": overall["profit_1u_win"]},
        {"metric": "roi_1u_win", "value": overall["roi_1u_win"]},
        {"metric": "strong_watch_profitable", "value": strong_watch_profitable},
        {"metric": "standard_profile_profitable", "value": standard_profitable},
        {"metric": "chaotic_races_still_destroying_performance", "value": chaotic_destroying},
        {"metric": "v3_outperforms_v2_on_settled_runners", "value": v2_comparison},
        {"metric": "v2_reference_roi_1u_win", "value": v2_roi if not math.isnan(v2_roi) else "NA"},
        {"metric": "v2_reference_win_rate", "value": v2_win_rate if not math.isnan(v2_win_rate) else "NA"},
        {"metric": "strongest_execution_action_v3", "value": strongest_action if strongest_action != "" else "NA"},
        {"metric": "strongest_trust_profile_v1", "value": strongest_profile if strongest_profile != "" else "NA"},
    ]
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(SUMMARY_PATH, index=False)

    settled_preview = settled_df[
        [
            "meeting_date",
            "track",
            "race_no",
            "horse",
            "execution_action_v3",
            "trust_profile_v1",
            "market_price_v1",
            "result_status",
            "finish_position",
            "won",
            "placed",
            "profit_1u_win",
        ]
    ].copy()
    settled_preview = settled_preview[settled_preview["result_status"].astype(str).str.upper().ne("PENDING")]
    settled_preview = settled_preview.sort_values(
        ["meeting_date", "track", "race_no", "execution_action_v3", "horse"],
        key=lambda series: series.map(action_priority) if series.name == "execution_action_v3" else series,
        kind="mergesort",
    )

    print("[EDGEIQ_EXECUTION_TRACKING_SETTLEMENT_V3] COMPLETE")
    print(summary_df.to_string(index=False))
    print("\nAction Breakdown")
    print(action_breakdown_df.to_string(index=False))
    print("\nTrust Profile Breakdown")
    print(trust_breakdown_df.to_string(index=False))
    print("\nSettled Runners")
    if settled_preview.empty:
        print("No settled or result-not-found rows yet.")
    else:
        print(settled_preview.to_string(index=False))


if __name__ == "__main__":
    main()
