from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

csv.field_size_limit(1024 * 1024 * 128)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
PROFILE = DATA / "edgeiq_current_runner_profile_history_v1.csv"
BASE = DATA / "edgeiq_current_runner_performance_history_v1.csv"
WAREHOUSE = DATA / "edgeiq_racingcom_performance_warehouse_v2.csv"
AUDIT = DATA / "edgeiq_current_runner_performance_history_v1_audit.json"

FIELDS = [
    "current_race_date", "current_track", "current_race_no", "current_horse", "current_runner_key",
    "historical_race_date", "historical_track", "historical_race_no", "historical_horse",
    "distance", "race_class", "going", "finish", "margin", "field_size", "jockey", "trainer", "sp",
    "performance_rating", "epi", "early_sectional", "late_sectional", "last_600", "last_400", "last_200",
    "history_source", "rating_source", "sectional_source", "identity_certification", "strict_prior_certified",
]


def text(value: Any) -> str:
    value = "" if value is None else str(value)
    value = re.sub(r"\s+", " ", value).strip()
    return "" if value.lower() in {"", "none", "null", "nan", "-", "n/a", "na"} else value


def canon(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", text(value).upper())


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sectional_map() -> dict[tuple[str, str], dict[str, str]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in read_csv(WAREHOUSE):
        key = (text(row.get("race_date"))[:10], canon(row.get("horse") or row.get("horse_key")))
        if all(key):
            grouped[key].append(row)
    out: dict[tuple[str, str], dict[str, str]] = {}
    for key, rows in grouped.items():
        if len(rows) != 1:
            continue
        row = rows[0]
        out[key] = {
            "early_sectional": text(row.get("early_speed")),
            "late_sectional": text(row.get("late_speed")),
            "last_600": text(row.get("last_600") or row.get("last600")),
            "last_400": text(row.get("last_400") or row.get("last400")),
            "last_200": text(row.get("last_200") or row.get("last200")),
        }
    return out


def main() -> int:
    profile_rows = read_csv(PROFILE)
    base_rows = read_csv(BASE)
    if not profile_rows:
        raise SystemExit("PROFILE_HISTORY_EMPTY")

    preferred_by_runner: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in profile_rows:
        preferred_by_runner[text(row.get("current_runner_key"))].append(row)

    base_by_runner: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in base_rows:
        base_by_runner[text(row.get("current_runner_key"))].append(row)

    all_runner_keys = sorted(set(preferred_by_runner) | set(base_by_runner))
    sections = sectional_map()
    output: list[dict[str, str]] = []

    for runner_key in all_runner_keys:
        source = preferred_by_runner.get(runner_key) or base_by_runner.get(runner_key) or []
        source = sorted(source, key=lambda r: text(r.get("historical_race_date")), reverse=True)[:12]
        for candidate in source:
            row = {field: "" for field in FIELDS}
            for field in FIELDS:
                row[field] = text(candidate.get(field))
            if runner_key in preferred_by_runner:
                row["history_source"] = text(candidate.get("history_source")) or "RACING_COM_HORSE_PROFILE_FORM"
                row["rating_source"] = text(candidate.get("rating_source")) if row["performance_rating"] else ""
                row["identity_certification"] = text(candidate.get("identity_certification")) or "CURRENT_HORSE_PROFILE_URL_EXACT_STRICT_PRIOR"
                row["strict_prior_certified"] = "TRUE"
            sec = sections.get((row["historical_race_date"], canon(row["historical_horse"] or row["current_horse"])))
            if sec:
                for field, value in sec.items():
                    if value:
                        row[field] = value
                if any(sec.values()):
                    row["sectional_source"] = "edgeiq_racingcom_performance_warehouse_v2"
            output.append(row)

    output.sort(key=lambda r: (r["current_race_date"], r["current_track"], int(r["current_race_no"] or 0), canon(r["current_horse"]), r["historical_race_date"]), reverse=False)
    write_csv(BASE, output)

    grouped: dict[str, int] = defaultdict(int)
    rated_grouped: dict[str, int] = defaultdict(int)
    for row in output:
        grouped[row["current_runner_key"]] += 1
        if row["performance_rating"]:
            rated_grouped[row["current_runner_key"]] += 1

    audit = {
        "schemaVersion": "edgeiq_current_runner_performance_history_v1_audit",
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "historyRows": len(output),
        "runnersWith1PlusHistory": sum(1 for v in grouped.values() if v >= 1),
        "runnersWith3PlusHistory": sum(1 for v in grouped.values() if v >= 3),
        "runnersWith5PlusHistory": sum(1 for v in grouped.values() if v >= 5),
        "rowsWithRating": sum(1 for r in output if r["performance_rating"]),
        "runnersWith1PlusRatedHistory": sum(1 for v in rated_grouped.values() if v >= 1),
        "rowsWithAnySectional": sum(1 for r in output if any(r[f] for f in ("early_sectional", "late_sectional", "last_600", "last_400", "last_200"))),
        "profilePreferredRunners": len(preferred_by_runner),
        "fallbackRunners": sum(1 for key in all_runner_keys if key not in preferred_by_runner),
        "historySourceCounts": dict(sorted({s: sum(1 for r in output if r["history_source"] == s) for s in {r["history_source"] for r in output}}.items())),
        "output": str(BASE.relative_to(ROOT)).replace("\\", "/"),
    }
    AUDIT.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("EDGEIQ_CURRENT_RUNNER_PROFILE_HISTORY_MERGE PASS")
    for key, value in audit.items():
        if key not in {"historySourceCounts", "output", "schemaVersion", "generatedAt"}:
            print(f"{key.upper()}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
