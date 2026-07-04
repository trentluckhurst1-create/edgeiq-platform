from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
UNIVERSE = DATA / "edgeiq_vic_three_day_meeting_universe.csv"
IDENTITY = DATA / "edgeiq_sectional_identity_engine_v1.csv"
MASTER = DATA / "edgeiq_sectional_master_v1.csv"
OUT = DATA / "edgeiq_horse_alias_engine_v1.csv"

FIELDS = ["raw_horse", "canonical_horse", "horse_key", "alias_key", "alias_type", "source", "confidence", "notes"]


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"} else text


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


def canonical_horse(value: object) -> str:
    text = clean(value).upper()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.replace("'", "").replace("`", "").replace("’", "").replace("‘", "")
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"\b(NZ|AUS|GB|IRE|USA|FR|JPN|SAF|GER)\b", "", text)
    text = re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9]+", " ", text)).strip()
    return text


def alias_key(value: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", canonical_horse(value))


def first(row: dict[str, str], names: list[str]) -> str:
    for name in names:
        value = clean(row.get(name))
        if value:
            return value
    return ""


def add_alias(rows: list[dict[str, object]], seen: set[tuple[str, str, str]], raw: str, source: str, supplied_key: str = "") -> None:
    raw = clean(raw)
    key = supplied_key or alias_key(raw)
    canonical = canonical_horse(raw)
    if not raw or not key:
        return
    variants = {
        raw: ("RAW", 100, "source spelling"),
        canonical: ("NORMALIZED", 98, "punctuation/case/bracket cleanup"),
        key: ("COLLAPSED", 96, "non-alphanumeric collapse"),
    }
    no_country = canonical_horse(re.sub(r"\b(NZ|AUS|GB|IRE|USA|FR|JPN|SAF|GER)\b", "", raw, flags=re.IGNORECASE))
    if no_country and no_country != canonical:
        variants[no_country] = ("COUNTRY_SUFFIX", 94, "country suffix removed")
    dehyphen = canonical_horse(raw.replace("-", " "))
    if dehyphen and dehyphen != canonical:
        variants[dehyphen] = ("HYPHEN", 94, "hyphen spacing normalised")
    for alias, (kind, confidence, notes) in variants.items():
        alias = clean(alias)
        marker = (raw, key, alias_key(alias))
        if alias and marker not in seen:
            rows.append({
                "raw_horse": raw,
                "canonical_horse": canonical,
                "horse_key": key,
                "alias_key": alias_key(alias),
                "alias_type": kind,
                "source": source,
                "confidence": confidence,
                "notes": notes,
            })
            seen.add(marker)


def main() -> None:
    rows: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    for source, path in [("three_day_universe", UNIVERSE), ("sectional_identity_v1", IDENTITY), ("sectional_master", MASTER)]:
        for row in read_csv(path):
            horse = first(row, ["horse", "horse_name", "runner", "runner_name", "matched_horse"])
            key = first(row, ["horse_key", "runner_key", "matched_horse_key"]) or alias_key(horse)
            add_alias(rows, seen, horse, source, key)
            matched = first(row, ["matched_horse"])
            if matched and matched != horse:
                add_alias(rows, seen, matched, source, first(row, ["matched_horse_key"]) or alias_key(matched))
    write_csv(OUT, rows, FIELDS)
    print("=" * 90)
    print("EDGEIQ HORSE ALIAS ENGINE V1")
    print("=" * 90)
    print("ALIASES:", len(rows))
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
