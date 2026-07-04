from __future__ import annotations

from pathlib import Path
import pandas as pd
import numpy as np
import re


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
GOV = DATA / "edgeiq_no_history_governance_v1.csv"
UNIVERSE = DATA / "edgeiq_vic_three_day_meeting_universe.csv"

OUT = DATA / "edgeiq_live_runner_board_governed_v1.csv"
SUMMARY = DATA / "edgeiq_live_runner_board_governed_v1_summary.csv"


def safe(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def canon_horse(value: object) -> str:
    text = safe(value).upper()
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def key(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["_date"] = out.get("race_date", pd.Series("", index=out.index)).astype(str).str[:10]
    out["_track"] = out["track"].astype(str).str.upper().str.replace(r"[^A-Z0-9]", "", regex=True)
    out["_race"] = out["race_no"].astype(str).str.replace(r"[^0-9]", "", regex=True)
    out["_horse"] = out["horse"].map(canon_horse)
    return out


def governed_decision(row: pd.Series) -> str:
    band = safe(row.get("no_history_governance_band", ""))
    action = safe(row.get("execution_action", ""))

    if band.startswith("NO_HISTORY"):
        if band in {"NO_HISTORY_MARKET_CONFLICT_SHORT", "NO_HISTORY_MARKET_CONFLICT_MID"}:
            return "UNKNOWN_REVIEW"
        if band == "NO_HISTORY_LONGSHOT":
            return "UNKNOWN_LONGSHOT"
        if band == "NO_HISTORY_NO_LIVE":
            return "NO_LIVE_UNKNOWN"
        return "UNKNOWN_REVIEW"

    return action


def governed_reason(row: pd.Series) -> str:
    band = safe(row.get("no_history_governance_band", ""))
    comment = safe(row.get("no_history_governance_comment", ""))

    if band.startswith("NO_HISTORY"):
        return comment or "No-history runner. Price hidden from governed display."

    return "Runner has projection/history. Official price retained."


def main() -> None:
    board = pd.read_csv(BOARD, dtype=str, low_memory=False).fillna("")
    gov = pd.read_csv(GOV, dtype=str, low_memory=False).fillna("")
    universe = pd.read_csv(UNIVERSE, dtype=str, low_memory=False).fillna("") if UNIVERSE.exists() else pd.DataFrame()
    previous_governed = pd.read_csv(OUT, dtype=str, low_memory=False).fillna("") if OUT.exists() else pd.DataFrame()

    board.columns = [column.strip() for column in board.columns]
    gov.columns = [column.strip() for column in gov.columns]
    if not universe.empty:
        universe.columns = [column.strip() for column in universe.columns]

        board_keyed = key(board)
        universe_keyed = key(universe)
        board_keys = set(zip(board_keyed["_date"], board_keyed["_track"], board_keyed["_race"], board_keyed["_horse"]))
        universe_keyed["_join_key"] = list(zip(universe_keyed["_date"], universe_keyed["_track"], universe_keyed["_race"], universe_keyed["_horse"]))
        missing_from_board = universe_keyed[~universe_keyed["_join_key"].isin(board_keys)].drop(columns=["_join_key"], errors="ignore")

        if not missing_from_board.empty:
            for column in board.columns:
                if column not in missing_from_board.columns:
                    missing_from_board[column] = ""
            for column in missing_from_board.columns:
                if column not in board.columns and not column.startswith("_"):
                    board[column] = ""
            missing_from_board = missing_from_board[[column for column in board.columns if column in missing_from_board.columns]]
            if "source" in missing_from_board.columns:
                missing_from_board["source"] = missing_from_board["source"].replace("", "universe_fallback")
            if "terminal_scope" in missing_from_board.columns:
                missing_from_board["terminal_scope"] = missing_from_board["terminal_scope"].replace("", "CURRENT_TERMINAL")
            board = pd.concat([board, missing_from_board], ignore_index=True, sort=False).fillna("")

    previous_rows = len(previous_governed)
    previous_latest_date = safe(previous_governed.get("race_date", pd.Series(dtype=str)).astype(str).str[:10].max()) if not previous_governed.empty and "race_date" in previous_governed.columns else ""
    live_latest_date = safe(board.get("race_date", pd.Series(dtype=str)).astype(str).str[:10].max()) if "race_date" in board.columns else ""
    previous_meetings = set(previous_governed.get("meeting_key", pd.Series(dtype=str)).astype(str)) if not previous_governed.empty and "meeting_key" in previous_governed.columns else set()
    live_meetings = set(board.get("meeting_key", pd.Series(dtype=str)).astype(str)) if "meeting_key" in board.columns else set()
    stale_rows = previous_rows < len(board)
    stale_date = bool(live_latest_date and previous_latest_date and previous_latest_date < live_latest_date)
    stale_meeting = bool(live_meetings - previous_meetings)

    board = key(board)
    gov = key(gov)

    keep = [
        "_date",
        "_track",
        "_race",
        "_horse",
        "display_fair_price_governed",
        "no_history_flag",
        "no_projection_flag",
        "no_history_governance_band",
        "no_history_governance_comment",
    ]
    keep = [column for column in keep if column in gov.columns]

    merged = board.merge(
        gov[keep].drop_duplicates(["_date", "_track", "_race", "_horse"]),
        on=["_date", "_track", "_race", "_horse"],
        how="left",
    )

    merged["fair_price_raw"] = merged.get("fair_price", "")
    merged["edge_pct_raw"] = merged.get("edge_pct", "")
    merged["execution_action_raw"] = merged.get("execution_action", "")

    merged["fair_price_display"] = np.where(
        merged["no_history_flag"].eq("True"),
        "UNKNOWN",
        merged["fair_price_raw"].astype(str),
    )

    merged["edge_pct_display"] = np.where(
        merged["no_history_flag"].eq("True"),
        "",
        merged["edge_pct_raw"].astype(str),
    )

    merged["execution_action_governed"] = merged.apply(governed_decision, axis=1)
    merged["governance_reason"] = merged.apply(governed_reason, axis=1)

    merged = merged.drop(columns=["_date", "_track", "_race", "_horse"], errors="ignore")
    if "saddlecloth" in merged.columns:
        merged["_saddle_sort"] = pd.to_numeric(merged["saddlecloth"], errors="coerce").fillna(9999)
    else:
        merged["_saddle_sort"] = 9999
    merged["_date_sort"] = merged.get("race_date", "").astype(str)
    merged["_track_sort"] = merged.get("track", "").astype(str)
    merged["_race_sort"] = pd.to_numeric(merged.get("race_no", ""), errors="coerce").fillna(9999)
    merged = merged.sort_values(["_date_sort", "_track_sort", "_race_sort", "_saddle_sort", "horse"], kind="stable")
    merged = merged.drop(columns=["_date_sort", "_track_sort", "_race_sort", "_saddle_sort"], errors="ignore")
    merged.to_csv(OUT, index=False, encoding="utf-8")

    summary = [
        ("status", "COMPLETE"),
        ("rows", len(merged)),
        ("previous_governed_rows", previous_rows),
        ("live_rows_used", len(board)),
        ("self_healed_stale_rows", "YES" if stale_rows else "NO"),
        ("self_healed_stale_latest_date", "YES" if stale_date else "NO"),
        ("self_healed_missing_meeting", "YES" if stale_meeting else "NO"),
        ("previous_latest_date", previous_latest_date),
        ("live_latest_date", live_latest_date),
        ("flemington_2026_07_04_rows", int(((merged.get("track", pd.Series(dtype=str)).astype(str).str.upper() == "FLEMINGTON") & (merged.get("race_date", pd.Series(dtype=str)).astype(str).str[:10] == "2026-07-04")).sum())),
        ("no_history_rows", int(merged.get("no_history_flag", pd.Series(dtype=str)).eq("True").sum())),
        ("fair_price_hidden_unknown", int(merged.get("fair_price_display", pd.Series(dtype=str)).eq("UNKNOWN").sum())),
    ]

    if "execution_action_governed" in merged.columns:
        for key_name, value in merged["execution_action_governed"].value_counts(dropna=False).to_dict().items():
            summary.append((f"execution_action_governed_{key_name}", value))

    pd.DataFrame(summary, columns=["metric", "value"]).to_csv(SUMMARY, index=False, encoding="utf-8")

    print("[LIVE_RUNNER_BOARD_GOVERNED_V1] COMPLETE")
    print(f"rows={len(merged)}")
    print(f"fair_price_hidden_unknown={int(merged.get('fair_price_display', pd.Series(dtype=str)).eq('UNKNOWN').sum())}")
    print(f"wrote={OUT}")
    print(f"summary={SUMMARY}")


if __name__ == "__main__":
    main()
