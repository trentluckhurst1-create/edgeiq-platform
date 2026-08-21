from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from edgeiq_three_day_window_v1_common import build_three_day_window

csv.field_size_limit(1024 * 1024 * 128)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "operations-readiness" / "current-runner-intelligence"

FORM_GUIDE = DATA / "edgeiq_form_guide_enriched_v2.json"
RACE_FIELDS = DATA / "race_fields.csv"
ROW_AUDIT = DATA / "edgeiq_current_runner_intelligence_audit_v1.csv"

OUT_CSV = DOCS / "edgeiq_current_epr_join_forensics_v1.csv"
OUT_JSON = DOCS / "edgeiq_current_epr_join_forensics_v1.json"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"", "none", "null", "nan", "n/a", "na", "-"} else text


def norm_runner(value: Any) -> str:
    text = clean(value).upper().replace("'", "").replace("`", "")
    return "".join(ch for ch in text if ch.isalnum())


def norm_track(value: Any) -> str:
    text = clean(value).upper()
    for token in ("BET365", "SPORTSBET", "LADBROKES", "TAB", "THE", "RACECOURSE", "RACING", "TRACK"):
        text = text.replace(token, " ")
    return "".join(ch for ch in text if ch.isalnum())


def race_no(value: Any) -> str:
    digits = "".join(ch for ch in clean(value).upper().replace("R", "") if ch.isdigit())
    return str(int(digits)) if digits else ""


def normal_date(value: Any) -> str:
    return clean(value)[:10]


def number(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("value")
    text = clean(value).replace("$", "").replace(",", "")
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def key(date: Any, track: Any, race: Any, horse: Any) -> tuple[str, str, str, str]:
    return (normal_date(date), norm_track(track), race_no(race), norm_runner(horse))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def latest_eligible_history(runner: dict[str, Any], race_date: str) -> tuple[str, str]:
    latest_date = ""
    latest_epi = ""
    for run in runner.get("fullForm", []):
        if not isinstance(run, dict):
            continue
        run_date = normal_date(run.get("date"))
        if not run_date or run_date >= race_date:
            continue
        epi_value = number(run.get("historicalEpi"))
        if epi_value is None:
            continue
        if run_date > latest_date:
            latest_date = run_date
            latest_epi = f"{epi_value:.6g}"
    return latest_date, latest_epi


def race_field_index() -> dict[tuple[str, str, str, str], dict[str, str]]:
    out: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in read_csv(RACE_FIELDS):
        out[key(row.get("race_date"), row.get("track") or row.get("display_track"), row.get("race_no"), row.get("horse"))] = row
    return out


def row_audit_index() -> dict[tuple[str, str, str, str], dict[str, str]]:
    out: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in read_csv(ROW_AUDIT):
        out[key(row.get("race_date"), row.get("meeting"), row.get("race"), row.get("horse"))] = row
    return out


def classify(row: dict[str, Any]) -> str:
    if row["scratched"] == "YES":
        return "SCRATCHED"
    if clean(row["epr_value"]):
        return "POPULATED_GOVERNED_EPR"
    if clean(row["epr_missing_class"]).startswith("LEGITIMATE_"):
        return "LEGITIMATE_GOVERNED_EXCLUSION"
    if row["epr_missing_class"] == "JOIN_FAILURE":
        return "BLOCKING_JOIN_FAILURE"
    if clean(row["epr_missing_class"]):
        return clean(row["epr_missing_class"])
    return "UNKNOWN"


def build_forensics(current_date: str, include_scratched: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = json.loads(FORM_GUIDE.read_text(encoding="utf-8"))
    fields = race_field_index()
    audit = row_audit_index()
    rows: list[dict[str, Any]] = []

    for race in payload.get("races", []):
        race_date = normal_date(race.get("raceDate"))
        if race_date != current_date:
            continue
        for runner in race.get("runners", []):
            if not isinstance(runner, dict):
                continue
            scratched = bool(runner.get("scratched"))
            if scratched and not include_scratched:
                continue
            runner_key = key(race_date, race.get("meeting"), race.get("raceNumber"), runner.get("runnerName"))
            field_row = fields.get(runner_key, {})
            audit_row = audit.get(runner_key, {})
            latest_date, latest_epi = latest_eligible_history(runner, race_date)
            epr_value = clean(audit_row.get("epr_value")) or clean((runner.get("epi") or {}).get("value") if isinstance(runner.get("epi"), dict) else runner.get("epi"))
            epr_status = clean(audit_row.get("epr_status")) or clean((runner.get("epi") or {}).get("status") if isinstance(runner.get("epi"), dict) else "")
            epr_missing_class = clean(audit_row.get("epr_missing_class"))
            epr_reason = clean(audit_row.get("epr_reason")) or clean((runner.get("epi") or {}).get("missingReason") if isinstance(runner.get("epi"), dict) else "")
            history_rows = int(number(audit_row.get("history_count")) or len(runner.get("fullForm") or []))
            out = {
                "meeting_date": race_date,
                "track": clean(race.get("meeting")),
                "race_no": race_no(race.get("raceNumber")),
                "runner_number": clean(runner.get("runnerNumber")),
                "horse": clean(runner.get("runnerName")),
                "current_runner_id": clean(runner.get("runnerId") or field_row.get("runner_id")),
                "current_horse_id": clean(field_row.get("horse_code")) or clean(field_row.get("horse_id")),
                "normalized_horse": norm_runner(runner.get("normalisedRunnerName") or runner.get("runnerName")),
                "scratched": "YES" if scratched else "NO",
                "history_match": "YES" if history_rows > 0 else "NO",
                "history_rows": history_rows,
                "latest_eligible_history_date": latest_date,
                "latest_eligible_epi": latest_epi,
                "epr_value": epr_value,
                "epr_status": epr_status,
                "epr_source_artifact": clean(audit_row.get("epr_source_artifact")) or clean((runner.get("epi") or {}).get("source") if isinstance(runner.get("epi"), dict) else ""),
                "failure_reason": "NONE_POPULATED" if epr_value else (epr_missing_class or epr_reason or "UNKNOWN"),
                "epr_missing_class": epr_missing_class,
            }
            out["current_join_status"] = classify(out)
            out["prior_failure_verdict"] = (
                "STALE_PUBLICATION_RESOLVED_BY_CURRENT_REFRESH"
                if out["current_join_status"] == "POPULATED_GOVERNED_EPR"
                else out["current_join_status"]
            )
            rows.append(out)

    counts = Counter(row["current_join_status"] for row in rows)
    summary = {
        "schema_version": "edgeiq_current_epr_join_forensics_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "current_date": current_date,
        "include_scratched": include_scratched,
        "rows": len(rows),
        "counts": dict(sorted(counts.items())),
        "join_failures": counts.get("BLOCKING_JOIN_FAILURE", 0),
        "verdict": "PASS" if counts.get("BLOCKING_JOIN_FAILURE", 0) == 0 else "FAIL",
        "source_artifacts": {
            "form_guide": rel(FORM_GUIDE),
            "race_fields": rel(RACE_FIELDS),
            "row_audit": rel(ROW_AUDIT),
        },
    }
    return rows, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date")
    parser.add_argument("--include-scratched", action="store_true")
    args = parser.parse_args()

    current_date = args.date or build_three_day_window().today
    rows, summary = build_forensics(current_date, args.include_scratched)
    fields = [
        "meeting_date",
        "track",
        "race_no",
        "runner_number",
        "horse",
        "current_runner_id",
        "current_horse_id",
        "normalized_horse",
        "scratched",
        "history_match",
        "history_rows",
        "latest_eligible_history_date",
        "latest_eligible_epi",
        "epr_value",
        "epr_status",
        "epr_source_artifact",
        "failure_reason",
        "epr_missing_class",
        "current_join_status",
        "prior_failure_verdict",
    ]
    write_csv(OUT_CSV, rows, fields)
    OUT_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("EDGEIQ_CURRENT_EPR_JOIN_FORENSICS_V1")
    print(f"CURRENT_DATE={current_date}")
    print(f"ROWS={summary['rows']}")
    for name, count in summary["counts"].items():
        print(f"{name}={count}")
    print(f"JOIN_FAILURES={summary['join_failures']}")
    print(f"VERDICT={summary['verdict']}")
    print(f"CSV={OUT_CSV}")
    print(f"JSON={OUT_JSON}")
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
