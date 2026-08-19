from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
APPLY = DATA / "edgeiq_current_map_matching_repair_v1_apply.json"
FEED = DATA / "edgeiq_map_terminal_feed_v1.csv"
OUT_TXT = DATA / "edgeiq_current_map_matching_repair_v1_audit.txt"
OUT_JSON = DATA / "edgeiq_current_map_matching_repair_v1_audit.json"
MARKER = "EDGEIQ_CURRENT_MAP_MATCHING_REPAIR_V1_AUDIT_PASS"


def text(value: object) -> str:
    if value is None:
        return ""
    output = str(value).strip()
    if output.lower() in {"", "-", "none", "null", "undefined", "n/a", "na"}:
        return ""
    return output


def rows() -> list[dict[str, str]]:
    if not FEED.exists():
        return []
    with FEED.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    failures: list[str] = []
    apply = json.loads(APPLY.read_text(encoding="utf-8")) if APPLY.exists() else {}
    feed_rows = rows()
    current_races = len({row.get("race_key", "") for row in feed_rows if text(row.get("race_key"))})
    current_runners = len(feed_rows)
    map_source_rows = int(apply.get("map_source_rows") or 0)
    race_matches = int(apply.get("race_matches") or 0)
    runner_matches = int(apply.get("runner_matches") or 0)
    speed_value_coverage = sum(1 for row in feed_rows if text(row.get("early_speed")) or text(row.get("projected_position")) or text(row.get("run_style")))
    run_style_coverage = sum(1 for row in feed_rows if text(row.get("run_style")))
    unmatched_race_reasons = Counter()
    unmatched_runner_reasons = Counter()
    if race_matches == 0:
        unmatched_race_reasons[text(apply.get("reason")) or "NO_SOURCE_RACE_MATCH"] = current_races
    if runner_matches == 0:
        unmatched_runner_reasons[text(apply.get("reason")) or "NO_SOURCE_RUNNER_MATCH"] = current_runners
    duplicate_keys = Counter((row.get("race_key", ""), row.get("no", ""), row.get("horse", "")) for row in feed_rows)
    duplicate_count = sum(1 for count in duplicate_keys.values() if count > 1)
    missing_key_counts = {
        "race_key": sum(1 for row in feed_rows if not text(row.get("race_key"))),
        "horse": sum(1 for row in feed_rows if not text(row.get("horse"))),
        "no": sum(1 for row in feed_rows if not text(row.get("no"))),
    }

    if not apply:
        failures.append("Missing apply report")
    if not feed_rows:
        failures.append("Map terminal feed is empty")
    if speed_value_coverage > 0 and race_matches == 0:
        failures.append("Speed evidence present despite apply report showing no source race matches")

    status = "PASS" if not failures else "FAIL"
    payload = {
        "marker": MARKER if status == "PASS" else "EDGEIQ_CURRENT_MAP_MATCHING_REPAIR_V1_AUDIT_FAIL",
        "status": status,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "current_races": current_races,
        "current_runners": current_runners,
        "map_source_rows": map_source_rows,
        "race_matches": race_matches,
        "runner_matches": runner_matches,
        "speed_value_coverage": speed_value_coverage,
        "run_style_coverage": run_style_coverage,
        "unmatched_race_reasons": dict(unmatched_race_reasons),
        "unmatched_runner_reasons": dict(unmatched_runner_reasons),
        "duplicated_keys": duplicate_count,
        "missing_key_counts": missing_key_counts,
        "source_dates": apply.get("source_dates", []),
        "catalog_dates": apply.get("catalog_dates", []),
        "feed_changed": False,
        "failures": failures,
    }

    lines = [
        payload["marker"],
        f"status={status}",
        f"current_races={current_races}",
        f"current_runners={current_runners}",
        f"map_source_rows={map_source_rows}",
        f"race_matches={race_matches}",
        f"runner_matches={runner_matches}",
        f"speed_value_coverage={speed_value_coverage}",
        f"run_style_coverage={run_style_coverage}",
        f"unmatched_race_reasons={dict(unmatched_race_reasons)}",
        f"unmatched_runner_reasons={dict(unmatched_runner_reasons)}",
        f"duplicated_keys={duplicate_count}",
        f"missing_key_counts={missing_key_counts}",
    ]
    if failures:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in failures)
    OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("\n".join(lines))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
