from __future__ import annotations

import csv
import math
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
UNIVERSE = DATA / "edgeiq_vic_three_day_meeting_universe.csv"
TRUSTED = DATA / "edgeiq_trusted_sectional_universe.csv"
OUT = DATA / "edgeiq_sectional_normalisation_v1.csv"

FIELDS = [
    "race_date", "track", "race_no", "horse", "horse_key", "distance",
    "raw_last_600", "raw_last_400", "raw_last_200", "early_speed_raw",
    "midrace_speed_raw", "late_speed_raw", "track_adjustment", "distance_adjustment",
    "condition_adjustment", "tempo_adjustment", "trust_penalty", "identity_penalty",
    "quality_penalty", "lineage_penalty", "duplicate_penalty", "payload_penalty",
    "physics_penalty", "reconstruction_penalty", "structure_penalty",
    "field_composition_confidence", "identity_v2_status", "identity_v3_status",
    "runner_entity_confidence", "trusted_identity_flag", "trusted_runner_identity",
    "trusted_modelling_identity", "normalised_late_speed", "normalised_sustained_speed",
    "fatigue_index", "sectional_rating", "normalisation_confidence",
]


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


def first(row: dict[str, str] | None, names: list[str]) -> str:
    if row is None:
        return ""
    for name in names:
        value = clean(row.get(name))
        if value:
            return value
    return ""


def norm_track(value: object) -> str:
    return " ".join(clean(value).upper().replace("_", " ").split())


def race_no(value: object) -> str:
    digits = re.sub(r"[^0-9]", "", clean(value).upper().replace("RACE", "").replace("R", ""))
    return str(int(digits)) if digits else ""


def horse_key(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        first(row, ["race_date", "date", "meeting_date"])[:10],
        norm_track(first(row, ["track", "venue", "meeting"])),
        race_no(first(row, ["race_no", "race_number", "race"])),
        horse_key(first(row, ["horse_key", "runner_key", "horse", "horse_name", "runner", "runner_name"])),
    )


def confidence(value: object) -> int:
    try:
        return max(0, min(100, int(round(float(clean(value))))))
    except ValueError:
        return 0


def penalty_row(trusted: dict[str, str] | None) -> dict[str, str]:
    if trusted is None or clean(trusted.get("trusted_for_modelling")).upper() not in {"YES", "PARTIAL"}:
        return {name: "100" for name in ["trust_penalty", "identity_penalty", "quality_penalty", "lineage_penalty", "duplicate_penalty", "payload_penalty", "physics_penalty", "reconstruction_penalty", "structure_penalty"]}
    identity = clean(trusted.get("identity_v3_status")).upper()
    physics = clean(trusted.get("physics_grade")).upper()
    structure = clean(trusted.get("payload_structure_type")).upper()
    recon = confidence(trusted.get("reconstruction_confidence"))
    trust = clean(trusted.get("trusted_for_modelling")).upper()
    runner = clean(trusted.get("trusted_runner_identity")).upper()
    return {
        "trust_penalty": "0" if trust == "YES" else "25",
        "identity_penalty": "0" if identity == "TRUSTED" else "12" if identity == "LIKELY" else "35" if identity == "PARTIAL" else "100",
        "quality_penalty": "0" if physics in {"ELITE", "GOOD"} else "20" if physics == "PARTIAL" else "100",
        "lineage_penalty": "0" if runner == "YES" else "25" if runner == "PARTIAL" else "100",
        "duplicate_penalty": "0",
        "payload_penalty": "0" if structure in {"FINAL_SPLITS_ONLY", "INCREMENTAL", "CUMULATIVE"} else "35",
        "physics_penalty": "0" if physics in {"ELITE", "GOOD"} else "20" if physics == "PARTIAL" else "100",
        "reconstruction_penalty": "0" if recon >= 80 else "15" if recon >= 65 else "40" if recon >= 35 else "100",
        "structure_penalty": "0" if structure in {"FINAL_SPLITS_ONLY", "INCREMENTAL", "CUMULATIVE"} else "35",
    }


def trusted_lookup() -> dict[tuple[str, str, str, str], dict[str, str]]:
    out: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in read_csv(TRUSTED):
        row_key = key(row)
        if row_key[3] and clean(row.get("trusted_for_modelling")).upper() in {"YES", "PARTIAL"}:
            out[row_key] = row
    return out


def main() -> None:
    trusted = trusted_lookup()
    rows: list[dict[str, object]] = []
    for base in read_csv(UNIVERSE):
        row_key = key(base)
        if not row_key[1] or not row_key[2] or not row_key[3]:
            continue
        sec = trusted.get(row_key)
        usable = sec is not None and clean(sec.get("trusted_for_modelling")).upper() == "YES"
        penalties = penalty_row(sec)
        rows.append({
            "race_date": row_key[0],
            "track": row_key[1],
            "race_no": row_key[2],
            "horse": first(base, ["horse", "horse_name", "runner", "runner_name"]),
            "horse_key": first(base, ["horse_key", "runner_key"]) or row_key[3],
            "distance": first(base, ["distance", "race_distance", "dist"]),
            "raw_last_600": first(sec, ["raw_last_600"]),
            "raw_last_400": first(sec, ["raw_last_400"]),
            "raw_last_200": first(sec, ["raw_last_200"]),
            "early_speed_raw": first(sec, ["early_speed_raw"]),
            "midrace_speed_raw": first(sec, ["midrace_speed_raw"]),
            "late_speed_raw": first(sec, ["late_speed_raw"]),
            "track_adjustment": "",
            "distance_adjustment": "",
            "condition_adjustment": "",
            "tempo_adjustment": "",
            **penalties,
            "field_composition_confidence": first(sec, ["field_composition_confidence"]),
            "identity_v2_status": first(sec, ["identity_v2_status"]),
            "identity_v3_status": first(sec, ["identity_v3_status"]),
            "runner_entity_confidence": first(sec, ["runner_entity_confidence"]),
            "trusted_identity_flag": first(sec, ["trusted_modelling_identity"]),
            "trusted_runner_identity": first(sec, ["trusted_runner_identity"]),
            "trusted_modelling_identity": first(sec, ["trusted_modelling_identity"]),
            "normalised_late_speed": first(sec, ["late_speed_raw"]) if usable else "",
            "normalised_sustained_speed": first(sec, ["sustained_speed"]) if usable else "",
            "fatigue_index": first(sec, ["fatigue_index"]) if usable else "",
            "sectional_rating": first(sec, ["sectional_rating"]) if usable else "",
            "normalisation_confidence": first(sec, ["sectional_confidence"]) if usable else "0",
        })
    write_csv(OUT, rows, FIELDS)
    print("=" * 90)
    print("EDGEIQ SECTIONAL NORMALISATION V1")
    print("=" * 90)
    print("ROWS:", len(rows))
    print("TRUSTED USED:", sum(1 for row in rows if row["normalisation_confidence"] != "0"))
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
