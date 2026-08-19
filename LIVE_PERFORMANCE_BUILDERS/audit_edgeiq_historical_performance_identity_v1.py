
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CONFIG = ROOT / "config" / "performance-intelligence"
DOC_DIR = ROOT / "docs" / "performance-intelligence" / "horse-performance-rating"
MATCHES = DOC_DIR / "edgeiq_historical_performance_identity_matches_v1.csv"
MISSES = DOC_DIR / "edgeiq_historical_performance_identity_misses_v1.csv"
COLLISIONS = DOC_DIR / "edgeiq_historical_performance_identity_collisions_v1.csv"
REPORT = DOC_DIR / "edgeiq_historical_performance_identity_report_v1.md"

SECTIONAL = DATA / "edgeiq_runner_sectional_performance_v2.csv"
LENGTHS = DATA / "edgeiq_results_lengths_v_standard_v2.csv"
IDENTITY_MAP = CONFIG / "edgeiq_horse_performance_identity_map_v1.csv"


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

sectional_fields, sectional_rows = read_rows(SECTIONAL)
length_fields, length_rows = read_rows(LENGTHS)
identity_fields, identity_rows = read_rows(IDENTITY_MAP)

runner_keys: dict[str, dict[str, str]] = {}
for row in sectional_rows + length_rows:
    runner_id = text(row.get("canonical_runner_id"))
    race_id = text(row.get("canonical_race_id"))
    if not runner_id:
        continue
    key = f"{race_id}|{runner_id}"
    runner_keys.setdefault(key, {
        "canonical_race_id": race_id,
        "canonical_runner_id": runner_id,
        "race_date": text(row.get("race_date")),
        "track": text(row.get("track")),
        "race_number": text(row.get("race_number")),
        "race_distance_metres": text(row.get("race_distance_metres")),
        "canonical_surface_group": text(row.get("canonical_surface_group")),
    })

approved_by_source_name = {}
identity_collisions = []
if identity_rows:
    for idx, row in enumerate(identity_rows, start=1):
        if text(row.get("identity_status")) != "APPROVED":
            continue
        name = " ".join(text(row.get("source_horse_name")).split()).casefold()
        if not name:
            continue
        if name in approved_by_source_name:
            identity_collisions.append({
                "collision_type": "DUPLICATE_APPROVED_SOURCE_NAME",
                "source_horse_name": text(row.get("source_horse_name")),
                "first_canonical_horse_id": text(approved_by_source_name[name].get("canonical_horse_id")),
                "second_canonical_horse_id": text(row.get("canonical_horse_id")),
                "detail": "Multiple approved identities for the same normalised source horse name.",
            })
        approved_by_source_name[name] = row

matches = []
misses = []
for key, row in sorted(runner_keys.items()):
    # V2 speed rows expose canonical runner id, but not source horse name. The active observation builder requires winner_horse_name from rating-base rows.
    misses.append({
        **row,
        "miss_reason": "NO_GOVERNED_HORSE_IDENTITY_MAP_OR_NAME_FIELD",
        "identity_map_exists": "YES" if IDENTITY_MAP.exists() else "NO",
        "source_horse_name_available": "NO",
        "detail": "Governed V2 performance rows carry canonical_runner_id but no source_horse_name/canonical_horse_id usable by the current exact-name horse identity map contract.",
    })

write_csv(MATCHES, ["canonical_race_id", "canonical_runner_id", "canonical_horse_id", "canonical_horse_name", "match_method", "identity_status"], matches)
write_csv(MISSES, ["canonical_race_id", "canonical_runner_id", "race_date", "track", "race_number", "race_distance_metres", "canonical_surface_group", "miss_reason", "identity_map_exists", "source_horse_name_available", "detail"], misses)
write_csv(COLLISIONS, ["collision_type", "source_horse_name", "first_canonical_horse_id", "second_canonical_horse_id", "detail"], identity_collisions)

lines = [
    "# EDGEiQ Historical Performance Identity Audit V1",
    "",
    f"Historical race runners: `{len(runner_keys)}`",
    f"Racing.com horse/runner codes available: `{len({row['canonical_runner_id'] for row in runner_keys.values()})}`",
    f"Identity map exists: `{'YES' if IDENTITY_MAP.exists() else 'NO'}`",
    f"Identity map rows: `{len(identity_rows)}`",
    f"Exact identity matches: `{len(matches)}`",
    f"Identity misses: `{len(misses)}`",
    f"Ambiguous identities: `{len(identity_collisions)}`",
    "",
    "## Finding",
    "Historical identity is not the first zero-row stage because the performance rating base currently has zero rows. However, once normalisation is restored, the active observation builder would still require `config/performance-intelligence/edgeiq_horse_performance_identity_map_v1.csv` and source horse names from rating-base rows.",
    "The current V2 sectional and lengths rows expose `canonical_runner_id` but no source horse name or canonical horse id under the active exact-name identity-map contract. No deterministic repair is applied in this audit.",
]
REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

print(json.dumps({
    "historical_race_runners": len(runner_keys),
    "identity_map_exists": IDENTITY_MAP.exists(),
    "matches": len(matches),
    "misses": len(misses),
    "collisions": len(identity_collisions),
    "report": str(REPORT),
}, indent=2))
