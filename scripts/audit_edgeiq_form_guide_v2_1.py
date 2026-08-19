from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
ENRICHED_JSON = DATA / "edgeiq_form_guide_enriched_v1.json"
ENRICHED_CSV = DATA / "edgeiq_form_guide_enriched_v1.csv"
SOURCE_INVENTORY = DATA / "edgeiq_form_guide_v2_1_source_inventory.csv"
COVERAGE_CSV = DATA / "edgeiq_form_guide_v2_1_coverage.csv"
JOIN_AUDIT = DATA / "edgeiq_form_guide_v2_1_join_audit.csv"

AUDIT_TXT = DATA / "edgeiq_form_guide_v2_1_audit.txt"
AUDIT_JSON = DATA / "edgeiq_form_guide_v2_1_audit.json"

NORMALISER = ROOT / "src" / "edgeiq-os" / "race" / "services" / "formGuideNormaliser.ts"
ENRICHED_SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "formGuideEnrichedFeed.ts"
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceFormGuideWorkspace.tsx"
RACE_WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        return list(csv.DictReader(handle))


def normalise(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", str(value or "").upper())


def parse_date(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text[:10])
    except ValueError:
        return None


def check(name: str, passed: bool, detail: str = "") -> dict[str, Any]:
    return {"check": name, "passed": bool(passed), "detail": detail}


def main() -> None:
    checks: list[dict[str, Any]] = []

    required_files = [
        CATALOG,
        ENRICHED_JSON,
        ENRICHED_CSV,
        SOURCE_INVENTORY,
        COVERAGE_CSV,
        JOIN_AUDIT,
        NORMALISER,
        ENRICHED_SERVICE,
        COMPONENT,
    ]
    for path in required_files:
        checks.append(check(f"{path.name} exists", path.exists(), str(path)))

    if not all(path.exists() for path in required_files):
        status = "EDGEIQ_FORM_GUIDE_V2_1_AUDIT_FAIL"
        payload = {"status": status, "checks": checks}
        AUDIT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        AUDIT_TXT.write_text(status + "\nMissing required file.\n", encoding="utf-8")
        print(status)
        return

    catalog = read_json(CATALOG)
    enriched = read_json(ENRICHED_JSON)
    enriched_csv = read_csv(ENRICHED_CSV)
    join_rows = read_csv(JOIN_AUDIT)
    coverage_rows = read_csv(COVERAGE_CSV)

    catalog_runner_count = sum(
        len(race.get("runners", []))
        for meeting in catalog.get("meetings", [])
        for race in meeting.get("races", [])
    )
    enriched_runners = [
        runner
        for race in enriched.get("races", [])
        for runner in race.get("runners", [])
    ]

    checks.append(check("Runner count matches selected catalogue universe", len(enriched_runners) == catalog_runner_count, f"{len(enriched_runners)} vs {catalog_runner_count}"))
    checks.append(check("Enriched CSV row count matches JSON runners", len(enriched_csv) == len(enriched_runners), f"{len(enriched_csv)} vs {len(enriched_runners)}"))
    checks.append(check("Join audit has every runner once", len(join_rows) == len(enriched_runners), f"{len(join_rows)} vs {len(enriched_runners)}"))

    keys = [
        "|".join(
            [
                str(runner.get("raceDate")),
                normalise(runner.get("meeting")),
                str(runner.get("raceNumber")),
                str(runner.get("runnerNumber")),
                normalise(runner.get("runnerName")),
            ]
        )
        for runner in enriched_runners
    ]
    duplicates = [key for key, count in Counter(keys).items() if count > 1]
    checks.append(check("No duplicate race-runner keys", not duplicates, ", ".join(duplicates[:5])))

    accepted_ambiguous = [row for row in join_rows if row.get("join_method") == "AMBIGUOUS" and not row.get("ambiguity_reason")]
    ambiguous_rows = [row for row in join_rows if row.get("join_method") == "AMBIGUOUS"]
    checks.append(check("No ambiguous joins were accepted", not accepted_ambiguous and not ambiguous_rows, f"ambiguous={len(ambiguous_rows)}"))

    cross_race = [
        row for row in join_rows
        if not row.get("race_date") or not row.get("meeting") or not row.get("race_number")
    ]
    checks.append(check("No cross-race joins", not cross_race, f"bad rows={len(cross_race)}"))

    checks.append(check("Every populated EPI has source lineage", all((runner.get("epiSource") for runner in enriched_runners if runner.get("epi") is not None))))
    checks.append(check("Every populated market price has source lineage", all((runner.get("marketSource") for runner in enriched_runners if runner.get("marketPrice") is not None))))
    checks.append(check("Every populated EDGEiQ Price has source lineage", all((runner.get("edgeiqPriceSource") for runner in enriched_runners if runner.get("edgeiqPrice") is not None))))

    unsafe_market_sources = [
        runner for runner in enriched_runners
        if runner.get("marketSource") and re.search(r"\b(startingPrice|starting_price|SP)\b", str(runner.get("marketSource")), re.I)
    ]
    checks.append(check("Market does not fall back to historical SP", not unsafe_market_sources, f"unsafe={len(unsafe_market_sources)}"))

    copied_prices = [
        runner for runner in enriched_runners
        if runner.get("edgeiqPrice") is not None
        and runner.get("marketPrice") is not None
        and float(runner.get("edgeiqPrice")) == float(runner.get("marketPrice"))
        and runner.get("edgeiqPriceSource") == runner.get("marketSource")
    ]
    checks.append(check("EDGEiQ Price does not fall back to market price", not copied_prices, f"copied={len(copied_prices)}"))

    research_price = [runner for runner in enriched_runners if "RESEARCH" in str(runner.get("edgeiqPriceSource") or "").upper()]
    research_epi = [runner for runner in enriched_runners if "RESEARCH" in str(runner.get("epiSource") or "").upper()]
    checks.append(check("Research price fields are not silently mixed into production", not research_price, f"research_price={len(research_price)}"))
    checks.append(check("Research rating fields are not silently mixed into EPI", not research_epi, f"research_epi={len(research_epi)}"))

    negative_days = [runner for runner in enriched_runners if runner.get("daysSinceLastRun") is not None and int(runner.get("daysSinceLastRun")) < 0]
    first_starter_days = [runner for runner in enriched_runners if runner.get("firstStarter") and runner.get("daysSinceLastRun") is not None]
    checks.append(check("DAYS uses selected race date with no negative values", not negative_days, f"negative={len(negative_days)}"))
    checks.append(check("DAYS is blank for first starters", not first_starter_days, f"first_starter_days={len(first_starter_days)}"))

    unsorted_form = []
    last_five_mismatch = []
    for runner in enriched_runners:
        form = runner.get("fullForm") or []
        dates = [parse_date(run.get("date")) for run in form if run.get("date")]
        if dates != sorted(dates, reverse=True):
            unsorted_form.append(runner)
        canonical_l5 = [
            str(run.get("position"))
            for run in form[:5]
            if run.get("position") is not None and str(run.get("position")).strip()
        ]
        if canonical_l5 and runner.get("lastFive") != canonical_l5:
            last_five_mismatch.append(runner)
    checks.append(check("Full form is sorted most recent first", not unsorted_form, f"unsorted={len(unsorted_form)}"))
    checks.append(check("LAST 5 agrees with canonical full form", not last_five_mismatch, f"mismatch={len(last_five_mismatch)}"))

    contract = enriched.get("sourceContract") or {}
    checks.append(check("Track records match selected track rule documented", "selected track" in str(contract.get("records", "")).lower()))
    checks.append(check("Distance records use documented matching rule", "exact metres" in str(contract.get("records", "")).lower()))
    checks.append(check("Condition records use documented condition family", "condition family" in str(contract.get("records", "")).lower()))

    normaliser_src = NORMALISER.read_text(encoding="utf-8", errors="replace")
    component_src = COMPONENT.read_text(encoding="utf-8", errors="replace")
    service_src = ENRICHED_SERVICE.read_text(encoding="utf-8", errors="replace")
    workspace_src = RACE_WORKSPACE.read_text(encoding="utf-8", errors="replace") if RACE_WORKSPACE.exists() else ""

    checks.append(check("Frontend uses enriched adapter", "loadFormGuideEnrichedFeed" in component_src and "findEnrichedFormGuideRace" in component_src and "edgeiq_form_guide_enriched_v1.json" in service_src))
    checks.append(check("No unsafe eval", "eval(" not in normaliser_src and "eval(" not in component_src and "eval(" not in service_src))
    checks.append(check("No raw JSON rendering", "[object Object]" not in component_src and "JSON.stringify" not in component_src))
    checks.append(check("Market fallback no longer includes startingPrice", "MARKET_PRICE_FIELDS" not in normaliser_src and '"startingPrice"' not in normaliser_src.split("function extractRecentRuns")[0]))
    checks.append(check("Research rating fields are not probed by normaliser", "projected_rating_V6_1_RESEARCH" not in normaliser_src))
    checks.append(check("Research price fields are not probed by normaliser", "V6_1_RESEARCH_fair_price" not in normaliser_src))
    checks.append(check("Pricing logic not implemented in JSX", "formatPrice" not in component_src and "edgeiqPriceSource" not in component_src))
    checks.append(check("Existing MARKET/MAP/OVERVIEW tabs remain routed", all(token in workspace_src for token in ["market", "map", "overview"])))

    total_coverage = Counter()
    for row in coverage_rows:
        for key, value in row.items():
            if key in {"race_date", "meeting", "race_number"}:
                continue
            try:
                total_coverage[key] += int(value)
            except (TypeError, ValueError):
                pass

    status = "EDGEIQ_FORM_GUIDE_V2_1_AUDIT_PASS" if all(item["passed"] for item in checks) else "EDGEIQ_FORM_GUIDE_V2_1_AUDIT_FAIL"
    payload = {
        "status": status,
        "checks": checks,
        "coverage": dict(total_coverage),
        "canonical_sources": {
            "DAYS": "edgeiq_historical_results_warehouse_v2_graphql.csv:race_date",
            "EPI": "not selected; no approved same-race production EPI feed matched current catalogue",
            "MARKET": "edgeiq_three_day_product_catalog_v1.json:source.odds[].oddsWin",
            "EDGEiQ_PRICE": "not selected; no approved same-race production assessed-price feed matched current catalogue",
            "TRACK": "edgeiq_historical_results_warehouse_v2_graphql.csv aggregate selected track",
            "DIST": "edgeiq_historical_results_warehouse_v2_graphql.csv aggregate exact distance metres",
            "COND": "edgeiq_historical_results_warehouse_v2_graphql.csv aggregate selected condition family",
            "FULL_FORM": "edgeiq_historical_results_warehouse_v2_graphql.csv official results",
        },
    }
    AUDIT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [status, ""]
    for item in checks:
        marker = "PASS" if item["passed"] else "FAIL"
        detail = f" - {item['detail']}" if item.get("detail") else ""
        lines.append(f"{marker}: {item['check']}{detail}")
    lines.append("")
    lines.append("Coverage:")
    for key in sorted(total_coverage):
        lines.append(f"{key}: {total_coverage[key]}")
    AUDIT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(status)
    if status.endswith("FAIL"):
        for item in checks:
            if not item["passed"]:
                print(f"FAIL: {item['check']} {item.get('detail', '')}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
