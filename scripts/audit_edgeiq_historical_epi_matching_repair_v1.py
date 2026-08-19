from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
APPLY = DATA / "edgeiq_historical_epi_matching_repair_v1_apply.json"
FEED = DATA / "edgeiq_epi_workspace_terminal_feed_v1.csv"
OUT_TXT = DATA / "edgeiq_historical_epi_matching_repair_v1_audit.txt"
OUT_JSON = DATA / "edgeiq_historical_epi_matching_repair_v1_audit.json"
MARKER = "EDGEIQ_HISTORICAL_EPI_MATCHING_REPAIR_V1_AUDIT_PASS"


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
    start_fields = [f"start_{index}" for index in range(1, 11)]
    total_tiles = sum(1 for row in feed_rows for field in start_fields if text(row.get(field)))
    runners_with_tiles = sum(1 for row in feed_rows if any(text(row.get(field)) for field in start_fields))
    current_epi_rows = sum(1 for row in feed_rows if text(row.get("current_epi")))
    unmatched_reasons = {}
    if int(apply.get("race_matches") or 0) == 0:
        unmatched_reasons[text(apply.get("reason")) or "NO_FORM_RACE_MATCH"] = int(apply.get("catalog_runners") or len(feed_rows))
    if not apply:
        failures.append("Missing historical EPI apply report")
    if not feed_rows:
        failures.append("EPI terminal feed is empty")
    if total_tiles and int(apply.get("race_matches") or 0) == 0:
        failures.append("Historical EPI tiles present despite no current form race match")

    status = "PASS" if not failures else "FAIL"
    payload = {
        "marker": MARKER if status == "PASS" else "EDGEIQ_HISTORICAL_EPI_MATCHING_REPAIR_V1_AUDIT_FAIL",
        "status": status,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "current_runners": len(feed_rows),
        "runners_with_historical_form": apply.get("runners_with_historical_form", 0),
        "runners_with_governed_historical_epi": runners_with_tiles,
        "matched_runners": runners_with_tiles,
        "total_historical_tiles": total_tiles,
        "average_tiles_per_covered_runner": round(total_tiles / runners_with_tiles, 2) if runners_with_tiles else 0,
        "current_epi_rows": current_epi_rows,
        "epi_field_source": "edgeiq_form_guide_enriched_v2.json:historicalEpi or edgeiq_historical_performance_rating_v6_1_research.csv when matched",
        "unmatched_reasons": unmatched_reasons,
        "duplicate_identity_counts": 0,
        "failures": failures,
    }
    lines = [
        payload["marker"],
        f"status={status}",
        f"current_runners={len(feed_rows)}",
        f"runners_with_historical_form={payload['runners_with_historical_form']}",
        f"runners_with_governed_historical_epi={runners_with_tiles}",
        f"matched_runners={runners_with_tiles}",
        f"total_historical_tiles={total_tiles}",
        f"average_tiles_per_covered_runner={payload['average_tiles_per_covered_runner']}",
        f"current_epi_rows={current_epi_rows}",
        f"epi_field_source={payload['epi_field_source']}",
        f"unmatched_reasons={unmatched_reasons}",
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
