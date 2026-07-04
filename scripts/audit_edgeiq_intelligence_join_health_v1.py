from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Iterable

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

BASE_PATH = DATA / "edgeiq_live_runner_board_v1.csv"
OUT_PATH = DATA / "edgeiq_intelligence_join_health_v1.csv"
SUMMARY_PATH = DATA / "edgeiq_intelligence_join_health_summary_v1.csv"

SOURCE_FILES = {
    "runner_intelligence": DATA / "edgeiq_runner_intelligence_v1.csv",
    "horse_drawer_current": DATA / "edgeiq_horse_intelligence_drawer_current.csv",
    "runner_form_history": DATA / "runner_form_history.csv",
    "runner_history_detail": DATA / "edgeiq_runner_history_detail_v1.csv",
    "horse_career_intelligence": DATA / "edgeiq_horse_career_intelligence_v1.csv",
    "horse_archetype_engine": DATA / "edgeiq_horse_archetype_engine_v1.csv",
    "horse_trajectory_engine": DATA / "edgeiq_horse_trajectory_engine_v1.csv",
    "horse_projection_engine": DATA / "edgeiq_horse_projection_engine_v1.csv",
    "runner_profile_engine": DATA / "edgeiq_runner_profile_engine_current.csv",
    "runner_form_engine": DATA / "edgeiq_runner_form_engine_current.csv",
    "connection_intelligence": DATA / "edgeiq_connection_intelligence_v1.csv",
    "factor_scorecard": DATA / "edgeiq_live_runner_factor_scorecard_v2.csv",
    "explainability_terminal": DATA / "edgeiq_explainability_terminal_feed_v1_2.csv",
    "runner_dna_drawer": DATA / "edgeiq_runner_dna_drawer_feed_v2.csv",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    return text


def normalize_track(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean_text(value).upper())


def normalize_horse(value: object) -> str:
    text = clean_text(value).upper()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^A-Z0-9]+", "", text)
    text = re.sub(r"(NZ|GB|IRE|FR|USA|JPN|AUS)$", "", text)
    return text


def first_present(row: pd.Series, columns: Iterable[str]) -> str:
    for column in columns:
        if column in row.index:
            value = clean_text(row[column])
            if value:
                return value
    return ""


def truthy_flag(value: object) -> bool:
    return clean_text(value).upper() in {"1", "TRUE", "YES", "Y", "SCRATCHED"}


def parse_int(value: object) -> int | None:
    text = clean_text(value)
    if not text:
        return None
    match = re.search(r"-?\d+", text)
    if not match:
        return None
    try:
        return int(match.group(0))
    except ValueError:
        return None


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str).fillna("")


def build_base_rows() -> pd.DataFrame:
    base = load_csv(BASE_PATH)
    if base.empty:
        raise ValueError(f"Base runner board missing or empty: {BASE_PATH}")

    active_mask = ~base.apply(
        lambda row: (
            clean_text(row.get("runner_status", "")).upper() == "SCRATCHED"
            or truthy_flag(row.get("is_scratched", ""))
            or "SCRATCH" in clean_text(row.get("scratch_status", "")).upper()
        ),
        axis=1,
    )
    base = base.loc[active_mask].copy()
    base["race_date_norm"] = base["race_date"].map(clean_text)
    base["track_norm"] = base["track"].map(normalize_track)
    base["race_no_norm"] = base["race_no"].map(clean_text)
    base["horse_key_norm"] = base.apply(lambda row: normalize_horse(first_present(row, ["horse_key", "runner_key", "horse"])), axis=1)
    base["horse_norm"] = base["horse"].map(normalize_horse)
    base["runner_key_norm"] = base.apply(lambda row: normalize_horse(first_present(row, ["runner_key", "horse_key", "horse"])), axis=1)
    base["ctx_horse_key"] = base.apply(
        lambda row: "|".join([row["race_date_norm"], row["track_norm"], row["race_no_norm"], row["horse_key_norm"]]),
        axis=1,
    )
    base["ctx_horse"] = base.apply(
        lambda row: "|".join([row["race_date_norm"], row["track_norm"], row["race_no_norm"], row["horse_norm"]]),
        axis=1,
    )
    base["ctx_runner_key"] = base.apply(
        lambda row: "|".join([row["race_date_norm"], row["track_norm"], row["race_no_norm"], row["runner_key_norm"]]),
        axis=1,
    )
    base["ctx_nodate_horse_key"] = base.apply(
        lambda row: "|".join([row["track_norm"], row["race_no_norm"], row["horse_key_norm"]]),
        axis=1,
    )
    base["ctx_nodate_horse"] = base.apply(
        lambda row: "|".join([row["track_norm"], row["race_no_norm"], row["horse_norm"]]),
        axis=1,
    )
    return base


def prepare_source(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    prepared = df.copy()
    prepared["race_date_norm"] = prepared.apply(
        lambda row: first_present(row, ["race_date", "meeting_date", "run_date_iso", "run_date"]),
        axis=1,
    )
    prepared["track_norm"] = prepared.apply(
        lambda row: normalize_track(first_present(row, ["track", "meeting", "meeting_name"])),
        axis=1,
    )
    prepared["race_no_norm"] = prepared.apply(
        lambda row: first_present(row, ["race_no", "race_number", "race"]),
        axis=1,
    )
    prepared["horse_key_norm"] = prepared.apply(
        lambda row: normalize_horse(first_present(row, ["horse_key", "runner_key", "horse"])),
        axis=1,
    )
    prepared["horse_norm"] = prepared.apply(
        lambda row: normalize_horse(first_present(row, ["horse", "runner", "runner_name"])),
        axis=1,
    )
    prepared["runner_key_norm"] = prepared.apply(
        lambda row: normalize_horse(first_present(row, ["runner_key", "horse_key", "horse"])),
        axis=1,
    )
    return prepared


def key_sets_for_source(df: pd.DataFrame) -> tuple[dict[str, set[str]], list[str], list[str]]:
    if df.empty:
        return {}, [], []

    available_columns = list(df.columns)
    key_sets: dict[str, set[str]] = {}
    join_keys_used: list[str] = []

    def add_key(name: str, parts: list[str], required: list[str]) -> None:
        if any(column not in df.columns for column in required):
            return
        keys = set()
        for _, row in df.iterrows():
            values = [clean_text(row[part]) for part in parts]
            if all(values):
                keys.add("|".join(values))
        if keys:
            key_sets[name] = keys
            join_keys_used.append(name)

    add_key("DATE_TRACK_RACE_NO_RUNNER_KEY", ["race_date_norm", "track_norm", "race_no_norm", "runner_key_norm"], ["race_date_norm", "track_norm", "race_no_norm", "runner_key_norm"])
    add_key("DATE_TRACK_RACE_NO_HORSE_KEY", ["race_date_norm", "track_norm", "race_no_norm", "horse_key_norm"], ["race_date_norm", "track_norm", "race_no_norm", "horse_key_norm"])
    add_key("DATE_TRACK_RACE_NO_HORSE", ["race_date_norm", "track_norm", "race_no_norm", "horse_norm"], ["race_date_norm", "track_norm", "race_no_norm", "horse_norm"])
    add_key("TRACK_RACE_NO_HORSE_KEY", ["track_norm", "race_no_norm", "horse_key_norm"], ["track_norm", "race_no_norm", "horse_key_norm"])
    add_key("TRACK_RACE_NO_HORSE", ["track_norm", "race_no_norm", "horse_norm"], ["track_norm", "race_no_norm", "horse_norm"])
    add_key("HORSE_KEY_ONLY", ["horse_key_norm"], ["horse_key_norm"])

    return key_sets, join_keys_used, available_columns


def match_base_rows(base: pd.DataFrame, key_sets: dict[str, set[str]]) -> tuple[pd.Series, str]:
    matched_flags = []
    methods_used: dict[str, int] = {}

    for _, row in base.iterrows():
        matched = False
        checks = [
            ("DATE_TRACK_RACE_NO_RUNNER_KEY", clean_text(row["ctx_runner_key"])),
            ("DATE_TRACK_RACE_NO_HORSE_KEY", clean_text(row["ctx_horse_key"])),
            ("DATE_TRACK_RACE_NO_HORSE", clean_text(row["ctx_horse"])),
            ("TRACK_RACE_NO_HORSE_KEY", clean_text(row["ctx_nodate_horse_key"])),
            ("TRACK_RACE_NO_HORSE", clean_text(row["ctx_nodate_horse"])),
            ("HORSE_KEY_ONLY", clean_text(row["horse_key_norm"])),
        ]
        for method, key in checks:
            if key and method in key_sets and key in key_sets[method]:
                matched = True
                methods_used[method] = methods_used.get(method, 0) + 1
                break
        matched_flags.append(matched)

    methods_summary = "; ".join(f"{method}:{count}" for method, count in methods_used.items())
    return pd.Series(matched_flags, index=base.index), methods_summary


def infer_issue(path: Path, df: pd.DataFrame, match_pct: float, join_keys_used: list[str]) -> str:
    if not path.exists():
        return "MISSING_SOURCE_FILE"
    if df.empty:
        return "SOURCE_EMPTY"
    if not join_keys_used:
        return "NO_USABLE_JOIN_KEYS"
    if match_pct < 50:
        return "JOIN_FAILURE_SUSPECTED"
    if match_pct < 85:
        return "PARTIAL_COVERAGE_OR_SPARSE_SOURCE"
    return "HEALTHY"


def main() -> None:
    base = build_base_rows()
    built_at = now_iso()
    detail_rows: list[dict[str, object]] = []

    for source_name, path in SOURCE_FILES.items():
        df = load_csv(path)
        prepared = prepare_source(df)
        key_sets, join_keys_used, available_columns = key_sets_for_source(prepared)
        matched_flags, methods_summary = match_base_rows(base, key_sets) if key_sets else (pd.Series([False] * len(base), index=base.index), "")

        matched_rows = int(matched_flags.sum())
        unmatched_rows = int(len(base) - matched_rows)
        match_pct = round((matched_rows / len(base)) * 100, 2) if len(base) else 0.0
        unmatched_horses = (
            base.loc[~matched_flags, "horse"]
            .drop_duplicates()
            .head(8)
            .astype(str)
            .tolist()
        )
        status = "PASS" if match_pct >= 85 else "WARN" if match_pct >= 50 else "FAIL"
        suspected_issue = infer_issue(path, df, match_pct, join_keys_used)

        detail_rows.append(
            {
                "source_name": source_name,
                "base_rows": len(base),
                "source_rows": len(df),
                "matched_rows": matched_rows,
                "unmatched_rows": unmatched_rows,
                "match_pct": f"{match_pct:.2f}",
                "sample_unmatched_horses": " | ".join(unmatched_horses),
                "join_keys_used": " | ".join(join_keys_used) if join_keys_used else "NONE",
                "match_methods_hit": methods_summary or "NONE",
                "available_columns": " | ".join(available_columns[:20]) + (" | ..." if len(available_columns) > 20 else ""),
                "suspected_issue": suspected_issue,
                "status": status,
                "built_at": built_at,
            }
        )

    detail = pd.DataFrame(detail_rows)
    detail["match_pct_num"] = pd.to_numeric(detail["match_pct"], errors="coerce").fillna(0.0)
    detail = detail.sort_values(["status", "match_pct_num", "source_name"], ascending=[True, False, True])
    detail.to_csv(OUT_PATH, index=False)

    summary = pd.DataFrame(
        [
            {
                "status": "PASS" if int((detail["status"] == "FAIL").sum()) == 0 else "WARN",
                "base_active_rows": len(base),
                "sources_checked": len(detail),
                "pass_sources": int((detail["status"] == "PASS").sum()),
                "warn_sources": int((detail["status"] == "WARN").sum()),
                "fail_sources": int((detail["status"] == "FAIL").sum()),
                "lowest_match_source": detail.sort_values("match_pct_num", ascending=True).iloc[0]["source_name"] if not detail.empty else "",
                "lowest_match_pct": detail.sort_values("match_pct_num", ascending=True).iloc[0]["match_pct"] if not detail.empty else "",
                "highest_match_source": detail.sort_values("match_pct_num", ascending=False).iloc[0]["source_name"] if not detail.empty else "",
                "highest_match_pct": detail.sort_values("match_pct_num", ascending=False).iloc[0]["match_pct"] if not detail.empty else "",
                "built_at": built_at,
            }
        ]
    )
    summary.to_csv(SUMMARY_PATH, index=False)

    print(summary.to_string(index=False))
    print()
    print(detail[["source_name", "matched_rows", "unmatched_rows", "match_pct", "status", "suspected_issue"]].to_string(index=False))


if __name__ == "__main__":
    main()
