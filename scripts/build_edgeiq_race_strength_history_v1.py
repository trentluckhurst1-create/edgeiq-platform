from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
TRACK_ALIAS_PATH = DATA / "edgeiq_track_alias_bridge_v1.csv"
HISTORICAL_RACE_RATINGS_PATH = DATA / "historical_race_ratings.csv"
RESULTS_REPORT_PATH = DATA / "results_report.csv"
OUT_PATH = DATA / "edgeiq_race_strength_history_v1.csv"


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


def parse_float(value: object) -> float | None:
    text = safe_text(value).replace("$", "").replace(",", "")
    if not text:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


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


def main() -> None:
    built_at = now_iso()
    alias_map = load_track_alias_map()
    frames = []

    if HISTORICAL_RACE_RATINGS_PATH.exists():
        hr = pd.read_csv(HISTORICAL_RACE_RATINGS_PATH, dtype=str).fillna("")
        if not hr.empty:
            frames.append(pd.DataFrame({
                "track": hr["track"].map(lambda value: canonical_track(value, alias_map)),
                "track_key": hr["track"].map(lambda value: compact(canonical_track(value, alias_map))),
                "race_date": hr["race_date"],
                "race_no": hr["race_no"].map(normalize_race_no),
                "distance": hr["distance"].map(normalize_distance),
                "class": hr["race_class_clean"].where(hr["race_class_clean"].astype(str).str.strip().ne(""), hr["race_class"]),
                "condition": hr["condition"],
                "race_strength": hr["race_strength_rating"],
                "field_strength": hr["field_depth_adj"],
                "source_file": HISTORICAL_RACE_RATINGS_PATH.name,
                "source_confidence": "PRIMARY_HISTORICAL_RACE_RATINGS",
                "built_at": built_at,
            }))

    if RESULTS_REPORT_PATH.exists():
        rr = pd.read_csv(RESULTS_REPORT_PATH, dtype=str).fillna("")
        if not rr.empty:
            rr["track_canonical"] = rr["track"].map(lambda value: canonical_track(value, alias_map))
            grouped = rr.groupby(["race_date", "track_canonical", "race_no", "distance"], dropna=False, as_index=False).agg({"track_condition": "first", "race_strength": "first", "race_rating": "first"})
            frames.append(pd.DataFrame({
                "track": grouped["track_canonical"],
                "track_key": grouped["track_canonical"].map(compact),
                "race_date": grouped["race_date"],
                "race_no": grouped["race_no"].map(normalize_race_no),
                "distance": grouped["distance"].map(normalize_distance),
                "class": "",
                "condition": grouped["track_condition"],
                "race_strength": grouped["race_strength"].where(grouped["race_strength"].astype(str).str.strip().ne(""), grouped["race_rating"]),
                "field_strength": "",
                "source_file": RESULTS_REPORT_PATH.name,
                "source_confidence": "SECONDARY_RESULTS_REPORT",
                "built_at": built_at,
            }))

    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["track", "track_key", "race_date", "race_no", "distance", "class", "condition", "race_strength", "field_strength", "source_file", "source_confidence", "built_at"])
    if not combined.empty:
        combined["distance"] = combined["distance"].map(normalize_distance)
        combined["race_no"] = combined["race_no"].map(normalize_race_no)
        combined["strength_num"] = combined["race_strength"].map(parse_float)
        combined = combined[combined["strength_num"].notna()].copy()
        combined["priority"] = combined["source_confidence"].map({"PRIMARY_HISTORICAL_RACE_RATINGS": 1, "SECONDARY_RESULTS_REPORT": 2}).fillna(99)
        combined["dedupe_key"] = combined.apply(lambda row: "|".join([safe_text(row["race_date"]), safe_text(row["track_key"]), safe_text(row["race_no"]), safe_text(row["distance"]), safe_text(row["class"])]), axis=1)
        combined.sort_values(by=["priority"], inplace=True)
        combined = combined.drop_duplicates(subset=["dedupe_key"], keep="first")
        combined = combined.drop(columns=["priority", "strength_num", "dedupe_key"])
        combined.sort_values(by=["race_date", "track", "race_no", "distance", "class"], inplace=True)
    combined.to_csv(OUT_PATH, index=False)
    print("[EDGEIQ_RACE_STRENGTH_HISTORY_V1] rows=", len(combined))
    if not combined.empty:
        print(combined.head(10).to_string(index=False))


if __name__ == "__main__":
    main()

