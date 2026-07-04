from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
UNIVERSE = DATA / "edgeiq_vic_three_day_meeting_universe.csv"
OUT = DATA / "edgeiq_racingcom_sectional_catalogue.csv"

LOCAL_SECTIONAL_FILES = [
    "edgeiq_sectional_master_v1.csv",
    "edgeiq_sectional_intelligence_v2.csv",
    "edgeiq_sectional_feature_engine_v2.csv",
    "edgeiq_vic_90day_sectional_warehouse_final_v1.csv",
    "edgeiq_vic_sectional_warehouse_v1.csv",
    "edgeiq_universal_sectional_memory_v1.csv",
    "sectionals.csv",
]

FIELDS = [
    "race_date",
    "track",
    "race_no",
    "race_id",
    "source_url",
    "sectional_available",
    "status",
    "notes",
]


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"", "-", "nan", "none", "null", "undefined"} else text


def norm_track(value: object) -> str:
    return " ".join(clean(value).upper().replace("_", " ").replace("|", " ").split())


def race_no(value: object) -> str:
    digits = "".join(ch for ch in clean(value) if ch.isdigit())
    return str(int(digits)) if digits else ""


def race_key(row: dict[str, str]) -> tuple[str, str, str]:
    return clean(row.get("race_date") or row.get("date") or row.get("meeting_date"))[:10], norm_track(row.get("track") or row.get("venue") or row.get("meeting")), race_no(row.get("race_no") or row.get("race_number") or row.get("race"))


def canonical_race_key(race_date: object, track: object, race_no_value: object) -> str:
    return f"{clean(race_date)[:10]}_{norm_track(track)}_R{race_no(race_no_value)}"


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


def load_local_sectional_index() -> dict[tuple[str, str, str], dict[str, str]]:
    index: dict[tuple[str, str, str], dict[str, str]] = {}
    for name in LOCAL_SECTIONAL_FILES:
        path = DATA / name
        for row in read_csv(path):
            key = race_key(row)
            if key[1] and key[2] and key not in index:
                index[key] = {**row, "_source_file": name}
    return index


def main() -> None:
    universe = read_csv(UNIVERSE)
    sectional_index = load_local_sectional_index()
    races: dict[tuple[str, str, str], dict[str, str]] = {}

    for row in universe:
        key = race_key(row)
        if key[0] and key[1] and key[2]:
            races.setdefault(key, row)

    rows: list[dict[str, object]] = []
    for key, race in sorted(races.items(), key=lambda item: (item[0][0], item[0][1], int(item[0][2] or 0))):
        local = sectional_index.get(key)
        available = local is not None
        race_id = first_text(local or {}, ["race_id", "raceId", "meeting_race_id"]) or canonical_race_key(key[0], key[1], key[2])
        source_url = first_text(local or {}, ["source_url", "url", "race_url", "sectional_url"])
        rows.append({
            "race_date": key[0],
            "track": key[1],
            "race_no": key[2],
            "race_id": race_id,
            "source_url": source_url,
            "sectional_available": "YES" if available else "NO",
            "status": "AVAILABLE_LOCAL" if available else "READY_FOR_SOURCE_MAPPING",
            "notes": f"matched {clean((local or {}).get('_source_file'))}" if available else "safe scaffold only; Racing.com source mapping pending",
        })

    write_csv(OUT, rows)
    print("=" * 90)
    print("EDGEIQ RACING.COM SECTIONAL CATALOGUE")
    print("=" * 90)
    print("RACES:", len(rows))
    print("AVAILABLE:", sum(1 for row in rows if row["sectional_available"] == "YES"))
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
