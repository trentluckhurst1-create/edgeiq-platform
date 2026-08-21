from __future__ import annotations

import csv
import importlib.util
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
RECOVERY = ROOT / "docs" / "performance-intelligence" / "results-recovery-v40"
WAREHOUSE = DATA / "edgeiq_racingcom_results_warehouse_v2.csv"
BACKUP_DIR = DATA / "backups" / "results-warehouse-v40"

HARVESTER = ROOT / "scripts" / "build_edgeiq_racingcom_rendered_results_harvester_v2.py"

TARGETS = [
    {
        "meeting_date": "2026-08-01",
        "track": "BET365 HAMILTON",
        "race_no": "8",
        "source_url": "https://www.racing.com/form/2026-08-01/bet365-hamilton/race/8",
        "expected_winner": "Cinnamon Kiss",
        "expected_distance": "1200m",
        "expected_race_time": "1:15.84",
    },
    {
        "meeting_date": "2026-08-09",
        "track": "CASTERTON",
        "race_no": "8",
        "source_url": "https://www.racing.com/form/2026-08-09/casterton/race/8",
        "expected_winner": "Thurmond (GB)",
        "expected_distance": "3500m",
        "expected_race_time": "4:01.78",
    },
]

R1_REVALIDATION_TARGETS = [
    {
        "meeting_date": "2026-08-01",
        "track": "BET365 HAMILTON",
        "race_no": "1",
        "source_url": "https://www.racing.com/form/2026-08-01/bet365-hamilton/race/1",
    },
    {
        "meeting_date": "2026-08-09",
        "track": "CASTERTON",
        "race_no": "1",
        "source_url": "https://www.racing.com/form/2026-08-09/casterton/race/1",
    },
]

OUT_COLUMNS = [
    "built_at",
    "meeting_date",
    "track",
    "race_no",
    "race_key",
    "source_url",
    "page_loaded",
    "visible_results",
    "race_name",
    "distance",
    "race_class",
    "track_condition",
    "race_time",
    "finish_position",
    "horse_no",
    "horse_name",
    "horse_key",
    "barrier",
    "trainer",
    "jockey",
    "weight",
    "prizemoney_earned",
    "in_run",
    "margin",
    "sp",
    "status",
    "error",
]


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def norm(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean(value).upper())


def horse_key(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", re.sub(r"\([^)]*\)", "", clean(value).upper()))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
    tmp.replace(path)


def load_harvester_module():
    spec = importlib.util.spec_from_file_location("edgeiq_rendered_harvester_v2", HARVESTER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load harvester module: {HARVESTER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def race_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (clean(row.get("meeting_date")), clean(row.get("track")).upper(), clean(row.get("race_no")))


def runner_fingerprint(rows: list[dict[str, Any]]) -> str:
    parts = []
    for row in sorted(rows, key=lambda r: (clean(r.get("finish_position")), clean(r.get("horse_no")), clean(r.get("horse_name")))):
        parts.append(
            "|".join(
                [
                    clean(row.get("finish_position")),
                    clean(row.get("horse_no")),
                    horse_key(row.get("horse_name")),
                    clean(row.get("barrier")),
                    clean(row.get("trainer")),
                    clean(row.get("jockey")),
                    clean(row.get("weight")),
                    clean(row.get("margin")).upper().replace(" ", ""),
                    clean(row.get("sp")),
                ]
            )
        )
    return "\n".join(parts)


def validate_staged_rows(target: dict[str, str], rows: list[dict[str, Any]], compare_r1_rows: list[dict[str, Any]]) -> None:
    label = f"{target['meeting_date']}|{target['track']}|R{target['race_no']}"
    if not rows:
        raise RuntimeError(f"{label}: no staged rows")

    requested = target["race_no"]
    url_match = re.search(r"/race/(\d+)(?:[/?#]|$)", target["source_url"])
    if not url_match or url_match.group(1) != requested:
        raise RuntimeError(f"{label}: source URL race number does not match target")

    if any(clean(row.get("race_no")) != requested for row in rows):
        raise RuntimeError(f"{label}: staged row race_no mismatch")

    if any(clean(row.get("source_url")) != target["source_url"] for row in rows):
        raise RuntimeError(f"{label}: staged source URL mismatch")

    if any(clean(row.get("page_loaded")).upper() != "TRUE" for row in rows):
        raise RuntimeError(f"{label}: page load was not successful")

    if any(clean(row.get("visible_results")).upper() != "TRUE" for row in rows):
        raise RuntimeError(f"{label}: visible results were not proven")

    if len({horse_key(row.get("horse_name")) for row in rows}) != len(rows):
        raise RuntimeError(f"{label}: duplicate staged runner identities")

    winners = [row for row in rows if clean(row.get("finish_position")) == "1"]
    if len(winners) != 1:
        raise RuntimeError(f"{label}: expected exactly one winner, got {len(winners)}")

    if target.get("expected_winner") and clean(winners[0].get("horse_name")) != target["expected_winner"]:
        raise RuntimeError(
            f"{label}: winner mismatch: {clean(winners[0].get('horse_name'))!r} != {target['expected_winner']!r}"
        )

    if target.get("expected_distance"):
        distances = {clean(row.get("distance")) for row in rows}
        if distances != {target["expected_distance"]}:
            raise RuntimeError(f"{label}: distance mismatch: {sorted(distances)}")

    if target.get("expected_race_time"):
        race_times = {clean(row.get("race_time")) for row in rows}
        if race_times != {target["expected_race_time"]}:
            raise RuntimeError(f"{label}: race_time mismatch: {sorted(race_times)}")

    finishers = [clean(row.get("finish_position")) for row in rows if clean(row.get("finish_position"))]
    if len(finishers) != len(set(finishers)):
        raise RuntimeError(f"{label}: duplicate finish positions")

    if clean(target.get("race_no")) != "1" and compare_r1_rows and runner_fingerprint(compare_r1_rows) == runner_fingerprint(rows):
        raise RuntimeError(f"{label}: staged fingerprint equals current R1 fingerprint")


def warehouse_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    def intish(value: Any, default: int) -> int:
        try:
            return int(float(clean(value)))
        except Exception:
            return default

    return (
        clean(row.get("meeting_date")),
        clean(row.get("track")),
        intish(row.get("race_no"), 9999),
        intish(row.get("finish_position"), 9999),
        intish(row.get("horse_no"), 9999),
        clean(row.get("horse_name")),
    )


def main() -> None:
    if not WAREHOUSE.exists():
        raise FileNotFoundError(WAREHOUSE)

    built_at = datetime.now(timezone.utc).isoformat()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    RECOVERY.mkdir(parents=True, exist_ok=True)

    backup = BACKUP_DIR / f"edgeiq_racingcom_results_warehouse_v2.pre_v40_{stamp}.csv"
    shutil.copy2(WAREHOUSE, backup)

    harvester = load_harvester_module()
    harvest_targets = TARGETS + R1_REVALIDATION_TARGETS

    payload = harvester.run_node(
        [
            {
                "meeting_date": target["meeting_date"],
                "track": target["track"],
                "race_no": target["race_no"],
                "race_key": f"{target['meeting_date']}|{target['track']}|{target['race_no']}",
                "source_url": target["source_url"],
            }
            for target in harvest_targets
        ]
    )

    staged_rows: list[dict[str, Any]] = []
    for row in payload.get("rows", []):
        staged_rows.append(
            {
                "built_at": built_at,
                "meeting_date": clean(row.get("meeting_date")),
                "track": clean(row.get("track")),
                "race_no": clean(row.get("race_no")),
                "race_key": clean(row.get("race_key")) or f"{clean(row.get('meeting_date'))}|{clean(row.get('track'))}|{clean(row.get('race_no'))}",
                "source_url": clean(row.get("source_url")),
                "page_loaded": clean(row.get("page_loaded")),
                "visible_results": clean(row.get("visible_results")),
                "race_name": clean(row.get("raceName")),
                "distance": clean(row.get("distance")),
                "race_class": clean(row.get("raceClass")),
                "track_condition": clean(row.get("trackCondition")),
                "race_time": clean(row.get("raceTime")),
                "finish_position": clean(row.get("finishPosition")),
                "horse_no": clean(row.get("horseNo")),
                "horse_name": clean(row.get("horseName")),
                "horse_key": clean(row.get("horseKey")) or horse_key(row.get("horseName")),
                "barrier": clean(row.get("barrier")),
                "trainer": clean(row.get("trainer")),
                "jockey": clean(row.get("jockey")),
                "weight": clean(row.get("weight")),
                "prizemoney_earned": clean(row.get("prizemoneyEarned")),
                "in_run": clean(row.get("inRun")),
                "margin": clean(row.get("margin")),
                "sp": clean(row.get("sp")),
                "status": clean(row.get("status")),
                "error": clean(row.get("error")),
            }
        )

    pages_file = RECOVERY / "edgeiq_target_r8_rendered_pages_v40.json"
    pages_file.write_text(json.dumps(payload.get("pages", []), indent=2), encoding="utf-8")

    write_csv(RECOVERY / "edgeiq_target_r8_staging_v40.csv", staged_rows, OUT_COLUMNS)

    existing = read_csv(WAREHOUSE)

    r1_repairs_required: list[dict[str, str]] = []
    for r1_target in R1_REVALIDATION_TARGETS:
        r8_target = next(
            target
            for target in TARGETS
            if target["meeting_date"] == r1_target["meeting_date"] and target["track"] == r1_target["track"]
        )
        current_r1 = [row for row in existing if race_key(row) == (r1_target["meeting_date"], r1_target["track"], "1")]
        staged_r8 = [row for row in staged_rows if race_key(row) == (r8_target["meeting_date"], r8_target["track"], "8")]
        if current_r1 and staged_r8 and runner_fingerprint(current_r1) == runner_fingerprint(staged_r8):
            r1_repairs_required.append(r1_target)

    replacement_targets = TARGETS + r1_repairs_required
    target_keys = {(target["meeting_date"], target["track"], target["race_no"]) for target in replacement_targets}
    removed = [row for row in existing if race_key(row) in target_keys]
    retained = [row for row in existing if race_key(row) not in target_keys]

    if len(removed) not in {19, 38}:
        raise RuntimeError(f"Expected to remove 19 target rows, or 38 after R1 partial-repair detection; got {len(removed)}")

    for target in replacement_targets:
        rows = [row for row in staged_rows if race_key(row) == (target["meeting_date"], target["track"], target["race_no"])]
        compare_r1_rows = [
            row
            for row in staged_rows
            if race_key(row) == (target["meeting_date"], target["track"], "1")
        ]
        if not compare_r1_rows:
            compare_r1_rows = [
                row
                for row in existing
                if race_key(row) == (target["meeting_date"], target["track"], "1")
            ]
        validate_staged_rows(target, rows, compare_r1_rows)

    staged_replacements = [row for row in staged_rows if race_key(row) in target_keys]
    repaired = retained + staged_replacements
    repaired.sort(key=warehouse_sort_key)

    if len(repaired) != len(existing) - len(removed) + len(staged_replacements):
        raise RuntimeError("Repaired row-count reconciliation failed")

    tmp = WAREHOUSE.with_suffix(WAREHOUSE.suffix + ".v40.tmp")
    write_csv(tmp, repaired, OUT_COLUMNS)

    reread = read_csv(tmp)
    if len(reread) != len(repaired):
        raise RuntimeError("Temporary repaired warehouse did not round-trip")

    tmp.replace(WAREHOUSE)

    audit = {
        "status": "PASS",
        "backup": str(backup),
        "removed_rows": len(removed),
        "inserted_rows": len(staged_replacements),
        "r1_repairs_required": [
            f"{target['meeting_date']}|{target['track']}|R1" for target in r1_repairs_required
        ],
        "target_pages": payload.get("pages", []),
        "runtime_error": payload.get("runtime_error", ""),
        "built_at": built_at,
    }
    (RECOVERY / "edgeiq_target_r8_repair_v40_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")

    print("EDGEIQ_TARGET_R8_REPAIR_V40=PASS")
    print(f"BACKUP={backup}")
    print(f"REMOVED_ROWS={len(removed)}")
    print(f"INSERTED_ROWS={len(staged_replacements)}")
    print(f"R1_REPAIRS_REQUIRED={len(r1_repairs_required)}")
    print(f"STAGING={RECOVERY / 'edgeiq_target_r8_staging_v40.csv'}")


if __name__ == "__main__":
    main()
