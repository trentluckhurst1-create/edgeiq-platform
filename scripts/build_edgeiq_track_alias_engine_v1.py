from __future__ import annotations

import csv
import re
import unicodedata
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
UNIVERSE = DATA / "edgeiq_vic_three_day_meeting_universe.csv"
IDENTITY = DATA / "edgeiq_sectional_identity_engine_v1.csv"
OUT = DATA / "edgeiq_track_alias_engine_v1.csv"

FIELDS = ["raw_track", "canonical_track", "track_key", "alias_type", "confidence", "notes"]

VIC_TRACKS = [
    "CAULFIELD HEATH", "CAULFIELD", "FLEMINGTON", "MOONEE VALLEY", "SANDOWN", "PAKENHAM",
    "CRANBOURNE", "BALLARAT", "BENDIGO", "GEELONG", "SEYMOUR", "WARRNAMBOOL", "SALE",
    "MORNINGTON", "HORSHAM", "STAWELL", "WANGARATTA", "WODONGA", "KYNETON", "KILMORE",
    "COLAC", "TERANG", "ARARAT", "CAMPERDOWN", "CASTERTON", "DONALD", "ECHUCA",
    "HAMILTON", "HEALESVILLE", "KERANG", "MILDURA", "MOE", "MURTOA", "NARACOORTE",
    "PAKENHAM SYNTHETIC", "SWAN HILL", "TATURA", "WERRIBEE", "YARRA VALLEY",
]

MANUAL = {
    "THE VALLEY": "MOONEE VALLEY",
    "MV": "MOONEE VALLEY",
    "LADBROKES PARK": "SANDOWN",
    "LADBROKES PARK HILLSIDE": "SANDOWN",
    "LADBROKES PARK LAKESIDE": "SANDOWN",
    "SANDOWN HILLSIDE": "SANDOWN",
    "SANDOWN LAKESIDE": "SANDOWN",
    "SPORTSBET PAKENHAM": "PAKENHAM",
    "PAKENHAM SYNTHETIC": "PAKENHAM",
    "BET365 GEELONG": "GEELONG",
    "CAULFIELD HEATH": "CAULFIELD HEATH",
}


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"} else text


def norm(value: object) -> str:
    text = clean(value).upper()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"\b(BET365|SPORTSBET|LADBROKES|TAB|MRC|VRC|RACING|CLUB)\b", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return " ".join(text.split())


def track_key(value: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", norm(value))


def canonical(value: object) -> str:
    raw = norm(value)
    if raw in MANUAL:
        return MANUAL[raw]
    for track in VIC_TRACKS:
        if raw == track or raw.endswith(f" {track}") or track in raw.split(" "):
            return track
    return raw


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    except Exception:
        return []


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{int(datetime.now().timestamp() * 1000)}.tmp")
    try:
        with tmp.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        tmp.replace(path)
    except PermissionError:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)


def track_values(row: dict[str, str]) -> list[str]:
    return [clean(row.get(name)) for name in ["track", "venue", "meeting", "matched_track"] if clean(row.get(name))]


def main() -> None:
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for track in VIC_TRACKS:
        for raw, alias_type, confidence, notes in [
            (track, "OFFICIAL", 100, "Victorian canonical track"),
            (track_key(track), "COLLAPSED", 96, "non-alphanumeric collapse"),
        ]:
            marker = f"{raw}|{track}"
            if marker not in seen:
                rows.append({"raw_track": raw, "canonical_track": track, "track_key": track_key(track), "alias_type": alias_type, "confidence": confidence, "notes": notes})
                seen.add(marker)
    for raw, target in MANUAL.items():
        marker = f"{raw}|{target}"
        if marker not in seen:
            rows.append({"raw_track": raw, "canonical_track": target, "track_key": track_key(target), "alias_type": "MANUAL", "confidence": 98, "notes": "sponsor/venue alias"})
            seen.add(marker)
    for path in [UNIVERSE, IDENTITY]:
        for row in read_csv(path):
            for raw in track_values(row):
                target = canonical(raw)
                marker = f"{raw}|{target}"
                if raw and marker not in seen:
                    rows.append({"raw_track": raw, "canonical_track": target, "track_key": track_key(target), "alias_type": "OBSERVED", "confidence": 95 if target in VIC_TRACKS else 70, "notes": f"observed in {path.name}"})
                    seen.add(marker)
    write_csv(OUT, rows, FIELDS)
    print("=" * 90)
    print("EDGEIQ TRACK ALIAS ENGINE V1")
    print("=" * 90)
    print("ALIASES:", len(rows))
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
