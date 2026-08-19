from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_TXT = ROOT / "public/data/edgeiq_form_guide_data_contract_v2_audit.txt"
OUT_JSON = ROOT / "public/data/edgeiq_form_guide_data_contract_v2_audit.json"

COMPONENT = ROOT / "src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx"
NORMALISER = ROOT / "src/edgeiq-os/race/services/formGuideNormaliser.ts"
FEED = ROOT / "public/data/edgeiq_form_guide_enriched_v2.json"

FIELD_COLUMNS = [
    "NO",
    "SILKS",
    "LAST 5",
    "HORSE",
    "TRAINER",
    "JOCKEY",
    "WT",
    "BAR",
    "DAYS",
    "EPI",
    "EARLY SPEED",
    "LATE SPEED",
    "SUITABILITY",
    "FORM MOMENTUM",
    "MARKET",
    "EDGEiQ PRICE",
]

RECENT_COLUMNS = [
    "DATE",
    "TRACK",
    "DIST",
    "COND",
    "POS",
    "CLASS",
    "MARGIN",
    "WT",
    "JOCKEY",
    "BAR",
    "SP",
    "ERI",
    "EPI",
    "8-6",
    "6-4",
    "4-2",
    "2-F",
]


def extract_array(text: str, name: str) -> list[str]:
    match = re.search(rf"const\s+{re.escape(name)}\s*=\s*\[(.*?)\]\s+as const", text, re.S)
    if not match:
        return []
    return re.findall(r'"([^"]+)"', match.group(1))


def load_feed_summary() -> dict:
    if not FEED.exists():
        return {"exists": False}
    with FEED.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    races = data.get("races", [])
    runners = [runner for race in races for runner in race.get("runners", [])]
    full_form = [run for runner in runners for run in runner.get("fullForm", [])]
    with_sectionals = [
        run
        for run in full_form
        if run.get("sectionalIndices")
        and any(run["sectionalIndices"].get(key) for key in ("index800To600", "index600To400", "index400To200", "index200ToFinish"))
    ]
    return {
        "exists": True,
        "races": len(races),
        "runners": len(runners),
        "historical_runs": len(full_form),
        "historical_runs_with_sectionals": len(with_sectionals),
    }


def main() -> int:
    component = COMPONENT.read_text(encoding="utf-8")
    normaliser = NORMALISER.read_text(encoding="utf-8")

    checks = []

    field_columns = extract_array(component, "summaryColumns")
    recent_columns = extract_array(component, "recentFormColumns")

    checks.append({"name": "exact_field_column_order", "pass": field_columns == FIELD_COLUMNS, "actual": field_columns})
    checks.append({"name": "exact_recent_form_column_order", "pass": recent_columns == RECENT_COLUMNS, "actual": recent_columns})
    checks.append({"name": "race_shape_absent_from_field_table", "pass": "RACE SHAPE" not in field_columns and "runner.shapeFit" not in component})
    checks.append({"name": "late_speed_after_early_speed", "pass": field_columns.index("LATE SPEED") == field_columns.index("EARLY SPEED") + 1 if "LATE SPEED" in field_columns and "EARLY SPEED" in field_columns else False})
    checks.append({"name": "recent_class_between_pos_margin", "pass": recent_columns[5:7] == ["CLASS", "MARGIN"] if len(recent_columns) >= 7 else False})
    checks.append({"name": "react_no_epi_summary_calculation", "pass": "epiSummary" not in component and "signedNumber(" not in component and "metricNumber(" not in component})
    checks.append({"name": "normaliser_owns_active_epi_metrics", "pass": all(token in normaliser for token in ("activeFieldEpi", "epiRank", "epiFieldAverage", "epiDifference"))})
    checks.append({"name": "profile_match_flags_present", "pass": "matchesToday" in normaliser and "is-current-match" in component})
    checks.append({"name": "historical_eri_epi_distinguished", "pass": "eri:" in normaliser and "historicalEpi" in normaliser and "raceRating" in normaliser})
    checks.append({"name": "sectionals_signed_not_zero_fallback", "pass": "signedMetricText" in normaliser and "index800To600" in normaliser})

    feed_summary = load_feed_summary()
    checks.append({"name": "canonical_enriched_feed_exists", "pass": feed_summary.get("exists") is True, "actual": feed_summary})
    checks.append({"name": "canonical_feed_has_historical_runs", "pass": feed_summary.get("historical_runs", 0) > 0, "actual": feed_summary})

    status = "PASS" if all(item["pass"] for item in checks) else "FAIL"
    result = {
        "status": f"EDGEIQ_FORM_GUIDE_DATA_CONTRACT_V2_AUDIT_{status}",
        "checks": checks,
        "feed_summary": feed_summary,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    OUT_TXT.write_text(
        "\n".join([result["status"], "", *[f"{'PASS' if item['pass'] else 'FAIL'} {item['name']}" for item in checks]]),
        encoding="utf-8",
    )
    print(result["status"])
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
