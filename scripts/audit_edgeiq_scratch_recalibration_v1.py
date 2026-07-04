from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SOURCES = [
    {
        "source_file": "edgeiq_live_runner_board_v1.csv",
        "path": DATA / "edgeiq_live_runner_board_v1.csv",
        "source_kind": "LIVE_RUNNER_BOARD",
    },
    {
        "source_file": "edgeiq_live_runner_board_governed_v1.csv",
        "path": DATA / "edgeiq_live_runner_board_governed_v1.csv",
        "source_kind": "LIVE_RUNNER_BOARD_GOVERNED",
    },
    {
        "source_file": "edgeiq_live_v6_1_research_vs_production_comparison_v1_TAB_ONLY_TODAY.csv",
        "path": DATA / "edgeiq_live_v6_1_research_vs_production_comparison_v1_TAB_ONLY_TODAY.csv",
        "source_kind": "V61_COMPARISON",
    },
    {
        "source_file": "edgeiq_current_fair_prices_v6_1_research_replay.csv",
        "path": DATA / "edgeiq_current_fair_prices_v6_1_research_replay.csv",
        "source_kind": "CURRENT_FAIR_PRICES_REPLAY",
    },
]

AUDIT_OUT = DATA / "edgeiq_scratch_recalibration_audit_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_scratch_recalibration_summary_v1.csv"

FOCUS_DATE = "2026-06-15"
FOCUS_TRACK = "PAKENHAM SYNTHETIC"
FOCUS_RACE_NO = 9

DATE_COLUMNS = ["race_date", "meeting_date", "date", "race_date_dt"]
TRACK_COLUMNS = ["track", "meeting", "meeting_name"]
RACE_NO_COLUMNS = ["race_no", "race", "race_number"]
HORSE_COLUMNS = ["horse", "runner", "runner_name"]
WIN_PCT_COLUMNS = ["win_pct", "production_win_pct", "display_win_pct"]
PROBABILITY_COLUMNS = [
    "V6_1_RESEARCH_probability",
    "v6_1_research_probability",
    "v3_probability",
    "probability",
    "win_probability",
    "rated_probability",
]
FAIR_PRICE_COLUMNS = [
    "fair_price",
    "ui_fair_price",
    "rated_price",
    "V6_1_RESEARCH_fair_price",
    "production_fair_price",
]
TAB_PRICE_COLUMNS = [
    "tab_fixed_win",
    "live_price",
    "display_live_price",
    "tab_price",
]
EDGE_COLUMNS = [
    "display_edge_pct",
    "edge_pct",
    "ui_edge_pct",
    "production_edge_pct",
    "v6_1_research_edge_pct",
]


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "null", "nat"}:
        return ""
    return text


def num(value: object) -> float | None:
    text = clean(value).replace("$", "").replace(",", "").replace("%", "")
    if not text or text == "-":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def pick_column(frame: pd.DataFrame, candidates: list[str]) -> str:
    for column in candidates:
        if column in frame.columns:
            return column
    return ""


def race_no_int(value: object) -> int:
    digits = re.sub(r"[^0-9]", "", clean(value))
    return int(digits) if digits else 0


def normalize_track(value: object) -> str:
    return re.sub(r"\s+", " ", clean(value).upper()).strip()


def probability_to_pct(value: float | None) -> float | None:
    if value is None:
        return None
    if abs(value) <= 1.5:
        return value * 100.0
    return value


def bool_to_flag(value: bool) -> str:
    return "YES" if value else "NO"


def detect_scratched(row: pd.Series) -> bool:
    text_blob = " ".join(
        [
            clean(row.get("display_decision")),
            clean(row.get("runner_status")),
            clean(row.get("tab_fixed_betting_status")),
            clean(row.get("scratch_status")),
            clean(row.get("is_scratched")),
            clean(row.get("execution_action")),
            clean(row.get("decision")),
            clean(row.get("production_action")),
            clean(row.get("execution_action_governed")),
            clean(row.get("market_state")),
        ]
    ).upper()
    if "SCRATCH" in text_blob:
        return True
    return clean(row.get("is_scratched")).upper() in {"YES", "Y", "TRUE", "1"}


def first_numeric_in_row(row: pd.Series, candidates: list[str]) -> tuple[float | None, str]:
    for column in candidates:
        if column in row.index:
            value = num(row.get(column))
            if value is not None:
                return value, column
    for column in candidates:
        if column in row.index:
            return None, column
    return None, ""


def build_source_frame(meta: dict[str, object]) -> tuple[pd.DataFrame, dict[str, object]]:
    path = Path(meta["path"])
    source_file = str(meta["source_file"])
    source_kind = str(meta["source_kind"])
    if not path.exists():
        return pd.DataFrame(), {
            "source_file": source_file,
            "source_kind": source_kind,
            "file_exists": "NO",
        }

    frame = pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)

    date_col = pick_column(frame, DATE_COLUMNS)
    track_col = pick_column(frame, TRACK_COLUMNS)
    race_no_col = pick_column(frame, RACE_NO_COLUMNS)
    horse_col = pick_column(frame, HORSE_COLUMNS)
    win_pct_col = pick_column(frame, WIN_PCT_COLUMNS)
    probability_col = pick_column(frame, PROBABILITY_COLUMNS)
    fair_price_col = pick_column(frame, FAIR_PRICE_COLUMNS)
    tab_price_col = pick_column(frame, TAB_PRICE_COLUMNS)
    edge_col = pick_column(frame, EDGE_COLUMNS)

    frame["__race_date"] = frame[date_col].map(clean).str[:10] if date_col else ""
    frame["__track"] = frame[track_col].map(normalize_track) if track_col else ""
    frame["__race_no"] = frame[race_no_col].map(race_no_int) if race_no_col else 0
    frame["__horse"] = frame[horse_col].map(clean) if horse_col else ""
    frame["__scratched"] = frame.apply(detect_scratched, axis=1)
    frame["__win_pct"] = frame[win_pct_col].map(num) if win_pct_col else math.nan
    frame["__probability_raw"] = frame[probability_col].map(num) if probability_col else math.nan
    frame["__probability_pct_equiv"] = frame["__probability_raw"].map(probability_to_pct) if probability_col else math.nan
    frame["__fair_price"] = frame[fair_price_col].map(num) if fair_price_col else math.nan
    frame["__tab_price"] = frame[tab_price_col].map(num) if tab_price_col else math.nan
    frame["__edge"] = frame[edge_col].map(num) if edge_col else math.nan

    info = {
        "source_file": source_file,
        "source_kind": source_kind,
        "file_exists": "YES",
        "rows": int(len(frame)),
        "date_col": date_col,
        "track_col": track_col,
        "race_no_col": race_no_col,
        "horse_col": horse_col,
        "win_pct_col": win_pct_col,
        "probability_col": probability_col,
        "fair_price_col": fair_price_col,
        "tab_price_col": tab_price_col,
        "edge_col": edge_col,
    }
    return frame, info


def main() -> None:
    source_frames: list[tuple[pd.DataFrame, dict[str, object]]] = [build_source_frame(meta) for meta in SOURCES]

    available_dates: list[str] = []
    for frame, info in source_frames:
        if info["file_exists"] == "YES" and not frame.empty and "__race_date" in frame.columns:
            available_dates.extend([value for value in frame["__race_date"].tolist() if value])
    global_max_date = max(available_dates) if available_dates else ""

    audit_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    for frame, info in source_frames:
        source_file = str(info["source_file"])
        source_kind = str(info["source_kind"])
        file_exists = str(info["file_exists"])

        if file_exists == "NO":
            summary_rows.append(
                {
                    "summary_scope": "SOURCE",
                    "source_file": source_file,
                    "source_kind": source_kind,
                    "file_exists": "NO",
                    "rows": 0,
                    "unique_races": 0,
                    "source_date_min": "",
                    "source_date_max": "",
                    "source_stale_vs_latest_flag": "MISSING",
                    "current_focus_rows": 0,
                    "current_focus_active_runners": 0,
                    "current_focus_scratched_runners": 0,
                    "current_focus_active_win_pct_sum": "",
                    "current_focus_active_probability_pct_equiv": "",
                    "current_focus_probability_close_to_100": "",
                    "current_focus_scratched_with_win_pct_gt0": 0,
                    "current_focus_scratched_with_fair_price_present": 0,
                    "current_focus_scratched_with_tab_price_present": 0,
                    "current_focus_scratched_with_edge_present": 0,
                    "current_focus_scratched_excluded_from_recalculated_market": "",
                    "races_probability_close_to_100": 0,
                    "races_probability_not_close_to_100": 0,
                    "scratched_with_win_pct_gt0_total": 0,
                    "scratched_with_fair_price_present_total": 0,
                    "scratched_with_tab_price_present_total": 0,
                    "scratched_with_edge_present_total": 0,
                    "verdict": "SOURCE_MISSING",
                }
            )
            continue

        working = frame[
            frame["__race_date"].ne("")
            & frame["__track"].ne("")
            & frame["__race_no"].gt(0)
        ].copy()

        source_date_min = working["__race_date"].min() if not working.empty else ""
        source_date_max = working["__race_date"].max() if not working.empty else ""
        stale_flag = (
            "STALE_VS_LATEST_DATE"
            if source_date_max and global_max_date and source_date_max < global_max_date
            else "CURRENT_OR_LATEST"
        )

        if working.empty:
            summary_rows.append(
                {
                    "summary_scope": "SOURCE",
                    "source_file": source_file,
                    "source_kind": source_kind,
                    "file_exists": "YES",
                    "rows": int(info["rows"]),
                    "unique_races": 0,
                    "source_date_min": source_date_min,
                    "source_date_max": source_date_max,
                    "source_stale_vs_latest_flag": stale_flag,
                    "current_focus_rows": 0,
                    "current_focus_active_runners": 0,
                    "current_focus_scratched_runners": 0,
                    "current_focus_active_win_pct_sum": "",
                    "current_focus_active_probability_pct_equiv": "",
                    "current_focus_probability_close_to_100": "",
                    "current_focus_scratched_with_win_pct_gt0": 0,
                    "current_focus_scratched_with_fair_price_present": 0,
                    "current_focus_scratched_with_tab_price_present": 0,
                    "current_focus_scratched_with_edge_present": 0,
                    "current_focus_scratched_excluded_from_recalculated_market": "",
                    "races_probability_close_to_100": 0,
                    "races_probability_not_close_to_100": 0,
                    "scratched_with_win_pct_gt0_total": 0,
                    "scratched_with_fair_price_present_total": 0,
                    "scratched_with_tab_price_present_total": 0,
                    "scratched_with_edge_present_total": 0,
                    "verdict": "NO_VALID_RACE_KEYS",
                }
            )
            continue

        probability_close_yes = 0
        probability_close_no = 0
        scratched_prob_total = 0
        scratched_fair_total = 0
        scratched_tab_total = 0
        scratched_edge_total = 0
        focus_summary: dict[str, object] | None = None

        grouped = working.groupby(["__race_date", "__track", "__race_no"], sort=True)
        for (race_date, track, race_no), group in grouped:
            total_runners = int(len(group))
            scratched_mask = group["__scratched"] == True
            active_mask = ~scratched_mask
            scratched_runners = int(scratched_mask.sum())
            active_runners = int(active_mask.sum())

            scratched_with_win_pct_gt0 = int((scratched_mask & group["__win_pct"].fillna(0).gt(0)).sum())
            scratched_with_fair_price_present = int((scratched_mask & group["__fair_price"].notna()).sum())
            scratched_with_tab_price_present = int((scratched_mask & group["__tab_price"].notna()).sum())
            scratched_with_edge_present = int((scratched_mask & group["__edge"].notna()).sum())

            active_win_pct_sum = float(group.loc[active_mask, "__win_pct"].fillna(0).sum())
            active_probability_sum_raw = float(group.loc[active_mask, "__probability_raw"].fillna(0).sum())
            active_probability_pct_equiv = float(group.loc[active_mask, "__probability_pct_equiv"].fillna(0).sum())
            active_probability_delta_from_100 = (
                round(active_probability_pct_equiv - 100.0, 4)
                if str(info["probability_col"])
                else math.nan
            )
            active_fair_price_count = int((active_mask & group["__fair_price"].notna()).sum())
            active_tab_price_count = int((active_mask & group["__tab_price"].notna()).sum())
            active_edge_count = int((active_mask & group["__edge"].notna()).sum())

            if str(info["probability_col"]):
                active_probabilities_sum_close_to_100 = bool_to_flag(99.0 <= active_probability_pct_equiv <= 101.0)
            elif str(info["win_pct_col"]):
                active_probabilities_sum_close_to_100 = bool_to_flag(99.0 <= active_win_pct_sum <= 101.0)
            else:
                active_probabilities_sum_close_to_100 = "NO_PROBABILITY_FIELD"

            if active_probabilities_sum_close_to_100 == "YES":
                probability_close_yes += 1
            elif active_probabilities_sum_close_to_100 == "NO":
                probability_close_no += 1

            scratched_excluded_from_recalculated_market = (
                "NOT_APPLICABLE"
                if scratched_runners == 0
                else "YES"
                if scratched_with_win_pct_gt0 == 0
                and scratched_with_fair_price_present == 0
                and scratched_with_edge_present == 0
                else "NO"
            )

            scratched_prob_total += scratched_with_win_pct_gt0
            scratched_fair_total += scratched_with_fair_price_present
            scratched_tab_total += scratched_with_tab_price_present
            scratched_edge_total += scratched_with_edge_present

            issue_flags: list[str] = []
            if active_probabilities_sum_close_to_100 == "NO":
                issue_flags.append("ACTIVE_PROBABILITY_SUM_NOT_100")
            if scratched_with_win_pct_gt0 > 0:
                issue_flags.append("SCRATCHED_HAS_WIN_CHANCE")
            if scratched_with_fair_price_present > 0:
                issue_flags.append("SCRATCHED_HAS_FAIR_PRICE")
            if scratched_with_edge_present > 0:
                issue_flags.append("SCRATCHED_HAS_VALUE_EDGE")
            if scratched_with_tab_price_present > 0:
                issue_flags.append("SCRATCHED_HAS_TAB_PRICE")
            if stale_flag == "STALE_VS_LATEST_DATE":
                issue_flags.append("STALE_SOURCE_DATE")

            audit_row = {
                "source_file": source_file,
                "source_kind": source_kind,
                "file_exists": "YES",
                "source_date_min": source_date_min,
                "source_date_max": source_date_max,
                "source_stale_vs_latest_flag": stale_flag,
                "race_date": race_date,
                "track": track,
                "race_no": int(race_no),
                "race_key": f"{race_date}|{track}|R{int(race_no)}",
                "total_runners": total_runners,
                "active_runners": active_runners,
                "scratched_runners": scratched_runners,
                "scratched_with_win_pct_gt0": scratched_with_win_pct_gt0,
                "scratched_with_fair_price_present": scratched_with_fair_price_present,
                "scratched_with_tab_price_present": scratched_with_tab_price_present,
                "scratched_with_edge_present": scratched_with_edge_present,
                "active_win_pct_sum": round(active_win_pct_sum, 4),
                "active_probability_sum_raw": round(active_probability_sum_raw, 6) if str(info["probability_col"]) else "",
                "active_probability_sum_pct_equiv": round(active_probability_pct_equiv, 4) if str(info["probability_col"]) else "",
                "active_probability_delta_from_100": active_probability_delta_from_100 if str(info["probability_col"]) else "",
                "active_fair_price_count": active_fair_price_count,
                "active_tab_price_count": active_tab_price_count,
                "active_edge_count": active_edge_count,
                "active_probabilities_sum_close_to_100": active_probabilities_sum_close_to_100,
                "scratched_excluded_from_recalculated_market": scratched_excluded_from_recalculated_market,
                "win_pct_column_used": str(info["win_pct_col"]),
                "probability_column_used": str(info["probability_col"]),
                "fair_price_column_used": str(info["fair_price_col"]),
                "tab_price_column_used": str(info["tab_price_col"]),
                "edge_column_used": str(info["edge_col"]),
                "issue_flags": "|".join(issue_flags),
            }
            audit_rows.append(audit_row)

            if race_date == FOCUS_DATE and track == FOCUS_TRACK and int(race_no) == FOCUS_RACE_NO:
                focus_summary = audit_row

        unique_races = int(working.groupby(["__race_date", "__track", "__race_no"]).ngroups)
        summary_rows.append(
            {
                "summary_scope": "SOURCE",
                "source_file": source_file,
                "source_kind": source_kind,
                "file_exists": "YES",
                "rows": int(info["rows"]),
                "unique_races": unique_races,
                "source_date_min": source_date_min,
                "source_date_max": source_date_max,
                "source_stale_vs_latest_flag": stale_flag,
                "current_focus_rows": int(focus_summary["total_runners"]) if focus_summary else 0,
                "current_focus_active_runners": int(focus_summary["active_runners"]) if focus_summary else 0,
                "current_focus_scratched_runners": int(focus_summary["scratched_runners"]) if focus_summary else 0,
                "current_focus_active_win_pct_sum": focus_summary["active_win_pct_sum"] if focus_summary else "",
                "current_focus_active_probability_pct_equiv": focus_summary["active_probability_sum_pct_equiv"] if focus_summary else "",
                "current_focus_probability_close_to_100": focus_summary["active_probabilities_sum_close_to_100"] if focus_summary else "",
                "current_focus_scratched_with_win_pct_gt0": int(focus_summary["scratched_with_win_pct_gt0"]) if focus_summary else 0,
                "current_focus_scratched_with_fair_price_present": int(focus_summary["scratched_with_fair_price_present"]) if focus_summary else 0,
                "current_focus_scratched_with_tab_price_present": int(focus_summary["scratched_with_tab_price_present"]) if focus_summary else 0,
                "current_focus_scratched_with_edge_present": int(focus_summary["scratched_with_edge_present"]) if focus_summary else 0,
                "current_focus_scratched_excluded_from_recalculated_market": focus_summary["scratched_excluded_from_recalculated_market"] if focus_summary else "",
                "races_probability_close_to_100": probability_close_yes,
                "races_probability_not_close_to_100": probability_close_no,
                "scratched_with_win_pct_gt0_total": scratched_prob_total,
                "scratched_with_fair_price_present_total": scratched_fair_total,
                "scratched_with_tab_price_present_total": scratched_tab_total,
                "scratched_with_edge_present_total": scratched_edge_total,
                "verdict": (
                    "SCRATCH_RECALIBRATION_CLEAN"
                    if scratched_prob_total == 0 and scratched_fair_total == 0 and scratched_edge_total == 0 and probability_close_no == 0
                    else "SCRATCH_RECALIBRATION_REVIEW_REQUIRED"
                ),
            }
        )

    audit = pd.DataFrame(audit_rows)
    if not audit.empty:
        audit = audit.sort_values(["source_file", "race_date", "track", "race_no"]).reset_index(drop=True)
    audit.to_csv(AUDIT_OUT, index=False)

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(SUMMARY_OUT, index=False)

    print("[SCRATCH_RECALIBRATION_AUDIT_V1] COMPLETE")
    print(f"rows={len(audit)}")
    print(f"summary_rows={len(summary)}")
    print(f"wrote={AUDIT_OUT}")
    print(f"wrote={SUMMARY_OUT}")


if __name__ == "__main__":
    main()
