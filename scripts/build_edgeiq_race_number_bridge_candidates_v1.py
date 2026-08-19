from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import math
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC_EXPANDED = DATA / "edgeiq_v6_1_settled_gap_replay_v2_expanded.csv"
SRC_DIAGNOSTICS = DATA / "edgeiq_v6_1_settled_gap_replay_v2_expanded_match_diagnostics.csv"
SRC_ALIAS = DATA / "edgeiq_track_alias_bridge_v1.csv"
SRC_SETTLED = DATA / "edgeiq_historical_replay_settled_v1.csv"
SRC_V6_BACKTEST = DATA / "edgeiq_projection_v6_1_research_prior_rating_backtest.csv"

OUT_CANDIDATES = DATA / "edgeiq_race_number_bridge_candidates_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_race_number_bridge_candidates_v1_summary.csv"

MODEL_FILTER = "V6_1_RESEARCH_PRIOR"


def clean(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def upper(value: object) -> str:
    return clean(value).upper()


def canon_horse(value: object) -> str:
    text = upper(value).replace("ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢", "'").replace("Ã¢â‚¬â„¢", "'").replace("â€™", "'")
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def compact_token(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", upper(value))


def base_track_name(value: object) -> str:
    text = upper(value).replace("-", " ")
    for prefix in [
        "BET365 ",
        "LADBROKES ",
        "SPORTSBET ",
        "SPORTSBET-",
        "APIAM ",
        "SOUTHSIDE ",
        "PICKLEBET PARK ",
        "BET365 PARK ",
        "THE EXCHANGE ",
    ]:
        if text.startswith(prefix):
            text = text[len(prefix):]
    text = re.sub(r"\s+", " ", text).strip()
    if text.endswith(" PICNIC"):
        text = text[: -len(" PICNIC")].strip()
    return text


def apply_track_alias(value: object, alias_map: dict[str, str]) -> str:
    raw = upper(value).replace("-", " ")
    base = base_track_name(value)
    keys = []
    for key in [raw, base, compact_token(raw), compact_token(base)]:
        key = clean(key)
        if key != "" and key not in keys:
            keys.append(key)
    for key in keys:
        if key in alias_map and clean(alias_map[key]) != "":
            return clean(alias_map[key])
    return base


def first_existing(columns: list[str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def load_required_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)


def to_int(value: object) -> int | None:
    text = clean(value)
    if text == "":
        return None
    try:
        number = float(text)
    except Exception:
        return None
    if not math.isfinite(number):
        return None
    return int(round(number))


def safe_pct(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round((float(numerator) / float(denominator)) * 100.0, 3)


def round_num(value: float | None, places: int = 3) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return round(float(value), places)


def pick_first_non_empty(series: pd.Series) -> str:
    for value in series:
        text = clean(value)
        if text != "":
            return text
    return ""


def sort_race_no_key(value: object) -> tuple[int, str]:
    text = clean(value)
    if text == "":
        return (9999, "")
    parsed = to_int(text)
    if parsed is not None:
        return (parsed, text)
    return (9999, text)


def load_alias_map() -> dict[str, str]:
    alias = load_required_csv(SRC_ALIAS)
    alias = alias[alias["chosen"].map(upper).eq("YES")].copy()
    alias_map: dict[str, str] = {}
    for _, row in alias.iterrows():
        key = clean(row.get("alias_key", ""))
        canonical = clean(row.get("canonical_track", ""))
        if key != "" and canonical != "":
            alias_map[key] = canonical
    return alias_map


def build_settled_groups(alias_map: dict[str, str]) -> pd.DataFrame:
    settled = load_required_csv(SRC_SETTLED)
    columns = list(settled.columns)

    race_key_col = first_existing(columns, ["race_key"])
    date_col = first_existing(columns, ["meeting_date", "race_date"])
    track_col = first_existing(columns, ["track"])
    race_no_col = first_existing(columns, ["race_no"])
    horse_col = first_existing(columns, ["horse"])
    horse_key_col = first_existing(columns, ["horse_key"])

    missing = []
    for label, col in [
        ("race_key", race_key_col),
        ("meeting_date/race_date", date_col),
        ("track", track_col),
        ("race_no", race_no_col),
        ("horse", horse_col),
    ]:
        if col is None:
            missing.append(label)
    if missing:
        raise RuntimeError(f"Missing required settled columns: {missing}")

    frame = pd.DataFrame()
    frame["meeting_date"] = settled[date_col].map(clean).str[:10]
    frame["track_raw_v1"] = settled[track_col].map(clean)
    frame["canonical_track_v1"] = frame["track_raw_v1"].map(lambda value: apply_track_alias(value, alias_map))
    frame["settled_race_no_v1"] = settled[race_no_col].map(clean)
    frame["settled_race_key_v1"] = settled[race_key_col].map(clean)
    frame["horse_key_v1"] = (
        settled[horse_key_col].where(settled[horse_key_col].map(clean).ne(""), settled[horse_col].map(canon_horse))
        if horse_key_col
        else settled[horse_col].map(canon_horse)
    ).map(canon_horse)

    groups = (
        frame.groupby(["meeting_date", "canonical_track_v1", "settled_race_no_v1"], dropna=False)
        .agg(
            settled_race_key_v1=("settled_race_key_v1", "first"),
            settled_field_size_v1=("horse_key_v1", lambda values: len({clean(v) for v in values if clean(v) != ""})),
            settled_horse_keys_v1=("horse_key_v1", lambda values: sorted({clean(v) for v in values if clean(v) != ""})),
        )
        .reset_index()
    )
    return groups


def build_backtest_groups(alias_map: dict[str, str]) -> pd.DataFrame:
    back = load_required_csv(SRC_V6_BACKTEST)
    back = back[back["model"].map(upper).eq(MODEL_FILTER)].copy()
    if back.empty:
        raise RuntimeError(f"No rows found for model={MODEL_FILTER} in {SRC_V6_BACKTEST}")

    frame = pd.DataFrame()
    frame["meeting_date"] = back["race_date"].map(clean).str[:10]
    frame["track_raw_v1"] = back["track"].map(clean)
    frame["canonical_track_v1"] = frame["track_raw_v1"].map(lambda value: apply_track_alias(value, alias_map))
    frame["v6_backtest_race_key_v1"] = back["race_key"].map(clean)
    frame["horse_key_v1"] = back["horse"].map(canon_horse)

    groups = (
        frame.groupby(["meeting_date", "canonical_track_v1", "v6_backtest_race_key_v1"], dropna=False)
        .agg(
            v6_field_size_v1=("horse_key_v1", lambda values: len({clean(v) for v in values if clean(v) != ""})),
            v6_horse_keys_v1=("horse_key_v1", lambda values: sorted({clean(v) for v in values if clean(v) != ""})),
        )
        .reset_index()
    )
    groups = groups.sort_values(["meeting_date", "canonical_track_v1", "v6_backtest_race_key_v1"]).reset_index(drop=True)
    groups["v6_race_slot_v1"] = groups.groupby(["meeting_date", "canonical_track_v1"], dropna=False).cumcount() + 1
    return groups


def load_v2_context() -> tuple[pd.DataFrame, pd.DataFrame]:
    expanded = load_required_csv(SRC_EXPANDED)
    diagnostics = load_required_csv(SRC_DIAGNOSTICS)

    diag = diagnostics[diagnostics["backtest_race_key"].map(clean).ne("")].copy()
    if diag.empty:
        diag_grouped = pd.DataFrame(
            columns=[
                "meeting_date",
                "canonical_track_v1",
                "v6_backtest_race_key_v1",
                "v6_inferred_race_no_v2",
                "v6_race_mapping_status_v2",
                "v6_mapped_settled_race_key_v2",
                "v6_diag_rows_v2",
            ]
        )
    else:
        track_col = "backtest_track_canonical_v2" if "backtest_track_canonical_v2" in diag.columns else "track_canonical_v2"
        diag_grouped = (
            diag.groupby(["meeting_date", track_col, "backtest_race_key"], dropna=False)
            .agg(
                v6_inferred_race_no_v2=("inferred_race_no_v2", pick_first_non_empty),
                v6_race_mapping_status_v2=("race_mapping_status_v2", pick_first_non_empty),
                v6_mapped_settled_race_key_v2=("mapped_settled_race_key_v2", pick_first_non_empty),
                v6_diag_rows_v2=("backtest_race_key", "size"),
            )
            .reset_index()
            .rename(
                columns={
                    track_col: "canonical_track_v1",
                    "backtest_race_key": "v6_backtest_race_key_v1",
                }
            )
        )

    expanded_back = expanded[expanded["backtest_race_key"].map(clean).ne("")].copy()
    if expanded_back.empty:
        expanded_grouped = pd.DataFrame(
            columns=[
                "meeting_date",
                "canonical_track_v1",
                "v6_backtest_race_key_v1",
                "v2_rows_for_backtest_race_v1",
                "v2_complete_match_race_v1",
            ]
        )
    else:
        expanded_grouped = (
            expanded_back.groupby(["meeting_date", "track", "backtest_race_key"], dropna=False)
            .agg(
                v2_rows_for_backtest_race_v1=("backtest_race_key", "size"),
                v2_complete_match_race_v1=("complete_match_race_v2", lambda values: "YES" if any(upper(v) == "TRUE" for v in values) else "NO"),
            )
            .reset_index()
            .rename(
                columns={
                    "track": "canonical_track_v1",
                    "backtest_race_key": "v6_backtest_race_key_v1",
                }
            )
        )

    return diag_grouped, expanded_grouped


def classify_confidence(overlap_count: int, overlap_pct_min: float | None) -> str:
    pct = overlap_pct_min or 0.0
    if overlap_count >= 5 and pct >= 70.0:
        return "HIGH"
    if overlap_count >= 3 and pct >= 50.0:
        return "MEDIUM"
    return "LOW"


def build_candidates(
    settled_groups: pd.DataFrame,
    back_groups: pd.DataFrame,
    diag_grouped: pd.DataFrame,
    expanded_grouped: pd.DataFrame,
) -> pd.DataFrame:
    back_context = back_groups.merge(
        diag_grouped,
        on=["meeting_date", "canonical_track_v1", "v6_backtest_race_key_v1"],
        how="left",
    ).merge(
        expanded_grouped,
        on=["meeting_date", "canonical_track_v1", "v6_backtest_race_key_v1"],
        how="left",
    )

    settled_lookup: dict[tuple[str, str], list[dict[str, object]]] = {}
    for _, row in settled_groups.iterrows():
        key = (clean(row["meeting_date"]), clean(row["canonical_track_v1"]))
        settled_lookup.setdefault(key, []).append(
            {
                "settled_race_no_v1": clean(row["settled_race_no_v1"]),
                "settled_race_key_v1": clean(row["settled_race_key_v1"]),
                "settled_field_size_v1": to_int(row["settled_field_size_v1"]) or 0,
                "settled_horse_keys_v1": set(row["settled_horse_keys_v1"]),
            }
        )

    back_lookup: dict[tuple[str, str], list[dict[str, object]]] = {}
    for _, row in back_context.iterrows():
        key = (clean(row["meeting_date"]), clean(row["canonical_track_v1"]))
        back_lookup.setdefault(key, []).append(
            {
                "v6_backtest_race_key_v1": clean(row["v6_backtest_race_key_v1"]),
                "v6_field_size_v1": to_int(row["v6_field_size_v1"]) or 0,
                "v6_horse_keys_v1": set(row["v6_horse_keys_v1"]),
                "v6_race_slot_v1": to_int(row["v6_race_slot_v1"]) or 0,
                "v6_inferred_race_no_v2": clean(row.get("v6_inferred_race_no_v2", "")),
                "v6_race_mapping_status_v2": clean(row.get("v6_race_mapping_status_v2", "")),
                "v6_mapped_settled_race_key_v2": clean(row.get("v6_mapped_settled_race_key_v2", "")),
                "v6_diag_rows_v2": to_int(row.get("v6_diag_rows_v2", "")) or 0,
                "v2_rows_for_backtest_race_v1": to_int(row.get("v2_rows_for_backtest_race_v1", "")) or 0,
                "v2_complete_match_race_v1": clean(row.get("v2_complete_match_race_v1", "")),
            }
        )

    rows: list[dict[str, object]] = []
    built_at = datetime.now(timezone.utc).isoformat()
    shared_keys = sorted(set(settled_lookup.keys()).intersection(set(back_lookup.keys())))
    for meeting_date, canonical_track in shared_keys:
        settled_races = sorted(
            settled_lookup[(meeting_date, canonical_track)],
            key=lambda row: sort_race_no_key(row["settled_race_no_v1"]),
        )
        v6_races = sorted(
            back_lookup[(meeting_date, canonical_track)],
            key=lambda row: (row["v6_race_slot_v1"], row["v6_backtest_race_key_v1"]),
        )
        for settled_row in settled_races:
            for v6_row in v6_races:
                overlap_horses = sorted(settled_row["settled_horse_keys_v1"].intersection(v6_row["v6_horse_keys_v1"]))
                overlap_count = len(overlap_horses)
                if overlap_count <= 0:
                    continue
                settled_size = int(settled_row["settled_field_size_v1"])
                v6_size = int(v6_row["v6_field_size_v1"])
                settled_pct = safe_pct(overlap_count, settled_size)
                v6_pct = safe_pct(overlap_count, v6_size)
                overlap_pct_min = None
                overlap_pct_avg = None
                if settled_pct is not None and v6_pct is not None:
                    overlap_pct_min = min(settled_pct, v6_pct)
                    overlap_pct_avg = round((settled_pct + v6_pct) / 2.0, 3)
                confidence = classify_confidence(overlap_count, overlap_pct_min)
                field_diff = abs(settled_size - v6_size)
                rows.append(
                    {
                        "meeting_date": meeting_date,
                        "canonical_track_v1": canonical_track,
                        "settled_race_no_v1": settled_row["settled_race_no_v1"],
                        "settled_race_key_v1": settled_row["settled_race_key_v1"],
                        "settled_field_size_v1": settled_size,
                        "v6_race_slot_v1": v6_row["v6_race_slot_v1"],
                        "v6_backtest_race_key_v1": v6_row["v6_backtest_race_key_v1"],
                        "v6_field_size_v1": v6_size,
                        "v6_inferred_race_no_v2": v6_row["v6_inferred_race_no_v2"],
                        "v6_race_mapping_status_v2": v6_row["v6_race_mapping_status_v2"],
                        "v6_mapped_settled_race_key_v2": v6_row["v6_mapped_settled_race_key_v2"],
                        "v6_diag_rows_v2": v6_row["v6_diag_rows_v2"],
                        "v2_rows_for_backtest_race_v1": v6_row["v2_rows_for_backtest_race_v1"],
                        "v2_complete_match_race_v1": v6_row["v2_complete_match_race_v1"],
                        "overlap_count_v1": overlap_count,
                        "settled_overlap_pct_v1": settled_pct,
                        "v6_overlap_pct_v1": v6_pct,
                        "overlap_pct_min_v1": overlap_pct_min,
                        "overlap_pct_avg_v1": overlap_pct_avg,
                        "field_size_diff_v1": field_diff,
                        "overlap_horse_keys_sample_v1": "|".join(overlap_horses[:12]),
                        "overlap_horse_count_sample_v1": min(overlap_count, 12),
                        "confidence_v1": confidence,
                        "built_at_v1": built_at,
                    }
                )

    if not rows:
        raise RuntimeError("No settled/V6 race overlap candidates were found.")

    candidates = pd.DataFrame(rows)
    candidates = candidates.sort_values(
        [
            "meeting_date",
            "canonical_track_v1",
            "settled_race_no_v1",
            "overlap_count_v1",
            "overlap_pct_min_v1",
            "field_size_diff_v1",
            "v6_race_slot_v1",
        ],
        ascending=[True, True, True, False, False, True, True],
    ).reset_index(drop=True)
    candidates["candidate_rank_within_settled_v1"] = (
        candidates.groupby(["meeting_date", "canonical_track_v1", "settled_race_no_v1"], dropna=False).cumcount() + 1
    )

    candidates = candidates.sort_values(
        [
            "meeting_date",
            "canonical_track_v1",
            "v6_backtest_race_key_v1",
            "overlap_count_v1",
            "overlap_pct_min_v1",
            "field_size_diff_v1",
            "settled_race_no_v1",
        ],
        ascending=[True, True, True, False, False, True, True],
    ).reset_index(drop=True)
    candidates["candidate_rank_within_v6_v1"] = (
        candidates.groupby(["meeting_date", "canonical_track_v1", "v6_backtest_race_key_v1"], dropna=False).cumcount() + 1
    )

    candidates["high_medium_flag_v1"] = candidates["confidence_v1"].isin(["HIGH", "MEDIUM"]).map(lambda value: "YES" if value else "NO")

    settled_counts = (
        candidates[candidates["high_medium_flag_v1"].eq("YES")]
        .groupby(["meeting_date", "canonical_track_v1", "settled_race_no_v1"], dropna=False)
        .size()
        .reset_index(name="settled_high_medium_candidate_count_v1")
    )
    v6_counts = (
        candidates[candidates["high_medium_flag_v1"].eq("YES")]
        .groupby(["meeting_date", "canonical_track_v1", "v6_backtest_race_key_v1"], dropna=False)
        .size()
        .reset_index(name="v6_high_medium_candidate_count_v1")
    )

    candidates = candidates.merge(
        settled_counts,
        on=["meeting_date", "canonical_track_v1", "settled_race_no_v1"],
        how="left",
    ).merge(
        v6_counts,
        on=["meeting_date", "canonical_track_v1", "v6_backtest_race_key_v1"],
        how="left",
    )
    candidates["settled_high_medium_candidate_count_v1"] = candidates["settled_high_medium_candidate_count_v1"].fillna(0).astype(int)
    candidates["v6_high_medium_candidate_count_v1"] = candidates["v6_high_medium_candidate_count_v1"].fillna(0).astype(int)

    candidates["mutual_best_flag_v1"] = (
        candidates["candidate_rank_within_settled_v1"].eq(1) & candidates["candidate_rank_within_v6_v1"].eq(1)
    ).map(lambda value: "YES" if value else "NO")
    candidates["settled_conflict_flag_v1"] = candidates["settled_high_medium_candidate_count_v1"].gt(1).map(lambda value: "YES" if value else "NO")
    candidates["v6_conflict_flag_v1"] = candidates["v6_high_medium_candidate_count_v1"].gt(1).map(lambda value: "YES" if value else "NO")

    def conflict_type(row: pd.Series) -> str:
        if row["settled_conflict_flag_v1"] == "YES" and row["v6_conflict_flag_v1"] == "YES":
            return "MANY_TO_MANY_CONFLICT"
        if row["settled_conflict_flag_v1"] == "YES":
            return "SETTLED_TO_MULTIPLE_V6"
        if row["v6_conflict_flag_v1"] == "YES":
            return "MULTIPLE_SETTLED_TO_V6"
        if row["mutual_best_flag_v1"] == "YES":
            return "NONE"
        if int(row["candidate_rank_within_settled_v1"]) == 1:
            return "V6_PREFERS_OTHER_SETTLED"
        if int(row["candidate_rank_within_v6_v1"]) == 1:
            return "SETTLED_PREFERS_OTHER_V6"
        return "SECONDARY_CANDIDATE"

    candidates["conflict_type_v1"] = candidates.apply(conflict_type, axis=1)

    def bridge_use_flag(row: pd.Series) -> str:
        if row["confidence_v1"] == "HIGH" and row["mutual_best_flag_v1"] == "YES" and row["conflict_type_v1"] == "NONE":
            return "USE_HIGH"
        if row["confidence_v1"] == "MEDIUM" and row["mutual_best_flag_v1"] == "YES" and row["conflict_type_v1"] == "NONE":
            return "USE_MEDIUM"
        if row["confidence_v1"] in ["HIGH", "MEDIUM"]:
            return "REVIEW"
        return "IGNORE"

    candidates["bridge_use_flag_v1"] = candidates.apply(bridge_use_flag, axis=1)
    candidates["estimated_recoverable_rows_v1"] = candidates.apply(
        lambda row: int(row["overlap_count_v1"]) if clean(row["bridge_use_flag_v1"]).startswith("USE_") else 0,
        axis=1,
    )
    candidates["current_v2_alignment_v1"] = candidates.apply(
        lambda row: "CURRENT_V2_SAME"
        if clean(row["v6_inferred_race_no_v2"]) != "" and clean(row["v6_inferred_race_no_v2"]) == clean(row["settled_race_no_v1"])
        else ("CURRENT_V2_DIFFERENT" if clean(row["v6_inferred_race_no_v2"]) != "" else "CURRENT_V2_UNMAPPED"),
        axis=1,
    )
    candidates["notes_v1"] = candidates.apply(
        lambda row: "V6 source has no native race_no; bridge maps settled_race_no to backtest_race_key using horse overlap",
        axis=1,
    )

    candidates = candidates.sort_values(
        [
            "bridge_use_flag_v1",
            "confidence_v1",
            "overlap_count_v1",
            "overlap_pct_min_v1",
            "meeting_date",
            "canonical_track_v1",
            "settled_race_no_v1",
            "v6_race_slot_v1",
        ],
        ascending=[True, True, False, False, True, True, True, True],
    ).reset_index(drop=True)
    return candidates


def build_summary(candidates: pd.DataFrame, settled_groups: pd.DataFrame, back_groups: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    def add_row(
        section: str,
        rank_v1: int,
        label: str,
        value: object,
        meeting_date: str = "",
        canonical_track_v1: str = "",
        settled_race_no_v1: str = "",
        v6_backtest_race_key_v1: str = "",
        notes: str = "",
    ) -> None:
        rows.append(
            {
                "section": section,
                "rank_v1": rank_v1,
                "label": label,
                "value": value,
                "meeting_date": meeting_date,
                "canonical_track_v1": canonical_track_v1,
                "settled_race_no_v1": settled_race_no_v1,
                "v6_backtest_race_key_v1": v6_backtest_race_key_v1,
                "notes": notes,
            }
        )

    add_row("OVERALL", 1, "candidate_rows", int(len(candidates)))
    add_row("OVERALL", 2, "settled_races_scanned", int(len(settled_groups)))
    add_row("OVERALL", 3, "v6_races_scanned", int(len(back_groups)))
    add_row(
        "OVERALL",
        4,
        "date_track_groups_with_candidates",
        int(candidates[["meeting_date", "canonical_track_v1"]].drop_duplicates().shape[0]),
    )
    add_row("OVERALL", 5, "high_candidates", int(candidates["confidence_v1"].eq("HIGH").sum()))
    add_row("OVERALL", 6, "medium_candidates", int(candidates["confidence_v1"].eq("MEDIUM").sum()))
    add_row("OVERALL", 7, "low_candidates", int(candidates["confidence_v1"].eq("LOW").sum()))
    add_row("OVERALL", 8, "use_high_candidates", int(candidates["bridge_use_flag_v1"].eq("USE_HIGH").sum()))
    add_row("OVERALL", 9, "use_medium_candidates", int(candidates["bridge_use_flag_v1"].eq("USE_MEDIUM").sum()))
    add_row("OVERALL", 10, "review_candidates", int(candidates["bridge_use_flag_v1"].eq("REVIEW").sum()))
    add_row("OVERALL", 11, "ignore_candidates", int(candidates["bridge_use_flag_v1"].eq("IGNORE").sum()))
    add_row("OVERALL", 12, "mutual_best_candidates", int(candidates["mutual_best_flag_v1"].eq("YES").sum()))
    add_row("OVERALL", 13, "settled_conflict_candidates", int(candidates["settled_conflict_flag_v1"].eq("YES").sum()))
    add_row("OVERALL", 14, "v6_conflict_candidates", int(candidates["v6_conflict_flag_v1"].eq("YES").sum()))
    add_row("OVERALL", 15, "estimated_recoverable_rows_use_only", int(candidates["estimated_recoverable_rows_v1"].sum()))
    add_row(
        "OVERALL",
        16,
        "v6_native_race_no_present",
        "NO",
        notes="bridge is keyed to backtest_race_key and current inferred_race_no_v2 because source backtest has no native race_no column",
    )

    confidence_counts = (
        candidates.groupby("confidence_v1", dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(["rows", "confidence_v1"], ascending=[False, True])
    )
    for idx, (_, row) in enumerate(confidence_counts.iterrows(), start=1):
        add_row("CONFIDENCE_COUNT", idx, "rows", int(row["rows"]), notes=clean(row["confidence_v1"]))

    use_counts = (
        candidates.groupby("bridge_use_flag_v1", dropna=False)
        .agg(rows=("bridge_use_flag_v1", "size"), recoverable_rows=("estimated_recoverable_rows_v1", "sum"))
        .reset_index()
        .sort_values(["recoverable_rows", "rows", "bridge_use_flag_v1"], ascending=[False, False, True])
    )
    for idx, (_, row) in enumerate(use_counts.iterrows(), start=1):
        add_row(
            "BRIDGE_USE_COUNT",
            idx,
            "recoverable_rows",
            int(row["recoverable_rows"]),
            notes=f"{clean(row['bridge_use_flag_v1'])} rows={int(row['rows'])}",
        )

    conflict_counts = (
        candidates.groupby("conflict_type_v1", dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(["rows", "conflict_type_v1"], ascending=[False, True])
    )
    for idx, (_, row) in enumerate(conflict_counts.iterrows(), start=1):
        add_row("CONFLICT_COUNT", idx, "rows", int(row["rows"]), notes=clean(row["conflict_type_v1"]))

    top_tracks = (
        candidates.groupby("canonical_track_v1", dropna=False)
        .agg(
            candidate_rows=("canonical_track_v1", "size"),
            recoverable_rows=("estimated_recoverable_rows_v1", "sum"),
        )
        .reset_index()
        .sort_values(["recoverable_rows", "candidate_rows", "canonical_track_v1"], ascending=[False, False, True])
        .head(20)
    )
    for idx, (_, row) in enumerate(top_tracks.iterrows(), start=1):
        add_row(
            "TOP_TRACK",
            idx,
            "recoverable_rows",
            int(row["recoverable_rows"]),
            canonical_track_v1=clean(row["canonical_track_v1"]),
            notes=f"candidate_rows={int(row['candidate_rows'])}",
        )

    top_dates = (
        candidates.groupby("meeting_date", dropna=False)
        .agg(
            candidate_rows=("meeting_date", "size"),
            recoverable_rows=("estimated_recoverable_rows_v1", "sum"),
        )
        .reset_index()
        .sort_values(["recoverable_rows", "candidate_rows", "meeting_date"], ascending=[False, False, True])
        .head(20)
    )
    for idx, (_, row) in enumerate(top_dates.iterrows(), start=1):
        add_row(
            "TOP_DATE",
            idx,
            "recoverable_rows",
            int(row["recoverable_rows"]),
            meeting_date=clean(row["meeting_date"]),
            notes=f"candidate_rows={int(row['candidate_rows'])}",
        )

    top_bridges = (
        candidates[candidates["bridge_use_flag_v1"].isin(["USE_HIGH", "USE_MEDIUM"])]
        .sort_values(
            ["estimated_recoverable_rows_v1", "overlap_pct_min_v1", "meeting_date", "canonical_track_v1", "settled_race_no_v1"],
            ascending=[False, False, True, True, True],
        )
        .head(30)
    )
    for idx, (_, row) in enumerate(top_bridges.iterrows(), start=1):
        add_row(
            "TOP_BRIDGE",
            idx,
            clean(row["bridge_use_flag_v1"]),
            int(row["estimated_recoverable_rows_v1"]),
            meeting_date=clean(row["meeting_date"]),
            canonical_track_v1=clean(row["canonical_track_v1"]),
            settled_race_no_v1=clean(row["settled_race_no_v1"]),
            v6_backtest_race_key_v1=clean(row["v6_backtest_race_key_v1"]),
            notes=(
                f"confidence={clean(row['confidence_v1'])} "
                f"overlap={int(row['overlap_count_v1'])} "
                f"min_pct={round_num(row['overlap_pct_min_v1'], 3)} "
                f"current_v2={clean(row['current_v2_alignment_v1'])}"
            ),
        )

    return pd.DataFrame(rows)


def main() -> None:
    alias_map = load_alias_map()
    settled_groups = build_settled_groups(alias_map)
    back_groups = build_backtest_groups(alias_map)
    diag_grouped, expanded_grouped = load_v2_context()
    candidates = build_candidates(settled_groups, back_groups, diag_grouped, expanded_grouped)
    summary = build_summary(candidates, settled_groups, back_groups)

    candidates.to_csv(OUT_CANDIDATES, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)

    overall = summary[summary["section"].eq("OVERALL")].copy()
    top_bridge = summary[summary["section"].eq("TOP_BRIDGE")].head(20).copy()

    print("[EDGEIQ_RACE_NUMBER_BRIDGE_CANDIDATES_V1] COMPLETE")
    print(overall.to_string(index=False))
    if not top_bridge.empty:
        print(top_bridge.to_string(index=False))
    print(f"wrote={OUT_CANDIDATES}")
    print(f"wrote={OUT_SUMMARY}")


if __name__ == "__main__":
    main()
