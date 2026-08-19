from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import math

import pandas as pd

from edgeiq_track_alias_bridge_v1 import canon_horse
from build_edgeiq_v6_1_settled_gap_replay_v2_expanded import (
    apply_alias_to_settled,
    build_settled_base,
    build_v61_lookup,
    load_v61_backtest_raw,
)


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC_REPLAY = DATA / "edgeiq_v6_1_settled_gap_replay_v2_expanded.csv"
SRC_DIAGNOSTICS = DATA / "edgeiq_v6_1_settled_gap_replay_v2_expanded_match_diagnostics.csv"
SRC_ALIAS = DATA / "edgeiq_track_alias_bridge_v1.csv"
SRC_SETTLED = DATA / "edgeiq_historical_replay_settled_v1.csv"
SRC_BACKTEST = DATA / "edgeiq_projection_v6_1_research_prior_rating_backtest.csv"

OUT_AUDIT = DATA / "edgeiq_v6_1_settled_replay_unmatched_collisions_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_v6_1_settled_replay_unmatched_collisions_v1_summary.csv"
OUT_EXAMPLES = DATA / "edgeiq_v6_1_settled_replay_unmatched_collision_examples_v1.csv"

ISSUE_ORDER = [
    "TRACK_ALIAS_MISSING",
    "RACE_NO_MISMATCH",
    "DUPLICATE_HORSE_SAME_DATE_TRACK",
    "DUPLICATE_RACE_RUNNER",
    "HORSE_KEY_COLLISION",
    "SOURCE_RACE_MISSING",
    "SETTLED_RACE_MISSING",
    "UNKNOWN",
]


def clean(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def to_float(value: object) -> float | None:
    text = clean(value)
    if text == "":
        return None
    text = text.replace(",", "").replace("$", "")
    try:
        number = float(text)
    except Exception:
        return None
    if not math.isfinite(number):
        return None
    return number


def to_int(value: object) -> int | None:
    number = to_float(value)
    if number is None:
        return None
    return int(round(number))


def load_required_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)


def load_alias_map() -> dict[str, str]:
    alias_df = load_required_csv(SRC_ALIAS)
    alias_df = alias_df[alias_df["chosen"].map(clean).eq("YES")].copy()
    alias_map: dict[str, str] = {}
    for _, row in alias_df.iterrows():
        alias_key = clean(row.get("alias_key"))
        canonical = clean(row.get("canonical_track"))
        if alias_key != "" and canonical != "":
            alias_map[alias_key] = canonical
    return alias_map


def build_context() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    alias_map = load_alias_map()

    settled_base, _ = build_settled_base()
    settled_enriched = apply_alias_to_settled(settled_base, alias_map)

    back_raw, _ = load_v61_backtest_raw()
    lookup, mapping_df = build_v61_lookup(back_raw, settled_enriched, alias_map)

    diagnostics = load_required_csv(SRC_DIAGNOSTICS)
    replay = load_required_csv(SRC_REPLAY)

    diagnostics["meeting_date"] = diagnostics["meeting_date"].map(clean).str[:10]
    diagnostics["track_canonical_v2"] = diagnostics["track_canonical_v2"].map(clean)
    diagnostics["track_norm_v2"] = diagnostics["track_norm_v2"].map(clean)
    diagnostics["race_no"] = diagnostics["race_no"].map(clean)
    diagnostics["horse"] = diagnostics["horse"].map(clean)
    diagnostics["horse_key"] = diagnostics["horse_key"].map(canon_horse)
    diagnostics["source_match_stage_v2"] = diagnostics["source_match_stage_v2"].map(clean)
    diagnostics["candidate_count_stage_1"] = diagnostics["candidate_count_stage_1"].map(to_int).fillna(0).astype(int)
    diagnostics["candidate_count_stage_2"] = diagnostics["candidate_count_stage_2"].map(to_int).fillna(0).astype(int)
    diagnostics["candidate_count_stage_3"] = diagnostics["candidate_count_stage_3"].map(to_int).fillna(0).astype(int)
    diagnostics["candidate_count_stage_4"] = diagnostics["candidate_count_stage_4"].map(to_int).fillna(0).astype(int)

    replay["source_match_stage_v2"] = replay["source_match_stage_v2"].map(clean)

    return settled_enriched, lookup, mapping_df, diagnostics


def build_metrics_maps(settled: pd.DataFrame, lookup: pd.DataFrame) -> dict[str, dict[str, object]]:
    settled = settled.copy()
    settled["date_track_key"] = settled["meeting_date"].map(clean) + "|" + settled["track_norm_v2"].map(clean)
    settled["date_track_race_key"] = settled["date_track_key"] + "|" + settled["race_no"].map(clean)
    settled["date_track_horse_key"] = settled["date_track_key"] + "|" + settled["horse_key"].map(clean)
    settled["date_track_race_horse_key"] = settled["date_track_race_key"] + "|" + settled["horse_key"].map(clean)
    settled["date_horse_key"] = settled["meeting_date"].map(clean) + "|" + settled["horse_key"].map(clean)

    lookup = lookup.copy()
    lookup["meeting_date"] = lookup["meeting_date"].map(clean).str[:10]
    lookup["track_norm_v2"] = lookup["track_norm_v2"].map(clean)
    lookup["track_canonical_v2"] = lookup["track_canonical_v2"].map(clean)
    lookup["inferred_race_no_v2"] = lookup["inferred_race_no_v2"].map(clean)
    lookup["backtest_horse_key"] = lookup["backtest_horse_key"].map(canon_horse)
    lookup["backtest_horse_norm"] = lookup["backtest_horse_norm"].map(canon_horse)
    lookup["date_track_key"] = lookup["meeting_date"] + "|" + lookup["track_norm_v2"]
    lookup["date_track_race_key"] = lookup["date_track_key"] + "|" + lookup["inferred_race_no_v2"]
    lookup["date_track_horse_key"] = lookup["date_track_key"] + "|" + lookup["backtest_horse_key"]
    lookup["date_track_race_horse_key"] = lookup["date_track_race_key"] + "|" + lookup["backtest_horse_key"]
    lookup["date_horse_key"] = lookup["meeting_date"] + "|" + lookup["backtest_horse_key"]

    settled_dup_race_runner = settled["date_track_race_horse_key"].value_counts().to_dict()
    source_dup_race_runner = lookup["date_track_race_horse_key"].value_counts().to_dict()

    settled_same_track_horse_races = (
        settled.groupby("date_track_horse_key", dropna=False)["race_no"].nunique().to_dict()
    )
    source_same_track_horse_races = (
        lookup[lookup["inferred_race_no_v2"].map(clean).ne("")]
        .groupby("date_track_horse_key", dropna=False)["inferred_race_no_v2"]
        .nunique()
        .to_dict()
    )

    settled_same_date_horse_tracks = (
        settled.groupby("date_horse_key", dropna=False)["track_canonical_v2"].nunique().to_dict()
    )
    source_same_date_horse_tracks = (
        lookup.groupby("date_horse_key", dropna=False)["track_canonical_v2"].nunique().to_dict()
    )

    settled_race_count_by_date_track = (
        settled.groupby("date_track_key", dropna=False)["race_no"].nunique().to_dict()
    )
    source_race_count_by_date_track = (
        lookup[lookup["inferred_race_no_v2"].map(clean).ne("")]
        .groupby("date_track_key", dropna=False)["inferred_race_no_v2"]
        .nunique()
        .to_dict()
    )

    settled_runner_count_by_race = settled.groupby("date_track_race_key", dropna=False).size().to_dict()
    source_runner_count_by_race = (
        lookup[lookup["inferred_race_no_v2"].map(clean).ne("")]
        .groupby("date_track_race_key", dropna=False)
        .size()
        .to_dict()
    )

    settled_key_collision = (
        settled.groupby("date_track_race_horse_key", dropna=False)["horse"].nunique().to_dict()
    )
    source_key_collision = (
        lookup.groupby("date_track_race_horse_key", dropna=False)["backtest_horse_norm"].nunique().to_dict()
    )

    source_track_candidates = (
        lookup.groupby("date_horse_key", dropna=False)["track_canonical_v2"]
        .agg(lambda values: sorted({clean(value) for value in values if clean(value) != ""}))
        .to_dict()
    )
    source_race_candidates = (
        lookup.groupby("date_track_horse_key", dropna=False)["inferred_race_no_v2"]
        .agg(lambda values: sorted({clean(value) for value in values if clean(value) != ""}))
        .to_dict()
    )
    source_race_keys_by_date_track = (
        lookup.groupby("date_track_key", dropna=False)["backtest_race_key"]
        .agg(lambda values: sorted({clean(value) for value in values if clean(value) != ""}))
        .to_dict()
    )

    return {
        "settled_dup_race_runner": settled_dup_race_runner,
        "source_dup_race_runner": source_dup_race_runner,
        "settled_same_track_horse_races": settled_same_track_horse_races,
        "source_same_track_horse_races": source_same_track_horse_races,
        "settled_same_date_horse_tracks": settled_same_date_horse_tracks,
        "source_same_date_horse_tracks": source_same_date_horse_tracks,
        "settled_race_count_by_date_track": settled_race_count_by_date_track,
        "source_race_count_by_date_track": source_race_count_by_date_track,
        "settled_runner_count_by_race": settled_runner_count_by_race,
        "source_runner_count_by_race": source_runner_count_by_race,
        "settled_key_collision": settled_key_collision,
        "source_key_collision": source_key_collision,
        "source_track_candidates": source_track_candidates,
        "source_race_candidates": source_race_candidates,
        "source_race_keys_by_date_track": source_race_keys_by_date_track,
    }


def recoverable_flag(issue_type: str) -> str:
    if issue_type in {"TRACK_ALIAS_MISSING", "RACE_NO_MISMATCH", "DUPLICATE_RACE_RUNNER", "DUPLICATE_HORSE_SAME_DATE_TRACK"}:
        return "YES"
    if issue_type == "HORSE_KEY_COLLISION":
        return "MAYBE"
    if issue_type in {"SOURCE_RACE_MISSING", "SETTLED_RACE_MISSING"}:
        return "NO"
    return "UNKNOWN"


def classify_settled_unmatched(row: pd.Series, metrics: dict[str, dict[str, object]]) -> tuple[str, str]:
    date_track_key = clean(row["meeting_date"]) + "|" + clean(row["track_norm_v2"])
    date_track_race_key = date_track_key + "|" + clean(row["race_no"])
    date_track_horse_key = date_track_key + "|" + clean(row["horse_key"])
    date_track_race_horse_key = date_track_race_key + "|" + clean(row["horse_key"])
    date_horse_key = clean(row["meeting_date"]) + "|" + clean(row["horse_key"])

    settled_dup_race_runner = int(metrics["settled_dup_race_runner"].get(date_track_race_horse_key, 0))
    source_dup_race_runner = int(metrics["source_dup_race_runner"].get(date_track_race_horse_key, 0))
    settled_same_track_horse_races = int(metrics["settled_same_track_horse_races"].get(date_track_horse_key, 0))
    source_same_track_horse_races = int(metrics["source_same_track_horse_races"].get(date_track_horse_key, 0))
    settled_same_date_horse_tracks = int(metrics["settled_same_date_horse_tracks"].get(date_horse_key, 0))
    source_same_date_horse_tracks = int(metrics["source_same_date_horse_tracks"].get(date_horse_key, 0))
    settled_key_collision = int(metrics["settled_key_collision"].get(date_track_race_horse_key, 0))
    source_key_collision = int(metrics["source_key_collision"].get(date_track_race_horse_key, 0))

    candidate_stage_1 = int(row.get("candidate_count_stage_1", 0))
    candidate_stage_3 = int(row.get("candidate_count_stage_3", 0))
    candidate_stage_4 = int(row.get("candidate_count_stage_4", 0))
    source_race_candidates = metrics["source_race_candidates"].get(date_track_horse_key, [])
    source_track_candidates = metrics["source_track_candidates"].get(date_horse_key, [])
    source_race_count = int(metrics["source_race_count_by_date_track"].get(date_track_key, 0))
    settled_race_count = int(metrics["settled_race_count_by_date_track"].get(date_track_key, 0))
    source_runner_count = int(metrics["source_runner_count_by_race"].get(date_track_race_key, 0))
    settled_runner_count = int(metrics["settled_runner_count_by_race"].get(date_track_race_key, 0))

    if settled_dup_race_runner > 1 or source_dup_race_runner > 1:
        return "DUPLICATE_RACE_RUNNER", f"duplicate_race_runner settled={settled_dup_race_runner} source={source_dup_race_runner}"
    if settled_key_collision > 1 or source_key_collision > 1:
        return "HORSE_KEY_COLLISION", f"horse_key_collision settled={settled_key_collision} source={source_key_collision}"
    if settled_same_track_horse_races > 1 or source_same_track_horse_races > 1:
        return "DUPLICATE_HORSE_SAME_DATE_TRACK", (
            f"same horse appears in multiple race numbers settled={settled_same_track_horse_races} "
            f"source={source_same_track_horse_races}"
        )
    if candidate_stage_1 > 0 or candidate_stage_3 > 0:
        race_candidates_text = ",".join(source_race_candidates)
        return "RACE_NO_MISMATCH", f"source candidates exist but exact race join failed source_race_nos={race_candidates_text}"
    if candidate_stage_4 > 0:
        if source_same_date_horse_tracks > 1 or settled_same_date_horse_tracks > 1:
            return "HORSE_KEY_COLLISION", (
                f"same horse key appears across multiple tracks settled_tracks={settled_same_date_horse_tracks} "
                f"source_tracks={source_same_date_horse_tracks}"
            )
        track_text = ",".join(source_track_candidates)
        return "TRACK_ALIAS_MISSING", f"horse found on same date but not same canonical track source_tracks={track_text}"
    if source_race_count == 0:
        return "SOURCE_RACE_MISSING", "no V6.1 source race found for date+canonical_track"
    if source_runner_count == 0 and source_race_count > 0:
        return "RACE_NO_MISMATCH", (
            f"date+track exists in source but race_no runner missing settled_races={settled_race_count} source_races={source_race_count}"
        )
    if source_race_count != settled_race_count or source_runner_count != settled_runner_count:
        return "RACE_NO_MISMATCH", (
            f"race or runner counts mismatch settled_races={settled_race_count} source_races={source_race_count} "
            f"settled_runners={settled_runner_count} source_runners={source_runner_count}"
        )
    return "UNKNOWN", "no direct collision signature found"


def build_audit_rows() -> pd.DataFrame:
    settled_enriched, lookup, mapping_df, diagnostics = build_context()
    metrics = build_metrics_maps(settled_enriched, lookup)
    lookup_dates = sorted({clean(value) for value in lookup["meeting_date"].tolist() if clean(value) != ""})
    source_min_date = lookup_dates[0] if lookup_dates else ""
    source_max_date = lookup_dates[-1] if lookup_dates else ""

    rows: list[dict[str, object]] = []

    unmatched = diagnostics[diagnostics["source_match_stage_v2"].eq("UNMATCHED")].copy()
    for _, row in unmatched.iterrows():
        issue_type, issue_reason = classify_settled_unmatched(row, metrics)
        date_track_key = clean(row["meeting_date"]) + "|" + clean(row["track_norm_v2"])
        date_track_race_key = date_track_key + "|" + clean(row["race_no"])
        date_track_horse_key = date_track_key + "|" + clean(row["horse_key"])
        date_track_race_horse_key = date_track_race_key + "|" + clean(row["horse_key"])
        date_horse_key = clean(row["meeting_date"]) + "|" + clean(row["horse_key"])

        rows.append(
            {
                "record_scope_v1": "SETTLED_ROW",
                "issue_type": issue_type,
                "recoverable_flag_v1": recoverable_flag(issue_type),
                "meeting_date": clean(row["meeting_date"]),
                "canonical_track_v1": clean(row["track_canonical_v2"]),
                "settled_track_raw_v1": clean(row["track"]),
                "race_no": clean(row["race_no"]),
                "horse": clean(row["horse"]),
                "horse_key": clean(row["horse_key"]),
                "settled_race_key": clean(row["race_key"]),
                "source_race_key": clean(row["backtest_race_key"]),
                "source_race_no_inferred_v1": clean(row["inferred_race_no_v2"]),
                "track_alias_applied_settled_v2": clean(row["track_alias_applied_v2"]),
                "track_alias_applied_source_v2": clean(row["backtest_track_alias_applied_v2"]),
                "candidate_count_stage_1": int(row.get("candidate_count_stage_1", 0)),
                "candidate_count_stage_2": int(row.get("candidate_count_stage_2", 0)),
                "candidate_count_stage_3": int(row.get("candidate_count_stage_3", 0)),
                "candidate_count_stage_4": int(row.get("candidate_count_stage_4", 0)),
                "settled_same_date_track_horse_race_count": int(metrics["settled_same_track_horse_races"].get(date_track_horse_key, 0)),
                "source_same_date_track_horse_race_count": int(metrics["source_same_track_horse_races"].get(date_track_horse_key, 0)),
                "settled_same_date_horse_track_count": int(metrics["settled_same_date_horse_tracks"].get(date_horse_key, 0)),
                "source_same_date_horse_track_count": int(metrics["source_same_date_horse_tracks"].get(date_horse_key, 0)),
                "settled_duplicate_race_runner_count": int(metrics["settled_dup_race_runner"].get(date_track_race_horse_key, 0)),
                "source_duplicate_race_runner_count": int(metrics["source_dup_race_runner"].get(date_track_race_horse_key, 0)),
                "settled_race_count_date_track": int(metrics["settled_race_count_by_date_track"].get(date_track_key, 0)),
                "source_race_count_date_track": int(metrics["source_race_count_by_date_track"].get(date_track_key, 0)),
                "settled_runner_count_date_track_race": int(metrics["settled_runner_count_by_race"].get(date_track_race_key, 0)),
                "source_runner_count_date_track_race": int(metrics["source_runner_count_by_race"].get(date_track_race_key, 0)),
                "source_track_candidates_v1": ",".join(metrics["source_track_candidates"].get(date_horse_key, [])),
                "source_race_candidates_v1": ",".join(metrics["source_race_candidates"].get(date_track_horse_key, [])),
                "within_v6_source_date_range_v1": "YES" if source_min_date <= clean(row["meeting_date"]) <= source_max_date and source_min_date != "" else "NO",
                "issue_reason_v1": issue_reason,
                "built_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    source_problem_rows = mapping_df[mapping_df["race_mapping_status_v2"].map(clean) != "INFERRED_RACE_NO_OVERLAP_2_PLUS"].copy()
    for _, row in source_problem_rows.iterrows():
        mapping_status = clean(row["race_mapping_status_v2"])
        if mapping_status == "AMBIGUOUS_RACE_NO_MATCH":
            issue_type = "RACE_NO_MISMATCH"
            issue_reason = "source race could not be assigned to a single settled race number"
        elif mapping_status == "NO_SETTLED_RACE_FOR_DATE_TRACK":
            issue_type = "SETTLED_RACE_MISSING"
            issue_reason = "source backtest race exists with no settled date+track candidate"
        elif mapping_status == "NO_HORSE_OVERLAP":
            issue_type = "SETTLED_RACE_MISSING"
            issue_reason = "source backtest race has no horse overlap with settled date+track candidates"
        else:
            issue_type = "UNKNOWN"
            issue_reason = mapping_status or "unclassified source-side mapping issue"

        rows.append(
            {
                "record_scope_v1": "SOURCE_RACE",
                "issue_type": issue_type,
                "recoverable_flag_v1": recoverable_flag(issue_type),
                "meeting_date": clean(row["meeting_date"]),
                "canonical_track_v1": clean(row["track_norm_v2"]),
                "settled_track_raw_v1": "",
                "race_no": clean(row["inferred_race_no_v2"]),
                "horse": "",
                "horse_key": "",
                "settled_race_key": clean(row["mapped_settled_race_key_v2"]),
                "source_race_key": clean(row["backtest_race_key"]),
                "source_race_no_inferred_v1": clean(row["inferred_race_no_v2"]),
                "track_alias_applied_settled_v2": "",
                "track_alias_applied_source_v2": "",
                "candidate_count_stage_1": None,
                "candidate_count_stage_2": None,
                "candidate_count_stage_3": None,
                "candidate_count_stage_4": None,
                "settled_same_date_track_horse_race_count": None,
                "source_same_date_track_horse_race_count": None,
                "settled_same_date_horse_track_count": None,
                "source_same_date_horse_track_count": None,
                "settled_duplicate_race_runner_count": None,
                "source_duplicate_race_runner_count": None,
                "settled_race_count_date_track": int(row.get("candidate_settled_races_same_date_track", 0) or 0),
                "source_race_count_date_track": None,
                "settled_runner_count_date_track_race": None,
                "source_runner_count_date_track_race": int(row.get("backtest_field_size", 0) or 0),
                "source_track_candidates_v1": "",
                "source_race_candidates_v1": "",
                "within_v6_source_date_range_v1": "YES",
                "issue_reason_v1": issue_reason,
                "built_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    audit = pd.DataFrame(rows)
    if audit.empty:
        return audit

    issue_order_map = {value: idx for idx, value in enumerate(ISSUE_ORDER)}
    audit["_issue_order"] = audit["issue_type"].map(lambda value: issue_order_map.get(clean(value), 999))
    audit = audit.sort_values(
        ["_issue_order", "meeting_date", "canonical_track_v1", "race_no", "horse"],
        ascending=[True, True, True, True, True],
    ).drop(columns=["_issue_order"])
    return audit.reset_index(drop=True)


def build_summary(audit: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if audit.empty:
        return pd.DataFrame(
            [
                {
                    "section": "OVERALL",
                    "rank_v1": 1,
                    "label": "status",
                    "value": "NO_AUDIT_ROWS",
                    "issue_type": "",
                    "meeting_date": "",
                    "canonical_track_v1": "",
                    "race_no": "",
                    "horse": "",
                    "notes": "",
                }
            ]
        )

    rows.append(
        {
            "section": "OVERALL",
            "rank_v1": 1,
            "label": "audit_rows",
            "value": int(len(audit)),
            "issue_type": "",
            "meeting_date": "",
            "canonical_track_v1": "",
            "race_no": "",
            "horse": "",
            "notes": "all classified unmatched/collision rows",
        }
    )
    rows.append(
        {
            "section": "OVERALL",
            "rank_v1": 2,
            "label": "recoverable_rows_estimated_yes",
            "value": int(audit["recoverable_flag_v1"].eq("YES").sum()),
            "issue_type": "",
            "meeting_date": "",
            "canonical_track_v1": "",
            "race_no": "",
            "horse": "",
            "notes": "rows classified as likely recoverable",
        }
    )
    rows.append(
        {
            "section": "OVERALL",
            "rank_v1": 3,
            "label": "recoverable_rows_estimated_yes_or_maybe",
            "value": int(audit["recoverable_flag_v1"].isin(["YES", "MAYBE"]).sum()),
            "issue_type": "",
            "meeting_date": "",
            "canonical_track_v1": "",
            "race_no": "",
            "horse": "",
            "notes": "rows classified as recoverable or maybe recoverable",
        }
    )
    rows.append(
        {
            "section": "OVERALL",
            "rank_v1": 4,
            "label": "rows_within_v6_source_date_range",
            "value": int(audit["within_v6_source_date_range_v1"].eq("YES").sum()),
            "issue_type": "",
            "meeting_date": "",
            "canonical_track_v1": "",
            "race_no": "",
            "horse": "",
            "notes": "rows dated inside the current V6.1 source coverage window",
        }
    )
    rows.append(
        {
            "section": "OVERALL",
            "rank_v1": 5,
            "label": "recoverable_rows_within_v6_source_date_range",
            "value": int(
                (
                    audit["within_v6_source_date_range_v1"].eq("YES")
                    & audit["recoverable_flag_v1"].isin(["YES", "MAYBE"])
                ).sum()
            ),
            "issue_type": "",
            "meeting_date": "",
            "canonical_track_v1": "",
            "race_no": "",
            "horse": "",
            "notes": "recoverable rows dated inside the current V6.1 source coverage window",
        }
    )

    issue_counts = audit.groupby("issue_type", dropna=False).size().reset_index(name="rows").sort_values("rows", ascending=False)
    for idx, (_, row) in enumerate(issue_counts.iterrows(), start=1):
        rows.append(
            {
                "section": "ISSUE_TYPE_COUNT",
                "rank_v1": idx,
                "label": "rows",
                "value": int(row["rows"]),
                "issue_type": clean(row["issue_type"]),
                "meeting_date": "",
                "canonical_track_v1": "",
                "race_no": "",
                "horse": "",
                "notes": "",
            }
        )

    top_tracks = audit.groupby("canonical_track_v1", dropna=False).size().reset_index(name="rows").sort_values("rows", ascending=False).head(20)
    for idx, (_, row) in enumerate(top_tracks.iterrows(), start=1):
        rows.append(
            {
                "section": "TOP_TRACK",
                "rank_v1": idx,
                "label": "rows",
                "value": int(row["rows"]),
                "issue_type": "",
                "meeting_date": "",
                "canonical_track_v1": clean(row["canonical_track_v1"]),
                "race_no": "",
                "horse": "",
                "notes": "",
            }
        )

    top_dates = audit.groupby("meeting_date", dropna=False).size().reset_index(name="rows").sort_values("rows", ascending=False).head(20)
    for idx, (_, row) in enumerate(top_dates.iterrows(), start=1):
        rows.append(
            {
                "section": "TOP_DATE",
                "rank_v1": idx,
                "label": "rows",
                "value": int(row["rows"]),
                "issue_type": "",
                "meeting_date": clean(row["meeting_date"]),
                "canonical_track_v1": "",
                "race_no": "",
                "horse": "",
                "notes": "",
            }
        )

    examples = audit[
        (audit["within_v6_source_date_range_v1"].eq("YES"))
        & (audit["issue_type"] != "SOURCE_RACE_MISSING")
    ].copy()
    if examples.empty:
        examples = audit.copy()
    examples["_issue_count"] = examples["issue_type"].map(issue_counts.set_index("issue_type")["rows"].to_dict())
    examples = examples.sort_values(
        ["recoverable_flag_v1", "_issue_count", "issue_type", "meeting_date", "canonical_track_v1"],
        ascending=[True, False, True, True, True],
    ).head(20)
    for idx, (_, row) in enumerate(examples.iterrows(), start=1):
        rows.append(
            {
                "section": "TOP_EXAMPLE",
                "rank_v1": idx,
                "label": row["record_scope_v1"],
                "value": "",
                "issue_type": clean(row["issue_type"]),
                "meeting_date": clean(row["meeting_date"]),
                "canonical_track_v1": clean(row["canonical_track_v1"]),
                "race_no": clean(row["race_no"]),
                "horse": clean(row["horse"]),
                "notes": clean(row["issue_reason_v1"]),
            }
        )

    summary = pd.DataFrame(rows)
    return summary


def build_examples(audit: pd.DataFrame) -> pd.DataFrame:
    if audit.empty:
        return audit
    examples = []
    for issue_type in ISSUE_ORDER:
        subset = audit[audit["issue_type"].eq(issue_type)].copy()
        if subset.empty:
            continue
        subset = subset.sort_values(
            ["recoverable_flag_v1", "meeting_date", "canonical_track_v1", "race_no", "horse"],
            ascending=[True, True, True, True, True],
        ).head(15)
        subset["example_issue_rank_v1"] = range(1, len(subset) + 1)
        examples.append(subset)
    if not examples:
        return pd.DataFrame()
    return pd.concat(examples, ignore_index=True)


def main() -> None:
    audit = build_audit_rows()
    summary = build_summary(audit)
    examples = build_examples(audit)

    audit.to_csv(OUT_AUDIT, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    examples.to_csv(OUT_EXAMPLES, index=False)

    print("[EDGEIQ_V6_1_SETTLED_REPLAY_UNMATCHED_COLLISIONS_V1] COMPLETE")
    if not summary.empty:
        print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
