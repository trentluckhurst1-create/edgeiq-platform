from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import math
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC_SETTLED = DATA / "edgeiq_historical_replay_settled_v1.csv"
SRC_V6_BACKTEST = DATA / "edgeiq_projection_v6_1_research_prior_rating_backtest.csv"
SRC_HIST_V6 = DATA / "edgeiq_historical_performance_rating_v6_research.csv"
SRC_CURRENT_FAIR = DATA / "edgeiq_current_fair_prices_V6_1_RESEARCH_replay.csv"

OUT_REPLAY = DATA / "edgeiq_v6_1_settled_gap_replay_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_v6_1_settled_gap_replay_v1_summary.csv"

JOIN_STATUS_MATCHED = "MATCHED_V6_1_BACKTEST_DATE_TRACK_HORSE"
JOIN_STATUS_UNMATCHED = "NO_V6_1_BACKTEST_MATCH"


def clean(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def upper(value: object) -> str:
    return clean(value).upper()


def to_float(value: object) -> float | None:
    text = clean(value)
    if text == "":
        return None
    text = text.replace(",", "").replace("$", "")
    try:
        parsed = float(text)
    except Exception:
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def canon_horse(value: object) -> str:
    text = upper(value).replace("’", "'")
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def norm_track(value: object) -> str:
    text = upper(value)
    for prefix in ["BET365 ", "LADBROKES ", "SPORTSBET ", "SPORTSBET-", "APIAM "]:
        text = text.replace(prefix, "")
    return re.sub(r"\s+", " ", text).strip()


def first_existing(columns: list[str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def load_required_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)


def build_settled_base() -> tuple[pd.DataFrame, str]:
    settled = load_required_csv(SRC_SETTLED)
    columns = list(settled.columns)

    race_col = first_existing(columns, ["race_key"])
    date_col = first_existing(columns, ["meeting_date", "race_date"])
    track_col = first_existing(columns, ["track"])
    race_no_col = first_existing(columns, ["race_no"])
    horse_col = first_existing(columns, ["horse"])
    horse_key_col = first_existing(columns, ["horse_key"])
    won_col = first_existing(columns, ["won"])
    finish_col = first_existing(columns, ["finish_position"])
    sp_col = first_existing(columns, ["sp_num_settled", "sp_settled", "sp"])

    missing = []
    for label, col in [
        ("race_key", race_col),
        ("meeting_date/race_date", date_col),
        ("track", track_col),
        ("race_no", race_no_col),
        ("horse", horse_col),
        ("won", won_col),
        ("finish_position", finish_col),
    ]:
        if col is None:
            missing.append(label)

    if missing:
        raise RuntimeError(f"Missing required settled columns: {missing}")

    base = pd.DataFrame()
    base["race_key"] = settled[race_col].map(clean)
    base["meeting_date"] = settled[date_col].map(clean).str[:10]
    base["track"] = settled[track_col].map(clean)
    base["race_no"] = settled[race_no_col].map(clean)
    base["horse"] = settled[horse_col].map(clean)
    if horse_key_col:
        base["horse_key"] = settled[horse_key_col].where(
            settled[horse_key_col].map(clean).ne(""),
            settled[horse_col].map(canon_horse),
        ).map(canon_horse)
    else:
        base["horse_key"] = settled[horse_col].map(canon_horse)
    base["won"] = pd.to_numeric(settled[won_col], errors="coerce").fillna(0).astype(int)
    base["finish_position"] = pd.to_numeric(settled[finish_col], errors="coerce")
    base["placed"] = ((base["finish_position"] >= 1) & (base["finish_position"] <= 3)).astype(int)
    base["sp"] = settled[sp_col].map(to_float) if sp_col else None

    base["join_key_v1"] = (
        base["meeting_date"].map(clean) + "|" +
        base["track"].map(norm_track) + "|" +
        base["horse_key"].map(canon_horse)
    )

    return base, sp_col or ""


def build_v61_projection_lookup() -> tuple[pd.DataFrame, int]:
    back = load_required_csv(SRC_V6_BACKTEST)
    back = back[back["model"].map(upper).eq("V6_1_RESEARCH_PRIOR")].copy()

    back["meeting_date"] = back["race_date"].map(clean).str[:10]
    back["track_norm_v1"] = back["track"].map(norm_track)
    back["horse_key"] = back["horse"].map(canon_horse)
    back["join_key_v1"] = back["meeting_date"] + "|" + back["track_norm_v1"] + "|" + back["horse_key"]

    duplicate_rows = int(back["join_key_v1"].duplicated().sum())
    if duplicate_rows > 0:
        back = back.sort_values(["join_key_v1", "race_key", "horse"]).drop_duplicates("join_key_v1", keep="first")

    lookup = pd.DataFrame(
        {
            "join_key_v1": back["join_key_v1"],
            "projection_gap_V6_1_RESEARCH": pd.to_numeric(back["rating_gap"], errors="coerce"),
            "projected_rating_V6_1_RESEARCH": pd.to_numeric(back["rating"], errors="coerce"),
            "race_target_rating_V6_1_RESEARCH": pd.to_numeric(back["race_median_rating"], errors="coerce"),
            "projection_band_V6_1_RESEARCH": back["projection_band"].map(clean),
            "V6_1_RESEARCH_probability": pd.to_numeric(back["model_prob"], errors="coerce"),
            "V6_1_RESEARCH_fair_price": pd.to_numeric(back["fair_price"], errors="coerce"),
        }
    )
    return lookup, duplicate_rows


def build_output() -> tuple[pd.DataFrame, pd.DataFrame]:
    settled_base, sp_source_col = build_settled_base()
    v61_lookup, duplicate_rows = build_v61_projection_lookup()

    merged = settled_base.merge(v61_lookup, on="join_key_v1", how="left")
    matched = merged["projection_gap_V6_1_RESEARCH"].notna()
    merged["source_match_status"] = matched.map({True: JOIN_STATUS_MATCHED, False: JOIN_STATUS_UNMATCHED})

    output = merged[
        [
            "race_key",
            "meeting_date",
            "track",
            "race_no",
            "horse",
            "horse_key",
            "won",
            "placed",
            "finish_position",
            "sp",
            "projection_gap_V6_1_RESEARCH",
            "projected_rating_V6_1_RESEARCH",
            "race_target_rating_V6_1_RESEARCH",
            "projection_band_V6_1_RESEARCH",
            "V6_1_RESEARCH_probability",
            "V6_1_RESEARCH_fair_price",
            "source_match_status",
        ]
    ].copy()

    matched_rows = int((output["source_match_status"] == JOIN_STATUS_MATCHED).sum())
    unmatched_rows = int((output["source_match_status"] == JOIN_STATUS_UNMATCHED).sum())
    matched_races = int(output.loc[output["source_match_status"] == JOIN_STATUS_MATCHED, "race_key"].nunique())
    matched_min_date = clean(output.loc[output["source_match_status"] == JOIN_STATUS_MATCHED, "meeting_date"].min())
    matched_max_date = clean(output.loc[output["source_match_status"] == JOIN_STATUS_MATCHED, "meeting_date"].max())

    summary = pd.DataFrame(
        [
            {
                "status": "EDGEIQ_V6_1_SETTLED_GAP_REPLAY_V1_BUILT",
                "settled_source": SRC_SETTLED.name,
                "v6_1_source": SRC_V6_BACKTEST.name,
                "supporting_source_historical_v6": SRC_HIST_V6.name if SRC_HIST_V6.exists() else "",
                "supporting_source_current_fair_replay": SRC_CURRENT_FAIR.name if SRC_CURRENT_FAIR.exists() else "",
                "sp_source_col_used": sp_source_col,
                "match_key_v1": "meeting_date|normalized_track|horse_key",
                "backtest_model_used": "V6_1_RESEARCH_PRIOR",
                "race_target_mapping_note": "race_median_rating mapped to race_target_rating_V6_1_RESEARCH",
                "settled_rows": int(len(output)),
                "v6_1_backtest_rows_filtered": int(len(v61_lookup)),
                "matched_rows": matched_rows,
                "unmatched_rows": unmatched_rows,
                "matched_pct": round((matched_rows / len(output)) * 100.0, 3) if len(output) else 0.0,
                "matched_races": matched_races,
                "total_races": int(output["race_key"].nunique()),
                "matched_min_date": matched_min_date,
                "matched_max_date": matched_max_date,
                "duplicate_backtest_rows_removed": duplicate_rows,
                "built_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
    )

    return output, summary


def print_section(title: str, frame: pd.DataFrame) -> None:
    print("")
    print(title)
    if frame.empty:
        print("(no rows)")
        return
    print(frame.to_string(index=False))


def main() -> None:
    output, summary = build_output()
    output.to_csv(OUT_REPLAY, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)

    print("[V6_1_SETTLED_GAP_REPLAY_V1] COMPLETE")
    print_section("SUMMARY", summary)
    print_section("MATCH STATUS", output.groupby("source_match_status").size().reset_index(name="rows"))


if __name__ == "__main__":
    main()
