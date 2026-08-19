from __future__ import annotations

import importlib.util
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
BASE_CHECKPOINT_PATH = ROOT / "scripts" / "build_edgeiq_runner_history_detail_v1_CHECKPOINT_BEFORE_FIGURE_RECOVERY_20260625.py"
TRACK_ALIAS_PATH = DATA / "edgeiq_track_alias_bridge_v1.csv"
RECOVERY_PATH = DATA / "edgeiq_historical_figure_recovery_v1.csv"
RACE_STRENGTH_PATH = DATA / "edgeiq_race_strength_history_v1.csv"
OUT_PATH = DATA / "edgeiq_runner_history_detail_v1.csv"
SUMMARY_PATH = DATA / "edgeiq_runner_history_detail_v1_summary.csv"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def upper_text(value: object) -> str:
    return safe_text(value).upper()


def normalize_spaces(value: object) -> str:
    return re.sub(r"\s+", " ", safe_text(value)).strip()


def compact(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", upper_text(value).replace("'", "'").replace("'", "'"))


def normalize_horse(value: object) -> str:
    text = upper_text(value).replace("'", "'").replace("'", "'")
    text = re.sub(r"\([^)]*\)", " ", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def parse_float(value: object) -> float | None:
    text = safe_text(value).replace("$", "").replace(",", "").replace("KG", "").replace("kg", "").replace("L", "")
    if not text:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        number = float(match.group(0))
    except ValueError:
        return None
    return None if math.isnan(number) else number


def normalize_distance(value: object) -> str:
    number = parse_float(value)
    return "" if number is None else str(int(round(number)))


def normalize_race_no(value: object) -> str:
    text = safe_text(value)
    if not text:
        return ""
    match = re.search(r"\d+", text)
    return match.group(0) if match else text.upper()


def normalize_track_basic(value: object) -> str:
    text = upper_text(value)
    if not text:
        return ""
    for old, new in {"SPORTSBET-": "", "SPORTSBET ": "", "BET365 ": "", "LADBROKES ": "", "TAB ": "", "THE VALLEY": "MOONEE VALLEY", "MT V": "MOONEE VALLEY"}.items():
        text = text.replace(old, new)
    return normalize_spaces(re.sub(r"[^A-Z0-9]+", " ", text))


def load_track_alias_map() -> dict[str, str]:
    if not TRACK_ALIAS_PATH.exists():
        return {}
    df = pd.read_csv(TRACK_ALIAS_PATH, dtype=str).fillna("")
    alias_map = {}
    for row in df.to_dict("records"):
        if upper_text(row.get("chosen")) not in {"", "YES", "TRUE", "1"}:
            continue
        alias_key = compact(row.get("alias_key"))
        canonical = upper_text(row.get("canonical_track"))
        if alias_key and canonical:
            alias_map[alias_key] = canonical
    return alias_map


def canonical_track(value: object, alias_map: dict[str, str]) -> str:
    raw = upper_text(value)
    if not raw:
        return ""
    for candidate in [compact(raw), compact(normalize_track_basic(raw))]:
        if candidate and candidate in alias_map:
            return alias_map[candidate]
    return normalize_track_basic(raw) or raw


def compute_keys(df: pd.DataFrame, alias_map: dict[str, str]) -> pd.DataFrame:
    df = df.copy()
    df["track"] = df["track"].map(lambda value: canonical_track(value, alias_map))
    df["horse_match_key"] = df.apply(lambda row: normalize_horse(row.get("horse_key") or row.get("horse")), axis=1)
    df["track_key_norm"] = df["track"].map(compact)
    df["distance_norm"] = df["distance"].map(normalize_distance)
    df["race_no_norm"] = df["race_no"].map(normalize_race_no)
    df["match_key_primary"] = df.apply(lambda row: "|".join([safe_text(row["horse_match_key"]), safe_text(row["run_date_iso"]), safe_text(row["track_key_norm"]), safe_text(row["distance_norm"]), safe_text(row["race_no_norm"])]), axis=1)
    df["match_key_track_distance"] = df.apply(lambda row: "|".join([safe_text(row["horse_match_key"]), safe_text(row["run_date_iso"]), safe_text(row["track_key_norm"]), safe_text(row["distance_norm"])]), axis=1)
    df["detail_recovery_key"] = df.apply(lambda row: row["match_key_primary"] if safe_text(row["race_no_norm"]) else row["match_key_track_distance"], axis=1)
    return df


def run_base_builder() -> None:
    spec = importlib.util.spec_from_file_location("edgeiq_history_base_builder", BASE_CHECKPOINT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load base builder: {BASE_CHECKPOINT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "main"):
        raise RuntimeError("Base builder checkpoint does not expose main()")
    module.main()


def fill_blank(target: pd.Series, fallback: pd.Series) -> pd.Series:
    target_text = target.astype(str).fillna("").str.strip()
    fallback_text = fallback.astype(str).fillna("").str.strip()
    return target.where(target_text.ne(""), fallback)


def apply_recovery(base_df: pd.DataFrame, recovery_df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    if recovery_df.empty:
        base_df["recovered_rating"] = base_df.get("performance_rating", "")
        base_df["recovery_action"] = base_df.apply(lambda row: "ORIGINAL" if safe_text(row.get("run_rating")) else "RECOVERED_EXISTING_PERFORMANCE" if safe_text(row.get("performance_rating")) else "MISSING", axis=1)
        return base_df, 0
    existing = recovery_df[recovery_df["detail_row_exists"] == "YES"].copy()
    rename_cols = {col: f"recovery_{col}" for col in existing.columns if col != "detail_recovery_key"}
    existing = existing.rename(columns=rename_cols)
    merged = base_df.merge(existing, on="detail_recovery_key", how="left")
    for field in ["class_name", "condition", "finish_pos", "field_size", "barrier", "jockey", "trainer", "weight", "margin", "sp"]:
        recovery_col = f"recovery_{field}"
        if recovery_col in merged.columns:
            merged[field] = fill_blank(merged[field], merged[recovery_col])
    merged["recovered_rating"] = merged.apply(lambda row: safe_text(row.get("recovery_recovered_rating")) or safe_text(row.get("performance_rating")), axis=1)
    merged["recovery_action"] = merged["recovery_recovery_action"].fillna("")
    merged["recovery_source_file"] = merged["recovery_recovery_source_file"].fillna("") if "recovery_recovery_source_file" in merged.columns else ""
    merged["recovery_source_confidence"] = merged["recovery_recovery_source_confidence"].fillna("") if "recovery_recovery_source_confidence" in merged.columns else ""
    merged["recovery_match_method"] = merged["recovery_match_method"].fillna("") if "recovery_match_method" in merged.columns else ""

    new_rows = recovery_df[recovery_df["detail_row_exists"] == "NO"].copy()
    appended = 0
    if not new_rows.empty:
        existing_keys = set(merged["detail_recovery_key"].astype(str))
        new_rows = new_rows[~new_rows["detail_recovery_key"].astype(str).isin(existing_keys)].copy()
        appended = int(len(new_rows))
        if appended:
            mapped = pd.DataFrame({
                "horse": new_rows["horse"], "horse_key": new_rows["horse_key"], "track": new_rows["track"], "track_key": new_rows["track_key"],
                "race_date": new_rows["race_date"], "run_date_iso": new_rows["run_date_iso"], "race_no": new_rows["race_no"], "distance": new_rows["distance"],
                "class_name": new_rows["class_name"], "condition": new_rows["condition"], "finish_pos": new_rows["finish_pos"], "field_size": new_rows["field_size"],
                "barrier": new_rows["barrier"], "jockey": new_rows["jockey"], "weight": new_rows["weight"], "margin": new_rows["margin"], "sp": new_rows["sp"],
                "race_strength": new_rows["race_strength"], "run_rating": "", "performance_rating": "", "pos_800": "", "pos_400": "", "source_file": new_rows["source_file"],
                "source_confidence": new_rows["source_confidence"], "race_name": "", "prize_money": "", "trainer": new_rows["trainer"], "settling_position": "", "closing_sectional_rank": "",
                "last_600": "", "last_400": "", "last_200": "", "days_since_run": "", "weight_change": "", "class_change": "", "distance_change": "", "condition_change": "",
                "built_at": new_rows["built_at"], "detail_recovery_key": new_rows["detail_recovery_key"], "recovered_rating": new_rows["recovered_rating"], "recovery_action": new_rows["recovery_action"],
                "recovery_source_file": new_rows["recovery_source_file"], "recovery_source_confidence": new_rows["recovery_source_confidence"], "recovery_match_method": new_rows["match_method"],
            })
            merged = pd.concat([merged, mapped], ignore_index=True, sort=False)
    return merged, appended


def apply_race_strength(df: pd.DataFrame, race_strength_df: pd.DataFrame, alias_map: dict[str, str]) -> pd.DataFrame:
    if race_strength_df.empty:
        return df
    race_strength_df = race_strength_df.copy()
    race_strength_df["track"] = race_strength_df["track"].map(lambda value: canonical_track(value, alias_map))
    race_strength_df["track_key_norm"] = race_strength_df["track"].map(compact)
    race_strength_df["race_no_norm"] = race_strength_df["race_no"].map(normalize_race_no)
    race_strength_df["distance_norm"] = race_strength_df["distance"].map(normalize_distance)
    exact = {}
    relaxed = {}
    for row in race_strength_df.to_dict("records"):
        exact_key = "|".join([safe_text(row.get("race_date")), safe_text(row.get("track_key_norm")), safe_text(row.get("race_no_norm")), safe_text(row.get("distance_norm"))])
        relaxed_key = "|".join([safe_text(row.get("race_date")), safe_text(row.get("track_key_norm")), safe_text(row.get("distance_norm"))])
        exact.setdefault(exact_key, row)
        relaxed.setdefault(relaxed_key, row)
    strengths, sources = [], []
    for row in df.to_dict("records"):
        current = safe_text(row.get("race_strength"))
        if current:
            strengths.append(current)
            sources.append(safe_text(row.get("race_strength_source")) or safe_text(row.get("source_file")))
            continue
        exact_key = "|".join([safe_text(row.get("race_date")), safe_text(row.get("track_key_norm")), safe_text(row.get("race_no_norm")), safe_text(row.get("distance_norm"))])
        relaxed_key = "|".join([safe_text(row.get("race_date")), safe_text(row.get("track_key_norm")), safe_text(row.get("distance_norm"))])
        matched = exact.get(exact_key) or relaxed.get(relaxed_key) or {}
        strengths.append(safe_text(matched.get("race_strength")))
        sources.append(safe_text(matched.get("source_file")))
    df["race_strength"] = strengths
    df["race_strength_source"] = sources
    return df


def main() -> None:
    built_at = now_iso()
    alias_map = load_track_alias_map()
    run_base_builder()
    base_df = pd.read_csv(OUT_PATH, dtype=str).fillna("")
    base_df = compute_keys(base_df, alias_map)
    recovery_df = pd.read_csv(RECOVERY_PATH, dtype=str).fillna("") if RECOVERY_PATH.exists() else pd.DataFrame()
    race_strength_df = pd.read_csv(RACE_STRENGTH_PATH, dtype=str).fillna("") if RACE_STRENGTH_PATH.exists() else pd.DataFrame()
    enriched_df, appended_rows = apply_recovery(base_df, recovery_df)
    enriched_df = compute_keys(enriched_df.fillna(""), alias_map)
    enriched_df = apply_race_strength(enriched_df, race_strength_df, alias_map)
    enriched_df["run_rating_final"] = enriched_df.apply(lambda row: safe_text(row.get("run_rating")) or safe_text(row.get("recovered_rating")) or safe_text(row.get("performance_rating")), axis=1)
    enriched_df["rating_source"] = enriched_df.apply(lambda row: "ORIGINAL" if safe_text(row.get("run_rating")) else "RECOVERED" if safe_text(row.get("run_rating_final")) else "MISSING", axis=1)
    enriched_df["built_at"] = built_at
    enriched_df.sort_values(by=["horse_key", "run_date_iso", "distance_norm", "track", "race_no"], ascending=[True, False, False, True, True], inplace=True)
    enriched_df.to_csv(OUT_PATH, index=False)

    summary = pd.DataFrame([{
        "status": "PASS" if len(enriched_df) > 0 else "FAIL",
        "output_rows": int(len(enriched_df)),
        "appended_safe_history_rows": appended_rows,
        "rows_with_run_rating": int((enriched_df["run_rating"].astype(str).str.strip() != "").sum()),
        "rows_with_performance_rating": int((enriched_df["performance_rating"].astype(str).str.strip() != "").sum()),
        "rows_with_recovered_rating": int((enriched_df["recovered_rating"].astype(str).str.strip() != "").sum()),
        "rows_with_run_rating_final": int((enriched_df["run_rating_final"].astype(str).str.strip() != "").sum()),
        "rows_with_race_strength": int((enriched_df["race_strength"].astype(str).str.strip() != "").sum()),
        "rating_source_counts": "; ".join(f"{key}:{value}" for key, value in enriched_df["rating_source"].value_counts(dropna=False).to_dict().items()),
        "recovery_action_counts": "; ".join(f"{key}:{value}" for key, value in enriched_df["recovery_action"].fillna("").replace("", "NONE").value_counts(dropna=False).to_dict().items()),
        "built_at": built_at,
    }])
    summary.to_csv(SUMMARY_PATH, index=False)
    print("[EDGEIQ_RUNNER_HISTORY_DETAIL_V1] rows=", len(enriched_df))
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()

