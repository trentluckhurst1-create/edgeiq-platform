from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import math
import re

import pandas as pd

from edgeiq_track_alias_bridge_v1 import apply_track_alias, build_track_alias_bridge


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC_SETTLED = DATA / "edgeiq_historical_replay_settled_v1.csv"
SRC_V6_BACKTEST = DATA / "edgeiq_projection_v6_1_research_prior_rating_backtest.csv"
SRC_HIST_V6 = DATA / "edgeiq_historical_performance_rating_v6_research.csv"
SRC_CURRENT_FAIR = DATA / "edgeiq_current_fair_prices_V6_1_RESEARCH_replay.csv"
SRC_V1_REPLAY = DATA / "edgeiq_v6_1_settled_gap_replay_v1.csv"
SRC_V1_SUMMARY = DATA / "edgeiq_v6_1_settled_gap_replay_v1_summary.csv"

OUT_REPLAY = DATA / "edgeiq_v6_1_settled_gap_replay_v2_expanded.csv"
OUT_SUMMARY = DATA / "edgeiq_v6_1_settled_gap_replay_v2_expanded_summary.csv"
OUT_DIAGNOSTICS = DATA / "edgeiq_v6_1_settled_gap_replay_v2_expanded_match_diagnostics.csv"
OUT_ALIAS_AUDIT = DATA / "edgeiq_track_alias_bridge_v1.csv"

JOIN_STAGE_1 = "DATE_TRACK_RACE_NO_HORSE_KEY"
JOIN_STAGE_2 = "DATE_TRACK_RACE_NO_NORMALIZED_HORSE"
JOIN_STAGE_3 = "DATE_TRACK_NORMALIZED_HORSE"
JOIN_STAGE_4 = "DATE_HORSE_KEY"
JOIN_STAGE_NONE = "UNMATCHED"

JOIN_STATUS_BY_STAGE = {
    JOIN_STAGE_1: "MATCHED_V2_DATE_TRACK_RACE_NO_HORSE_KEY",
    JOIN_STAGE_2: "MATCHED_V2_DATE_TRACK_RACE_NO_NORMALIZED_HORSE",
    JOIN_STAGE_3: "MATCHED_V2_DATE_TRACK_NORMALIZED_HORSE",
    JOIN_STAGE_4: "MATCHED_V2_DATE_HORSE_KEY",
    JOIN_STAGE_NONE: "NO_V6_1_BACKTEST_MATCH",
}


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


def to_int(value: object) -> int | None:
    number = to_float(value)
    if number is None:
        return None
    return int(round(number))


def canon_horse(value: object) -> str:
    text = upper(value).replace("â€™", "'").replace("’", "'")
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def norm_track(value: object) -> str:
    text = upper(value)
    for prefix in ["BET365 ", "LADBROKES ", "SPORTSBET ", "SPORTSBET-", "APIAM ", "PICKLEBET PARK ", "THE EXCHANGE "]:
        text = text.replace(prefix, "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compact_track(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", norm_track(value))


def first_existing(columns: list[str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def load_required_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)


def safe_pct(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return (float(numerator) / float(denominator)) * 100.0


def round_num(value: float | None, places: int = 3) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return round(float(value), places)


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
    base["settled_row_id_v2"] = range(1, len(settled) + 1)
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
    base["horse_norm"] = settled[horse_col].map(canon_horse)
    base["track_norm_v2"] = base["track"].map(compact_track)
    base["won"] = pd.to_numeric(settled[won_col], errors="coerce").fillna(0).astype(int)
    base["finish_position"] = pd.to_numeric(settled[finish_col], errors="coerce")
    base["placed"] = ((base["finish_position"] >= 1) & (base["finish_position"] <= 3)).astype(int)
    base["sp"] = settled[sp_col].map(to_float) if sp_col else None

    return base, sp_col or ""


def apply_alias_to_settled(settled_base: pd.DataFrame, alias_map: dict[str, str]) -> pd.DataFrame:
    settled_base = settled_base.copy()
    settled_base["track_canonical_v2"] = settled_base["track"].map(lambda value: apply_track_alias(value, alias_map))
    settled_base["track_norm_v2"] = settled_base["track_canonical_v2"].map(compact_track)
    settled_base["track_alias_applied_v2"] = settled_base.apply(
        lambda row: "YES" if clean(row["track_canonical_v2"]) != norm_track(row["track"]) else "NO",
        axis=1,
    )
    settled_base["key_stage_1"] = (
        settled_base["meeting_date"] + "|" + settled_base["track_norm_v2"] + "|" + settled_base["race_no"] + "|" + settled_base["horse_key"]
    )
    settled_base["key_stage_2"] = (
        settled_base["meeting_date"] + "|" + settled_base["track_norm_v2"] + "|" + settled_base["race_no"] + "|" + settled_base["horse_norm"]
    )
    settled_base["key_stage_3"] = settled_base["meeting_date"] + "|" + settled_base["track_norm_v2"] + "|" + settled_base["horse_norm"]
    settled_base["key_stage_4"] = settled_base["meeting_date"] + "|" + settled_base["horse_key"]
    return settled_base


def load_v61_backtest_raw() -> tuple[pd.DataFrame, int]:
    back = load_required_csv(SRC_V6_BACKTEST)
    back = back[back["model"].map(upper).eq("V6_1_RESEARCH_PRIOR")].copy()
    back["back_row_id_v2"] = range(1, len(back) + 1)
    back["meeting_date"] = back["race_date"].map(clean).str[:10]
    back["backtest_race_key"] = back["race_key"].map(clean)
    back["backtest_horse_key"] = back["horse"].map(canon_horse)
    back["backtest_horse_norm"] = back["horse"].map(canon_horse)
    unique_dedup = int(back.duplicated(subset=["backtest_race_key", "meeting_date", "backtest_horse_key"]).sum())
    if unique_dedup > 0:
        back = back.sort_values(["backtest_race_key", "horse"]).drop_duplicates(
            subset=["backtest_race_key", "meeting_date", "backtest_horse_key"],
            keep="first",
        )
    return back, unique_dedup


def infer_backtest_race_numbers(back: pd.DataFrame, settled_base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    settled_groups = (
        settled_base.groupby(["meeting_date", "track_norm_v2", "race_no"], dropna=False)
        .agg(
            settled_race_key=("race_key", "first"),
            settled_field_size=("horse_key", "count"),
            settled_horse_keys=("horse_key", lambda values: set(value for value in values if clean(value) != "")),
            settled_horse_norms=("horse_norm", lambda values: set(value for value in values if clean(value) != "")),
        )
        .reset_index()
    )

    back_groups = (
        back.groupby(["meeting_date", "track_norm_v2", "backtest_race_key"], dropna=False)
        .agg(
            backtest_field_size=("backtest_horse_key", "count"),
            backtest_horse_keys=("backtest_horse_key", lambda values: set(value for value in values if clean(value) != "")),
            backtest_horse_norms=("backtest_horse_norm", lambda values: set(value for value in values if clean(value) != "")),
        )
        .reset_index()
    )

    mapping_rows: list[dict[str, object]] = []
    for _, back_group in back_groups.iterrows():
        date_value = clean(back_group["meeting_date"])
        track_value = clean(back_group["track_norm_v2"])
        candidates = settled_groups[
            settled_groups["meeting_date"].eq(date_value) & settled_groups["track_norm_v2"].eq(track_value)
        ].copy()

        best_race_no = ""
        best_settled_key = ""
        best_overlap = 0
        best_field_diff = None
        candidate_count = int(len(candidates))
        second_overlap = 0
        mapping_status = "NO_SETTLED_RACE_FOR_DATE_TRACK"

        if candidate_count > 0:
            scored: list[dict[str, object]] = []
            back_horse_keys = back_group["backtest_horse_keys"]
            back_horse_norms = back_group["backtest_horse_norms"]
            back_field_size = to_int(back_group["backtest_field_size"])
            for _, settled_group in candidates.iterrows():
                overlap_keys = len(back_horse_keys.intersection(settled_group["settled_horse_keys"]))
                overlap_norms = len(back_horse_norms.intersection(settled_group["settled_horse_norms"]))
                overlap = max(overlap_keys, overlap_norms)
                settled_field_size = to_int(settled_group["settled_field_size"])
                field_diff = None
                if back_field_size is not None and settled_field_size is not None:
                    field_diff = abs(back_field_size - settled_field_size)
                scored.append(
                    {
                        "race_no": clean(settled_group["race_no"]),
                        "settled_race_key": clean(settled_group["settled_race_key"]),
                        "overlap": overlap,
                        "field_diff": 9999 if field_diff is None else field_diff,
                    }
                )

            scored = sorted(scored, key=lambda row: (-int(row["overlap"]), int(row["field_diff"]), row["race_no"]))
            if scored:
                best = scored[0]
                best_overlap = int(best["overlap"])
                best_field_diff = int(best["field_diff"]) if best["field_diff"] != 9999 else None
                best_race_no = clean(best["race_no"])
                best_settled_key = clean(best["settled_race_key"])
                second_overlap = int(scored[1]["overlap"]) if len(scored) > 1 else 0

                if best_overlap <= 0:
                    mapping_status = "NO_HORSE_OVERLAP"
                    best_race_no = ""
                    best_settled_key = ""
                elif best_overlap >= 2 and best_overlap > second_overlap:
                    mapping_status = "INFERRED_RACE_NO_OVERLAP_2_PLUS"
                elif best_overlap == 1 and candidate_count == 1:
                    mapping_status = "INFERRED_RACE_NO_SOLO_CANDIDATE"
                elif best_overlap == 1 and best_overlap > second_overlap and best_field_diff is not None and best_field_diff <= 1:
                    mapping_status = "INFERRED_RACE_NO_OVERLAP_1_FIELDSIZE_SUPPORT"
                elif best_overlap > second_overlap and best_field_diff is not None and best_field_diff == 0:
                    mapping_status = "INFERRED_RACE_NO_UNIQUE_BEST_FIELDSIZE_TIEBREAKER"
                else:
                    mapping_status = "AMBIGUOUS_RACE_NO_MATCH"
                    best_race_no = ""
                    best_settled_key = ""

        mapping_rows.append(
            {
                "meeting_date": date_value,
                "track_norm_v2": track_value,
                "backtest_race_key": clean(back_group["backtest_race_key"]),
                "backtest_field_size": to_int(back_group["backtest_field_size"]),
                "candidate_settled_races_same_date_track": candidate_count,
                "best_overlap_count": best_overlap,
                "second_best_overlap_count": second_overlap,
                "best_field_size_diff": best_field_diff,
                "inferred_race_no_v2": best_race_no,
                "mapped_settled_race_key_v2": best_settled_key,
                "race_mapping_status_v2": mapping_status,
            }
        )

    mapping_df = pd.DataFrame(mapping_rows)
    back = back.merge(mapping_df, on=["meeting_date", "track_norm_v2", "backtest_race_key"], how="left")
    return back, mapping_df


def build_v61_lookup(back: pd.DataFrame, settled_base: pd.DataFrame, alias_map: dict[str, str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    back = back.copy()
    back["track_canonical_v2"] = back["track"].map(lambda value: apply_track_alias(value, alias_map))
    back["track_norm_v2"] = back["track_canonical_v2"].map(compact_track)
    back["track_alias_applied_v2"] = back.apply(
        lambda row: "YES" if clean(row["track_canonical_v2"]) != norm_track(row["track"]) else "NO",
        axis=1,
    )

    back, mapping_df = infer_backtest_race_numbers(back, settled_base)

    back["projection_gap_V6_1_RESEARCH"] = pd.to_numeric(back["rating_gap"], errors="coerce")
    back["projected_rating_V6_1_RESEARCH"] = pd.to_numeric(back["rating"], errors="coerce")
    back["race_target_rating_V6_1_RESEARCH"] = pd.to_numeric(back["race_median_rating"], errors="coerce")
    back["projection_band_V6_1_RESEARCH"] = back["projection_band"].map(clean)
    back["V6_1_RESEARCH_probability"] = pd.to_numeric(back["model_prob"], errors="coerce")
    back["V6_1_RESEARCH_fair_price"] = pd.to_numeric(back["fair_price"], errors="coerce")

    back["key_stage_1"] = (
        back["meeting_date"] + "|" + back["track_norm_v2"] + "|" + back["inferred_race_no_v2"].map(clean) + "|" + back["backtest_horse_key"]
    )
    back["key_stage_2"] = (
        back["meeting_date"] + "|" + back["track_norm_v2"] + "|" + back["inferred_race_no_v2"].map(clean) + "|" + back["backtest_horse_norm"]
    )
    back["key_stage_3"] = back["meeting_date"] + "|" + back["track_norm_v2"] + "|" + back["backtest_horse_norm"]
    back["key_stage_4"] = back["meeting_date"] + "|" + back["backtest_horse_key"]

    lookup = back[
        [
            "back_row_id_v2",
            "backtest_race_key",
            "meeting_date",
            "track_canonical_v2",
            "track_norm_v2",
            "track_alias_applied_v2",
            "inferred_race_no_v2",
            "mapped_settled_race_key_v2",
            "race_mapping_status_v2",
            "candidate_settled_races_same_date_track",
            "best_overlap_count",
            "second_best_overlap_count",
            "best_field_size_diff",
            "backtest_horse_key",
            "backtest_horse_norm",
            "projection_gap_V6_1_RESEARCH",
            "projected_rating_V6_1_RESEARCH",
            "race_target_rating_V6_1_RESEARCH",
            "projection_band_V6_1_RESEARCH",
            "V6_1_RESEARCH_probability",
            "V6_1_RESEARCH_fair_price",
            "key_stage_1",
            "key_stage_2",
            "key_stage_3",
            "key_stage_4",
        ]
    ].copy()
    return lookup, mapping_df


def key_count_map(lookup: pd.DataFrame, key_column: str) -> dict[str, int]:
    counts = lookup[key_column].value_counts(dropna=False).to_dict()
    return {clean(key): int(value) for key, value in counts.items() if clean(key) != ""}


def assign_matches(settled_base: pd.DataFrame, lookup: pd.DataFrame) -> pd.DataFrame:
    diagnostics = settled_base.copy()
    diagnostics["assigned_back_row_id_v2"] = ""
    diagnostics["source_match_stage_v2"] = JOIN_STAGE_NONE
    diagnostics["source_match_status"] = JOIN_STATUS_BY_STAGE[JOIN_STAGE_NONE]
    diagnostics["match_confidence_v2"] = ""

    stage_key_map = {
        JOIN_STAGE_1: ("key_stage_1", "key_stage_1"),
        JOIN_STAGE_2: ("key_stage_2", "key_stage_2"),
        JOIN_STAGE_3: ("key_stage_3", "key_stage_3"),
        JOIN_STAGE_4: ("key_stage_4", "key_stage_4"),
    }

    diagnostics["candidate_count_stage_1"] = diagnostics["key_stage_1"].map(key_count_map(lookup, "key_stage_1")).fillna(0).astype(int)
    diagnostics["candidate_count_stage_2"] = diagnostics["key_stage_2"].map(key_count_map(lookup, "key_stage_2")).fillna(0).astype(int)
    diagnostics["candidate_count_stage_3"] = diagnostics["key_stage_3"].map(key_count_map(lookup, "key_stage_3")).fillna(0).astype(int)
    diagnostics["candidate_count_stage_4"] = diagnostics["key_stage_4"].map(key_count_map(lookup, "key_stage_4")).fillna(0).astype(int)

    assigned_back_rows: set[int] = set()

    for stage_name, (settled_key_col, back_key_col) in stage_key_map.items():
        unmatched_mask = diagnostics["source_match_stage_v2"].eq(JOIN_STAGE_NONE)
        if not unmatched_mask.any():
            break

        available_lookup = lookup[~lookup["back_row_id_v2"].isin(assigned_back_rows)].copy()
        available_lookup = available_lookup[available_lookup[back_key_col].map(clean).ne("")]
        unique_counts = available_lookup[back_key_col].value_counts()
        unique_keys = set(unique_counts[unique_counts == 1].index.tolist())
        lookup_unique = (
            available_lookup[available_lookup[back_key_col].isin(unique_keys)]
            [[back_key_col, "back_row_id_v2"]]
            .drop_duplicates(subset=[back_key_col], keep="first")
        )
        unique_map = {clean(row[back_key_col]): int(row["back_row_id_v2"]) for _, row in lookup_unique.iterrows()}

        for idx, row in diagnostics[unmatched_mask].iterrows():
            key_value = clean(row[settled_key_col])
            if key_value == "":
                continue
            back_row_id = unique_map.get(key_value)
            if back_row_id is None or back_row_id in assigned_back_rows:
                continue
            assigned_back_rows.add(back_row_id)
            diagnostics.at[idx, "assigned_back_row_id_v2"] = str(back_row_id)
            diagnostics.at[idx, "source_match_stage_v2"] = stage_name
            diagnostics.at[idx, "source_match_status"] = JOIN_STATUS_BY_STAGE[stage_name]
            if stage_name in {JOIN_STAGE_1, JOIN_STAGE_2}:
                diagnostics.at[idx, "match_confidence_v2"] = "HIGH"
            elif stage_name == JOIN_STAGE_3:
                diagnostics.at[idx, "match_confidence_v2"] = "MEDIUM"
            else:
                diagnostics.at[idx, "match_confidence_v2"] = "LOW"

    return diagnostics


def compare_v1_metrics(settled_base: pd.DataFrame) -> tuple[int | None, int | None]:
    if not SRC_V1_REPLAY.exists():
        return None, None
    v1 = pd.read_csv(SRC_V1_REPLAY, dtype=str, keep_default_na=False, low_memory=False)
    matched_status = v1["source_match_status"].map(clean).ne("NO_V6_1_BACKTEST_MATCH")
    matched_rows = int(matched_status.sum())
    race_counts = (
        v1.assign(matched_flag=matched_status.astype(int))
        .groupby("race_key", dropna=False)
        .agg(total_rows=("horse", "count"), matched_rows=("matched_flag", "sum"))
        .reset_index()
    )
    complete_races = int((race_counts["total_rows"] == race_counts["matched_rows"]).sum())
    return matched_rows, complete_races


def build_output() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    settled_base, sp_source_col = build_settled_base()
    back_raw, unique_dedup = load_v61_backtest_raw()
    alias_map, alias_audit = build_track_alias_bridge(settled_base, back_raw)
    settled_base = apply_alias_to_settled(settled_base, alias_map)
    lookup, mapping_df = build_v61_lookup(back_raw, settled_base, alias_map)
    diagnostics = assign_matches(settled_base, lookup)
    diagnostics["assigned_back_row_id_num_v2"] = diagnostics["assigned_back_row_id_v2"].map(
        lambda value: to_int(value) if clean(value) != "" else None
    )
    lookup_reduced = lookup[
        [
            "back_row_id_v2",
            "backtest_race_key",
            "track_canonical_v2",
            "track_alias_applied_v2",
            "inferred_race_no_v2",
            "mapped_settled_race_key_v2",
            "race_mapping_status_v2",
            "candidate_settled_races_same_date_track",
            "best_overlap_count",
            "second_best_overlap_count",
            "best_field_size_diff",
            "projection_gap_V6_1_RESEARCH",
            "projected_rating_V6_1_RESEARCH",
            "race_target_rating_V6_1_RESEARCH",
            "projection_band_V6_1_RESEARCH",
            "V6_1_RESEARCH_probability",
            "V6_1_RESEARCH_fair_price",
        ]
    ].copy().rename(
        columns={
            "track_canonical_v2": "backtest_track_canonical_v2",
            "track_alias_applied_v2": "backtest_track_alias_applied_v2",
        }
    )
    merged = diagnostics.merge(
        lookup_reduced,
        left_on="assigned_back_row_id_num_v2",
        right_on="back_row_id_v2",
        how="left",
    )

    race_match_counts = (
        merged.assign(matched_flag=merged["source_match_stage_v2"].ne(JOIN_STAGE_NONE).astype(int))
        .groupby("race_key", dropna=False)
        .agg(total_rows_in_race=("horse", "count"), matched_rows_in_race=("matched_flag", "sum"))
        .reset_index()
    )
    race_match_counts["complete_match_race_v2"] = race_match_counts["total_rows_in_race"] == race_match_counts["matched_rows_in_race"]
    merged = merged.merge(race_match_counts, on="race_key", how="left")

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
            "source_match_stage_v2",
            "match_confidence_v2",
            "backtest_race_key",
            "inferred_race_no_v2",
            "race_mapping_status_v2",
            "complete_match_race_v2",
        ]
    ].copy()

    diagnostics_out = merged[
        [
            "settled_row_id_v2",
            "race_key",
            "meeting_date",
            "track",
            "track_canonical_v2",
            "track_alias_applied_v2",
            "track_norm_v2",
            "race_no",
            "horse",
            "horse_key",
            "horse_norm",
            "key_stage_1",
            "key_stage_2",
            "key_stage_3",
            "key_stage_4",
            "candidate_count_stage_1",
            "candidate_count_stage_2",
            "candidate_count_stage_3",
            "candidate_count_stage_4",
            "assigned_back_row_id_v2",
            "source_match_stage_v2",
            "source_match_status",
            "match_confidence_v2",
            "backtest_race_key",
            "backtest_track_canonical_v2",
            "backtest_track_alias_applied_v2",
            "inferred_race_no_v2",
            "mapped_settled_race_key_v2",
            "race_mapping_status_v2",
            "candidate_settled_races_same_date_track",
            "best_overlap_count",
            "second_best_overlap_count",
            "best_field_size_diff",
            "complete_match_race_v2",
        ]
    ].copy()

    matched_rows = int(output["source_match_stage_v2"].ne(JOIN_STAGE_NONE).sum())
    unmatched_rows = int(output["source_match_stage_v2"].eq(JOIN_STAGE_NONE).sum())
    matched_races = int(output.loc[output["source_match_stage_v2"].ne(JOIN_STAGE_NONE), "race_key"].nunique())
    total_races = int(output["race_key"].nunique())
    total_rows = int(len(output))
    complete_races = int(race_match_counts["complete_match_race_v2"].sum())
    complete_rows = int(race_match_counts.loc[race_match_counts["complete_match_race_v2"], "matched_rows_in_race"].sum())
    complete_race_dates = sorted({clean(value) for value in output.loc[output["complete_match_race_v2"], "meeting_date"].tolist() if clean(value) != ""})

    mapping_status_counts = mapping_df["race_mapping_status_v2"].value_counts().to_dict()
    stage_counts = output["source_match_stage_v2"].value_counts().to_dict()
    v1_matched_rows, v1_complete_races = compare_v1_metrics(settled_base)
    chosen_alias_rows = alias_audit[alias_audit["chosen"].map(clean).eq("YES")].copy() if not alias_audit.empty else pd.DataFrame()
    dynamic_alias_rows = chosen_alias_rows[chosen_alias_rows["source"].map(clean) != "STATIC_SEED"].copy() if not chosen_alias_rows.empty else pd.DataFrame()

    summary_row = {
        "status": "EDGEIQ_V6_1_SETTLED_GAP_REPLAY_V2_EXPANDED_BUILT",
        "settled_source": SRC_SETTLED.name,
        "v6_1_source": SRC_V6_BACKTEST.name,
        "supporting_source_historical_v6": SRC_HIST_V6.name if SRC_HIST_V6.exists() else "",
        "supporting_source_current_fair_replay": SRC_CURRENT_FAIR.name if SRC_CURRENT_FAIR.exists() else "",
        "supporting_source_v1_replay": SRC_V1_REPLAY.name if SRC_V1_REPLAY.exists() else "",
        "sp_source_col_used": sp_source_col,
        "backtest_model_used": "V6_1_RESEARCH_PRIOR",
        "join_stage_1": JOIN_STAGE_1,
        "join_stage_2": JOIN_STAGE_2,
        "join_stage_3": JOIN_STAGE_3,
        "join_stage_4": JOIN_STAGE_4,
        "settled_rows": total_rows,
        "settled_races": total_races,
        "v6_1_backtest_rows_filtered": int(len(lookup)),
        "matched_rows": matched_rows,
        "unmatched_rows": unmatched_rows,
        "matched_pct": round_num(safe_pct(matched_rows, total_rows), 3),
        "matched_races": matched_races,
        "complete_matched_races": complete_races,
        "complete_matched_rows": complete_rows,
        "complete_match_race_pct": round_num(safe_pct(complete_races, total_races), 3),
        "complete_match_row_pct": round_num(safe_pct(complete_rows, total_rows), 3),
        "matched_rows_stage_1": int(stage_counts.get(JOIN_STAGE_1, 0)),
        "matched_rows_stage_2": int(stage_counts.get(JOIN_STAGE_2, 0)),
        "matched_rows_stage_3": int(stage_counts.get(JOIN_STAGE_3, 0)),
        "matched_rows_stage_4": int(stage_counts.get(JOIN_STAGE_4, 0)),
        "unmatched_rows_stage_none": int(stage_counts.get(JOIN_STAGE_NONE, 0)),
        "backtest_races_inferred_overlap_2_plus": int(mapping_status_counts.get("INFERRED_RACE_NO_OVERLAP_2_PLUS", 0)),
        "backtest_races_inferred_overlap_1_fieldsize_support": int(mapping_status_counts.get("INFERRED_RACE_NO_OVERLAP_1_FIELDSIZE_SUPPORT", 0)),
        "backtest_races_inferred_unique_best_fieldsize_tiebreaker": int(mapping_status_counts.get("INFERRED_RACE_NO_UNIQUE_BEST_FIELDSIZE_TIEBREAKER", 0)),
        "backtest_races_inferred_solo_candidate": int(mapping_status_counts.get("INFERRED_RACE_NO_SOLO_CANDIDATE", 0)),
        "backtest_races_ambiguous": int(mapping_status_counts.get("AMBIGUOUS_RACE_NO_MATCH", 0)),
        "backtest_races_no_overlap": int(mapping_status_counts.get("NO_HORSE_OVERLAP", 0)),
        "track_alias_bridge_rows_chosen": int(len(chosen_alias_rows)),
        "track_alias_bridge_dynamic_rows_chosen": int(len(dynamic_alias_rows)),
        "settled_rows_with_alias_applied_v2": int(settled_base["track_alias_applied_v2"].eq("YES").sum()),
        "backtest_rows_with_alias_applied_v2": int(lookup["track_alias_applied_v2"].eq("YES").sum()),
        "duplicate_backtest_rows_removed": unique_dedup,
        "v1_matched_rows": v1_matched_rows,
        "v1_complete_matched_races": v1_complete_races,
        "delta_vs_v1_matched_rows": None if v1_matched_rows is None else matched_rows - v1_matched_rows,
        "delta_vs_v1_complete_matched_races": None if v1_complete_races is None else complete_races - v1_complete_races,
        "complete_match_date_min": complete_race_dates[0] if complete_race_dates else "",
        "complete_match_date_max": complete_race_dates[-1] if complete_race_dates else "",
        "built_at": datetime.now(timezone.utc).isoformat(),
    }

    summary = pd.DataFrame([summary_row])
    if not alias_audit.empty:
        alias_audit.to_csv(OUT_ALIAS_AUDIT, index=False)
    else:
        pd.DataFrame(columns=["alias_key", "canonical_track", "rows", "second_rows", "source", "chosen"]).to_csv(OUT_ALIAS_AUDIT, index=False)
    return output, summary, diagnostics_out


def print_section(title: str, frame: pd.DataFrame) -> None:
    print("")
    print(title)
    if frame.empty:
        print("(no rows)")
        return
    print(frame.to_string(index=False))


def main() -> None:
    output, summary, diagnostics = build_output()
    output.to_csv(OUT_REPLAY, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    diagnostics.to_csv(OUT_DIAGNOSTICS, index=False)

    print("[V6_1_SETTLED_GAP_REPLAY_V2_EXPANDED] COMPLETE")
    print_section("SUMMARY", summary)
    print_section(
        "MATCH STAGE COUNTS",
        output.groupby("source_match_stage_v2").size().reset_index(name="rows").sort_values("rows", ascending=False),
    )
    print_section(
        "RACE MAPPING STATUS",
        diagnostics.groupby("race_mapping_status_v2").size().reset_index(name="rows").sort_values("rows", ascending=False),
    )


if __name__ == "__main__":
    main()
