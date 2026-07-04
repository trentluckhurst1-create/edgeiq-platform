from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
UNIVERSE = DATA / "edgeiq_vic_three_day_meeting_universe.csv"
OUT = DATA / "edgeiq_sectional_schema_v2.csv"

LOCAL_SECTIONAL_FILES = [
    "edgeiq_sectional_feature_engine_v2.csv",
    "edgeiq_sectional_intelligence_v2.csv",
    "edgeiq_sectional_master_v1.csv",
    "edgeiq_universal_sectional_memory_v1.csv",
    "edgeiq_vic_90day_sectional_warehouse_final_v1.csv",
    "sectionals.csv",
]

FIELDS = [
    "horse",
    "horse_key",
    "race_date",
    "track",
    "race_no",
    "distance",
    "sectional_200",
    "sectional_400",
    "sectional_600",
    "last_600",
    "last_400",
    "last_200",
    "early_speed",
    "midrace_speed",
    "late_speed",
    "sustained_speed",
    "fatigue_index",
    "sectional_rating",
    "sectional_confidence",
    "source",
]


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"", "-", "nan", "none", "null", "undefined"} else text


def norm_track(value: object) -> str:
    return " ".join(clean(value).upper().replace("_", " ").replace("|", " ").split())


def norm_horse(value: object) -> str:
    return clean(value).upper().replace("(NZ)", "").replace("(AUS)", "").replace("(GB)", "").replace("(IRE)", "")


def compact_key(value: object) -> str:
    return "".join(ch for ch in norm_horse(value) if ch.isalnum())


def race_no(value: object) -> str:
    digits = "".join(ch for ch in clean(value) if ch.isdigit())
    return str(int(digits)) if digits else ""


def runner_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    race_date = clean(row.get("race_date") or row.get("date") or row.get("meeting_date"))[:10]
    track = norm_track(row.get("track") or row.get("venue") or row.get("meeting"))
    race = race_no(row.get("race_no") or row.get("race_number") or row.get("race"))
    horse = compact_key(row.get("horse") or row.get("runner") or row.get("horse_name") or row.get("runner_name"))
    return race_date, track, race, horse


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    except Exception:
        return []


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{int(datetime.now().timestamp() * 1000)}.tmp")
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def first_text(row: dict[str, str], keys: list[str]) -> str:
    for key in keys:
        value = clean(row.get(key))
        if value:
            return value
    return ""


def build_sectional_index() -> dict[tuple[str, str, str, str], dict[str, str]]:
    index: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for file_name in LOCAL_SECTIONAL_FILES:
        path = DATA / file_name
        for row in read_csv(path):
            key = runner_key(row)
            if key[1] and key[2] and key[3] and key not in index:
                index[key] = {**row, "_source_file": file_name}
    return index


def main() -> None:
    universe = read_csv(UNIVERSE)
    sectional_index = build_sectional_index()
    rows: list[dict[str, object]] = []

    for base in universe:
        key = runner_key(base)
        if not key[1] or not key[2] or not key[3]:
            continue
        sectional = sectional_index.get(key, {})
        horse = first_text(base, ["horse", "runner", "horse_name", "runner_name"])
        rows.append({
            "horse": horse,
            "horse_key": first_text(base, ["horse_key", "runner_key"]) or compact_key(horse),
            "race_date": key[0],
            "track": key[1],
            "race_no": key[2],
            "distance": first_text(base, ["distance", "race_distance"]),
            "sectional_200": first_text(sectional, ["sectional_200", "split_200", "first_200"]),
            "sectional_400": first_text(sectional, ["sectional_400", "split_400", "first_400"]),
            "sectional_600": first_text(sectional, ["sectional_600", "split_600", "first_600"]),
            "last_600": first_text(sectional, ["last_600", "last600", "l600", "final_600"]),
            "last_400": first_text(sectional, ["last_400", "last400", "l400", "final_400"]),
            "last_200": first_text(sectional, ["last_200", "last200", "l200", "final_200"]),
            "early_speed": first_text(sectional, ["early_speed", "early_speed_rating", "early_sectional_rating"]),
            "midrace_speed": first_text(sectional, ["midrace_speed", "mid_speed", "middle_speed_rating"]),
            "late_speed": first_text(sectional, ["late_speed", "late_speed_rating", "closing_speed"]),
            "sustained_speed": first_text(sectional, ["sustained_speed", "sustained_speed_rating", "sustain_rating"]),
            "fatigue_index": first_text(sectional, ["fatigue_index", "fatigue", "fade_index"]),
            "sectional_rating": first_text(sectional, ["sectional_rating", "rating", "sectional_score"]),
            "sectional_confidence": first_text(sectional, ["sectional_confidence", "confidence"]) or ("LOCAL_MATCH" if sectional else "READY_FOR_SOURCE_MAPPING"),
            "source": first_text(sectional, ["source", "source_file"]) or clean(sectional.get("_source_file")) or "THREE_DAY_UNIVERSE_SCAFFOLD",
        })

    write_csv(OUT, rows)
    print("=" * 90)
    print("EDGEIQ SECTIONAL SCHEMA V2")
    print("=" * 90)
    print("ROWS:", len(rows))
    print("LOCAL MATCHES:", sum(1 for row in rows if row["source"] != "THREE_DAY_UNIVERSE_SCAFFOLD"))
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
