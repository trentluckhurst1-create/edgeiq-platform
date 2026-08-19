from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import math
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC_BRIDGE = DATA / "edgeiq_race_number_bridge_candidates_v1.csv"
SRC_DIAG = DATA / "edgeiq_v6_1_settled_gap_replay_v2_expanded_match_diagnostics.csv"
SRC_COLLISIONS = DATA / "edgeiq_v6_1_settled_replay_unmatched_collisions_v1.csv"
SRC_ALIAS = DATA / "edgeiq_track_alias_bridge_v1.csv"
SRC_SETTLED = DATA / "edgeiq_historical_replay_settled_v1.csv"
SRC_BACKTEST = DATA / "edgeiq_projection_v6_1_research_prior_rating_backtest.csv"

OUT_AUDIT = DATA / "edgeiq_race_identity_conflicts_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_race_identity_conflicts_v1_summary.csv"
OUT_EXAMPLES = DATA / "edgeiq_race_identity_conflicts_v1_examples.csv"

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


def to_float(value: object) -> float | None:
    text = clean(value)
    if text == "":
        return None
    try:
        number = float(text)
    except Exception:
        return None
    if not math.isfinite(number):
        return None
    return float(number)


def round_num(value: float | None, places: int = 3) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return round(float(value), places)


def safe_pct(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round((float(numerator) / float(denominator)) * 100.0, 3)


def join_list(values: list[str], max_items: int = 20) -> str:
    seen: list[str] = []
    for value in values:
        text = clean(value)
        if text != "" and text not in seen:
            seen.append(text)
    return "|".join(seen[:max_items])


def sort_race_no_key(value: object) -> tuple[int, str]:
    text = clean(value)
    if text == "":
        return (9999, "")
    parsed = to_int(text)
    if parsed is not None:
        return (parsed, text)
    return (9999, text)


def first_existing(columns: list[str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


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
    date_col = first_existing(columns, ["meeting_date", "race_date"])
    track_col = first_existing(columns, ["track"])
    race_no_col = first_existing(columns, ["race_no"])
    race_key_col = first_existing(columns, ["race_key"])
    horse_col = first_existing(columns, ["horse"])
    horse_key_col = first_existing(columns, ["horse_key"])
    missing = []
    for label, col in [
        ("meeting_date/race_date", date_col),
        ("track", track_col),
        ("race_no", race_no_col),
        ("race_key", race_key_col),
        ("horse", horse_col),
    ]:
        if col is None:
            missing.append(label)
    if missing:
        raise RuntimeError(f"Missing required settled columns: {missing}")

    frame = pd.DataFrame()
    frame["meeting_date"] = settled[date_col].map(clean).str[:10]
    frame["canonical_track_v1"] = settled[track_col].map(lambda value: apply_track_alias(value, alias_map))
    frame["settled_race_no_v1"] = settled[race_no_col].map(clean)
    frame["settled_race_key_v1"] = settled[race_key_col].map(clean)
    frame["horse_key_v1"] = (
        settled[horse_key_col].where(settled[horse_key_col].map(clean).ne(""), settled[horse_col].map(canon_horse))
        if horse_key_col
        else settled[horse_col].map(canon_horse)
    ).map(canon_horse)
    frame["horse_name_v1"] = settled[horse_col].map(clean)

    groups = (
        frame.groupby(["meeting_date", "canonical_track_v1", "settled_race_no_v1", "settled_race_key_v1"], dropna=False)
        .agg(
            settled_field_size_v1=("horse_key_v1", lambda values: len({clean(v) for v in values if clean(v) != ""})),
            settled_horse_keys_v1=("horse_key_v1", lambda values: sorted({clean(v) for v in values if clean(v) != ""})),
            settled_horse_names_v1=("horse_name_v1", lambda values: sorted({clean(v) for v in values if clean(v) != ""})),
        )
        .reset_index()
    )
    return groups


def build_backtest_groups(alias_map: dict[str, str]) -> pd.DataFrame:
    back = load_required_csv(SRC_BACKTEST)
    back = back[back["model"].map(upper).eq(MODEL_FILTER)].copy()
    if back.empty:
        raise RuntimeError(f"No rows found for model={MODEL_FILTER}")

    frame = pd.DataFrame()
    frame["meeting_date"] = back["race_date"].map(clean).str[:10]
    frame["canonical_track_v1"] = back["track"].map(lambda value: apply_track_alias(value, alias_map))
    frame["v6_backtest_race_key_v1"] = back["race_key"].map(clean)
    frame["horse_key_v1"] = back["horse"].map(canon_horse)
    frame["horse_name_v1"] = back["horse"].map(clean)

    groups = (
        frame.groupby(["meeting_date", "canonical_track_v1", "v6_backtest_race_key_v1"], dropna=False)
        .agg(
            v6_field_size_v1=("horse_key_v1", lambda values: len({clean(v) for v in values if clean(v) != ""})),
            v6_horse_keys_v1=("horse_key_v1", lambda values: sorted({clean(v) for v in values if clean(v) != ""})),
            v6_horse_names_v1=("horse_name_v1", lambda values: sorted({clean(v) for v in values if clean(v) != ""})),
        )
        .reset_index()
    )
    groups = groups.sort_values(["meeting_date", "canonical_track_v1", "v6_backtest_race_key_v1"]).reset_index(drop=True)
    groups["v6_race_slot_v1"] = groups.groupby(["meeting_date", "canonical_track_v1"], dropna=False).cumcount() + 1
    return groups


def build_group_lookups(frame: pd.DataFrame, key_cols: list[str], prefix: str) -> dict[tuple[str, ...], dict[str, object]]:
    lookup: dict[tuple[str, ...], dict[str, object]] = {}
    for _, row in frame.iterrows():
        key = tuple(clean(row[col]) for col in key_cols)
        lookup[key] = {
            f"{prefix}_field_size_v1": to_int(row[f"{prefix}_field_size_v1"]) or 0,
            f"{prefix}_horse_keys_v1": set(row[f"{prefix}_horse_keys_v1"]),
            f"{prefix}_horse_names_v1": list(row[f"{prefix}_horse_names_v1"]),
        }
        for col in frame.columns:
            if col in key_cols or col.startswith(f"{prefix}_horse_") or col == f"{prefix}_field_size_v1":
                continue
            lookup[key][col] = row[col]
    return lookup


def pairwise_similarity_pct(list_of_sets: list[set[str]]) -> float | None:
    if len(list_of_sets) < 2:
        return None
    scores: list[float] = []
    for idx in range(len(list_of_sets)):
        for jdx in range(idx + 1, len(list_of_sets)):
            left = list_of_sets[idx]
            right = list_of_sets[jdx]
            denom = max(len(left), len(right))
            if denom <= 0:
                continue
            score = (len(left.intersection(right)) / float(denom)) * 100.0
            scores.append(score)
    if not scores:
        return None
    return round(sum(scores) / len(scores), 3)


def load_review_conflicts() -> pd.DataFrame:
    bridge = load_required_csv(SRC_BRIDGE)
    review = bridge[bridge["bridge_use_flag_v1"].map(upper).eq("REVIEW")].copy()
    if review.empty:
        raise RuntimeError("No REVIEW rows found in edgeiq_race_number_bridge_candidates_v1.csv")
    review["overlap_count_v1"] = pd.to_numeric(review["overlap_count_v1"], errors="coerce").fillna(0).astype(int)
    review["overlap_pct_min_v1"] = pd.to_numeric(review["overlap_pct_min_v1"], errors="coerce")
    review["settled_field_size_v1"] = pd.to_numeric(review["settled_field_size_v1"], errors="coerce").fillna(0).astype(int)
    review["v6_field_size_v1"] = pd.to_numeric(review["v6_field_size_v1"], errors="coerce").fillna(0).astype(int)
    review["candidate_rank_within_settled_v1"] = pd.to_numeric(review["candidate_rank_within_settled_v1"], errors="coerce").fillna(999).astype(int)
    review["candidate_rank_within_v6_v1"] = pd.to_numeric(review["candidate_rank_within_v6_v1"], errors="coerce").fillna(999).astype(int)
    review["v6_race_slot_v1"] = pd.to_numeric(review["v6_race_slot_v1"], errors="coerce").fillna(0).astype(int)
    review["review_conflict_group_id_v1"] = review.apply(
        lambda row: (
            f"V6::{clean(row['meeting_date'])}|{clean(row['canonical_track_v1'])}|{clean(row['v6_backtest_race_key_v1'])}"
            if clean(row["conflict_type_v1"]) == "MULTIPLE_SETTLED_TO_V6"
            else f"SETTLED::{clean(row['meeting_date'])}|{clean(row['canonical_track_v1'])}|{clean(row['settled_race_key_v1'])}"
        ),
        axis=1,
    )
    review["review_side_mode_v1"] = review["conflict_type_v1"].map(
        {
            "MULTIPLE_SETTLED_TO_V6": "SETTLED_SIDE_DUPLICATION",
            "SETTLED_TO_MULTIPLE_V6": "SOURCE_SIDE_DUPLICATION",
        }
    ).fillna("UNKNOWN")
    return review


def build_collision_maps(collisions: pd.DataFrame) -> tuple[dict[tuple[str, str, str, str], int], dict[tuple[str, str], int]]:
    exact_map: dict[tuple[str, str, str, str], int] = {}
    meeting_map: dict[tuple[str, str], int] = {}
    for _, row in collisions.iterrows():
        date_value = clean(row.get("meeting_date", ""))
        track_value = clean(row.get("canonical_track_v1", ""))
        race_no = clean(row.get("race_no", ""))
        issue = clean(row.get("issue_type", ""))
        key_exact = (date_value, track_value, race_no, issue)
        exact_map[key_exact] = exact_map.get(key_exact, 0) + 1
        key_meeting = (date_value, track_value)
        meeting_map[key_meeting] = meeting_map.get(key_meeting, 0) + 1
    return exact_map, meeting_map


def classify_group(
    side_mode: str,
    group_size: int,
    pairwise_similarity: float | None,
    meeting_group_count: int,
    exact_dup_runner_count: int,
    exact_dup_horse_count: int,
    race_gap_values: list[int],
    any_current_same: bool,
) -> tuple[str, str, int, str]:
    pair = pairwise_similarity or 0.0
    max_gap = max(race_gap_values) if race_gap_values else 0

    if exact_dup_runner_count > 0 or (exact_dup_horse_count > 0 and pair < 80.0):
        if exact_dup_runner_count >= 3 or exact_dup_horse_count >= 10:
            return "HORSE_DUPLICATION", "HIGH", 90, "duplicate runner evidence present in collision audit"
        return "HORSE_DUPLICATION", "MEDIUM", 75, "horse duplication evidence present in collision audit"

    if side_mode == "SETTLED_SIDE_DUPLICATION":
        if pair >= 90.0:
            if meeting_group_count >= 3:
                return "DUPLICATE_MEETING", "HIGH", 95, "multiple settled races mirror the same source race across the meeting"
            return "DUPLICATE_RACE_CARD", "HIGH", 90, "settled race identities are near-identical against one source race"
        if pair >= 75.0:
            if max_gap <= 2:
                return "RACE_RENUMBERED", "MEDIUM", 72, "settled race numbers are close and horse overlap remains strong"
            return "SETTLED_EXTRA_RACE", "MEDIUM", 68, "one settled-side race likely extra or duplicated"
        if any_current_same:
            return "SETTLED_EXTRA_RACE", "LOW", 52, "current V2 already favors one settled race and alternate settled race remains weak"
        return "UNKNOWN", "LOW", 35, "settled-side duplication remains ambiguous"

    if side_mode == "SOURCE_SIDE_DUPLICATION":
        if pair >= 90.0:
            if meeting_group_count >= 3:
                return "DUPLICATE_MEETING", "HIGH", 95, "multiple source races mirror the same settled race across the meeting"
            return "SOURCE_EXTRA_RACE", "HIGH", 90, "source-side race identity appears duplicated"
        if pair >= 75.0:
            if any_current_same:
                return "SOURCE_EXTRA_RACE", "MEDIUM", 70, "current V2 favors one source race and alternate source race looks duplicative"
            return "RACE_RENUMBERED", "MEDIUM", 66, "source-side race identity looks renumbered rather than unique"
        return "UNKNOWN", "LOW", 40, "source-side duplication remains ambiguous"

    return "UNKNOWN", "LOW", 25, "no classification rule matched"


def build_audit() -> tuple[pd.DataFrame, pd.DataFrame]:
    alias_map = load_alias_map()
    review = load_review_conflicts()
    collisions = load_required_csv(SRC_COLLISIONS)
    _diag = load_required_csv(SRC_DIAG)
    settled_groups = build_settled_groups(alias_map)
    back_groups = build_backtest_groups(alias_map)

    settled_lookup = build_group_lookups(
        settled_groups,
        ["meeting_date", "canonical_track_v1", "settled_race_no_v1", "settled_race_key_v1"],
        "settled",
    )
    back_lookup = build_group_lookups(
        back_groups,
        ["meeting_date", "canonical_track_v1", "v6_backtest_race_key_v1"],
        "v6",
    )

    exact_collision_map, meeting_collision_map = build_collision_maps(collisions)

    meeting_context = (
        review.groupby(["meeting_date", "canonical_track_v1"], dropna=False)
        .agg(
            meeting_review_rows_v1=("review_conflict_group_id_v1", "size"),
            meeting_review_groups_v1=("review_conflict_group_id_v1", pd.Series.nunique),
            meeting_distinct_settled_races_v1=("settled_race_key_v1", pd.Series.nunique),
            meeting_distinct_v6_races_v1=("v6_backtest_race_key_v1", pd.Series.nunique),
        )
        .reset_index()
    )
    meeting_context_lookup = {
        (clean(row["meeting_date"]), clean(row["canonical_track_v1"])): row
        for _, row in meeting_context.iterrows()
    }

    group_rows: list[dict[str, object]] = []
    audit_rows: list[dict[str, object]] = []
    built_at = datetime.now(timezone.utc).isoformat()

    for group_id, group in review.groupby("review_conflict_group_id_v1", dropna=False):
        group = group.copy().sort_values(
            ["overlap_count_v1", "overlap_pct_min_v1", "candidate_rank_within_settled_v1", "candidate_rank_within_v6_v1"],
            ascending=[False, False, True, True],
        )
        first = group.iloc[0]
        meeting_date = clean(first["meeting_date"])
        canonical_track = clean(first["canonical_track_v1"])
        side_mode = clean(first["review_side_mode_v1"])
        group_type_raw = clean(first["conflict_type_v1"])

        meeting_ctx = meeting_context_lookup.get((meeting_date, canonical_track))
        meeting_group_count = int(meeting_ctx["meeting_review_groups_v1"]) if meeting_ctx is not None else 0
        meeting_rows_count = int(meeting_ctx["meeting_review_rows_v1"]) if meeting_ctx is not None else 0

        settled_sets: list[set[str]] = []
        v6_sets: list[set[str]] = []
        race_gap_values: list[int] = []
        settled_race_numbers: list[str] = []
        settled_race_keys: list[str] = []
        v6_race_keys: list[str] = []
        current_alignment_values: list[str] = []

        exact_dup_runner_count = 0
        exact_dup_horse_count = 0

        for _, row in group.iterrows():
            settled_key = (
                clean(row["meeting_date"]),
                clean(row["canonical_track_v1"]),
                clean(row["settled_race_no_v1"]),
                clean(row["settled_race_key_v1"]),
            )
            back_key = (
                clean(row["meeting_date"]),
                clean(row["canonical_track_v1"]),
                clean(row["v6_backtest_race_key_v1"]),
            )
            settled_info = settled_lookup.get(settled_key, {})
            back_info = back_lookup.get(back_key, {})
            if settled_info:
                settled_sets.append(settled_info["settled_horse_keys_v1"])
            if back_info:
                v6_sets.append(set(back_info["v6_horse_keys_v1"]))

            settled_race_numbers.append(clean(row["settled_race_no_v1"]))
            settled_race_keys.append(clean(row["settled_race_key_v1"]))
            v6_race_keys.append(clean(row["v6_backtest_race_key_v1"]))
            current_alignment_values.append(clean(row["current_v2_alignment_v1"]))

            race_no_int = to_int(row["settled_race_no_v1"])
            inferred_int = to_int(row["v6_inferred_race_no_v2"])
            if race_no_int is not None and inferred_int is not None:
                race_gap_values.append(abs(race_no_int - inferred_int))

            exact_dup_runner_count += exact_collision_map.get(
                (meeting_date, canonical_track, clean(row["settled_race_no_v1"]), "DUPLICATE_RACE_RUNNER"),
                0,
            )
            exact_dup_horse_count += exact_collision_map.get(
                (meeting_date, canonical_track, clean(row["settled_race_no_v1"]), "DUPLICATE_HORSE_SAME_DATE_TRACK"),
                0,
            )

        if side_mode == "SETTLED_SIDE_DUPLICATION":
            pairwise_similarity = pairwise_similarity_pct(settled_sets)
        elif side_mode == "SOURCE_SIDE_DUPLICATION":
            pairwise_similarity = pairwise_similarity_pct(v6_sets)
        else:
            pairwise_similarity = None

        source_overlap_set = set()
        settled_overlap_set = set()
        for _, row in group.iterrows():
            settled_key = (
                clean(row["meeting_date"]),
                clean(row["canonical_track_v1"]),
                clean(row["settled_race_no_v1"]),
                clean(row["settled_race_key_v1"]),
            )
            back_key = (
                clean(row["meeting_date"]),
                clean(row["canonical_track_v1"]),
                clean(row["v6_backtest_race_key_v1"]),
            )
            settled_info = settled_lookup.get(settled_key, {})
            back_info = back_lookup.get(back_key, {})
            settled_horses = set(settled_info.get("settled_horse_keys_v1", set()))
            source_horses = set(back_info.get("v6_horse_keys_v1", set()))
            source_overlap_set.update(source_horses)
            settled_overlap_set.update(settled_horses)

        shared_horses = sorted(settled_overlap_set.intersection(source_overlap_set))
        exclusive_settled = sorted(settled_overlap_set.difference(source_overlap_set))
        exclusive_source = sorted(source_overlap_set.difference(settled_overlap_set))

        conflict_type_resolved, confidence_label, confidence_score, confidence_reason = classify_group(
            side_mode=side_mode,
            group_size=len(group),
            pairwise_similarity=pairwise_similarity,
            meeting_group_count=meeting_group_count,
            exact_dup_runner_count=exact_dup_runner_count,
            exact_dup_horse_count=exact_dup_horse_count,
            race_gap_values=race_gap_values,
            any_current_same=any(value == "CURRENT_V2_SAME" for value in current_alignment_values),
        )

        current_alignment_mix = join_list(sorted(set(current_alignment_values)))
        best_candidate = group.iloc[0]
        additional_recoverable_rows = 0
        if "CURRENT_V2_SAME" not in current_alignment_values and conflict_type_resolved != "UNKNOWN":
            additional_recoverable_rows = int(best_candidate["overlap_count_v1"])

        group_row = {
            "review_conflict_group_id_v1": group_id,
            "meeting_date": meeting_date,
            "canonical_track_v1": canonical_track,
            "review_side_mode_v1": side_mode,
            "group_type_raw_v1": group_type_raw,
            "conflict_type_resolved_v1": conflict_type_resolved,
            "confidence_v1": confidence_label,
            "confidence_score_v1": confidence_score,
            "confidence_reason_v1": confidence_reason,
            "meeting_review_groups_v1": meeting_group_count,
            "meeting_review_rows_v1": meeting_rows_count,
            "meeting_collision_rows_v1": meeting_collision_map.get((meeting_date, canonical_track), 0),
            "group_row_count_v1": int(len(group)),
            "group_distinct_settled_races_v1": int(group["settled_race_key_v1"].nunique()),
            "group_distinct_v6_races_v1": int(group["v6_backtest_race_key_v1"].nunique()),
            "settled_race_nos_v1": join_list(sorted(set(settled_race_numbers), key=sort_race_no_key)),
            "settled_race_keys_v1": join_list(sorted(set(settled_race_keys))),
            "v6_backtest_race_keys_v1": join_list(sorted(set(v6_race_keys))),
            "current_v2_alignment_mix_v1": current_alignment_mix,
            "pairwise_similarity_pct_v1": round_num(pairwise_similarity, 3),
            "shared_horse_count_v1": len(shared_horses),
            "shared_horses_v1": join_list(shared_horses, 30),
            "exclusive_settled_horse_count_v1": len(exclusive_settled),
            "exclusive_settled_horses_v1": join_list(exclusive_settled, 20),
            "exclusive_source_horse_count_v1": len(exclusive_source),
            "exclusive_source_horses_v1": join_list(exclusive_source, 20),
            "best_overlap_count_v1": int(best_candidate["overlap_count_v1"]),
            "best_overlap_pct_min_v1": round_num(best_candidate["overlap_pct_min_v1"], 3),
            "best_settled_race_no_v1": clean(best_candidate["settled_race_no_v1"]),
            "best_settled_race_key_v1": clean(best_candidate["settled_race_key_v1"]),
            "best_v6_backtest_race_key_v1": clean(best_candidate["v6_backtest_race_key_v1"]),
            "best_v6_inferred_race_no_v2": clean(best_candidate["v6_inferred_race_no_v2"]),
            "best_candidate_rank_within_settled_v1": int(best_candidate["candidate_rank_within_settled_v1"]),
            "best_candidate_rank_within_v6_v1": int(best_candidate["candidate_rank_within_v6_v1"]),
            "exact_dup_race_runner_rows_v1": exact_dup_runner_count,
            "exact_dup_horse_rows_v1": exact_dup_horse_count,
            "estimated_recoverable_rows_if_resolved_v1": additional_recoverable_rows,
            "built_at_v1": built_at,
        }
        group_rows.append(group_row)

        for _, row in group.iterrows():
            settled_key = (
                clean(row["meeting_date"]),
                clean(row["canonical_track_v1"]),
                clean(row["settled_race_no_v1"]),
                clean(row["settled_race_key_v1"]),
            )
            back_key = (
                clean(row["meeting_date"]),
                clean(row["canonical_track_v1"]),
                clean(row["v6_backtest_race_key_v1"]),
            )
            settled_info = settled_lookup.get(settled_key, {})
            back_info = back_lookup.get(back_key, {})
            settled_horses = set(settled_info.get("settled_horse_keys_v1", set()))
            source_horses = set(back_info.get("v6_horse_keys_v1", set()))
            shared = sorted(settled_horses.intersection(source_horses))
            exclusive_settled_row = sorted(settled_horses.difference(source_horses))
            exclusive_source_row = sorted(source_horses.difference(settled_horses))

            audit_rows.append(
                {
                    "review_conflict_group_id_v1": group_id,
                    "meeting_date": meeting_date,
                    "canonical_track_v1": canonical_track,
                    "settled_race_no_v1": clean(row["settled_race_no_v1"]),
                    "settled_race_key_v1": clean(row["settled_race_key_v1"]),
                    "v6_backtest_race_key_v1": clean(row["v6_backtest_race_key_v1"]),
                    "v6_inferred_race_no_v2": clean(row["v6_inferred_race_no_v2"]),
                    "review_side_mode_v1": side_mode,
                    "group_type_raw_v1": group_type_raw,
                    "conflict_type_resolved_v1": conflict_type_resolved,
                    "confidence_v1": confidence_label,
                    "confidence_score_v1": confidence_score,
                    "overlap_count_v1": int(row["overlap_count_v1"]),
                    "overlap_pct_min_v1": round_num(row["overlap_pct_min_v1"], 3),
                    "settled_field_size_v1": int(row["settled_field_size_v1"]),
                    "v6_field_size_v1": int(row["v6_field_size_v1"]),
                    "field_size_diff_v1": abs(int(row["settled_field_size_v1"]) - int(row["v6_field_size_v1"])),
                    "shared_horse_count_v1": len(shared),
                    "shared_horses_v1": join_list(shared, 30),
                    "exclusive_settled_horse_count_v1": len(exclusive_settled_row),
                    "exclusive_settled_horses_v1": join_list(exclusive_settled_row, 20),
                    "exclusive_source_horse_count_v1": len(exclusive_source_row),
                    "exclusive_source_horses_v1": join_list(exclusive_source_row, 20),
                    "candidate_rank_within_settled_v1": int(row["candidate_rank_within_settled_v1"]),
                    "candidate_rank_within_v6_v1": int(row["candidate_rank_within_v6_v1"]),
                    "current_v2_alignment_v1": clean(row["current_v2_alignment_v1"]),
                    "v2_complete_match_race_v1": clean(row["v2_complete_match_race_v1"]),
                    "v6_race_mapping_status_v2": clean(row["v6_race_mapping_status_v2"]),
                    "pairwise_similarity_pct_v1": round_num(pairwise_similarity, 3),
                    "exact_dup_race_runner_rows_v1": exact_dup_runner_count,
                    "exact_dup_horse_rows_v1": exact_dup_horse_count,
                    "group_row_count_v1": int(len(group)),
                    "meeting_review_groups_v1": meeting_group_count,
                    "meeting_review_rows_v1": meeting_rows_count,
                    "estimated_recoverable_rows_if_resolved_v1": additional_recoverable_rows,
                    "confidence_reason_v1": confidence_reason,
                    "built_at_v1": built_at,
                }
            )

    group_frame = pd.DataFrame(group_rows)
    audit_frame = pd.DataFrame(audit_rows)
    return audit_frame, group_frame


def build_summary(group_frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    def add_row(
        section: str,
        rank_v1: int,
        label: str,
        value: object,
        conflict_type_resolved_v1: str = "",
        meeting_date: str = "",
        canonical_track_v1: str = "",
        review_conflict_group_id_v1: str = "",
        notes: str = "",
    ) -> None:
        rows.append(
            {
                "section": section,
                "rank_v1": rank_v1,
                "label": label,
                "value": value,
                "conflict_type_resolved_v1": conflict_type_resolved_v1,
                "meeting_date": meeting_date,
                "canonical_track_v1": canonical_track_v1,
                "review_conflict_group_id_v1": review_conflict_group_id_v1,
                "notes": notes,
            }
        )

    add_row("OVERALL", 1, "conflict_groups", int(len(group_frame)))
    add_row("OVERALL", 2, "estimated_recoverable_rows_if_conflicts_resolved", int(group_frame["estimated_recoverable_rows_if_resolved_v1"].sum()))
    add_row("OVERALL", 3, "high_confidence_groups", int(group_frame["confidence_v1"].eq("HIGH").sum()))
    add_row("OVERALL", 4, "medium_confidence_groups", int(group_frame["confidence_v1"].eq("MEDIUM").sum()))
    add_row("OVERALL", 5, "low_confidence_groups", int(group_frame["confidence_v1"].eq("LOW").sum()))
    add_row("OVERALL", 6, "groups_currently_unmapped", int(group_frame["current_v2_alignment_mix_v1"].str.contains("CURRENT_V2_UNMAPPED", regex=False).sum()))
    add_row("OVERALL", 7, "groups_currently_same", int(group_frame["current_v2_alignment_mix_v1"].str.contains("CURRENT_V2_SAME", regex=False).sum()))

    by_type = (
        group_frame.groupby("conflict_type_resolved_v1", dropna=False)
        .agg(
            groups=("review_conflict_group_id_v1", "size"),
            estimated_recoverable_rows=("estimated_recoverable_rows_if_resolved_v1", "sum"),
            avg_confidence_score=("confidence_score_v1", "mean"),
        )
        .reset_index()
        .sort_values(["estimated_recoverable_rows", "groups", "conflict_type_resolved_v1"], ascending=[False, False, True])
    )
    for idx, (_, row) in enumerate(by_type.iterrows(), start=1):
        add_row(
            "TYPE_COUNT",
            idx,
            "groups",
            int(row["groups"]),
            conflict_type_resolved_v1=clean(row["conflict_type_resolved_v1"]),
            notes=f"estimated_recoverable_rows={int(row['estimated_recoverable_rows'])} avg_confidence_score={round_num(row['avg_confidence_score'], 2)}",
        )

    top_tracks = (
        group_frame.groupby("canonical_track_v1", dropna=False)
        .agg(groups=("review_conflict_group_id_v1", "size"), estimated_recoverable_rows=("estimated_recoverable_rows_if_resolved_v1", "sum"))
        .reset_index()
        .sort_values(["estimated_recoverable_rows", "groups", "canonical_track_v1"], ascending=[False, False, True])
        .head(20)
    )
    for idx, (_, row) in enumerate(top_tracks.iterrows(), start=1):
        add_row(
            "TOP_TRACK",
            idx,
            "estimated_recoverable_rows",
            int(row["estimated_recoverable_rows"]),
            canonical_track_v1=clean(row["canonical_track_v1"]),
            notes=f"groups={int(row['groups'])}",
        )

    top_dates = (
        group_frame.groupby("meeting_date", dropna=False)
        .agg(groups=("review_conflict_group_id_v1", "size"), estimated_recoverable_rows=("estimated_recoverable_rows_if_resolved_v1", "sum"))
        .reset_index()
        .sort_values(["estimated_recoverable_rows", "groups", "meeting_date"], ascending=[False, False, True])
        .head(20)
    )
    for idx, (_, row) in enumerate(top_dates.iterrows(), start=1):
        add_row(
            "TOP_DATE",
            idx,
            "estimated_recoverable_rows",
            int(row["estimated_recoverable_rows"]),
            meeting_date=clean(row["meeting_date"]),
            notes=f"groups={int(row['groups'])}",
        )

    top_meetings = (
        group_frame.groupby(["meeting_date", "canonical_track_v1"], dropna=False)
        .agg(groups=("review_conflict_group_id_v1", "size"), estimated_recoverable_rows=("estimated_recoverable_rows_if_resolved_v1", "sum"))
        .reset_index()
        .sort_values(["estimated_recoverable_rows", "groups", "meeting_date", "canonical_track_v1"], ascending=[False, False, True, True])
        .head(20)
    )
    for idx, (_, row) in enumerate(top_meetings.iterrows(), start=1):
        add_row(
            "TOP_MEETING",
            idx,
            "estimated_recoverable_rows",
            int(row["estimated_recoverable_rows"]),
            meeting_date=clean(row["meeting_date"]),
            canonical_track_v1=clean(row["canonical_track_v1"]),
            notes=f"groups={int(row['groups'])}",
        )

    top_groups = (
        group_frame.sort_values(
            ["estimated_recoverable_rows_if_resolved_v1", "confidence_score_v1", "meeting_date", "canonical_track_v1"],
            ascending=[False, False, True, True],
        )
        .head(30)
    )
    for idx, (_, row) in enumerate(top_groups.iterrows(), start=1):
        add_row(
            "TOP_DUPLICATED_RACE_IDENTITY",
            idx,
            clean(row["conflict_type_resolved_v1"]),
            int(row["estimated_recoverable_rows_if_resolved_v1"]),
            conflict_type_resolved_v1=clean(row["conflict_type_resolved_v1"]),
            meeting_date=clean(row["meeting_date"]),
            canonical_track_v1=clean(row["canonical_track_v1"]),
            review_conflict_group_id_v1=clean(row["review_conflict_group_id_v1"]),
            notes=(
                f"confidence={clean(row['confidence_v1'])} "
                f"settled={clean(row['settled_race_nos_v1'])} "
                f"best_v6={clean(row['best_v6_backtest_race_key_v1'])}"
            ),
        )

    return pd.DataFrame(rows)


def main() -> None:
    audit_frame, group_frame = build_audit()
    summary = build_summary(group_frame)
    examples = group_frame.sort_values(
        ["estimated_recoverable_rows_if_resolved_v1", "confidence_score_v1", "meeting_date", "canonical_track_v1"],
        ascending=[False, False, True, True],
    ).reset_index(drop=True)

    audit_frame.to_csv(OUT_AUDIT, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    examples.to_csv(OUT_EXAMPLES, index=False)

    overall = summary[summary["section"].eq("OVERALL")].copy()
    type_counts = summary[summary["section"].eq("TYPE_COUNT")].copy()

    print("[EDGEIQ_RACE_IDENTITY_CONFLICTS_V1] COMPLETE")
    print(overall.to_string(index=False))
    if not type_counts.empty:
        print(type_counts.to_string(index=False))
    print(f"wrote={OUT_AUDIT}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_EXAMPLES}")


if __name__ == "__main__":
    main()
