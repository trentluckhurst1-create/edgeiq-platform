from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RANK1_SRC = DATA / "edgeiq_rank1_failure_audit_v1.csv"
RESULTS_SRC = DATA / "edgeiq_racingcom_results_warehouse_v1.csv"
ENV_SRC = DATA / "edgeiq_environment_score_replay_v1.csv"

OUT = DATA / "edgeiq_rank1_sp_history_v1.csv"
SUMMARY = DATA / "edgeiq_rank1_sp_history_v1_summary.csv"
UNMATCHED = DATA / "edgeiq_rank1_sp_history_v1_unmatched.csv"


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def normalise_text(value: object) -> str:
    text = clean_text(value).upper()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\([^)]*\)", " ", text)
    text = text.replace("&", " AND ")
    text = re.sub(r"['`’]", "", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalise_horse_key(value: object) -> str:
    return normalise_text(value).replace(" ", "")


def clean_race_no(value: object) -> str:
    match = re.search(r"\d+", clean_text(value))
    return str(int(match.group(0))) if match else ""


def parse_track_from_race_key(value: object) -> str:
    parts = clean_text(value).split("|")
    if len(parts) >= 2:
        return parts[1]
    return ""


def normalise_track(value: object) -> str:
    text = normalise_text(value)
    text = re.sub(r"\bSPORTS\s*BET\b", "SPORTSBET", text)
    text = re.sub(r"\bBET365\b|\bLADBROKES\b|\bSPORTSBET\b|\bAPIAM\b|\bTAB\b|\bHYLANDS\b|\bCRANBOURNE\b(?=\s*RACECOURSE\b)", " ", text)
    text = re.sub(r"\bRACECOURSE\b|\bRACING\b|\bCLUB\b|\bTURF\b|\bPARK\b(?=\s*KILMORE\b)|\bTHE\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalise_date(value: object) -> str:
    text = clean_text(value)
    if not text:
        return ""
    try:
        return pd.to_datetime(text).strftime("%Y-%m-%d")
    except Exception:
        return text


def parse_sp(value: object) -> float | None:
    text = clean_text(value)
    if not text:
        return None
    text = text.replace("$", "").replace(",", "").replace("â€“", "").replace("–", "")
    text = text.strip()
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        return None


def is_missing_number(value: object) -> bool:
    return value is None or pd.isna(value)


def build_match_keys(date_key: str, race_no_key: str, track_values: list[str], horse_values: list[str]) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()
    for track_key in track_values:
        if not track_key:
            continue
        for horse_key in horse_values:
            if not horse_key:
                continue
            key = "|".join([date_key, track_key, race_no_key, horse_key])
            if key not in seen:
                seen.add(key)
                keys.append(key)
    return keys


def enrich_environment(rank1: pd.DataFrame) -> pd.DataFrame:
    if not ENV_SRC.exists():
        rank1["environment_score_v1"] = ""
        rank1["environment_band_v1"] = ""
        return rank1

    env = pd.read_csv(ENV_SRC, low_memory=False)
    env_keep = [
        "join_key_v1",
        "environment_score_v1",
        "environment_band_v1",
    ]
    env_keep = [col for col in env_keep if col in env.columns]
    if not env_keep:
        rank1["environment_score_v1"] = ""
        rank1["environment_band_v1"] = ""
        return rank1

    env_small = env[env_keep].copy().drop_duplicates("join_key_v1")
    merged = rank1.merge(env_small, on="join_key_v1", how="left", suffixes=("", "_env"))

    if "environment_score_v1" not in merged.columns:
        merged["environment_score_v1"] = ""
    if "environment_band_v1" not in merged.columns:
        merged["environment_band_v1"] = ""

    merged["environment_score_v1"] = merged["environment_score_v1"].fillna("")
    merged["environment_band_v1"] = merged["environment_band_v1"].fillna("")
    return merged


def build_results_index(results: pd.DataFrame) -> dict[str, dict[str, object]]:
    records: list[dict[str, object]] = []

    for _, row in results.iterrows():
        date_key = normalise_date(row.get("meeting_date"))
        race_no_key = clean_race_no(row.get("race_no"))
        track_primary = normalise_track(row.get("track"))
        track_racekey = normalise_track(parse_track_from_race_key(row.get("race_key")))
        horse_key = normalise_horse_key(row.get("horseKey")) or normalise_horse_key(row.get("horseName")) or normalise_horse_key(row.get("horse"))
        horse_name_key = normalise_horse_key(row.get("horseName")) or normalise_horse_key(row.get("horse"))

        match_variants = [
            (1, track_primary, horse_key),
            (2, track_primary, horse_name_key),
            (3, track_racekey, horse_key),
            (4, track_racekey, horse_name_key),
        ]

        base_record = {
            "finishPosition": row.get("finishPosition"),
            "horseName": row.get("horseName"),
            "horseKey": row.get("horseKey"),
            "sp": row.get("sp"),
            "sp_num_v1": parse_sp(row.get("sp")),
            "track": row.get("track"),
            "race_key": row.get("race_key"),
        }

        for priority, track_key, horse_key_variant in match_variants:
            if not date_key or not race_no_key or not track_key or not horse_key_variant:
                continue
            match_key = "|".join([date_key, track_key, race_no_key, horse_key_variant])
            record = dict(base_record)
            record["match_priority_v1"] = priority
            record["match_key_v1"] = match_key
            records.append(record)

    if not records:
        return {}

    index_df = pd.DataFrame(records)
    index_df = index_df.sort_values(["match_priority_v1", "match_key_v1"]).drop_duplicates("match_key_v1", keep="first")
    return {row["match_key_v1"]: row.to_dict() for _, row in index_df.iterrows()}


def main() -> None:
    if not RANK1_SRC.exists():
        raise SystemExit("Missing edgeiq_rank1_failure_audit_v1.csv")
    if not RESULTS_SRC.exists():
        raise SystemExit("Missing edgeiq_racingcom_results_warehouse_v1.csv")

    rank1 = pd.read_csv(RANK1_SRC, low_memory=False)
    results = pd.read_csv(RESULTS_SRC, low_memory=False)

    required_rank1 = [
        "join_key_v1",
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "rank1_horse",
        "rank1_horse_key",
        "rank1_won",
        "rank1_finish_position",
        "trust_profile_v1",
        "field_size",
        "score_share_band",
        "rank1_score_share_of_race",
        "rank1_dominance_band_v1",
        "rank1_dominance_score_v1",
    ]
    missing_rank1 = [col for col in required_rank1 if col not in rank1.columns]
    if missing_rank1:
        raise SystemExit("Rank1 source missing columns: " + ", ".join(missing_rank1))

    required_results = ["meeting_date", "track", "race_no", "horseName", "horseKey", "finishPosition", "sp"]
    missing_results = [col for col in required_results if col not in results.columns]
    if missing_results:
        raise SystemExit("Results warehouse missing columns: " + ", ".join(missing_results))

    rank1 = enrich_environment(rank1.copy())

    results_index = build_results_index(results)

    output_rows: list[dict[str, object]] = []
    unresolved_rows: list[dict[str, object]] = []

    for _, row in rank1.iterrows():
        date_key = normalise_date(row.get("meeting_date"))
        race_no_key = clean_race_no(row.get("race_no"))
        track_primary = normalise_track(row.get("track"))
        track_racekey = normalise_track(parse_track_from_race_key(row.get("race_key")))
        horse_key = normalise_horse_key(row.get("rank1_horse_key")) or normalise_horse_key(row.get("rank1_horse"))
        horse_name_key = normalise_horse_key(row.get("rank1_horse"))

        match_keys = build_match_keys(
            date_key,
            race_no_key,
            [track_primary, track_racekey],
            [horse_key, horse_name_key],
        )

        matched = None
        for match_key in match_keys:
            matched = results_index.get(match_key)
            if matched is not None:
                break

        if matched is None:
            sp_join_status = "UNMATCHED"
            sp_raw = ""
            sp_num = None
            finish_position = row.get("rank1_finish_position")
            won = row.get("rank1_won")
        else:
            sp_raw = matched.get("sp", "")
            sp_num = matched.get("sp_num_v1")
            finish_position = matched.get("finishPosition")
            try:
                won = 1 if int(float(finish_position)) == 1 else 0
            except Exception:
                won = row.get("rank1_won")

            if is_missing_number(sp_num):
                sp_join_status = "MATCHED_NO_SP"
            elif float(sp_num) > 1:
                sp_join_status = "MATCHED_VALID_SP"
            else:
                sp_join_status = "MATCHED_INVALID_SP"

        sp_valid = bool((not is_missing_number(sp_num)) and float(sp_num) > 1)

        out_row = {
            "join_key_v1": row.get("join_key_v1"),
            "meeting_date": row.get("meeting_date"),
            "track": row.get("track"),
            "race_no": row.get("race_no"),
            "race_key": row.get("race_key"),
            "rank1_horse": row.get("rank1_horse"),
            "rank1_horse_key": row.get("rank1_horse_key"),
            "rank1_won": won,
            "rank1_finish_position": finish_position,
            "environment_score_v1": row.get("environment_score_v1", ""),
            "environment_band_v1": row.get("environment_band_v1", ""),
            "sp": sp_raw,
            "sp_num_v1": sp_num if sp_num is not None else "",
            "sp_valid_v1": sp_valid,
            "sp_join_status_v1": sp_join_status,
            "trust_profile_v1": row.get("trust_profile_v1"),
            "field_size": row.get("field_size"),
            "score_share_band": row.get("score_share_band"),
            "rank1_score_share_of_race": row.get("rank1_score_share_of_race"),
            "rank1_dominance_band_v1": row.get("rank1_dominance_band_v1"),
            "rank1_dominance_score_v1": row.get("rank1_dominance_score_v1"),
        }
        output_rows.append(out_row)

        if sp_join_status != "MATCHED_VALID_SP":
            unresolved_rows.append(out_row)

    out_df = pd.DataFrame(output_rows)
    unresolved_df = pd.DataFrame(unresolved_rows)

    total_rows = len(out_df)
    matched_rows = int((out_df["sp_join_status_v1"] != "UNMATCHED").sum())
    unmatched_rows = int((out_df["sp_join_status_v1"] == "UNMATCHED").sum())
    valid_sp_rows = int(out_df["sp_valid_v1"].sum())
    valid_sp_winners = int(((pd.to_numeric(out_df["rank1_won"], errors="coerce").fillna(0) == 1) & out_df["sp_valid_v1"]).sum())
    winner_rows = int((pd.to_numeric(out_df["rank1_won"], errors="coerce").fillna(0) == 1).sum())

    summary_df = pd.DataFrame(
        [
            {"metric": "rank1_rows", "value": total_rows},
            {"metric": "matched_results_rows", "value": matched_rows},
            {"metric": "unmatched_results_rows", "value": unmatched_rows},
            {"metric": "valid_sp_rows", "value": valid_sp_rows},
            {"metric": "sp_coverage_pct", "value": round((valid_sp_rows / total_rows * 100) if total_rows else 0, 2)},
            {"metric": "winner_rows", "value": winner_rows},
            {"metric": "winner_valid_sp_rows", "value": valid_sp_winners},
            {"metric": "winner_sp_coverage_pct", "value": round((valid_sp_winners / winner_rows * 100) if winner_rows else 0, 2)},
            {"metric": "matched_no_sp_rows", "value": int((out_df["sp_join_status_v1"] == "MATCHED_NO_SP").sum())},
            {"metric": "matched_invalid_sp_rows", "value": int((out_df["sp_join_status_v1"] == "MATCHED_INVALID_SP").sum())},
            {"metric": "assumption_note", "value": "Environment score fields enriched from edgeiq_environment_score_replay_v1.csv because they are not present in edgeiq_rank1_failure_audit_v1.csv."},
        ]
    )

    out_df.to_csv(OUT, index=False)
    summary_df.to_csv(SUMMARY, index=False)
    unresolved_df.to_csv(UNMATCHED, index=False)

    print("[EDGEIQ_RANK1_SP_HISTORY_V1] COMPLETE")
    print(f"rank1_rows={total_rows}")
    print(f"valid_sp_rows={valid_sp_rows}")
    print(f"sp_coverage_pct={round((valid_sp_rows / total_rows * 100) if total_rows else 0, 2)}")
    print(f"wrote={OUT}")
    print(f"wrote={SUMMARY}")
    print(f"wrote={UNMATCHED}")


if __name__ == "__main__":
    main()
