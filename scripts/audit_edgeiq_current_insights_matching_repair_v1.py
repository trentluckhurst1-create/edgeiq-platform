from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
APPLY = DATA / "edgeiq_current_insights_matching_repair_v1_apply.json"
FEED = DATA / "edgeiq_insights_terminal_feed_v1.csv"
OUT_TXT = DATA / "edgeiq_current_insights_matching_repair_v1_audit.txt"
OUT_JSON = DATA / "edgeiq_current_insights_matching_repair_v1_audit.json"
MARKER = "EDGEIQ_CURRENT_INSIGHTS_MATCHING_REPAIR_V1_AUDIT_PASS"

CATEGORIES = [
    "stable_intent",
    "prep_stage",
    "heavy_skill",
    "campaign_profile",
    "distance_profile",
    "track_profile",
    "late_strength",
    "suitability",
    "form_momentum",
    "race_shape_relevance",
    "map_pressure",
    "market_behaviour",
]


def text(value: object) -> str:
    if value is None:
        return ""
    output = str(value).strip()
    if output.lower() in {"", "-", "none", "null", "undefined", "n/a", "na"}:
        return ""
    return output


def load_rows() -> list[dict[str, str]]:
    if not FEED.exists():
        return []
    with FEED.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    failures: list[str] = []
    apply = json.loads(APPLY.read_text(encoding="utf-8")) if APPLY.exists() else {}
    rows = load_rows()
    cards = [row for row in rows if text(row.get("row_kind")) == "card"]
    runners = [row for row in rows if text(row.get("row_kind")) == "runner"]
    value_rows = sum(1 for row in rows if text(row.get("key_insight")) or text(row.get("edge")) or text(row.get("card_value")) or text(row.get("card_detail")))
    current_category_coverage = {category: 0 for category in CATEGORIES}
    reason = text(apply.get("reason")) or "UNKNOWN"
    if not apply:
        failures.append("Missing insights apply report")
    if not rows:
        failures.append("Insights terminal feed is empty")
    if value_rows > 0 and int(apply.get("race_matches") or 0) == 0:
        failures.append("Insight values present even though apply report shows no matched current source races")

    status = "PASS" if not failures else "FAIL"
    payload = {
        "marker": MARKER if status == "PASS" else "EDGEIQ_CURRENT_INSIGHTS_MATCHING_REPAIR_V1_AUDIT_FAIL",
        "status": status,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "catalog_races": apply.get("catalog_races", 0),
        "source_races": apply.get("source_races", 0),
        "race_matches": apply.get("race_matches", 0),
        "terminal_rows": len(rows),
        "card_rows": len(cards),
        "runner_rows": len(runners),
        "value_rows": value_rows,
        "category_coverage": current_category_coverage,
        "source_evidence_by_category": apply.get("source_evidence_by_category", {}),
        "unmatched_reason": reason,
        "failures": failures,
    }
    lines = [
        payload["marker"],
        f"status={status}",
        f"catalog_races={payload['catalog_races']}",
        f"source_races={payload['source_races']}",
        f"race_matches={payload['race_matches']}",
        f"terminal_rows={len(rows)}",
        f"card_rows={len(cards)}",
        f"runner_rows={len(runners)}",
        f"value_rows={value_rows}",
        f"unmatched_reason={reason}",
        "category_coverage:",
    ]
    lines.extend(f"- {category}: {current_category_coverage[category]}" for category in CATEGORIES)
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
