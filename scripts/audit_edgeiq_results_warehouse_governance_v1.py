from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
WAREHOUSE = DATA / "edgeiq_racingcom_results_warehouse_v2.csv"
OUT_DIR = ROOT / "docs" / "performance-intelligence" / "results-recovery-v40"
SUMMARY = OUT_DIR / "edgeiq_results_warehouse_governance_audit_v1.json"
DETAIL = OUT_DIR / "edgeiq_results_warehouse_cross_race_fingerprints_v1.csv"


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


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
        writer.writerows(rows)
    tmp.replace(path)


def race_no(value: Any) -> str:
    raw = clean(value)
    try:
        return str(int(float(raw)))
    except Exception:
        return raw


def race_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (clean(row.get("meeting_date")), clean(row.get("track")).upper(), race_no(row.get("race_no")))


def fingerprint(rows: list[dict[str, Any]]) -> str:
    parts = []
    for row in sorted(rows, key=lambda r: (race_no(r.get("finish_position")), clean(r.get("horse_no")), clean(r.get("horse_name")))):
        parts.append(
            "|".join(
                [
                    race_no(row.get("finish_position")),
                    clean(row.get("horse_no")),
                    horse_key(row.get("horse_name")),
                    clean(row.get("barrier")),
                    clean(row.get("trainer")),
                    clean(row.get("jockey")),
                    clean(row.get("weight")),
                    clean(row.get("margin")).upper().replace(" ", ""),
                    clean(row.get("sp")),
                    clean(row.get("status")).upper(),
                ]
            )
        )
    return "\n".join(parts)


def main() -> None:
    rows = read_csv(WAREHOUSE)
    by_race: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_race[race_key(row)].append(row)

    cross_race_groups = []
    for (date, track), race_rows in defaultdict(list).items():
        pass

    by_meeting: dict[tuple[str, str], dict[str, list[dict[str, str]]]] = defaultdict(lambda: defaultdict(list))
    for key, grouped in by_race.items():
        date, track, rn = key
        by_meeting[(date, track)][rn].extend(grouped)

    detail = []
    for (date, track), races in by_meeting.items():
        by_fp: dict[str, list[str]] = defaultdict(list)
        for rn, grouped in races.items():
            if grouped:
                by_fp[fingerprint(grouped)].append(rn)
        for fp, race_numbers in by_fp.items():
            if fp and len(race_numbers) > 1:
                cross_race_groups.append((date, track, sorted(race_numbers, key=lambda v: int(v) if v.isdigit() else 999)))
                detail.append(
                    {
                        "meeting_date": date,
                        "track": track,
                        "race_numbers": "|".join(sorted(race_numbers, key=lambda v: int(v) if v.isdigit() else 999)),
                        "fingerprint_rows": len(fp.splitlines()),
                    }
                )

    duplicate_runner_keys = defaultdict(int)
    duplicate_finish_positions = []
    source_url_mismatches = []
    empty_horse_names = []
    malformed_dates = []
    malformed_race_numbers = []

    for row in rows:
        key = (*race_key(row), horse_key(row.get("horse_name")))
        duplicate_runner_keys[key] += 1

        date = clean(row.get("meeting_date"))
        rn = race_no(row.get("race_no"))
        url = clean(row.get("source_url"))

        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            malformed_dates.append(row)

        if not re.fullmatch(r"\d+", rn):
            malformed_race_numbers.append(row)

        url_match = re.search(r"/race/(\d+)(?:[/?#]|$)", url)
        if url_match and url_match.group(1) != rn:
            source_url_mismatches.append(row)

        if not clean(row.get("horse_name")):
            empty_horse_names.append(row)

    for key, grouped in by_race.items():
        seen_positions = defaultdict(int)
        for row in grouped:
            finish = race_no(row.get("finish_position"))
            status = clean(row.get("status")).upper()
            if finish and status != "SCRATCHED":
                seen_positions[finish] += 1
        for finish, count in seen_positions.items():
            if count > 1:
                duplicate_finish_positions.append({"race_key": "|".join(key), "finish_position": finish, "count": count})

    duplicate_runner_key_count = sum(1 for count in duplicate_runner_keys.values() if count > 1)

    hamilton_r1 = fingerprint(by_race.get(("2026-08-01", "BET365 HAMILTON", "1"), []))
    hamilton_r8 = fingerprint(by_race.get(("2026-08-01", "BET365 HAMILTON", "8"), []))
    casterton_r1 = fingerprint(by_race.get(("2026-08-09", "CASTERTON", "1"), []))
    casterton_r8 = fingerprint(by_race.get(("2026-08-09", "CASTERTON", "8"), []))

    summary = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "warehouse": str(WAREHOUSE),
        "rows": len(rows),
        "unique_races": len(by_race),
        "CROSS_RACE_EXACT_FINGERPRINT_GROUPS": len(cross_race_groups),
        "HAMILTON_R1_R8_FINGERPRINT_DIFFERENT": bool(hamilton_r1 and hamilton_r8 and hamilton_r1 != hamilton_r8),
        "CASTERTON_R1_R8_FINGERPRINT_DIFFERENT": bool(casterton_r1 and casterton_r8 and casterton_r1 != casterton_r8),
        "duplicate_runner_race_keys": duplicate_runner_key_count,
        "malformed_race_numbers": len(malformed_race_numbers),
        "race_no_source_url_mismatches": len(source_url_mismatches),
        "duplicate_finish_positions": len(duplicate_finish_positions),
        "empty_horse_names": len(empty_horse_names),
        "malformed_dates": len(malformed_dates),
        "governance_status": "PASS"
        if not cross_race_groups
        and hamilton_r1
        and hamilton_r8
        and hamilton_r1 != hamilton_r8
        and casterton_r1
        and casterton_r8
        and casterton_r1 != casterton_r8
        and duplicate_runner_key_count == 0
        and not malformed_race_numbers
        and not source_url_mismatches
        and not empty_horse_names
        and not malformed_dates
        else "FAIL",
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_csv(DETAIL, detail, ["meeting_date", "track", "race_numbers", "fingerprint_rows"])

    for key, value in summary.items():
        print(f"{key}={value}")

    if summary["governance_status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
