from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_PATH = DATA / "edgeiq_live_runner_board_v1.csv"
CAMPAIGN_PATH = DATA / "edgeiq_campaign_intelligence_engine_v1_1.csv"

OUT_AUDIT_PATH = DATA / "edgeiq_campaign_frontend_join_audit_v1.csv"
OUT_SUMMARY_PATH = DATA / "edgeiq_campaign_frontend_join_audit_v1_summary.csv"

BUILT_AT = datetime.now(timezone.utc).isoformat()


def text(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def normalize_track(value) -> str:
    return re.sub(r"[^A-Z0-9]+", "", text(value).upper())


def normalize_horse(value) -> str:
    base = text(value).upper()
    base = re.sub(r"\([^)]*\)", "", base)
    return re.sub(r"[^A-Z0-9]+", "", base)


def normalize_horse_loose(value) -> str:
    base = normalize_horse(value)
    return re.sub(r"(NZ|GB|IRE|FR|USA|JPN|AUS)$", "", base)


def race_date_live(row: pd.Series) -> str:
    for key in ["race_date", "meeting_date", "date", "raceDate"]:
        value = text(row.get(key))
        if value:
            return value
    return ""


def race_date_campaign_for_frontend(row: pd.Series) -> str:
    # Mimics current frontend raceDate(row) helper, which does not include current_race_date.
    for key in ["race_date", "meeting_date", "date", "raceDate"]:
        value = text(row.get(key))
        if value:
            return value
    return ""


def race_date_campaign_recommended(row: pd.Series) -> str:
    for key in ["current_race_date", "race_date", "meeting_date", "date", "raceDate"]:
        value = text(row.get(key))
        if value:
            return value
    return ""


def race_no_value(row: pd.Series) -> str:
    for key in ["race_no", "raceNo", "race_number", "race"]:
        value = text(row.get(key))
        if value:
            return value
    return ""


def track_value(row: pd.Series) -> str:
    for key in ["track", "meeting", "meeting_name"]:
        value = text(row.get(key))
        if value:
            return value
    return ""


def horse_value(row: pd.Series) -> str:
    for key in ["horse", "horseName", "runner", "runner_name"]:
        value = text(row.get(key))
        if value:
            return value
    return ""


def horse_key_value(row: pd.Series) -> str:
    for key in ["horse_key", "horseKey", "runner_key", "runnerKey"]:
        value = text(row.get(key))
        if value:
            return value
    return ""


def is_active_live(row: pd.Series) -> bool:
    runner_status = text(row.get("runner_status")).upper()
    is_scratched = text(row.get("is_scratched")).upper()
    if runner_status == "SCRATCHED":
        return False
    if is_scratched in {"TRUE", "1", "YES"}:
        return False
    return True


def same_runner_frontend(live_row: pd.Series, campaign_row: pd.Series) -> bool:
    live_runner_key = text(live_row.get("runner_key") or live_row.get("runnerKey"))
    campaign_runner_key = text(campaign_row.get("runner_key") or campaign_row.get("runnerKey"))
    if live_runner_key and campaign_runner_key and live_runner_key == campaign_runner_key:
        return True

    live_race_key = text(live_row.get("race_key") or live_row.get("raceKey"))
    campaign_race_key = text(campaign_row.get("race_key") or campaign_row.get("raceKey"))
    live_horse_key = normalize_horse(live_row.get("horse_key") or live_row.get("horseKey"))
    campaign_horse_key = normalize_horse(campaign_row.get("horse_key") or campaign_row.get("horseKey"))
    if live_race_key and campaign_race_key and live_horse_key and campaign_horse_key and live_race_key == campaign_race_key and live_horse_key == campaign_horse_key:
        return True

    live_date = race_date_live(live_row)
    campaign_date = race_date_campaign_for_frontend(campaign_row)
    if live_date and campaign_date and live_date != campaign_date:
        return False
    if normalize_track(track_value(live_row)) != normalize_track(track_value(campaign_row)):
        return False
    if race_no_value(live_row) != race_no_value(campaign_row):
        return False

    live_tokens = {
        normalize_horse(live_row.get("horse_key")),
        normalize_horse(live_row.get("horse_canon")),
        normalize_horse(horse_value(live_row)),
        normalize_horse_loose(live_row.get("horse_key")),
        normalize_horse_loose(live_row.get("horse_canon")),
        normalize_horse_loose(horse_value(live_row)),
    }
    campaign_tokens = {
        normalize_horse(campaign_row.get("horse_key")),
        normalize_horse(campaign_row.get("horse_canon")),
        normalize_horse(horse_value(campaign_row)),
        normalize_horse_loose(campaign_row.get("horse_key")),
        normalize_horse_loose(campaign_row.get("horse_canon")),
        normalize_horse_loose(horse_value(campaign_row)),
    }
    live_tokens.discard("")
    campaign_tokens.discard("")
    return bool(live_tokens & campaign_tokens)


def determine_issue(row: dict) -> str:
    if row["frontend_style_match_count"] > 0:
        return "FRONTEND_STYLE_JOIN_OK"
    if row["recommended_join_match_count"] > 0 and row["frontend_style_match_count"] == 0:
        return "FRONTEND_JOIN_MISMATCH"
    if row["cleaned_date_track_race_horse_match_count"] > 0:
        return "HORSE_NORMALIZATION_ISSUE"
    if row["same_date_track_race_campaign_rows"] == 0 and row["same_track_race_horse_any_date_count"] > 0:
        return "STALE_FILE_OR_DATE_MISMATCH"
    if row["same_date_track_horse_any_race_count"] > 0:
        return "RACE_MISMATCH"
    if row["horse_only_match_count"] > 0:
        return "TRACK_MISMATCH"
    return "NO_CAMPAIGN_MATCH_FOUND"


def main() -> None:
    if not LIVE_PATH.exists():
        raise FileNotFoundError(f"Missing live runner board: {LIVE_PATH}")
    if not CAMPAIGN_PATH.exists():
        raise FileNotFoundError(f"Missing campaign file: {CAMPAIGN_PATH}")

    live = pd.read_csv(LIVE_PATH, low_memory=False)
    campaign = pd.read_csv(CAMPAIGN_PATH, low_memory=False)

    active_live = live[live.apply(is_active_live, axis=1)].copy()

    active_live["audit_race_date"] = active_live.apply(race_date_live, axis=1)
    active_live["audit_track"] = active_live.apply(track_value, axis=1)
    active_live["audit_race_no"] = active_live.apply(race_no_value, axis=1)
    active_live["audit_horse"] = active_live.apply(horse_value, axis=1)
    active_live["audit_horse_key"] = active_live.apply(horse_key_value, axis=1)
    active_live["audit_track_norm"] = active_live["audit_track"].map(normalize_track)
    active_live["audit_horse_norm"] = active_live["audit_horse"].map(normalize_horse)
    active_live["audit_horse_loose"] = active_live["audit_horse"].map(normalize_horse_loose)
    active_live["audit_horse_key_norm"] = active_live["audit_horse_key"].map(normalize_horse)

    campaign["audit_race_date_frontend"] = campaign.apply(race_date_campaign_for_frontend, axis=1)
    campaign["audit_race_date_recommended"] = campaign.apply(race_date_campaign_recommended, axis=1)
    campaign["audit_track"] = campaign.apply(track_value, axis=1)
    campaign["audit_race_no"] = campaign.apply(race_no_value, axis=1)
    campaign["audit_horse"] = campaign.apply(horse_value, axis=1)
    campaign["audit_horse_key"] = campaign.apply(horse_key_value, axis=1)
    campaign["audit_track_norm"] = campaign["audit_track"].map(normalize_track)
    campaign["audit_horse_norm"] = campaign["audit_horse"].map(normalize_horse)
    campaign["audit_horse_loose"] = campaign["audit_horse"].map(normalize_horse_loose)
    campaign["audit_horse_key_norm"] = campaign["audit_horse_key"].map(normalize_horse)

    audit_rows: list[dict] = []

    for _, live_row in active_live.sort_values(["audit_race_date", "audit_track", "audit_race_no", "audit_horse"]).iterrows():
        same_date_track_race = campaign[
            (campaign["audit_race_date_recommended"] == live_row["audit_race_date"])
            & (campaign["audit_track_norm"] == live_row["audit_track_norm"])
            & (campaign["audit_race_no"] == live_row["audit_race_no"])
        ].copy()

        exact_track_race_horse_key = same_date_track_race[
            (same_date_track_race["audit_track"] == live_row["audit_track"])
            & (same_date_track_race["audit_horse_key"] == live_row["audit_horse_key"])
            & (same_date_track_race["audit_horse_key"] != "")
        ]

        exact_track_race_horse = same_date_track_race[
            (same_date_track_race["audit_track"] == live_row["audit_track"])
            & (same_date_track_race["audit_horse"] == live_row["audit_horse"])
        ]

        cleaned_date_track_race_horse = same_date_track_race[
            (
                (
                    (same_date_track_race["audit_horse_key_norm"] != "")
                    & (same_date_track_race["audit_horse_key_norm"] == live_row["audit_horse_key_norm"])
                )
                | (same_date_track_race["audit_horse_norm"] == live_row["audit_horse_norm"])
                | (same_date_track_race["audit_horse_loose"] == live_row["audit_horse_loose"])
            )
        ]

        same_date_track_horse_any_race = campaign[
            (campaign["audit_race_date_recommended"] == live_row["audit_race_date"])
            & (campaign["audit_track_norm"] == live_row["audit_track_norm"])
            & (
                (
                    (campaign["audit_horse_key_norm"] != "")
                    & (campaign["audit_horse_key_norm"] == live_row["audit_horse_key_norm"])
                )
                | (campaign["audit_horse_norm"] == live_row["audit_horse_norm"])
                | (campaign["audit_horse_loose"] == live_row["audit_horse_loose"])
            )
        ]

        same_track_race_horse_any_date = campaign[
            (campaign["audit_track_norm"] == live_row["audit_track_norm"])
            & (campaign["audit_race_no"] == live_row["audit_race_no"])
            & (
                (
                    (campaign["audit_horse_key_norm"] != "")
                    & (campaign["audit_horse_key_norm"] == live_row["audit_horse_key_norm"])
                )
                | (campaign["audit_horse_norm"] == live_row["audit_horse_norm"])
                | (campaign["audit_horse_loose"] == live_row["audit_horse_loose"])
            )
        ]

        horse_only = campaign[
            (
                (
                    (campaign["audit_horse_key_norm"] != "")
                    & (campaign["audit_horse_key_norm"] == live_row["audit_horse_key_norm"])
                )
                | (campaign["audit_horse_norm"] == live_row["audit_horse_norm"])
                | (campaign["audit_horse_loose"] == live_row["audit_horse_loose"])
            )
        ]

        frontend_style = campaign[campaign.apply(lambda row: same_runner_frontend(live_row, row), axis=1)]

        recommended_join = same_date_track_race[
            (
                (
                    (same_date_track_race["audit_horse_key_norm"] != "")
                    & (same_date_track_race["audit_horse_key_norm"] == live_row["audit_horse_key_norm"])
                )
                | (same_date_track_race["audit_horse_loose"] == live_row["audit_horse_loose"])
            )
        ]

        preferred_match = None
        for frame in [frontend_style, recommended_join, cleaned_date_track_race_horse, horse_only]:
            if not frame.empty:
                preferred_match = frame.iloc[0]
                break

        audit_row = {
            "race_date": live_row["audit_race_date"],
            "track": live_row["audit_track"],
            "race_no": live_row["audit_race_no"],
            "horse": live_row["audit_horse"],
            "horse_key": live_row["audit_horse_key"],
            "same_date_track_race_campaign_rows": int(len(same_date_track_race)),
            "exact_track_race_horse_key_match_count": int(len(exact_track_race_horse_key)),
            "exact_track_race_horse_match_count": int(len(exact_track_race_horse)),
            "cleaned_date_track_race_horse_match_count": int(len(cleaned_date_track_race_horse)),
            "frontend_style_match_count": int(len(frontend_style)),
            "recommended_join_match_count": int(len(recommended_join)),
            "same_date_track_horse_any_race_count": int(len(same_date_track_horse_any_race)),
            "same_track_race_horse_any_date_count": int(len(same_track_race_horse_any_date)),
            "horse_only_match_count": int(len(horse_only)),
            "matched_campaign_date": text(preferred_match["audit_race_date_recommended"]) if preferred_match is not None else "",
            "matched_campaign_track": text(preferred_match["audit_track"]) if preferred_match is not None else "",
            "matched_campaign_race_no": text(preferred_match["audit_race_no"]) if preferred_match is not None else "",
            "matched_campaign_horse": text(preferred_match["audit_horse"]) if preferred_match is not None else "",
            "matched_campaign_horse_key": text(preferred_match["audit_horse_key"]) if preferred_match is not None else "",
            "matched_campaign_evidence_status": text(preferred_match.get("evidence_status")) if preferred_match is not None else "",
            "matched_campaign_history_runs_used": text(preferred_match.get("history_runs_used")) if preferred_match is not None else "",
            "issue_type": "",
            "suspected_reason": "",
            "built_at": BUILT_AT,
        }
        audit_row["issue_type"] = determine_issue(audit_row)

        if audit_row["issue_type"] == "FRONTEND_STYLE_JOIN_OK":
            audit_row["suspected_reason"] = "Current frontend-style join finds a match."
        elif audit_row["issue_type"] == "FRONTEND_JOIN_MISMATCH":
            audit_row["suspected_reason"] = "Explicit date-aware join works, but current frontend-style join misses."
        elif audit_row["issue_type"] == "HORSE_NORMALIZATION_ISSUE":
            audit_row["suspected_reason"] = "Race match exists but only cleaned horse normalization finds it."
        elif audit_row["issue_type"] == "STALE_FILE_OR_DATE_MISMATCH":
            audit_row["suspected_reason"] = "Horse matches same track/race on a different date."
        elif audit_row["issue_type"] == "RACE_MISMATCH":
            audit_row["suspected_reason"] = "Horse matches same date/track but race number differs."
        elif audit_row["issue_type"] == "TRACK_MISMATCH":
            audit_row["suspected_reason"] = "Horse appears in campaign file but not on the same track/race context."
        else:
            audit_row["suspected_reason"] = "No safe campaign-side match found."

        audit_rows.append(audit_row)

    audit_df = pd.DataFrame(audit_rows)
    audit_df.to_csv(OUT_AUDIT_PATH, index=False)

    active_count = len(active_live)
    campaign_count = len(campaign)
    frontend_matches = int((audit_df["frontend_style_match_count"] > 0).sum())
    recommended_matches = int((audit_df["recommended_join_match_count"] > 0).sum())
    cleaned_matches = int((audit_df["cleaned_date_track_race_horse_match_count"] > 0).sum())
    horse_only_matches = int((audit_df["horse_only_match_count"] > 0).sum())
    exact_key_matches = int((audit_df["exact_track_race_horse_key_match_count"] > 0).sum())
    exact_horse_matches = int((audit_df["exact_track_race_horse_match_count"] > 0).sum())

    active_race_groups = {
        (text(row["audit_race_date"]), normalize_track(row["audit_track"]), text(row["audit_race_no"]))
        for _, row in active_live.iterrows()
    }
    campaign_race_groups = {
        (text(row["audit_race_date_recommended"]), normalize_track(row["audit_track"]), text(row["audit_race_no"]))
        for _, row in campaign.iterrows()
    }
    stale_file_flag = "YES" if active_race_groups != campaign_race_groups else "NO"

    issue_counts = audit_df["issue_type"].value_counts().to_dict()
    unmatched_examples = audit_df[audit_df["frontend_style_match_count"] == 0][["race_date", "track", "race_no", "horse", "issue_type"]].head(20)
    unmatched_text = "; ".join(
        f"{row.race_date} {row.track} R{row.race_no} {row.horse} [{row.issue_type}]"
        for row in unmatched_examples.itertuples(index=False)
    )

    if frontend_matches == active_count and stale_file_flag == "NO":
        diagnosis = "NOT_STALE_FRONTEND_JOIN_HEALTHY"
        root_cause = "Current files support 100% frontend-style joins. If UI shows 0/N, the likely cause is stale browser/runtime state or a page that has not reloaded the latest build/data."
    elif recommended_matches == active_count and frontend_matches < active_count:
        diagnosis = "FRONTEND_JOIN_MISMATCH"
        root_cause = "Explicit campaign join works, but the current frontend-style matcher misses rows."
    elif stale_file_flag == "YES":
        diagnosis = "STALE_OR_MISALIGNED_FILE"
        root_cause = "Active live race groups do not match campaign race groups."
    else:
        diagnosis = "PARTIAL_JOIN_HEALTH"
        root_cause = "Join health is partial and needs targeted review of unmatched rows."

    recommended_key_strategy = (
        "Use explicit campaign join key: "
        "live.race_date == campaign.current_race_date "
        "AND cleanTrack(track) "
        "AND race_no "
        "AND cleanHorse(horse_key || horse) "
        "with fallback to cleanHorseLoose(horse) only when horse_key is missing. "
        "Do not rely on the generic raceDate() helper for campaign rows, because the campaign feed uses current_race_date rather than race_date."
    )

    summary_rows = [
        {
            "record_type": "OVERALL",
            "scope": "ALL_ACTIVE_RUNNERS",
            "active_runner_count": int(active_count),
            "campaign_row_count": int(campaign_count),
            "exact_track_race_horse_key_matches": int(exact_key_matches),
            "exact_track_race_horse_matches": int(exact_horse_matches),
            "cleaned_date_track_race_horse_matches": int(cleaned_matches),
            "frontend_style_matches": int(frontend_matches),
            "recommended_join_matches": int(recommended_matches),
            "horse_only_matches": int(horse_only_matches),
            "frontend_style_join_success_pct": round(frontend_matches / active_count * 100, 2) if active_count else 0.0,
            "recommended_join_success_pct": round(recommended_matches / active_count * 100, 2) if active_count else 0.0,
            "stale_file_flag": stale_file_flag,
            "diagnosis": diagnosis,
            "root_cause": root_cause,
            "issue_type_counts": "; ".join(f"{key}={value}" for key, value in sorted(issue_counts.items())),
            "sample_unmatched": unmatched_text,
            "recommended_key_strategy": recommended_key_strategy,
            "built_at": BUILT_AT,
        }
    ]

    for (race_date_value, track_norm, race_no_raw), group in audit_df.groupby(["race_date", audit_df["track"].map(normalize_track), "race_no"], dropna=False):
        track_display = group["track"].iloc[0] if not group.empty else track_norm
        frontend_group_matches = int((group["frontend_style_match_count"] > 0).sum())
        recommended_group_matches = int((group["recommended_join_match_count"] > 0).sum())
        summary_rows.append(
            {
                "record_type": "RACE",
                "scope": f"{race_date_value}|{track_display}|R{race_no_raw}",
                "active_runner_count": int(len(group)),
                "campaign_row_count": int(group["same_date_track_race_campaign_rows"].max()),
                "exact_track_race_horse_key_matches": int((group["exact_track_race_horse_key_match_count"] > 0).sum()),
                "exact_track_race_horse_matches": int((group["exact_track_race_horse_match_count"] > 0).sum()),
                "cleaned_date_track_race_horse_matches": int((group["cleaned_date_track_race_horse_match_count"] > 0).sum()),
                "frontend_style_matches": int(frontend_group_matches),
                "recommended_join_matches": int(recommended_group_matches),
                "horse_only_matches": int((group["horse_only_match_count"] > 0).sum()),
                "frontend_style_join_success_pct": round(frontend_group_matches / len(group) * 100, 2) if len(group) else 0.0,
                "recommended_join_success_pct": round(recommended_group_matches / len(group) * 100, 2) if len(group) else 0.0,
                "stale_file_flag": "YES" if int(group["same_date_track_race_campaign_rows"].max()) == 0 else "NO",
                "diagnosis": "FRONTEND_JOIN_OK" if frontend_group_matches == len(group) else "CHECK_RACE",
                "root_cause": "",
                "issue_type_counts": "; ".join(f"{key}={value}" for key, value in sorted(group["issue_type"].value_counts().to_dict().items())),
                "sample_unmatched": "; ".join(group.loc[group["frontend_style_match_count"] == 0, "horse"].head(10).tolist()),
                "recommended_key_strategy": "",
                "built_at": BUILT_AT,
            }
        )

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(OUT_SUMMARY_PATH, index=False)

    print("[CAMPAIGN_FRONTEND_JOIN_AUDIT_V1] COMPLETE")
    print(f"audit={OUT_AUDIT_PATH}")
    print(f"summary={OUT_SUMMARY_PATH}")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
